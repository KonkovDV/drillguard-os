import pandas as pd
import pytest
from drillguard.synthetic import make_scenario
from drillguard.timebase import prepare_timebase

def test_sort_and_dt():
    df, _ = make_scenario("normal", n=40, seed=0)
    df = df.iloc[::-1].reset_index(drop=True)
    out = prepare_timebase(df)
    assert out["timestamp"].is_monotonic_increasing
    assert out["median_dt_s"].iloc[-1] == pytest.approx(1.0, abs=0.01)

def test_duplicate_timestamps():
    df, _ = make_scenario("normal", n=40, seed=0)
    df.loc[5, "timestamp"] = df.loc[4, "timestamp"]
    out = prepare_timebase(df)
    assert out.attrs["dropped_duplicate_rows"] >= 1

def test_unparseable_timestamp():
    df, _ = make_scenario("normal", n=10, seed=0)
    df["timestamp"] = df["timestamp"].astype(str)
    df.loc[2, "timestamp"] = "not-a-time"
    with pytest.raises(ValueError):
        prepare_timebase(df)
