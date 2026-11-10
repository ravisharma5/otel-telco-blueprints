"""Reference pages: per-page content checks and the recipe wording rule.

Reference pages are recipes. They say how to build a design, not how far it
has been tested, so they carry no validation-status wording and no readiness
levels. Vale scopes rules by path and the blueprint templates legitimately use
that wording, so the rule lives here.

The helpers below are shared: per-page tests for each reference page go in
this module and call them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from markdown_it import MarkdownIt

from tools.bplint.loader import load_yaml, split_front_matter
from tools.tests.conftest import REPO_ROOT

TEMPLATE = REPO_ROOT / "templates/reference-page.md"
CONFIG = REPO_ROOT / "tools/bplint/config.yaml"

# Words are matched case-insensitively; readiness levels (E0-E4, M0-M3) are
# matched case-sensitively so names like MI300X or "e2e" never trip the rule.
WORDING = re.compile(
    r"\b(?:(?i:unverified|unvalidated|untested"
    r"|not\s+(?:yet\s+)?(?:validated|verified|tested|run|measured))"
    r"|E[0-4]\b(?!\d)|M[0-3]\b)"
)
FENCE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.M | re.S)
EXEMPT_CELL = re.compile(r"^E[1-7]$")
MERMAID_KEYWORDS = ("flowchart", "graph", "sequenceDiagram")


# ---------- helpers ----------


def _md():
    return MarkdownIt("commonmark").enable("table")


def reference_pages() -> list[Path]:
    """Pages matched by reference_globs whose front matter type is reference."""
    out = []
    for pattern in load_yaml(CONFIG).get("reference_globs") or []:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_file() and (front_matter(path) or {}).get("type") == "reference":
                out.append(path)
    return out


def front_matter(path: Path) -> dict | None:
    fm, _, _ = split_front_matter(Path(path).read_text(encoding="utf-8"))
    return fm


def body(path: Path) -> str:
    _, text, _ = split_front_matter(Path(path).read_text(encoding="utf-8"))
    return text


def sections(text):
    """Map h2 title -> list of tokens in that section."""
    tokens = _md().parse(text)
    out, current = {}, None
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.tag == "h2":
            current = tokens[i + 1].content
            out[current] = []
        elif current is not None:
            out[current].append(tok)
    return out


def tables(tokens):
    """Tables in a token list, each a list of rows (header row first)."""
    tables, rows, row, in_table = [], [], None, False
    for tok in tokens:
        if tok.type == "table_open":
            in_table, rows = True, []
        elif tok.type == "table_close":
            in_table = False
            tables.append(rows)
        elif in_table and tok.type == "tr_open":
            row = []
        elif in_table and tok.type == "tr_close":
            rows.append(row)
        elif in_table and tok.type == "inline":
            row.append(tok.content.strip())
    return tables


def _fences(text: str, info: str) -> list[str]:
    return [
        t.content
        for t in _md().parse(text)
        if t.type == "fence" and t.info.strip().split(" ")[0] == info
    ]


def mermaid_fences(text: str) -> list[str]:
    return _fences(text, "mermaid")


def json_fences(text: str) -> list:
    return [json.loads(content) for content in _fences(text, "json")]


def flows(text: str) -> dict[str, str]:
    """Map lowercased "### Flow: <name>" names to the first mermaid fence under them."""
    tokens = _md().parse(text)
    out: dict[str, str] = {}
    for i, tok in enumerate(tokens):
        if not (tok.type == "heading_open" and tok.tag == "h3"):
            continue
        title = tokens[i + 1].content.strip()
        if not title.startswith("Flow: "):
            continue
        name = title[len("Flow: ") :].strip().lower()
        for nxt in tokens[i + 3 :]:
            if nxt.type == "heading_open":
                break
            if nxt.type == "fence" and nxt.info.strip().split(" ")[0] == "mermaid":
                out[name] = nxt.content
                break
    return out


def _drop_exempt_cells(line: str) -> str:
    if not line.lstrip().startswith("|"):
        return line
    cells = line.split("|")
    return "|".join("" if EXEMPT_CELL.match(c.strip()) else c for c in cells)


def wording_hits(text: str) -> list[str]:
    """Validation-status wording and readiness levels outside code fences.

    Table cells that hold only an extension-row id (E1-E7) are allowed.
    """
    text = FENCE.sub("", text)
    text = "\n".join(_drop_exempt_cells(line) for line in text.splitlines())
    return [m.group(0) for m in WORDING.finditer(text)]


def _scanned_files() -> list[Path]:
    return [*reference_pages(), TEMPLATE]


# ---------- the wording rule ----------


@pytest.mark.parametrize(
    "sample",
    [
        "This step is unverified.",
        "The routing is not yet validated.",
        "Not tested on this hardware.",
        "The path is untested.",
        "This sits at readiness E2.",
        "The model level M1 applies.",
        "The figure was not measured.",
    ],
)
def test_wording_regex_catches(sample):
    assert wording_hits(sample), sample


@pytest.mark.parametrize(
    "sample",
    [
        "This page is a draft pending review by the agent-school maintainers.",
        "Run it on an MI300X node.",
        "| E7 | Extension row |",
        "| E2 | Extension row |",
        "Serve each LoRA adapter on its base.",
        "PB-02 builds on this page.",
        "```text\nnot yet validated\n```",
        "Use e2e tests and m3 storage.",
    ],
)
def test_wording_regex_allows(sample):
    assert wording_hits(sample) == [], sample


def test_wording_exempt_cell_only_when_whole_cell():
    assert wording_hits("| Row E2 here | x |")
    assert wording_hits("The E2 row is optional.")


@pytest.mark.parametrize("path", _scanned_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_wording_reference_pages(path):
    assert wording_hits(path.read_text(encoding="utf-8")) == []


# ---------- shared structure ----------


@pytest.mark.parametrize("path", _scanned_files(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_mermaid_fences_start_with_known_keyword(path):
    for fence in mermaid_fences(body(path)):
        first = next((ln.strip() for ln in fence.splitlines() if ln.strip()), "")
        assert first.split(" ")[0] in MERMAID_KEYWORDS, (path, first)


def test_flow_helper():
    sample = (
        "## The design\n\n"
        "### Flow: grounded answer\n\n"
        "Some text.\n\n"
        "```mermaid\nflowchart LR\n  A --> B\n```\n\n"
        "### Flow: empty\n\n"
        "### Other\n\n"
        "```mermaid\ngraph TD\n  C --> D\n```\n"
    )
    assert flows(sample) == {"grounded answer": "flowchart LR\n  A --> B\n"}


def test_json_fence_helper():
    sample = '```json\n{"label": "LOOK"}\n```\n\n```text\n{}\n```\n'
    assert json_fences(sample) == [{"label": "LOOK"}]


def test_reference_pages_helper_reads_config():
    assert TEMPLATE not in reference_pages()
    for path in reference_pages():
        assert front_matter(path)["type"] == "reference"


# ---------- readiness questions (framework landing page) ----------

READINESS = REPO_ROOT / "framework/index.md"
PB_IDS = [f"PB-{i:02d}" for i in range(1, 11)]
READINESS_DOMAINS = [
    "intake",
    "evaluation",
    "adaptation",
    "serving",
    "integration",
    "autonomy",
    "security",
    "quality",
    "compliance",
    "operating model",
]
MD_LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")


def _readiness_rows():
    """Body rows of the ten-questions table in The design."""
    design = sections(body(READINESS))["The design"]
    for table in tables(design):
        header = table[0]
        if {"Question", "What ready means", "Answered by"} <= set(header):
            return header, table[1:]
    raise AssertionError("no ten-questions table in The design")


def _cell(header, row, name):
    return row[header.index(name)]


def test_readiness_is_reference():
    fm = front_matter(READINESS)
    assert fm["type"] == "reference"
    assert fm["platform_blueprints"] == PB_IDS


def test_readiness_ten_questions():
    header, rows = _readiness_rows()
    assert len(rows) == 10
    assert [row[0] for row in rows] == [str(i) for i in range(1, 11)]


def test_readiness_domains_in_order():
    header, rows = _readiness_rows()
    for row, domain in zip(rows, READINESS_DOMAINS, strict=True):
        assert domain in _cell(header, row, "Question").lower(), (domain, row)


def test_readiness_answered_by():
    header, rows = _readiness_rows()
    answered = [_cell(header, row, "Answered by") for row in rows]
    for pb in PB_IDS:
        assert any(pb in cell for cell in answered), pb
    assert "PB-06" in answered[5] and "PB-07" in answered[5]
    assert "PB-10" in answered[8] and "PB-10" in answered[9]


def test_readiness_no_pb_links():
    for text, target in MD_LINK.findall(body(READINESS)):
        for bad in ("PB-", "platform/"):
            assert bad not in text and bad not in target, (text, target)


# ---------- architecture overview (architecture landing page) ----------

OVERVIEW = REPO_ROOT / "architecture/index.md"
SLOTS = ["llm", "embedding", "reranker", "safety", "decision", "classification"]
LAYERS = [
    "Data and knowledge",
    "Model endpoint inferencing",
    "Network capabilities",
    "AI Gateway",
    "MCP Gateway",
    "Agent runtime",
    "Safety and governance",
    "Action",
    "Placement",
    "Evaluation",
    "Adaptation",
    "Observability",
    "Control",
]
PLANES = ["Data and execution", "Placement", "Lifecycle", "Control"]


def _design_tables(path):
    return tables(sections(body(path))["The design"])


def test_overview_is_reference():
    fm = front_matter(OVERVIEW)
    assert fm["type"] == "reference"
    assert set(SLOTS) <= set(fm["otel_slots"])


def test_overview_slots():
    for table in _design_tables(OVERVIEW):
        header = " ".join(table[0]).lower()
        if "slot" not in header or "role" not in header or "red hat product" not in header:
            continue
        firsts = [row[0].lower() for row in table[1:]]
        assert len(firsts) == len(SLOTS), firsts
        for slot in SLOTS:
            assert any(slot in cell for cell in firsts), slot
        return
    raise AssertionError("no slot, role, and product table in The design")


def test_overview_layers():
    for table in _design_tables(OVERVIEW):
        if table[0][:2] != ["Layer", "Plane"]:
            continue
        assert [row[0] for row in table[1:]] == LAYERS
        assert {row[1] for row in table[1:]} == set(PLANES)
        return
    raise AssertionError("no layer table keyed by layer and plane name in The design")


def test_overview_tiers_and_replaceable():
    text = body(OVERVIEW)
    for tier in ("far edge", "regional", "core"):
        assert tier in text.lower(), tier
    assert "Any component can be replaced" in text


def test_overview_flows():
    found = flows(body(OVERVIEW))
    for name in ("grounded answer", "investigate then act"):
        assert name in found, name
        first = next(ln.strip() for ln in found[name].splitlines() if ln.strip())
        assert first.split(" ")[0] in MERMAID_KEYWORDS, (name, first)


# ---------- decision gate ----------

GATE = REPO_ROOT / "architecture/decision-gate.md"
GATE_SCHEMA_PATH = REPO_ROOT / "schemas/decision-gate.schema.json"
GATE_SCHEMA_URL = (
    "https://github.com/ravisharma5/otel-telco-blueprints/blob/main/schemas/decision-gate.schema.json"
)
GATE_LABELS = ["LOOK", "NOTIFY", "REVIEW", "ACT", "STOP"]
NUMERIC_DEFAULT = re.compile(r"\b0?\.\d+\b|\d+\s*%")


def _find_table(path, wanted):
    """First table in The design whose header holds every name in wanted."""
    for table in _design_tables(path):
        if set(wanted) <= set(table[0]):
            return table
    raise AssertionError(f"no table with header {wanted} in The design")


def _gate_examples():
    return json_fences(body(GATE))


def _gate_validator():
    from jsonschema import Draft202012Validator

    return Draft202012Validator(json.loads(GATE_SCHEMA_PATH.read_text(encoding="utf-8")))


def _all_keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _all_keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _all_keys(v)


def test_gate_is_reference():
    fm = front_matter(GATE)
    assert fm["type"] == "reference"
    assert {"PB-02", "PB-06", "PB-07"} <= set(fm["platform_blueprints"])
    assert {"decision", "llm"} <= set(fm["otel_slots"])


def test_gate_policy_table():
    table = _find_table(GATE, ["Label", "Who acts", "What runs", "What is logged"])
    assert table[0][:4] == ["Label", "Who acts", "What runs", "What is logged"]
    assert [row[0] for row in table[1:]] == GATE_LABELS


def test_gate_paths():
    text = body(GATE)
    assert "Automation Orchestrator" in text
    assert "`uri`" in text
    firsts = [row[0] for table in _design_tables(GATE) for row in table[1:]]
    assert "Intended" in firsts and "Fallback" in firsts


def test_gate_thresholds():
    table = _find_table(GATE, ["Parameter", "How to calibrate"])
    params = " ".join(row[0].lower() for row in table[1:])
    for name in ("minimum act probability", "review band", "false-act budget", "ceiling per risk class"):
        assert name in params, name
    for row in table[1:]:
        for cell in row:
            assert not NUMERIC_DEFAULT.search(cell), cell
    text = sections(body(GATE))["The design"]
    thresholds_text = "".join(t.content for t in text if t.type == "inline")
    assert "PB-02" in thresholds_text


def test_gate_examples_validate():
    examples = _gate_examples()
    kinds = sorted(e.get("kind") for e in examples)
    assert kinds == ["action_request", "gate_decision"]
    validator = _gate_validator()
    for example in examples:
        errors = list(validator.iter_errors(example))
        assert errors == [], [e.message for e in errors]
        keys = {k.lower() for k in _all_keys(example)}
        assert "threshold" not in keys and "default" not in keys
    decision = next(e for e in examples if e["kind"] == "gate_decision")
    assert abs(sum(decision["label_probabilities"].values()) - 1) <= 0.01


def test_gate_runtime_pattern():
    tokens = _md().parse(body(GATE))
    steps, in_list, item = [], False, []
    for tok in tokens:
        if tok.type == "ordered_list_open":
            in_list, steps = True, []
        elif tok.type == "ordered_list_close":
            if len(steps) == 3:
                break
            in_list = False
        elif in_list and tok.type == "inline":
            steps.append(tok.content)
    assert len(steps) == 3, steps
    joined = " ".join(steps)
    for needle in ("action-request tool", "Decision model", "AAP"):
        assert needle in joined, needle


def test_gate_links_schema():
    assert GATE_SCHEMA_URL in body(GATE)


# ---------- adaptation ladder ----------

LADDER = REPO_ROOT / "architecture/adaptation-ladder.md"
AGENT_SCHOOL_ROADMAP = "https://github.com/open-experiments/agent-school/blob/main/docs/RoadMap.md"
RUNGS = ["Retrieval", "Skills and capability manifests", "LoRA", "OSFT"]
MANIFEST_FIELDS = [
    "backend pattern",
    "I/O schema",
    "risk class",
    "allowed identities",
    "rate class",
    "data class",
]
FOUR_FLOWS = ["grounded answer", "investigate then act", "adaptation loop", "continuous evaluation"]


def test_ladder_is_reference():
    fm = front_matter(LADDER)
    assert fm["type"] == "reference"
    assert {"PB-02", "PB-03"} <= set(fm["platform_blueprints"])


def test_ladder_rungs():
    for table in _design_tables(LADDER):
        if any("Climb when" in cell for cell in table[0]):
            assert [row[0] for row in table[1:]] == RUNGS
            return
    raise AssertionError("no rung table with a Climb when column")


def test_ladder_principle():
    principle = sections(body(LADDER))["The principle"]
    text = " ".join(t.content for t in principle if t.type == "inline").lower()
    assert "measured evaluation gap" in text


def test_ladder_401():
    text = body(LADDER)
    assert AGENT_SCHOOL_ROADMAP in text
    for field in MANIFEST_FIELDS:
        assert field.lower() in text.lower(), field


def test_ladder_flows():
    found = flows(body(LADDER))
    for name in ("adaptation loop", "continuous evaluation"):
        assert name in found, name


def test_flows_four_present():
    found = {}
    for path in reference_pages():
        found.update(flows(body(path)))
    for name in FOUR_FLOWS:
        assert name in found, name


# ---------- layer codes and product names ----------

# Layers and planes are named in words on every published page. Short layer
# codes are internal shorthand and never reach readers.
LAYER_CODE = re.compile(r"\bL(?:10|9[abc]|[0-9])\b")
# Diagrams name capabilities, never products. Page tables still name the
# product used for each role, so only diagrams are checked.
PRODUCT_TERMS = re.compile(
    r"OpenShift|Red Hat|\bRHEL\b|vLLM|KServe|llm-d|Models-as-a-Service|\bMaaS\b"
    r"|Argo CD|Keycloak|SPIFFE|SPIRE|NeMo|EvalHub|Kuadrant|Ansible|\bAAP\b"
    r"|MLflow|Perses|\bACM\b|Prometheus|OpenTelemetry|Podman|SDG Hub|Training Hub"
    r"|Automation Orchestrator|Connectivity Link|LangGraph|Device Edge"
    r"|Data Science Pipelines"
)
TEMPLATES = sorted((REPO_ROOT / "templates").glob("*.md"))


def _published_docs() -> list[Path]:
    return [*reference_pages(), *TEMPLATES]


@pytest.mark.parametrize(
    "sample", ["L0 to L7", "layer L9a", "| L10 |", "L9c observability"]
)
def test_layer_code_regex_catches(sample):
    assert LAYER_CODE.search(sample), sample


@pytest.mark.parametrize("sample", ["LLM slot", "L40S GPUs", "Layer 1", "PB-10", "OTel-LLM-12B"])
def test_layer_code_regex_allows(sample):
    assert not LAYER_CODE.search(sample), sample


@pytest.mark.parametrize("path", _published_docs(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_layer_codes_in_published_docs(path):
    assert LAYER_CODE.findall(path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("path", reference_pages(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_mermaid_names_capabilities_not_products(path):
    for fence in mermaid_fences(body(path)):
        assert PRODUCT_TERMS.findall(fence) == [], path.name
        assert LAYER_CODE.findall(fence) == [], path.name


def test_product_terms_regex():
    assert PRODUCT_TERMS.search("Red Hat AI Inference (vLLM)")
    assert PRODUCT_TERMS.search("runs on AAP")
    assert not PRODUCT_TERMS.search("AI Gateway routes to model endpoint inferencing")
    assert not PRODUCT_TERMS.search("GitOps promotes a canary")
