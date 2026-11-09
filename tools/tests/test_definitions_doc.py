"""framework/definitions.md must match schemas/common.schema.json.

The schema is the source of truth. If a test here fails, fix the doc.
"""

from __future__ import annotations

import json

from markdown_it import MarkdownIt

from tools.tests.conftest import REPO_ROOT

DOC = (REPO_ROOT / "framework/definitions.md").read_text(encoding="utf-8")
SCHEMA = json.loads((REPO_ROOT / "schemas/common.schema.json").read_text(encoding="utf-8"))
ENUMS = SCHEMA["$defs"]


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


def _claim_table():
    for table in _tables(SECTIONS["Claim terms and evidence levels"]):
        if table[0][:2] == ["Term", "E-code"]:
            return table
    raise AssertionError("claim-terms table with Term | E-code columns not found")


def test_claim_terms_match_x_claim_term_map():
    pairs = {row[0]: row[1] for row in _claim_table()[1:]}
    assert pairs == SCHEMA["x-claim-term-map"]


def test_claim_table_covers_every_e_level():
    codes = {row[1].split()[0] for row in _claim_table()[1:]}
    assert set(ENUMS["e_level"]["enum"]) <= codes


def test_m_table_lists_exactly_m_levels():
    tables = _tables(SECTIONS["Model readiness (M0-M3)"])
    levels = [row[0] for row in tables[0][1:]]
    assert sorted(levels) == sorted(ENUMS["m_level"]["enum"])


def test_headline_section_worked_example():
    tokens = SECTIONS["Headline level: the minimum rule"]
    assert any("Load-bearing" in t[0] for t in _tables(tokens))
    text = _section_text(tokens)
    assert "minimum" in text
    assert "= E0" in text


def test_component_naming_section():
    text = _section_text(SECTIONS["Component naming"])
    standard = (
        "Any component can be replaced. "
        "The Red Hat products named here show one way to build this design."
    )
    assert standard in text
    assert "Blueprints.InlineStatus" in text


def test_platform_model_readiness_na():
    assert "model_readiness: n/a" in DOC


def test_evidence_location_rule():
    text = _section_text(SECTIONS["Evidence columns and links"])
    assert "evidence/" in text
    assert "parent folder" in text
    assert "itself" in text


def test_load_bearing_exactly_yes_or_no():
    text = _section_text(SECTIONS["Headline level: the minimum rule"])
    assert "exactly `yes` or `no`" in text
    assert "VT007" in text
    assert "still counts toward the minimum" in text


def test_honest_one_liner_checked_against_front_matter():
    text = _section_text(SECTIONS["Honest one-liner"])
    assert "AG002" in text
