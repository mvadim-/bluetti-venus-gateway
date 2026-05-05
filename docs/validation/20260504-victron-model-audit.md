# Victron Model Audit - 2026-05-04

Target:

```text
host: venus.local
device: Raspberry Pi 5
Venus OS: v3.72
VRM Portal ID: 2ccf672c2794
```

Audit sources:

- live BLUETTI snapshot from `/run/bluetti-gateway/latest.json`
- live Venus GUIv2 through the Codex in-app browser
- Venus OS v3.72 `dbus-systemcalc-py`
- Venus OS v3.72 `vrmlogger/datalist.py`
- gateway payload builder unit contract tests

## BLUETTI Fields Available In The Live Snapshot

The current EP760 telemetry supports these Victron-facing data groups:

- Battery:
  - `soc`
  - `battery_voltage_v`
  - `battery_current_a`
  - `dc_power_w`
  - `pack_avg_temp_c` / `pack_temp_c`
  - `charging_status`
- Grid / AC input:
  - `grid_power_w`
  - `grid_power_w_phase_1`
  - `grid_charge_power_w`
  - `grid_voltage_v`
  - `grid_current_a`
  - `grid_freq_hz`
  - `grid_charge_energy_total_kwh`
  - `grid_charge_energy_kwh`
  - `grid_feedback_energy_total_kwh`
  - `feedback_energy_kwh`
- AC loads:
  - `ac_load_power_w`
  - `ac_power_w`
  - `load_voltage_v`
  - `load_current_a`
  - `ac_energy_kwh`
- Inverter AC output:
  - `inv_output_power_w`
  - `inverter_power_w`
  - `inv_output_voltage_v`
  - `inv_output_current_a`
  - `inv_output_freq_hz`
- PV debug data currently available but disabled for v1 UI/VRM output:
  - `pv_power_w`
  - `pv_charge_energy_kwh`

Unsupported in the current BLUETTI snapshot:

- EV charger state, current, and energy
- Essential Loads
- L2/L3 AC phases
- real battery time-to-go
- battery SOH
- cell/module diagnostics unless pack diagnostics polling is enabled and mapped later
- power factor, because the live snapshot reports `grid_apparent_va=0`
- inverter error/alarm paths

## Victron Service Mapping

### `com.victronenergy.battery.ep760_41`

Supported paths:

- `/Soc`
- `/State`
- `/Dc/0/Voltage`
- `/Dc/0/Current`
- `/Dc/0/Power`
- `/Dc/0/Temperature`
- `/Capacity`, `/ConsumedAmphours`, `/InstalledCapacity` when configured
- `/Alarms/LowVoltage`, `/Alarms/HighVoltage`, `/Alarms/LowSoc`
- `/Io/AllowToCharge`, `/Io/AllowToDischarge`

State mapping:

- `/State = 9` (`Running`) while connected telemetry is available
- `/Connected = 0` when telemetry is stale or unavailable
- charge/discharge direction is represented by `/Dc/0/Power` and `/Dc/0/Current`, not by battery
  lifecycle `/State`

Unsupported VRM battery fields are intentionally omitted instead of faked: SOH, time-to-go,
starter voltage, BMS/cell/module alarms, and max charge/discharge limits.

### `com.victronenergy.grid.ep760_30`

Supported paths:

- `/Ac/L1/Power`
- `/Ac/L1/Voltage`
- `/Ac/L1/Current`
- `/Ac/Frequency`
- `/Ac/L1/Energy/Forward`
- `/Ac/L1/Energy/Reverse`
- `/Ac/Energy/Forward`
- `/Ac/Energy/Reverse`

Only L1 is published because EP760 live telemetry provides a single-phase view. L2/L3 and power
factor are intentionally omitted.

### `com.victronenergy.acload.ep760_31`

Supported paths:

- `/Position = 1` for AC output loads
- `/Ac/L1/Power`
- `/Ac/L1/Voltage`
- `/Ac/L1/Current`
- `/Ac/Frequency`
- `/Ac/L1/Energy/Forward`
- `/Ac/Energy/Forward`

AC Load power comes from `ac_load_power_w`, falling back to `ac_power_w` and then
`inv_output_power_w`. In grid pass-through, AC Loads will naturally be very close to Grid power.

### `com.victronenergy.inverter.ep760_32`

Supported paths:

- `/Mode`
- `/State`
- `/Soc`
- `/Dc/0/Voltage`
- `/Dc/0/Current`
- `/Dc/0/Power`
- `/Dc/0/Temperature`
- `/Ac/ActiveIn/ActiveInput`
- `/Ac/ActiveIn/Connected`
- `/Ac/In/1/Type`
- `/Ac/In/1/L1/V`
- `/Ac/In/1/L1/I`
- `/Ac/In/1/L1/P`
- `/Ac/In/1/L1/F`
- `/Ac/Out/L1/V`
- `/Ac/Out/L1/I`
- `/Ac/Out/L1/P`
- `/Ac/Out/L1/S`
- `/Ac/Out/L1/F`

This service is kept for local GUI device semantics and inverter VRM logging. Venus OS v3.72 does
not use inverter active-input paths for system active-source detection, so this service alone is not
enough for Grid-to-Inverter flow.

### `com.victronenergy.multi.ep760_32`

Supported paths:

- `/Mode`
- `/State`
- `/Soc`
- `/Dc/0/Voltage`
- `/Dc/0/Current`
- `/Dc/0/Power`
- `/Dc/0/Temperature`
- `/Ac/NumberOfAcInputs`
- `/Ac/ActiveIn/ActiveInput`
- `/Ac/ActiveIn/Connected`
- `/Ac/ActiveIn/L1/V`
- `/Ac/ActiveIn/L1/I`
- `/Ac/ActiveIn/L1/P`
- `/Ac/In/1/Connected`
- `/Ac/In/1/Type`
- `/Ac/In/1/L1/V`
- `/Ac/In/1/L1/I`
- `/Ac/In/1/L1/P`
- `/Ac/In/1/L1/F`
- `/Ac/Out/L1/V`
- `/Ac/Out/L1/I`
- `/Ac/Out/L1/P`
- `/Ac/Out/L1/S`
- `/Ac/Out/L1/F`

This is the compatibility service Venus OS v3.72 needs for systemcalc and GUI flow rendering. Grid is
published as Multi AC input 1. AC Loads are published as Multi AC output.

### `com.victronenergy.vebus.ep760_32`

This optional compatibility service is disabled by default. When enabled, it now follows the same
state and AC input/output mapping as the Multi service so it does not drift from the tested model.

### `com.victronenergy.system`

This service is produced by Venus systemcalc, not by the gateway. The gateway feeds it through
Battery, Grid, AC Load, Inverter, and Multi services.

Validated live outputs after the Multi compatibility fix:

```text
/Ac/ActiveIn/Source = 1
/Ac/ActiveIn/L1/Power ~= Grid L1 power
/Ac/Consumption/L1/Power ~= AC Loads L1 power
/Ac/ConsumptionOnOutput/L1/Power ~= AC Loads L1 power
```

### Not Published In V1

- `com.victronenergy.evcharger`: BLUETTI EP760 snapshot does not provide EV charger data.
- Essential Loads: no BLUETTI data source is available; the VRM block must stay empty/zero rather
  than being filled with AC Load values.
- PV/Solar charger: BLUETTI exposes basic PV power/energy, but v1 keeps PV disabled until panel
  topology and Venus/VRM model choice are validated.
- `com.victronenergy.acsystem`: not needed because Multi compatibility gives systemcalc the tested
  path for active AC input and output consumption.

## Inverter And Multi State Contract

Shared state contract for `inverter`, `multi`, and optional `vebus`:

- disconnected or stale telemetry: `/Connected = 0`, `/Mode = 4`, `/State = 0`
- grid input present and real inverter output power is `<= 5W`: `/State = 8` (`Pass-thru`)
- real inverter output power is `> 5W`: `/State = 9` (`Inverting`)
- active AC input is Grid: `/Ac/ActiveIn/ActiveInput = 0`, `/Ac/In/1/Type = 1`
- no active AC input: `/Ac/ActiveIn/ActiveInput = 0xF0`, `/Ac/ActiveIn/Connected = 0`

The bridge uses `inv_output_power_w` / `inverter_power_w` for inverter output state. It does not use
`ac_load_power_w` as inverter output while Grid is present, because that double-counts pass-through
load in systemcalc.

## Regression Coverage

`tests/test_bridge_model.py` now includes a Victron contract test covering the paths Venus
systemcalc and VRM logger need for:

- Battery
- Grid
- AC Loads
- Inverter
- Multi
- optional VE.Bus compatibility

## Live Post-Deploy Check

After deploying commit `19582ba`, the Raspberry Pi reported:

```text
bluetti-collector: running
bluetti-dbus-bridge: running
latest telemetry age: 0s
D-Bus battery service: present
D-Bus grid service: present
D-Bus acload service: present
D-Bus inverter service: present
D-Bus multi service: present
```

Spot checks:

```text
com.victronenergy.multi.ep760_32 /Soc = 100
com.victronenergy.multi.ep760_32 /Ac/In/1/L1/P = 396W
com.victronenergy.multi.ep760_32 /Ac/In/1/L1/I = 3.1A
com.victronenergy.multi.ep760_32 /Ac/In/1/L1/F = 49.9Hz
com.victronenergy.inverter.ep760_32 /Ac/In/1/L1/P = 350W
com.victronenergy.inverter.ep760_32 /Soc = 100
com.victronenergy.system /Ac/ActiveIn/Source = 1
com.victronenergy.system /Ac/Consumption/L1/Power = 353W
```

`/Dc/0/Temperature` was present but `null` on the live Multi service because the current BLUETTI
snapshot did not include `pack_avg_temp_c` or `pack_temp_c` at that moment.

The Codex in-app browser showed Venus GUIv2 still rendering Grid, Inverter / Charger, AC Loads,
Battery, and the Grid-to-Inverter-to-AC-Loads flow after deployment.
