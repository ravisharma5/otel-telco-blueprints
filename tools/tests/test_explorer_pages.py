"""Explorer toolchain pins and the built home page.

Unmarked tests check the pinned toolchain (Node version, exact astro pin, lockfile,
install scripts blocked, no tracked .gitignore) and that the lockfile carries the
linux-x64 native binaries the CI runner needs, so `npm ci` works without scripts.

Tests marked `site_output` read explorer/dist and run after `make explorer`
(`make test-site`); they check the hero, the skip link, the header nav, and that
nothing in the build loads a resource from another origin.
"""

from __future__ import annotations

import functools
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


JS_MARKER = "document.documentElement.classList.add('js')"


@pytest.mark.site_output
def test_phone_nav_reachable_without_js(explorer_dist):
    # The header nav collapses behind the Menu button only once a script has
    # marked the page with html.js, so without JavaScript the links stay visible.
    for html in explorer_dist.rglob("*.html"):
        text = html.read_text(encoding="utf-8")
        if 'id="site-nav"' not in text:
            continue
        head = text.split("</head>", 1)[0]
        assert JS_MARKER in head, f"{html.relative_to(explorer_dist)}: no js marker in head"
    css = "".join(p.read_text(encoding="utf-8") for p in explorer_dist.rglob("*.css"))
    hiding = []
    for rule in css.replace("\n", "").split("}"):
        selector, _, body = rule.rpartition("{")
        selector = selector.split("{")[-1]
        if re.search(r"display:\s*none", body):
            for part in selector.split(","):
                if re.search(r"\.(?:site-nav)(?![\w-])(?!\S*\.is-open)", part) and " ul" not in part:
                    hiding.append(part.strip())
    assert hiding, "expected a rule that collapses the nav"
    assert all(part.startswith(".js ") for part in hiding), hiding


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


# ---------- home page (site_output) ----------
#
# The home page is compared against explorer/src/generated/explorer.json (written by
# make explorer-data) and copy.md, never hand-copied card text. Only the fixed
# UI-SPEC labels (headings, counts words, status strings, architect links) are typed here.

GENERATED = EXPLORER / "src/generated/explorer.json"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
BAND_HEADINGS = [
    ("h2", "How it works"),
    ("h2", "What do you want to improve?"),
    ("h2", "All use cases"),
    ("h2", "Planning the platform?"),
    ("h2", "Open source, every claim sourced"),
]
COUNT_WORDS = {
    "slots": ("model slot", "model slots"),
    "blueprints": ("platform blueprint", "platform blueprints"),
    "tiers": ("site tier", "site tiers"),
}
RECIPE_STATUS = {"done": "Recipe published", "review": "Recipe in review", "draft": "Recipe in draft"}
TIER_LABELS = {"far-edge": "Far edge", "regional": "Regional site", "core": "Core"}
ARCHITECT_LINKS = [
    ("Readiness questions", "framework/"),
    ("Architecture overview", "architecture/"),
    ("Platform blueprints", "platform/"),
    ("All recipes", "recipes/"),
]
REPLACEABLE = "Any component can be replaced."


class _Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.order = 0

    def text(self):
        parts = []
        for child in self.children:
            parts.append(child if isinstance(child, str) else child.text())
        return " ".join(" ".join(parts).split())

    def walk(self):
        for child in self.children:
            if isinstance(child, _Node):
                yield child
                yield from child.walk()

    def find_all(self, pred):
        return [n for n in self.walk() if pred(n)]

    def has_class(self, name):
        return name in (self.attrs.get("class") or "").split()


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = _Node("#root", [])
        self.stack = [self.root]
        self.count = 0
        self.scripts = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs, self.stack[-1])
        self.count += 1
        node.order = self.count
        self.stack[-1].children.append(node)
        if tag == "script":
            self._script = node
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.stack.pop()

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break
        if tag == "script":
            self._script = None

    def handle_data(self, data):
        if self._script is not None:
            self.scripts.append(data)
            return
        self.stack[-1].children.append(data)


def _home(explorer_dist):
    tree = _Tree()
    tree.feed((explorer_dist / "index.html").read_text(encoding="utf-8"))
    return tree


@functools.cache
def _fresh_export():
    from tools.site.export_explorer import build_explorer_data

    return build_explorer_data(REPO_ROOT)


def _data():
    """explorer.json as built, checked against a fresh export of the source data.

    The page tests compare built HTML with this JSON, so a JSON left over from
    before a data or recipe edit would let a stale page pass.
    """
    assert GENERATED.is_file(), "explorer.json missing: run make explorer"
    data = json.loads(GENERATED.read_text(encoding="utf-8"))
    assert data == _fresh_export(), "explorer.json is stale: run make explorer (make test-site rebuilds it)"
    return data


def _used_tiers(data, uc):
    state = uc["states"][data["default"]["setup"]][data["default"]["batch"]]
    return [c["tier"] for c in state["tiers"] if c["used"]]


def _counts_line(counts):
    parts = []
    for key in ("slots", "blueprints", "tiers"):
        one, many = COUNT_WORDS[key]
        n = counts[key]
        parts.append(f"{n} {one if n == 1 else many}")
    return " · ".join(parts)


def _tiles(tree):
    return tree.root.find_all(lambda n: n.tag == "a" and n.has_class("goal-tile"))


def _cards(tree):
    return tree.root.find_all(lambda n: "data-card" in n.attrs)


@pytest.mark.site_output
def test_home_title_and_lang(explorer_dist):
    tree = _home(explorer_dist)
    html = tree.root.find_all(lambda n: n.tag == "html")[0]
    assert html.attrs.get("lang") == "en"
    title = tree.root.find_all(lambda n: n.tag == "title")[0].text()
    assert title == "OTel Telco Blueprints: telecom AI use cases in production"


@pytest.mark.site_output
def test_home_bands_in_order(explorer_dist):
    tree = _home(explorer_dist)
    h1 = tree.root.find_all(lambda n: n.tag == "h1")
    assert len(h1) == 1
    order = [h1[0].order]
    for tag, text in BAND_HEADINGS:
        hits = tree.root.find_all(lambda n, t=tag, x=text: n.tag == t and n.text() == x)
        assert len(hits) == 1, f"expected one {tag} '{text}', found {len(hits)}"
        order.append(hits[0].order)
    footer = tree.root.find_all(lambda n: n.tag == "footer")
    assert len(footer) == 1
    order.append(footer[0].order)
    assert order == sorted(order), "home bands are out of order"
    steps = tree.root.find_all(lambda n: n.tag == "ol" and n.has_class("steps"))
    assert len(steps) == 1
    items = [c for c in steps[0].children if isinstance(c, _Node) and c.tag == "li"]
    assert len(items) == 3
    assert all(i.find_all(lambda n: n.tag == "h3") for i in items)
    # How it works sits between the hero and the goal picker.
    assert h1[0].order < steps[0].order < order[2]


@pytest.mark.site_output
def test_goal_tiles(explorer_dist):
    data = _data()
    tiles = _tiles(_home(explorer_dist))
    assert len(tiles) == len(data["use_cases"])
    by_href = {t.attrs["href"]: t for t in tiles}
    for uc in data["use_cases"]:
        href = f"{BASE}use-cases/{uc['slug']}/"
        assert href in by_href, f"no goal tile for {uc['slug']}"
        text = by_href[href].text()
        assert uc["card"]["goal"] in text
        assert uc["card"]["audience"] in text
        assert uc["stage"]["label"] in text
    slugs = {uc["slug"] for uc in data["use_cases"]}
    for href in by_href:
        assert re.fullmatch(rf"{re.escape(BASE)}use-cases/([a-z0-9-]+)/", href).group(1) in slugs


@pytest.mark.site_output
def test_gallery_cards(explorer_dist):
    data = _data()
    cards = _cards(_home(explorer_dist))
    assert len(cards) == len(data["use_cases"])
    by_slug = {c.attrs["data-card"]: c for c in cards}
    assert set(by_slug) == {uc["slug"] for uc in data["use_cases"]}
    for uc in data["use_cases"]:
        card = by_slug[uc["slug"]]
        text = card.text()
        for value in (uc["domain_label"], uc["title"], uc["card"]["summary"], uc["stage"]["label"]):
            assert value in text, f"{uc['slug']}: missing {value!r}"
        tags = [n.text() for n in card.find_all(lambda n: n.has_class("tag"))]
        assert tags == uc["slot_names"]
        assert _counts_line(uc["counts"]) in text
        assert RECIPE_STATUS[uc["doc_status"]] in text
        links = card.find_all(lambda n: n.tag == "a")
        assert [a.attrs["href"] for a in links] == [f"{BASE}use-cases/{uc['slug']}/"]
        assert card.attrs["data-domain"] == uc["domain"]
        assert card.attrs["data-stage"] == uc["stage"]["id"]
        assert card.attrs["data-tiers"].split() == _used_tiers(data, uc)


def test_counts_line_singular():
    assert _counts_line({"slots": 1, "blueprints": 2, "tiers": 1}) == (
        "1 model slot · 2 platform blueprints · 1 site tier"
    )


@pytest.mark.site_output
def test_filter_chips_present_values_only(explorer_dist):
    data = _data()
    tree = _home(explorer_dist)
    chips = tree.root.find_all(lambda n: n.tag == "button" and "data-group" in n.attrs)
    assert chips and all(c.attrs.get("aria-pressed") == "false" for c in chips)
    by_group = {}
    for chip in chips:
        by_group.setdefault(chip.attrs["data-group"], []).append((chip.attrs["data-value"], chip.text()))
    f = data["filters"]
    assert by_group["domain"] == [(d["id"], d["label"]) for d in f["domains"]]
    assert by_group["stage"] == [(s["id"], s["label"]) for s in f["stages"]]
    assert by_group["tiers"] == [(t, TIER_LABELS[t]) for t in f["tiers"]]
    assert set(by_group) == {"domain", "stage", "tiers"}
    # A chip only for a value at least one published use case has.
    used = {
        "domain": {uc["domain"] for uc in data["use_cases"]},
        "stage": {uc["stage"]["id"] for uc in data["use_cases"]},
        "tiers": {t for uc in data["use_cases"] for t in _used_tiers(data, uc)},
    }
    for group, values in by_group.items():
        assert {v for v, _ in values} <= used[group]
    if "far-edge" not in f["tiers"]:
        assert "Far edge" not in [c.text() for c in chips]
    groups = tree.root.find_all(lambda n: n.attrs.get("role") == "group")
    assert len(groups) == 3
    labels = []
    for group in groups:
        label_id = group.attrs.get("aria-labelledby")
        assert label_id, "each chip group needs a visible label"
        label = tree.root.find_all(lambda n, i=label_id: n.attrs.get("id") == i)
        assert len(label) == 1 and not label[0].has_class("visually-hidden")
        labels.append(label[0].text())
    assert labels == ["Domain", "How far it goes", "Where it runs"]


@pytest.mark.site_output
def test_filter_bar_hidden_without_js(explorer_dist):
    tree = _home(explorer_dist)
    bars = tree.root.find_all(lambda n: "data-filter-bar" in n.attrs)
    assert len(bars) == 1 and "hidden" in bars[0].attrs
    cards = _cards(tree)
    assert cards and all("hidden" not in c.attrs for c in cards)
    empty = tree.root.find_all(lambda n: "data-empty" in n.attrs)
    assert len(empty) == 1 and "hidden" in empty[0].attrs
    count = tree.root.find_all(lambda n: "data-result-count" in n.attrs)
    assert len(count) == 1 and count[0].attrs.get("aria-live") == "polite"


@pytest.mark.site_output
def test_architect_links_and_note(explorer_dist):
    tree = _home(explorer_dist)
    anchors = [(a.text(), a.attrs.get("href")) for a in tree.root.find_all(lambda n: n.tag == "a")]
    for label, path in ARCHITECT_LINKS:
        assert (label, BASE + path) in anchors, f"missing architect link {label}"
    note = tree.root.find_all(lambda n: n.tag == "section" and n.has_class("oss-note"))
    assert len(note) == 1 and REPLACEABLE in note[0].text()
    otel = tree.root.find_all(lambda n: n.has_class("otel-line"))
    assert len(otel) == 1
    hrefs = [a.attrs.get("href") for a in otel[0].find_all(lambda n: n.tag == "a")]
    assert hrefs == [BASE + "platform/intake-model-selection/"]


@pytest.mark.site_output
def test_no_coming_soon_and_no_innerhtml(explorer_dist):
    for html in explorer_dist.rglob("*.html"):
        text = html.read_text(encoding="utf-8")
        assert "coming soon" not in text.lower(), html.name
        tree = _Tree()
        tree.feed(text)
        assert "innerHTML" not in "".join(tree.scripts), html.name
    for js in explorer_dist.rglob("*.js"):
        assert "innerHTML" not in js.read_text(encoding="utf-8"), js.name


def test_filter_script_reads_no_url_input():
    # The filter script toggles hidden and aria-pressed and writes textContent only.
    for astro in (EXPLORER / "src").rglob("*.astro"):
        text = astro.read_text(encoding="utf-8")
        assert "innerHTML" not in text, astro.name
        if "data-filter-bar" in text:
            for banned in ("location", "URLSearchParams", "localStorage", "sessionStorage", "document.cookie"):
                assert banned not in text, f"{astro.name} uses {banned}"
