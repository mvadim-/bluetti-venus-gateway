# Raspberry Pi Hardware Validation - 2026-05-04

Target:

```text
host: venus.local
device: Raspberry Pi 5
Venus OS: v3.72
VRM Portal ID: 2ccf672c2794
gateway commit: 5c23951
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
```

Expected D-Bus services were present:

```text
com.victronenergy.battery.ep760_41
com.victronenergy.grid.ep760_30
com.victronenergy.acload.ep760_31
```

Battery alarm paths after the EP760 voltage-threshold correction:

```text
/Connected: 1
/Alarms/HighVoltage: 0
/Alarms/LowVoltage: 0
```

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

## Operational Notes

- The Raspberry Pi system clock was wrong during validation and was manually corrected to
  `2026-05-04` UTC. No `timedatectl`, `ntpd`, `chronyc`, `sntp`, or dedicated time-sync service was
  found during the check. Correct system time is required for TLS/auth behavior and telemetry
  freshness.
- One boot produced a transient BLUETTI auth DNS error immediately after restart, then the collector
  connected successfully on retry.
- Offline bundle was not installed on the Raspberry Pi during this pass; Git deployment was used.

## Pending User Confirmation

- Local Venus GUI visual confirmation that the Overview/device list shows Battery, AC Input, and AC
  Loads as expected.
- VRM Portal or VRM mobile app confirmation that Battery, AC Input, and AC Loads appear and update
  where VRM supports those service classes.
