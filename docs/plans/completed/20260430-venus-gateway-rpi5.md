# Raspberry Pi 5 Venus Gateway Plan - Completed

Completed date: 2026-05-05

## Scope

Build a standalone native Venus OS gateway for BLUETTI EP760 / PBOX on Raspberry Pi 5.

The production flow is:

```text
BLUETTI cloud/MQTT
  -> bluetti-collector
  -> /run/bluetti-gateway/latest.json
  -> bluetti-dbus-bridge
  -> Venus OS D-Bus
  -> native vrmlogger
  -> VRM Portal / VRM mobile app
```

The gateway does not require Docker, MongoDB, a backend API, a PWA/frontend, or custom VRM upload
logic. It runs directly on Venus OS and relies on stock `vrmlogger`.

## Completed Outcomes

- Created standalone `bluetti-venus-gateway` repository and runtime package.
- Implemented BLUETTI authentication, MQTT polling, parser reuse, telemetry envelope, and volatile
  snapshot store.
- Added native Venus OS installer, updater, restart, status, logs, repair, and offline-bundle scripts.
- Added runit services:
  - `bluetti-collector`
  - `bluetti-dbus-bridge`
  - `bluetti-repair-on-boot`
- Added D-Bus projections for:
  - `com.victronenergy.battery.ep760_41`
  - `com.victronenergy.grid.ep760_30`
  - `com.victronenergy.acload.ep760_31`
  - `com.victronenergy.inverter.ep760_32`
  - `com.victronenergy.multi.ep760_32`
- Added installer-managed NTP setup for Venus OS targets.
- Added status diagnostics for config, ready files, logs, telemetry age, D-Bus services, `vrmlogger`,
  and offline bundle presence.
- Added local unit tests for parser, telemetry, snapshot, Victron bridge contracts, service scripts,
  status output, and installer behavior.
- Validated on Raspberry Pi 5 running Venus OS v3.72.
- Validated local Venus GUIv2 and VRM Portal behavior with Grid, Battery, Inverter / Charger,
  AC Loads, Essential Loads / Total consumption, and energy-flow lines.

## Runtime Paths

```text
repo checkout: /data/bluetti-venus-gateway
local config:  /data/bluetti-gateway/bluetti-gateway.env
logs:          /data/bluetti-gateway/logs/
snapshot:      /run/bluetti-gateway/latest.json
services:      /service/bluetti-collector
               /service/bluetti-dbus-bridge
               /service/bluetti-repair-on-boot
```

## Key Signal Policy

- Grid / AC Input is sourced from `INV_GRID_INFO (1300)` where possible.
- AC Loads is sourced from `INV_LOAD_INFO (1400)` and `ac_load_power_w`.
- Inverter output state is sourced from real inverter-output fields such as `inv_output_power_w` or
  `inverter_power_w`, not from AC load power.
- EP760 grid passthrough publishes inverter `/State = 8` (`Pass-thru`) when grid input is present and
  real inverter output is zero or near zero.
- Real inverter output publishes `/State = 9` (`Inverting`) only when inverter-output fields indicate
  actual output above the noise threshold.
- Missing or unsupported Victron fields should remain absent, `None`, or stale-safe instead of being
  filled with unrelated BLUETTI values.

## Validation Evidence

Detailed validation records:

- `docs/validation/20260504-local-pre-hardware.md`
- `docs/validation/20260504-raspberry-pi-hardware.md`
- `docs/validation/20260504-victron-model-audit.md`

Common local checks:

```bash
env PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src
git diff --check
bash -n venus/*.sh venus/services/*/run
```

Common Raspberry Pi checks:

```bash
cd /data/bluetti-venus-gateway
./venus/install-venus.sh
./venus/restart.sh
./venus/status.sh
./venus/logs.sh 120
```

Use the Codex in-app browser / browser-use plugin for Venus GUI checks at
`http://venus.local/gui-v2/`.

## Remaining Future Work

- Add PV/Solar D-Bus projection once BLUETTI PV fields are validated against Venus/VRM expectations.
- Add richer pack diagnostics once `PACK_MAIN_INFO (6000)` and `PACK_ITEM_INFO (6100)` are validated
  on real payloads.
- Add warning/fault name mapping for BLUETTI alarm/fault bitfields.
- Decide whether to publish versioned release artifacts beyond the existing offline bundle workflow.

## Done Criteria

The plan is complete because:

- Gateway runtime runs directly on Venus OS.
- Raspberry Pi services recover through runit and repair-on-boot.
- Local GUIv2 shows the expected EP760 topology and energy-flow direction.
- VRM shows live Grid, Battery, Essential Loads / Total consumption, and inverter compatibility state.
- The repository can be developed independently from any previous application stack.
