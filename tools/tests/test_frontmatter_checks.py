"""Tests for FM001, FM002, and RF001, plus shared blueprint builders.

The builders here are reused by test_sections_budgets.py and
test_sources_table.py: they render a structurally valid blueprint from the
real budgets.yaml section order so each test changes one thing.
"""

from __future__ import annotations

import pytest
import yaml

from tools.bplint.cli import load_context, run_doc_checks
from tools.bplint.markdown import parse_doc
from tools.tests.conftest import FIXTURES, FIXED_TODAY, REPO_ROOT

SOURCES_HEADER = "| # | Claim | Basis | Source |\n|---|---|---|---|"
SOURCES_ROW = "| 1 | Claim one | model card | [card](https://example.com/card) |"

UC_AT_A_GLANCE = [
    "One-liner",
    "Problem",
    "Audience",
    "OTel slots",
    "Autonomy ceiling",
    "Placement tier",
    "Agent-school courses",
]
PB_AT_A_GLANCE = [
    "One-liner",
    "Question answered",
    "Audience",
    "OTel slots",
    "Placement tier",
    "Top 3 decisions",
    "Agent-school courses",
]


def glance_table(labels, values=None):
    """At-a-glance table; `values` maps a label to its cell, others get "value"."""
    values = values or {}
    rows = "\n".join(f"| **{label}** | {values.get(label, 'value')} |" for label in labels)
    return "| Field | Value |\n|---|---|\n" + rows


AS001_SENTENCE = "None: no agent-school course covers this use case yet"
COURSES_FILE = REPO_ROOT / "tools/bplint/agent-school-courses.yaml"
UC_CARD = {
    "goal": "incidents",
    "summary": "Drafts a triage label for each alarm and an engineer approves it.",
    "outcome": "Engineers spend less time sorting alarms by hand.",
    "audience": "Engineers and their business owner",
    "measures": ["Time to first triage"],
    "risk": "A wrong label slows the fix until an engineer catches it.",
}
UC_PLACEMENT = {"regional": {"runs": ["llm-small"], "note": ""}}
# Matches the default slots (llm only): skills, a golden set, and one tool contract.
UC_ADAPTATION = {
    "rung": "skills",
    "expertise": ["golden-set", "tool-contracts"],
    "bring": [{"item": "Read-only widget tools", "domains": ["oss-bss"], "mechanism": "tool-contract"}],
}
UC_ONE_LINER = "Drafts triage labels with human approval. Needs a tool-calling LLM slot."
PB_ONE_LINER = "Gives each team a model endpoint. Depends on a gateway."
UC_GLANCE_VALUES = {"One-liner": UC_ONE_LINER, "Autonomy ceiling": "Recommend with approval"}
PB_GLANCE_VALUES = {"One-liner": PB_ONE_LINER}


def use_case_fm(**overrides):
    fm = {
        "id": "UC-DEMO-01",
        "type": "use-case",
        "title": "Fictional widget triage",
        "doc_status": "draft",
        "domain": "demo",
        "flagship": False,
        "otel_slots": ["llm"],
        "autonomy_ceiling": "recommend-with-approval",
        "placement_tier": ["regional"],
        "one_liner": UC_ONE_LINER,
        "platform_blueprints": ["PB-04"],
        "agent_school": [301],
        "depth": "entry",
        "card": dict(UC_CARD),
        "placement": {k: dict(v) for k, v in UC_PLACEMENT.items()},
        "adaptation": {**UC_ADAPTATION, "bring": [dict(b) for b in UC_ADAPTATION["bring"]]},
    }
    if overrides.get("flagship") is True and "depth" not in overrides:
        fm["depth"] = "recipe"  # a flagship is always a recipe (DP001)
    for k, v in overrides.items():
        if v is None:
            fm.pop(k, None)
        else:
            fm[k] = v
    return fm


def platform_fm(**overrides):
    fm = {
        "id": "PB-04",
        "type": "platform",
        "title": "Demo platform",
        "readiness_question": "What does it take?",
        "doc_status": "draft",
        "otel_slots": ["llm"],
        "placement_tier": ["core"],
        "one_liner": PB_ONE_LINER,
        "top_decisions": ["one"],
        "agent_school": [301],
    }
    fm.update(overrides)
    return fm


def use_case_sections():
    return {
        "At a glance": glance_table(UC_AT_A_GLANCE, UC_GLANCE_VALUES),
        "Problem and value": "One line about the problem.",
        "How it works": "1. Step one\n2. Step two",
        "What you need": "- A model slot\n- A platform blueprint",
        "Governance": "| Control | Owner |\n|---|---|\n| Approval | NOC |",
        "Sources": SOURCES_HEADER + "\n" + SOURCES_ROW,
        "Deploy and verify": "Link the how-to steps.",
        "Limitations": "- One limitation",
    }


def platform_sections():
    return {
        "At a glance": glance_table(PB_AT_A_GLANCE, PB_GLANCE_VALUES),
        "The operator question": "What does it take?",
        "Decisions you must make": "| Decision | Options |\n|---|---|\n| A | B |",
        "Reference design": "1. Step one",
        "Components": "| Component role | Red Hat product used |\n|---|---|\n| Serves X | Demo runtime |",
        "OTel slot guidance": "| Slot | Guidance |\n|---|---|\n| llm | x |",
        "Sources and acceptance": SOURCES_HEADER + "\n" + SOURCES_ROW,
        "Operating model": "| Role | Duty |\n|---|---|\n| SRE | run |",
        "Risks and limitations": "| Risk | Mitigation |\n|---|---|\n| R | M |",
        "Used by and next steps": "- Next step",
    }


def render(fm, sections, raw_fm=None):
    """Render front matter (dict or raw string) and ordered sections to markdown."""
    if raw_fm is not None:
        head = raw_fm
    elif fm is None:
        head = ""
    else:
        head = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n"
    parts = [head, "# Title\n"]
    items = sections.items() if isinstance(sections, dict) else sections
    for title, body in items:
        parts.append(f"\n## {title}\n\n{body}\n")
    return "".join(parts)


def make_doc(tmp_path, text, name="README.md", is_blueprint=True):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return parse_doc(p, text, display=name, is_blueprint=is_blueprint)


def ctx_for(tmp_path=None):
    ctx = load_context(config=FIXTURES / "config.yaml", today=FIXED_TODAY)
    if tmp_path is not None:
        ctx.repo_root = tmp_path.resolve()
    return ctx


def lint(tmp_path, text, **kw):
    doc = make_doc(tmp_path, text, **kw)
    return run_doc_checks(doc, ctx_for(tmp_path))


def codes(findings, *wanted):
    return [f.code for f in findings if not wanted or f.code in wanted]


# ---- FM001 ---------------------------------------------------------------


def test_valid_use_case_has_no_findings(tmp_path):
    assert lint(tmp_path, render(use_case_fm(), use_case_sections())) == []


def test_valid_platform_has_no_findings(tmp_path):
    assert lint(tmp_path, render(platform_fm(), platform_sections())) == []


def test_no_front_matter_yields_exactly_one_fm001(tmp_path):
    secs = use_case_sections()
    secs.pop("Governance")  # would be SC001 if structure checks ran
    findings = lint(tmp_path, render(None, secs))
    assert codes(findings) == ["FM001"]
    assert findings[0].line == 1


def test_unterminated_front_matter_is_fm001(tmp_path):
    findings = lint(tmp_path, render(None, use_case_sections(), raw_fm="---\nid: x\n"))
    assert codes(findings) == ["FM001"]


def test_yaml_error_is_fm001_with_line(tmp_path):
    raw = "---\nid: UC-DEMO-01\ntype: [unclosed\n---\n"
    findings = lint(tmp_path, render(None, use_case_sections(), raw_fm=raw))
    assert codes(findings) == ["FM001"]
    assert findings[0].line >= 3


def test_non_mapping_front_matter_is_fm001(tmp_path):
    findings = lint(tmp_path, render(None, use_case_sections(), raw_fm="---\n- a\n- b\n---\n"))
    assert codes(findings) == ["FM001"]


def test_docs_are_not_front_matter_checked(tmp_path):
    findings = lint(tmp_path, "# Plain doc\n\nNo front matter.\n", is_blueprint=False)
    assert findings == []


# ---- RF001 / FM002 ------------------------------------------------------


def test_missing_placement_tier_is_rf001(tmp_path):
    findings = lint(tmp_path, render(use_case_fm(placement_tier=None), use_case_sections()))
    rf = [f for f in findings if f.code == "RF001"]
    assert len(rf) == 1
    assert "placement_tier" in rf[0].message
    assert "FM002" not in codes(findings)


def test_invalid_autonomy_ceiling_is_rf001_on_key_line(tmp_path):
    text = render(use_case_fm(autonomy_ceiling="act-alone"), use_case_sections())
    findings = lint(tmp_path, text)
    rf = [f for f in findings if f.code == "RF001"]
    assert len(rf) == 1 and "autonomy_ceiling" in rf[0].message
    key_line = text.splitlines().index("autonomy_ceiling: act-alone") + 1
    assert rf[0].line == key_line


@pytest.mark.parametrize(
    "field, value",
    [("evidence_level", "E1"), ("model_readiness", "M2"), ("honest_one_liner", "Old one-liner field.")],
)
def test_retired_readiness_field_is_fm002(tmp_path, field, value):
    findings = lint(tmp_path, render(use_case_fm(**{field: value}), use_case_sections()))
    fm2 = [f for f in findings if f.code == "FM002"]
    assert len(fm2) == 1 and field in fm2[0].message
    assert "RF001" not in codes(findings)


@pytest.mark.parametrize("field", ["evidence_level", "model_readiness", "honest_one_liner"])
def test_retired_readiness_field_is_fm002_on_platform(tmp_path, field):
    findings = lint(tmp_path, render(platform_fm(**{field: "E1 value"}), platform_sections()))
    assert codes(findings) == ["FM002"]


def test_invalid_placement_tier_item_is_rf001(tmp_path):
    findings = lint(tmp_path, render(use_case_fm(placement_tier=["moon"]), use_case_sections()))
    assert codes(findings, "RF001") == ["RF001"]


def test_unknown_extra_key_is_fm002(tmp_path):
    findings = lint(tmp_path, render(use_case_fm(surprise="x"), use_case_sections()))
    fm2 = [f for f in findings if f.code == "FM002"]
    assert len(fm2) == 1 and "surprise" in fm2[0].message
    assert "RF001" not in codes(findings)


def test_missing_type_is_fm002_and_skips_structure(tmp_path):
    secs = use_case_sections()
    secs.pop("Governance")
    findings = lint(tmp_path, render(use_case_fm(type=None), secs))
    assert codes(findings) == ["FM002"]


def test_unknown_type_is_fm002_and_skips_structure(tmp_path):
    secs = use_case_sections()
    secs.pop("Governance")
    findings = lint(tmp_path, render(use_case_fm(type="howto"), secs))
    assert codes(findings) == ["FM002"]


# ---- DP001 ----------------------------------------------------------------


def test_flagship_with_depth_entry_is_dp001(tmp_path):
    findings = lint(tmp_path, render(use_case_fm(flagship=True, depth="entry"), use_case_sections()))
    assert codes(findings) == ["DP001"]
    assert "recipe" in findings[0].message


def test_non_flagship_recipe_passes(tmp_path):
    assert lint(tmp_path, render(use_case_fm(flagship=False, depth="recipe"), use_case_sections())) == []


def test_missing_depth_is_fm002(tmp_path):
    findings = lint(tmp_path, render(use_case_fm(depth=None), use_case_sections()))
    assert "FM002" in codes(findings) and any("depth" in f.message for f in findings)


# ---- AD001 ----------------------------------------------------------------

CLASSIFY_SLOTS = ["classification", "llm"]
CLASSIFY_PLACEMENT = {"regional": {"runs": ["classification", "llm-small"], "note": ""}}


def _item(mechanism, domains=("oss-bss",), item="Widget item"):
    return {"item": item, "domains": list(domains), "mechanism": mechanism}


def classify_fm(**adaptation):
    ad = {
        "rung": "head-retrain",
        "expertise": ["taxonomy", "golden-set"],
        "bring": [_item("classification-labels"), _item("skill-manifest")],
    }
    ad.update(adaptation)
    return use_case_fm(otel_slots=CLASSIFY_SLOTS, placement=CLASSIFY_PLACEMENT, adaptation=ad)


def ad001(tmp_path, fm):
    """The AD001 messages joined; every finding must be AD001."""
    findings = lint(tmp_path, render(fm, use_case_sections()))
    assert findings and set(codes(findings)) == {"AD001"}, [f"{f.code} {f.message}" for f in findings]
    return " | ".join(f.message for f in findings)


def test_classification_page_with_head_retrain_passes(tmp_path):
    assert lint(tmp_path, render(classify_fm(), use_case_sections())) == []


def test_bring_rules_skip_when_bring_is_absent(tmp_path):
    from tools.bplint.checks.frontmatter import _adaptation_messages

    ad = {"rung": "head-retrain", "expertise": ["taxonomy", "golden-set"]}
    fm = use_case_fm(otel_slots=CLASSIFY_SLOTS, placement=CLASSIFY_PLACEMENT, adaptation=ad)
    assert _adaptation_messages(fm) == []
    findings = lint(tmp_path, render(fm, use_case_sections()))
    assert codes(findings) == ["FM002"] and "bring" in findings[0].message  # the schema requires bring


def test_classification_slot_with_skills_is_ad001(tmp_path):
    assert "rung" in ad001(tmp_path, classify_fm(rung="skills"))


def test_head_retrain_without_classification_is_ad001(tmp_path):
    ad = dict(UC_ADAPTATION, rung="head-retrain")
    assert "rung" in ad001(tmp_path, use_case_fm(adaptation=ad))


def test_taxonomy_must_follow_classification(tmp_path):
    assert "taxonomy" in ad001(tmp_path, classify_fm(expertise=["golden-set"]))
    ad = dict(UC_ADAPTATION, expertise=["taxonomy", "golden-set", "tool-contracts"])
    assert "taxonomy" in ad001(tmp_path, use_case_fm(adaptation=ad))


def test_gate_labels_must_follow_decision(tmp_path):
    ad = dict(UC_ADAPTATION, expertise=["golden-set", "gate-labels", "tool-contracts"])
    assert "gate-labels" in ad001(tmp_path, use_case_fm(adaptation=ad))
    fm = use_case_fm(
        otel_slots=["llm", "decision"],
        placement={"regional": {"runs": ["llm-small", "decision"], "note": ""}},
    )
    assert "gate-labels" in ad001(tmp_path, fm)


def test_corpus_must_follow_embedding(tmp_path):
    ad = dict(UC_ADAPTATION, expertise=["golden-set", "tool-contracts", "corpus"])
    assert "corpus" in ad001(tmp_path, use_case_fm(adaptation=ad))
    fm = use_case_fm(
        otel_slots=["llm", "embedding"],
        placement={"regional": {"runs": ["llm-small", "embedding"], "note": ""}},
    )
    assert "corpus" in ad001(tmp_path, fm)


def test_golden_set_is_always_required(tmp_path):
    ad = dict(UC_ADAPTATION, expertise=["tool-contracts"])
    assert "golden-set" in ad001(tmp_path, use_case_fm(adaptation=ad))


def test_classification_page_needs_a_labels_item(tmp_path):
    msg = ad001(tmp_path, classify_fm(bring=[_item("skill-manifest")]))
    assert "classification-labels" in msg


def test_labels_item_needs_classification(tmp_path):
    ad = dict(UC_ADAPTATION, bring=UC_ADAPTATION["bring"] + [_item("classification-labels")])
    assert "classification-labels" in ad001(tmp_path, use_case_fm(adaptation=ad))


def test_rag_corpus_item_needs_embedding(tmp_path):
    ad = dict(UC_ADAPTATION, bring=UC_ADAPTATION["bring"] + [_item("rag-corpus")])
    assert "rag-corpus" in ad001(tmp_path, use_case_fm(adaptation=ad))


EMBED_SLOTS = ["llm", "embedding"]
EMBED_PLACEMENT = {"regional": {"runs": ["llm-small", "embedding"], "note": ""}}


def embed_fm(rung):
    ad = {
        "rung": rung,
        "expertise": ["golden-set", "tool-contracts", "corpus"],
        "bring": UC_ADAPTATION["bring"] + [_item("rag-corpus")],
    }
    return use_case_fm(otel_slots=EMBED_SLOTS, placement=EMBED_PLACEMENT, adaptation=ad)


def test_rung_names_retrieval_only_with_the_embedding_slot(tmp_path):
    # skills alone does no retrieval, so it cannot sit on a page with the embedding slot
    assert "retrieval" in ad001(tmp_path, embed_fm("skills"))
    assert lint(tmp_path, render(embed_fm("retrieval-and-skills"), use_case_sections())) == []
    assert lint(tmp_path, render(embed_fm("retrieval"), use_case_sections())) == []
    # a rung that names retrieval needs the embedding slot
    for rung in ("retrieval-and-skills", "retrieval"):
        assert "retrieval" in ad001(tmp_path, use_case_fm(adaptation=dict(UC_ADAPTATION, rung=rung)))


def test_tool_contracts_expertise_needs_a_tool_contract_item(tmp_path):
    ad = dict(UC_ADAPTATION, bring=[_item("skill-manifest")])
    assert "tool-contract" in ad001(tmp_path, use_case_fm(adaptation=ad))
    ad = dict(UC_ADAPTATION, expertise=["golden-set"])
    assert "tool-contract" in ad001(tmp_path, use_case_fm(adaptation=ad))


def test_lora_data_only_with_lora_if_gap(tmp_path):
    msg = ad001(tmp_path, classify_fm(bring=[_item("classification-labels"), _item("lora-data")]))
    assert "lora-data" in msg
    ok = classify_fm(rung="lora-if-gap", bring=[_item("classification-labels"), _item("lora-data")])
    assert lint(tmp_path, render(ok, use_case_sections())) == []


# ---- AS001 / AS002 --------------------------------------------------------


def _glance_with_courses(cell):
    secs = use_case_sections()
    secs["At a glance"] = glance_table(UC_AT_A_GLANCE, {**UC_GLANCE_VALUES, "Agent-school courses": cell})
    return secs


def test_empty_agent_school_without_sentence_is_as001(tmp_path):
    findings = lint(tmp_path, render(use_case_fm(agent_school=[]), _glance_with_courses("None")))
    assert codes(findings) == ["AS001"]
    assert AS001_SENTENCE in findings[0].message


def test_empty_agent_school_with_sentence_passes(tmp_path):
    cell = f"{AS001_SENTENCE}; see the [agent-school roadmap](https://example.com/RoadMap.md)"
    assert lint(tmp_path, render(use_case_fm(agent_school=[]), _glance_with_courses(cell))) == []


def test_unknown_agent_school_course_is_as002(tmp_path):
    findings = lint(tmp_path, render(use_case_fm(agent_school=[405]), use_case_sections()))
    assert codes(findings) == ["AS002"]
    assert "405" in findings[0].message


def test_known_agent_school_course_passes(tmp_path):
    assert lint(tmp_path, render(use_case_fm(agent_school=[401]), use_case_sections())) == []


@pytest.mark.parametrize("alias", [404])
def test_retired_agent_school_alias_is_as002(tmp_path, alias):
    """Retired ballot aliases (401 to 404 with old meanings) only pass when the number is a real course."""
    assert codes(lint(tmp_path, render(use_case_fm(agent_school=[alias]), use_case_sections()))) == ["AS002"]


def test_unknown_agent_school_course_on_platform_is_as002(tmp_path):
    findings = lint(tmp_path, render(platform_fm(agent_school=[999]), platform_sections()))
    assert codes(findings) == ["AS002"]


def test_courses_file_pinned():
    data = yaml.safe_load(COURSES_FILE.read_text(encoding="utf-8"))
    assert data["roadmap_commit"] == "30458bda61cdc1ea939ce7d1fe6b8d425ed2bbad"
    assert str(data["checked"]) == "2026-11-15"
    assert sorted(data["courses"]) == [101, 102, 103, 104, 201, 202, 203, 301, 302, 303, 304, 401, 402, 403]
    assert all(isinstance(t, str) and t.strip() for t in data["courses"].values())
