"""Explorer toolchain pins and the built home page.

Unmarked tests check the pinned toolchain (Node version, exact astro pin, lockfile,
install scripts blocked, no tracked .gitignore) and that the lockfile carries the
linux-x64 native binaries the CI runner needs, so `npm ci` works without scripts.

Tests marked `site_output` read explorer/dist and run after `make explorer`
(`make test-site`); they check the hero, the skip link, the header nav, and that
nothing in the build loads a resource from another origin.
"""

from __future__ import annotations

import json
import re
import subprocess
from html.parser import HTMLParser

import pytest
import yaml

from tools.guards.patterns import PLANNING_ID_RE
from tools.tests.conftest import REPO_ROOT

EXPLORER = REPO_ROOT / "explorer"
LOCK_PATH = EXPLORER / "package-lock.json"
COPY_PATH = EXPLORER / "src/content/copy.md"
NODE_VERSION = "26.13.1"
ASTRO_VERSION = "7.4.11"
BASE = "/otel-telco-blueprints/"
NAV = ["Use cases", "Recipes", "Platform", "Architecture", "Framework"]
NAV_PATHS = ["", "recipes/", "platform/", "architecture/", "framework/"]
# Native packages the build loads on Linux x64 CI. Each must ship as an optional,
# platform-specific dependency in the lockfile, so npm ci needs no install script.
LINUX_X64_BINARIES = {
    "node_modules/rolldown": "node_modules/@rolldown/binding-linux-x64-gnu",
    "node_modules/lightningcss": "node_modules/lightningcss-linux-x64-gnu",
    "node_modules/sharp": "node_modules/@img/sharp-linux-x64",
    "node_modules/esbuild": "node_modules/@esbuild/linux-x64",
    "node_modules/rollup": "node_modules/@rollup/rollup-linux-x64-gnu",
}
# Packages allowed to declare an install script. npm never runs it (ignore-scripts),
# and fsevents is a macOS-only file watcher used by the dev server, not by builds.
INSTALL_SCRIPT_ALLOWED = {"node_modules/fsevents"}
OTHER_ORIGIN = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//", re.I)


def _lock():
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


# ---------- toolchain (unmarked) ----------


def test_explorer_toolchain():
    assert (EXPLORER / ".node-version").read_text(encoding="utf-8").strip() == NODE_VERSION
    package = json.loads((EXPLORER / "package.json").read_text(encoding="utf-8"))
    assert package["private"] is True
    assert package["dependencies"] == {"astro": ASTRO_VERSION}
    assert not package.get("devDependencies")
    lock = _lock()
    assert lock["lockfileVersion"] == 3
    assert lock["packages"]["node_modules/astro"]["version"] == ASTRO_VERSION
    npmrc = (EXPLORER / ".npmrc").read_text(encoding="utf-8").splitlines()
    assert "ignore-scripts=true" in [line.strip() for line in npmrc]
    assert not list(EXPLORER.rglob(".gitignore")), "no .gitignore under explorer/"


def test_explorer_not_tracking_build_output():
    out = subprocess.run(
        ["git", "ls-files", "explorer"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    bad = [p for p in out if re.search(r"node_modules|/dist/|/\.astro/|src/generated/|\.gitignore", p)]
    assert bad == []


def test_lockfile_has_ci_binaries():
    packages = _lock()["packages"]
    assert "node_modules/rolldown" in packages, "expected the rolldown bundler in the tree"
    for parent, binary in LINUX_X64_BINARIES.items():
        if parent not in packages:
            continue
        assert binary in packages, f"{parent} present but {binary} missing from the lockfile"
        assert packages[binary].get("optional") is True, f"{binary} should be optional"
        assert packages[binary].get("os") == ["linux"] and packages[binary].get("cpu") == ["x64"]


def test_install_scripts_limited():
    packages = _lock()["packages"]
    scripted = {k for k, v in packages.items() if v.get("hasInstallScript")}
    assert scripted <= INSTALL_SCRIPT_ALLOWED, f"new install scripts: {scripted - INSTALL_SCRIPT_ALLOWED}"


def test_lockfile_has_no_planning_ids():
    text = LOCK_PATH.read_text(encoding="utf-8")
    match = PLANNING_ID_RE.search(text)
    assert match is None, match and match.group(0)


# ---------- built output (site_output) ----------


class _Page(HTMLParser):
    FOCUSABLE = {"a", "button", "input", "select", "textarea"}

    def __init__(self):
        super().__init__()
        self.focusable = []
        self.h1 = []
        self._in_h1 = False
        self.nav_links = []
        self._nav_depth = 0
        self.resources = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        tabindex = a.get("tabindex")
        if (tag in self.FOCUSABLE and (tag != "a" or "href" in a)) or (
            tabindex is not None and int(tabindex) >= 0
        ):
            if tabindex is None or int(tabindex) >= 0:
                self.focusable.append((tag, a))
        if tag == "h1":
            self._in_h1 = True
            self.h1.append("")
        if tag == "nav":
            self._nav_depth += 1
        if tag == "a" and self._nav_depth and "href" in a:
            self.nav_links.append([a["href"], ""])
        if tag == "link" and "stylesheet" in a.get("rel", ""):
            self.resources.append(a.get("href", ""))
        if tag in {"script", "img", "iframe", "source", "audio", "video"} and "src" in a:
            self.resources.append(a["src"])

    def handle_endtag(self, tag):
        if tag == "h1":
            self._in_h1 = False
        if tag == "nav":
            self._nav_depth -= 1

    def handle_data(self, data):
        if self._in_h1:
            self.h1[-1] += data
        if self._nav_depth and self.nav_links and self.nav_links[-1][1] == "":
            self.nav_links[-1][1] = data.strip()


def _parse(path):
    page = _Page()
    page.feed(path.read_text(encoding="utf-8"))
    return page


def _headline():
    text = COPY_PATH.read_text(encoding="utf-8")
    front = yaml.safe_load(re.match(r"^---\n(.*?)\n---\n", text, re.S).group(1))
    return front["home"]["hero"]["headline"]


@pytest.mark.site_output
def test_home_hero(explorer_dist):
    index = explorer_dist / "index.html"
    assert index.is_file()
    page = _parse(index)
    assert len(page.h1) == 1
    assert " ".join(page.h1[0].split()) == _headline()


@pytest.mark.site_output
def test_skip_link_first(explorer_dist):
    page = _parse(explorer_dist / "index.html")
    tag, attrs = page.focusable[0]
    assert tag == "a" and attrs["href"] == "#content"
    assert 'id="content"' in (explorer_dist / "index.html").read_text(encoding="utf-8")


@pytest.mark.site_output
def test_header_nav(explorer_dist):
    page = _parse(explorer_dist / "index.html")
    links = [(href, text) for href, text in page.nav_links if text in NAV]
    assert [text for _, text in links] == NAV
    assert [href for href, _ in links] == [BASE + p for p in NAV_PATHS]


@pytest.mark.site_output
def test_no_third_party_resources(explorer_dist):
    hits = []
    for html in explorer_dist.rglob("*.html"):
        for ref in _parse(html).resources:
            if OTHER_ORIGIN.match(ref):
                hits.append(f"{html.name}: {ref}")
    for css in explorer_dist.rglob("*.css"):
        text = css.read_text(encoding="utf-8")
        for ref in re.findall(r"url\(\s*['\"]?([^'\")]+)", text):
            if OTHER_ORIGIN.match(ref):
                hits.append(f"{css.name}: {ref}")
        for ref in re.findall(r"@import\s+(?:url\()?\s*['\"]?([^'\"); ]+)", text):
            if OTHER_ORIGIN.match(ref):
                hits.append(f"{css.name}: {ref}")
    assert hits == []
