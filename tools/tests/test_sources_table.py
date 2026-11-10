"""Tests for VT001, VT002, VT004, and VT007 on the Sources table."""

from __future__ import annotations

import pytest

from tools.bplint.cli import ConfigError, _check_sources_spec
from tools.bplint.loader import load_yaml
from tools.tests.conftest import REPO_ROOT
from tools.tests.test_frontmatter_checks import (
    SOURCES_HEADER,
    codes,
    lint,
    platform_fm,
    platform_sections,
    render,
    use_case_fm,
    use_case_sections,
)

SPEC = load_yaml(REPO_ROOT / "schemas/sources-table.yaml")
NOTE = "sources/note.md"


def row(n=1, basis="model card", source="[card](https://example.com/card)", claim=None):
    return f"| {n} | {claim or f'Claim {n}'} | {basis} | {source} |"


def doc_with(tmp_path, rows, header=SOURCES_HEADER, rel="README.md"):
    (tmp_path / "sources").mkdir(exist_ok=True)
    (tmp_path / NOTE).write_text("# Note\n")
    secs = use_case_sections()
    secs["Sources"] = header + "\n" + "\n".join(rows)
    return lint(tmp_path, render(use_case_fm(), secs), name=rel)


def vt(findings, code=None):
    return [f for f in findings if f.code.startswith("VT") and (code is None or f.code == code)]


# ---- spec ----------------------------------------------------------------


def test_spec_columns_and_basis_values():
    assert SPEC["columns"] == ["#", "Claim", "Basis", "Source"]
    assert SPEC["basis_values"] == ["model card", "research", "Red Hat guidance", "industry use case"]


@pytest.mark.parametrize("drop", ["Basis", "Source", "Claim"])
def test_spec_missing_required_column_is_config_error(drop):
    spec = dict(SPEC, columns=[c for c in SPEC["columns"] if c != drop])
    with pytest.raises(ConfigError):
        _check_sources_spec(spec)


def test_spec_basis_values_must_be_strings():
    with pytest.raises(ConfigError):
        _check_sources_spec(dict(SPEC, basis_values="model card"))


# ---- VT001 / VT002 -------------------------------------------------------


def test_valid_table_is_clean(tmp_path):
    assert vt(doc_with(tmp_path, [row(1), row(2, "research", f"[note]({NOTE})")])) == []


def test_no_table_is_vt001(tmp_path):
    secs = use_case_sections()
    secs["Sources"] = "No table here."
    assert codes(lint(tmp_path, render(use_case_fm(), secs)), "VT001") == ["VT001"]


def test_missing_sources_section_is_vt001(tmp_path):
    secs = use_case_sections()
    secs.pop("Sources")
    vt1 = vt(lint(tmp_path, render(use_case_fm(), secs)), "VT001")
    assert len(vt1) == 1 and vt1[0].line == 1


def test_platform_uses_sources_and_acceptance(tmp_path):
    secs = platform_sections()
    secs["Sources and acceptance"] = "- Gate bullet only"
    assert codes(lint(tmp_path, render(platform_fm(), secs)), "VT001") == ["VT001"]


def test_header_missing_basis_is_vt002_and_skips_rows(tmp_path):
    header = "| # | Claim | Source |\n|---|---|---|"
    findings = vt(doc_with(tmp_path, ["| 1 | c | x |"], header=header))
    assert codes(findings) == ["VT002"]
    assert "Basis" in findings[0].message


def test_reordered_columns_is_vt002(tmp_path):
    header = "| # | Claim | Source | Basis |\n|---|---|---|---|"
    assert codes(vt(doc_with(tmp_path, [row()], header=header))) == ["VT002"]


def test_old_validation_header_is_vt002(tmp_path):
    header = (
        "| # | Claim | Load-bearing | E-level | Evidence |\n|---|---|---|---|---|"
    )
    assert codes(vt(doc_with(tmp_path, ["| 1 | c | yes | E0 | x |"], header=header))) == ["VT002"]


# ---- VT004 ---------------------------------------------------------------


def test_no_source_link_is_vt004(tmp_path):
    findings = vt(doc_with(tmp_path, [row(source="the model card")]))
    assert codes(findings) == ["VT004"] and "no Source link" in findings[0].message


@pytest.mark.parametrize("href", ["mailto:a@example.com", "ftp://example.com/x", "//example.com/x"])
def test_non_http_external_scheme_is_vt004(tmp_path, href):
    assert codes(vt(doc_with(tmp_path, [row(source=f"[x]({href})")]))) == ["VT004"]


def test_http_and_https_are_ok(tmp_path):
    rows = [row(1, source="[a](http://example.com/a)"), row(2, source="[b](HTTPS://example.com/b)")]
    assert vt(doc_with(tmp_path, rows)) == []


def test_missing_repo_file_is_vt004(tmp_path):
    findings = vt(doc_with(tmp_path, [row(source="[x](sources/missing.md)")]))
    assert codes(findings) == ["VT004"] and "does not exist" in findings[0].message


def test_path_outside_repo_is_vt004(tmp_path):
    findings = vt(doc_with(tmp_path, [row(source="[x](../../../../etc/passwd)")]))
    assert codes(findings) == ["VT004"]
    assert "outside the repository" in findings[0].message


def test_self_link_is_vt004(tmp_path):
    findings = vt(doc_with(tmp_path, [row(source="[me](README.md)")]))
    assert codes(findings) == ["VT004"] and "page itself" in findings[0].message


def test_symlink_to_page_is_vt004(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources/alias.md").symlink_to(tmp_path / "README.md")
    findings = vt(doc_with(tmp_path, [row(source="[a](sources/alias.md)")]))
    assert codes(findings) == ["VT004"] and "page itself" in findings[0].message


def test_directory_is_vt004(tmp_path):
    assert codes(vt(doc_with(tmp_path, [row(source="[d](sources/)")]))) == ["VT004"]


def test_any_repo_folder_is_ok(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/report.md").write_text("x\n")
    assert vt(doc_with(tmp_path, [row(source="[r](docs/report.md)")])) == []


@pytest.mark.parametrize("link", [f"{NOTE}#results", f"{NOTE}?plain=1", "/sources/note.md", "sources/n%6Fte.md"])
def test_fragment_query_root_relative_and_encoded_links_are_ok(tmp_path, link):
    assert vt(doc_with(tmp_path, [row(source=f"[n](<{link}>)")])) == []


def test_parent_folder_file_is_ok(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / NOTE).write_text("x\n")
    findings = vt(doc_with(tmp_path, [row(source="[n](../../sources/note.md)")], rel="catalog/ops/README.md"))
    assert findings == []


# ---- VT007 ---------------------------------------------------------------


@pytest.mark.parametrize("basis", ["vendor blog", "", "evaluated", "E1"])
def test_bad_basis_is_vt007(tmp_path, basis):
    findings = vt(doc_with(tmp_path, [row(basis=basis)]))
    assert codes(findings) == ["VT007"]


@pytest.mark.parametrize("basis", ["Model Card", " research ", "red hat guidance", "INDUSTRY USE CASE"])
def test_basis_is_case_insensitive(tmp_path, basis):
    assert vt(doc_with(tmp_path, [row(basis=basis)])) == []


def test_bad_basis_and_bad_link_both_reported(tmp_path):
    findings = vt(doc_with(tmp_path, [row(basis="blog", source="no link")]))
    assert sorted(codes(findings)) == ["VT004", "VT007"]


def test_missing_basis_values_falls_back_to_defaults(tmp_path):
    from tools.tests.test_frontmatter_checks import ctx_for, make_doc
    from tools.bplint.checks import sources_table

    (tmp_path / "sources").mkdir()
    secs = use_case_sections()
    secs["Sources"] = SOURCES_HEADER + "\n" + row(basis="vendor blog") + "\n" + row(2, basis="research")
    doc = make_doc(tmp_path, render(use_case_fm(), secs))
    ctx = ctx_for(tmp_path)
    ctx.sources_spec = {"columns": SPEC["columns"]}
    assert codes(sources_table.check(doc, ctx)) == ["VT007"]


# ---- retired codes -------------------------------------------------------


def test_retired_codes_are_never_emitted(tmp_path):
    findings = doc_with(tmp_path, [row(1), row(2, "research", f"[note]({NOTE})")])
    assert not {"VT003", "VT005", "VT006", "AG002"} & set(codes(findings))
