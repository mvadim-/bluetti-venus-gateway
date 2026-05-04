verify_offline_bundle() {
  bundle="$1"
  extract_dir="$2"
  if [ -z "$bundle" ] || [ ! -f "$bundle" ]; then
    echo "offline bundle not found: $bundle" >&2
    return 1
  fi
  if ! command -v tar >/dev/null 2>&1; then
    echo "missing required command: tar" >&2
    return 1
  fi
  if ! command -v sha256sum >/dev/null 2>&1; then
    echo "missing required command: sha256sum" >&2
    return 1
  fi
  mkdir -p "$extract_dir"
  if ! tar -xzf "$bundle" -C "$extract_dir"; then
    echo "offline bundle is not a readable gzip tar archive: $bundle" >&2
    return 1
  fi
  if [ ! -d "$extract_dir/app" ]; then
    echo "offline bundle is missing app/" >&2
    return 1
  fi
  if [ ! -f "$extract_dir/manifest.json" ]; then
    echo "offline bundle is missing manifest.json" >&2
    return 1
  fi
  if [ ! -f "$extract_dir/checksums.txt" ]; then
    echo "offline bundle is missing checksums.txt" >&2
    return 1
  fi
  if [ ! -x "$extract_dir/app/venus/install-venus.sh" ]; then
    echo "offline bundle app is missing executable venus/install-venus.sh" >&2
    return 1
  fi
  (cd "$extract_dir" && sha256sum -c checksums.txt >/dev/null)
}

apply_offline_bundle() {
  bundle="$1"
  app_dir="$2"
  extract_dir="$(mktemp -d)"
  cleanup_extract_dir() {
    rm -rf "$extract_dir"
  }
  trap cleanup_extract_dir EXIT HUP INT TERM
  verify_offline_bundle "$bundle" "$extract_dir"
  mkdir -p "$app_dir"
  (cd "$extract_dir/app" && tar -cf - .) | (cd "$app_dir" && tar -xf -)
  cleanup_extract_dir
  trap - EXIT HUP INT TERM
}
