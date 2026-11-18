"""Far-edge site roles in the catalog: the F3 site option and the site entries.

The CPU-only far-edge setup sizes the roles a use case places at the far edge.
These tests pin the first such roles: an optional Classification site option
on alarm-triage-adaptation (regional triage stays the default), and site pages
that run a CPU role at the cell site. Site text stays vendor-neutral and
carries no performance numbers, and every claim it adds is sourced.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.bplint.slug import github_slug
from tools.tests.conftest import REPO_ROOT
from tools.tests.test_platform_pages import section_text
from tools.tests.test_reference_pages import body, front_matter

CATALOG = REPO_ROOT / "catalog"
F3 = CATALOG / "network-operations" / "alarm-triage-adaptation" / "README.md"
PLACEMENT = REPO_ROOT / "architecture" / "placement.md"
VDU_LINK = "../../../architecture/placement.md#servers-shared-with-a-vdu"

# New pages that place a CPU role at the far edge. A row may land before its
# page; the page tests skip until it exists.
SITE_PAGES = [
    "network-operations/site-log-reduction",
]

RHAII_NOTES = (
    "https://docs.redhat.com/en/documentation/red_hat_ai_inference/3.5/html/release_notes/"
    "rhaii-350-ga-release-notes_release-notes"
)
VLLM_POOLING = "https://docs.vllm.ai/en/latest/models/pooling_models/"
RAN_DU = (
    "https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/"
    "scalability_and_performance/telco-ran-du-ref-design-specs"
)

VENDOR_NAMES = re.compile(r"(?i)AT&T|Ericsson|OCTO|Granite Rapids|Xeon|\bIntel\b")
PERFORMANCE = re.compile(r"(?i)tok/s|tokens per second|\b\d+\s?ms\b|\d+x faster")
URL_IN_LINK = re.compile(r"\]\([^)]*\)")

# F3's adaptation and sandbox before the site option landed: the site option
# changes neither.
F3_ADAPTATION = {
    "rung": "lora-if-gap",
    "expertise": ["taxonomy", "golden-set", "gate-labels", "tool-contracts", "corpus"],
    "bring": [
        {"item": "Vendor manuals and runbooks with usage rights", "domains": ["ran", "transport-ip"], "mechanism": "rag-corpus"},
        {"item": "Alarm taxonomy and SME-labelled replayed tapes", "domains": ["ran", "transport-ip"], "mechanism": "classification-labels"},
        {"item": "Read-only alarm and device tool contracts", "domains": ["ran", "transport-ip"], "mechanism": "tool-contract"},
        {"item": "Triage skill and capability manifests", "domains": ["ran", "transport-ip"], "mechanism": "skill-manifest"},
        {"item": "Ceilings and approver roles for notes and fixes", "domains": ["ran", "transport-ip"], "mechanism": "gate-policy"},
        {"item": "Vocabulary and report examples, only after a measured gap", "domains": ["ran", "transport-ip"], "mechanism": "lora-data"},
    ],
}
F3_SANDBOX = {"fit": "none", "why": "Reads alarms and runbooks through read tools; the agent runs no code"}


# ---------- helpers ----------


def site_option_paragraph() -> str:
    """The F3 body paragraph that names the far-edge site option."""
    paras = [p for p in re.split(r"\n\s*\n", body(F3)) if p.strip().startswith("Site option:")]
    assert len(paras) == 1, f"expected one 'Site option:' paragraph, found {len(paras)}"
    return re.sub(r"\s+", " ", paras[0].strip())


def prose_words(text: str) -> int:
    return len(URL_IN_LINK.sub("]", text).split())


def site_texts() -> list[tuple[str, str]]:
    """(label, text) for the F3 site text and each landed site page."""
    fm = front_matter(F3) or {}
    paras = [p for p in re.split(r"\n\s*\n", body(F3)) if p.strip().startswith("Site option:")]
    out = [
        ("F3 site option", " ".join(paras)),
        ("F3 far-edge note", fm["placement"]["far-edge"]["note"]),
    ]
    for key in SITE_PAGES:
        path = CATALOG / key / "README.md"
        if path.is_file():
            out.append((key, path.read_text(encoding="utf-8")))
    return out


def site_page(key: str) -> Path:
    path = CATALOG / key / "README.md"
    if not path.is_file():
        pytest.skip(f"{key} has not landed yet")
    return path


def placement_h3_slugs() -> set[str]:
    return {github_slug(m) for m in re.findall(r"^### (.+?)\s*$", PLACEMENT.read_text(encoding="utf-8"), re.M)}


# ---------- F3 site option ----------


def test_f3_far_edge_option():
    fm = front_matter(F3) or {}
    placement = fm["placement"]
    assert placement["far-edge"]["runs"] == ["classification"]
    assert placement["far-edge"]["note"].startswith("Optional")
    assert len(placement["far-edge"]["note"].split()) <= 15
    assert "far-edge" in fm["placement_tier"]
    assert placement["regional"]["runs"] == [
        "llm-large", "classification", "safety", "decision", "embedding", "reranker",
    ]
    assert placement["core"]["runs"] == ["llm-large", "classification"]


def test_f3_site_option_text():
    para = site_option_paragraph()
    assert "CPU" in para
    assert "structured incidents" in para
    assert re.search(r"(?i)regional triage stays the default", para)
    assert VDU_LINK in para
    glance = section_text(F3, "At a glance")
    row = next(line for line in glance.splitlines() if line.startswith("| Placement tier"))
    assert "by default" in row and "far edge" in row


def test_f3_site_option_sourced():
    sources = section_text(F3, "Sources")
    for url in (RHAII_NOTES, VLLM_POOLING, RAN_DU):
        assert f"({url})" in sources, f"F3 Sources has no row linking {url}"
    slugs = placement_h3_slugs()
    for anchor in re.findall(r"architecture/placement\.md#([a-z0-9-]+)", body(F3)):
        assert anchor in slugs, f"placement.md has no H3 for #{anchor}"


def test_f3_site_option_short():
    assert prose_words(site_option_paragraph()) <= 55


def test_f3_bring_and_sandbox_unchanged():
    fm = front_matter(F3) or {}
    assert fm["adaptation"] == F3_ADAPTATION
    assert fm["sandbox"] == F3_SANDBOX


# ---------- every site text ----------


@pytest.mark.parametrize("label,text", site_texts(), ids=lambda v: v if len(v) < 60 else "text")
def test_site_pages_vendor_neutral(label, text):
    assert VENDOR_NAMES.findall(URL_IN_LINK.sub("]", text)) == [], label


@pytest.mark.parametrize("label,text", site_texts(), ids=lambda v: v if len(v) < 60 else "text")
def test_no_performance_numbers_on_site_pages(label, text):
    assert PERFORMANCE.findall(URL_IN_LINK.sub("]", text)) == [], label
