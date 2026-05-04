#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
DATA_DIR="${BLUETTI_DATA_DIR:-/data/bluetti-gateway}"
RUN_DIR="${BLUETTI_RUN_DIR:-/run/bluetti-gateway}"
CONFIG_FILE="$DATA_DIR/bluetti-gateway.env"
SERVICE_ROOT="${BLUETTI_SERVICE_ROOT:-/service}"
STATE_DIR="$DATA_DIR/state"
INSTALL_NTP="${BLUETTI_INSTALL_NTP:-1}"
NTP_CONF="${BLUETTI_NTP_CONF:-/etc/ntp.conf}"
NTP_SERVERS="${BLUETTI_NTP_SERVERS:-time.cloudflare.com time.google.com 0.pool.ntp.org 1.pool.ntp.org}"
DRY_RUN=0
OFFLINE_BUNDLE=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --offline-bundle)
      OFFLINE_BUNDLE="${2:-}"
      if [ -z "$OFFLINE_BUNDLE" ]; then
        echo "--offline-bundle requires a path" >&2
        exit 1
      fi
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

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

apply_or_verify_offline_bundle() {
  if [ -z "$OFFLINE_BUNDLE" ]; then
    return 0
  fi
  # shellcheck source=/dev/null
  . "$APP_DIR/venus/lib/offline-bundle.sh"
  if [ "$DRY_RUN" = "1" ]; then
    extract_dir="$(mktemp -d)"
    verify_offline_bundle "$OFFLINE_BUNDLE" "$extract_dir"
    rm -rf "$extract_dir"
    log "Verified offline bundle: $OFFLINE_BUNDLE"
    return 0
  fi
  if [ "${BLUETTI_BUNDLE_APPLIED:-0}" = "1" ]; then
    return 0
  fi
  log "Applying offline bundle: $OFFLINE_BUNDLE"
  apply_offline_bundle "$OFFLINE_BUNDLE" "$APP_DIR"
  BLUETTI_BUNDLE_APPLIED=1 exec "$APP_DIR/venus/install-venus.sh"
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
  if [ "$DRY_RUN" = "1" ]; then
    log "dry-run: skipping Venus OS prerequisite checks"
    return 0
  fi
  missing=0
  for cmd in python3 openssl dbus-send; do
    require_command "$cmd" || missing=1
  done
  require_python_import dbus || missing=1
  require_python_import gi || missing=1
  require_python_import paho.mqtt.client || missing=1
  require_python_import cryptography || missing=1
  if [ ! -f /usr/lib/ossl-modules/legacy.so ]; then
    log "missing required OpenSSL legacy provider: install opkg package openssl-ossl-module-legacy"
    missing=1
  fi
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

ensure_time_sync() {
  case "$INSTALL_NTP" in
    1|true|TRUE|yes|YES|on|ON) ;;
    *)
      log "Skipping NTP setup because BLUETTI_INSTALL_NTP=$INSTALL_NTP"
      return 0
      ;;
  esac
  if [ "$DRY_RUN" = "1" ]; then
    log "dry-run: ensure ntp package, configure $NTP_CONF, and restart ntpd"
    return 0
  fi
  if ! command -v ntpd >/dev/null 2>&1; then
    if ! command -v opkg >/dev/null 2>&1; then
      log "missing ntpd and opkg; install ntp manually or set BLUETTI_INSTALL_NTP=0"
      exit 1
    fi
    log "Installing ntp through opkg"
    opkg update
    opkg install ntp
  fi
  configure_ntp
  restart_ntpd
}

configure_ntp() {
  marker_begin="# BEGIN BLUETTI Venus Gateway NTP"
  marker_end="# END BLUETTI Venus Gateway NTP"
  tmp="$STATE_DIR/ntp.conf.tmp"
  mkdir -p "$(dirname "$NTP_CONF")" "$STATE_DIR"
  if [ -f "$NTP_CONF" ] && [ ! -f "$STATE_DIR/ntp.conf.before-bluetti" ]; then
    cp "$NTP_CONF" "$STATE_DIR/ntp.conf.before-bluetti"
  fi
  if [ ! -f "$NTP_CONF" ]; then
    cat >"$NTP_CONF" <<EOF
driftfile /var/lib/ntp/drift
restrict -4 default notrap nomodify nopeer noquery
restrict -6 default notrap nomodify nopeer noquery
restrict 127.0.0.1
restrict ::1
EOF
  fi
  awk -v begin="$marker_begin" -v end="$marker_end" '
    $0 == begin { skip = 1; next }
    $0 == end { skip = 0; next }
    skip { next }
    /^[[:space:]]*server[[:space:]]+127\.127\.1\.0/ { print "# " $0; next }
    /^[[:space:]]*fudge[[:space:]]+127\.127\.1\.0/ { print "# " $0; next }
    { print }
  ' "$NTP_CONF" >"$tmp"
  {
    cat "$tmp"
    printf '%s\n' "$marker_begin"
    for server in $NTP_SERVERS; do
      printf 'server %s iburst\n' "$server"
    done
    printf '%s\n' "$marker_end"
  } >"$tmp.next"
  mv "$tmp.next" "$NTP_CONF"
  rm -f "$tmp"
}

restart_ntpd() {
  if [ -x /etc/init.d/ntpd ]; then
    /etc/init.d/ntpd restart || /etc/init.d/ntpd start || true
    return 0
  fi
  if pidof ntpd >/dev/null 2>&1; then
    return 0
  fi
  if command -v ntpd >/dev/null 2>&1; then
    ntpd -u ntp:ntp -p /var/run/ntpd.pid -g || true
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

install_boot_hook() {
  rc_local="${BLUETTI_RC_LOCAL:-/data/rc.local}"
  marker_begin="# BEGIN BLUETTI Venus Gateway"
  marker_end="# END BLUETTI Venus Gateway"
  if [ "$DRY_RUN" = "1" ]; then
    log "dry-run: install boot hook in $rc_local"
    return 0
  fi
  if [ -f "$rc_local" ] && grep -q "$marker_begin" "$rc_local"; then
    return 0
  fi
  tmp="$STATE_DIR/rc.local.tmp"
  mkdir -p "$(dirname "$rc_local")" "$STATE_DIR"
  {
    if [ -f "$rc_local" ]; then
      first_line="$(sed -n '1p' "$rc_local")"
      case "$first_line" in
        '#!'*) printf '%s\n' "$first_line" ;;
        *) printf '%s\n' '#!/bin/sh' ;;
      esac
    else
      printf '%s\n' '#!/bin/sh'
    fi
    cat <<EOF
$marker_begin
if [ -x "$APP_DIR/venus/repair-if-needed.sh" ]; then
  mkdir -p "$DATA_DIR/logs"
  "$APP_DIR/venus/repair-if-needed.sh" >>"$DATA_DIR/logs/bluetti-repair-on-boot.log" 2>&1 || true
fi
$marker_end
EOF
    if [ -f "$rc_local" ]; then
      first_line="$(sed -n '1p' "$rc_local")"
      case "$first_line" in
        '#!'*) tail -n +2 "$rc_local" ;;
        *) cat "$rc_local" ;;
      esac
    else
      printf '%s\n' 'exit 0'
    fi
  } >"$tmp"
  mv "$tmp" "$rc_local"
  chmod 755 "$rc_local"
}

apply_or_verify_offline_bundle
log "Installing BLUETTI Venus Gateway from $APP_DIR"
check_prerequisites
run mkdir -p "$DATA_DIR" "$DATA_DIR/cache" "$DATA_DIR/certs" "$DATA_DIR/logs" "$STATE_DIR" "$RUN_DIR"
run touch "$DATA_DIR/logs/bluetti-collector.log" "$DATA_DIR/logs/bluetti-dbus-bridge.log" "$DATA_DIR/logs/bluetti-repair-on-boot.log"
ensure_time_sync
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
install_boot_hook

start_service_if_ready bluetti-collector
start_service_if_ready bluetti-dbus-bridge

log "Install complete."
