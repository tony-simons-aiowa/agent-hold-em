"""service.py — TableService: the single, process-wide game/turn orchestrator
(docs/ARCHITECTURE.md §5).

Owns: the engine `Table`, per-seat runners (real `HermesSeatRunner` or dev-only
`FakeSeatRunner`), the turn scheduler (one in-flight agent decision per table,
deadline fallback, hand-end delay), persistence (`store.py`), and event broadcast.
`plugin_api.py` is a thin FastAPI wrapper around this class's public methods.

Concurrency model (see docs/ARCHITECTURE.md §5 for the full spec):
  - One `threading.RLock` guards all mutable state.
  - A small `ThreadPoolExecutor` (max 3) runs blocking `SeatRunner.decide()` calls.
  - Exactly one in-flight decision per table, keyed by `turn_id` (uuid4 hex).
  - A generation counter makes a retired instance's callbacks/timers inert — this
    is what makes the singleton guard (`get_service()`) safe across a hot re-mount.
  - `threading.Timer` provides the hand-end delay and a deadline safety net (the
    primary deadline bound is `SeatRunner.decide()`'s own `deadline_s`; this timer
    is a belt-and-suspenders backstop in case a runner ever fails to self-bound).
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
import uuid
from collections import OrderedDict
from typing import Any, Callable, Optional

from .engine import Action, IllegalAction, Table
from .engine.views import build_public_history, build_view
from .controller import models as models_mod
from .controller.fake import FakeSeatRunner
from .controller.runner import HermesSeatRunner
from .controller.types import DecisionRequest, SeatAgentConfig
from .controller.parse import sanitize_talk
from . import profiles as profiles_mod, store

logger = logging.getLogger(__name__)

__all__ = ["TableService", "ServiceError", "get_service"]

_HUMAN_AVATAR = "🧑"
_HUMAN_NAME = "You"
_DEFAULT_AVATAR = "🤖"
_AVATAR_ALLOWLIST = frozenset({
    "🦊", "🐙", "🧪", "🤖", "🐺", "🦉", "🐍", "🦁", "🐯", "🐻", "🐼", "🦅",
    "🐲", "🐉", "👻", "🎩", "🕶️", "🃏", "😈", "🤡", "🧠", "👾", "🐸", "🦂",
    "🦈", "🐢", "🐳", "🦄", "🐧",
})
_PERSONALITIES = frozenset({"cautious", "aggressive", "balanced"})
_MAX_NAME_LEN = 24
_MAX_RECENT_ACTIONS = 64
_TALK_TTL_S = 8.0
_MAX_CHAT = 80
_MAX_CHAT_TEXT = 160
_CHAT_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_QUI = {
    "aggressive": ("Keep up. The pot isn't waiting for you.", "That hesitation is getting expensive.", "I like the sound of chips moving."),
    "cautious": ("I'm watching every chip you put in.", "Patience pays. Usually yours pays me.", "Go on, make this interesting."),
    "balanced": ("Let's see what you've got.", "The table remembers that move.", "You make this look easy. Almost."),
}
_DEADLINE_SAFETY_MARGIN_S = 3.0  # backstop over the runner's own deadline_s
_DEV_ENV_VAR = "AGENT_HOLD_EM_DEV"
_NAME_SANITIZE_RE = re.compile(r"[^\w \-'.]", re.UNICODE)


class ServiceError(Exception):
    """Raised by any `TableService` public method for an API-shaped failure.

    `plugin_api.py` maps this straight to an HTTP response: `status_code` (409/422),
    `code` + `message` become the JSON error body, `extra` is merged in (e.g. `legal`
    on a 422 `illegal`).
    """

    def __init__(self, code: str, message: str, *, status_code: int = 409, extra: Optional[dict] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.extra = extra or {}


def _sanitize_name(raw: Any) -> str:
    name = _NAME_SANITIZE_RE.sub("", str(raw or "").strip())
    name = name[:_MAX_NAME_LEN].strip()
    return name or "Agent"


def _sanitize_avatar(raw: Any) -> str:
    return raw if isinstance(raw, str) and raw in _AVATAR_ALLOWLIST else _DEFAULT_AVATAR


def _sanitize_personality(raw: Any) -> str:
    return raw if raw in _PERSONALITIES else "balanced"


def _empty_tokens() -> dict[str, int]:
    return {"input": 0, "output": 0, "total": 0}


def _empty_seat_meta(seat: int) -> dict[str, Any]:
    if seat == 0:
        return {
            "kind": "human", "name": _HUMAN_NAME, "avatar": _HUMAN_AVATAR, "personality": None,
            "model_id": None, "model_label": None,
        }
    return {
        "kind": "hermes", "name": f"Agent {seat}", "avatar": _DEFAULT_AVATAR, "personality": "balanced",
        "profile_id": None, "model_id": "default", "model_label": None,
        "agent_state": "idle", "agent_since": None, "agent_last_error": None,
        "tokens": _empty_tokens(), "decisions": 0, "fallbacks": 0, "consec_provider_errors": 0,
        "talk": None, "talk_at": None,
    }


class TableService:
    """One table's whole backend lifecycle. See module docstring for the concurrency model."""

    #: Registry key stashed on the (always-the-same-object) `threading` module so the singleton
    #: guard survives `service.py` being re-imported under a fresh module object on hot-reload.
    _REGISTRY_ATTR = "_agent_hold_em_service_registry_v1"

    def __init__(
        self,
        *,
        seat_runner_factory: Optional[Callable[[dict, str, int], Any]] = None,
        broadcaster: Optional[Callable[[str, dict], None]] = None,
        time_func: Callable[[], float] = time.time,
        executor: Optional[Any] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._time = time_func
        self._seat_runner_factory = seat_runner_factory
        self._broadcaster = broadcaster

        if executor is None:
            from concurrent.futures import ThreadPoolExecutor

            executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ahe-seat")
        self._executor = executor

        self.table_id: str = uuid.uuid4().hex
        self.status: str = "setup"
        self.pause_reason: Optional[str] = None
        self.table: Optional[Table] = None
        self.settings: dict[str, Any] = {"decision_timeout_s": 20.0, "next_hand_delay_s": 4.0, "chatter": True}
        self.turn_id: Optional[str] = None
        self.turn_started_at: Optional[float] = None
        self.next_hand_at: Optional[float] = None

        self._seats_meta: dict[int, dict[str, Any]] = {s: _empty_seat_meta(s) for s in range(4)}
        self._runners: dict[int, Any] = {}
        self._recent_actions: "OrderedDict[str, dict]" = OrderedDict()
        self._chat: list[dict[str, Any]] = []
        self._last_attention_key: Optional[str] = None
        self._service_version = 0

        self._in_flight: Optional[dict[str, Any]] = None
        self._next_hand_timer: Optional[threading.Timer] = None

        self._generation = self._register_self()
        self._load()

        with self._lock:
            self._maybe_schedule()

    # -- singleton registry ------------------------------------------------

    def _register_self(self) -> int:
        registry = getattr(threading, self._REGISTRY_ATTR, None)
        if registry is None:
            registry = {"next_generation": 0, "instance": None}
            setattr(threading, self._REGISTRY_ATTR, registry)
        gen = registry["next_generation"] + 1
        registry["next_generation"] = gen
        old = registry.get("instance")
        registry["instance"] = self
        if old is not None and old is not self:
            try:
                old._retire()
            except Exception:
                logger.exception("agent-hold-em: error retiring previous service instance")
        return gen

    def _retire(self) -> None:
        with self._lock:
            self._generation = -1  # every captured-gen comparison in timers/callbacks now fails
            self._cancel_next_hand_timer()
            if self._in_flight is not None:
                try:
                    self._in_flight["cancel_event"].set()
                except Exception:
                    pass
            for runner in self._runners.values():
                try:
                    runner.close()
                except Exception:
                    logger.debug("agent-hold-em: error closing retired runner", exc_info=True)

    @staticmethod
    def is_current(instance: "TableService") -> bool:
        registry = getattr(threading, TableService._REGISTRY_ATTR, None)
        return bool(registry and registry.get("instance") is instance)

    # -- persistence ---------------------------------------------------

    def _load(self) -> None:
        data = store.load()
        if not data:
            return
        try:
            self.table_id = data.get("table_id") or self.table_id
            self.status = data.get("status", "setup")
            self.settings = data.get("settings") or self.settings
            meta = data.get("seats_meta") or {}
            self._seats_meta = {int(k): v for k, v in meta.items()} if meta else self._seats_meta
            recent = data.get("recent_actions") or []
            self._recent_actions = OrderedDict((k, v) for k, v in recent)
            self._service_version = int(data.get("version", 0))
            self._chat = (data.get("chat") or [])[-_MAX_CHAT:]
            table_dict = data.get("table")
            if table_dict:
                self.table = Table.from_dict(table_dict)
        except Exception:
            logger.exception("agent-hold-em: failed to restore persisted state; starting fresh")
            self.table = None
            self.status = "setup"
            return

        if self.table is None:
            self.status = "setup"
            return

        # Restart safety (ARCHITECTURE.md §5): a table persisted mid-play never auto-resumes
        # spending tokens; any in-flight decision is implicitly dropped (we never persist one).
        if self.status == "running":
            self.status = "paused"
            self.pause_reason = "restored"
            self._add_chat("system", "Table restored. Resume when you're ready; agents are paused.", level="attention")
        if self.status in ("running", "paused") and not self.table.table_over:
            self._rebuild_runners()

    def _persist(self) -> None:
        try:
            store.save({
                "table_id": self.table_id,
                "status": self.status,
                "settings": self.settings,
                "seats_meta": {str(k): v for k, v in self._seats_meta.items()},
                "recent_actions": list(self._recent_actions.items())[-_MAX_RECENT_ACTIONS:],
                "chat": self._chat[-_MAX_CHAT:],
                "table": self.table.to_dict() if self.table else None,
                "version": self._service_version,
            })
        except Exception:
            logger.exception("agent-hold-em: persist failed (continuing in-memory)")

    # -- runner construction ---------------------------------------------------

    def _rebuild_runners(self) -> None:
        for seat in (1, 2, 3):
            cfg = self._seats_meta.get(seat, _empty_seat_meta(seat))
            self._runners[seat] = self._make_runner(seat, cfg)

    def _make_runner(self, seat: int, cfg: dict[str, Any], *, table_id: Optional[str] = None) -> Any:
        runner_table_id = table_id or self.table_id
        if self._seat_runner_factory is not None:
            return self._seat_runner_factory(cfg, runner_table_id, seat)
        if cfg.get("kind") == "test_bot":
            return FakeSeatRunner(mode="test_bot")
        sc = SeatAgentConfig(
            name=cfg.get("name", f"Agent {seat}"), avatar=cfg.get("avatar", _DEFAULT_AVATAR),
            personality=cfg.get("personality", "balanced"), model_choice=cfg.get("model_id") or "default",
            profile_id=cfg.get("profile_id"),
        )
        return HermesSeatRunner(sc, table_id=runner_table_id, seat=seat, cwd=str(store.data_dir()))

    def _model_label(self, model_id: str, profile: Optional[dict[str, Any]] = None) -> str:
        if not model_id or model_id == "default":
            if profile and profile.get("model"):
                return f"{profile.get('provider') or profile['id']} — {profile['model']}"
            return "Your default model"
        provider, model = models_mod.resolve(model_id)
        return f"{provider} — {model}" if provider and model else "Your default model"

    # -- public API: setup / lifecycle ---------------------------------------------------

    def health(self) -> dict[str, Any]:
        return {"ok": True, "version": "1.0.0", "engine": "native", "hermes": {"pid": os.getpid()}}

    def profiles(self) -> dict[str, Any]:
        return {"profiles": profiles_mod.list_profile_rows()}

    def models(self, profile_name: Optional[str] = None) -> dict[str, Any]:
        if profile_name:
            from hermes_cli.profiles import list_profile_names

            if profile_name not in list_profile_names():
                raise ServiceError("unknown_profile", "Choose a valid Hermes profile.", status_code=422)
        options, default_id = models_mod.list_options(profile_name=profile_name)
        return {
            "options": [{"id": o.id, "label": o.label, "provider": o.provider, "model": o.model} for o in options],
            "default_id": default_id,
        }

    def configure(self, opponents: list[dict[str, Any]], decision_timeout_s: Optional[float] = None) -> dict[str, Any]:
        with self._lock:
            if self.status not in ("setup", "finished"):
                raise ServiceError("already_running", "a table already exists; reset first", status_code=409)
            if not isinstance(opponents, list) or len(opponents) != 3:
                raise ServiceError("invalid_opponents", "exactly 3 opponents are required", status_code=422)

            dev_mode = os.environ.get(_DEV_ENV_VAR) == "1"
            names = [_HUMAN_NAME]
            seats_meta: dict[int, dict[str, Any]] = {0: _empty_seat_meta(0)}
            profile_rows = {row["id"]: row for row in profiles_mod.list_profile_rows()}
            selected_profiles: set[str] = set()
            for i, opp in enumerate(opponents, start=1):
                if not isinstance(opp, dict):
                    raise ServiceError("invalid_opponents", f"opponent {i} must be an object", status_code=422)
                kind = opp.get("kind") or "hermes"
                if kind not in ("hermes", "test_bot"):
                    raise ServiceError("invalid_kind", f"unknown seat kind {kind!r}", status_code=422)
                if kind == "test_bot" and not dev_mode:
                    raise ServiceError(
                        "test_bot_forbidden", "test_bot seats require AGENT_HOLD_EM_DEV=1", status_code=422,
                    )
                profile_id = str(opp.get("profile_id") or "").strip() or None
                profile = profile_rows.get(profile_id) if profile_id else None
                if profile_id and profile is None:
                    raise ServiceError("unknown_profile", f"opponent {i} has an unknown Hermes profile", status_code=422)
                if profile_id and profile_id in selected_profiles:
                    raise ServiceError("duplicate_profile", "Choose a different Hermes profile for each opponent.", status_code=422)
                if profile_id:
                    selected_profiles.add(profile_id)
                name = _sanitize_name(profile["name"] if profile else opp.get("name") or f"Agent {i}")
                model_id = str(opp.get("model_id") or "default")
                meta = _empty_seat_meta(i)
                meta.update({
                    "kind": kind, "name": name,
                    "avatar": profile["avatar"] if profile else _sanitize_avatar(opp.get("avatar")),
                    "personality": _sanitize_personality(opp.get("personality")),
                    "profile_id": profile_id,
                    "model_id": model_id, "model_label": self._model_label(model_id, profile) if kind == "hermes" else "Test Bot",
                })
                seats_meta[i] = meta
                names.append(name)

            new_table_id = uuid.uuid4().hex
            new_settings = {
                "decision_timeout_s": float(decision_timeout_s or 20.0),
                "next_hand_delay_s": 4.0, "chatter": True,
            }
            new_table = Table.new(names=names)
            new_table.start_hand()
            new_runners = {}
            try:
                for seat in (1, 2, 3):
                    runner = self._make_runner(seat, seats_meta[seat], table_id=new_table_id)
                    # Eager agent construction validates the seat's provider at setup time so a
                    # broken model connection surfaces as a 422 here rather than a string of
                    # fallback decisions later. Loading a persisted table (`_rebuild_runners`)
                    # does NOT do this — a restore must succeed even when the provider isn't
                    # currently resolvable; the runner builds lazily on first use instead.
                    configure = getattr(runner, "configure_table_runner", None)
                    if callable(configure):
                        configure()
                    new_runners[seat] = runner
            except Exception:
                for runner in new_runners.values():
                    try:
                        runner.close()
                    except Exception:
                        logger.debug("agent-hold-em: error closing failed-setup runner", exc_info=True)
                logger.exception("agent-hold-em: could not initialize seat agents")
                raise ServiceError(
                    "model_unavailable", "Could not initialize an opponent model. Choose another model or check its provider connection.",
                    status_code=422,
                ) from None
            for runner in self._runners.values():
                try:
                    runner.close()
                except Exception:
                    logger.debug("agent-hold-em: error closing previous-table runner", exc_info=True)
            self.table_id = new_table_id
            self.settings = new_settings
            self._seats_meta = seats_meta
            self._recent_actions = OrderedDict()
            self._chat = []
            self._last_attention_key = None
            self.table = new_table
            self._runners = new_runners
            self.status = "running"
            self.pause_reason = None
            self.next_hand_at = None
            self.turn_id = None
            self._service_version += 1
            self._add_chat("system", "Table is live. Your turn and agent connection issues will appear here.")
            self._after_mutation()
            return self._human_view()

    def pause(self) -> dict[str, Any]:
        with self._lock:
            if self.status == "running":
                self.status = "paused"
                self.pause_reason = "manual"
                self._cancel_in_flight()
                self._cancel_next_hand_timer()
                self._service_version += 1
                self._add_chat("system", "Table paused. Resume to continue.", level="attention")
                self._persist()
                self._broadcast()
            return self._human_view()

    def resume(self) -> dict[str, Any]:
        with self._lock:
            if self.status == "paused":
                self.status = "running"
                self.pause_reason = None
                self._service_version += 1
                self._add_chat("system", "Table resumed.")
                self._after_mutation()
            return self._human_view()

    def next_hand(self) -> dict[str, Any]:
        with self._lock:
            if self.status == "running" and self.next_hand_at is not None:
                self._cancel_next_hand_timer()
                self._start_next_hand()
            return self._human_view()

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self._cancel_in_flight()
            self._cancel_next_hand_timer()
            for runner in self._runners.values():
                try:
                    runner.close()
                except Exception:
                    logger.debug("agent-hold-em: error closing runner on reset", exc_info=True)
            self._runners = {}
            self.table = None
            self.table_id = uuid.uuid4().hex
            self.status = "setup"
            self.pause_reason = None
            self.next_hand_at = None
            self.turn_id = None
            self.turn_started_at = None
            self._seats_meta = {s: _empty_seat_meta(s) for s in range(4)}
            self._recent_actions = OrderedDict()
            self._chat = []
            self._last_attention_key = None
            self._service_version += 1
            self._persist()
            self._broadcast()
            return self._human_view()

    def close(self) -> None:
        """Best-effort full shutdown (process exit / test teardown), not part of the REST API."""
        with self._lock:
            self._cancel_in_flight()
            self._cancel_next_hand_timer()
            for runner in self._runners.values():
                try:
                    runner.close()
                except Exception:
                    pass

    def history(self, limit: int = 20) -> dict[str, Any]:
        with self._lock:
            if not self.table:
                return {"hands": []}
            hands = build_public_history(self.table)
            limit = max(1, min(200, int(limit or 20)))
            return {"hands": hands[-limit:]}

    def human_view(self) -> dict[str, Any]:
        with self._lock:
            return self._human_view()

    def send_chat(self, text: str) -> dict[str, Any]:
        with self._lock:
            if self.table is None or self.status not in ("running", "paused"):
                raise ServiceError("no_table", "Start a table before chatting.", status_code=409)
            clean = re.sub(r"\s+", " ", _CHAT_CONTROL_RE.sub(" ", text)).strip()
            if not clean or len(clean) > _MAX_CHAT_TEXT:
                raise ServiceError("invalid_chat", "Message must be 1–160 characters.", status_code=422)
            self._add_chat("human", clean, seat=0)
            # Chat is NOT game state: bumping `_service_version` here would invalidate the
            # version/turn token the UI is holding for an in-flight human action, so a
            # message typed while your own turn was showing could make the very next
            # `/action` fail with 409 `stale`. Stale-write protection is unaffected: `act()`
            # still requires a current `turn_id`, and every real mutation (actions, agent
            # decisions, pause/resume, hands) keeps bumping the version. Broadcast so the
            # desktop client picks up the new chat line.
            self._persist()
            self._broadcast()
            return self._human_view()

    def _add_chat(self, kind: str, text: str, *, seat: Optional[int] = None, level: str = "info") -> None:
        self._chat.append({
            "id": uuid.uuid4().hex, "kind": kind, "seat": seat, "text": text,
            "level": level, "at": self._time(), "hand_no": self.table.hand_no if self.table else 0,
        })
        del self._chat[:-_MAX_CHAT]

    def _notice_human_turn(self) -> None:
        if self.status != "running" or self.table is None or not self.table.hand_in_progress or self.table.to_act() != 0:
            return
        key = f"{self.table.hand_no}:{self.table.version}"
        if key != self._last_attention_key:
            self._last_attention_key = key
            self._add_chat("system", "Your turn. Choose an action below the table.", level="attention")

    # -- public API: human actions ---------------------------------------------------

    def act(
        self, *, turn_id: str, expected_version: int, client_action_id: str, kind: str, to: Optional[int] = None,
    ) -> dict[str, Any]:
        with self._lock:
            cached = self._recent_actions.get(client_action_id)
            if cached is not None:
                view = dict(cached)
                view["duplicate"] = True
                return view

            if self.status == "paused":
                raise ServiceError("paused", "table is paused", status_code=409)
            if self.status != "running" or self.table is None or not self.table.hand_in_progress:
                raise ServiceError("not_your_turn", "no hand is in progress", status_code=409)
            if self.table.to_act() != 0:
                raise ServiceError("not_your_turn", "it is not your turn", status_code=409)
            if turn_id != self.turn_id or expected_version != self._service_version:
                raise ServiceError("stale", "turn_id/version no longer current", status_code=409)

            try:
                action = Action(kind=kind, to=to)
                self.table.apply(0, action)
            except IllegalAction as e:
                legal = self.table.legal()
                raise ServiceError(
                    "illegal", e.message, status_code=422, extra={"legal": legal.to_dict() if legal else None},
                ) from e

            self._service_version += 1
            self._after_mutation()
            view = self._human_view()
            self._record_action(client_action_id, view)
            return view

    def _record_action(self, client_action_id: str, view: dict[str, Any]) -> None:
        self._recent_actions[client_action_id] = view
        self._recent_actions.pop("__marker__", None)
        while len(self._recent_actions) > _MAX_RECENT_ACTIONS:
            self._recent_actions.popitem(last=False)

    # -- turn scheduling ---------------------------------------------------

    def _maybe_schedule(self) -> None:
        if self.status != "running" or self.table is None:
            return
        if not self.table.hand_in_progress:
            return
        if self._in_flight is not None:
            return
        to_act = self.table.to_act()
        if to_act is None or to_act == 0:
            return
        self._submit_agent_turn(to_act)

    def _submit_agent_turn(self, seat: int) -> None:
        assert self.table is not None
        turn_id = uuid.uuid4().hex
        now = self._time()
        deadline_s = float(self.settings.get("decision_timeout_s", 20.0))
        self.turn_id = turn_id
        self.turn_started_at = now

        meta = self._seats_meta.setdefault(seat, _empty_seat_meta(seat))
        meta["agent_state"] = "thinking"
        meta["agent_since"] = now

        gen = self._generation
        req = DecisionRequest(
            table_id=self.table_id, hand_no=self.table.hand_no, seat=seat, turn_id=turn_id,
            state_version=self.table.version, observation=self._agent_observation(seat), deadline_s=deadline_s,
        )
        cancel_event = threading.Event()
        runner = self._runners.get(seat)
        self._in_flight = {"seat": seat, "turn_id": turn_id, "cancel_event": cancel_event, "gen": gen, "req": req}

        timer = threading.Timer(deadline_s + _DEADLINE_SAFETY_MARGIN_S, self._on_deadline_safety_net, args=(gen, turn_id))
        timer.daemon = True
        self._in_flight["safety_timer"] = timer
        timer.start()

        if runner is None:
            # Should not happen in normal operation; treat as an immediate provider error.
            self._on_decision(gen, req, _synthetic_result(req, "provider_error", "no runner for seat"))
            return

        self._executor.submit(self._run_decision, runner, req, cancel_event, gen)

    def _run_decision(self, runner: Any, req: DecisionRequest, cancel_event: threading.Event, gen: int) -> None:
        result = runner.decide(req, cancel_event)
        with self._lock:
            self._on_decision(gen, req, result)

    def _on_deadline_safety_net(self, gen: int, turn_id: str) -> None:
        with self._lock:
            if gen != self._generation:
                return
            if self._in_flight is None or self._in_flight.get("turn_id") != turn_id:
                return
            seat = self._in_flight["seat"]
            req = self._in_flight["req"]
            self._in_flight["cancel_event"].set()
            runner = self._runners.get(seat)
            if runner is not None:
                try:
                    runner.interrupt()
                except Exception:
                    logger.debug("agent-hold-em: interrupt() raised on safety net", exc_info=True)
            self._on_decision(gen, req, _synthetic_result(req, "timeout", "deadline safety net"))

    def _on_decision(self, gen: int, req: DecisionRequest, result: Any) -> None:
        """Completion path: re-validate binding, apply-or-fallback, never mutate on a stale
        binding (ARCHITECTURE.md §5). Always called with `self._lock` held."""
        if gen != self._generation:
            logger.info("stale_decision seat=%s reason=generation", req.seat)
            return
        if self.status != "running" or self.table is None:
            logger.info("stale_decision seat=%s reason=not_running", req.seat)
            return
        if self._in_flight is None or self._in_flight.get("turn_id") != req.turn_id:
            logger.info("stale_decision seat=%s reason=turn_id_mismatch", req.seat)
            return
        if self.table.hand_no != req.hand_no or self.table.version != req.state_version:
            logger.info("stale_decision seat=%s reason=version_mismatch", req.seat)
            return

        safety_timer = self._in_flight.get("safety_timer")
        if safety_timer is not None:
            safety_timer.cancel()
        self._in_flight = None

        seat = req.seat
        meta = self._seats_meta.setdefault(seat, _empty_seat_meta(seat))

        usage = getattr(result, "usage", None) or {}
        tokens = meta.setdefault("tokens", _empty_tokens())
        tokens["input"] += int(usage.get("input_tokens", 0) or 0)
        tokens["output"] += int(usage.get("output_tokens", 0) or 0)
        tokens["total"] += int(usage.get("total_tokens", 0) or 0)

        applied_ok = False
        if result.status in ("ok", "retry_ok") and result.action:
            try:
                action = Action(kind=result.action["kind"], to=result.action.get("to"))
                self.table.apply(seat, action)
                applied_ok = True
            except IllegalAction:
                pass  # falls through to fallback below

        if applied_ok:
            if self.settings.get("chatter", True):
                talk = sanitize_talk(getattr(result, "talk", None))
                if not talk:
                    lines = _QUI.get(meta.get("personality"), _QUI["balanced"])
                    talk = lines[(self.table.hand_no + seat + int(meta.get("decisions", 0))) % len(lines)]
                meta["talk"] = talk
                meta["talk_at"] = self._time()
                self._add_chat("agent", talk, seat=seat)
            meta["decisions"] = int(meta.get("decisions", 0)) + 1
            meta["consec_provider_errors"] = 0
            meta["agent_state"] = "idle"
            meta["agent_last_error"] = None
        else:
            reason = result.status if result.status in ("timeout", "invalid", "provider_error", "cancelled") else "invalid"
            self._apply_fallback(seat, reason)
            meta["fallbacks"] = int(meta.get("fallbacks", 0)) + 1
            if reason == "provider_error":
                meta["consec_provider_errors"] = int(meta.get("consec_provider_errors", 0)) + 1
                meta["agent_last_error"] = getattr(result, "error", None)
                meta["agent_state"] = "disconnected" if meta["consec_provider_errors"] >= 2 else "fallback"
            else:
                meta["consec_provider_errors"] = 0
                meta["agent_state"] = "fallback"
            name = meta.get("name", f"Agent {seat}")
            detail = "Model connection failed" if reason == "provider_error" else "Decision timed out" if reason == "timeout" else "Invalid agent response"
            self._add_chat("system", f"{name}: {detail}. A safe check or fold was played. Check the agent's model connection if this repeats.", level="attention")

        self._service_version += 1
        self._after_mutation()

    def _apply_fallback(self, seat: int, reason: str) -> None:
        assert self.table is not None
        legal = self.table.legal()
        if legal is not None and legal.seat == seat and legal.can_check:
            action = Action(kind="check", fallback=True)
        else:
            action = Action(kind="fold", fallback=True)
        try:
            self.table.apply(seat, action)
        except IllegalAction:
            logger.error("agent-hold-em: fallback action itself was illegal (seat=%s reason=%s)", seat, reason)

    def _cancel_in_flight(self) -> None:
        if self._in_flight is not None:
            try:
                self._in_flight["cancel_event"].set()
            except Exception:
                pass
            timer = self._in_flight.get("safety_timer")
            if timer is not None:
                timer.cancel()
            seat = self._in_flight.get("seat")
            runner = self._runners.get(seat)
            if runner is not None:
                try:
                    runner.interrupt()
                except Exception:
                    pass
            self._in_flight = None

    # -- hand-end scheduling ---------------------------------------------------

    def _after_mutation(self) -> None:
        self._maybe_end_hand_or_table()
        self._notice_human_turn()
        self._persist()
        self._broadcast()
        self._maybe_schedule()

    def _maybe_end_hand_or_table(self) -> None:
        if self.table is None:
            return
        if self.table.table_over:
            if self.status != "finished":
                self._add_chat("system", "Table finished. Start a new table to play again.", level="attention")
            self.status = "finished"
            self._cancel_next_hand_timer()
            return
        if self.status == "running" and not self.table.hand_in_progress and self.next_hand_at is None:
            delay = float(self.settings.get("next_hand_delay_s", 4.0))
            self.next_hand_at = self._time() + delay
            self._start_next_hand_timer(delay)

    def _start_next_hand_timer(self, delay: float) -> None:
        self._cancel_next_hand_timer()
        gen = self._generation
        timer = threading.Timer(max(0.0, delay), self._on_next_hand_timer, args=(gen,))
        timer.daemon = True
        self._next_hand_timer = timer
        timer.start()

    def _cancel_next_hand_timer(self) -> None:
        if self._next_hand_timer is not None:
            self._next_hand_timer.cancel()
            self._next_hand_timer = None

    def _on_next_hand_timer(self, gen: int) -> None:
        with self._lock:
            if gen != self._generation or self.status != "running" or self.next_hand_at is None:
                return
            self._start_next_hand()

    def _start_next_hand(self) -> None:
        assert self.table is not None
        self.next_hand_at = None
        self.table.start_hand()
        for seat, runner in self._runners.items():
            try:
                runner.reset_hand(self.table.hand_no)
            except Exception:
                logger.debug("agent-hold-em: reset_hand failed for seat %s", seat, exc_info=True)
        self._service_version += 1
        self._after_mutation()

    # -- events ---------------------------------------------------

    def _broadcast(self) -> None:
        payload = {"version": self._service_version, "status": self.status}
        try:
            if self._broadcaster is not None:
                self._broadcaster("table.changed", payload)
            else:
                from hermes_cli.plugin_events import broadcast_plugin_event

                broadcast_plugin_event("agent-hold-em", "table.changed", payload)
        except Exception:
            logger.debug("agent-hold-em: broadcast failed (no desktop client? fine)", exc_info=True)

    # -- views / observations ---------------------------------------------------

    def _agent_observation(self, seat: int) -> dict[str, Any]:
        assert self.table is not None
        obs = build_view(self.table, seat)
        obs["schema"] = 1
        obs["table_id"] = self.table_id
        obs["seat"] = seat
        obs["public_chat"] = [
            {"speaker": "You" if msg["kind"] == "human" else self._seats_meta.get(msg["seat"], {}).get("name", "Agent"),
             "text": msg["text"]}
            for msg in self._chat[-12:] if msg["kind"] in ("human", "agent")
        ][-6:]
        return obs

    def _human_view(self) -> dict[str, Any]:
        if self.table is None:
            return {
                "schema": 1, "table_id": self.table_id, "version": self._service_version,
                "status": self.status, "pause_reason": self.pause_reason, "hand_no": 0, "button": None,
                "blinds": None, "sb_seat": None, "bb_seat": None,
                "street": None, "board": [], "pots": [], "total_pot": 0,
                "to_act": None, "turn_id": None, "turn_started_at": None, "turn_deadline_at": None,
                "next_hand_at": None, "seats": self._seat_stubs(), "legal": None, "log": [],
                "last_hand": None, "settings": self.settings, "chat": self._chat[-_MAX_CHAT:],
            }

        base = build_view(self.table, 0)
        running = self.status == "running"
        to_act = base["to_act"] if running else None
        legal = base["legal"] if (running and to_act == 0) else None
        deadline_s = float(self.settings.get("decision_timeout_s", 20.0))
        turn_deadline_at = (
            self.turn_started_at + deadline_s if (running and to_act not in (None, 0) and self.turn_started_at) else None
        )

        now = self._time()
        seats_out = []
        for s in base["seats"]:
            meta = self._seats_meta.get(s["seat"], _empty_seat_meta(s["seat"]))
            kind = meta.get("kind", "human" if s["seat"] == 0 else "hermes")
            agent = None
            if kind != "human":
                agent = {
                    "state": meta.get("agent_state", "idle"), "since": meta.get("agent_since"),
                    "last_error": meta.get("agent_last_error"), "tokens": meta.get("tokens", _empty_tokens()),
                    "decisions": meta.get("decisions", 0), "fallbacks": meta.get("fallbacks", 0),
                }
            talk = None
            talk_at = meta.get("talk_at")
            if meta.get("talk") and talk_at is not None and (now - talk_at) < _TALK_TTL_S:
                talk = meta["talk"]
            seats_out.append({
                **s, "kind": kind, "avatar": meta.get("avatar"), "profile_id": meta.get("profile_id"),
                "personality": meta.get("personality"),
                "model_label": meta.get("model_label"), "agent": agent, "talk": talk,
            })

        return {
            "schema": 1, "table_id": self.table_id, "version": self._service_version, "status": self.status,
            "pause_reason": self.pause_reason, "hand_no": base["hand_no"], "button": base["button"],
            "blinds": base["blinds"], "sb_seat": base["sb_seat"], "bb_seat": base["bb_seat"],
            "street": base["street"], "board": base["board"], "pots": base["pots"],
            "total_pot": base["total_pot"], "to_act": to_act,
            "turn_id": self.turn_id if to_act is not None else None,
            "turn_started_at": self.turn_started_at if to_act is not None else None,
            "turn_deadline_at": turn_deadline_at, "next_hand_at": self.next_hand_at,
            "seats": seats_out, "legal": legal, "log": base["log"], "last_hand": base["last_hand"],
            "settings": self.settings, "chat": self._chat[-_MAX_CHAT:],
        }

    def _seat_stubs(self) -> list[dict[str, Any]]:
        out = []
        for seat in range(4):
            meta = self._seats_meta.get(seat, _empty_seat_meta(seat))
            kind = meta.get("kind", "human" if seat == 0 else "hermes")
            agent = None if kind == "human" else {
                "state": meta.get("agent_state", "idle"), "since": meta.get("agent_since"),
                "last_error": meta.get("agent_last_error"), "tokens": meta.get("tokens", _empty_tokens()),
                "decisions": meta.get("decisions", 0), "fallbacks": meta.get("fallbacks", 0),
            }
            out.append({
                "seat": seat, "kind": kind, "name": meta.get("name"), "avatar": meta.get("avatar"),
                "profile_id": meta.get("profile_id"),
                "personality": meta.get("personality"), "model_label": meta.get("model_label"),
                "stack": 1000, "committed": 0, "total_in_pot": 0, "state": "active", "hole": None,
                "hand_label": None, "agent": agent, "last_action": None, "talk": None, "stats": None,
            })
        return out


def _synthetic_result(req: DecisionRequest, status: str, error: str) -> Any:
    from .controller.types import DecisionResult, empty_usage

    return DecisionResult(None, None, status, error, empty_usage(), 0, DecisionResult.binding_of(req))


def get_service() -> TableService:
    """Process-wide singleton (ARCHITECTURE.md §5). Safe across a hot re-mount of this module:
    the registry lives on the `threading` module object, which stays the same object even when
    `agent_hold_em.service` itself is re-imported fresh."""
    registry = getattr(threading, TableService._REGISTRY_ATTR, None)
    instance = registry.get("instance") if registry else None
    if instance is not None:
        return instance
    return TableService()
