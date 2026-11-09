"""Tests for VT001-VT007 and the headline E-level rule."""

from __future__ import annotations

import pytest

from tools.tests.test_frontmatter_checks import (
    VT_HEADER,
    codes,
    lint,
    platform_fm,
    platform_sections,
    render,
    use_case_fm,
    use_case_sections,
)

REPORT = "evidence/report.md"


def row(n=1, lb="yes", e="E0", evidence="[card](https://example.com/card)", rev="—",
        vendor="—", gsma="—", ours=None):
    # Rows above E0 need an operator-task eval (only that column raises E); default it so tests change one thing.
    if ours is None:
        ours = "—" if e.strip().startswith("E0") or not e.strip().startswith("E") else "replay set"
    return (
        f"| {n} | Claim {n} | llm | {lb} | {vendor} | {gsma} | {ours} | {e} | {evidence} "
        f"| pass | 2026-11-07 | {rev} |"
    )


def repo_link(path=REPORT):
    return f"[report]({path})"


def doc_with(tmp_path, rows, fm_e="E0", header=VT_HEADER, **fm):
    (tmp_path / "evidence").mkdir(exist_ok=True)
    (tmp_path / REPORT).write_text("# Eval report\n")
    secs = use_case_sections()
    secs["Validation"] = header + "\n" + "\n".join(rows)
    return lint(tmp_path, render(use_case_fm(evidence_level=fm_e, **fm), secs))


def vt(findings, code=None):
    return [f for f in findings if f.code.startswith("VT") and (code is None or f.code == code)]


# ---- VT001 / VT002 -------------------------------------------------------


def test_no_table_is_vt001(tmp_path):
    secs = use_case_sections()
    secs["Validation"] = "Nothing measured yet."
    assert codes(lint(tmp_path, render(use_case_fm(), secs)), "VT001") == ["VT001"]


def test_missing_validation_section_is_vt001(tmp_path):
    secs = use_case_sections()
    secs.pop("Validation")
    findings = lint(tmp_path, render(use_case_fm(), secs))
    vt1 = vt(findings, "VT001")
    assert len(vt1) == 1 and vt1[0].line == 1


def test_header_missing_column_is_vt002_and_skips_rest(tmp_path):
    header = VT_HEADER.replace(" GSMA external |", "").replace("|---|---|---|---|---|---|---|---|---|---|---|---|", "|---|---|---|---|---|---|---|---|---|---|---|")
    bad = "| 1 | c | llm | yes | — | — | E9 | x | — | — | — |"
    findings = doc_with(tmp_path, [bad], fm_e="E2", header=header)
    assert codes(vt(findings)) == ["VT002"]


def test_reordered_columns_is_vt002(tmp_path):
    header = VT_HEADER.replace("| Result | Date |", "| Date | Result |")
    findings = doc_with(tmp_path, [row()], header=header)
    assert codes(vt(findings)) == ["VT002"]


def test_platform_uses_validation_and_acceptance(tmp_path):
    secs = platform_sections()
    secs["Validation and acceptance"] = "- Gate bullet only"
    assert codes(lint(tmp_path, render(platform_fm(), secs)), "VT001") == ["VT001"]


# ---- VT003 ---------------------------------------------------------------

MIXED = [
    row(1, "yes", "E2", repo_link(), "v1.0"),
    row(2, "yes", "E1", repo_link()),
    row(3, "no", "E0"),
]


def test_headline_matches_front_matter(tmp_path):
    assert vt(doc_with(tmp_path, MIXED, fm_e="E1")) == []


def test_headline_mismatch_is_vt003(tmp_path):
    findings = vt(doc_with(tmp_path, MIXED, fm_e="E2"), "VT003")
    assert len(findings) == 1
    assert "headline E-level is E1" in findings[0].message
    assert "front matter says E2" in findings[0].message


def test_no_load_bearing_rows_is_vt003(tmp_path):
    findings = vt(doc_with(tmp_path, [row(1, "no", "E0")]), "VT003")
    assert len(findings) == 1 and "no load-bearing rows" in findings[0].message


def test_missing_front_matter_level_skips_vt003(tmp_path):
    findings = doc_with(tmp_path, MIXED, fm_e=None)
    assert "RF001" in codes(findings)
    assert vt(findings, "VT003") == []


def test_invalid_front_matter_level_skips_vt003(tmp_path):
    findings = doc_with(tmp_path, MIXED, fm_e="E9")
    assert vt(findings, "VT003") == []


def test_evaluated_counts_as_e3(tmp_path):
    rows = [row(1, "yes", "E3 (evaluated)", repo_link(), "v1"), row(2, "yes", "E3", repo_link(), "v1")]
    assert vt(doc_with(tmp_path, rows, fm_e="E3")) == []


@pytest.mark.parametrize("cell", ["E5", "high"])
def test_invalid_e_level_cell_is_vt003(tmp_path, cell):
    rows = [row(1, "yes", "E0"), row(2, "yes", cell)]
    findings = vt(doc_with(tmp_path, rows), "VT003")
    assert len(findings) == 1 and "invalid E-level cell" in findings[0].message


# ---- VT004 ---------------------------------------------------------------


def test_e0_with_relative_link_is_vt004(tmp_path):
    assert codes(vt(doc_with(tmp_path, [row(1, "yes", "E0", repo_link())]))) == ["VT004"]


@pytest.mark.parametrize("level,rev", [("E1", "—"), ("E2", "v1")])
def test_e1_e2_with_http_link_is_vt004(tmp_path, level, rev):
    rows = [row(1, "yes", level, "[x](http://example.com/a)", rev)]
    assert codes(vt(doc_with(tmp_path, rows, fm_e=level))) == ["VT004"]


def test_e2_missing_repo_file_is_vt004(tmp_path):
    rows = [row(1, "yes", "E2", repo_link("evidence/missing.md"), "v1")]
    assert codes(vt(doc_with(tmp_path, rows, fm_e="E2"))) == ["VT004"]


def test_path_traversal_is_vt004(tmp_path):
    rows = [row(1, "yes", "E2", repo_link("../../../../etc/passwd"), "v1")]
    findings = vt(doc_with(tmp_path, rows, fm_e="E2"))
    assert codes(findings) == ["VT004"]
    assert "outside the repository" in findings[0].message


def test_absolute_path_is_vt004(tmp_path):
    rows = [row(1, "yes", "E1", repo_link("/etc/hosts"))]
    assert codes(vt(doc_with(tmp_path, rows, fm_e="E1"))) == ["VT004"]


def test_evaluated_missing_file_is_vt004(tmp_path):
    rows = [row(1, "yes", "E3 (evaluated)", repo_link("evidence/nope.md"), "v1")]
    assert codes(vt(doc_with(tmp_path, rows, fm_e="E3"))) == ["VT004"]


def test_no_evidence_link_is_vt004(tmp_path):
    findings = vt(doc_with(tmp_path, [row(1, "yes", "E0", "model card")]))
    assert codes(findings) == ["VT004"] and "no evidence link" in findings[0].message


def test_repo_link_with_fragment_is_ok(tmp_path):
    rows = [row(1, "yes", "E1", repo_link(REPORT + "#results"))]
    assert vt(doc_with(tmp_path, rows, fm_e="E1")) == []


# ---- VT005 ---------------------------------------------------------------


@pytest.mark.parametrize("rev", ["", "—", "-"])
def test_e2_plus_empty_revision_is_vt005(tmp_path, rev):
    rows = [row(1, "yes", "E2", repo_link(), rev)]
    assert codes(vt(doc_with(tmp_path, rows, fm_e="E2"))) == ["VT005"]


@pytest.mark.parametrize("level", ["E3", "E4"])
def test_e3_e4_empty_revision_is_vt005(tmp_path, level):
    rows = [row(1, "yes", level, repo_link(), "—")]
    assert codes(vt(doc_with(tmp_path, rows, fm_e=level))) == ["VT005"]


def test_e0_e1_empty_revision_is_fine(tmp_path):
    rows = [row(1, "yes", "E0"), row(2, "no", "E1", repo_link())]
    assert vt(doc_with(tmp_path, rows)) == []


# ---- VT006 ---------------------------------------------------------------


def test_vendor_only_row_above_e0_is_vt006(tmp_path):
    rows = [row(1, "yes", "E2", repo_link(), "v1", vendor="0.9 on card", ours="—")]
    findings = vt(doc_with(tmp_path, rows, fm_e="E2"))
    assert codes(findings) == ["VT006"]
    assert "Our operator-task eval" in findings[0].message


def test_vendor_only_row_at_e0_is_fine(tmp_path):
    rows = [row(1, "yes", "E0", vendor="0.9 on card", gsma="TeleQnA 80%")]
    assert vt(doc_with(tmp_path, rows)) == []


def test_vendor_with_own_eval_above_e0_is_fine(tmp_path):
    rows = [row(1, "yes", "E2", repo_link(), "v1", vendor="0.9", ours="replay set, 200 Qs")]
    assert vt(doc_with(tmp_path, rows, fm_e="E2")) == []


def test_vt006_e3_row_with_all_evidence_columns_empty(tmp_path):
    rows = [row(1, "yes", "E3", repo_link(), "v1", ours="—")]
    findings = vt(doc_with(tmp_path, rows, fm_e="E3"))
    assert codes(findings) == ["VT006"]
    assert findings[0].message == (
        "row 1: E-level E3 needs a non-empty 'Our operator-task eval' cell; "
        "only that column can raise E above E0"
    )


def test_vt006_e0_row_with_all_evidence_columns_empty_is_fine(tmp_path):
    assert vt(doc_with(tmp_path, [row(1, "yes", "E0")])) == []


def test_vt006_e2_row_with_own_eval_only_is_fine(tmp_path):
    rows = [row(1, "yes", "E2", repo_link(), "v1", ours="replay set")]
    assert vt(doc_with(tmp_path, rows, fm_e="E2")) == []


# ---- VT007 ---------------------------------------------------------------


@pytest.mark.parametrize("cell", ["Yes (core)", "**yes**", "y", "true", ""])
def test_vt007_bad_load_bearing_value(tmp_path, cell):
    rows = [row(1, "yes", "E0"), row(2, cell, "E0")]
    findings = vt(doc_with(tmp_path, rows), "VT007")
    assert len(findings) == 1
    assert "[yes, no]" in findings[0].message
    assert f"'{cell}'" in findings[0].message


@pytest.mark.parametrize("cell", ["yes", "Yes", " YES ", "no", "No"])
def test_vt007_accepts_yes_no_case_insensitive(tmp_path, cell):
    rows = [row(1, "yes", "E0"), row(2, cell, "E0")]
    assert vt(doc_with(tmp_path, rows), "VT007") == []


def test_vt007_cr01_reproduction_counts_row_toward_minimum(tmp_path):
    rows = [row(1, "yes", "E1", repo_link(), ours="replay"), row(2, "Yes (core)", "E0")]
    findings = vt(doc_with(tmp_path, rows, fm_e="E1"))
    assert sorted(codes(findings)) == ["VT003", "VT007"]
    vt3 = [f for f in findings if f.code == "VT003"]
    assert "headline E-level is E0" in vt3[0].message


def test_vt007_invalid_e_level_load_bearing_row_counts_as_lowest(tmp_path):
    rows = [row(1, "yes", "E2", repo_link(), "v1", ours="replay"), row(2, "yes", "E9")]
    findings = vt(doc_with(tmp_path, rows, fm_e="E2"), "VT003")
    assert len(findings) == 2
    assert any("invalid E-level cell" in f.message for f in findings)
    assert any("headline E-level is E0" in f.message for f in findings)


def test_vt007_invalid_e_level_unknown_load_bearing_counts_as_lowest(tmp_path):
    rows = [row(1, "yes", "E2", repo_link(), "v1", ours="replay"), row(2, "maybe", "E9")]
    findings = vt(doc_with(tmp_path, rows, fm_e="E2"))
    assert codes(findings, "VT007") == ["VT007"]
    assert any("headline E-level is E0" in f.message for f in findings if f.code == "VT003")


def test_vt007_invalid_e_level_non_load_bearing_row_is_ignored(tmp_path):
    rows = [row(1, "yes", "E2", repo_link(), "v1", ours="replay"), row(2, "no", "E9")]
    findings = vt(doc_with(tmp_path, rows, fm_e="E2"), "VT003")
    assert len(findings) == 1 and "invalid E-level cell" in findings[0].message


# ---- VT004: evidence location ---------------------------------------


def _e(level, link, rev="v1"):
    return row(1, "yes", level, link, rev, ours="replay set")


def _lint_at(tmp_path, rel_doc, rows, fm_e):
    secs = use_case_sections()
    secs["Validation"] = VT_HEADER + "\n" + "\n".join(rows)
    (tmp_path / rel_doc).parent.mkdir(parents=True, exist_ok=True)
    return lint(tmp_path, render(use_case_fm(evidence_level=fm_e), secs), name=rel_doc)


def test_cr02_self_link_is_vt004(tmp_path):
    findings = vt(doc_with(tmp_path, [_e("E4", "[self](README.md)", "r1")], fm_e="E4"))
    assert codes(findings) == ["VT004"]
    assert "cannot be the blueprint itself" in findings[0].message


def test_file_outside_evidence_dir_is_vt004(tmp_path):
    (tmp_path / "LICENSE").write_text("license\n")
    findings = vt(doc_with(tmp_path, [_e("E2", "[l](LICENSE)")], fm_e="E2"))
    assert codes(findings) == ["VT004"]
    assert "evidence/" in findings[0].message


def test_sibling_blueprint_evidence_is_vt004(tmp_path):
    (tmp_path / "b/evidence").mkdir(parents=True)
    (tmp_path / "b/evidence/x.jsonl").write_text("{}\n")
    findings = vt(_lint_at(tmp_path, "a/README.md", [_e("E2", "[x](../b/evidence/x.jsonl)")], "E2"))
    assert codes(findings) == ["VT004"]


@pytest.mark.parametrize("evdir,link", [
    ("evidence", "../../evidence/r.jsonl"),
    ("catalog/evidence", "../evidence/r.jsonl"),
])
def test_ancestor_evidence_dir_is_ok(tmp_path, evdir, link):
    (tmp_path / evdir).mkdir(parents=True)
    (tmp_path / evdir / "r.jsonl").write_text("{}\n")
    findings = vt(_lint_at(tmp_path, "catalog/ops/README.md", [_e("E2", f"[r]({link})")], "E2"))
    assert findings == []


def test_symlink_to_blueprint_is_vt004(tmp_path):
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence/alias.md").symlink_to(tmp_path / "README.md")
    findings = vt(doc_with(tmp_path, [_e("E2", "[a](evidence/alias.md)")], fm_e="E2"))
    assert codes(findings) == ["VT004"]


def test_evidence_directory_itself_is_vt004(tmp_path):
    findings = vt(doc_with(tmp_path, [_e("E2", "[d](evidence/)")], fm_e="E2"))
    assert codes(findings) == ["VT004"]


@pytest.mark.parametrize("fname,link", [
    ("eval-spec.md", "evidence/eval%2Dspec.md"),
    ("my report.md", "evidence/my%20report.md"),
    ("report.md", "evidence/report.md?plain=1"),
])
def test_wr04_encoded_and_query_evidence_is_ok(tmp_path, fname, link):
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence" / fname).write_text("x\n")
    assert vt(doc_with(tmp_path, [_e("E2", f"[s](<{link}>)")], fm_e="E2")) == []


def test_wr11_root_relative_evidence_is_ok(tmp_path):
    assert vt(doc_with(tmp_path, [_e("E2", "[r](/evidence/report.md)")], fm_e="E2")) == []
