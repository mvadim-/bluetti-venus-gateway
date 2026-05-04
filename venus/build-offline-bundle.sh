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
COMMIT="unknown"
if command -v git >/dev/null 2>&1 && git -C "$APP_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  COMMIT="$(git -C "$APP_DIR" rev-parse --short HEAD)"
fi

mkdir -p "$(dirname "$OUT")" "$STAGING/app"
tar \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'dist' \
  --exclude '.pytest_cache' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.DS_Store' \
  --exclude 'venus/services/*/supervise' \
  --exclude 'bluetti-gateway.env' \
  --exclude 'certs' \
  --exclude 'cache' \
  --exclude 'logs' \
  -cf - -C "$APP_DIR" . | tar -xf - -C "$STAGING/app"
cat >"$STAGING/manifest.json" <<EOF
$(sed \
  -e "s/@VERSION@/$VERSION/g" \
  -e "s/@REPO_COMMIT@/$COMMIT/g" \
  -e "s/@CREATED_AT@/$(date -u '+%Y-%m-%dT%H:%M:%SZ')/g" \
  "$APP_DIR/venus/bundle-manifest.template.json")
EOF
cat >"$STAGING/system-packages.txt" <<'EOF'
git
openssl
openssl-ossl-module-legacy
mosquitto-clients
python3-core
python3-dbus
python3-paho-mqtt
python3-pygobject
python3-cryptography
EOF
(cd "$STAGING" && find app manifest.json system-packages.txt -type f -print | sort | xargs sha256sum > checksums.txt)
tar -czf "$OUT" -C "$STAGING" .
rm -rf "$STAGING"
echo "$OUT"
