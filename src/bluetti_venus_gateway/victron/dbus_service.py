from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Any

from bluetti_venus_gateway.victron.bridge_model import iter_venus_service_payloads


LOGGER = logging.getLogger(__name__)
BUS_ITEM_INTERFACE = "com.victronenergy.BusItem"
SETTINGS_SERVICE_NAME = "com.victronenergy.settings"
SETTINGS_BATTERY_PATH = "/Settings/SystemSetup/BatteryService"

VELIB_PYTHON_PATHS = [
    Path("/opt/victronenergy/dbus-systemcalc-py/ext/velib_python"),
    Path("/opt/victronenergy/vrmlogger/ext/velib_python"),
    Path("/opt/victronenergy/dbus-digitalinputs/ext/velib_python"),
]


def bootstrap_velib_python_path() -> None:
    for candidate in VELIB_PYTHON_PATHS:
        if candidate.exists():
            candidate_str = str(candidate)
            if candidate_str not in sys.path:
                sys.path.insert(0, candidate_str)


class VenusDbusPublisher:
    def __init__(self, *, process_name: str, process_version: str, connection_name: str) -> None:
        bootstrap_velib_python_path()
        import dbus
        from vedbus import VeDbusService

        self._dbus = dbus
        self._service_type = VeDbusService
        self._settings_bus = dbus.SystemBus()
        self._services: dict[str, Any] = {}
        self._service_buses: dict[str, Any] = {}
        self._process_name = process_name
        self._process_version = process_version
        self._connection_name = connection_name
        self._selected_battery_service: str | None = None

    def publish(self, bridge_payload: dict[str, Any]) -> None:
        for service_name, values in iter_venus_service_payloads(bridge_payload):
            if service_name not in self._services:
                self._initialize_service(service_name, values)
            self._update_values(service_name, values)
        self._select_battery_service_if_available(bridge_payload)

    def _initialize_service(self, service_name: str, values: dict[str, Any]) -> None:
        LOGGER.info("Initializing Venus D-Bus service %s", service_name)
        service_bus = self._dbus.SystemBus(private=True)
        service = self._service_type(service_name, bus=service_bus, register=False)
        service.add_path("/Mgmt/ProcessName", self._process_name)
        service.add_path("/Mgmt/ProcessVersion", self._process_version)
        service.add_path("/Mgmt/Connection", self._connection_name)
        for path, value in sorted(values.items()):
            service.add_path(path, value)
        service.register()
        self._service_buses[service_name] = service_bus
        self._services[service_name] = service

    def _update_values(self, service_name: str, values: dict[str, Any]) -> None:
        service = self._services[service_name]
        for path, value in values.items():
            try:
                service[path] = value
            except KeyError:
                service.add_path(path, value)

    def _select_battery_service_if_available(self, bridge_payload: dict[str, Any]) -> None:
        battery = bridge_payload.get("venus_battery") or {}
        service_name = str(battery.get("service_name") or "").strip()
        values = battery.get("values") or {}
        device_instance = values.get("/DeviceInstance")
        if not service_name or not isinstance(device_instance, int):
            return
        service_class = ".".join(service_name.split(".")[:3])
        setting_value = f"{service_class}/{device_instance}"
        if setting_value == self._selected_battery_service:
            return
        try:
            battery_service = self._settings_bus.get_object(SETTINGS_SERVICE_NAME, SETTINGS_BATTERY_PATH)
            iface = self._dbus.Interface(battery_service, BUS_ITEM_INTERFACE)
            iface.SetValue(setting_value)
            self._selected_battery_service = setting_value
            LOGGER.info("Selected Venus battery service %s", setting_value)
        except self._dbus.exceptions.DBusException as exc:
            if exc.get_dbus_name() in {
                "org.freedesktop.DBus.Error.NameHasNoOwner",
                "org.freedesktop.DBus.Error.ServiceUnknown",
            }:
                LOGGER.info("Venus settings service unavailable; battery selection deferred")
                return
            LOGGER.exception("Failed to select Venus battery service %s", setting_value)

