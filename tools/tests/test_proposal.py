"""Tests for the facts stamp (tools/site/facts.py and data/facts-check.yaml).

The digest is computed offline from the Sources tables, the serving-data source
URLs, and the extra URLs in data/facts-check.yaml. The network re-check is tested
with injected fetch functions only; no test opens a socket.
"""

from __future__ import annotations

import datetime
import re
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


# ---- proposal page (tools/site/build_proposal.py, proposal/index.md) ------

PROPOSAL = REPO_ROOT / "proposal/index.md"
BLOCKS = (
    "facts-stamp",
    "readiness-questions",
    "architecture",
    "platform",
    "catalog",
    "flagships",
    "evidence-summary",
)
BASIS = ("model card", "research", "Red Hat guidance", "industry use case", "project documentation")


def _proposal_text() -> str:
    return PROPOSAL.read_text(encoding="utf-8")


def _block(name: str) -> str:
    text = _proposal_text()
    start = f"<!-- generated:{name} start -->"
    end = f"<!-- generated:{name} end -->"
    assert text.count(start) == 1 and text.count(end) == 1, name
    return text.split(start, 1)[1].split(end, 1)[0]


def _table_rows(block: str) -> list[list[str]]:
    rows = []
    for line in block.splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def _use_case_pages():
    from tools.bplint.markdown import parse_doc

    out = []
    for path in sorted(REPO_ROOT.glob("catalog/*/*/README.md")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        doc = parse_doc(path, path.read_text(encoding="utf-8"), display=rel)
        fm = doc.front_matter or {}
        if fm.get("type") == "use-case" and fm.get("domain") != "demo":
            out.append((fm, doc))
    return sorted(out, key=lambda p: p[0]["id"])


def _evidence_rows() -> dict[str, list[str]]:
    rows = _table_rows(_block("evidence-summary"))
    header, body = rows[0], rows[1:]
    out = {}
    for row in body:
        m = re.match(r"\[([A-Z]+-[A-Z]+-\d{2})\]", row[0])
        assert m, row[0]
        out[m.group(1)] = dict(zip(header, row))
    return out


def test_proposal_matches_sources():
    from tools.site import build_proposal

    assert build_proposal.main(["--check"]) == 0


def test_proposal_blocks_present():
    text = _proposal_text()
    for name in BLOCKS:
        assert text.count(f"<!-- generated:{name} start -->") == 1, name
        assert text.count(f"<!-- generated:{name} end -->") == 1, name


def test_readiness_questions_block():
    framework = (REPO_ROOT / "framework/index.md").read_text(encoding="utf-8")
    table = framework.split("### The ten questions", 1)[1].split("###", 1)[0]
    expected = [r[1] for r in _table_rows(table)[1:] if r[0].isdigit()]
    got = [r[1] for r in _table_rows(_block("readiness-questions"))[1:]]
    assert len(expected) == 10
    assert got == expected


def test_catalog_block_lists_every_use_case():
    from tools.site.export_explorer import DEPTH_LABELS

    block = _block("catalog")
    rows = _table_rows(block)
    for fm, _doc in _use_case_pages():
        hits = [r for r in rows if r[0].startswith(f"[{fm['id']}]")]
        assert len(hits) == 1, fm["id"]
        assert DEPTH_LABELS[fm["depth"]] in hits[0], fm["id"]


def test_flagships_block():
    flagships = sorted(fm["title"] for fm, _ in _use_case_pages() if fm.get("flagship"))
    assert len(flagships) == 4
    rows = _table_rows(_block("flagships"))[1:]
    got = sorted(re.match(r"\[([^\]]+)\]", r[0]).group(1) for r in rows)
    assert got == flagships


def test_evidence_summary_counts():
    from tools.site.export_explorer import EXPORTER_TABLE_HEADERS, _plain

    rows = _evidence_rows()
    pages = _use_case_pages()
    assert sorted(rows) == [fm["id"] for fm, _ in pages]
    for fm, doc in pages:
        sources = doc.section("Sources")
        counts = dict.fromkeys(BASIS, 0)
        lower = {b.lower(): b for b in BASIS}
        for table in sources.tables:
            idx = table.header.index("Basis")
            for row in table.rows:
                counts[lower[row.cells[idx].strip().lower()]] += 1
        row = rows[fm["id"]]
        for basis in BASIS:
            assert row[basis[0].upper() + basis[1:]] == str(counts[basis]), (fm["id"], basis)
        header = EXPORTER_TABLE_HEADERS["parameters"]
        params = [t for t in doc.section("Governance").tables if tuple(t.header) == header]
        names = [_plain(r.cells[0]) for r in params[0].rows]
        assert row["Named gates"] == "; ".join(names), fm["id"]


def test_evidence_summary_what_you_bring():
    from tools.site.render_bring import bring_summary

    header = _table_rows(_block("evidence-summary"))[0]
    assert header[-1] == "What you bring"
    rows = _evidence_rows()
    for fm, _doc in _use_case_pages():
        assert rows[fm["id"]]["What you bring"] == bring_summary(fm), fm["id"]


def test_platform_block_lists_pb11():
    from tools.bplint.markdown import split_front_matter

    fm, _, _ = split_front_matter((REPO_ROOT / "platform/bring-your-own-data/README.md").read_text(encoding="utf-8"))
    rows = [r for r in _table_rows(_block("platform")) if r[0] == "PB-11"]
    assert len(rows) == 1
    assert fm["title"] in rows[0][1]
    assert rows[0][2] == fm["one_liner"]


def test_evidence_summary_dated():
    checked = FACTS["checked"]
    assert checked in _block("facts-stamp")
    assert f"Facts checked as of {checked}." in _block("facts-stamp")
    lead = _block("evidence-summary").strip().splitlines()[0]
    assert checked in lead


def test_proposal_no_planning_ids():
    from tools.guards.patterns import PLANNING_ID_PATTERNS

    text = _proposal_text()
    for pattern in PLANNING_ID_PATTERNS:
        assert not re.search(pattern, text), pattern
    assert not re.search(r"\bPhase \d", text, re.I)
