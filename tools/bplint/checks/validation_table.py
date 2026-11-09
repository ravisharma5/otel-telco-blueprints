"""VT001-VT007: the canonical validation table and the headline E rule.

Column names, empty-cell values, evidence tiers, and the revision threshold come
from schemas/validation-table.yaml. The e_level order comes from
common.schema.json (ctx.enums["e_level"]); it is never hardcoded here.

Evidence paths are only resolved and stat'ed, never read or printed beyond the
href the author wrote.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..report import Finding
from . import structure_type
from ._paths import href_path, is_external, resolve

EVALUATED = "evaluated"


def _err(doc, line, code, msg) -> Finding:
    return Finding(doc.path, line, 1, "error", code, msg)


def _parse_level(cell: str, pattern: re.Pattern, order: list[str]):
    """Return (code, evaluated) or None when the cell is not a valid E-level."""
    cell = cell.strip()
    if not pattern.match(cell):
        return None
    code = cell.split()[0]
    if code not in order:
        return None
    return code, cell.endswith("(evaluated)")


def _is_empty(value: str, empties) -> bool:
    return value.strip() in empties


def _check_evidence(doc, ctx, rownum, line, tier, href) -> Finding | None:
    if href is None:
        return _err(doc, line, "VT004", f"row {rownum}: no evidence link")
    if tier == "http":
        if not href.lower().startswith(("http://", "https://")):
            return _err(doc, line, "VT004", f"row {rownum}: evidence must be an http(s) link at this level, got '{href}'")
        return None
    # repo-file tier: a real file under an evidence/ dir in the blueprint's
    # folder or an ancestor up to the repo root, never the blueprint.
    if is_external(href):
        return _err(doc, line, "VT004", f"row {rownum}: evidence must be a relative link to a repository file, got '{href}'")
    rel = href_path(href)
    if not rel:
        return _err(doc, line, "VT004", f"row {rownum}: evidence link '{href}' has no file path")
    target, inside = resolve(doc, rel, ctx.repo_root)
    if not inside:
        return _err(doc, line, "VT004", f"row {rownum}: evidence link '{href}' resolves outside the repository")
    root = Path(ctx.repo_root).resolve()
    doc_path = Path(doc.abs_path).resolve() if doc.abs_path is not None else None
    if doc_path is not None and target == doc_path:
        return _err(doc, line, "VT004", f"row {rownum}: evidence cannot be the blueprint itself")
    if not target.is_file():
        return _err(doc, line, "VT004", f"row {rownum}: evidence file '{href}' does not exist")
    names = [str(n) for n in (ctx.vt_spec.get("evidence_dirs") or [])] or ["evidence"]
    folder = doc_path.parent if doc_path is not None else root
    ancestors = [folder] + [p for p in folder.parents if p == root or root in p.parents]
    if not any((a / n) in target.parents for a in ancestors for n in names):
        return _err(
            doc,
            line,
            "VT004",
            f"row {rownum}: evidence '{href}' must live under an evidence/ directory "
            f"in the blueprint's folder or a parent folder (see framework/definitions.md)",
        )
    return None


def check(doc, ctx) -> list[Finding]:
    btype = structure_type(doc, ctx)
    if btype is None:
        return []
    spec = ctx.vt_spec
    order: list[str] = list(ctx.enums.get("e_level") or [])
    section_title = ctx.budgets["types"][btype].get("validation_section")
    sec = doc.section(section_title) if section_title else None
    if sec is None or not sec.tables:
        line = sec.line if sec is not None else 1
        return [_err(doc, line, "VT001", f"no validation table in section '{section_title}'")]

    table = sec.tables[0]
    columns = list(spec["columns"])
    if table.header != columns:
        missing = [c for c in columns if c not in table.header]
        detail = f"missing {missing}" if missing else "columns differ or are out of order"
        return [_err(doc, table.line, "VT002", f"validation table header differs from canonical ({detail})")]

    pattern = re.compile(spec["e_level_pattern"])
    empties = set(spec.get("empty_cell_values") or [])
    tiers = spec.get("evidence_tiers") or {}
    rev_from = spec.get("revision_required_from")
    rev_idx = order.index(rev_from) if rev_from in order else None
    raising = spec.get("raising_column")
    lb_col, e_col, ev_col, rev_col = "Load-bearing", "E-level", "Evidence", "Release / revision"
    # Fail closed: a missing or empty spec key still enforces yes/no.
    lb_allowed = [str(v).strip().lower() for v in (spec.get("load_bearing_values") or [])] or ["yes", "no"]
    lb_list = ", ".join(lb_allowed)
    ev_pos = columns.index(ev_col)

    out: list[Finding] = []
    load_bearing: list[str] = []
    for r in table.rows:
        cells = dict(zip(columns, r.cells + [""] * (len(columns) - len(r.cells))))
        rownum = cells.get("#", "").strip() or str(r.line)
        # VT007: Load-bearing must be an allowed value; unknown values count
        # toward the minimum (fail closed).
        lb_raw = cells[lb_col]
        lb = lb_raw.strip().lower()
        if lb not in lb_allowed:
            out.append(
                _err(doc, r.line, "VT007", f"row {rownum}: Load-bearing must be one of [{lb_list}], got '{lb_raw.strip()}'")
            )
            counts = True
        else:
            counts = lb == "yes"

        parsed = _parse_level(cells[e_col], pattern, order)
        if parsed is None:
            out.append(_err(doc, r.line, "VT003", f"row {rownum}: invalid E-level cell '{cells[e_col].strip()}'"))
            if counts and order:
                load_bearing.append(order[0])
            continue
        level, evaluated = parsed
        idx = order.index(level)
        if counts:
            load_bearing.append(level)

        # VT004: each E-level needs its evidence tier
        tier = tiers.get(EVALUATED if evaluated else level)
        if tier is not None:
            hrefs = r.hrefs[ev_pos] if ev_pos < len(r.hrefs) else []
            f = _check_evidence(doc, ctx, rownum, r.line, tier, hrefs[0] if hrefs else None)
            if f is not None:
                out.append(f)

        # VT005: revision required from E2
        if rev_idx is not None and idx >= rev_idx and _is_empty(cells[rev_col], empties):
            out.append(_err(doc, r.line, "VT005", f"row {rownum}: {level} row needs a Release / revision"))

        # VT006: only the raising column can lift E above the lowest level.
        # Context columns (spec "context_columns") are documentation only.
        if raising and idx > 0 and _is_empty(cells.get(raising, ""), empties):
            out.append(
                _err(
                    doc,
                    r.line,
                    "VT006",
                    f"row {rownum}: E-level {level} needs a non-empty '{raising}' cell; "
                    f"only that column can raise E above {order[0]}",
                )
            )

    # VT003: headline E = min over load-bearing rows
    if not load_bearing:
        out.append(_err(doc, table.line, "VT003", "no load-bearing rows; cannot compute the headline E-level"))
    else:
        headline = min(load_bearing, key=order.index)
        fm_level = doc.front_matter.get("evidence_level")
        if fm_level in order and fm_level != headline:
            out.append(
                _err(
                    doc,
                    table.line,
                    "VT003",
                    f"headline E-level is {headline} (min over load-bearing rows) but front matter says {fm_level}",
                )
            )
    return out
