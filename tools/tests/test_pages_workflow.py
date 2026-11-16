"""GitHub Pages workflow hardening: deploy gated by a repo variable, no PR triggers, pinned actions.

pages.yml must pin every action by a 40-hex commit SHA, keep a read-only workflow token,
grant pages/id-token write only to the deploy job, trigger only on push to main and manual
dispatch, and stay inert (build-only) until PAGES_ENABLED is set on the public repo.
"""

from __future__ import annotations

import copy
import re

import yaml

from tools.tests.conftest import REPO_ROOT

WORKFLOW_PATH = REPO_ROOT / ".github/workflows/pages.yml"
# The uv version that produced uv.lock; must match lint.yml.
UV_VERSION = "0.9.28"
SHA_PIN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.\-/]+@[0-9a-f]{40}")
GUARD_PARTS = (
    "vars.PAGES_ENABLED == 'true'",
    "github.event.repository.visibility == 'public'",
)

WORKFLOW = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _triggers(workflow=WORKFLOW):
    # PyYAML (YAML 1.1) parses the bare key `on` as boolean True.
    return workflow.get("on", workflow.get(True))


def _all_steps(workflow=WORKFLOW):
    return [s for job in workflow["jobs"].values() for s in job.get("steps", [])]


def _uses_values(workflow=WORKFLOW):
    return [s["uses"] for s in _all_steps(workflow) if "uses" in s]


def _unpinned(workflow=WORKFLOW):
    return [u for u in _uses_values(workflow) if not SHA_PIN.fullmatch(u)]


def _upload_step(workflow=WORKFLOW):
    matches = [
        s
        for s in workflow["jobs"]["build"]["steps"]
        if s.get("uses", "").startswith("actions/upload-pages-artifact@")
    ]
    assert len(matches) == 1, "expected exactly one upload-pages-artifact step"
    return matches[0]


def _guarded(expr) -> bool:
    return isinstance(expr, str) and all(part in expr for part in GUARD_PARTS)


def test_all_actions_sha_pinned():
    assert _uses_values(), "no actions found"
    assert _unpinned() == []


def test_sha_pin_check_bites():
    # The regex must reject tag pins, and a mutated copy must be flagged.
    assert not SHA_PIN.fullmatch("actions/checkout@v7")
    assert not SHA_PIN.fullmatch("actions/checkout@v7.0.1")
    mutated = copy.deepcopy(WORKFLOW)
    mutated["jobs"]["build"]["steps"][0]["uses"] = "actions/checkout@v7"
    assert _unpinned(mutated) == ["actions/checkout@v7"]


def test_workflow_permissions_read_only():
    assert WORKFLOW["permissions"] == {"contents": "read"}


def test_write_permissions_only_on_deploy():
    build_perms = WORKFLOW["jobs"]["build"].get("permissions")
    # Absent means the job inherits the read-only workflow token.
    assert build_perms is None or (
        isinstance(build_perms, dict) and "write" not in build_perms.values()
    )
    assert WORKFLOW["jobs"]["deploy"]["permissions"] == {
        "pages": "write",
        "id-token": "write",
    }


def test_deploy_guarded():
    assert _guarded(WORKFLOW["jobs"]["deploy"].get("if"))
    assert _guarded(_upload_step().get("if"))


def test_guard_check_bites():
    mutated = copy.deepcopy(WORKFLOW)
    mutated["jobs"]["deploy"]["if"] = "vars.PAGES_ENABLED == 'true'"
    assert not _guarded(mutated["jobs"]["deploy"]["if"])
    del _upload_step(mutated)["if"]
    assert not _guarded(_upload_step(mutated).get("if"))


def test_triggers():
    triggers = _triggers()
    assert set(triggers) == {"push", "workflow_dispatch"}
    assert triggers["push"] == {"branches": ["main"]}
    assert "pull_request" not in triggers
    assert "pull_request_target" not in triggers


def test_build_uses_locked_sync_and_make_site():
    steps = WORKFLOW["jobs"]["build"]["steps"]
    runs = [s.get("run", "").strip() for s in steps]
    assert any("uv sync" in r and "--locked" in r for r in runs)
    # make test-site builds the site (its prerequisite) and runs the built-output
    # checks; both test runs come before the upload so a failure stops the deploy.
    assert "make test" in runs and "make test-site" in runs
    upload = next(i for i, s in enumerate(steps) if s.get("uses", "").startswith("actions/upload-pages-artifact@"))
    assert runs.index("make test") < upload and runs.index("make test-site") < upload
    uv_steps = [
        s
        for s in WORKFLOW["jobs"]["build"]["steps"]
        if s.get("uses", "").startswith("astral-sh/setup-uv@")
    ]
    assert len(uv_steps) == 1
    assert str(uv_steps[0].get("with", {}).get("version", "")) == UV_VERSION


def test_deploy_environment():
    assert WORKFLOW["jobs"]["deploy"]["needs"] == "build"
    assert WORKFLOW["jobs"]["deploy"]["environment"]["name"] == "github-pages"


# ---------- Node toolchain for the explorer ----------

SETUP_NODE = "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1"
BUILD_STEPS = WORKFLOW["jobs"]["build"]["steps"]
# No install script was needed (npm ci + astro build pass with ignore-scripts=true),
# so no run step may re-enable scripts.
SCRIPT_ENABLERS = re.compile(
    r"--ignore-scripts=false|ignore-scripts\s+false|npm config set ignore-scripts|npm rebuild"
)


def _build_runs():
    return [s.get("run", "") for s in BUILD_STEPS]


def test_setup_node_pinned():
    steps = [s for s in BUILD_STEPS if s.get("uses", "").startswith("actions/setup-node@")]
    assert len(steps) == 1
    assert steps[0]["uses"] == SETUP_NODE
    assert SHA_PIN.fullmatch(steps[0]["uses"])
    assert steps[0]["with"]["node-version-file"] == "explorer/.node-version"
    assert steps[0]["with"]["package-manager-cache"] is False


def test_npm_ci_only():
    runs = _build_runs()
    assert any("npm ci --prefix explorer" in r for r in runs)
    assert not any("npm install" in r for r in runs)


def test_scripts_stay_blocked():
    assert not [r for r in _build_runs() if SCRIPT_ENABLERS.search(r)]
    assert SCRIPT_ENABLERS.search("npm rebuild esbuild --ignore-scripts=false")


def test_astro_telemetry_disabled():
    env = WORKFLOW["jobs"]["build"].get("env", {})
    assert env.get("ASTRO_TELEMETRY_DISABLED") == "1"


def test_workflows_checkout_without_credentials():
    """No checkout leaves the token in the workspace for later steps to read."""
    checkouts = [st for st in _all_steps() if str(st.get("uses", "")).startswith("actions/checkout@")]
    assert checkouts
    for step in checkouts:
        assert (step.get("with") or {}).get("persist-credentials") is False, step
