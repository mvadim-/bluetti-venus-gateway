#!/bin/sh
set -eu

DATA_DIR="${BLUETTI_DATA_DIR:-/data/bluetti-gateway}"
LINES="${1:-120}"

for log_file in "$DATA_DIR"/logs/bluetti-collector.log "$DATA_DIR"/logs/bluetti-dbus-bridge.log "$DATA_DIR"/logs/bluetti-repair-on-boot.log; do
  if [ -f "$log_file" ]; then
    echo "==> $log_file <=="
    tail -n "$LINES" "$log_file" | sed -E 's/(PASSWORD|TOKEN|SECRET)=([^ ]+)/\1=***/g'
  fi
done

