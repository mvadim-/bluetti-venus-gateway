from __future__ import annotations

from collections import deque
from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest

from bluetti_venus_gateway.bluetti.polling import PollSpec
from bluetti_venus_gateway.services.collector import LiveMqttCollector


class FakeClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes, int]] = []

    def publish(self, topic: str, payload: bytes, qos: int = 0) -> None:
        self.published.append((topic, payload, qos))


class CollectorSequentialPollingTests(unittest.TestCase):
    def test_publishes_next_poll_only_after_matching_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            collector = self._collector(
                Path(tmp_dir),
                [
                    PollSpec("home", 100, 92, 1),
                    PollSpec("grid", 1300, 19, 1),
                    PollSpec("load", 1400, 36, 1),
                ],
            )

            collector._drive_polling(100.0)
            self.assertEqual(self._published_addrs(collector), [100])

            collector._on_message(None, None, SimpleNamespace(payload=self._response_payload(1300)))
            self.assertEqual(self._published_addrs(collector), [100])

            collector._on_message(None, None, SimpleNamespace(payload=self._response_payload(100)))
            self.assertEqual(self._published_addrs(collector), [100, 1300])

            collector._on_message(None, None, SimpleNamespace(payload=self._response_payload(1300)))
            self.assertEqual(self._published_addrs(collector), [100, 1300, 1400])

    def test_timeout_advances_to_next_queued_poll(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            collector = self._collector(
                Path(tmp_dir),
                [
                    PollSpec("home", 100, 92, 1),
                    PollSpec("grid", 1300, 19, 1),
                ],
            )

            collector._drive_polling(100.0)
            collector._drive_polling(104.9)
            self.assertEqual(self._published_addrs(collector), [100])

            with self.assertLogs("bluetti_venus_gateway.services.collector", level="WARNING"):
                collector._drive_polling(105.0)
            self.assertEqual(self._published_addrs(collector), [100, 1300])

    def _collector(self, run_dir: Path, poll_specs: list[PollSpec]) -> LiveMqttCollector:
        collector = LiveMqttCollector.__new__(LiveMqttCollector)
        collector._config = SimpleNamespace(
            poll_interval_seconds=5,
            mqtt_payload_format="new",
            run_dir=run_dir,
            snapshot_path=run_dir / "latest.json",
            stale_after_seconds=20,
            device_sn="PBOXTEST",
        )
        collector._context = SimpleNamespace(modbus_slave=1, publish_topic="SUB/test")
        collector._client = FakeClient()
        collector._poll_specs = poll_specs
        collector._decoded_state = {}
        collector._last_observed_at = None
        collector._connected = True
        collector._cycle = 0
        collector._poll_queue = deque()
        collector._inflight_poll = None
        collector._inflight_started_monotonic = None
        collector._next_cycle_monotonic = 0.0
        collector._next_snapshot_write_monotonic = 0.0
        collector._poll_lock = threading.RLock()
        return collector

    def _published_addrs(self, collector: LiveMqttCollector) -> list[int]:
        return [int.from_bytes(payload[3:5], "big") for _topic, payload, _qos in collector._client.published]

    def _response_payload(self, addr: int) -> bytes:
        wrapper = b"\x01\xf8\x0f" + addr.to_bytes(2, "big") + b"\x00\x00\x00\x00\x00"
        modbus = b"\x01\x03\x00\x00\x00"
        return wrapper + modbus


if __name__ == "__main__":
    unittest.main()
