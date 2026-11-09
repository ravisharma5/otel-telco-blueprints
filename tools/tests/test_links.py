"""Tests for LK001, LK002 (links) and DG001 (diagrams)."""

from __future__ import annotations

import dataclasses

import pytest

from tools.bplint import cli
from tools.bplint.checks import diagrams, links
from tools.bplint.markdown import parse_doc
from tools.tests.conftest import FIXED_TODAY, FIXTURES


@pytest.fixture
def ctx(tmp_path):
    base = cli.load_context(FIXTURES / "config.yaml", today=FIXED_TODAY)
    return dataclasses.replace(base, repo_root=tmp_path)


def _doc(tmp_path, body, name="docs/page.md"):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    return parse_doc(p, body, display=name, is_blueprint=False)


def _codes(findings):
    return [f.code for f in findings]


def test_missing_relative_target_is_lk001(tmp_path, ctx):
    doc = _doc(tmp_path, "# T\n\nSee [x](../nope.md).\n")
    out = links.check(doc, ctx)
    assert _codes(out) == ["LK001"]
    assert out[0].line == 3


def test_existing_target_without_anchor_is_clean(tmp_path, ctx):
    (tmp_path / "docs/other.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/other.md").write_text("# Other\n\n## Real heading\n")
    doc = _doc(tmp_path, "# T\n\nSee [x](other.md).\n")
    assert links.check(doc, ctx) == []


def test_missing_anchor_in_other_file_is_lk002(tmp_path, ctx):
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/other.md").write_text("# Other\n\n## Real heading\n")
    doc = _doc(tmp_path, "# T\n\nSee [x](other.md#missing).\n")
    assert _codes(links.check(doc, ctx)) == ["LK002"]


def test_existing_anchor_in_other_file_is_clean(tmp_path, ctx):
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/other.md").write_text("# Other\n\n### Real heading\n")
    doc = _doc(tmp_path, "# T\n\nSee [x](other.md#real-heading).\n")
    assert links.check(doc, ctx) == []


def test_missing_same_file_anchor_is_lk002(tmp_path, ctx):
    doc = _doc(tmp_path, "# T\n\nSee [x](#no-such-section).\n")
    assert _codes(links.check(doc, ctx)) == ["LK002"]


def test_same_file_anchor_matching_h2_is_clean(tmp_path, ctx):
    doc = _doc(tmp_path, "# T\n\nSee [x](#risks-and-limitations).\n\n## Risks and limitations\n\nText.\n")
    assert links.check(doc, ctx) == []


def test_external_links_are_skipped(tmp_path, ctx):
    doc = _doc(
        tmp_path,
        "# T\n\n[a](https://example.invalid/x) [b](http://example.invalid) [c](mailto:a@example.invalid)\n",
    )
    assert links.check(doc, ctx) == []


def test_link_outside_repo_is_lk001(tmp_path, ctx):
    doc = _doc(tmp_path, "# T\n\nSee [x](../../../../etc/passwd).\n")
    out = links.check(doc, ctx)
    assert _codes(out) == ["LK001"]
    assert "outside repository" in out[0].message


def test_missing_image_is_dg001(tmp_path, ctx):
    doc = _doc(tmp_path, "# T\n\n![Flow](diagrams/missing.svg)\n")
    out = diagrams.check(doc, ctx)
    assert _codes(out) == ["DG001"]
    assert out[0].line == 3


def test_existing_image_is_clean(tmp_path, ctx):
    (tmp_path / "docs/diagrams").mkdir(parents=True)
    (tmp_path / "docs/diagrams/flow.svg").write_text("<svg/>")
    doc = _doc(tmp_path, "# T\n\n![Flow](diagrams/flow.svg)\n")
    assert diagrams.check(doc, ctx) == []


def test_http_image_is_skipped(tmp_path, ctx):
    doc = _doc(tmp_path, "# T\n\n![Flow](https://example.invalid/flow.svg)\n")
    assert diagrams.check(doc, ctx) == []


def test_image_outside_repo_is_dg001(tmp_path, ctx):
    doc = _doc(tmp_path, "# T\n\n![Flow](../../../../tmp/flow.svg)\n")
    assert _codes(diagrams.check(doc, ctx)) == ["DG001"]


def test_root_relative_link_resolves_against_repo_root(tmp_path, ctx):
    (tmp_path / "README.md").write_text("# Root\n")
    doc = _doc(tmp_path, "# T\n\nSee [readme](/README.md).\n")
    assert links.check(doc, ctx) == []


def test_root_relative_missing_link_is_lk001(tmp_path, ctx):
    doc = _doc(tmp_path, "# T\n\nSee [x](/missing.md).\n")
    out = links.check(doc, ctx)
    assert _codes(out) == ["LK001"]
    assert "link target not found" in out[0].message
