"""SC001, SC002, AG001: section order, declared stubs, and at-a-glance labels."""

from __future__ import annotations

from ..report import Finding
from . import structure_type

FIRST = "At a glance"


def _lcs_keep(actual: list[str], expected: list[str]) -> set[int]:
    """Indexes in `actual` that form a longest subsequence in expected order."""
    n, m = len(actual), len(expected)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = (
                dp[i + 1][j + 1] + 1
                if actual[i] == expected[j]
                else max(dp[i + 1][j], dp[i][j + 1])
            )
    keep, i, j = set(), 0, 0
    while i < n and j < m:
        if actual[i] == expected[j]:
            keep.add(i)
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return keep


def _order_findings(doc, expected: list[str]) -> list[Finding]:
    out = []
    h2 = [s for s in doc.sections if s.level == 2]
    titles = [s.title for s in h2]
    expected_set = set(expected)

    seen = set()
    known = []  # (index into h2, title) for first occurrence of expected titles
    for idx, s in enumerate(h2):
        if s.title not in expected_set:
            out.append(Finding(doc.path, s.line, 1, "error", "SC001", f"unexpected section '{s.title}'"))
        elif s.title in seen:
            out.append(Finding(doc.path, s.line, 1, "error", "SC001", f"duplicate section '{s.title}'"))
        else:
            seen.add(s.title)
            known.append((idx, s.title))

    for title in expected:
        if title not in seen:
            out.append(Finding(doc.path, 1, 1, "error", "SC001", f"missing section '{title}'"))

    if titles and titles[0] != FIRST:
        out.append(
            Finding(doc.path, h2[0].line, 1, "error", "SC001", f"first section must be '{FIRST}', found '{titles[0]}'")
        )

    keep = _lcs_keep([t for _, t in known], expected)
    for pos, (idx, title) in enumerate(known):
        if pos not in keep and title != FIRST:
            out.append(
                Finding(doc.path, h2[idx].line, 1, "error", "SC001", f"section '{title}' is out of order")
            )
    return out


def _stub_findings(doc, ctx, btype, tcfg) -> list[Finding]:
    marker = ctx.budgets.get("stub_marker")
    if not marker:
        return []
    fm = doc.front_matter
    if btype == "use-case" and fm.get("flagship") is not True:
        scope = set(tcfg.get("catalog_required") or [])
        why = "catalog entries must fill it"
    else:
        scope = None  # every section
        why = "flagship and platform blueprints cannot stub sections"
    out = []
    for s in doc.sections:
        if s.level != 2 or not s.body_text.strip().startswith(marker):
            continue
        if scope is None or s.title in scope:
            out.append(
                Finding(doc.path, s.line, 1, "error", "SC002", f"section '{s.title}' is a stub; {why}")
            )
    return out


def _glance_findings(doc, tcfg) -> list[Finding]:
    sec = doc.section(FIRST)
    if sec is None:
        return []  # SC001 reports the missing section
    if not sec.tables:
        return [Finding(doc.path, sec.line, 1, "error", "AG001", f"'{FIRST}' has no table")]
    table = sec.tables[0]
    labels = {r.cells[0].replace("**", "").strip() for r in table.rows if r.cells}
    return [
        Finding(doc.path, table.line, 1, "error", "AG001", f"'{FIRST}' table is missing row '{label}'")
        for label in tcfg.get("at_a_glance_rows") or []
        if label not in labels
    ]


def check(doc, ctx) -> list[Finding]:
    btype = structure_type(doc, ctx)
    if btype is None:
        return []
    tcfg = ctx.budgets["types"][btype]
    expected = [s["title"] for s in tcfg.get("sections") or []]
    return (
        _order_findings(doc, expected)
        + _stub_findings(doc, ctx, btype, tcfg)
        + _glance_findings(doc, tcfg)
    )
