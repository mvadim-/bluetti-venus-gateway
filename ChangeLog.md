# ChangeLog

## [2026-05-01 21:02] Ignore runit supervise state in gateway repo
- Added `venus/services/*/supervise/` to `.gitignore` because Venus runit creates per-service supervise state inside symlinked service directories
- Verified on Raspberry Pi 5 after the config parsing fix:
  - `bluetti-collector` and `bluetti-dbus-bridge` run as Python module processes
  - `dbus-bridge.ready` is created
  - collector and D-Bus bridge logs are written
  - missing snapshot and missing D-Bus services remain expected until live collector or fixture telemetry is enabled

## [2026-05-01 20:59] Fix Venus service config parsing under runit
- Removed shell sourcing of `/data/bluetti-gateway/bluetti-gateway.env` from `bluetti-collector` and `bluetti-dbus-bridge` run scripts
- Kept config parsing inside Python so values with spaces such as `BLUETTI EP760` do not break runit startup
- Quoted custom-name values in the example config for safer manual shell usage
- Verified on Raspberry Pi 5 that the previous failure came from `readproctitle service errors` reporting `bluetti-gateway.env: line 21: EP760`
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `bash -n venus/install-venus.sh venus/update-venus.sh venus/repair-if-needed.sh venus/status.sh venus/restart.sh venus/logs.sh venus/uninstall-venus.sh venus/build-offline-bundle.sh venus/services/bluetti-collector/run venus/services/bluetti-dbus-bridge/run venus/services/bluetti-repair-on-boot/run`

## [2026-05-01 20:54] Improve Venus gateway service diagnostics
- Updated `install-venus.sh` to create empty collector, D-Bus bridge, and repair log files during install so `logs.sh` has deterministic targets immediately after service registration
- Updated `status.sh` service reporting to include the raw `svstat` summary for gateway services and `vrmlogger`
- Changed repair status from a simple installed check to the same service-state reporting as collector and D-Bus bridge
- Added status lines for collector/D-Bus ready files and log file presence/size
- Added VRM Portal ID fallback through `/sbin/get-unique-id` and `PATH` lookup before returning `unknown`
- Added status helper coverage for file state output
- Verified with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `bash -n venus/install-venus.sh venus/update-venus.sh venus/repair-if-needed.sh venus/status.sh venus/restart.sh venus/logs.sh venus/uninstall-venus.sh venus/build-offline-bundle.sh venus/services/bluetti-collector/run venus/services/bluetti-dbus-bridge/run venus/services/bluetti-repair-on-boot/run`

## [2026-05-01 20:49] Fix Venus runit repair loop and status output
- Fixed `bluetti-repair-on-boot` so the one-shot repair runs once per service start and then stays alive with a long sleep instead of exiting and being restarted repeatedly by runit
- Updated `install-venus.sh` to wait for each new service's `supervise/control` file before calling `svc -u`, avoiding immediate `svc: file does not exist` warnings after symlink creation
- Normalized Venus OS version detection to the first non-empty line so multi-line `/opt/victronenergy/version` files render as a single version
- Added VRM Portal ID fallback through `/opt/victronenergy/serial-starter/get-unique-id` with a bounded timeout
- Updated `logs.sh` to show missing service log files explicitly
- Parked the bootstrap collector process when no fixture source is configured so runit does not restart it repeatedly before the live BLUETTI collector is implemented
- Rate-limited missing snapshot logs in the D-Bus bridge to once per minute
- Added status helper coverage for multi-line version files
- Verified with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `bash -n venus/install-venus.sh venus/update-venus.sh venus/repair-if-needed.sh venus/status.sh venus/restart.sh venus/logs.sh venus/uninstall-venus.sh venus/build-offline-bundle.sh venus/services/bluetti-collector/run venus/services/bluetti-dbus-bridge/run venus/services/bluetti-repair-on-boot/run`

## [2026-05-01 20:44] Bootstrap Raspberry Pi 5 Venus gateway package
- Added the standalone `bluetti-venus-gateway` package skeleton with no production `pip` dependencies
- Added config parsing/validation, secret masking, VRM-minimal polling profile, atomic snapshot store, and telemetry envelope helpers
- Added the v1 EP760 Venus bridge payload model for Battery, AC Input, and AC Loads, with optional disabled VE.Bus compatibility
- Added Venus OS D-Bus publisher/runtime entrypoints and service wrappers for:
  - `bluetti-collector`
  - `bluetti-dbus-bridge`
  - `bluetti-repair-on-boot`
- Added Venus install/update/repair/status/restart/logs/uninstall/offline-bundle scripts and the local env template
- Added Raspberry Pi 5 deployment notes under `docs/deploy/venus-gateway-rpi5.md`
- Current bootstrap limitation: live BLUETTI cloud/MQTT collector is not implemented yet; collector supports fixture mode through `BLUETTI_COLLECTOR_FIXTURE_JSON`
- Verified with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `bash -n venus/install-venus.sh venus/update-venus.sh venus/repair-if-needed.sh venus/status.sh venus/restart.sh venus/logs.sh venus/uninstall-venus.sh venus/build-offline-bundle.sh venus/services/bluetti-collector/run venus/services/bluetti-dbus-bridge/run venus/services/bluetti-repair-on-boot/run`
