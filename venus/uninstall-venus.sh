#!/bin/sh
set -eu

SERVICE_ROOT="${BLUETTI_SERVICE_ROOT:-/service}"
for name in bluetti-collector bluetti-dbus-bridge bluetti-repair-on-boot; do
  if command -v svc >/dev/null 2>&1 && [ -e "$SERVICE_ROOT/$name" ]; then
    svc -d "$SERVICE_ROOT/$name" || true
  fi
  rm -f "$SERVICE_ROOT/$name"
done

echo "Services removed. Preserved /data/bluetti-gateway config, cache, certs, and logs."

