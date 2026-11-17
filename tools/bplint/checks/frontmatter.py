"""FM001, FM002, RF001: front matter presence, type binding, and schema validity.

DP001: a flagship use case must be a recipe (depth: recipe).
AD001: a use case's adaptation field must agree with its OTel slots: the
Classification slot, a retraining rung, and a Classification labels item go
together; taxonomy, gate labels, and corpus follow the Classification,
Decision, and Embedding slots; tool contracts expertise and a tool contract
item go together; LoRA training data only with the lora-if-gap rung; a golden
set always.
SB001: a use case's sandbox fit must agree with its autonomy ceiling: a use
case that can act within policy needs whole-agent, and an inform-only use case
cannot be whole-agent. The page-text rules for the fit live in the tests.
AS001: an empty agent_school list needs the no-course sentence in the
At a glance Agent-school courses cell. AS002: every course number must be in
the pinned list in tools/bplint/agent-school-courses.yaml (read locally, no
network).
"""

from __future__ import annotations

import functools
import re
from pathlib import Path

from ..loader import load_yaml
from ..report import Finding

COURSES_FILE = Path(__file__).resolve().parents[1] / "agent-school-courses.yaml"
NO_COURSE_SENTENCE = "None: no agent-school course covers this use case yet"
COURSES_ROW = "Agent-school courses"

_REQUIRED = re.compile(r"^'([^']+)' is a required property")
_QUOTED = re.compile(r"'([^']+)'")
_WORD_LIMIT = re.compile(r"\{0,(\d+)\}")

# Placement roles split the llm slot by size; every other role is its slot.
_ROLE_SLOT = {"llm-small": "llm", "llm-large": "llm"}


def _key_line(doc, key) -> int:
    """File line of `key:` in the front matter block, else 1."""
    if key:
        pat = re.compile(rf"^{re.escape(str(key))}\s*:")
        for i, ln in enumerate(doc.fm_lines):
            if pat.match(ln):
                return i + 2  # line 1 is the opening ---
    return 1


def _error_key(err) -> str | None:
    if err.absolute_path:
        return str(err.absolute_path[0])
    if err.validator == "required":
        m = _REQUIRED.match(err.message)
        return m.group(1) if m else None
    return None


def _json_path(err, key) -> str:
    parts = [str(p) for p in err.absolute_path]
    if not parts and key:
        parts = [key]
    return "$" + "".join(f"[{p}]" if p.isdigit() else f".{p}" for p in parts)


def _word_limit_message(err, path) -> str | None:
    """'<path>: N words; the limit is L' for a word-limit pattern error, else None.

    Applies to card fields, placement notes, and the sandbox why line, whose patterns end in {0,K}
    for an L = K + 1 word limit.
    """
    parts = [str(p) for p in err.absolute_path]
    in_card = parts[:1] == ["card"]
    in_note = len(parts) == 3 and parts[0] == "placement" and parts[2] == "note"
    in_why = parts == ["sandbox", "why"]
    if err.validator != "pattern" or not (in_card or in_note or in_why) or not isinstance(err.instance, str):
        return None
    m = _WORD_LIMIT.search(str(err.validator_value))
    if not m:
        return None
    limit = int(m.group(1)) + 1
    count = len(err.instance.split())
    if count == 0:
        return f"{path}: is empty; write 1 to {limit} words"
    return f"{path}: {count} words; the limit is {limit}"


def _placement_messages(fm) -> list[str]:
    """Consistency of the placement map with otel_slots and placement_tier.

    Runs only when the schema accepts the page, so shapes are known.
    """
    placement = fm.get("placement")
    if not isinstance(placement, dict):
        return []
    slots = list(fm.get("otel_slots") or [])
    tiers = list(fm.get("placement_tier") or [])
    out = []
    used = {t for t, v in placement.items() if v.get("runs")}
    for tier in tiers:
        if tier not in used:
            out.append(f"$.placement: tier '{tier}' is in placement_tier but runs no slot role in placement")
    for tier in placement:
        if tier in used and tier not in tiers:
            out.append(f"$.placement.{tier}: tier '{tier}' runs slot roles but is not in placement_tier")
    placed = set()
    for tier, value in placement.items():
        runs = value.get("runs") or []
        if not runs and not str(value.get("note") or "").strip():
            out.append(f"$.placement.{tier}.note: tier '{tier}' runs no slot role, so it needs a note saying why")
        for role in runs:
            slot = _ROLE_SLOT.get(role, role)
            placed.add(slot)
            if slot not in slots:
                out.append(
                    f"$.placement.{tier}.runs: role '{role}' needs slot '{slot}', which is not in otel_slots"
                )
    for slot in slots:
        if slot not in placed:
            out.append(f"$.placement: slot '{slot}' from otel_slots is not placed at any tier")
    return out


@functools.lru_cache(maxsize=1)
def _courses() -> frozenset[int]:
    data = load_yaml(COURSES_FILE) or {}
    return frozenset(int(k) for k in (data.get("courses") or {}))


def _courses_cell(doc) -> str | None:
    sec = doc.section("At a glance")
    if sec is None or not sec.tables:
        return None
    for row in sec.tables[0].rows:
        if len(row.cells) >= 2 and row.cells[0].replace("**", "").strip() == COURSES_ROW:
            return row.cells[1]
    return None


def _depth_findings(doc, fm) -> list[Finding]:
    if fm.get("flagship") is True and fm.get("depth") != "recipe":
        text = f"$.depth: a flagship use case must have depth 'recipe', found '{fm.get('depth')}'"
        return [Finding(doc.path, _key_line(doc, "depth"), 1, "error", "DP001", text)]
    return []


_RETRAIN_RUNGS = {"head-retrain", "lora-if-gap"}
# No-model-change rungs whose rendered text says the page retrieves; skills is the one without retrieval.
_RETRIEVAL_RUNGS = {"retrieval", "retrieval-and-skills"}


def _adaptation_messages(fm) -> list[str]:
    """AD001 rule failures, one message per rule. Runs after the schema passes."""
    ad = fm.get("adaptation")
    if not isinstance(ad, dict):
        return []
    slots = set(fm.get("otel_slots") or [])
    rung = ad.get("rung")
    expertise = set(ad.get("expertise") or [])
    bring = ad.get("bring")
    mechs = {b.get("mechanism") for b in bring or [] if isinstance(b, dict)}
    has_bring = isinstance(bring, list)
    out = []

    classify = "classification" in slots
    retrains = rung in _RETRAIN_RUNGS
    labels_ok = not has_bring or (("classification-labels" in mechs) == classify)
    if classify != retrains or not labels_ok:
        out.append(
            "the Classification slot, a retraining rung (head-retrain or lora-if-gap), and a "
            f"classification-labels bring item must go together; found classification "
            f"{'in' if classify else 'not in'} otel_slots and rung '{rung}'"
            + ("" if labels_ok else ", and the classification-labels item does not match")
        )
    for exp, slot in (("taxonomy", "classification"), ("gate-labels", "decision"), ("corpus", "embedding")):
        if (exp in expertise) != (slot in slots):
            out.append(f"expertise '{exp}' must be listed if and only if '{slot}' is in otel_slots")
    if has_bring and ("rag-corpus" in mechs) != ("embedding" in slots):
        out.append("a rag-corpus bring item needs the embedding slot, and the embedding slot needs one")
    if has_bring and ("tool-contract" in mechs) != ("tool-contracts" in expertise):
        out.append("expertise 'tool-contracts' and a tool-contract bring item must go together")
    if rung in _RETRIEVAL_RUNGS and "embedding" not in slots:
        out.append(f"rung '{rung}' names retrieval, so the embedding slot must be in otel_slots")
    if rung == "skills" and "embedding" in slots:
        out.append("rung 'skills' does no retrieval; with the embedding slot use 'retrieval-and-skills'")
    if "lora-data" in mechs and rung != "lora-if-gap":
        out.append(f"a lora-data bring item needs rung 'lora-if-gap', found '{rung}'")
    if "golden-set" not in expertise:
        out.append("expertise must include 'golden-set'")
    return out


def _adaptation_findings(doc, fm) -> list[Finding]:
    line = _key_line(doc, "adaptation")
    return [
        Finding(doc.path, line, 1, "error", "AD001", f"$.adaptation: {text}")
        for text in _adaptation_messages(fm)
    ]


def _sandbox_messages(fm) -> list[str]:
    """SB001 rule failures, one message per rule. Runs after the schema passes."""
    sb = fm.get("sandbox")
    if not isinstance(sb, dict):
        return []
    fit = sb.get("fit")
    ceiling = fm.get("autonomy_ceiling")
    out = []
    if ceiling == "act-within-policy" and fit != "whole-agent":
        out.append(
            "a use case that can act within policy can make changes on its own, so sandbox the whole agent "
            f"(fit 'whole-agent'); found fit '{fit}'"
        )
    if fit == "whole-agent" and ceiling == "inform":
        out.append("an inform-only use case has no path to act, so it cannot be whole-agent")
    return out


def _sandbox_findings(doc, fm) -> list[Finding]:
    line = _key_line(doc, "sandbox")
    return [
        Finding(doc.path, line, 1, "error", "SB001", f"$.sandbox: {text}")
        for text in _sandbox_messages(fm)
    ]


def _course_findings(doc, fm) -> list[Finding]:
    courses = fm.get("agent_school")
    if not isinstance(courses, list):
        return []
    line = _key_line(doc, "agent_school")
    if not courses:
        cell = _courses_cell(doc)
        if cell is None or NO_COURSE_SENTENCE not in cell:
            text = (
                f"$.agent_school: empty, so the At a glance '{COURSES_ROW}' cell must say "
                f"'{NO_COURSE_SENTENCE}'"
            )
            return [Finding(doc.path, line, 1, "error", "AS001", text)]
        return []
    known = _courses()
    return [
        Finding(
            doc.path,
            line,
            1,
            "error",
            "AS002",
            f"$.agent_school: course {n} is not in the pinned agent-school course list ({COURSES_FILE.name})",
        )
        for n in courses
        if n not in known
    ]


def check_type_binding(doc, ctx) -> list[Finding]:
    """FM002 when the page's `type` is not one its glob group accepts.

    Runs on blueprints and plain docs alike, before check(). On a finding it
    flags the doc so check() and the structural checks skip it.
    """
    allowed = doc.allowed_types
    fm = doc.front_matter
    if allowed is None or not isinstance(fm, dict):
        return []
    btype = fm.get("type")
    if btype is None or btype in allowed:
        return []  # a missing blueprint type is reported by check() below
    if allowed:
        expected = ", ".join(f"'{t}'" for t in allowed)
        text = f"$.type: '{btype}' is not allowed here; expected one of {expected}"
    else:
        text = f"$.type: '{btype}' is not allowed here; pages in this folder must not declare a type"
    doc.flags.update({"skip_structure", "type_not_allowed"})
    return [Finding(doc.path, _key_line(doc, "type"), 1, "error", "FM002", text)]


def check(doc, ctx) -> list[Finding]:
    if not doc.is_blueprint or "type_not_allowed" in doc.flags:
        return []
    fm = doc.front_matter
    if doc.fm_error is not None or fm is None or not isinstance(fm, dict):
        doc.flags.add("fm001")
        if doc.fm_error is not None:
            line, msg = doc.fm_error
            text = f"front matter does not parse: {msg}"
        elif fm is None:
            line, text = 1, "blueprint has no YAML front matter block"
        else:
            line, text = 1, "front matter must be a YAML mapping"
        return [Finding(doc.path, line, 1, "error", "FM001", text)]

    btype = fm.get("type")
    validator = ctx.schemas.get(btype) if isinstance(btype, str) else None
    if validator is None:
        doc.flags.add("skip_structure")
        what = "missing" if btype is None else f"unknown ('{btype}')"
        known = ", ".join(f"'{k}'" for k in (doc.allowed_types or sorted(ctx.schemas)))
        return [
            Finding(
                doc.path,
                _key_line(doc, "type"),
                1,
                "error",
                "FM002",
                f"$.type: blueprint type is {what}; expected one of {known}",
            )
        ]

    facets = set(ctx.config.get("facet_fields") or [])
    out = []
    for err in sorted(validator.iter_errors(fm), key=lambda e: (list(map(str, e.absolute_path)), e.message)):
        key = _error_key(err)
        code = "RF001" if key in facets else "FM002"
        line_key = key
        if err.validator == "additionalProperties":
            extras = _QUOTED.findall(err.message)
            line_key = extras[-1] if extras else None
        path = _json_path(err, key)
        text = _word_limit_message(err, path) or f"{path}: {err.message}"
        out.append(Finding(doc.path, _key_line(doc, line_key), 1, "error", code, text))
    if not out and btype == "use-case":
        line = _key_line(doc, "placement")
        out.extend(
            Finding(doc.path, line, 1, "error", "FM002", text) for text in _placement_messages(fm)
        )
        out.extend(_depth_findings(doc, fm))
        out.extend(_adaptation_findings(doc, fm))
        out.extend(_sandbox_findings(doc, fm))
    if not out:
        out.extend(_course_findings(doc, fm))
    return out
