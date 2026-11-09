"""Tests for CR001 (clarity review recorded on done docs) and CR002 (its date)."""

from __future__ import annotations

from tools.bplint import cli
from tools.bplint.checks import clarity
from tools.bplint.markdown import parse_doc
from tools.tests.conftest import FIXED_TODAY, FIXTURES


def _doc(tmp_path, fm: str, is_blueprint=True):
    p = tmp_path / "bp.md"
    text = f"---\n{fm}---\n\n# T\n"
    p.write_text(text)
    return parse_doc(p, text, is_blueprint=is_blueprint)


def _ctx():
    return cli.load_context(FIXTURES / "config.yaml", today=FIXED_TODAY)


def test_done_without_clarity_reviewed_is_error(tmp_path):
    # A done doc without a clarity review fails CI.
    out = clarity.check(_doc(tmp_path, 'id: x\ndoc_status: "done"\n'), _ctx())
    assert [(f.code, f.severity) for f in out] == [("CR001", "error")]
    assert out[0].line == 3


def test_done_without_clarity_reviewed_non_blueprint_is_error(tmp_path):
    out = clarity.check(_doc(tmp_path, 'doc_status: "done"\n', is_blueprint=False), _ctx())
    assert [(f.code, f.severity) for f in out] == [("CR001", "error")]


def test_draft_without_clarity_reviewed_is_clean(tmp_path):
    assert clarity.check(_doc(tmp_path, 'doc_status: "draft"\n'), _ctx()) == []


def test_done_with_clarity_reviewed_is_clean(tmp_path):
    doc = _doc(tmp_path, 'doc_status: "done"\nclarity_reviewed: "2026-11-07"\n')
    assert clarity.check(doc, _ctx()) == []


def test_review_without_clarity_reviewed_is_clean(tmp_path):
    assert clarity.check(_doc(tmp_path, 'doc_status: "review"\n'), _ctx()) == []


def test_no_front_matter_is_clean(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text("# T\n")
    assert clarity.check(parse_doc(p, "# T\n", is_blueprint=False), _ctx()) == []


# ---- CR002 -----------------------------------------------------------

import pytest  # noqa: E402


@pytest.mark.parametrize("value", ['"yes"', "yes", "soon", '"2026-13-40"', "2026-13-40", '"2026-1-5"'])
def test_non_date_clarity_reviewed_on_doc_is_cr002(tmp_path, value):
    fm = f'title: x\ndoc_status: "review"\nclarity_reviewed: {value}\n'
    out = clarity.check(_doc(tmp_path, fm, is_blueprint=False), _ctx())
    assert [(f.code, f.severity) for f in out] == [("CR002", "error")]
    assert out[0].line == 4
    assert "quoted ISO date" in out[0].message


@pytest.mark.parametrize("value", ['"2026-11-07"', "2026-11-07"])
def test_iso_date_clarity_reviewed_on_doc_is_clean(tmp_path, value):
    fm = f'doc_status: "done"\nclarity_reviewed: {value}\n'
    assert clarity.check(_doc(tmp_path, fm, is_blueprint=False), _ctx()) == []


def test_blueprint_never_gets_cr002(tmp_path):
    # The blueprint schemas report a bad clarity_reviewed as FM002.
    fm = 'doc_status: "review"\nclarity_reviewed: "yes"\n'
    assert clarity.check(_doc(tmp_path, fm), _ctx()) == []
