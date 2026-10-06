import os
import sys
import threading
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent.parent
_DASHBOARD = _ROOT / "package" / "agent-hold-em" / "dashboard"
for _p in (str(_DASHBOARD), str(_ROOT / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault("HERMES_DISABLE_LAZY_INSTALLS", "1")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

import importlib.util

_svc_conftest_path = Path(__file__).resolve().parent.parent / "service" / "conftest.py"
_spec = importlib.util.spec_from_file_location("agent_hold_em_service_test_helpers", _svc_conftest_path)
_svc_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_svc_helpers)

# Same helper module, loaded under its real name so the fixture below shares the fix.
_scratch_home = _svc_helpers._scratch_home_outside_native_root


@pytest.fixture(autouse=True)
def _isolated_scratch_home(tmp_path, monkeypatch, request):
    home = _scratch_home(tmp_path, request)
    monkeypatch.setenv("HERMES_HOME", str(home))
    if hasattr(threading, "_agent_hold_em_service_registry_v1"):
        delattr(threading, "_agent_hold_em_service_registry_v1")
    yield
    if hasattr(threading, "_agent_hold_em_service_registry_v1"):
        delattr(threading, "_agent_hold_em_service_registry_v1")


@pytest.fixture
def app_client(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import plugin_api
    from agent_hold_em.service import TableService

    InlineExecutor = _svc_helpers.InlineExecutor
    RecordingBroadcaster = _svc_helpers.RecordingBroadcaster
    configure_with_fake_bots = _svc_helpers.configure_with_fake_bots

    svc = TableService(broadcaster=RecordingBroadcaster(), executor=InlineExecutor())
    monkeypatch.setattr(plugin_api, "get_service", lambda: svc)

    app = FastAPI()
    app.include_router(plugin_api.router, prefix="/api/plugins/agent-hold-em")
    client = TestClient(app)
    client.service = svc
    client.configure_with_fake_bots = lambda **kw: configure_with_fake_bots(svc, **kw)
    return client
