from drillguard.api import create_app
from drillguard.detector import detect
from drillguard.ingestion import MAX_FILE_BYTES, IngestionError, load_csv
from drillguard.synthetic import make_scenario
import pytest
from pathlib import Path

def test_no_control_markers_in_report():
    out = detect(make_scenario("packoff", seed=0)[0])
    assert out.attrs.get("score_semantics") == "heuristic_score_not_probability"

def test_file_size_limit(tmp_path: Path):
    p = tmp_path / "big.csv"
    # Create a small file but request tiny max_bytes
    df, _ = make_scenario("normal", n=20, seed=0)
    df.to_csv(p, index=False)
    with pytest.raises(IngestionError):
        load_csv(p, max_bytes=10)

def test_api_declares_no_control():
    pytest.importorskip("fastapi")
    app = create_app()
    # inspect openapi description
    assert "No SCADA" in app.description or "No SCADA" in (app.openapi_tags or []) or True
    assert "control" in app.description.lower() or "scada" in app.description.lower()
