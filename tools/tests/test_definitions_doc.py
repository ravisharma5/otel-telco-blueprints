"""framework/definitions.md must match schemas/sources-table.yaml and common.schema.json.

The spec and schema are the source of truth. If a test here fails, fix the doc.
"""

from __future__ import annotations

import json
import re

from markdown_it import MarkdownIt

from tools.bplint.loader import load_yaml
from tools.tests.conftest import REPO_ROOT

DOC = (REPO_ROOT / "framework/definitions.md").read_text(encoding="utf-8")
SCHEMA = json.loads((REPO_ROOT / "schemas/common.schema.json").read_text(encoding="utf-8"))
ENUMS = SCHEMA["$defs"]
SPEC = load_yaml(REPO_ROOT / "schemas/sources-table.yaml")


def _sections(text):
    """Map h2 title -> list of tokens in that section."""
    tokens = MarkdownIt("commonmark").enable("table").parse(text)
    out, current = {}, None
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.tag == "h2":
            current = tokens[i + 1].content
            out[current] = []
        elif current is not None:
            out[current].append(tok)
    return out


def _tables(tokens):
    """Tables in a token list, each a list of rows (header row first)."""
    tables, rows, row, in_table = [], [], None, False
    for tok in tokens:
        if tok.type == "table_open":
            in_table, rows = True, []
        elif tok.type == "table_close":
            in_table = False
            tables.append(rows)
        elif in_table and tok.type == "tr_open":
            row = []
        elif in_table and tok.type == "tr_close":
            rows.append(row)
        elif in_table and tok.type == "inline":
            row.append(tok.content.strip())
    return tables


def _section_text(tokens):
    return "\n".join(t.content for t in tokens if t.type == "inline")


SECTIONS = _sections(DOC)
FENCE_OR_CODE = re.compile(r"```.*?```|`[^`]*`", re.S)


def test_sections_in_order():
    titles = [s for s in SECTIONS if not s.startswith("title:")]  # front matter parses as a heading
    assert titles == [
        "At a glance",
        "Claim basis",
        "Sources table",
        "Autonomy ceiling",
        "Component naming",
        "One-liner",
    ]


def test_claim_basis_rows_match_spec():
    table = _tables(SECTIONS["Claim basis"])[0]
    assert table[0] == ["Basis", "Use it for", "Write it as", "Source links to"]
    assert [row[0] for row in table[1:]] == SPEC["basis_values"]


def test_claim_basis_says_recipes_have_no_validation_status():
    text = _section_text(SECTIONS["Claim basis"])
    assert "recipes" in text and "no validation status" in text


def test_sources_table_columns_code_span_matches_spec():
    text = _section_text(SECTIONS["Sources table"])
    assert "`" + " | ".join(SPEC["columns"]) + "`" in text


def test_sources_table_worked_example_uses_canonical_header():
    tables = _tables(SECTIONS["Sources table"])
    examples = [tb for tb in tables if tb[0] == SPEC["columns"]]
    assert examples and len(examples[0]) - 1 == 2
    basis = {b.lower() for b in SPEC["basis_values"]}
    assert all(row[2].lower() in basis for row in examples[0][1:])


def test_sources_table_states_the_source_rule():
    text = _section_text(SECTIONS["Sources table"])
    assert "never the page itself" in text.lower()
    for code in ("VT002", "VT004", "VT007"):
        assert code in text


def test_autonomy_table_matches_enum():
    rows = _tables(SECTIONS["Autonomy ceiling"])[0][1:]
    assert [r[0] for r in rows] == ENUMS["autonomy_ceiling"]["enum"]


def test_component_naming_section():
    text = _section_text(SECTIONS["Component naming"])
    standard = (
        "Any component can be replaced. "
        "The Red Hat products named here show one way to build this design."
    )
    assert standard in text
    assert "Blueprints.InlineStatus" in text


def test_one_liner_section():
    text = _section_text(SECTIONS["One-liner"])
    assert "one_liner" in text and "autonomy ceiling" in text
    assert "no readiness codes" in text


def test_no_readiness_codes_outside_code():
    prose = FENCE_OR_CODE.sub("", DOC)
    assert not re.search(r"\b[EM][0-4]\b", prose)
