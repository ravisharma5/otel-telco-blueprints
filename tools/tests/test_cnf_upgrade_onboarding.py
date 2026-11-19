"""The CNF upgrade pre- and post-checks recipe and the software onboarding entry.

An agent reads live workload state through read-only tools before and after a
vendor CNF upgrade. Every upgrade passes the Decision gate, and automation
jobs run the upgrade, the post-check, and the rollback. These tests pin the
gate contract, the per-class TM Forum targets, the write paths, the harness,
the slots, the rollback design (text and diagram agree), the ROI measures, the
fictitious worked example, and the vendor-neutral, number-free text.

The software onboarding and CVE review entry recommends a permit-to-build
decision to a person through read-only tools and never writes.
"""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path

import pytest

from tools.tests.conftest import REPO_ROOT
from tools.tests.test_platform_pages import section_text
from tools.tests.test_reference_pages import body, front_matter
from tools.tests.test_site_far_edge import (
    CLOSED_LOOP_FOLDER,
    CURRENCY_OR_SAVING,
    EXPECTED_H2,
    GATE_LINK,
    PB06_STAGED,
    PB10_ROI,
    PERFORMANCE,
    TMF_AN,
    URL_IN_LINK,
    _flat,
    _h3_titles,
)

CNF = "agentic-operations/cnf-upgrade-checks"
PB07_LINK = "../../../platform/action-layer/README.md"
ADAPT_LINK = "../../../platform/adaptation/README.md"
INTEGRATION_LINK = "../../../platform/integration/README.md"
LEVEL3 = "Level 3 once the class earns the act stage"
LEVEL4 = (
    "An operator aiming for Level 4 can set it as a per-class target; the stage register earns each "
    "class up to the act stage (Level 3), and PB-06 treats Level 4 as a later target beyond these "
    "blueprints. This recipe claims no level."
)
NARROWING = (
    "This narrows the [PB-07](../../../platform/action-layer/README.md) default of always rolling back, "
    "for workloads whose rollback is unsafe."
)
FAILED_LEAD = (
    "The Classification slot labels the failure first, and the Decision slot then gives the "
    "rollback-or-escalate label."
)
PUBLIC_VENDORS = re.compile(r"(?i)AT&T|Ericsson|OCTO")
SHORTHAND = re.compile(r"\b[Ff][1-4]\b")
ID_TOKEN = re.compile(r"^[a-z]+(-[a-z]+)*-\d{4}$")
IPV4 = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
IPV6 = re.compile(r"(?i)\b(?:[0-9a-f]{1,4}:){2,}[0-9a-f:]*")
DOC_V4 = [ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")]
DOC_V6 = ipaddress.ip_network("2001:db8::/32")
URL = re.compile(r"\(https?://[^)]*\)|https?://\S+")
VERSION_25 = re.compile(r"(?<![\d.])2\.5(?!\d)")


# ---------- helpers ----------


def page() -> Path:
    path = REPO_ROOT / "catalog" / CNF / "README.md"
    if not path.is_file():
        pytest.skip(f"{CNF} has not landed yet")
    return path


def h3_text(section: str, title_prefix: str) -> str:
    """Raw markdown under the first H3 whose title starts with title_prefix."""
    m = re.search(rf"^### {re.escape(title_prefix)}.*$", section, re.M)
    assert m, f"no '### {title_prefix}' H3"
    nxt = re.search(r"^### ", section[m.end() :], re.M)
    return section[m.end() : m.end() + nxt.start()] if nxt else section[m.end() :]


def table_rows(text: str) -> list[list[str]]:
    """Rows of the first markdown table in text, header first, separator dropped."""
    rows, started = [], False
    for line in text.splitlines():
        if line.startswith("|"):
            started = True
            if re.match(r"^\|[\s:|-]+\|\s*$", line):
                continue
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
        elif started:
            break
    return rows


def how() -> str:
    return section_text(page(), "How it works")


def first_steps() -> list[str]:
    """The numbered steps of the first ordered list in How it works."""
    intro = how().split("### ")[0]
    return [m.group(1).strip() for m in re.finditer(r"^\d+\. (.+)$", intro, re.M)]


def mermaid_edges() -> list[tuple[str, str]]:
    """(from label, to label) for every edge in the How it works Mermaid fence."""
    fences = re.findall(r"```mermaid\n(.*?)```", how(), re.S)
    assert len(fences) == 1, len(fences)
    fence = fences[0]
    labels = dict(re.findall(r"\b(\w+)\s*[\[{]\"([^\"]*)\"[\]}]", fence))
    edges = []
    for line in fence.splitlines():
        parts = re.split(r"\s*(?:--\s*\"[^\"]*\"\s*)?-->\s*", line.strip())
        if len(parts) < 2:
            continue
        ids = [re.match(r"(\w+)", p).group(1) for p in parts if p]
        edges += [(labels.get(a, a), labels.get(b, b)) for a, b in zip(ids, ids[1:])]
    return edges


def governance_rows() -> list[list[str]]:
    return table_rows(section_text(page(), "Governance"))


# ---------- front matter and sections ----------


def test_cnf_front_matter():
    fm = front_matter(page()) or {}
    assert fm["id"] == "UC-AGOPS-05"
    assert fm["title"] == "CNF upgrade pre- and post-checks"
    assert fm["domain"] == "agentic-operations"
    assert fm["depth"] == "recipe" and fm["flagship"] is False
    assert fm["otel_slots"] == ["llm", "decision", "safety", "classification", "embedding", "reranker"]
    assert fm["autonomy_ceiling"] == "act-within-policy"
    assert fm["tmf_an_level_target"] == 3
    assert fm["placement_tier"] == ["regional", "core"]
    placement = fm["placement"]
    assert placement["far-edge"]["runs"] == []
    assert placement["regional"]["runs"] == ["decision", "safety", "classification", "embedding", "reranker"]
    assert placement["core"]["runs"] == ["llm-large"]
    assert fm["sandbox"]["fit"] == "whole-agent"
    assert fm["adaptation"]["rung"] == "lora-if-gap"
    assert fm["card"]["goal"] == "change"


def test_cnf_sections():
    path = page()
    h2 = re.findall(r"^## (.+?)\s*$", body(path), re.M)
    assert h2 == EXPECTED_H2, h2
    text = how()
    assert text.count("```mermaid") == 1
    assert 3 <= len(first_steps()) <= 8, first_steps()
    h3 = _h3_titles(text)
    for title in (
        "Tools and risk classes",
        "Gate policy per change class",
        "On a failed post-check",
        "Harness",
        "Slots and checkpoints",
    ):
        assert title in h3, (title, h3)
    assert sum(t.startswith("Worked example: ") for t in h3) == 1


# ---------- gate contract and TM Forum scope ----------


def test_cnf_gate_contract():
    path = page()
    text = _flat(section_text(path, "How it works") + " " + section_text(path, "Governance"))
    for phrase in ("shadow stage", "lower of the", "forces STOP", "false ACT", "Major upgrades are always REVIEW"):
        assert phrase in text, phrase
    assert GATE_LINK in text
    assert PB06_STAGED in text


def test_cnf_gate_policy_tmf():
    rows = table_rows(h3_text(how(), "Gate policy per change class"))
    header = rows[0]
    assert "TM Forum target" in header, header
    col = header.index("TM Forum target")
    by_class = {r[0]: r[col] for r in rows[1:]}
    level3 = ("Patch", "Certificate rotation", "Configuration change listed")
    level2 = ("Other configuration change", "Minor upgrade", "Major upgrade")
    for prefix in level3 + level2:
        matches = [k for k in by_class if k.startswith(prefix)]
        assert len(matches) == 1, (prefix, list(by_class))
        want = LEVEL3 if prefix in level3 else "Level 2"
        assert by_class[matches[0]] == want, (prefix, by_class[matches[0]])
    assert TMF_AN in section_text(page(), "Sources")


def test_cnf_level4_wording():
    flat = _flat(body(page()))
    assert LEVEL4 in flat
    assert "This recipe claims no level." in flat


# ---------- tools and write paths ----------


def _tool_rows() -> list[list[str]]:
    return table_rows(h3_text(how(), "Tools and risk classes"))[1:]


def test_cnf_tools_contracts():
    rows = _tool_rows()
    reads = [r for r in rows if not r[0].startswith("`submit_action_request`")]
    for r in reads:
        assert "`read`" in r[1], r
    tool_text = " ".join(r[0] for r in reads)
    for group in ("software gateway", "inventory", "compliance", "CVE", "YANG", "cluster", "GitOps", "job status", "tickets"):
        assert group in tool_text, group
    job = next(r for r in reads if "job status" in r[0])
    joined = " ".join(job)
    assert "read-only mode" in joined and re.search(r"(?i)never launch a job", joined), job
    flat = _flat(body(page()))
    assert "deny-unless-allowed" in flat
    assert INTEGRATION_LINK in flat


def test_cnf_write_paths():
    rows = _tool_rows()
    writes = [r for r in rows if "write_" in r[1]]
    assert len(writes) == 3, writes
    assert all(r[0].startswith("`submit_action_request`") for r in writes), writes
    pr = [r for r in writes if "pull request" in r[0]]
    assert len(pr) == 1
    pr_text = " ".join(pr[0])
    assert "`write_low`" in pr[0][1]
    assert "recommend stage" in pr_text and "merge is the approval" in pr_text
    upgrade = [r for r in writes if "minor or major upgrade" in r[0]]
    assert len(upgrade) == 1
    assert "`write_high`" in upgrade[0][1]
    assert re.search(r"(?i)always REVIEW", " ".join(upgrade[0]))


# ---------- harness and slots ----------


def test_cnf_harness():
    rows = table_rows(h3_text(how(), "Harness"))[1:]
    assert [r[0] for r in rows] == [
        "Skills", "Capability manifest", "Corpora", "Gate policy", "Classification head", "LoRA",
    ]
    cells = {r[0]: r[1] for r in rows}
    for skill in (
        "pre-upgrade check", "post-upgrade verification", "rollback decision",
        "compliance explain-and-fix", "YANG change review", "change summary",
    ):
        assert skill.lower() in cells["Skills"].lower(), skill
    for corpus in ("release notes", "MOP", "past upgrade outcomes", "compliance-rule catalog", "YANG modules", "CVE advisories"):
        assert corpus in cells["Corpora"], corpus
    for cls in ("crash loop", "certificate expiry", "configuration mismatch", "quota", "dependency", "licence"):
        assert cls in cells["Classification head"], cls
    assert "measured" in cells["LoRA"] and "gap" in cells["LoRA"]
    assert ADAPT_LINK in body(page())


def test_cnf_slots_table():
    rows = table_rows(h3_text(how(), "Slots and checkpoints"))[1:]
    assert [r[0] for r in rows] == ["`llm`", "`decision`", "`safety`", "`classification`", "`embedding`", "`reranker`"]
    for r in rows:
        assert "pinned by revision" in r[1], r
        assert not VERSION_25.search(r[1]), r
        assert r[-1] == ("Core" if r[0] == "`llm`" else "Regional"), r


def test_cnf_otel25_framing():
    text = _flat(URL.sub("", body(page())))
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if VERSION_25.search(s)]
    assert sentences
    for s in sentences:
        assert "intake" in s or "assumes no" in s, s
    assert any(re.search(r"(?i)tool calling", s) for s in sentences)


# ---------- rollback design ----------


def test_cnf_rollback_design():
    section = h3_text(how(), "On a failed post-check")
    assert FAILED_LEAD in _flat(section)
    rows = table_rows(section)[1:]
    prefixes = ("Rollback", "Escalate", "Safety abstains", "STOP")
    assert len(rows) == 4 and all(r[0].startswith(p) for r, p in zip(rows, prefixes)), [r[0] for r in rows]
    rollback, escalate, abstain, stop = rows
    for r in (rollback, abstain):
        assert "paired rollback job" in r[1], r
        assert r[2].startswith("None"), r
    assert re.search(r"(?i)hold the workload in place", escalate[1]), escalate
    for cause in ("certificate", "quota", "dependency"):
        assert cause in escalate[0], cause
    assert "REVIEW" in escalate[2]
    stop_text = " ".join(stop)
    assert re.search(r"(?i)freeze further upgrades", stop_text)
    assert "hold it in place" in stop_text and "approver" in stop_text
    assert "never cancels a rollback job already running" in stop_text
    flat_body = _flat(body(page()))
    assert flat_body.count(NARROWING) == 1
    assert PB07_LINK in flat_body
    gov = governance_rows()[1:]
    assert any("paired rollback job" in r[0] for r in gov)
    hold = [r for r in gov if r[0].startswith("Hold a failed workload in place")]
    assert len(hold) == 1 and "REVIEW from the recommend stage up" in hold[0][1], hold
    freeze = [r for r in gov if r[0].startswith("Freeze further upgrades")]
    assert len(freeze) == 1 and freeze[0][1].startswith("STOP"), freeze


def test_cnf_rollback_order_text_matches_diagram():
    edges = set(mermaid_edges())
    for edge in (
        ("Post-check job", "Classify the failure"),
        ("Classify the failure", "Rollback-or-escalate label"),
        ("Rollback-or-escalate label", "Rollback job"),
        ("Rollback-or-escalate label", "Hold in place for the approver"),
        ("Rollback-or-escalate label", "Freeze further upgrades of the workload"),
    ):
        assert edge in edges, edge
    assert ("Post-check job", "Rollback-or-escalate label") not in edges
    steps = first_steps()
    assert len(steps) >= 6
    step = steps[5]
    positions = [step.find(w) for w in ("post-check", "Classification", "rollback-or-escalate label")]
    assert -1 not in positions and positions == sorted(positions), (positions, step)
    lead = FAILED_LEAD
    assert lead.index("Classification") < lead.index("rollback-or-escalate label")


# ---------- value, example, links, neutrality ----------


def test_cnf_roi_measures():
    flat = _flat(section_text(page(), "Problem and value"))
    for pattern in (
        r"(?i)failed upgrades avoided or rolled back early",
        r"(?i)incident or outage",
        r"(?i)vendor delivery to production",
        r"(?i)first-time post-check pass rate",
        r"(?i)approver time saved per change",
    ):
        assert re.search(pattern, flat), pattern
    prose = URL_IN_LINK.sub("]", flat)
    assert CURRENCY_OR_SAVING.findall(prose) == []
    assert "%" not in prose
    assert PB10_ROI in flat


def test_cnf_worked_example():
    example = h3_text(how(), "Worked example: ")
    flat = _flat(example)
    assert "`chg-4417`" in flat
    assert re.search(r"(?i)minor upgrade", flat)
    assert "IMS core" in flat
    assert re.search(r"(?i)certificate[^.]*expires inside the upgrade window", flat)
    assert "REVIEW" in flat
    for token in re.findall(r"`([^`]+)`", example):
        if re.search(r"\d", token):
            assert ID_TOKEN.match(token), token
    text = URL.sub("", body(page()))
    for ip in IPV4.findall(text):
        assert any(ipaddress.ip_address(ip) in net for net in DOC_V4), ip
    for ip in IPV6.findall(text):
        assert ipaddress.ip_network(ip if "/" in ip else f"{ip}/128", strict=False).subnet_of(DOC_V6), ip


def test_cnf_impl_link():
    deploy = section_text(page(), "Deploy and verify")
    assert CLOSED_LOOP_FOLDER in deploy
    bullet = next(b for b in re.findall(r"^- .*$", deploy, re.M) if CLOSED_LOOP_FOLDER in b)
    assert re.search(r"(?i)replays incidents, not upgrades", bullet), bullet


def test_cnf_vendor_neutral():
    text = URL_IN_LINK.sub("]", page().read_text(encoding="utf-8"))
    assert PUBLIC_VENDORS.findall(text) == []
    assert SHORTHAND.findall(text) == []


def test_cnf_no_performance_numbers():
    text = URL_IN_LINK.sub("]", page().read_text(encoding="utf-8"))
    assert PERFORMANCE.findall(text) == []


# ---------- software onboarding and CVE review entry ----------

ONBOARDING = "security/software-onboarding-cve-review"
CNF_FROM_ENTRY = "../../agentic-operations/cnf-upgrade-checks/README.md"
ENTRY_FROM_CNF = "../../security/software-onboarding-cve-review/README.md"


def onboarding_page() -> Path:
    path = REPO_ROOT / "catalog" / ONBOARDING / "README.md"
    if not path.is_file():
        pytest.skip(f"{ONBOARDING} has not landed yet")
    return path


def onboarding_text() -> str:
    """Body with URLs removed and whitespace flattened."""
    return _flat(URL_IN_LINK.sub("]", body(onboarding_page())))


def test_onboarding_spec():
    fm = front_matter(onboarding_page()) or {}
    assert fm["id"] == "UC-SEC-03"
    assert fm["title"] == "Software onboarding and CVE review"
    assert fm["depth"] == "entry" and fm["flagship"] is False
    assert fm["domain"] == "security"
    assert set(fm["otel_slots"]) == {"llm", "embedding", "reranker", "safety"}
    assert len(fm["otel_slots"]) == 4
    assert fm["autonomy_ceiling"] == "inform"
    assert "tmf_an_level_target" not in fm
    placement = fm["placement"]
    assert placement["far-edge"]["runs"] == []
    assert set(placement["regional"]["runs"]) == {"embedding", "reranker", "safety"}
    assert placement["core"]["runs"] == ["llm-large"]
    assert fm["adaptation"]["rung"] == "retrieval-and-skills"
    assert fm["sandbox"]["fit"] == "none"
    assert fm["card"]["goal"] == "secure"


def test_onboarding_never_writes():
    text = onboarding_text()
    assert "submit_action_request" not in text
    assert "- [ ] Write path:" not in body(onboarding_page())
    assert "write_low" not in text and "write_high" not in text
    assert "signs off" in text or "signs the permit" in text
    assert "never writes" in text or "holds no write tool" in text


def test_onboarding_governance_look():
    section = section_text(onboarding_page(), "Governance")
    rows = table_rows(section)
    header = rows[0]
    col = next(i for i, h in enumerate(header) if h.startswith("Gate outcome"))
    assert len(rows) > 1
    for row in rows[1:]:
        assert row[col] == "LOOK", row
    flat = _flat(section)
    assert "Every outcome is LOOK." in flat
    assert re.search(r"nothing reaches the \[decision gate\]\(" + re.escape(GATE_LINK) + r"\)", flat)


def test_onboarding_tools_read_only():
    need = _flat(section_text(onboarding_page(), "What you need"))
    bullet = next(b for b in re.findall(r"- \[ \] Integrations:[^\n]*", section_text(onboarding_page(), "What you need")))
    for contract in ("inventory", "security and CVE", "compliance", "software gateway"):
        assert contract in bullet, contract
    assert "read-only" in bullet
    assert "MCP gateway" in bullet
    assert re.search(r"denies each call unless a role allows it", bullet), bullet
    assert INTEGRATION_LINK in need


def test_onboarding_output():
    text = onboarding_text()
    assert "permit-to-build summary" in text
    assert re.search(r"(?i)CVE reductions", text)
    assert re.search(r"(?i)open findings", text)
    assert re.search(r"(?i)recommends approval or rejection", text)


def test_onboarding_roi_measures():
    flat = _flat(section_text(onboarding_page(), "Problem and value"))
    for pattern in (
        r"(?i)review time per release",
        r"(?i)findings missed",
        r"(?i)time from delivery to permit",
    ):
        assert re.search(pattern, flat), pattern
    prose = URL_IN_LINK.sub("]", flat)
    assert CURRENCY_OR_SAVING.findall(prose) == []
    assert "%" not in prose
    assert PB10_ROI in flat


def test_onboarding_cross_links():
    assert CNF_FROM_ENTRY in body(onboarding_page())
    assert ENTRY_FROM_CNF in body(page())


def test_onboarding_vendor_neutral():
    text = URL_IN_LINK.sub("]", onboarding_page().read_text(encoding="utf-8"))
    assert PUBLIC_VENDORS.findall(text) == []
    assert SHORTHAND.findall(text) == []


def test_onboarding_no_performance_numbers():
    text = URL_IN_LINK.sub("]", onboarding_page().read_text(encoding="utf-8"))
    assert PERFORMANCE.findall(text) == []
