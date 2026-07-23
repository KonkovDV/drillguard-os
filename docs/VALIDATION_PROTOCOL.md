# Validation protocol

## Allowed

- Temporal train / calibration / test splits.
- Well-level or operation-level holdout.
- Multi-seed synthetic stress tests (claim_level=`synthetic_only`).
- Causal baseline audits (no future points in features).

## Forbidden for quality claims

- Random shuffle of time series as primary validation.
- Training ML on synthetic data and reporting as field accuracy.
- Using set-membership “class appeared somewhere” as sole gate without delay/FA metrics.

## Required report fields

precision, recall, F1, false alarms per hour, detection delay (seconds), seed dispersion (p05/median/p95), normal-scenario FA table, claim_level marker.
