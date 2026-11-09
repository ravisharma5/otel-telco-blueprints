"""Regression cases for the shared guard patterns in tools/guards/patterns.py.

Internal path names and planning-id shapes are built from string fragments, so
this file passes the public content checks it exercises. Private terms are
never written here: the term cases use synthetic placeholders that start with
"zz".
"""

from __future__ import annotations

import subprocess

import pytest

from tools.guards import patterns
from tools.tests import test_public_tree

PLAN_DIR = "." + "plan" + "ning"
AGENT = "CLAU" + "DE.md"


# Forbidden paths: nested, case-variant, and register-era copies all count.
@pytest.mark.parametrize(
    "path",
    [
        "framework/" + AGENT,
        "Clau" + "de.md",
        ".Plan" + "ning/STATE.md",
        "tools/" + PLAN_DIR + "/n.md",
        "catalog/x/" + "." + "claude/settings.local.json",
        "docs/" + "." + "gitignore",
        "architecture/support" + "-status.md",
        "tools/tests/test_" + "register_checks.py",
        "tools/tests/fixtures/broken/stale-" + "register/a.md",
    ],
)
def test_forbidden_path_hits(path):
    assert patterns.forbidden_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "framework/definitions.md",
        "site-src/index.md",
        "tools/guards/patterns.py",
        "plan" + "ning/notes.md",
        "templates/use-case-blueprint.md",
    ],
)
def test_forbidden_path_misses(path):
    assert not patterns.forbidden_path(path)


def _kinds(text, extra=None, **kw):
    return [kind for _, kind, _ in patterns.scan_text(text, extra, **kw)]


@pytest.mark.parametrize(
    "text",
    [
        "see `" + PLAN_DIR + "` for details",
        "clone otel-" + "plan" + "ning.git first",
        "read clau" + "de.md first",
    ],
)
def test_mention_hits(text):
    assert "mention" in _kinds(text)


def test_mention_miss_on_plain_word():
    assert "mention" not in _kinds("I am planning the platform")


@pytest.mark.parametrize(
    "text",
    [
        "fixed in (02" + "-01)",
        "fixed in (01.1" + "-09)",
        "see 02-01" + "-PLAN.md",
    ],
)
def test_planning_id_hits(text):
    assert "planning-id" in _kinds(text)


@pytest.mark.parametrize(
    "text",
    ["2026-11-09", "PB-04", "E0-E4", "M0-M3", "the 10 questions (10)"],
)
def test_planning_id_misses(text):
    assert _kinds(text) == []


@pytest.mark.parametrize(
    "message",
    ["feat(02" + "-01): x", "docs(01.1" + "): x", "docs(02" + "): x"],
)
def test_commit_scope_hits(message):
    kinds = [k for _, k, _ in patterns.scan_message(message)]
    assert "commit-scope" in kinds


@pytest.mark.parametrize(
    "message",
    ["docs: link the docs site", "feat(guards): add hooks", "Initial public release"],
)
def test_commit_scope_misses(message):
    assert patterns.scan_message(message) == []


# Extra terms: synthetic placeholders only.
TERM = "zz" + "secretterm"
ALLOWED = "zz" + "secretterm.example/ok"
LINES = ["# c", "", TERM, "re:zz-?rel[ -]?9(\\.[0-9])?\\b", "allow:" + ALLOWED]


@pytest.fixture
def extra():
    return patterns.compile_extra_terms(LINES)


def test_compile_extra_terms_counts(extra):
    assert len(extra.terms) == 1
    assert len(extra.regexes) == 1
    assert len(extra.allow) == 1
    assert extra


def test_term_hit_is_case_insensitive_and_never_echoed(extra):
    hits = patterns.scan_text(TERM.upper() + " here", extra)
    assert [(n, k, m) for n, k, m in hits if k == "term"] == [(1, "term", "private term #1")]
    for hit in hits:
        for field in hit:
            assert TERM not in str(field).lower()


@pytest.mark.parametrize("text", ["zz-rel 9.1", "zzrel9"])
def test_regex_term_hits(extra, text):
    assert "term" in _kinds(text, extra)


def test_allow_substring_is_stripped(extra):
    assert "term" not in _kinds("see " + ALLOWED + "/page", extra)


def test_fragment_form_is_joined(extra):
    joiner = '"' + " + " + '"'
    line = 'x = "zz' + joiner + "secret" + joiner + 'term"'
    assert "term" in _kinds(line, extra, joined=True)
    assert "term" not in _kinds(line, extra, joined=False)


@pytest.mark.parametrize("value", [None, patterns.ExtraTerms((), (), ())])
def test_no_extra_terms_skips_term_checks_only(value):
    text = TERM + " and `" + PLAN_DIR + "` and (02" + "-01)"
    kinds = _kinds(text, value)
    assert "term" not in kinds
    assert "mention" in kinds
    assert "planning-id" in kinds


def test_load_extra_terms_matches_compile(tmp_path, extra):
    f = tmp_path / "terms.txt"
    f.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    loaded = patterns.load_extra_terms(f)
    assert loaded.terms == extra.terms
    assert loaded.allow == extra.allow
    assert [r.pattern for r in loaded.regexes] == [r.pattern for r in extra.regexes]


def test_load_extra_terms_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        patterns.load_extra_terms(tmp_path / "absent.txt")


def test_invalid_regex_names_line_not_text():
    bad = "zz" + "badpat("
    with pytest.raises(ValueError) as exc:
        patterns.compile_extra_terms(["# c", "re:" + bad])
    assert "2" in str(exc.value)
    assert bad not in str(exc.value)


# Shared helper for paths and ref names: number only, never the text.
def test_term_number_plain_term_in_path(extra):
    assert patterns.term_number("architecture/" + TERM + "-notes.md", extra) == 1


def test_term_number_regex_term_in_path(extra):
    assert patterns.term_number("docs/zz-rel9-notes.md", extra) == 2


def test_term_number_clean_path(extra):
    assert patterns.term_number("docs/clean-notes.md", extra) is None


@pytest.mark.parametrize("value", [None, patterns.ExtraTerms((), (), ())])
def test_term_number_without_terms(value):
    assert patterns.term_number("architecture/" + TERM + "-notes.md", value) is None


def test_term_number_allowlisted_path(extra):
    assert patterns.term_number("docs/" + ALLOWED + "/a.md", extra) is None


@pytest.fixture
def clean_git_env(tmp_path, monkeypatch):
    empty = tmp_path / "empty-gitconfig"
    empty.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.delenv("GUARDS_EXTRA_TERMS", raising=False)
    return tmp_path


def test_resolve_env_wins(clean_git_env, monkeypatch):
    monkeypatch.setenv("GUARDS_EXTRA_TERMS", "/from/env")
    assert patterns.resolve_extra_terms_path(clean_git_env) == "/from/env"


def test_resolve_git_config(clean_git_env):
    repo = clean_git_env / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "guards.extraTerms", "/x"], cwd=repo, check=True)
    assert patterns.resolve_extra_terms_path(repo) == "/x"


def test_resolve_none(clean_git_env):
    repo = clean_git_env / "bare-dir"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    assert patterns.resolve_extra_terms_path(repo) is None


@pytest.mark.parametrize(
    "module, name",
    [
        (patterns, "SENSITIVE_TERMS"),
        (patterns, "SENSITIVE_RE"),
        (patterns, "PUBLIC_MODEL_NS"),
        (patterns, "RELEASE_RE"),
        (test_public_tree, "SENSITIVE_TERMS"),
        (test_public_tree, "PUBLIC_MODEL_NS"),
    ],
)
def test_no_term_lists_in_public_code(module, name):
    assert not hasattr(module, name)


@pytest.mark.parametrize("name", ["FORBIDDEN_PATH_RE", "MENTIONS_RE", "PLANNING_ID_RE"])
def test_public_tree_uses_shared_patterns(name):
    assert getattr(test_public_tree, name) is getattr(patterns, name)
