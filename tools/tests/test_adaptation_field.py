"""The adaptation field on every use case, tied to the page text and to PB-11.

Every use-case page records, in front matter, how far up the adaptation
ladder it climbs (rung), which operator expertise it needs, and the items the
operator brings. These tests tie that field to what the page says: a page
with the Classification slot retrains its head; only the alarm triage recipe
may train a LoRA adapter, and only after a measured gap; a page that names MCP
tools needs skills and tool contracts. The generator (tools/site/render_bring)
reads owners and anchors from the PB-11 matrix, so the page table cannot
disagree with PB-11.
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
F3 = "network-operations/alarm-triage-adaptation"
URL = re.compile(r"\(https?://[^)]*\)|https?://\S+")
RETRAIN_HEAD = re.compile(
    r"(?i)retrain\w*[^.\n|]{0,40}classification head|classification head[^.\n|]{0,60}retrain|head (?:is )?retrained"
)
# A model-card fact about the OTel rerankers, not an operator fine-tune.
CARD_FACT = re.compile(r"(?i)one-label head|full fine-tune of qwen3")
EXPECTED_COUNTS = {"retrieval": 6, "skills": 11, "head-retrain": 8, "lora-if-gap": 1}


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


def test_only_f3_is_lora_if_gap():
    lora = [page_key(p) for p in use_case_pages() if _ad(p).get("rung") == "lora-if-gap"]
    assert lora == [F3]
    f3 = next(p for p in use_case_pages() if page_key(p) == F3)
    text = body(f3)
    how = re.search(r"^## How it works[ \t]*$(.*?)(?=^## )", text, re.M | re.S)
    assert how and re.search(r"^### When to train a LoRA", how.group(1), re.M)
    assert "../../../platform/adaptation/README.md" in text


@PAGES
def test_no_lora_below_the_rung(path):
    if _ad(path).get("rung") == "lora-if-gap":
        return
    assert "LoRA" not in _no_url(path)


@PAGES
def test_no_model_change_pages_name_no_retrain(path):
    if _ad(path).get("rung") not in {"retrieval", "skills"}:
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


def test_rung_counts():
    counts = {r: 0 for r in RUNG_ORDER}
    for p in use_case_pages():
        counts[_ad(p).get("rung")] = counts.get(_ad(p).get("rung"), 0) + 1
    assert counts == EXPECTED_COUNTS
    assert sum(counts.values()) == 26


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
        assert f"| {mx[(item['domains'][0], item['mechanism'])]['owner']} |" in row, row
    assert "LoRA" not in out
    f3 = {"adaptation": dict(FIXTURE_FM["adaptation"], rung="lora-if-gap")}
    assert "only if a measured gap remains" in block(f3, mx)


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
        assert page_key(path) == F3


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
        assert cells[3] == mx[(item["domains"][0], item["mechanism"])]["owner"], row
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
