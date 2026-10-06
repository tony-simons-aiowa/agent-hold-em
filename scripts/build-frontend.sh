#!/usr/bin/env bash
# Builds the Agent Hold 'Em desktop plugin bundle:
#   frontend/src/index.jsx -> package/agent-hold-em/desktop/plugin.js
#
# Output is a single uncompiled-looking ESM file with exactly three allowed
# import specifiers (@hermes/plugin-sdk, react, react/jsx-runtime) — the only
# ones the Hermes desktop runtime loader will resolve (see
# apps/desktop/src/contrib/runtime-loader.ts unsupportedImports()). No
# minification: the file must stay readable for review/hot-reload debugging.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"

if [ -z "${ESBUILD:-}" ]; then
  . scripts/env.sh
fi

OUT="package/agent-hold-em/desktop/plugin.js"
mkdir -p "$(dirname "$OUT")"

VERSION="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo dev)"
BANNER="/**
 * Agent Hold 'Em — desktop plugin (built file — edit frontend/src, never this file)
 * Version: ${VERSION}
 * Built:   $(date -u +%Y-%m-%dT%H:%M:%SZ)
 * Build:   scripts/build-frontend.sh
 */"

echo "==> esbuild frontend/src/index.jsx -> ${OUT}"
"$ESBUILD" frontend/src/index.jsx \
  --bundle \
  --format=esm \
  --jsx=automatic \
  --target=es2022 \
  --external:@hermes/plugin-sdk \
  --external:react \
  --external:react/jsx-runtime \
  --banner:js="$BANNER" \
  --outfile="$OUT"

echo "==> checking import specifiers"
# Every static/dynamic import specifier in the OUTPUT must be one of the three
# allowed ones. esbuild's ESM output only ever uses `import ... from "…"` (no
# side-effect-only or dynamic import for externals), so this regex is exact
# for our own build's shape — not a general-purpose JS parser.
BAD_IMPORTS="$(grep -oE 'from *"[^"]+"' "$OUT" | sed -E 's/from *"(.*)"/\1/' | sort -u | grep -vE '^(@hermes/plugin-sdk|react|react/jsx-runtime)$' || true)"
if [ -n "$BAD_IMPORTS" ]; then
  echo "FAIL: bundle imports specifiers outside the allowed set:" >&2
  echo "$BAD_IMPORTS" >&2
  exit 1
fi
echo "    OK — only allowed specifiers present:"
grep -oE 'from *"[^"]+"' "$OUT" | sort -u | sed 's/^/    /'

echo "==> checking the bundle parses as ESM"
# node --check doesn't understand `import`/`export` in a .js file run this
# way, so force module mode explicitly; this parses (does not execute) the
# file, which is enough to catch a syntax error in the build output without
# needing to resolve the (deliberately external) bare specifiers.
node --input-type=module --check < "$OUT"
echo "    OK — parses as ESM"

SIZE="$(wc -c < "$OUT" | tr -d ' ')"
echo "==> build OK: ${OUT} (${SIZE} bytes)"
