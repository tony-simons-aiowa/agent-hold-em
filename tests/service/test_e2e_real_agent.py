"""End-to-end: REAL `HermesSeatRunner`s (real `AIAgent`, real `run_conversation`) driven
by the REAL `TableService` scheduler, against the fake OpenAI-compatible server — the
service-level counterpart to `tests/controller/test_integration_real_agent.py`
(ARCHITECTURE.md §5 deliverable 4: "one end-to-end test with REAL HermesSeatRunners ...
playing a few full hands through the API, asserting zero tools in every request").

Marked `integration` (excluded from the fast default `scripts/test.sh` run, included with
`--slow`/`-m integration`) since it spins up real `AIAgent`s.
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).resolve().parent.parent.parent
for _p in (str(_ROOT / "scripts"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _fake_openai_server import FakeOpenAIServer, ReplyPlan  # noqa: E402
from conftest import InlineExecutor, RecordingBroadcaster  # noqa: E402

from agent_hold_em.controller.runner import HermesSeatRunner
from agent_hold_em.controller.types import SeatAgentConfig
from agent_hold_em.service import TableService

pytestmark = pytest.mark.integration


@pytest.fixture
def fake_openai_server():
    server = FakeOpenAIServer().start()
    try:
        yield server
    finally:
        server.stop()


def _real_runner_factory(server):
    fake_rp = {
        "provider": "custom", "model": "fake-model", "api_key": "sk-fake", "base_url": server.base_url,
        "api_mode": "chat_completions", "credential_pool": None, "request_overrides": {},
    }

    def factory(cfg, table_id, seat):
        sc = SeatAgentConfig(
            name=cfg["name"], avatar=cfg["avatar"], personality=cfg["personality"], model_choice="default",
        )
        with patch("hermes_cli.runtime_provider.resolve_runtime_provider", return_value=fake_rp):
            runner = HermesSeatRunner(sc, table_id=table_id, seat=seat, cwd=None)
            # Agent construction is lazy; TableService.configure() calls
            # `configure_table_runner()` AFTER this factory returns (outside the patch), so the
            # agent must be built here where the resolver is patched.
            runner.configure_table_runner()
            return runner

    return factory


def test_service_plays_full_hands_with_real_agents_zero_tools(fake_openai_server):
    fake_openai_server.set_reply(ReplyPlan(content='{"action": "call", "talk": "calling"}'))

    svc = TableService(
        seat_runner_factory=_real_runner_factory(fake_openai_server),
        broadcaster=RecordingBroadcaster(),
        executor=InlineExecutor(),
    )
    try:
        view = svc.configure(
            [
                {"name": "Grokbot", "avatar": "🦊", "personality": "aggressive", "model_id": "default"},
                {"name": "OpenClaw", "avatar": "🐙", "personality": "cautious", "model_id": "default"},
                {"name": "Sandbox", "avatar": "🧪", "personality": "balanced", "model_id": "default"},
            ],
            decision_timeout_s=15.0,
        )
        assert view["status"] == "running"

        steps = 0
        while steps < 500 and view["hand_no"] <= 3 and view["status"] != "finished":
            steps += 1
            if view["status"] == "running" and view["next_hand_at"] is not None:
                view = svc.next_hand()
                continue
            if view["to_act"] == 0 and view["legal"]:
                legal = view["legal"]
                kind = "check" if legal["can_check"] else ("call" if legal["can_call"] else "fold")
                view = svc.act(
                    turn_id=view["turn_id"], expected_version=view["version"],
                    client_action_id=f"e2e-{steps}", kind=kind,
                )
            else:
                view = svc.human_view()

        assert view["hand_no"] >= 2

        # Every outgoing request across the whole run had zero tools and no canary strings.
        for req in fake_openai_server.requests:
            assert req.get("tools") in (None, [])
            body_text = json.dumps(req)
            for canary in ("SOUL.md", "MEMORY.md", "USER.md", "AGENTS.md"):
                assert canary not in body_text
    finally:
        svc.close()
