"""BG001: per-section and page budgets from budgets.yaml (tunable without code changes).

No budget number lives in this file; every limit is read from budgets.yaml.
A section budget that omits a unit does not limit that unit.
"""

from __future__ import annotations

from ..report import Finding
from . import structure_type


def _counts(sec) -> dict[str, int]:
    return {
        "tables": len(sec.tables),
        "steps": sec.ordered_items,
        "bullets": sec.bullet_items,
        "lines": sec.prose_lines,
        "diagrams": len(sec.images),
    }


def _page_budget(tcfg, fm):
    pw = tcfg.get("page_words")
    if isinstance(pw, dict):
        return pw.get("flagship" if fm.get("flagship") is True else "catalog")
    return pw


def check(doc, ctx) -> list[Finding]:
    btype = structure_type(doc, ctx)
    if btype is None:
        return []
    tcfg = ctx.budgets["types"][btype]
    out = []
    for budget in tcfg.get("sections") or []:
        sec = doc.section(budget["title"])
        if sec is None:
            continue
        counts = _counts(sec)
        for unit, value in counts.items():
            limit = budget.get(unit)
            if limit is not None and value > limit:
                out.append(
                    Finding(doc.path, sec.line, 1, "error", "BG001", f"{sec.title}: {value} {unit} > budget {limit}")
                )
        limit = budget.get("rows")
        if limit is not None:
            for table in sec.tables:
                if len(table.rows) > limit:
                    out.append(
                        Finding(
                            doc.path,
                            table.line,
                            1,
                            "error",
                            "BG001",
                            f"{sec.title}: {len(table.rows)} rows > budget {limit}",
                        )
                    )
    limit = _page_budget(tcfg, doc.front_matter)
    total = sum(s.prose_words for s in doc.sections)
    if limit is not None and total > limit:
        out.append(Finding(doc.path, 1, 1, "error", "BG001", f"document: {total} page_words > budget {limit}"))
    return out
