"""Style guide and review checklist match budgets.yaml and linter codes.

budgets.yaml and the linter code are the source of truth. If a test fails, fix the doc.
"""

from __future__ import annotations

import re

import pytest
from markdown_it import MarkdownIt

from tools.bplint.loader import load_yaml
from tools.tests.conftest import REPO_ROOT

BUDGETS = load_yaml(REPO_ROOT / "tools/bplint/budgets.yaml")
STYLE = (REPO_ROOT / "framework/style-guide.md").read_text(encoding="utf-8")
CHECKLIST = (REPO_ROOT / "framework/review-checklist.md").read_text(encoding="utf-8")
MD = MarkdownIt("commonmark").enable("table")
SKELETON_HEADING = {
    "platform": "Platform blueprint",
    "use-case": "Use-case blueprint",
    "reference": "Reference page",
}
UNIT_WORD = {
    "rows": "row",
    "tables": "table",
    "steps": "step",
    "bullets": "bullet",
    "lines": "line",
    "diagrams": "diagram",
}
EXPECTED_CODES = {
    "FM001", "FM002", "RF001", "SC001", "SC002", "AG001", "BG001",
    "VT001", "VT002", "VT004", "VT007", "LK001", "LK002",
    "DG001", "CR001", "CR002", "ID001", "XR001",
}  # fmt: skip


def _skeleton_rows(heading):
    """Section -> budget cell from the skeleton table under `### heading`."""
    lines = STYLE.splitlines()
    start = lines.index(f"### {heading}")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("#"))
    rows, row, in_body = {}, None, False
    for tok in MD.parse("\n".join(lines[start + 1 : end])):
        if tok.type == "tbody_open":
            in_body = True
        elif tok.type == "tbody_close":
            in_body = False
        elif in_body and tok.type == "tr_open":
            row = []
        elif in_body and tok.type == "tr_close":
            rows[row[1]] = row[2]
        elif in_body and tok.type == "inline":
            row.append(tok.content.strip())
    return rows


def _cases():
    for btype, spec in BUDGETS["types"].items():
        for section in spec["sections"]:
            yield pytest.param(btype, section, id=f"{btype}:{section['title']}")


@pytest.mark.parametrize("btype,section", list(_cases()))
def test_section_budget_in_style_guide(btype, section):
    rows = _skeleton_rows(SKELETON_HEADING[btype])
    assert section["title"] in rows, f"{section['title']} missing from {btype} skeleton"
    cell = rows[section["title"]]
    for unit, limit in section.items():
        if unit == "title":
            continue
        pat = rf"\b{limit} {UNIT_WORD[unit]}s?\b"
        assert re.search(pat, cell), f"{btype}/{section['title']}: '{limit} {unit}' not in '{cell}'"


@pytest.mark.parametrize("btype", list(BUDGETS["types"]))
def test_skeleton_has_no_extra_sections(btype):
    rows = _skeleton_rows(SKELETON_HEADING[btype])
    titles = [s["title"] for s in BUDGETS["types"][btype]["sections"]]
    assert list(rows) == titles


@pytest.mark.parametrize("btype", list(BUDGETS["types"]))
def test_at_a_glance_labels_in_style_guide(btype):
    cell = _skeleton_rows(SKELETON_HEADING[btype])["At a glance"]
    for label in BUDGETS["types"][btype]["at_a_glance_rows"]:
        assert label in cell, label


def test_page_words_in_style_guide():
    values = []
    for spec in BUDGETS["types"].values():
        pw = spec["page_words"]
        values += list(pw.values()) if isinstance(pw, dict) else [pw]
    assert values
    for v in values:
        assert re.search(rf"\b{v} prose words\b", STYLE), v


def test_writing_rules_at_most_twelve():
    lines = STYLE.splitlines()
    start = lines.index("## Writing rules")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("## "))
    items = [ln for ln in lines[start + 1 : end] if re.match(r"^\d+\. ", ln)]
    assert 0 < len(items) <= 12


def test_checklist_mentions_clarity_pass():
    assert "humanizer" in CHECKLIST
    assert "clarity_reviewed" in CHECKLIST


def test_checklist_lists_every_code():
    missing = sorted(c for c in EXPECTED_CODES if c not in CHECKLIST)
    assert missing == []


def test_expected_codes_match_linter():
    found = set()
    for path in (REPO_ROOT / "tools/bplint/checks").glob("*.py"):
        found |= set(re.findall(r'"([A-Z]{2}[0-9]{3})"', path.read_text(encoding="utf-8")))
    assert found == EXPECTED_CODES


def _checklist_row(code):
    for line in CHECKLIST.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == code:
            return cells
    raise AssertionError(f"no checklist row for {code}")


def test_cr001_is_error_per_d33():
    assert _checklist_row("CR001")[1] == "error"
    for line in CHECKLIST.splitlines():
        if "CR001" in line:
            assert "warns" not in line, line


def test_checklist_lists_io001():
    # IO001 lives in tools/bplint/cli.py, so it is outside EXPECTED_CODES.
    assert _checklist_row("IO001")[1] == "error"


def test_style_guide_has_no_readiness_levels():
    assert not re.search(r"E-level|M-level|evidence level|\bE[0-4]\b|\bM[0-3]\b", STYLE, re.I)
    assert "Every factual claim links its source" in STYLE


def test_checklist_lists_validation_status_rule():
    assert "Blueprints.ValidationStatus" in CHECKLIST
