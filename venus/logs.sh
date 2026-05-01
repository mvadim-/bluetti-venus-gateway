#!/bin/sh
set -eu

DATA_DIR="${BLUETTI_DATA_DIR:-/data/bluetti-gateway}"
LINES="${1:-120}"

for log_file in "$DATA_DIR"/logs/bluetti-collector.log "$DATA_DIR"/logs/bluetti-dbus-bridge.log "$DATA_DIR"/logs/bluetti-repair-on-boot.log; do
  echo "==> $log_file <=="
  if [ -f "$log_file" ]; then
    tail -n "$LINES" "$log_file" | sed -E 's/(PASSWORD|TOKEN|SECRET)=([^ ]+)/\1=***/g'
  else
    echo "log file missing"
  fi
done
