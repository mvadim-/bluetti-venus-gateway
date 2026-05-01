from __future__ import annotations


def crc16_modbus(hex_payload: str) -> str:
    raw = bytes.fromhex(hex_payload.replace(" ", ""))
    value = 0xFFFF
    for item in raw:
        value ^= item
        for _ in range(8):
            if value & 1:
                value = (value >> 1) ^ 0xA001
            else:
                value >>= 1
    crc_hex = f"{value:04X}"
    return crc_hex[2:4] + crc_hex[0:2]


def build_modbus_read(reg_addr: int, reg_len: int, modbus_slave: int = 1) -> str:
    body = f"{modbus_slave & 0xFF:02X}03{reg_addr & 0xFFFF:04X}{reg_len & 0xFFFF:04X}"
    return body + crc16_modbus(body)


def build_mqtt_payload(modbus_cmd: str, reg_addr: int, payload_format: str = "new") -> str:
    if payload_format == "new":
        return f"01F80F{reg_addr & 0xFFFF:04X}0000000000{modbus_cmd}"
    if payload_format == "old":
        return "01" + modbus_cmd
    raise ValueError(f"unsupported MQTT payload format: {payload_format}")

