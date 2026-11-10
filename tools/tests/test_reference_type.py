"""The reference doc type: schema, discovery, budgets, and no validation table."""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from tools.bplint.cli import discover
from tools.bplint.loader import load_yaml
from tools.tests.conftest import FIXTURES, REPO_ROOT, run_bplint

SCHEMAS = REPO_ROOT / "schemas"
VALID_REFERENCE = FIXTURES / "valid/reference/README.md"

SAMPLE = {
    "type": "reference",
    "title": "Fictional reference page",
    "question": "How should the fictional gate route a demo request?",
    "doc_status": "draft",
    "platform_blueprints": ["PB-06", "PB-07"],
    "otel_slots": ["decision"],
    "clarity_reviewed": "2026-11-07",
}


def _reference_validator() -> Draft202012Validator:
    reg = Registry()
    for p in SCHEMAS.glob("*.schema.json"):
        s = json.loads(p.read_text())
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    schema = json.loads((SCHEMAS / "reference.schema.json").read_text())
    return Draft202012Validator(
        schema, registry=reg, format_checker=Draft202012Validator.FORMAT_CHECKER
    )


def test_valid_reference_fixture_clean():
    rc, findings = run_bplint(VALID_REFERENCE)
    assert findings == []
    assert rc == 0


def test_reference_gets_no_vt001():
    _, findings = run_bplint(VALID_REFERENCE)
    assert "VT001" not in {f["code"] for f in findings}


def test_reference_budgets_have_no_validation_section():
    budgets = load_yaml(REPO_ROOT / "tools/bplint/budgets.yaml")
    spec = budgets["types"]["reference"]
    assert "validation_section" not in spec
    titles = [s["title"] for s in spec["sections"]]
    assert titles == [
        "At a glance",
        "The question",
        "The principle",
        "The design",
        "Trade-offs and limits",
        "Used by",
    ]


def test_discover_reference_globs_first():
    found = dict(
        discover(
            {
                "reference_globs": ["framework/definitions.md"],
                "doc_globs": ["framework/*.md"],
            }
        )
    )
    assert found[REPO_ROOT / "framework/definitions.md"] is True
    assert found[REPO_ROOT / "framework/glossary.md"] is False


def test_repo_config_lists_reference_globs():
    config = load_yaml(REPO_ROOT / "tools/bplint/config.yaml")
    assert "framework/index.md" in config["reference_globs"]
    assert "architecture/*.md" in config["reference_globs"]


def test_reference_schema_accepts_sample():
    assert list(_reference_validator().iter_errors(SAMPLE)) == []


def test_reference_schema_rejects_unknown_field():
    v = _reference_validator()
    errors = list(v.iter_errors(dict(SAMPLE, requirement_ids=["X"])))
    assert any(e.validator == "additionalProperties" for e in errors)


def test_reference_schema_rejects_bad_platform_id():
    v = _reference_validator()
    assert not v.is_valid(dict(SAMPLE, platform_blueprints=["PB-6"]))


def test_unknown_type_message_lists_known_types(tmp_path):
    page = tmp_path / "README.md"
    page.write_text(VALID_REFERENCE.read_text().replace('type: "reference"', 'type: "essay"', 1))
    _, findings = run_bplint(page)
    msgs = [f["message"] for f in findings if f["code"] == "FM002"]
    assert msgs and "'platform', 'reference', 'use-case'" in msgs[0]


# ---------- reference page template ----------

TEMPLATE = REPO_ROOT / "templates/reference-page.md"
REFERENCE_SPEC = load_yaml(REPO_ROOT / "tools/bplint/budgets.yaml")["types"]["reference"]


def _template_parts():
    from tools.bplint.loader import split_front_matter

    fm, body, _ = split_front_matter(TEMPLATE.read_text(encoding="utf-8"))
    return fm, body


def _template_tokens(body):
    from markdown_it import MarkdownIt

    return MarkdownIt("commonmark").enable("table").parse(body)


def test_reference_template_sections():
    _, body = _template_parts()
    toks = _template_tokens(body)
    titles = [
        toks[i + 1].content
        for i, t in enumerate(toks)
        if t.type == "heading_open" and t.tag == "h2"
    ]
    assert titles == [s["title"] for s in REFERENCE_SPEC["sections"]]


def test_reference_template_at_a_glance():
    _, body = _template_parts()
    toks = _template_tokens(body)
    start = next(i for i, t in enumerate(toks) if t.type == "table_open")
    labels, in_body, first_cell = [], False, False
    for i in range(start, len(toks)):
        t = toks[i]
        if t.type == "table_close":
            break
        if t.type == "tbody_open":
            in_body = True
        elif in_body and t.type == "tr_open":
            first_cell = True
        elif in_body and first_cell and t.type == "inline":
            labels.append(t.content.strip())
            first_cell = False
    assert labels == REFERENCE_SPEC["at_a_glance_rows"]


def test_reference_template_front_matter():
    fm, _ = _template_parts()
    schema = json.loads((SCHEMAS / "reference.schema.json").read_text())
    assert set(fm) <= set(schema["properties"])
    assert fm["type"] == "reference"
    assert list(_reference_validator().iter_errors(fm)) == []


def test_reference_template_no_validation_table():
    import re

    text = TEMPLATE.read_text(encoding="utf-8")
    headings_and_headers = [
        line for line in text.splitlines() if line.startswith("#") or line.startswith("|")
    ]
    assert not any("Validation" in line for line in headings_and_headers)
    assert not re.search(r"\b(E[0-4]|M[0-3])\b", text)


def test_reference_template_replaceable():
    assert "Any component can be replaced" in TEMPLATE.read_text(encoding="utf-8")


def test_reference_template_lints_clean():
    _, findings = run_bplint(TEMPLATE, config=REPO_ROOT / "tools/bplint/config.yaml")
    codes = {f["code"] for f in findings}
    assert not codes & {"SC001", "AG001", "FM002"}, findings
