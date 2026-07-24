import pandas as pd
import pytest

from drillguard.ingestion import IngestionError, validate_frame
from drillguard.schema import REQUIRED_COLUMNS, schema_manifest


def test_schema_manifest():
    m = schema_manifest()
    assert "heuristic_score" in m["score_semantics"]
    assert set(REQUIRED_COLUMNS) <= set(m["required_columns"])
    assert "temperature_c" in m["optional_columns"]
    assert "active_alarms" in m["optional_columns"]
    assert m["readiness_level"]["level"].startswith("УТГ 4")
    assert m["event_class_letter_ru"]["signal_conflict"] == "конфликт режима и сигналов"
    assert m.get("industrix_letter_alignment") is True

def test_missing_column():
    df = pd.DataFrame({c: [1] for c in REQUIRED_COLUMNS if c != "pump_flow_lpm"})
    df["timestamp"] = ["2026-01-01"]
    with pytest.raises(IngestionError):
        validate_frame(df)
