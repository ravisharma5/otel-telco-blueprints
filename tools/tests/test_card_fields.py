"""Card fields and the placement map in use-case front matter.

The card is the director-facing summary the explorer shows on the home page.
The placement map says which slot roles run at each tier. Both are optional
in the schema; bplint explains word-limit failures and checks the placement
map against otel_slots and placement_tier.
"""

from __future__ import annotations

import copy

import pytest

from tools.bplint.schema import load_validators
from tools.tests.conftest import FIXTURES, REPO_ROOT, run_bplint
from tools.tests.test_frontmatter_checks import lint, render, use_case_fm, use_case_sections

VALIDATOR = load_validators(REPO_ROOT / "schemas")["use-case"]

CARD = {
    "goal": "Cut time to first triage",
    "summary": "Drafts a triage label for each alarm and an engineer approves it.",
    "outcome": "Engineers spend less time sorting alarms by hand.",
    "audience": "NOC engineers and their business owner",
    "measures": ["Time to first triage", "Labels approved unchanged"],
    "risk": "A wrong label slows the fix until an engineer catches it.",
}

LIMITS = {"goal": 8, "summary": 25, "outcome": 20, "audience": 12, "risk": 15, "measures": 6}


def words(n):
    return " ".join(f"w{i}" for i in range(n))


def card_with(field, value):
    card = copy.deepcopy(CARD)
    if field == "measures":
        card["measures"] = [value]
    else:
        card[field] = value
    return card


def schema_errors(fm):
    return list(VALIDATOR.iter_errors(fm))


def errors_under(fm, top):
    return [e for e in schema_errors(fm) if e.absolute_path and e.absolute_path[0] == top]


# ---- card schema ----------------------------------------------------------


def test_full_card_validates():
    assert schema_errors(use_case_fm(card=CARD)) == []


@pytest.mark.parametrize("field,limit", sorted(LIMITS.items()))
def test_word_limits(field, limit):
    at_limit = use_case_fm(card=card_with(field, words(limit)))
    assert errors_under(at_limit, "card") == []

    padded = use_case_fm(card=card_with(field, "  " + words(limit) + "  "))
    assert errors_under(padded, "card") == []

    over = use_case_fm(card=card_with(field, words(limit + 1)))
    errs = errors_under(over, "card")
    assert [e.validator for e in errs] == ["pattern"]

    padded_over = use_case_fm(card=card_with(field, "  " + words(limit + 1) + "  "))
    assert [e.validator for e in errors_under(padded_over, "card")] == ["pattern"]


@pytest.mark.parametrize(
    "measures",
    [[], ["one", "two", "three", "four"], ["same measure", "same measure"]],
    ids=["zero", "four", "duplicate"],
)
def test_measures_bounds(measures):
    card = dict(CARD, measures=measures)
    assert errors_under(use_case_fm(card=card), "card")


@pytest.mark.parametrize("field", sorted(CARD))
def test_card_requires_all_fields(field):
    card = {k: v for k, v in CARD.items() if k != field}
    errs = errors_under(use_case_fm(card=card), "card")
    assert [e.validator for e in errs] == ["required"]


def test_card_rejects_unknown_keys():
    errs = errors_under(use_case_fm(card=dict(CARD, status="ready")), "card")
    assert [e.validator for e in errs] == ["additionalProperties"]


# ---- bplint word-count message -------------------------------------------


def test_bplint_word_count_message(tmp_path):
    fm = use_case_fm(card=card_with("summary", words(31)))
    findings = lint(tmp_path, render(fm, use_case_sections()))
    assert [(f.code, f.message) for f in findings] == [
        ("FM002", "$.card.summary: 31 words; the limit is 25")
    ]


def test_bplint_word_count_message_for_a_measure(tmp_path):
    fm = use_case_fm(card=card_with("measures", words(7)))
    findings = lint(tmp_path, render(fm, use_case_sections()))
    assert [(f.code, f.message) for f in findings] == [
        ("FM002", "$.card.measures[0]: 7 words; the limit is 6")
    ]


def test_bplint_word_count_message_for_a_placement_note(tmp_path):
    placement = {"regional": {"runs": ["llm-small"], "note": words(16)}}
    fm = use_case_fm(placement=placement)
    findings = lint(tmp_path, render(fm, use_case_sections()))
    assert [(f.code, f.message) for f in findings] == [
        ("FM002", "$.placement.regional.note: 16 words; the limit is 15")
    ]


def test_other_card_errors_keep_their_messages(tmp_path):
    card = {k: v for k, v in CARD.items() if k != "risk"}
    findings = lint(tmp_path, render(use_case_fm(card=card), use_case_sections()))
    assert [f.code for f in findings] == ["FM002"]
    assert "'risk' is a required property" in findings[0].message
    assert "the limit is" not in findings[0].message


# ---- placement schema ------------------------------------------------------


GOOD_PLACEMENT = {"regional": {"runs": ["llm-small"], "note": ""}}


def test_placement_schema_accepts_a_good_map():
    assert errors_under(use_case_fm(placement=GOOD_PLACEMENT), "placement") == []


@pytest.mark.parametrize(
    "placement",
    [
        {"metro": {"runs": ["llm-small"], "note": ""}},
        {"regional": {"runs": ["llm"], "note": ""}},
        {"regional": {"runs": ["gpu"], "note": ""}},
        {"regional": {"runs": ["llm-small"]}},
        {"regional": {"runs": ["llm-small", "llm-small"], "note": ""}},
        {"regional": {"runs": ["llm-small"], "note": "", "extra": 1}},
        {},
    ],
    ids=["unknown-tier", "bare-llm-role", "unknown-role", "missing-note", "duplicate-role", "extra-key", "empty"],
)
def test_placement_schema(placement):
    assert errors_under(use_case_fm(placement=placement), "placement")


# ---- placement consistency (bplint) ---------------------------------------


def placement_findings(tmp_path, **fm):
    findings = lint(tmp_path, render(use_case_fm(**fm), use_case_sections()))
    return [f for f in findings if f.code == "FM002" and "placement" in f.message]


def test_placement_consistency(tmp_path):
    consistent = placement_findings(
        tmp_path,
        otel_slots=["llm", "safety"],
        placement_tier=["regional", "core"],
        placement={
            "far-edge": {"runs": [], "note": "Too little memory for the 31B."},
            "regional": {"runs": ["llm-small", "safety"], "note": ""},
            "core": {"runs": ["llm-large"], "note": ""},
        },
    )
    assert consistent == []


def test_placement_tiers_must_match_placement_tier(tmp_path):
    found = placement_findings(
        tmp_path,
        placement_tier=["regional"],
        placement={
            "regional": {"runs": ["llm-small"], "note": ""},
            "core": {"runs": ["llm-large"], "note": ""},
        },
    )
    assert len(found) == 1 and "core" in found[0].message and "placement_tier" in found[0].message


def test_placement_tier_without_runs_is_flagged(tmp_path):
    found = placement_findings(
        tmp_path,
        placement_tier=["regional", "core"],
        placement={"regional": {"runs": ["llm-small"], "note": ""}},
    )
    assert len(found) == 1 and "core" in found[0].message


def test_placement_role_needs_its_slot(tmp_path):
    found = placement_findings(
        tmp_path,
        otel_slots=["llm"],
        placement={"regional": {"runs": ["llm-small", "safety"], "note": ""}},
    )
    assert len(found) == 1 and "safety" in found[0].message and "otel_slots" in found[0].message


def test_every_slot_is_placed(tmp_path):
    found = placement_findings(
        tmp_path,
        otel_slots=["llm", "safety"],
        placement={"regional": {"runs": ["llm-small"], "note": ""}},
    )
    assert len(found) == 1 and "safety" in found[0].message


def test_empty_tier_needs_a_note(tmp_path):
    found = placement_findings(
        tmp_path,
        placement={
            "far-edge": {"runs": [], "note": ""},
            "regional": {"runs": ["llm-small"], "note": ""},
        },
    )
    assert len(found) == 1 and "far-edge" in found[0].message and "note" in found[0].message


def test_placement_finding_points_at_the_placement_line(tmp_path):
    text = render(
        use_case_fm(otel_slots=["llm", "safety"], placement=GOOD_PLACEMENT), use_case_sections()
    )
    findings = lint(tmp_path, text)
    fm_lines = text.split("---\n")[1].splitlines()
    expected = next(i for i, ln in enumerate(fm_lines) if ln.startswith("placement:")) + 2
    assert [f.line for f in findings if f.code == "FM002"] == [expected]


# ---- optional ---------------------------------------------------------------


def test_card_and_placement_optional(tmp_path):
    fixture = FIXTURES / "valid/use-case/README.md"
    text = fixture.read_text(encoding="utf-8")
    assert "\ncard:" not in text and "\nplacement:" not in text
    rc, findings = run_bplint(fixture)
    assert (rc, findings) == (0, [])
    assert lint(tmp_path, render(use_case_fm(), use_case_sections())) == []
    assert schema_errors(use_case_fm()) == []
