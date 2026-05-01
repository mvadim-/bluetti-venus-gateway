from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from bluetti_venus_gateway.bluetti.auth import generate_totp
from bluetti_venus_gateway.bluetti.auth import normalize_password_hash
from bluetti_venus_gateway.bluetti.auth import _coerce_int
from bluetti_venus_gateway.bluetti.auth import _path_or_default_ca
from bluetti_venus_gateway.bluetti.auth import _try_run_pkcs12_with_fallbacks


class AuthTests(unittest.TestCase):
    def test_normalize_password_hash_hashes_plain_password(self) -> None:
        self.assertEqual(
            normalize_password_hash("password"),
            "5E884898DA28047151D0E56F8DC6292773603D0D6AABBDD62A11EF721D1542D8",
        )

    def test_normalize_password_hash_keeps_existing_sha256_digest(self) -> None:
        digest = "5e884898da28047151d0e56f8dc6292773603d0d6aabbbdd62a11ef721d1542d"

        self.assertEqual(normalize_password_hash(digest), digest.upper())

    def test_generate_totp_is_stable_for_same_inputs(self) -> None:
        self.assertEqual(generate_totp("user-id", "device-id", 1710000000000), "60922689")

    def test_coerce_int_accepts_numeric_utc_string(self) -> None:
        self.assertEqual(_coerce_int("1777630585000"), 1777630585000)
        self.assertIsNone(_coerce_int("not-a-number"))

    def test_pkcs12_fallback_runner_returns_false_for_missing_file(self) -> None:
        self.assertFalse(_try_run_pkcs12_with_fallbacks(Path("/missing.p12"), "secret", []))

    def test_path_or_default_ca_prefers_nonempty_extracted_ca(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ca_path = Path(directory) / "ca.crt"
            ca_path.write_text("certificate", encoding="utf-8")

            self.assertEqual(_path_or_default_ca(ca_path), ca_path)


if __name__ == "__main__":
    unittest.main()
