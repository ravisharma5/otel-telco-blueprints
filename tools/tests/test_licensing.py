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


def test_vendored_mermaid_license():
    import hashlib
    import re

    folder = REPO_ROOT / "site-src/brand/vendor/mermaid"
    assert "MIT" in (folder / "LICENSE").read_text(encoding="utf-8")
    prov = (folder / "PROVENANCE.txt").read_text(encoding="utf-8")
    data = (folder / "mermaid.min.js").read_bytes()
    assert "mermaid" in prov and "11.17.2" in prov
    assert re.search(r"^integrity: sha512-[A-Za-z0-9+/=]+$", prov, re.M)
    digest = hashlib.sha256(data).hexdigest()
    assert f"sha256: {digest}" in prov
    # The hash is also pinned in code, so editing the file and PROVENANCE.txt together fails.
    from tools.guards.patterns import VENDORED
    from tools.tests.test_guard_patterns import MERMAID_SHA256

    assert digest == MERMAID_SHA256 == VENDORED["site-src/brand/vendor/mermaid/mermaid.min.js"]
    assert re.search(rf"^size_bytes: {len(data)}$", prov, re.M)
