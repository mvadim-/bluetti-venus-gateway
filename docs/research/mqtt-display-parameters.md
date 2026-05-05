# BLUETTI Display Parameters Snapshot

Snapshot date: 2026-04-24

This document lists normalized BLUETTI MQTT parameters that are useful for the standalone Venus
gateway collector, telemetry snapshot, Victron D-Bus bridge, local Venus GUI, and VRM projection.

Primary code references:

- `src/bluetti_venus_gateway/bluetti/parser.py`: MQTT payload decode and normalized snapshot extraction
- `src/bluetti_venus_gateway/telemetry/core.py`: telemetry envelope, freshness, and derived facts
- `src/bluetti_venus_gateway/telemetry/snapshot_store.py`: volatile latest snapshot persistence
- `src/bluetti_venus_gateway/victron/bridge_model.py`: EP760 to Victron service projection
- `docs/research/telemetry-signal-map.md`: shorter signal source map

## Runtime Shape

The collector decodes BLUETTI MQTT payloads into a normalized snapshot. The gateway wraps that
snapshot in a telemetry envelope and writes the latest sample to `/run/bluetti-gateway/latest.json`.

Gateway snapshots expose:

| Field | Meaning | Display use |
| --- | --- | --- |
| `device_sn` | Device serial number selected by gateway config and reported by the payload. | Header, device selector, debugging. |
| `observed_at` | Timestamp from the MQTT sample/snapshot. | "Last updated" / local time indicators. |
| `received_at` | Gateway-side receive time. | Latency/debugging; usually secondary. |
| `sample_key` | Stable hash for latest sample identity. | Debug/details only; avoid prominent UI display. |
| `snapshot` | Full normalized snapshot, including transport metadata such as `timestamp` and `topic`. | Developer/debug details. |
| `signals` | Snapshot without metadata keys like `timestamp` and `topic`. | Main Victron projection source. |
| `freshness.state` | `fresh`, `stale`, or `missing`. | Realtime/stale/missing UI state. |
| `freshness.age_seconds` | Current age of the latest observed sample. | Optional freshness tooltip. |
| `freshness.stale_after_seconds` | Runtime threshold for stale detection. | Optional status explanation. |
| `derived_facts` | Canonical facts derived from multiple possible signal names. | Best source for cross-system summaries/projections. |

## Source Groups

| Source group | Register | What it contributes |
| --- | --- | --- |
| `HOME_INFO` | `100` | Main device identity, battery aggregate, total AC/grid/PV/DC power, energy counters, flow flags, warnings/faults. |
| `INV_PV_INFO` | `1200` | PV charge power, PV charge energy, per-input PV details. |
| `INV_GRID_INFO` | `1300` | Live grid voltage/current/frequency/power and grid energy counters. |
| `INV_LOAD_INFO` | `1400` | AC/DC load power and first-phase load voltage/current. |
| `INV_INVERTER_INFO` | `1500` | Inverter output power/voltage/current/frequency. |
| `PACK_MAIN_INFO` | `6000` | Battery pack aggregate SOC/SOH/temp/voltage/current/count and pack-level warnings/faults. |
| `PACK_ITEM_INFO` | `6100` | Individual pack ID/SN/SOC/SOH/voltage/current/temp and pack item warnings/faults. |

## Transport And Metadata

| Normalized key | Type/unit | Source | Description | Display priority |
| --- | --- | --- | --- | --- |
| `timestamp` | ISO datetime/string | MQTT runtime | Timestamp assigned to the decoded MQTT sample before normalization. | Debug/details. |
| `topic` | string | MQTT topic, e.g. `PUB/PBOX/<device_sn>` | Source topic from the BLUETTI MQTT stream. | Debug/details. |
| `rssi_dbm` | dBm | MQTT wrapper `rssi` | Signal strength reported in the MQTT wrapper when present. | Optional diagnostics. |

## Device And Battery Summary

| Normalized key | Type/unit | Source field | Description | Suggested UI use |
| --- | --- | --- | --- | --- |
| `device_model` | string | `HOME_INFO.deviceModel` | Device model, for example EP760. | Device identity/details. |
| `device_sn` | string | `HOME_INFO.deviceSN` | Serial number reported by the device payload. | Device identity/details. |
| `soc` | % | `HOME_INFO.packTotalSoc` | Main battery state of charge. | Primary battery tile. |
| `battery_voltage_v` | V | `HOME_INFO.packTotalVoltage` | Aggregate battery voltage from home snapshot. | Battery detail. |
| `battery_current_a` | A | `HOME_INFO.packTotalCurrent` | Aggregate battery current from home snapshot. | Battery detail; sign may indicate charge/discharge direction. |
| `charging_status` | string/number | `HOME_INFO.packChargingStatus` | Device charging state as decoded from the BLUETTI payload. | Battery/status details. |
| `grid_parallel_soc` | % | `HOME_INFO.gridParallelSoC` | SOC value used by grid-parallel operating mode when present. | Advanced operating mode detail. |
| `dc_power_w` | W | `HOME_INFO.totalDCPower` | Aggregate DC-side power. | Battery/DC detail; fallback for derived battery power. |
| `inverter_power_w` | W | `HOME_INFO.totalInvPower` | Aggregate inverter power from home snapshot. | Inverter/load summary fallback. |

## Grid Input

These are the fields for the "Grid" tile. For display, show grid input power as the primary value
and keep `grid_voltage_v`, `grid_current_a`, and `grid_freq_hz` as secondary values.

| Normalized key | Type/unit | Source field | Description | Suggested UI use |
| --- | --- | --- | --- | --- |
| `grid_voltage_v` | V | `INV_GRID_INFO.gridVoltage` or first `phaseList[*].gridVoltage` | Live grid/input voltage. This is the preferred signal for grid-loss and voltage alerts. | Grid tile secondary metric. |
| `grid_current_a` | A | `INV_GRID_INFO.gridCurrent` or first `phaseList[*].gridCurrent` | Live grid/input current. | Grid tile secondary metric. |
| `grid_freq_hz` | Hz | `INV_GRID_INFO.gridFreq` | Live grid frequency. | Grid tile secondary metric. |
| `grid_power_w` | W | `HOME_INFO.totalGridPower` | Aggregate grid power from home snapshot. | Grid power fallback / summary. |
| `grid_power_w_phase_1` | W | `INV_GRID_INFO.gridPower` | Grid power for phase 1 from inverter grid info. | Preferred detailed input power when present. |
| `grid_charge_power_w` | W | `INV_GRID_INFO.totalChgPower` | Total grid charging power. | Fallback input/charge power display. |
| `grid_apparent_va` | VA | `INV_GRID_INFO.apparent` or first `phaseList[*].apparent` | Apparent grid power. | Advanced grid detail. |
| `grid_phase_count` | count | `INV_GRID_INFO.phaseList` | Number of grid phases returned in the payload. | Grid topology/details. |
| `grid_charge_energy_kwh` | kWh | `HOME_INFO.totalGridChargingEnergy` | Grid charging energy from home snapshot. | Energy totals/history. |
| `grid_charge_energy_total_kwh` | kWh | `INV_GRID_INFO.totalChgEnergy` | Total grid charge energy from inverter grid info. | Energy totals/history. |
| `grid_feedback_energy_total_kwh` | kWh | `INV_GRID_INFO.totalFeedbackEnergy` | Total feedback/export energy from inverter grid info. | Energy totals/history. |
| `feedback_energy_kwh` | kWh | `HOME_INFO.totalFeedbackEnergy` | Aggregate feedback/export energy from home snapshot. | Energy totals/history. |

Recommended Grid tile primary power fallback:

1. `grid_power_w`
2. `grid_power_w_phase_1`
3. `grid_charge_power_w`

For alerting, do not infer outage state from power alone; prefer `grid_voltage_v`.

## PV / Solar

| Normalized key | Type/unit | Source field | Description | Suggested UI use |
| --- | --- | --- | --- | --- |
| `pv_power_w` | W | `HOME_INFO.totalPVPower` | Aggregate PV power from home snapshot. | Primary solar tile. |
| `pv_charge_power_w` | W | `INV_PV_INFO.totalChgPower` | PV charging power from inverter PV info. | Primary PV Charger tile value. |
| `pv_charge_energy_kwh` | kWh | `HOME_INFO.totalPVChargingEnergy` | Aggregate PV charge energy from home snapshot. | Energy totals/history. |
| `pv_charge_energy_total_kwh` | kWh | `INV_PV_INFO.totalChgEnergy` | Total PV charge energy from inverter PV info. | PV Charger detail / energy totals. |
| `pv_input_count` | count | `INV_PV_INFO.phaseList` | Number of PV input entries. | PV detail header. |
| `pv_inputs` | array | `INV_PV_INFO.phaseList[*]` | Per-input PV details: `phase`, `power_w`, `voltage_v`, `current_a`. | PV Charger per-input detail blocks. |

`pv_inputs` item shape:

| Key | Type/unit | Description |
| --- | --- | --- |
| `phase` | number/string | PV input/phase identifier from the payload. |
| `power_w` | W | PV input power. |
| `voltage_v` | V | PV input voltage. |
| `current_a` | A | PV input current. |

## Loads And Inverter Output

| Normalized key | Type/unit | Source field | Description | Suggested UI use |
| --- | --- | --- | --- | --- |
| `ac_power_w` | W | `HOME_INFO.totalACPower` | Aggregate AC power from home snapshot. | AC loads fallback/summary. |
| `ac_load_power_w` | W | `INV_LOAD_INFO.acLoadTotalPower` | AC load power from load-specific info. | Primary AC Loads tile when present. |
| `dc_load_power_w` | W | `INV_LOAD_INFO.dcLoadTotalPower` | DC load power. | DC load detail. |
| `load_voltage_v` | V | `INV_LOAD_INFO.phase1LoadVoltage` | First-phase load voltage. | Load detail. |
| `load_current_a` | A | `INV_LOAD_INFO.phase1LoadCurrent` | First-phase load current. | Load detail. |
| `inv_output_power_w` | W | `INV_INVERTER_INFO.phase1InvPower` | Inverter output power. | Inverter output tile/detail. |
| `inv_output_voltage_v` | V | `INV_INVERTER_INFO.phase1InvVoltage` | Inverter output voltage. | Inverter detail. |
| `inv_output_current_a` | A | `INV_INVERTER_INFO.phase1InvCurrent` | Inverter output current. | Inverter detail. |
| `inv_output_freq_hz` | Hz | `INV_INVERTER_INFO.frequency` | Inverter output frequency. | Inverter detail. |
| `ac_energy_kwh` | kWh | `HOME_INFO.totalACEnergy` | Aggregate AC energy. | Energy totals/history. |

Recommended AC Loads tile fallback:

1. `ac_load_power_w`

Show `load_voltage_v` and `load_current_a` as compact secondary values on the AC Loads tile. Do not show frequency in this tile; keep frequency on the input Grid tile and inverter detail views.

## Energy Flow Flags

`flow` is an object derived from `HOME_INFO.energyLines` and `HOME_INFO.ctrlStatus`.

| `flow` key | Source field | Description | Suggested UI use |
| --- | --- | --- | --- |
| `battery_to_inverter` | `energyLines.batteryToInvert` | Whether the battery-to-inverter flow line is active. | Animate/enable battery to inverter link. |
| `inverter_to_battery` | `energyLines.invertToBattery` | Whether inverter-to-battery flow is active. | Animate/enable charging link. |
| `pv_present` | `energyLines.pvIcon` | Whether PV source is present in the home snapshot. | Show PV source state. |
| `meter_enabled` | `ctrlStatus.meterEnable` | Whether meter mode/control is enabled. | Advanced control/status detail. |

Frontend flow-board fallback logic:

- Grid link is active when `grid_voltage_v` is present above AC threshold, or when
  `grid_current_a` / grid power fallback is non-zero.
- AC Loads link is active when `ac_load_power_w` or `load_current_a` is non-zero.
- PV link animates only when `pv_charge_power_w`, `pv_power_w`, or
  `pv_inputs[*].power_w/current_a` is non-zero. `flow.pv_present` is only a presence fallback when
  no numeric PV measurements are available.
- Battery direction is driven by `battery_current_a` / `pack_total_current_a` first: negative current
  is charging, positive current is discharging, and near-zero current is idle. The
  `flow.battery_to_inverter` / `flow.inverter_to_battery` flags are only fallback direction hints
  when no numeric battery current is available.

## Battery Pack Aggregate

| Normalized key | Type/unit | Source field | Description | Suggested UI use |
| --- | --- | --- | --- | --- |
| `pack_total_soc` | % | `PACK_MAIN_INFO.totalSOC` | Aggregate pack SOC. | Primary Battery tile value. |
| `pack_total_soh` | % | `PACK_MAIN_INFO.totalSOH` | Aggregate pack state of health. | Battery health tile/detail. |
| `pack_avg_temp_c` | Celsius | `PACK_MAIN_INFO.averageTemp` | Average pack temperature. | Battery thermal detail. |
| `pack_total_voltage_v` | V | `PACK_MAIN_INFO.totalVoltage` | Aggregate pack voltage. | Battery voltage fallback/detail. |
| `pack_total_current_a` | A | `PACK_MAIN_INFO.totalCurrent` | Aggregate pack current. | Battery current fallback/detail. |
| `pack_count` | count | `PACK_MAIN_INFO.packCnts` | Number of battery packs. | Battery inventory/status. |
| `battery_protection` | array/string | `PACK_MAIN_INFO.protectStatusNames` | Human-readable protection statuses when decoded. | Warnings/protection panel. |
| `battery_warnings` | array/string | `PACK_MAIN_INFO.packHighVoltAlarmNames` | Pack-main warning names. | Alert/warnings panel. |
| `battery_faults` | array/string | `PACK_MAIN_INFO.packSysErrNames` | Pack-main fault names. | Fault panel/high-priority alerts. |

## Battery Pack Item

These values represent the current decoded pack item payload. If multiple pack item polls are
added later, model the UI as a list/table keyed by `pack_id` or `pack_sn`.

| Normalized key | Type/unit | Source field | Description | Suggested UI use |
| --- | --- | --- | --- | --- |
| `pack_id` | number/string | `PACK_ITEM_INFO.packID` | Pack identifier. | Pack table key. |
| `pack_sn` | string | `PACK_ITEM_INFO.packSN` | Pack serial number. | Pack inventory/detail. |
| `pack_soc` | % | `PACK_ITEM_INFO.packSoc` | Individual pack SOC. | Pack table/detail. |
| `pack_soh` | % | `PACK_ITEM_INFO.packSoh` | Individual pack state of health. | Pack health detail. |
| `pack_voltage_v` | V | `PACK_ITEM_INFO.voltage` | Individual pack voltage. | Pack electrical detail. |
| `pack_current_a` | A | `PACK_ITEM_INFO.current` | Individual pack current. | Pack electrical detail. |
| `pack_temp_c` | Celsius | `PACK_ITEM_INFO.averageTemp` | Individual pack average temperature. | Pack thermal detail. |
| `pack_protection` | array/string | `PACK_ITEM_INFO.packProtectNames` | Pack item protection statuses. | Pack warning/protection detail. |
| `pack_warnings` | array/string | `PACK_ITEM_INFO.packHighVoltAlarmNames` | Pack item warning names. | Pack warning detail. |
| `pack_faults` | array/string | `PACK_ITEM_INFO.packSysErrNames` | Pack item fault names. | Pack fault detail. |

## Device Warnings And Faults

| Normalized key | Type/unit | Source field | Description | Suggested UI use |
| --- | --- | --- | --- | --- |
| `device_warnings` | array/string | `HOME_INFO.alarmNames` | Device-level warnings decoded from the home payload. | Warnings panel / alert source. |
| `device_faults` | array/string | `HOME_INFO.faultNames` | Device-level faults decoded from the home payload. | Fault panel / high-priority alert source. |

## Derived Facts

The gateway derives these facts from the available normalized signals. They are useful when Victron
projection logic needs one canonical value even though multiple source fields can provide it.

| Derived fact | Source fallback order | Description | Suggested UI use |
| --- | --- | --- | --- |
| `battery_soc_pct` | `soc`, `pack_total_soc`, `pack_soc` | Canonical battery SOC. | Battery tile, Victron bridge, summaries. |
| `battery_voltage_v` | `battery_voltage_v`, `pack_total_voltage_v`, `pack_voltage_v` | Canonical battery voltage. | Battery detail. |
| `battery_current_a` | `battery_current_a`, `pack_total_current_a`, `pack_current_a` | Canonical battery current. | Battery detail. |
| `battery_power_w` | `dc_power_w`, then voltage * current | Canonical battery power estimate. | Battery flow/detail. |
| `grid_power_w` | `grid_power_w`, `grid_power_w_phase_1`, `grid_charge_power_w` | Canonical grid power. | Grid tile secondary metric / projection. |
| `pv_power_w` | `pv_power_w`, `pv_charge_power_w` | Canonical PV power. | Solar tile / projection. |

## Venus / VRM Display Recommendations

| UI area | Preferred fields | Notes |
| --- | --- | --- |
| Header status | `freshness.state`, `freshness.age_seconds`, `observed_at` | Show stale/missing clearly; do not hide old telemetry. |
| Grid tile | grid power fallback; secondary `grid_voltage_v`, `grid_current_a`, `grid_freq_hz` | This is the live AC input view. Keep power prominent, with voltage/current/frequency below. |
| AC Loads tile | Primary `ac_load_power_w`; secondary `load_voltage_v`, `load_current_a` | Match the Grid tile hierarchy, but omit frequency because this block represents load output. |
| Battery tile | Primary `pack_total_soc`; secondary `pack_total_voltage_v`, `pack_total_current_a`, `pack_avg_temp_c` | Match the Grid tile hierarchy with pack-level battery state and compact electrical/thermal details. |
| PV Charger tile | Primary `pv_charge_power_w`; secondary `pv_charge_energy_total_kwh` and `pv_inputs[*].power_w/voltage_v/current_a` | Keep this as the single PV flow tile; do not render a separate PV Inverter tile unless inverter-output PV fields become operationally distinct. |
| Flow board links | `flow.*` first; fallback to Grid/PV/AC load/battery numeric signals | Animate only active energy paths so duplicate summary cards are not needed for system state. |
| Inverter tile/detail | `inv_output_power_w`, `inv_output_voltage_v`, `inv_output_current_a`, `inv_output_freq_hz` | Keep separate from AC load if both are available. |
| Energy/history | `*_energy_kwh` | Use cumulative counters for VRM history when the corresponding Victron path supports it. |
| Warnings/faults | `device_warnings`, `device_faults`, `battery_warnings`, `battery_faults`, `pack_warnings`, `pack_faults` | Keep warning/fault display separate from numeric telemetry. |
| Diagnostics | `topic`, `rssi_dbm`, `sample_key`, `sourceField` mapping | Good for debug/details drawers, not first-screen UI. |

## Known Caveats

- `grid_voltage_v` comes from `INV_GRID_INFO (1300)`, not from `HOME_INFO (100)`.
- `HOME_INFO.totalGridPower` can be zero while grid is still healthy. Do not use grid power alone
  for outage detection.
- `signals` intentionally excludes transport metadata; use `snapshot` for `timestamp` and `topic`.
- `pv_inputs` and warning/fault fields can be absent or empty depending on which register group was
  last received/polled.
- Current pack-item normalization is a single decoded item shape. If the runtime begins polling many
  pack item addresses, the UI should evolve from single fields to a pack list/table.
