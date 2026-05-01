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


def decode_bluetti_payload(payload: bytes, expected_addr: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "payloadLength": len(payload),
    }
    if len(payload) < 4:
        return result
    if payload[:2] == b"\x01\xf8":
        result["frameType"] = "new"
        result["wrapper"] = {
            "addr": int.from_bytes(payload[3:5], "big", signed=False),
            "rssi": int.from_bytes(payload[7:8], "big", signed=True) if len(payload) > 7 else None,
        }
        modbus = payload[10:]
    elif payload[:1] == b"\x01":
        result["frameType"] = "old"
        modbus = payload[1:]
    else:
        result["frameType"] = "unknown"
        modbus = payload

    if len(modbus) < 5:
        return result
    byte_count = modbus[2]
    data = modbus[3:-2]
    wrapper = result.get("wrapper") or {}
    requested_addr = _infer_requested_addr(wrapper.get("addr"), byte_count, expected_addr)
    result["modbus"] = {
        "slave": modbus[0],
        "function": modbus[1],
        "byteCount": byte_count,
        "requestedAddr": requested_addr,
    }
    if modbus[1] != 0x03:
        return result
    if requested_addr == 100:
        result["messageType"] = "homeInfo"
        result["homeInfo"] = parse_home_info_data(data)
    elif requested_addr == 1300:
        result["messageType"] = "invGridInfo"
        result["invGridInfo"] = parse_inv_grid_info_data(data)
    elif requested_addr == 1400:
        result["messageType"] = "invLoadInfo"
        result["invLoadInfo"] = parse_inv_load_info_data(data)
    elif requested_addr == 1500:
        result["messageType"] = "invInvInfo"
        result["invInvInfo"] = parse_inv_inv_info_data(data)
    return result


def merge_decoded_state(state: dict[str, Any], decoded: dict[str, Any]) -> dict[str, Any]:
    merged = dict(state)
    for key in ("homeInfo", "invGridInfo", "invLoadInfo", "invInvInfo", "packMainInfo", "packItemInfo"):
        if key in decoded:
            merged[key] = decoded[key]
    return merged


def parse_home_info_data(data: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {
        "packTotalVoltage": _u16be(data, 0) / 10.0 if len(data) >= 2 else None,
        "packTotalCurrent": _u16be(data, 2) / 10.0 if len(data) >= 4 else None,
        "packTotalSoc": _u16be(data, 4) if len(data) >= 6 else None,
        "packChargingStatus": _u16be(data, 6) if len(data) >= 8 else None,
        "deviceModel": _ascii_swapped(data[20:32]) if len(data) >= 32 else "",
        "deviceSN": _device_sn_from_bytes(data[32:40]) if len(data) >= 40 else "",
    }
    if len(data) >= 120:
        result.update(
            {
                "totalDCPower": _u32_reg(data, 80),
                "totalACPower": _s32_reg(data, 84),
                "totalPVPower": _u32_reg(data, 88),
                "totalGridPower": _s32_reg(data, 92),
                "totalInvPower": _s32_reg(data, 96),
                "totalACEnergy": _u32_reg(data, 104) / 10.0,
                "totalPVChargingEnergy": _u32_reg(data, 108) / 10.0,
                "totalGridChargingEnergy": _u32_reg(data, 112) / 10.0,
                "totalFeedbackEnergy": _u32_reg(data, 116) / 10.0,
            }
        )
    return result


def parse_inv_grid_info_data(data: bytes) -> dict[str, Any]:
    phase_count = data[25] if len(data) > 25 else 0
    phase_list = []
    available_phase_count = min(phase_count, max(0, len(data) - 26) // 12)
    for phase_index in range(available_phase_count):
        offset = 26 + (phase_index * 12)
        phase_list.append(
            {
                "phase": phase_index + 1,
                "gridPower": abs(_s16be(data, offset)),
                "gridVoltage": _u16be(data, offset + 2) / 10.0,
                "gridCurrent": abs(_s16be(data, offset + 4)) / 10.0,
                "apparent": abs(_s16be(data, offset + 6)),
            }
        )
    result: dict[str, Any] = {
        "frequency": _u16be(data, 0) / 10.0 if len(data) >= 2 else None,
        "totalChgPower": _s32_reg(data, 2) if len(data) >= 6 else None,
        "totalChgEnergy": _u32_reg(data, 6) / 10.0 if len(data) >= 10 else None,
        "totalFeedbackEnergy": _u32_reg(data, 10) / 10.0 if len(data) >= 14 else None,
        "sysPhaseNumber": available_phase_count,
        "phaseList": phase_list,
    }
    if phase_list:
        first = phase_list[0]
        result["gridVoltage"] = first["gridVoltage"]
        result["gridCurrent"] = first["gridCurrent"]
        result["gridPower"] = first["gridPower"]
        result["apparent"] = first["apparent"]
        result["gridFreq"] = result["frequency"]
    return result


def parse_inv_load_info_data(data: bytes) -> dict[str, Any]:
    phase_count = data[59] if len(data) > 59 else 0
    phase_list = []
    available_phase_count = min(phase_count, max(0, len(data) - 60) // 12)
    for phase_index in range(available_phase_count):
        offset = 60 + (phase_index * 12)
        phase_list.append(
            {
                "phase": phase_index + 1,
                "loadPower": _u16be(data, offset) if len(data) > offset + 1 else None,
                "loadVoltage": _u16be(data, offset + 2) / 10.0 if len(data) > offset + 3 else None,
                "loadCurrent": _u16be(data, offset + 4) / 10.0 if len(data) > offset + 5 else None,
                "apparent": _u16be(data, offset + 6) if len(data) > offset + 7 else None,
            }
        )
    result: dict[str, Any] = {
        "dcLoadTotalPower": _u32_reg(data, 0) if len(data) >= 4 else None,
        "dcLoadTotalEnergy": _u32_reg(data, 4) / 10.0 if len(data) >= 8 else None,
        "acLoadTotalPower": _u32_reg(data, 40) if len(data) >= 44 else None,
        "acLoadTotalEnergy": _u32_reg(data, 44) / 10.0 if len(data) >= 48 else None,
        "sysPhaseNumber": available_phase_count,
        "phaseList": phase_list,
    }
    if phase_list:
        result["phase1LoadPower"] = phase_list[0].get("loadPower")
        result["phase1LoadVoltage"] = phase_list[0].get("loadVoltage")
        result["phase1LoadCurrent"] = phase_list[0].get("loadCurrent")
    return result


def parse_inv_inv_info_data(data: bytes) -> dict[str, Any]:
    phase_count = data[17] if len(data) > 17 else 0
    frequency = _u16be(data, 0) / 10.0 if len(data) >= 2 else None
    phase_list = []
    available_phase_count = min(phase_count, max(0, len(data) - 18) // 12)
    for phase_index in range(available_phase_count):
        offset = 18 + (phase_index * 12)
        phase_list.append(
            {
                "phase": phase_index + 1,
                "workStatus": data[offset + 1] if len(data) > offset + 1 else None,
                "invPower": _u16be(data, offset + 2) if len(data) > offset + 3 else None,
                "invVoltage": _u16be(data, offset + 4) / 10.0 if len(data) > offset + 5 else None,
                "invCurrent": _u16be(data, offset + 6) / 10.0 if len(data) > offset + 7 else None,
                "invFreq": frequency,
            }
        )
    result: dict[str, Any] = {
        "frequency": frequency,
        "totalEnergy": _u32_reg(data, 2) / 10.0 if len(data) >= 6 else None,
        "sysPhaseNumber": available_phase_count,
        "phaseList": phase_list,
    }
    if phase_list:
        result["phase1InvPower"] = phase_list[0].get("invPower")
        result["phase1InvVoltage"] = phase_list[0].get("invVoltage")
        result["phase1InvCurrent"] = phase_list[0].get("invCurrent")
    return result


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


def _infer_requested_addr(wrapper_addr: Any, byte_count: int, expected_addr: int | None) -> int | None:
    if isinstance(wrapper_addr, int) and wrapper_addr in {100, 1300, 1400, 1500}:
        return wrapper_addr
    by_size = {
        184: 100,
        38: 1300,
        72: 1400,
        30: 1500,
    }
    return by_size.get(byte_count, expected_addr)


def _u16be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "big", signed=False)


def _s16be(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "big", signed=True)


def _u32_reg(data: bytes, offset: int) -> int:
    swapped = data[offset + 2:offset + 4] + data[offset:offset + 2]
    return int.from_bytes(swapped, "big", signed=False)


def _s32_reg(data: bytes, offset: int) -> int:
    swapped = data[offset + 2:offset + 4] + data[offset:offset + 2]
    return int.from_bytes(swapped, "big", signed=True)


def _ascii_swapped(data: bytes) -> str:
    chars = []
    for index in range(0, len(data), 2):
        pair = data[index:index + 2]
        if len(pair) < 2:
            continue
        if pair[1] != 0:
            chars.append(chr(pair[1]))
        if pair[0] != 0:
            chars.append(chr(pair[0]))
    return "".join(chars)


def _device_sn_from_bytes(data: bytes) -> str:
    parts = []
    for index in range(len(data) - 2, -1, -2):
        parts.append("%02X%02X" % (data[index], data[index + 1]))
    joined = "".join(parts)
    if not joined:
        return "0"
    return str(int(joined, 16))
