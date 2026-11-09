"""CR001, CR002: a doc marked done must record a dated clarity review.

CR001: `doc_status: done` without `clarity_reviewed` is an
error, so CI blocks it. The project writing rule: no document is done until it
passes a clarity review. Drafts and docs in review are not flagged.

CR002: on non-blueprint docs, `clarity_reviewed` must be an ISO date
(YYYY-MM-DD). Blueprints skip CR002 because their schemas already validate the
field (FM002). NoDatesLoader keeps unquoted dates as strings, so an unquoted
valid date passes, matching the schema behavior.
"""

from __future__ import annotations

import re
from datetime import date

from ..report import Finding

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _line(doc, key: str) -> int:
    for i, ln in enumerate(doc.fm_lines):
        if ln.startswith(f"{key}:"):
            return i + 2  # line 1 is the opening ---
    return 1


def _is_iso_date(value) -> bool:
    if not isinstance(value, str) or not _ISO_DATE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def check(doc, ctx) -> list[Finding]:
    fm = doc.front_matter
    if not isinstance(fm, dict):
        return []
    out = []
    if fm.get("doc_status") == "done" and not fm.get("clarity_reviewed"):
        out.append(
            Finding(
                doc.path,
                _line(doc, "doc_status"),
                1,
                "error",
                "CR001",
                "doc_status is 'done' but clarity_reviewed is not set",
            )
        )
    if not doc.is_blueprint and "clarity_reviewed" in fm:
        value = fm["clarity_reviewed"]
        if value is not None and not _is_iso_date(value):
            out.append(
                Finding(
                    doc.path,
                    _line(doc, "clarity_reviewed"),
                    1,
                    "error",
                    "CR002",
                    f"clarity_reviewed must be a quoted ISO date (YYYY-MM-DD), got '{value}'",
                )
            )
    return out
