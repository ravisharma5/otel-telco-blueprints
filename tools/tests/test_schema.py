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
    "reference.schema.json",
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
    "autonomy_ceiling": "recommend-with-approval",
    "placement_tier": ["regional"],
    "one_liner": "Drafts triage labels with human approval. Needs a tool-calling LLM slot.",
    "platform_blueprints": ["PB-04"],
    "agent_school": [301],
    "depth": "entry",
    "card": {
        "goal": "incidents",
        "summary": "Drafts a triage label for each alarm and an engineer approves it.",
        "outcome": "Engineers spend less time sorting alarms by hand.",
        "audience": "NOC engineers and their business owner",
        "measures": ["Time to first triage"],
        "risk": "A wrong label slows the fix until an engineer catches it.",
    },
    "placement": {"regional": {"runs": ["llm-small", "safety"], "note": ""}},
    "adaptation": {
        "rung": "skills",
        "expertise": ["golden-set", "tool-contracts"],
        "bring": [{"item": "Read-only widget tools", "domains": ["oss-bss"], "mechanism": "tool-contract"}],
    },
}

PLATFORM = {
    "id": "PB-04",
    "type": "platform",
    "title": "Fictional platform blueprint",
    "readiness_question": "What does it take to serve the demo slot?",
    "doc_status": "draft",
    "otel_slots": ["llm"],
    "placement_tier": ["core"],
    "one_liner": "Serves the demo slot from one endpoint. Depends on a model runtime.",
    "top_decisions": ["Pick a runtime", "Pick a tier"],
    "agent_school": [201],
}

@pytest.mark.parametrize("name", SCHEMA_FILES)
def test_schema_is_valid_draft_2020_12(name):
    schema = json.loads((SCHEMAS / name).read_text())
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == f"https://otel-telco-blueprints.invalid/schemas/{name}"


def test_common_schema_has_no_readiness_levels():
    common = json.loads((SCHEMAS / "common.schema.json").read_text())
    assert "x-claim-term-map" not in common
    assert not {"e_level", "m_level"} & set(common["$defs"])


def test_valid_use_case_passes():
    assert _error_paths(_validator("use-case.schema.json"), USE_CASE) == []


def test_use_case_depth_is_required():
    v = _validator("use-case.schema.json")
    bad = {k: x for k, x in USE_CASE.items() if k != "depth"}
    assert not v.is_valid(bad)


@pytest.mark.parametrize("depth", ["recipe", "entry"])
def test_use_case_depth_values_pass(depth):
    assert _error_paths(_validator("use-case.schema.json"), dict(USE_CASE, depth=depth)) == []


def test_use_case_unknown_depth_fails():
    assert "depth" in _error_paths(_validator("use-case.schema.json"), dict(USE_CASE, depth="deep"))


def test_use_case_adaptation_is_required():
    v = _validator("use-case.schema.json")
    assert not v.is_valid({k: x for k, x in USE_CASE.items() if k != "adaptation"})


@pytest.mark.parametrize("rung", ["retrieval", "skills", "head-retrain", "lora-if-gap"])
def test_use_case_adaptation_rungs_pass(rung):
    ad = dict(USE_CASE["adaptation"], rung=rung)
    assert _error_paths(_validator("use-case.schema.json"), dict(USE_CASE, adaptation=ad)) == []


def _bring(**item):
    return [dict(USE_CASE["adaptation"]["bring"][0], **item)]


@pytest.mark.parametrize(
    "change",
    [
        {"rung": "lora"},
        {"expertise": ["golden-set", "vibes"]},
        {"expertise": []},
        {"bring": _bring(domains=["satellite"])},
        {"bring": _bring(mechanism="prompt")},
        {"bring": _bring(owner="Risk owner")},
        {"bring": _bring(item="x" * 61)},
        {"bring": []},
        {"extra": True},
    ],
)
def test_use_case_bad_adaptation_fails(change):
    ad = dict(USE_CASE["adaptation"], **change)
    paths = _error_paths(_validator("use-case.schema.json"), dict(USE_CASE, adaptation=ad))
    assert any(p == "adaptation" or p.startswith("adaptation.") for p in paths), paths


@pytest.mark.parametrize("field", ["card", "placement"])
def test_use_case_card_and_placement_are_required(field):
    v = _validator("use-case.schema.json")
    bad = {k: x for k, x in USE_CASE.items() if k != field}
    assert not v.is_valid(bad), field


def test_use_case_bad_autonomy_ceiling_fails_on_path():
    v = _validator("use-case.schema.json")
    bad = dict(USE_CASE, autonomy_ceiling="act-alone")
    assert "autonomy_ceiling" in _error_paths(v, bad)


@pytest.mark.parametrize("field", ["model_readiness", "evidence_level", "honest_one_liner"])
def test_retired_readiness_fields_rejected(field):
    for name, sample in (("use-case.schema.json", USE_CASE), ("platform.schema.json", PLATFORM)):
        errors = list(_validator(name).iter_errors(dict(sample, **{field: "E1"})))
        assert any(e.validator == "additionalProperties" for e in errors), (name, field)


def test_one_liner_is_required():
    for name, sample in (("use-case.schema.json", USE_CASE), ("platform.schema.json", PLATFORM)):
        bad = {k: v for k, v in sample.items() if k != "one_liner"}
        assert not _validator(name).is_valid(bad), name


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


def test_valid_platform_passes():
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


def test_sources_table_columns():
    spec = yaml.safe_load((SCHEMAS / "sources-table.yaml").read_text())
    assert spec["columns"] == ["#", "Claim", "Basis", "Source"]
    assert spec["basis_values"] == [
        "model card",
        "research",
        "Red Hat guidance",
        "industry use case",
        "project documentation",
    ]
    assert not (SCHEMAS / "validation-table.yaml").exists()


def test_platform_layers_use_names_not_codes():
    v = _validator("platform.schema.json")
    assert _error_paths(v, dict(PLATFORM, layers=["safety-governance", "action"])) == []
    assert "layers.0" in _error_paths(v, dict(PLATFORM, layers=["L6"]))
