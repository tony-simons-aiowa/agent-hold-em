#!/usr/bin/env bash
# Builds the screenshot harness: bundles frontend/harness/harness-entry.jsx
# with the REAL plugin source (frontend/src/index.jsx), aliasing
# '@hermes/plugin-sdk' to the harness's fake SDK, and bundling real
# react/react-dom/@tanstack/react-query/nanostores pulled from the Hermes
# checkout's own node_modules (there is no npm registry access anywhere, so
# nothing is installed — existing packages are symlinked in). Harness-only:
# never affects the shipped plugin bundle.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"

if [ -z "${ESBUILD:-}" ] || [ -z "${HERMES_AGENT_DIR:-}" ]; then
  . scripts/env.sh
fi

HARNESS_DIR="frontend/harness"
# node_modules lives at frontend/ (a common ancestor of both frontend/src and
# frontend/harness) — esbuild's resolver walks UP from the importing file, so
# a node_modules only under frontend/harness would never be found for a
# `react` import inside frontend/src/*.
NM="frontend/node_modules"
mkdir -p "$NM/@tanstack" "$NM/@nanostores"

link() {
  local src="$1" dest="$2"
  # A checkout copied from another machine can retain stale absolute links.
  if [ -L "$dest" ] && [ ! -e "$dest" ]; then
    rm "$dest"
  fi
  if [ ! -e "$dest" ]; then
    ln -s "$src" "$dest"
  fi
}

link "$HERMES_AGENT_DIR/node_modules/react" "$NM/react"
link "$HERMES_AGENT_DIR/node_modules/react-dom" "$NM/react-dom"
link "$HERMES_AGENT_DIR/node_modules/nanostores" "$NM/nanostores"
link "$HERMES_AGENT_DIR/node_modules/@tanstack/react-query" "$NM/@tanstack/react-query"
link "$HERMES_AGENT_DIR/node_modules/@tanstack/query-core" "$NM/@tanstack/query-core"
link "$HERMES_AGENT_DIR/node_modules/@nanostores/react" "$NM/@nanostores/react"

OUT="$HARNESS_DIR/harness.bundle.js"

echo "==> esbuild frontend/harness/harness-entry.jsx -> ${OUT}"
"$ESBUILD" "$HARNESS_DIR/harness-entry.jsx" \
  --bundle \
  --format=iife \
  --jsx=automatic \
  --target=es2022 \
  --alias:@hermes/plugin-sdk="$ROOT/$HARNESS_DIR/fake-sdk.jsx" \
  --outfile="$OUT"

echo "==> harness build OK: ${OUT} ($(wc -c < "$OUT" | tr -d ' ') bytes)"
echo "==> serve with: (cd ${HARNESS_DIR} && python3 -m http.server 8877)"
