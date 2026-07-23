"""Future leakage and prefix/full causality tests."""

import numpy as np

from drillguard.detector import detect
from drillguard.synthetic import make_scenario


def test_prefix_matches_full_stream_z():
    df, _ = make_scenario("packoff", seed=0, n=220)
    cut = 130
    full = detect(df)
    pref = detect(df.iloc[:cut].copy())
    for c in ("standpipe_pressure_kpa_z", "pump_flow_lpm_z"):
        a = np.nan_to_num(pref[c].to_numpy(dtype=float), nan=0.0)
        b = np.nan_to_num(full[c].iloc[:cut].to_numpy(dtype=float), nan=0.0)
        assert np.allclose(a, b, atol=1e-6)


def test_future_mutation_does_not_change_past_z():
    df, _ = make_scenario("normal", seed=2, n=160)
    base = detect(df)
    mut_df = df.copy()
    mut_df.loc[130:, "standpipe_pressure_kpa"] += 8000
    mut = detect(mut_df)
    cut = 90
    assert np.allclose(
        np.nan_to_num(base["standpipe_pressure_kpa_z"].iloc[:cut], nan=0.0),
        np.nan_to_num(mut["standpipe_pressure_kpa_z"].iloc[:cut], nan=0.0),
        atol=1e-6,
    )


def test_strong_event_does_not_absorb_baseline():
    df, _ = make_scenario("packoff", seed=0)
    out = detect(df)
    # Late in event, |z| should remain elevated (baseline frozen after warmup)
    z = out["standpipe_pressure_kpa_z"].iloc[-1]
    assert abs(float(z)) > 3.0


def test_candidate_mask_flag_present():
    df, _ = make_scenario("packoff", seed=0, n=200)
    out = detect(df)
    assert "baseline_candidate_mask_applied" in out.columns
    assert bool(out["baseline_candidate_mask_applied"].iloc[-1]) is True


def test_baseline_does_not_track_confirmed_ramp():
    """During a strong sustained ramp, baseline median must stay near pre-event level."""
    from drillguard.baseline import BaselineConfig, add_causal_baselines
    from drillguard.ingestion import validate_frame
    from drillguard.quality import add_quality_flags
    from drillguard.regimes import add_regimes
    from drillguard.timebase import prepare_timebase

    df, gt = make_scenario("packoff", seed=0)
    frame = add_causal_baselines(
        add_regimes(add_quality_flags(prepare_timebase(validate_frame(df)))),
        cfg=BaselineConfig(slow_adapt_alpha=0.05, freeze_on_candidate=True),
    )
    a = int(gt["event_start_idx"])
    pre = float(frame.loc[a - 5, "standpipe_pressure_kpa_baseline"])
    late = float(frame.loc[len(frame) - 1, "standpipe_pressure_kpa_baseline"])
    # Must not climb toward the elevated event level
    assert abs(late - pre) < 200.0
