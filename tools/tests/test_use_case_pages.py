"""Use-case blueprint pages: shared checks and platform sync tests.

Each shared check runs on every catalog/<domain>/<slug>/README.md. The sync
tests read facts from the platform pages at run time (serving flags, the gate
rule, the stage table, parameter names and owners, RACI rows) and compare each
use-case page against them, so a recipe cannot drift from the platform page it
copies. The "present" tests prove each source still parses today. With no
use-case pages yet, the per-page checks collect as skipped and the
expected-pages guard compares two empty maps.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.guards.patterns import PLANNING_ID_RE
from tools.tests.conftest import REPO_ROOT
from tools.tests.test_open_source_framing import STANDARD_LINE
from tools.tests.test_platform_pages import (
    ADAPTATION,
    ALLOWED_ROLES,
    BLOG_URL,
    CODE_FENCE,
    DECISION_CARD,
    DEMOTE,
    EXPECTED_PLATFORM_PAGES,
    GATING,
    INTEGRATION,
    ISO_QUOTED,
    ISSUE_URL,
    LEGAL_CONCLUSION,
    MERMAID_FENCE,
    MILLISECONDS,
    MIN_SOURCES_ROWS,
    NO_DEMOTE,
    NOTIFY_GATE_PAGE,
    NOTIFY_OLD_PHRASES,
    PARAM_TABLE_HEADER,
    RAW_FRONT_MATTER,
    SERVING,
    STAGE_HEADER,
    TELECOM_ROLE,
    VENDOR_TERMS_URL,
    _h3_text,
    _id,
    _ordered_steps,
    _rnj_sentence_problem,
    _sentences,
    _units,
    notify_edge_problems,
    notify_sections_without_gate_link,
    page_tables,
    param_table_problems,
    platform_pages,
    section_text,
    table_with_header,
)
from tools.tests.test_reference_pages import (
    LAYER_CODE,
    PRODUCT_TERMS,
    blueprint_pages,
    body,
    front_matter,
    mermaid_fences,
    sections,
    tables,
)

# Grows by one entry per landed use case ({"<domain>/<slug>": id}), so a lost
# or renamed page fails here instead of quietly dropping out of every check.
EXPECTED_USE_CASE_PAGES: dict[str, str] = {
    "standards-knowledge/grounded-knowledge-assistant": "UC-KNOW-01",
    "agentic-operations/closed-loop-incident-handling": "UC-AGOPS-01",
    "network-operations/alarm-triage-adaptation": "UC-OPS-01",
}

# Parameters a use case may name that no platform page defines
# ({"<domain>/<slug>": {name: owner}}). Add a name here only with an allowed
# role as owner, and never give it a default value on the page.
USE_CASE_LOCAL_PARAMS: dict[str, dict[str, str]] = {
    "standards-knowledge/grounded-knowledge-assistant": {"Decision routing threshold": "Model owner"},
}

UC_ID = re.compile(r"^UC-[A-Z]+-[0-9]{2}$")
ROADMAP_URL = "https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md"
# OTel slot -> the header line prefix of its block in the serving page flag fence.
SLOT_BLOCK = {
    "llm": "# LLM 31B",
    "decision": "# Decision",
    "classification": "# Classification",
    "reranker": "# Classification",
    "embedding": "# Embedding",
}
PB_SLUG = {pb: slug for slug, pb in EXPECTED_PLATFORM_PAGES.items()}
PLATFORM_LINK = re.compile(r"\.\./\.\./\.\./platform/([a-z0-9-]+)/README\.md")
EVALUATION_LINK = "../../../platform/evaluation-acceptance/README.md"
INTEGRATION_LINK = "../../../platform/integration/README.md"
RACI_HEADER = ["Activity", "Responsible", "Accountable", "Consulted", "Informed"]
VERIFY_HEADER = ["Check", "PB-02 gate or parameter", "Owner"]
FLAG = re.compile(r"(?<![\w-])--[a-z][a-z0-9-]*")
# Ids from the platform worked example; each recipe uses its own.
REUSED_EXAMPLE_IDS = ("inc-2041", "noc-triage-agent", "req-0001", "dec-0001")
# Ofcom's drama range for UK mobiles: the only phone numbers a page may show.
OFCOM_DRAMA = re.compile(r"\+44 ?7700 ?900\d{3}\b")
PHONE_LIKE = re.compile(r"\+\d[\d ]{7,16}\d")
# Identifiers whose digits are not results in a verification table.
SAFE_VERIFY_ID = re.compile(r"PB-\d{2}|TMF\d{3}|Level \d|\b2\.[05]\b")


# ---------- helpers ----------


def use_case_pages() -> list[Path]:
    """Blueprint pages under catalog/ (platform pages are excluded)."""
    return [p for p in blueprint_pages() if p.relative_to(REPO_ROOT).parts[0] == "catalog"]


def page_key(path: Path) -> str:
    """"<domain>/<slug>" for a catalog page."""
    return "/".join(path.parent.relative_to(REPO_ROOT / "catalog").parts)


def phone_number_problems(text: str) -> list[str]:
    """Every phone-number-like string outside the Ofcom drama range."""
    return [m for m in PHONE_LIKE.findall(text) if not OFCOM_DRAMA.fullmatch(m.strip())]


def normalise_owner(text: str) -> str:
    """Owner text with the acronym expansion folded, so first and later mentions match."""
    return re.sub(r"\s+", " ", text.replace("subject-matter expert (SME)", "SME")).strip()


def role_tokens(cell: str) -> list[str]:
    """Lowercased role names in a RACI or owner cell.

    Splits on commas, "and", and "or", and drops articles, a "with ... review"
    wrapper, and a trailing "role", so "Risk owner, with SME review" gives
    ["risk owner", "sme"].
    """
    out = []
    for part in re.split(r",|\band\b|\bor\b", normalise_owner(cell).lower()):
        part = re.sub(r"^(with|an?|the)\s+", "", part.strip())
        part = re.sub(r"\s+(review|roles?)$", "", part).strip()
        if part:
            out.append(part)
    return out


def pb04_flag_blocks() -> dict[str, list[str]]:
    """Header line -> flag lines, from the serving page "Key flags per slot" fence."""
    sec = section_text(SERVING, "Reference design")
    fence = CODE_FENCE.search(sec[sec.index("### Key flags per slot") :]).group(1)
    blocks: dict[str, list[str]] = {}
    current = None
    for line in fence.splitlines():
        if line.startswith("#"):
            current = line.rstrip()
            blocks[current] = []
        elif line.strip() and current:
            blocks[current].append(line.rstrip())
    return blocks


def adapter_fence_flags() -> set[str]:
    """Flags in the adaptation page "Adapter serving and security" fence."""
    text = _h3_text(section_text(ADAPTATION, "Reference design"), "Adapter serving and security")
    return set(FLAG.findall(CODE_FENCE.search(text).group(1)))


def platform_flags() -> set[str]:
    """Every flag a use-case page may use: the serving fence plus the adapter fence."""
    lines = [ln for block in pb04_flag_blocks().values() for ln in block]
    return set(FLAG.findall("\n".join(lines))) | adapter_fence_flags()


def decision_engine_prerequisite() -> str:
    """The serving page prerequisite cell for the Decision slot engine."""
    table = table_with_header(SERVING, "Reference design", ["Prerequisite", "Source"])
    col = table[0].index("Prerequisite")
    return next(row[col] for row in table[1:] if row[0] == "Decision slot engine")


def gate_rule_sentences() -> list[str]:
    """The first two sentences of the gating page "Gate rules"."""
    text = re.sub(r"\s+", " ", _h3_text(section_text(GATING, "Reference design"), "Gate rules"))
    return re.split(r"(?<=[.!?])\s+", text.strip())[:2]


def stage_targets() -> dict[str, str | None]:
    """Autonomy ceiling -> "Level N", or None where the scenario keeps its level."""
    table = table_with_header(GATING, "Reference design", STAGE_HEADER)
    ceiling = STAGE_HEADER.index("Autonomy ceiling")
    target = STAGE_HEADER.index("TM Forum target")
    out: dict[str, str | None] = {}
    for row in table[1:]:
        key = row[ceiling].split(",")[0].strip()
        m = re.search(r"\bLevel \d\b", row[target])
        out[key] = m.group(0) if m else None
    return out


def platform_params() -> dict[str, str]:
    """Parameter name -> normalised owner, over platform pages and the gate page."""
    out: dict[str, str] = {}
    for page in [*platform_pages(), NOTIFY_GATE_PAGE]:
        for table in page_tables(page):
            if set(PARAM_TABLE_HEADER) <= set(table[0]):
                who = table[0].index("Who sets it")
                for row in table[1:]:
                    out[row[0]] = normalise_owner(row[who])
    return out


def platform_raci_rows() -> dict[str, list[list[str]]]:
    """Activity -> every normalised RACI row with that activity on a platform page."""
    out: dict[str, list[list[str]]] = {}
    for page in platform_pages():
        for table in page_tables(page):
            if table[0][: len(RACI_HEADER)] == RACI_HEADER:
                for row in table[1:]:
                    out.setdefault(row[0], []).append([normalise_owner(c) for c in row])
    return out


def raci_tables(path: Path) -> list[list[list[str]]]:
    return [t for t in page_tables(path) if t[0][:3] == RACI_HEADER[:3]]


def param_tables(path: Path) -> list[list[list[str]]]:
    return [t for t in page_tables(path) if set(PARAM_TABLE_HEADER) <= set(t[0])]


def known_params(path: Path) -> dict[str, str]:
    local = {k: normalise_owner(v) for k, v in USE_CASE_LOCAL_PARAMS.get(page_key(path), {}).items()}
    return {**platform_params(), **local}


def verification_table(path: Path) -> list[list[str]]:
    for table in tables(sections(body(path)).get("Deploy and verify", [])):
        if table[0][: len(VERIFY_HEADER)] == VERIFY_HEADER:
            return table
    raise AssertionError(f"{_id(path)}: no verification table {VERIFY_HEADER} in Deploy and verify")


def page_code(path: Path) -> str:
    """Code fence contents on the page, Mermaid left out."""
    return "\n".join(CODE_FENCE.findall(MERMAID_FENCE.sub("", body(path))))


def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


PAGES = pytest.mark.parametrize("path", use_case_pages(), ids=_id)


# ---------- shared checks ----------


def test_shared_expected_pages():
    found = {page_key(p): (front_matter(p) or {}).get("id") for p in use_case_pages()}
    assert found == EXPECTED_USE_CASE_PAGES


@pytest.mark.parametrize(
    ("text", "ok"),
    [
        ("Call +44 7700 900123 to test.", True),
        ("Subscriber +447700900999 is fictional.", True),
        ("No number here.", True),
        ("Call +44 7911 123456.", False),
        ("Call +1 202 555 0100.", False),
        ("Call +49 151 12345678.", False),
    ],
)
def test_shared_fictitious_number_rule_cases(text, ok):
    assert (phone_number_problems(text) == []) is ok, phone_number_problems(text)


@PAGES
def test_shared_front_matter(path):
    fm = front_matter(path) or {}
    assert fm.get("type") == "use-case"
    assert fm.get("flagship") is True
    assert UC_ID.match(str(fm.get("id", ""))), fm.get("id")
    assert not PLANNING_ID_RE.search(str(fm.get("id", ""))), fm.get("id")


@PAGES
def test_shared_one_mermaid_fence_in_how_it_works(path):
    assert len(mermaid_fences(body(path))) == 1
    assert len(mermaid_fences(section_text(path, "How it works"))) == 1


@PAGES
def test_shared_mermaid_capability_names(path):
    fence = mermaid_fences(body(path))[0]
    assert PRODUCT_TERMS.findall(fence) == []
    assert LAYER_CODE.findall(fence) == []


@PAGES
def test_shared_no_image_placeholder(path):
    text = body(path)
    assert "diagrams/" not in text
    assert "![" not in text


@PAGES
def test_shared_worked_example(path):
    lines = section_text(path, "How it works").splitlines()
    assert any(ln.startswith("### Worked example:") for ln in lines)


@PAGES
def test_shared_no_reused_example_ids(path):
    text = body(path)
    for old in REUSED_EXAMPLE_IDS:
        assert old not in text, old


@PAGES
def test_shared_parameter_tables_have_no_values(path):
    for table in param_tables(path):
        assert param_table_problems(table) == []


@PAGES
def test_shared_no_millisecond_numbers(path):
    assert MILLISECONDS.findall(body(path)) == []


@PAGES
def test_shared_done_page_has_quoted_review_date(path):
    fm = front_matter(path) or {}
    if fm.get("doc_status") != "done":
        pytest.skip("only done pages need a review date")
    m = RAW_FRONT_MATTER.match(path.read_text(encoding="utf-8"))
    assert m and ISO_QUOTED.search(m.group(1)), "clarity_reviewed must be a quoted ISO date"


@PAGES
def test_shared_sources_table_rows(path):
    tbls = tables(sections(body(path)).get("Sources", []))
    assert tbls, "Sources has no table"
    assert len(tbls[0]) - 1 >= MIN_SOURCES_ROWS


@PAGES
def test_shared_sources_basis_fits_the_source(path):
    """Issue reports are research, a model publisher's licence or terms are
    model card, and no row cites a page of this repository."""
    table = tables(sections(body(path)).get("Sources", []))[0]
    basis, source = table[0].index("Basis"), table[0].index("Source")
    for row in table[1:]:
        if ISSUE_URL.search(row[source]):
            assert row[basis] == "research", row
        if VENDOR_TERMS_URL.search(row[source]):
            assert row[basis] == "model card", row
        assert not re.search(r"\]\((?!https?:)[^)]*\.md", row[source]), row


@PAGES
def test_shared_sources_no_blog_under_project_documentation(path):
    table = tables(sections(body(path)).get("Sources", []))[0]
    basis, source = table[0].index("Basis"), table[0].index("Source")
    for row in table[1:]:
        if row[basis].strip().lower() == "project documentation":
            assert not BLOG_URL.search(row[source]), row[source]


@PAGES
def test_shared_standard_line(path):
    assert STANDARD_LINE in section_text(path, "What you need")


@PAGES
def test_shared_notify_mentions_link_the_gate(path):
    raw = body(path)
    if "NOTIFY" not in MERMAID_FENCE.sub("", raw):
        pytest.skip("page does not mention NOTIFY")
    assert notify_sections_without_gate_link(raw) == [], _id(path)
    text = flat(raw)
    for phrase in NOTIFY_OLD_PHRASES:
        assert phrase not in text, phrase
    for fence in mermaid_fences(raw):
        assert notify_edge_problems(fence) == []


@PAGES
def test_shared_generic_roles(path):
    assert TELECOM_ROLE.findall(body(path)) == []
    for table in raci_tables(path):
        for row in table[1:]:
            for cell in row[1:]:
                for role in role_tokens(cell):
                    assert role in ALLOWED_ROLES, (row[0], cell, role)


@PAGES
def test_shared_injection_never_drops_a_stage(path):
    for unit in _units(path):
        if re.search(r"(?i)injection", unit) and DEMOTE.search(unit):
            assert NO_DEMOTE.search(unit), unit


@PAGES
def test_shared_false_act_drop_needs_confirmation(path):
    for unit in _units(path):
        if re.search(r"false ACT", unit) and DEMOTE.search(unit):
            assert "confirmed" in unit, unit


@PAGES
def test_shared_rnj_not_called_gemma(path):
    problems = [p for p in map(_rnj_sentence_problem, _sentences(body(path))) if p]
    assert problems == [], problems


@PAGES
def test_shared_no_legal_conclusions(path):
    assert LEGAL_CONCLUSION.findall(CODE_FENCE.sub("", body(path))) == []


@PAGES
def test_shared_fictitious_numbers(path):
    assert phone_number_problems(body(path)) == []


@PAGES
def test_shared_runtime_adapter_rule(path):
    text = path.read_text(encoding="utf-8")
    assert "VLLM_ALLOW_RUNTIME_LORA_UPDATING=True" not in text
    for line in text.splitlines():
        if "VLLM_ALLOW_RUNTIME_LORA_UPDATING" in line:
            assert re.search(r"(?i)never|block", line), line


@PAGES
def test_shared_deploy_steps_and_checks(path):
    assert len(_ordered_steps(section_text(path, "Deploy and verify"))) >= 3
    table = verification_table(path)
    owner = table[0].index("Owner")
    assert len(table) > 1, "verification table has no rows"
    for row in table[1:]:
        roles = role_tokens(row[owner])
        assert roles and all(r in ALLOWED_ROLES for r in roles), row


@PAGES
def test_shared_deploy_verify_claims_no_results(path):
    assert "%" not in section_text(path, "Deploy and verify")
    for row in verification_table(path)[1:]:
        cells = SAFE_VERIFY_ID.sub("", " | ".join(row))
        assert not re.search(r"\d", cells), row


@PAGES
def test_links_platform_blueprints_and_agent_school(path):
    fm = front_matter(path) or {}
    text = body(path)
    listed = fm.get("platform_blueprints") or []
    for pb in listed:
        assert f"../../../platform/{PB_SLUG[pb]}/README.md" in text, pb
    linked = set(PLATFORM_LINK.findall(text))
    listed_slugs = {PB_SLUG[pb] for pb in listed}
    assert linked <= listed_slugs, sorted(linked - listed_slugs)
    assert fm.get("agent_school"), "agent_school is empty"
    assert ROADMAP_URL in section_text(path, "At a glance")
    assert ROADMAP_URL in section_text(path, "Deploy and verify")


# ---------- sync sources: each platform fact still parses ----------


def test_sync_flag_blocks_read_from_serving_page():
    blocks = pb04_flag_blocks()
    for prefix in ("# LLM 31B", "# Decision", "# Classification", "# Embedding", "# Static LoRA"):
        header = next((h for h in blocks if h.startswith(prefix)), None)
        assert header, prefix
        assert blocks[header], header


def test_sync_decision_engine_cell_present():
    assert decision_engine_prerequisite() == "vLLM 0.26 or later on CUDA, or 0.30 or later on ROCm"


def test_sync_gate_rule_sentences_present():
    sentences = gate_rule_sentences()
    assert len(sentences) == 2
    assert "policy ceiling" in sentences[0]
    assert sentences[1] == "A STOP label forces STOP at every stage."


def test_sync_deny_unless_allowed_row_present():
    table = table_with_header(INTEGRATION, "Reference design", ["Control", "What it does"])
    assert any(row[0] == "Deny unless allowed" for row in table[1:])


def test_sync_stage_table_present():
    assert stage_targets() == {
        "inform": None,
        "notify": "Level 1",
        "recommend-with-approval": "Level 2",
        "act-within-policy": "Level 3",
    }


def test_sync_platform_params_present():
    params = platform_params()
    assert len(params) >= 40
    assert "Minimum measured gap to train" in params
    assert "Safety abstain-recall floor" in params
    assert not any("subject-matter expert (SME)" in v for v in params.values())


def test_sync_platform_raci_rows_present():
    assert "Change a policy ceiling" in platform_raci_rows()


def test_sync_local_params_are_well_formed():
    params = platform_params()
    for key, entries in USE_CASE_LOCAL_PARAMS.items():
        assert key in EXPECTED_USE_CASE_PAGES, key
        for name, owner in entries.items():
            assert name not in params, f"{name} is a platform parameter; reuse it"
            roles = role_tokens(owner)
            assert roles and all(r in ALLOWED_ROLES for r in roles), (name, owner)


# ---------- sync checks per page ----------


@PAGES
def test_sync_flags_match_serving_page(path):
    code = page_code(path)
    blocks = pb04_flag_blocks()
    for slot in (front_matter(path) or {}).get("otel_slots", []):
        prefix = SLOT_BLOCK.get(slot)
        if not prefix:
            continue
        header = next(h for h in blocks if h.startswith(prefix))
        assert header in code, (slot, header)
        for line in blocks[header]:
            assert line in code, (slot, line)


@PAGES
def test_sync_no_invented_flags(path):
    allowed = platform_flags()
    invented = sorted(set(FLAG.findall(page_code(path))) - allowed)
    assert invented == [], invented


@PAGES
def test_sync_decision_engine_prerequisite(path):
    if "decision" not in (front_matter(path) or {}).get("otel_slots", []):
        pytest.skip("page does not use the Decision slot")
    text = body(path)
    assert decision_engine_prerequisite() in flat(text)
    assert DECISION_CARD in text


@PAGES
def test_sync_gate_rule_sentences(path):
    text = flat(body(path))
    if "submit_action_request" not in text and "action request" not in text.lower():
        pytest.skip("page does not send action requests")
    for sentence in gate_rule_sentences():
        assert sentence in text, sentence


@PAGES
def test_sync_deny_unless_allowed(path):
    text = body(path)
    if "MCP" not in text:
        pytest.skip("page uses no MCP tools")
    assert re.search(r"(?i)deny[^.|]*unless", text), "MCP page must say deny unless allowed"
    assert INTEGRATION_LINK in text


@PAGES
def test_sync_parameters_reuse_platform_names(path):
    known = known_params(path)
    for table in param_tables(path):
        who = table[0].index("Who sets it")
        for row in table[1:]:
            assert row[0] in known, f"{row[0]} is neither a platform nor an allowlisted parameter"
            assert normalise_owner(row[who]) == known[row[0]], (row[0], row[who], known[row[0]])


@PAGES
def test_sync_raci_rows_match_platform(path):
    platform = platform_raci_rows()
    for table in raci_tables(path):
        for row in table[1:]:
            if row[0] not in platform:
                continue
            mine = [normalise_owner(c) for c in row]
            assert mine in platform[row[0]], (mine, platform[row[0]])


@PAGES
def test_sync_stage_tmf_mapping(path):
    fm = front_matter(path) or {}
    targets = stage_targets()
    ceiling = fm.get("autonomy_ceiling")
    assert ceiling in targets, ceiling
    target = targets[ceiling]
    if target is None:
        assert "tmf_an_level_target" not in fm
    else:
        assert fm.get("tmf_an_level_target") == int(target.split()[1]), (ceiling, target)


@PAGES
def test_sync_verification_checks_tie_to_gates(path):
    names = [n.lower() for n in known_params(path)]
    table = verification_table(path)
    col = table[0].index("PB-02 gate or parameter")
    for row in table[1:]:
        cell = row[col]
        ok = EVALUATION_LINK in cell or any(n in cell.lower() for n in names)
        assert ok, row


# ---------- grounded knowledge assistant ----------

KNOWLEDGE = REPO_ROOT / "catalog/standards-knowledge/grounded-knowledge-assistant/README.md"
KNOWLEDGE_KEY = "standards-knowledge/grounded-knowledge-assistant"
SLOTS_HEADER = ["Slot", "Checkpoint", "Role", "Placement"]
ACTION_HEADER = ["Action", "Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP)", "Approval", "AI Act class"]
MERMAID_NODE = re.compile(r'[A-Za-z0-9_]+\s*(\[|\{)"([^"]+)"[\]\}]')


def _knowledge_nodes() -> list[tuple[str, str]]:
    """(shape opener, text) for each Mermaid node on the knowledge page."""
    return [(m.group(1), m.group(2)) for m in MERMAID_NODE.finditer(mermaid_fences(body(KNOWLEDGE))[0])]


def test_knowledge_slots():
    fm = front_matter(KNOWLEDGE) or {}
    assert set(fm.get("otel_slots", [])) == {"embedding", "reranker", "safety", "decision", "llm"}
    assert fm.get("autonomy_ceiling") == "inform"
    assert "tmf_an_level_target" not in fm


def test_knowledge_mermaid_abstain_and_size_routing():
    nodes = _knowledge_nodes()
    texts = [t for _, t in nodes]
    assert any("Abstain" in t for t in texts), texts
    assert any("Small" in t and "LLM" in t for t in texts), texts
    assert any("Large" in t and "LLM" in t for t in texts), texts
    diamonds = [t for shape, t in nodes if shape == "{"]
    assert any(re.search(r"(?i)rout|size", t) for t in diamonds), diamonds


def test_knowledge_released_checkpoints_only():
    text = body(KNOWLEDGE)
    for name in ("OTel-2.0-LLM-31B-IT", "OTel-2.0-Decision-26B-A4B-4bit", "OTel-Reranker", "OTel-Embedding", "Safety"):
        assert name in text, name
    assert not re.search(r"OTel-2\.5|2\.5-", text)
    table = table_with_header(KNOWLEDGE, "How it works", SLOTS_HEADER)
    col = table[0].index("Checkpoint")
    assert len(table) > 1
    for row in table[1:]:
        assert row[col].endswith("pinned by revision"), row


def test_knowledge_no_action_requests():
    text = body(KNOWLEDGE)
    assert "submit_action_request" not in text
    table = table_with_header(KNOWLEDGE, "Governance", ACTION_HEADER)
    col = table[0].index(ACTION_HEADER[1])
    assert len(table) > 1
    for row in table[1:]:
        assert row[col] == "LOOK", row


def test_knowledge_retrieval_prerequisites():
    units = _sentences(body(KNOWLEDGE)) + [" | ".join(r) for t in page_tables(KNOWLEDGE) for r in t]
    assert any("sentence-transformers" in u and re.search(r"(?i)reranker", u) for u in units)
    assert any("re-index" in u and re.search(r"(?i)embedding", u) for u in units)
    assert any(re.search(r"usage[- ]rights", u) and INTEGRATION_LINK in u for u in units)


def test_knowledge_routing_threshold_allowlisted():
    assert USE_CASE_LOCAL_PARAMS[KNOWLEDGE_KEY] == {"Decision routing threshold": "Model owner"}
    table = table_with_header(KNOWLEDGE, "Governance", PARAM_TABLE_HEADER)
    who = table[0].index("Who sets it")
    rows = {row[0]: row[who] for row in table[1:]}
    assert rows.get("Decision routing threshold") == "Model owner", rows


def test_knowledge_raci_rows():
    activities = {row[0] for table in raci_tables(KNOWLEDGE) for row in table[1:]}
    assert {"Set Decision routing thresholds", "Tune Safety slot abstention"} <= activities, activities


def test_knowledge_worked_example_abstains():
    heading = next(
        ln for ln in section_text(KNOWLEDGE, "How it works").splitlines() if ln.startswith("### Worked example:")
    )
    example = _h3_text(section_text(KNOWLEDGE, "How it works"), heading[4:])
    assert re.search(r"(?i)abstain", example), example
    assert "3GPP" in example or "TS " in example, example


# ---------- closed-loop incident handling ----------

CLOSED_LOOP = REPO_ROOT / "catalog/agentic-operations/closed-loop-incident-handling/README.md"
NODE_DEF = re.compile(r'([A-Za-z0-9_]+)\s*(\[|\{)"([^"]+)"[\]\}]')
EDGE = re.compile(r'([A-Za-z0-9_]+)(?:\s*[\[\{]"[^"]*"[\]\}])?\s*--\s*"([^"]+)"\s*-->\s*([A-Za-z0-9_]+)')
SWAP_STEPS = ("Baseline", "Swap", "Promote or roll back")


def _loop_units() -> list[str]:
    """Prose sentences plus table rows on the closed-loop page."""
    return _sentences(body(CLOSED_LOOP)) + [" | ".join(r) for t in page_tables(CLOSED_LOOP) for r in t]


def _loop_graph() -> tuple[dict[str, tuple[str, str]], list[tuple[str, str, str]]]:
    """Node id -> (shape opener, text), and (from, label, to) edges, from the Mermaid fence."""
    fence = mermaid_fences(body(CLOSED_LOOP))[0]
    nodes = {m.group(1): (m.group(2), m.group(3)) for m in NODE_DEF.finditer(fence)}
    return nodes, EDGE.findall(fence)


def _swap_steps() -> list[str]:
    """The Baseline, Swap, and Promote or roll back steps of Deploy and verify, in page order."""
    steps = _ordered_steps(section_text(CLOSED_LOOP, "Deploy and verify"))
    found = []
    for prefix in SWAP_STEPS:
        idx = next((i for i, s in enumerate(steps) if s.startswith(prefix)), None)
        assert idx is not None, f"no Deploy and verify step starts with {prefix!r}"
        found.append((idx, steps[idx]))
    assert [i for i, _ in found] == sorted(i for i, _ in found), "steps out of order"
    return [s for _, s in found]


def test_closed_loop_tmf_loop():
    text = body(CLOSED_LOOP)
    for term in ("TMF642", "TMF621", "/troubleTicket", "router state"):
        assert term in text, term
    assert "alarmCreateEvent" in text or "/hub" in text
    steps = _ordered_steps(section_text(CLOSED_LOOP, "How it works"))
    alarm = next(i for i, s in enumerate(steps) if "TMF642" in s)
    ticket = next(i for i, s in enumerate(steps) if "TMF621" in s)
    assert alarm < ticket, (alarm, ticket)


def test_closed_loop_writes_through_action_request():
    assert "submit_action_request" in section_text(CLOSED_LOOP, "How it works")
    assert "submit_action_request" in section_text(CLOSED_LOOP, "What you need")
    units = _loop_units()
    assert any("write credentials" in u and re.search(r"\b(no|never)\b", u) for u in units)
    assert any(
        re.search(r"(?i)ticket creation|creat\w*[^.|]*ticket", u) and "action request" in u.lower() for u in units
    )


def test_closed_loop_gate_and_workflow():
    nodes, edges = _loop_graph()
    gates = [i for i, (shape, t) in nodes.items() if shape == "{" and "lower of the label and the policy ceiling" in t]
    assert gates, nodes
    review = [dst for src, label, dst in edges if src in gates and "REVIEW" in label]
    assert any("approver" in nodes[d][1].lower() for d in review), review
    act = [dst for src, label, dst in edges if src in gates and re.search(r"\bACT\b", label)]
    assert any("playbook" in nodes[d][1] for d in act), act
    assert "Ansible Automation Platform" in section_text(CLOSED_LOOP, "What you need")


def test_closed_loop_swap_procedure():
    steps = _swap_steps()
    joined = " ".join(steps)
    for term in ("replayed incidents", "registry", "Non-inferiority margin", "canary", "pinned 2.0 revision"):
        assert term in joined, term
    stripped = re.sub(r"\b2\.[05]\b|PB-\d{2}|TMF\d{3}|Level \d", "", joined)
    assert not re.search(r"\d", stripped), stripped


def test_closed_loop_no_2_0_loop_claim():
    claim = re.compile(r"(?i)\b2\.0\b[^.]*\b(runs|handles|closes|completes) the loop")
    assert [s for s in _sentences(body(CLOSED_LOOP)) if claim.search(s)] == []
    table = tables(sections(body(CLOSED_LOOP)).get("Sources", []))[0]
    claim_col, basis, source = (table[0].index(c) for c in ("Claim", "Basis", "Source"))
    rows = [r for r in table[1:] if r[basis] == "model card" and "OTel-2.0-LLM-31B-IT" in r[source]]
    assert any(re.search(r"(?i)tool[- ]calling|closed[- ]loop", r[claim_col]) for r in rows), rows


def test_closed_loop_risk_classes():
    text = body(CLOSED_LOOP)
    assert "write_low" in text and "write_high" in text
    table = table_with_header(CLOSED_LOOP, "Governance", ACTION_HEADER)
    out = table[0].index(ACTION_HEADER[1])
    rows = table[1:]
    assert any("ticket" in r[0].lower() and "NOTIFY" in r[out] for r in rows), rows
    assert any("soft reset" in r[0].lower() and "REVIEW" in r[out] and "ACT" in r[out] for r in rows), rows
    assert any("drain" in r[0].lower() and r[out] == "REVIEW" for r in rows), rows


def test_closed_loop_zero_tolerance():
    assert any(re.search(r"(?i)zero[- ]tolerance", u) for u in _loop_units())
    text = flat(body(CLOSED_LOOP))
    for term in ("duplicate ticket", "outside the allowed set", "secret"):
        assert term in text, term


def test_closed_loop_gate_endpoint_and_label_mass():
    assert "Label-mass floor" in body(CLOSED_LOOP)
    units = _loop_units()
    assert any("fails closed" in u and "STOP" in u for u in units)
    assert any(re.search(r"(?i)\brequire", u) and "token" in u and "gate endpoint" in u for u in units)


def test_closed_loop_example_ids():
    how = section_text(CLOSED_LOOP, "How it works")
    heading = next(ln for ln in how.splitlines() if ln.startswith("### Worked example:"))
    example = _h3_text(how, heading[4:])
    for ident in ("inc-3107", "req-3107-1", "dec-3107-1"):
        assert ident in example, ident


# ---------- alarm triage adaptation ladder ----------

TRIAGE = REPO_ROOT / "catalog/network-operations/alarm-triage-adaptation/README.md"
LADDER_PAGE = REPO_ROOT / "architecture/adaptation-ladder.md"
ADAPTATION_LINK = "../../../platform/adaptation/README.md"
GATE_PAGE_LINK = "../../../architecture/decision-gate.md"
KSERVE_ISSUE = "https://github.com/kserve/kserve/issues/6094"
F2_IDS = ("inc-3107", "req-3107", "dec-3107", "noc-loop-agent")


def _triage_h3(prefix: str) -> str:
    """Text of the first How it works H3 whose title starts with prefix."""
    how = section_text(TRIAGE, "How it works")
    heading = next((ln for ln in how.splitlines() if ln.startswith(f"### {prefix}")), None)
    assert heading, f"no H3 starting {prefix!r} in How it works"
    return _h3_text(how, heading[4:])


def _ladder_rungs() -> list[str]:
    """First-column values of the rung table on the adaptation ladder page."""
    for table in tables(sections(body(LADDER_PAGE)).get("The design", [])):
        if table[0][0] == "Rung":
            return [row[0] for row in table[1:]]
    raise AssertionError("no rung table on the adaptation ladder page")


def test_adaptation_ladder_rungs():
    rungs = _ladder_rungs()[:3]
    assert rungs == ["Retrieval", "Skills and capability manifests", "LoRA"], rungs
    table = next(
        t for t in tables(sections(body(TRIAGE)).get("How it works", [])) if any("Rung" in h for h in t[0])
    )
    firsts = [row[0] for row in table[1:]]
    assert len(firsts) >= 3, firsts
    for want, got in zip(rungs, firsts):
        assert got.startswith(want), (want, got)
    assert "skills-only baseline" in body(TRIAGE)


def test_adaptation_ladder_when_to_train_rule():
    text = flat(_triage_h3("When to train"))
    for term in (
        "Minimum measured gap to train",
        "paired runs",
        "Minimum share of non-ACT training cases",
        "Non-inferiority margin",
        "retrieval",
        "skills",
        ADAPTATION_LINK,
        EVALUATION_LINK,
    ):
        assert term in text, term


def test_adaptation_ladder_classification_head():
    sentences = _sentences(body(TRIAGE))
    assert any("Classification" in s and "taxonomy" in s for s in sentences)
    assert any("drive-test" in s for s in sentences)
    text = body(TRIAGE)
    assert "Classification per-class recall floor" in text
    assert "Classification other-or-abstain recall floor" in text


def test_adaptation_ladder_static_adapters():
    code = page_code(TRIAGE)
    for flag in ("--enable-lora", "--lora-modules", "--max-lora-rank"):
        assert flag in code, flag
    text = flat(body(TRIAGE))
    for term in ("object storage", "pinned by digest", KSERVE_ISSUE):
        assert term in text, term


def test_adaptation_ladder_retrain_on_base_change():
    assert any(
        "retrain" in s and "re-gate" in s and "base revision" in s for s in _sentences(body(TRIAGE))
    )


def test_adaptation_ladder_training_labels():
    """The step or H3 that describes training data names the four non-ACT labels
    and links the decision gate page for them."""
    how = section_text(TRIAGE, "How it works")
    units = [u for u in re.split(r"\n(?=\d+\. |### )", how) if "training data" in u]
    labels = ("LOOK", "NOTIFY", "REVIEW", "STOP")
    assert any(GATE_PAGE_LINK in u and all(lbl in u for lbl in labels) for u in units), units


def test_adaptation_ladder_gate_stage():
    table = table_with_header(TRIAGE, "Governance", ACTION_HEADER)
    out = table[0].index(ACTION_HEADER[1])
    rows = table[1:]
    assert any("triage note" in r[0].lower() and "NOTIFY" in r[out] for r in rows), rows
    assert any("fix" in r[0].lower() and "REVIEW" in r[out] for r in rows), rows
    for r in rows:
        assert not re.search(r"\bACT\b", r[out]), r


def test_adaptation_ladder_decision_quantized():
    assert any(
        "Decision" in s and "quantized" in s and "model owner" in s for s in _sentences(body(TRIAGE))
    )


def test_adaptation_ladder_example_distinct():
    assert "inc-5520" in _triage_h3("Worked example:")
    text = body(TRIAGE)
    for old in F2_IDS:
        assert old not in text, old
