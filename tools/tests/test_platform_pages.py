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
    "evaluation-acceptance": "PB-02",
    "adaptation": "PB-03",
    "quality-operations": "PB-09",
    "security-identity-sandbox": "PB-08",
    "intake-model-selection": "PB-01",
    "compliance-operating-model": "PB-10",
}

PB_ID = re.compile(r"^PB-[0-9]{2}$")
PARAM_TABLE_HEADER = ["Parameter", "What it controls", "Who sets it", "How to calibrate"]
COMPONENTS_HEADER = ["Component role", "Red Hat product used"]
WORKED_EXAMPLE_H3 = "Worked example: alarm and root-cause triage"
MILLISECONDS = re.compile(r"\b\d+\s?ms\b")
ISO_QUOTED = re.compile(r'^clarity_reviewed: "\d{4}-\d{2}-\d{2}"$', re.M)
RAW_FRONT_MATTER = re.compile(r"\A---\n(.*?)^---[ \t]*$", re.M | re.S)
MIN_SOURCES_ROWS = 6
PARAM_NAME_COLUMNS = ("Parameter", "Who sets it")
PARAM_VALUE_COLUMNS = ("What it controls", "How to calibrate")
VALUE_HEADER = re.compile(r"\b(default|value)s?\b", re.I)
# Identifiers whose digits are not values: Level N, PB ids, TM Forum API numbers.
SAFE_ID = re.compile(r"\bLevel [0-9]\b|\bPB-[0-9]{2}\b|\bTMF[0-9]{3}\b")
# Named methods whose number is part of the name, not a default.
NAMED_RULES = re.compile(r"\brule of three\b", re.I)
# Spelled-out numbers. "one" is left out: pages use it as a determiner
# ("one owner", "back one stage"), never as a threshold.
WORD_NUMBER = re.compile(
    r"\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty"
    r"|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|dozen"
    r"|half|percent|per cent)\b",
    re.I,
)


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


def param_table_problems(table: list[list[str]]) -> list[str]:
    """Why a parameter table breaks the no-default-values rule (empty if it does not).

    A table counts as a parameter table when its header holds every name in
    PARAM_TABLE_HEADER, so an extra column cannot exempt it. A Default or Value
    column fails outright. The calibration columns may hold no digits and no
    spelled-out numbers. The name columns may hold digits only inside a safe
    identifier (Level N, a PB id, a TM Forum API number).
    """
    header = table[0]
    if not set(PARAM_TABLE_HEADER) <= set(header):
        return []
    problems = [f"value column {h!r}" for h in header if VALUE_HEADER.search(h)]
    value_cols = [header.index(h) for h in PARAM_VALUE_COLUMNS]
    name_cols = [header.index(h) for h in PARAM_NAME_COLUMNS]
    for row in table[1:]:
        for i in value_cols:
            cell = NAMED_RULES.sub("", row[i])
            if re.search(r"\d", cell) or WORD_NUMBER.search(cell):
                problems.append(f"{row[0]}: {row[i]}")
        for i in name_cols:
            if re.search(r"\d", SAFE_ID.sub("", row[i])):
                problems.append(f"{row[0]}: {row[i]}")
    return problems


@pytest.mark.parametrize(
    ("table", "ok"),
    [
        ([PARAM_TABLE_HEADER, ["Floor", "The lowest share", "Risk owner", "Fit on a set"]], True),
        ([PARAM_TABLE_HEADER, ["Level 3 ceiling", "The ceiling", "PB-02 owner", "Fit"]], True),
        ([PARAM_TABLE_HEADER, ["Budget", "Uses the rule of three", "Risk owner", "Fit"]], True),
        ([PARAM_TABLE_HEADER, ["Floor", "About 95 percent", "Risk owner", "Fit"]], False),
        ([PARAM_TABLE_HEADER, ["Floor", "About ninety-five percent", "Risk owner", "Fit"]], False),
        ([PARAM_TABLE_HEADER, ["Floor", "The share", "Risk owner", "Start at three requests"]], False),
        ([PARAM_TABLE_HEADER, ["Floor 2", "The share", "Risk owner", "Fit"]], False),
        ([[*PARAM_TABLE_HEADER, "Default"], ["Floor", "The share", "Risk owner", "Fit", "high"]], False),
        ([["Parameter", "Value", *PARAM_TABLE_HEADER[1:]], ["Floor", "x", "y", "z", "w"]], False),
        ([["Name", "Notes"], ["Floor", "95"]], True),
    ],
)
def test_param_table_rule_cases(table, ok):
    assert (param_table_problems(table) == []) is ok, param_table_problems(table)


@PAGES
def test_shared_parameter_tables_have_no_values(path):
    for table in page_tables(path):
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


def test_serving_fp8_source_includes_blackwell():
    """The FP8 source row must allow the FP8 fix the Blackwell prerequisite gives."""
    table = tables(sections(body(SERVING)).get("Sources and acceptance", []))[0]
    claim = table[0].index("Claim")
    rows = [r for r in table[1:] if "FP8 W8A8 needs" in r[claim]]
    assert rows, "no FP8 W8A8 source row"
    for row in rows:
        assert "Blackwell" in row[claim] and "8.9" in row[claim], row[claim]


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


def test_integration_example_roles_cover_its_calls():
    """Deny by default: the agent holds a role for every call the example makes."""
    text = reference_design_text(INTEGRATION)
    example = text[text.index(f"### {WORKED_EXAMPLE_H3}") :]
    roles = next(s for s in re.split(r"(?<=\.)\s+", example) if "holds roles for" in s)
    for want in ("TMF642", "TMF628", "TMF639", "TMF621", "show interface", "Classification",
                 "submit_action_request"):
        assert want in roles, want
    for want in ("inc-2041", "r2", "eth1"):
        assert want in example, want


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
    """The TM Forum autonomy levels come from a standards body's whitepaper,
    which the project documentation basis covers."""
    table = tables(sections(body(GATING)).get("Sources and acceptance", []))[0]
    basis, source = table[0].index("Basis"), table[0].index("Source")
    assert any(
        row[basis].lower() == "project documentation"
        and "tmforum.org" in row[source]
        and "whitepaper" in row[source].lower()
        for row in table[1:]
    )
    assert "whitepapers" in project_documentation_definition()


def project_documentation_definition() -> str:
    """The "project documentation" row of the claim basis table in the definitions."""
    for line in (REPO_ROOT / "framework/definitions.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("| project documentation |"):
            return line
    raise AssertionError("no project documentation row in framework/definitions.md")


def test_project_documentation_covers_standards_bodies():
    row = project_documentation_definition()
    for want in ("3GPP", "IETF", "TM Forum", "CAMARA", "specifications", "whitepapers"):
        assert want in row, want


# A blog post or news item: a dated path, or a /blog/ folder.
BLOG_URL = re.compile(r"/blog/|/20[0-9]{2}/[0-9]{2}/[0-9]{2}/")


@PAGES
def test_project_documentation_rows_are_not_blog_posts(path):
    table = tables(sections(body(path)).get("Sources and acceptance", []))[0]
    basis, source = table[0].index("Basis"), table[0].index("Source")
    for row in table[1:]:
        if row[basis].strip().lower() == "project documentation":
            assert not BLOG_URL.search(row[source]), row[source]


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
    # The length limit covers the snippet itself and every other yaml fence.
    assert len(snippet[0].splitlines()) <= MAX_YAML_LINES
    for fence in fences:
        assert len(fence.splitlines()) <= MAX_YAML_LINES, fence[:80]


def test_action_gate_rules():
    text = body(ACTION)
    assert "policy ceiling" in text
    assert "forces STOP" in text or "forces a STOP" in text
    assert "label mass" in text


def test_action_alarm_example():
    text = reference_design_text(ACTION)
    example = text[text.index(f"### {WORKED_EXAMPLE_H3}") :]
    for want in ("eth1", "r2", "`approver`", "pb-interface-restart", "REVIEW", "roll"):
        assert want in example, want
    assert "noc-shift-lead" not in example


# ---------- NOTIFY delivery (shared across pages) ----------

NOTIFY_GATE_PAGE = REPO_ROOT / "architecture/decision-gate.md"
# Each page that mentions NOTIFY states the two delivery paths, once.
NOTIFY_RULE = ("from the assist stage up", "the shadow stage gets no notify role", "notification job")
# A Mermaid edge: source node, label, target node with its quoted text.
MERMAID_EDGE = re.compile(r'(\w+)(?:\[[^\]]*\]|\{[^}]*\})?\s*--\s*"([^"]*)"\s*-->\s*(\w+)')
MERMAID_NODE = re.compile(r'(\w+)[\[{]+"([^"]*)"[\]}]+')


def notify_pages() -> list[Path]:
    return [INTEGRATION, GATING, ACTION, NOTIFY_GATE_PAGE]


def mermaid_edges(fence: str) -> list[tuple[str, str, str]]:
    """(edge label, target id, target text) for each labelled edge in fence."""
    nodes = dict(MERMAID_NODE.findall(fence))
    return [(label, dst, nodes.get(dst, "")) for _src, label, dst in MERMAID_EDGE.findall(fence)]


def notify_edge_problems(fence: str) -> list[str]:
    """NOTIFY must lead to a notification job, never to a no-change branch."""
    out = []
    for label, dst, text in mermaid_edges(fence):
        if "NOTIFY" not in label:
            continue
        if "no change" in label.lower():
            out.append(f"NOTIFY shares a no-change edge to {dst}")
        elif "notification job" not in text.lower():
            out.append(f"NOTIFY goes to {dst} ({text!r}), not a notification job")
    return out


@pytest.mark.parametrize(
    ("fence", "ok"),
    [
        ('DG -- "NOTIFY" --> NJ["Run the notification job"]', True),
        ('DG -- "LOOK, NOTIFY, or STOP: no change" --> AU["Audit record"]', False),
        ('DG -- "NOTIFY" --> AU["Audit record"]', False),
        ('DG{"Decision gate"} -- "NOTIFY" --> NJ["Run the notification job"]', True),
    ],
)
def test_notify_edge_rule_cases(fence, ok):
    assert (notify_edge_problems(fence) == []) is ok


@pytest.mark.parametrize("path", notify_pages(), ids=_id)
def test_notify_rule_stated_once(path):
    text = re.sub(r"\s+", " ", body(path)).lower()
    for phrase in NOTIFY_RULE:
        assert phrase in text, phrase
    assert text.count(NOTIFY_RULE[1]) == 1


@pytest.mark.parametrize("path", [GATING, ACTION], ids=_id)
def test_notify_diagram_runs_a_notification_job(path):
    fence = mermaid_fences(body(path))[0]
    assert "NOTIFY" in fence
    assert notify_edge_problems(fence) == []


def test_notify_pages_agree():
    stages = table_with_header(GATING, "Reference design", STAGE_HEADER)
    shadow = next(row for row in stages[1:] if row[0] == "Shadow")
    assert "NOTIFY" not in shadow[STAGE_HEADER.index("Gate outcomes allowed")]
    tools_table = table_with_header(INTEGRATION, "Reference design", ["Tool", "Standard", "Access"])
    access = tools_table[0].index("Access")
    notify_rows = [row for row in tools_table[1:] if row[access] == "notify"]
    assert notify_rows and all("assist stage" in row[0] for row in notify_rows)
    for path in notify_pages():
        text = re.sub(r"\s+", " ", body(path))
        assert "read and notify tools plus" not in text, _id(path)
        assert "NOTIFY sends a notification" not in text, _id(path)


# Phrasings that describe NOTIFY without its stage rule.
NOTIFY_OLD_PHRASES = ("read and notify tools plus", "NOTIFY sends a notification")


@pytest.mark.parametrize("path", platform_pages(), ids=_id)
def test_shared_notify_mentions_link_the_gate(path):
    """Any page that mentions NOTIFY links the decision gate page, which holds
    the stage rule, and uses none of the old phrasings."""
    text = re.sub(r"\s+", " ", body(path))
    if "NOTIFY" not in text:
        return
    assert "decision-gate.md" in text, _id(path)
    for phrase in NOTIFY_OLD_PHRASES:
        assert phrase not in text, phrase


# ---------- shared role vocabulary ----------

# Telecom job titles and older audience names the pages replaced with generic
# roles, and the "named approver" wording a role-based approval step rejects.
TELECOM_ROLE = re.compile(
    r"noc-shift-lead|\bNOC lead|\bshift lead|operator risk owner|operator SME"
    r"|\bplatform engineers?\b|\bplatform owners?\b|\bautomation teams?\b"
    r"|\brisk and compliance leads?\b|\bnamed approver\b|\bsecurity architects?\b"
    r"|\bNOC engineers?\b",
    re.I,
)


@pytest.mark.parametrize(
    ("text", "hit"),
    [
        ("Architects and platform engineers", True),
        ("Operator architects, platform owners, and risk and compliance leads", True),
        ("Architects, platform engineers, and automation teams", True),
        ("a named approver handles REVIEW", True),
        ("Platform teams and security architects", True),
        ("Architects, platform teams, business owners, and risk owners", False),
        ("an approver handles REVIEW", False),
    ],
)
def test_generic_role_pattern_cases(text, hit):
    assert bool(TELECOM_ROLE.search(text)) is hit


def _role_scan_pages() -> list[Path]:
    return [
        *platform_pages(),
        *sorted((REPO_ROOT / "architecture").glob("*.md")),
        *sorted((REPO_ROOT / "framework").glob("*.md")),
    ]


@pytest.mark.parametrize("path", _role_scan_pages(), ids=_id)
def test_shared_generic_role_names(path):
    assert TELECOM_ROLE.findall(body(path)) == []


# ---------- shared worked example vocabulary ----------

# inc-2041 is the incident and correlation ID; the ticket ID comes from the create call.
INCIDENT_AS_TICKET = re.compile(r"inc-2041`?\s+ticket", re.I)


@pytest.mark.parametrize("path", [*platform_pages(), NOTIFY_GATE_PAGE], ids=_id)
def test_example_incident_id_is_not_a_ticket_id(path):
    assert not INCIDENT_AS_TICKET.search(body(path))


def _abstention_floor_rows(path: Path) -> list[list[str]]:
    rows = []
    for table in page_tables(path):
        if set(PARAM_TABLE_HEADER) <= set(table[0]):
            controls = table[0].index("What it controls")
            rows += [r for r in table[1:] if "floor" in r[0].lower()
                     and "Safety slot" in r[controls] and re.search(r"abstain", r[controls])]
    return rows


def test_abstention_floor_has_one_name_and_owner():
    """The gating and evaluation pages name the Safety abstention floor the same
    way and give it the same owner."""
    found = {_id(p): _abstention_floor_rows(p) for p in (GATING, ACCEPTANCE)}
    assert all(len(rows) == 1 for rows in found.values()), found
    (g,), (e,) = found.values()
    who = PARAM_TABLE_HEADER.index("Who sets it")
    assert g[0] == e[0], (g[0], e[0])
    assert g[who] == e[who], (g[who], e[who])


# ---------- evaluation and acceptance ----------

ACCEPTANCE = REPO_ROOT / "platform/evaluation-acceptance/README.md"
LADDER_STAGES = [
    "Intake and smoke",
    "Public sanity",
    "Operator offline acceptance",
    "Safety and red team",
    "Shadow, then canary",
]
TRAJECTORY_CHECKS = (
    "No unnecessary writes",
    "ID retention",
    "Failed actions surfaced",
    "Verification after fix",
    "Fact vs theory",
)


def _h3_text(text: str, name: str) -> str:
    """Raw markdown between "### <name>" and the next H2 or H3."""
    m = re.search(rf"^### {re.escape(name)}[ \t]*$", text, re.M)
    assert m, f"no '### {name}'"
    nxt = re.search(r"^#{2,3} ", text[m.end() :], re.M)
    return text[m.end() : m.end() + nxt.start()] if nxt else text[m.end() :]


def test_acceptance_ladder():
    table = table_with_header(ACCEPTANCE, "Reference design", ["Stage"])
    assert table[0][0] == "Stage"
    assert [row[0] for row in table[1:]] == LADDER_STAGES


def test_acceptance_trajectory_checks():
    header = ["Check", "How it is computed", "Type"]
    table = table_with_header(ACCEPTANCE, "Reference design", header)
    assert table[0] == header
    firsts = [row[0] for row in table[1:]]
    for want in TRAJECTORY_CHECKS:
        assert any(f.startswith(want) for f in firsts), want


def test_acceptance_per_slot_gates():
    table = table_with_header(ACCEPTANCE, "Reference design", PARAM_TABLE_HEADER)
    assert table[0] == PARAM_TABLE_HEADER
    rows = " ".join(" ".join(row) for row in table[1:])
    assert re.search(r"\bLLM\b|\bllm\b", rows)
    for want in ("Safety", "Classification", "Decision", "no-write"):
        assert want in rows, want
    assert "Embedding" in rows or "Reranker" in rows


def test_acceptance_false_act_method():
    text = _h3_text(reference_design_text(ACCEPTANCE), "False-ACT method")
    assert "rule of three" in text
    assert "3/n" in text


def test_acceptance_zero_tolerance():
    text = _h3_text(reference_design_text(ACCEPTANCE), "Zero-tolerance rules")
    assert "duplicate ticket" in text
    assert "secret" in text


def test_acceptance_regression_triggers():
    header = ["Change", "What re-runs"]
    table = table_with_header(ACCEPTANCE, "Reference design", header)
    assert table[0] == header
    assert len(table) - 1 >= 8


def test_acceptance_suites():
    text = body(ACCEPTANCE)
    for want in (
        "bring-your-own-framework",
        "GSMA Open-Telco",
        "https://github.com/gsma-labs/evals",
        "promotion pipeline",
    ):
        assert want in text, want


def test_acceptance_no_gap_wording():
    text = CODE_FENCE.sub("", body(ACCEPTANCE))
    assert not re.search(r"\bgaps?\b", text, re.I)
    assert not re.search(r"not yet", text, re.I)


def test_acceptance_mermaid_capabilities():
    fence = mermaid_fences(body(ACCEPTANCE))[0]
    for want in LADDER_STAGES[:4] + ["Promotion pipeline", "Model registry"]:
        assert want in fence, want
    assert PRODUCT_TERMS.findall(fence) == []


# ---------- adaptation ----------

ADAPTATION = REPO_ROOT / "platform/adaptation/README.md"
LADDER_PAGE = REPO_ROOT / "architecture/adaptation-ladder.md"
MANIFEST_FIELDS = (
    "backend_pattern",
    "io_schema",
    "risk_class",
    "allowed_identities",
    "rate_class",
    "data_class",
)
KSERVE_OCI_ISSUE = "https://github.com/kserve/kserve/issues/6094"


def test_adaptation_rungs_match_ladder():
    table = table_with_header(ADAPTATION, "Reference design", ["Rung", "Gate to climb"])
    ladder = table_with_header(LADDER_PAGE, "The design", ["Rung", "Climb when"])
    assert [row[0] for row in table[1:]] == [row[0] for row in ladder[1:]]
    assert "adaptation-ladder.md" in reference_design_text(ADAPTATION)


def test_adaptation_manifest_fields():
    fences = YAML_FENCE.findall(body(ADAPTATION))
    assert len(fences) == 1
    fence = fences[0]
    assert len(fence.strip().splitlines()) <= MAX_YAML_LINES
    for key in MANIFEST_FIELDS:
        assert re.search(rf"^{key}:", fence, re.M), key
    assert "noc-triage-agent" in fence


def test_adaptation_retrain_and_regate():
    text = re.sub(r"\s+", " ", body(ADAPTATION))
    sentences = re.split(r"(?<=[.!?])\s", text)
    assert any(
        "retrain" in s.lower()
        and "re-gate" in s.lower()
        and ("base revision" in s or "base-model revision" in s)
        for s in sentences
    )


def test_adaptation_static_adapters():
    code = "\n".join(CODE_FENCE.findall(body(ADAPTATION)))
    assert "--lora-modules" in code
    assert "--max-lora-rank" in code
    text = ADAPTATION.read_text(encoding="utf-8")
    assert "VLLM_ALLOW_RUNTIME_LORA_UPDATING=True" not in text
    for line in text.splitlines():
        if "VLLM_ALLOW_RUNTIME_LORA_UPDATING" in line:
            assert re.search(r"(?i)never|block", line), line


def test_adaptation_no_oci_adapter_uris():
    text = body(ADAPTATION)
    assert "object storage" in text
    assert KSERVE_OCI_ISSUE in text


def test_adaptation_components():
    rows = tables(sections(body(ADAPTATION)).get("Components", []))[0][1:]
    text = " ".join(" ".join(row) for row in rows)
    for want in ("Training Hub", "SDG Hub"):
        assert want in text, want
    assert "model registry" in text.lower()


def test_adaptation_method_table():
    table = table_with_header(ADAPTATION, "Reference design", ["Method", "Use when"])
    firsts = [row[0] for row in table[1:]]
    for want in ("LoRA", "QLoRA", "OSFT", "GRPO"):
        assert any(re.search(rf"\b{want}\b", f) for f in firsts), want


def test_adaptation_training_data_covers_labels():
    text = reference_design_text(ADAPTATION)
    for want in ("LOOK", "NOTIFY", "REVIEW", "STOP"):
        assert want in text, want
    assert "decision-gate.md" in text


TRAINING_DATA_CHECKS = ("provenance", "usage rights", "personal data", "traffic and location",
                        "lawful basis", "label balance")
TRAINING_DATA_ANCHOR = "../adaptation/README.md#training-data-checks"


def test_adaptation_training_data_checks():
    h3 = _h3_matching(reference_design_text(ADAPTATION), "Training data checks")
    table = next(t for t in _text_tables(h3) if t[0][:2] == ["Check", "What it enforces"])
    checks = " ".join(row[0] for row in table[1:]).lower()
    for want in TRAINING_DATA_CHECKS:
        assert want in checks, want
    for want in ("LOOK", "NOTIFY", "REVIEW", "STOP"):
        assert want in _table_text(table), want
    gates = section_text(ADAPTATION, "Sources and acceptance")
    assert "- Gate: no dataset enters training without passing the training data checks." in gates


def test_compliance_data_checks_link_the_adaptation_checks():
    """Every compliance mention of data checks points at the checks on the
    adaptation page, and every line that links them names training data."""
    text = body(COMPLIANCE)
    lines = [line for line in text.splitlines() if re.search(r"data checks", line, re.I)]
    assert lines
    for line in lines:
        assert TRAINING_DATA_ANCHOR in line, line
        assert re.search(r"training data checks", line, re.I), line


def test_adaptation_mermaid_capabilities():
    fence = mermaid_fences(body(ADAPTATION))[0]
    for want in ("Measured evaluation gap", "Registry binds base revision"):
        assert want in fence, want
    assert PRODUCT_TERMS.findall(fence) == []


# ---------- quality operations ----------

QUALITY = REPO_ROOT / "platform/quality-operations/README.md"
GENAI_CONVENTIONS = "https://github.com/open-telemetry/semantic-conventions-genai"
QUALITY_SIGNALS = ("abstention", "groundedness", "gate label", "override", "tool error", "root-cause")
GENERIC_ROLE = re.compile(
    r"\b(business owner|approver|platform team|model owner|risk owner|security"
    r"|data protection officer|change board|operations engineer|SME|subject-matter expert"
    r"|legal team)\b",
    re.I,
)
INLINE_CODE = re.compile(r"`[^`\n]+`")


def _without_code(text: str) -> str:
    return INLINE_CODE.sub("", CODE_FENCE.sub("", text))


def test_quality_span_names():
    text = body(QUALITY)
    code = "\n".join(CODE_FENCE.findall(text))
    for want in ("invoke_agent", "execute_tool", "tools/call"):
        assert want in code, want
    assert "OpenTelemetry" in text
    assert GENAI_CONVENTIONS in text


def test_quality_drift_parameters():
    table = table_with_header(QUALITY, "Reference design", PARAM_TABLE_HEADER)
    assert table[0] == PARAM_TABLE_HEADER
    firsts = " ".join(row[0] for row in table[1:]).lower()
    for want in QUALITY_SIGNALS:
        assert want in firsts, want
    who = PARAM_TABLE_HEADER.index("Who sets it")
    for row in table[1:]:
        assert GENERIC_ROLE.search(row[who]), row[who]


def test_quality_signal_span_table():
    table = table_with_header(QUALITY, "Reference design", ["Signal", "Span"])
    span = table[0].index("Span")
    assert len(table) - 1 >= 6
    for row in table[1:]:
        cell = row[span]
        assert "`" in cell or "gate decision" in cell or "action outcome" in cell, cell


def test_quality_incident_table():
    table = table_with_header(QUALITY, "Reference design", ["Trigger", "First action"])
    text = " ".join(" ".join(row) for row in table)
    for want in ("NOC", "SOC", "false ACT", "../safety-autonomy-gating/README.md"):
        assert want in text, want


def test_quality_no_otlp_in_prose():
    text = _without_code(body(QUALITY))
    for banned in ("OTLP", "OTel trace", "OTel collector", "OTel span"):
        assert banned not in text, banned


def test_quality_content_capture_opt_in():
    text = re.sub(r"\s+", " ", body(QUALITY))
    sentences = re.split(r"(?<=[.!?])\s", text)
    assert any(
        re.search(r"opt[- ]in", s, re.I) and re.search(r"prompt|tool argument", s, re.I)
        for s in sentences
    )


def test_quality_feedback_loop():
    text = reference_design_text(QUALITY)
    for want in ("../evaluation-acceptance/README.md", "../adaptation/README.md", "SME"):
        assert want in text, want


def test_quality_nis2_deadlines_outside_parameters():
    text = body(QUALITY)
    assert "24 hours" in text and "72 hours" in text
    for table in page_tables(QUALITY):
        if set(PARAM_TABLE_HEADER) <= set(table[0]):
            assert "hour" not in " ".join(" ".join(row) for row in table).lower()


def test_quality_mermaid_capabilities():
    fence = mermaid_fences(body(QUALITY))[0]
    for want in ("Trace spans per agent step", "Drift signals", "Next golden set"):
        assert want in fence, want
    assert PRODUCT_TERMS.findall(fence) == []


# ---------- security, identity, and sandbox ----------

SECURITY = REPO_ROOT / "platform/security-identity-sandbox/README.md"
CROSSWALK_PAGE = REPO_ROOT / "architecture/crosswalk.md"
MATURITY_WORDS = ("early-stage", "Technology Preview", "Developer Preview", "community project")


def _table_text(table: list[list[str]]) -> str:
    return "\n".join(" | ".join(row) for row in table)


def test_security_sandbox_controls():
    table = table_with_header(SECURITY, "Reference design", ["Control", "What it enforces"])
    text = _table_text(table[1:]).lower()
    for want in ("shell", "read-only", "egress", "workload identity", "secrets"):
        assert want in text, want
    assert "resource" in text or "limits" in text
    egress = [r for r in table[1:] if "egress" in " ".join(r).lower()]
    assert any("AI Gateway" in " ".join(r) and "MCP Gateway" in " ".join(r) for r in egress), egress


def test_security_sandbox_options():
    table = table_with_header(SECURITY, "Reference design", ["Option", "Source"])
    text = _table_text(table[1:])
    for want in ("sandboxed containers", "Agent Sandbox", "OpenShell"):
        assert want in text, want
    src = table[0].index("Source")
    for row in table[1:]:
        assert "](http" in row[src], row


def test_security_no_maturity_labels():
    text = body(SECURITY)
    for word in MATURITY_WORDS:
        assert word.lower() not in text.lower(), word


def test_security_mirror_flow_steps():
    steps = _ordered_steps(reference_design_text(SECURITY))
    assert 0 < len(steps) <= 8, len(steps)
    joined = " ".join(steps)
    for want in ("oc-mirror", "HF_HUB_OFFLINE=1", "signed", "Python index", "object storage", "teacher"):
        assert want in joined, want


def test_security_offline_changes():
    table = table_with_header(SECURITY, "Reference design", ["What changes offline"])
    text = _table_text(table)
    for want in ("approximate", "/v1/chat/completions", "/v1/systemone", "runtime adapter",
                 "external provider"):
        assert want.lower() in text.lower(), want


def test_security_tool_output_injection():
    table = None
    for header in ("Defence", "Defense"):
        try:
            table = table_with_header(SECURITY, "Reference design", [header])
            break
        except AssertionError:
            continue
    assert table, "no defence table"
    rows = [" | ".join(r) for r in table[1:]]
    assert any(
        re.search(r"tool (response|output)", r, re.I) and "fail closed" in r.lower() for r in rows
    ), rows
    assert "../integration/README.md" in _table_text(table)


def test_security_secrets_never_in_context():
    text = re.sub(r"\s+", " ", body(SECURITY))
    sentences = re.split(r"(?<=[.!?])\s", text)
    assert any(
        "never" in s.lower() and "model context" in s.lower() and "secret" in s.lower()
        for s in sentences
    )


def test_security_mermaid_capabilities():
    fence = mermaid_fences(body(SECURITY))[0]
    for want in ("Workload identity", "Screen for injection"):
        assert want in fence, want
    assert PRODUCT_TERMS.findall(fence) == []


def test_security_identity_links_integration():
    table = table_with_header(SECURITY, "Reference design", ["Concern", "Design"])
    text = _table_text(table).lower()
    assert "per agent" in text or "per-agent" in text
    assert "short-lived" in text
    assert "../integration/readme.md" in text


def test_crosswalk_used_by_links_each_platform_page():
    text = body(CROSSWALK_PAGE)
    assert "PB-04 to PB-08" not in text
    for slug in ("serving-routing-placement", "integration", "safety-autonomy-gating",
                 "action-layer", "security-identity-sandbox"):
        assert f"../platform/{slug}/README.md" in text, slug


# ---------- drop-back rules (shared across pages) ----------

DEMOTE = re.compile(r"(?i)\bdrops?\b[^.|]*\bback\b|\bdrop back\b|\bdemot")
NO_DEMOTE = re.compile(r"(?i)\bdoes not drop\b|\bdoesn't drop\b|\bkeeps its stage\b|\bwithout a drop\b")


def _units(path: Path) -> list[str]:
    """Prose sentences plus table rows, so a rule in either form is one unit."""
    rows = [" | ".join(r) for t in page_tables(path) for r in t[1:]]
    return _sentences(body(path)) + rows


def test_gating_drop_back_rules():
    """A confirmed false ACT drops a stage; a blocked injection opens a SOC case
    and does not, so planted text cannot force autonomy down."""
    staged = re.sub(r"\s+", " ", _h3_text(reference_design_text(GATING), "Staged autonomy"))
    sentences = re.split(r"(?<=[.!?])\s", staged)
    assert any("confirmed false ACT" in s and "back one stage" in s for s in sentences), staged
    assert any("injection" in s and "SOC case" in s and NO_DEMOTE.search(s) and "attacker" in s
               for s in sentences), staged


@pytest.mark.parametrize("path", [GATING, SECURITY, QUALITY], ids=_id)
def test_injection_never_drops_a_stage(path):
    for unit in _units(path):
        if re.search(r"(?i)injection", unit) and DEMOTE.search(unit):
            assert NO_DEMOTE.search(unit), unit


@pytest.mark.parametrize("path", [SECURITY, QUALITY], ids=_id)
def test_false_act_drop_needs_confirmation(path):
    for unit in _units(path):
        if re.search(r"false ACT", unit) and DEMOTE.search(unit):
            assert "confirmed" in unit, unit



# ---------- intake and model selection ----------

INTAKE = REPO_ROOT / "platform/intake-model-selection/README.md"
FAMILY_HEADER = ["Slot", "OTel checkpoint", "Base model", "Licence", "Source"]
COMMIT_HASH = re.compile(r"\b[0-9a-f]{12,}\b")


def _sentences(text: str) -> list[str]:
    """Prose sentences only: table rows and code fences are left out."""
    prose = "\n".join(
        line for line in CODE_FENCE.sub("", text).splitlines() if not line.lstrip().startswith("|")
    )
    return re.split(r"(?<=[.!?])\s", re.sub(r"\s+", " ", prose))


def test_intake_family_table():
    table = table_with_header(INTAKE, "Reference design", FAMILY_HEADER)
    rows = table[1:]
    lic = table[0].index("Licence")
    src = table[0].index("Source")

    def row(name: str) -> list[str]:
        hits = [r for r in rows if name in " ".join(r)]
        assert hits, name
        return hits[0]

    for name in ("OTel-2.0-LLM-31B-IT", "OTel-2.0-Decision-26B-A4B-4bit", "OTel-LLM-12B-Safety",
                 "OTel-LLM-8.3B-Safety", "OTel-LLM-8.3B-Classification", "Reranker", "Embedding"):
        row(name)
    assert "Apache-2.0" in row("OTel-2.0-LLM-31B-IT")[lic]
    assert "Apache-2.0" in row("OTel-2.0-Decision-26B-A4B-4bit")[lic]
    assert "Gemma Terms of Use" in row("OTel-LLM-12B-Safety")[lic]
    for r in rows:
        assert "huggingface.co" in r[src], r


def test_intake_rnj_not_gemma_base():
    table = table_with_header(INTAKE, "Reference design", FAMILY_HEADER)
    rows = [" | ".join(r) for r in table[1:] if "8.3B" in " ".join(r)]
    assert rows
    for r in rows:
        assert "rnj-1" in r, r
        assert "Gemma 3" not in r, r
    for s in _sentences(body(INTAKE)):
        if "8.3B" in s and "Gemma 3" in s:
            assert "architecture class" in s and "config.json" in s, s


def test_intake_lfm_licence_trap():
    text = body(INTAKE)
    assert any("LFM Open License" in " ".join(r) for t in page_tables(INTAKE) for r in t[1:])
    for size in ("1.2B", "8B-A1B", "24B"):
        assert size in text, size
    table = table_with_header(INTAKE, "Reference design", ["Licence", "What it says"])
    assert "10,000,000" in _table_text(table)


def test_intake_dated_family_note():
    assert re.search(r"Checked against the model cards on \d{4}-\d{2}-\d{2}", body(INTAKE))


def test_intake_check_steps():
    steps = _ordered_steps(reference_design_text(INTAKE))
    assert 0 < len(steps) <= 8, len(steps)
    joined = " ".join(steps).lower()
    for want in ("base model", "redistribution", "use restrictions", "attribution", "derivative",
                 "adapter", "legal review"):
        assert want in joined, want


def test_intake_legal_line():
    assert "your legal team decides what they mean for you" in re.sub(r"\s+", " ", body(INTAKE))


def test_intake_no_commit_hashes():
    assert COMMIT_HASH.findall(body(INTAKE)) == []


def test_intake_pinned_and_signed():
    text = body(INTAKE)
    for want in ("pinned", "revision", "signed", "ModelCar"):
        assert want in text, want
    assert any(
        "signature" in s.lower() and "revision" in s.lower() and "also" in s.lower()
        for s in _sentences(text)
    )


def test_intake_licence_sources():
    table = table_with_header(INTAKE, "Sources and acceptance", ["Claim", "Basis", "Source"])
    basis = table[0].index("Basis")
    src = table[0].index("Source")
    for url in ("https://ai.google.dev/gemma/terms", "https://ai.google.dev/gemma/docs/gemma_4_license"):
        hits = [r for r in table[1:] if f"({url})" in r[src]]
        assert hits, url
        assert all(r[basis] == "project documentation" for r in hits), hits


def test_intake_selection_guide():
    table = table_with_header(INTAKE, "Reference design", ["Slot", "Pick when"])
    rows = table[1:]
    assert len(rows) == 6
    text = " ".join(r[0] for r in rows).lower()
    for slot in ("llm", "embedding", "reranker", "safety", "decision", "classification"):
        assert slot in text, slot


def test_intake_mermaid_capabilities():
    fence = mermaid_fences(body(INTAKE))[0]
    for want in ("Licence chain recorded", "Verify signature and revision"):
        assert want in fence, want
    assert PRODUCT_TERMS.findall(fence) == []


# ---------- compliance and operating model ----------

COMPLIANCE = REPO_ROOT / "platform/compliance-operating-model/README.md"
ALLOWED_ROLES = {
    "business owner",
    "approver",
    "platform team",
    "model owner",
    "risk owner",
    "security",
    "data protection officer",
    "change board",
    "operations engineer",
    "sme",
    "subject-matter expert",
    "legal team",
}
RECORD_FIELDS = (
    "system description",
    "intended purpose",
    "risk-category reasoning",
    "human oversight",
    "logging",
    "data governance",
)
LEGAL_LINE = "Your legal team owns the classification."
LEGAL_CONCLUSION = re.compile(
    r"(?i)\b(is|are) not high-risk\b|\bcomplian(t|ce) with\b|\bcomplies with\b"
    r"|\bis exempt\b|\bmeets the AI Act\b|\byou are a provider\b"
    r"|\bdo(es)?(n't| not) apply\b|\b(is|are) out of scope\b"
    r"|\b(triage|the system|this system|the use case|this use case) falls outside\b"
    r"|\b(is|are) not a safety component\b|\bonly to engineers\b"
    r"|\brecord the exclusion\b|\bthe exclusion applies\b"
)
# An applicability call in a map's control column: the control says when a
# provision applies, or names the example use case.
APPLICABILITY = re.compile(r"(?i)\bapplies (where|to|only)\b|\btriage\b")
ROI_MEASURES = (
    "mean time to identify",
    "auto-triaged",
    "engineer hours saved",
    "false-ACT cost",
    "abstention handling cost",
)
GSMA_LEVELS = ("Foundational", "Evolving", "Performing", "Advanced")


def _text_tables(text: str) -> list[list[list[str]]]:
    """Tables in a slice of raw markdown."""
    return tables(sections("## Slice\n" + text)["Slice"])


def _h3_matching(text: str, *words: str) -> str:
    """Raw markdown under the first H3 whose heading holds every word."""
    for m in re.finditer(r"^### (.+)$", text, re.M):
        if all(w in m.group(1) for w in words):
            nxt = re.search(r"^#{2,3} ", text[m.end() :], re.M)
            return text[m.end() : m.end() + nxt.start()] if nxt else text[m.end() :]
    raise AssertionError(f"no H3 holding {words}")


def _text_fences(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"^```text\n(.*?)^```", text, re.M | re.S)]


def _control_tables() -> list[list[list[str]]]:
    rd = tables(sections(body(COMPLIANCE)).get("Reference design", []))
    return [t for t in rd if any("Blueprint control" in h for h in t[0])]


def test_compliance_example_record():
    record = _h3_matching(reference_design_text(COMPLIANCE), "Example", "classification record")
    table = next(t for t in _text_tables(record) if t[0][:2] == ["Field", "Example entry"])
    fields = " ".join(row[0].lower() for row in table[1:])
    for want in RECORD_FIELDS:
        assert want in fields, want
    for want in ("Annex III", "Article 6(1a)", "2026/1744", "2024/1689", "December 2, 2027"):
        assert want in record, want


def test_compliance_record_true_at_every_stage():
    """The example record says the act stage runs approved playbooks with no
    approver, and promotion to the act stage reopens the record."""
    record = _h3_matching(reference_design_text(COMPLIANCE), "Example", "classification record")
    table = next(t for t in _text_tables(record) if t[0][:2] == ["Field", "Example entry"])
    purpose = next(row[1] for row in table[1:] if row[0] == "Intended purpose")
    assert "act stage" in purpose and "without an approver" in purpose, purpose
    reasoning = next(row[1] for row in table[1:] if row[0] == "Risk-category reasoning")
    assert "before every change" not in reasoning, reasoning
    assert "each stage" in reasoning, reasoning
    reopen = "Promotion to the act stage reopens the classification record"
    gates = section_text(COMPLIANCE, "Sources and acceptance")
    assert any(reopen.lower() in line.lower() for line in gates.splitlines()
               if line.startswith("- Gate:"))
    rollout = _h3_matching(reference_design_text(COMPLIANCE), "Staged rollout")
    assert reopen in re.sub(r"\s+", " ", rollout)
    risks = _table_text(table_with_header(COMPLIANCE, "Risks and limitations", ["Risk", "Mitigation"]))
    assert "act stage" in risks and "reopens the classification record" in risks


def test_compliance_blank_record():
    fences = _text_fences(body(COMPLIANCE))
    assert any(all(f in fence.lower() for f in RECORD_FIELDS) for fence in fences)


def test_compliance_legal_ownership_line():
    assert re.sub(r"\s+", " ", body(COMPLIANCE)).count(LEGAL_LINE) == 1


def test_compliance_legal_team_accountable_for_classification():
    """The ownership line and the RACI agree: the legal team is accountable."""
    table = table_with_header(COMPLIANCE, "Operating model", ["Activity", "Accountable"])
    row = next(r for r in table[1:] if r[0].startswith("Classify the use case"))
    assert row[table[0].index("Accountable")] == "Legal team", row
    assert "Legal team" not in row[table[0].index("Consulted")], row


@pytest.mark.parametrize(
    ("text", "hit"),
    [
        ("Article 50 does not apply because triage talks to engineers", True),
        ("This provision doesn't apply to network elements", True),
        ("Triage is out of scope for Annex III", True),
        ("NOC triage talks only to engineers", True),
        ("Record the exclusion and the date you checked it", True),
        ("Triage falls outside high risk", True),
        ("The system is not a safety component", True),
        ("Record whether your legal team relies on the exclusion", False),
        ("An Annex III system that poses no significant risk falls outside high risk", False),
        ("Articles 9 to 15 apply only to high-risk systems", False),
    ],
)
def test_legal_conclusion_pattern_cases(text, hit):
    assert bool(LEGAL_CONCLUSION.search(text)) is hit


def test_compliance_no_legal_conclusions():
    assert LEGAL_CONCLUSION.findall(CODE_FENCE.sub("", body(COMPLIANCE))) == []


def test_compliance_control_columns_make_no_applicability_call():
    for table in _control_tables():
        col = next(i for i, h in enumerate(table[0]) if "Blueprint control" in h)
        for row in table[1:]:
            assert not APPLICABILITY.search(row[col]), (row[0], row[col])


def test_compliance_no_scope_note_rows():
    """The maps leave scope calls on transparency and automated decisions to the
    legal team, so neither provision gets a row of its own."""
    for table in _control_tables():
        firsts = [row[0] for row in table[1:]]
        assert not any(re.match(r"Article 50\b", f) for f in firsts), firsts
        assert not any(re.match(r"GDPR Article 22\b", f) for f in firsts), firsts


def test_compliance_data_governance_states_facts():
    record = _h3_matching(reference_design_text(COMPLIANCE), "Example", "classification record")
    table = next(t for t in _text_tables(record) if t[0][:2] == ["Field", "Example entry"])
    for field in ("Data governance", "Fundamental rights impact assessment"):
        cell = next(row[1] for row in table[1:] if row[0] == field)
        assert not LEGAL_CONCLUSION.search(cell), (field, cell)
        assert not re.search(r"(?i)\bholds no\b|\bno subscriber\b", cell), (field, cell)


def test_compliance_regimes_mapped():
    found = _control_tables()
    text = "\n".join(_table_text(t) for t in found)
    for want in ("NIS2", "GDPR", "CAMARA", "GSMA"):
        assert want in text or want in reference_design_text(COMPLIANCE), want
    assert len(found) >= 5, len(found)
    for t in found:
        if "Source" in t[0]:
            src = t[0].index("Source")
            for row in t[1:]:
                assert "](http" in row[src], row
    ai_act = _text_tables(_h3_matching(reference_design_text(COMPLIANCE), "EU AI Act map"))[0]
    col = ai_act[0].index("Blueprint control")
    controls = " ".join(row[col] for row in ai_act[1:])
    for link in ("decision-gate.md", "../safety-autonomy-gating/README.md",
                 "../action-layer/README.md", "../evaluation-acceptance/README.md"):
        assert link in controls, link


def test_compliance_regime_headings():
    rd = reference_design_text(COMPLIANCE)
    for words in (("NIS2",), ("GDPR",), ("CAMARA",), ("GSMA",)):
        h3 = _h3_matching(rd, *words)
        assert any(any("Blueprint control" in h for h in t[0]) for t in _text_tables(h3)), words


def test_compliance_raci_generic_roles():
    table = table_with_header(
        COMPLIANCE, "Operating model", ["Activity", "Responsible", "Accountable", "Consulted", "Informed"]
    )
    for row in table[1:]:
        for name in ("Responsible", "Accountable", "Consulted", "Informed"):
            cell = row[table[0].index(name)]
            for role in re.split(r",\s*|\s+and\s+", cell):
                role = role.strip().lower()
                if role:
                    assert role in ALLOWED_ROLES, (row[0], role)


def test_compliance_rollout_and_roi():
    rd = reference_design_text(COMPLIANCE)
    table = table_with_header(COMPLIANCE, "Reference design", ["Stage", "What is allowed"])
    assert [row[0] for row in table[1:]] == ["Shadow", "Assist", "Recommend", "Act"]
    assert "../safety-autonomy-gating/README.md" in rd
    for want in ROI_MEASURES:
        assert want in rd, want
    assert "shadow-stage baseline" in rd
    fences = [f for f in _text_fences(rd) if "value per period" in f]
    assert fences
    assert not any(re.search(r"\d", f) for f in fences)


def test_compliance_residency():
    table = table_with_header(COMPLIANCE, "Reference design", ["Data", "Where it lives"])
    text = _table_text(table[1:]).lower()
    for want in ("prompts", "retrieved passages", "traces", "training data", "adapters"):
        assert want in text, want


def test_compliance_gsma_levels_named():
    text = body(COMPLIANCE)
    for level in GSMA_LEVELS:
        assert level in text, level
    for s in _sentences(text):
        if "GSMA" in s:
            assert not re.search(r"\bLevel [0-9]", s), s


def test_compliance_mermaid_capabilities():
    fence = mermaid_fences(body(COMPLIANCE))[0]
    for want in ("Classification record", "Legal review", "shadow baseline"):
        assert want in fence, want
    assert PRODUCT_TERMS.findall(fence) == []
