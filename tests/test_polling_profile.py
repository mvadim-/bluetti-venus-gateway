from __future__ import annotations

import unittest

from bluetti_venus_gateway.bluetti.polling import build_poll_profile
from bluetti_venus_gateway.bluetti.polling import due_polls


class PollingProfileTests(unittest.TestCase):
    def test_vrm_minimal_profile_contains_required_v1_streams(self) -> None:
        specs = build_poll_profile("vrm-minimal")

        self.assertEqual(
            [(spec.addr, spec.every) for spec in specs],
            [
                (100, 1),
                (1300, 1),
                (1400, 1),
                (1500, 2),
            ],
        )

    def test_vrm_minimal_profile_keeps_future_streams_disabled_by_default(self) -> None:
        addrs = {spec.addr for spec in build_poll_profile("vrm-minimal")}

        self.assertNotIn(1200, addrs)
        self.assertNotIn(6000, addrs)
        self.assertNotIn(6100, addrs)

    def test_vrm_minimal_profile_enables_optional_future_streams(self) -> None:
        addrs = {
            spec.addr
            for spec in build_poll_profile(
                "vrm-minimal",
                enable_pv=True,
                enable_pack_diagnostics=True,
            )
        }

        self.assertTrue({1200, 6000, 6100}.issubset(addrs))

    def test_due_polls_respects_cycle_frequency(self) -> None:
        specs = build_poll_profile("vrm-minimal")

        self.assertEqual([spec.addr for spec in due_polls(specs, 1)], [100, 1300, 1400])
        self.assertEqual([spec.addr for spec in due_polls(specs, 2)], [100, 1300, 1400, 1500])

    def test_unknown_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported"):
            build_poll_profile("ep760-full")


if __name__ == "__main__":
    unittest.main()
