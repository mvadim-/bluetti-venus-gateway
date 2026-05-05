# Telemetry Signal Map

## Scope

This note captures the current standalone gateway signal coverage for the EP760 / PBOX path and maps
it to Venus OS / VRM projection needs.

The inventory below is intentionally focused on normalized, user-facing fields emitted by
the BLUETTI parser. Deep raw decoder structures are useful for local development but should not be
published to Victron paths unless they are mapped intentionally.

## Confirmed Sources

| Source group | Register | Current normalized fields | Status |
| --- | --- | --- | --- |
| `HOME_INFO` | `100` | `device_model`, `device_sn`, `soc`, `battery_voltage_v`, `battery_current_a`, `charging_status`, `grid_parallel_soc`, `ac_power_w`, `grid_power_w`, `pv_power_w`, `dc_power_w`, `inverter_power_w`, `ac_energy_kwh`, `grid_charge_energy_kwh`, `pv_charge_energy_kwh`, `feedback_energy_kwh`, `flow`, `device_warnings`, `device_faults` | Confirmed |
| `INV_PV_INFO` | `1200` | `pv_charge_power_w`, `pv_charge_energy_total_kwh`, `pv_input_count`, `pv_inputs` | Confirmed |
| `INV_GRID_INFO` | `1300` | `grid_voltage_v`, `grid_current_a`, `grid_power_w_phase_1`, `grid_apparent_va`, `grid_freq_hz`, `grid_charge_power_w`, `grid_charge_energy_total_kwh`, `grid_feedback_energy_total_kwh`, `grid_phase_count` | Confirmed |
| `INV_LOAD_INFO` | `1400` | `ac_load_power_w`, `dc_load_power_w`, `load_voltage_v`, `load_current_a` | Confirmed |
| `INV_INVERTER_INFO` | `1500` | `inv_output_power_w`, `inv_output_voltage_v`, `inv_output_current_a`, `inv_output_freq_hz` | Confirmed |
| `PACK_MAIN_INFO` | `6000` | `pack_total_soc`, `pack_total_soh`, `pack_total_voltage_v`, `pack_total_current_a`, `pack_count`, `battery_protection`, `battery_warnings`, `battery_faults` | Confirmed |
| `PACK_ITEM_INFO` | `6100` | `pack_temp_c`, `pack_protection`, `pack_warnings`, `pack_faults` | Temperature confirmed from the live EP760 NTC pair; remaining pack-item identity/electrical fields are still incomplete |

## Requirement Mapping

| Product requirement | Preferred normalized signal(s) | Source group | v1 status | Fallback |
| --- | --- | --- | --- | --- |
| External power loss detection | `grid_voltage_v` | `INV_GRID_INFO (1300)` | Ready when grid poll is enabled | If only `grid_power_w`, `grid_power_w_phase_1`, `grid_current_a`, or `grid_charge_power_w` exist, treat outage state as unknown and do not alert |
| Grid voltage below / above threshold | `grid_voltage_v` | `INV_GRID_INFO (1300)` | Ready when grid poll is enabled | If missing, skip the alert and inspect a debug artifact |
| Battery SOC below threshold | `soc`, `pack_total_soc`, `pack_soc` | `HOME_INFO (100)` preferred, pack groups as backup | Ready | Disable that sample if all SOC fields are missing |
| Battery voltage below / above threshold | `battery_voltage_v`, `pack_total_voltage_v`, `pack_voltage_v` | `HOME_INFO (100)` preferred, pack groups as backup | Ready | Disable that sample if all voltage fields are missing |
| Device warning visibility | `device_warnings` | `HOME_INFO (100)` | Ready | No alerting logic yet, but signal is present |
| Battery warning / fault visibility | `battery_warnings`, `battery_faults`, `pack_warnings`, `pack_faults` | `PACK_MAIN_INFO (6000)` and `PACK_ITEM_INFO (6100)` | Ready | Prefer pack-main summary for v1 notifications |

## Grid Voltage Conclusion

`grid_voltage_v` is already available from the known payload set.

- It does **not** come from `HOME_INFO (100)`.
- It comes from `INV_GRID_INFO (1300)`.
- The gateway EP760 full polling profile includes `1300 / 19`.
- A minimal `HOME_INFO`-only run is not enough for grid-loss or grid-voltage alerting.

This removes the earlier uncertainty from the plan: no extra reverse engineering is required for
live grid voltage as long as the grid poll stays enabled.

## v1 Fallback Policy

For v1 alerting, use only signals that are confirmed in the current sample.

- If `grid_voltage_v` is absent, keep external-power-loss and grid-voltage conditions in `unknown`
  state and suppress alert generation for that sample.
- If SOC signals are absent, skip SOC evaluation for that sample.
- If battery voltage signals are absent, skip battery-voltage evaluation for that sample.
- Do not infer voltage thresholds from aggregate energy counters.
- Do not infer outages from `totalGridPower` alone; import/export can be zero even when the grid is
  healthy.

## Signal Debug Guidance

When adding a new Victron projection path, capture the normalized snapshot and document:

- which BLUETTI register group provides the value
- which normalized key is preferred
- which fallback keys are acceptable
- what the bridge should publish when the signal is missing or stale

Do not add a Victron path by reusing a visually similar BLUETTI value unless the source semantics
match. This was important for AC Loads vs. inverter output: `ac_load_power_w` is a load service
value, while `inv_output_power_w` / `inverter_power_w` are inverter-output candidates.

## Practical Polling Guidance

- For dashboard-only battery and power summary, `HOME_INFO (100)` is enough.
- For any grid-loss or grid-voltage alerting, keep `INV_GRID_INFO (1300)` enabled.
- For future richer battery diagnostics, keep `PACK_MAIN_INFO (6000)` and `PACK_ITEM_INFO (6100)`
  in the full profile, but do not block v1 alerts on low-level pack-item calibration work.
