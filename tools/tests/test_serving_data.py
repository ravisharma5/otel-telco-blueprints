"""Serving data files: schemas, drift against the serving page, setups, and prose guards.

data/serving/*.yaml are the source of truth for the serving page's sizing table
and key flags fence. tools/site/render_serving.py writes them between generated
markers; these tests keep the page and the data in step and keep the data free
of support labels, planning ids, and product release numbers.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from tools.guards.patterns import PLANNING_ID_RE
from tools.site import render_serving
from tools.tests.conftest import REPO_ROOT
from tools.tests.test_platform_pages import SERVING, table_with_header
from tools.tests.test_use_case_pages import pb04_flag_blocks

DATA_DIR = REPO_ROOT / "data/serving"
SCHEMAS = REPO_ROOT / "schemas"
DATA_SCHEMAS = {
    "slot-variants.yaml": "serving-slot-variants.schema.json",
    "flags.yaml": "serving-flags.schema.json",
    "setups.yaml": "serving-setups.schema.json",
}
SIZING_HEADER = ["Slot", "Precision", "Weights", "Hardware class"]
MARKERS = ("sizing", "flags-per-slot")
EXPECTED_SETUPS = {
    "regional-48": "Regional site, one 48 GB GPU (Ada or newer)",
    "regional-96": "Regional site, one 96 GB GPU",
    "regional-2x48": "Regional site, two 48 GB GPUs",
    "core-nvidia": "Core pool, NVIDIA H200 or B200",
    "core-amd": "Core pool, AMD MI300X",
}
OTEL_CARD_PREFIX = "https://huggingface.co/farbodtavakkoli/"
RED_HAT_BUILD_PREFIX = "https://huggingface.co/RedHatAI/"
IMAGE_PREFIX = "registry.redhat.io/rhaii/"
STATUS_LABEL = re.compile(r"\b(GA|TP|DP)\b")
STATUS_WORDS = re.compile(
    r"Technology Preview|Developer Preview|production-ready|\bvalidated\b", re.I
)
PRODUCT_RELEASE = re.compile(r"(Red Hat [A-Za-z ]+|OpenShift AI|llm-d) \d+\.\d+")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
RANGE = re.compile(r"(\d+(?:\.\d+)?) to (\d+(?:\.\d+)?)")


# ---------- helpers ----------


def load(name: str, data_dir: Path = DATA_DIR):
    return yaml.safe_load((data_dir / name).read_text(encoding="utf-8"))


def validator(schema_name: str) -> Draft202012Validator:
    reg = Registry()
    for p in SCHEMAS.glob("*.schema.json"):
        s = json.loads(p.read_text(encoding="utf-8"))
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    return Draft202012Validator(
        schema, registry=reg, format_checker=Draft202012Validator.FORMAT_CHECKER
    )


def strings(node):
    """Every string value in a loaded YAML tree."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)


def fmt_number(x) -> str:
    return f"{x:g}"


def figure_in_text(figure: float, text: str) -> bool:
    """True when text names figure, or states a range "A to B" that holds it."""
    if fmt_number(figure) in NUMBER.findall(text):
        return True
    return any(float(a) <= figure <= float(b) for a, b in RANGE.findall(text))


# ---------- schemas ----------


@pytest.mark.parametrize("schema_name", sorted(DATA_SCHEMAS.values()))
def test_serving_schema_is_valid(schema_name):
    Draft202012Validator.check_schema(json.loads((SCHEMAS / schema_name).read_text()))


@pytest.mark.parametrize(("data_name", "schema_name"), sorted(DATA_SCHEMAS.items()))
def test_serving_schemas_valid(data_name, schema_name):
    errors = [e.message for e in validator(schema_name).iter_errors(load(data_name))]
    assert errors == []


def _objects(node, path=()):
    """(path, dict) for every mapping in a loaded YAML tree."""
    if isinstance(node, dict):
        yield path, node
        for k, v in node.items():
            yield from _objects(v, (*path, k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _objects(v, (*path, i))


@pytest.mark.parametrize(("data_name", "schema_name"), sorted(DATA_SCHEMAS.items()))
def test_serving_schema_rejects_unknown_keys(data_name, schema_name):
    data = load(data_name)
    v = validator(schema_name)
    for path, _ in _objects(data):
        bad = copy.deepcopy(data)
        target = bad
        for step in path:
            target = target[step]
        target["unexpected_key"] = "x"
        assert not v.is_valid(bad), f"extra key accepted at {path}"


# ---------- page drift ----------


def test_generated_markers_present():
    text = SERVING.read_text(encoding="utf-8")
    positions = []
    for name in MARKERS:
        for edge in ("start", "end"):
            marker = f"<!-- generated:{name} {edge} -->"
            assert text.count(marker) == 1, marker
            assert re.search(rf"^{re.escape(marker)}$", text, re.M), f"{marker} not on its own line"
            positions.append(text.index(marker))
    assert positions == sorted(positions)


def test_serving_page_matches_data():
    text = SERVING.read_text(encoding="utf-8")
    assert render_serving.render(text) == text, "run `make render`"


def test_render_check_bites(tmp_path):
    data_dir = tmp_path / "serving"
    shutil.copytree(DATA_DIR, data_dir)
    variants = load("slot-variants.yaml", data_dir)
    variants["sizing_table"][0]["weights"] = "about 99.9 GB"
    (data_dir / "slot-variants.yaml").write_text(yaml.safe_dump(variants), encoding="utf-8")
    text = SERVING.read_text(encoding="utf-8")
    assert render_serving.render(text, data_dir=data_dir) != text


def test_render_rejects_missing_marker():
    text = SERVING.read_text(encoding="utf-8").replace("<!-- generated:sizing end -->\n", "")
    with pytest.raises(SystemExit, match="sizing"):
        render_serving.render(text)


def test_render_rejects_duplicate_marker():
    text = SERVING.read_text(encoding="utf-8")
    marker = "<!-- generated:flags-per-slot start -->\n"
    with pytest.raises(SystemExit, match="flags-per-slot"):
        render_serving.render(text.replace(marker, marker + marker))


def test_sizing_table_on_page_equals_data_rows():
    table = table_with_header(SERVING, "Reference design", SIZING_HEADER)
    assert table[0] == SIZING_HEADER
    rows = [
        [r["slot"], r["precision"], r["weights"], r["hardware_class"]]
        for r in load("slot-variants.yaml")["sizing_table"]
    ]
    assert table[1:] == rows


def test_flag_blocks_on_page_equal_data_blocks():
    want = {
        f"# {b['comment']}": render_serving.flag_lines(b) for b in load("flags.yaml")["per_slot"]
    }
    assert pb04_flag_blocks() == want


# ---------- data content ----------


def test_setups_profiles():
    data = load("setups.yaml")
    setups = {s["id"]: s for s in data["setups"]}
    assert [s["id"] for s in data["setups"]] == list(EXPECTED_SETUPS)
    assert {k: s["label"] for k, s in setups.items()} == EXPECTED_SETUPS
    two = setups["regional-2x48"]["accelerators"]
    assert two["count_per_node"] == 2 and two["memory_per_gpu_gb"] == 48
    for s in setups.values():
        assert s["engine_image"].startswith(IMAGE_PREFIX), s["id"]
        assert ":" not in s["engine_image"].removeprefix(IMAGE_PREFIX), s["id"]
    assert {k for k, s in setups.items() if s["ampere_note"]} == {"regional-48", "regional-2x48"}
    assert data["default"] == {"setup": "regional-96", "batch": "yes"}
    assert data["default"]["setup"] in setups
    bands = data["fit_bands"]
    assert (bands["fits_max_pct"], bands["tight_max_pct"]) == (60, 80)
    assert bands["why"].strip()


def test_variant_links():
    for v in load("slot-variants.yaml")["variants"]:
        if v["checkpoint"]:
            assert v["checkpoint"].startswith("OTel-"), v["id"]
            assert v["model_card"] == OTEL_CARD_PREFIX + v["checkpoint"], v["id"]
        if v["red_hat_build"]:
            assert v["red_hat_build"].startswith(RED_HAT_BUILD_PREFIX), v["id"]


def test_sizing_rows_match_variants():
    data = load("slot-variants.yaml")
    variants = {v["id"]: v for v in data["variants"]}
    assert len(variants) == len(data["variants"]), "duplicate variant id"
    used = set()
    for row in data["sizing_table"]:
        for vid in row["variants"]:
            assert vid in variants, f"{row['slot']}: unknown variant {vid}"
            assert figure_in_text(variants[vid]["weights_gb"], row["weights"]), (row["slot"], vid)
            used.add(vid)
    assert used == set(variants), f"variants in no sizing row: {set(variants) - used}"


def test_flag_blocks_have_why():
    for block in load("flags.yaml")["per_slot"]:
        for line in block["lines"]:
            for arg in line["args"]:
                assert arg["why"].strip(), (block["id"], arg["flag"])


@pytest.mark.parametrize("data_name", sorted(DATA_SCHEMAS))
def test_no_status_or_release_in_data(data_name):
    for s in strings(load(data_name)):
        assert not STATUS_LABEL.search(s), s
        assert not STATUS_WORDS.search(s), s
        assert not PLANNING_ID_RE.search(s), s
        assert not PRODUCT_RELEASE.search(s), s
