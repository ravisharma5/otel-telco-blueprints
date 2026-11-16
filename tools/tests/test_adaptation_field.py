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
