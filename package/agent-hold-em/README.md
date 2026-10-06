# Agent Hold 'Em (plugin package)

No-Limit Texas Hold 'Em: one human vs three real Hermes agents, inside Hermes Desktop.

This directory is the install unit — copied whole by `scripts/install.sh` to
`<hermes_home>/profiles/<profile>/plugins/agent-hold-em/`.

## Layout

- `dashboard/manifest.json` — plugin manifest (`tab.hidden: true`: this plugin has its
  own full-page UI via the desktop half's `ROUTES_AREA`, not the legacy web dashboard tab).
- `dashboard/plugin_api.py` — thin FastAPI router (`router = APIRouter()`), mounted at
  `/api/plugins/agent-hold-em/` by the Hermes backend.
- `dashboard/agent_hold_em/` — the game itself:
  - `engine/` — pure, synchronous Texas Hold 'Em rules engine (no I/O, no Hermes imports).
  - `controller/` — turns one seat's turn into a validated action via a real, isolated,
    zero-tool Hermes `AIAgent` (`HermesSeatRunner`), plus a `FakeSeatRunner` test double.
  - `service.py` — `TableService`: the single process-wide turn scheduler, persistence,
    and event broadcaster tying the engine and controller together.
  - `store.py` — atomic, permissioned (0600) JSON persistence at
    `<HERMES_HOME>/plugin-data/agent-hold-em/table.json`.
- `desktop/plugin.js` — the BUILT desktop UI bundle (`scripts/build-frontend.sh`
  regenerates this from `frontend/src/`; never hand-edit it).

## Configuration

`POST /table` accepts `{opponents: [{profile_id, name, personality, model_id, kind?}, ×3],
decision_timeout_s?}`. `kind: "test_bot"` (a scripted, clearly-labelled dev opponent
policy, never a real Hermes agent) is accepted only when the server process has
`AGENT_HOLD_EM_DEV=1` set — it is refused with a 422 otherwise, so a real install can
never accidentally seat a fake opponent at the table.

## Persistence & restart safety

The table's full private state (including hole cards and remaining deck order) is
written to `<HERMES_HOME>/plugin-data/agent-hold-em/table.json` after every mutation —
directory mode 0700, file mode 0600, atomic temp-file + `os.replace`. A table
persisted mid-hand always reloads as `paused` (`pause_reason: "restored"`): no
in-flight agent decision is ever resumed automatically, so a backend restart can
never spend tokens on the human's behalf without them choosing to resume.

## Uninstall

`scripts/uninstall.sh` reverses `scripts/install.sh`: removes the plugin directory and
its `plugins.enabled` entry, but keeps the config.yaml backup and
`plugin-data/agent-hold-em/` (pass `--purge` to also remove the persisted table).
