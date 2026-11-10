"""VT001, VT002, VT004, VT007: the canonical Sources table.

Blueprints are recipes, so every key claim names its basis and links its
source. Column names and allowed Basis values come from
schemas/sources-table.yaml; the section that holds the table comes from the
budgets `sources_section` key.

Source paths are only resolved and stat'ed, never read or printed beyond the
href the author wrote.
"""

from __future__ import annotations

from pathlib import Path

from ..report import Finding
from . import structure_type
from ._paths import href_path, is_external, resolve

# Fail closed: a spec without basis_values still enforces these terms.
DEFAULT_BASIS = (
    "model card",
    "research",
    "Red Hat guidance",
    "industry use case",
    "project documentation",
)


def _err(doc, line, code, msg) -> Finding:
    return Finding(doc.path, line, 1, "error", code, msg)


def _check_source(doc, ctx, rownum, line, href) -> Finding | None:
    """VT004: an http(s) URL, or a relative link to an existing repo file that is not the page."""
    if href is None:
        return _err(doc, line, "VT004", f"row {rownum}: no Source link")
    if is_external(href):
        if href.lower().startswith(("http://", "https://")):
            return None
        return _err(doc, line, "VT004", f"row {rownum}: Source must be an http(s) URL or a repository file, got '{href}'")
    rel = href_path(href)
    if not rel:
        return _err(doc, line, "VT004", f"row {rownum}: Source link '{href}' has no file path")
    target, inside = resolve(doc, rel, ctx.repo_root)
    if not inside:
        return _err(doc, line, "VT004", f"row {rownum}: Source link '{href}' resolves outside the repository")
    doc_path = Path(doc.abs_path).resolve() if doc.abs_path is not None else None
    if doc_path is not None and target == doc_path:
        return _err(doc, line, "VT004", f"row {rownum}: Source cannot be the page itself")
    if not target.is_file():
        return _err(doc, line, "VT004", f"row {rownum}: Source file '{href}' does not exist")
    return None


def check(doc, ctx) -> list[Finding]:
    btype = structure_type(doc, ctx)
    if btype is None:
        return []
    spec = ctx.sources_spec
    section_title = ctx.budgets["types"][btype].get("sources_section")
    if not section_title:
        return []  # types without a Sources table (reference pages)
    sec = doc.section(section_title)
    if sec is None or not sec.tables:
        line = sec.line if sec is not None else 1
        return [_err(doc, line, "VT001", f"no Sources table in section '{section_title}'")]

    table = sec.tables[0]
    columns = list(spec["columns"])
    if table.header != columns:
        missing = [c for c in columns if c not in table.header]
        detail = f"missing {missing}" if missing else "columns differ or are out of order"
        return [_err(doc, table.line, "VT002", f"Sources table header differs from canonical ({detail})")]

    allowed = [str(v).strip() for v in (spec.get("basis_values") or [])] or list(DEFAULT_BASIS)
    allowed_lower = {v.lower() for v in allowed}
    allowed_list = ", ".join(allowed)
    src_pos = columns.index("Source")

    out: list[Finding] = []
    for r in table.rows:
        cells = dict(zip(columns, r.cells + [""] * (len(columns) - len(r.cells))))
        rownum = cells.get("#", "").strip() or str(r.line)
        basis = cells["Basis"].strip()
        if basis.lower() not in allowed_lower:
            out.append(_err(doc, r.line, "VT007", f"row {rownum}: Basis must be one of [{allowed_list}], got '{basis}'"))
        hrefs = r.hrefs[src_pos] if src_pos < len(r.hrefs) else []
        f = _check_source(doc, ctx, rownum, r.line, hrefs[0] if hrefs else None)
        if f is not None:
            out.append(f)
    return out
