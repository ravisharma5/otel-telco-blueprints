"""Open source framing: components are replaceable reference choices and blueprints make no product support claims."""

from __future__ import annotations

import json
import re
import subprocess

import pytest

from tools.tests.conftest import FIXTURES, REPO_ROOT, run_bplint, vale_or_skip

CHECK = "Blueprints.InlineStatus"
STATUS_CLAIM = FIXTURES / "broken/status-claim/README.md"
STANDARD_LINE = (
    "Any component can be replaced. "
    "The Red Hat products named here show one way to build this design."
)
REMOVED_PATHS = [
    "architecture/support" + "-status.yaml",
    "architecture/support" + "-status.md",
    "schemas/support" + "-status.schema.json",
    "tools/render_support" + "_status.py",
    "tools/bplint/checks/register.py",
    "tools/tests/fixtures/register.yaml",
]
LEGACY_FIELDS = ("critical_path_components", "status_verified_on")
COMMON_DEFS = {
    "autonomy_ceiling",
    "otel_slot",
    "slot_role",
    "placement_tier",
    "doc_status",
    "date",
    "agent_school_course",
}
PROSE_GLOBS = ["README.md", "framework/*.md", "templates/*.md", "platform/**/*.md", "catalog/**/*.md"]


def _inline_status_alerts(vale, *paths):
    proc = subprocess.run(
        [vale, "--config", ".vale.ini", "--output=JSON", *map(str, paths)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout or "{}")
    alerts = [a for file_alerts in data.values() for a in file_alerts if a["Check"] == CHECK]
    return proc.returncode, alerts


def test_vale_flags_product_support_claims_in_fixture():
    vale = vale_or_skip()
    rc, alerts = _inline_status_alerts(vale, STATUS_CLAIM.relative_to(REPO_ROOT))
    assert rc == 1
    assert all(a["Severity"] == "error" for a in alerts)
    matches = {a["Match"] for a in alerts}
    assert {"generally available", "Technology Preview", "GA", "TP"} <= matches


def test_vale_allows_parallelism_hardware_and_metric_terms(tmp_path):
    vale = vale_or_skip()
    doc = tmp_path / "negative.md"
    doc.write_text(
        "# Negative cases\n\n"
        "Run the 31B model with TP-2 tensor parallelism.\n\n"
        "FP8 is not supported on A100 GPUs.\n\n"
        "Watch TPOT and GAIE metrics.\n\n"
        "A community of operators reviews this.\n"
    )
    _, alerts = _inline_status_alerts(vale, doc)
    assert alerts == []


def test_bplint_rejects_legacy_register_field_as_fm002():
    rc, findings = run_bplint(STATUS_CLAIM)
    assert [f["code"] for f in findings] == ["FM002"]
    assert rc == 1


def test_templates_and_valid_fixtures_make_no_product_support_claim():
    vale = vale_or_skip()
    paths = [
        "templates/platform-blueprint.md",
        "templates/use-case-blueprint.md",
        "tools/tests/fixtures/valid/use-case/README.md",
        "tools/tests/fixtures/valid/platform/README.md",
    ]
    _, alerts = _inline_status_alerts(vale, *paths)
    assert alerts == []


def test_templates_carry_the_component_convention():
    platform = (REPO_ROOT / "templates/platform-blueprint.md").read_text()
    use_case = (REPO_ROOT / "templates/use-case-blueprint.md").read_text()
    assert "| Component role | Red Hat product used |" in platform
    for text in (platform, use_case):
        assert STANDARD_LINE in text
        assert "Weakest component status" not in text
        assert not re.search(r"^\|.*\bSupport status\b.*\|$", text, re.M)


def test_register_machinery_and_legacy_schema_fields_are_gone():
    for rel in REMOVED_PATHS:
        assert not (REPO_ROOT / rel).exists(), rel
    for name in ("use-case.schema.json", "platform.schema.json"):
        props = json.loads((REPO_ROOT / "schemas" / name).read_text())["properties"]
        for field in LEGACY_FIELDS:
            assert field not in props, (name, field)
    common = json.loads((REPO_ROOT / "schemas/common.schema.json").read_text())
    assert set(common["$defs"]) == COMMON_DEFS


def test_readiness_machinery_is_gone():
    """Blueprints are recipes: no readiness levels, headline rule, or validation table."""
    common = json.loads((REPO_ROOT / "schemas/common.schema.json").read_text())
    assert not {"e_level", "m_level"} & set(common["$defs"])
    assert "x-claim-term-map" not in common
    for name in ("use-case.schema.json", "platform.schema.json"):
        schema = json.loads((REPO_ROOT / "schemas" / name).read_text())
        for field in ("evidence_level", "model_readiness", "honest_one_liner"):
            assert field not in schema["properties"], (name, field)
            assert field not in schema["required"], (name, field)
    assert not (REPO_ROOT / "schemas/validation-table.yaml").exists()
    assert "validation_section" not in (REPO_ROOT / "tools/bplint/budgets.yaml").read_text()
    retired = re.compile(r"vt_spec|AG002|VT003|VT005|VT006")
    for path in sorted((REPO_ROOT / "tools/bplint").rglob("*")):
        if path.is_file() and path.suffix in (".py", ".yaml"):
            assert not retired.search(path.read_text()), path.relative_to(REPO_ROOT).as_posix()


def _prose_docs():
    seen = set()
    for pattern in PROSE_GLOBS:
        for p in sorted(REPO_ROOT.glob(pattern)):
            if p.is_file() and p not in seen:
                seen.add(p)
                yield p


@pytest.mark.parametrize("path", list(_prose_docs()), ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_vale_exceptions_state_a_reason(path):
    lines = path.read_text().splitlines()
    off = f"vale {CHECK} = NO"
    on = f"vale {CHECK} = YES"
    for i, line in enumerate(lines):
        if off not in line:
            continue
        prev = next((ln.strip() for ln in reversed(lines[:i]) if ln.strip()), "")
        assert prev.startswith("<!-- vale-exception:"), f"line {i + 1}: exception has no reason comment"
        reason = prev.removeprefix("<!-- vale-exception:").removesuffix("-->").strip()
        assert reason, f"line {i + 1}: exception reason is empty"
        assert any(on in ln for ln in lines[i + 1 :]), f"line {i + 1}: exception is never closed"
