#!/usr/bin/env bash
# Reverses scripts/install.sh (docs/ARCHITECTURE.md §8). Removes the plugin directory
# and its plugins.enabled entry; keeps the config.yaml backup and the plugin's
# persisted table data (<hermes_home>/plugin-data/agent-hold-em/) unless --purge.
#
# Usage:
#   scripts/uninstall.sh [--profile NAME] [--hermes-home PATH] [--dry-run] [--purge]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
PLUGIN_ID="agent-hold-em"
PROFILE=""
HERMES_HOME_ARG=""
DRY_RUN=0
PURGE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --profile=*) PROFILE="${1#*=}"; shift ;;
    --hermes-home) HERMES_HOME_ARG="$2"; shift 2 ;;
    --hermes-home=*) HERMES_HOME_ARG="${1#*=}"; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --purge) PURGE=1; shift ;;
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
DATA_DIR="$HERMES_HOME/plugin-data/$PLUGIN_ID"

echo "==> Agent Hold 'Em uninstall"
echo "    HERMES_HOME : $HERMES_HOME"
echo "    profile     : $PROFILE"
echo "    plugin dir  : $PLUGIN_DIR"
echo "    config.yaml : $CONFIG_PATH"
echo "    purge data  : $([ "$PURGE" -eq 1 ] && echo yes || echo no) ($DATA_DIR)"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "==> --dry-run: no changes made. Would have:"
  echo "    - removed $PLUGIN_DIR"
  echo "    - removed '$PLUGIN_ID' from plugins.enabled in $CONFIG_PATH (if present)"
  if [ "$PROFILE_DIR" != "$HERMES_HOME" ]; then
    echo "    - removed owned root dashboard symlink and enabled entry (if present)"
  fi
  if [ "$PURGE" -eq 1 ]; then
    echo "    - removed $DATA_DIR (--purge)"
  fi
  exit 0
fi

if [ -d "$PLUGIN_DIR" ]; then
  rm -rf "$PLUGIN_DIR"
  echo "==> removed $PLUGIN_DIR"
else
  echo "==> $PLUGIN_DIR not present (nothing to remove)"
fi

if [ -f "$CONFIG_PATH" ]; then
  PY_BIN="${PY:-python3}"
  "$PY_BIN" "$ROOT/scripts/_edit_plugins_enabled.py" "$CONFIG_PATH" "$PLUGIN_ID" remove
else
  echo "==> $CONFIG_PATH not present; skipping plugins.enabled edit"
fi

if [ "$PROFILE_DIR" != "$HERMES_HOME" ] && [ -L "$ROOT_PLUGIN_LINK" ] && [ "$(readlink "$ROOT_PLUGIN_LINK")" = "$PLUGIN_DIR" ]; then
  rm "$ROOT_PLUGIN_LINK"
  echo "==> removed multiplexed dashboard link $ROOT_PLUGIN_LINK"
  if [ -f "$ROOT_CONFIG_PATH" ]; then
    "${PY:-python3}" "$ROOT/scripts/_edit_plugins_enabled.py" "$ROOT_CONFIG_PATH" "$PLUGIN_ID" remove
  fi
fi

if [ "$PURGE" -eq 1 ]; then
  if [ -d "$DATA_DIR" ]; then
    rm -rf "$DATA_DIR"
    echo "==> purged persisted table data: $DATA_DIR"
  fi
else
  echo "==> keeping persisted table data (pass --purge to remove $DATA_DIR)"
fi

echo
echo "==> Uninstall complete. Restart the Hermes backend for profile '$PROFILE' to stop"
echo "    serving the plugin's routes; config.yaml backups from install are left in place."
