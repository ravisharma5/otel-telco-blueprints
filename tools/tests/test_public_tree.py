"""Backstop: nothing internal is tracked in the public tree.

Four checks run over `git ls-files`:

- test_no_internal_paths_tracked: no planning, context, agent, personal, or
  register-era path is tracked.
- test_no_sensitive_terms: no tracked public file names internal documents,
  people, local paths, or product release numbers.
- test_no_internal_path_mentions: no tracked public file points at the
  planning folder or the agent instructions file.
- test_no_planning_ids: no tracked public file cites planning ids (decisions,
  requirements, review findings, threats, roadmap criteria, plan numbers);
  public text states the rule itself instead.

The path check is marked as a strict xfail before the release, because the
planning folder is still tracked in the working repository. The marker lives on
the two lines that end with the pre-release marker comment. The release export
deletes exactly those lines, so the check is enforced in the
public commit and in CI from then on. The xfail is deliberately not conditional
on repository state: a condition such as "is the planning folder tracked" would
switch the backstop off exactly when it matters.

Every pattern is built from string fragments so this file never matches itself.
The content scans also skip this file by path.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from tools.tests.conftest import REPO_ROOT

SELF = "tools/tests/test_public_tree.py"
PLANNING = "." + "planning"
AGENT_FILE = "CLAU" + "DE.md"
CONTEXT_DIR = "con" + "text/"

FORBIDDEN_PATHS = [
    re.escape(PLANNING + "/"),
    re.escape(CONTEXT_DIR),
    re.escape(AGENT_FILE) + "$",
    re.escape("." + "gitignore") + "$",
    re.escape("NOTES" + ".md") + "$",
    re.escape("docs/" + "blog-"),
    re.escape("." + "claude/"),
    re.escape("architecture/support" + "-status."),
    re.escape("schemas/support" + "-status.schema.json") + "$",
    re.escape("tools/render_support" + "_status.py") + "$",
    re.escape("tools/bplint/checks/" + "register.py") + "$",
    re.escape("tools/tests/test_" + "register.py") + "$",
    re.escape("tools/tests/test_" + "register_checks.py") + "$",
    re.escape("tools/tests/test_" + "render.py") + "$",
    re.escape("tools/tests/fixtures/" + "register.yaml") + "$",
    re.escape("tools/tests/fixtures/support" + "-status.md") + "$",
    re.escape("tools/tests/fixtures/broken/" + "stale-register/"),
    re.escape("tools/tests/fixtures/broken/" + "unknown-component/"),
    re.escape("tools/tests/fixtures/broken/" + "weakest-mismatch/"),
]
# Anchored at the start of the repo-relative path; nested copies also count.
FORBIDDEN_PATH_RE = re.compile(r"(?:^|/)(?:" + "|".join(FORBIDDEN_PATHS) + ")")

# Public model namespace on Hugging Face; stripped before the term scan.
PUBLIC_MODEL_NS = re.compile(re.escape("huggingface.co/" + "far" + "bod" + "tavakkoli/"), re.IGNORECASE)
SENSITIVE_TERMS = [
    "hybrid-" + "inferenc",
    "far" + "bod",
    "fat" + "ih",
    "ai-" + "grid",
    "research-" + "findings",
    "/Us" + "ers/",
    "rav" + "sharm",
    "RHOAI" + " 3.",
    "RHAII" + " 3.",
]
SENSITIVE_RE = re.compile("|".join(re.escape(t) for t in SENSITIVE_TERMS), re.IGNORECASE)

MENTIONS = [PLANNING + "/", PLANNING + "/**", AGENT_FILE]

# Planning references (decision, requirement, review, and threat ids, roadmap
# criteria, plan numbers) mean nothing to a public reader. Linter codes such as
# FM001 or CR001 and the E/M levels have no hyphen-digit form, so they never match.
# Platform blueprint ids are public schema ids and are not in this list.
PLANNING_ID_PATTERNS = [
    r"\b" + "D" + r"-\d{2}\b",
    r"\b(?:" + "|".join(["FN" + "D", "AR" + "CH", "U" + "C", "PR" + "OP", "IM" + "PL", "SI" + "TE", "PU" + "B", "W" + "R", "C" + "R"]) + r")-\d{2}\b",
    r"\b" + "T" + r"-\d{2}(?:\.\d+)?-[A-Z0-9]",
    r"\b" + "S" + r"C\d\b",
    r"\b" + "ROAD" + "MAP" + r"\b",
    "REV" + r"IEW\.md",
    r"\b" + "pl" + r"an \d{2}\b",
    r"\b\d{2}\.\d" + r"-\d{2}\b",
]
PLANNING_ID_RE = re.compile("|".join(PLANNING_ID_PATTERNS))



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
        path == SELF
        or path == AGENT_FILE
        or path.startswith(PLANNING + "/")
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
    hits = [p for p in _tracked() if FORBIDDEN_PATH_RE.search(p)]
    assert not hits, f"internal paths tracked: {hits[:20]}"


def test_no_sensitive_terms():
    hits = []
    for path, text in _public_texts():
        scrubbed = PUBLIC_MODEL_NS.sub("", text)
        for lineno, line in enumerate(scrubbed.splitlines(), 1):
            match = SENSITIVE_RE.search(line)
            if match:
                hits.append(f"{path}:{lineno}: {match.group(0)}")
    assert not hits, "sensitive terms in public files:\n" + "\n".join(hits)


def test_no_internal_path_mentions():
    hits = []
    for path, text in _public_texts():
        for lineno, line in enumerate(text.splitlines(), 1):
            for needle in MENTIONS:
                if needle in line:
                    hits.append(f"{path}:{lineno}: {needle}")
                    break
    assert not hits, "internal path mentions in public files:\n" + "\n".join(hits)


def test_no_planning_ids():
    hits = []
    for path, text in _public_texts():
        for lineno, line in enumerate(text.splitlines(), 1):
            match = PLANNING_ID_RE.search(line)
            if match:
                hits.append(f"{path}:{lineno}: {match.group(0)}")
    assert not hits, "planning ids in public files:\n" + "\n".join(hits)
