# Red Team Audit — 2026-07-24

Adversarial review of DrillGuard OS **v0.2.2** after evidence hard-sync.
**Claimed counts unchanged:** 53 pytest · 50 cases (10×5) · 12 probes / 11 hard · `synthetic_only`.

## Verdict

Headline numbers remain consistent with `CLAIMS_MANIFEST`. Audit found **real code/metrics bugs** (negative TN, confirm_time case mismatch, decorative `min_points`, gap Δt confirm bypass, `pressure_per_flow` without candidate freeze, false-green security assert, ballooning scored as Level-A FA while red-team passes). Fixes landed in the same tip without changing claim counts.

## Findings → disposition

| ID | Sev | Finding | Fix |
|---|---|---|---|
| RT-01 | HIGH | `tn = (~y_pred).sum()` on int masks → negative TN in published JSON | Boolean invert; TN ≥ 0 asserted |
| RT-02 | HIGH | `event_detected_in_window: fp==0` for none-like | Set `False`; use `gate_no_complication` |
| RT-03 | HIGH | Ballooning Level-A FA/F1 vs red-team pass conflict | Confound branch; FA excludes influx-candidate |
| RT-04 | HIGH | `confirm_time` filtered `confirmed` vs stored `CONFIRMED` | Case-insensitive `CONFIRMED` match |
| RT-05 | HIGH | `min_points` unused; gap Δt could confirm | Enforce points + Δt cap 5s |
| RT-06 | HIGH | Gap/irregular/desync set reason but `quality_ok=True` | Gate `quality_ok=False` |
| RT-07 | HIGH | `pressure_per_flow` baseline ignored run keys / freeze | Align with `_regime_run_keys` + mask |
| RT-08 | MED | `well_control_overclaim` hardcoded `False` | Derive from influx score > 0.55 |
| RT-09 | MED | Influx confirm floored to 0.5 | No floor for influx-candidate |
| RT-10 | MED | API buffered then size-checked; open `origin` | Stream cap + origin allowlist |
| RT-11 | MED | Reports missing claim fields | Add `claim_level` / `requires_field_validation` |
| RT-12 | MED | Benchmark gates hardcoded `True` | Compute from banner/contents |
| RT-13 | MED | Security test `or True` | Real assertion |
| RT-14 | MED | CI pytest before regen | Benchmark → Redteam → Pytest |
| RT-15 | LOW | Stale dashboard HTML 0.2.0 | Regenerated |
| RT-16 | LOW | Global B008 ignore | `per-file-ignores` for api only |
| RT-17 | LOW | Transient mapped to CANDIDATE | Map to `TRANSIENT` |

## Unchanged claims (verified)

- `algorithm_version` **0.2.2**
- pytest **53**
- benchmark **50** / **10** scenarios / **5** seeds
- redteam **12** probes / **11** hard / `all_hard_gates_pass`
- `claim_level=synthetic_only` · `requires_field_validation=true`

## Residual risk (accepted)

- Soft API probe remains optional (`hard: false`).
- CLI/dashboard can write arbitrary local paths (trusted operator surface).
- No auth/rate-limit on FastAPI (local advisory only; see `THREAT_MODEL.md`).
- Field accuracy still **not** claimed.
