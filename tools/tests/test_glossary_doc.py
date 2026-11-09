"""framework/glossary.md states the OTel naming rule and links resolve."""

from __future__ import annotations

import re

from markdown_it import MarkdownIt

from tools.bplint.slug import heading_slugs
from tools.tests.conftest import REPO_ROOT

GLOSSARY = (REPO_ROOT / "framework/glossary.md").read_text(encoding="utf-8")
DEFINITIONS = (REPO_ROOT / "framework/definitions.md").read_text(encoding="utf-8")
MD = MarkdownIt("commonmark").enable("table")


def _rows(text):
    """All table body rows in the doc, as lists of cell strings."""
    rows, row, in_body = [], None, False
    for tok in MD.parse(text):
        if tok.type == "tbody_open":
            in_body = True
        elif tok.type == "tbody_close":
            in_body = False
        elif in_body and tok.type == "tr_open":
            row = []
        elif in_body and tok.type == "tr_close":
            rows.append(row)
        elif in_body and tok.type == "inline":
            row.append(tok.content.strip())
    return rows


def _headings(text):
    tokens = MD.parse(text)
    return [tokens[i + 1].content for i, t in enumerate(tokens) if t.type == "heading_open"]


def _section_source(text, title):
    lines = text.splitlines()
    start = lines.index(f"## {title}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start + 1 : end])


def test_otel_row_means_model_family():
    row = next(r for r in _rows(GLOSSARY) if r[0] == "OTel")
    assert "model family" in row[1]


def test_opentelemetry_row_exists():
    assert any(r[0] == "OpenTelemetry" for r in _rows(GLOSSARY))


def test_naming_rule_section():
    text = _section_source(GLOSSARY, "The naming rule")
    assert "OpenTelemetry" in text
    bad = re.findall(r"`(OTel [^`]+|OTLP)`", text)
    assert len(bad) >= 4, bad


def test_definitions_anchors_resolve():
    slugs = heading_slugs(_headings(DEFINITIONS))
    anchors = re.findall(r"\(definitions\.md#([^)]+)\)", GLOSSARY)
    assert anchors, "glossary has no definitions.md anchors"
    missing = sorted({a for a in anchors if a not in slugs})
    assert missing == []


def test_glossary_local_anchors_resolve():
    slugs = heading_slugs(_headings(GLOSSARY))
    anchors = re.findall(r"\]\(#([^)]+)\)", GLOSSARY)
    assert sorted({a for a in anchors if a not in slugs}) == []


def test_replaceable_component_row_exists():
    row = next(r for r in _rows(GLOSSARY) if r[0] == "Replaceable component")
    assert "definitions.md#component-naming" in row[2]
