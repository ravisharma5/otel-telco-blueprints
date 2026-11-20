"""Merge the explorer build into the docs site, write legacy redirects, check links.

`make site` builds MkDocs into site/ and the explorer into explorer/dist/, then runs
this step, which does four things in order:

1. merge: copy every file from explorer/dist into site/. A file that exists in both
   builds with different bytes stops the run. MkDocs owns the only 404 page, so an
   explorer/dist/404.html stops the run even if the bytes match.
2. write_redirects: for every path in tools/site/legacy-urls.txt (the frozen list of
   URLs published under catalog/ before recipes moved to recipes/), write a short
   redirect page to the matching recipes/ URL. Targets come only from that list and
   titles only from the recipe front matter; nothing is read from a URL or query.
3. write_moves: for every "old new" pair in tools/site/moved-urls.txt (the frozen list
   of use-case URLs moved by the catalog focus change), write a redirect page at the
   old path. Both paths are strict lowercase site-relative paths; only the new one may
   carry a single #fragment, and the target page (and its anchor, if any) must exist
   in the built site.
4. check_links: parse every HTML file in site/ and report any internal href or src
   (relative, or under the site base path) that resolves to no file.

The proposal PDF (built by tools/site/build_pdf.py before this step) is the one
optional target: it is built only with REQUIRE_PDF=1 (set in the Pages workflow), so
without it a missing PDF's link is not reported.

Usage:
    python -m tools.site.merge_site
"""

from __future__ import annotations

import html
import os
import posixpath
import re
import shutil
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "explorer/dist"
SITE = ROOT / "site"
LEGACY = ROOT / "tools/site/legacy-urls.txt"
MOVED = ROOT / "tools/site/moved-urls.txt"
MKDOCS_CONFIG = ROOT / "mkdocs.yml"
BASE_PATH = "/otel-telco-blueprints/"
OLD_PREFIX = "catalog/"
NEW_PREFIX = "recipes/"
# A legacy entry: catalog/ plus lowercase path segments, each ending in a slash.
LEGACY_ENTRY = re.compile(r"^catalog/(?:[a-z0-9][a-z0-9-]*/)*$")
# A moved pair: lowercase site-relative segments ending in a slash; only the new
# path may add one #fragment. No scheme, query, leading slash, or dot segment.
MOVED_OLD = re.compile(r"^[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)*/$")
MOVED_NEW = re.compile(r"^[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)*/(?:#[a-z0-9-]+)?$")
# Built by tools/site/build_pdf.py; may be skipped locally when Pango is missing.
PROPOSAL_PDF = "proposal/otel-telco-blueprints-proposal.pdf"
SKIP_SCHEMES = ("http:", "https:", "mailto:", "tel:", "data:", "javascript:")

REDIRECT = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved: {title}</title>
<link rel="canonical" href="{canonical}">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0; url={rel}">
<script>location.replace("{rel}" + location.hash)</script>
</head>
<body>
<p>This page moved to <a href="{rel}">{title}</a>.</p>
</body>
</html>
"""

# A fragment target already names its anchor, so the script must not add location.hash.
REDIRECT_FRAGMENT = REDIRECT.replace('location.replace("{rel}" + location.hash)', 'location.replace("{rel}")')


# ---------- merge ----------


def merge(dist: Path, site: Path) -> None:
    """Copy every file in dist into site; stop on a collision or an explorer 404 page."""
    if not dist.is_dir():
        raise SystemExit(f"merge: {dist} is missing; build the explorer first")
    if (dist / "404.html").exists():
        raise SystemExit(
            "merge: explorer/dist/404.html found; MkDocs owns the 404 page, "
            "remove src/pages/404.astro"
        )
    files = sorted(p for p in dist.rglob("*") if p.is_file())
    for src in files:
        rel = src.relative_to(dist)
        dest = site / rel
        if dest.exists() and (not dest.is_file() or dest.read_bytes() != src.read_bytes()):
            raise SystemExit(f"merge: {rel.as_posix()} exists in both builds")
    for src in files:
        dest = site / src.relative_to(dist)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


# ---------- redirects ----------


def read_legacy(path: Path) -> list[str]:
    """Return the legacy paths in the frozen list (comments and blank lines skipped)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def _display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _front_matter_title(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise SystemExit(f"redirect: {_display(path)} has no front matter")
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^title:\s*(.+?)\s*$", line)
        if m:
            value = m.group(1)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            return value
    raise SystemExit(f"redirect: {_display(path)} has no title")


def _title_for(entry: str) -> str:
    """Title from the recipe source that the legacy path was built from."""
    sub = entry[len(OLD_PREFIX) :]
    candidates = [ROOT / "catalog" / sub / name for name in ("README.md", "index.md")]
    candidates.append(ROOT / "site-src/catalog" / sub / "index.md")
    for path in candidates:
        if path.is_file():
            return _front_matter_title(path)
    raise SystemExit(f"redirect: no source page for {entry}")


def write_redirects(site: Path, legacy_list: list[str], site_url: str) -> None:
    """Write a redirect stub at site/<entry>/index.html for every legacy entry."""
    if not site_url.endswith("/"):
        site_url += "/"
    for entry in legacy_list:
        if not LEGACY_ENTRY.fullmatch(entry):
            raise SystemExit(f"redirect: bad legacy entry {entry!r}")
        target = NEW_PREFIX + entry[len(OLD_PREFIX) :]
        if not (site / target / "index.html").is_file():
            raise SystemExit(f"redirect: target {target} for {entry} is missing")
        page = site / entry / "index.html"
        if page.exists():
            raise SystemExit(f"redirect: {entry} is still built; it must only redirect")
        rel = "../" * entry.count("/") + target
        title = html.escape(_title_for(entry), quote=True)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(
            REDIRECT.format(title=title, canonical=site_url + target, rel=rel),
            encoding="utf-8",
        )


def read_moves(path: Path) -> list[tuple[str, str]]:
    """Return the (old, new) pairs in the frozen moved list (comments and blanks skipped)."""
    pairs = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        fields = text.split()
        if len(fields) != 2:
            raise SystemExit(f"redirect: {_display(path)} line {n}: want 'old new', got {text!r}")
        pairs.append((fields[0], fields[1]))
    return pairs


def _moved_title(target: str, root: Path = ROOT) -> str:
    """Title from the source page the moved target is built from."""
    page = target.split("#", 1)[0]
    parts = page.rstrip("/").split("/")
    source = None
    if parts[0] == NEW_PREFIX.rstrip("/") and len(parts) == 3:
        source = root / "catalog" / parts[1] / parts[2] / "README.md"
    elif parts[0] == "platform" and len(parts) == 2:
        source = root / "platform" / parts[1] / "README.md"
    if source is None or not source.is_file():
        raise SystemExit(f"redirect: no source page for {target}")
    return _front_matter_title(source)


def write_moves(site: Path, pairs: list[tuple[str, str]], site_url: str, root: Path = ROOT) -> None:
    """Write a redirect stub at site/<old>/index.html for every moved pair."""
    if not site_url.endswith("/"):
        site_url += "/"
    for old, new in pairs:
        if not MOVED_OLD.fullmatch(old):
            raise SystemExit(f"redirect: bad moved path {old!r}")
        if not MOVED_NEW.fullmatch(new):
            raise SystemExit(f"redirect: bad moved target {new!r} for {old}")
        page_path = new.split("#", 1)[0]
        target_html = site / page_path / "index.html"
        if not target_html.is_file():
            raise SystemExit(f"redirect: target {page_path} for {old} is missing")
        if "#" in new:
            frag = new.split("#", 1)[1]
            anchor = re.compile(r"""\bid\s*=\s*["']""" + re.escape(frag) + r"""["']""")
            if not anchor.search(target_html.read_text(encoding="utf-8")):
                raise SystemExit(f"redirect: anchor #{frag} missing in {page_path} for {old}")
        page = site / old / "index.html"
        if page.exists():
            raise SystemExit(f"redirect: {old} is still built; it must only redirect")
        rel = "../" * old.count("/") + new
        title = html.escape(_moved_title(new, root), quote=True)
        template = REDIRECT_FRAGMENT if "#" in new else REDIRECT
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(template.format(title=title, canonical=site_url + new, rel=rel), encoding="utf-8")


# ---------- link check ----------


class _Refs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs: list[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.refs.append(value)


def _resolve(site: Path, page: Path, ref: str) -> Path | None:
    """File a reference points to, or None when it is external or fragment-only."""
    ref = ref.strip()
    if not ref or ref.startswith("#") or ref.startswith("//"):
        return None
    if ref.lower().startswith(SKIP_SCHEMES):
        return None
    path = unquote(urlsplit(ref).path)
    if not path:
        return None
    if path.startswith("/"):
        if not (path + "/").startswith(BASE_PATH):
            return site / "__outside_base__" / path.lstrip("/")
        joined = path[len(BASE_PATH) :] if len(path) >= len(BASE_PATH) else ""
    else:
        here = page.parent.relative_to(site).as_posix()
        joined = posixpath.join(here, path)
    norm = posixpath.normpath(joined) if joined else "."
    if norm == ".." or norm.startswith("../"):
        return site / "__outside_site__" / norm
    target = site if norm == "." else site / norm
    if target.is_dir() or path.endswith("/"):
        target = target / "index.html"
    return target


def check_links(site: Path, optional: frozenset[str] = frozenset()) -> list[str]:
    """Return 'page: ref' for every internal href or src that resolves to no file.

    optional holds site-relative paths whose absence is not reported.
    """
    broken = []
    for page in sorted(site.rglob("*.html")):
        parser = _Refs()
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        for ref in parser.refs:
            target = _resolve(site, page, ref)
            if target is None or target.is_file():
                continue
            try:
                rel = target.relative_to(site).as_posix()
            except ValueError:
                rel = None
            if rel in optional:
                continue
            broken.append(f"{page.relative_to(site).as_posix()}: {ref}")
    return broken


def optional_targets(site: Path) -> frozenset[str]:
    """The proposal PDF is optional only when it is missing and REQUIRE_PDF is not 1."""
    if (site / PROPOSAL_PDF).is_file() or os.environ.get("REQUIRE_PDF") == "1":
        return frozenset()
    print(f"links: {PROPOSAL_PDF} not built (REQUIRE_PDF is not 1); its link is not checked")
    return frozenset({PROPOSAL_PDF})


# ---------- CLI ----------


def _site_url() -> str:
    m = re.search(r"(?m)^site_url:\s*(\S+)\s*$", MKDOCS_CONFIG.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("merge: site_url missing from mkdocs.yml")
    return m.group(1)


def main() -> int:
    if not SITE.is_dir():
        raise SystemExit("merge: site/ is missing; build the docs first")
    merge(DIST, SITE)
    write_redirects(SITE, read_legacy(LEGACY), _site_url())
    write_moves(SITE, read_moves(MOVED), _site_url())
    broken = check_links(SITE, optional_targets(SITE))
    if broken:
        print(f"links: {len(broken)} internal link(s) resolve to no file:", file=sys.stderr)
        for item in broken:
            print(f"  {item}", file=sys.stderr)
        return 1
    print("merge: explorer merged, legacy and moved redirects written, links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
