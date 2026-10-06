"""store.py — atomic, permissioned JSON persistence for the table's private state
(docs/ARCHITECTURE.md §5).

Location: `<HERMES_HOME>/plugin-data/agent-hold-em/table.json`. Directory 0700, file
0600, written via temp-file + fsync + `os.replace` (atomic on the same filesystem),
schema-versioned. A corrupt file is moved aside (`table.json.corrupt-<ts>`) rather
than raised on — the service starts fresh (`setup`) instead of crashing the plugin.

This module holds ONLY the private recovery blob (deck order, hole cards included,
via `engine.Table.to_dict()`) plus service metadata (seat config, recent action ids,
settings). It never filters privacy itself — that is `service.py`'s job when it
builds views for the API; this module's whole job is durable, safe-permission I/O.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

__all__ = ["SCHEMA_VERSION", "data_dir", "table_path", "load", "save"]

SCHEMA_VERSION = 1
_DATA_DIRNAME = "plugin-data/agent-hold-em"
_FILENAME = "table.json"

# Logged once per process so a persistently-corrupt file doesn't spam the log on
# every load() retry loop.
_logged_corrupt = False


def _hermes_home() -> Path:
    """Resolve HERMES_HOME the supported way (verified: `hermes_constants.get_hermes_home()`,
    ARCHITECTURE.md §1 rule: never write under the real `~/.hermes` in dev)."""
    try:
        from hermes_constants import get_hermes_home

        return Path(get_hermes_home())
    except Exception:
        home = os.environ.get("HERMES_HOME", "").strip()
        if home:
            return Path(home)
        raise RuntimeError("cannot resolve HERMES_HOME: hermes_constants unavailable and HERMES_HOME unset")


def data_dir() -> Path:
    return _hermes_home() / _DATA_DIRNAME


def table_path() -> Path:
    return data_dir() / _FILENAME


def _ensure_dir(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        logger.debug("agent-hold-em: could not chmod %s", d, exc_info=True)


def load() -> Optional[dict[str, Any]]:
    """Load persisted state, or None if there is none (first run) or it was corrupt
    (moved aside, logged once, treated as absent so the service falls back to `setup`)."""
    path = table_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict) or "schema" not in data:
            raise ValueError("missing/invalid schema field")
        return data
    except Exception as e:
        global _logged_corrupt
        ts = time.strftime("%Y%m%d-%H%M%S")
        corrupt_path = path.with_name(f"{path.name}.corrupt-{ts}")
        try:
            os.replace(path, corrupt_path)
        except OSError:
            logger.debug("agent-hold-em: could not move aside corrupt store", exc_info=True)
        if not _logged_corrupt:
            logger.error("agent-hold-em: corrupt table.json moved aside to %s (%s)", corrupt_path, e)
            _logged_corrupt = True
        return None


def save(data: dict[str, Any]) -> None:
    """Atomic write: temp file in the same directory, fsync, `os.replace`, mode 0600.

    Called after every mutation (ARCHITECTURE.md §5). Never raises to the caller on
    a transient filesystem error other than the initial directory creation — callers
    (service.py) wrap this in try/except so a persistence hiccup never crashes a
    live decision; but a fundamental HERMES_HOME resolution failure IS allowed to
    raise (there is nowhere safe to write, better to surface loudly at startup).
    """
    d = data_dir()
    _ensure_dir(d)
    path = table_path()
    payload = dict(data)
    payload["schema"] = SCHEMA_VERSION
    text = json.dumps(payload, separators=(",", ":"))

    fd, tmp_name = tempfile.mkstemp(prefix=".table.", suffix=".tmp", dir=str(d))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
