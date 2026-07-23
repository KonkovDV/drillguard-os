from drillguard.regimes import add_regimes, classify_operation
from drillguard.synthetic import make_scenario
from drillguard.timebase import prepare_timebase


def test_classify():
    assert classify_operation("drilling ahead") == "drilling"
    assert classify_operation("connection") == "connection"

def test_first_row_not_regime_change():
    df, _ = make_scenario("normal", n=50, seed=0)
    out = add_regimes(prepare_timebase(df))
    assert not bool(out.loc[0, "regime_change"])

def test_connection_resets_adaptation():
    df, _ = make_scenario("connection", n=200, seed=0)
    out = add_regimes(prepare_timebase(df), adaptation_points=15)
    # find first connection row
    idx = out.index[out["regime"] == "connection"][0]
    assert out.loc[idx, "regime_change"]
    assert out.loc[idx, "regime_adapting"]
