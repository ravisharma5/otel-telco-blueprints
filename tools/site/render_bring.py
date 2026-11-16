"""Render the "What you bring" block on every use-case page from its front matter.

Each catalog/*/*/README.md (the demo domain is skipped) holds one generated
block under "### What you bring" in What you need:

    <!-- generated:what-you-bring start -->
    <!-- generated:what-you-bring end -->

The block has two tables, built from the page's `adaptation` field:

- a summary: model change, your expertise, and how far to climb (PB-03 link)
- one row per bring item: item, network component, mechanism, owner, and a
  link to the PB-11 domain row

Owner and matrix-row anchor come from the PB-11 domain tables
(platform/bring-your-own-data/README.md), so a page cannot disagree with PB-11.
Only the text between the markers is replaced. A missing or duplicated marker
stops the run.

bring_summary(front_matter) gives the one-line rung and expertise text used by
the proposal's evidence summary.

Usage:
    python -m tools.site.render_bring          # rewrite every block
    python -m tools.site.render_bring --check  # exit 1 if a block drifts
"""

from __future__ import annotations

import argparse
import functools
import re
import sys
from pathlib import Path

import yaml

from tools.bplint.slug import github_slug

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "catalog"
PB11 = ROOT / "platform/bring-your-own-data/README.md"
NAME = "what-you-bring"
SKIPPED_DOMAINS = {"demo"}

PB03_LINK = "../../../platform/adaptation/README.md"
PB11_LINK = "../../../platform/bring-your-own-data/README.md"

RUNG_ORDER = ["retrieval", "skills", "head-retrain", "lora-if-gap"]
CHANGE_ORDER = ["none", "retrain"]
CHANGE_OF_RUNG = {"retrieval": "none", "skills": "none", "head-retrain": "retrain", "lora-if-gap": "retrain"}
RUNG_LABELS = {
    "retrieval": "No model change: retrieval only",
    "skills": "No model change: retrieval and skills",
    "head-retrain": "Retrain the Classification head",
    "lora-if-gap": "Retrain the head; LoRA only if a gap remains",
}
CHANGE_LABELS = {"none": "No model change", "retrain": "You retrain or adapt"}
EXPERTISE_ORDER = ["taxonomy", "golden-set", "gate-labels", "tool-contracts", "corpus"]
EXPERTISE_LABELS = {
    "taxonomy": "Your fault or alert taxonomy",
    "golden-set": "A golden set your experts label",
    "gate-labels": "Gate labels from your approvers",
    "tool-contracts": "A contract for each tool",
    "corpus": "Your domain corpus",
}
RUNG_PAGE_TEXT = {
    "retrieval": "No model change: retrieval over your corpus",
    "skills": "No model change: retrieval, a skill per role, and a capability manifest per tool",
    "head-retrain": "Retrain the Classification head on your taxonomy; no other model changes",
    "lora-if-gap": (
        "Retrain the Classification head on your taxonomy; train a LoRA adapter only if a measured gap "
        "remains after retrieval and skills"
    ),
}
CLIMB_TEXT = f"Configure first, and train only on a measured gap, as [PB-03 Adaptation]({PB03_LINK}) sets out"

# Schema id -> the name PB-11 uses ("### Domain: <name>" and Mechanism rows).
DOMAIN_ORDER = ["ran", "vran-oran", "core-cnf", "vnf", "transport-ip", "oss-bss", "customer-care"]
DOMAIN_NAMES = {
    "ran": "RAN",
    "vran-oran": "vRAN and O-RAN",
    "core-cnf": "5G core CNFs",
    "vnf": "VNFs",
    "transport-ip": "Transport and IP",
    "oss-bss": "OSS and BSS",
    "customer-care": "Customer and care",
}
MECHANISM_ORDER = [
    "rag-corpus",
    "skill-manifest",
    "tool-contract",
    "gate-policy",
    "classification-labels",
    "lora-data",
]
MECHANISM_NAMES = {
    "rag-corpus": "RAG corpus",
    "skill-manifest": "Skill or capability manifest",
    "tool-contract": "MCP tool contract",
    "gate-policy": "Gate and action-layer policy",
    "classification-labels": "Classification labels",
    "lora-data": "LoRA training data",
}

ITEM_HEADER = ("Item", "Network component", "Mechanism", "Owner", "Matrix row")
SUMMARY_HEADER = ("Model change", "Your expertise", "How far to climb")

_DOMAIN_H3 = re.compile(r"^### Domain: (.+?)[ \t]*$", re.M)


def _fail(msg: str) -> None:
    raise SystemExit(f"render_bring: {msg}")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _cell(text: str) -> str:
    if "|" in text or "\n" in text:
        _fail(f"table cell cannot hold '|' or a newline: {text!r}")
    return text


def _table_after(text: str, start: int) -> list[list[str]]:
    """Rows (header first, separator dropped) of the first table after `start`."""
    rows: list[list[str]] = []
    for line in text[start:].splitlines():
        if line.startswith("|"):
            if not re.fullmatch(r"\|(\s*:?-+:?\s*\|)+", line.strip()):
                rows.append(_cells(line))
        elif rows:
            break
        elif line.startswith("#"):
            break
    return rows


@functools.lru_cache(maxsize=4)
def _matrix_cached(path_str: str) -> dict[tuple[str, str], dict[str, str]]:
    path = Path(path_str)
    text = path.read_text(encoding="utf-8")
    headings = {m.group(1): m for m in _DOMAIN_H3.finditer(text)}
    mech = re.search(r"^### Mechanisms[ \t]*$", text, re.M)
    if not mech:
        _fail(f"{path.name} has no '### Mechanisms' table")
    mech_rows = {r[0] for r in _table_after(text, mech.end())[1:]}
    for mid, name in MECHANISM_NAMES.items():
        if name not in mech_rows:
            _fail(f"mechanism '{mid}' ({name}) has no row in the PB-11 Mechanisms table")
    out: dict[tuple[str, str], dict[str, str]] = {}
    for did, name in DOMAIN_NAMES.items():
        m = headings.get(name)
        if not m:
            _fail(f"domain '{did}' ({name}) has no '### Domain: {name}' heading on PB-11")
        rows = _table_after(text, m.end())
        if not rows or "Mechanism" not in rows[0] or "Owner" not in rows[0]:
            _fail(f"'### Domain: {name}' on PB-11 has no table with Mechanism and Owner columns")
        mcol, ocol = rows[0].index("Mechanism"), rows[0].index("Owner")
        by_mech = {r[mcol]: r[ocol] for r in rows[1:]}
        anchor = github_slug(f"Domain: {name}")
        for mid, mname in MECHANISM_NAMES.items():
            if mname not in by_mech:
                _fail(f"'### Domain: {name}' on PB-11 has no '{mname}' row")
            out[(did, mid)] = {"owner": by_mech[mname], "anchor": anchor, "domain": name, "mechanism": mname}
    return out


def matrix(pb11_path: Path = PB11) -> dict[tuple[str, str], dict[str, str]]:
    """{(domain id, mechanism id): {owner, anchor, domain, mechanism}} read from the PB-11 domain tables."""
    return dict(_matrix_cached(str(pb11_path)))


def _adaptation(fm: dict, where: str = "front matter") -> dict:
    ad = fm.get("adaptation")
    if not isinstance(ad, dict):
        _fail(f"{where}: no adaptation field")
    if ad.get("rung") not in RUNG_ORDER:
        _fail(f"{where}: unknown rung {ad.get('rung')!r}")
    for e in ad.get("expertise") or []:
        if e not in EXPERTISE_LABELS:
            _fail(f"{where}: unknown expertise {e!r}")
    return ad


def expertise_in_order(fm: dict) -> list[str]:
    chosen = set(_adaptation(fm).get("expertise") or [])
    return [e for e in EXPERTISE_ORDER if e in chosen]


def bring_summary(fm: dict) -> str:
    """One line: the short rung label, then the expertise labels in enum order."""
    ad = _adaptation(fm)
    labels = ", ".join(EXPERTISE_LABELS[e] for e in expertise_in_order(fm))
    return f"{RUNG_LABELS[ad['rung']]}. You bring: {labels}"


def block(fm: dict, mx: dict[tuple[str, str], dict[str, str]] | None = None, where: str = "front matter") -> str:
    """The generated block body: a blank line, the summary table, a blank line, the item table."""
    mx = mx if mx is not None else matrix()
    ad = _adaptation(fm, where)
    lines = [
        "",
        "| " + " | ".join(SUMMARY_HEADER) + " |",
        "|" + "---|" * len(SUMMARY_HEADER),
        "| "
        + " | ".join(
            _cell(c)
            for c in (
                RUNG_PAGE_TEXT[ad["rung"]],
                "; ".join(EXPERTISE_LABELS[e] for e in expertise_in_order(fm)),
                CLIMB_TEXT,
            )
        )
        + " |",
        "",
        "| " + " | ".join(ITEM_HEADER) + " |",
        "|" + "---|" * len(ITEM_HEADER),
    ]
    for item in ad.get("bring") or []:
        domains = item.get("domains") or []
        mech = item.get("mechanism")
        if not domains or mech not in MECHANISM_NAMES:
            _fail(f"{where}: bring item {item.get('item')!r} needs domains and a known mechanism")
        for d in domains:
            if d not in DOMAIN_NAMES:
                _fail(f"{where}: bring item {item.get('item')!r} has unknown domain {d!r}")
        owner = mx[(domains[0], mech)]["owner"]
        # Semicolons, not commas: domain names hold "and", which reads as a list.
        links = "; ".join(f"[{DOMAIN_NAMES[d]}]({PB11_LINK}#{mx[(d, mech)]['anchor']})" for d in domains)
        cells = (item["item"], "; ".join(DOMAIN_NAMES[d] for d in domains), MECHANISM_NAMES[mech], owner, links)
        lines.append("| " + " | ".join(_cell(c) for c in cells) + " |")
    return "\n".join(lines) + "\n\n"


def _marker(edge: str) -> re.Pattern[str]:
    return re.compile(rf"^<!-- generated:{NAME} {edge} -->[ \t]*\n", re.M)


def _front_matter(text: str, where: str) -> dict:
    if not text.startswith("---"):
        _fail(f"{where} has no front matter")
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def has_markers(text: str) -> bool:
    return bool(_marker("start").search(text) or _marker("end").search(text))


def render(page_text: str, where: str = "page", mx: dict | None = None) -> str:
    """page_text with its what-you-bring block replaced by the render."""
    starts = list(_marker("start").finditer(page_text))
    ends = list(_marker("end").finditer(page_text))
    if len(starts) != 1 or len(ends) != 1:
        _fail(f"{where}: need exactly one start and one end marker for '{NAME}', found {len(starts)} and {len(ends)}")
    start, end = starts[0], ends[0]
    if end.start() < start.end():
        _fail(f"{where}: '{NAME}' end marker comes before its start")
    content = block(_front_matter(page_text, where), mx, where)
    return page_text[: start.end()] + content + page_text[end.start() :]


def pages(catalog: Path = CATALOG) -> list[Path]:
    """Every published use-case page (the demo domain is skipped)."""
    out = []
    for path in sorted(catalog.glob("*/*/README.md")):
        fm = _front_matter(path.read_text(encoding="utf-8"), str(path))
        if fm.get("type") == "use-case" and fm.get("domain") not in SKIPPED_DOMAINS:
            out.append(path)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a block drifts")
    args = parser.parse_args(argv)
    mx = matrix()
    stale = []
    for path in pages():
        rel = path.relative_to(ROOT).as_posix()
        old = path.read_text(encoding="utf-8")
        new = render(old, rel, mx)
        if new == old:
            continue
        if args.check:
            stale.append(rel)
        else:
            path.write_text(new, encoding="utf-8")
            print(f"rewrote {rel}")
    if stale:
        for rel in stale:
            print(f"{rel}: generated block out of date ({NAME}); run `make render`", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
