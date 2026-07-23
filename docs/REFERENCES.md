# References and design basis (July 2026)

Each entry: what it supports · what it does **not** prove for DrillGuard · transferability · data needed.

## Cayeux et al., 2026 — Open-source online transient T&D (SPE-230785-MS)

- Supports: open engineering precedent for transparent mechanical models.
- Does not prove: DrillGuard torque_drag_index accuracy.
- Transfer: future optional module, not v0.2.
- Needs: trajectory, friction factors, survey, validated surface/downhole pairs.

## SINDI DRILLING (Zenodo 2024) — hydraulics monitoring on recorded rig data

- Supports: recorded-rig validation culture.
- Does not prove: our synthetic F1.
- Transfer: validation protocol pattern.
- Needs: owner archive + labels.

## Dadfar et al., 2019 — Drilling Library (Modelica)

- Supports: physics-library mindset for well construction.
- Does not prove: our screens.
- Transfer: long-term physics roadmap.
- Needs: Modelica stack + calibration data.

## OPM Flow 2026.04 / JutulDarcy.jl 2025

- Supports: reproducible open energy software longevity.
- Does not prove: drilling complication detection.
- Transfer: packaging/reproducibility culture only.

## ESP RUL / physics-informed predictive maintenance (2025–2026)

- Supports: adjacent telemetry+physics consistency idea.
- Does not prove: kick/packoff detection.
- Transfer: conceptual only.

## SPE EKLD / ballooning discrimination (2024–2025; e.g. SPE-218837, SPE-223799, SPE-221358)

- Supports: need for pit/Δflow, false-alarm control, ballooning confound.
- Does not prove: DrillGuard field performance.
- Transfer: motivates optional channels + residual-risk docs.
- Needs: flow-out, pit volume, labeled events.
