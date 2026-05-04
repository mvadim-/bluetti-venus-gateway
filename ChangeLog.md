# ChangeLog

## [2026-05-04 16:34] Disable unverified EP760 voltage alarms
- Fixed false Venus GUI high-voltage alarm found during Raspberry Pi GUI validation
- EP760 live Battery voltage was around `105V`, while previous default voltage alarm thresholds were inherited from a 48V-class battery profile
- Disabled voltage alarm thresholds by default until EP760-specific low/high limits are confirmed
- Added bridge model coverage proving unconfigured voltage thresholds do not raise HighVoltage/LowVoltage alarms
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-04 16:29] Persist boot repair through Venus rc.local
- Fixed reboot recovery found during Raspberry Pi Task 13 validation:
  - `/service` is a tmpfs on Venus OS, so service symlinks disappear after reboot
  - `bluetti-repair-on-boot` cannot repair service links if its own `/service` symlink is gone
- Updated installer to add a persistent `/data/rc.local` hook that runs `repair-if-needed.sh` during Venus `custom-rc-late.sh`
- The hook logs to `bluetti-repair-on-boot.log` and preserves config/cache/certs
- Verified locally with:
  - `bash -n venus/install-venus.sh venus/repair-if-needed.sh venus/services/bluetti-repair-on-boot/run`
  - `BLUETTI_RC_LOCAL=/private/tmp/bluetti-test-rc.local ./venus/install-venus.sh --dry-run`
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `git diff --check`

## [2026-05-04 16:21] Mark D-Bus services stale when collector stops
- Fixed D-Bus bridge stale behavior found during Raspberry Pi Task 13 validation:
  - bridge now recalculates snapshot freshness from `received_at` on every publish cycle
  - Battery, Grid, AC Load, and optional VE.Bus services are marked `/Connected = 0` after `BLUETTI_STALE_AFTER_SECONDS`
- Added `stale_after_seconds` to snapshot envelopes for diagnostics
- Fixed `status.sh` service parsing so `svstat` output like `down ..., normally up` reports as not running
- Added unit coverage for refreshed stale freshness and `svstat` parsing
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-04 15:57] Record local pre-hardware validation
- Added `docs/validation/20260504-local-pre-hardware.md` with Task 12 validation evidence
- Marked Task 12 complete in the copied implementation plan
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests` (`28` tests)
  - `python3 -m compileall -q src`
  - `bash -n venus/install-venus.sh venus/update-venus.sh venus/repair-if-needed.sh venus/status.sh venus/restart.sh venus/logs.sh venus/uninstall-venus.sh venus/build-offline-bundle.sh venus/lib/offline-bundle.sh venus/services/bluetti-collector/run venus/services/bluetti-dbus-bridge/run venus/services/bluetti-repair-on-boot/run`
  - `PYTHONPATH=backend/src python3 -m unittest backend.tests.bluetti.test_parser backend.tests.victron.test_bridge_model backend.tests.victron.test_projection_parity` in the reference `bluettiMonitor` repo (`11` tests)
  - v1 bridge service parity check against the reference Victron bridge model
  - `git diff --check`

## [2026-05-04 15:54] Complete Raspberry Pi deployment documentation
- Added canonical deploy guide at `docs/deploy/bluetti-venus-gateway-rpi5.md`
- Kept `docs/deploy/venus-gateway-rpi5.md` as a compatibility pointer
- Expanded README with expected D-Bus services and operations commands
- Documented fresh Venus OS setup, config fields, Git/offline update, repair, troubleshooting, and future PV/GUI notes
- Copied the updated implementation plan into `docs/plans/20260430-venus-gateway-rpi5.md`
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `bash -n venus/install-venus.sh venus/update-venus.sh venus/repair-if-needed.sh venus/status.sh venus/restart.sh venus/logs.sh venus/uninstall-venus.sh venus/build-offline-bundle.sh venus/lib/offline-bundle.sh venus/services/bluetti-collector/run venus/services/bluetti-dbus-bridge/run venus/services/bluetti-repair-on-boot/run`
  - `git diff --check`

## [2026-05-04 15:44] Complete offline bundle install path
- Added offline bundle verification/apply helper for manifest and checksum validation
- Updated `build-offline-bundle.sh` to include:
  - app source and Venus scripts under `app/`
  - `manifest.json` generated from `venus/bundle-manifest.template.json`
  - `system-packages.txt`
  - `checksums.txt`
- Excluded local secrets, cache, certs, logs, Python bytecode, supervise state, and macOS metadata from bundle artifacts
- Added `--offline-bundle` and `--dry-run --offline-bundle` handling to install/update scripts
- Updated README and Raspberry Pi deploy docs for live runtime and offline bundle recovery
- Verified locally with:
  - `bash -n venus/install-venus.sh venus/update-venus.sh venus/build-offline-bundle.sh venus/lib/offline-bundle.sh`
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `./venus/build-offline-bundle.sh`
  - `./venus/update-venus.sh --dry-run --offline-bundle dist/bluetti-venus-gateway-rpi5-aarch64-v0.1.0.tar.gz`
  - valid, missing, corrupt, and apply-to-temp bundle checks through `venus/lib/offline-bundle.sh`
  - `git diff --check`

## [2026-05-01 21:37] Attach Venus D-Bus services to GLib main loop
- Added D-Bus GLib main loop bootstrap before creating Venus `SystemBus` connections for `vedbus`
- Added lightweight GLib event processing in the D-Bus bridge refresh loop so exported services can respond to D-Bus traffic
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-01 21:34] Allow BLUETTI MQTT private CA fallback
- Added `BLUETTI_MQTT_TLS_VERIFY_SERVER` config to control MQTT server certificate verification
- Defaulted verification to disabled because the BLUETTI broker presents a private PowerOak-issued server certificate, does not send the issuer chain, and uses a weak 1880-bit RSA leaf key that Venus OpenSSL rejects under normal CA verification
- Kept TLS 1.2, configured ciphers, and client certificate authentication enabled when server verification is disabled
- Added config unit coverage for the new switch
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `bash -n venus/install-venus.sh venus/update-venus.sh venus/repair-if-needed.sh venus/status.sh venus/restart.sh venus/logs.sh venus/uninstall-venus.sh venus/build-offline-bundle.sh venus/services/bluetti-collector/run venus/services/bluetti-dbus-bridge/run venus/services/bluetti-repair-on-boot/run`
  - `git diff --check`

## [2026-05-01 21:29] Use BLUETTI P12 CA chain for MQTT TLS
- Updated BLUETTI P12 extraction to export `ca.crt` from the certificate bundle in addition to `client.crt` and `client.key`
- Collector TLS now prefers the extracted non-empty `ca.crt` for MQTT broker verification and falls back to system CA only when no P12 CA chain is available
- Removed stale TLS export artifacts before each extraction so a replaced P12 cannot reuse an old CA/key/cert file
- Added unit coverage for preferring an extracted CA file
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-01 21:24] Support paho MQTT 2 callback API
- Updated the live collector MQTT client construction to pass `CallbackAPIVersion.VERSION1` when running on Venus OS `python3-paho-mqtt` 2.x
- Keeps fallback construction for older paho MQTT versions that do not require callback API selection
- Verified on Raspberry Pi 5 that auth/P12 now reaches MQTT context preparation before this paho API mismatch

## [2026-05-01 21:22] Require and use OpenSSL legacy provider for BLUETTI P12
- Added OpenSSL legacy provider detection and `openssl pkcs12 -legacy` fallback for BLUETTI P12 key/cert extraction
- Updated Venus installer prerequisites to require:
  - Python `cryptography`
  - `/usr/lib/ossl-modules/legacy.so` from opkg package `openssl-ossl-module-legacy`
- Added unit coverage for the PKCS12 fallback runner
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `bash -n venus/install-venus.sh venus/update-venus.sh venus/repair-if-needed.sh venus/status.sh venus/restart.sh venus/logs.sh venus/uninstall-venus.sh venus/build-offline-bundle.sh venus/services/bluetti-collector/run venus/services/bluetti-dbus-bridge/run venus/services/bluetti-repair-on-boot/run`

## [2026-05-01 21:18] Add cryptography P12 extraction fallback
- Updated BLUETTI P12 extraction so Venus OS does not require the missing OpenSSL `legacy.so` provider
- Collector now first tries system `openssl pkcs12` without legacy provider and falls back to system `python3-cryptography` PKCS12 parsing when OpenSSL cannot export the key/cert
- Verified on Raspberry Pi 5 that the previous blocker was OpenSSL provider lookup for `/usr/lib/ossl-modules/legacy.so`
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-01 21:16] Accept BLUETTI UTC time string responses
- Updated BLUETTI auth parsing so `/api/midppkic/cert/app/v2/now/utc-time` accepts numeric string `data` values as well as JSON integers
- Verified on Raspberry Pi 5 that the live response shape is `code=0`, `message=OK`, and `data` as a string such as `1777630585000`
- Added unit coverage for UTC integer coercion
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-01 21:07] Add live BLUETTI MQTT collector path
- Added BLUETTI cloud auth and MQTT context preparation for the standalone gateway:
  - login token retrieval
  - user/device lookup
  - server time and P12 download
  - client certificate/key extraction through system `openssl`
  - MQTT topic, broker, username, and password derivation
- Added live paho MQTT collector behavior:
  - connects with Venus OS system `python3-paho-mqtt`
  - subscribes to the device `PUB/...` topic
  - publishes Modbus read requests to the matching `SUB/...` topic
  - uses the configured `vrm-minimal` polling profile
  - refreshes auth periodically
- Added minimal EP760 payload decoding for v1 VRM streams:
  - `HOME_INFO (100)`
  - `INV_GRID_INFO (1300)`
  - `INV_LOAD_INFO (1400)`
  - `INV_INVERTER_INFO (1500)`
- Collector now writes `/run/bluetti-gateway/latest.json` from live decoded state when BLUETTI MQTT replies arrive
- Added config keys for auth device id, MQTT client id, payload format, and ciphers
- Added validation for untouched template credentials/device serial values after Raspberry Pi testing confirmed the current Pi config still contains placeholders
- Collector and D-Bus bridge now park with a clear log message on invalid config instead of crash-looping under runit
- BLUETTI `account does not exist` login responses are classified as non-retryable auth failures
- Added auth/parser unit coverage
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

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
## [2026-05-04 16:40] Record Raspberry Pi hardware validation
- Continued Task 13 from `docs/plans/20260430-venus-gateway-rpi5.md`
- Added `docs/validation/20260504-raspberry-pi-hardware.md`
- Updated deploy notes with:
  - Venus OS time/NTP risk
  - expected EP760 voltage alarm state
  - persistent `/data/rc.local` repair hook behavior
- Marked completed Raspberry Pi validation items in the copied implementation plan
- Left local GUI Overview and VRM Portal checks open for user confirmation
- Verified live Raspberry Pi status on `venus.local`:
  - gateway commit `5c23951`
  - collector, D-Bus bridge, repair service, and `vrmlogger` running
  - latest telemetry age `1s`
  - Battery, AC Input, and AC Load D-Bus services present
  - Battery `/Connected = 1`, `/Alarms/HighVoltage = 0`, `/Alarms/LowVoltage = 0`
## [2026-05-04 20:56] Record inverter passthrough GUI validation
- Deployed commit `3d7f92e` to Raspberry Pi and restarted gateway services
- Verified live D-Bus values:
  - `com.victronenergy.inverter.ep760_32 /State = 8`
  - `com.victronenergy.inverter.ep760_32 /Ac/Out/L1/P = 0`
  - `com.victronenergy.inverter.ep760_32 /Ac/Out/L1/I = 0`
  - `com.victronenergy.system /Ac/Consumption/L1/Power` matches Grid power
- Verified with the Codex in-app browser that Venus GUIv2 renders the Inverter / Charger card as
  `Pass-thru` while Grid and AC Loads remain visible

## [2026-05-04 21:05] Publish inverter AC input and phase energy paths
- Added active AC input paths to `com.victronenergy.inverter.ep760_32` so Venus GUI/VRM can identify
  the EP760 grid input while the inverter remains in pass-through
- Kept inverter AC output power isolated from standalone AC Loads to avoid returning to system
  consumption double-counting
- Added phase-level energy counters for Grid and AC Loads:
  - `/Ac/L1/Energy/Forward`
  - `/Ac/L1/Energy/Reverse` for Grid
- Added unit coverage for inverter active input state and VRM-compatible phase energy paths
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-04 21:13] Add Multi compatibility service for Venus systemcalc
- Added `com.victronenergy.multi.ep760_32` compatibility output enabled by `BLUETTI_ENABLE_MULTI_COMPAT=1`
  by default
- Published Grid as Multi `/Ac/In/1` and AC Loads as Multi `/Ac/Out`, allowing Venus systemcalc and
  VRM to derive the active AC source without relying on unsupported inverter active-input monitoring
- Updated status output to report the Multi D-Bus service
- Updated the Venus config/deploy examples and unit coverage for the new compatibility service
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-04 21:17] Record Multi service Raspberry Pi validation
- Deployed commit `76ea8c6` to Raspberry Pi and restarted gateway services
- Verified live D-Bus values:
  - `com.victronenergy.multi.ep760_32 /State = 8`
  - `com.victronenergy.multi.ep760_32 /Ac/In/1/Type = 1`
  - `com.victronenergy.multi.ep760_32 /Ac/In/1/L1/P` tracks Grid power
  - `com.victronenergy.multi.ep760_32 /Ac/Out/L1/P` tracks AC Loads power
  - `com.victronenergy.system /Ac/ActiveIn/Source = 1`
- Verified with the Codex in-app browser that Venus GUIv2 shows the Grid-to-Inverter and
  Inverter-to-AC-Loads flow while Inverter / Charger remains `Pass-thru`
- Updated Raspberry Pi hardware validation notes with the live evidence

## [2026-05-04 21:33] Audit Victron model contracts against BLUETTI telemetry
- Audited live BLUETTI snapshot fields against Venus OS v3.72 systemcalc and VRM logger service
  models
- Added `docs/validation/20260504-victron-model-audit.md` with supported, derived, and intentionally
  unsupported Victron paths
- Aligned `inverter`, `multi`, and optional `vebus` compatibility outputs:
  - shared pass-through/inverting state contract
  - full single-phase AC input paths
  - battery SOC and temperature paths where VRM logs them
- Added contract unit coverage for Battery, Grid, AC Loads, Inverter, Multi, and optional VE.Bus
  paths required by Venus systemcalc/VRM logger
- Verified local Venus GUIv2 through the Codex in-app browser
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-04 20:55] Fix inverter passthrough state mapping
- Fixed `com.victronenergy.inverter.ep760_32` state mapping for EP760 grid passthrough
- The bridge now publishes `/State = 8` (`Pass-thru` in Venus GUIv2) when grid input is present and
  real inverter output power is zero or near zero
- The bridge keeps `/State = 9` (`Inverting`) only when `inv_output_power_w` or `inverter_power_w`
  indicates real inverter output above the noise threshold
- Suppressed near-zero inverter output current when output power is effectively zero, so passthrough
  does not show a misleading inverter AC output current
- Added unit coverage for passthrough and real inverter-output states

## [2026-05-04 17:06] Record inverter service Raspberry Pi validation
- Updated Raspberry Pi hardware validation notes after deploying commit `154033a`
- Recorded user findings:
  - local Venus GUI showed Battery and Grid/AC Input, but inverter was off and AC Loads was missing
  - VRM showed Total consumption and Battery values, while other blocks had no readings
  - `ntp` was installed manually through opkg before being added to the installer
- Recorded live post-fix checks on Raspberry Pi:
  - `D-Bus inverter service: present`
  - `com.victronenergy.inverter.ep760_32 /Mode = 3`
  - `com.victronenergy.inverter.ep760_32 /State = 9`
  - `com.victronenergy.system /Ac/HasAcLoads = 1`
  - `com.victronenergy.system /Ac/Consumption/L1/Power` matches grid power and no longer
    double-counts inverter passthrough load
- Left final local GUI and VRM Portal visual confirmation open for the user after this deployment

## [2026-05-04 17:04] Avoid double-counting inverter passthrough load
- During live Raspberry Pi validation of `com.victronenergy.inverter.ep760_32`, systemcalc
  `/Ac/Consumption/L1/Power` became approximately `grid + inverter output`
- Updated inverter projection to prefer real inverter-output fields:
  - `inv_output_power_w`
  - `inverter_power_w`
  - `inv_output_current_a`
- Kept `ac_load_power_w` on the standalone `acload` service instead of reusing it as inverter output
  while grid input is present
- Verified locally with:
  - `env PYTHONPATH=src python3 -m unittest discover -s tests`
  - `python3 -m compileall -q src`
  - `git diff --check`

## [2026-05-04 16:58] Add Venus inverter service and installer NTP setup
- Continued Raspberry Pi Task 13 follow-up from user GUI/VRM validation
- Added default `com.victronenergy.inverter.ep760_32` publishing with Venus-compatible AC output
  paths:
  - `/Ac/Out/L1/P`
  - `/Ac/Out/L1/V`
  - `/Ac/Out/L1/I`
  - `/Ac/Out/L1/F`
  - `/Mode`
  - `/State`
- Kept `com.victronenergy.acload.ep760_31` for VRM logging compatibility while adding the inverter
  service required by Venus OS v3.72 systemcalc/GUIv2
- Added config keys for enabling and naming the inverter service
- Updated `status.sh` to report the inverter D-Bus service
- Updated `install-venus.sh` to install/configure `ntp` by default through opkg, add external NTP
  servers, and restart `ntpd`
- Updated README, Raspberry Pi deploy docs, and implementation plan notes
