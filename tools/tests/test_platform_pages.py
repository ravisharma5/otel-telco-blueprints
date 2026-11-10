"""Platform blueprint pages: shared template checks for every landed page.

Each check here runs on every platform/<slug>/README.md. Per-page content
checks for a single blueprint go in their own test module and import the
helpers below. With no platform pages yet, the parametrized checks collect
no cases and the expected-pages guard compares two empty maps.
"""

from __future__ import annotations

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
EXPECTED_PLATFORM_PAGES: dict[str, str] = {"serving-routing-placement": "PB-04"}

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
