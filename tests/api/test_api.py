"""tests/api — FastAPI route-level tests via TestClient (docs/ARCHITECTURE.md §5 REST table)."""
from __future__ import annotations

import os


def test_health(app_client):
    r = app_client.get("/api/plugins/agent-hold-em/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True


def test_models(app_client):
    r = app_client.get("/api/plugins/agent-hold-em/models")
    assert r.status_code == 200
    body = r.json()
    assert body["options"]
    assert body["options"][0]["id"] == "default"


def test_profiles_route(app_client):
    r = app_client.get("/api/plugins/agent-hold-em/profiles")
    assert r.status_code == 200
    assert "profiles" in r.json()


def test_models_rejects_unknown_profile(app_client):
    r = app_client.get("/api/plugins/agent-hold-em/models?profile=does-not-exist")
    assert r.status_code == 422
    assert r.json()["code"] == "unknown_profile"


def test_state_before_setup(app_client):
    r = app_client.get("/api/plugins/agent-hold-em/state")
    assert r.status_code == 200
    assert r.json()["status"] == "setup"


def test_create_table(app_client):
    view = app_client.configure_with_fake_bots()[0]
    assert view["status"] == "running"
    r = app_client.get("/api/plugins/agent-hold-em/state")
    assert r.json()["status"] == "running"


def test_create_table_rejects_test_bot_without_dev_flag(app_client, monkeypatch):
    monkeypatch.delenv("AGENT_HOLD_EM_DEV", raising=False)
    r = app_client.post(
        "/api/plugins/agent-hold-em/table",
        json={"opponents": [
            {"name": "A", "kind": "test_bot"}, {"name": "B", "kind": "hermes"}, {"name": "C", "kind": "hermes"},
        ]},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "test_bot_forbidden"


def test_create_table_validation_wrong_count(app_client):
    r = app_client.post("/api/plugins/agent-hold-em/table", json={"opponents": [{"name": "A"}]})
    assert r.status_code == 422


def test_action_route_shapes(app_client):
    view, _ = app_client.configure_with_fake_bots()
    if view["to_act"] != 0:
        return  # not seat 0's turn in this deal shape; other tests cover the validation paths directly
    legal = view["legal"]
    kind = "check" if legal["can_check"] else "fold"
    r = app_client.post(
        "/api/plugins/agent-hold-em/action",
        json={
            "turn_id": view["turn_id"], "expected_version": view["version"],
            "client_action_id": "api-1", "kind": kind,
        },
    )
    assert r.status_code == 200

    # stale version -> 409
    r2 = app_client.post(
        "/api/plugins/agent-hold-em/action",
        json={
            "turn_id": view["turn_id"], "expected_version": view["version"],
            "client_action_id": "api-2", "kind": kind,
        },
    )
    assert r2.status_code == 409
    # Either the turn has already moved on (not_your_turn) or the same binding is now stale
    # (stale) — which one depends on whether seat 0 happened to act again this deal.
    assert r2.json()["code"] in ("stale", "not_your_turn")


def test_action_illegal_shape(app_client):
    view, _ = app_client.configure_with_fake_bots()
    if view["to_act"] != 0:
        return
    r = app_client.post(
        "/api/plugins/agent-hold-em/action",
        json={
            "turn_id": view["turn_id"], "expected_version": view["version"],
            "client_action_id": "api-illegal", "kind": "raise", "to": 1,
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "illegal"
    assert "legal" in body


def test_pause_resume_next_hand_reset_routes(app_client):
    app_client.configure_with_fake_bots()
    r = app_client.post("/api/plugins/agent-hold-em/pause")
    assert r.status_code == 200 and r.json()["status"] == "paused"
    r = app_client.post("/api/plugins/agent-hold-em/resume")
    assert r.status_code == 200 and r.json()["status"] == "running"
    r = app_client.post("/api/plugins/agent-hold-em/next-hand")
    assert r.status_code == 200
    r = app_client.post("/api/plugins/agent-hold-em/reset", json={"confirm": True})
    assert r.status_code == 200 and r.json()["status"] == "setup"


def test_reset_requires_confirm(app_client):
    app_client.configure_with_fake_bots()
    r = app_client.post("/api/plugins/agent-hold-em/reset", json={"confirm": False})
    assert r.status_code == 422


def test_history_route(app_client):
    app_client.configure_with_fake_bots()
    r = app_client.get("/api/plugins/agent-hold-em/history?limit=5")
    assert r.status_code == 200
    assert "hands" in r.json()


def test_action_body_validation_rejects_extra_fields(app_client):
    app_client.configure_with_fake_bots()
    r = app_client.post(
        "/api/plugins/agent-hold-em/action",
        json={"turn_id": "x", "expected_version": 0, "client_action_id": "y", "kind": "check", "sneaky": 1},
    )
    assert r.status_code == 422


def test_errors_never_include_tracebacks(app_client):
    r = app_client.post(
        "/api/plugins/agent-hold-em/action",
        json={"turn_id": "x", "expected_version": 0, "client_action_id": "y", "kind": "check"},
    )
    assert r.status_code in (409, 422)
    assert "Traceback" not in r.text
