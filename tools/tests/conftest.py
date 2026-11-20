"""Shared test helpers: run the linter, locate Vale, and list catalog pages."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml

from tools.bplint.ideas import is_idea
from tools.site.export_explorer import SKIPPED_DOMAINS

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tools/tests/fixtures"
FIXED_TODAY = "2026-11-07"
CATALOG = REPO_ROOT / "catalog"


def _catalog_fm(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def use_case_pages(catalog: pathlib.Path = CATALOG) -> list[pathlib.Path]:
    """Every use-case page under catalog/*/*/, ideas included, demo skipped, sorted."""
    out = []
    for path in sorted(catalog.glob("*/*/README.md")):
        fm = _catalog_fm(path)
        if fm.get("type") == "use-case" and fm.get("domain") not in SKIPPED_DOMAINS:
            out.append(path)
    return out


def front_page_pages(catalog: pathlib.Path = CATALOG) -> list[pathlib.Path]:
    """Use-case pages on the front page: not ideas, not demo (the shared is_idea rule)."""
    return [p for p in use_case_pages(catalog) if not is_idea(_catalog_fm(p))]


def idea_pages(catalog: pathlib.Path = CATALOG) -> list[pathlib.Path]:
    """Use-case pages that carry the idea object (the shared is_idea rule)."""
    return [p for p in use_case_pages(catalog) if is_idea(_catalog_fm(p))]


def run_bplint(
    *paths,
    today=FIXED_TODAY,
    config=FIXTURES / "config.yaml",
    extra=(),
):
    """Run `python -m tools.bplint` and return (returncode, findings_list)."""
    cmd = [
        sys.executable,
        "-m",
        "tools.bplint",
        "--config",
        str(config),
        "--today",
        today,
        "--format",
        "json",
        *extra,
        *map(str, paths),
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    out = proc.stdout.strip()
    findings = json.loads(out) if out else []
    return proc.returncode, findings


def vale_or_skip():
    """Return the vale binary path; skip if missing, or fail when REQUIRE_VALE=1."""
    vale = shutil.which("vale")
    if vale is None:
        if os.environ.get("REQUIRE_VALE") == "1":
            pytest.fail("vale not found on PATH and REQUIRE_VALE=1")
        pytest.skip("vale not installed")
    return vale


@pytest.fixture
def bplint():
    return run_bplint


@pytest.fixture
def vale_bin():
    return vale_or_skip()


EXPLORER_DIST = REPO_ROOT / "explorer/dist"
SITE_DIR = REPO_ROOT / "site"


@pytest.fixture
def explorer_dist():
    """Built explorer output; fails (never skips) when the build is missing."""
    if not EXPLORER_DIST.is_dir():
        pytest.fail("explorer/dist is missing: run make explorer first")
    return EXPLORER_DIST


@pytest.fixture
def site_dir():
    """Built docs site; fails (never skips) when the build is missing."""
    if not SITE_DIR.is_dir():
        pytest.fail("site/ is missing: run make site first")
    return SITE_DIR


def pdf_or_skip():
    """Skip unless REQUIRE_PDF=1; with it, fail when WeasyPrint or Pango cannot load.

    Only the Pages workflow (and make test-pdf) sets REQUIRE_PDF=1, so lint skips
    the PDF even on a runner where WeasyPrint happens to import.
    """
    if os.environ.get("REQUIRE_PDF") != "1":
        pytest.skip("PDF tests run only with REQUIRE_PDF=1 (make test-pdf, Pages workflow)")
    try:
        import weasyprint  # noqa: F401  (loads Pango through cffi)
    except (ImportError, OSError) as exc:
        pytest.fail(f"WeasyPrint cannot load ({exc}) and REQUIRE_PDF=1")


@pytest.fixture(autouse=True)
def _pdf_gate(request):
    """Every test marked pdf skips unless REQUIRE_PDF=1."""
    if request.node.get_closest_marker("pdf") is not None:
        pdf_or_skip()
