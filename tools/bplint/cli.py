"""bplint command line: discovery, check orchestration, output, exit codes.

Exit codes: 0 = clean or warnings only, 1 = at least one error,
2 = usage or configuration error.
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from datetime import date
from pathlib import Path

from . import checks
from .loader import load_yaml
from .markdown import parse_doc
from .report import Finding, exit_code, format_json, format_text, sort_findings
from .schema import load_enums, load_validators

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "tools/bplint/config.yaml"


class ConfigError(Exception):
    pass


def _resolve(p) -> Path:
    p = Path(p)
    return p if p.is_absolute() else (REPO_ROOT / p)


def display_path(p: Path) -> str:
    try:
        return p.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(p)


def _parse_args(argv):
    ap = argparse.ArgumentParser(prog="bplint", description="Lint OTel telco blueprints.")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--today", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    ap.add_argument("paths", nargs="*")
    return ap.parse_args(argv)


def _load_yaml_dict(path: Path, what: str) -> dict:
    if not path.is_file():
        raise ConfigError(f"{what} not found: {path}")
    try:
        data = load_yaml(path)
    except Exception as exc:  # yaml errors, permission errors
        raise ConfigError(f"cannot load {what} {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{what} {path} is not a mapping")
    return data


# Column names validation_table.py reads by name. A spec without them
# would raise KeyError mid-run, so reject it up front as a config error.
VT_REQUIRED_COLUMNS = ("Load-bearing", "E-level", "Evidence", "Release / revision")


def _check_vt_spec(spec: dict) -> None:
    columns = spec.get("columns")
    if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
        raise ConfigError("validation table spec 'columns' must be a list of column names")
    missing = [c for c in VT_REQUIRED_COLUMNS if c not in columns]
    if missing:
        raise ConfigError(f"validation table spec columns are missing required column(s): {missing}")
    raising = spec.get("raising_column")
    if raising is not None and raising not in columns:
        raise ConfigError(
            f"validation table spec raising_column '{raising}' is not one of the columns"
        )
    context = spec.get("context_columns") or []
    if not isinstance(context, list):
        raise ConfigError("validation table spec 'context_columns' must be a list")
    unknown = [c for c in context if c not in columns]
    if unknown:
        raise ConfigError(
            f"validation table spec context_columns {unknown} are not in the columns"
        )


def build_context(args) -> checks.Context:
    config = _load_yaml_dict(_resolve(args.config), "config")
    for key in ("schemas_dir", "budgets", "validation_table"):
        if key not in config:
            raise ConfigError(f"config is missing key '{key}'")
    budgets = _load_yaml_dict(_resolve(config["budgets"]), "budgets")
    vt_spec = _load_yaml_dict(_resolve(config["validation_table"]), "validation table spec")
    _check_vt_spec(vt_spec)
    schema_dir = _resolve(config["schemas_dir"])
    try:
        validators = load_validators(schema_dir)
        enums = load_enums(schema_dir)
    except Exception as exc:
        raise ConfigError(f"cannot load schemas from {schema_dir}: {exc}") from exc
    try:
        today = date.fromisoformat(args.today) if args.today else date.today()
    except ValueError as exc:
        raise ConfigError(f"--today must be YYYY-MM-DD: {exc}") from exc

    return checks.Context(
        repo_root=REPO_ROOT,
        config=config,
        budgets=budgets,
        vt_spec=vt_spec,
        schemas=validators,
        enums=enums,
        today=today,
    )


def _glob_match(rel: str, pattern: str) -> bool:
    """Repo-relative glob match where a trailing `/**` means the whole subtree."""
    if pattern.endswith("/**"):
        prefix_parts = pattern[:-3].split("/")
        rel_parts = rel.split("/")
        if len(rel_parts) <= len(prefix_parts):
            return False
        return all(
            fnmatch.fnmatchcase(r, p) for r, p in zip(rel_parts, prefix_parts)
        )
    return fnmatch.fnmatchcase(rel, pattern)


def load_context(config=DEFAULT_CONFIG, today=None) -> checks.Context:
    """Build a Context without the CLI (used by unit tests and other tools)."""
    ns = argparse.Namespace(config=str(config), today=today)
    return build_context(ns)


def run_doc_checks(doc, ctx) -> list:
    """Run every registered per-document check on one doc, in registry order."""
    out = []
    for check in checks.DOC_CHECKS:
        if checks.applies(check, doc):
            out.extend(check(doc, ctx))
    return sort_findings(out)


def _excluded(rel: str, patterns) -> bool:
    return any(_glob_match(rel, pat) for pat in patterns)


def discover(config) -> list[tuple[Path, bool]]:
    """Return (path, is_blueprint) for files matching the config globs."""
    excludes = config.get("exclude_globs") or []
    seen: dict[Path, bool] = {}
    for globs, is_bp in ((config.get("blueprint_globs") or [], True), (config.get("doc_globs") or [], False)):
        for pattern in globs:
            for p in sorted(REPO_ROOT.glob(pattern)):
                if not p.is_file():
                    continue
                rel = p.relative_to(REPO_ROOT).as_posix()
                if _excluded(rel, excludes):
                    continue
                seen.setdefault(p, is_bp)
    return sorted(seen.items())


def main(argv=None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        ctx = build_context(args)
    except ConfigError as exc:
        print(f"bplint: {exc}", file=sys.stderr)
        return 2

    if args.paths:
        targets = []
        for raw in args.paths:
            p = Path(raw)
            p = p if p.is_absolute() else Path.cwd() / p
            if not p.is_file():
                print(f"bplint: no such file: {raw}", file=sys.stderr)
                return 2
            targets.append((p, True))
    else:
        targets = discover(ctx.config)
        ctx.discovery = True  # full-repo run: XR001 may treat absent platforms as dangling

    findings = []
    for p, is_bp in targets:
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # Report instead of crashing; the rest of the run continues.
            findings.append(
                Finding(
                    display_path(p),
                    1,
                    1,
                    "error",
                    "IO001",
                    f"cannot read file as UTF-8 text: {type(exc).__name__}",
                )
            )
            continue
        ctx.docs.append(parse_doc(p, text, display=display_path(p), is_blueprint=is_bp))

    for doc in ctx.docs:
        for check in checks.DOC_CHECKS:
            if checks.applies(check, doc):
                findings.extend(check(doc, ctx))
    for check in checks.REPO_CHECKS:
        findings.extend(check(ctx))

    findings = sort_findings(findings)
    if args.format == "json":
        print(format_json(findings))
    elif findings:
        print(format_text(findings))
    return exit_code(findings)
