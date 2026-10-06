"""End-to-end integration test: the REAL `HermesSeatRunner` (a real `AIAgent`, real
`run_conversation`) against the fake OpenAI-compatible server, for a handful of decisions.
Asserts zero tools and no canary strings in every outgoing request — this is the automated
counterpart to `scripts/probe_runtime.py` (ARCHITECTURE.md §4 deliverable 4).

Requires `scripts/env.sh` to have been sourced (HERMES_DISABLE_LAZY_INSTALLS=1, scratch
HERMES_HOME, Hermes on PYTHONPATH) — run via
`cd $HOME/mnt/agent-hold-em && . scripts/env.sh && $PY -m pytest tests/controller -q`.
"""
from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

import pytest
from _fake_openai_server import ReplyPlan
from conftest import LEGAL_CAN_CHECK, LEGAL_FACING_BET, make_observation

from agent_hold_em.controller.runner import HermesSeatRunner
from agent_hold_em.controller.types import DecisionRequest, SeatAgentConfig

pytestmark = pytest.mark.integration


def _seat_config() -> SeatAgentConfig:
    return SeatAgentConfig(name="Ada", avatar="🤖", personality="balanced", model_choice="default")


def _runner(server, table_id="itest", profile_id=None) -> HermesSeatRunner:
    """A `HermesSeatRunner` pointed at the fake server: `resolve_runtime_provider` is patched so
    the test never depends on this machine's real config.yaml / credentials."""
    fake_rp = {
        "provider": "custom", "model": "fake-model", "api_key": "sk-fake", "base_url": server.base_url,
        "api_mode": "chat_completions", "credential_pool": None, "request_overrides": {},
    }
    with patch("hermes_cli.runtime_provider.resolve_runtime_provider", return_value=fake_rp):
        runner = HermesSeatRunner(replace(_seat_config(), profile_id=profile_id), table_id=table_id, seat=1)
        # Agent construction is lazy (a restored table must build on first use, not on load);
        # build here inside the patch so these tests never touch the machine's real provider.
        runner.configure_table_runner()
        return runner


def _req(legal=LEGAL_FACING_BET, **kw) -> DecisionRequest:
    defaults = dict(table_id="itest", hand_no=1, seat=1, turn_id="turn-1", state_version=1, deadline_s=15.0)
    defaults.update(kw)
    return DecisionRequest(observation=make_observation(legal), **defaults)


def test_real_agent_zero_tools_and_no_canary(fake_openai_server):
    fake_openai_server.set_reply(ReplyPlan(content='{"action": "call", "talk": "calling"}'))
    runner = _runner(fake_openai_server)
    try:
        result = runner.decide(_req(), threading.Event())
    finally:
        runner.close()

    assert result.status == "ok"
    assert result.action == {"kind": "call", "to": None}

    req = fake_openai_server.last_request()
    assert req is not None
    assert req.get("tools") in (None, [])
    body_text = json.dumps(req)
    for canary in ("SOUL.md", "MEMORY.md", "USER.md", "AGENTS.md"):
        assert canary not in body_text


def test_selected_profile_scope_covers_build_and_agent_turn(fake_openai_server):
    fake_openai_server.set_reply(ReplyPlan(content='{"action": "call"}'))
    entered = []

    @contextmanager
    def fake_scope(profile):
        entered.append((profile, threading.current_thread().name))
        yield

    with patch("hermes_cli.web_server_profiles._config_profile_scope", fake_scope):
        runner = _runner(fake_openai_server, profile_id="writer")
        try:
            result = runner.decide(_req(), threading.Event())
        finally:
            runner.close()

    assert result.status == "ok"
    assert len(entered) >= 2
    assert all(profile == "writer" for profile, _ in entered)
    assert len({thread_name for _, thread_name in entered}) >= 2


def test_real_agent_several_decisions_stay_isolated_per_seat(fake_openai_server):
    fake_openai_server.set_reply(ReplyPlan(content='{"action": "check"}'))
    runner_a = _runner(fake_openai_server, table_id="itest-a")
    runner_b = _runner(fake_openai_server, table_id="itest-b")
    try:
        r1 = runner_a.decide(_req(legal=LEGAL_CAN_CHECK, seat=1, turn_id="a1"), threading.Event())
        r2 = runner_b.decide(_req(legal=LEGAL_CAN_CHECK, seat=2, turn_id="b1"), threading.Event())
        assert r1.status == "ok" and r2.status == "ok"
        assert runner_a._agent is not runner_b._agent
        assert runner_a._agent._session_messages is not runner_b._agent._session_messages
        assert runner_a._agent.session_id != runner_b._agent.session_id
    finally:
        runner_a.close()
        runner_b.close()


def test_real_agent_provider_error(fake_openai_server):
    fake_openai_server.set_reply(ReplyPlan(http_status=500, error_body={"error": {"message": "boom"}}))
    runner = _runner(fake_openai_server)
    try:
        result = runner.decide(_req(deadline_s=10.0), threading.Event())
    finally:
        runner.close()
    assert result.status in ("provider_error", "invalid")  # some providers surface a 500 as an empty/failed turn
    assert result.action is None


def test_real_agent_timeout(fake_openai_server):
    fake_openai_server.set_reply(ReplyPlan(content='{"action": "fold"}', delay_s=3.0))
    runner = _runner(fake_openai_server)
    try:
        result = runner.decide(_req(deadline_s=0.5), threading.Event())
    finally:
        runner.close()
    assert result.status == "timeout"
    assert result.action is None


def test_real_agent_no_persistence_to_state_db(fake_openai_server, tmp_path, monkeypatch):
    """`session_db=None` + `_persist_disabled=True` -> no session-db row is ever created."""
    fake_openai_server.set_reply(ReplyPlan(content='{"action": "fold"}'))
    runner = _runner(fake_openai_server)
    try:
        runner.decide(_req(), threading.Event())
        assert runner._agent._session_db is None
        assert getattr(runner._agent, "_session_db_created", False) is False
    finally:
        runner.close()
