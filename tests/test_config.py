from __future__ import annotations

from pathlib import Path
import unittest

from bluetti_venus_gateway.config import ConfigError
from bluetti_venus_gateway.config import load_config
from bluetti_venus_gateway.config import masked_config
from bluetti_venus_gateway.config import parse_env_file


class ConfigTests(unittest.TestCase):
    def test_load_config_parses_required_values(self) -> None:
        with self.subTest():
            import tempfile

            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "bluetti-gateway.env"
                config_path.write_text(
                    "\n".join(
                        [
                            "BLUETTI_EMAIL=user@example.com",
                            "BLUETTI_PASSWORD=secret",
                            "BLUETTI_DEVICE_SN=EP760SN",
                            "BLUETTI_ENABLE_PV=1",
                            "BLUETTI_ENABLE_PACK_DIAGNOSTICS=false",
                            "BLUETTI_POLL_INTERVAL_SECONDS=7",
                        ]
                    ),
                    encoding="utf-8",
                )

                config = load_config(config_path)

                self.assertEqual(config.email, "user@example.com")
                self.assertEqual(config.password, "secret")
                self.assertEqual(config.device_sn, "EP760SN")
                self.assertIs(config.enable_pv, True)
                self.assertIs(config.enable_pack_diagnostics, False)
                self.assertEqual(config.poll_interval_seconds, 7)
                self.assertEqual(config.mqtt_client_id, "bluetti-venus-gateway")
                self.assertEqual(config.mqtt_payload_format, "new")
                self.assertIs(config.mqtt_tls_verify_server, False)

    def test_load_config_can_enable_mqtt_tls_server_verification(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "bluetti-gateway.env"
            config_path.write_text(
                "\n".join(
                    [
                        "BLUETTI_EMAIL=user@example.com",
                        "BLUETTI_PASSWORD=secret",
                        "BLUETTI_DEVICE_SN=EP760SN",
                        "BLUETTI_MQTT_TLS_VERIFY_SERVER=1",
                    ]
                ),
                encoding="utf-8",
            )

            self.assertIs(load_config(config_path).mqtt_tls_verify_server, True)

    def test_load_config_rejects_missing_required_values(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "bluetti-gateway.env"
            config_path.write_text("BLUETTI_EMAIL=user@example.com\n", encoding="utf-8")

            with self.assertRaisesRegex(ConfigError, "BLUETTI_PASSWORD"):
                load_config(config_path)

    def test_load_config_rejects_template_values(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "bluetti-gateway.env"
            config_path.write_text(
                "\n".join(
                    [
                        "BLUETTI_EMAIL=your-email@example.com",
                        "BLUETTI_PASSWORD=your-password",
                        "BLUETTI_DEVICE_SN=your-device-sn",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ConfigError, "replace template"):
                load_config(config_path)

    def test_parse_env_file_strips_quotes(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "bluetti-gateway.env"
            config_path.write_text('BLUETTI_PASSWORD="secret value"\n', encoding="utf-8")

            self.assertEqual(parse_env_file(config_path)["BLUETTI_PASSWORD"], "secret value")

    def test_masked_config_hides_secrets(self) -> None:
        self.assertEqual(
            masked_config({"BLUETTI_PASSWORD": "secret", "BLUETTI_EMAIL": "user@example.com"}),
            {
                "BLUETTI_PASSWORD": "***",
                "BLUETTI_EMAIL": "user@example.com",
            },
        )


if __name__ == "__main__":
    unittest.main()
