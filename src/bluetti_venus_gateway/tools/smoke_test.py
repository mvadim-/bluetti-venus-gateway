from __future__ import annotations

import argparse
from pathlib import Path

from bluetti_venus_gateway.config import DEFAULT_CONFIG_PATH
from bluetti_venus_gateway.config import load_config
from bluetti_venus_gateway.telemetry.snapshot_store import read_snapshot
from bluetti_venus_gateway.victron.bridge_model import build_venus_bridge_payload
from bluetti_venus_gateway.victron.bridge_model import iter_venus_service_payloads
from bluetti_venus_gateway.victron.bridge_model import settings_from_gateway_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    config = load_config(args.config)
    payload = build_venus_bridge_payload(
        read_snapshot(config.snapshot_path),
        settings=settings_from_gateway_config(config),
    )
    for service_name, values in iter_venus_service_payloads(payload):
        connected = values.get("/Connected")
        print(f"{service_name}: Connected={connected}")


if __name__ == "__main__":
    main()

