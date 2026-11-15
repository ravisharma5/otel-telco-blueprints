"""Merge step: collision check, the MkDocs-only 404 rule, redirect pages, and the link check.

Unit tests on tmp folders. The built-output checks live in test_site_output.py.
"""

from __future__ import annotations

import re

import pytest

from tools.site import merge_site
from tools.tests.conftest import REPO_ROOT

LEGACY_PATH = REPO_ROOT / "tools/site/legacy-urls.txt"
SITE_URL = "https://ravisharma5.github.io/otel-telco-blueprints/"
SAMPLE = "catalog/network-operations/alarm-triage-adaptation/"
FLAGSHIP_LEGACY = [
    "catalog/",
    "catalog/agentic-operations/closed-loop-incident-handling/",
    "catalog/business-assurance/camara-care-diagnostics/",
    "catalog/network-operations/alarm-triage-adaptation/",
    "catalog/standards-knowledge/grounded-knowledge-assistant/",
]


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def trees(tmp_path):
    dist, site = tmp_path / "dist", tmp_path / "site"
    dist.mkdir()
    site.mkdir()
    return dist, site


# ---------- merge ----------


def test_merge_copies(trees):
    dist, site = trees
    _write(dist / "index.html", "<p>home</p>")
    _write(dist / "use-cases/a/index.html", "<p>a</p>")
    _write(site / "platform/index.html", "<p>platform</p>")
    merge_site.merge(dist, site)
    assert (site / "index.html").read_text(encoding="utf-8") == "<p>home</p>"
    assert (site / "use-cases/a/index.html").is_file()
    assert (site / "platform/index.html").read_text(encoding="utf-8") == "<p>platform</p>"


def test_merge_collision_fails(trees):
    dist, site = trees
    _write(dist / "sitemap.xml", "explorer")
    _write(site / "sitemap.xml", "mkdocs")
    with pytest.raises(SystemExit) as exc:
        merge_site.merge(dist, site)
    assert "sitemap.xml exists in both builds" in str(exc.value)
    assert (site / "sitemap.xml").read_text(encoding="utf-8") == "mkdocs"


def test_merge_identical_ok(trees):
    dist, site = trees
    _write(dist / "brand/fonts/a.woff2", "same")
    _write(site / "brand/fonts/a.woff2", "same")
    merge_site.merge(dist, site)
    assert (site / "brand/fonts/a.woff2").read_text(encoding="utf-8") == "same"


def test_merge_rejects_astro_404(trees):
    dist, site = trees
    _write(dist / "404.html", "<p>missing</p>")
    _write(site / "404.html", "<p>missing</p>")
    with pytest.raises(SystemExit) as exc:
        merge_site.merge(dist, site)
    assert "404.html" in str(exc.value)


def test_merge_missing_dist_fails(tmp_path):
    with pytest.raises(SystemExit):
        merge_site.merge(tmp_path / "nope", tmp_path)


# ---------- redirects ----------


def _redirect(site, path=SAMPLE):
    target = "recipes/" + path[len("catalog/") :]
    _write(site / target / "index.html", "<p>recipe</p>")
    merge_site.write_redirects(site, [path], SITE_URL)
    return (site / path / "index.html").read_text(encoding="utf-8"), target


def test_redirect_page_shape(tmp_path):
    html, target = _redirect(tmp_path)
    rel = "../../../" + target
    assert html.lower().startswith("<!doctype html>")
    assert '<html lang="en">' in html
    assert f'<meta http-equiv="refresh" content="0; url={rel}">' in html
    assert f'<link rel="canonical" href="{SITE_URL}{target}">' in html
    assert '<meta name="robots" content="noindex">' in html
    assert f'location.replace("{rel}" + location.hash)' in html
    assert f'<a href="{rel}">' in html
    assert "<title>Moved: Adaptation ladder on alarm and root-cause triage</title>" in html
    # Targets come only from the frozen list: no query strings, no URL reads.
    assert "?" not in html
    assert "location.search" not in html and "URLSearchParams" not in html


def test_redirect_catalog_root(tmp_path):
    html, _ = _redirect(tmp_path, "catalog/")
    assert '<meta http-equiv="refresh" content="0; url=../recipes/">' in html
    assert f'<link rel="canonical" href="{SITE_URL}recipes/">' in html


def test_redirect_missing_target_fails(tmp_path):
    with pytest.raises(SystemExit) as exc:
        merge_site.write_redirects(tmp_path, [SAMPLE], SITE_URL)
    assert "recipes/network-operations/alarm-triage-adaptation/" in str(exc.value)


@pytest.mark.parametrize(
    "bad", ["catalog/../x/", "recipes/a/", "catalog/a", "catalog/a/?q=1/", "/catalog/a/"]
)
def test_redirect_rejects_bad_entry(tmp_path, bad):
    with pytest.raises(SystemExit):
        merge_site.write_redirects(tmp_path, [bad], SITE_URL)


def test_legacy_list_frozen():
    entries = merge_site.read_legacy(LEGACY_PATH)
    for want in FLAGSHIP_LEGACY:
        assert want in entries, want
    assert all(e.startswith("catalog/") and e.endswith("/") for e in entries)
    assert entries == sorted(set(entries))


# ---------- link check ----------


def test_check_links_finds_broken(tmp_path):
    _write(tmp_path / "index.html", '<a href="a/">ok</a><a href="https://example.com/">x</a>')
    _write(tmp_path / "a/index.html", "<p>a</p>")
    _write(
        tmp_path / "b/index.html",
        '<a href="../missing/">bad</a>'
        '<img src="/otel-telco-blueprints/nope.png">'
        '<a href="/otel-telco-blueprints/a/#top">ok</a>'
        '<a href="#here">ok</a><a href="mailto:x@example.com">ok</a>'
        '<a href="../a/index.html?x=1">ok</a>',
    )
    broken = merge_site.check_links(tmp_path)
    assert len(broken) == 2, broken
    assert any("../missing/" in b for b in broken)
    assert any("/otel-telco-blueprints/nope.png" in b for b in broken)


def test_check_links_clean(tmp_path):
    _write(tmp_path / "index.html", '<a href="./">self</a><a href="/otel-telco-blueprints/.">root</a>')
    assert merge_site.check_links(tmp_path) == []


def test_no_planning_ids_in_merge_files():
    from tools.guards.patterns import PLANNING_ID_RE

    for rel in ("tools/site/merge_site.py", "tools/site/legacy-urls.txt"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert not PLANNING_ID_RE.search(text), rel
        assert not re.search(r"(?i)\bphase [0-9]", text), rel
