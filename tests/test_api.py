import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from drillguard.api import create_app
from drillguard.synthetic import make_scenario


def test_health_and_screen(tmp_path):
    app = create_app()
    client = TestClient(app)
    assert client.get("/health").json()["control_actions"] is False
    df, _ = make_scenario("normal", n=80, seed=0)
    p = tmp_path / "u.csv"
    df.to_csv(p, index=False)
    r = client.post("/screen", files={"file": ("u.csv", p.read_bytes(), "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["score_semantics"].startswith("heuristic_score")
    assert body.get("claim_level") == "synthetic_only"
    assert body.get("requires_field_validation") is True
    assert "confidence" not in body["summary"]
    bad = client.post(
        "/screen",
        params={"origin": "field_validated"},
        files={"file": ("u.csv", p.read_bytes(), "text/csv")},
    )
    assert bad.status_code == 400
