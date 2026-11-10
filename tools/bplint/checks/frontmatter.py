"""FM001, FM002, RF001: front matter presence, type binding, and schema validity."""

from __future__ import annotations

import re

from ..report import Finding

_REQUIRED = re.compile(r"^'([^']+)' is a required property")
_QUOTED = re.compile(r"'([^']+)'")


def _key_line(doc, key) -> int:
    """File line of `key:` in the front matter block, else 1."""
    if key:
        pat = re.compile(rf"^{re.escape(str(key))}\s*:")
        for i, ln in enumerate(doc.fm_lines):
            if pat.match(ln):
                return i + 2  # line 1 is the opening ---
    return 1


def _error_key(err) -> str | None:
    if err.absolute_path:
        return str(err.absolute_path[0])
    if err.validator == "required":
        m = _REQUIRED.match(err.message)
        return m.group(1) if m else None
    return None


def _json_path(err, key) -> str:
    parts = [str(p) for p in err.absolute_path]
    if not parts and key:
        parts = [key]
    return "$" + "".join(f"[{p}]" if p.isdigit() else f".{p}" for p in parts)


def check_type_binding(doc, ctx) -> list[Finding]:
    """FM002 when the page's `type` is not one its glob group accepts.

    Runs on blueprints and plain docs alike, before check(). On a finding it
    flags the doc so check() and the structural checks skip it.
    """
    allowed = doc.allowed_types
    fm = doc.front_matter
    if allowed is None or not isinstance(fm, dict):
        return []
    btype = fm.get("type")
    if btype is None or btype in allowed:
        return []  # a missing blueprint type is reported by check() below
    if allowed:
        expected = ", ".join(f"'{t}'" for t in allowed)
        text = f"$.type: '{btype}' is not allowed here; expected one of {expected}"
    else:
        text = f"$.type: '{btype}' is not allowed here; pages in this folder must not declare a type"
    doc.flags.update({"skip_structure", "type_not_allowed"})
    return [Finding(doc.path, _key_line(doc, "type"), 1, "error", "FM002", text)]


def check(doc, ctx) -> list[Finding]:
    if not doc.is_blueprint or "type_not_allowed" in doc.flags:
        return []
    fm = doc.front_matter
    if doc.fm_error is not None or fm is None or not isinstance(fm, dict):
        doc.flags.add("fm001")
        if doc.fm_error is not None:
            line, msg = doc.fm_error
            text = f"front matter does not parse: {msg}"
        elif fm is None:
            line, text = 1, "blueprint has no YAML front matter block"
        else:
            line, text = 1, "front matter must be a YAML mapping"
        return [Finding(doc.path, line, 1, "error", "FM001", text)]

    btype = fm.get("type")
    validator = ctx.schemas.get(btype) if isinstance(btype, str) else None
    if validator is None:
        doc.flags.add("skip_structure")
        what = "missing" if btype is None else f"unknown ('{btype}')"
        known = ", ".join(f"'{k}'" for k in (doc.allowed_types or sorted(ctx.schemas)))
        return [
            Finding(
                doc.path,
                _key_line(doc, "type"),
                1,
                "error",
                "FM002",
                f"$.type: blueprint type is {what}; expected one of {known}",
            )
        ]

    facets = set(ctx.config.get("facet_fields") or [])
    out = []
    for err in sorted(validator.iter_errors(fm), key=lambda e: (list(map(str, e.absolute_path)), e.message)):
        key = _error_key(err)
        code = "RF001" if key in facets else "FM002"
        line_key = key
        if err.validator == "additionalProperties":
            extras = _QUOTED.findall(err.message)
            line_key = extras[-1] if extras else None
        out.append(
            Finding(
                doc.path,
                _key_line(doc, line_key),
                1,
                "error",
                code,
                f"{_json_path(err, key)}: {err.message}",
            )
        )
    return out
