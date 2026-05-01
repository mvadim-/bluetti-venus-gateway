#!/bin/sh
set -eu

SERVICE_ROOT="${BLUETTI_SERVICE_ROOT:-/service}"
if ! command -v svc >/dev/null 2>&1; then
  echo "svc command is not available; restart services manually." >&2
  exit 1
fi

svc -t "$SERVICE_ROOT/bluetti-collector" || true
svc -t "$SERVICE_ROOT/bluetti-dbus-bridge" || true

