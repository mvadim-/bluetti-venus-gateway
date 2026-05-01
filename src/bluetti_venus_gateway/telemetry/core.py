from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any


SCHEMA_VERSION = 1


def build_snapshot_envelope(
    *,
    device_sn: str,
    snapshot: dict[str, Any],
    observed_at: datetime | None = None,
    received_at: datetime | None = None,
    stale_after_seconds: int = 20,
) -> dict[str, Any]:
    observed = ensure_aware_utc(observed_at or datetime.now(timezone.utc))
    received = ensure_aware_utc(received_at or datetime.now(timezone.utc))
    age_seconds = max(0.0, (received - observed).total_seconds())
    return {
        "schema_version": SCHEMA_VERSION,
        "device_sn": device_sn,
        "observed_at": observed.isoformat(),
        "received_at": received.isoformat(),
        "freshness": {
            "state": "fresh" if age_seconds <= stale_after_seconds else "stale",
            "age_seconds": round(age_seconds, 3),
        },
        "snapshot": dict(snapshot),
    }


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_iso8601(raw_value: str) -> datetime:
    normalized = raw_value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)

