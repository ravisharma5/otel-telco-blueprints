#!/usr/bin/env python3
"""Git guard CLI: the logic behind the versioned hooks in tools/git-hooks.

Modes:

- pre-commit: rejects staged internal paths (renames included), staged paths
  with a configured private term, and staged text with internal mentions,
  planning ids, or configured private terms.
- commit-msg FILE: rejects messages with planning-id scopes, internal mentions,
  planning ids, or configured private terms.
- pre-push REMOTE: checks every pushed ref name (local and remote side,
  branches and tags) and every annotated tag message in the pushed tag chain,
  then the commits new to REMOTE (tree paths, private terms in those paths,
  messages, and the content each commit introduces). Ref deletions are
  allowed.
- tree [REV]: path (internal paths and private terms) and content checks over
  every file at REV (default HEAD).
- install [--check] [--extra-terms PATH]: points core.hooksPath at
  tools/git-hooks, makes the hooks executable, and adds the local exclude
  lines. --check changes nothing and reports drift.

All rules come from tools/guards/patterns.py. Private terms are never stored
in this repository: they load at run time from the file named by
GUARDS_EXTRA_TERMS or the local git config key guards.extraTerms. If neither
is set, term checks are skipped and every other check still runs. If one is
set but the file is missing or invalid, every mode fails closed. A term hit
prints as "private term #n", never as the term text; a path with a private
term prints only as "<path with private term #n>".

Standard library only; Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.guards import patterns  # noqa: E402

HOOKS_DIR = "tools/git-hooks"
HOOKS = ("pre-commit", "commit-msg", "pre-push")
CONFIG_KEY = "guards.extraTerms"
ADVICE = "planning files belong in the local planning repo"
GITLINK_MODE = "160000"


class TermsError(Exception):
    """The configured extra-terms file is missing or invalid (fail closed)."""


def git(*args: str, cwd: Optional[str] = None, check: bool = True, data: Optional[bytes] = None) -> bytes:
    proc = subprocess.run(["git", *args], cwd=cwd, input=data, capture_output=True)
    if check and proc.returncode != 0:
        msg = proc.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {msg}")
    return proc.stdout


def git_ok(*args: str, cwd: Optional[str] = None) -> bool:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True).returncode == 0


def toplevel() -> str:
    return git("rev-parse", "--show-toplevel").decode().strip()


def load_terms(top: str) -> Optional[patterns.ExtraTerms]:
    path = patterns.resolve_extra_terms_path(top)
    if path is None:
        return None
    full = Path(path).expanduser()
    if not full.is_absolute():
        full = Path(top) / full
    try:
        return patterns.load_extra_terms(full)
    except FileNotFoundError:
        raise TermsError(
            f"{CONFIG_KEY} (or GUARDS_EXTRA_TERMS) names a file that does not exist; "
            f"restore the file or run `git config --unset {CONFIG_KEY}`"
        ) from None
    except ValueError as exc:
        raise TermsError(f"{CONFIG_KEY} file is invalid: {exc}") from None
    except OSError:
        raise TermsError(f"{CONFIG_KEY} file cannot be read") from None


class Report:
    def __init__(self, hook: str):
        self.hook = hook
        self.hits = 0

    def hit(self, where: str, kind: str, match: str) -> None:
        self.hits += 1
        print(f"{self.hook}: {where}: {kind} {match}; {ADVICE}", file=sys.stderr)

    def text_hits(self, where: str, found: list) -> None:
        for lineno, kind, match in found:
            self.hit(f"{where}:{lineno}", kind, match)

    def path(self, where: str, name: str, extra=None) -> bool:
        n = patterns.term_number(name, extra)
        if n is not None:
            # Checked first so a forbidden, term-bearing path is never printed.
            label = f"<path with private term #{n}>"
            self.hit(label if where == name else where, "internal path", label)
            return True
        if patterns.forbidden_path(name):
            self.hit(where, "internal path", name)
            return True
        return False

    def content(self, where: str, name: str, data: bytes, extra) -> None:
        """Content rules shared by pre-commit, pre-push, and tree."""
        if name in patterns.SELF_EXCLUDED:
            return
        if Path(name).suffix.lower() in patterns.BINARY_SUFFIXES:
            return
        try:
            if b"\0" in data:
                raise UnicodeDecodeError("utf-8", data, 0, 1, "NUL byte")
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            self.hit(where, "unreadable content", "(binary or non-UTF-8 text in a non-binary file type)")
            return
        self.text_hits(where, patterns.scan_text(text, extra, joined=True))

    def exit_code(self) -> int:
        return 1 if self.hits else 0


def parse_raw(out: bytes) -> Iterator[Tuple[str, str, str, str]]:
    """Yield (new_mode, new_sha, status, path) from `--raw -z --no-renames` output."""
    parts = out.split(b"\0")
    i = 0
    while i < len(parts):
        head = parts[i].decode("utf-8", "replace")
        if not head.startswith(":"):
            i += 1
            continue
        fields = head[1:].split()
        path = parts[i + 1].decode("utf-8", "surrogateescape") if i + 1 < len(parts) else ""
        i += 2
        if len(fields) < 5:
            continue
        yield fields[1], fields[3], fields[4][:1], path


def blob(sha: str, cwd: str) -> bytes:
    return git("cat-file", "blob", sha, cwd=cwd)


def cmd_pre_commit(top: str, extra) -> int:
    rep = Report("pre-commit")
    out = git("diff", "--cached", "--raw", "-z", "--no-renames", "--diff-filter=ACMRT", cwd=top)
    for mode, sha, _status, name in parse_raw(out):
        if rep.path(name, name, extra):
            continue
        if mode == GITLINK_MODE:
            continue
        rep.content(name, name, blob(sha, top), extra)
    return rep.exit_code()


def cmd_commit_msg(top: str, extra, msg_file: str) -> int:
    rep = Report("commit-msg")
    raw = Path(msg_file).read_text(encoding="utf-8", errors="replace")
    message = "\n".join(line for line in raw.splitlines() if not line.startswith("#"))
    rep.text_hits("message", patterns.scan_message(message, extra))
    return rep.exit_code()


def _is_zero(sha: str) -> bool:
    return not sha.strip("0")


def _push_commits(top: str, remote: str, local_sha: str, remote_sha: str) -> List[str]:
    if not _is_zero(remote_sha) and git_ok("cat-file", "-e", remote_sha + "^{commit}", cwd=top):
        out = git("rev-list", local_sha, "^" + remote_sha, cwd=top)
    else:
        # Only the target remote counts as published; another remote does not.
        out = git("rev-list", local_sha, "--not", f"--remotes={remote}", cwd=top)
    return out.decode().split()


MAX_TAG_DEPTH = 10
NOT_A_REF = ("HEAD", "(delete)")


def _ref_label(ref: str, extra) -> str:
    """The ref name, or a masked label when it holds a private term."""
    n = patterns.term_number(ref, extra)
    return ref if n is None else f"<ref name with private term #{n}>"


def _check_ref_names(rep: Report, extra, refs: Tuple[str, ...]) -> None:
    for ref in dict.fromkeys(refs):
        if ref in NOT_A_REF:
            continue
        label = _ref_label(ref, extra)
        for _lineno, kind, match in patterns.scan_text(ref, extra, joined=False):
            rep.hit(f"ref {label}", kind, match)


def _check_tag_chain(rep: Report, top: str, extra, sha: str, label: str) -> None:
    """Scan the message and name header of every tag object from sha down."""
    obj = sha
    for depth in range(MAX_TAG_DEPTH + 1):
        if git("cat-file", "-t", obj, cwd=top).strip() != b"tag":
            return
        if depth == MAX_TAG_DEPTH:
            rep.hit(label, "tag chain too deep", f"(more than {MAX_TAG_DEPTH} nested tags)")
            return
        body = git("cat-file", "tag", obj, cwd=top).decode("utf-8", "replace")
        headers, _, message = body.partition("\n\n")
        next_obj = None
        for header in headers.splitlines():
            if header.startswith("object "):
                next_obj = header[len("object "):].strip()
            elif header.startswith("tag "):
                name = header[len("tag "):]
                for _lineno, kind, match in patterns.scan_text(name, extra, joined=False):
                    rep.hit(f"{label} (tag name)", kind, match)
        rep.text_hits(label, patterns.scan_message(message, extra))
        if not next_obj:
            return
        obj = next_obj


def cmd_pre_push(top: str, extra, remote: str, stdin_text: str) -> int:
    rep = Report("pre-push")
    if extra is None:
        print(f"pre-push: private term checks skipped: {CONFIG_KEY} unset", file=sys.stderr)
    seen_commits: set = set()
    seen_blobs: set = set()
    for line in stdin_text.splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = fields[:4]
        if _is_zero(local_sha):
            continue  # ref deletion (branch or tag): allowed, nothing is published
        _check_ref_names(rep, extra, (local_ref, remote_ref))
        tag_ref = local_ref if local_ref not in NOT_A_REF else remote_ref
        _check_tag_chain(rep, top, extra, local_sha, _ref_label(tag_ref, extra) + " tag message")
        for c in _push_commits(top, remote, local_sha, remote_sha):
            if c in seen_commits:
                continue
            seen_commits.add(c)
            short = c[:12]
            names = git("ls-tree", "-r", "--name-only", "-z", c, cwd=top).split(b"\0")
            for raw_name in names:
                if raw_name:
                    name = raw_name.decode("utf-8", "surrogateescape")
                    rep.path(f"commit {short}", name, extra)
            message = git("log", "-1", "--format=%B", c, cwd=top).decode("utf-8", "replace")
            rep.text_hits(f"commit {short} message", patterns.scan_message(message, extra))
            out = git(
                "diff-tree", "-r", "-m", "--root", "--no-commit-id", "--no-renames",
                "--raw", "-z", "--diff-filter=AMT", c, cwd=top,
            )
            for mode, sha, _status, name in parse_raw(out):
                if (
                    mode == GITLINK_MODE
                    or patterns.forbidden_path(name)
                    or patterns.term_number(name, extra) is not None
                ):
                    continue  # paths are reported (masked) from the tree listing above
                if (sha, name) in seen_blobs:
                    continue
                seen_blobs.add((sha, name))
                rep.content(f"commit {short} {name}", name, blob(sha, top), extra)
    return rep.exit_code()


def cmd_tree(top: str, extra, rev: str) -> int:
    rep = Report("tree")
    out = git("ls-tree", "-r", "-z", rev, cwd=top)
    for entry in out.split(b"\0"):
        if not entry:
            continue
        meta, _, raw_name = entry.partition(b"\t")
        mode, kind, sha = meta.decode().split()
        name = raw_name.decode("utf-8", "surrogateescape")
        if rep.path(name, name, extra):
            continue
        if kind != "blob":
            continue
        rep.content(name, name, blob(sha, top), extra)
    return rep.exit_code()


def _exclude_file(top: str) -> Path:
    rel = git("rev-parse", "--git-path", "info/exclude", cwd=top).decode().strip()
    path = Path(rel)
    return path if path.is_absolute() else Path(top) / path


def _install_problems(top: str) -> List[str]:
    problems = []
    proc = subprocess.run(["git", "config", "--get", "core.hooksPath"], cwd=top, capture_output=True, text=True)
    if proc.stdout.strip() != HOOKS_DIR:
        problems.append(f"core.hooksPath is not {HOOKS_DIR} (run `make hooks`)")
    for hook in HOOKS:
        path = Path(top) / HOOKS_DIR / hook
        if not path.is_file():
            problems.append(f"hook missing: {HOOKS_DIR}/{hook}")
        elif not os.access(path, os.X_OK):
            problems.append(f"hook not executable: {HOOKS_DIR}/{hook}")
    exclude = _exclude_file(top)
    present = exclude.read_text().splitlines() if exclude.is_file() else []
    for line in patterns.EXCLUDE_LINES:
        if line not in present:
            problems.append(f"info/exclude line missing: {line}")
    try:
        load_terms(top)
    except TermsError as exc:
        problems.append(str(exc))
    return problems


def cmd_install(top: str, check_only: bool, extra_terms: Optional[str]) -> int:
    cwd = Path.cwd().resolve()
    if cwd != Path(top).resolve():
        print("install: run from the top level of the work tree", file=sys.stderr)
        return 1
    if check_only:
        problems = _install_problems(top)
        for problem in problems:
            print(f"install --check: {problem}", file=sys.stderr)
        return 1 if problems else 0
    git("config", "--local", "core.hooksPath", HOOKS_DIR, cwd=top)
    for hook in HOOKS:
        path = Path(top) / HOOKS_DIR / hook
        if path.is_file():
            path.chmod(0o755)
    exclude = _exclude_file(top)
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text() if exclude.is_file() else ""
    present = existing.splitlines()
    missing = [line for line in patterns.EXCLUDE_LINES if line not in present]
    if missing:
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        block = "# Added by the guard installer (internal files stay untracked):\n"
        with exclude.open("a", encoding="utf-8") as fh:
            fh.write(prefix + block + "\n".join(missing) + "\n")
    if extra_terms:
        path = Path(extra_terms).expanduser().resolve()
        if not path.is_file():
            print("install: --extra-terms file does not exist", file=sys.stderr)
            return 1
        try:
            patterns.load_extra_terms(path)
        except ValueError as exc:
            print(f"install: --extra-terms file is invalid: {exc}", file=sys.stderr)
            return 1
        git("config", "--local", CONFIG_KEY, str(path), cwd=top)
    problems = _install_problems(top)
    for problem in problems:
        print(f"install: {problem}", file=sys.stderr)
    return 1 if problems else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="check.py", description="Public-repository git guards.")
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("pre-commit")
    p_msg = sub.add_parser("commit-msg")
    p_msg.add_argument("msg_file")
    p_push = sub.add_parser("pre-push")
    p_push.add_argument("remote")
    p_push.add_argument("url", nargs="?")
    p_tree = sub.add_parser("tree")
    p_tree.add_argument("rev", nargs="?", default="HEAD")
    p_inst = sub.add_parser("install")
    p_inst.add_argument("--check", action="store_true")
    p_inst.add_argument("--extra-terms", metavar="PATH")
    args = parser.parse_args(argv)

    try:
        top = toplevel()
    except RuntimeError:
        print(f"{args.mode}: not inside a git work tree", file=sys.stderr)
        return 1

    if args.mode == "install":
        return cmd_install(top, args.check, args.extra_terms)

    try:
        extra = load_terms(top)
    except TermsError as exc:
        print(f"{args.mode}: {exc}", file=sys.stderr)
        return 1

    try:
        if args.mode == "pre-commit":
            return cmd_pre_commit(top, extra)
        if args.mode == "commit-msg":
            return cmd_commit_msg(top, extra, args.msg_file)
        if args.mode == "pre-push":
            return cmd_pre_push(top, extra, args.remote, sys.stdin.read())
        return cmd_tree(top, extra, args.rev)
    except RuntimeError as exc:
        print(f"{args.mode}: {exc} (fail closed)", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
