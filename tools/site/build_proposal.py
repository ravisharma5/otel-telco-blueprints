"""Render the proposal's generated blocks from the blueprints.

The proposal (proposal/index.md) holds seven generated blocks between marker lines:

    <!-- generated:facts-stamp start -->          "Facts checked as of <date>."
    <!-- generated:readiness-questions start -->  the ten questions (framework/index.md)
    <!-- generated:architecture start -->         architecture pages and the question each answers
    <!-- generated:platform start -->             platform pages: id, title, one-liner
    <!-- generated:catalog start -->              use cases by domain: id, title, depth, summary
    <!-- generated:flagships start -->            flagship recipes: outcome and measures
    <!-- generated:evidence-summary start -->     per use case: Sources rows per Basis,
                                                  named gates, depth, and what you bring

Every block comes from front matter or tables already on the pages, and the
dates come from data/facts-check.yaml. Only the text between a start and an end
marker is replaced. A missing or duplicated marker stops the run. Hand-written
framing between the blocks is left alone.

Usage:
    python -m tools.site.build_proposal          # rewrite the proposal
    python -m tools.site.build_proposal --check  # exit 1 if a block drifts
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from tools.bplint.loader import split_front_matter
from tools.bplint.markdown import parse_doc
from tools.site.export_explorer import (
    DEPTH_LABELS,
    DOMAIN_LABELS,
    EXPORTER_TABLE_HEADERS,
    SKIPPED_DOMAINS,
    _plain,
    is_idea,
)
from tools.site.render_bring import bring_summary
from tools.site.render_catalog import domain_order

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "proposal/index.md"
FACTS_FILE = ROOT / "data/facts-check.yaml"
FRAMEWORK = ROOT / "framework/index.md"
QUESTIONS_HEADING = "### The ten questions"
# Same order as the Architecture nav in mkdocs.yml.
ARCHITECTURE_ORDER = ("index", "decision-gate", "adaptation-ladder", "placement", "crosswalk")
# The five Basis values of schemas/sources-table.yaml, in schema order.
BASIS = ("model card", "research", "Red Hat guidance", "industry use case", "project documentation")
NAMES = (
    "facts-stamp",
    "readiness-questions",
    "architecture",
    "platform",
    "catalog",
    "flagships",
    "evidence-summary",
    "ideas",
)
LINK_RE = re.compile(r"\]\(([^)]+)\)")


def _fail(msg: str) -> None:
    raise SystemExit(f"build_proposal: {msg}")


def _cell(text: str) -> str:
    if "|" in text or "\n" in text:
        _fail(f"table cell cannot hold '|' or a newline: {text!r}")
    return text


def _row(cells) -> str:
    return "| " + " | ".join(_cell(str(c)) for c in cells) + " |"


def _table(header, rows) -> list[str]:
    return [_row(header), "|" + "---|" * len(header), *(_row(r) for r in rows)]


def _doc(path: Path):
    rel = path.relative_to(ROOT).as_posix()
    doc = parse_doc(path, path.read_text(encoding="utf-8"), display=rel)
    if doc.fm_error:
        _fail(f"{rel}: front matter line {doc.fm_error[0]}: {doc.fm_error[1]}")
    return rel, doc


def checked_date(facts_file: Path = FACTS_FILE) -> str:
    facts = yaml.safe_load(facts_file.read_text(encoding="utf-8")) or {}
    checked = facts.get("checked")
    if not checked:
        _fail(f"{facts_file.relative_to(ROOT)} has no checked date")
    return str(checked)


# ---- blocks ----------------------------------------------------------------


def facts_stamp(checked: str) -> str:
    return f"Facts checked as of {checked}."


def readiness_questions(framework: Path = FRAMEWORK) -> str:
    """The ten questions table, copied from framework/index.md.

    framework/ and proposal/ sit at the same depth, so "../" links resolve the
    same from both; any other relative link stops the run.
    """
    text = framework.read_text(encoding="utf-8")
    if QUESTIONS_HEADING not in text:
        _fail(f"framework/index.md has no '{QUESTIONS_HEADING}' section")
    body = text.split(QUESTIONS_HEADING, 1)[1].split("\n#", 1)[0]
    lines = [ln for ln in body.splitlines() if ln.startswith("|")]
    questions = [ln for ln in lines[2:] if re.match(r"^\|\s*\d+\s*\|", ln)]
    if len(questions) != 10:
        _fail(f"framework/index.md lists {len(questions)} questions, expected 10")
    for href in LINK_RE.findall("\n".join(lines)):
        if not href.startswith(("../", "https://", "http://")):
            _fail(f"readiness question link {href!r} would break when copied into the proposal")
    return "\n".join(lines)


def architecture(arch_dir: Path | None = None) -> str:
    arch_dir = arch_dir or ROOT / "architecture"
    found = sorted(p.stem for p in arch_dir.glob("*.md"))
    if sorted(ARCHITECTURE_ORDER) != found:
        _fail(f"architecture pages {found} do not match ARCHITECTURE_ORDER")
    rows = []
    for stem in ARCHITECTURE_ORDER:
        _rel, doc = _doc(arch_dir / f"{stem}.md")
        fm = doc.front_matter or {}
        rows.append([f"[{fm['title']}](../architecture/{stem}.md)", fm["question"]])
    return "\n".join(_table(("Page", "Question it answers"), rows))


def platform_pages(platform_dir: Path | None = None) -> list[dict]:
    platform_dir = platform_dir or ROOT / "platform"
    out = []
    for path in platform_dir.glob("*/README.md"):
        rel, doc = _doc(path)
        fm = doc.front_matter or {}
        out.append({"id": fm["id"], "title": fm["title"], "one_liner": fm["one_liner"], "rel": rel})
    return sorted(out, key=lambda p: p["id"])


def platform(pbs: list[dict]) -> str:
    rows = [[pb["id"], f"[{pb['title']}](../{pb['rel']})", pb["one_liner"]] for pb in pbs]
    return "\n".join(_table(("ID", "Platform blueprint", "One-liner"), rows))


def use_cases(catalog_dir: Path | None = None) -> list[dict]:
    """Every front-page use case (no ideas), sorted by id, with what the blocks need."""
    catalog_dir = catalog_dir or ROOT / "catalog"
    header = EXPORTER_TABLE_HEADERS["parameters"]
    lower = {b.lower(): b for b in BASIS}
    out = []
    for path in sorted(catalog_dir.glob("*/*/README.md")):
        rel, doc = _doc(path)
        fm = doc.front_matter or {}
        if fm.get("type") != "use-case" or fm.get("domain") in SKIPPED_DOMAINS or is_idea(fm):
            continue
        if fm.get("depth") not in DEPTH_LABELS:
            _fail(f"{rel}: depth {fm.get('depth')!r} has no label")
        sources = doc.section("Sources")
        if sources is None or not sources.tables:
            _fail(f"{rel}: no Sources table")
        counts = dict.fromkeys(BASIS, 0)
        for table in sources.tables:
            if "Basis" not in table.header:
                continue
            idx = table.header.index("Basis")
            for row in table.rows:
                basis = lower.get(row.cells[idx].strip().lower())
                if basis is None:
                    _fail(f"{rel}: unknown Basis {row.cells[idx]!r}")
                counts[basis] += 1
        gov = doc.section("Governance")
        params = [t for t in (gov.tables if gov else []) if tuple(t.header) == header]
        if len(params) != 1:
            _fail(f"{rel}: Governance needs one table with header {' | '.join(header)}")
        out.append(
            {
                "id": fm["id"],
                "title": fm["title"],
                "domain": fm["domain"],
                "depth": fm["depth"],
                "flagship": bool(fm.get("flagship")),
                "card": fm.get("card") or {},
                "link": "../" + rel,
                "counts": counts,
                "gates": [_plain(r.cells[0]) for r in params[0].rows],
                "bring": bring_summary(fm),
            }
        )
    return sorted(out, key=lambda u: u["id"])


NUMBER_WORDS = ("One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten")


def ideas_line(catalog_dir: Path | None = None) -> str:
    """One sentence with the idea count and a link to the ideas index, or "" with no ideas."""
    catalog_dir = catalog_dir or ROOT / "catalog"
    count = 0
    for path in catalog_dir.glob("*/*/README.md"):
        fm, _, _ = split_front_matter(path.read_text(encoding="utf-8"))
        if fm is None:
            continue
        if fm.get("type") == "use-case" and fm.get("domain") not in SKIPPED_DOMAINS and is_idea(fm):
            count += 1
    if not count:
        return ""
    number = NUMBER_WORDS[count - 1] if count <= len(NUMBER_WORDS) else str(count)
    noun = "use case is" if count == 1 else "use cases are"
    return f"{number} more {noun} open for contribution as [exploration ideas](../catalog/ideas/index.md)."


def catalog(ucs: list[dict]) -> str:
    parts = []
    for domain in domain_order():
        rows = [u for u in ucs if u["domain"] == domain]
        if not rows:
            continue
        table = _table(
            ("Use case", "Title", "Depth", "Summary"),
            [[f"[{u['id']}]({u['link']})", u["title"], DEPTH_LABELS[u["depth"]], u["card"]["summary"]] for u in rows],
        )
        parts.append("\n".join([f"### {DOMAIN_LABELS[domain]}", "", *table]))
    return "\n\n".join(parts)


def flagships(ucs: list[dict]) -> str:
    rows = [
        [f"[{u['title']}]({u['link']})", u["card"]["outcome"], "; ".join(u["card"]["measures"])]
        for u in ucs
        if u["flagship"]
    ]
    if not rows:
        _fail("no flagship use cases")
    return "\n".join(_table(("Recipe", "Outcome", "Measures"), rows))


def evidence_summary(ucs: list[dict], checked: str) -> str:
    header = (
        "Use case",
        "Depth",
        *(b[0].upper() + b[1:] for b in BASIS),
        "Named gates",
        "What you bring",
    )
    rows = [
        [
            f"[{u['id']}]({u['link']}) {u['title']}",
            DEPTH_LABELS[u["depth"]],
            *(u["counts"][b] for b in BASIS),
            "; ".join(u["gates"]),
            u["bring"],
        ]
        for u in ucs
    ]
    lead = (
        f"Counted from each page's Sources table on {checked}. "
        "Each number is how many Sources rows on the page have that Basis."
    )
    return "\n".join([lead, "", *_table(header, rows)])


def blocks(root: Path = ROOT) -> dict[str, str]:
    """Marker name -> rendered text. A blank line separates each block from its markers."""
    checked = checked_date(root / "data/facts-check.yaml")
    ucs = use_cases(root / "catalog")
    bodies = {
        "facts-stamp": facts_stamp(checked),
        "readiness-questions": readiness_questions(root / "framework/index.md"),
        "architecture": architecture(root / "architecture"),
        "platform": platform(platform_pages(root / "platform")),
        "catalog": catalog(ucs),
        "flagships": flagships(ucs),
        "evidence-summary": evidence_summary(ucs, checked),
        "ideas": ideas_line(root / "catalog"),
    }
    # An empty body (no ideas yet) leaves one blank line between the markers.
    return {name: f"\n{bodies[name]}\n\n" if bodies[name] else "\n" for name in NAMES}


# ---- markers and CLI -------------------------------------------------------


def _marker(name: str, edge: str) -> re.Pattern[str]:
    return re.compile(rf"^<!-- generated:{re.escape(name)} {edge} -->[ \t]*\n", re.M)


def render(page_text: str, root: Path = ROOT) -> str:
    """page_text with every generated block replaced by its render."""
    out = page_text
    for name, content in blocks(root).items():
        starts = list(_marker(name, "start").finditer(out))
        ends = list(_marker(name, "end").finditer(out))
        if len(starts) != 1 or len(ends) != 1:
            _fail(
                f"need exactly one start and one end marker for '{name}', "
                f"found {len(starts)} and {len(ends)}"
            )
        start, end = starts[0], ends[0]
        if end.start() < start.end():
            _fail(f"'{name}' end marker comes before its start")
        out = out[: start.end()] + content + out[end.start() :]
    return out


def _drifted(old: str, new: str) -> list[str]:
    names = []
    for name in NAMES:
        pat = re.compile(
            rf"<!-- generated:{re.escape(name)} start -->(.*?)<!-- generated:{re.escape(name)} end -->",
            re.S,
        )
        a, b = pat.search(old), pat.search(new)
        if not a or not b or a.group(1) != b.group(1):
            names.append(name)
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the proposal drifts")
    args = parser.parse_args(argv)
    old = PAGE.read_text(encoding="utf-8")
    new = render(old)
    if args.check:
        if new != old:
            names = ", ".join(_drifted(old, new)) or "unknown block"
            print(
                f"{PAGE.relative_to(ROOT)}: generated block out of date ({names}); run `make render`",
                file=sys.stderr,
            )
            return 1
        return 0
    if new != old:
        PAGE.write_text(new, encoding="utf-8")
        print(f"rewrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
