"""Integration: valid samples pass; each broken variant yields exactly its expected codes.

Each `fixtures/broken/<name>/expected.txt` lists one bplint code per line.
Repeated codes mean repeated findings; an empty file means zero findings.
The comparison is the sorted multiset of codes, so an unintended extra code
fails the test.
"""

from __future__ import annotations

import pytest

from tools.tests.conftest import FIXTURES, run_bplint

VALID = sorted(p for p in (FIXTURES / "valid").iterdir() if p.is_dir())
BROKEN = sorted(p for p in (FIXTURES / "broken").iterdir() if p.is_dir())
# CR001 is an error (CI blocks it); no fixture code is warning-level today.
WARNING_CODES: set[str] = set()


def _expected(d):
    return sorted(ln.strip() for ln in (d / "expected.txt").read_text().splitlines() if ln.strip())


def _run(d):
    return run_bplint(d / "README.md")


def test_fixture_sets_exist():
    assert len(VALID) == 4
    assert len(BROKEN) == 16
    for d in BROKEN:
        assert (d / "README.md").is_file() and (d / "expected.txt").is_file(), d.name


@pytest.mark.parametrize("d", VALID, ids=lambda p: p.name)
def test_valid_fixture_is_clean(d):
    rc, findings = run_bplint(d / "README.md")
    assert findings == []
    assert rc == 0


@pytest.mark.parametrize("d", BROKEN, ids=lambda p: p.name)
def test_broken_fixture_yields_expected_codes(d):
    expected = _expected(d)
    rc, findings = _run(d)
    actual = sorted(f["code"] for f in findings)
    assert actual == expected, [f"{f['code']} {f['message']}" for f in findings]
    want_rc = 1 if any(c not in WARNING_CODES for c in expected) else 0
    assert rc == want_rc


def test_criterion_4_each_defect_reported():
    """Missing front matter, missing facet, broken link are reported."""
    for name, code in (("no-front-matter", "FM001"), ("missing-facet", "RF001"), ("broken-link", "LK001")):
        rc, findings = _run(FIXTURES / "broken" / name)
        assert code in {f["code"] for f in findings}, name
        assert rc == 1
    rc, findings = run_bplint(FIXTURES / "valid/use-case/README.md")
    assert (rc, findings) == (0, [])
