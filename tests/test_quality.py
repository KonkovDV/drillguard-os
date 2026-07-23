import numpy as np
from drillguard.quality import add_quality_flags
from drillguard.synthetic import make_scenario
from drillguard.timebase import prepare_timebase

def test_nan_flag():
    df, _ = make_scenario("normal", n=50, seed=0)
    df = prepare_timebase(df)
    df.loc[10, "standpipe_pressure_kpa"] = np.nan
    out = add_quality_flags(df)
    assert not out.loc[10, "quality_ok"]
    assert "nan" in out.loc[10, "quality_reason"]

def test_negative_flow():
    df, _ = make_scenario("normal", n=50, seed=0)
    df = prepare_timebase(df)
    df.loc[12, "pump_flow_lpm"] = -10
    out = add_quality_flags(df)
    assert not out.loc[12, "quality_ok"]
    assert "negative" in out.loc[12, "quality_reason"]

def test_flagged_data_quality():
    df, _ = make_scenario("normal", n=50, seed=0)
    df = prepare_timebase(df)
    df.loc[3, "data_quality"] = "bad"
    out = add_quality_flags(df)
    assert not out.loc[3, "quality_ok"]
