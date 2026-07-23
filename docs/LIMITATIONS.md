# Limitations

- Synthetic generator ≠ field data.
- No multiphase hydraulics, ECD, full rheology, or 4DOF T&D.
- Influx/loss screens without pit/flow-out are incomplete.
- Influx-like / ballooning confound without pit/flow-out.
- Point-level F1 is not used as primary for `operation_change` (interval hit is).
- Appearance rates are demoted compatibility metrics only.
- Regime classification depends on operation string quality.
- Not SIL / IEC 61508 certified; not a protection system.
- Benchmark metrics are synthetic_only until labeled archive exists.
