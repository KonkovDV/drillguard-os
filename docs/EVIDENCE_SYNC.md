# Evidence sync — how to verify main (no cache)

If the GitHub UI looks stale, **do not trust the rendered blob preview alone**. Use these checks:

## 1. Tip of main

```bash
gh api repos/KonkovDV/drillguard-os/commits/main --jq ".sha,.commit.message"
```

Expected family: commit message contains `v0.2.2` (not only `82cff49`).

## 2. Raw artifacts (bypass UI cache)

- https://raw.githubusercontent.com/KonkovDV/drillguard-os/main/artifacts/CLAIMS_MANIFEST.json
- https://raw.githubusercontent.com/KonkovDV/drillguard-os/main/artifacts/redteam_results.json
- https://raw.githubusercontent.com/KonkovDV/drillguard-os/main/artifacts/benchmark_results.json

Must show:

| Field | Value |
|-------|-------|
| algorithm_version | `0.2.2` |
| benchmark cases | `50` |
| n_scenarios × n_seeds | `10` × `5` |
| n_probes | `12` |
| n_hard_gates | `11` |
| first red-team probe | `baseline_prefix_equals_full` (not `baseline_causality_packoff`) |

## 3. Local consistency gate

```bash
pytest tests/test_artifact_claims_consistency.py -q
```

This test **fails CI** if published JSON disagrees with `CLAIMS_MANIFEST.json`.

## 4. Note on commit `82cff49`

`82cff49` is **v0.2.1 parent**. It already had 12 probes, but version string was `0.2.1`.  
Current application tip must be **`main` ≥ v0.2.2 evidence commits**, not `82cff49`.
