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
                    "grid_voltage_v": 231.0,
                    "grid_current_a": 4.2,
                    "grid_freq_hz": 50.0,
                    "grid_power_w": 920,
                    "ac_load_power_w": 650,
                    "load_voltage_v": 230.0,
                    "load_current_a": 2.8,
                },
            },
            settings=VenusBridgeSettings(),
        )

        self.assertEqual(payload["venus_battery"]["service_name"], "com.victronenergy.battery.ep760_41")
        self.assertEqual(payload["venus_grid"]["service_name"], "com.victronenergy.grid.ep760_30")
        self.assertEqual(payload["venus_ac_load"]["service_name"], "com.victronenergy.acload.ep760_31")
        self.assertNotIn("venus_vebus", payload)
        self.assertEqual(payload["venus_battery"]["values"]["/Soc"], 76.0)
        self.assertEqual(payload["venus_battery"]["values"]["/Dc/0/Power"], -646.04)
        self.assertEqual(payload["venus_grid"]["values"]["/Ac/L1/Power"], 920.0)
        self.assertEqual(payload["venus_ac_load"]["values"]["/Ac/L1/Current"], 2.8)

    def test_build_venus_bridge_payload_can_include_vebus_compat(self) -> None:
        payload = build_venus_bridge_payload(
            {
                "device_sn": "EP760SN",
                "freshness": {"state": "fresh", "age_seconds": 2},
                "snapshot": {"grid_power_w": 100.0, "load_voltage_v": 230.0, "ac_load_power_w": 460.0},
            },
            settings=VenusBridgeSettings(enable_vebus_compat=True),
        )

        self.assertEqual(payload["venus_vebus"]["service_name"], "com.victronenergy.vebus.ep760_32")
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
            ],
        )


if __name__ == "__main__":
    unittest.main()
