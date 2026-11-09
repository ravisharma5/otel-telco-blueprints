"""Findings and output formatting."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    col: int
    severity: str  # "error" | "warning"
    code: str
    message: str


def sort_findings(findings):
    return sorted(findings, key=lambda f: (f.path, f.line, f.code, f.col, f.message))


def format_text(findings) -> str:
    return "\n".join(
        f"{f.path}:{f.line}:{f.col}: {f.severity} {f.code} {f.message}" for f in findings
    )


def format_json(findings) -> str:
    return json.dumps([asdict(f) for f in findings], indent=2)


def exit_code(findings) -> int:
    """1 if any finding is an error, else 0 (warnings never fail the run)."""
    return 1 if any(f.severity == "error" for f in findings) else 0
