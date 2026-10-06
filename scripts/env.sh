# Source me:  . scripts/env.sh
# Dev/test environment for Agent Hold 'Em. Uses the installed Hermes source and
# its Python 3.11 test venv (which includes pytest). A live Hermes backend may
# run in a newer managed runtime; check that runtime separately before install.
# Never points HERMES_HOME at the real ~/.hermes.

_ahe_root="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
export AHE_ROOT="$_ahe_root"

# Locate the Hermes checkout + its interpreter. Works both on the real machine
# (~/.hermes) and inside the Cowork VM (folders mounted under $HOME/mnt).
if [ -z "${HERMES_AGENT_DIR:-}" ]; then
  for c in "$HOME/mnt/.hermes/hermes-agent" "$HOME/.hermes/hermes-agent"; do
    [ -d "$c" ] && HERMES_AGENT_DIR="$c" && break
  done
fi
export HERMES_AGENT_DIR
_site="$HERMES_AGENT_DIR/venv/lib/python3.11/site-packages"

if [ -z "${PY:-}" ]; then
  for c in "$HOME"/mnt/uv/python/cpython-3.11*/bin/python3.11 \
           "$HOME"/.local/share/uv/python/cpython-3.11*/bin/python3.11 \
           "$HERMES_AGENT_DIR/venv/bin/python"; do
    [ -x "$c" ] && PY="$c" && break
  done
fi
export PY

export PYTHONPATH="$AHE_ROOT/package/agent-hold-em/dashboard:$AHE_ROOT/package/agent-hold-em/dashboard/_vendor:$HERMES_AGENT_DIR:$_site${PYTHONPATH:+:$PYTHONPATH}"
export HERMES_DISABLE_LAZY_INSTALLS=1      # importing hermes must never try to sync/download deps
export PYTHONDONTWRITEBYTECODE=1           # never drop .pyc files into the Hermes checkout
export AHE_SCRATCH="${AHE_SCRATCH:-/tmp/ahe-scratch}"
export HERMES_HOME="$AHE_SCRATCH/hermes-home"   # scratch home — NEVER the real one
mkdir -p "$HERMES_HOME"

export ESBUILD="${ESBUILD:-$HERMES_AGENT_DIR/node_modules/@esbuild/linux-x64/bin/esbuild}"
