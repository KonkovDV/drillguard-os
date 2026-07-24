# Changelog

## 0.2.2 — 2026-07-24 (red-team pass 3, counts unchanged)

- Do not bridge candidates across quality holes; sticky desync until SPP recovers.
- Drift FULL scenarios mark `data_quality=bad`; mud_density SPP bump reduced; clearing→CLEARING.
- Appearance demotion gate requires per_class demotion note.

## 0.2.2 — 2026-07-24 (red-team pass 2, counts unchanged)

- CLI `dashboard` subcommand; `python -m drillguard.api` starts local uvicorn.
- Preserve persistence across quality holes; shared `ALLOWED_DATA_ORIGINS` for CLI/API.
- Desync: latch + quality flag window (no packoff FA); gates from case fields; confirm_time assert.
- Emit `flatline`; document FA/h as row-rate; release_manifest lists dashboards.

## 0.2.2 — 2026-07-24 (red-team hardening, counts unchanged)

- Fixed negative TN (`~` on int masks), ballooning confound scoring, confirm_time CONFIRMED match.
- Persistence: enforce `min_points`, cap credited Δt; quality gates gaps/desync.
- Align `pressure_per_flow` baseline with regime-run keys + candidate freeze.
- API: streamed size limit, origin allowlist; reports carry claim fields.
- CI: Benchmark → Redteam → Pytest; remove false-green security `or True`.
- Audit: `docs/AUDIT_REDTEAM_2026_07_24.md`. Claim counts still 53 / 50 / 12·11.

## 0.2.2 — 2026-07-23

- CLAIMS_MANIFEST + artifact consistency tests (P0 evidence sync).
- Baseline pass-2 applies `candidate_mask` when `freeze_on_candidate=True`.
- Ballooning hard gate exposes `well_control_overclaim`.
- Display label: «Кандидат на поведение, похожее на проявление».
- Regenerated benchmark/redteam artifacts stamped to 0.2.2.

## 0.2.1 — 2026-07-23

- Benchmark Level A/B/C; demote appearance-rate KPI; HTML leads with limitations.
- Rename influx screen to `possible_influx_candidate` (not well-control diagnosis).
- Full Apache-2.0 `LICENSE` text + SPDX in `pyproject.toml` (fix GitHub NOASSERTION risk).
- Causality tests: prefix=full, future mutation, regime return warmup.
- Hard red-team gates with non-zero exit; expanded probe count/scope statement.
- Machine-readable quality reason codes; ballooning_like scenario.
- Version sync to 0.2.1.

## 0.2.0 — 2026-07-23

- Causal baseline, timebase, persistence, API/dashboard, synthetic MVP docs.
