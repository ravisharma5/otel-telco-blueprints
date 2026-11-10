"""Architecture diagrams: safety checks for the overview diagram files.

The overview diagram is authored with archify. Its HTML source and input JSON
are committed next to the page but never published, and the exported SVG is
the only file the site serves.
"""

from __future__ import annotations

import json
import re

import pytest

from tools.site import hooks
from tools.tests.conftest import REPO_ROOT
from tools.tests.test_reference_pages import LAYER_CODE, PRODUCT_TERMS

DIAGRAMS = REPO_ROOT / "architecture/diagrams"
SOURCES = [DIAGRAMS / "overview.html", DIAGRAMS / "candidate.json"]
# Local home folders on macOS and Linux. The character classes keep the
# literal paths out of this file, so it passes the public-tree term checks.
LOCAL_PATH_RE = re.compile(r"/(?:[U]sers|[h]ome)/")


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_diagram_sources_have_no_local_paths(path):
    text = path.read_text(encoding="utf-8")
    assert not LOCAL_PATH_RE.search(text)


def test_diagram_sources_not_published():
    assert ".html" not in hooks.SUFFIXES
    assert ".json" not in hooks.SUFFIXES


# The viewer embeds fonts and images as base64. Long base64 runs can contain
# short letter groups by chance, so they are removed before word checks.
BASE64_RUN = re.compile(r"[A-Za-z0-9+/=]{100,}")


def _diagram_text(path):
    return BASE64_RUN.sub("", path.read_text(encoding="utf-8"))


def _candidate_strings(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from _candidate_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _candidate_strings(value)
    elif isinstance(node, str):
        yield node


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_diagram_sources_have_no_layer_codes(path):
    assert LAYER_CODE.findall(_diagram_text(path)) == []


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_diagram_sources_name_no_products(path):
    assert PRODUCT_TERMS.findall(_diagram_text(path)) == []


def test_diagram_candidate_names_capabilities():
    candidate = json.loads((DIAGRAMS / "candidate.json").read_text(encoding="utf-8"))
    labels = {c["label"] for c in candidate["components"]}
    for name in ("AI Gateway", "MCP Gateway", "Guardrails", "Agent runtime", "Decision gate"):
        assert name in labels, name
    assert {"Operations user", "Network event"} <= labels
    assert "Operator" not in labels
    into_guardrails = {c["from"] for c in candidate["connections"] if c["to"] == "guardrails"}
    entries = {c["id"] for c in candidate["components"] if c["label"] in ("Operations user", "Network event")}
    assert entries <= into_guardrails
    boundaries = " ".join(b["label"] for b in candidate["boundaries"])
    assert "Model endpoint inferencing" in boundaries
    for plane in ("Control plane", "Data and execution plane", "Lifecycle plane"):
        assert plane in boundaries, plane
    texts = list(_candidate_strings(candidate))
    for tier in ("Far edge", "Regional", "Core"):
        assert tier in texts, tier


# The viewer draws the sublabel at mid-height + 14 and a tag 8 above the box
# bottom. Below this height the tag line overlaps the sublabel.
TAGGED_MIN_HEIGHT = 64


def test_tagged_boxes_tall_enough_for_three_lines():
    candidate = json.loads((DIAGRAMS / "candidate.json").read_text(encoding="utf-8"))
    short = [
        c["id"]
        for c in candidate["components"]
        if c.get("tag") and c["size"][1] < TAGGED_MIN_HEIGHT
    ]
    assert short == []
