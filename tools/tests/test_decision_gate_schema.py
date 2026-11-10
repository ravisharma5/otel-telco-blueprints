"""Decision gate schema tests: payload fixtures, ceiling rules, and no defaults.

Valid payloads must pass. Each invalid payload breaks exactly one rule and
must fail. Thresholds are operator-set and referenced by policy version, so
the schema carries no `default` keyword and no threshold fields.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = REPO_ROOT / "schemas"
GATE_SCHEMA = SCHEMAS / "decision-gate.schema.json"
GATE_FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures" / "decision-gate"
VALID = sorted((GATE_FIXTURES / "valid").glob("*.json"))
INVALID = sorted((GATE_FIXTURES / "invalid").glob("*.json"))
LABELS = ["LOOK", "NOTIFY", "REVIEW", "ACT", "STOP"]


def _registry() -> Registry:
    reg = Registry()
    for p in SCHEMAS.glob("*.schema.json"):
        s = json.loads(p.read_text())
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    return reg


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(GATE_SCHEMA.read_text())


@pytest.fixture(scope="module")
def gate_validator(schema) -> Draft202012Validator:
    return Draft202012Validator(
        schema,
        registry=_registry(),
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def _load(p: pathlib.Path):
    return json.loads(p.read_text())


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys(v)


def test_fixture_counts():
    assert len(VALID) == 4
    assert len(INVALID) == 10


def test_schema_is_valid_draft_2020_12(schema):
    Draft202012Validator.check_schema(schema)
    assert schema["$id"].endswith(".invalid/schemas/decision-gate.schema.json")


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.name)
def test_valid_payload_passes(gate_validator, path):
    errors = [e.message for e in gate_validator.iter_errors(_load(path))]
    assert errors == []


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.name)
def test_invalid_payload_fails(gate_validator, path):
    assert not gate_validator.is_valid(_load(path))


def test_no_default_keyword(schema):
    assert "default" not in set(_keys(schema))


def test_no_threshold_fields(schema):
    assert not any("threshold" in k.lower() for k in _keys(schema))


def test_probabilities_sum_to_one():
    decisions = [d for d in map(_load, VALID) if d["kind"] == "gate_decision"]
    assert decisions
    for d in decisions:
        assert abs(sum(d["label_probabilities"].values()) - 1) <= 0.01, d["decision_id"]


def test_labels_match_policy_order(schema):
    assert schema["$defs"]["label"]["enum"] == LABELS


def test_stop_is_allowed_under_every_ceiling(gate_validator):
    base = _load(GATE_FIXTURES / "valid" / "gate-decision-stop.json")
    for ceiling in LABELS:
        assert gate_validator.is_valid({**base, "policy_ceiling": ceiling}), ceiling


def _allowed_under_ceiling(ceiling: str, outcome: str) -> bool:
    if outcome == "STOP":
        return True
    if ceiling == "STOP":
        return False
    return LABELS.index(outcome) <= LABELS.index(ceiling)


def test_outcome_above_ceiling_is_rejected(gate_validator):
    base = _load(GATE_FIXTURES / "valid" / "gate-decision-act.json")
    for ceiling in LABELS:
        for outcome in LABELS:
            approver = "noc-shift-lead" if outcome == "REVIEW" else None
            payload = {**base, "policy_ceiling": ceiling, "outcome": outcome, "required_approver": approver}
            assert gate_validator.is_valid(payload) == _allowed_under_ceiling(ceiling, outcome), (ceiling, outcome)


def test_stop_ceiling_rejects_act(gate_validator):
    base = _load(GATE_FIXTURES / "valid" / "gate-decision-act.json")
    assert not gate_validator.is_valid({**base, "policy_ceiling": "STOP", "outcome": "ACT"})


@pytest.mark.parametrize(
    "stamp",
    [
        "2026-11-09T10:15:01Z\n",
        "2026-13-09T10:15:01Z",
        "2026-11-32T10:15:01Z",
        "2026-11-09T24:00:00Z",
        "2026-11-09T10:61:00Z",
        "2026-11-09T10:15:01+25:00",
        "\u0662\u0660\u0662\u0666-11-09T10:15:01Z",
    ],
)
def test_timestamp_rejects_malformed_values(gate_validator, stamp):
    base = _load(GATE_FIXTURES / "valid" / "gate-decision-review.json")
    assert not gate_validator.is_valid({**base, "decided_at": stamp}), repr(stamp)


@pytest.mark.parametrize(
    "stamp",
    ["2026-11-09T10:15:01Z", "2026-11-09T23:59:59.250+05:30", "2026-02-28T00:00:00-08:00"],
)
def test_timestamp_accepts_rfc3339_values(gate_validator, stamp):
    base = _load(GATE_FIXTURES / "valid" / "gate-decision-review.json")
    assert gate_validator.is_valid({**base, "decided_at": stamp}), stamp


@pytest.mark.parametrize("field", ["decision_id", "request_id", "correlation_id"])
def test_ids_reject_a_trailing_newline(gate_validator, field):
    base = _load(GATE_FIXTURES / "valid" / "gate-decision-review.json")
    assert not gate_validator.is_valid({**base, field: base[field] + "\n"}), field


def _request():
    return _load(GATE_FIXTURES / "valid" / "action-request-restart-interface.json")


@pytest.mark.parametrize(
    "part, extra",
    [("proposed_step", {"override_gate": True}), ("evidence_bundle", {"x": 1})],
)
def test_request_nested_objects_reject_unknown_keys(gate_validator, part, extra):
    req = _request()
    req[part] = {**req[part], **extra}
    assert not gate_validator.is_valid(req), part


def test_request_parameters_stay_open(gate_validator):
    req = _request()
    req["proposed_step"]["parameters"] = {"device": "r2", "interface": "eth1", "dry_run": True}
    assert gate_validator.is_valid(req)
