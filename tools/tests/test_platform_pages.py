"""Platform blueprint pages: shared template checks for every landed page.

Each check here runs on every platform/<slug>/README.md. Per-page content
checks for a single blueprint go in their own test module and import the
helpers below. With no platform pages yet, the parametrized checks collect
no cases and the expected-pages guard compares two empty maps.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tools.tests.conftest import REPO_ROOT
from tools.tests.test_open_source_framing import STANDARD_LINE
from tools.tests.test_reference_pages import (  # noqa: F401  (shared with per-page modules)
    GATE_SCHEMA_PATH,
    GATE_SCHEMA_URL,
    LAYER_CODE,
    PRODUCT_TERMS,
    blueprint_pages,
    body,
    front_matter,
    json_fences,
    mermaid_fences,
    sections,
    tables,
)

# Grows by one entry per landed blueprint ({slug: id}), so a lost or renamed
# page fails here instead of quietly dropping out of every check.
EXPECTED_PLATFORM_PAGES: dict[str, str] = {
    "serving-routing-placement": "PB-04",
    "integration": "PB-05",
    "safety-autonomy-gating": "PB-06",
    "action-layer": "PB-07",
}

PB_ID = re.compile(r"^PB-[0-9]{2}$")
PARAM_TABLE_HEADER = ["Parameter", "What it controls", "Who sets it", "How to calibrate"]
COMPONENTS_HEADER = ["Component role", "Red Hat product used"]
WORKED_EXAMPLE_H3 = "Worked example: alarm and root-cause triage"
MILLISECONDS = re.compile(r"\b\d+\s?ms\b")
ISO_QUOTED = re.compile(r'^clarity_reviewed: "\d{4}-\d{2}-\d{2}"$', re.M)
RAW_FRONT_MATTER = re.compile(r"\A---\n(.*?)^---[ \t]*$", re.M | re.S)
MIN_SOURCES_ROWS = 6


# ---------- helpers ----------


def platform_pages() -> list[Path]:
    """Blueprint pages under platform/ (catalog use cases are excluded)."""
    return [p for p in blueprint_pages() if p.relative_to(REPO_ROOT).parts[0] == "platform"]


def _id(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def section_text(path: Path, name: str) -> str:
    """Raw markdown between the "## <name>" heading and the next H2."""
    text = body(path)
    m = re.search(rf"^## {re.escape(name)}[ \t]*$", text, re.M)
    if not m:
        raise AssertionError(f"{_id(path)}: no '## {name}' section")
    nxt = re.search(r"^## ", text[m.end() :], re.M)
    return text[m.end() : m.end() + nxt.start()] if nxt else text[m.end() :]


def reference_design_text(path: Path) -> str:
    return section_text(path, "Reference design")


def table_with_header(path: Path, section: str, wanted) -> list[list[str]]:
    """First table in section whose header holds every name in wanted."""
    for table in tables(sections(body(path)).get(section, [])):
        if set(wanted) <= set(table[0]):
            return table
    raise AssertionError(f"{_id(path)}: no table in '{section}' with header {list(wanted)}")


def page_tables(path: Path) -> list[list[list[str]]]:
    """Every table on the page, across all sections."""
    return [t for tokens in sections(body(path)).values() for t in tables(tokens)]


PAGES = pytest.mark.parametrize("path", platform_pages(), ids=_id)


# ---------- shared checks ----------


def test_shared_expected_pages():
    found = {p.parent.name: (front_matter(p) or {}).get("id") for p in platform_pages()}
    assert found == EXPECTED_PLATFORM_PAGES


@PAGES
def test_shared_front_matter(path):
    fm = front_matter(path) or {}
    assert fm.get("type") == "platform"
    assert PB_ID.match(str(fm.get("id", ""))), fm.get("id")


@PAGES
def test_shared_components_table_and_standard_line(path):
    tbls = tables(sections(body(path)).get("Components", []))
    assert tbls, "Components has no table"
    assert tbls[0][0][: len(COMPONENTS_HEADER)] == COMPONENTS_HEADER
    assert STANDARD_LINE in section_text(path, "Components")


@PAGES
def test_shared_one_mermaid_fence_in_reference_design(path):
    assert len(mermaid_fences(body(path))) == 1
    assert len(mermaid_fences(reference_design_text(path))) == 1


@PAGES
def test_shared_no_image_placeholder(path):
    text = body(path)
    assert "diagrams/" not in text
    assert "![" not in text


@PAGES
def test_shared_worked_example(path):
    lines = [ln.rstrip() for ln in reference_design_text(path).splitlines()]
    assert f"### {WORKED_EXAMPLE_H3}" in lines


@PAGES
def test_shared_parameter_tables_have_no_values(path):
    for table in page_tables(path):
        if table[0] != PARAM_TABLE_HEADER:
            continue
        for row in table[1:]:
            for cell in row:
                assert not re.search(r"\d", cell), (row[0], cell)


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
    tbls = tables(sections(body(path)).get("Sources and acceptance", []))
    assert tbls, "Sources and acceptance has no table"
    assert len(tbls[0]) - 1 >= MIN_SOURCES_ROWS


# ---------- serving, routing, and placement ----------

SERVING = REPO_ROOT / "platform/serving-routing-placement/README.md"
ACCELERATOR_NAME = re.compile(
    r"\b(H100|H200|B200|B300|L4|L40S|A100|T4|MI\d{3}[A-Z]?|RTX|GB10|Gaudi)\b"
)
HARDWARE_CLASSES = ("CPU", "Small edge GPU", "Single large GPU", "Multi-GPU core node")
DECISION_CARD = "https://huggingface.co/farbodtavakkoli/OTel-2.0-Decision-26B-A4B-4bit"
CODE_FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.M | re.S)


def test_serving_three_routing_layers():
    table = table_with_header(SERVING, "Reference design", ["Layer", "Decides"])
    rows = table[1:]
    assert len(rows) == 3
    for row, name in zip(rows, ("Front door", "Content routing", "Replica scheduling"), strict=True):
        assert name in row[0], row[0]
    assert any("Decision" in cell for cell in rows[1])


def test_serving_sizing_by_class():
    table = table_with_header(
        SERVING, "Reference design", ["Slot", "Precision", "Weights", "Hardware class"]
    )
    col = table[0].index("Hardware class")
    assert len(table) > 1
    for row in table[1:]:
        for cell in row:
            assert not ACCELERATOR_NAME.search(cell), cell
        assert any(name in row[col] for name in HARDWARE_CLASSES), row[col]


def test_serving_key_flags():
    code = "\n".join(CODE_FENCE.findall(body(SERVING)))
    for flag in (
        "--revision",
        "--tool-call-parser gemma4",
        "--limit-mm-per-prompt",
        "--max-logprobs 64",
        "--convert classify",
        "--convert embed",
        "--lora-modules",
    ):
        assert flag in code, flag


def test_serving_hardware_prerequisites():
    table = table_with_header(SERVING, "Reference design", ["Prerequisite", "Source"])
    text = "\n".join(" | ".join(row) for row in table)
    for want in ("VLLM_ROCM_USE_AITER=0", "--moe-backend triton", "INT8", "TRITON_ATTN"):
        assert want in text, want
    src = table[0].index("Source")
    for row in table[1:]:
        assert "](http" in row[src], row


def test_serving_decision_engine_prerequisite():
    text = body(SERVING)
    assert "0.26" in text
    assert DECISION_CARD in text


def test_serving_no_runtime_adapter_hot_load():
    text = SERVING.read_text(encoding="utf-8")
    assert "VLLM_ALLOW_RUNTIME_LORA_UPDATING=True" not in text
    for line in text.splitlines():
        if "VLLM_ALLOW_RUNTIME_LORA_UPDATING" in line:
            assert re.search(r"(?i)never|block", line), line


def test_serving_edge_options():
    table = table_with_header(SERVING, "Reference design", ["Option", "Limits"])
    text = "\n".join(" | ".join(row) for row in table[1:])
    for want in ("Podman", "Device Edge", "single-node OpenShift"):
        assert want.lower() in text.lower(), want
    assert any("one AI model" in cell for row in table[1:] for cell in row)


# ---------- integration ----------

INTEGRATION = REPO_ROOT / "platform/integration/README.md"
TOOL_ACCESS = {"read", "notify", "action request"}


def test_integration_standards_named():
    text = body(INTEGRATION)
    for want in ("TMF642", "TMF628", "TMF621", "TMF639", "CAMARA", "3GPP", "NWDAF", "command line"):
        assert want in text, want


def test_integration_tools_table():
    table = table_with_header(INTEGRATION, "Reference design", ["Tool", "Standard", "Access"])
    col = table[0].index("Access")
    rows = table[1:]
    assert rows
    for row in rows:
        assert row[col] in TOOL_ACCESS, row
    assert sum(row[col] == "action request" for row in rows) == 1
    tmf621 = [row for row in rows if any("TMF621" in cell for cell in row)]
    assert tmf621 and all(row[col] == "read" for row in tmf621)


def test_integration_gateway_component():
    rows = tables(sections(body(INTEGRATION)).get("Components", []))[0][1:]
    assert any("MCP" in row[0] and "Connectivity Link" in row[1] for row in rows)
    assert any("Keycloak" in row[1] for row in rows)


def test_integration_per_tool_authorization():
    text = body(INTEGRATION)
    for want in ("x-mcp-toolname", "deny", "token exchange", "audit"):
        assert want in text, want


def test_integration_conformance_gate():
    text = section_text(INTEGRATION, "Sources and acceptance")
    gates = [ln for ln in text.splitlines() if ln.startswith("- Gate:")]
    assert any("Conformance Test Kit" in ln for ln in gates)


def test_integration_usage_rights():
    assert any(
        "Usage rights" in table[0]
        for table in tables(sections(body(INTEGRATION)).get("Reference design", []))
    )


def test_integration_stateful_mocks():
    assert "stateful mock" in body(INTEGRATION)


def test_integration_writes_through_action_request():
    assert "submit_action_request" in body(INTEGRATION)


# ---------- safety and autonomy gating ----------

GATING = REPO_ROOT / "platform/safety-autonomy-gating/README.md"
STAGE_HEADER = ["Stage", "Autonomy ceiling", "Gate outcomes allowed", "Who does what", "TM Forum target"]
STAGE_TARGETS = {
    "Shadow": "current level",
    "Assist": "Level 1",
    "Recommend": "Level 2",
    "Act": "Level 3",
}
CONTROLS = (
    "input guardrails",
    "tool-response guardrails",
    "safety slot",
    "decision gate",
    "output guardrails",
)


def test_gating_stage_table():
    table = table_with_header(GATING, "Reference design", STAGE_HEADER)
    assert table[0] == STAGE_HEADER
    rows = table[1:]
    assert [row[0] for row in rows] == list(STAGE_TARGETS)
    col = STAGE_HEADER.index("TM Forum target")
    for row in rows:
        assert STAGE_TARGETS[row[0]] in row[col], row


def test_gating_controls_table():
    table = table_with_header(GATING, "Reference design", ["Control", "Position", "Role"])
    names = [row[0].lower() for row in table[1:]]
    for want in CONTROLS:
        assert any(want in name for name in names), want


def test_gating_components():
    rows = tables(sections(body(GATING)).get("Components", []))[0][1:]
    products = [row[1] for row in rows]
    assert any("NeMo Guardrails" in cell for cell in products)
    assert any("OTel Safety" in cell for cell in products)
    assert any("OTel Decision" in cell for cell in products)


def test_gating_mermaid_capabilities():
    fence = mermaid_fences(body(GATING))[0]
    for want in ("Safety slot", "Decision gate"):
        assert want in fence, want
    assert "guardrails" in fence.lower()


def test_gating_tm_forum_source():
    table = tables(sections(body(GATING)).get("Sources and acceptance", []))[0]
    basis, source = table[0].index("Basis"), table[0].index("Source")
    assert any(
        row[basis].lower() == "project documentation" and "tmforum.org" in row[source]
        for row in table[1:]
    )


def test_gating_gate_rules():
    text = body(GATING)
    assert "policy ceiling" in text
    sentences = re.split(r"(?<=[.!?])\s+", text)
    assert any("STOP" in s and "forces" in s for s in sentences)


def test_gating_promotion_parameters():
    table = table_with_header(GATING, "Reference design", PARAM_TABLE_HEADER)
    assert table[0] == PARAM_TABLE_HEADER
    assert len(table) - 1 >= 3


def test_gating_no_deprecated_guardrails():
    text = body(GATING)
    assert not re.search(r"\b(FMS|OGX)\b", text)
    assert not re.search(r"Guardrails Orchestrator|Orchestrator Guardrails", text)


def test_gating_alarm_example_review():
    text = reference_design_text(GATING)
    example = text[text.index(f"### {WORKED_EXAMPLE_H3}") :]
    for want in ("NOTIFY", "REVIEW", "eth1", "r2"):
        assert want in example, want


# ---------- action layer ----------

ACTION = REPO_ROOT / "platform/action-layer/README.md"
YAML_FENCE = re.compile(r"^```ya?ml[ \t]*\n(.*?)^```", re.M | re.S)
MAX_YAML_LINES = 20


def _ordered_steps(text: str) -> list[str]:
    """Inline text of each item in the first ordered list of text."""
    from tools.tests.test_reference_pages import _md

    steps, in_list, depth = [], False, 0
    for tok in _md().parse(text):
        if tok.type == "ordered_list_open":
            if in_list:
                depth += 1
            in_list = True
        elif tok.type == "ordered_list_close":
            if depth:
                depth -= 1
                continue
            break
        elif in_list and tok.type == "list_item_open" and depth == 0:
            steps.append("")
        elif in_list and tok.type == "inline" and steps:
            steps[-1] += tok.content + " "
    return steps


def test_action_two_paths():
    table = table_with_header(ACTION, "Reference design", ["Path"])
    rows = [" | ".join(row) for row in table[1:]]
    assert any("Automation Orchestrator" in r and "default" in r.lower() for r in rows), rows
    assert any(
        "job template" in r.lower() and "`uri`" in r and "alternative" in r.lower() for r in rows
    ), rows


def test_action_write_path_steps():
    steps = _ordered_steps(reference_design_text(ACTION))
    assert 0 < len(steps) <= 8, len(steps)
    lowered = [s.lower() for s in steps]

    def first(*words):
        for i, s in enumerate(lowered):
            if any(w in s for w in words):
                return i
        raise AssertionError(f"no step mentions {words}")

    order = [
        first("approv"),
        first("verif"),
        first("roll back", "rollback"),
        first("audit"),
    ]
    assert order == sorted(order), order


def test_action_components():
    rows = tables(sections(body(ACTION)).get("Components", []))[0][1:]
    products = [row[1] for row in rows]
    assert any("Automation Orchestrator" in cell for cell in products)
    assert any("Event-Driven Ansible" in cell for cell in products)
    mcp = [row for row in rows if "MCP Server" in row[1]]
    assert mcp and all("read-only" in " ".join(row) for row in mcp), mcp


def test_action_json_validates():
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(json.loads(GATE_SCHEMA_PATH.read_text(encoding="utf-8")))
    for example in json_fences(body(ACTION)):
        errors = list(validator.iter_errors(example))
        assert errors == [], [e.message for e in errors]


def test_action_schema_url():
    assert GATE_SCHEMA_URL in body(ACTION)


def test_action_private_address_prerequisite():
    assert "private network addresses" in body(ACTION)


def test_action_fallback_snippet():
    fences = YAML_FENCE.findall(body(ACTION))
    snippet = [f for f in fences if "ansible.builtin.uri" in f and "ansible.builtin.assert" in f]
    assert snippet, "no yaml fence with the uri and assert tasks"
    for fence in fences:
        if fence is snippet[0]:
            continue
        assert len(fence.splitlines()) <= MAX_YAML_LINES, fence[:80]


def test_action_gate_rules():
    text = body(ACTION)
    assert "policy ceiling" in text
    assert "forces STOP" in text or "forces a STOP" in text
    assert "label mass" in text


def test_action_alarm_example():
    text = reference_design_text(ACTION)
    example = text[text.index(f"### {WORKED_EXAMPLE_H3}") :]
    for want in ("eth1", "r2", "noc-shift-lead", "pb-interface-restart", "REVIEW", "roll"):
        assert want in example, want
