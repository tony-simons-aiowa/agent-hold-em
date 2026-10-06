"""Plain dataclasses for Component B (ARCHITECTURE.md §4).

The engine's `Legal`/`Action` value objects may not exist yet, so the controller
speaks plain dicts shaped like ARCHITECTURE.md §3's `Legal` fields
(`to_call, can_fold, can_check, can_call, call_amount, raise_kind, min_to, max_to,
all_in_to, stack, current_bet, committed`) and returns actions as plain dicts
`{"kind": ..., "to": ...}`. `service.py` is responsible for converting to/from the
engine's real `Legal`/`Action` types once they exist.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

ActionKind = Literal["fold", "check", "call", "bet", "raise", "all_in"]
Personality = Literal["cautious", "aggressive", "balanced"]
Status = Literal["ok", "retry_ok", "invalid", "timeout", "provider_error", "cancelled"]

#: `{"kind": ActionKind, "to": int | None}` — `to` is required for bet/raise/all_in,
#: None for fold/check/call (the engine computes the call amount itself).
Action = dict


@dataclass(frozen=True, slots=True)
class SeatAgentConfig:
    """One opponent seat's configuration (ARCHITECTURE.md §4)."""

    name: str
    avatar: Any
    personality: Personality
    model_choice: str  # an id from controller.models.list_options()
    profile_id: Optional[str] = None  # selected local Hermes profile, or legacy plugin owner


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    """One decision request for one seat's turn (ARCHITECTURE.md §4/§5)."""

    table_id: str
    hand_no: int
    seat: int
    turn_id: str
    state_version: int
    observation: dict[str, Any]  # engine.view(viewer=seat) shape; must include "legal"
    deadline_s: float = 20.0


def empty_usage() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """Result of one `SeatRunner.decide()` call (ARCHITECTURE.md §4).

    `action` is None when the controller could not produce a legal action; the
    service applies the check-else-fold fallback in that case. `binding` echoes
    the request's identity so the service can re-check it is still current before
    applying the action (stale/duplicate/late results never mutate state).
    """

    action: Optional[Action]
    talk: Optional[str]
    status: Status
    error: Optional[str]
    usage: dict[str, int] = field(default_factory=empty_usage)  # {input_tokens, output_tokens, total_tokens}
    latency_ms: int = 0
    binding: tuple[str, int, int, str, int] = ("", 0, 0, "", 0)  # (table_id, hand_no, seat, turn_id, state_version)

    @staticmethod
    def binding_of(req: DecisionRequest) -> tuple[str, int, int, str, int]:
        return (req.table_id, req.hand_no, req.seat, req.turn_id, req.state_version)
