from __future__ import annotations

import unittest

from bluetti_venus_gateway.victron.bridge_model import VenusBridgeSettings
from bluetti_venus_gateway.victron.bridge_model import build_venus_bridge_payload
from bluetti_venus_gateway.victron.bridge_model import iter_venus_service_payloads


class BridgeModelTests(unittest.TestCase):
    def test_build_venus_bridge_payload_publishes_required_v1_services(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {
                    "soc": 76,
                    "battery_voltage_v": 52.1,
                    "battery_current_a": -12.4,
                    "pack_avg_temp_c": 24.0,
                    "grid_voltage_v": 231.0,
                    "grid_current_a": 4.2,
                    "grid_freq_hz": 50.0,
                    "grid_power_w": 920,
                    "grid_charge_energy_total_kwh": 123.4,
                    "ac_load_power_w": 650,
                    "ac_energy_kwh": 56.7,
                    "inv_output_power_w": 0,
                    "load_voltage_v": 230.0,
                    "load_current_a": 2.8,
                },
            },
            settings=VenusBridgeSettings(),
        )

        self.assertEqual(payload["venus_battery"]["service_name"], "com.victronenergy.battery.ep760_41")
        self.assertEqual(payload["venus_grid"]["service_name"], "com.victronenergy.grid.ep760_30")
        self.assertEqual(payload["venus_ac_load"]["service_name"], "com.victronenergy.acload.ep760_31")
        self.assertEqual(payload["venus_inverter"]["service_name"], "com.victronenergy.inverter.ep760_32")
        self.assertEqual(payload["venus_multi"]["service_name"], "com.victronenergy.multi.ep760_32")
        self.assertNotIn("venus_vebus", payload)
        self.assertEqual(payload["venus_battery"]["values"]["/Soc"], 76.0)
        self.assertEqual(payload["venus_battery"]["values"]["/State"], 9)
        self.assertEqual(payload["venus_battery"]["values"]["/Dc/0/Power"], -646.04)
        self.assertEqual(payload["venus_grid"]["values"]["/Ac/L1/Power"], 920.0)
        self.assertEqual(payload["venus_grid"]["values"]["/Ac/L1/Energy/Forward"], 123.4)
        self.assertEqual(payload["venus_ac_load"]["values"]["/Ac/L1/Current"], 2.8)
        self.assertEqual(payload["venus_ac_load"]["values"]["/Ac/L1/Energy/Forward"], 56.7)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/ActiveIn/ActiveInput"], 0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/ActiveIn/Connected"], 1)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/ActiveIn/L1/P"], 920.0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/In/1/Type"], 1)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/In/1/L1/I"], 4.2)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/In/1/L1/P"], 920.0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/Out/L1/P"], 650.0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/Out/L1/I"], 2.8)
        self.assertEqual(payload["venus_inverter"]["values"]["/Soc"], 76.0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Dc/0/Temperature"], 24.0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Mode"], 3)
        self.assertEqual(payload["venus_inverter"]["values"]["/State"], 8)
        self.assertEqual(payload["venus_multi"]["values"]["/Ac/In/1/L1/P"], 920.0)
        self.assertIsNone(payload["venus_multi"]["values"]["/Ac/Out/L1/P"])
        self.assertIsNone(payload["venus_multi"]["values"]["/Ac/Out/L1/I"])
        self.assertIsNone(payload["venus_multi"]["values"]["/Ac/Out/L1/S"])
        self.assertEqual(payload["venus_multi"]["values"]["/Soc"], 76.0)
        self.assertEqual(payload["venus_multi"]["values"]["/Dc/0/Temperature"], 24.0)
        self.assertEqual(payload["venus_multi"]["values"]["/State"], 8)

    def test_build_venus_bridge_payload_marks_inverter_state_when_output_power_is_real(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {
                    "battery_voltage_v": 103.4,
                    "inv_output_power_w": 420.0,
                    "inv_output_voltage_v": 230.0,
                    "inv_output_current_a": 1.8,
                    "inv_output_freq_hz": 50.0,
                },
            },
            settings=VenusBridgeSettings(),
        )

        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/Out/L1/P"], 420.0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/Out/L1/I"], 1.8)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/ActiveIn/ActiveInput"], 0xF0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/ActiveIn/Connected"], 0)
        self.assertEqual(payload["venus_inverter"]["values"]["/State"], 9)
        self.assertEqual(payload["venus_multi"]["values"]["/Ac/ActiveIn/ActiveInput"], 0xF0)
        self.assertIsNone(payload["venus_multi"]["values"]["/Ac/Out/L1/P"])
        self.assertIsNone(payload["venus_multi"]["values"]["/Ac/Out/L1/S"])
        self.assertEqual(payload["venus_multi"]["values"]["/State"], 9)

    def test_build_venus_bridge_payload_does_not_publish_charging_power_as_ac_load(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {
                    "soc": 97.0,
                    "battery_voltage_v": 105.0,
                    "battery_current_a": 18.4,
                    "grid_power_w": 2462.0,
                    "grid_voltage_v": 231.0,
                    "grid_freq_hz": 49.9,
                    "inv_output_power_w": -1432.0,
                    "inv_output_voltage_v": 231.0,
                    "inv_output_current_a": 6.2,
                    "inv_output_freq_hz": 49.9,
                },
            },
            settings=VenusBridgeSettings(),
        )

        self.assertEqual(payload["venus_inverter"]["values"]["/State"], 3)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/Out/L1/P"], 0.0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Ac/Out/L1/I"], 0.0)
        self.assertEqual(payload["venus_multi"]["values"]["/State"], 3)
        self.assertIsNone(payload["venus_multi"]["values"]["/Ac/Out/L1/P"])
        self.assertIsNone(payload["venus_multi"]["values"]["/Ac/Out/L1/I"])
        self.assertIsNone(payload["venus_multi"]["values"]["/Ac/Out/L1/S"])
        self.assertEqual(payload["venus_multi"]["values"]["/Dc/0/Power"], 1932.0)

    def test_multi_carries_ac_output_when_native_inverter_service_is_disabled(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {
                    "grid_power_w": 420.0,
                    "grid_voltage_v": 230.0,
                    "ac_load_power_w": 418.0,
                    "load_voltage_v": 231.0,
                    "load_current_a": 1.8,
                },
            },
            settings=VenusBridgeSettings(enable_inverter_service=False),
        )

        self.assertNotIn("venus_inverter", payload)
        self.assertEqual(payload["venus_multi"]["values"]["/Ac/Out/L1/P"], 418.0)
        self.assertEqual(payload["venus_multi"]["values"]["/Ac/Out/L1/I"], 1.8)

    def test_build_venus_bridge_payload_can_include_vebus_compat(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {
                    "soc": 88.0,
                    "battery_voltage_v": 103.0,
                    "grid_power_w": 100.0,
                    "grid_voltage_v": 230.0,
                    "load_voltage_v": 230.0,
                    "ac_load_power_w": 460.0,
                    "inv_output_power_w": 0.0,
                },
            },
            settings=VenusBridgeSettings(enable_vebus_compat=True),
        )

        self.assertEqual(payload["venus_vebus"]["service_name"], "com.victronenergy.vebus.ep760_32")
        self.assertEqual(payload["venus_vebus"]["values"]["/State"], 8)
        self.assertEqual(payload["venus_vebus"]["values"]["/Mode"], 3)
        self.assertEqual(payload["venus_vebus"]["values"]["/Soc"], 88.0)
        self.assertEqual(payload["venus_vebus"]["values"]["/Ac/In/1/Type"], 1)
        self.assertEqual(payload["venus_vebus"]["values"]["/Ac/In/1/L1/P"], 100.0)
        self.assertEqual(payload["venus_vebus"]["values"]["/Ac/Out/L1/P"], 460.0)
        self.assertEqual(payload["venus_vebus"]["values"]["/Ac/Out/L1/I"], 2.0)

    def test_build_venus_bridge_payload_marks_stale_disconnected(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "stale", "age_seconds": 120},
                "snapshot": {"soc": 76, "grid_power_w": 920, "ac_load_power_w": 650},
            },
            settings=VenusBridgeSettings(),
        )

        self.assertEqual(payload["venus_battery"]["values"]["/Connected"], 0)
        self.assertEqual(payload["venus_grid"]["values"]["/Connected"], 0)
        self.assertEqual(payload["venus_ac_load"]["values"]["/Connected"], 0)
        self.assertEqual(payload["venus_inverter"]["values"]["/Connected"], 0)

    def test_build_venus_bridge_payload_uses_battery_lifecycle_state(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {
                    "soc": 80,
                    "battery_voltage_v": 104.0,
                    "battery_current_a": -3.0,
                },
            },
            settings=VenusBridgeSettings(),
        )

        self.assertEqual(payload["venus_battery"]["values"]["/Connected"], 1)
        self.assertEqual(payload["venus_battery"]["values"]["/State"], 9)

    def test_build_venus_bridge_payload_does_not_raise_unconfigured_voltage_alarms(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {"battery_voltage_v": 105.2, "battery_current_a": 18.1, "soc": 97},
            },
            settings=VenusBridgeSettings(),
        )

        self.assertEqual(payload["venus_battery"]["values"]["/Alarms/HighVoltage"], 0)
        self.assertEqual(payload["venus_battery"]["values"]["/Alarms/LowVoltage"], 0)
        self.assertEqual(payload["venus_battery"]["values"]["/Alarms/HighTemperature"], 0)
        self.assertEqual(payload["venus_battery"]["values"]["/Alarms/LowTemperature"], 0)

    def test_build_venus_bridge_payload_raises_configured_temperature_alarms(self) -> None:
        high_payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {"soc": 76, "pack_avg_temp_c": 46.0},
            },
            settings=VenusBridgeSettings(battery_low_temp_alarm_c=0.0, battery_high_temp_alarm_c=45.0),
        )
        low_payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {"soc": 76, "pack_avg_temp_c": -1.0},
            },
            settings=VenusBridgeSettings(battery_low_temp_alarm_c=0.0, battery_high_temp_alarm_c=45.0),
        )

        self.assertEqual(high_payload["venus_battery"]["values"]["/Alarms/HighTemperature"], 2)
        self.assertEqual(high_payload["venus_battery"]["values"]["/Alarms/LowTemperature"], 0)
        self.assertEqual(low_payload["venus_battery"]["values"]["/Alarms/HighTemperature"], 0)
        self.assertEqual(low_payload["venus_battery"]["values"]["/Alarms/LowTemperature"], 2)

    def test_iter_venus_service_payloads_skips_missing_optional_vebus(self) -> None:
        payload = build_venus_bridge_payload(
            {"device_sn": "EP760SN", "snapshot": {"soc": 76}},
            settings=VenusBridgeSettings(),
        )

        self.assertEqual(
            [service_name for service_name, _ in iter_venus_service_payloads(payload)],
            [
                "com.victronenergy.battery.ep760_41",
                "com.victronenergy.grid.ep760_30",
                "com.victronenergy.acload.ep760_31",
                "com.victronenergy.inverter.ep760_32",
                "com.victronenergy.multi.ep760_32",
            ],
        )

    def test_bridge_payload_includes_vrm_and_systemcalc_contract_paths(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {
                    "soc": 100,
                    "battery_voltage_v": 103.0,
                    "battery_current_a": 0.0,
                    "pack_avg_temp_c": 21.0,
                    "grid_voltage_v": 230.0,
                    "grid_current_a": 2.0,
                    "grid_freq_hz": 50.0,
                    "grid_power_w": 460.0,
                    "grid_charge_energy_total_kwh": 2383.0,
                    "grid_feedback_energy_total_kwh": 9.8,
                    "ac_load_power_w": 455.0,
                    "load_voltage_v": 231.0,
                    "load_current_a": 1.97,
                    "ac_energy_kwh": 2048.0,
                    "inv_output_power_w": 0.0,
                    "inv_output_voltage_v": 231.0,
                    "inv_output_freq_hz": 50.0,
                },
            },
            settings=VenusBridgeSettings(enable_vebus_compat=True),
        )

        expected_paths = {
            "venus_battery": {
                "/Connected",
                "/Soc",
                "/State",
                "/Dc/0/Voltage",
                "/Dc/0/Current",
                "/Dc/0/Power",
                "/Dc/0/Temperature",
                "/Alarms/LowVoltage",
                "/Alarms/HighVoltage",
                "/Alarms/LowSoc",
                "/Alarms/LowTemperature",
                "/Alarms/HighTemperature",
            },
            "venus_grid": {
                "/Ac/L1/Power",
                "/Ac/L1/Voltage",
                "/Ac/L1/Current",
                "/Ac/Frequency",
                "/Ac/L1/Energy/Forward",
                "/Ac/L1/Energy/Reverse",
                "/Ac/Energy/Forward",
                "/Ac/Energy/Reverse",
            },
            "venus_ac_load": {
                "/Position",
                "/Ac/L1/Power",
                "/Ac/L1/Voltage",
                "/Ac/L1/Current",
                "/Ac/Frequency",
                "/Ac/L1/Energy/Forward",
                "/Ac/Energy/Forward",
            },
            "venus_inverter": {
                "/Mode",
                "/State",
                "/Soc",
                "/Dc/0/Voltage",
                "/Dc/0/Current",
                "/Dc/0/Power",
                "/Dc/0/Temperature",
                "/Ac/ActiveIn/ActiveInput",
                "/Ac/In/1/Type",
                "/Ac/In/1/L1/P",
                "/Ac/In/1/L1/I",
                "/Ac/In/1/L1/F",
                "/Ac/Out/L1/P",
                "/Ac/Out/L1/I",
                "/Ac/Out/L1/V",
                "/Ac/Out/L1/F",
            },
            "venus_multi": {
                "/Mode",
                "/State",
                "/Soc",
                "/Dc/0/Voltage",
                "/Dc/0/Current",
                "/Dc/0/Power",
                "/Dc/0/Temperature",
                "/Ac/ActiveIn/ActiveInput",
                "/Ac/In/1/Type",
                "/Ac/In/1/L1/P",
                "/Ac/In/1/L1/I",
                "/Ac/In/1/L1/F",
                "/Ac/Out/L1/P",
                "/Ac/Out/L1/I",
                "/Ac/Out/L1/V",
                "/Ac/Out/L1/F",
            },
            "venus_vebus": {
                "/Mode",
                "/State",
                "/Soc",
                "/Dc/0/Voltage",
                "/Dc/0/Current",
                "/Dc/0/Power",
                "/Dc/0/Temperature",
                "/Ac/ActiveIn/ActiveInput",
                "/Ac/In/1/Type",
                "/Ac/In/1/L1/P",
                "/Ac/In/1/L1/I",
                "/Ac/In/1/L1/F",
                "/Ac/Out/L1/P",
                "/Ac/Out/L1/I",
                "/Ac/Out/L1/V",
            },
        }

        for key, paths in expected_paths.items():
            with self.subTest(service=key):
                self.assertTrue(paths.issubset(payload[key]["values"]))


if __name__ == "__main__":
    unittest.main()
