"""Reference pages: per-page content checks and the recipe wording rule.

Reference pages are recipes. They say how to build a design, not how far it
has been tested, so they carry no validation-status wording and no readiness
levels. Vale scopes rules by path and the blueprint templates legitimately use
that wording, so the rule lives here.

The helpers below are shared: per-page tests for each reference page go in
this module and call them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from markdown_it import MarkdownIt

from tools.bplint.loader import load_yaml, split_front_matter
from tools.tests.conftest import REPO_ROOT

TEMPLATE = REPO_ROOT / "templates/reference-page.md"
CONFIG = REPO_ROOT / "tools/bplint/config.yaml"

# Words are matched case-insensitively; readiness levels (E0-E4, M0-M3) are
# matched case-sensitively so names like MI300X or "e2e" never trip the rule.
WORDING = re.compile(
    r"\b(?:(?i:unverified|unvalidated|untested"
    r"|not\s+(?:yet\s+)?(?:validated|verified|tested|run|measured))"
    r"|E[0-4]\b(?!\d)|M[0-3]\b)"
)
FENCE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.M | re.S)
EXEMPT_CELL = re.compile(r"^E[1-7]$")
MERMAID_KEYWORDS = ("flowchart", "graph", "sequenceDiagram")


# ---------- helpers ----------


def _md():
    return MarkdownIt("commonmark").enable("table")


def reference_pages() -> list[Path]:
    """Pages matched by reference_globs whose front matter type is reference."""
    out = []
    for pattern in load_yaml(CONFIG).get("reference_globs") or []:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_file() and (front_matter(path) or {}).get("type") == "reference":
                out.append(path)
    return out


def front_matter(path: Path) -> dict | None:
    fm, _, _ = split_front_matter(Path(path).read_text(encoding="utf-8"))
    return fm


def body(path: Path) -> str:
    _, text, _ = split_front_matter(Path(path).read_text(encoding="utf-8"))
    return text


def sections(text):
    """Map h2 title -> list of tokens in that section."""
    tokens = _md().parse(text)
    out, current = {}, None
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.tag == "h2":
            current = tokens[i + 1].content
            out[current] = []
        elif current is not None:
            out[current].append(tok)
    return out


def tables(tokens):
    """Tables in a token list, each a list of rows (header row first)."""
    tables, rows, row, in_table = [], [], None, False
    for tok in tokens:
        if tok.type == "table_open":
            in_table, rows = True, []
        elif tok.type == "table_close":
            in_table = False
            tables.append(rows)
        elif in_table and tok.type == "tr_open":
            row = []
        elif in_table and tok.type == "tr_close":
            rows.append(row)
        elif in_table and tok.type == "inline":
            row.append(tok.content.strip())
    return tables


def _fences(text: str, info: str) -> list[str]:
    return [
        t.content
        for t in _md().parse(text)
        if t.type == "fence" and t.info.strip().split(" ")[0] == info
    ]


def mermaid_fences(text: str) -> list[str]:
    return _fences(text, "mermaid")


def json_fences(text: str) -> list:
    return [json.loads(content) for content in _fences(text, "json")]


def flows(text: str) -> dict[str, str]:
    """Map lowercased "### Flow: <name>" names to the first mermaid fence under them."""
    tokens = _md().parse(text)
    out: dict[str, str] = {}
    for i, tok in enumerate(tokens):
        if not (tok.type == "heading_open" and tok.tag == "h3"):
            continue
        title = tokens[i + 1].content.strip()
        if not title.startswith("Flow: "):
            continue
        name = title[len("Flow: ") :].strip().lower()
        for nxt in tokens[i + 3 :]:
            if nxt.type == "heading_open":
                break
            if nxt.type == "fence" and nxt.info.strip().split(" ")[0] == "mermaid":
                out[name] = nxt.content
                break
    return out


def _drop_exempt_cells(line: str) -> str:
    if not line.lstrip().startswith("|"):
        return line
    cells = line.split("|")
    return "|".join("" if EXEMPT_CELL.match(c.strip()) else c for c in cells)


def wording_hits(text: str) -> list[str]:
    """Validation-status wording and readiness levels outside code fences.

    Table cells that hold only an extension-row id (E1-E7) are allowed.
    """
    text = FENCE.sub("", text)
    text = "\n".join(_drop_exempt_cells(line) for line in text.splitlines())
    return [m.group(0) for m in WORDING.finditer(text)]


def _scanned_files() -> list[Path]:
    return [*reference_pages(), TEMPLATE]


# ---------- the wording rule ----------


@pytest.mark.parametrize(
    "sample",
    [
        "This step is unverified.",
        "The routing is not yet validated.",
        "Not tested on this hardware.",
        "The path is untested.",
        "This sits at readiness E2.",
        "The model level M1 applies.",
        "The figure was not measured.",
    ],
)
def test_wording_regex_catches(sample):
    assert wording_hits(sample), sample


@pytest.mark.parametrize(
    "sample",
    [
        "This page is a draft pending review by the agent-school maintainers.",
        "Run it on an MI300X node.",
        "| E7 | Extension row |",
        "| E2 | Extension row |",
        "Serve each LoRA adapter on its base.",
        "PB-02 builds on this page.",
        "```text\nnot yet validated\n```",
        "Use e2e tests and m3 storage.",
    ],
)
def test_wording_regex_allows(sample):
    assert wording_hits(sample) == [], sample


def test_wording_exempt_cell_only_when_whole_cell():
    assert wording_hits("| Row E2 here | x |")
    assert wording_hits("The E2 row is optional.")


@pytest.mark.parametrize("path", _scanned_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_wording_reference_pages(path):
    assert wording_hits(path.read_text(encoding="utf-8")) == []


# ---------- shared structure ----------


@pytest.mark.parametrize("path", _scanned_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_mermaid_fences_start_with_known_keyword(path):
    for fence in mermaid_fences(body(path)):
        first = next((ln.strip() for ln in fence.splitlines() if ln.strip()), "")
        assert first.split(" ")[0] in MERMAID_KEYWORDS, (path, first)


def test_flow_helper():
    sample = (
        "## The design\n\n"
        "### Flow: grounded answer\n\n"
        "Some text.\n\n"
        "```mermaid\nflowchart LR\n  A --> B\n```\n\n"
        "### Flow: empty\n\n"
        "### Other\n\n"
        "```mermaid\ngraph TD\n  C --> D\n```\n"
    )
    assert flows(sample) == {"grounded answer": "flowchart LR\n  A --> B\n"}


def test_json_fence_helper():
    sample = '```json\n{"label": "LOOK"}\n```\n\n```text\n{}\n```\n'
    assert json_fences(sample) == [{"label": "LOOK"}]


def test_reference_pages_helper_reads_config():
    assert TEMPLATE not in reference_pages()
    for path in reference_pages():
        assert front_matter(path)["type"] == "reference"
