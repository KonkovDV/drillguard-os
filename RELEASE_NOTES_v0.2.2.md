# Release notes — DrillGuard OS v0.2.2

Evidence-sync patch after external red-team review of `82cff49`.

## Fixes

- `artifacts/CLAIMS_MANIFEST.json` is the SSOT for claim numbers.
- `tests/test_artifact_claims_consistency.py` fails CI if JSON ≠ claimed cases/probes/version.
- Baseline pass-2 now applies `candidate_mask` when `freeze_on_candidate=True`.
- Ballooning hard gate reports `well_control_overclaim`.
- User-facing display: «Кандидат на поведение, похожее на проявление».

## Verified locally before push

- pytest green (includes artifact consistency).
- benchmark: 50 cases / 10 scenarios / 5 seeds.
- red-team: 12 probes / 11 hard gates / `well_control_overclaim=false`.

## Status for INDUSTRIX

Synthetic advisory demonstrator only. Not field validated.
