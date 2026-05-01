from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


class SnapshotStoreError(RuntimeError):
    pass


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        temp_path = Path(handle.name)
    temp_path.replace(path)


def read_snapshot(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotStoreError(f"snapshot missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SnapshotStoreError(f"snapshot invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SnapshotStoreError(f"snapshot root must be an object: {path}")
    return payload

