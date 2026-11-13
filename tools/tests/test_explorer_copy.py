"""Explorer UI copy: one front-matter file, word limits, and banned terms.

Every explorer UI string lives in explorer/src/content/copy.md, which Vale lints
through DOC_DIRS. Strings under a key named `buttons`, `headings`, or `notes`
(at any depth) carry word limits. No string may use a support or validation
label, a filler word the style guide bans, a planning id, or a phase number.
"""

from __future__ import annotations

import re

import pytest
import yaml

from tools.guards.patterns import PLANNING_ID_RE
from tools.tests.conftest import REPO_ROOT

COPY_PATH = REPO_ROOT / "explorer/src/content/copy.md"
EXPLORER_SRC = REPO_ROOT / "explorer/src"
LIMITS = {"buttons": 4, "headings": 8, "notes": 25}
PHASE_NUMBER = re.compile(r"(?i)\bphases? [0-9]")
# GA is matched case-sensitively so "gateway" or "ga" inside words never trip it.
BANNED_CASED = [re.compile(r"\bGA\b")]
BANNED = [
    "Technology Preview",
    "Developer Preview",
    "production-ready",
    "supported by Red Hat",
    "validated",
    "unverified",
    "proven",
    "seamless",
    "robust",
    "Coming soon",
    "Click here",
    "Send to team",
]


def _copy():
    text = COPY_PATH.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, "copy.md has no front matter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def _strings(node, path=()):
    """Yield (key path, string) for every string leaf."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, path + (str(key),))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _strings(value, path + (str(i),))
    elif isinstance(node, str):
        yield path, node


def _words(text):
    return len([w for w in text.split() if re.search(r"\w", w)])


def _banned_hits(text):
    hits = [p.pattern for p in BANNED_CASED if p.search(text)]
    hits += [term for term in BANNED if term.lower() in text.lower()]
    if PLANNING_ID_RE.search(text):
        hits.append("planning id")
    if PHASE_NUMBER.search(text):
        hits.append("phase number")
    return hits


def test_copy_loads():
    data = _copy()
    assert data["home"]["hero"]["headline"]
    assert data["site"]["skip_link"] == "Skip to content"


def test_word_limits():
    over = []
    for path, text in _strings(_copy()):
        limits = [LIMITS[k] for k in path if k in LIMITS]
        if limits and _words(text) > min(limits):
            over.append(f"{'.'.join(path)}: {_words(text)} words > {min(limits)}")
    assert over == []


@pytest.mark.parametrize(
    "text,limit_key",
    [("Open the recipe now please", "buttons"), (" ".join(["word"] * 9), "headings")],
)
def test_word_limit_check_bites(text, limit_key):
    assert _words(text) > LIMITS[limit_key]


def test_no_banned_terms():
    hits = []
    for path, text in _strings(_copy()):
        for hit in _banned_hits(text):
            hits.append(f"{'.'.join(path)}: {hit}")
    assert hits == []


@pytest.mark.parametrize(
    "sample", ["Now GA on the platform", "a seamless rollout", "Coming soon", "see Phase 5"]
)
def test_banned_check_bites(sample):
    assert _banned_hits(sample)


def test_no_prose_in_astro_files():
    # The hero and footer strings must come from copy.md, never be typed into a template.
    data = _copy()
    samples = [
        data["home"]["hero"]["headline"],
        data["home"]["hero"]["notes"]["lede"],
        data["footer"]["notes"]["otel"],
        data["site"]["skip_link"],
    ]
    for astro in EXPLORER_SRC.rglob("*.astro"):
        text = astro.read_text(encoding="utf-8")
        for sample in samples:
            assert sample not in text, f"{astro.relative_to(REPO_ROOT)} hard-codes: {sample}"


# Home sections the page renders; each lives under copy.home.
HOME_SECTIONS = ["hero", "how", "goals", "gallery", "architects", "note"]
COPY_REF = re.compile(r"(?<![/\w.])copy(?!\.md\b)((?:\.[A-Za-z_][\w]*|\[['\"][\w-]+['\"]\])+)")


def _ref_path(ref):
    return [p for p in re.split(r"\.|\[['\"]|['\"]\]", ref) if p]


def test_home_copy_sections():
    home = _copy()["home"]
    missing = [s for s in HOME_SECTIONS if s not in home]
    assert missing == []


def test_copy_keys_used():
    # Every copy.<path> referenced by an explorer template resolves in copy.md.
    data = _copy()
    refs = 0
    bad = []
    for astro in EXPLORER_SRC.rglob("*.astro"):
        for match in COPY_REF.finditer(astro.read_text(encoding="utf-8")):
            node = data
            for key in _ref_path(match.group(1)):
                if not isinstance(node, dict):
                    break  # a method or index on a string or list
                if key not in node:
                    bad.append(f"{astro.name}: copy{match.group(1)}")
                    break
                node = node[key]
            refs += 1
    assert refs, "no copy references found"
    assert bad == []


def test_no_home_prose_in_astro_files():
    # Any home string of three or more words typed into a template is a copy leak.
    samples = [text for _, text in _strings(_copy()["home"]) if _words(text) >= 3]
    for astro in EXPLORER_SRC.rglob("*.astro"):
        text = astro.read_text(encoding="utf-8")
        for sample in samples:
            assert sample not in text, f"{astro.relative_to(REPO_ROOT)} hard-codes: {sample}"
