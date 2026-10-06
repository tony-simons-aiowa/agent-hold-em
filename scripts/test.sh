#!/usr/bin/env bash
# Full automated test suite for Agent Hold 'Em (docs/ARCHITECTURE.md §8).
#
# Default (fast, ~what you run while iterating): engine + controller + service + api
# tests, deselecting `slow` and `integration` marks, plus the frontend build check.
#
#   scripts/test.sh            # fast suites + frontend build check
#   scripts/test.sh --slow     # also the exhaustive/long-running engine sweeps and the
#                               # real-AIAgent end-to-end integration test
#   scripts/test.sh --no-build # skip the frontend build check (Python suites only)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"
. scripts/env.sh

RUN_SLOW=0
RUN_BUILD=1
for arg in "$@"; do
  case "$arg" in
    --slow) RUN_SLOW=1 ;;
    --no-build) RUN_BUILD=0 ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

FAILED=0
declare -a SUMMARY

_run_suite() {
  local label="$1"; shift
  echo "==> ${label}"
  if "$@"; then
    SUMMARY+=("PASS  ${label}")
  else
    SUMMARY+=("FAIL  ${label}")
    FAILED=1
  fi
  echo
}

if [ "$RUN_SLOW" -eq 1 ]; then
  _run_suite "engine (full, incl. slow)"      "$PY" -m pytest tests/engine -q
  _run_suite "controller (incl. integration)" "$PY" -m pytest tests/controller -q
  _run_suite "service (incl. integration)"    "$PY" -m pytest tests/service -q
else
  _run_suite "engine (fast)"      "$PY" -m pytest tests/engine -m "not slow" -q
  _run_suite "controller (fast)"  "$PY" -m pytest tests/controller -m "not integration" -q
  _run_suite "service (fast)"     "$PY" -m pytest tests/service -m "not integration" -q
fi

_run_suite "api" "$PY" -m pytest tests/api -q
_run_suite "frontend errors" node --test tests/frontend/api-errors.test.mjs

if [ "$RUN_BUILD" -eq 1 ]; then
  _run_suite "frontend build" bash scripts/build-frontend.sh
fi

echo "================ Agent Hold 'Em — test summary ================"
for line in "${SUMMARY[@]}"; do echo "  $line"; done
echo "================================================================="

exit "$FAILED"
