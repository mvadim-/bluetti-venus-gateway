from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime
from datetime import timezone
from pathlib import Path
import time

from bluetti_venus_gateway.bluetti.auth import BluettiAuthError
from bluetti_venus_gateway.bluetti.auth import BluettiAuthSettings
from bluetti_venus_gateway.bluetti.auth import build_ssl_context
from bluetti_venus_gateway.bluetti.auth import prepare_mqtt_context
from bluetti_venus_gateway.bluetti.auth import refresh_mqtt_password
from bluetti_venus_gateway.bluetti.mqtt_client import build_modbus_read
from bluetti_venus_gateway.bluetti.mqtt_client import build_mqtt_payload
from bluetti_venus_gateway.bluetti.parser import decode_bluetti_payload
from bluetti_venus_gateway.bluetti.parser import merge_decoded_state
from bluetti_venus_gateway.bluetti.parser import normalize_decoded_state
from bluetti_venus_gateway.bluetti.polling import build_poll_profile
from bluetti_venus_gateway.bluetti.polling import due_polls
from bluetti_venus_gateway.config import DEFAULT_CONFIG_PATH
from bluetti_venus_gateway.config import ConfigError
from bluetti_venus_gateway.config import GatewayConfig
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
        run_live_collector(config)
        return

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


def run_live_collector(config: GatewayConfig) -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError as exc:
        raise RuntimeError("python3-paho-mqtt is required for live collector") from exc

    poll_specs = build_poll_profile(
        config.poll_profile,
        enable_pv=config.enable_pv,
        enable_pack_diagnostics=config.enable_pack_diagnostics,
    )
    backoff_seconds = 5
    while True:
        try:
            context = prepare_mqtt_context(_auth_settings_from_config(config))
            LOGGER.info(
                "Prepared BLUETTI MQTT context host=%s:%s subscribe=%s publish=%s polls=%s",
                context.host,
                context.port,
                context.subscribe_topic,
                context.publish_topic,
                ",".join(str(spec.addr) for spec in poll_specs),
            )
            collector = LiveMqttCollector(config=config, mqtt_module=mqtt, context=context, poll_specs=poll_specs)
            collector.run()
            backoff_seconds = 5
        except BluettiAuthError as exc:
            LOGGER.error("BLUETTI auth failed: %s", exc)
            if not exc.retryable:
                _park_unavailable_collector("non-retryable BLUETTI auth failure")
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 300)
        except Exception:
            LOGGER.exception("BLUETTI collector failed; restarting")
            time.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 300)


class LiveMqttCollector:
    def __init__(self, *, config: GatewayConfig, mqtt_module: object, context: object, poll_specs: list[object]) -> None:
        self._config = config
        self._mqtt = mqtt_module
        self._context = context
        self._poll_specs = poll_specs
        self._decoded_state: dict[str, object] = {}
        self._last_observed_at: datetime | None = None
        self._connected = False
        self._client = self._build_client()

    def run(self) -> None:
        self._client.connect(self._context.host, self._context.port, keepalive=60)
        self._client.loop_start()
        cycle = 0
        try:
            while True:
                if int(time.time()) >= self._context.refresh_after_epoch:
                    LOGGER.info("Refreshing BLUETTI auth context")
                    return
                if self._connected:
                    cycle += 1
                    self._publish_due_polls(cycle)
                self._write_latest_snapshot()
                time.sleep(self._config.poll_interval_seconds)
        finally:
            self._client.loop_stop()
            self._client.disconnect()

    def _build_client(self):
        client = self._new_mqtt_client()
        client.username_pw_set(self._context.username, refresh_mqtt_password(self._context))
        client.tls_set_context(build_ssl_context(self._context))
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        return client

    def _new_mqtt_client(self):
        callback_api_version = getattr(self._mqtt, "CallbackAPIVersion", None)
        if callback_api_version is not None and hasattr(callback_api_version, "VERSION1"):
            return self._mqtt.Client(
                callback_api_version.VERSION1,
                client_id=self._context.client_id,
                protocol=self._mqtt.MQTTv311,
            )
        return self._mqtt.Client(
            client_id=self._context.client_id,
            protocol=self._mqtt.MQTTv311,
        )

    def _on_connect(self, client, _userdata, _flags, rc) -> None:
        if rc != 0:
            LOGGER.error("BLUETTI MQTT connect failed rc=%s", rc)
            return
        self._connected = True
        client.subscribe(self._context.subscribe_topic, qos=0)
        LOGGER.info("Connected to BLUETTI MQTT and subscribed to %s", self._context.subscribe_topic)

    def _on_disconnect(self, _client, _userdata, rc) -> None:
        self._connected = False
        LOGGER.warning("BLUETTI MQTT disconnected rc=%s", rc)

    def _on_message(self, _client, _userdata, message) -> None:
        decoded = decode_bluetti_payload(message.payload)
        if not decoded.get("messageType"):
            return
        self._decoded_state = merge_decoded_state(self._decoded_state, decoded)
        self._last_observed_at = datetime.now(timezone.utc)
        self._write_latest_snapshot()

    def _publish_due_polls(self, cycle: int) -> None:
        for spec in due_polls(self._poll_specs, cycle):
            modbus_cmd = build_modbus_read(spec.addr, spec.length, self._context.modbus_slave)
            payload_hex = build_mqtt_payload(modbus_cmd, spec.addr, self._config.mqtt_payload_format)
            self._client.publish(self._context.publish_topic, bytes.fromhex(payload_hex), qos=0)

    def _write_latest_snapshot(self) -> None:
        if not self._decoded_state:
            return
        snapshot = normalize_decoded_state(self._decoded_state)
        if not snapshot:
            return
        observed_at = self._last_observed_at or datetime.now(timezone.utc)
        envelope = build_snapshot_envelope(
            device_sn=self._config.device_sn,
            snapshot=snapshot,
            observed_at=observed_at,
            received_at=datetime.now(timezone.utc),
            stale_after_seconds=self._config.stale_after_seconds,
        )
        atomic_write_json(self._config.snapshot_path, envelope)
        (self._config.run_dir / "collector.ready").write_text(str(time.time()), encoding="utf-8")


def _auth_settings_from_config(config: GatewayConfig) -> BluettiAuthSettings:
    return BluettiAuthSettings(
        email=config.email,
        password=config.password,
        device_sn=config.device_sn,
        auth_device_id=config.auth_device_id,
        certs_dir=config.certs_dir,
        mqtt_client_id=config.mqtt_client_id,
        mqtt_ciphers=config.mqtt_ciphers,
    )


def _park_unavailable_collector(reason: str) -> None:
    LOGGER.error("Parking collector: %s", reason)
    while True:
        time.sleep(3600)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    try:
        run(args.config)
    except ConfigError as exc:
        logging.basicConfig(level=logging.ERROR, format="%(asctime)s %(levelname)s %(name)s %(message)s")
        LOGGER.error("Invalid gateway config: %s", exc)
        _park_unavailable_collector("invalid gateway config")


if __name__ == "__main__":
    main()
