# Local Pre-Hardware Validation - 2026-05-04

Scope: Task 12 from `docs/plans/20260430-venus-gateway-rpi5.md`.

## Commands

```bash
env PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall -q src
bash -n venus/install-venus.sh venus/update-venus.sh venus/repair-if-needed.sh venus/status.sh venus/restart.sh venus/logs.sh venus/uninstall-venus.sh venus/build-offline-bundle.sh venus/lib/offline-bundle.sh venus/services/bluetti-collector/run venus/services/bluetti-dbus-bridge/run venus/services/bluetti-repair-on-boot/run
git diff --check
```

Reference checks run from `/Users/mvadym/Documents/Dev/bluettiMonitor`:

```bash
PYTHONPATH=backend/src python3 -m unittest backend.tests.bluetti.test_parser backend.tests.victron.test_bridge_model backend.tests.victron.test_projection_parity
```

Bridge parity check:

```text
bridge parity ok: com.victronenergy.battery.ep760_41, com.victronenergy.grid.ep760_30, com.victronenergy.acload.ep760_31
```

## Results

- Gateway unit tests: `28` passed.
- Reference parser/bridge tests: `11` passed.
- Python compile check: passed.
- Shell syntax check: passed.
- Whitespace diff check: passed.
- v1 bridge service names match the reference Victron bridge expectations.
- No gateway implementation code was added to the legacy `bluettiMonitor` runtime tree.

## Remaining Hardware-Only Checks

- Confirm Battery, AC Input, and AC Loads in local Venus GUI.
- Confirm Battery, AC Input, and AC Loads in VRM Portal/VRM mobile app.
- Stop collector temporarily and confirm stale telemetry sets `/Connected = 0`.
- Reboot Raspberry Pi and confirm services recover.
- Run `repair-if-needed.sh --force` on the Raspberry Pi and confirm config/cache/certs are preserved.
