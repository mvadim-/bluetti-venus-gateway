from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime
from datetime import timezone
from pathlib import Path
import time

from bluetti_venus_gateway.config import DEFAULT_CONFIG_PATH
from bluetti_venus_gateway.config import load_config
from bluetti_venus_gateway.logging import configure_logging
from bluetti_venus_gateway.telemetry.core import build_snapshot_envelope
from bluetti_venus_gateway.telemetry.snapshot_store import atomic_write_json


LOGGER = logging.getLogger(__name__)


def run(config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    config = load_config(config_path)
    configure_logging(config.log_level)
    config.run_dir.mkdir(parents=True, exist_ok=True)

    fixture_path = os.environ.get("BLUETTI_COLLECTOR_FIXTURE_JSON")
    if not fixture_path:
        LOGGER.error(
            "live BLUETTI MQTT collector is not implemented in this bootstrap cycle; "
            "set BLUETTI_COLLECTOR_FIXTURE_JSON for local bridge validation",
        )
        _park_unavailable_collector()

    LOGGER.warning("Using fixture snapshot source: %s", fixture_path)
    while True:
        raw_payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        snapshot = raw_payload.get("snapshot") if isinstance(raw_payload, dict) else None
        if not isinstance(snapshot, dict):
            raise ValueError("fixture JSON must contain an object at key 'snapshot'")
        envelope = build_snapshot_envelope(
            device_sn=config.device_sn,
            snapshot=snapshot,
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            stale_after_seconds=config.stale_after_seconds,
        )
        atomic_write_json(config.snapshot_path, envelope)
        (config.run_dir / "collector.ready").write_text(str(time.time()), encoding="utf-8")
        LOGGER.info("Wrote fixture telemetry snapshot to %s", config.snapshot_path)
        time.sleep(config.poll_interval_seconds)


def _park_unavailable_collector() -> None:
    while True:
        time.sleep(3600)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
