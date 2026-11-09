"""Docs site: strict build, safe config, and the site sources stay in sync.

The strict MkDocs build must pass on the real repo and fail on each broken-page class:
a missing link target, a missing anchor, a page left out of nav, and a nav entry for a
missing file. Builds run on a copy in tmp_path, so faults never touch the repo.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

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
        "  - Platform: platform/index.md\n",
        "  - Platform:\n      - Overview: platform/index.md\n      - Missing: platform/missing.md\n",
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


def test_no_tooling_pages(site_copy):
    # Plant files the hook must never publish, then check the output tree.
    (site_copy / "framework/candidate.json").write_text("{}", encoding="utf-8")
    code, out = _build(site_copy)
    assert code == 0, out
    built = [p.relative_to(site_copy / "out").as_posix() for p in (site_copy / "out").rglob("*")]
    leaked = [p for p in built if any(part in p.split("/") for part in ("tools", "schemas", "fixtures"))]
    assert leaked == []
    assert not any(p.endswith("candidate.json") for p in built)


def test_mermaid(site_copy):
    _append(
        site_copy / "site-src/framework/index.md",
        "\n```mermaid\ngraph LR\n  A --> B\n```\n",
    )
    code, out = _build(site_copy)
    assert code == 0, out
    html = (site_copy / "out/framework/index.html").read_text(encoding="utf-8")
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
    (site_copy / "site-src/framework/definitions.md").write_text("# Stub\n", encoding="utf-8")
    code, out = _build(site_copy)
    assert code != 0, out
    assert "collides" in out, out
