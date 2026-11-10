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
from tools.tests.conftest import FIXTURES, FIXED_TODAY

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
    }
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
