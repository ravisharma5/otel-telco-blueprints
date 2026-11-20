"""Render the ideas index and the idea block on every idea page from front matter.

An idea page sits in catalog/ideas/<slug>/README.md and carries the `idea`
front-matter object (why, promote, optional merged_into). This tool writes two
kinds of generated block:

    <!-- generated:ideas start -->   in catalog/ideas/index.md: one table row per idea
    <!-- generated:idea start -->    on each idea page, directly after the H1:
                                     the banner, why it's an idea, and what would promote it

Only the text between a start and an end marker is replaced. An idea page with
no idea markers gets them inserted after its H1. A duplicated marker stops the
run. With no idea pages and no catalog/ideas/index.md, the run does nothing.

Usage:
    python -m tools.site.render_ideas          # rewrite every block
    python -m tools.site.render_ideas --check  # exit 1 if a block drifts
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from tools.bplint.loader import split_front_matter
from tools.site.export_explorer import IDEAS_DIR, SKIPPED_DOMAINS, is_idea

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog"
INDEX_NAME = "ideas"
PAGE_NAME = "idea"
INDEX_COLUMNS = ("Idea", "Why it's an idea", "What would promote it")
BANNER = (
    "> **Exploration idea, not a recipe.** Try it, test it, and contribute back. "
    "[How to promote an idea](../index.md#promote-an-idea)."
)
H1_RE = re.compile(r"^# .*\n", re.M)


def _fail(msg: str) -> None:
    raise SystemExit(f"render_ideas: {msg}")


def _front_matter(path: Path, where: str) -> dict:
    # The block closes at the first line that is exactly "---", not at a "---" substring.
    fm, _, _ = split_front_matter(path.read_text(encoding="utf-8"))
    if fm is None:
        _fail(f"{where} has no front matter")
    return fm


def _cell(text: str) -> str:
    if "|" in text or "\n" in text:
        _fail(f"table cell cannot hold '|' or a newline: {text!r}")
    return text


def _line(text: str, where: str) -> str:
    if "\n" in text:
        _fail(f"{where}: idea text cannot hold a newline: {text!r}")
    return text


def ideas(catalog: Path = CATALOG) -> list[dict]:
    """Every idea page, sorted by id, with its merge host resolved (or None)."""
    pages = []
    for path in sorted(catalog.glob("*/*/README.md")):
        where = path.relative_to(catalog.parent).as_posix()
        fm = _front_matter(path, where)
        if fm.get("type") != "use-case" or fm.get("domain") in SKIPPED_DOMAINS:
            continue
        pages.append((path, where, fm))
    hosts = {fm["id"]: (path, fm) for path, _, fm in pages if not is_idea(fm) and fm.get("id")}
    out = []
    for path, where, fm in pages:
        if not is_idea(fm):
            continue
        if path.parent.parent.name != IDEAS_DIR:
            _fail(f"{where}: an idea page must sit in catalog/{IDEAS_DIR}/")
        idea = fm["idea"]
        why = str(idea.get("why") or "").strip()
        promote = [str(p).strip() for p in idea.get("promote") or []]
        if not why or not promote:
            _fail(f"{where}: the idea object needs why and promote")
        host = None
        merged = idea.get("merged_into")
        if merged:
            if merged not in hosts:
                _fail(f"{where}: merged_into {merged} is not a front-page use case")
            host_path, host_fm = hosts[merged]
            host = {
                "id": merged,
                "title": host_fm["title"],
                "rel": host_path.relative_to(catalog).as_posix(),
            }
        out.append(
            {
                "id": fm["id"],
                "title": fm["title"],
                "slug": path.parent.name,
                "why": why,
                "promote": promote,
                "host": host,
                "path": path,
                "where": where,
            }
        )
    return sorted(out, key=lambda i: i["id"])


def index_table(items: list[dict]) -> str:
    """The ideas index table: one row per idea, promote items joined with "; "."""
    lines = ["| " + " | ".join(INDEX_COLUMNS) + " |", "|" + "---|" * len(INDEX_COLUMNS)]
    for i in items:
        cells = [f"[{i['id']} {i['title']}]({i['slug']}/README.md)", i["why"], "; ".join(i["promote"])]
        lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    return "\n".join(lines)


def idea_block(idea: dict, host: dict | None) -> str:
    """The idea page block body, with a blank line next to each marker."""
    where = idea.get("where", idea["id"])
    parts = [
        BANNER,
        f"**Why it's an idea.** {_line(idea['why'], where)}",
        "**What would promote it:**",
        "\n".join(f"- [ ] {_line(p, where)}" for p in idea["promote"]),
    ]
    if host:
        parts.append(f"Its scope now sits in [{host['id']} {host['title']}](../../{host['rel']}).")
    return "\n" + "\n\n".join(parts) + "\n\n"


def _marker(name: str, edge: str) -> re.Pattern[str]:
    return re.compile(rf"^<!-- generated:{re.escape(name)} {edge} -->[ \t]*\n", re.M)


def _replace(text: str, name: str, content: str, where: str) -> str:
    starts = list(_marker(name, "start").finditer(text))
    ends = list(_marker(name, "end").finditer(text))
    if len(starts) != 1 or len(ends) != 1:
        _fail(
            f"{where}: need exactly one start and one end marker for '{name}', "
            f"found {len(starts)} and {len(ends)}"
        )
    start, end = starts[0], ends[0]
    if end.start() < start.end():
        _fail(f"{where}: '{name}' end marker comes before its start")
    return text[: start.end()] + content + text[end.start() :]


def render_page(text: str, block: str, where: str = "page") -> str:
    """text with its idea block replaced; markers are inserted after the H1 when both are missing."""
    if not _marker(PAGE_NAME, "start").search(text) and not _marker(PAGE_NAME, "end").search(text):
        fm, body, _ = split_front_matter(text)
        body_at = len(text) - len(body) if fm is not None else 0
        h1 = H1_RE.search(text, body_at)
        if h1 is None:
            _fail(f"{where}: no H1 to place the idea block after")
        insert = f"\n<!-- generated:{PAGE_NAME} start -->\n<!-- generated:{PAGE_NAME} end -->\n"
        text = text[: h1.end()] + insert + text[h1.end() :]
    return _replace(text, PAGE_NAME, block, where)


def render_index(text: str, items: list[dict], where: str = "index") -> str:
    """text with the ideas table replaced."""
    return _replace(text, INDEX_NAME, f"\n{index_table(items)}\n\n", where)


def main(argv: list[str] | None = None, catalog: Path = CATALOG) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a block drifts")
    args = parser.parse_args(argv)
    items = ideas(catalog)
    index = catalog / IDEAS_DIR / "index.md"
    if not items and not index.exists():
        return 0
    if not index.exists():
        _fail(f"{catalog.name}/{IDEAS_DIR}/index.md is missing")
    # Render everything before writing anything, so a bad value leaves no half-written tree.
    changes: list[tuple[Path, str, str, str, str]] = []
    where = index.relative_to(catalog.parent).as_posix()
    old = index.read_text(encoding="utf-8")
    changes.append((index, where, INDEX_NAME, old, render_index(old, items, where)))
    for i in items:
        old = i["path"].read_text(encoding="utf-8")
        changes.append((i["path"], i["where"], PAGE_NAME, old, render_page(old, idea_block(i, i["host"]), i["where"])))
    stale = []
    for path, where, name, old, new in changes:
        if new == old:
            continue
        if args.check:
            stale.append((where, name))
        else:
            path.write_text(new, encoding="utf-8")
            print(f"rewrote {where}")
    for where, name in stale:
        print(f"{where}: generated block out of date ({name}); run `make render`", file=sys.stderr)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
