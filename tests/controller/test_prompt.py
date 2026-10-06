from __future__ import annotations

import json

from conftest import LEGAL_FACING_BET, make_observation

from agent_hold_em.controller.prompt import (
    ALLOWED_OBSERVATION_KEYS, build_observation_message, build_retry_message, build_system_prompt,
)
from agent_hold_em.controller.types import DecisionRequest, SeatAgentConfig


def test_system_prompt_names_the_seat_and_personality():
    cfg = SeatAgentConfig(name="Ada", avatar="🤖", personality="aggressive", model_choice="default")
    text = build_system_prompt(cfg)
    assert "Ada" in text
    assert "aggressive" in text
    assert '"action"' in text  # output-format instructions are present


def test_observation_message_embeds_observation_verbatim_as_compact_json():
    obs = make_observation(LEGAL_FACING_BET)
    req = DecisionRequest(
        table_id="t1", hand_no=3, seat=2, turn_id="turn-9", state_version=5, observation=obs, deadline_s=20.0,
    )
    msg = build_observation_message(req)
    compact = json.dumps(obs, separators=(",", ":"), ensure_ascii=True, sort_keys=True)
    assert compact in msg
    assert " " * 2 not in compact  # sanity: it really is compact, not pretty-printed


def test_observation_only_contains_allowed_keys():
    """Guards against a future engine change silently widening what reaches an agent
    (ARCHITECTURE.md §6 leak-test intent, scoped to this module's contract)."""
    obs = make_observation(LEGAL_FACING_BET)
    assert set(obs.keys()) <= ALLOWED_OBSERVATION_KEYS


def test_retry_message_lists_legal_options_and_the_error():
    msg = build_retry_message(LEGAL_FACING_BET, "unknown action 'surrender'")
    assert "surrender" in msg
    assert "fold" in msg
    assert "call 10" in msg
    assert "raise to between 20 and 1000" in msg
