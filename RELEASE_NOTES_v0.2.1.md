# Release notes — DrillGuard OS v0.2.1

Synthetic advisory demonstrator update focused on **honest metrics** and claim hygiene for INDUSTRIX packaging.

## Highlights

- Level A/B/C benchmark reporting; appearance rate demoted.
- `possible_influx_candidate` wording + lower heuristic score without pit/flow-out.
- Full Apache-2.0 license file for GitHub detection.
- Stronger causality / red-team hard gates (non-zero exit on failure).

## Not claimed

Field accuracy, kick diagnosis, economic impact, SIL/ПАЗ, calibrated probabilities, full hydraulics / 4DOF T&D.

## Verify

```bash
pip install -e ".[dev]"
pytest -q
python -m benchmark.run_benchmark
python -m benchmark.run_redteam
```
