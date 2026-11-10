"""Check registry and shared run context.

DOC_CHECKS: callables check(doc, ctx) -> list[Finding], run per document in order.
REPO_CHECKS: callables check(ctx) -> list[Finding], run once per invocation
after every doc check (ID001 id uniqueness, XR001 platform cross-references).
Context.discovery is True when the CLI discovered files from the config globs
(no explicit paths); XR001 runs only then.
Check modules are added to the registry at the bottom of this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class Context:
    repo_root: Path
    config: dict
    budgets: dict
    sources_spec: dict
    schemas: dict  # validators by type: "platform", "use-case", "reference"
    enums: dict  # enum lists from common.schema.json $defs, in schema order
    today: date = field(default_factory=date.today)
    docs: list = field(default_factory=list)
    discovery: bool = False  # True on full-repo runs (no explicit paths)


def structure_type(doc, ctx) -> str | None:
    """Blueprint type for structural checks, or None when they must skip.

    Skips non-blueprint docs, docs with FM001 (no usable front matter), and docs
    flagged `skip_structure` (missing or unknown `type`, reported as FM002).
    """
    if not doc.is_blueprint or doc.flags & {"fm001", "skip_structure"}:
        return None
    fm = doc.front_matter
    if not isinstance(fm, dict):
        return None
    t = fm.get("type")
    return t if t in (ctx.budgets.get("types") or {}) else None


DOC_CHECKS: list = []
REPO_CHECKS: list = []

# Registration order matters: frontmatter sets the flags later checks read.
from . import frontmatter, sections, budgets, sources_table  # noqa: E402
from . import links, diagrams, clarity  # noqa: E402
from . import repo  # noqa: E402

DOC_CHECKS.extend(
    [
        frontmatter.check_type_binding,
        frontmatter.check,
        sections.check,
        budgets.check,
        sources_table.check,
        links.check,
        diagrams.check,
        clarity.check,
    ]
)

# Repo checks: ids first, then cross-references.
REPO_CHECKS.extend([repo.check_ids, repo.check_refs])

# Non-blueprint docs (config doc_globs) run only these checks.
GENERAL_DOC_CHECKS = (frontmatter.check_type_binding, links.check, diagrams.check, clarity.check)


def applies(check, doc) -> bool:
    """True when `check` should run on `doc` (blueprints run every doc check)."""
    return doc.is_blueprint or check in GENERAL_DOC_CHECKS
