"""DG001: every relative image must exist inside the repository."""

from __future__ import annotations

from ..report import Finding
from ._paths import is_external, resolve


def check(doc, ctx) -> list[Finding]:
    out: list[Finding] = []
    for section in doc.sections:
        for src, line in section.images:
            if not src or is_external(src):
                continue
            path_part = src.split("#", 1)[0].split("?", 1)[0]
            if not path_part:
                continue
            target, inside = resolve(doc, path_part, ctx.repo_root)
            if not inside:
                msg = f"diagram outside repository: {path_part}"
            elif not target.is_file():
                msg = f"diagram file not found: {path_part}"
            else:
                continue
            out.append(Finding(doc.path, line, 1, "error", "DG001", msg))
    return out
