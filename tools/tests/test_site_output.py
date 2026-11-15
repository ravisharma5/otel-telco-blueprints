"""Built-output tests for the combined site (run after `make site`).

`make site` builds MkDocs into site/, builds the explorer into explorer/dist/, and
merges the two. These tests check the merged result: one MkDocs 404 page, a redirect
stub for every frozen legacy catalog URL, the explorer as the home page with the old
Start here routes, disjoint build outputs, and no broken internal link.
"""

from __future__ import annotations

import posixpath
import re
from html.parser import HTMLParser

import pytest

from tools.site import merge_site
from tools.tests.conftest import REPO_ROOT

pytestmark = pytest.mark.site_output

LEGACY_PATH = REPO_ROOT / "tools/site/legacy-urls.txt"
REFRESH = re.compile(r'<meta http-equiv="refresh" content="0; url=([^"]+)">')
# Top-level entries MkDocs writes; the explorer must never write any of them.
MKDOCS_OWNED = {
    "404.html", "assets", "search", "sitemap.xml", "sitemap.xml.gz", "recipes", "platform",
    "framework", "architecture", "templates", "brand", "catalog",
}
REDIRECT_MAX_BYTES = 4096


def _anchors(html):
    """Return [(href, text)] for every <a>, text joined from its contents."""
    out, stack = [], []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "a":
                stack.append([dict(attrs).get("href"), []])

        def handle_data(self, data):
            for item in stack:
                item[1].append(data)

        def handle_endtag(self, tag):
            if tag == "a" and stack:
                href, parts = stack.pop()
                out.append((href, " ".join(" ".join(parts).split())))

    P().feed(html)
    return out


def test_single_mkdocs_404(site_dir, explorer_dist):
    assert not (explorer_dist / "404.html").exists()
    assert not (REPO_ROOT / "explorer/src/pages/404.astro").exists()
    page = site_dir / "404.html"
    assert page.is_file()
    html = page.read_text(encoding="utf-8")
    assert '<meta name="generator" content="mkdocs-' in html
    roots = {"/otel-telco-blueprints/", "/otel-telco-blueprints/."}
    assert any(href in roots for href, _ in _anchors(html)), "404 page has no link to the site root"


def test_every_legacy_url_redirects(site_dir):
    entries = merge_site.read_legacy(LEGACY_PATH)
    assert entries
    for path in entries:
        page = site_dir / path / "index.html"
        assert page.is_file(), f"no redirect for {path}"
        data = page.read_bytes()
        assert len(data) < REDIRECT_MAX_BYTES, f"{path} is not a short stub"
        html = data.decode("utf-8")
        assert "md-content" not in html, f"{path} still carries a recipe body"
        assert '<meta name="robots" content="noindex">' in html
        assert "location.hash" in html
        m = REFRESH.search(html)
        assert m, f"{path} has no meta refresh"
        target = posixpath.normpath(posixpath.join(path, m.group(1)))
        assert target.startswith("recipes"), target
        assert (site_dir / target / "index.html").is_file(), f"{path} -> {target} missing"


def test_no_stale_catalog_pages(site_dir):
    legacy = set(merge_site.read_legacy(LEGACY_PATH))
    built = {
        p.parent.relative_to(site_dir).as_posix() + "/"
        for p in (site_dir / "catalog").rglob("index.html")
    }
    assert built == legacy
    others = [p for p in (site_dir / "catalog").rglob("*") if p.is_file() and p.name != "index.html"]
    assert others == []


def test_old_home_is_explorer(site_dir):
    html = (site_dir / "index.html").read_text(encoding="utf-8")
    assert "Run telecom AI use cases in production" in html
    assert '<meta name="generator" content="mkdocs-' not in html
    links = _anchors(html)
    for label, path in (
        ("Readiness questions", "framework/"),
        ("Architecture overview", "architecture/"),
        ("Platform blueprints", "platform/"),
        ("All recipes", "recipes/"),
    ):
        assert any(
            text.startswith(label) and href == f"/otel-telco-blueprints/{path}" for href, text in links
        ), label


def test_internal_links_resolve(site_dir):
    assert merge_site.check_links(site_dir) == []


def test_build_paths_disjoint(explorer_dist):
    explorer_top = {p.name for p in explorer_dist.iterdir()}
    assert explorer_top & MKDOCS_OWNED == set()
    assert {"index.html", "use-cases", "_astro"} <= explorer_top


# Resource-loading tags and the attribute that names the resource. <a href> is a
# link, not a load, so links to other sites stay allowed.
_LOADS = {"script": "src", "img": "src", "source": "src", "iframe": "src", "link": "href"}
_LINK_LOAD_RELS = {"stylesheet", "preload", "icon", "modulepreload", "preconnect", "dns-prefetch"}
_CSS_REMOTE = re.compile(r"""(?:url\(\s*['"]?|@import\s+['"])\s*(?:https?:)?//""", re.I)


def _remote_loads(html):
    found = []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag not in _LOADS:
                return
            a = dict(attrs)
            if tag == "link":
                rels = set((a.get("rel") or "").lower().split())
                if not rels & _LINK_LOAD_RELS:
                    return
            value = a.get(_LOADS[tag]) or ""
            if re.match(r"(?:https?:)?//", value.strip(), re.I):
                found.append(f"<{tag}> {value}")
            for candidate in (a.get("srcset") or "").split(","):
                if re.match(r"\s*(?:https?:)?//", candidate, re.I):
                    found.append(f"<{tag} srcset> {candidate.strip()}")

    P().feed(html)
    return found


def test_no_third_party_resources(site_dir):
    bad = []
    for page in site_dir.rglob("*.html"):
        for hit in _remote_loads(page.read_text(encoding="utf-8")):
            bad.append(f"{page.relative_to(site_dir)}: {hit}")
    for sheet in site_dir.rglob("*.css"):
        text = sheet.read_text(encoding="utf-8", errors="replace")
        for m in _CSS_REMOTE.finditer(text):
            bad.append(f"{sheet.relative_to(site_dir)}: {text[m.start():m.start() + 80]}")
    assert not bad, "\n".join(bad[:20])


def test_no_google_fonts_or_unpkg_in_html(site_dir):
    bad = []
    for page in site_dir.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for host in ("fonts.googleapis.com", "fonts.gstatic.com", "unpkg.com"):
            if host in text:
                bad.append(f"{page.relative_to(site_dir)}: {host}")
    assert not bad, "\n".join(bad[:20])


def test_no_repo_stats_widget(site_dir):
    # Material's repo widget (data-md-component="source") fetches api.github.com
    # from the browser; the GitHub link must stay a plain link.
    bad = [
        str(page.relative_to(site_dir))
        for page in site_dir.rglob("*.html")
        if 'data-md-component="source"' in page.read_text(encoding="utf-8")
    ]
    assert not bad, bad[:10]


FOOTER = re.compile(r"<footer\b.*?</footer>", re.S)
CONTRIBUTOR_LINK = re.compile(r'<a href="(?:/otel-telco-blueprints/|\.\./)*templates/"[^>]*>\s*Write a blueprint\s*</a>')


@pytest.mark.parametrize(
    "page",
    [
        "index.html",
        "use-cases/alarm-triage-adaptation/index.html",
        "recipes/network-operations/alarm-triage-adaptation/index.html",
        "platform/serving-routing-placement/index.html",
    ],
)
def test_footer_links_contributor_page(site_dir, page):
    html = (site_dir / page).read_text(encoding="utf-8")
    footers = FOOTER.findall(html)
    assert footers, page
    assert any(CONTRIBUTOR_LINK.search(f) for f in footers), page


def test_contributor_page_title(site_dir):
    html = (site_dir / "templates/index.html").read_text(encoding="utf-8")
    assert re.search(r'<h1 id="write-a-blueprint">Write a blueprint<', html)
    assert "<title>Write a blueprint" in html
