from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


DEFAULT_CONFIG_PATH = Path("/data/bluetti-gateway/bluetti-gateway.env")
DEFAULT_DATA_DIR = Path("/data/bluetti-gateway")
DEFAULT_RUN_DIR = Path("/run/bluetti-gateway")

SECRET_KEYS = {
    "BLUETTI_PASSWORD",
    "BLUETTI_ACCESS_TOKEN",
    "BLUETTI_MQTT_PASSWORD",
    "BLUETTI_IOT_CONN_SECRET",
}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class GatewayConfig:
    environment: str
    log_level: str
    region: str
    email: str
    password: str
    device_sn: str
    poll_profile: str
    poll_interval_seconds: int
    stale_after_seconds: int
    enable_pv: bool
    enable_pack_diagnostics: bool
    enable_vebus_compat: bool
    battery_device_instance: int
    grid_device_instance: int
    acload_device_instance: int
    battery_custom_name: str
    grid_custom_name: str
    acload_custom_name: str
    auth_device_id: str
    mqtt_client_id: str
    mqtt_payload_format: str
    mqtt_ciphers: str
    data_dir: Path = DEFAULT_DATA_DIR
    run_dir: Path = DEFAULT_RUN_DIR

    @property
    def snapshot_path(self) -> Path:
        return self.run_dir / "latest.json"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def certs_dir(self) -> Path:
        return self.data_dir / "certs"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"{path}:{line_number}: expected KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise ConfigError(f"{path}:{line_number}: empty key")
        values[key] = _strip_optional_quotes(value.strip())
    return values


def load_config(path: Path = DEFAULT_CONFIG_PATH, env: Mapping[str, str] | None = None) -> GatewayConfig:
    file_values = parse_env_file(path)
    merged = dict(file_values)
    if env:
        merged.update({key: value for key, value in env.items() if key.startswith("BLUETTI_")})

    missing = [
        key
        for key in ("BLUETTI_EMAIL", "BLUETTI_PASSWORD", "BLUETTI_DEVICE_SN")
        if not merged.get(key)
    ]
    if missing:
        raise ConfigError("missing required config keys: " + ", ".join(missing))
    _reject_template_values(merged)

    return GatewayConfig(
        environment=merged.get("BLUETTI_GATEWAY_ENV", "production"),
        log_level=merged.get("BLUETTI_LOG_LEVEL", "INFO").upper(),
        region=merged.get("BLUETTI_REGION", "de"),
        email=merged["BLUETTI_EMAIL"],
        password=merged["BLUETTI_PASSWORD"],
        device_sn=merged["BLUETTI_DEVICE_SN"],
        poll_profile=merged.get("BLUETTI_POLL_PROFILE", "vrm-minimal"),
        poll_interval_seconds=_positive_int(merged.get("BLUETTI_POLL_INTERVAL_SECONDS", "5"), "BLUETTI_POLL_INTERVAL_SECONDS"),
        stale_after_seconds=_positive_int(merged.get("BLUETTI_STALE_AFTER_SECONDS", "20"), "BLUETTI_STALE_AFTER_SECONDS"),
        enable_pv=_bool(merged.get("BLUETTI_ENABLE_PV", "0"), "BLUETTI_ENABLE_PV"),
        enable_pack_diagnostics=_bool(merged.get("BLUETTI_ENABLE_PACK_DIAGNOSTICS", "0"), "BLUETTI_ENABLE_PACK_DIAGNOSTICS"),
        enable_vebus_compat=_bool(merged.get("BLUETTI_ENABLE_VEBUS_COMPAT", "0"), "BLUETTI_ENABLE_VEBUS_COMPAT"),
        battery_device_instance=_non_negative_int(merged.get("BLUETTI_BATTERY_DEVICE_INSTANCE", "41"), "BLUETTI_BATTERY_DEVICE_INSTANCE"),
        grid_device_instance=_non_negative_int(merged.get("BLUETTI_GRID_DEVICE_INSTANCE", "30"), "BLUETTI_GRID_DEVICE_INSTANCE"),
        acload_device_instance=_non_negative_int(merged.get("BLUETTI_ACLOAD_DEVICE_INSTANCE", "31"), "BLUETTI_ACLOAD_DEVICE_INSTANCE"),
        battery_custom_name=merged.get("BLUETTI_BATTERY_CUSTOM_NAME", "BLUETTI EP760"),
        grid_custom_name=merged.get("BLUETTI_GRID_CUSTOM_NAME", "BLUETTI EP760 AC Input"),
        acload_custom_name=merged.get("BLUETTI_ACLOAD_CUSTOM_NAME", "BLUETTI EP760 AC Loads"),
        auth_device_id=merged.get("BLUETTI_AUTH_DEVICE_ID", "4C12EBA9-B7B8-40DC-91D6-9A6DC81235A6"),
        mqtt_client_id=merged.get("BLUETTI_MQTT_CLIENT_ID", "bluetti-venus-gateway"),
        mqtt_payload_format=merged.get("BLUETTI_MQTT_PAYLOAD_FORMAT", "new"),
        mqtt_ciphers=merged.get("BLUETTI_MQTT_CIPHERS", "DEFAULT:@SECLEVEL=0"),
        data_dir=Path(merged.get("BLUETTI_DATA_DIR", str(DEFAULT_DATA_DIR))),
        run_dir=Path(merged.get("BLUETTI_RUN_DIR", str(DEFAULT_RUN_DIR))),
    )


def masked_config(values: Mapping[str, str]) -> dict[str, str]:
    return {
        key: "***" if key in SECRET_KEYS or "PASSWORD" in key or "TOKEN" in key or "SECRET" in key else value
        for key, value in values.items()
    }


def _strip_optional_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _reject_template_values(values: Mapping[str, str]) -> None:
    placeholders = {
        "BLUETTI_EMAIL": "your-email@example.com",
        "BLUETTI_PASSWORD": "your-password",
        "BLUETTI_DEVICE_SN": "your-device-sn",
    }
    invalid = [key for key, placeholder in placeholders.items() if values.get(key) == placeholder]
    if invalid:
        raise ConfigError("replace template config values: " + ", ".join(invalid))


def _positive_int(raw_value: str, key: str) -> int:
    value = _non_negative_int(raw_value, key)
    if value <= 0:
        raise ConfigError(f"{key} must be greater than zero")
    return value


def _non_negative_int(raw_value: str, key: str) -> int:
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer") from exc
    if value < 0:
        raise ConfigError(f"{key} must be non-negative")
    return value


def _bool(raw_value: str, key: str) -> bool:
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{key} must be a boolean")
