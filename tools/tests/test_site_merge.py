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


# ---------- moved URLs ----------

MOVED_PATH = REPO_ROOT / "tools/site/moved-urls.txt"
# Every pair here must stay in moved-urls.txt; later catalog moves extend this set.
PINNED_MOVES: list[tuple[str, str]] = [
    (
        "recipes/agentic-operations/policy-following-ops-agents/",
        "platform/safety-autonomy-gating/#policies-as-action-classes",
    ),
    (
        "use-cases/policy-following-ops-agents/",
        "platform/safety-autonomy-gating/#policies-as-action-classes",
    ),
]
MOVE_OLD = "recipes/research/old-name/"
MOVE_NEW = "recipes/network-operations/alarm-triage-adaptation/"
MOVE_TITLE = "Adaptation ladder on alarm and root-cause triage"


def test_read_moves_pairs(tmp_path):
    f = tmp_path / "moved.txt"
    f.write_text("# header\n\n  a/ b/  \n# c/ d/\nx/y/ z/#frag\n", encoding="utf-8")
    assert merge_site.read_moves(f) == [("a/", "b/"), ("x/y/", "z/#frag")]


@pytest.mark.parametrize("line", ["a/", "a/ b/ c/"])
def test_read_moves_rejects_wrong_field_count(tmp_path, line):
    f = tmp_path / "moved.txt"
    f.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        merge_site.read_moves(f)


def _move(site, old=MOVE_OLD, new=MOVE_NEW):
    _write(site / new.split("#", 1)[0] / "index.html", "<p>recipe</p>")
    merge_site.write_moves(site, [(old, new)], SITE_URL)
    return (site / old / "index.html").read_text(encoding="utf-8")


def test_move_stub_shape(tmp_path):
    html = _move(tmp_path)
    rel = "../../../" + MOVE_NEW
    assert html.lower().startswith("<!doctype html>")
    assert f'<meta http-equiv="refresh" content="0; url={rel}">' in html
    assert f'<link rel="canonical" href="{SITE_URL}{MOVE_NEW}">' in html
    assert '<meta name="robots" content="noindex">' in html
    assert f'location.replace("{rel}" + location.hash)' in html
    assert f"<title>Moved: {MOVE_TITLE}</title>" in html
    assert "?" not in html and "location.search" not in html


def test_move_fragment_target_has_one_hash(tmp_path):
    new = MOVE_NEW + "#what-you-need"
    html = _move(tmp_path, new=new)
    rel = "../../../" + new
    assert f'location.replace("{rel}")' in html
    assert "location.hash" not in html
    assert f'<meta http-equiv="refresh" content="0; url={rel}">' in html
    assert f'<link rel="canonical" href="{SITE_URL}{new}">' in html
    script = re.search(r"<script>(.*?)</script>", html).group(1)
    assert script.count("#") == 1, script
    for url in re.findall(r'(?:href|url)=([^">]+)', html):
        assert url.count("#") <= 1, url


def test_move_missing_target_fails(tmp_path):
    with pytest.raises(SystemExit) as exc:
        merge_site.write_moves(tmp_path, [(MOVE_OLD, MOVE_NEW + "#x")], SITE_URL)
    assert "target" in str(exc.value) and "is missing" in str(exc.value)
    assert MOVE_NEW in str(exc.value)


def test_move_old_still_built_fails(tmp_path):
    _write(tmp_path / MOVE_OLD / "index.html", "<p>old</p>")
    with pytest.raises(SystemExit) as exc:
        _move(tmp_path)
    assert "is still built; it must only redirect" in str(exc.value)


@pytest.mark.parametrize(
    "old,new",
    [
        ("Recipes/x/", MOVE_NEW),
        ("recipes/x", MOVE_NEW),
        ("/recipes/x/", MOVE_NEW),
        ("recipes/x/#frag", MOVE_NEW),
        ("recipes/../x/", MOVE_NEW),
        (MOVE_OLD, "Recipes/x/"),
        (MOVE_OLD, "recipes/x"),
        (MOVE_OLD, "/recipes/x/"),
        (MOVE_OLD, "https://example.com/"),
        (MOVE_OLD, "recipes/x/?q=1"),
        (MOVE_OLD, "recipes/x/#a#b"),
        (MOVE_OLD, "recipes/x/#Frag"),
    ],
)
def test_move_rejects_bad_pairs(tmp_path, old, new):
    with pytest.raises(SystemExit):
        merge_site.write_moves(tmp_path, [(old, new)], SITE_URL)


def test_moved_title_sources(tmp_path):
    def page(rel, title):
        _write(tmp_path / rel, f'---\ntitle: "{title}"\n---\n# x\n')

    page("catalog/ideas/some-idea/README.md", "Idea <one>")
    page("catalog/research/kpi/README.md", "Recipe two")
    page("platform/serving/README.md", "Platform three")
    assert merge_site._moved_title("recipes/ideas/some-idea/", tmp_path) == "Idea <one>"
    assert merge_site._moved_title("recipes/research/kpi/#a", tmp_path) == "Recipe two"
    assert merge_site._moved_title("platform/serving/", tmp_path) == "Platform three"
    with pytest.raises(SystemExit) as exc:
        merge_site._moved_title("explorer/x/", tmp_path)
    assert "no source page" in str(exc.value)


def test_move_title_is_escaped(tmp_path):
    _write(tmp_path / "src/catalog/ideas/some-idea/README.md", '---\ntitle: "A <b> & \\"q\\""\n---\n')
    site = tmp_path / "site"
    _write(site / "recipes/ideas/some-idea/index.html", "<p>x</p>")
    merge_site.write_moves(site, [(MOVE_OLD, "recipes/ideas/some-idea/")], SITE_URL, root=tmp_path / "src")
    html = (site / MOVE_OLD / "index.html").read_text(encoding="utf-8")
    assert "<b>" not in html and "&lt;b&gt; &amp;" in html


def test_moved_list_frozen():
    text = MOVED_PATH.read_text(encoding="utf-8")
    assert "Use cases moved by the catalog focus change. Frozen: never remove a line." in text.splitlines()[0]
    pairs = merge_site.read_moves(MOVED_PATH)
    for want in PINNED_MOVES:
        assert want in pairs, want
    olds = [old for old, _ in pairs]
    assert len(set(olds)) == len(olds)


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


def _pdf_link_site(tmp_path):
    _write(
        tmp_path / "proposal/index.html",
        '<a href="otel-telco-blueprints-proposal.pdf">pdf</a><a href="other.pdf">x</a>',
    )
    return tmp_path


def test_missing_pdf_optional_without_require_pdf(tmp_path, monkeypatch):
    site = _pdf_link_site(tmp_path)
    monkeypatch.delenv("REQUIRE_PDF", raising=False)
    optional = merge_site.optional_targets(site)
    assert optional == {merge_site.PROPOSAL_PDF}
    broken = merge_site.check_links(site, optional)
    # Only the proposal PDF is exempt; any other missing file still fails.
    assert broken == ["proposal/index.html: other.pdf"]


def test_missing_pdf_fails_with_require_pdf(tmp_path, monkeypatch):
    site = _pdf_link_site(tmp_path)
    monkeypatch.setenv("REQUIRE_PDF", "1")
    assert merge_site.optional_targets(site) == frozenset()
    broken = merge_site.check_links(site, merge_site.optional_targets(site))
    assert "proposal/index.html: otel-telco-blueprints-proposal.pdf" in broken


def test_built_pdf_never_optional(tmp_path, monkeypatch):
    site = _pdf_link_site(tmp_path)
    _write(site / merge_site.PROPOSAL_PDF, "%PDF-1.7")
    monkeypatch.delenv("REQUIRE_PDF", raising=False)
    assert merge_site.optional_targets(site) == frozenset()


def test_no_planning_ids_in_merge_files():
    from tools.guards.patterns import PLANNING_ID_RE

    for rel in ("tools/site/merge_site.py", "tools/site/legacy-urls.txt", "tools/site/moved-urls.txt"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert not PLANNING_ID_RE.search(text), rel
        assert not re.search(r"(?i)\bphase [0-9]", text), rel
