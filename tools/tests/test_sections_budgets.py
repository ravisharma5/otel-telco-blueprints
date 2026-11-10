"""Tests for SC001, SC002, AG001, and BG001."""

from __future__ import annotations

from tools.tests.test_frontmatter_checks import (
    PB_AT_A_GLANCE,
    PB_GLANCE_VALUES,
    UC_AT_A_GLANCE,
    UC_GLANCE_VALUES,
    codes,
    glance_table,
    lint,
    platform_fm,
    platform_sections,
    render,
    use_case_fm,
    use_case_sections,
)


def words(n):
    return " ".join(["word"] * n)


# ---- SC001 ---------------------------------------------------------------


def test_sections_in_order_no_sc001(tmp_path):
    assert codes(lint(tmp_path, render(use_case_fm(), use_case_sections())), "SC001") == []


def test_missing_section_is_sc001(tmp_path):
    secs = use_case_sections()
    secs.pop("Limitations")
    findings = [f for f in lint(tmp_path, render(use_case_fm(), secs)) if f.code == "SC001"]
    assert len(findings) == 1 and "Limitations" in findings[0].message


def test_swapped_sections_is_sc001(tmp_path):
    items = list(use_case_sections().items())
    items[2], items[3] = items[3], items[2]
    assert "SC001" in codes(lint(tmp_path, render(use_case_fm(), items)))


def test_first_h2_not_at_a_glance_is_sc001(tmp_path):
    items = list(use_case_sections().items())
    items[0], items[1] = items[1], items[0]
    findings = [f for f in lint(tmp_path, render(use_case_fm(), items)) if f.code == "SC001"]
    assert any("At a glance" in f.message for f in findings)


def test_unexpected_section_is_sc001(tmp_path):
    items = list(use_case_sections().items()) + [("Appendix", "Extra.")]
    findings = [f for f in lint(tmp_path, render(use_case_fm(), items)) if f.code == "SC001"]
    assert len(findings) == 1 and "Appendix" in findings[0].message


# ---- SC002 ---------------------------------------------------------------


def test_catalog_required_stub_is_sc002(tmp_path):
    secs = use_case_sections()
    secs["Governance"] = "_Stub: governance comes later._"
    findings = [f for f in lint(tmp_path, render(use_case_fm(), secs)) if f.code == "SC002"]
    assert len(findings) == 1 and "Governance" in findings[0].message


def test_catalog_optional_stub_is_allowed(tmp_path):
    secs = use_case_sections()
    secs["How it works"] = "_Stub: steps come later._"
    assert codes(lint(tmp_path, render(use_case_fm(), secs)), "SC002") == []


def test_flagship_any_stub_is_sc002(tmp_path):
    secs = use_case_sections()
    secs["How it works"] = "_Stub: steps come later._"
    assert codes(lint(tmp_path, render(use_case_fm(flagship=True), secs)), "SC002") == ["SC002"]


def test_platform_any_stub_is_sc002(tmp_path):
    secs = platform_sections()
    secs["Operating model"] = "_Stub: later._"
    assert codes(lint(tmp_path, render(platform_fm(), secs)), "SC002") == ["SC002"]


# ---- AG001 ---------------------------------------------------------------


def test_missing_at_a_glance_label_is_ag001(tmp_path):
    secs = use_case_sections()
    secs["At a glance"] = glance_table([x for x in UC_AT_A_GLANCE if x != "Placement tier"])
    findings = [f for f in lint(tmp_path, render(use_case_fm(), secs)) if f.code == "AG001"]
    assert len(findings) == 1 and "Placement tier" in findings[0].message


def test_extra_label_is_not_ag001_but_bg001(tmp_path):
    secs = use_case_sections()
    secs["At a glance"] = glance_table(UC_AT_A_GLANCE + ["Bonus row"])
    findings = lint(tmp_path, render(use_case_fm(), secs))
    assert "AG001" not in codes(findings)
    assert codes(findings, "BG001") == ["BG001"]


def test_at_a_glance_without_table_is_ag001(tmp_path):
    secs = use_case_sections()
    secs["At a glance"] = "No table here."
    assert "AG001" in codes(lint(tmp_path, render(use_case_fm(), secs)))


# ---- at-a-glance values carry no readiness codes -------------------------


def test_one_liner_values_are_not_compared_with_facets(tmp_path):
    """No readiness codes are left to compare, so any one-liner text passes."""
    secs = use_case_sections()
    secs["At a glance"] = glance_table(
        UC_AT_A_GLANCE, {**UC_GLANCE_VALUES, "One-liner": "Answers widget questions. Needs an LLM slot."}
    )
    assert lint(tmp_path, render(use_case_fm(), secs)) == []
    secs = platform_sections()
    secs["At a glance"] = glance_table(PB_AT_A_GLANCE, {**PB_GLANCE_VALUES, "One-liner": "Serves a slot."})
    assert lint(tmp_path, render(platform_fm(), secs)) == []


def test_missing_one_liner_row_is_ag001(tmp_path):
    secs = use_case_sections()
    labels = [x for x in UC_AT_A_GLANCE if x != "One-liner"]
    secs["At a glance"] = glance_table(labels, UC_GLANCE_VALUES)
    findings = lint(tmp_path, render(use_case_fm(), secs))
    assert codes(findings, "AG001") == ["AG001"]


def test_old_glance_labels_are_ag001(tmp_path):
    secs = use_case_sections()
    labels = ["Honest one-liner" if x == "One-liner" else x for x in UC_AT_A_GLANCE]
    secs["At a glance"] = glance_table(labels)
    findings = [f for f in lint(tmp_path, render(use_case_fm(), secs)) if f.code == "AG001"]
    assert len(findings) == 1 and "One-liner" in findings[0].message


# ---- BG001 ---------------------------------------------------------------


def test_at_a_glance_nine_rows_is_bg001(tmp_path):
    secs = use_case_sections()
    secs["At a glance"] = glance_table(UC_AT_A_GLANCE + ["Ninth"])
    findings = [f for f in lint(tmp_path, render(use_case_fm(), secs)) if f.code == "BG001"]
    assert len(findings) == 1 and "rows" in findings[0].message


def test_nine_steps_is_bg001(tmp_path):
    secs = use_case_sections()
    secs["How it works"] = "\n".join(f"{i}. step" for i in range(1, 10))
    findings = [f for f in lint(tmp_path, render(use_case_fm(), secs)) if f.code == "BG001"]
    assert len(findings) == 1 and "9 steps > budget 8" in findings[0].message


def test_seven_limitation_bullets_is_bg001(tmp_path):
    secs = use_case_sections()
    secs["Limitations"] = "\n".join(f"- limit {i}" for i in range(7))
    assert codes(lint(tmp_path, render(use_case_fm(), secs)), "BG001") == ["BG001"]


def test_six_problem_lines_is_bg001(tmp_path):
    secs = use_case_sections()
    secs["Problem and value"] = "\n".join(f"Line {i} of the problem." for i in range(6))
    findings = [f for f in lint(tmp_path, render(use_case_fm(), secs)) if f.code == "BG001"]
    assert len(findings) == 1 and "lines" in findings[0].message


def test_two_tables_over_budget_is_bg001(tmp_path):
    secs = use_case_sections()
    tbl = "| Control | Owner |\n|---|---|\n| Approval | NOC |"
    secs["Governance"] = tbl + "\n\nBetween.\n\n" + tbl
    findings = [f for f in lint(tmp_path, render(use_case_fm(), secs)) if f.code == "BG001"]
    assert len(findings) == 1 and "tables" in findings[0].message


def test_unit_without_budget_is_unlimited(tmp_path):
    secs = use_case_sections()
    # Governance budget only limits tables; steps and bullets are free
    secs["Governance"] += "\n\n" + "\n".join(f"{i}. step" for i in range(1, 15))
    assert codes(lint(tmp_path, render(use_case_fm(), secs)), "BG001") == []


def test_catalog_over_page_words_is_bg001(tmp_path):
    secs = use_case_sections()
    secs["Problem and value"] = words(460)
    findings = [f for f in lint(tmp_path, render(use_case_fm(), secs)) if f.code == "BG001"]
    assert len(findings) == 1 and "page_words" in findings[0].message


def test_flagship_thousand_words_is_within_budget(tmp_path):
    secs = use_case_sections()
    secs["Problem and value"] = words(1000)
    assert codes(lint(tmp_path, render(use_case_fm(flagship=True), secs)), "BG001") == []
