"""FakeSeatRunner: scripted/latency/error/malformed stand-in for tests, plus a simple
"TEST BOT" policy for local dev without burning real model calls (ARCHITECTURE.md §4).

Same public shape as `HermesSeatRunner` (`decide`/`interrupt`/`reset_hand`/`close`) so
`service.py` and tests can use either behind one interface. Never imports Hermes.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Optional

from . import parse
from .types import DecisionRequest, DecisionResult, empty_usage

__all__ = ["FakeSeatRunner"]

Mode = str  # "scripted" | "latency" | "error" | "malformed" | "test_bot"


class FakeSeatRunner:
    """A `SeatRunner`-shaped test double.

    Modes:
      - "scripted": returns replies from `script` (a list of raw-text model replies, one per
        `decide()` call, consumed in order; a corrective retry consumes the NEXT scripted reply).
      - "latency": sleeps `latency_s` (interruptibly, via a `threading.Event.wait`) before replying
        with `script`'s next entry (or a legal "check/fold" default) — for deadline/interrupt tests.
      - "error": raises inside the simulated model call, mapped to status "provider_error".
      - "malformed": always returns a fixed non-JSON / garbage string, to drive the retry path.
      - "test_bot": a simple, clearly-labeled dev policy (ARCHITECTURE.md §4: "clearly-labelled
        dev 'TEST BOT' seats only") — check/call small bets, fold to large ones, never bluffs.
    """

    def __init__(
        self, *, mode: Mode = "test_bot", script: Optional[list[str]] = None,
        latency_s: float = 0.0, error: Optional[BaseException] = None,
        policy: Optional[Callable[[dict[str, Any]], str]] = None,
    ) -> None:
        self.mode = mode
        self._script = list(script or [])
        self._script_i = 0
        self.latency_s = latency_s
        self.error = error
        self._policy = policy or _test_bot_policy
        self._closed = False
        self._interrupted = threading.Event()
        self.calls: list[DecisionRequest] = []  # test introspection: every decide() request seen

    def _next_scripted(self) -> str:
        if self._script_i < len(self._script):
            text = self._script[self._script_i]
            self._script_i += 1
            return text
        return '{"action": "fold"}'

    def decide(self, req: DecisionRequest, cancel_event: threading.Event) -> DecisionResult:
        start = time.monotonic()
        self.calls.append(req)
        binding = DecisionResult.binding_of(req)
        if self._closed:
            return DecisionResult(None, None, "provider_error", "seat runner is closed", empty_usage(), 0, binding)

        legal = req.observation.get("legal") or {}

        if self.mode == "error":
            return DecisionResult(
                None, None, "provider_error", str(self.error or "simulated provider error"),
                empty_usage(), self._elapsed_ms(start), binding,
            )

        if self.mode == "latency":
            deadline = start + req.deadline_s
            remaining = deadline - time.monotonic()
            interrupted = self._interrupted.wait(timeout=max(0.0, min(self.latency_s, remaining)))
            if interrupted or time.monotonic() >= deadline or cancel_event.is_set():
                status = "cancelled" if (interrupted or cancel_event.is_set()) else "timeout"
                return DecisionResult(None, None, status, "simulated slow provider", empty_usage(), self._elapsed_ms(start), binding)
            text = self._next_scripted()
        elif self.mode == "malformed":
            text = "not json at all, just prose from a confused model"
        elif self.mode == "scripted":
            text = self._next_scripted()
        else:  # "test_bot"
            text = self._policy(req.observation)

        result = parse.parse_decision(text, legal)
        if result.ok:
            return DecisionResult(result.action, result.talk, "ok", None, empty_usage(), self._elapsed_ms(start), binding)

        # One corrective retry, mirroring HermesSeatRunner's contract.
        if self.mode in ("scripted", "latency"):
            retry_text = self._next_scripted()
            retry_result = parse.parse_decision(retry_text, legal)
            if retry_result.ok:
                talk = retry_result.talk if retry_result.talk is not None else result.talk
                return DecisionResult(retry_result.action, talk, "retry_ok", None, empty_usage(), self._elapsed_ms(start), binding)
            return DecisionResult(None, retry_result.talk or result.talk, "invalid", retry_result.error, empty_usage(), self._elapsed_ms(start), binding)

        return DecisionResult(None, result.talk, "invalid", result.error, empty_usage(), self._elapsed_ms(start), binding)

    def _elapsed_ms(self, start: float) -> int:
        return int((time.monotonic() - start) * 1000)

    def interrupt(self) -> None:
        self._interrupted.set()

    def reset_hand(self, hand_no: int) -> None:
        del hand_no
        self._interrupted.clear()

    def close(self) -> None:
        self._closed = True


def _test_bot_policy(observation: dict[str, Any]) -> str:
    """Deterministic dev-only "TEST BOT" policy: check when free, call small bets relative to the
    pot, fold to big ones, never raises or bluffs. Clearly not a real opponent — for local UI/dev
    only, per ARCHITECTURE.md §4."""
    import json

    legal = observation.get("legal") or {}
    to_call = int(legal.get("to_call", 0) or 0)
    if to_call == 0:
        return json.dumps({"action": "check", "talk": "Check."})
    pot = int(observation.get("total_pot", 0) or 0)
    if legal.get("can_call") and to_call <= max(20, pot // 2):
        return json.dumps({"action": "call", "talk": "I call."})
    return json.dumps({"action": "fold", "talk": "Not this time."})
