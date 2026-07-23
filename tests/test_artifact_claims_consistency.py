"""Fail CI if published artifacts disagree with CLAIMS_MANIFEST / current code."""

from __future__ import annotations

import json
from pathlib import Path

from benchmark.scenarios import CORE_SCENARIOS
from drillguard.schema import ALGORITHM_VERSION

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "CLAIMS_MANIFEST.json"
BENCH = ROOT / "artifacts" / "benchmark_results.json"
RED = ROOT / "artifacts" / "redteam_results.json"


def test_claims_manifest_matches_code_version():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert m["algorithm_version"] == ALGORITHM_VERSION
    assert m["expected_core_scenarios"] == len(CORE_SCENARIOS)
    assert m["expected_benchmark_cases"] == m["expected_core_scenarios"] * m["expected_seeds"]


def test_benchmark_artifact_matches_manifest():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    b = json.loads(BENCH.read_text(encoding="utf-8"))
    assert b.get("algorithm_version") == m["algorithm_version"]
    assert b.get("claim_level") == "synthetic_only"
    assert b.get("requires_field_validation") is True
    assert len(b.get("cases", [])) == m["expected_benchmark_cases"]
    assert b.get("n_scenarios") == m["expected_core_scenarios"]
    assert b.get("n_seeds") == m["expected_seeds"]
    assert "limitations_banner" in b
    # Appearance rate must not be the only/primary gate key
    assert "gates" in b
    assert b["gates"].get("event_appearance_rate_is_not_primary") is True
    # Normal gate
    assert b["aggregate"]["normal_scenario_gate"]["all_zero_complication_fa"] is True
    # Level separation present
    sample = b["cases"][0]
    assert "level_a" in sample and "level_b" in sample and "level_c" in sample


def test_redteam_artifact_matches_manifest():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    r = json.loads(RED.read_text(encoding="utf-8"))
    assert r.get("algorithm_version") == m["algorithm_version"]
    assert r.get("n_probes") == m["expected_redteam_probes"]
    assert r.get("n_hard_gates") == m["expected_redteam_hard_gates"]
    assert len(r.get("probes", [])) == m["expected_redteam_probes"]
    assert r.get("all_hard_gates_pass") is True
    hard = [p for p in r["probes"] if p.get("hard")]
    assert len(hard) == m["expected_redteam_hard_gates"]
    assert all(p["pass"] for p in hard)
    names = {p["name"] for p in r["probes"]}
    assert "ballooning_like_not_confirmed_manifestation" in names
    balloon = next(p for p in r["probes"] if p["name"] == "ballooning_like_not_confirmed_manifestation")
    assert balloon.get("well_control_overclaim") is False
    # Must not be the old 5-probe schema
    assert "baseline_causality_packoff" not in names
