"""LK001, LK002: internal link targets and anchors.

External links (any URL scheme) are skipped. Relative targets must resolve
inside the repository root; targets outside it are reported and never read.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote

from ..markdown import parse_doc
from ..report import Finding
from ..slug import heading_slugs
from ._paths import is_external, resolve

_MD_SUFFIXES = {".md", ".markdown"}
_SLUG_CACHE: dict[Path, set[str]] = {}


def doc_slugs(doc) -> set[str]:
    """Anchor slugs for every heading in a parsed doc (any level, document order)."""
    return heading_slugs([t for s in doc.sections for t in s.headings])


def _target_slugs(path: Path) -> set[str]:
    cached = _SLUG_CACHE.get(path)
    if cached is None:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        cached = doc_slugs(parse_doc(path, text))
        _SLUG_CACHE[path] = cached
    return cached


def _err(doc, line, code, msg) -> Finding:
    return Finding(doc.path, line, 1, "error", code, msg)


def check(doc, ctx) -> list[Finding]:
    out: list[Finding] = []
    own_slugs = None
    for section in doc.sections:
        for href, line in section.links:
            if not href or is_external(href):
                continue
            path_part, _, fragment = href.partition("#")
            fragment = unquote(fragment)
            if not path_part:
                if not fragment:
                    continue
                if own_slugs is None:
                    own_slugs = doc_slugs(doc)
                if fragment not in own_slugs:
                    out.append(_err(doc, line, "LK002", f"anchor '#{fragment}' not found in this file"))
                continue
            target, inside = resolve(doc, path_part, ctx.repo_root)
            if not inside:
                out.append(_err(doc, line, "LK001", f"link target outside repository: {path_part}"))
            elif not target.exists():
                out.append(_err(doc, line, "LK001", f"link target not found: {path_part}"))
            elif fragment and target.is_file() and target.suffix.lower() in _MD_SUFFIXES:
                if fragment not in _target_slugs(target):
                    out.append(
                        _err(doc, line, "LK002", f"anchor '#{fragment}' not found in {path_part}")
                    )
    return out
