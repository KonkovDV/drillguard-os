# Physics and assumptions

## Feature kinds (v0.2)

| Kind | Meaning | Examples in code |
|------|---------|------------------|
| Observed | Direct channel or simple difference | SPP, flow-in, ΔSPP |
| Physically motivated | Intuition from hydraulics/mechanics, **not** a simulator | SPP/Q, torque_drag_index |
| Empirical rule | Threshold + persistence | z_enter, confirm_seconds |
| Future physics | Not implemented | Multiphase hydraulics, ECD, 4DOF T&D, rheology |

## Explicit non-claims

- DrillGuard OS **is not** a hydraulic transient model.
- `torque_drag_index` **is not** the SPE open-source 4DOF T&D model (Cayeux et al., 2026).
- `possible_influx` without pit/flow-out is a **hypothesis screen** only.
- Ballooning vs kick discrimination is **out of scope** until flow-out/pit channels exist.

## Units and noise floors

Noise floors (MAD lower bound) prevent hypersensitive z-scores on low-noise synthetics:

- SPP: 50 kPa · Flow: 8 L/min · Hookload: 1 kN · Torque: 0.4 kN·m · ROP: 0.5 m/h

## Causal baseline

Baseline median/MAD uses only past samples in the **same regime**, minimum history length, and freezes updates while a candidate deviation is active. Future samples are never used.
