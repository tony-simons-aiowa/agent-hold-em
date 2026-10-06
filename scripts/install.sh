#!/usr/bin/env bash
# Installs Agent Hold 'Em into a Hermes profile (docs/ARCHITECTURE.md §8).
#
# Idempotent: safe to re-run. Copies package/agent-hold-em/ into the profile's
# plugins/ directory, backs up that profile's config.yaml, and adds
# "agent-hold-em" to its `plugins.enabled` YAML list via a line-level text edit
# that preserves everything else in the file (never `hermes config set
# plugins.enabled ...`, which stores a STRING per the hermes-desktop-plugins
# SKILL's own warning).
#
# Usage:
#   scripts/install.sh [--profile NAME] [--hermes-home PATH] [--dry-run]
#
# --profile NAME        Profile to install into. Default: the profile named in
#                        <hermes_home>/active_profile, or "default" if that file
#                        is absent.
# --hermes-home PATH     Hermes home to install into. Default: $HERMES_HOME if
#                        set, else ~/.hermes. NEVER defaults into a test/scratch
#                        home silently — pass --hermes-home explicitly when
#                        testing against a scratch layout.
# --dry-run              Print what would happen; touch nothing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
PLUGIN_ID="agent-hold-em"
PROFILE=""
HERMES_HOME_ARG=""
DRY_RUN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --profile=*) PROFILE="${1#*=}"; shift ;;
    --hermes-home) HERMES_HOME_ARG="$2"; shift 2 ;;
    --hermes-home=*) HERMES_HOME_ARG="${1#*=}"; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) grep -E '^#( |$)' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

HERMES_HOME="${HERMES_HOME_ARG:-${HERMES_HOME:-$HOME/.hermes}}"
if [ ! -d "$HERMES_HOME" ]; then
  echo "error: HERMES_HOME does not exist: $HERMES_HOME" >&2
  exit 1
fi

if [ -z "$PROFILE" ]; then
  if [ -f "$HERMES_HOME/active_profile" ]; then
    PROFILE="$(tr -d '[:space:]' < "$HERMES_HOME/active_profile")"
  fi
  PROFILE="${PROFILE:-default}"
fi

PROFILE_DIR="$HERMES_HOME/profiles/$PROFILE"
if [ "$PROFILE" = "default" ]; then
  PROFILE_DIR="$HERMES_HOME"
fi
CONFIG_PATH="$PROFILE_DIR/config.yaml"
PLUGIN_DIR="$PROFILE_DIR/plugins/$PLUGIN_ID"
ROOT_CONFIG_PATH="$HERMES_HOME/config.yaml"
ROOT_PLUGIN_LINK="$HERMES_HOME/plugins/$PLUGIN_ID"
SRC_DIR="$ROOT/package/agent-hold-em"

echo "==> Agent Hold 'Em install"
echo "    HERMES_HOME : $HERMES_HOME"
echo "    profile     : $PROFILE"
echo "    plugin dir  : $PLUGIN_DIR"
echo "    config.yaml : $CONFIG_PATH"

if [ ! -d "$PROFILE_DIR" ]; then
  echo "error: profile directory does not exist: $PROFILE_DIR (create the profile in Hermes first)" >&2
  exit 1
fi
if [ ! -f "$CONFIG_PATH" ]; then
  echo "error: profile has no config.yaml: $CONFIG_PATH" >&2
  exit 1
fi
if [ ! -d "$SRC_DIR/dashboard" ]; then
  echo "error: package source not found: $SRC_DIR (run from the repo root, or check the checkout)" >&2
  exit 1
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "==> --dry-run: no changes made. Would have:"
  echo "    - copied $SRC_DIR -> $PLUGIN_DIR"
  echo "    - backed up $CONFIG_PATH -> ${CONFIG_PATH}.bak-agent-hold-em-<timestamp>"
  echo "    - added '$PLUGIN_ID' to plugins.enabled in $CONFIG_PATH"
  if [ "$PROFILE_DIR" != "$HERMES_HOME" ] && [ -f "$ROOT_CONFIG_PATH" ]; then
    echo "    - linked $ROOT_PLUGIN_LINK -> $PLUGIN_DIR for the multiplexed dashboard"
    echo "    - added '$PLUGIN_ID' to plugins.enabled in $ROOT_CONFIG_PATH"
  fi
  exit 0
fi

if [ "$PROFILE_DIR" != "$HERMES_HOME" ] && [ -e "$ROOT_PLUGIN_LINK" ] && [ ! -L "$ROOT_PLUGIN_LINK" ]; then
  echo "error: root plugin path exists and is not our symlink: $ROOT_PLUGIN_LINK" >&2
  exit 1
fi
if [ -L "$ROOT_PLUGIN_LINK" ] && [ "$(readlink "$ROOT_PLUGIN_LINK")" != "$PLUGIN_DIR" ]; then
  echo "error: root plugin symlink points elsewhere: $ROOT_PLUGIN_LINK" >&2
  exit 1
fi

TS="$(date -u +%Y%m%d-%H%M%S)"
BACKUP_PATH="${CONFIG_PATH}.bak-agent-hold-em-${TS}"
cp -p "$CONFIG_PATH" "$BACKUP_PATH"
echo "==> backed up config.yaml -> $BACKUP_PATH"

mkdir -p "$(dirname "$PLUGIN_DIR")"
rm -rf "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"
cp -r "$SRC_DIR/." "$PLUGIN_DIR/"
# __pycache__ directories from any local test run must never ship into the install.
find "$PLUGIN_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} +
echo "==> copied package -> $PLUGIN_DIR"

PY_BIN="${PY:-python3}"
"$PY_BIN" "$ROOT/scripts/_edit_plugins_enabled.py" "$CONFIG_PATH" "$PLUGIN_ID" add

# The machine dashboard launched from the Hermes root scans root/plugins at
# import time, even when a profile is preselected in its UI. A symlink keeps
# one package copy while Path.resolve() still identifies the owning profile
# for per-seat config/secret scoping.
if [ "$PROFILE_DIR" != "$HERMES_HOME" ] && [ -f "$ROOT_CONFIG_PATH" ]; then
  mkdir -p "$HERMES_HOME/plugins"
  if [ ! -L "$ROOT_PLUGIN_LINK" ]; then
    ln -s "$PLUGIN_DIR" "$ROOT_PLUGIN_LINK"
    echo "==> linked multiplexed dashboard plugin -> $ROOT_PLUGIN_LINK"
  fi
  ROOT_BACKUP_PATH="${ROOT_CONFIG_PATH}.bak-agent-hold-em-${TS}"
  cp -p "$ROOT_CONFIG_PATH" "$ROOT_BACKUP_PATH"
  echo "==> backed up root config.yaml -> $ROOT_BACKUP_PATH"
  "$PY_BIN" "$ROOT/scripts/_edit_plugins_enabled.py" "$ROOT_CONFIG_PATH" "$PLUGIN_ID" add
fi

echo
echo "==> Install complete. Next steps:"
echo "    1. Restart the Hermes backend serving this profile (the 'hermes serve' child"
echo "       process for profile '$PROFILE') so it imports the new plugin_api.py."
echo "       (Find it, e.g.: pgrep -af 'hermes_cli.main serve'.)"
echo "    2. Confirm the log shows: Mounted plugin API routes: /api/plugins/$PLUGIN_ID/"
echo "    3. In Hermes Desktop: press ⌘K -> 'Reload desktop plugins' (the desktop half is"
echo "       auto-copied from plugins/$PLUGIN_ID/desktop/plugin.js on next launch/reload)."
