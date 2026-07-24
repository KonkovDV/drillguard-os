# Pilot plan (aligned with INDUSTRIX cover letter)

## Stage 0 — contract

Timestamp resolution, tag names, units, missing-data semantics, operation taxonomy, data owner, local deployment boundary, InfoSec, stop criteria. Agree pilot KPIs before work starts.

## Stage 1 — retrospective archive (first)

One rig or well series. **Not** a control-system connection.

- Describe available channels, units, sample rate.
- Check gaps, duplicates, delays, channel quality.
- Label operations.
- Confirm / reject episodes with experts + daily reports.
- Compare to existing alarms and current review procedure.
- Fit thresholds only on agreed historical period.
- Evaluate on a **temporal holdout** (never random shuffle).
- Define criteria for read-only / shadow transition.

Metrics to agree: FA/h (complications), detection delay, precision/recall vs labels, regime accuracy, robustness to gaps/noise/drift, share of cards useful to engineers, time-to-first-check, **zero control actions**, stop/go criteria.

## Stage 2 — local shadow mode

Read-only local deployment:

- no writes to control systems;
- no automatic commands;
- card journal;
- expert label per card: useful / incorrect / non-informative;
- `data_origin=shadow_mode` allowed in API/CLI allowlist.

## Stage 3 — decision memo

Stop · recalibrate · expand archive · continue shadow · design controlled field test.  
No field pilot until object, data, owner, InfoSec, and stop criteria are agreed.

## Safety

No automatic actuation. No claim of preventing kicks, losses, stuck pipe, or blowouts.  
Synthetic evidence confirms software loop reproducibility only.
