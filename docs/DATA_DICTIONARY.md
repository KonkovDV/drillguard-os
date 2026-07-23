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

## Optional columns

| Column | Unit | Notes |
|--------|------|-------|
| mud_density_sg | SG | Used for consistency screens only |
| plastic_viscosity_cp | cP | Recorded; not full rheology model |
| flow_out_lpm | L/min | **Recommended for influx/loss** — not required in v0.2 |
| pit_volume_m3 | m³ | **Recommended for kick/loss** — not required in v0.2 |
| bit_depth_m | m | Optional |

## Missing-data rules

- NaN / non-finite on required numeric → `quality_ok=false`, reason `nan:` / `nonfinite:`
- Negative physically non-negative channel → `negative:`
- Out of soft range → `out_of_range:`
- Duplicate timestamps → dropped (keep first), flagged
- Gaps > 3× median Δt → `gap_in_timeline`
- Flatline SPP ≥ 16 samples → `flatline` (legacy alias noted as `stale_channel` in older notes)

## Example validation error

```json
{
  "error": "Missing required columns: ['pump_flow_lpm']",
  "required_columns": ["timestamp", "depth_m", "standpipe_pressure_kpa", "pump_flow_lpm", "..."]
}
```

See `artifacts/schema_example.csv`.
