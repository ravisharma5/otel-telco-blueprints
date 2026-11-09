"""The Google Vale style is vendored with provenance; nothing downloads it."""

from __future__ import annotations

import re
import subprocess

from tools.tests.conftest import REPO_ROOT

GOOGLE = REPO_ROOT / ".vale/styles/Google"


def _non_comment_lines(path):
    lines = path.read_text().splitlines()
    return [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def test_vale_ini_has_no_packages_line():
    lines = _non_comment_lines(REPO_ROOT / ".vale.ini")
    assert not [ln for ln in lines if ln.strip().startswith("Packages")]


def test_provenance_records_source_tag_and_sha256():
    text = (GOOGLE / "PROVENANCE.txt").read_text()
    assert "https://github.com/vale-cli/Google" in text
    assert "v0.7.1" in text
    assert re.search(r"\b[0-9a-f]{64}\b", text)


def test_google_style_is_tracked():
    proc = subprocess.run(
        ["git", "ls-files", ".vale/styles/Google"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    names = {p.rsplit("/", 1)[-1] for p in proc.stdout.split()}
    assert {"Acronyms.yml", "Headings.yml", "meta.json", "LICENSE"} <= names


def test_makefile_never_syncs_vale():
    text = (REPO_ROOT / "Makefile").read_text()
    assert "vale sync" not in text
    assert "$(VALE) sync" not in text
    assert "vale-sync" not in text


def test_makefile_uv_sync_is_locked():
    lines = [ln for ln in (REPO_ROOT / "Makefile").read_text().splitlines() if "uv sync" in ln]
    assert lines, "expected a uv sync line in the Makefile"
    assert all("--locked" in ln for ln in lines), lines
