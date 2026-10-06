"""HermesSeatRunner: one seat's isolated real `AIAgent` (ARCHITECTURE.md §4).

Every Hermes API used here is verified against the installed source; see
docs/CONTRACT.md "## Hermes agent runtime (verified)" for file:line citations and
the offline probe (`scripts/probe_runtime.py`) that exercises this exact
construction pattern against a fake OpenAI-compatible server.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from . import models as models_mod
from . import parse, prompt
from .types import DecisionRequest, DecisionResult, SeatAgentConfig, empty_usage
from ..runtime_scope import hermes_profile_scope

logger = logging.getLogger(__name__)

__all__ = ["HermesSeatRunner"]

#: Bounded private history: trimmed on `reset_hand()` so token cost doesn't grow across a whole
#: session's worth of hands.
_MAX_HISTORY_MESSAGES = 40

#: Grace period after `interrupt()` before giving up and discarding the in-flight call
#: (ARCHITECTURE.md §4: "best effort; ... return timeout and let the thread finish in the
#: background with its result discarded").
_INTERRUPT_GRACE_S = 1.5

#: How long a corrective retry must still have to be worth attempting at all.
_MIN_RETRY_BUDGET_S = 1.0


class HermesSeatRunner:
    """Owns one isolated `AIAgent` (zero tools, no memory, no context files, no persistence) plus
    that seat's bounded private message history.

    Thread-safety: `decide()` is blocking and is NOT meant to be called concurrently with itself on
    the same instance — the service already guarantees at most one in-flight decision per table.
    `interrupt()` and `close()` ARE safe to call from another thread while `decide()` is running;
    that is their entire purpose (best-effort cancellation of the in-flight model call).
    """

    def __init__(self, seat_config: SeatAgentConfig, *, table_id: str, seat: int, cwd: Optional[str] = None) -> None:
        self._seat_config = seat_config
        self._table_id = table_id
        self._seat = seat
        self._cwd = cwd
        self._closed = False
        self._accounted_tokens = {"input": 0, "output": 0}
        # Lazy agent construction: building the AIAgent resolves the seat's provider, which can
        # fail (AuthError) on a machine with no configured provider. A runner is also created on
        # every restart while loading a persisted table (`TableService._load()` ->
        # `_rebuild_runners()`), and a restore must never spend tokens or refuse to load — the
        # restored table always comes back paused. Construction is therefore deferred to the
        # first `decide()` (or an explicit `ensure_agent()`); a provider that is unavailable at
        # that point surfaces as a normal `provider_error` decision result, which the service
        # already handles with its check/fold fallback + attention chat.
        self._agent: Optional[Any] = None
        self._agent_lock = threading.Lock()

    def ensure_agent(self) -> Any:
        """Construct the seat's AIAgent on first use. Raises on provider-configuration errors,
        so explicit table setup (`TableService.configure`) keeps its eager validation via
        `configure_table_runner()`; loading a persisted table never calls this."""
        with self._agent_lock:
            if self._agent is None:
                self._agent = self._build_agent()
            return self._agent

    def configure_table_runner(self) -> None:
        """Eagerly build the agent (validates provider availability), for table setup."""
        self.ensure_agent()

    # -- construction --------------------------------------------------

    def _build_agent(self) -> Any:
        with hermes_profile_scope(self._seat_config.profile_id):
            return self._build_agent_scoped()

    def _build_agent_scoped(self) -> Any:
        from hermes_cli.config import load_config_readonly
        from hermes_cli.runtime_provider import resolve_runtime_provider
        from hermes_constants import resolve_reasoning_config
        from run_agent import AIAgent

        provider_req, model_req = models_mod.resolve(self._seat_config.model_choice)
        rp = resolve_runtime_provider(requested=provider_req, target_model=model_req)

        config = load_config_readonly()
        configured_model = config.get("model") if isinstance(config, dict) else None
        configured_default = configured_model.get("default") if isinstance(configured_model, dict) else None
        # The runtime resolver returns connection details but may omit `model`
        # when no explicit target was supplied. Use this profile's configured
        # default rather than constructing an agent with an empty model name.
        model_name = str(model_req or rp.get("model") or configured_default or "")
        reasoning_config = resolve_reasoning_config(config, model_name)

        agent_kwargs: dict[str, Any] = dict(
            model=model_name,
            provider=rp.get("provider"),
            api_key=rp.get("api_key"),
            base_url=rp.get("base_url"),
            api_mode=rp.get("api_mode"),
            credential_pool=rp.get("credential_pool"),
            request_overrides=rp.get("request_overrides"),
            reasoning_config=reasoning_config,
            enabled_toolsets=[],  # zero tools — verified: model_tools._select_tool_names([]) -> set()
            skip_memory=True,
            skip_context_files=True,
            skip_background_review=True,
            quiet_mode=True,
            load_soul_identity=False,
            session_db=None,
            max_iterations=2,
            # No recognized PLATFORM_HINTS/platform_registry entry for "agent-hold-em" -> platform_hint()
            # returns "" (verified: agent/system_prompt.py platform_hint/_default_platform_hint).
            platform="agent-hold-em",
            # Pin cwd to the plugin's own private data directory (never the real project cwd)
            # when the caller supplies one, so build_environment_hints() reveals only that path,
            # never the user's Hermes project. `cwd` is a real AIAgent __init__ kwarg (verified:
            # run_agent.py `cwd: str | None = None`).
            cwd=self._cwd,
            session_id=f"holdem-{self._table_id}-seat{self._seat}",
            ephemeral_system_prompt=prompt.build_system_prompt(self._seat_config),
            side_agent=True,
        )
        # `process://` plugin providers (e.g. claude-subscription-directsdk-experimental) resolve to an
        # `acp_command`/`acp_args` pair instead of api_key/base_url (verified: hermes_cli/runtime_provider.py
        # rungs return "command"/"args" for those; agent/curator.py::_run_llm_review forwards them the same
        # way). AIAgent handles them via the same __init__ path — no separate construction branch needed.
        acp_command = rp.get("command")
        if isinstance(acp_command, str) and acp_command:
            agent_kwargs["acp_command"] = acp_command
            agent_kwargs["acp_args"] = list(rp.get("args") or [])

        agent = AIAgent(**agent_kwargs)
        # Persistence isolation. NOT __init__ kwargs — AIAgent.__init__ has no such parameters.
        # Verified pattern (docs/CONTRACT.md): agent/background_review.py build_cache_parity_fork() and
        # agent/curator.py _run_llm_review() both set these on an already-constructed AIAgent fork.
        agent._persist_disabled = True  # no state.db row, no trajectories, no checkpoints
        agent._skip_mcp_refresh = True  # no late-connecting MCP tools between turns
        agent.suppress_status_output = True  # status/warning emits never touch real stdout
        agent._end_session_on_close = False  # close() must not finalize a session row that never existed
        agent._memory_nudge_interval = 0  # no "save this to memory" nudges
        agent._skill_nudge_interval = 0  # no "author a skill" nudges
        # Verified (docs/CONTRACT.md, probe 3): the default app-level API retry count is 3
        # (agent/agent_init.py:1421-1428, "agent.api_max_retries", default 3), and a transient/5xx
        # provider error can chew through ~3 attempts x exponential backoff ("well under 60s" per
        # agent/chat_completion_helpers.py:69) BEFORE our own decide()-level deadline/interrupt
        # even gets a chance to matter. One attempt keeps a bad decision call failing fast; our
        # own corrective-retry logic (controller/parse.py, one retry) is the seat's real retry
        # budget, not the transport's.
        agent._api_max_retries = 1
        # Verified (docs/CONTRACT.md, probe 3): post-exhaustion auto-recovery cycles
        # (agent/agent_init.py:1430-1434, "agent.auto_recovery_cycles", default 5,
        # agent/turn_recovery_autorecover.py) run an additional bounded ladder AFTER retries and
        # the fallback chain are spent on a transient outage — on a sustained outage this made a
        # single decide() call run well past any sane deadline in testing. We have our own
        # deadline/interrupt and our own corrective retry; disable this ladder entirely.
        agent._auto_recovery_cycles = 0
        return agent

    # -- decision --------------------------------------------------

    def decide(self, req: DecisionRequest, cancel_event: threading.Event) -> DecisionResult:
        """One decision call + at most one corrective retry, bounded by `req.deadline_s`. Never raises."""
        binding = DecisionResult.binding_of(req)
        start = time.monotonic()
        if self._closed:
            return DecisionResult(
                None, None, "provider_error", "seat runner is closed", empty_usage(), 0, binding,
            )

        deadline = start + max(0.0, req.deadline_s)
        try:
            self.ensure_agent()
            return self._decide_inner(req, cancel_event, deadline, start, binding)
        except Exception as e:  # pragma: no cover - decide() must never raise (ARCHITECTURE.md §4)
            logger.exception("agent-hold-em seat %s: unexpected error in decide()", self._seat)
            return DecisionResult(
                None, None, "provider_error", f"unexpected error: {e}",
                self._usage_delta(), self._elapsed_ms(start), binding,
            )

    def _decide_inner(
        self, req: DecisionRequest, cancel_event: threading.Event, deadline: float, start: float,
        binding: tuple[str, int, int, str, int],
    ) -> DecisionResult:
        legal = req.observation.get("legal") or {}

        text, status, error = self._run_one_call(prompt.build_observation_message(req), deadline, cancel_event)
        if status != "ok":
            return DecisionResult(None, None, status, error, self._usage_delta(), self._elapsed_ms(start), binding)

        result = parse.parse_decision(text, legal)
        if result.ok:
            return DecisionResult(
                result.action, result.talk, "ok", None, self._usage_delta(), self._elapsed_ms(start), binding,
            )

        remaining = deadline - time.monotonic()
        if remaining < _MIN_RETRY_BUDGET_S or cancel_event.is_set():
            return DecisionResult(
                None, result.talk, "invalid", result.error, self._usage_delta(), self._elapsed_ms(start), binding,
            )

        retry_text, status, error = self._run_one_call(
            prompt.build_retry_message(legal, result.error or "invalid reply"), deadline, cancel_event,
        )
        if status != "ok":
            return DecisionResult(None, result.talk, status, error, self._usage_delta(), self._elapsed_ms(start), binding)

        retry_result = parse.parse_decision(retry_text, legal)
        talk = retry_result.talk if retry_result.talk is not None else result.talk
        if retry_result.ok:
            return DecisionResult(
                retry_result.action, talk, "retry_ok", None, self._usage_delta(), self._elapsed_ms(start), binding,
            )
        return DecisionResult(
            None, talk, "invalid", retry_result.error, self._usage_delta(), self._elapsed_ms(start), binding,
        )

    def _elapsed_ms(self, start: float) -> int:
        return int((time.monotonic() - start) * 1000)

    def _run_one_call(
        self, user_message: str, deadline: float, cancel_event: threading.Event,
    ) -> tuple[str, str, Optional[str]]:
        """Run one `run_conversation` call bounded by `deadline`/`cancel_event`.

        Returns `(final_response_text, status, error)`, status one of "ok", "timeout", "cancelled",
        "provider_error". Never raises. No `conversation_history=` is passed: `run_conversation`
        appends to (and reads from) `self._agent._session_messages` on its own — verified pattern
        (docs/CONTRACT.md): `agent/curator.py::_run_llm_review` calls
        `review_agent.run_conversation(user_message=prompt)` the same way and then reads
        `review_agent._session_messages` back.
        """
        box: dict[str, Any] = {}

        def _work() -> None:
            try:
                with hermes_profile_scope(self._seat_config.profile_id):
                    box["result"] = self.ensure_agent().run_conversation(user_message=user_message, task_id=None)
            except Exception as e:  # pragma: no cover - provider/transport failure
                box["exc"] = e

        thread = threading.Thread(target=_work, daemon=True)
        thread.start()

        poll_s = 0.05
        while thread.is_alive():
            remaining = deadline - time.monotonic()
            if remaining <= 0 or cancel_event.is_set():
                break
            thread.join(timeout=min(poll_s, remaining))

        if thread.is_alive():
            # We are the ones ending this call (deadline exceeded or service cancellation), not the
            # provider — so regardless of whether the interrupted thread manages to unwind within
            # the grace period below, the OUTCOME is "timeout"/"cancelled", never "provider_error"
            # (verified: scripts/probe_runtime.py Probe 2 — an interrupted turn still returns a
            # normal-shaped result dict with completed=False, which would otherwise be
            # indistinguishable from a genuine provider failure).
            was_cancelled = cancel_event.is_set()
            try:
                self._agent.interrupt(hard_cancel=True, tool_reason="cancelled" if was_cancelled else "deadline exceeded")
            except Exception:
                logger.debug("agent-hold-em seat %s: interrupt() raised", self._seat, exc_info=True)
            # Best-effort only (ARCHITECTURE.md §4): give it a grace period to unwind, but either
            # way — whether it finishes inside the grace period or is left running in the
            # background (daemon thread, discarded) — WE decided to end this call, so we report
            # our own outcome rather than inspecting whatever `box` ends up holding.
            thread.join(timeout=_INTERRUPT_GRACE_S)
            return "", ("cancelled" if was_cancelled else "timeout"), (
                "cancelled by service" if was_cancelled else f"no reply within {req_deadline_desc(deadline)}"
            )

        if "exc" in box:
            return "", "provider_error", _safe_error_text(box["exc"])

        result = box.get("result")
        if not isinstance(result, dict):
            return "", "provider_error", "no response from provider"
        if result.get("failed") or result.get("completed") is False:
            return "", "provider_error", _safe_str(
                result.get("error") or result.get("failure_reason") or "provider call did not complete",
            )
        final = result.get("final_response")
        if not isinstance(final, str) or not final.strip():
            return "", "provider_error", "empty response from model"
        return final, "ok", None

    # -- lifecycle --------------------------------------------------

    def interrupt(self) -> None:
        """Best-effort cancel of an in-flight model call (call from another thread)."""
        agent = self._agent
        if agent is None:
            return  # never built: nothing in flight to cancel
        try:
            agent.interrupt(hard_cancel=True, tool_reason="cancelled")
        except Exception:
            logger.debug("agent-hold-em seat %s: interrupt() raised", self._seat, exc_info=True)

    def reset_hand(self, hand_no: int) -> None:
        """Trim this seat's private history so it doesn't grow without bound across a session's
        worth of hands. `_session_messages` is `AIAgent`'s own running conversation list (verified:
        `agent/background_review.py` reads the same attribute on a review fork the same way)."""
        del hand_no  # not needed to decide the trim; kept for the documented interface
        agent = self._agent
        if agent is None:
            return
        try:
            messages = getattr(agent, "_session_messages", None)
            if isinstance(messages, list) and len(messages) > _MAX_HISTORY_MESSAGES:
                agent._session_messages = messages[-_MAX_HISTORY_MESSAGES:]
        except Exception:
            logger.debug("agent-hold-em seat %s: reset_hand trim failed", self._seat, exc_info=True)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        agent = self._agent
        if agent is not None:
            try:
                agent.interrupt(hard_cancel=True, tool_reason="table closed")
            except Exception:
                pass
        close = getattr(agent, "close", None) if agent is not None else None
        if callable(close):
            try:
                close()
            except Exception:
                logger.debug("agent-hold-em seat %s: agent.close() raised", self._seat, exc_info=True)

    # -- usage --------------------------------------------------

    def _usage_delta(self) -> dict[str, int]:
        """Best-effort cumulative-counter delta since the last accounted point (ARCHITECTURE.md §4
        `DecisionResult.usage`). `session_input_tokens`/`session_output_tokens` are cumulative for the
        agent's whole lifetime (verified: `agent/agent_init.py` `_USAGE_STATE`, `agent/turn_usage.py`),
        so we snapshot and diff rather than read them as a per-call figure."""
        cur_in = int(getattr(self._agent, "session_input_tokens", 0) or 0) if self._agent is not None else 0
        cur_out = int(getattr(self._agent, "session_output_tokens", 0) or 0) if self._agent is not None else 0
        d_in = max(0, cur_in - self._accounted_tokens["input"])
        d_out = max(0, cur_out - self._accounted_tokens["output"])
        self._accounted_tokens["input"], self._accounted_tokens["output"] = cur_in, cur_out
        return {"input_tokens": d_in, "output_tokens": d_out, "total_tokens": d_in + d_out}


def req_deadline_desc(deadline: float) -> str:
    remaining = deadline - time.monotonic()
    return f"{max(0.0, remaining) + _INTERRUPT_GRACE_S:.1f}s"


def _safe_error_text(exc: BaseException) -> str:
    """A short, safe-to-show error string — never a raw traceback or provider body that might embed
    request contents (ARCHITECTURE.md: errors "never include tracebacks, prompts or secrets")."""
    return f"{type(exc).__name__}: {_safe_str(str(exc))}"


def _safe_str(value: Any) -> str:
    return str(value)[:400]
