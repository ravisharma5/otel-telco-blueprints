"""Tests for the facts stamp (tools/site/facts.py and data/facts-check.yaml).

The digest is computed offline from the Sources tables, the serving-data source
URLs, and the extra URLs in data/facts-check.yaml. The network re-check is tested
with injected fetch functions only; no test opens a socket.
"""

from __future__ import annotations

import datetime
import shutil
import urllib.error

import pytest
import yaml

from tools.site import facts
from tools.tests.conftest import REPO_ROOT

FACTS = yaml.safe_load((REPO_ROOT / "data/facts-check.yaml").read_text(encoding="utf-8"))
GSMA_PRESS = (
    "https://www.gsma.com/newsroom/press-release/"
    "gsma-launches-open-telco-ai-to-accelerate-development-of-telco%E2%80%91grade-ai/"
)


def _copy_inputs(tmp_path):
    """Copy only what the digest reads into a temp repo root."""
    for rel in ("platform", "catalog", "data", "tools/bplint/budgets.yaml"):
        src = REPO_ROOT / rel
        dst = tmp_path / rel
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    return tmp_path


# ---- digest --------------------------------------------------------------


def test_digest_is_stable():
    assert facts.sources_digest(REPO_ROOT) == facts.sources_digest(REPO_ROOT)


def test_digest_changes_with_a_row(tmp_path):
    root = _copy_inputs(tmp_path)
    before = facts.sources_digest(root)
    page = root / "catalog/network-operations/core-network-rca/README.md"
    text = page.read_text(encoding="utf-8")
    marker = "TS 28.552 defines the 5G performance measurements"
    assert marker in text
    page.write_text(text.replace(marker, marker + " for NG-RAN"), encoding="utf-8")
    assert facts.sources_digest(root) != before


def test_digest_ignores_fixtures_and_demo(tmp_path):
    root = _copy_inputs(tmp_path)
    before = facts.sources_digest(root)
    stray = root / "tools/tests/fixtures/extra/README.md"
    stray.parent.mkdir(parents=True)
    stray.write_text(
        "---\ntype: \"use-case\"\n---\n\n## Sources\n\n"
        "| # | Claim | Basis | Source |\n|---|---|---|---|\n"
        "| 1 | A | model card | [x](https://example.com/x) |\n",
        encoding="utf-8",
    )
    assert facts.sources_digest(root) == before


def test_all_urls_unique_sorted():
    urls = facts.all_urls(REPO_ROOT)
    assert urls == sorted(set(urls))
    assert all(u.startswith("https://") for u in urls)
    for extra in FACTS["extra_urls"]:
        assert extra in urls
    assert len(urls) > 100


# ---- stamp ---------------------------------------------------------------


def test_facts_digest():
    assert facts.sources_digest(REPO_ROOT) == FACTS["sources_digest"], (
        "Sources changed after the fact re-check: re-run the re-check, then "
        "`uv run python -m tools.site.facts --write` and update `checked`"
    )
    datetime.date.fromisoformat(FACTS["checked"])
    assert FACTS["url_count"] == len(facts.all_urls(REPO_ROOT))


def test_facts_extra_urls():
    assert GSMA_PRESS in FACTS["extra_urls"]


# ---- network re-check (injected fetch, no sockets) ----------------------


def _scripted(responses):
    """A fetch that returns or raises the scripted responses in order."""
    calls = []

    def fetch(url, timeout):
        calls.append(url)
        item = responses[min(len(calls), len(responses)) - 1]
        if isinstance(item, BaseException):
            raise item
        return item

    fetch.calls = calls
    return fetch


def test_check_urls_retries_then_succeeds():
    url = "https://example.com/a"
    fetch = _scripted([TimeoutError("slow"), (503, url), (200, url)])
    slept = []
    [res] = facts.check_urls([url], fetch=fetch, sleep=slept.append)
    assert res.ok and res.attempts == 3 and res.status == 200
    assert slept == [2, 4]


def test_check_urls_gives_up_after_three():
    url = "https://example.com/b"
    [res] = facts.check_urls([url], fetch=_scripted([(503, url)]), sleep=lambda s: None)
    assert not res.ok and res.attempts == 3 and res.status == 503

    fetch = _scripted([(404, url)])
    [res] = facts.check_urls([url], fetch=fetch, sleep=lambda s: None)
    assert not res.ok and res.attempts == 1 and len(fetch.calls) == 1

    err = urllib.error.URLError("unreachable")
    [res] = facts.check_urls([url], fetch=_scripted([err]), sleep=lambda s: None)
    assert not res.ok and res.attempts == 3 and res.status is None


def test_check_urls_flags_host_change():
    url = "https://example.com/c"
    fetch = _scripted([(200, "https://elsewhere.org/c")])
    [res] = facts.check_urls([url], fetch=fetch, sleep=lambda s: None)
    assert res.ok and res.host_changed
    rows = facts.triage_rows([res], {})
    assert [r[0] for r in rows] == ["cross-host redirect"]

    same = _scripted([(200, "https://www.example.com/c/")])
    [res] = facts.check_urls([url], fetch=same, sleep=lambda s: None)
    assert not res.host_changed
    assert facts.triage_rows([res], {}) == []


def test_card_revisions_reads_sha():
    def fetch_json(url, timeout):
        assert url == "https://huggingface.co/api/models/org/model"
        return {"sha": "abcdef0123456789"}

    assert facts.card_revisions(["org/model"], fetch_json=fetch_json) == {"org/model": "abcdef01"}


def test_card_changes_reach_triage():
    rows = facts.triage_rows([], {"org/model": ("abcdef01", "12345678")})
    assert rows == [("changed card revision", "org/model", "cited abcdef01, now 12345678")]


@pytest.mark.parametrize("flag", ["--urls", "--digest", "--check"])
def test_cli_offline_modes(flag, capsys):
    rc = facts.main([flag])
    out = capsys.readouterr().out
    assert rc == 0 and out.strip()
