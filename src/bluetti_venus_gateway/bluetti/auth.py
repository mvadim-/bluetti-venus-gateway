from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import time
from typing import Any
from urllib import error
from urllib import parse
from urllib import request


BASE_URL = "https://gw.bluettipower.com"
ACCESS_TOKEN_URL = BASE_URL + "/accessToken"
BASIC_GET_URL = BASE_URL + "/api/bluuc/uc/v1/basic/get"
DEVICE_PAGE_URL = BASE_URL + "/api/blusmartprod/device/group/v3/findDevicePage"
DEVICE_REMOTE_SEARCH_URL = BASE_URL + "/api/blusmartprod/device/basic/v1/deviceRemoteSearch"
UTC_URL = BASE_URL + "/api/midppkic/cert/app/v2/now/utc-time"
PFX_URL = BASE_URL + "/api/midppkic/cert/app/v1/pfx"

DEFAULT_PASS_OPEN = "f36fffc2e36d691a0458db0906d9ebad158b6db16566aaa9b1aab184eb305cd8"
DEFAULT_X_OS = "ios"
DEFAULT_X_APP_VER = "3.0.8"
DEFAULT_X_APP_KEY = "1783AF460D4D0615365940C9D3A"
DEFAULT_X_OS_VER = "32362e342e31"
DEFAULT_ACCEPT_LANGUAGE = "en-US"
DEFAULT_USER_AGENT = "Bluetti/3.0.8 (iPhone; iOS 26.4.1; Scale/3.00)"
DEFAULT_PFX_USER_AGENT = "Bluetti/2432 CFNetwork/3860.500.112 Darwin/25.4.0"

SHARED_PRIVATE_KEY = "ga3sa4hj6kfl"
T0 = 1371517200
STEP = 30
DIGITS_POWER = [1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000]


class BluettiAuthError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True)
class BluettiAuthSettings:
    email: str
    password: str
    device_sn: str
    auth_device_id: str
    certs_dir: Path
    mqtt_client_id: str
    mqtt_ciphers: str
    pass_open: str = DEFAULT_PASS_OPEN
    x_os: str = DEFAULT_X_OS
    x_app_ver: str = DEFAULT_X_APP_VER
    x_app_key: str = DEFAULT_X_APP_KEY
    x_os_ver: str = DEFAULT_X_OS_VER
    accept_language: str = DEFAULT_ACCEPT_LANGUAGE
    user_agent: str = DEFAULT_USER_AGENT
    pfx_user_agent: str = DEFAULT_PFX_USER_AGENT


@dataclass(frozen=True)
class BluettiMqttContext:
    host: str
    port: int
    username: str
    password: str
    password_kind: str
    subscribe_topic: str
    publish_topic: str
    client_id: str
    cert_path: Path
    key_path: Path
    ca_path: Path | None
    mqtt_ciphers: str
    modbus_slave: int
    device_sn: str
    device_model: str | None
    token_parts: tuple[str, ...]
    server_utc_offset_ms: int
    refresh_after_epoch: int


def prepare_mqtt_context(settings: BluettiAuthSettings) -> BluettiMqttContext:
    settings.certs_dir.mkdir(parents=True, exist_ok=True)
    token = _login(settings)
    user_id = _basic_user_id(settings, token)
    device = _find_device(settings, token, user_id)
    utc_observed_local_ms = int(time.time() * 1000)
    utc_time, x_signature, iot_server = _server_utc(settings, token)
    sid = _sid_from_token(token)
    _, utc_request_sign = _build_request_sign(
        sid,
        settings.x_app_key,
        settings.x_app_ver,
        settings.x_os,
        utc_time,
        UTC_URL,
    )
    p12_password = _decrypt_signature(x_signature, utc_request_sign)
    _download_p12(settings, token, sid, user_id, p12_password, utc_time)
    tls_files = _extract_mqtt_tls_files(settings.certs_dir, p12_password)

    device_model = _pick_string(device, "model")
    device_sub_sn = _pick_string(device, "subSn")
    device_iot_server = _pick_string(device, "iotSrvIp")
    iot_conn_secret = _pick_string(device, "iotConnSecret")
    host, port = _split_host_port(device_iot_server or iot_server)
    subscribe_topic = f"PUB/{device_model}/{device_sub_sn}" if device_model and device_sub_sn else "PUB/#"
    publish_topic = "SUB/" + subscribe_topic[4:] if subscribe_topic.startswith("PUB/") else subscribe_topic

    token_parts = tuple(token.split("."))
    server_utc_offset_ms = utc_time - utc_observed_local_ms
    if iot_conn_secret:
        mqtt_password = "rmt:" + iot_conn_secret
        password_kind = "iotConnSecret"
    else:
        if len(token_parts) < 2:
            raise BluettiAuthError("authorization token cannot be used for MQTT TOTP fallback", retryable=False)
        mqtt_password = generate_totp(token_parts[1], token_parts[0], int(time.time() * 1000) + server_utc_offset_ms)
        password_kind = "totp"

    return BluettiMqttContext(
        host=host,
        port=port,
        username="tid:" + sid,
        password=mqtt_password,
        password_kind=password_kind,
        subscribe_topic=subscribe_topic,
        publish_topic=publish_topic,
        client_id=settings.mqtt_client_id,
        cert_path=tls_files["cert"],
        key_path=tls_files["key"],
        ca_path=tls_files["ca"],
        mqtt_ciphers=settings.mqtt_ciphers,
        modbus_slave=0 if device_model == "PBOX" else 1,
        device_sn=_pick_string(device, "sn") or settings.device_sn,
        device_model=device_model,
        token_parts=token_parts,
        server_utc_offset_ms=server_utc_offset_ms,
        refresh_after_epoch=int(time.time()) + 3300,
    )


def refresh_mqtt_password(context: BluettiMqttContext) -> str:
    if context.password_kind == "iotConnSecret":
        return context.password
    if len(context.token_parts) < 2:
        raise BluettiAuthError("authorization token cannot refresh MQTT password", retryable=False)
    return generate_totp(
        context.token_parts[1],
        context.token_parts[0],
        int(time.time() * 1000) + context.server_utc_offset_ms,
    )


def build_ssl_context(context: BluettiMqttContext) -> ssl.SSLContext:
    ssl_context = ssl.create_default_context(cafile=str(context.ca_path) if context.ca_path else None)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.set_ciphers(context.mqtt_ciphers)
    ssl_context.load_cert_chain(str(context.cert_path), str(context.key_path))
    return ssl_context


def normalize_password_hash(password_or_hash: str) -> str:
    normalized = password_or_hash.strip()
    if re.fullmatch(r"[0-9A-Fa-f]{64}", normalized):
        return normalized.upper()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper()


def generate_totp(user_id: str, device_id: str, utc_time_ms: int) -> str:
    factor = ((utc_time_ms // 1000) - T0) // STEP
    counter_hex = format(factor, "X").rjust(16, "0")
    encrypted = _totp_encrypt(bytes.fromhex(counter_hex), _build_kvalue(user_id, device_id).encode("utf-8"))
    return _truncate_totp(encrypted)


def _login(settings: BluettiAuthSettings) -> str:
    body = parse.urlencode(
        {
            "passOpen": settings.pass_open,
            "password": normalize_password_hash(settings.password),
            "username": settings.email,
        }
    ).encode("utf-8")
    status, _, response_body = _http_request(
        ACCESS_TOKEN_URL,
        "POST",
        _common_headers(settings) | {"content-type": "application/x-www-form-urlencoded"},
        body,
    )
    payload = _ensure_json_status("accessToken", status, response_body)
    token = _json_path(payload, ["data", "token"])
    if not isinstance(token, str) or not token:
        raise BluettiAuthError("accessToken response did not include token", retryable=True)
    return token


def _basic_user_id(settings: BluettiAuthSettings, token: str) -> str:
    status, _, body = _http_request(BASIC_GET_URL, "GET", _common_headers(settings, token), None)
    payload = _ensure_json_status("basic/get", status, body)
    user_id = _json_path(payload, ["data", "uid"])
    if not isinstance(user_id, str) or not user_id:
        raise BluettiAuthError("basic/get response did not include user id", retryable=True)
    return user_id


def _find_device(settings: BluettiAuthSettings, token: str, user_id: str) -> dict[str, Any]:
    url = DEVICE_PAGE_URL + "?" + parse.urlencode({"userId": user_id})
    status, _, body = _http_request(url, "GET", _common_headers(settings, token), None)
    payload = _ensure_json_status("findDevicePage", status, body)
    device_list = ((payload.get("data") or {}).get("deviceList") or []) if isinstance(payload, dict) else []
    candidates = [item for item in device_list if isinstance(item, dict)]
    selected = _select_device(candidates, settings.device_sn)
    remote = None
    if selected.get("sn"):
        remote_url = DEVICE_REMOTE_SEARCH_URL + "?" + parse.urlencode({"deviceSn": selected["sn"]})
        status, _, body = _http_request(remote_url, "GET", _common_headers(settings, token), None)
        remote_payload = _ensure_json_status("deviceRemoteSearch", status, body)
        remote_data = remote_payload.get("data") if isinstance(remote_payload, dict) else None
        if isinstance(remote_data, dict):
            remote = remote_data
    merged = dict(selected)
    if remote:
        merged.update({key: value for key, value in remote.items() if value is not None})
    return merged


def _server_utc(settings: BluettiAuthSettings, token: str) -> tuple[int, str, str | None]:
    status, headers, body = _http_request(UTC_URL, "GET", _common_headers(settings, token), None)
    payload = _ensure_json_status("utc-time", status, body)
    utc_time = _json_path(payload, ["data"])
    x_signature = _header_ci(headers, "x-signature")
    iot_server = _header_ci(headers, "x-iot-server")
    if not isinstance(utc_time, int):
        raise BluettiAuthError("utc-time response did not include integer time", retryable=True)
    if not x_signature:
        raise BluettiAuthError("utc-time response did not include x-signature", retryable=True)
    return utc_time, x_signature, iot_server


def _download_p12(
    settings: BluettiAuthSettings,
    token: str,
    sid: str,
    user_id: str,
    p12_password: str,
    utc_time: int,
) -> Path:
    totp_value = generate_totp(user_id, settings.auth_device_id, utc_time)
    totp_int = int(totp_value)
    _, pfx_request_sign = _build_request_sign(
        sid,
        settings.x_app_key,
        settings.x_app_ver,
        settings.x_os,
        totp_int,
        PFX_URL,
    )
    headers = _common_headers(settings, token, user_agent=settings.pfx_user_agent)
    headers["url"] = "/api/midppkic/cert/app/v1/pfx"
    headers["currentutctime"] = format(totp_int, "x")
    headers["x-app-resource"] = _encrypt_p12_password(p12_password, pfx_request_sign)
    headers["range"] = "bytes=0-"
    status, _, body = _http_request(PFX_URL, "POST", headers, b"")
    if status != 200:
        raise BluettiAuthError(f"pfx download failed with status {status}", retryable=True)
    p12_path = settings.certs_dir / "device_cert.p12"
    p12_path.write_bytes(body)
    return p12_path


def _extract_mqtt_tls_files(certs_dir: Path, p12_password: str) -> dict[str, Path | None]:
    p12_path = certs_dir / "device_cert.p12"
    cert_path = certs_dir / "client.crt"
    key_path = certs_dir / "client.key"
    _run_pkcs12(p12_path, p12_password, ["-clcerts", "-nokeys", "-out", str(cert_path)])
    _run_pkcs12(p12_path, p12_password, ["-nocerts", "-nodes", "-out", str(key_path)])
    ca_path = _default_ca_path()
    return {"cert": cert_path, "key": key_path, "ca": ca_path}


def _run_pkcs12(p12_path: Path, password: str, extra_args: list[str]) -> None:
    base_cmd = ["openssl", "pkcs12", "-in", str(p12_path), "-passin", "pass:" + password]
    attempts = [
        base_cmd + extra_args,
        base_cmd + ["-legacy"] + extra_args,
        base_cmd + ["-provider", "default", "-provider", "legacy"] + extra_args,
    ]
    stderr = ""
    for cmd in attempts:
        completed = subprocess.run(cmd, capture_output=True, text=True)
        if completed.returncode == 0:
            return
        stderr = completed.stderr.strip()
    raise BluettiAuthError(f"openssl pkcs12 export failed: {stderr}", retryable=False)


def _http_request(
    url: str,
    method: str,
    headers: dict[str, str],
    data: bytes | None,
) -> tuple[int, dict[str, str], bytes]:
    req = request.Request(url=url, data=data, method=method)
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), dict(resp.headers.items()), resp.read()
    except error.HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


def _ensure_json_status(step: str, status: int, body: bytes) -> Any:
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise BluettiAuthError(f"{step} returned invalid JSON with status {status}", retryable=True) from exc
    if status == 200:
        return payload
    retryable = True
    message = ""
    code = None
    if isinstance(payload, dict):
        message = str(payload.get("message") or payload.get("msg") or payload.get("error") or "")
        code = payload.get("code")
    message_lower = message.lower()
    if code == 20003015 or "incorrect" in message_lower or "password" in message_lower:
        retryable = False
    raise BluettiAuthError(f"{step} failed with status {status}, code={code}", retryable=retryable)


def _common_headers(
    settings: BluettiAuthSettings,
    authorization: str | None = None,
    *,
    user_agent: str | None = None,
) -> dict[str, str]:
    headers = {
        "accept": "*/*",
        "x-os": settings.x_os,
        "x-app-ver": settings.x_app_ver,
        "accept-language": settings.accept_language,
        "user-agent": user_agent or settings.user_agent,
        "x-device-id": settings.auth_device_id,
        "x-os-ver": settings.x_os_ver,
        "x-app-key": settings.x_app_key,
    }
    if authorization:
        headers["authorization"] = authorization
    return headers


def _json_path(payload: Any, path: list[str]) -> Any:
    current = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _select_device(devices: list[dict[str, Any]], device_sn: str) -> dict[str, Any]:
    for device in devices:
        if str(device.get("sn") or "") == device_sn:
            return device
    if devices:
        return devices[0]
    raise BluettiAuthError("BLUETTI account does not list any devices", retryable=False)


def _split_host_port(host_port: str | None) -> tuple[str, int]:
    if not host_port:
        raise BluettiAuthError("could not determine BLUETTI MQTT host", retryable=True)
    host, separator, raw_port = host_port.partition(":")
    return host, int(raw_port if separator else "18760")


def _sid_from_token(token: str) -> str:
    parts = token.split(".")
    if len(parts) < 2:
        raise BluettiAuthError("authorization token does not contain x-sid part", retryable=True)
    return parts[1]


def _build_request_sign(
    sid: str,
    app_key: str,
    app_ver: str,
    os_name: str,
    current_utc_time: int,
    url: str,
) -> tuple[str, str]:
    params = {
        "currentUtcTime": format(current_utc_time, "x"),
        "url": url.replace(BASE_URL, ""),
        "x-app-key": app_key,
        "x-app-ver": app_ver,
        "x-os": os_name,
        "x-sid": sid,
    }
    base = "&".join("%s=%s" % (key, value) for key, value in sorted(params.items()))
    return base, hashlib.md5(base.encode("utf-8")).hexdigest().upper()


def _openssl_crypt(data: bytes, request_sign: str, decrypt: bool) -> bytes:
    key_hex = request_sign.encode("utf-8").hex()
    cmd = ["openssl", "enc", "-aes-256-ecb", "-nosalt", "-K", key_hex]
    if decrypt:
        cmd.append("-d")
    completed = subprocess.run(cmd, input=data, capture_output=True)
    if completed.returncode != 0:
        raise BluettiAuthError("openssl AES operation failed", retryable=True)
    return completed.stdout


def _decrypt_signature(x_signature: str, request_sign: str) -> str:
    cipher_bytes = bytes.fromhex(re.sub(r"\s+", "", x_signature))
    return _openssl_crypt(cipher_bytes, request_sign, decrypt=True).decode("utf-8")


def _encrypt_p12_password(password: str, request_sign: str) -> str:
    return _openssl_crypt(password.encode("utf-8"), request_sign, decrypt=False).hex()


def _build_kvalue(user_id: str, device_id: str) -> str:
    head = user_id[:2]
    tail = user_id[-2:]
    shared_head = SHARED_PRIVATE_KEY[:6]
    return head + shared_head + device_id + SHARED_PRIVATE_KEY.replace(shared_head, "") + tail


def _totp_encrypt(counter_bytes: bytes, key_bytes: bytes) -> bytes:
    counter_hash = hashlib.md5(counter_bytes).hexdigest().upper()
    key_hash = hashlib.md5(key_bytes).hexdigest().upper()
    return "".join(a + b for a, b in zip(key_hash, counter_hash)).encode("utf-8")


def _truncate_totp(data: bytes) -> str:
    offset = data[-1] & 0x0F
    value = (
        ((data[offset] & 0x7F) << 24)
        | ((data[offset + 1] & 0xFF) << 16)
        | ((data[offset + 2] & 0xFF) << 8)
        | (data[offset + 3] & 0xFF)
    ) % DIGITS_POWER[8]
    return str(value).rjust(8, "0")


def _header_ci(headers: dict[str, str], name: str) -> str | None:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def _pick_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _default_ca_path() -> Path | None:
    candidates = [
        Path("/etc/ssl/certs/ca-certificates.crt"),
        Path("/etc/ssl/cert.pem"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    openssl = shutil.which("openssl")
    if openssl:
        return None
    return None

