from __future__ import annotations

import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
import tempfile
import unittest

from bluetti_venus_gateway.telemetry.core import build_snapshot_envelope
from bluetti_venus_gateway.telemetry.snapshot_store import atomic_write_json
from bluetti_venus_gateway.telemetry.snapshot_store import read_snapshot


class SnapshotStoreTests(unittest.TestCase):
    def test_atomic_write_json_replaces_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "latest.json"

            atomic_write_json(path, {"value": 1})
            atomic_write_json(path, {"value": 2})

            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"value": 2})
            self.assertEqual(read_snapshot(path), {"value": 2})

    def test_build_snapshot_envelope_marks_freshness(self) -> None:
        envelope = build_snapshot_envelope(
            device_sn="EP760SN",
            snapshot={"soc": 76},
            observed_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
            received_at=datetime(2026, 5, 1, 12, 0, 5, tzinfo=timezone.utc),
            stale_after_seconds=20,
        )

        self.assertEqual(envelope["schema_version"], 1)
        self.assertEqual(envelope["device_sn"], "EP760SN")
        self.assertEqual(envelope["freshness"], {"state": "fresh", "age_seconds": 5.0})
        self.assertEqual(envelope["snapshot"], {"soc": 76})

    def test_build_snapshot_envelope_marks_stale(self) -> None:
        envelope = build_snapshot_envelope(
            device_sn="EP760SN",
            snapshot={"soc": 76},
            observed_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
            received_at=datetime(2026, 5, 1, 12, 0, 30, tzinfo=timezone.utc),
            stale_after_seconds=20,
        )

        self.assertEqual(envelope["freshness"]["state"], "stale")


if __name__ == "__main__":
    unittest.main()
