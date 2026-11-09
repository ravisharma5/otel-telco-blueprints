"""Vale catches "OTel" used for OpenTelemetry tracing.

bplint finds nothing in the otel-tracing fixture (its expected.txt is empty);
the Blueprints.OTelTracing Vale rule is what reports it. Google-style alerts may
appear on both files; they are not calibrated yet, so only Blueprints.*
alerts are asserted here.
"""

from __future__ import annotations

import json
import subprocess

from tools.tests.conftest import REPO_ROOT, vale_or_skip

TRACING = "tools/tests/fixtures/broken/otel-tracing/README.md"
VALID = "tools/tests/fixtures/valid/use-case/README.md"


def _alerts(vale, rel):
    proc = subprocess.run(
        [vale, "--config", ".vale.ini", "--output=JSON", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout or "{}")
    return proc.returncode, [a for alerts in data.values() for a in alerts]


def test_vale_flags_otel_tracing_fixture():
    vale = vale_or_skip()
    rc, alerts = _alerts(vale, TRACING)
    assert rc == 1
    matches = {a["Match"] for a in alerts if a["Check"] == "Blueprints.OTelTracing"}
    assert {"OTel traces", "OTel collector"} <= matches


def test_vale_valid_fixture_has_no_blueprints_alerts():
    vale = vale_or_skip()
    _, alerts = _alerts(vale, VALID)
    assert [a for a in alerts if a["Check"].startswith("Blueprints.")] == []
