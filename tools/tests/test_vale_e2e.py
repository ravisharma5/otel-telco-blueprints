"""End-to-end Vale checks with the real .vale.ini.

`vale test` runs a rule without .vale.ini, so it cannot see TokenIgnores or
scopes. These tests feed sentences on stdin with `--ext=.md`, which makes Vale
apply the [*.md] section exactly as it does for repo prose.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from tools.tests.conftest import REPO_ROOT, vale_or_skip

TRACING = "Blueprints.OTelTracing"
STATUS = "Blueprints.InlineStatus"
UNEVIDENCED = "Blueprints.Unevidenced"


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


MUST_FLAG = [
    ("The OTel-Collector ships data.", TRACING, "OTel-Collector"),
    ("Install the OTel-SDK.", TRACING, "OTel-SDK"),
    ("Send OTel-traces upstream.", TRACING, "OTel-traces"),
    ("The OTel collector ships OTel traces over OTLP.", TRACING, "OTel collector"),
    ("The OTel collector ships OTel traces over OTLP.", TRACING, "OTel traces"),
    ("The OTel collector ships OTel traces over OTLP.", TRACING, "OTLP"),
    ("Wire the OTel metrics pipeline.", TRACING, None),
    ("The gateway reached general availability.", STATUS, "general availability"),
    ("The router is a Tech-Preview.", STATUS, "Tech-Preview"),
    ("The router is a Dev Preview.", STATUS, "Dev Preview"),
    ("It is a Developer-Preview.", STATUS, "Developer-Preview"),
    ("It is a Technology-Preview.", STATUS, "Technology-Preview"),
    ("The runtime is production-supported.", STATUS, "production-supported"),
    ("The scheduler is TP today.", STATUS, "TP"),
    ("The gateway is GA today.", STATUS, "GA"),
    ("The model is validated.", UNEVIDENCED, "validated"),
]

MUST_NOT_FLAG = [
    ("Our OTel agent traffic is high.", TRACING),
    ("OTel metrics on TeleQnA improved.", TRACING),
    ("Use TP=2 and DP 4.", STATUS),
    ("Run TP x2 with DP×4.", STATUS),
    ("Use TP-2 tensor parallelism.", STATUS),
    ("The Decision model is not validated on this engine.", UNEVIDENCED),
    ("It is not yet validated.", UNEVIDENCED),
    ("It was never validated.", UNEVIDENCED),
    ("This claim is operator-validated (E4).", UNEVIDENCED),
    ("Red Hat Validated Patterns use tiers.", UNEVIDENCED),
]

CHECKPOINTS = [
    "OTel-2.0-LLM-31B-IT serves answers.",
    "OTel-LLM-8.3B-Safety abstains.",
    "OTel-Embedding-8B indexes text.",
    "OTel-Reranker-4B scores pairs.",
    "OTel-2.0-Decision-26B-A4B-4bit gates actions.",
]


@pytest.mark.parametrize(("text", "check", "match"), MUST_FLAG)
def test_flags(text, check, match):
    hits = [a for a in _alerts(text) if a["Check"] == check]
    assert hits, f"{check} did not fire on: {text}"
    if match is not None:
        assert match in {a["Match"] for a in hits}


@pytest.mark.parametrize(("text", "check"), MUST_NOT_FLAG)
def test_does_not_flag(text, check):
    hits = [a for a in _alerts(text) if a["Check"] == check]
    assert hits == [], f"{check} fired on: {text} -> {[a['Match'] for a in hits]}"


@pytest.mark.parametrize("text", CHECKPOINTS)
def test_checkpoint_names_stay_silent(text):
    hits = [a for a in _alerts(text) if "OTel-" in a["Match"]]
    assert hits == [], [(a["Check"], a["Match"]) for a in hits]
