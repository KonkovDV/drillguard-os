"""Regime reset / adaptation tests."""

from drillguard.detector import detect
from drillguard.regimes import add_regimes
from drillguard.synthetic import make_scenario
from drillguard.timebase import prepare_timebase


def test_connection_starts_adaptation():
    df, _ = make_scenario("connection", n=250, seed=0)
    out = add_regimes(prepare_timebase(df), adaptation_points=15)
    idx = int(out.index[out["regime"] == "connection"][0])
    assert bool(out.loc[idx, "regime_change"])
    assert bool(out.loc[idx, "regime_adapting"])


def test_return_to_drilling_gets_new_run_baseline():
    df, _ = make_scenario("connection", n=300, seed=0)
    # After connection window, operation returns to drilling in generator? 
    # Current generator keeps connection until b then resumes drilling values with op still connection until b.
    # Force return:
    a = int(len(df) * 0.45)
    b = a + 40
    df.loc[a:b, "operation"] = "connection"
    df.loc[b + 1 :, "operation"] = "drilling"
    out = detect(df)
    # After return there should be insufficient_history / warmup again
    after = out.iloc[b + 1 : b + 20]
    assert (after["event"] == "insufficient_history").any() or (after["regime_adapting"]).any()
