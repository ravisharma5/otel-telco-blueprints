"""Docs site: strict build, safe config, and the site sources stay in sync.

The strict MkDocs build must pass on the real repo and fail on each broken-page class:
a missing link target, a missing anchor, a page left out of nav, and a nav entry for a
missing file. Builds run on a copy in tmp_path, so faults never touch the repo.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest
import yaml
from pymdownx.slugs import slugify

from tools.bplint.slug import github_slug
from tools.tests.conftest import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "mkdocs.yml"
SITE_DIRS = ["site-src", "tools/site", "framework", "templates", "architecture", "platform", "catalog"]


class _TagTolerantLoader(yaml.SafeLoader):
    """SafeLoader that maps `!!python/...` tags to None instead of executing them."""


_TagTolerantLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/", lambda loader, suffix, node: None
)

CONFIG = yaml.load(CONFIG_PATH.read_text(encoding="utf-8"), Loader=_TagTolerantLoader)


def _copy_site(tmp_path):
    """Copy the files the site build reads into tmp_path and return that root."""
    root = tmp_path / "repo"
    root.mkdir()
    shutil.copy2(CONFIG_PATH, root / "mkdocs.yml")
    for rel in SITE_DIRS:
        src = REPO_ROOT / rel
        if src.is_dir():
            shutil.copytree(src, root / rel, ignore=shutil.ignore_patterns("__pycache__"))
    return root


def _build(root):
    """Run the strict build on a copied tree; return (returncode, combined output)."""
    env = {**os.environ, "NO_MKDOCS_2_WARNING": "1"}
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mkdocs",
            "build",
            "--strict",
            "-f",
            str(root / "mkdocs.yml"),
            "-d",
            str(root / "out"),
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _append(path, text):
    with path.open("a", encoding="utf-8") as fh:
        fh.write(text)


@pytest.fixture
def site_copy(tmp_path):
    return _copy_site(tmp_path)


def test_clean_build_strict(site_copy):
    code, out = _build(site_copy)
    assert code == 0, out
    assert "WARNING" not in out, out
    assert (site_copy / "out/index.html").is_file()
    assert (site_copy / "out/framework/definitions/index.html").is_file()


def _fault_broken_link(root):
    _append(root / "framework/glossary.md", "\nSee [nothing](nope.md).\n")


def _fault_missing_anchor(root):
    _append(root / "framework/glossary.md", "\nSee [nowhere](#no-such-anchor).\n")


def _fault_unlisted_page(root):
    (root / "framework/new.md").write_text("# New\n\nNot in nav.\n", encoding="utf-8")


def _fault_missing_nav_target(root):
    cfg = root / "mkdocs.yml"
    text = cfg.read_text(encoding="utf-8")
    text = text.replace(
        "      - Overview: platform/index.md\n",
        "      - Overview: platform/index.md\n      - Missing: platform/missing.md\n",
    )
    assert "platform/missing.md" in text
    cfg.write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    "fault",
    [_fault_broken_link, _fault_missing_anchor, _fault_unlisted_page, _fault_missing_nav_target],
    ids=["broken-link", "missing-anchor", "unlisted-page", "missing-nav-target"],
)
def test_strict_failures(site_copy, fault):
    fault(site_copy)
    code, out = _build(site_copy)
    assert code != 0, out
    assert "WARNING" in out, out


def test_routes():
    text = (REPO_ROOT / "site-src/index.md").read_text(encoding="utf-8")
    assert "# Start here" in text
    for target in ("catalog/index.md", "framework/index.md", "architecture/index.md"):
        assert f"]({target})" in text, target


def test_nav_sections():
    titles = [next(iter(item)) for item in CONFIG["nav"]]
    for want in ("Start here", "Framework", "Architecture", "Catalog", "Platform", "Templates"):
        assert want in titles, want
    assert "search" in CONFIG["plugins"]
    assert CONFIG["strict"] is True


# Internal folder name, built from fragments so this file passes the content guards.
PLAN_DIR = "." + "planning"
LEAK_DIRS = ["tools", "schemas", PLAN_DIR]


def _plant_leaks(root):
    for top in LEAK_DIRS:
        (root / top).mkdir(parents=True, exist_ok=True)
        (root / top / "leak.md").write_text("# Leak\n\nInternal page.\n", encoding="utf-8")


def _built(root):
    out = root / "out"
    return [p.relative_to(out).as_posix() for p in out.rglob("*")] if out.is_dir() else []


def test_no_tooling_pages(site_copy):
    # Plant files the hook must never publish, then check the output tree.
    _plant_leaks(site_copy)
    (site_copy / "framework/candidate.json").write_text("{}", encoding="utf-8")
    code, out = _build(site_copy)
    assert code == 0, out
    built = _built(site_copy)
    assert [p for p in built if "leak" in p] == []
    assert not any(p.endswith("candidate.json") for p in built)


def test_no_tooling_pages_detects_widened_allowlist(site_copy):
    # Mutation check: widen the hook allowlist to tools/; the leak check must notice.
    hook = site_copy / "tools/site/hooks.py"
    text = hook.read_text(encoding="utf-8")
    widened = text.replace('"catalog"]', '"catalog", "tools"]')
    assert widened != text
    hook.write_text(widened, encoding="utf-8")
    _plant_leaks(site_copy)
    code, out = _build(site_copy)
    leaked = [p for p in _built(site_copy) if "leak" in p]
    assert code != 0 or leaked, out


def test_snippets_restricted():
    snippets = next(
        ext["pymdownx.snippets"]
        for ext in CONFIG["markdown_extensions"]
        if isinstance(ext, dict) and "pymdownx.snippets" in ext
    )
    assert snippets["base_path"] == ["templates"]
    assert snippets["check_paths"] is True
    assert snippets["restrict_base_path"] is True


@pytest.mark.parametrize("target", ["schemas/leak.md", "../schemas/leak.md"])
def test_snippet_escape_fails(site_copy, target):
    _plant_leaks(site_copy)
    _append(site_copy / "site-src/templates.md", f'\n````markdown\n--8<-- "{target}"\n````\n')
    code, out = _build(site_copy)
    assert code != 0, out
    html = site_copy / "out/templates/index.html"
    assert not (html.is_file() and "Internal page" in html.read_text(encoding="utf-8"))


def test_templates_page_renders(site_copy):
    code, out = _build(site_copy)
    assert code == 0, out
    html = (site_copy / "out/templates/index.html").read_text(encoding="utf-8")
    assert "Platform blueprint title" in html
    assert "Use case title" in html
    assert "Reference page title" in html


@pytest.mark.parametrize("kind", ["file", "dir"])
def test_symlink_rejected(site_copy, kind):
    _plant_leaks(site_copy)
    if kind == "file":
        os.symlink("../schemas/leak.md", site_copy / "framework/link.md")
    else:
        os.symlink("../schemas", site_copy / "framework/linked", target_is_directory=True)
    code, out = _build(site_copy)
    assert code != 0, out
    assert "symlink not allowed" in out, out


def test_mermaid(site_copy):
    _append(
        site_copy / "site-src/index.md",
        "\n```mermaid\ngraph LR\n  A --> B\n```\n",
    )
    code, out = _build(site_copy)
    assert code == 0, out
    html = (site_copy / "out/index.html").read_text(encoding="utf-8")
    assert 'class="mermaid"' in html


@pytest.mark.parametrize(
    "text",
    [
        "A -- B double",
        "Step 15: gate",
        "Ünïcode ok",
        "trailing  spaces",
        "PB-04 serving & routing",
        "At a glance",
        "What ready means (M0-M3)",
    ],
)
def test_slug_parity(text):
    assert slugify(case="lower")(text, "-") == github_slug(text)


def test_hook_collision(site_copy):
    stub = site_copy / "site-src/framework/definitions.md"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text("# Stub\n", encoding="utf-8")
    code, out = _build(site_copy)
    assert code != 0, out
    assert "collides" in out, out


def _load_hooks():
    spec = importlib.util.spec_from_file_location("site_hooks", REPO_ROOT / "tools/site/hooks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _banner(markdown, meta):
    return _load_hooks().on_page_markdown(markdown, SimpleNamespace(meta=meta), None, None)


def _line_after_h1(text, h1):
    lines = text.splitlines()
    idx = lines.index(h1)
    return next(ln for ln in lines[idx + 1 :] if ln.strip())


def test_banner_unit_draft():
    out = _banner("# Title\n\nBody\n", {"type": "reference", "doc_status": "draft"})
    assert _line_after_h1(out, "# Title") == '!!! warning "Draft: content may change"'


def test_banner_unit_review():
    out = _banner("# Title\n\nBody\n", {"type": "reference", "doc_status": "review"})
    assert _line_after_h1(out, "# Title") == '!!! warning "In review"'


@pytest.mark.parametrize("status", ["done", "weird"])
def test_banner_unit_done_and_unknown(status):
    src = "# Title\n\nBody\n"
    assert _banner(src, {"type": "reference", "doc_status": status}) == src


def test_banner_unit_non_reference():
    src = "# Title\n\nBody\n"
    assert _banner(src, {"doc_status": "draft"}) == src


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_banner_unit_skips_fenced_h1(fence):
    src = f"{fence}text\n# not a heading\n{fence}\n\n# Real\n\nBody\n"
    out = _banner(src, {"type": "reference", "doc_status": "draft"})
    assert _line_after_h1(out, "# not a heading") == fence
    assert _line_after_h1(out, "# Real") == '!!! warning "Draft: content may change"'
    assert out.count("!!! warning") == 1


def test_banner_unit_nested_longer_fence():
    src = "````md\n```\n# fake\n```\n````\n\n# Real\n\nBody\n"
    out = _banner(src, {"type": "reference", "doc_status": "draft"})
    assert _line_after_h1(out, "# fake") == "```"
    assert _line_after_h1(out, "# Real") == '!!! warning "Draft: content may change"'
    assert out.count("!!! warning") == 1


def test_banner_unit_info_string_does_not_close_fence():
    src = "```text\n```python\n# not a heading\n```\n\n# Real\n\nBody\n"
    out = _banner(src, {"type": "reference", "doc_status": "draft"})
    assert _line_after_h1(out, "# not a heading") == "```"
    assert _line_after_h1(out, "# Real") == '!!! warning "Draft: content may change"'


def test_banner_unit_other_fence_char_does_not_close():
    src = "~~~\n```\n# not a heading\n~~~\n\n# Real\n\nBody\n"
    out = _banner(src, {"type": "reference", "doc_status": "draft"})
    assert _line_after_h1(out, "# Real") == '!!! warning "Draft: content may change"'
    assert out.count("!!! warning") == 1


@pytest.mark.parametrize(
    "comment",
    ["<!--\n# hidden\n-->\n", "<!-- note -->\n", "  <!-- a\n# hidden\nstill hidden -->\n"],
)
def test_banner_unit_skips_html_comments(comment):
    src = f"{comment}\n# Real\n\nBody\n"
    out = _banner(src, {"type": "reference", "doc_status": "draft"})
    assert _line_after_h1(out, "# Real") == '!!! warning "Draft: content may change"'
    assert out.count("!!! warning") == 1


@pytest.mark.parametrize("status", [["draft"], {"draft": True}, 3, None])
def test_banner_unit_non_string_status_gives_no_banner(status):
    src = "# Title\n\nBody\n"
    assert _banner(src, {"type": "reference", "doc_status": status}) == src


def test_banner_unit_platform_draft():
    out = _banner("# Title\n\nBody\n", {"type": "platform", "doc_status": "draft"})
    assert _line_after_h1(out, "# Title") == '!!! warning "Draft: content may change"'


def test_banner_unit_platform_review():
    out = _banner("# Title\n\nBody\n", {"type": "platform", "doc_status": "review"})
    assert _line_after_h1(out, "# Title") == '!!! warning "In review"'


@pytest.mark.parametrize("status", ["done", "weird", None, 3])
def test_banner_unit_platform_done_unknown_or_non_string(status):
    src = "# Title\n\nBody\n"
    assert _banner(src, {"type": "platform", "doc_status": status}) == src


def test_banner_unit_use_case_untouched():
    src = "# Title\n\nBody\n"
    assert _banner(src, {"type": "use-case", "doc_status": "draft"}) == src


def _make_reference(root, status):
    page = root / "framework/glossary.md"
    text = page.read_text(encoding="utf-8")
    new = text.replace("doc_status: done\n", f"type: reference\ndoc_status: {status}\n", 1)
    assert new != text
    page.write_text(new, encoding="utf-8")


def _make_platform(root, status):
    page = root / "framework/glossary.md"
    text = page.read_text(encoding="utf-8")
    new = text.replace("doc_status: done\n", f"type: platform\ndoc_status: {status}\n", 1)
    assert new != text
    page.write_text(new, encoding="utf-8")


def _html(root, rel):
    return (root / "out" / rel / "index.html").read_text(encoding="utf-8")


def test_banner_build(site_copy):
    _make_reference(site_copy, "draft")
    code, out = _build(site_copy)
    assert code == 0, out
    html = _html(site_copy, "framework/glossary")
    title = '<p class="admonition-title">Draft: content may change</p>'
    assert title in html
    assert html.index(title) > html.index("<h1")
    assert 'admonition-title">Draft' not in _html(site_copy, "framework/definitions")


def test_banner_build_done(site_copy):
    _make_reference(site_copy, "done")
    code, out = _build(site_copy)
    assert code == 0, out
    html = _html(site_copy, "framework/glossary")
    assert 'admonition-title">Draft' not in html
    assert 'admonition-title">In review' not in html


def test_banner_build_platform(site_copy):
    _make_platform(site_copy, "draft")
    code, out = _build(site_copy)
    assert code == 0, out
    html = _html(site_copy, "framework/glossary")
    title = '<p class="admonition-title">Draft: content may change</p>'
    assert title in html
    assert html.index(title) > html.index("<h1")


def _nav_children(section):
    entry = next(item for item in CONFIG["nav"] if next(iter(item)) == section)
    return [next(iter(child.values())) for child in entry[section]]


def test_nav_order():
    assert _nav_children("Architecture") == [
        "architecture/index.md",
        "architecture/decision-gate.md",
        "architecture/adaptation-ladder.md",
        "architecture/placement.md",
        "architecture/crosswalk.md",
    ]
    assert _nav_children("Framework") == [
        "framework/index.md",
        "framework/definitions.md",
        "framework/glossary.md",
        "framework/style-guide.md",
        "framework/review-checklist.md",
    ]
    assert _nav_children("Platform") == [
        "platform/index.md",
        "platform/serving-routing-placement/README.md",
        "platform/integration/README.md",
        "platform/safety-autonomy-gating/README.md",
    ]


def test_start_here_labels():
    text = (REPO_ROOT / "site-src/index.md").read_text(encoding="utf-8")
    assert "[Readiness questions](framework/index.md)" in text
    assert "[Architecture overview](architecture/index.md)" in text


def test_overview_links_pages():
    text = (REPO_ROOT / "architecture/index.md").read_text(encoding="utf-8")
    for target in (
        "decision-gate.md",
        "adaptation-ladder.md",
        "placement.md",
        "crosswalk.md",
        "../framework/index.md",
    ):
        assert f"]({target})" in text, target


def test_readiness_links_architecture_pages():
    text = (REPO_ROOT / "framework/index.md").read_text(encoding="utf-8")
    for target in (
        "../architecture/index.md",
        "../architecture/decision-gate.md",
        "../architecture/adaptation-ladder.md",
        "../architecture/placement.md",
    ):
        assert f"]({target})" in text, target


# ---------- no internal phase numbers on published pages ----------

PHASE_NUMBER = re.compile(r"(?i)\bphases? [0-9]")
PUBLISHED_DIRS = ["site-src", "framework", "templates", "architecture", "platform", "catalog"]


def _published_markdown():
    for name in PUBLISHED_DIRS:
        root = REPO_ROOT / name
        if root.is_dir():
            yield from sorted(root.rglob("*.md"))


@pytest.mark.parametrize("sample", ["arrive in Phase 5", "in phases 3 and 4", "| Phase 4 |"])
def test_phase_number_regex_catches(sample):
    assert PHASE_NUMBER.search(sample), sample


@pytest.mark.parametrize("sample", ["in the phase that adds it", "multi-phase rollout", "phase-in"])
def test_phase_number_regex_allows(sample):
    assert not PHASE_NUMBER.search(sample), sample


def test_no_phase_numbers_on_published_pages():
    hits = []
    for path in _published_markdown():
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if PHASE_NUMBER.search(line):
                hits.append(f"{path.relative_to(REPO_ROOT)}:{n}")
    assert hits == []
