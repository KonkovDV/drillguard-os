# Pilot plan

## Stage 0 — contract

Timestamp resolution, tag names, units, missing-data semantics, operation taxonomy, data owner, local deployment boundary, safety review, stop criteria.

## Stage 1 — retrospective archive

One rig or well series. **Temporal** split only (never random shuffle). Expert labels. Compare to existing alarms and post-job reports. Metrics: FA/h, detection delay, precision/recall/F1, card usefulness.

## Stage 2 — shadow mode

Read-only local deployment. Log cards + heuristic_score. **No** SCADA/ACS writes. Engineer labels useful / not useful / incorrect.

## Stage 3 — decision memo

Stop · recalibrate thresholds · expand archive · continue shadow · design controlled field test.  
No field pilot until object, data, owner, InfoSec, and stop criteria are agreed.

## Safety

No automatic actuation. No claim of preventing kicks, losses, stuck pipe, or blowouts.
