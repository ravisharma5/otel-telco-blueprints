"""Render the Recipes overview's generated blocks from use-case front matter.

The overview (catalog/index.md) holds two generated blocks between marker lines:

    <!-- generated:catalog-by-domain start -->   one table per domain
    <!-- generated:catalog-by-platform start -->  one H3 per platform blueprint

Each block reads id, title, domain, depth, also_covers, and platform_blueprints
from every catalog/*/*/README.md (the demo domain and idea pages are skipped). Only the text
between a start and an end marker is replaced. A missing or duplicated marker
stops the run.

Usage:
    python -m tools.site.render_catalog          # rewrite the overview
    python -m tools.site.render_catalog --check  # exit 1 if the overview drifts
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from tools.bplint.loader import split_front_matter
from tools.bplint.slug import github_slug
from tools.site.export_explorer import DEPTH_LABELS, DOMAIN_LABELS, SKIPPED_DOMAINS, is_idea

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog"
PLATFORM = ROOT / "platform"
PAGE = CATALOG / "index.md"
SCHEMA = ROOT / "schemas/use-case.schema.json"
DOMAIN_COLUMNS = ("Recipe", "Topic", "Depth", "Also covers")
NAMES = ("catalog-by-domain", "catalog-by-platform")


def _front_matter(path: Path) -> dict:
    # The block closes at the first line that is exactly "---", not at a "---" substring.
    fm, _, _ = split_front_matter(path.read_text(encoding="utf-8"))
    if fm is None:
        raise SystemExit(f"render_catalog: {path.relative_to(ROOT)} has no front matter")
    return fm


def _cell(text: str) -> str:
    if "|" in text or "\n" in text:
        raise SystemExit(f"render_catalog: table cell cannot hold '|' or a newline: {text!r}")
    return text


def domain_order() -> list[str]:
    """Domains in schema enum order, without the skipped (fixture) domains."""
    enum = json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]["domain"]["enum"]
    return [d for d in enum if d not in SKIPPED_DOMAINS]


def use_cases(catalog: Path = CATALOG) -> list[dict]:
    """Every front-page use-case page (no ideas), sorted by id, with its path relative to catalog/."""
    out = []
    for path in sorted(catalog.glob("*/*/README.md")):
        fm = _front_matter(path)
        if fm.get("domain") in SKIPPED_DOMAINS or is_idea(fm):
            continue
        rel = path.relative_to(catalog).as_posix()
        if fm.get("domain") not in DOMAIN_LABELS:
            raise SystemExit(f"render_catalog: {rel}: domain {fm.get('domain')!r} has no label")
        if fm.get("depth") not in DEPTH_LABELS:
            raise SystemExit(f"render_catalog: {rel}: depth {fm.get('depth')!r} has no label")
        out.append(
            {
                "id": fm["id"],
                "title": fm["title"],
                "domain": fm["domain"],
                "depth": fm["depth"],
                "also_covers": list(fm.get("also_covers") or []),
                "platform_blueprints": list(fm.get("platform_blueprints") or []),
                "rel": rel,
            }
        )
    return sorted(out, key=lambda u: u["id"])


def platforms(platform: Path = PLATFORM) -> list[dict]:
    """Every platform page, sorted by id, with its path relative to the repository root."""
    out = []
    for path in platform.glob("*/README.md"):
        fm = _front_matter(path)
        out.append({"id": fm["id"], "title": fm["title"], "rel": path.relative_to(ROOT).as_posix()})
    return sorted(out, key=lambda p: p["id"])


def platform_heading(pb: dict) -> str:
    """The overview H3 for a platform page, for example "PB-08 Security, identity, and sandbox"."""
    return f"{pb['id']} {pb['title']}"


def platform_anchor(pb: dict) -> str:
    """The anchor each platform page links, for example "pb-08-security-identity-and-sandbox"."""
    return github_slug(platform_heading(pb))


def by_domain(ucs: list[dict]) -> str:
    """One H2 and table per domain that has pages, in schema domain order."""
    parts = []
    for domain in domain_order():
        rows = [u for u in ucs if u["domain"] == domain]
        if not rows:
            continue
        lines = [
            f"## {DOMAIN_LABELS[domain]}",
            "",
            "| " + " | ".join(DOMAIN_COLUMNS) + " |",
            "|" + "---|" * len(DOMAIN_COLUMNS),
        ]
        for u in rows:
            cells = [
                f"[{u['id']}]({u['rel']})",
                u["title"],
                DEPTH_LABELS[u["depth"]],
                "; ".join(u["also_covers"]),
            ]
            lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def by_platform(ucs: list[dict], pbs: list[dict]) -> str:
    """One H3 per platform page in id order, listing every recipe that names it."""
    known = {pb["id"] for pb in pbs}
    for u in ucs:
        for pb in u["platform_blueprints"]:
            if pb not in known:
                raise SystemExit(f"render_catalog: {u['rel']} names unknown platform page {pb}")
    parts = []
    for pb in pbs:
        lines = [
            f"### {platform_heading(pb)}",
            "",
            f"These recipes use [the {pb['title']} page](../{pb['rel']}):",
            "",
        ]
        users = [u for u in ucs if pb["id"] in u["platform_blueprints"]]
        if users:
            lines.extend(f"- [{u['id']} {u['title']}]({u['rel']})" for u in users)
        else:
            lines[-2] = f"No recipe uses [the {pb['title']} page](../{pb['rel']}) yet."
            lines.pop()
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def blocks(catalog: Path = CATALOG, platform: Path = PLATFORM) -> dict[str, str]:
    """Marker name -> rendered text. A blank line separates each block from its markers."""
    ucs = use_cases(catalog)
    return {
        "catalog-by-domain": f"\n{by_domain(ucs)}\n\n",
        "catalog-by-platform": f"\n{by_platform(ucs, platforms(platform))}\n\n",
    }


def _marker(name: str, edge: str) -> re.Pattern[str]:
    return re.compile(rf"^<!-- generated:{re.escape(name)} {edge} -->[ \t]*\n", re.M)


def render(page_text: str, catalog: Path = CATALOG, platform: Path = PLATFORM) -> str:
    """page_text with every generated block replaced by its render."""
    out = page_text
    for name, content in blocks(catalog, platform).items():
        starts = list(_marker(name, "start").finditer(out))
        ends = list(_marker(name, "end").finditer(out))
        if len(starts) != 1 or len(ends) != 1:
            raise SystemExit(
                f"render_catalog: need exactly one start and one end marker for "
                f"'{name}', found {len(starts)} and {len(ends)}"
            )
        start, end = starts[0], ends[0]
        if end.start() < start.end():
            raise SystemExit(f"render_catalog: '{name}' end marker comes before its start")
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
    parser.add_argument("--check", action="store_true", help="exit 1 if the overview drifts")
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
