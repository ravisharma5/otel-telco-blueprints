"""Tests for repo-level checks ID001, XR001, and IDEA002."""

from __future__ import annotations

from tools.bplint.checks import REPO_CHECKS, repo
from tools.tests.conftest import FIXTURES, run_bplint
from tools.tests.test_frontmatter_checks import (
    ctx_for,
    make_doc,
    platform_fm,
    platform_sections,
    render,
    use_case_fm,
    use_case_sections,
)


def _key_line(text, key):
    return next(i for i, ln in enumerate(text.splitlines(), 1) if ln.startswith(f"{key}:"))


def _ctx(tmp_path, docs, discovery=True):
    ctx = ctx_for(tmp_path)
    ctx.docs = list(docs)
    ctx.discovery = discovery
    return ctx


def test_repo_checks_registered_in_order():
    assert REPO_CHECKS == [repo.check_ids, repo.check_refs, repo.check_idea_merges]


def test_context_discovery_defaults_false(tmp_path):
    assert ctx_for(tmp_path).discovery is False


def test_duplicate_id_is_id001_on_second_doc(tmp_path):
    a = make_doc(tmp_path, render(platform_fm(), platform_sections()), name="a/README.md")
    text_b = render(platform_fm(), platform_sections())
    b = make_doc(tmp_path, text_b, name="b/README.md")
    out = repo.check_ids(_ctx(tmp_path, [b, a]))
    assert [(f.code, f.severity, f.path) for f in out] == [("ID001", "error", "b/README.md")]
    assert out[0].line == _key_line(text_b, "id")
    assert "duplicate id 'PB-04'" in out[0].message and "a/README.md" in out[0].message


def test_unique_ids_are_clean(tmp_path):
    a = make_doc(tmp_path, render(platform_fm(), platform_sections()), name="a/README.md")
    b = make_doc(tmp_path, render(use_case_fm(), use_case_sections()), name="b/README.md")
    assert repo.check_ids(_ctx(tmp_path, [a, b])) == []


def test_dangling_platform_ref_is_xr001(tmp_path):
    pb = make_doc(tmp_path, render(platform_fm(), platform_sections()), name="pb/README.md")
    text_uc = render(use_case_fm(platform_blueprints=["PB-04", "PB-99"]), use_case_sections())
    uc = make_doc(tmp_path, text_uc, name="uc/README.md")
    out = repo.check_refs(_ctx(tmp_path, [pb, uc]))
    assert [(f.code, f.severity, f.path) for f in out] == [("XR001", "error", "uc/README.md")]
    assert "'PB-99'" in out[0].message
    assert out[0].line == _key_line(text_uc, "platform_blueprints")


def test_xr001_skipped_without_discovery(tmp_path):
    pb = make_doc(tmp_path, render(platform_fm(), platform_sections()), name="pb/README.md")
    uc = make_doc(
        tmp_path,
        render(use_case_fm(platform_blueprints=["PB-04", "PB-99"]), use_case_sections()),
        name="uc/README.md",
    )
    ctx = _ctx(tmp_path, [pb, uc], discovery=False)
    assert repo.check_refs(ctx) == []
    # ID001 still runs on explicit-path runs.
    dup = make_doc(tmp_path, render(platform_fm(), platform_sections()), name="dup/README.md")
    ctx.docs.append(dup)
    assert [f.code for f in repo.check_ids(ctx)] == ["ID001"]


def test_non_blueprints_and_bad_front_matter_ignored(tmp_path):
    pb = make_doc(tmp_path, render(platform_fm(), platform_sections()), name="pb/README.md")
    doc = make_doc(
        tmp_path, render(platform_fm(), platform_sections()), name="doc.md", is_blueprint=False
    )
    bad = make_doc(tmp_path, "---\nid: [unclosed\n---\n# T\n", name="bad/README.md")
    listy = make_doc(tmp_path, "---\n- a\n---\n# T\n", name="listy/README.md")
    uc_doc = make_doc(
        tmp_path,
        render(use_case_fm(platform_blueprints=["PB-99"]), use_case_sections()),
        name="ucdoc.md",
        is_blueprint=False,
    )
    ctx = _ctx(tmp_path, [pb, doc, bad, listy, uc_doc])
    assert repo.check_ids(ctx) == []
    assert repo.check_refs(ctx) == []


def test_cli_discovery_run_is_clean():
    rc, findings = run_bplint(config=FIXTURES.parent.parent / "bplint/config.yaml")
    assert (rc, findings) == (0, [])


def test_cli_explicit_use_case_fixture_has_no_xr001():
    # The fixture references PB-99, which is not in the run; explicit paths skip XR001.
    rc, findings = run_bplint(FIXTURES / "valid/use-case/README.md")
    assert (rc, findings) == (0, [])


# ---- IDEA002 -------------------------------------------------------------

IDEA = {"why": "Kept as an idea until an operator trial shows the gate works", "promote": ["A public trial"]}


def _host(tmp_path, name="catalog/security/host/README.md", **fm):
    base = dict(id="UC-SEC-01", also_covers=["Fictional widget triage"])
    base.update(fm)
    return make_doc(tmp_path, render(use_case_fm(**base), use_case_sections()), name=name)


def _idea(tmp_path, merged_into="UC-SEC-01", uid="UC-DEMO-02", name="catalog/ideas/widget/README.md"):
    idea = dict(IDEA, merged_into=merged_into)
    return make_doc(tmp_path, render(use_case_fm(id=uid, idea=idea), use_case_sections()), name=name)


def test_idea_merged_into_valid_host_is_clean(tmp_path):
    out = repo.check_idea_merges(_ctx(tmp_path, [_host(tmp_path), _idea(tmp_path)]))
    assert out == []


def test_idea_merged_into_missing_host_is_idea002(tmp_path):
    out = repo.check_idea_merges(_ctx(tmp_path, [_host(tmp_path), _idea(tmp_path, merged_into="UC-SEC-09")]))
    assert [(f.code, f.path) for f in out] == [("IDEA002", "catalog/ideas/widget/README.md")]
    assert "'UC-SEC-09'" in out[0].message and "no matching use case" in out[0].message


def test_idea_merged_into_another_idea_is_idea002(tmp_path):
    host = _host(tmp_path, name="catalog/ideas/host/README.md", idea=IDEA)
    out = repo.check_idea_merges(_ctx(tmp_path, [host, _idea(tmp_path)]))
    assert [f.code for f in out] == ["IDEA002"] and "itself an idea" in out[0].message


def test_idea_merged_into_host_without_also_covers_is_idea002(tmp_path):
    for covers in (None, []):
        host = _host(tmp_path, also_covers=covers)
        out = repo.check_idea_merges(_ctx(tmp_path, [host, _idea(tmp_path)]))
        assert [f.code for f in out] == ["IDEA002"] and "also_covers" in out[0].message


def test_idea_merged_into_host_not_listing_it_is_idea002(tmp_path):
    host = _host(tmp_path, also_covers=["Some other merged scope"])
    out = repo.check_idea_merges(_ctx(tmp_path, [host, _idea(tmp_path)]))
    assert [f.code for f in out] == ["IDEA002"]
    assert "does not list 'Fictional widget triage' in also_covers" in out[0].message


def test_idea_listed_among_several_also_covers_is_clean(tmp_path):
    host = _host(tmp_path, also_covers=["Some other merged scope", "Fictional widget triage"])
    assert repo.check_idea_merges(_ctx(tmp_path, [host, _idea(tmp_path)])) == []


def test_idea002_skipped_without_discovery(tmp_path):
    ctx = _ctx(tmp_path, [_idea(tmp_path, merged_into="UC-SEC-09")], discovery=False)
    assert repo.check_idea_merges(ctx) == []
