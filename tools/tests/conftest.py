"""Shared test helpers: run the linter as a subprocess and locate Vale."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tools/tests/fixtures"
FIXED_TODAY = "2026-11-07"


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
