"""Permanent regression tests for critical linter bypasses found in code review.

Each test reproduces the exact case the review confirmed and asserts that the
linter (bplint or Vale) now rejects it.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from tools.bplint.cli import run_doc_checks
from tools.bplint.markdown import parse_doc
from tools.tests.conftest import FIXTURES, REPO_ROOT, vale_or_skip
from tools.tests.test_frontmatter_checks import ctx_for

VALID_PLATFORM = FIXTURES / "valid/platform"
ROW1 = (
    "| 1 | Demo runtime answers within 200 ms at p95 | demo-runtime | yes | — | — "
    "| spec written | E1 | [spec](evidence/eval-spec.md) | — | 2026-11-07 | — |"
)
ROW2 = (
    "| 2 | Demo runtime handles 100 requests per second | demo-runtime | no "
    "| vendor says 100 rps | — | — | E0 | [notes](https://example.invalid/demo-runtime) | — | 2026-11-07 | — |"
)


def _copy_platform(tmp_path):
    dest = tmp_path / "platform"
    shutil.copytree(VALID_PLATFORM, dest)
    readme = dest / "README.md"
    text = readme.read_text(encoding="utf-8")
    assert ROW1 in text and ROW2 in text, "valid platform fixture changed; update the row literals"
    return readme, text


def _lint(tmp_path, readme, text):
    readme.write_text(text, encoding="utf-8")
    doc = parse_doc(readme, text, display="platform/README.md", is_blueprint=True)
    return run_doc_checks(doc, ctx_for(tmp_path))


def _codes(findings, code):
    return [f for f in findings if f.code == code]


def test_cr01_load_bearing_typo_is_rejected(tmp_path):
    """Row 2 (E0) with Load-bearing 'Yes (core)' must not drop out of the minimum."""
    readme, text = _copy_platform(tmp_path)
    text = text.replace(ROW2, ROW2.replace("| demo-runtime | no |", "| demo-runtime | Yes (core) |"))
    findings = _lint(tmp_path, readme, text)
    assert _codes(findings, "VT007"), findings
    assert any(
        "headline E-level is E0" in f.message and "front matter says E1" in f.message
        for f in _codes(findings, "VT003")
    ), findings


def test_cr02_self_evidence_is_rejected(tmp_path):
    """An E4 claim linking the blueprint itself, or a non-evidence repo file, must fail."""
    readme, text = _copy_platform(tmp_path)
    text = text.replace('evidence_level: "E1"', 'evidence_level: "E4"')
    self_row = (
        ROW1.replace("| E1 |", "| E4 |")
        .replace("[spec](evidence/eval-spec.md)", "[self](README.md)")
        .replace("| 2026-11-07 | — |", "| 2026-11-07 | r1 |")
    )
    findings = _lint(tmp_path, readme, text.replace(ROW1, self_row))
    assert any("cannot be the blueprint itself" in f.message for f in _codes(findings, "VT004")), findings

    (tmp_path / "LICENSE").write_text("license text\n", encoding="utf-8")
    license_row = self_row.replace("[self](README.md)", "[license](../LICENSE)")
    findings = _lint(tmp_path, readme, text.replace(ROW1, license_row))
    assert any("evidence/" in f.message for f in _codes(findings, "VT004")), findings


def _alerts(text):
    vale = vale_or_skip()
    proc = subprocess.run(
        [vale, "--config", ".vale.ini", "--ext=.md", "--output=JSON"],
        cwd=REPO_ROOT,
        input=text + "\n",
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), proc.stderr
    data = json.loads(proc.stdout or "{}")
    return [a for alerts in data.values() for a in alerts]


def test_cr03_hyphenated_otel_tracing_is_flagged():
    """TokenIgnores must not hide hyphenated OTel tracing terms."""
    alerts = _alerts("The OTel-Collector ships data.")
    assert any(a["Check"] == "Blueprints.OTelTracing" and a["Match"] == "OTel-Collector" for a in alerts), alerts
    alerts = _alerts("OTel-2.0-LLM-31B-IT serves answers.")
    assert not any("OTel-" in a.get("Match", "") for a in alerts), alerts


def test_cr04_status_variants_are_flagged():
    """InlineStatus must catch common product-status wording variants."""
    for sentence in (
        "The gateway reached general availability.",
        "The router is a Tech-Preview.",
        "The router is a Dev Preview.",
        "It is a Developer-Preview.",
        "It is a Technology-Preview.",
        "The runtime is production-supported.",
    ):
        alerts = _alerts(sentence)
        assert any(a["Check"] == "Blueprints.InlineStatus" for a in alerts), (sentence, alerts)
