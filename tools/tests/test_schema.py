"""Schema tests: enums, facets, cross-file $ref, and the PyYAML date pitfall."""

from __future__ import annotations

import datetime
import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = REPO_ROOT / "schemas"
SCHEMA_FILES = [
    "common.schema.json",
    "platform.schema.json",
    "use-case.schema.json",
]


def _registry() -> Registry:
    reg = Registry()
    for p in SCHEMAS.glob("*.schema.json"):
        s = json.loads(p.read_text())
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    return reg


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS / name).read_text())
    return Draft202012Validator(
        schema,
        registry=_registry(),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def _error_paths(validator: Draft202012Validator, instance) -> list[str]:
    return [".".join(str(x) for x in e.absolute_path) for e in validator.iter_errors(instance)]


USE_CASE = {
    "id": "UC-DEMO-01",
    "type": "use-case",
    "title": "Fictional widget triage",
    "doc_status": "draft",
    "domain": "demo",
    "flagship": False,
    "otel_slots": ["llm", "safety"],
    "model_readiness": "M2",
    "evidence_level": "E1",
    "autonomy_ceiling": "recommend-with-approval",
    "placement_tier": ["regional"],
    "honest_one_liner": "M2 / E1 / recommend-with-approval. Method defined, not yet run.",
    "platform_blueprints": ["PB-04"],
    "agent_school": [301],
}

PLATFORM = {
    "id": "PB-04",
    "type": "platform",
    "title": "Fictional platform blueprint",
    "readiness_question": "What does it take to serve the demo slot?",
    "doc_status": "draft",
    "otel_slots": ["llm"],
    "model_readiness": "n/a",
    "evidence_level": "E0",
    "placement_tier": ["core"],
    "honest_one_liner": "E0. Described from vendor docs only.",
    "top_decisions": ["Pick a runtime", "Pick a tier"],
    "agent_school": [201],
}

@pytest.mark.parametrize("name", SCHEMA_FILES)
def test_schema_is_valid_draft_2020_12(name):
    schema = json.loads((SCHEMAS / name).read_text())
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == f"https://otel-telco-blueprints.invalid/schemas/{name}"


def test_claim_term_map_present():
    common = json.loads((SCHEMAS / "common.schema.json").read_text())
    assert common["x-claim-term-map"]["operator-validated"] == "E4"
    assert common["x-claim-term-map"]["evaluated"] == "E3 (evaluated)"


def test_valid_use_case_passes():
    assert _error_paths(_validator("use-case.schema.json"), USE_CASE) == []


def test_use_case_bad_model_readiness_fails_on_path():
    v = _validator("use-case.schema.json")
    bad = dict(USE_CASE, model_readiness="M5")
    assert "model_readiness" in _error_paths(v, bad)


def test_use_case_rejects_na_model_readiness():
    v = _validator("use-case.schema.json")
    bad = dict(USE_CASE, model_readiness="n/a")
    assert "model_readiness" in _error_paths(v, bad)


def test_use_case_rejects_unknown_key():
    v = _validator("use-case.schema.json")
    bad = dict(USE_CASE, maturity_tier="sandbox")
    assert not v.is_valid(bad)


def test_use_case_date_object_fails():
    """Pitfall 1: an unquoted YAML date becomes datetime.date and must fail."""
    v = _validator("use-case.schema.json")
    bad = dict(USE_CASE, clarity_reviewed=datetime.date(2026, 11, 7))
    assert "clarity_reviewed" in _error_paths(v, bad)
    loaded = yaml.safe_load("d: 2026-11-07")
    assert isinstance(loaded["d"], datetime.date)


def test_valid_platform_with_na_passes():
    assert _error_paths(_validator("platform.schema.json"), PLATFORM) == []


def test_platform_top_decisions_max_three():
    v = _validator("platform.schema.json")
    bad = dict(PLATFORM, top_decisions=["a", "b", "c", "d"])
    assert "top_decisions" in _error_paths(v, bad)


def test_legacy_register_fields_rejected():
    """Legacy register fields fail additionalProperties (bplint maps this to FM002)."""
    for name, sample in (("use-case.schema.json", USE_CASE), ("platform.schema.json", PLATFORM)):
        v = _validator(name)
        bad = dict(sample, critical_path_components=["demo-gateway"])
        errors = list(v.iter_errors(bad))
        assert any(e.validator == "additionalProperties" for e in errors), name


def test_validation_table_columns():
    vt = yaml.safe_load((SCHEMAS / "validation-table.yaml").read_text())
    cols = vt["columns"]
    assert len(cols) == 12
    for c in ("Vendor-reported", "GSMA external", "Our operator-task eval"):
        assert c in cols
    assert vt["load_bearing_values"] == ["yes", "no"]
