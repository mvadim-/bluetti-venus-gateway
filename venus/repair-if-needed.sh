#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DATA_DIR="${BLUETTI_DATA_DIR:-/data/bluetti-gateway}"
STATE_FILE="$DATA_DIR/state/install.json"
FORCE=0

if [ "${1:-}" = "--force" ]; then
  FORCE=1
fi

current_version="unknown"
if [ -f /opt/victronenergy/version ]; then
  current_version="$(sed -n '/[^[:space:]]/{p;q;}' /opt/victronenergy/version)"
fi

installed_version=""
if [ -f "$STATE_FILE" ]; then
  installed_version="$(sed -n 's/.*"venus_os_version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$STATE_FILE" | head -n 1)"
fi

if [ "$FORCE" = "1" ] || [ "$current_version" != "$installed_version" ] || [ ! -e /service/bluetti-collector ] || [ ! -e /service/bluetti-dbus-bridge ]; then
  "$APP_DIR/venus/install-venus.sh"
else
  printf 'No repair needed.\n'
fi
