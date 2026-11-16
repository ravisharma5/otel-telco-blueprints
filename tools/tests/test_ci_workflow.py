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


# ---------- Node toolchain for the explorer ----------

SETUP_NODE = "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1"
SHA_PIN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.\-/]+@[0-9a-f]{40}")
MAKEFILE = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
# No install script was needed (npm ci + astro build pass with ignore-scripts=true),
# so neither CI nor the Makefile may re-enable scripts.
SCRIPT_ENABLERS = re.compile(
    r"--ignore-scripts=false|ignore-scripts\s+false|npm config set ignore-scripts|npm rebuild"
)


def _makefile_recipes():
    return [line.strip() for line in MAKEFILE.splitlines() if line.startswith("\t")]


def test_setup_node_pinned():
    steps = [s for s in STEPS if s.get("uses", "").startswith("actions/setup-node@")]
    assert len(steps) == 1
    assert steps[0]["uses"] == SETUP_NODE
    assert SHA_PIN.fullmatch(steps[0]["uses"])
    assert steps[0]["with"]["node-version-file"] == "explorer/.node-version"
    assert steps[0]["with"]["package-manager-cache"] is False


def test_all_actions_sha_pinned():
    uses = [s["uses"] for s in STEPS if "uses" in s]
    assert uses and all(SHA_PIN.fullmatch(u) for u in uses)


def test_npm_ci_only():
    runs = _run_steps()
    assert any("npm ci --prefix explorer" in r for r in runs)
    assert not any("npm install" in r for r in runs)
    assert not [line for line in _makefile_recipes() if "npm install" in line]


def test_scripts_stay_blocked():
    assert not [r for r in _run_steps() if SCRIPT_ENABLERS.search(r)]
    assert not [line for line in _makefile_recipes() if SCRIPT_ENABLERS.search(line)]


def test_astro_telemetry_disabled():
    env = WORKFLOW["jobs"]["lint"].get("env", {})
    assert env.get("ASTRO_TELEMETRY_DISABLED") == "1"


def test_makefile_telemetry():
    astro_lines = [line for line in _makefile_recipes() if re.search(r"\bastro\b", line)]
    assert astro_lines, "no Makefile recipe runs astro"
    assert all("ASTRO_TELEMETRY_DISABLED=1" in line for line in astro_lines)


def test_makefile_ci_order():
    assert re.search(r"(?m)^ci: test test-vale lint site test-site$", MAKEFILE)
    assert re.search(r"(?m)^explorer-deps:\n\tnpm ci --prefix explorer$", MAKEFILE)
    # test-site builds first through its prerequisite, so make -j never reads a stale build.
    assert re.search(r"(?m)^test-site: site\n\tuv run pytest -q -m site_output$", MAKEFILE)
    doc_dirs = re.search(r"(?m)^DOC_DIRS := (.*)$", MAKEFILE).group(1).split()
    assert "explorer/src/content" in doc_dirs


def test_workflows_checkout_without_credentials():
    """No checkout leaves the token in the workspace for later steps to read."""
    checkouts = [st for st in STEPS if str(st.get("uses", "")).startswith("actions/checkout@")]
    assert checkouts
    for step in checkouts:
        assert (step.get("with") or {}).get("persist-credentials") is False, step


def test_no_stale_pin_comment():
    assert "pin actions by commit sha" not in WORKFLOW_PATH.read_text(encoding="utf-8").lower()
