"""Closed-loop incident handling links to the public reference implementation: Sources row, Deploy and verify bullet, and try-it data."""

from __future__ import annotations

import re

from tools.tests.conftest import REPO_ROOT
from tools.tests.test_platform_pages import section_text

CLOSED_LOOP = REPO_ROOT / "catalog/agentic-operations/closed-loop-incident-handling/README.md"
IMPL = "https://github.com/ravisharma5/otel-telco-blueprints-impl"
QUICKSTART = f"{IMPL}/tree/main/closed-loop-incident-handling"
REPORT_RE = re.compile(
    r"\(https://github\.com/ravisharma5/otel-telco-blueprints-impl/blob/main/closed-loop-incident-handling/results/"
    r"\d{4}-\d{2}-\d{2}/report\.md\)"
)
BANNED = re.compile(
    r"(?i)\b(validated|unverified|proven|production[- ]ready|technology preview|developer preview)\b"
    r"|\bGA\b|\b[Pp]hase \d"
)


def _source_rows() -> list[list[str]]:
    """Body rows of the Sources table, as raw markdown cells."""
    rows = []
    for line in section_text(CLOSED_LOOP, "Sources").splitlines():
        if line.startswith("|") and not re.match(r"^\|\s*(#|-)", line):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def _report_rows() -> list[list[str]]:
    return [r for r in _source_rows() if REPORT_RE.search(r[3])]


def _quickstart_bullets() -> list[str]:
    deploy = section_text(CLOSED_LOOP, "Deploy and verify")
    return [ln for ln in deploy.splitlines() if ln.startswith("- ") and f"({QUICKSTART})" in ln]


def test_closed_loop_sources_links_report():
    rows = _report_rows()
    assert len(rows) == 1, rows
    _, claim, basis, _ = rows[0]
    assert basis == "project documentation", basis
    assert "no model" in claim, claim


def test_closed_loop_deploy_bullet_links_quickstart():
    assert len(_quickstart_bullets()) == 1


def test_impl_wording():
    texts = [" | ".join(r) for r in _report_rows()] + _quickstart_bullets()
    assert texts
    for text in texts:
        assert not BANNED.search(text), text


def test_try_it_matches_facts():
    import yaml

    try_it = yaml.safe_load((REPO_ROOT / "data/explorer/try-it.yaml").read_text(encoding="utf-8")) or {}
    facts = yaml.safe_load((REPO_ROOT / "data/facts-check.yaml").read_text(encoding="utf-8"))
    assert try_it.get("UC-AGOPS-01") == QUICKSTART, try_it
    for url in try_it.values():
        assert url in facts["extra_urls"], url
