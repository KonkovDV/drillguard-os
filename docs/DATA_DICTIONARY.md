# Data dictionary

## Required columns

| Column | Unit | Type | Range (soft) | Notes |
|--------|------|------|--------------|-------|
| timestamp | datetime | datetime64 | monotonic preferred | ISO-8601 / pandas-parseable |
| depth_m | m | float | 0…15000 | Hole/bit depth context |
| standpipe_pressure_kpa | kPa | float | 0…80000 | Standpipe / SPP |
| pump_flow_lpm | L/min | float | 0…5000 | Flow-in |
| hookload_kn | kN | float | 0…5000 | |
| torque_knm | kN·m | float | 0…100 | Surface torque |
| rate_of_penetration_m_h | m/h | float | -50…200 | |
| pump_rpm | rpm | float | 0…400 | |
| operation | — | string | taxonomy | drilling/circulation/tripping/connection… |
| data_quality | — | string | ok/good/bad… | Operator or QC flag |

## Optional columns (letter-aligned)

These match the INDUSTRIX cover letter («при наличии дополнительно»).  
Numeric optionals may be range-checked; text optionals are carried into event-card `optional_context` for engineer review. **They do not by themselves confirm kick/loss/packoff.**

| Column | Unit | Notes |
|--------|------|-------|
| flow_out_lpm | L/min | Recommended for influx/loss screening context |
| pit_volume_m3 | m³ | Recommended for kick/loss screening context |
| mud_density_sg | SG | Density |
| plastic_viscosity_cp | cP | Rheology (not full model) |
| yield_point_pa | Pa | Rheology (not full model) |
| bit_depth_m | m | Optional depth of bit |
| temperature_c | °C | Temperature if available |
| cuttings_load_pct | % | Cuttings / solids indicator if available |
| equipment_status | text | Equipment operating notes |
| daily_report_ref | text | Daily report id / excerpt reference |
| active_alarms | text | Active alarm codes / text |
| engineer_comment | text | Engineer notes |

## Missing-data rules

- NaN / non-finite on required numeric → `quality_ok=false`, reason `missing_value` / `nonfinite_value`
- Negative physically non-negative channel → `negative_physical_value`
- Out of soft range → `out_of_range`
- Duplicate timestamps → dropped (keep first), flagged
- Gaps > 3× median Δt → `gap_in_timeline`
- Flatline SPP ≥ 16 samples → `flatline`

## Example validation error

```json
{
  "error": "Missing required columns: ['pump_flow_lpm']",
  "required_columns": ["timestamp", "depth_m", "standpipe_pressure_kpa", "pump_flow_lpm", "..."]
}
```

See `artifacts/schema_example.csv`.
