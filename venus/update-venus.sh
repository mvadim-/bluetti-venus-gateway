#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

if [ "${1:-}" = "--offline-bundle" ]; then
  bundle="${2:-}"
  if [ -z "$bundle" ] || [ ! -f "$bundle" ]; then
    echo "offline bundle not found: $bundle" >&2
    exit 1
  fi
  tar -xzf "$bundle" -C "$APP_DIR"
fi

"$APP_DIR/venus/install-venus.sh"

