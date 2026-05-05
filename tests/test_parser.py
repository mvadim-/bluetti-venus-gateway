from __future__ import annotations

import unittest

from bluetti_venus_gateway.bluetti.parser import decode_bluetti_payload
from bluetti_venus_gateway.bluetti.parser import normalize_decoded_state
from bluetti_venus_gateway.bluetti.parser import parse_pack_item_info_data
from bluetti_venus_gateway.bluetti.parser import parse_pack_main_info_data
from bluetti_venus_gateway.bluetti.parser import parse_inv_grid_info_data
from bluetti_venus_gateway.bluetti.parser import parse_inv_inv_info_data


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
                "packMainInfo": {
                    "totalSOC": 81,
                    "totalSOH": 99,
                    "averageTemp": 24.0,
                    "totalVoltage": 105.1,
                    "totalCurrent": -4.2,
                    "packCnts": 2,
                },
            }
        )

        self.assertEqual(snapshot["device_sn"], "EP760SN")
        self.assertEqual(snapshot["soc"], 80)
        self.assertEqual(snapshot["battery_voltage_v"], 52.5)
        self.assertEqual(snapshot["grid_voltage_v"], 231.0)
        self.assertEqual(snapshot["load_current_a"], 2.0)
        self.assertEqual(snapshot["pack_avg_temp_c"], 24.0)
        self.assertEqual(snapshot["pack_total_current_a"], -4.2)

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

    def test_parse_inv_inv_info_data_decodes_signed_phase_power(self) -> None:
        data = bytearray(30)
        data[0:2] = (500).to_bytes(2, "big")
        data[17] = 1
        data[19] = 1
        data[20:22] = (-1432).to_bytes(2, "big", signed=True)
        data[22:24] = (2310).to_bytes(2, "big")
        data[24:26] = (62).to_bytes(2, "big")

        parsed = parse_inv_inv_info_data(bytes(data))

        self.assertEqual(parsed["phase1InvPower"], -1432)
        self.assertEqual(parsed["phase1InvVoltage"], 231.0)
        self.assertEqual(parsed["phase1InvCurrent"], 6.2)

    def test_parse_pack_main_info_data_decodes_aggregate_battery_diagnostics(self) -> None:
        data = bytearray(84)
        data[0:2] = (82).to_bytes(2, "big")
        data[2:4] = (99).to_bytes(2, "big")
        data[4:6] = (245).to_bytes(2, "big", signed=True)
        data[6:8] = (1053).to_bytes(2, "big")
        data[8:10] = (-37).to_bytes(2, "big", signed=True)
        data[10:12] = (2).to_bytes(2, "big")

        parsed = parse_pack_main_info_data(bytes(data))

        self.assertEqual(parsed["totalSOC"], 82)
        self.assertEqual(parsed["totalSOH"], 99)
        self.assertEqual(parsed["averageTemp"], 24.5)
        self.assertEqual(parsed["totalVoltage"], 105.3)
        self.assertEqual(parsed["totalCurrent"], -3.7)
        self.assertEqual(parsed["packCnts"], 2)

    def test_decode_bluetti_payload_routes_pack_diagnostics_by_wrapper_addr(self) -> None:
        data = bytearray(84)
        data[4:6] = (245).to_bytes(2, "big", signed=True)
        modbus = bytes([1, 3, len(data)]) + bytes(data) + bytes(2)
        payload = bytes.fromhex("01F80F17700000000000") + modbus

        decoded = decode_bluetti_payload(payload)

        self.assertEqual(decoded["messageType"], "packMainInfo")
        self.assertEqual(decoded["packMainInfo"]["averageTemp"], 24.5)

    def test_parse_pack_item_info_data_decodes_pack_temperature_fallback(self) -> None:
        data = bytearray(208)
        data[0:2] = (1).to_bytes(2, "big")
        data[2:18] = bytes([ord("P"), ord("A"), ord("C"), ord("K"), ord("S"), ord("N"), ord("0"), ord("1")]) + bytes(8)
        data[18:20] = (81).to_bytes(2, "big")
        data[20:22] = (98).to_bytes(2, "big")
        data[22:24] = (526).to_bytes(2, "big")
        data[24:26] = (12).to_bytes(2, "big", signed=True)
        data[26:28] = (23).to_bytes(2, "big", signed=True)

        parsed = parse_pack_item_info_data(bytes(data))

        self.assertEqual(parsed["packID"], 1)
        self.assertEqual(parsed["packSN"], "APKCNS10")
        self.assertEqual(parsed["packSoc"], 81)
        self.assertEqual(parsed["packSoh"], 98)
        self.assertEqual(parsed["voltage"], 52.6)
        self.assertEqual(parsed["current"], 1.2)
        self.assertEqual(parsed["averageTemp"], 23.0)


if __name__ == "__main__":
    unittest.main()
