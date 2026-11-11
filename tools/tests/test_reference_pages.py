"""Reference pages: per-page content checks and the recipe wording rule.

Reference pages, blueprint pages, and the templates they come from are all
recipes. They say how to build a design, not how far it has been tested, so
they carry no validation-status wording and no readiness levels. The ban here
covers reference pages, blueprint pages, the three templates, and the valid
fixtures. Vale's Blueprints.ValidationStatus rule covers the words across all
doc dirs; readiness codes live here because the crosswalk's E1-E7
extension-row cells need the cell exemption.

The helpers below are shared: per-page tests for each reference page go in
this module and call them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from markdown_it import MarkdownIt

from tools.bplint.checks.links import doc_slugs
from tools.bplint.loader import load_yaml, split_front_matter
from tools.bplint.markdown import parse_doc
from tools.tests.conftest import REPO_ROOT

TEMPLATE = REPO_ROOT / "templates/reference-page.md"
TEMPLATES = [
    TEMPLATE,
    REPO_ROOT / "templates/platform-blueprint.md",
    REPO_ROOT / "templates/use-case-blueprint.md",
]
VALID_FIXTURES = REPO_ROOT / "tools/tests/fixtures/valid"
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
# Front matter `extension_rows:` lists crosswalk extension-row ids such as E2.
EXEMPT_FM_LINE = re.compile(r"^extension_rows:")
FRONT_MATTER = re.compile(r"\A---\n(.*?)^---[ \t]*$", re.M | re.S)
MERMAID_KEYWORDS = ("flowchart", "graph", "sequenceDiagram")


# ---------- helpers ----------


def _md():
    return MarkdownIt("commonmark").enable("table")


# Every page reference_globs must find. Page-driven tests take their cases
# from reference_pages(), so a renamed glob or a lost page fails here instead
# of quietly collecting zero cases.
EXPECTED_REFERENCE_PAGES = {
    "framework/index.md",
    "architecture/index.md",
    "architecture/decision-gate.md",
    "architecture/adaptation-ladder.md",
    "architecture/placement.md",
    "architecture/crosswalk.md",
}


def reference_pages() -> list[Path]:
    """Every file matched by reference_globs, whatever its front matter says.

    A page that drops `type: reference` stays in the list, so the type check
    in the helper test fails rather than the page vanishing from every test.
    Raises when discovery finds nothing, so parametrized tests cannot pass by
    collecting zero cases.
    """
    out = []
    for pattern in load_yaml(CONFIG).get("reference_globs") or []:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_file() and path not in out:
                out.append(path)
    if not out:
        raise AssertionError("reference_globs in the bplint config matched no pages")
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


def _drop_exempt_front_matter_lines(text: str) -> str:
    m = FRONT_MATTER.match(text)
    if not m:
        return text
    kept = "".join(
        ln for ln in m.group(1).splitlines(keepends=True) if not EXEMPT_FM_LINE.match(ln)
    )
    return text[: m.start(1)] + kept + text[m.end(1) :]


def wording_hits(text: str) -> list[str]:
    """Validation-status wording and readiness levels outside code fences.

    Table cells that hold only an extension-row id (E1-E7) are allowed, and so
    is a whole front matter line that starts with `extension_rows:`.
    """
    text = _drop_exempt_front_matter_lines(text)
    text = FENCE.sub("", text)
    text = "\n".join(_drop_exempt_cells(line) for line in text.splitlines())
    return [m.group(0) for m in WORDING.finditer(text)]


def blueprint_pages() -> list[Path]:
    """Every file matched by blueprint_globs (none until the first blueprint lands)."""
    out = []
    for pattern in load_yaml(CONFIG).get("blueprint_globs") or []:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_file() and path not in out:
                out.append(path)
    return out


def valid_fixtures() -> list[Path]:
    return sorted(p for p in VALID_FIXTURES.glob("*/README.md") if p.is_file())


def _scanned_files() -> list[Path]:
    out: list[Path] = []
    for path in [*reference_pages(), *TEMPLATES, *valid_fixtures(), *blueprint_pages()]:
        if path not in out:
            out.append(path)
    return out


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


def test_wording_exempt_extension_rows_front_matter_line():
    text = '---\nid: "PB-04"\nextension_rows: ["E2"]\n---\n\n# Title\n'
    assert wording_hits(text) == []
    assert wording_hits(text + "\nThe E2 row is optional.\n")
    assert wording_hits('# Title\n\nextension_rows: ["E2"]\n')
    assert wording_hits('---\nnote: "E2"\n---\n')


@pytest.mark.parametrize(
    "sample",
    ["This step is unverified.", "Method defined, not yet run.", "Rated M2 / E1."],
)
def test_wording_flags_blueprint_prose(tmp_path, sample):
    page = tmp_path / "README.md"
    page.write_text(f'---\ntype: "use-case"\n---\n\n# Title\n\n{sample}\n', encoding="utf-8")
    assert wording_hits(page.read_text(encoding="utf-8")), sample


def test_scanned_set_covers_templates_fixtures_and_blueprints():
    scanned = set(_scanned_files())
    assert set(TEMPLATES) <= scanned
    fixtures = valid_fixtures()
    assert len(fixtures) >= 3 and set(fixtures) <= scanned
    for name in ("platform", "use-case", "catalog-entry"):
        assert VALID_FIXTURES / name / "README.md" in scanned
    assert set(blueprint_pages()) <= scanned


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
    pages = reference_pages()
    assert TEMPLATE not in pages
    assert {p.relative_to(REPO_ROOT).as_posix() for p in pages} == EXPECTED_REFERENCE_PAGES
    for path in pages:
        assert (front_matter(path) or {}).get("type") == "reference", path.name


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
# A reference-style link definition: "[label]: target" at the start of a line.
REF_DEF = re.compile(r"^ {0,3}\[([^\]]+)\]:[ \t]*(\S+)", re.M)
# A relative target inside the platform/ folder, with or without a trailing slash.
PLATFORM_TARGET = re.compile(r"(^|/)platform(/|$|#)")
PB_IN_TEXT = re.compile(r"\bPB-[0-9]{2}\b")


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


def test_readiness_every_row_links_a_platform_page():
    """Each of the ten questions links the platform blueprint that answers it."""
    header, rows = _readiness_rows()
    for row in rows:
        targets = [target for _label, target in MD_LINK.findall(_cell(header, row, "Answered by"))]
        assert any("platform/" in target for target in targets), row[0]


def test_readiness_serving_row_uses_hardware_class():
    header, rows = _readiness_rows()
    ready = _cell(header, rows[3], "What ready means")
    assert "hardware class" in ready
    assert "named hardware" not in ready


def _md_slugs(path: Path) -> set[str]:
    return doc_slugs(parse_doc(path, path.read_text(encoding="utf-8")))


def platform_link_problems(text: str, base: Path) -> list[str]:
    """Broken relative links into platform/ in text, resolved from folder base.

    External URLs are skipped. Inline and reference-style links count, with or
    without a trailing slash. The target page must exist, a #fragment must
    match one of its headings, and link text naming a PB id must match the
    target page's id.
    """
    links = MD_LINK.findall(text) + REF_DEF.findall(text)
    out = []
    for label, target in links:
        target = target.strip().split(" ", 1)[0].strip("<>")
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or not PLATFORM_TARGET.search(target):
            continue
        path_part, _, fragment = target.partition("#")
        page = (base / path_part).resolve()
        if page.is_dir():
            page = page / "README.md"
        if not page.is_file():
            out.append(f"{target}: no such page")
            continue
        if fragment and fragment not in _md_slugs(page):
            out.append(f"{target}: no heading for #{fragment}")
        named = PB_IN_TEXT.search(label)
        if named and named.group(0) != (front_matter(page) or {}).get("id"):
            out.append(f"{target}: link text {label!r} names another blueprint")
    return out


@pytest.mark.parametrize(
    ("link", "ok"),
    [
        ("[PB-04](../platform/serving-routing-placement/README.md)", True),
        ("[PB-04](../platform/serving-routing-placement/README.md#components)", True),
        ("[PB-04](../platform/serving-routing-placement/README.md#no-such-anchor)", False),
        ("[PB-05](../platform/serving-routing-placement/README.md)", False),
        ("[x](../platform/no-such-page/README.md)", False),
        ("[x](../platform/no-such-page)", False),
        ("[PB-04][s]\n\n[s]: ../platform/serving-routing-placement/README.md#nope", False),
        ("[docs](https://docs.example.com/openshift_container_platform/4/x.html)", True),
    ],
)
def test_platform_link_rule_cases(link, ok):
    problems = platform_link_problems(link, READINESS.parent)
    assert (problems == []) is ok, problems


def test_readiness_platform_links_resolve():
    """Links into platform/ are allowed only once the target page exists."""
    assert platform_link_problems(body(READINESS), READINESS.parent) == []


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
# codes are internal shorthand and never reach readers. The NVIDIA L4 GPU is
# not a layer code: "NVIDIA L4", a count such as "1x L4", and "L4 GPU" pass.
LAYER_CODE = re.compile(
    r"(?<!NVIDIA )(?<![0-9]x )\bL(?:10|9[abc]|[0-9])\b(?!\s+GPUs?\b)"
)
# Diagrams name capabilities, never products. Page tables still name the
# product used for each role, so only diagrams are checked.
PRODUCT_TERMS = re.compile(
    r"OpenShift|Red Hat|\bRHEL\b|vLLM|KServe|llm-d|Models-as-a-Service|\bMaaS\b"
    r"|Argo CD|Keycloak|SPIFFE|SPIRE|NeMo|EvalHub|Kuadrant|Ansible|\bAAP\b"
    r"|MLflow|Perses|\bACM\b|Prometheus|OpenTelemetry|Podman|SDG Hub|Training Hub"
    r"|Automation Orchestrator|Connectivity Link|LangGraph|Device Edge"
    r"|Data Science Pipelines|Garak|Inspect AI|Kueue|Istio|Envoy|\bQuay\b|Kubeflow"
    r"|Unsloth|KubeRay|MicroShift|ModelCar|LLM Compressor|Model Optimization Toolkit"
    r"|Workload Identity Manager|TrustyAI"
    r"|\bTempo\b|OpenShell|\bKata\b|Sigstore|\bcosign\b|External Secrets"
    r"|Trusted Artifact Signer|Hugging Face"
)
TEMPLATES = sorted((REPO_ROOT / "templates").glob("*.md"))


def _published_docs() -> list[Path]:
    return [*reference_pages(), *TEMPLATES, *blueprint_pages()]


@pytest.mark.parametrize(
    "sample", ["L0 to L7", "layer L9a", "| L10 |", "L9c observability", "the L4 layer", "L3 --> L4"]
)
def test_layer_code_regex_catches(sample):
    assert LAYER_CODE.search(sample), sample


@pytest.mark.parametrize(
    "sample",
    [
        "LLM slot",
        "L40S GPUs",
        "Layer 1",
        "PB-10",
        "OTel-LLM-12B",
        "NVIDIA L4",
        "1x L4 or 1x L40S",
        "2x L4",
        "an L4 GPU",
        "L4 GPUs",
    ],
)
def test_layer_code_regex_allows(sample):
    assert not LAYER_CODE.search(sample), sample


@pytest.mark.parametrize("path", _published_docs(), ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_layer_codes_in_published_docs(path):
    assert LAYER_CODE.findall(path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "path",
    [*reference_pages(), *blueprint_pages()],
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_mermaid_names_capabilities_not_products(path):
    for fence in mermaid_fences(body(path)):
        assert PRODUCT_TERMS.findall(fence) == [], path.name
        assert LAYER_CODE.findall(fence) == [], path.name


def test_product_terms_regex():
    assert PRODUCT_TERMS.search("Red Hat AI Inference (vLLM)")
    assert PRODUCT_TERMS.search("runs on AAP")
    assert not PRODUCT_TERMS.search("AI Gateway routes to model endpoint inferencing")
    assert not PRODUCT_TERMS.search("GitOps promotes a canary")
    for name in ("Garak scan", "Inspect AI", "Red Hat build of Kueue", "Istio", "Envoy",
                 "Quay", "Kubeflow", "Unsloth", "MicroShift", "ModelCar images"):
        assert PRODUCT_TERMS.search(name), name
    assert not PRODUCT_TERMS.search("Promotion pipeline writes to the model registry")


# ---------- placement tiers ----------

PLACEMENT = REPO_ROOT / "architecture/placement.md"
TIERS = ["Far edge", "Regional", "Core"]
LATENCY_RANGES = [
    "milliseconds per decision",
    "sub-second closed loop",
    "seconds (interactive) to minutes-hours (batch)",
]
MS_NUMBER = re.compile(r"\d+\s*ms\b")


def test_placement_is_reference():
    fm = front_matter(PLACEMENT)
    assert fm["type"] == "reference"
    assert "PB-04" in fm["platform_blueprints"]


def test_placement_tiers():
    table = _find_table(PLACEMENT, ["Tier", "OTel slots placed here", "Latency range"])
    header = table[0]
    assert any(cell.startswith("Platform") for cell in header), header
    rows = table[1:]
    assert [row[0] for row in rows] == TIERS
    latency = header.index("Latency range")
    assert [row[latency] for row in rows] == LATENCY_RANGES
    slots = header.index("OTel slots placed here")
    for row in rows:
        assert row[slots].strip(), row


def test_placement_no_ms_numbers():
    assert MS_NUMBER.findall(PLACEMENT.read_text(encoding="utf-8")) == []


def test_placement_all_slots():
    text = body(PLACEMENT)
    for slot in ("LLM", "Embedding", "Reranker", "Safety", "Decision", "Classification"):
        assert slot in text, slot


# ---------- crosswalk to the agent blueprint table ----------

CROSSWALK = REPO_ROOT / "architecture/crosswalk.md"
ARTICLE = (
    "https://developers.redhat.com/articles/2026/07/20/architect-open-blueprint-cloud-native-ai-agents"
)
AGENT_SCHOOL = "https://github.com/open-experiments/agent-school"
TABLE1 = [
    "Agent blueprint / GitOps",
    "Agent orchestration",
    "Sandbox runtime (supervisor)",
    "Harness",
    "Agentic loop runtime (Agent-as-a-Service)",
    "Model",
    "AI gateway (MaaS)",
    "Semantic routing",
    "Inference routing",
    "Model workers",
    "Skills",
    "Workload identity",
    "Tool governance",
]
EXTENSIONS = [
    "knowledge",
    "guardrails",
    "decision gate",
    "action",
    "evaluation",
    "adaptation",
    "placement",
]


def _first_column_table(path, firsts):
    for table in _design_tables(path):
        if [row[0] for row in table[1:]] == firsts:
            return table
    raise AssertionError(f"no table in The design with first cells {firsts}")


def test_crosswalk_is_reference_draft():
    fm = front_matter(CROSSWALK)
    assert fm["type"] == "reference"
    assert fm["doc_status"] == "draft"
    assert {"PB-04", "PB-05", "PB-06", "PB-07", "PB-08"} <= set(fm["platform_blueprints"])


def test_crosswalk_table1_rows():
    table = _first_column_table(CROSSWALK, [str(i) for i in range(1, 14)])
    assert [row[1] for row in table[1:]] == TABLE1


def test_crosswalk_extension_rows():
    table = _first_column_table(CROSSWALK, [f"E{i}" for i in range(1, 8)])
    for row, name in zip(table[1:], EXTENSIONS, strict=True):
        assert name in row[1].lower(), (name, row)


def test_crosswalk_links_and_review_note():
    text = body(CROSSWALK)
    targets = [target for _, target in MD_LINK.findall(text)]
    assert ARTICLE in targets
    assert AGENT_SCHOOL_ROADMAP in targets
    assert AGENT_SCHOOL in targets
    assert "pending review by the agent-school maintainers" in text.lower()


def test_crosswalk_numbering_source():
    text = " ".join(body(CROSSWALK).split()).lower()
    assert re.search(r"number[^.]{0,120}roadmap|roadmap[^.]{0,120}number", text)


def test_crosswalk_no_extension_ids_in_prose():
    text = FENCE.sub("", body(CROSSWALK))
    prose = [ln for ln in text.splitlines() if not ln.lstrip().startswith("|")]
    assert re.findall(r"\bE[1-7]\b", "\n".join(prose)) == []


# ---------- final status after the clarity pass ----------

ISO_QUOTED = re.compile(r'^clarity_reviewed: "\d{4}-\d{2}-\d{2}"$', re.M)
DONE_PAGES = [READINESS, OVERVIEW, GATE, LADDER, PLACEMENT]


@pytest.mark.parametrize(
    "path", [*DONE_PAGES, CROSSWALK], ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_reference_status(path):
    text = path.read_text(encoding="utf-8")
    assert ISO_QUOTED.search(text), "clarity_reviewed must be a quoted ISO date"
    expected = "draft" if path == CROSSWALK else "done"
    assert front_matter(path)["doc_status"] == expected
