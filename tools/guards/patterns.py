"""Single source of the public-repository guard patterns.

The CI backstop (tools/tests/test_public_tree.py), the local git hooks, and the
local release scanner all import this module, so their rules cannot drift.

What lives here:

- FORBIDDEN_PATH_RE: internal paths that must never be tracked. Matched at the
  start of the path or after any "/", case-insensitively, so nested and
  case-variant copies count.
- MENTIONS_RE: text that points at the internal planning folder, the planning
  repository, or the agent instructions file.
- PLANNING_ID_RE: planning ids (decisions, requirements, review findings,
  threats, roadmap criteria, plan numbers, planning artifact names).
- COMMIT_SCOPE_RE: conventional-commit subjects whose scope is a phase or plan
  number.

What does not live here: private terms. This repository never stores them, not
even as string fragments. They are read at run time from a local file named by
the GUARDS_EXTRA_TERMS environment variable or the `guards.extraTerms` git
config key. Without that file, term checks are skipped and every other check
still runs.

Extra-terms file format, one entry per line:

- blank lines and lines starting with "#" are ignored;
- "re:<regex>" adds a case-insensitive regular expression, for example
  "re:zz-?example[ -]?9";
- "allow:<substring>" adds an allowed substring, removed case-insensitively
  from a line before terms are matched, for example "allow:zzexample.org/ok";
- any other line is a plain substring, matched case-insensitively.

A term hit is reported as "private term #<n>" (1-based, plain terms first, then
regexes, each in file order), never as the term text, so no log can echo it.
term_number() is the shared helper for file paths and ref names: it returns
that number (or None) so callers can print a masked label instead of the name.

Internal names below are built from string fragments so this file passes the
content checks it defines.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Iterable, NamedTuple, Optional, Union

PLAN_DIR = "." + "plan" + "ning"
CONTEXT_DIR = "con" + "text/"
AGENT_FILE = "CLAU" + "DE.md"

FORBIDDEN_PATH_PATTERNS = [
    re.escape(PLAN_DIR + "/"),
    re.escape(CONTEXT_DIR),
    re.escape(AGENT_FILE) + "$",
    re.escape("." + "gitignore") + "$",
    # Case-sensitive: an ordinary lowercase notes.md page is legitimate content.
    "(?-i:" + re.escape("NOTES" + ".md") + ")$",
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
FORBIDDEN_PATH_RE = re.compile(
    r"(?:^|/)(?:" + "|".join(FORBIDDEN_PATH_PATTERNS) + ")", re.IGNORECASE
)

MENTIONS_RE = re.compile(
    "|".join(
        [
            re.escape(PLAN_DIR) + r"\b",
            re.escape("plan" + "ning" + ".git"),
            re.escape(AGENT_FILE),
        ]
    ),
    re.IGNORECASE,
)

_ARTIFACTS = ["PL" + "AN", "SUM" + "MARY", "CON" + "TEXT", "RE" + "SEARCH", "VERIFI" + "CATION", "RE" + "VIEW"]
PLANNING_ID_PATTERNS = [
    r"\b" + "D" + r"-\d{2}\b",
    r"\b(?:" + "|".join(["FN" + "D", "AR" + "CH", "U" + "C", "PR" + "OP", "IM" + "PL", "SI" + "TE", "PU" + "B", "W" + "R", "C" + "R"]) + r")-\d{2}\b",
    r"\b" + "T" + r"-\d{2}(?:\.\d+)?-[A-Z0-9]",
    r"\b" + "S" + r"C\d\b",
    r"\b" + "ROAD" + "MAP" + r"\b",
    "REV" + r"IEW\.md",
    r"\b" + "pl" + r"an \d{2}\b",
    r"\b\d{2}\.\d" + r"-\d{2}\b",
    r"\(\d{2}(?:\.\d+)?" + r"-\d{2}\)",
    r"\b\d{2}(?:\.\d+)?" + r"-\d{2}-(?:" + "|".join(_ARTIFACTS) + r")\b",
]
# Case-sensitive on purpose: lowercase words such as "roadmap" are ordinary prose.
PLANNING_ID_RE = re.compile("|".join(PLANNING_ID_PATTERNS))

COMMIT_SCOPE_RE = re.compile(
    r"^[a-z]+\(\d{1,2}(?:\.\d+)?" + r"(?:-\d{2})?\)!?:", re.IGNORECASE | re.MULTILINE
)

BINARY_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2"})

# Files that cannot avoid fragment-built internal names in a way the content
# checks would still flag. Keep this list minimal.
SELF_EXCLUDED = frozenset({"tools/tests/test_public_tree.py"})

# Lines for .git/info/exclude written by the hook installer.
EXCLUDE_LINES = (
    "/" + PLAN_DIR + "/",
    "/" + CONTEXT_DIR,
    "/" + AGENT_FILE,
    "/" + "." + "claude/",
    "NOTES" + ".md",
    "docs/" + "blog-*",
)


class ExtraTerms(NamedTuple):
    """Private terms loaded at run time; never stored in this repository."""

    terms: tuple = ()
    regexes: tuple = ()
    allow: tuple = ()

    def __bool__(self) -> bool:
        return bool(self.terms or self.regexes or self.allow)


def compile_extra_terms(lines: Iterable[str]) -> ExtraTerms:
    """Parse extra-terms lines (format in the module docstring)."""
    terms: list[str] = []
    regexes: list[re.Pattern] = []
    allow: list[str] = []
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("re:"):
            try:
                regexes.append(re.compile(line[3:], re.IGNORECASE))
            except re.error:
                raise ValueError(f"invalid regex on line {lineno} of the extra-terms file") from None
        elif line.startswith("allow:"):
            if line[6:]:
                allow.append(line[6:])
        else:
            terms.append(line)
    return ExtraTerms(tuple(terms), tuple(regexes), tuple(allow))


def load_extra_terms(path: Union[str, os.PathLike]) -> ExtraTerms:
    """Read an extra-terms file; a missing file raises FileNotFoundError."""
    text = Path(path).read_text(encoding="utf-8")
    return compile_extra_terms(text.splitlines())


def resolve_extra_terms_path(cwd: Union[str, os.PathLike]) -> Optional[str]:
    """GUARDS_EXTRA_TERMS if set, else `git config --get guards.extraTerms`, else None."""
    env = os.environ.get("GUARDS_EXTRA_TERMS", "").strip()
    if env:
        return env
    try:
        proc = subprocess.run(
            ["git", "config", "--get", "guards.extraTerms"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = proc.stdout.strip()
    if proc.returncode != 0 or not value:
        return None
    return value


_JOINER_RE = re.compile(r"""(["'])\s*\+\s*\1""")


def join_fragments(line: str) -> str:
    """Remove string-concatenation joiners so fragment-built text becomes contiguous."""
    return _JOINER_RE.sub("", line)


def forbidden_path(path: str) -> bool:
    return bool(FORBIDDEN_PATH_RE.search(path))


def _strip_allowed(line: str, allow: tuple) -> str:
    for item in allow:
        line = re.sub(re.escape(item), "", line, flags=re.IGNORECASE)
    return line


def _term_hit(line: str, extra: ExtraTerms) -> Optional[int]:
    lower = line.lower()
    for i, term in enumerate(extra.terms, 1):
        if term.lower() in lower:
            return i
    for j, rx in enumerate(extra.regexes, len(extra.terms) + 1):
        if rx.search(line):
            return j
    return None


def term_number(text: str, extra: Optional[ExtraTerms]) -> Optional[int]:
    """Return the 1-based number of the first private term in text, else None.

    For file paths and ref names: no fragment joining, since they are not code.
    Callers print "private term #<n>" in a masked label, never the text.
    """
    if not extra:
        return None
    for line in text.splitlines():
        n = _term_hit(_strip_allowed(line, extra.allow), extra)
        if n is not None:
            return n
    return None


def scan_text(text: str, extra: Optional[ExtraTerms] = None, *, joined: bool = True) -> list:
    """Return (lineno, kind, match) hits; kind is "term", "mention", or "planning-id".

    Term hits report "private term #<n>", never the term text.
    """
    hits: list = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if extra:
            candidates = [_strip_allowed(line, extra.allow)]
            if joined:
                candidates.append(_strip_allowed(join_fragments(line), extra.allow))
            for candidate in candidates:
                n = _term_hit(candidate, extra)
                if n is not None:
                    hits.append((lineno, "term", f"private term #{n}"))
                    break
        m = MENTIONS_RE.search(line)
        if m:
            hits.append((lineno, "mention", m.group(0)))
        m = PLANNING_ID_RE.search(line)
        if m:
            hits.append((lineno, "planning-id", m.group(0)))
    return hits


def scan_message(message: str, extra: Optional[ExtraTerms] = None) -> list:
    """scan_text hits plus "commit-scope" for phase or plan scopes."""
    hits = scan_text(message, extra, joined=True)
    for m in COMMIT_SCOPE_RE.finditer(message):
        lineno = message.count("\n", 0, m.start()) + 1
        hits.append((lineno, "commit-scope", m.group(0)))
    return hits
