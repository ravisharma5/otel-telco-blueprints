"""Backstop: nothing internal is tracked in the public tree.

Four checks run over `git ls-files`:

- test_no_internal_paths_tracked: no planning, context, agent, personal, or
  register-era path is tracked, at any depth and in any letter case.
- test_no_sensitive_terms: no tracked public file contains a private term.
- test_no_internal_path_mentions: no tracked public file points at the
  planning folder, the planning repository, or the agent instructions file.
- test_no_planning_ids: no tracked public file cites planning ids; public text
  states the rule itself instead.

The generic patterns come from tools/guards/patterns.py, which the git hooks
share, so the rules cannot drift. Private terms are never stored in this
repository. They are read at run time from a local file when GUARDS_EXTRA_TERMS
or the `guards.extraTerms` git config key names one; otherwise the term check
is skipped and the other three checks still run.

Internal names are built from string fragments; the content scans also skip
this file by path.
"""

from __future__ import annotations

import subprocess

import pytest

from tools.guards.patterns import (
    compile_extra_terms,
    FORBIDDEN_PATH_RE,
    MENTIONS_RE,
    PLANNING_ID_RE,
    SELF_EXCLUDED,
    forbidden_path,
    load_extra_terms,
    resolve_extra_terms_path,
    scan_text,
)
from tools.tests.conftest import REPO_ROOT

PLAN_DIR = "." + "plan" + "ning"
AGENT_FILE = "CLAU" + "DE.md"
CONTEXT_DIR = "con" + "text/"

__all__ = ["FORBIDDEN_PATH_RE", "MENTIONS_RE", "PLANNING_ID_RE"]


def _tracked():
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


def _excluded(path):
    return (
        path in SELF_EXCLUDED
        or path == AGENT_FILE
        or path.startswith(PLAN_DIR + "/")
        or path.startswith(CONTEXT_DIR)
    )


def _public_texts():
    for path in _tracked():
        if _excluded(path):
            continue
        full = REPO_ROOT / path
        if not full.is_file():
            continue
        yield path, full.read_bytes().decode("utf-8", errors="ignore")


def test_no_internal_paths_tracked():
    hits = [p for p in _tracked() if forbidden_path(p)]
    assert not hits, f"internal paths tracked: {hits[:20]}"


def test_no_sensitive_terms():
    terms_path = resolve_extra_terms_path(REPO_ROOT)
    if terms_path is None:
        pytest.skip("no local private terms configured (GUARDS_EXTRA_TERMS / guards.extraTerms unset)")
    extra = load_extra_terms(terms_path)  # a missing file fails, it does not skip
    hits = []
    for path, text in _public_texts():
        for lineno, kind, match in scan_text(text, extra):
            if kind == "term":
                hits.append(f"{path}:{lineno}: {match}")
    assert not hits, "private terms in public files:\n" + "\n".join(hits)


def test_no_internal_path_mentions():
    hits = []
    for path, text in _public_texts():
        for lineno, line in enumerate(text.splitlines(), 1):
            match = MENTIONS_RE.search(line)
            if match:
                hits.append(f"{path}:{lineno}: {match.group(0)}")
    assert not hits, "internal path mentions in public files:\n" + "\n".join(hits)


def test_no_planning_ids():
    hits = []
    for path, text in _public_texts():
        for lineno, line in enumerate(text.splitlines(), 1):
            match = PLANNING_ID_RE.search(line)
            if match:
                hits.append(f"{path}:{lineno}: {match.group(0)}")
    assert not hits, "planning ids in public files:\n" + "\n".join(hits)


def test_term_scan_covers_paths():
    term = "zz" + "pathterm"
    extra = compile_extra_terms([term])
    entries = [
        ("architecture/" + term + "-notes.md", "Clean text.\n"),
        ("docs/clean.md", "Clean text.\n"),
    ]
    hits = _term_hits(entries, extra)
    assert hits == ["<path with private term #1>"]
    assert all(term not in h.lower() for h in hits)
    assert _term_hits([("docs/clean.md", "Clean text.\n")], extra) == []
