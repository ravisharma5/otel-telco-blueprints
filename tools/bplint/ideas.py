"""The idea rule, shared by bplint and the site generators.

A leaf module with no imports from the repository, so any tool can import it at the
top level without an import cycle.
"""

from __future__ import annotations

# Exploration ideas live in catalog/<IDEAS_DIR>/<slug>/ and keep their real domain.
IDEAS_DIR = "ideas"


def is_idea(fm: dict) -> bool:
    """True when the page carries the idea object; every tool uses this one rule."""
    return isinstance(fm.get("idea"), dict)
