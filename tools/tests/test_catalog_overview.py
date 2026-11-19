"""The Recipes overview (catalog/index.md) is generated from use-case front matter.

tools/site/render_catalog.py writes two blocks between generated markers: the
recipes by domain, and the recipes per platform blueprint. These tests check the
page matches front matter, lists every page once, shows the flagship merges
(also_covers), and gives every platform blueprint an anchor that its page links.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from tools.bplint.slug import github_slug
from tools.tests.conftest import REPO_ROOT

OVERVIEW = REPO_ROOT / "catalog/index.md"
STUB = REPO_ROOT / "site-src/catalog/index.md"
TRIAGE = REPO_ROOT / "catalog/network-operations/alarm-triage-adaptation/README.md"
CARD_31B = "https://huggingface.co/farbodtavakkoli/OTel-2.0-LLM-31B-IT#supported-language-and-modality"
DEPTH_LABELS = {"recipe": "Full recipe", "entry": "Catalog entry"}


def _fm(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1]) or {}


def use_case_pages() -> list[Path]:
    return [
        p
        for p in sorted((REPO_ROOT / "catalog").glob("*/*/README.md"))
        if _fm(p).get("domain") != "demo"
    ]


def platform_pages() -> list[Path]:
    return sorted((REPO_ROOT / "platform").glob("*/README.md"), key=lambda p: _fm(p)["id"])


def _block(name: str) -> str:
    text = OVERVIEW.read_text(encoding="utf-8")
    m = re.search(
        rf"<!-- generated:{name} start -->\n(.*?)<!-- generated:{name} end -->", text, re.S
    )
    assert m, f"no generated:{name} block"
    return m.group(1)


def _split(block: str, level: str) -> dict[str, str]:
    """Heading text -> body for each heading of the given level ("##" or "###")."""
    parts = re.split(rf"^{level} (.+)$", block, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts), 2)}


def _rows(section: str) -> list[list[str]]:
    rows = []
    for line in section.splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows[1:]


def test_overview_matches_front_matter():
    from tools.site import render_catalog

    assert render_catalog.main(["--check"]) == 0, "run `make render`"


def test_overview_check_fails_on_drift(tmp_path):
    from tools.site import render_catalog

    text = OVERVIEW.read_text(encoding="utf-8")
    broken = text.replace("| Full recipe |", "| Catalog entry |", 1)
    assert broken != text
    assert render_catalog.render(broken) == text


def test_overview_no_stub_left():
    assert OVERVIEW.is_file()
    assert not STUB.exists()


def test_overview_front_matter():
    fm = _fm(OVERVIEW)
    assert fm["title"] == "Recipes"
    assert "type" not in fm
    assert "\n# Recipes\n" in OVERVIEW.read_text(encoding="utf-8")


def test_overview_lists_every_page_once():
    from tools.site.export_explorer import DOMAIN_LABELS

    domains = _split(_block("catalog-by-domain"), "##")
    seen: list[str] = []
    for path in use_case_pages():
        fm = _fm(path)
        label = DOMAIN_LABELS[fm["domain"]]
        assert label in domains, label
        rows = [r for r in _rows(domains[label]) if r[0].startswith(f"[{fm['id']}]")]
        assert len(rows) == 1, (fm["id"], rows)
        rel = path.relative_to(REPO_ROOT / "catalog").as_posix()
        assert rows[0][0] == f"[{fm['id']}]({rel})"
        assert rows[0][1] == fm["title"]
        assert rows[0][2] == DEPTH_LABELS[fm["depth"]]
        seen.append(fm["id"])
    block = _block("catalog-by-domain")
    for uc in seen:
        assert block.count(f"[{uc}]") == 1, uc
    assert len(re.findall(r"^\| \[UC-", block, re.M)) == len(seen)


def test_overview_domains_in_schema_order():
    from tools.site.export_explorer import DOMAIN_LABELS

    schema = json.loads((REPO_ROOT / "schemas/use-case.schema.json").read_text(encoding="utf-8"))
    order = [d for d in schema["properties"]["domain"]["enum"] if d != "demo"]
    present = {_fm(p)["domain"] for p in use_case_pages()}
    want = [DOMAIN_LABELS[d] for d in order if d in present]
    assert list(_split(_block("catalog-by-domain"), "##")) == want


def test_overview_also_covers():
    block = _block("catalog-by-domain")
    rows = {r[0].split("]")[0][1:]: r for r in _rows(block)}
    for path in use_case_pages():
        fm = _fm(path)
        items = fm.get("also_covers") or []
        assert rows[fm["id"]][3] == "; ".join(items), fm["id"]
    assert "standards Q&A" in rows["UC-KNOW-01"][3]
    assert "Grounded RAG assistants" in rows["UC-KNOW-01"][3]
    assert "Closed-loop incident handling" in rows["UC-AGOPS-01"][3]
    assert "NOC ticket triage" in rows["UC-OPS-01"][3]
    assert "Customer care diagnostics" in rows["UC-CARE-01"][3]


def test_overview_no_duplicate_merged_entries():
    """A merged item has no page of its own: no title repeats an also_covers item."""
    titles = {_fm(p)["title"].lower() for p in use_case_pages()}
    for path in use_case_pages():
        for item in _fm(path).get("also_covers") or []:
            assert item.lower() not in titles, item


def test_overview_by_platform():
    text = OVERVIEW.read_text(encoding="utf-8")
    assert "\n## By platform blueprint\n" in text
    assert text.index("## By platform blueprint") < text.index("<!-- generated:catalog-by-platform start -->")
    sections = _split(_block("catalog-by-platform"), "###")
    pages = platform_pages()
    assert list(sections) == [f"{_fm(p)['id']} {_fm(p)['title']}" for p in pages]
    for path in pages:
        pb = _fm(path)["id"]
        head = f"{pb} {_fm(path)['title']}"
        listed = re.findall(r"^- \[(UC-[A-Z]+-\d{2}) ", sections[head], re.M)
        want = sorted(_fm(u)["id"] for u in use_case_pages() if pb in _fm(u)["platform_blueprints"])
        assert listed == want, (pb, listed, want)
        assert github_slug(head).startswith(pb.lower() + "-")


def test_overview_platform_anchor_example():
    sections = _split(_block("catalog-by-platform"), "###")
    assert github_slug(next(h for h in sections if h.startswith("PB-08 "))) == (
        "pb-08-security-identity-and-sandbox"
    )


@pytest.mark.parametrize(
    ("items", "ok"),
    [
        (["Telecom standards Q&A over documents you hold rights to"], True),
        (["one two three four five six seven eight nine ten eleven twelve"], True),
        (["one two three four five six seven eight nine ten eleven twelve thirteen"], False),
        (["Same item", "Same item"], False),
        ([""], False),
    ],
)
def test_also_covers_schema(items, ok):
    fm = _fm(TRIAGE)
    fm["also_covers"] = items
    from tools.tests.test_schema import _validator

    errors = list(_validator("use-case.schema.json").iter_errors(fm))
    assert (not errors) == ok, [e.message for e in errors]


def test_triage_language_scope():
    from tools.tests.test_platform_pages import section_text

    lim = section_text(TRIAGE, "Limitations")
    bullets = [ln for ln in lim.splitlines() if ln.startswith("- ")]
    assert len(bullets) <= 6, bullets
    assert any("English" in b and "French" in b and CARD_31B in b for b in bullets), bullets


# Every item of the application list the catalog was built from, and every
# agenda gap, maps to a landed page ("<domain>/<slug>") or to an also_covers
# item on a flagship ("also_covers:<domain>/<slug>"). Generic names only.
COVERAGE: dict[str, str] = {
    # Standards and protocol knowledge
    "telecom standards Q&A": "also_covers:standards-knowledge/grounded-knowledge-assistant",
    "grounded RAG assistants": "also_covers:standards-knowledge/grounded-knowledge-assistant",
    "spec summarisation": "standards-knowledge/spec-summarisation",
    "OSS/BSS architecture guidance": "standards-knowledge/oss-bss-architecture-guidance",
    # Network software and automation
    "RAN and core code assistants": "network-software/ran-core-code-assistant",
    "network automation": "network-software/network-automation-review",
    "O-RAN RIC": "network-software/oran-ric-xapp-assistant",
    # Network operations
    "signalling trace analysis": "network-operations/signalling-trace-analysis",
    "core network RCA": "network-operations/core-network-rca",
    "RAN and RF health checks": "network-operations/ran-rf-health-checks",
    "NOC ticket triage": "also_covers:network-operations/alarm-triage-adaptation",
    "security triage": "security/security-triage",
    # Agentic operations
    "closed-loop incident handling": "also_covers:agentic-operations/closed-loop-incident-handling",
    "customer care diagnostics": "also_covers:business-assurance/camara-care-diagnostics",
    "router and 5G core operations": "agentic-operations/router-core-read-only-ops",
    "policy-following operations agents": "agentic-operations/policy-following-ops-agents",
    # Under development
    "broadband digital troubleshooting": "business-assurance/broadband-digital-troubleshooting",
    "network RCA reasoning": "research/kpi-rca-reasoning",
    "5G mobility failure analysis": "research/mobility-failure-analysis",
    "cybersecurity attack classification": "security/signalling-attack-classification",
    # Agenda gaps
    "churn": "business-assurance/churn-risk-explanation",
    "revenue assurance": "business-assurance/revenue-assurance-triage",
    "energy": "network-operations/ran-energy-saving",
    "slice SLA": "network-operations/slice-sla-assurance",
    "MOP validation": "network-operations/mop-validation",
    "transport and IETF diagnostics": "network-operations/transport-ip-diagnostics",
    "cross-domain OSS correlation": "network-operations/cross-domain-oss-correlation",
}
# The words each merged item must show in its flagship's also_covers list.
ALSO_COVERS_WORDS = {
    "telecom standards Q&A": "standards Q&A",
    "grounded RAG assistants": "Grounded RAG assistants",
    "NOC ticket triage": "NOC ticket triage",
    "closed-loop incident handling": "Closed-loop incident handling",
    "customer care diagnostics": "Customer care diagnostics",
}


def _pages_by_key() -> dict[str, dict]:
    return {p.relative_to(REPO_ROOT / "catalog").parent.as_posix(): _fm(p) for p in use_case_pages()}


def test_catalog_covers_application_list_and_gaps():
    pages = _pages_by_key()
    assert len(COVERAGE) == 27
    for item, target in COVERAGE.items():
        if target.startswith("also_covers:"):
            key = target.split(":", 1)[1]
            assert key in pages, (item, key)
            fm = pages[key]
            assert fm.get("flagship") is True, (item, key)
            covers = fm.get("also_covers") or []
            assert any(ALSO_COVERS_WORDS[item] in c for c in covers), (item, covers)
        else:
            assert target in pages, (item, target)
            assert pages[target].get("flagship") is not True, (item, target)
    merged = {t.split(":", 1)[1] for t in COVERAGE.values() if t.startswith("also_covers:")}
    flagships = {k for k, fm in pages.items() if fm.get("flagship") is True}
    assert merged == flagships


def test_catalog_counts():
    pages = list(_pages_by_key().values())
    assert len(pages) == 29
    recipes = [fm for fm in pages if fm.get("depth") == "recipe"]
    entries = [fm for fm in pages if fm.get("depth") == "entry"]
    assert len(recipes) == 10 and len(entries) == 19
    assert sum(1 for fm in recipes if fm.get("flagship") is True) == 4
    assert sum(1 for fm in recipes if fm.get("flagship") is False) == 6
    for fm in pages:
        assert fm.get("card") and fm.get("placement") and fm.get("depth"), fm.get("id")
