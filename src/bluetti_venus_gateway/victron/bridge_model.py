from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from typing import Any

from bluetti_venus_gateway.telemetry.core import parse_iso8601


SCHEMA_VERSION = 1
DEFAULT_PRODUCT_ID = 0
INVERTER_OUTPUT_EPSILON_W = 5.0
AC_INPUT_NOT_CONNECTED = 0xF0
AC_INPUT_TYPE_GRID = 1
SYSTEM_STATE_OFF = 0
SYSTEM_STATE_PASS_THROUGH = 8
SYSTEM_STATE_INVERTING = 9
BATTERY_STATE_RUNNING = 9
BATTERY_STATE_UNKNOWN = 11


@dataclass(frozen=True)
class VenusBridgeSettings:
    battery_device_instance: int = 41
    grid_device_instance: int = 30
    acload_device_instance: int = 31
    inverter_device_instance: int = 32
    multi_device_instance: int = 32
    vebus_device_instance: int = 32
    battery_custom_name: str = "BLUETTI EP760"
    grid_custom_name: str = "BLUETTI EP760 AC Input"
    acload_custom_name: str = "BLUETTI EP760 AC Loads"
    inverter_custom_name: str = "BLUETTI EP760 Inverter"
    vebus_custom_name: str = "BLUETTI EP760 VE.Bus"
    product_name: str = "BLUETTI EP760 Bridge"
    grid_product_name: str = "BLUETTI EP760 AC Input Bridge"
    acload_product_name: str = "BLUETTI EP760 AC Loads Bridge"
    inverter_product_name: str = "BLUETTI EP760 Inverter Bridge"
    multi_product_name: str = "BLUETTI EP760 Multi Bridge"
    vebus_product_name: str = "BLUETTI EP760 VE.Bus Bridge"
    product_id: int = DEFAULT_PRODUCT_ID
    model_service_id: str = "ep760"
    installed_capacity_ah: float | None = None
    voltage_low_alarm_v: float | None = None
    voltage_high_alarm_v: float | None = None
    soc_low_alarm_pct: float = 10.0
    enable_inverter_service: bool = True
    enable_multi_compat: bool = True
    enable_vebus_compat: bool = False
    gui_gauge_auto_max: bool = False
    gui_grid_max_current_a: float = 50.0
    gui_load_max_current_a: float = 33.0


def settings_from_gateway_config(config: Any) -> VenusBridgeSettings:
    return VenusBridgeSettings(
        battery_device_instance=config.battery_device_instance,
        grid_device_instance=config.grid_device_instance,
        acload_device_instance=config.acload_device_instance,
        inverter_device_instance=config.inverter_device_instance,
        multi_device_instance=config.inverter_device_instance,
        battery_custom_name=config.battery_custom_name,
        grid_custom_name=config.grid_custom_name,
        acload_custom_name=config.acload_custom_name,
        inverter_custom_name=config.inverter_custom_name,
        enable_inverter_service=config.enable_inverter_service,
        enable_multi_compat=config.enable_multi_compat,
        enable_vebus_compat=config.enable_vebus_compat,
        gui_gauge_auto_max=config.gui_gauge_auto_max,
        gui_grid_max_current_a=config.gui_grid_max_current_a,
        gui_load_max_current_a=config.gui_load_max_current_a,
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
    inverter = _build_inverter_values(
        snapshot,
        settings=settings,
        serial=serial,
        battery_voltage=battery["/Dc/0/Voltage"],
        battery_soc=battery["/Soc"],
        battery_temperature=battery["/Dc/0/Temperature"],
    )

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
    if settings.enable_inverter_service:
        payload["venus_inverter"] = {
            "service_name": f"com.victronenergy.inverter.{settings.model_service_id}_{settings.inverter_device_instance}",
            "values": inverter,
        }
    if settings.enable_multi_compat:
        payload["venus_multi"] = {
            "service_name": f"com.victronenergy.multi.{settings.model_service_id}_{settings.multi_device_instance}",
            "values": _build_multi_values(
                snapshot,
                settings=settings,
                serial=serial,
                battery_voltage=battery["/Dc/0/Voltage"],
                battery_soc=battery["/Soc"],
                battery_temperature=battery["/Dc/0/Temperature"],
            ),
        }
    if settings.enable_vebus_compat:
        payload["venus_vebus"] = {
            "service_name": f"com.victronenergy.vebus.{settings.model_service_id}_{settings.vebus_device_instance}",
            "values": _build_vebus_values(
                snapshot,
                settings=settings,
                serial=serial,
                battery_voltage=battery["/Dc/0/Voltage"],
                battery_soc=battery["/Soc"],
                battery_temperature=battery["/Dc/0/Temperature"],
            ),
        }
    if not _is_envelope_fresh(envelope):
        disconnect_venus_services(payload)
    return payload


def disconnect_venus_services(payload: dict[str, Any]) -> None:
    for key in ("venus_battery", "venus_grid", "venus_ac_load", "venus_inverter", "venus_multi", "venus_vebus"):
        service_payload = payload.get(key)
        if not isinstance(service_payload, dict):
            continue
        values = service_payload.get("values")
        if isinstance(values, dict):
            values["/Connected"] = 0


def iter_venus_service_payloads(payload: dict[str, Any]):
    for key in ("venus_battery", "venus_grid", "venus_ac_load", "venus_inverter", "venus_multi", "venus_vebus"):
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
    connected = any(value is not None for value in (soc, voltage, current, power))
    return {
        "/Connected": 1 if connected else 0,
        "/CustomName": settings.battery_custom_name,
        "/DeviceInstance": settings.battery_device_instance,
        "/ProductId": settings.product_id,
        "/ProductName": settings.product_name,
        "/Serial": serial,
        "/Soc": soc,
        "/Capacity": _calculate_capacity(settings.installed_capacity_ah, soc),
        "/ConsumedAmphours": _calculate_consumed_ah(settings.installed_capacity_ah, soc),
        "/InstalledCapacity": settings.installed_capacity_ah,
        "/State": BATTERY_STATE_RUNNING if connected else BATTERY_STATE_UNKNOWN,
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
    forward_energy = _pick_number(snapshot, "grid_charge_energy_total_kwh", "grid_charge_energy_kwh")
    reverse_energy = _pick_number(snapshot, "grid_feedback_energy_total_kwh", "feedback_energy_kwh")
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
        "/Ac/L1/Energy/Forward": forward_energy,
        "/Ac/L1/Energy/Reverse": reverse_energy,
        "/Ac/Energy/Forward": forward_energy,
        "/Ac/Energy/Reverse": reverse_energy,
    }


def _build_acload_values(snapshot: dict[str, Any], *, settings: VenusBridgeSettings, serial: str) -> dict[str, Any]:
    power = _pick_number(snapshot, "ac_load_power_w", "ac_power_w", "inv_output_power_w")
    voltage = _pick_number(snapshot, "load_voltage_v", "inv_output_voltage_v", "grid_voltage_v")
    current = _pick_number(snapshot, "load_current_a", "inv_output_current_a") or _calculate_current(power, voltage)
    frequency = _pick_number(snapshot, "inv_output_freq_hz", "grid_freq_hz")
    forward_energy = _pick_number(snapshot, "ac_energy_kwh")
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
        "/Ac/L1/Energy/Forward": forward_energy,
        "/Ac/Energy/Forward": forward_energy,
    }


def _build_inverter_values(
    snapshot: dict[str, Any],
    *,
    settings: VenusBridgeSettings,
    serial: str,
    battery_voltage: float | None,
    battery_soc: float | None,
    battery_temperature: float | None,
) -> dict[str, Any]:
    load_power = _pick_inverter_output_power(snapshot)
    load_voltage = _pick_number(snapshot, "inv_output_voltage_v", "load_voltage_v", "grid_voltage_v")
    load_current = _pick_inverter_output_current(snapshot, load_power=load_power, load_voltage=load_voltage)
    frequency = _pick_number(snapshot, "inv_output_freq_hz", "grid_freq_hz")
    grid_power = _pick_number(snapshot, "grid_power_w", "grid_power_w_phase_1", "grid_charge_power_w")
    grid_voltage = _pick_number(snapshot, "grid_voltage_v")
    grid_current = _pick_number(snapshot, "grid_current_a") or _calculate_current(grid_power, grid_voltage)
    grid_connected = any(value is not None for value in (grid_power, grid_voltage, grid_current))
    active_input = 0 if grid_connected else AC_INPUT_NOT_CONNECTED
    dc_power = -load_power if load_power is not None else None
    dc_current = _calculate_current(dc_power, battery_voltage)
    connected = 1 if any(value is not None for value in (load_power, load_voltage, load_current, frequency)) else 0
    state = _derive_inverter_state(snapshot=snapshot, connected=connected == 1, inverter_power=load_power)
    return {
        "/Connected": connected,
        "/CustomName": settings.inverter_custom_name,
        "/DeviceInstance": settings.inverter_device_instance,
        "/DeviceOffReason": 0,
        "/IsInverterCharger": 1,
        "/Mode": 3 if connected else 4,
        "/ProductId": settings.product_id,
        "/ProductName": settings.inverter_product_name,
        "/Serial": f"{serial}-inverter",
        "/State": state,
        "/Soc": battery_soc,
        "/Dc/0/Voltage": battery_voltage,
        "/Dc/0/Current": dc_current,
        "/Dc/0/Power": dc_power,
        "/Dc/0/Temperature": battery_temperature,
        "/Ac/NumberOfAcInputs": 1,
        "/Ac/ActiveIn/ActiveInput": active_input,
        "/Ac/ActiveIn/Connected": 1 if grid_connected else 0,
        "/Ac/ActiveIn/L1/V": grid_voltage,
        "/Ac/ActiveIn/L1/I": grid_current,
        "/Ac/ActiveIn/L1/P": grid_power,
        "/Ac/In/1/Connected": 1 if grid_connected else 0,
        "/Ac/In/1/Type": AC_INPUT_TYPE_GRID,
        "/Ac/In/1/L1/V": grid_voltage,
        "/Ac/In/1/L1/I": grid_current,
        "/Ac/In/1/L1/P": grid_power,
        "/Ac/In/1/L1/F": frequency,
        "/Ac/Out/L1/V": load_voltage,
        "/Ac/Out/L1/I": load_current,
        "/Ac/Out/L1/P": load_power,
        "/Ac/Out/L1/S": _calculate_power(load_voltage, load_current),
        "/Ac/Out/L1/F": frequency,
    }


def _pick_inverter_output_power(snapshot: dict[str, Any]) -> float | None:
    inverter_power = _pick_number(snapshot, "inv_output_power_w", "inverter_power_w")
    if inverter_power is not None:
        return inverter_power
    ac_load_power = _pick_number(snapshot, "ac_load_power_w", "ac_power_w")
    grid_power = _pick_number(snapshot, "grid_power_w", "grid_power_w_phase_1", "grid_charge_power_w")
    if ac_load_power is not None and grid_power is None:
        return ac_load_power
    return None


def _pick_inverter_output_current(
    snapshot: dict[str, Any],
    *,
    load_power: float | None,
    load_voltage: float | None,
) -> float | None:
    if load_power is not None and abs(load_power) <= INVERTER_OUTPUT_EPSILON_W:
        return 0.0
    return _pick_number(snapshot, "inv_output_current_a", "load_current_a") or _calculate_current(
        load_power,
        load_voltage,
    )


def _derive_inverter_state(
    *,
    snapshot: dict[str, Any],
    connected: bool,
    inverter_power: float | None,
) -> int:
    if not connected:
        return SYSTEM_STATE_OFF
    if inverter_power is not None and abs(inverter_power) > INVERTER_OUTPUT_EPSILON_W:
        return SYSTEM_STATE_INVERTING
    grid_power = _pick_number(snapshot, "grid_power_w", "grid_power_w_phase_1", "grid_charge_power_w")
    grid_voltage = _pick_number(snapshot, "grid_voltage_v")
    grid_current = _pick_number(snapshot, "grid_current_a")
    if any(value is not None for value in (grid_power, grid_voltage, grid_current)):
        return SYSTEM_STATE_PASS_THROUGH
    return SYSTEM_STATE_INVERTING


def _build_vebus_values(
    snapshot: dict[str, Any],
    *,
    settings: VenusBridgeSettings,
    serial: str,
    battery_voltage: float | None,
    battery_soc: float | None,
    battery_temperature: float | None,
) -> dict[str, Any]:
    grid_power = _pick_number(snapshot, "grid_power_w", "grid_power_w_phase_1", "grid_charge_power_w")
    grid_voltage = _pick_number(snapshot, "grid_voltage_v")
    grid_current = _pick_number(snapshot, "grid_current_a") or _calculate_current(grid_power, grid_voltage)
    load_power = _pick_number(snapshot, "ac_load_power_w", "ac_power_w", "inv_output_power_w")
    load_voltage = _pick_number(snapshot, "load_voltage_v", "inv_output_voltage_v", "grid_voltage_v")
    load_current = _pick_number(snapshot, "load_current_a", "inv_output_current_a") or _calculate_current(load_power, load_voltage)
    connected = 1 if any(value is not None for value in (grid_power, load_power, load_voltage, load_current)) else 0
    inverter_power = _pick_inverter_output_power(snapshot)
    state = _derive_inverter_state(snapshot=snapshot, connected=connected == 1, inverter_power=inverter_power)
    dc_power = -inverter_power if inverter_power is not None else None
    dc_current = _calculate_current(dc_power, battery_voltage)
    active_input = 0 if any(value is not None for value in (grid_power, grid_voltage, grid_current)) else 0xF0
    return {
        "/Connected": connected,
        "/CustomName": settings.vebus_custom_name,
        "/DeviceInstance": settings.vebus_device_instance,
        "/ProductId": settings.product_id,
        "/ProductName": settings.vebus_product_name,
        "/Serial": f"{serial}-vebus",
        "/State": state,
        "/Mode": 3 if connected else 4,
        "/DeviceOffReason": 0,
        "/Soc": battery_soc,
        "/Dc/0/Voltage": battery_voltage,
        "/Dc/0/Current": dc_current,
        "/Dc/0/Power": dc_power,
        "/Dc/0/Temperature": battery_temperature,
        "/Ac/NumberOfAcInputs": 1,
        "/Ac/ActiveIn/ActiveInput": active_input,
        "/Ac/ActiveIn/Connected": 1 if active_input != 0xF0 else 0,
        "/Ac/ActiveIn/L1/V": grid_voltage,
        "/Ac/ActiveIn/L1/I": grid_current,
        "/Ac/ActiveIn/L1/P": grid_power,
        "/Ac/In/1/Connected": 1 if active_input != 0xF0 else 0,
        "/Ac/In/1/Type": AC_INPUT_TYPE_GRID,
        "/Ac/In/1/L1/V": grid_voltage,
        "/Ac/In/1/L1/I": grid_current,
        "/Ac/In/1/L1/P": grid_power,
        "/Ac/In/1/L1/F": _pick_number(snapshot, "grid_freq_hz"),
        "/Ac/Out/L1/V": load_voltage,
        "/Ac/Out/L1/I": load_current,
        "/Ac/Out/L1/P": load_power,
        "/Ac/Out/L1/S": _calculate_power(load_voltage, load_current),
    }


def _build_multi_values(
    snapshot: dict[str, Any],
    *,
    settings: VenusBridgeSettings,
    serial: str,
    battery_voltage: float | None,
    battery_soc: float | None,
    battery_temperature: float | None,
) -> dict[str, Any]:
    grid_power = _pick_number(snapshot, "grid_power_w", "grid_power_w_phase_1", "grid_charge_power_w")
    grid_voltage = _pick_number(snapshot, "grid_voltage_v")
    grid_current = _pick_number(snapshot, "grid_current_a") or _calculate_current(grid_power, grid_voltage)
    grid_frequency = _pick_number(snapshot, "grid_freq_hz")
    grid_connected = any(value is not None for value in (grid_power, grid_voltage, grid_current, grid_frequency))
    active_input = 0 if grid_connected else AC_INPUT_NOT_CONNECTED

    output_power = _pick_number(snapshot, "ac_load_power_w", "ac_power_w", "inv_output_power_w")
    output_voltage = _pick_number(snapshot, "load_voltage_v", "inv_output_voltage_v", "grid_voltage_v")
    output_current = _pick_number(snapshot, "load_current_a", "inv_output_current_a") or _calculate_current(
        output_power,
        output_voltage,
    )
    output_frequency = _pick_number(snapshot, "inv_output_freq_hz", "grid_freq_hz")
    inverter_power = _pick_inverter_output_power(snapshot)
    dc_power = -inverter_power if inverter_power is not None else None
    dc_current = _calculate_current(dc_power, battery_voltage)
    connected = 1 if any(
        value is not None
        for value in (grid_power, grid_voltage, grid_current, output_power, output_voltage, output_current)
    ) else 0
    state = _derive_inverter_state(snapshot=snapshot, connected=connected == 1, inverter_power=inverter_power)
    return {
        "/Connected": connected,
        "/CustomName": settings.inverter_custom_name,
        "/DeviceInstance": settings.multi_device_instance,
        "/DeviceOffReason": 0,
        "/Mode": 3 if connected else 4,
        "/ProductId": settings.product_id,
        "/ProductName": settings.multi_product_name,
        "/Serial": f"{serial}-multi",
        "/State": state,
        "/Soc": battery_soc,
        "/Dc/0/Voltage": battery_voltage,
        "/Dc/0/Current": dc_current,
        "/Dc/0/Power": dc_power,
        "/Dc/0/Temperature": battery_temperature,
        "/Ac/NumberOfAcInputs": 1,
        "/Ac/ActiveIn/ActiveInput": active_input,
        "/Ac/ActiveIn/Connected": 1 if grid_connected else 0,
        "/Ac/ActiveIn/L1/V": grid_voltage,
        "/Ac/ActiveIn/L1/I": grid_current,
        "/Ac/ActiveIn/L1/P": grid_power,
        "/Ac/In/1/Connected": 1 if grid_connected else 0,
        "/Ac/In/1/Type": AC_INPUT_TYPE_GRID,
        "/Ac/In/1/L1/V": grid_voltage,
        "/Ac/In/1/L1/I": grid_current,
        "/Ac/In/1/L1/P": grid_power,
        "/Ac/In/1/L1/F": grid_frequency,
        "/Ac/Out/L1/V": output_voltage,
        "/Ac/Out/L1/I": output_current,
        "/Ac/Out/L1/P": output_power,
        "/Ac/Out/L1/S": _calculate_power(output_voltage, output_current),
        "/Ac/Out/L1/F": output_frequency,
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


def _derive_alarm(value: float | None, threshold: float | None, direction: str) -> int:
    if value is None or threshold is None:
        return 0
    if direction == "low":
        return 2 if value <= threshold else 0
    return 2 if value >= threshold else 0


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
