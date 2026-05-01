from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from pathlib import Path

from bluetti_venus_gateway.config import DEFAULT_CONFIG_PATH
from bluetti_venus_gateway.config import ConfigError
from bluetti_venus_gateway.config import load_config
from bluetti_venus_gateway.telemetry.core import parse_iso8601
from bluetti_venus_gateway.telemetry.snapshot_store import read_snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    print(render_status(args.config))


def render_status(config_path: Path = DEFAULT_CONFIG_PATH) -> str:
    lines = []
    lines.append(f"Venus OS: {'detected' if Path('/opt/victronenergy').exists() else 'not detected'}")
    lines.append(f"Venus OS version: {_read_first_existing(['/opt/victronenergy/version', '/etc/venus-version']) or 'unknown'}")
    lines.append(f"VRM Portal ID: {_read_vrm_portal_id()}")
    lines.append(f"config: {'present' if config_path.exists() else 'missing'}")
    try:
        config = load_config(config_path)
    except (ConfigError, FileNotFoundError) as exc:
        lines.append(f"config status: invalid ({exc})")
        return "\n".join(lines)

    lines.append(f"bluetti-collector: {_service_state('bluetti-collector')}")
    lines.append(f"bluetti-dbus-bridge: {_service_state('bluetti-dbus-bridge')}")
    lines.append(f"bluetti-repair-on-boot: {'installed' if Path('/service/bluetti-repair-on-boot').exists() else 'missing'}")
    lines.append(f"vrmlogger: {_service_state('vrmlogger')}")
    lines.append(_snapshot_status(config.snapshot_path))
    lines.append(f"D-Bus battery service: {_dbus_has_name('com.victronenergy.battery.ep760_' + str(config.battery_device_instance))}")
    lines.append(f"D-Bus grid service: {_dbus_has_name('com.victronenergy.grid.ep760_' + str(config.grid_device_instance))}")
    lines.append(f"D-Bus acload service: {_dbus_has_name('com.victronenergy.acload.ep760_' + str(config.acload_device_instance))}")
    lines.append(f"offline bundle: {'present' if list(Path('/data').glob('bluetti-venus-gateway-*.tar.gz')) else 'missing'}")
    return "\n".join(lines)


def _snapshot_status(path: Path) -> str:
    try:
        payload = read_snapshot(path)
        received_at = parse_iso8601(str(payload.get("received_at") or ""))
        age = int(max(0.0, time.time() - received_at.timestamp()))
        return f"latest telemetry age: {age}s"
    except Exception as exc:
        return f"latest telemetry age: unavailable ({exc})"


def _service_state(name: str) -> str:
    service_dir = Path("/service") / name
    if not service_dir.exists():
        return "missing"
    if shutil.which("svstat"):
        result = subprocess.run(["svstat", str(service_dir)], capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout.strip()
            if " up " in f" {output} " or output.endswith(" up"):
                return "running"
            return output or "installed"
    return "installed"


def _dbus_has_name(name: str) -> str:
    if not shutil.which("dbus-send"):
        return "unknown"
    result = subprocess.run(
        [
            "dbus-send",
            "--system",
            "--print-reply",
            "--dest=org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus.ListNames",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        return "unknown"
    return "present" if f'string "{name}"' in result.stdout else "missing"


def _read_vrm_portal_id() -> str:
    candidates = [
        "/data/conf/vrm/portalId",
        "/data/conf/serial-starter/unique-id",
        "/etc/venus/serial-number",
    ]
    value = _read_first_existing(candidates)
    if value:
        return value
    get_unique_id = Path("/opt/victronenergy/serial-starter/get-unique-id")
    if get_unique_id.exists():
        try:
            result = subprocess.run(
                [str(get_unique_id)],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception:
            return "unknown"
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().splitlines()[0]
    return "unknown"


def _read_first_existing(paths: list[str]) -> str | None:
    for raw_path in paths:
        path = Path(raw_path)
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                value = line.strip()
                if value:
                    return value
    return None


if __name__ == "__main__":
    main()
