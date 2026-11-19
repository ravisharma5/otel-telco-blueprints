"""Far-edge site roles in the catalog: the alarm-triage site option and the site entries.

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
ALARM_TRIAGE = CATALOG / "network-operations" / "alarm-triage-adaptation" / "README.md"
PLACEMENT = REPO_ROOT / "architecture" / "placement.md"
VDU_LINK = "../../../architecture/placement.md#servers-shared-with-a-vdu"

# New pages that place a CPU role at the far edge. A row may land before its
# page; the page tests skip until it exists.
SITE_PAGES = [
    "network-operations/site-log-reduction",
    "agentic-operations/site-change-risk-gate",
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

# Alarm triage's adaptation and sandbox before the site option landed: the site option
# changes neither.
ALARM_TRIAGE_ADAPTATION = {
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
ALARM_TRIAGE_SANDBOX = {"fit": "none", "why": "Reads alarms and runbooks through read tools; the agent runs no code"}


# ---------- helpers ----------


def site_option_paragraph() -> str:
    """The alarm-triage body paragraph that names the far-edge site option."""
    paras = [p for p in re.split(r"\n\s*\n", body(ALARM_TRIAGE)) if p.strip().startswith("Site option:")]
    assert len(paras) == 1, f"expected one 'Site option:' paragraph, found {len(paras)}"
    return re.sub(r"\s+", " ", paras[0].strip())


def prose_words(text: str) -> int:
    return len(URL_IN_LINK.sub("]", text).split())


def site_texts() -> list[tuple[str, str]]:
    """(label, text) for the alarm-triage site text and each landed site page."""
    fm = front_matter(ALARM_TRIAGE) or {}
    paras = [p for p in re.split(r"\n\s*\n", body(ALARM_TRIAGE)) if p.strip().startswith("Site option:")]
    out = [
        ("alarm-triage site option", " ".join(paras)),
        ("alarm-triage far-edge note", fm["placement"]["far-edge"]["note"]),
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


# ---------- alarm-triage site option ----------


def test_alarm_triage_far_edge_option():
    fm = front_matter(ALARM_TRIAGE) or {}
    placement = fm["placement"]
    assert placement["far-edge"]["runs"] == ["classification"]
    assert placement["far-edge"]["note"].startswith("Optional")
    assert len(placement["far-edge"]["note"].split()) <= 15
    assert "far-edge" in fm["placement_tier"]
    assert placement["regional"]["runs"] == [
        "llm-large", "classification", "safety", "decision", "embedding", "reranker",
    ]
    assert placement["core"]["runs"] == ["llm-large", "classification"]


def test_alarm_triage_site_option_text():
    para = site_option_paragraph()
    assert "CPU" in para
    assert "structured incidents" in para
    assert re.search(r"(?i)regional triage stays the default", para)
    assert VDU_LINK in para
    glance = section_text(ALARM_TRIAGE, "At a glance")
    row = next(line for line in glance.splitlines() if line.startswith("| Placement tier"))
    assert "by default" in row and "far edge" in row


def test_alarm_triage_site_option_sourced():
    sources = section_text(ALARM_TRIAGE, "Sources")
    for url in (RHAII_NOTES, VLLM_POOLING, RAN_DU):
        assert f"({url})" in sources, f"Alarm triage Sources has no row linking {url}"
    slugs = placement_h3_slugs()
    for anchor in re.findall(r"architecture/placement\.md#([a-z0-9-]+)", body(ALARM_TRIAGE)):
        assert anchor in slugs, f"placement.md has no H3 for #{anchor}"


def test_alarm_triage_site_option_short():
    assert prose_words(site_option_paragraph()) <= 55


def test_alarm_triage_bring_and_sandbox_unchanged():
    fm = front_matter(ALARM_TRIAGE) or {}
    assert fm["adaptation"] == ALARM_TRIAGE_ADAPTATION
    assert fm["sandbox"] == ALARM_TRIAGE_SANDBOX


# ---------- every site text ----------


@pytest.mark.parametrize("label,text", site_texts(), ids=lambda v: v if len(v) < 60 else "text")
def test_site_pages_vendor_neutral(label, text):
    assert VENDOR_NAMES.findall(URL_IN_LINK.sub("]", text)) == [], label


@pytest.mark.parametrize("label,text", site_texts(), ids=lambda v: v if len(v) < 60 else "text")
def test_no_performance_numbers_on_site_pages(label, text):
    assert PERFORMANCE.findall(URL_IN_LINK.sub("]", text)) == [], label


# ---------- Site log reduction ----------

SLR = "network-operations/site-log-reduction"
PB10_ROI = "../../../platform/compliance-operating-model/README.md#staged-rollout-and-roi"
GATE_LINK = "../../../architecture/decision-gate.md"
CURRENCY_OR_SAVING = re.compile(r"[$€£¥]\s?\d|\d+(\.\d+)?\s?%|\bsaves? \d")


def test_site_log_reduction_spec():
    fm = front_matter(site_page(SLR)) or {}
    assert fm["id"] == "UC-OPS-10"
    assert fm["depth"] == "entry"
    assert fm["otel_slots"] == ["embedding"]
    assert fm["autonomy_ceiling"] == "inform"
    assert fm["placement_tier"] == ["far-edge"]
    placement = fm["placement"]
    assert placement["far-edge"]["runs"] == ["embedding"]
    assert placement["regional"]["runs"] == [] and placement["core"]["runs"] == []
    assert fm["adaptation"]["rung"] == "retrieval"
    assert fm["sandbox"]["fit"] == "none"
    assert fm["card"]["goal"] == "incidents"


def test_site_log_reduction_roi_measure():
    text = section_text(site_page(SLR), "Problem and value")
    flat = re.sub(r"\s+", " ", text)
    assert re.search(r"(?i)GB per day per site", flat)
    assert re.search(r"(?i)number of sites", flat)
    assert re.search(r"(?i)cost per GB", flat)
    assert re.search(r"(?i)you supply|operator supplies|your own", flat)
    assert CURRENCY_OR_SAVING.findall(URL_IN_LINK.sub("]", flat)) == []
    assert PB10_ROI in flat


def test_site_log_reduction_scope():
    flat = re.sub(r"\s+", " ", body(site_page(SLR)))
    assert re.search(r"(?i)operational logs only", flat)
    assert re.search(r"(?i)security logs keep their own retention", flat)
    assert re.search(r"(?i)raw logs stay (on the site server|local|at the site)[^.]*retention period", flat)
    assert re.search(r"(?i)never deletes? (a )?(raw )?logs? before", flat)


def test_site_log_reduction_governance():
    gov = section_text(site_page(SLR), "Governance")
    assert "Every outcome is LOOK" in gov
    assert f"[decision gate]({GATE_LINK})" in gov
    outcomes = re.findall(r"\| (LOOK|NOTIFY|REVIEW|ACT|STOP) \|", gov)
    assert outcomes and set(outcomes) == {"LOOK"}, outcomes


# ---------- Site change-risk gate ----------

SCG = "agentic-operations/site-change-risk-gate"
PB06_STAGED = "../../../platform/safety-autonomy-gating/README.md#staged-autonomy"
PB04_SETTINGS = "../../../platform/serving-routing-placement/README.md#key-settings-per-setup"
TMF_AN = "https://www.tmforum.org/wp-content/uploads/2019/05/22553-Autonomous-Networks-whitepaper.pdf"
CLOSED_LOOP_FOLDER = "https://github.com/ravisharma5/otel-telco-blueprints-impl/tree/main/closed-loop-incident-handling"
CODE_FENCE = re.compile(r"^```[^\n]*\n(.*?)^```", re.M | re.S)
EXPECTED_H2 = [
    "At a glance", "Problem and value", "How it works", "What you need",
    "Governance", "Sources", "Deploy and verify", "Limitations",
]


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _h3_titles(text: str) -> list[str]:
    return re.findall(r"^### (.+?)\s*$", text, re.M)


def _no_fences(text: str) -> str:
    return CODE_FENCE.sub("", text)


def test_change_gate_front_matter():
    path = site_page(SCG)
    fm = front_matter(path) or {}
    assert fm["id"] == "UC-AGOPS-04"
    assert fm["depth"] == "recipe" and fm["flagship"] is False
    assert fm["otel_slots"] == ["decision"]
    assert fm["autonomy_ceiling"] == "act-within-policy"
    assert fm["tmf_an_level_target"] == 3
    assert fm["sandbox"]["fit"] == "whole-agent"
    assert fm["placement_tier"] == ["far-edge"]
    placement = fm["placement"]
    assert placement["far-edge"]["runs"] == ["decision"]
    assert placement["regional"]["runs"] == [] and placement["core"]["runs"] == []
    assert fm["card"]["goal"] == "change"
    flat = _flat(body(path))
    assert re.search(r"(?i)Level 3 for low-risk change types only", flat)
    assert f"({TMF_AN})" in section_text(path, "Sources")


def test_change_gate_sections():
    path = site_page(SCG)
    h2 = re.findall(r"^## (.+?)\s*$", body(path), re.M)
    assert h2 == EXPECTED_H2, h2
    how = section_text(path, "How it works")
    assert "```mermaid" in how
    first_list = re.findall(r"^\d+\. ", how.split("### ")[0], re.M)
    assert 3 <= len(first_list) <= 8, len(first_list)
    h3 = _h3_titles(how)
    assert "Tools and risk classes" in h3 and "Slots and checkpoints" in h3
    assert sum(t.startswith("Worked example: ") for t in h3) == 1


def test_change_gate_contract():
    path = site_page(SCG)
    text = _flat(section_text(path, "How it works") + " " + section_text(path, "Governance"))
    for phrase in ("shadow stage", "lower of the", "forces STOP", "false ACT"):
        assert phrase in text, phrase
    assert GATE_LINK in text
    assert PB06_STAGED in text
    assert re.search(r"(?i)OS (and|or) firmware upgrades? (is|are) always REVIEW", text)


def test_change_gate_site_state():
    how = _flat(section_text(site_page(SCG), "How it works"))
    for term in ("active alarms", "PTP lock", "traffic", "maintenance window"):
        assert re.search(rf"(?i){term}", how), term
    assert "SMO or EMS" in how
    assert re.search(r"ZTP or TALM", how)


def test_change_gate_no_llm_at_site():
    path = site_page(SCG)
    how = section_text(path, "How it works")
    part = how[how.index("### Slots and checkpoints"):]
    part = part[: part.index("### ", 4)] if "### " in part[4:] else part
    rows = [ln for ln in part.splitlines() if ln.startswith("| `")]
    assert len(rows) == 1, rows
    assert rows[0].startswith("| `decision` |") and rows[0].rstrip().endswith("| Far edge |"), rows[0]
    assert re.search(r"(?i)no 31B or other LLM runs at the site", _flat(body(path)))


def test_change_gate_cpu_check():
    from tools.tests.test_use_case_pages import pb04_flag_blocks

    path = site_page(SCG)
    need = section_text(path, "What you need")
    flat = _flat(need)
    assert "vllm-cpu-rhel9" in flat
    assert re.search(r"(?i)W4A16 build on the CPU image", flat)
    assert re.search(r"W8A8", flat) and re.search(r"AWQ or GPTQ", flat) and "LLM Compressor" in flat
    assert re.search(r"(?i)same gates", flat)
    code = "\n".join(CODE_FENCE.findall(need))
    header = next(h for h in pb04_flag_blocks() if h.startswith("# Decision"))
    assert header in code
    for line in pb04_flag_blocks()[header]:
        assert line in code, line
    prose = _flat(_no_fences(need))
    assert re.search(r"(?i)non-real-time cores", prose) and "isolated" in prose
    for token in ("`VLLM_CPU_OMP_THREADS_BIND`", "`--kv-cache-memory-bytes`"):
        assert token in prose, token
    assert re.search(r"(?i)memory set aside for AI", prose)
    assert PB04_SETTINGS in prose
    all_code = "\n".join(CODE_FENCE.findall(body(path)))
    assert "VLLM_CPU_OMP_THREADS_BIND" not in all_code
    assert "--kv-cache-memory-bytes" not in all_code


def test_change_gate_settings_anchor_exists():
    serving = REPO_ROOT / "platform" / "serving-routing-placement" / "README.md"
    slugs = {github_slug(m) for m in re.findall(r"^### (.+?)\s*$", serving.read_text(encoding="utf-8"), re.M)}
    assert "key-settings-per-setup" in slugs


def test_change_gate_engine_qualifier():
    from tools.tests.test_use_case_pages import decision_engine_prerequisite

    need = section_text(site_page(SCG), "What you need")
    bullets = [ln for ln in need.splitlines() if ln.startswith("- [ ] Decision engine:")]
    assert len(bullets) == 1, bullets
    bullet = bullets[0]
    assert decision_engine_prerequisite() in bullet
    tail = bullet[bullet.index(decision_engine_prerequisite()) :]
    assert "CPU image" in tail
    assert re.search(r"(?i)Decision CPU check", tail)


def test_change_gate_roi_measures():
    text = section_text(site_page(SCG), "Problem and value")
    flat = _flat(text)
    assert re.search(r"(?i)changes deferred that would have failed", flat)
    assert re.search(r"(?i)outage or truck roll", flat)
    assert re.search(r"(?i)failed-change rate before and after", flat)
    assert re.search(r"(?i)in shadow|shadow stage", flat)
    assert CURRENCY_OR_SAVING.findall(URL_IN_LINK.sub("]", flat)) == []
    assert PB10_ROI in flat


def test_change_gate_impl_links():
    deploy = _flat(section_text(site_page(SCG), "Deploy and verify"))
    assert CLOSED_LOOP_FOLDER in deploy
    assert GATE_LINK in deploy
    bullet = next(b for b in re.findall(r"^- .*$", section_text(site_page(SCG), "Deploy and verify"), re.M) if CLOSED_LOOP_FOLDER in b)
    assert re.search(r"(?i)replays incidents, not changes", bullet), bullet
