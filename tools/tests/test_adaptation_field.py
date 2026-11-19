"""The adaptation field on every use case, tied to the page text and to PB-11.

Every use-case page records, in front matter, how far up the adaptation
ladder it climbs (rung), which operator expertise it needs, and the items the
operator brings. These tests tie that field to what the page says: a page
with the Classification slot retrains its head; only the alarm triage and CNF
upgrade recipes may train a LoRA adapter, and only after a measured gap; a page
that names MCP tools needs skills and tool contracts. The generator (tools/site/render_bring)
reads owners and anchors from the PB-11 matrix; the tests read PB-11 on their
own and check the Owner cell against every listed domain.
"""

from __future__ import annotations

import re

import pytest

from tools.bplint.slug import heading_slugs
from tools.site.render_bring import (
    CHANGE_OF_RUNG,
    DOMAIN_NAMES,
    EXPERTISE_LABELS,
    EXPERTISE_ORDER,
    MECHANISM_NAMES,
    PB11,
    RUNG_LABELS,
    RUNG_ORDER,
    block,
    bring_summary,
    matrix,
)
from tools.tests.test_reference_pages import body, front_matter
from tools.tests.test_use_case_pages import _id, page_key, use_case_pages

PAGES = pytest.mark.parametrize("path", use_case_pages(), ids=_id)
ALARM_TRIAGE = "network-operations/alarm-triage-adaptation"
CNF_UPGRADE = "agentic-operations/cnf-upgrade-checks"
LORA_PAGES = {ALARM_TRIAGE, CNF_UPGRADE}
URL = re.compile(r"\(https?://[^)]*\)|https?://\S+")
RETRAIN_HEAD = re.compile(
    r"(?i)retrain\w*[^.\n|]{0,40}classification head|classification head[^.\n|]{0,60}retrain|head (?:is )?retrained"
)
# A model-card fact about the OTel rerankers, not an operator fine-tune.
CARD_FACT = re.compile(r"(?i)one-label head|full fine-tune of qwen3")
EXPECTED_COUNTS = {"retrieval": 7, "skills": 6, "retrieval-and-skills": 6, "head-retrain": 8, "lora-if-gap": 2}


def _ad(path) -> dict:
    return (front_matter(path) or {}).get("adaptation") or {}


def _slots(path) -> set[str]:
    return set((front_matter(path) or {}).get("otel_slots") or [])


def _no_url(path) -> str:
    return URL.sub("", body(path))


@PAGES
def test_adaptation_field_present(path):
    ad = _ad(path)
    assert ad.get("rung") in RUNG_ORDER, ad
    assert ad.get("expertise"), ad


@PAGES
def test_classification_pages_retrain_the_head(path):
    retrains = _ad(path).get("rung") in {"head-retrain", "lora-if-gap"}
    assert ("classification" in _slots(path)) == retrains, (sorted(_slots(path)), _ad(path).get("rung"))
    if retrains:
        assert RETRAIN_HEAD.search(_no_url(path)), "the page must say the Classification head is retrained"


def _how_it_works(key: str) -> tuple[str, str]:
    page = next(p for p in use_case_pages() if page_key(p) == key)
    text = body(page)
    how = re.search(r"^## How it works[ \t]*$(.*?)(?=^## )", text, re.M | re.S)
    assert how, key
    return text, how.group(1)


def test_lora_if_gap_pages():
    lora = {page_key(p) for p in use_case_pages() if _ad(p).get("rung") == "lora-if-gap"}
    assert lora == LORA_PAGES
    text, how = _how_it_works(ALARM_TRIAGE)
    assert re.search(r"^### When to train a LoRA", how, re.M)
    assert "../../../platform/adaptation/README.md" in text
    text, how = _how_it_works(CNF_UPGRADE)
    harness = re.search(r"^### Harness[ \t]*$(.*?)(?=^### |\Z)", how, re.M | re.S)
    assert harness, "the CNF upgrade recipe needs a Harness H3 under How it works"
    lora_rows = [ln for ln in harness.group(1).splitlines() if ln.startswith("| LoRA |")]
    assert len(lora_rows) == 1 and "measured" in lora_rows[0] and "gap" in lora_rows[0], lora_rows
    assert "../../../platform/adaptation/README.md" in text


@PAGES
def test_no_lora_below_the_rung(path):
    if _ad(path).get("rung") == "lora-if-gap":
        return
    assert "LoRA" not in _no_url(path)


@PAGES
def test_no_model_change_pages_name_no_retrain(path):
    if _ad(path).get("rung") not in {"retrieval", "skills", "retrieval-and-skills"}:
        return
    for line in _no_url(path).splitlines():
        assert not re.search(r"(?i)retrain", line), line
        if re.search(r"(?i)fine-tun", line):
            assert CARD_FACT.search(line), line


@PAGES
def test_mcp_pages_reach_skills(path):
    ad = _ad(path)
    names_mcp = "MCP" in _no_url(path)
    if names_mcp:
        assert ad.get("rung") != "retrieval"
        assert "tool-contracts" in (ad.get("expertise") or [])
    elif "classification" not in _slots(path):
        assert ad.get("rung") == "retrieval"


@PAGES
def test_expertise_follows_slots(path):
    exp = set(_ad(path).get("expertise") or [])
    slots = _slots(path)
    assert ("taxonomy" in exp) == ("classification" in slots)
    assert ("gate-labels" in exp) == ("decision" in slots)
    assert ("corpus" in exp) == ("embedding" in slots)
    assert "golden-set" in exp


@PAGES
def test_rung_text_names_retrieval_only_with_the_embedding_slot(path):
    """The generated rung text, the proposal row, and the explorer label say retrieval only when the page retrieves."""
    from tools.site.render_bring import RUNG_PAGE_TEXT

    retrieves = "embedding" in _slots(path)
    m = BLOCK.search(body(path))
    assert m, "no generated block"
    summary = next(ln for ln in m.group(1).splitlines() if ln.startswith("| ") and not ln.startswith("| Model change |"))
    model_change = summary.strip().strip("|").split("|")[0]
    rung = _ad(path).get("rung")
    link = "../catalog/" + page_key(path) + "/README.md)"
    proposal = (PB11.parents[2] / "proposal/index.md").read_text(encoding="utf-8")
    row = next(ln for ln in proposal.splitlines() if ln.startswith("| [") and link in ln and "You bring:" in ln)
    bring_cell = row.strip().strip("|").split("|")[-1].split(". You bring:")[0]
    for text in (model_change, RUNG_LABELS[rung], bring_cell):
        # "after retrieval and skills" is the LoRA rule on the ladder, not a claim that this page retrieves
        claim = text.split("after retrieval")[0]
        assert ("retrieval" in claim.lower()) == retrieves or rung in {"head-retrain", "lora-if-gap"}, (
            rung,
            sorted(_slots(path)),
            text,
        )
    assert RUNG_PAGE_TEXT[rung].split(":")[0] in model_change


def test_rung_counts():
    counts = {r: 0 for r in RUNG_ORDER}
    for p in use_case_pages():
        counts[_ad(p).get("rung")] = counts.get(_ad(p).get("rung"), 0) + 1
    assert counts == EXPECTED_COUNTS
    assert sum(counts.values()) == 29


def test_matrix_reader():
    mx = matrix(PB11)
    assert len(mx) == len(DOMAIN_NAMES) * len(MECHANISM_NAMES) == 42
    text = PB11.read_text(encoding="utf-8")
    slugs = heading_slugs(m.group(1) for m in re.finditer(r"^#{1,6} (.+)$", text, re.M))
    for key, cell in mx.items():
        assert cell["owner"].strip(), key
        assert cell["anchor"] in slugs, (key, cell["anchor"])
    assert mx[("ran", "rag-corpus")]["anchor"] == "domain-ran"
    assert mx[("vran-oran", "tool-contract")]["anchor"] == "domain-vran-and-o-ran"


FIXTURE_FM = {
    "adaptation": {
        "rung": "skills",
        "expertise": ["tool-contracts", "golden-set"],
        "bring": [
            {"item": "Router guides", "domains": ["transport-ip", "core-cnf"], "mechanism": "skill-manifest"},
            {"item": "Read-only device tools", "domains": ["transport-ip"], "mechanism": "tool-contract"},
        ],
    }
}


def test_bring_summary():
    assert bring_summary(FIXTURE_FM) == (
        f"{RUNG_LABELS['skills']}. You bring: "
        f"{EXPERTISE_LABELS['golden-set']}, {EXPERTISE_LABELS['tool-contracts']}"
    )
    assert EXPERTISE_ORDER.index("golden-set") < EXPERTISE_ORDER.index("tool-contracts")


def _pb11_owners(domains: list[str], mechanism: str) -> dict[str, str]:
    """{domain name: Owner cell}, read straight from each '### Domain:' table on PB-11, not via the generator."""
    text = PB11.read_text(encoding="utf-8")
    out = {}
    for d in domains:
        name = DOMAIN_NAMES[d]
        sec = re.search(rf"^### Domain: {re.escape(name)}[ \t]*$(.*?)(?=^#{{1,3}} |\Z)", text, re.M | re.S)
        assert sec, name
        rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in sec.group(1).splitlines() if ln.startswith("|")]
        col = rows[0].index("Owner")
        row = next(r for r in rows if r[0] == MECHANISM_NAMES[mechanism])
        out[name] = row[col]
    return out


def _owner_claims(cell: str, domains: list[str]) -> dict[str, str]:
    """What an Owner cell claims for each listed domain.

    A bare owner claims that owner for every listed domain. Otherwise the cell
    must be "Domain: owner" entries joined by "; ", one per listed domain.
    """
    names = [DOMAIN_NAMES[d] for d in domains]
    parts = [p.strip() for p in cell.split("; ")]
    if not any(p.startswith(f"{n}: ") for p in parts for n in names):
        return {n: cell for n in names}
    claims = {}
    for p in parts:
        name, _, owner = p.partition(": ")
        assert name in names and name not in claims, (cell, name)
        claims[name] = owner
    return claims


def test_owner_cell_names_every_domain_owner():
    """An item spanning domains with different PB-11 owners shows each domain's owner."""
    mx = matrix(PB11)
    fm = {
        "adaptation": {
            "rung": "retrieval",
            "expertise": ["golden-set", "corpus"],
            "bring": [
                {"item": "Mixed corpus", "domains": ["ran", "core-cnf", "customer-care"], "mechanism": "rag-corpus"},
                {"item": "Care corpus last", "domains": ["oss-bss", "customer-care"], "mechanism": "rag-corpus"},
                {"item": "Same owner", "domains": ["ran", "transport-ip"], "mechanism": "rag-corpus"},
            ],
        }
    }
    out = block(fm, mx)
    for item in fm["adaptation"]["bring"]:
        row = next(ln for ln in out.splitlines() if ln.startswith(f"| {item['item']} |"))
        owner = [c.strip() for c in row.strip().strip("|").split("|")][3]
        assert _owner_claims(owner, item["domains"]) == _pb11_owners(item["domains"], item["mechanism"]), row
    assert "data protection officer review" in next(ln for ln in out.splitlines() if "Care corpus last" in ln)
    same = next(ln for ln in out.splitlines() if ln.startswith("| Same owner |"))
    assert "| Operations engineer |" in same


def test_render_bring_block_shape():
    mx = matrix(PB11)
    out = block(FIXTURE_FM, mx)
    assert "| Model change | Your expertise | How far to climb |" in out
    assert "| Item | Network component | Mechanism | Owner | Matrix row |" in out
    assert "](../../../platform/adaptation/README.md)" in out
    assert out.count("../../../platform/bring-your-own-data/README.md#domain-") == 3
    assert "#domain-transport-and-ip" in out and "#domain-5g-core-cnfs" in out
    for item in FIXTURE_FM["adaptation"]["bring"]:
        row = next(ln for ln in out.splitlines() if ln.startswith(f"| {item['item']} |"))
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert _owner_claims(cells[3], item["domains"]) == _pb11_owners(item["domains"], item["mechanism"]), row
    assert "LoRA" not in out
    triage = {"adaptation": dict(FIXTURE_FM["adaptation"], rung="lora-if-gap")}
    assert "only if a measured gap remains" in block(triage, mx)


def test_change_of_rung_covers_every_rung():
    assert set(CHANGE_OF_RUNG) == set(RUNG_ORDER) == set(RUNG_LABELS)


# ---------- bring items, the generated block, and the PB-03 and PB-11 links ----------

BLOCK = re.compile(r"<!-- generated:what-you-bring start -->\n(.*?)<!-- generated:what-you-bring end -->", re.S)
BRING_H3 = re.compile(r"^### What you bring[ \t]*$", re.M)
MUST_ADD_H3 = re.compile(r"^### What you must add[ \t]*$", re.M)
GATE_ROW = re.compile(r"^\|[^|\n]+\|[^|\n]*\b(?:NOTIFY|REVIEW)\b", re.M)
MATRIX_LINK = re.compile(r"\]\(\.\./\.\./\.\./platform/bring-your-own-data/README\.md#([a-z0-9-]+)\)")
NEW_RECIPES = (
    "network-operations/core-network-rca",
    "network-operations/ran-energy-saving",
    "network-operations/slice-sla-assurance",
    "network-operations/mop-validation",
    "agentic-operations/site-change-risk-gate",
    "agentic-operations/cnf-upgrade-checks",
)
EXPERTISE_GAP = {
    "taxonomy": "taxonomy",
    "golden-set": "golden set",
    "gate-labels": "gate labels",
    "tool-contracts": "tool contract",
    "corpus": "corpus",
}


def _need(path) -> str:
    from tools.tests.test_use_case_pages import _raw_section

    return _raw_section(body(path), "What you need") or ""


def _governance_gate_rows(path) -> bool:
    from tools.tests.test_use_case_pages import _raw_section

    gov = _raw_section(body(path), "Governance") or ""
    return any("Action" not in m.group(0) for m in GATE_ROW.finditer(gov))


@PAGES
def test_bring_items_follow_the_page(path):
    bring = _ad(path).get("bring") or []
    assert 3 <= len(bring) <= 8, len(bring)
    mechs = {b["mechanism"] for b in bring}
    slots = _slots(path)
    if "classification" in slots:
        assert "classification-labels" in mechs
    if "embedding" in slots:
        assert "rag-corpus" in mechs
    if "MCP" in _no_url(path):
        assert "tool-contract" in mechs
    if "decision" in slots or _governance_gate_rows(path):
        assert "gate-policy" in mechs
    if "lora-data" in mechs:
        assert page_key(path) in LORA_PAGES


@PAGES
def test_every_page_has_the_bring_block(path):
    need = _need(path)
    heads = list(BRING_H3.finditer(need))
    assert len(heads) == 1, "What you need needs exactly one '### What you bring' H3"
    after = need[heads[0].end() :]
    nxt = re.search(r"^#{2,3} ", after, re.M)
    sub = after[: nxt.start()] if nxt else after
    assert sub.count("<!-- generated:what-you-bring start -->") == 1
    assert sub.count("<!-- generated:what-you-bring end -->") == 1
    assert body(path).count("<!-- generated:what-you-bring start -->") == 1
    must = MUST_ADD_H3.search(need)
    if must:
        assert heads[0].start() < must.start(), "the bring block comes before What you must add"


def test_bring_blocks_current():
    from tools.site import render_bring

    assert render_bring.main(["--check"]) == 0
    with pytest.raises(SystemExit):
        render_bring.main(["--allow-missing"])  # the Task 1 escape hatch is gone


@PAGES
def test_bring_owner_and_link_match_matrix(path):
    mx = matrix(PB11)
    m = BLOCK.search(body(path))
    assert m, "no generated block"
    headers = ("| Item |", "| Model change |")
    rows = [ln for ln in m.group(1).splitlines() if ln.startswith("| ") and not ln.startswith(headers)]
    items = _ad(path).get("bring") or []
    item_rows = rows[1:]  # rows[0] is the summary row
    assert len(item_rows) == len(items)
    slugs = heading_slugs(
        mm.group(1) for mm in re.finditer(r"^#{1,6} (.+)$", PB11.read_text(encoding="utf-8"), re.M)
    )
    for row, item in zip(item_rows, items):
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert cells[0] == item["item"]
        assert _owner_claims(cells[3], item["domains"]) == _pb11_owners(item["domains"], item["mechanism"]), row
        anchors = MATRIX_LINK.findall(cells[4])
        assert anchors == [mx[(d, item["mechanism"])]["anchor"] for d in item["domains"]], row
        assert all(a in slugs for a in anchors)


@PAGES
def test_every_page_lists_pb03_and_pb11(path):
    listed = (front_matter(path) or {}).get("platform_blueprints") or []
    assert "PB-03" in listed and "PB-11" in listed
    assert listed == sorted(listed)


@pytest.mark.parametrize("key", NEW_RECIPES)
def test_new_recipes_must_add_table(key):
    from tools.tests.test_use_case_pages import language_row_problems, must_add_problems, must_add_table

    path = next(p for p in use_case_pages() if page_key(p) == key)
    text = body(path)
    assert must_add_problems(text) == []
    assert language_row_problems(text) == []
    gaps = " ".join(r[0].lower() for r in must_add_table(text)[1:])
    for exp in _ad(path).get("expertise") or []:
        assert EXPERTISE_GAP[exp] in gaps, (exp, gaps)


@PAGES
def test_bring_block_adds_no_prose_words(path):
    from tools.bplint.markdown import parse_doc

    raw = path.read_text(encoding="utf-8")
    stripped = BLOCK.sub("<!-- generated:what-you-bring start -->\n<!-- generated:what-you-bring end -->", raw)
    assert stripped != raw

    def words(text):
        return sum(s.prose_words for s in parse_doc(path, text).sections)

    assert words(raw) == words(stripped)
