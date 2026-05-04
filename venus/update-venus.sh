#!/bin/sh
set -eu

APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
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

if [ "$DRY_RUN" = "1" ]; then
  if [ -n "$OFFLINE_BUNDLE" ]; then
    "$APP_DIR/venus/install-venus.sh" --dry-run --offline-bundle "$OFFLINE_BUNDLE"
  else
    "$APP_DIR/venus/install-venus.sh" --dry-run
  fi
  exit 0
fi

if [ -n "$OFFLINE_BUNDLE" ]; then
  "$APP_DIR/venus/install-venus.sh" --offline-bundle "$OFFLINE_BUNDLE"
else
  "$APP_DIR/venus/install-venus.sh"
fi
