from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any

from bluetti_venus_gateway.telemetry.core import parse_iso8601


SCHEMA_VERSION = 1
DEFAULT_PRODUCT_ID = 0


@dataclass(frozen=True)
class VenusBridgeSettings:
    battery_device_instance: int = 41
    grid_device_instance: int = 30
    acload_device_instance: int = 31
    vebus_device_instance: int = 32
    battery_custom_name: str = "BLUETTI EP760"
    grid_custom_name: str = "BLUETTI EP760 AC Input"
    acload_custom_name: str = "BLUETTI EP760 AC Loads"
    vebus_custom_name: str = "BLUETTI EP760 VE.Bus"
    product_name: str = "BLUETTI EP760 Bridge"
    grid_product_name: str = "BLUETTI EP760 AC Input Bridge"
    acload_product_name: str = "BLUETTI EP760 AC Loads Bridge"
    vebus_product_name: str = "BLUETTI EP760 VE.Bus Bridge"
    product_id: int = DEFAULT_PRODUCT_ID
    model_service_id: str = "ep760"
    installed_capacity_ah: float | None = None
    voltage_low_alarm_v: float = 44.0
    voltage_high_alarm_v: float = 58.5
    soc_low_alarm_pct: float = 10.0
    enable_vebus_compat: bool = False


def settings_from_gateway_config(config: Any) -> VenusBridgeSettings:
    return VenusBridgeSettings(
        battery_device_instance=config.battery_device_instance,
        grid_device_instance=config.grid_device_instance,
        acload_device_instance=config.acload_device_instance,
        battery_custom_name=config.battery_custom_name,
        grid_custom_name=config.grid_custom_name,
        acload_custom_name=config.acload_custom_name,
        enable_vebus_compat=config.enable_vebus_compat,
    )


def build_venus_bridge_payload(
    envelope: dict[str, Any],
    *,
    settings: VenusBridgeSettings,
    exported_at: datetime | None = None,
) -> dict[str, Any]:
    exported = _ensure_aware_utc(exported_at or datetime.now(timezone.utc))
    snapshot = envelope.get("snapshot") or envelope
    serial = _pick_string(envelope, "device_sn") or _pick_string(snapshot, "device_sn", "pack_sn") or "bluetti"
    battery = _build_battery_values(snapshot, settings=settings, serial=serial)
    grid = _build_grid_values(snapshot, settings=settings, serial=serial)
    acload = _build_acload_values(snapshot, settings=settings, serial=serial)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": exported.isoformat(),
        "source_observed_at": str(envelope.get("observed_at") or snapshot.get("timestamp") or ""),
        "source_received_at": str(envelope.get("received_at") or ""),
        "source_freshness": dict(envelope.get("freshness") or {}),
        "snapshot": dict(snapshot),
        "venus_battery": {
            "service_name": f"com.victronenergy.battery.{settings.model_service_id}_{settings.battery_device_instance}",
            "values": battery,
        },
        "venus_grid": {
            "service_name": f"com.victronenergy.grid.{settings.model_service_id}_{settings.grid_device_instance}",
            "values": grid,
        },
        "venus_ac_load": {
            "service_name": f"com.victronenergy.acload.{settings.model_service_id}_{settings.acload_device_instance}",
            "values": acload,
        },
    }
    if settings.enable_vebus_compat:
        payload["venus_vebus"] = {
            "service_name": f"com.victronenergy.vebus.{settings.model_service_id}_{settings.vebus_device_instance}",
            "values": _build_vebus_values(
                snapshot,
                settings=settings,
                serial=serial,
                battery_voltage=battery["/Dc/0/Voltage"],
            ),
        }
    if not _is_envelope_fresh(envelope):
        disconnect_venus_services(payload)
    return payload


def disconnect_venus_services(payload: dict[str, Any]) -> None:
    for key in ("venus_battery", "venus_grid", "venus_ac_load", "venus_vebus"):
        service_payload = payload.get(key)
        if not isinstance(service_payload, dict):
            continue
        values = service_payload.get("values")
        if isinstance(values, dict):
            values["/Connected"] = 0


def iter_venus_service_payloads(payload: dict[str, Any]):
    for key in ("venus_battery", "venus_grid", "venus_ac_load", "venus_vebus"):
        service_payload = payload.get(key) or {}
        service_name = str(service_payload.get("service_name") or "").strip()
        values = service_payload.get("values") or {}
        if service_name and values:
            yield service_name, values


def _build_battery_values(snapshot: dict[str, Any], *, settings: VenusBridgeSettings, serial: str) -> dict[str, Any]:
    soc = _pick_number(snapshot, "soc", "pack_total_soc", "pack_soc")
    voltage = _pick_number(snapshot, "battery_voltage_v", "pack_total_voltage_v", "pack_voltage_v")
    current = _pick_number(snapshot, "battery_current_a", "pack_total_current_a", "pack_current_a")
    power = _pick_number(snapshot, "dc_power_w") or _calculate_power(voltage, current)
    temperature = _pick_number(snapshot, "pack_avg_temp_c", "pack_temp_c")
    return {
        "/Connected": 1 if any(value is not None for value in (soc, voltage, current, power)) else 0,
        "/CustomName": settings.battery_custom_name,
        "/DeviceInstance": settings.battery_device_instance,
        "/ProductId": settings.product_id,
        "/ProductName": settings.product_name,
        "/Serial": serial,
        "/Soc": soc,
        "/Capacity": _calculate_capacity(settings.installed_capacity_ah, soc),
        "/ConsumedAmphours": _calculate_consumed_ah(settings.installed_capacity_ah, soc),
        "/InstalledCapacity": settings.installed_capacity_ah,
        "/State": _derive_battery_state(snapshot=snapshot, current=current),
        "/Dc/0/Voltage": voltage,
        "/Dc/0/Current": current,
        "/Dc/0/Power": power,
        "/Dc/0/Temperature": temperature,
        "/Io/AllowToCharge": 1,
        "/Io/AllowToDischarge": 1,
        "/Alarms/LowVoltage": _derive_alarm(voltage, settings.voltage_low_alarm_v, "low"),
        "/Alarms/HighVoltage": _derive_alarm(voltage, settings.voltage_high_alarm_v, "high"),
        "/Alarms/LowSoc": _derive_alarm(soc, settings.soc_low_alarm_pct, "low"),
    }


def _build_grid_values(snapshot: dict[str, Any], *, settings: VenusBridgeSettings, serial: str) -> dict[str, Any]:
    power = _pick_number(snapshot, "grid_power_w", "grid_power_w_phase_1", "grid_charge_power_w")
    voltage = _pick_number(snapshot, "grid_voltage_v")
    current = _pick_number(snapshot, "grid_current_a") or _calculate_current(power, voltage)
    frequency = _pick_number(snapshot, "grid_freq_hz")
    return {
        "/Connected": 1 if any(value is not None for value in (power, voltage, current, frequency)) else 0,
        "/CustomName": settings.grid_custom_name,
        "/DeviceInstance": settings.grid_device_instance,
        "/DeviceType": 0,
        "/ProductId": settings.product_id,
        "/ProductName": settings.grid_product_name,
        "/Serial": f"{serial}-grid",
        "/Ac/L1/Voltage": voltage,
        "/Ac/L1/Current": current,
        "/Ac/L1/Power": power,
        "/Ac/Power": power,
        "/Ac/Frequency": frequency,
        "/Ac/Energy/Forward": _pick_number(snapshot, "grid_charge_energy_total_kwh", "grid_charge_energy_kwh"),
        "/Ac/Energy/Reverse": _pick_number(snapshot, "grid_feedback_energy_total_kwh", "feedback_energy_kwh"),
    }


def _build_acload_values(snapshot: dict[str, Any], *, settings: VenusBridgeSettings, serial: str) -> dict[str, Any]:
    power = _pick_number(snapshot, "ac_load_power_w", "ac_power_w", "inv_output_power_w")
    voltage = _pick_number(snapshot, "load_voltage_v", "inv_output_voltage_v", "grid_voltage_v")
    current = _pick_number(snapshot, "load_current_a", "inv_output_current_a") or _calculate_current(power, voltage)
    frequency = _pick_number(snapshot, "inv_output_freq_hz", "grid_freq_hz")
    return {
        "/Connected": 1 if any(value is not None for value in (power, voltage, current, frequency)) else 0,
        "/CustomName": settings.acload_custom_name,
        "/DeviceInstance": settings.acload_device_instance,
        "/Position": 1,
        "/ProductId": settings.product_id,
        "/ProductName": settings.acload_product_name,
        "/Serial": f"{serial}-acload",
        "/Ac/L1/Voltage": voltage,
        "/Ac/L1/Current": current,
        "/Ac/L1/Power": power,
        "/Ac/Power": power,
        "/Ac/Frequency": frequency,
        "/Ac/Energy/Forward": _pick_number(snapshot, "ac_energy_kwh"),
    }


def _build_vebus_values(
    snapshot: dict[str, Any],
    *,
    settings: VenusBridgeSettings,
    serial: str,
    battery_voltage: float | None,
) -> dict[str, Any]:
    grid_power = _pick_number(snapshot, "grid_power_w", "grid_power_w_phase_1", "grid_charge_power_w")
    grid_voltage = _pick_number(snapshot, "grid_voltage_v")
    grid_current = _pick_number(snapshot, "grid_current_a") or _calculate_current(grid_power, grid_voltage)
    load_power = _pick_number(snapshot, "ac_load_power_w", "ac_power_w", "inv_output_power_w")
    load_voltage = _pick_number(snapshot, "load_voltage_v", "inv_output_voltage_v", "grid_voltage_v")
    load_current = _pick_number(snapshot, "load_current_a", "inv_output_current_a") or _calculate_current(load_power, load_voltage)
    connected = 1 if any(value is not None for value in (grid_power, load_power, load_voltage, load_current)) else 0
    active_input = 0 if any(value is not None for value in (grid_power, grid_voltage, grid_current)) else 0xF0
    return {
        "/Connected": connected,
        "/CustomName": settings.vebus_custom_name,
        "/DeviceInstance": settings.vebus_device_instance,
        "/ProductId": settings.product_id,
        "/ProductName": settings.vebus_product_name,
        "/Serial": f"{serial}-vebus",
        "/State": 9 if connected else 0,
        "/Dc/0/Voltage": battery_voltage,
        "/Dc/0/Current": 0.0,
        "/Dc/0/Power": 0.0,
        "/Ac/ActiveIn/ActiveInput": active_input,
        "/Ac/ActiveIn/Connected": 1 if active_input != 0xF0 else 0,
        "/Ac/ActiveIn/L1/V": grid_voltage,
        "/Ac/ActiveIn/L1/I": grid_current,
        "/Ac/ActiveIn/L1/P": grid_power,
        "/Ac/Out/L1/V": load_voltage,
        "/Ac/Out/L1/I": load_current,
        "/Ac/Out/L1/P": load_power,
        "/Ac/Out/L1/S": _calculate_power(load_voltage, load_current),
    }


def _is_envelope_fresh(envelope: dict[str, Any]) -> bool:
    freshness = envelope.get("freshness")
    if isinstance(freshness, dict) and freshness.get("state") == "stale":
        return False
    return True


def _pick_number(snapshot: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        raw_value = snapshot.get(key)
        if raw_value is None or raw_value == "" or isinstance(raw_value, bool):
            continue
        if isinstance(raw_value, (int, float)):
            return float(raw_value)
        if isinstance(raw_value, str):
            try:
                return float(raw_value)
            except ValueError:
                continue
    return None


def _pick_string(snapshot: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = snapshot.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _calculate_power(voltage: float | None, current: float | None) -> float | None:
    if voltage is None or current is None:
        return None
    return round(voltage * current, 3)


def _calculate_current(power: float | None, voltage: float | None) -> float | None:
    if power is None or voltage in (None, 0):
        return None
    return round(power / voltage, 3)


def _calculate_capacity(installed_capacity_ah: float | None, soc: float | None) -> float | None:
    if installed_capacity_ah is None or soc is None:
        return None
    return round(installed_capacity_ah * soc / 100.0, 3)


def _calculate_consumed_ah(installed_capacity_ah: float | None, soc: float | None) -> float | None:
    if installed_capacity_ah is None or soc is None:
        return None
    return round(installed_capacity_ah * (100.0 - soc) / 100.0, 3)


def _derive_alarm(value: float | None, threshold: float, direction: str) -> int:
    if value is None:
        return 0
    if direction == "low":
        return 2 if value <= threshold else 0
    return 2 if value >= threshold else 0


def _derive_battery_state(snapshot: dict[str, Any], current: float | None) -> int:
    charging_status = str(snapshot.get("charging_status") or "").strip().lower()
    if "discharg" in charging_status:
        return 2
    if "charg" in charging_status or charging_status in {"grid", "pv"}:
        return 1
    if current is None:
        return 0
    if current > 0.2:
        return 1
    if current < -0.2:
        return 2
    return 0


def _ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


__all__ = [
    "VenusBridgeSettings",
    "build_venus_bridge_payload",
    "disconnect_venus_services",
    "iter_venus_service_payloads",
    "parse_iso8601",
    "settings_from_gateway_config",
]

