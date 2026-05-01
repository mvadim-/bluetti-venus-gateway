#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DATA_DIR="${BLUETTI_DATA_DIR:-/data/bluetti-gateway}"
RUN_DIR="${BLUETTI_RUN_DIR:-/run/bluetti-gateway}"
CONFIG_FILE="$DATA_DIR/bluetti-gateway.env"
SERVICE_ROOT="${BLUETTI_SERVICE_ROOT:-/service}"
STATE_DIR="$DATA_DIR/state"
DRY_RUN=0

if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN=1
fi

log() {
  printf '%s\n' "$*"
}

run() {
  if [ "$DRY_RUN" = "1" ]; then
    printf 'dry-run:'
    printf ' %s' "$@"
    printf '\n'
    return 0
  fi
  "$@"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "missing required command: $1"
    return 1
  fi
}

require_python_import() {
  module="$1"
  if ! python3 -c "import $module" >/dev/null 2>&1; then
    log "missing required Python import: $module"
    return 1
  fi
}

check_prerequisites() {
  missing=0
  for cmd in python3 openssl dbus-send; do
    require_command "$cmd" || missing=1
  done
  require_python_import dbus || missing=1
  require_python_import gi || missing=1
  require_python_import paho.mqtt.client || missing=1
  if [ "$missing" = "1" ]; then
    log "Install missing Venus OS/opkg prerequisites before continuing."
    exit 1
  fi
}

install_service() {
  name="$1"
  source_dir="$APP_DIR/venus/services/$name"
  target_dir="$SERVICE_ROOT/$name"
  run chmod +x "$source_dir/run"
  if [ -L "$target_dir" ] || [ -e "$target_dir" ]; then
    run rm -f "$target_dir"
  fi
  run ln -s "$source_dir" "$target_dir"
}

wait_for_service_control() {
  name="$1"
  target_dir="$SERVICE_ROOT/$name"
  attempts="${BLUETTI_SERVICE_CONTROL_WAIT_ATTEMPTS:-20}"
  i=0
  while [ "$i" -lt "$attempts" ]; do
    if [ -e "$target_dir/supervise/control" ]; then
      return 0
    fi
    sleep 1
    i=$((i + 1))
  done
  log "service control not ready yet: $target_dir"
  return 1
}

start_service_if_ready() {
  name="$1"
  if ! command -v svc >/dev/null 2>&1 || [ "$DRY_RUN" = "1" ]; then
    return 0
  fi
  if wait_for_service_control "$name"; then
    svc -u "$SERVICE_ROOT/$name" || true
  fi
}

write_install_state() {
  version="unknown"
  if [ -f /opt/victronenergy/version ]; then
    version="$(sed -n '/[^[:space:]]/{p;q;}' /opt/victronenergy/version)"
  fi
  run mkdir -p "$STATE_DIR"
  if [ "$DRY_RUN" = "1" ]; then
    return 0
  fi
  cat >"$STATE_DIR/install.json" <<EOF
{
  "app_dir": "$APP_DIR",
  "venus_os_version": "$version",
  "installed_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
EOF
}

log "Installing BLUETTI Venus Gateway from $APP_DIR"
check_prerequisites
run mkdir -p "$DATA_DIR" "$DATA_DIR/cache" "$DATA_DIR/certs" "$DATA_DIR/logs" "$STATE_DIR" "$RUN_DIR"
run touch "$DATA_DIR/logs/bluetti-collector.log" "$DATA_DIR/logs/bluetti-dbus-bridge.log" "$DATA_DIR/logs/bluetti-repair-on-boot.log"
if [ ! -f "$CONFIG_FILE" ]; then
  run cp "$APP_DIR/venus/config/bluetti-gateway.env.example" "$CONFIG_FILE"
  run chmod 600 "$CONFIG_FILE"
  log "Created config template at $CONFIG_FILE; edit it before starting live services."
else
  log "Preserving existing config: $CONFIG_FILE"
fi

install_service bluetti-collector
install_service bluetti-dbus-bridge
install_service bluetti-repair-on-boot
write_install_state

start_service_if_ready bluetti-collector
start_service_if_ready bluetti-dbus-bridge

log "Install complete."
