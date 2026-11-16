"""PB-11 Bring your own data and policies: matrix, how-to, link, and framing checks.

The shared platform checks in test_platform_pages.py also run on this page.
"""

from __future__ import annotations

import re

from tools.bplint.loader import load_yaml
from tools.bplint.slug import github_slug, heading_slugs
from tools.tests.conftest import REPO_ROOT
from tools.tests.test_platform_pages import (
    ACCEPTANCE,
    ALLOWED_ROLES,
    INTEGRATION,
    WORD_NUMBER,
    _h3_text,
    reference_design_text,
    section_text,
)
from tools.tests.test_reference_pages import (
    LAYER_CODE,
    PRODUCT_TERMS,
    body,
    front_matter,
    mermaid_fences,
    tables,
)
from tools.tests.test_use_case_pages import USE_CASES_BULLET, use_case_dependants

BYO = REPO_ROOT / "platform/bring-your-own-data/README.md"
COURSES = REPO_ROOT / "tools/bplint/agent-school-courses.yaml"

MECHANISMS = [
    "RAG corpus",
    "Skill or capability manifest",
    "MCP tool contract",
    "Gate and action-layer policy",
    "Classification labels",
    "LoRA training data",
]
CONFIGURE_OR_TRAIN = ["configure"] * 4 + ["train"] * 2
MECHANISMS_HEADER = [
    "Mechanism",
    "Configure or train",
    "What it changes",
    "Where it goes in the harness",
    "Platform page",
]
DOMAINS = [
    "RAN",
    "vRAN and O-RAN",
    "5G core CNFs",
    "VNFs",
    "Transport and IP",
    "OSS and BSS",
    "Customer and care",
]
DOMAIN_ANCHORS = [
    "domain-ran",
    "domain-vran-and-o-ran",
    "domain-5g-core-cnfs",
    "domain-vnfs",
    "domain-transport-and-ip",
    "domain-oss-and-bss",
    "domain-customer-and-care",
]
DOMAIN_HEADER = [
    "Mechanism",
    "What you bring",
    "Format",
    "Where it goes in the harness",
    "Owner",
    "PB-02 gate that checks it",
    "When to redo or retrain",
]
# Gate names a domain row may cite: PB-02 parameters and ladder stages, the
# PB-02 suites, and the PB-05 conformance gate. Each must appear on its page.
GATE_NAMES = (
    "Embedding and Reranker recall-at-k floor",
    "LLM groundedness floor",
    "Safety abstain-recall floor",
    "Classification per-class recall floor",
    "Classification other-or-abstain recall floor",
    "Decision false-ACT budget",
    "Non-inferiority margin",
    "Operator offline acceptance",
    "trajectory suite",
    "gate set",
    "Conformance Test Kit",
)
LINKED_PAGES = (
    "../evaluation-acceptance/README.md",
    "../adaptation/README.md",
    "../integration/README.md",
    "../safety-autonomy-gating/README.md",
    "../action-layer/README.md",
    "../compliance-operating-model/README.md",
)


def _md_tables(text: str) -> list[list[list[str]]]:
    from tools.tests.test_reference_pages import _md

    return tables(_md().parse(text))


def _plain(cell: str) -> str:
    """Cell text with Markdown links reduced to their labels."""
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)


def _mechanisms_table() -> list[list[str]]:
    tbls = _md_tables(_h3_text(reference_design_text(BYO), "Mechanisms"))
    assert tbls, "Mechanisms has no table"
    return tbls[0]


def _matrix_table() -> list[list[str]]:
    tbls = _md_tables(_h3_text(reference_design_text(BYO), "Matrix"))
    assert tbls, "Matrix has no table"
    return tbls[0]


def _domain_tables() -> dict[str, list[list[str]]]:
    rd = reference_design_text(BYO)
    out = {}
    for name in DOMAINS:
        tbls = _md_tables(_h3_text(rd, f"Domain: {name}"))
        assert len(tbls) == 1, (name, len(tbls))
        out[name] = tbls[0]
    return out


def _column(table: list[list[str]], name: str) -> list[str]:
    i = table[0].index(name)
    return [row[i] for row in table[1:]]


def test_byo_front_matter():
    fm = front_matter(BYO) or {}
    assert fm.get("id") == "PB-11"
    assert fm.get("type") == "platform"
    assert fm.get("title") == "Bring your own data and policies"
    assert fm.get("otel_slots") == ["llm", "embedding", "reranker", "safety", "decision",
                                    "classification"]
    assert fm.get("placement_tier") == ["regional", "core"]
    assert "table1_rows" not in fm and "extension_rows" not in fm
    pinned = set((load_yaml(COURSES) or {}).get("courses", {}))
    assert fm.get("agent_school") and set(fm["agent_school"]) <= pinned, fm.get("agent_school")


def test_byo_mechanisms_table():
    table = _mechanisms_table()
    assert table[0] == MECHANISMS_HEADER
    rows = table[1:]
    assert [r[0] for r in rows] == MECHANISMS
    assert [r[1].lower() for r in rows] == CONFIGURE_OR_TRAIN
    lora = " ".join(rows[-1])
    assert "measured gap" in lora and "retrieval and skills" in lora, lora
    assert "../adaptation/README.md" in lora, lora


def test_byo_matrix_domains_by_mechanisms():
    table = _matrix_table()
    assert table[0] == ["Domain", *MECHANISMS]
    rows = table[1:]
    assert [_plain(r[0]) for r in rows] == DOMAINS
    for row, anchor in zip(rows, DOMAIN_ANCHORS, strict=True):
        assert f"(#{anchor})" in row[0], row[0]
        assert all(cell.strip() for cell in row), row


def test_byo_domain_tables():
    for name, table in _domain_tables().items():
        assert table[0] == DOMAIN_HEADER, name
        rows = table[1:]
        assert [r[0] for r in rows] == MECHANISMS, name
        for row in rows:
            assert all(cell.strip() for cell in row), (name, row)
        lora = " ".join(rows[-1])
        assert "measured gap" in lora, (name, lora)


def test_byo_owners_are_generic():
    for name, table in _domain_tables().items():
        for cell in _column(table, "Owner"):
            text = re.sub(r"\s*\(SME\)", "", cell).replace(" review", "")
            for role in re.split(r",\s*with\s+|\s+with\s+|,\s*and\s+|,\s*|\s+and\s+", text):
                role = role.strip().lower()
                if role:
                    assert role in ALLOWED_ROLES, (name, cell, role)


def test_byo_gates_name_pb02():
    sources = body(ACCEPTANCE) + body(INTEGRATION)
    for gate in GATE_NAMES:
        assert gate.lower() in sources.lower(), gate
    for name, table in _domain_tables().items():
        for cell in _column(table, "PB-02 gate that checks it"):
            assert any(g.lower() in cell.lower() for g in GATE_NAMES), (name, cell)


def test_byo_redo_cells_have_no_values():
    for name, table in _domain_tables().items():
        for cell in _column(table, "When to redo or retrain"):
            assert not re.search(r"\d", cell), (name, cell)
            assert not WORD_NUMBER.search(cell), (name, cell)


def test_byo_harness_definition():
    rd = reference_design_text(BYO)
    sentence = next(
        (s for s in re.split(r"(?<=\.)\s+", rd) if "harness" in s and "agent runtime" in s), ""
    )
    assert sentence, "no sentence defines the harness"
    assert "../../architecture/index.md" in sentence, sentence
    assert "not agent-school's harness" in sentence, sentence


def test_byo_links_platform_pages():
    text = body(BYO)
    for link in LINKED_PAGES:
        assert link in text, link
    matrix = _h3_text(reference_design_text(BYO), "Matrix")
    assert "../evaluation-acceptance/README.md" in matrix


def test_byo_anchors_stable():
    titles = re.findall(r"^#{2,3} (.+?)\s*$", body(BYO), re.M)
    domains = [t for t in titles if t.startswith("Domain: ")]
    assert [github_slug(t) for t in domains] == DOMAIN_ANCHORS
    slugs = heading_slugs(titles)
    assert "mechanisms" in slugs and "matrix" in slugs


def test_byo_diagram_capabilities():
    fence = mermaid_fences(body(BYO))[0]
    for want in ("Configure", "Train", "Evaluation gate", "measured gap"):
        assert want in fence, want
    assert PRODUCT_TERMS.findall(fence) == []
    assert not LAYER_CODE.search(fence)


def test_byo_configure_before_train_in_example():
    example = _h3_text(reference_design_text(BYO), "Worked example: alarm and root-cause triage")
    for want in ("inc-6610", "byo-triage-agent", "Classification", "measured gap"):
        assert want in example, want


def test_byo_no_use_cases_bullet_yet():
    section = section_text(BYO, "Used by and next steps")
    if not use_case_dependants().get("PB-11"):
        assert USE_CASES_BULLET.findall(section) == []


def test_byo_back_links():
    for page in ("adaptation", "integration"):
        section = section_text(REPO_ROOT / f"platform/{page}/README.md", "Used by and next steps")
        assert "../bring-your-own-data/README.md" in section, page
