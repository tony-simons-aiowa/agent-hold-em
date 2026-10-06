"""System/persona prompt and per-turn observation message (ARCHITECTURE.md §4/§6).

Kept lean on purpose: this is charged as tokens on every single decision call, for
every seat, every hand. No filler prose in the observation message — just the
JSON the model needs plus one short instruction line.
"""
from __future__ import annotations

import json
from typing import Any

from .personalities import build_persona_prompt
from .types import DecisionRequest, SeatAgentConfig

__all__ = ["build_system_prompt", "build_observation_message"]


def build_system_prompt(seat_config: SeatAgentConfig) -> str:
    """The `ephemeral_system_prompt` for one seat's `AIAgent` (persona + shared rules)."""
    return build_persona_prompt(name=seat_config.name, personality=seat_config.personality)


#: Fields ARCHITECTURE.md §6 permits into a seat's own observation. `parse.py`'s
#: `assert_observation_shape` (used by tests, not at runtime) checks against this list so a future
#: engine change can't silently leak an extra field into every agent's turn.
ALLOWED_OBSERVATION_KEYS = frozenset({
    "schema", "table_id", "hand_no", "seat", "street", "board", "hole", "pots", "total_pot",
    "blinds", "button", "positions", "seats", "history", "legal", "to_call", "stats", "public_chat",
})


def build_observation_message(req: DecisionRequest) -> str:
    """The per-turn user message: compact JSON observation + a one-line instruction.

    `req.observation` is trusted to already be the seat-scoped, privacy-filtered view
    (ARCHITECTURE.md §6) — this module does not filter it, only serializes it compactly.
    """
    compact = json.dumps(req.observation, separators=(",", ":"), ensure_ascii=True, sort_keys=True)
    return (
        "It's your turn. Observation:\n"
        f"{compact}\n"
        "Reply with ONLY the JSON action object described in your instructions."
    )


def build_retry_message(legal: dict[str, Any], error: str) -> str:
    """Corrective retry message after an invalid/unparseable first reply (ARCHITECTURE.md §4).

    Sent as a follow-up user message in the SAME session so the model sees its own bad reply
    and the correction together; kept short since it eats into the deadline.
    """
    options = _describe_legal_options(legal)
    return (
        f"Your last reply was invalid ({error}). Reply again with ONLY one JSON object: "
        f'{{"action": "fold|check|call|bet|raise|all_in", "to": <integer if bet/raise>, "talk": "<optional>"}}. '
        f"Legal options right now: {options}."
    )


def _describe_legal_options(legal: dict[str, Any]) -> str:
    parts: list[str] = []
    if legal.get("can_fold"):
        parts.append("fold")
    if legal.get("can_check"):
        parts.append("check")
    if legal.get("can_call"):
        parts.append(f"call {legal.get('call_amount')}")
    raise_kind = legal.get("raise_kind")
    if raise_kind:
        parts.append(f"{raise_kind} to between {legal.get('min_to')} and {legal.get('max_to')}")
    if legal.get("stack", 0) and legal.get("all_in_to") is not None:
        parts.append(f"all_in (to {legal.get('all_in_to')})")
    return ", ".join(parts) if parts else "check or fold only"
