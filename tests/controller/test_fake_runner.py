from __future__ import annotations

import threading

from conftest import LEGAL_CAN_CHECK, LEGAL_FACING_BET, make_observation

from agent_hold_em.controller.fake import FakeSeatRunner
from agent_hold_em.controller.types import DecisionRequest


def _req(legal=LEGAL_FACING_BET, **kw) -> DecisionRequest:
    defaults = dict(table_id="t1", hand_no=1, seat=1, turn_id="turn-1", state_version=1, deadline_s=5.0)
    defaults.update(kw)
    return DecisionRequest(observation=make_observation(legal), **defaults)


def test_scripted_success():
    runner = FakeSeatRunner(mode="scripted", script=['{"action": "call", "talk": "calling"}'])
    result = runner.decide(_req(), threading.Event())
    assert result.status == "ok"
    assert result.action == {"kind": "call", "to": None}
    assert result.talk == "calling"
    assert result.binding == ("t1", 1, 1, "turn-1", 1)


def test_scripted_retry_path():
    """First scripted reply is invalid, second (the retry) is valid -> status 'retry_ok'."""
    runner = FakeSeatRunner(mode="scripted", script=["garbage, not json", '{"action": "fold"}'])
    result = runner.decide(_req(), threading.Event())
    assert result.status == "retry_ok"
    assert result.action == {"kind": "fold", "to": None}


def test_scripted_double_invalid_gives_up():
    runner = FakeSeatRunner(mode="scripted", script=["garbage", "still garbage"])
    result = runner.decide(_req(), threading.Event())
    assert result.status == "invalid"
    assert result.action is None


def test_malformed_mode_always_invalid():
    runner = FakeSeatRunner(mode="malformed")
    result = runner.decide(_req(), threading.Event())
    assert result.status == "invalid"
    assert result.action is None


def test_error_mode_maps_to_provider_error():
    runner = FakeSeatRunner(mode="error", error=RuntimeError("boom"))
    result = runner.decide(_req(), threading.Event())
    assert result.status == "provider_error"
    assert "boom" in result.error


def test_timeout_path():
    runner = FakeSeatRunner(mode="latency", latency_s=5.0)
    result = runner.decide(_req(deadline_s=0.2), threading.Event())
    assert result.status == "timeout"
    assert result.action is None


def test_cancellation_path():
    runner = FakeSeatRunner(mode="latency", latency_s=5.0)
    cancel = threading.Event()

    def _cancel_soon():
        import time
        time.sleep(0.1)
        cancel.set()
        runner.interrupt()

    t = threading.Thread(target=_cancel_soon)
    t.start()
    result = runner.decide(_req(deadline_s=5.0), cancel)
    t.join()
    assert result.status == "cancelled"
    assert result.action is None


def test_test_bot_policy_checks_when_free():
    runner = FakeSeatRunner(mode="test_bot")
    result = runner.decide(_req(legal=LEGAL_CAN_CHECK), threading.Event())
    assert result.status == "ok"
    assert result.action == {"kind": "check", "to": None}


def test_test_bot_policy_folds_to_a_big_bet():
    big_bet = {**LEGAL_FACING_BET, "to_call": 900, "call_amount": 900}
    runner = FakeSeatRunner(mode="test_bot")
    result = runner.decide(_req(legal=big_bet), threading.Event())
    assert result.status == "ok"
    assert result.action["kind"] == "fold"


def test_per_seat_isolation_two_runners_never_share_state():
    a = FakeSeatRunner(mode="scripted", script=['{"action": "fold"}'])
    b = FakeSeatRunner(mode="scripted", script=['{"action": "check"}'])
    a.decide(_req(seat=1), threading.Event())
    b.decide(_req(legal=LEGAL_CAN_CHECK, seat=2), threading.Event())
    assert len(a.calls) == 1 and a.calls[0].seat == 1
    assert len(b.calls) == 1 and b.calls[0].seat == 2
    assert a.calls is not b.calls


def test_decide_never_raises_when_closed():
    runner = FakeSeatRunner(mode="scripted", script=['{"action": "fold"}'])
    runner.close()
    result = runner.decide(_req(), threading.Event())
    assert result.status == "provider_error"
    assert result.action is None


def test_reset_hand_clears_interrupt_flag():
    runner = FakeSeatRunner(mode="test_bot")
    runner.interrupt()
    runner.reset_hand(2)
    result = runner.decide(_req(legal=LEGAL_CAN_CHECK), threading.Event())
    assert result.status == "ok"
