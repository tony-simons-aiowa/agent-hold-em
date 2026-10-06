import json
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


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "slow: long-running service tests")
    config.addinivalue_line("markers", "integration: exercises a REAL AIAgent against the fake OpenAI server (slower)")


def _scratch_home_outside_native_root(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    """A scratch HERMES_HOME the Hermes dependency manager can never confuse with the real one.

    `hermes_constants.get_default_hermes_root()` treats any HERMES_HOME under the platform
    native root (`~/.hermes`) as a profile dir and resolves the root back to `~/.hermes`
    itself. pytest's `tmp_path` lives under TMPDIR — which on a Hermes-hosted machine IS
    `~/.hermes/cache/scratch`, so a tmp_path-based home would silently bind the REAL
    dependency state (`~/.hermes/installs/...`). The first in-test import of
    `hermes_bootstrap` (via `run_agent.AIAgent`) then runs `activate_dependencies()`, which
    swaps this process onto the committed generation — built for a different Python — and
    every third-party import dies with ABI errors (`No module named
    'pydantic_core._pydantic_core'`). The integration suite passed only with `TMPDIR=/tmp`.

    Fix: when the tmp dir is under the native root, put the scratch home in a temp dir that
    is NOT under the native root (still per-test, still auto-cleaned)."""
    import shutil
    import tempfile

    native_root = Path.home() / ".hermes"

    def _under_native(p: Path) -> bool:
        try:
            p.resolve().relative_to(native_root.resolve())
            return True
        except (ValueError, OSError):
            return False

    if not _under_native(tmp_path):
        home = tmp_path / "hermes-home"
        home.mkdir()
        return home
    # tempfile.mkdtemp() honours TMPDIR itself, which may BE the dir under the native root
    # (Hermes exports TMPDIR=$HERMES_HOME/cache/scratch) — pick an explicit base instead.
    candidates = [Path(tempfile.gettempdir()), Path("/tmp"), Path.home()]
    base = next((c for c in candidates if c.is_dir() and not _under_native(c)), None)
    if base is None:  # pathological: every temp dir is inside the native root
        home = tmp_path / "hermes-home"
        home.mkdir()
        return home
    home = Path(tempfile.mkdtemp(prefix="ahe-scratch-home-", dir=str(base)))
    request.addfinalizer(lambda: shutil.rmtree(home, ignore_errors=True))
    return home


@pytest.fixture(autouse=True)
def _isolated_scratch_home(tmp_path, monkeypatch, request):
    """Every test gets its OWN scratch HERMES_HOME (never the real one) and its OWN singleton
    registry slot, so tests never see each other's persisted table.json or service instance."""
    home = _scratch_home_outside_native_root(tmp_path, request)
    monkeypatch.setenv("HERMES_HOME", str(home))
    # Reset the process-wide singleton registry between tests (the registry deliberately
    # survives module re-import across the real app's lifetime; tests must not inherit it).
    if hasattr(threading, "_agent_hold_em_service_registry_v1"):
        delattr(threading, "_agent_hold_em_service_registry_v1")
    yield
    if hasattr(threading, "_agent_hold_em_service_registry_v1"):
        delattr(threading, "_agent_hold_em_service_registry_v1")


class InlineExecutor:
    """Runs a submitted callable synchronously, on the caller's thread. Because
    `TableService` always calls `executor.submit()` while already holding its own
    (reentrant) lock, and the submitted function itself re-acquires that same lock,
    this makes every test's decision path deterministic and instant — no real
    thread scheduling races, no sleeping for real wall-clock deadlines except where
    a test explicitly wants FakeSeatRunner "latency" behavior (small, bounded)."""

    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)
        return _DoneFuture()


class _DoneFuture:
    def result(self, timeout=None):
        return None

    def done(self):
        return True


class RecordingBroadcaster:
    def __init__(self):
        self.events = []

    def __call__(self, event, payload):
        self.events.append((event, dict(payload)))


def make_service(seat_runner_factory=None, broadcaster=None, decision_timeout_s=None):
    from agent_hold_em.service import TableService

    svc = TableService(
        seat_runner_factory=seat_runner_factory,
        broadcaster=broadcaster or RecordingBroadcaster(),
        executor=InlineExecutor(),
    )
    return svc


def make_fake_factory(mode="test_bot", **fake_kwargs):
    from agent_hold_em.controller.fake import FakeSeatRunner

    runners = {}

    def factory(cfg, table_id, seat):
        r = FakeSeatRunner(mode=mode, **fake_kwargs)
        runners[seat] = r
        return r

    return factory, runners


def configure_with_fake_bots(svc, *, mode="test_bot", timeout_s=5.0, **fake_kwargs):
    factory, runners = make_fake_factory(mode=mode, **fake_kwargs)
    svc._seat_runner_factory = factory
    view = svc.configure(
        [
            {"name": "Grokbot", "avatar": "🦊", "personality": "aggressive", "model_id": "default"},
            {"name": "OpenClaw", "avatar": "🐙", "personality": "cautious", "model_id": "default"},
            {"name": "Sandbox", "avatar": "🧪", "personality": "balanced", "model_id": "default"},
        ],
        decision_timeout_s=timeout_s,
    )
    return view, runners


def dump_no_card_leak(obj, private_cards, boundary_chars=None):
    """Assert no token in `private_cards` (e.g. another seat's hole cards, or the
    current hand's remaining deck) appears as a standalone token anywhere in
    `obj`'s JSON serialization (boundary-aware: '2s' must not match inside a
    longer alphanumeric run)."""
    import re
    import string

    if boundary_chars is None:
        boundary_chars = string.ascii_letters + string.digits
    text = json.dumps(obj)
    for card in private_cards:
        for m in re.finditer(re.escape(card), text):
            start, end = m.start(), m.end()
            before_ok = start == 0 or text[start - 1] not in boundary_chars
            after_ok = end == len(text) or text[end] not in boundary_chars
            assert not (before_ok and after_ok), f"leaked card token {card!r} found in payload"
