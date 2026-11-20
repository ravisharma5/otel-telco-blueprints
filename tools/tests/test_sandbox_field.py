"""The sandbox field on every use case, tied to the page text and to PB-08.

Every use-case page records, in front matter, which sandbox layer it needs on
top of the PB-08 base controls:

- none: the agent reads through the gateways and runs no code itself
- execution: the agent's tools run code or binaries against live gear (dry
  runs, check mode, probes), or parse raw network bytes or files an attacker
  can shape, so those tools run in their own sandbox
- whole-agent: the use case acts within policy or has its own write
  path, so the agent itself runs in the sandbox

These tests derive the fit from the page text and fail when the field
disagrees. They scan only How it works, What you need, and Limitations, after
removing URLs, code fences, generated blocks, and the What you must add table.
"""

from __future__ import annotations

import re

import pytest

from tools.bplint.slug import github_slug
from tools.site.render_sandbox import (
    FIT_LABELS,
    FIT_ORDER,
    FIT_PAGE_TEXT,
    PB08_ANCHOR,
    SANDBOX_HEADER,
    block,
    fit_table,
)
from tools.tests.test_reference_pages import body, front_matter
from tools.tests.test_use_case_pages import _id, _raw_section, page_key, use_case_pages

PAGES = pytest.mark.parametrize("path", use_case_pages(), ids=_id)

# Runtime verbs from the execution principle: code or binaries run against live
# gear, or raw bytes and attacker-shapeable files parsed.
TRIGGER_RE = re.compile(
    r"\bdry[- ]runs?\b|check mode|parser tools|\bdecodes\b|\bdecoders\b|rebuild each|raw traces|LSP ping|TWAMP|untrusted",
    re.I,
)
WRITE_PATH = re.compile(r"^- \[ \] Write path:", re.M)
URL = re.compile(r"\(https?://[^)]*\)|https?://\S+")
FENCE = re.compile(r"^```.*?^```[ \t]*$", re.M | re.S)
GENERATED = re.compile(r"<!-- generated:([a-z-]+) start -->.*?<!-- generated:\1 end -->", re.S)
MUST_ADD_H3 = re.compile(r"^### What you must add[ \t]*$", re.M)
SCANNED = ("How it works", "What you need", "Limitations")
WHY_RULES = {
    "none": re.compile(r"\bruns no code\b", re.I),
    "execution": re.compile(r"dry-run|dry run|check mode|validate|pars|decod|rebuild|raw|probe", re.I),
    "whole-agent": re.compile(r"within policy|write|action request", re.I),
}
EXPECTED_COUNTS = {"none": 20, "execution": 5, "whole-agent": 4}


def _sandbox(path) -> dict:
    return (front_matter(path) or {}).get("sandbox") or {}


def _drop_must_add(need: str) -> str:
    m = MUST_ADD_H3.search(need)
    if not m:
        return need
    nxt = re.search(r"^#{2,3} ", need[m.end() :], re.M)
    return need[: m.start()] + (need[m.end() + nxt.start() :] if nxt else "")


def scanned_text(text: str) -> str:
    """How it works, What you need (without What you must add), and Limitations, cleaned."""
    parts = []
    for name in SCANNED:
        sec = _raw_section(text, name) or ""
        if name == "What you need":
            sec = _drop_must_add(sec)
        parts.append(sec)
    out = "\n".join(parts)
    out = GENERATED.sub("", out)
    out = FENCE.sub("", out)
    out = URL.sub("", out)
    return out.replace("--tool-call-parser", "")


def triggers(text: str) -> bool:
    return bool(TRIGGER_RE.search(scanned_text(text)))


def changes(path) -> bool:
    """The use case acts within policy or writes directly."""
    fm = front_matter(path) or {}
    need = _raw_section(body(path), "What you need") or ""
    return fm.get("autonomy_ceiling") == "act-within-policy" or bool(WRITE_PATH.search(need))


@PAGES
def test_sandbox_field_present(path):
    sb = _sandbox(path)
    assert sb.get("fit") in FIT_ORDER, sb
    words = len(str(sb.get("why") or "").split())
    assert 1 <= words <= 12, sb


@PAGES
def test_execution_triggers_are_never_none(path):
    if triggers(body(path)):
        assert _sandbox(path).get("fit") != "none", TRIGGER_RE.findall(scanned_text(body(path)))


@PAGES
def test_whole_agent_iff_change(path):
    assert (_sandbox(path).get("fit") == "whole-agent") == changes(path), _sandbox(path)


@PAGES
def test_execution_iff_trigger_without_change(path):
    want = triggers(body(path)) and not changes(path)
    assert (_sandbox(path).get("fit") == "execution") == want, (
        _sandbox(path),
        TRIGGER_RE.findall(scanned_text(body(path))),
    )


def test_trigger_scan_ignores_sources_and_must_add():
    text = (
        "## How it works\n\nThe agent reads alarms through read-only tools.\n\n"
        "## What you need\n\n- [ ] Integrations: read-only tools\n\n"
        "### What you must add\n\n| Gap | What you add | Source |\n|---|---|---|\n"
        "| Decoders | NAS decoders as tools | [x](https://example.invalid/decoders) |\n\n"
        "## Limitations\n\n- It reads what your tools return.\n\n"
        "## Sources\n\n| # | Claim | Basis | Source |\n|---|---|---|---|\n"
        "| 1 | Parser tools decode raw messages with decoders | research | [y](https://example.invalid/) |\n"
    )
    assert not triggers(text)
    assert triggers(text.replace("read-only tools.\n", "parser tools that decode messages.\n", 1))
    assert not triggers("## What you need\n\n<!-- generated:sandbox start -->\nParser tools decode\n<!-- generated:sandbox end -->\n")
    assert not triggers("## How it works\n\n```text\n--tool-call-parser gemma4\n```\n")


@PAGES
def test_why_names_the_trigger(path):
    sb = _sandbox(path)
    assert WHY_RULES[sb["fit"]].search(sb["why"]), sb
    for fit, rule in WHY_RULES.items():
        if fit == "none" and sb["fit"] != "none":
            assert not rule.search(sb["why"]), sb


def test_fit_counts():
    counts = {f: 0 for f in FIT_ORDER}
    for p in use_case_pages():
        counts[_sandbox(p).get("fit")] = counts.get(_sandbox(p).get("fit"), 0) + 1
    assert counts == EXPECTED_COUNTS
    assert sum(counts.values()) == 29


def test_pb08_anchor_matches_slug():
    assert PB08_ANCHOR == github_slug("When a use case needs a sandbox")


def test_fit_labels_cover_every_fit():
    assert set(FIT_LABELS) == set(FIT_PAGE_TEXT) == set(FIT_ORDER)
    for fit in FIT_ORDER:
        assert FIT_PAGE_TEXT[fit].startswith(FIT_LABELS[fit]), fit


FIXTURE_FM = {"sandbox": {"fit": "execution", "why": "Parser tools decode raw fictional widget messages"}}


def test_render_sandbox_block_shape():
    out = block(FIXTURE_FM)
    lines = out.splitlines()
    assert lines[0] == "" and out.endswith("\n\n")
    assert lines[1] == "| " + " | ".join(SANDBOX_HEADER) + " |"
    rows = [ln for ln in lines[3:] if ln.startswith("| ")]
    assert len(rows) == 1
    cells = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    assert cells[0] == FIT_PAGE_TEXT["execution"]
    assert cells[1] == FIXTURE_FM["sandbox"]["why"]
    assert re.search(r"\]\(\.\./\.\./\.\./platform/security-identity-sandbox/README\.md#when-a-use-case-needs-a-sandbox\)$", cells[2])
    with pytest.raises(SystemExit):
        block({"sandbox": {"fit": "kernel", "why": "x"}})
    with pytest.raises(SystemExit):
        block({"sandbox": {"fit": "none", "why": "a | b"}})


def test_fit_table_shape():
    pages = [
        ({"id": "UC-DEMO-02", "title": "Widget beta", "sandbox": {"fit": "none", "why": "x"}}, "demo/widget-beta"),
        ({"id": "UC-DEMO-01", "title": "Widget alpha", "sandbox": {"fit": "none", "why": "x"}}, "demo/widget-alpha"),
        ({"id": "UC-DEMO-03", "title": "Widget gamma", "sandbox": {"fit": "whole-agent", "why": "x"}}, "demo/widget-gamma"),
    ]
    out = fit_table(pages)
    lines = out.splitlines()
    assert lines[0] == "" and lines[1] == "| Fit | Use cases |"
    rows = [ln for ln in lines[3:] if ln.startswith("| ")]
    assert [r.split("|")[1].strip() for r in rows] == [FIT_LABELS[f] for f in FIT_ORDER]
    assert rows[0].split("|")[2].strip() == (
        "[Widget alpha](../../catalog/demo/widget-alpha/README.md); "
        "[Widget beta](../../catalog/demo/widget-beta/README.md)"
    )
    assert rows[1].split("|")[2].strip() == "None yet"
    assert "../../catalog/demo/widget-gamma/README.md" in rows[2]


# ---------- the generated Sandbox block on every page, and the PB-08 link ----------

BLOCK = re.compile(r"<!-- generated:sandbox start -->\n(.*?)<!-- generated:sandbox end -->", re.S)
SANDBOX_H3 = re.compile(r"^### Sandbox[ \t]*$", re.M)
BRING_END = "<!-- generated:what-you-bring end -->"
PB08_PAGE_LINK = "../../../platform/security-identity-sandbox/README.md#when-a-use-case-needs-a-sandbox"


def _need(path) -> str:
    return _raw_section(body(path), "What you need") or ""


@PAGES
def test_every_page_has_the_sandbox_block(path):
    need = _need(path)
    heads = list(SANDBOX_H3.finditer(need))
    assert len(heads) == 1, "What you need needs exactly one '### Sandbox' H3"
    after = need[heads[0].end() :]
    nxt = re.search(r"^#{2,3} ", after, re.M)
    sub = after[: nxt.start()] if nxt else after
    assert sub.count("<!-- generated:sandbox start -->") == 1
    assert sub.count("<!-- generated:sandbox end -->") == 1
    assert body(path).count("<!-- generated:sandbox start -->") == 1
    # Only the marker pair and its generated table sit under the H3.
    assert BLOCK.sub("", sub).strip() == "", sub
    bring_end = need.find(BRING_END)
    assert 0 <= bring_end < heads[0].start(), "the Sandbox block comes after the What you bring block"
    between = need[bring_end + len(BRING_END) : heads[0].start()]
    assert between.strip() == "", "the Sandbox H3 comes directly after the What you bring block"
    must = MUST_ADD_H3.search(need)
    if must:
        assert heads[0].start() < must.start(), "the Sandbox block comes before What you must add"


def test_sandbox_blocks_current():
    from pathlib import Path

    from tools.site import render_sandbox

    assert render_sandbox.main(["--check"]) == 0
    with pytest.raises(SystemExit):
        render_sandbox.main(["--allow-missing"])
    makefile = (Path(render_sandbox.ROOT) / "Makefile").read_text(encoding="utf-8")
    target = re.search(r"^render:\n((?:\t.*\n)+)", makefile, re.M)
    assert target and "tools.site.render_sandbox" in target.group(1)
    assert target.group(1).index("render_bring") < target.group(1).index("render_sandbox")


@PAGES
def test_sandbox_block_matches_field(path):
    sb = _sandbox(path)
    m = BLOCK.search(body(path))
    assert m, "no generated block"
    rows = [ln for ln in m.group(1).splitlines() if ln.startswith("| ") and not ln.startswith("| Sandbox fit |")]
    assert len(rows) == 1, rows
    cells = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    assert cells[0] == FIT_PAGE_TEXT[sb["fit"]]
    assert cells[1] == sb["why"]
    assert f"]({PB08_PAGE_LINK})" in cells[2]


@PAGES
def test_sandbox_block_adds_no_prose_words(path):
    from tools.bplint.markdown import parse_doc

    raw = path.read_text(encoding="utf-8")
    stripped = BLOCK.sub("<!-- generated:sandbox start -->\n<!-- generated:sandbox end -->", raw)
    assert stripped != raw

    def words(text):
        return sum(s.prose_words for s in parse_doc(path, text).sections)

    assert words(raw) == words(stripped)


@PAGES
def test_every_page_lists_pb08(path):
    listed = (front_matter(path) or {}).get("platform_blueprints") or []
    assert "PB-08" in listed
    assert listed == sorted(listed)
