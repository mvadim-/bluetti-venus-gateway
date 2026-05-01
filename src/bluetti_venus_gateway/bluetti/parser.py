from __future__ import annotations

from typing import Any


HOME_SIGNAL_MAP = {
    "deviceModel": "device_model",
    "deviceSN": "device_sn",
    "packTotalSoc": "soc",
    "packTotalVoltage": "battery_voltage_v",
    "packTotalCurrent": "battery_current_a",
    "packChargingStatus": "charging_status",
    "totalACPower": "ac_power_w",
    "totalGridPower": "grid_power_w",
    "totalPVPower": "pv_power_w",
    "totalDCPower": "dc_power_w",
    "totalInvPower": "inverter_power_w",
    "totalACEnergy": "ac_energy_kwh",
    "totalGridChargingEnergy": "grid_charge_energy_kwh",
    "totalPVChargingEnergy": "pv_charge_energy_kwh",
    "totalFeedbackEnergy": "feedback_energy_kwh",
}

GRID_SIGNAL_MAP = {
    "gridVoltage": "grid_voltage_v",
    "gridCurrent": "grid_current_a",
    "gridPower": "grid_power_w_phase_1",
    "apparent": "grid_apparent_va",
    "gridFreq": "grid_freq_hz",
    "totalChgPower": "grid_charge_power_w",
    "totalChgEnergy": "grid_charge_energy_total_kwh",
    "totalFeedbackEnergy": "grid_feedback_energy_total_kwh",
}

LOAD_SIGNAL_MAP = {
    "acLoadTotalPower": "ac_load_power_w",
    "dcLoadTotalPower": "dc_load_power_w",
    "phase1LoadVoltage": "load_voltage_v",
    "phase1LoadCurrent": "load_current_a",
    "acLoadTotalEnergy": "ac_energy_kwh",
}

INVERTER_SIGNAL_MAP = {
    "phase1InvPower": "inv_output_power_w",
    "phase1InvVoltage": "inv_output_voltage_v",
    "phase1InvCurrent": "inv_output_current_a",
    "frequency": "inv_output_freq_hz",
}

PACK_MAIN_SIGNAL_MAP = {
    "totalSOC": "pack_total_soc",
    "totalSOH": "pack_total_soh",
    "averageTemp": "pack_avg_temp_c",
    "totalVoltage": "pack_total_voltage_v",
    "totalCurrent": "pack_total_current_a",
    "packCnts": "pack_count",
}

PACK_ITEM_SIGNAL_MAP = {
    "packID": "pack_id",
    "packSN": "pack_sn",
    "packSoc": "pack_soc",
    "packSoh": "pack_soh",
    "voltage": "pack_voltage_v",
    "current": "pack_current_a",
    "averageTemp": "pack_temp_c",
}


def normalize_decoded_state(decoded_state: dict[str, Any]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    _copy_mapped(decoded_state.get("homeInfo") or {}, HOME_SIGNAL_MAP, snapshot)
    _copy_mapped(decoded_state.get("invGridInfo") or {}, GRID_SIGNAL_MAP, snapshot)
    _copy_mapped(decoded_state.get("invLoadInfo") or {}, LOAD_SIGNAL_MAP, snapshot)
    _copy_mapped(decoded_state.get("invInvInfo") or {}, INVERTER_SIGNAL_MAP, snapshot)
    _copy_mapped(decoded_state.get("packMainInfo") or {}, PACK_MAIN_SIGNAL_MAP, snapshot)
    _copy_mapped(decoded_state.get("packItemInfo") or {}, PACK_ITEM_SIGNAL_MAP, snapshot)

    grid = decoded_state.get("invGridInfo") or {}
    grid_phase = _first_phase(grid)
    snapshot.setdefault("grid_voltage_v", grid_phase.get("gridVoltage"))
    snapshot.setdefault("grid_current_a", grid_phase.get("gridCurrent"))
    snapshot.setdefault("grid_power_w_phase_1", grid_phase.get("gridPower"))

    load = decoded_state.get("invLoadInfo") or {}
    load_phase = _first_phase(load)
    snapshot.setdefault("load_voltage_v", load_phase.get("loadVoltage"))
    snapshot.setdefault("load_current_a", load_phase.get("loadCurrent"))
    snapshot.setdefault("ac_load_power_w", load_phase.get("loadPower"))

    return {key: value for key, value in snapshot.items() if value is not None}


def _copy_mapped(source: dict[str, Any], mapping: dict[str, str], target: dict[str, Any]) -> None:
    for source_key, target_key in mapping.items():
        value = source.get(source_key)
        if value is not None:
            target[target_key] = value


def _first_phase(payload: dict[str, Any]) -> dict[str, Any]:
    phase_list = payload.get("phaseList")
    if isinstance(phase_list, list) and phase_list and isinstance(phase_list[0], dict):
        return phase_list[0]
    return {}

