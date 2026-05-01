from __future__ import annotations

import unittest

from bluetti_venus_gateway.bluetti.parser import normalize_decoded_state
from bluetti_venus_gateway.bluetti.parser import parse_inv_grid_info_data


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

    def test_parse_inv_grid_info_data_projects_first_phase(self) -> None:
        data = bytearray(38)
        data[0:2] = (500).to_bytes(2, "big")
        data[25] = 1
        data[26:28] = (924).to_bytes(2, "big", signed=True)
        data[28:30] = (2310).to_bytes(2, "big")
        data[30:32] = (40).to_bytes(2, "big", signed=True)
        data[32:34] = (930).to_bytes(2, "big", signed=True)

        parsed = parse_inv_grid_info_data(bytes(data))

        self.assertEqual(parsed["gridFreq"], 50.0)
        self.assertEqual(parsed["gridPower"], 924)
        self.assertEqual(parsed["gridVoltage"], 231.0)
        self.assertEqual(parsed["gridCurrent"], 4.0)


if __name__ == "__main__":
    unittest.main()
