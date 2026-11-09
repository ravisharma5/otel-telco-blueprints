"""GitHub heading anchor slugs (assumed to match github-slugger behaviour)."""

from __future__ import annotations

import re

_STRIP = re.compile(r"[^\w\- ]", re.UNICODE)


def github_slug(text: str) -> str:
    """Lowercase, drop characters other than letters, digits, spaces, `-`, `_`; spaces to `-`."""
    return _STRIP.sub("", text.strip().lower()).replace(" ", "-")


def heading_slugs(titles) -> set[str]:
    """Slugs for a document's headings, with `-1`, `-2` suffixes on duplicates."""
    seen: dict[str, int] = {}
    out: set[str] = set()
    for title in titles:
        base = github_slug(title)
        slug = base
        n = seen.get(base, 0)
        while slug in out:
            n += 1
            slug = f"{base}-{n}"
        seen[base] = n
        out.add(slug)
    return out
