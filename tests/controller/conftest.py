from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent.parent
for _p in (str(_ROOT / "scripts"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _fake_openai_server import FakeOpenAIServer  # noqa: E402


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "integration: exercises a REAL AIAgent against the fake OpenAI server (slower)",
    )


@pytest.fixture
def fake_openai_server():
    server = FakeOpenAIServer().start()
    try:
        yield server
    finally:
        server.stop()


LEGAL_FACING_BET = {
    "to_call": 10, "can_fold": True, "can_check": False, "can_call": True, "call_amount": 10,
    "raise_kind": "raise", "min_to": 20, "max_to": 1000, "all_in_to": 1000, "stack": 990,
    "current_bet": 10, "committed": 0,
}

LEGAL_CAN_CHECK = {
    "to_call": 0, "can_fold": True, "can_check": True, "can_call": False, "call_amount": 0,
    "raise_kind": "bet", "min_to": 10, "max_to": 1000, "all_in_to": 1000, "stack": 1000,
    "current_bet": 0, "committed": 0,
}

LEGAL_NO_RAISE = {
    "to_call": 0, "can_fold": True, "can_check": True, "can_call": False, "call_amount": 0,
    "raise_kind": None, "min_to": None, "max_to": None, "all_in_to": 40, "stack": 40,
    "current_bet": 0, "committed": 0,
}


def make_observation(legal: dict, **extra) -> dict:
    obs = {
        "schema": 1, "hand_no": 1, "seat": 1, "street": "preflop", "board": [],
        "hole": ["Ah", "Kd"], "total_pot": 15, "legal": legal,
    }
    obs.update(extra)
    return obs
