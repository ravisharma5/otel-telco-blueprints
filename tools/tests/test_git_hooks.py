"""Scratch-repository tests for the versioned git guards.

Every hook case runs in a throwaway repository under pytest's tmp_path, with
global and system git config disabled, so the live repository and the user's
own config never leak in. The only test that reads the live repository is the
read-only `tree HEAD` check and the tracked-mode check.

Internal path names and planning-id shapes are built from string fragments, so
this file passes the content checks it exercises. Private terms are never
written here: the term cases use synthetic placeholders that start with "zz".
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.tests.conftest import REPO_ROOT

PLAN_DIR = "." + "plan" + "ning"
AGENT = "CLAU" + "DE.md"
ID_PAREN = "(02" + "-01)"
SYNTH_TERM = "zz" + "secretterm"
CHECK = "tools/guards/check.py"


def _env(tmp_path: Path) -> dict:
    env = dict(os.environ)
    gconf = tmp_path / "empty-gitconfig"
    gconf.write_text("")
    env.update(
        {
            "GIT_CONFIG_GLOBAL": str(gconf),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    for key in ("GUARDS_EXTRA_TERMS", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(key, None)
    return env


class Scratch:
    def __init__(self, root: Path, env: dict, tmp: Path):
        self.root = root
        self.env = env
        self.tmp = tmp

    def run(self, *args, check=False, cwd=None):
        return subprocess.run(
            list(args),
            cwd=cwd or self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=check,
        )

    def git(self, *args, check=False):
        return self.run("git", *args, check=check)

    def write(self, rel: str, data) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")
        return path

    def commit_file(self, rel: str, data, msg: str = "docs: add file", *, no_verify=False):
        self.write(rel, data)
        self.git("add", "--", rel, check=True)
        args = ["commit", "-q", "-m", msg]
        if no_verify:
            args.append("--no-verify")
        return self.git(*args)

    def head(self) -> str:
        return self.git("rev-parse", "HEAD", check=True).stdout.strip()

    def terms_file(self) -> Path:
        path = self.tmp / "terms.txt"
        path.write_text(
            "\n".join(
                [
                    "# synthetic terms only",
                    SYNTH_TERM,
                    "re:zz-?rel[ -]?9",
                    "allow:" + SYNTH_TERM + ".example/ok",
                ]
            )
            + "\n"
        )
        return path

    def configure_terms(self) -> Path:
        path = self.terms_file()
        proc = self.run(sys.executable, CHECK, "install", "--extra-terms", str(path))
        assert proc.returncode == 0, proc.stderr
        return path


def _copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))


@pytest.fixture
def scratch(tmp_path):
    env = _env(tmp_path)
    root = tmp_path / "repo"
    root.mkdir()
    s = Scratch(root, env, tmp_path)
    s.git("init", "-q", "-b", "main", check=True)
    _copy_tree(REPO_ROOT / "tools/guards", root / "tools/guards")
    _copy_tree(REPO_ROOT / "tools/git-hooks", root / "tools/git-hooks")
    proc = s.run(sys.executable, CHECK, "install")
    assert proc.returncode == 0, proc.stderr
    s.write("README.md", "# Scratch\n\nA clean seed file.\n")
    s.git("add", "README.md", "tools", check=True)
    s.git("commit", "-q", "-m", "docs: seed", check=True)
    return s


# Forbidden paths, nested, case-variant, register-era.
@pytest.mark.parametrize(
    "path",
    [
        "framework/" + AGENT,
        "Clau" + "de.md",
        ".Plan" + "ning/x.md",
        "tools/" + PLAN_DIR + "/n.md",
        "catalog/x/" + "." + "claude/settings.local.json",
        "architecture/support" + "-status.md",
    ],
)
def test_pre_commit_rejects_forbidden_path(scratch, path):
    before = scratch.head()
    proc = scratch.commit_file(path, "hello\n")
    assert proc.returncode != 0
    assert path in proc.stderr
    assert scratch.head() == before


def test_pre_commit_rejects_rename_into_forbidden_path(scratch):
    assert scratch.commit_file("ok.md", "fine\n").returncode == 0
    (scratch.root / "framework").mkdir()
    scratch.git("mv", "ok.md", "framework/" + AGENT, check=True)
    proc = scratch.git("commit", "-q", "-m", "docs: move")
    assert proc.returncode != 0
    assert "framework/" + AGENT in proc.stderr


# Content checks.
def test_pre_commit_rejects_planning_mention(scratch):
    proc = scratch.commit_file("doc.md", "See `" + PLAN_DIR + "` for details.\n")
    assert proc.returncode != 0
    assert "mention" in proc.stderr


def test_pre_commit_rejects_planning_id(scratch):
    proc = scratch.commit_file("doc.md", "Fixed in " + ID_PAREN + ".\n")
    assert proc.returncode != 0
    assert "planning-id" in proc.stderr


def test_pre_commit_accepts_clean_doc(scratch):
    assert scratch.commit_file("doc.md", "A clean public page.\n").returncode == 0


def test_pre_commit_accepts_binary_png(scratch):
    data = b"\x89PNG\r\n\x1a\n\x00\x00\xff\xfe binary"
    assert scratch.commit_file("img/logo.png", data).returncode == 0


def test_pre_commit_rejects_invalid_utf8_text(scratch):
    proc = scratch.commit_file("doc.md", b"bad \xff\xfe bytes\n")
    assert proc.returncode != 0
    assert "doc.md" in proc.stderr


def test_pre_commit_term_masked(scratch):
    scratch.configure_terms()
    proc = scratch.commit_file("doc.md", "This mentions " + SYNTH_TERM + " here.\n")
    assert proc.returncode != 0
    assert "private term #1" in proc.stderr
    assert SYNTH_TERM not in proc.stderr


def test_pre_commit_regex_term(scratch):
    scratch.configure_terms()
    proc = scratch.commit_file("doc.md", "Runs on zz-rel 9 today.\n")
    assert proc.returncode != 0
    assert "private term #2" in proc.stderr


def test_pre_commit_fragment_joined_term(scratch):
    scratch.configure_terms()
    line = 'X = "' + SYNTH_TERM[:5] + '" + "' + SYNTH_TERM[5:] + '"\n'
    proc = scratch.commit_file("tool.py", line)
    assert proc.returncode != 0
    assert "private term #" in proc.stderr


def test_pre_commit_allowlisted_term(scratch):
    scratch.configure_terms()
    proc = scratch.commit_file("doc.md", "See https://" + SYNTH_TERM + ".example/ok for more.\n")
    assert proc.returncode == 0, proc.stderr


# Private-term skip semantics.
def test_terms_skipped_when_unset(scratch):
    assert scratch.git("config", "--get", "guards.extraTerms").returncode != 0
    assert scratch.commit_file("doc.md", "This mentions " + SYNTH_TERM + ".\n").returncode == 0
    assert scratch.commit_file("framework/" + AGENT, "x\n").returncode != 0
    scratch.git("reset", "-q", "HEAD", "--", "framework/" + AGENT)
    assert scratch.commit_file("doc2.md", "Fixed in " + ID_PAREN + ".\n").returncode != 0


def test_terms_fail_closed_when_file_missing(scratch):
    scratch.git("config", "guards.extraTerms", str(scratch.tmp / "missing.txt"), check=True)
    proc = scratch.commit_file("doc.md", "A clean public page.\n")
    assert proc.returncode != 0
    assert "guards.extraTerms" in proc.stderr


# commit-msg.
@pytest.mark.parametrize("msg", ["feat(02" + "-01): x", "docs(01.1" + "): x"])
def test_commit_msg_rejects_id_scope(scratch, msg):
    proc = scratch.commit_file("doc.md", "Clean.\n", msg)
    assert proc.returncode != 0
    assert "commit-scope" in proc.stderr


def test_commit_msg_accepts_word_scope(scratch):
    assert scratch.commit_file("doc.md", "Clean.\n", "docs: fine").returncode == 0


def test_commit_msg_term_only_when_configured(scratch):
    msg = "docs: mention " + SYNTH_TERM
    assert scratch.commit_file("a.md", "Clean.\n", msg).returncode == 0
    scratch.configure_terms()
    proc = scratch.commit_file("b.md", "Clean.\n", msg)
    assert proc.returncode != 0
    assert "private term #1" in proc.stderr
    assert SYNTH_TERM not in proc.stderr


# pre-push.
def _bare(scratch, name: str) -> None:
    bare = scratch.tmp / (name + ".git")
    scratch.run("git", "init", "-q", "--bare", str(bare), cwd=scratch.tmp, check=True)
    scratch.git("remote", "add", name, str(bare), check=True)


def test_pre_push_accepts_clean_history(scratch):
    _bare(scratch, "origin")
    scratch.commit_file("doc.md", "Clean.\n")
    proc = scratch.git("push", "-q", "origin", "main")
    assert proc.returncode == 0, proc.stderr


def test_pre_push_rejects_forbidden_path(scratch):
    _bare(scratch, "origin")
    assert scratch.git("push", "-q", "origin", "main").returncode == 0
    scratch.commit_file("framework/" + AGENT, "x\n", no_verify=True)
    proc = scratch.git("push", "-q", "origin", "main")
    assert proc.returncode != 0
    assert "framework/" + AGENT in proc.stderr


def test_pre_push_rejects_id_scoped_message(scratch):
    _bare(scratch, "origin")
    scratch.commit_file("doc.md", "Clean.\n", "feat(02" + "-01): x", no_verify=True)
    proc = scratch.git("push", "-q", "origin", "main")
    assert proc.returncode != 0
    assert "commit-scope" in proc.stderr


def test_pre_push_rejects_bad_content(scratch):
    _bare(scratch, "origin")
    scratch.commit_file("doc.md", "Fixed in " + ID_PAREN + ".\n", no_verify=True)
    proc = scratch.git("push", "-q", "origin", "main")
    assert proc.returncode != 0
    assert "planning-id" in proc.stderr


def test_pre_push_scans_only_target_remote(scratch):
    """A bad commit already on another remote is still rejected for origin."""
    _bare(scratch, "origin")
    _bare(scratch, "other")
    scratch.commit_file("framework/" + AGENT, "x\n", no_verify=True)
    assert scratch.git("push", "-q", "--no-verify", "other", "main").returncode == 0
    proc = scratch.git("push", "-q", "origin", "main")
    assert proc.returncode != 0
    assert "framework/" + AGENT in proc.stderr


# Installer.
def _exclude_path(scratch) -> Path:
    rel = scratch.git("rev-parse", "--git-path", "info/exclude", check=True).stdout.strip()
    return scratch.root / rel


def test_installer_idempotent(scratch):
    from tools.guards import patterns

    for _ in range(2):
        proc = scratch.run("sh", "tools/git-hooks/install.sh")
        assert proc.returncode == 0, proc.stderr
    lines = _exclude_path(scratch).read_text().splitlines()
    for entry in patterns.EXCLUDE_LINES:
        assert lines.count(entry) == 1, entry
    path = scratch.git("config", "core.hooksPath", check=True).stdout.strip()
    assert path == "tools/git-hooks"


def test_installer_check_reports_drift(scratch):
    assert scratch.run(sys.executable, CHECK, "install", "--check").returncode == 0
    scratch.git("config", "--unset", "core.hooksPath", check=True)
    proc = scratch.run(sys.executable, CHECK, "install", "--check")
    assert proc.returncode == 1
    assert "hooksPath" in proc.stderr + proc.stdout


def test_installer_check_reports_missing_terms_file(scratch):
    scratch.git("config", "guards.extraTerms", str(scratch.tmp / "missing.txt"), check=True)
    proc = scratch.run(sys.executable, CHECK, "install", "--check")
    assert proc.returncode == 1


# Versioned hook modes in the live repository.
def test_hook_modes_tracked_executable():
    out = subprocess.run(
        ["git", "ls-files", "-s", "tools/git-hooks"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    modes = {line.split("\t")[1]: line.split()[0] for line in out.splitlines() if "\t" in line}
    if not modes:
        pytest.skip("tools/git-hooks is not tracked yet")
    for hook in ("pre-commit", "commit-msg", "pre-push"):
        assert modes.get("tools/git-hooks/" + hook) == "100755", hook


# Live tree is clean.
def test_live_tree_clean():
    proc = subprocess.run(
        [sys.executable, CHECK, "tree", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
