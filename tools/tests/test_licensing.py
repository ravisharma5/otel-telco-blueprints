"""Licensing: Apache-2.0 for code, CC BY 4.0 for docs, MIT for the vendored Vale style."""

from __future__ import annotations

from tools.tests.conftest import REPO_ROOT


def _read(rel):
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_license_is_apache_2():
    text = _read("LICENSE")
    assert text.lstrip().startswith("Apache License")
    assert "Version 2.0, January 2004" in text


def test_license_docs_is_cc_by_4():
    text = _read("LICENSE-docs")
    assert "Attribution 4.0 International" in text
    assert "Creative Commons" in text


def test_readme_states_license_split():
    text = _read("README.md")
    for needle in ("Apache-2.0", "CC-BY-4.0", "MIT", "LICENSE-docs", "PROVENANCE.txt"):
        assert needle in text, needle


def test_vendored_vale_style_keeps_mit_license():
    assert (REPO_ROOT / ".vale/styles/Google/LICENSE").is_file()
