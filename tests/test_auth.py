from __future__ import annotations

import unittest

from bluetti_venus_gateway.bluetti.auth import generate_totp
from bluetti_venus_gateway.bluetti.auth import normalize_password_hash


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


if __name__ == "__main__":
    unittest.main()
