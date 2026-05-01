from __future__ import annotations

import unittest

from bluetti_venus_gateway.bluetti.parser import normalize_decoded_state


class ParserTests(unittest.TestCase):
    def test_normalize_decoded_state_projects_vrm_signals(self) -> None:
        snapshot = normalize_decoded_state(
            {
                "homeInfo": {
                    "deviceSN": "EP760SN",
                    "packTotalSoc": 80,
                    "packTotalVoltage": 52.5,
                    "packTotalCurrent": -10.0,
                },
                "invGridInfo": {
                    "frequency": 50.0,
                    "phaseList": [{"gridVoltage": 231.0, "gridCurrent": 4.0, "gridPower": 924}],
                },
                "invLoadInfo": {
                    "phaseList": [{"loadVoltage": 230.0, "loadCurrent": 2.0, "loadPower": 460}],
                },
            }
        )

        self.assertEqual(snapshot["device_sn"], "EP760SN")
        self.assertEqual(snapshot["soc"], 80)
        self.assertEqual(snapshot["battery_voltage_v"], 52.5)
        self.assertEqual(snapshot["grid_voltage_v"], 231.0)
        self.assertEqual(snapshot["load_current_a"], 2.0)


if __name__ == "__main__":
    unittest.main()
