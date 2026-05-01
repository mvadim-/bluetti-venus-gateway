from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bluetti_venus_gateway.tools.status import _read_first_existing


class StatusTests(unittest.TestCase):
    def test_read_first_existing_returns_first_non_empty_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            version_path = Path(temp_dir) / "version"
            version_path.write_text("\n v3.72\nVictron Energy\n20260329202208\n", encoding="utf-8")

            self.assertEqual(_read_first_existing([str(version_path)]), "v3.72")


if __name__ == "__main__":
    unittest.main()

