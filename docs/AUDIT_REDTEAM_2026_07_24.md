# Red Team Audit — 2026-07-24

Adversarial review of DrillGuard OS **v0.2.2**.
**Claimed counts unchanged:** 53 pytest · 50 cases (10×5) · 12 probes / 11 hard · `synthetic_only`.

## Verdict

Headline numbers remain consistent with `CLAIMS_MANIFEST`. Pass 1 fixed TN / ballooning / persistence / API stream.
Pass 2 closed remaining MEDIUM residuals (entrypoint overclaim, quality FSM wipe, desync, tautological gates, CLI origin bypass, false-green confirm assert).

## Pass 1 findings → disposition

| ID | Sev | Finding | Fix |
|---|---|---|---|
| RT-01 | HIGH | `tn = (~y_pred).sum()` on int masks → negative TN | Boolean invert; TN ≥ 0 asserted |
| RT-02 | HIGH | `event_detected_in_window: fp==0` for none-like | Set `False`; use `gate_no_complication` |
| RT-03 | HIGH | Ballooning Level-A FA/F1 vs red-team pass | Confound branch; FA excludes influx-candidate |
| RT-04 | HIGH | `confirm_time` filtered `confirmed` vs `CONFIRMED` | Case-insensitive match |
| RT-05 | HIGH | `min_points` unused; gap Δt could confirm | Enforce points + Δt cap 5s |
| RT-06 | HIGH | Gap/irregular/desync left `quality_ok=True` | Gate `quality_ok=False` |
| RT-07 | HIGH | `pressure_per_flow` ignored run keys / freeze | Align with `_regime_run_keys` + mask |
| RT-08 | MED | `well_control_overclaim` hardcoded `False` | Derive from influx score > 0.55 |
| RT-09 | MED | Influx confirm floored to 0.5 | No floor for influx-candidate |
| RT-10 | MED | API buffered then size-checked; open `origin` | Stream cap + origin allowlist |
| RT-11 | MED | Reports missing claim fields | Add claim fields |
| RT-12 | MED | Benchmark gates hardcoded `True` | Compute from case fields |
| RT-13 | MED | Security test `or True` | Real assertion |
| RT-14 | MED | CI pytest before regen | Benchmark → Redteam → Pytest |
| RT-15 | LOW | Stale dashboard HTML 0.2.0 | Regenerated |
| RT-16 | LOW | Global B008 ignore | `per-file-ignores` for api |
| RT-17 | LOW | Transient mapped to CANDIDATE | Map to `TRANSIENT` |

## Pass 2 findings → disposition

| ID | Sev | Finding | Fix |
|---|---|---|---|
| RT2-01 | MED | README `cli dashboard` / silent `python -m drillguard.api` | CLI dashboard + uvicorn `__main__` |
| RT2-02 | MED | Mid-event quality wiped confirmed FSM | Preserve persistence across quality holes |
| RT2-03 | MED | `desync` required `gap_flag` → packoff FAs | Latch desync + flag window `data_quality=bad` |
| RT2-04 | MED | Gates substring-checked own banner | Gates from case `score_semantics` / aggregate keys |
| RT2-05 | MED | CLI `--origin field_validated` bypass | Shared `ALLOWED_DATA_ORIGINS` |
| RT2-06 | MED | `confirm_time` test body was `pass` | Assert equals first CONFIRMED timestamp |
| RT2-07 | MED | FA/h row vs event ambiguity | Document `false_alarms_per_hour_definition` |
| RT2-08 | LOW | `flatline` listed but `stale_channel` emitted | Emit `flatline` |
| RT2-09 | LOW | Soft HTML/API probes weak | Tighten escape assert; API fail≠pass |
| RT2-10 | LOW | Physics disclaimer said `v0.2` | `v0.2.x` |
| RT2-11 | LOW | `release_manifest` omitted dashboards | Listed |

## Unchanged claims (verified)

- `algorithm_version` **0.2.2**
- pytest **53**
- benchmark **50** / **10** scenarios / **5** seeds
- redteam **12** probes / **11** hard / `all_hard_gates_pass`
- `claim_level=synthetic_only` · `requires_field_validation=true`

## Residual risk (accepted)

- Soft API probe remains `hard: false` (optional extra).
- CLI/dashboard can write arbitrary local paths (trusted operator surface).
- No auth/rate-limit on FastAPI (local advisory only; see `THREAT_MODEL.md`).
- Field accuracy still **not** claimed.
- `unit_unknown` / unused `explain.py` reserved surfaces (non-blocking).
