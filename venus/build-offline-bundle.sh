#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
export PYTHONPATH="$APP_DIR/src:${PYTHONPATH:-}"
VERSION="$(python3 - <<'PY'
from bluetti_venus_gateway import __version__
print(__version__)
PY
)"
OUT="${1:-$APP_DIR/dist/bluetti-venus-gateway-rpi5-aarch64-v$VERSION.tar.gz}"
STAGING="$(mktemp -d)"

mkdir -p "$(dirname "$OUT")" "$STAGING/app"
tar --exclude '.git' --exclude '.venv' --exclude 'dist' --exclude '.pytest_cache' -cf - -C "$APP_DIR" . | tar -xf - -C "$STAGING/app"
cat >"$STAGING/manifest.json" <<EOF
{
  "name": "bluetti-venus-gateway",
  "version": "$VERSION",
  "created_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
EOF
(cd "$STAGING" && find . -type f -print | sort | xargs sha256sum > checksums.txt)
tar -czf "$OUT" -C "$STAGING" .
rm -rf "$STAGING"
echo "$OUT"
