# Raspberry Pi Hardware Validation - 2026-05-04

Target:

```text
host: venus.local
device: Raspberry Pi 5
Venus OS: v3.72
VRM Portal ID: 2ccf672c2794
gateway commit: 76ea8c6
Python: 3.12.12
OpenSSL: 3.5.5
```

## Runtime Status

Final live status after deployment, reboot recovery, and alarm-threshold fix:

```text
bluetti-collector: running
bluetti-dbus-bridge: running
bluetti-repair-on-boot: running
vrmlogger: running
collector ready file: present
dbus bridge ready file: present
latest telemetry age: 1s
D-Bus battery service: present
D-Bus grid service: present
D-Bus acload service: present
D-Bus inverter service: present
D-Bus multi service: present
```

Expected D-Bus services were present:

```text
com.victronenergy.battery.ep760_41
com.victronenergy.grid.ep760_30
com.victronenergy.acload.ep760_31
com.victronenergy.inverter.ep760_32
com.victronenergy.multi.ep760_32
```

Battery alarm paths after the EP760 voltage-threshold correction:

```text
/Connected: 1
/Alarms/HighVoltage: 0
/Alarms/LowVoltage: 0
```

Inverter/servicecalc state after the GUI/VRM follow-up fix:

```text
com.victronenergy.inverter.ep760_32 /Connected: 1
com.victronenergy.inverter.ep760_32 /Mode: 3
com.victronenergy.inverter.ep760_32 /State: 8
com.victronenergy.inverter.ep760_32 /Ac/Out/L1/P: 0W
com.victronenergy.inverter.ep760_32 /Ac/Out/L1/V: 231.5V
com.victronenergy.inverter.ep760_32 /Ac/Out/L1/I: 0A
com.victronenergy.system /Ac/HasAcLoads: 1
com.victronenergy.system /Ac/Grid/L1/Power: 380W
com.victronenergy.system /Ac/Consumption/L1/Power: 380W
com.victronenergy.system /Ac/ConsumptionOnOutput/L1/Power: 0W
```

After commit `3d7f92e`, the Codex in-app browser showed Venus GUIv2 rendering the Inverter / Charger
card as `Pass-thru` with Grid and AC Loads both around `332W`.

After commit `76ea8c6`, the Multi compatibility service fixed Venus systemcalc active-source
detection:

```text
com.victronenergy.multi.ep760_32 /Ac/In/1/Type: 1
com.victronenergy.multi.ep760_32 /Ac/In/1/L1/P: 433W
com.victronenergy.multi.ep760_32 /Ac/Out/L1/P: 438W
com.victronenergy.multi.ep760_32 /State: 8
com.victronenergy.multi.ep760_32 /Mode: 3
com.victronenergy.system /Ac/ActiveIn/Source: 1
com.victronenergy.system /Ac/ActiveIn/L1/Power: 432W
com.victronenergy.system /Ac/Consumption/L1/Power: 434W
com.victronenergy.system /Ac/ConsumptionOnOutput/L1/Power: 434W
```

The Codex in-app browser screenshot after commit `76ea8c6` showed Grid `435W`, Inverter / Charger
`Pass-thru`, AC Loads `433W`, and an animated energy-flow line from Grid to Inverter / Charger and
from Inverter / Charger to AC Loads.

## Validation Performed

- Deployed the standalone gateway checkout to `/data/bluetti-venus-gateway`.
- Installed with `./venus/install-venus.sh` while preserving `/data/bluetti-gateway/bluetti-gateway.env`.
- Restarted `bluetti-collector`, `bluetti-dbus-bridge`, and `bluetti-repair-on-boot`.
- Confirmed live telemetry snapshot generation under `/run/bluetti-gateway/latest.json`.
- Confirmed D-Bus Battery, AC Input, and AC Load services are registered.
- Confirmed `vrmlogger` is running.
- Forced stale telemetry by stopping `bluetti-collector`; after the stale threshold, all three
  D-Bus services kept their definitions and switched `/Connected` to `0`.
- Restarted `bluetti-collector`; live telemetry recovered and all three services returned
  `/Connected` to `1`.
- Ran `./venus/repair-if-needed.sh --force`; repair preserved config and left runtime healthy.
- Rebooted the Raspberry Pi. Because `/service` is tmpfs on this Venus OS image, the boot validation
  exposed lost service symlinks. The installer now persists a `/data/rc.local` hook so
  `repair-if-needed.sh` restores links during boot.
- Confirmed automatic recovery after reboot with collector, D-Bus bridge, repair service, telemetry,
  and D-Bus services present.
- Checked local Venus GUI after the voltage-alarm fix. The prior `High voltage` notification moved to
  inactive state after D-Bus alarm paths were cleared.
- After user GUI validation, added a native `com.victronenergy.inverter.ep760_32` service because
  Venus OS v3.72 systemcalc/GUIv2 does not use standalone `acload` for `/Ac/HasAcLoads`.
- After live deploy, corrected inverter output mapping to use BLUETTI `inv_output_power_w` instead of
  duplicating `ac_load_power_w`; this keeps Total consumption from double-counting grid passthrough
  load.
- Corrected inverter state mapping so grid passthrough publishes `/State = 8` (`Pass-thru`) instead
  of `/State = 9` (`Inverting`) when real inverter output power is zero.
- Added `com.victronenergy.multi.ep760_32` compatibility output because Venus OS v3.72 systemcalc
  does not subscribe to active AC input paths on `com.victronenergy.inverter`; the Multi service
  publishes Grid as `/Ac/In/1` and AC Loads as `/Ac/Out`.
- Added phase-level energy paths for Grid and AC Loads so VRM has the service-specific counters it
  expects:
  - `/Ac/L1/Energy/Forward`
  - `/Ac/L1/Energy/Reverse` for Grid
- Installed and configured `ntp` through `install-venus.sh`. `/etc/ntp.conf` now has the gateway NTP
  marker block with `time.cloudflare.com`, `time.google.com`, `0.pool.ntp.org`, and `1.pool.ntp.org`;
  the local hardware clock fallback is commented out.

## Hardware Findings Fixed During Validation

- Stale collector failure did not disconnect D-Bus services. Fixed by refreshing snapshot freshness in
  the D-Bus bridge publish loop.
- `status.sh` misclassified `svstat` output containing `down ..., normally up` as running. Fixed by
  requiring the status text to start with `up`.
- `/service` is tmpfs on the tested Venus OS image, so service symlinks disappeared after reboot.
  Fixed by installing a persistent `/data/rc.local` repair hook.
- EP760 battery voltage is around `105V`; previous default voltage alarm thresholds were 48V-class and
  caused a false local GUI high-voltage alarm. Voltage alarms are disabled by default until verified
  EP760 thresholds are configured.
- Venus GUI/VRM did not use standalone `com.victronenergy.acload` as expected on Venus OS v3.72.
  Added `com.victronenergy.inverter.ep760_32` with native inverter AC-out paths so systemcalc sees AC
  loads and VRM has inverter output paths to log.
- Venus systemcalc kept `/Ac/ActiveIn/Source = 240` after inverter active-input paths were added,
  because that Venus OS version monitors active input on `com.victronenergy.multi`, not
  `com.victronenergy.inverter`. Fixed by adding `com.victronenergy.multi.ep760_32`.

## Operational Notes

- The Raspberry Pi system clock was wrong during validation and was manually corrected to
  `2026-05-04` UTC. `ntp` is now installed/configured by the gateway installer unless
  `BLUETTI_INSTALL_NTP=0` is set.
- One boot produced a transient BLUETTI auth DNS error immediately after restart, then the collector
  connected successfully on retry.
- Offline bundle was not installed on the Raspberry Pi during this pass; Git deployment was used.

## Pending User Confirmation

- Re-check VRM Portal or VRM mobile app after commit `76ea8c6`: local GUI was confirmed with the
  Codex in-app browser; VRM should receive the corrected Multi, active-source, Grid, and AC Loads
  paths after the next vrmlogger upload interval.
