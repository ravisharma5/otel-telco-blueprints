"""CI workflow hardening: pinned Vale download, vendored style, least-privilege token.

The workflow must pin Vale by a SHA-256 it does not fetch from the release, install a
pinned uv, install exactly the locked dependency set, and keep the safe trigger and
read-only token.
"""

from __future__ import annotations

import re

import yaml

from tools.tests.conftest import REPO_ROOT

WORKFLOW_PATH = REPO_ROOT / ".github/workflows/lint.yml"
# The uv version that produced uv.lock (`uv --version` at the time of pinning).
UV_VERSION = "0.9.28"

WORKFLOW = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
STEPS = WORKFLOW["jobs"]["lint"]["steps"]


def _triggers():
    # PyYAML (YAML 1.1) parses the bare key `on` as boolean True.
    return WORKFLOW.get("on", WORKFLOW.get(True))


def _run_steps():
    return [s.get("run", "") for s in STEPS]


def _vale_step():
    matches = [s for s in STEPS if "vale" in s.get("name", "").lower()]
    assert len(matches) == 1, "expected exactly one Vale install step"
    return matches[0]


def test_setup_uv_pins_exact_local_version():
    uv_steps = [s for s in STEPS if s.get("uses", "").startswith("astral-sh/setup-uv@")]
    assert len(uv_steps) == 1
    version = str(uv_steps[0].get("with", {}).get("version", ""))
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), version
    assert version == UV_VERSION


def test_uv_sync_is_locked():
    assert any("uv sync" in r and "--locked" in r for r in _run_steps())


def test_vale_verified_against_hardcoded_sha256():
    step = _vale_step()
    env = {**WORKFLOW["jobs"]["lint"].get("env", {}), **step.get("env", {})}
    text = step["run"] + "\n" + "\n".join(str(v) for v in env.values())
    assert re.search(r"\b[0-9a-f]{64}\b", text), "no 64-hex SHA-256 literal"
    assert "sha256sum -c" in step["run"]
    assert "checksums.txt" not in step["run"]
    assert "checksums.txt" not in WORKFLOW_PATH.read_text(encoding="utf-8")


def test_trigger_is_pull_request_not_target():
    triggers = _triggers()
    assert "pull_request" in triggers
    assert "pull_request_target" not in triggers


def test_permissions_read_only():
    assert WORKFLOW["permissions"] == {"contents": "read"}


def test_last_step_runs_make_ci():
    assert STEPS[-1].get("run", "").strip() == "make ci"


def test_no_vale_sync():
    assert not any("vale sync" in r for r in _run_steps())
