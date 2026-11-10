"""Markdown token walk: sections, tables, lists, prose, images, links.

Uses markdown-it-py tokens only. Never regex-parse tables or headings
(RESEARCH.md anti-patterns). All line numbers are 1-based file lines:
body line index + body_offset + 1.

Note: per the GFM table spec, an unescaped `|` splits a cell even inside a
code span. Write `\\|` to keep a pipe inside a cell.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from markdown_it import MarkdownIt

from .loader import FrontMatterError, split_front_matter

_MD = MarkdownIt("commonmark").enable("table")


@dataclass
class Row:
    line: int
    cells: list[str] = field(default_factory=list)
    hrefs: list[list[str]] = field(default_factory=list)


@dataclass
class Table:
    line: int
    header: list[str] = field(default_factory=list)
    rows: list[Row] = field(default_factory=list)


@dataclass
class Section:
    title: str
    level: int
    line: int
    tables: list[Table] = field(default_factory=list)
    ordered_items: int = 0
    bullet_items: int = 0
    prose_lines: int = 0
    prose_words: int = 0
    images: list[tuple[str, int]] = field(default_factory=list)
    links: list[tuple[str, int]] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)  # all heading titles (H2 and below)
    body_text: str = ""
    _body_start: int = 0  # body line index where the section content starts


@dataclass
class Doc:
    path: str
    front_matter: dict | None
    body_offset: int
    sections: list[Section]
    abs_path: Path | None = None
    is_blueprint: bool = True
    fm_lines: list[str] = field(default_factory=list)  # raw front matter lines
    fm_error: tuple[int, str] | None = None  # (line, message) for FM001
    flags: set[str] = field(default_factory=set)
    # Front matter types the page's glob group accepts; None accepts any known type.
    allowed_types: tuple[str, ...] | None = None

    def section(self, title: str) -> Section | None:
        for s in self.sections:
            if s.title == title:
                return s
        return None

    @property
    def h2_titles(self) -> list[str]:
        return [s.title for s in self.sections if s.level == 2]


def _inline_text(token) -> str:
    parts = []
    for c in token.children or []:
        if c.type == "text":
            parts.append(c.content)
        elif c.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts)


def _inline_is_image_only(token) -> bool:
    kids = [c for c in token.children or [] if not (c.type == "text" and not c.content.strip())]
    return bool(kids) and all(c.type in ("image", "softbreak", "hardbreak") for c in kids)


def parse_doc(path, text: str, *, display: str | None = None, is_blueprint: bool = True) -> Doc:
    """Parse a markdown file into a Doc. Front-matter YAML errors set `fm_error`."""
    fm_error = None
    try:
        fm, body, offset = split_front_matter(text)
    except FrontMatterError as exc:
        fm, body, offset = None, text, 0
        fm_error = (exc.line, exc.message)
    first = text.splitlines()[:1]
    if fm is None and fm_error is None and first and first[0].strip() == "---":
        fm_error = (1, "unterminated front matter block")
    fm_lines = text.splitlines()[1 : offset - 1] if offset else []

    p = Path(path)
    doc = Doc(
        path=display if display is not None else str(path),
        front_matter=fm,
        body_offset=offset,
        sections=[],
        abs_path=p.resolve(),
        is_blueprint=is_blueprint,
        fm_lines=fm_lines,
        fm_error=fm_error,
    )

    def fline(idx: int) -> int:
        return idx + offset + 1

    body_lines = body.splitlines()
    tokens = _MD.parse(body)
    cur = Section(title="", level=0, line=1, _body_start=0)
    doc.sections.append(cur)

    list_stack: list[str] = []  # "ordered" | "bullet"
    in_heading = False
    in_table = False
    table: Table | None = None
    row: Row | None = None

    for i, t in enumerate(tokens):
        ty = t.type
        if ty == "heading_open":
            in_heading = True
            title = tokens[i + 1].content.strip()
            if t.tag == "h2":
                cur = Section(
                    title=title, level=2, line=fline(t.map[0]), _body_start=t.map[1]
                )
                doc.sections.append(cur)
            cur.headings.append(title)
        elif ty == "heading_close":
            in_heading = False
        elif ty in ("bullet_list_open", "ordered_list_open"):
            list_stack.append("ordered" if ty == "ordered_list_open" else "bullet")
        elif ty in ("bullet_list_close", "ordered_list_close"):
            list_stack.pop()
        elif ty == "list_item_open" and len(list_stack) == 1:
            if list_stack[-1] == "ordered":
                cur.ordered_items += 1
            else:
                cur.bullet_items += 1
        elif ty == "table_open":
            in_table = True
            table = Table(line=fline(t.map[0]))
            cur.tables.append(table)
        elif ty == "table_close":
            in_table = False
            table = None
        elif ty == "tr_open" and table is not None:
            row = Row(line=fline(t.map[0]))
        elif ty == "tr_close" and table is not None and row is not None:
            if _is_header(tokens, i):
                table.header = row.cells
            else:
                table.rows.append(row)
            row = None
        elif ty == "paragraph_open":
            # lines unit: top-level paragraphs only (not list items or tables)
            if not list_stack and not in_table and t.map:
                if not _inline_is_image_only(tokens[i + 1]):
                    cur.prose_lines += sum(
                        1 for ln in body_lines[t.map[0] : t.map[1]] if ln.strip()
                    )
        elif ty == "inline":
            line_idx = t.map[0] if t.map else 0
            if row is not None:
                row.cells.append(t.content.strip())
                row.hrefs.append(
                    [c.attrGet("href") for c in t.children or [] if c.type == "link_open"]
                )
            elif not in_heading and not in_table:
                cur.prose_words += len(_inline_text(t).split())
            # images and links anywhere in the section (tables included)
            ln = line_idx
            for c in t.children or []:
                if c.type in ("softbreak", "hardbreak"):
                    ln += 1
                elif c.type == "image":
                    cur.images.append((c.attrGet("src"), fline(ln)))
                elif c.type == "link_open":
                    cur.links.append((c.attrGet("href"), fline(ln)))

    # raw body text per section (content after the heading line)
    for idx, s in enumerate(doc.sections):
        # a section ends where the next H2 heading line starts
        end = (
            doc.sections[idx + 1].line - offset - 1
            if idx + 1 < len(doc.sections)
            else len(body_lines)
        )
        s.body_text = "\n".join(body_lines[s._body_start : end]).strip("\n")
    return doc


def _is_header(tokens, i) -> bool:
    """True when the tr_close at index i closes a row inside thead."""
    for j in range(i, len(tokens)):
        if tokens[j].type == "thead_close":
            return True
        if tokens[j].type in ("tr_open", "tbody_open", "table_close"):
            return False
    return False
