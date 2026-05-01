from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from bluetti_venus_gateway import __version__
from bluetti_venus_gateway.config import DEFAULT_CONFIG_PATH
from bluetti_venus_gateway.config import ConfigError
from bluetti_venus_gateway.config import load_config
from bluetti_venus_gateway.logging import configure_logging
from bluetti_venus_gateway.telemetry.snapshot_store import SnapshotStoreError
from bluetti_venus_gateway.telemetry.snapshot_store import read_snapshot
from bluetti_venus_gateway.victron.bridge_model import build_venus_bridge_payload
from bluetti_venus_gateway.victron.bridge_model import settings_from_gateway_config
from bluetti_venus_gateway.victron.dbus_service import VenusDbusPublisher


LOGGER = logging.getLogger(__name__)


def run(config_path: Path = DEFAULT_CONFIG_PATH) -> None:
    config = load_config(config_path)
    configure_logging(config.log_level)
    publisher = VenusDbusPublisher(
        process_name="bluetti-dbus-bridge",
        process_version=__version__,
        connection_name="BLUETTI Venus Gateway",
    )
    settings = settings_from_gateway_config(config)
    config.run_dir.mkdir(parents=True, exist_ok=True)
    ready_path = config.run_dir / "dbus-bridge.ready"
    ready_path.write_text(str(time.time()), encoding="utf-8")
    last_snapshot_missing_log_at = 0.0
    while True:
        try:
            envelope = read_snapshot(config.snapshot_path)
            publisher.publish(build_venus_bridge_payload(envelope, settings=settings))
        except SnapshotStoreError as exc:
            now = time.monotonic()
            if now - last_snapshot_missing_log_at >= 60:
                LOGGER.info("%s", exc)
                last_snapshot_missing_log_at = now
        except Exception:
            LOGGER.exception("D-Bus bridge refresh failed")
        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    try:
        run(args.config)
    except ConfigError as exc:
        logging.basicConfig(level=logging.ERROR, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        LOGGER.error("Invalid gateway config: %s", exc)
        while True:
            time.sleep(3600)


if __name__ == "__main__":
    main()
