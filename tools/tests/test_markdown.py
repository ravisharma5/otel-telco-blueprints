"""Tests for markdown parsing (sections, tables, lists, links) and the slugger."""

from tools.bplint.markdown import parse_doc
from tools.bplint.slug import github_slug, heading_slugs

DOC = """---
id: UC-DEMO-01
---
Intro paragraph before any H2.

## First

| Label | Value |
|---|---|
| One | [link](a.md) |
| Two | `p\\|q` |
| Three | x |

1. step one
2. step two
3. step three
4. step four

## Second

- bullet one
- bullet two
  - nested bullet

A paragraph line one
and line two with [a link](https://example.com).

![diagram](diagrams/x.svg)

### Sub heading

More words here.
"""


def parse():
    return parse_doc("demo.md", DOC)


def test_front_matter_and_offset():
    doc = parse()
    assert doc.front_matter == {"id": "UC-DEMO-01"}
    assert doc.body_offset == 3


def test_sections_and_lines():
    doc = parse()
    titles = [s.title for s in doc.sections]
    assert titles == ["", "First", "Second"]
    first, second = doc.sections[1], doc.sections[2]
    assert first.level == 2 and first.line == 6
    assert second.line == 19


def test_table_rows_cells_and_lines():
    first = parse().sections[1]
    assert len(first.tables) == 1
    table = first.tables[0]
    assert table.header == ["Label", "Value"]
    assert len(table.rows) == 3
    assert [r.line for r in table.rows] == [10, 11, 12]
    assert table.rows[0].hrefs[1] == ["a.md"]
    assert table.rows[0].hrefs[0] == []


def test_escaped_pipe_in_code_span_does_not_split_cell():
    row = parse().sections[1].tables[0].rows[1]
    assert len(row.cells) == 2
    assert "p" in row.cells[1] and "q" in row.cells[1]


def test_list_counts():
    first, second = parse().sections[1], parse().sections[2]
    assert first.ordered_items == 4
    assert first.bullet_items == 0
    assert second.bullet_items == 2  # nested bullet excluded


def test_prose_lines_words_images_links():
    second = parse().sections[2]
    # two paragraph lines + "More words here." (H3 belongs to parent); image-only paragraph excluded
    assert second.prose_lines == 3
    assert second.images == [("diagrams/x.svg", 28)]
    assert ("https://example.com", 26) in second.links
    assert second.prose_words > 10


def test_table_words_not_counted_as_prose():
    first = parse().sections[1]
    # only the four list items (2 words each)
    assert first.prose_words == 8


def test_body_text_is_raw_section_source():
    second = parse().sections[2]
    assert second.body_text.startswith("- bullet one")
    assert "### Sub heading" in second.body_text


def test_slug_examples():
    assert github_slug("Decisions you must make") == "decisions-you-must-make"
    assert github_slug("Model readiness (M0-M3)") == "model-readiness-m0-m3"
    assert github_slug("Used by and next steps") == "used-by-and-next-steps"
    assert github_slug("Risks and limitations") == "risks-and-limitations"


def test_slug_duplicates_get_suffixes():
    assert heading_slugs(["Notes", "Notes", "Notes"]) == {"notes", "notes-1", "notes-2"}
