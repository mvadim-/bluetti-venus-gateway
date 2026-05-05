from __future__ import annotations

import unittest

from bluetti_venus_gateway.victron.bridge_model import VenusBridgeSettings
from bluetti_venus_gateway.victron.dbus_service import SETTINGS_GUI_GAUGE_AUTO_MAX_PATH
from bluetti_venus_gateway.victron.dbus_service import SETTINGS_GUI_GRID_CURRENT_MAX_PATH
from bluetti_venus_gateway.victron.dbus_service import SETTINGS_GUI_GRID_CURRENT_MIN_PATH
from bluetti_venus_gateway.victron.dbus_service import SETTINGS_GUI_LOAD_WITHOUT_AC_IN_CURRENT_MAX_PATH
from bluetti_venus_gateway.victron.dbus_service import SETTINGS_GUI_LOAD_WITH_AC_IN_CURRENT_MAX_PATH
from bluetti_venus_gateway.victron.dbus_service import _gui_gauge_setting_values


class DbusServiceTests(unittest.TestCase):
    def test_gui_gauge_settings_use_ep760_fixed_ranges(self) -> None:
        self.assertEqual(
            _gui_gauge_setting_values(VenusBridgeSettings()),
            (
                (SETTINGS_GUI_GAUGE_AUTO_MAX_PATH, 0),
                (SETTINGS_GUI_GRID_CURRENT_MIN_PATH, 0.0),
                (SETTINGS_GUI_GRID_CURRENT_MAX_PATH, 50.0),
                (SETTINGS_GUI_LOAD_WITH_AC_IN_CURRENT_MAX_PATH, 33.0),
                (SETTINGS_GUI_LOAD_WITHOUT_AC_IN_CURRENT_MAX_PATH, 33.0),
            ),
        )

    def test_gui_gauge_settings_can_leave_venus_auto_max_enabled(self) -> None:
        self.assertEqual(
            _gui_gauge_setting_values(VenusBridgeSettings(gui_gauge_auto_max=True)),
            ((SETTINGS_GUI_GAUGE_AUTO_MAX_PATH, 1),),
        )


if __name__ == "__main__":
    unittest.main()
