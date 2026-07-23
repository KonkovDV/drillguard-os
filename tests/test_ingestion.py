from pathlib import Path

import pytest

from drillguard.ingestion import IngestionError, load_csv, validate_frame
from drillguard.synthetic import make_scenario


def test_load_example(tmp_path: Path):
    df, _ = make_scenario("normal", n=50, seed=0)
    p = tmp_path / "t.csv"
    df.to_csv(p, index=False)
    out = load_csv(p)
    assert len(out) == 50

def test_empty_file(tmp_path: Path):
    p = tmp_path / "e.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(IngestionError):
        load_csv(p)

def test_validate_memory():
    df, _ = make_scenario("normal", n=30, seed=1)
    assert len(validate_frame(df)) == 30
