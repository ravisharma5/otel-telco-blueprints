"""ID001, XR001: repo-level id uniqueness and platform cross-references.

ID001 runs on every invocation. XR001 runs only on discovery runs
(ctx.discovery): an explicit-path run lints a subset, so a platform missing
from that subset is not evidence of a dangling reference.
"""

from __future__ import annotations

from ..report import Finding
from .frontmatter import _key_line


def _blueprints(ctx):
    """Blueprint docs with usable front matter, in path order."""
    out = []
    for doc in sorted(ctx.docs, key=lambda d: str(d.path)):
        if not doc.is_blueprint or doc.fm_error is not None or "fm001" in doc.flags:
            continue
        if isinstance(doc.front_matter, dict):
            out.append(doc)
    return out


def check_ids(ctx) -> list[Finding]:
    first: dict[str, object] = {}
    out = []
    for doc in _blueprints(ctx):
        bid = doc.front_matter.get("id")
        if not isinstance(bid, str):
            continue
        if bid in first:
            out.append(
                Finding(
                    doc.path,
                    _key_line(doc, "id"),
                    1,
                    "error",
                    "ID001",
                    f"duplicate id '{bid}' (first used in {first[bid].path})",
                )
            )
        else:
            first[bid] = doc
    return out


def check_refs(ctx) -> list[Finding]:
    if not getattr(ctx, "discovery", False):
        return []
    docs = _blueprints(ctx)
    platform_ids = {
        d.front_matter.get("id")
        for d in docs
        if d.front_matter.get("type") == "platform" and isinstance(d.front_matter.get("id"), str)
    }
    out = []
    for doc in docs:
        fm = doc.front_matter
        if fm.get("type") != "use-case":
            continue
        refs = fm.get("platform_blueprints")
        if not isinstance(refs, list):
            continue
        for ref in refs:
            if isinstance(ref, str) and ref not in platform_ids:
                out.append(
                    Finding(
                        doc.path,
                        _key_line(doc, "platform_blueprints"),
                        1,
                        "error",
                        "XR001",
                        f"platform_blueprints entry '{ref}' has no matching platform blueprint",
                    )
                )
    return out
