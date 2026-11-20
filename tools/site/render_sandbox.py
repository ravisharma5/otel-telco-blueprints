"""Render the Sandbox block on every use-case page, and the PB-08 use-case list, from the sandbox field.

Each catalog/*/*/README.md (the demo domain is skipped) holds one generated
block under "### Sandbox" in What you need:

    <!-- generated:sandbox start -->
    <!-- generated:sandbox end -->

The block is a one-row table built from the page's `sandbox` field: the
sandbox fit, the trigger on this page (the why line), and a link to the PB-08
section "When a use case needs a sandbox".

PB-08 (platform/security-identity-sandbox/README.md) holds one generated block
in that section:

    <!-- generated:sandbox-fit start -->
    <!-- generated:sandbox-fit end -->

It lists every front-page use case by fit (idea pages are left out), with a
link back to each catalog page.
Only the text between the markers is replaced. A missing or duplicated marker
stops the run.

Usage:
    python -m tools.site.render_sandbox          # rewrite every block
    python -m tools.site.render_sandbox --check  # exit 1 if a block drifts
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from tools.bplint.ideas import is_idea
from tools.site.render_bring import _front_matter, pages

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog"
PB08 = ROOT / "platform/security-identity-sandbox/README.md"
NAME = "sandbox"
PB08_NAME = "sandbox-fit"

FIT_ORDER = ["none", "execution", "whole-agent"]
# Short labels, shared with the explorer chip (copy.md), the PB-08 fit table, and the PB-08 use-case list.
FIT_LABELS = {
    "none": "Base sandbox only",
    "execution": "Sandbox the tools and code",
    "whole-agent": "Sandbox the whole agent",
}
FIT_PAGE_TEXT = {
    "none": (
        "Base sandbox only: the agent reads through the gateways, so the six sandbox controls and the "
        "gateway screen are enough"
    ),
    "execution": "Sandbox the tools and code: run them in their own micro-VM",
    "whole-agent": "Sandbox the whole agent: run it under OpenShell policy inside a micro-VM",
}
PB08_ANCHOR = "when-a-use-case-needs-a-sandbox"
PB08_LINK = "../../../platform/security-identity-sandbox/README.md#" + PB08_ANCHOR
WHERE_TEXT = "[PB-08: when a use case needs a sandbox](" + PB08_LINK + ")"
SANDBOX_HEADER = ("Sandbox fit", "Trigger on this page", "Where to read")


def _fail(msg: str) -> None:
    raise SystemExit(f"render_sandbox: {msg}")


def _cell(text: str) -> str:
    if "|" in text or "\n" in text:
        _fail(f"table cell cannot hold '|' or a newline: {text!r}")
    return text


def _sandbox(fm: dict, where: str = "front matter") -> dict:
    sb = fm.get("sandbox")
    if not isinstance(sb, dict):
        _fail(f"{where}: no sandbox field")
    if sb.get("fit") not in FIT_ORDER:
        _fail(f"{where}: unknown sandbox fit {sb.get('fit')!r}")
    if not str(sb.get("why") or "").strip():
        _fail(f"{where}: the sandbox field needs a why line")
    return sb


def block(fm: dict, where: str = "front matter") -> str:
    """The catalog block body: a blank line, the header, the separator, one row, a blank line."""
    sb = _sandbox(fm, where)
    cells = (FIT_PAGE_TEXT[sb["fit"]], str(sb["why"]).strip(), WHERE_TEXT)
    lines = [
        "",
        "| " + " | ".join(SANDBOX_HEADER) + " |",
        "|" + "---|" * len(SANDBOX_HEADER),
        "| " + " | ".join(_cell(c) for c in cells) + " |",
    ]
    return "\n".join(lines) + "\n\n"


def fit_table(entries: list[tuple[dict, str]]) -> str:
    """The PB-08 block body: one row per fit, listing each use case as a link to its catalog page.

    entries holds (front matter, "<domain>/<slug>") pairs; use cases are sorted by id.
    """
    by_fit: dict[str, list[tuple[str, str]]] = {f: [] for f in FIT_ORDER}
    for fm, key in entries:
        sb = _sandbox(fm, key)
        link = f"[{_cell(str(fm.get('title') or key))}](../../catalog/{key}/README.md)"
        by_fit[sb["fit"]].append((str(fm.get("id") or ""), link))
    lines = ["", "| Fit | Use cases |", "|---|---|"]
    for fit in FIT_ORDER:
        links = [link for _, link in sorted(by_fit[fit])]
        lines.append(f"| {FIT_LABELS[fit]} | {'; '.join(links) if links else 'None yet'} |")
    return "\n".join(lines) + "\n\n"


def _marker(name: str, edge: str) -> re.Pattern[str]:
    return re.compile(rf"^<!-- generated:{name} {edge} -->[ \t]*\n", re.M)


def _replace(page_text: str, name: str, content: str, where: str) -> str:
    starts = list(_marker(name, "start").finditer(page_text))
    ends = list(_marker(name, "end").finditer(page_text))
    if len(starts) != 1 or len(ends) != 1:
        _fail(f"{where}: need exactly one start and one end marker for '{name}', found {len(starts)} and {len(ends)}")
    start, end = starts[0], ends[0]
    if end.start() < start.end():
        _fail(f"{where}: '{name}' end marker comes before its start")
    return page_text[: start.end()] + content + page_text[end.start() :]


def render(page_text: str, where: str = "page") -> str:
    """page_text with its sandbox block replaced by the render."""
    return _replace(page_text, NAME, block(_front_matter(page_text, where), where), where)


def render_pb08(pb08_text: str, entries: list[tuple[dict, str]], where: str = "PB-08") -> str:
    """PB-08 text with its sandbox-fit block replaced by the render."""
    return _replace(pb08_text, PB08_NAME, fit_table(entries), where)


def _key(path: Path) -> str:
    return "/".join(path.parent.relative_to(CATALOG).parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a block drifts")
    args = parser.parse_args(argv)
    stale = []
    entries = []
    for path in pages():
        rel = path.relative_to(ROOT).as_posix()
        old = path.read_text(encoding="utf-8")
        fm = _front_matter(old, rel)
        if not is_idea(fm):  # idea pages keep their own block but stay off the PB-08 list
            entries.append((fm, _key(path)))
        new = render(old, rel)
        if new == old:
            continue
        if args.check:
            stale.append((rel, NAME))
        else:
            path.write_text(new, encoding="utf-8")
            print(f"rewrote {rel}")
    rel = PB08.relative_to(ROOT).as_posix()
    old = PB08.read_text(encoding="utf-8")
    new = render_pb08(old, entries, rel)
    if new != old:
        if args.check:
            stale.append((rel, PB08_NAME))
        else:
            PB08.write_text(new, encoding="utf-8")
            print(f"rewrote {rel}")
    if stale:
        for rel, name in stale:
            print(f"{rel}: generated block out of date ({name}); run `make render`", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
