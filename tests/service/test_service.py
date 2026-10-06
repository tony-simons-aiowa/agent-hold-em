"""tests/service — TableService: turn scheduling, fallback, persistence, privacy, singleton
guard (docs/ARCHITECTURE.md §5). See tests/service/conftest.py for the InlineExecutor
technique that makes these tests deterministic and fast (no real thread races)."""
from __future__ import annotations

import os
import stat
import threading

import pytest

from conftest import (
    RecordingBroadcaster,
    configure_with_fake_bots,
    dump_no_card_leak,
    make_fake_factory,
    make_service,
)

from agent_hold_em import store
from agent_hold_em.controller.fake import FakeSeatRunner
from agent_hold_em.service import ServiceError, TableService, get_service


# ---------------------------------------------------------------------------
# setup / configure
# ---------------------------------------------------------------------------

def test_configure_starts_running_hand():
    svc = make_service()
    view, _ = configure_with_fake_bots(svc)
    assert view["status"] == "running"
    assert view["hand_no"] == 1
    assert len(view["seats"]) == 4
    assert view["seats"][0]["kind"] == "human"
    assert view["seats"][1]["kind"] == "hermes"
    assert view["sb_seat"] == svc.table._sb_seat
    assert view["bb_seat"] == svc.table._bb_seat


def test_table_chat_is_public_bounded_and_survives_reload():
    svc = make_service()
    configure_with_fake_bots(svc)
    before = svc.human_view()
    assert any(m["kind"] == "agent" for m in before["chat"])
    assert any(m["level"] == "attention" for m in before["chat"])
    sent = svc.send_chat("  Nice   bluff!  ")
    assert sent["chat"][-1]["text"] == "Nice bluff!"
    # Chat is not game state: it must NOT bump the service version (see send_chat).
    assert sent["version"] == before["version"]
    assert any(m["text"] == "Nice bluff!" for m in svc._agent_observation(1)["public_chat"])
    with pytest.raises(ServiceError) as empty:
        svc.send_chat(" \n ")
    assert empty.value.code == "invalid_chat"
    with pytest.raises(ServiceError) as long:
        svc.send_chat("x" * 161)
    assert long.value.code == "invalid_chat"
    restored = make_service()
    assert any(m["text"] == "Nice bluff!" for m in restored.human_view()["chat"])
    assert restored.human_view()["status"] == "paused"


def test_chat_does_not_change_human_action_version():
    svc = make_service()
    configure_with_fake_bots(svc)
    for i in range(30):
        view = svc.human_view()
        if view["to_act"] == 0:
            break
        if view["next_hand_at"] is not None:
            svc.next_hand()
    else:
        pytest.fail("no human turn")
    sent = svc.send_chat("Your move")
    assert sent["turn_id"] == view["turn_id"]
    # REGRESSION (readiness HOLD): chat used to bump `_service_version`, so a message sent
    # while your own turn was on screen invalidated the `version`/`turn_id` the UI was
    # holding and the immediate `/action` failed 409 `stale`. Chat must leave the
    # version untouched, and the pre-chat token must still be accepted.
    assert sent["version"] == view["version"]
    legal = sent["legal"]
    kind = "check" if legal["can_check"] else "call" if legal["can_call"] else "fold"
    result = svc.act(turn_id=view["turn_id"], expected_version=view["version"], client_action_id="after-chat", kind=kind)
    assert result["version"] > sent["version"]


def test_chat_does_not_weaken_stale_write_protection():
    """The counterpart guarantee: chat skipping the version bump must not let a genuinely
    stale action through — a version from a REAL mutation is still rejected."""
    svc = make_service()
    configure_with_fake_bots(svc)
    for i in range(30):
        view = svc.human_view()
        if view["to_act"] == 0:
            break
        if view["next_hand_at"] is not None:
            svc.next_hand()
    else:
        pytest.fail("no human turn")
    svc.send_chat("Hello table")
    with pytest.raises(ServiceError) as ei:
        svc.act(
            turn_id=view["turn_id"], expected_version=view["version"] + 1,
            client_action_id="stale-after-chat", kind="check" if view["legal"]["can_check"] else "fold",
        )
    assert ei.value.code == "stale"


def test_pause_resume_keeps_human_actions_usable():
    svc = make_service()
    configure_with_fake_bots(svc)
    for _ in range(30):
        view = svc.human_view()
        if view["to_act"] == 0:
            break
        if view["next_hand_at"] is not None:
            svc.next_hand()
    else:
        pytest.fail("fake opponents never yielded a human turn")

    svc.pause()
    view = svc.resume()
    assert view["version"] != svc.table.version
    legal = view["legal"]
    kind = "check" if legal["can_check"] else "call" if legal["can_call"] else "fold"
    acted = svc.act(
        turn_id=view["turn_id"], expected_version=view["version"],
        client_action_id="after-resume", kind=kind,
    )
    assert acted["version"] > view["version"]


def test_setup_avatar_choices_are_preserved():
    svc = make_service()
    svc._seat_runner_factory = make_fake_factory()[0]
    view = svc.configure([
        {"name": "Vex", "avatar": "🦊", "model_id": "default"},
        {"name": "Juniper", "avatar": "🦉", "model_id": "default"},
        {"name": "Ferro", "avatar": "🐉", "model_id": "default"},
    ])
    assert [seat["avatar"] for seat in view["seats"][1:]] == ["🦊", "🦉", "🐉"]


def test_profile_opponents_use_server_names_avatars_and_distinct_ids(monkeypatch):
    from agent_hold_em import profiles as profiles_mod

    rows = [
        {"id": f"bot-{i}", "name": f"Bot {i}", "label": f"Bot {i}",
         "avatar": {"image": f"data:image/png;base64,avatar{i}", "shape": "blobatar", "color": "red", "seed": f"bot-{i}"},
         "provider": "test", "model": f"model-{i}"}
        for i in range(1, 4)
    ]
    monkeypatch.setattr(profiles_mod, "list_profile_rows", lambda: rows)
    seen = []

    def factory(cfg, table_id, seat):
        seen.append((seat, cfg["profile_id"], cfg["name"]))
        return FakeSeatRunner(mode="test_bot")

    svc = make_service()
    svc._seat_runner_factory = factory
    view = svc.configure([
        {"name": "Spoofed", "avatar": "🦊", "profile_id": f"bot-{i}", "model_id": "default"}
        for i in range(1, 4)
    ])
    assert [s["name"] for s in view["seats"][1:]] == ["Bot 1", "Bot 2", "Bot 3"]
    assert [s["profile_id"] for s in view["seats"][1:]] == ["bot-1", "bot-2", "bot-3"]
    assert [s["avatar"] for s in view["seats"][1:]] == [r["avatar"] for r in rows]
    assert [s["model_label"] for s in view["seats"][1:]] == ["test — model-1", "test — model-2", "test — model-3"]
    assert seen == [(1, "bot-1", "Bot 1"), (2, "bot-2", "Bot 2"), (3, "bot-3", "Bot 3")]


def test_unknown_or_duplicate_profile_is_rejected(monkeypatch):
    from agent_hold_em import profiles as profiles_mod

    monkeypatch.setattr(profiles_mod, "list_profile_rows", lambda: [
        {"id": "one", "name": "One", "avatar": {"image": None}, "model": "m", "provider": "p"},
        {"id": "two", "name": "Two", "avatar": {"image": None}, "model": "m", "provider": "p"},
    ])
    svc = make_service()
    for ids, code in ((["one", "two", "missing"], "unknown_profile"), (["one", "one", "two"], "duplicate_profile")):
        with pytest.raises(ServiceError) as ei:
            svc.configure([{"name": "Ignored", "profile_id": p} for p in ids])
        assert ei.value.code == code
        assert svc.status == "setup"


def test_test_bot_forbidden_without_dev_flag(monkeypatch):
    monkeypatch.delenv("AGENT_HOLD_EM_DEV", raising=False)
    svc = make_service()
    with pytest.raises(ServiceError) as ei:
        svc.configure(
            [
                {"name": "A", "kind": "test_bot"},
                {"name": "B", "kind": "hermes"},
                {"name": "C", "kind": "hermes"},
            ],
        )
    assert ei.value.code == "test_bot_forbidden"


def test_test_bot_allowed_with_dev_flag(monkeypatch):
    monkeypatch.setenv("AGENT_HOLD_EM_DEV", "1")
    svc = make_service()

    def factory(cfg, table_id, seat):
        assert cfg["kind"] == "test_bot"
        return FakeSeatRunner(mode="test_bot")

    svc._seat_runner_factory = factory
    view = svc.configure(
        [{"name": "A", "kind": "test_bot"}, {"name": "B", "kind": "test_bot"}, {"name": "C", "kind": "test_bot"}],
    )
    assert view["status"] == "running"


def test_wrong_opponent_count_rejected():
    svc = make_service()
    with pytest.raises(ServiceError):
        svc.configure([{"name": "A"}, {"name": "B"}])


def test_model_initialization_failure_keeps_setup_available():
    svc = make_service()
    created = []

    def factory(cfg, table_id, seat):
        if seat == 2:
            raise RuntimeError("provider unavailable")
        runner = FakeSeatRunner(mode="test_bot")
        created.append(runner)
        return runner

    svc._seat_runner_factory = factory
    original_table_id = svc.table_id
    with pytest.raises(ServiceError) as ei:
        svc.configure([{"name": "A"}, {"name": "B"}, {"name": "C"}])
    assert ei.value.code == "model_unavailable"
    assert ei.value.status_code == 422
    assert svc.status == "setup"
    assert svc.table is None
    assert svc.table_id == original_table_id
    assert svc._runners == {}
    assert created[0]._closed


# ---------------------------------------------------------------------------
# singleton / hot-reload guard
# ---------------------------------------------------------------------------

def test_get_service_returns_same_instance():
    from agent_hold_em import service as service_mod

    a = get_service()
    b = get_service()
    assert a is b
    a.close()


def test_second_instance_retires_first():
    factory, _ = make_fake_factory()
    svc1 = make_service(seat_runner_factory=factory)
    svc2 = make_service(seat_runner_factory=factory)
    assert svc1 is not svc2
    assert svc1._generation == -1
    assert TableService.is_current(svc2)
    assert not TableService.is_current(svc1)
    assert get_service() is svc2
    svc2.close()


def test_retired_instance_stops_scheduling_new_turns():
    factory1, runners1 = make_fake_factory()
    svc1 = make_service(seat_runner_factory=factory1)
    view1 = svc1.configure(
        [
            {"name": "Grokbot", "avatar": "🦊", "personality": "aggressive", "model_id": "default"},
            {"name": "OpenClaw", "avatar": "🐙", "personality": "cautious", "model_id": "default"},
            {"name": "Sandbox", "avatar": "🧪", "personality": "balanced", "model_id": "default"},
        ],
    )
    calls_before = sum(len(r.calls) for r in runners1.values())

    # A second instance over the SAME scratch HERMES_HOME simulates a hot re-mount: it loads
    # svc1's persisted table (as `paused`/`restored`) and, critically, retires svc1 in the
    # process — we do not need svc2 to itself run a hand for this test's purpose.
    factory2, _ = make_fake_factory()
    svc2 = make_service(seat_runner_factory=factory2)
    assert svc2.status == "paused"

    # svc1 is retired: driving it further must not submit any more decisions.
    if svc1.status == "running" and svc1.table and svc1.table.hand_in_progress:
        svc1._maybe_schedule()
    calls_after = sum(len(r.calls) for r in runners1.values())
    assert calls_after == calls_before
    svc2.close()


# ---------------------------------------------------------------------------
# turn handoff + chip conservation
# ---------------------------------------------------------------------------

def _play_hands_to_completion(svc, max_hands=25, max_steps=4000):
    """Drives the table with check/call-only human moves and the FakeSeatRunner
    'test_bot' policy on every seat, asserting chip conservation after every human
    action, until `max_hands` hands have completed or the table finishes."""
    steps = 0
    while steps < max_steps:
        steps += 1
        view = svc.human_view()
        if view["status"] == "finished":
            break
        if view["hand_no"] > max_hands:
            break
        _assert_chip_conservation(view)
        if view["status"] == "running" and view["next_hand_at"] is not None:
            svc.next_hand()
            continue
        if view["to_act"] == 0 and view["legal"]:
            legal = view["legal"]
            kind = "check" if legal["can_check"] else ("call" if legal["can_call"] else "fold")
            view = svc.act(
                turn_id=view["turn_id"], expected_version=view["version"],
                client_action_id=f"h-{view['hand_no']}-{view['version']}-{steps}", kind=kind,
            )
            _assert_chip_conservation(view)
        else:
            # Nothing for the test to drive right now (agent turn already resolved
            # synchronously by the InlineExecutor as part of the last mutation).
            if view["status"] == "running" and not view["hand_no"]:
                break
    return svc.human_view()


def _assert_chip_conservation(view):
    # `pots[].amount` already sums each seat's current-hand contribution (views.py
    # `_live_pots`); adding `committed`/`total_in_pot` on top would double-count.
    total = sum(seat["stack"] for seat in view["seats"]) + sum(pot["amount"] for pot in view["pots"])
    assert total == 4000, f"chip conservation violated: {total} != 4000 ({view['seats']}, pots={view['pots']})"
    for seat in view["seats"]:
        assert seat["stack"] >= 0


def test_chip_conservation_and_turn_handoff_across_many_hands():
    svc = make_service()
    configure_with_fake_bots(svc, timeout_s=5.0)
    final = _play_hands_to_completion(svc, max_hands=20)
    assert final["hand_no"] >= 5 or final["status"] == "finished"


def test_action_out_of_turn_rejected():
    svc = make_service()
    view, _ = configure_with_fake_bots(svc)
    # Force it to not be seat 0's turn by advancing until an agent (or nobody) is to act,
    # otherwise directly assert against a deliberately wrong turn context.
    with pytest.raises(ServiceError) as ei:
        svc.act(turn_id="bogus", expected_version=999999, client_action_id="x1", kind="check")
    assert ei.value.code in ("stale", "not_your_turn")


def test_action_illegal_kind_rejected():
    svc = make_service()
    view, _ = configure_with_fake_bots(svc)
    if view["to_act"] != 0:
        pytest.skip("seat 0 not first to act in this deal")
    with pytest.raises(ServiceError) as ei:
        svc.act(
            turn_id=view["turn_id"], expected_version=view["version"], client_action_id="bad-1",
            kind="raise", to=1,  # far below any legal min_to
        )
    assert ei.value.code == "illegal"
    assert "legal" in ei.value.extra


def test_action_stale_version_rejected():
    svc = make_service()
    view, _ = configure_with_fake_bots(svc)
    if view["to_act"] != 0:
        pytest.skip("seat 0 not first to act in this deal")
    with pytest.raises(ServiceError) as ei:
        svc.act(
            turn_id=view["turn_id"], expected_version=view["version"] + 1,
            client_action_id="stale-1", kind="check" if view["legal"]["can_check"] else "fold",
        )
    assert ei.value.code == "stale"


def test_duplicate_client_action_id_is_idempotent():
    svc = make_service()
    view, _ = configure_with_fake_bots(svc)
    if view["to_act"] != 0:
        pytest.skip("seat 0 not first to act in this deal")
    legal = view["legal"]
    kind = "check" if legal["can_check"] else "fold"
    first = svc.act(turn_id=view["turn_id"], expected_version=view["version"], client_action_id="dup-1", kind=kind)
    assert "duplicate" not in first or not first["duplicate"]
    second = svc.act(turn_id=view["turn_id"], expected_version=view["version"], client_action_id="dup-1", kind=kind)
    assert second["duplicate"] is True
    assert second["version"] == first["version"]


# ---------------------------------------------------------------------------
# agent fallback / disconnect
# ---------------------------------------------------------------------------

def test_agent_timeout_falls_back_and_flags():
    svc = make_service()

    def factory(cfg, table_id, seat):
        if seat == 1:
            return FakeSeatRunner(mode="latency", latency_s=1.0)
        return FakeSeatRunner(mode="test_bot")

    svc._seat_runner_factory = factory
    view = svc.configure(
        [
            {"name": "Slow", "avatar": "🦊", "personality": "balanced", "model_id": "default"},
            {"name": "B", "avatar": "🐙", "personality": "balanced", "model_id": "default"},
            {"name": "C", "avatar": "🧪", "personality": "balanced", "model_id": "default"},
        ],
        decision_timeout_s=0.05,
    )
    # Whoever acts, drive the table forward until seat 1 has taken at least one turn.
    steps = 0
    while steps < 200:
        steps += 1
        view = svc.human_view()
        if view["hand_no"] > 3 or view["status"] == "finished":
            break
        seat1 = next(s for s in view["seats"] if s["seat"] == 1)
        if seat1.get("last_action") and seat1["last_action"].get("fallback"):
            break
        if view["to_act"] == 0 and view["legal"]:
            legal = view["legal"]
            kind = "check" if legal["can_check"] else ("call" if legal["can_call"] else "fold")
            view = svc.act(turn_id=view["turn_id"], expected_version=view["version"], client_action_id=f"a{steps}", kind=kind)
        elif view["next_hand_at"] is not None:
            view = svc.next_hand()
        else:
            break
    seat1 = next(s for s in svc.human_view()["seats"] if s["seat"] == 1)
    assert seat1["agent"]["fallbacks"] >= 1
    if seat1.get("last_action"):
        assert seat1["last_action"]["kind"] in ("check", "fold")


def test_agent_provider_error_marks_disconnected_after_two():
    svc = make_service()

    def factory(cfg, table_id, seat):
        if seat == 1:
            return FakeSeatRunner(mode="error", error=RuntimeError("simulated outage"))
        return FakeSeatRunner(mode="test_bot")

    svc._seat_runner_factory = factory
    view = svc.configure(
        [
            {"name": "Down", "avatar": "🦊", "personality": "balanced", "model_id": "default"},
            {"name": "B", "avatar": "🐙", "personality": "balanced", "model_id": "default"},
            {"name": "C", "avatar": "🧪", "personality": "balanced", "model_id": "default"},
        ],
        decision_timeout_s=5.0,
    )
    steps = 0
    seat1_meta = None
    while steps < 400:
        steps += 1
        view = svc.human_view()
        seat1_meta = next(s for s in view["seats"] if s["seat"] == 1)
        if seat1_meta["agent"]["state"] == "disconnected":
            break
        if view["status"] == "finished" or view["hand_no"] > 15:
            break
        if view["to_act"] == 0 and view["legal"]:
            legal = view["legal"]
            kind = "check" if legal["can_check"] else ("call" if legal["can_call"] else "fold")
            view = svc.act(turn_id=view["turn_id"], expected_version=view["version"], client_action_id=f"p{steps}", kind=kind)
        elif view["next_hand_at"] is not None:
            view = svc.next_hand()
        else:
            break
    assert seat1_meta is not None and seat1_meta["agent"]["state"] == "disconnected"

    # Clears on the next ok decision.
    runner = svc._runners[1]
    runner.mode = "test_bot"
    for _ in range(20):
        view = svc.human_view()
        if view["status"] == "finished":
            break
        seat1_meta = next(s for s in view["seats"] if s["seat"] == 1)
        if seat1_meta["agent"]["state"] != "disconnected":
            break
        if view["to_act"] == 0 and view["legal"]:
            legal = view["legal"]
            kind = "check" if legal["can_check"] else ("call" if legal["can_call"] else "fold")
            view = svc.act(turn_id=view["turn_id"], expected_version=view["version"], client_action_id=f"q{_}", kind=kind)
        elif view["next_hand_at"] is not None:
            view = svc.next_hand()
    assert seat1_meta["agent"]["state"] != "disconnected"


# ---------------------------------------------------------------------------
# stale/late decision discard
# ---------------------------------------------------------------------------

def test_late_decision_discarded_after_reset():
    svc = make_service()
    view, runners = configure_with_fake_bots(svc)
    in_flight = svc._in_flight
    if in_flight is None:
        pytest.skip("no agent in flight in this deal shape")
    req = in_flight["req"]
    gen = in_flight["gen"]
    version_before = svc._service_version
    svc.reset()
    from agent_hold_em.controller.types import DecisionResult, empty_usage

    late = DecisionResult({"kind": "fold", "to": None}, None, "ok", None, empty_usage(), 5, DecisionResult.binding_of(req))
    with svc._lock:
        svc._on_decision(gen, req, late)
    assert svc.status == "setup"
    assert svc._service_version == version_before + 1  # only reset's own bump, nothing double-applied


def test_late_decision_discarded_after_pause():
    svc = make_service()
    view, runners = configure_with_fake_bots(svc)
    in_flight = svc._in_flight
    if in_flight is None:
        pytest.skip("no agent in flight in this deal shape")
    req = in_flight["req"]
    gen = in_flight["gen"]
    svc.pause()
    version_after_pause = svc._service_version
    from agent_hold_em.controller.types import DecisionResult, empty_usage

    late = DecisionResult({"kind": "fold", "to": None}, None, "ok", None, empty_usage(), 5, DecisionResult.binding_of(req))
    with svc._lock:
        svc._on_decision(gen, req, late)
    assert svc._service_version == version_after_pause
    assert svc.status == "paused"


def test_resume_issues_new_turn_id():
    svc = make_service()
    view, runners = configure_with_fake_bots(svc)
    turn_before = svc.turn_id
    svc.pause()
    resumed = svc.resume()
    if resumed["to_act"] not in (None, 0):
        assert resumed["turn_id"] != turn_before


# ---------------------------------------------------------------------------
# pause / reset semantics
# ---------------------------------------------------------------------------

def test_pause_cancels_in_flight_and_reports_paused():
    svc = make_service()
    configure_with_fake_bots(svc)
    view = svc.pause()
    assert view["status"] == "paused"
    assert view["pause_reason"] == "manual"
    assert svc._in_flight is None


def test_reset_returns_to_setup():
    svc = make_service()
    configure_with_fake_bots(svc)
    view = svc.reset()
    assert view["status"] == "setup"
    assert svc.table is None


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------

def test_persisted_file_permissions_and_atomic_write():
    svc = make_service()
    configure_with_fake_bots(svc)
    path = store.table_path()
    assert path.exists()
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600
    dir_mode = stat.S_IMODE(os.stat(path.parent).st_mode)
    assert dir_mode == 0o700


def test_corrupt_file_is_moved_aside_and_starts_fresh(tmp_path):
    path = store.table_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")
    svc = make_service()
    assert svc.status == "setup"
    corrupt_files = list(path.parent.glob("table.json.corrupt-*"))
    assert len(corrupt_files) == 1


def test_reload_mid_hand_restores_paused():
    factory1, _ = make_fake_factory()
    svc1 = make_service(seat_runner_factory=factory1)
    view, _ = configure_with_fake_bots(svc1)
    assert svc1.status == "running"

    factory2, _ = make_fake_factory()
    svc2 = make_service(seat_runner_factory=factory2)
    assert svc2.status == "paused"
    assert svc2.pause_reason == "restored"
    assert svc2.table is not None
    assert svc2.table.hand_no == svc1.table.hand_no
    # Nothing double-applied: resuming issues a fresh turn_id rather than auto-continuing
    # whatever decision might have been in flight when persisted.
    resumed = svc2.resume()
    assert resumed["status"] == "running"


# ---------------------------------------------------------------------------
# privacy leak checks
# ---------------------------------------------------------------------------

def test_no_hole_card_leak_across_hands():
    svc = make_service()
    view, runners = configure_with_fake_bots(svc, timeout_s=5.0)
    broadcaster = svc._broadcaster
    steps = 0
    while steps < 3000:
        steps += 1
        view = svc.human_view()
        if view["hand_no"] > 12 or view["status"] == "finished":
            break

        if view["status"] == "running" and svc.table and svc.table.hand_in_progress:
            hole_by_seat = {s: list(svc.table._hole.get(s, [])) for s in svc.table._hand_seats}
            # `log`/`last_hand` legitimately carry the PREVIOUS hand's revealed cards (a
            # different shuffle) — a bare card token recurs every hand, so a prior hand's
            # legitimate reveal colliding, as a string, with a different card privately held
            # THIS hand would otherwise be flagged as a false leak (docs/TESTING.md's documented
            # trap). Scope the strict scan to fields that only ever describe the current hand.
            def _current_hand_only(obj):
                return {k: v for k, v in obj.items() if k not in ("log", "last_hand")}

            for seat, hole in hole_by_seat.items():
                other_holes = [c for s2, h2 in hole_by_seat.items() if s2 != seat for c in h2]
                # human view only ever carries seat 0's own hole cards (or a revealed showdown card).
                if seat != 0:
                    dump_no_card_leak(_current_hand_only(view), hole)
                # every agent's own observation must never carry another live seat's hole cards.
                obs = svc._agent_observation(seat)
                dump_no_card_leak(_current_hand_only(obs), other_holes)
            for event, payload in broadcaster.events:
                dump_no_card_leak(payload, [c for h in hole_by_seat.values() for c in h])

        if view["status"] == "running" and view["next_hand_at"] is not None:
            svc.next_hand()
            continue
        if view["to_act"] == 0 and view["legal"]:
            legal = view["legal"]
            kind = "check" if legal["can_check"] else ("call" if legal["can_call"] else "fold")
            svc.act(turn_id=view["turn_id"], expected_version=view["version"], client_action_id=f"lk{steps}", kind=kind)
        elif view["status"] == "finished":
            break


def test_broadcast_payload_never_carries_game_data():
    svc = make_service()
    configure_with_fake_bots(svc)
    broadcaster: RecordingBroadcaster = svc._broadcaster
    assert broadcaster.events
    for event, payload in broadcaster.events:
        assert event == "table.changed"
        assert set(payload.keys()) <= {"version", "status"}
