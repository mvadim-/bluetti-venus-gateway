# ChangeLog

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
