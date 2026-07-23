import pytest
from drillguard.ingestion import IngestionError, validate_frame
from drillguard.schema import REQUIRED_COLUMNS, schema_manifest
import pandas as pd

def test_schema_manifest():
    m = schema_manifest()
    assert "heuristic_score" in m["score_semantics"]
    assert set(REQUIRED_COLUMNS) <= set(m["required_columns"])

def test_missing_column():
    df = pd.DataFrame({c: [1] for c in REQUIRED_COLUMNS if c != "pump_flow_lpm"})
    df["timestamp"] = ["2026-01-01"]
    with pytest.raises(IngestionError):
        validate_frame(df)
