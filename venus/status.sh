#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export PYTHONPATH="$APP_DIR/src:${PYTHONPATH:-}"
exec python3 -m bluetti_venus_gateway.tools.status "$@"

