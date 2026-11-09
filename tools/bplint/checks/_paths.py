"""Relative-path resolution with repository containment.

Hrefs are percent-decoded. A leading "/" means root-relative: the path resolves
against the repository root, not the filesystem root. Everything else
resolves against the doc's folder. Containment is judged on the fully resolved
path, so symlinks and ".." cannot escape.

Targets are resolved and stat'ed only. Paths outside the repository root are
reported by the caller and never read.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


def is_external(href: str) -> bool:
    """True for hrefs with a URL scheme (http:, https:, mailto:, ...) or protocol-relative."""
    return bool(_SCHEME.match(href)) or href.startswith("//")


def href_path(href: str) -> str:
    """The path part of an href: drop "#fragment", then "?query"."""
    return href.split("#", 1)[0].split("?", 1)[0]


def resolve(doc, rel: str, repo_root: Path) -> tuple[Path, bool]:
    """Return (resolved target, inside_repo) for a path written in the doc."""
    root = Path(repo_root).resolve()
    path = unquote(rel)
    if path.startswith("/"):
        target = (root / path.lstrip("/")).resolve()
    else:
        base = Path(doc.abs_path).parent if doc.abs_path else root
        target = (base / path).resolve()
    return target, (target == root or root in target.parents)
