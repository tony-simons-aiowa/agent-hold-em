# Agent Hold 'Em

No-Limit Texas Hold 'Em for Hermes Desktop: play one human against three real,
isolated Hermes agents. The game uses play chips only. Agent decisions use the
models configured in Hermes and may consume provider tokens.

## Requirements

- Hermes Agent with Hermes Desktop and the desktop plugin SDK.
- Python 3.11+ and pytest for the backend test suite.
- Node.js and esbuild for building the desktop bundle (the build script resolves
the repository's configured Hermes development environment).

## Install

From a checkout of this repository, install into an existing Hermes profile:

```bash
scripts/install.sh --profile default --hermes-home "$HOME/.hermes"
```

Use the profile name and Hermes home appropriate for your installation. The
installer backs up affected configuration files, copies the package, and
updates the plugin enablement configuration. Review those changes before
running it. Restart the Hermes backend serving that profile after installation,
then enable Agent Hold 'Em in Hermes Desktop under Capabilities → Plugins.

## Play

Open the Agent Hold 'Em sidebar entry or choose **Agent Hold 'Em: Open table**
from the command palette. Select three local Hermes profiles, then choose each
opponent's poker personality and model. Start with 1,000 chips per seat and
fixed 5/10 blinds. Use the betting controls and their displayed keyboard
shortcuts. Pause stops new agent decisions; restored tables remain paused until
resumed.

## Develop and test

```bash
scripts/test.sh            # fast Python suite and frontend build
scripts/test.sh --slow     # exhaustive engine and real-agent tests
bash scripts/build-harness.sh
```

The standalone UI harness can be served from `frontend/harness` with
`python3 -m http.server 8877`; use `?fixture=setup` or `?fixture=preflop_turn`.
The engine is native and dependency-free. `docs/TESTING.md` documents rule
choices and test coverage; `package/agent-hold-em/README.md` describes the
installable package internals.

## Limitations and privacy

This is a local, single-player poker game, not a gambling product. Opponent
agents run through Hermes and can incur provider usage costs. Their model
responses are untrusted input; the game engine validates every action. See the
package documentation for persistence and restart behavior.
