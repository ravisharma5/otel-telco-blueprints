"""Drift tests: templates and valid fixtures stay locked to budgets.yaml,
sources-table.yaml, and the front-matter JSON Schemas.

Does not import tools.bplint on purpose (the templates must not depend on the linter).
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest
import yaml
from jsonschema import Draft202012Validator
from markdown_it import MarkdownIt
from referencing import Registry, Resource

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMAS = REPO_ROOT / "schemas"
TEMPLATES = REPO_ROOT / "templates"
FIXTURES = REPO_ROOT / "tools/tests/fixtures"
VALID = FIXTURES / "valid"

BUDGETS = yaml.safe_load((REPO_ROOT / "tools/bplint/budgets.yaml").read_text())
SOURCES = yaml.safe_load((SCHEMAS / "sources-table.yaml").read_text())

TEMPLATE_FILES = {
    "use-case": TEMPLATES / "use-case-blueprint.md",
    "platform": TEMPLATES / "platform-blueprint.md",
}
SCHEMA_FILES = {
    "use-case": "use-case.schema.json",
    "platform": "platform.schema.json",
}
# fixture dir -> blueprint type
VALID_FIXTURES = {
    "use-case": "use-case",
    "platform": "platform",
    "catalog-entry": "use-case",
}
STANDARD_LINE = (
    "Any component can be replaced. "
    "The Red Hat products named here show one way to build this design."
)
COMPONENT_HEADER = ["Component role", "Red Hat product used"]
# Budget unit -> the word used in template budget comments. Kept local because
# this module must not import the linter; it mirrors the style-guide test map.
UNIT_WORD = {
    "rows": "row",
    "tables": "table",
    "steps": "step",
    "bullets": "bullet",
    "lines": "line",
    "diagrams": "diagram",
}
BUDGET_COMMENT = re.compile(r"<!-- budget: ([^;]*);")


# ---------- helpers ----------


def split_doc(path: pathlib.Path) -> tuple[dict, str]:
    text = path.read_text()
    assert text.startswith("---\n"), f"{path} has no front matter"
    _, fm, body = text.split("---\n", 2)
    return yaml.safe_load(fm), body


def tokens(body: str):
    return MarkdownIt("commonmark").enable("table").parse(body)


def sections(body: str) -> list[tuple[str, list]]:
    """Return [(h2 title, tokens in that section)]."""
    toks = tokens(body)
    out: list[tuple[str, list]] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.type == "heading_open" and t.tag == "h2":
            out.append((toks[i + 1].content, []))
            i += 3
            continue
        if t.type == "heading_open" and t.tag == "h1":
            i += 3
            continue
        if out:
            out[-1][1].append(t)
        i += 1
    return out


def section(body: str, title: str) -> list:
    for t, toks in sections(body):
        if t == title:
            return toks
    raise AssertionError(f"section {title!r} missing")


def tables(toks: list) -> list[tuple[list[str], list[list[str]]]]:
    """Return [(header cells, body rows)] for each table in toks."""
    out = []
    cur_head: list[str] | None = None
    cur_rows: list[list[str]] = []
    row: list[str] = []
    in_head = False
    for i, t in enumerate(toks):
        if t.type == "table_open":
            cur_head, cur_rows = [], []
        elif t.type == "thead_open":
            in_head = True
        elif t.type == "thead_close":
            in_head = False
        elif t.type == "tr_open":
            row = []
        elif t.type in ("th_open", "td_open"):
            row.append(toks[i + 1].content.strip())
        elif t.type == "tr_close":
            if in_head:
                cur_head = row
            else:
                cur_rows.append(row)
        elif t.type == "table_close":
            out.append((cur_head, cur_rows))
    return out


def links(body: str) -> list[str]:
    out = []
    for t in tokens(body):
        for c in t.children or []:
            if c.type == "link_open":
                out.append(c.attrs["href"])
            elif c.type == "image":
                out.append(c.attrs["src"])
    return out


def prose_words(body: str) -> int:
    """Words in paragraphs and list items outside tables (headings, code, comments excluded)."""
    count = 0
    in_table = False
    toks = tokens(body)
    for i, t in enumerate(toks):
        if t.type == "table_open":
            in_table = True
        elif t.type == "table_close":
            in_table = False
        elif t.type == "inline" and not in_table and toks[i - 1].type == "paragraph_open":
            text = "".join(c.content for c in t.children if c.type in ("text", "code_inline"))
            count += len(text.split())
    return count


def schema_validator(name: str) -> Draft202012Validator:
    reg = Registry()
    for p in SCHEMAS.glob("*.schema.json"):
        s = json.loads(p.read_text())
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    return Draft202012Validator(
        json.loads((SCHEMAS / name).read_text()),
        registry=reg,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def section_titles(kind: str) -> list[str]:
    return [s["title"] for s in BUDGETS["types"][kind]["sections"]]


def sources_section(kind: str) -> str:
    return BUDGETS["types"][kind]["sources_section"]


# ---------- templates ----------


@pytest.mark.parametrize("kind", TEMPLATE_FILES)
def test_template_h2_titles_match_budgets(kind):
    _, body = split_doc(TEMPLATE_FILES[kind])
    assert [t for t, _ in sections(body)] == section_titles(kind)


@pytest.mark.parametrize("kind", TEMPLATE_FILES)
def test_template_sources_header_matches_canonical(kind):
    _, body = split_doc(TEMPLATE_FILES[kind])
    tbls = tables(section(body, sources_section(kind)))
    assert len(tbls) == 1
    assert tbls[0][0] == SOURCES["columns"]
    basis = {b.lower() for b in SOURCES["basis_values"]}
    assert tbls[0][1] and all(r[2].lower() in basis for r in tbls[0][1])


@pytest.mark.parametrize("kind", TEMPLATE_FILES)
def test_template_links_the_sources_table_definition(kind):
    _, body = split_doc(TEMPLATE_FILES[kind])
    assert any(h.endswith("framework/definitions.md#sources-table") for h in links(body))


@pytest.mark.parametrize("kind", TEMPLATE_FILES)
def test_template_has_no_readiness_or_validation_wording(kind):
    text = TEMPLATE_FILES[kind].read_text()
    assert not re.search(r"E-level|M-level|evidence|validat|not yet|honest", text, re.I)


@pytest.mark.parametrize("kind", TEMPLATE_FILES)
def test_template_at_a_glance_labels(kind):
    _, body = split_doc(TEMPLATE_FILES[kind])
    tbls = tables(section(body, "At a glance"))
    assert len(tbls) == 1
    assert [r[0] for r in tbls[0][1]] == BUDGETS["types"][kind]["at_a_glance_rows"]


@pytest.mark.parametrize("kind", TEMPLATE_FILES)
def test_template_front_matter_keys_match_schema(kind):
    fm, _ = split_doc(TEMPLATE_FILES[kind])
    schema = json.loads((SCHEMAS / SCHEMA_FILES[kind]).read_text())
    assert set(fm) == set(schema["properties"])


def test_template_has_diagram_slot_and_no_tier_field():
    text = TEMPLATE_FILES["platform"].read_text()
    assert re.search(r"!\[[^\]]*\]\(diagrams/[^)]+\.svg\)", text)
    assert "candidate.json" in text
    assert not re.search(r"maturity|sandbox|maintained", text, re.I)


def test_use_case_template_has_mermaid_slot_and_no_tier_field():
    """Use cases draw one capability-only Mermaid flow instead of an archify image."""
    text = TEMPLATE_FILES["use-case"].read_text()
    _, body = split_doc(TEMPLATE_FILES["use-case"])
    flow = section(body, "How it works")
    fences = [t for t in flow if t.type == "fence" and t.info.strip() == "mermaid"]
    assert text.count("```mermaid") == 1 and len(fences) == 1
    assert "![" not in text and "diagrams/" not in text
    assert not re.search(r"maturity|sandbox|maintained", text, re.I)
    fence = fences[0].content
    assert not re.search(r"Red Hat|OpenShift|vLLM|llm-d|\bL(?:10|[0-9])\b", fence)
    notify = re.search(r'--\s*"NOTIFY"\s*-->\s*(\w+)', fence)
    assert notify and re.search(rf'{notify.group(1)}\["[^"]*notification job', fence)


USE_CASE_ACTION_HEADER = ["Action", "Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP)", "Approval", "AI Act class"]
USE_CASE_PARAM_HEADER = ["Parameter", "What it controls", "Who sets it", "How to calibrate"]
USE_CASE_RACI_HEADER = ["Activity", "Responsible", "Accountable", "Consulted", "Informed"]
USE_CASE_VERIFY_HEADER = ["Check", "PB-02 gate or parameter", "Owner"]
NO_DEFAULT = "This page gives no default values."


def test_use_case_template_governance_tables():
    _, body = split_doc(TEMPLATE_FILES["use-case"])
    gov = section(body, "Governance")
    headers = [tbl[0] for tbl in tables(gov)]
    assert headers == [USE_CASE_ACTION_HEADER, USE_CASE_PARAM_HEADER, USE_CASE_RACI_HEADER]
    assert [rows for _head, rows in tables(gov)[1:]] == [[], []], "parameter and RACI tables carry headers only"
    assert any(NO_DEFAULT in p for p in paragraphs(gov))
    assert any(h.endswith("architecture/decision-gate.md") for h in links(body_of(gov)))


def test_use_case_template_deploy_and_verify():
    _, body = split_doc(TEMPLATE_FILES["use-case"])
    dv = section(body, "Deploy and verify")
    assert any(t.type == "ordered_list_open" for t in dv)
    assert [tbl[0] for tbl in tables(dv)] == [USE_CASE_VERIFY_HEADER]
    items = [t.content for t in dv if t.type == "inline"]
    bullets = [c for c in items if c.startswith(("Agent-school:", "NVIDIA", "LFN"))]
    assert bullets and bullets[0].startswith("Agent-school:"), bullets


def test_use_case_template_what_you_need_flags_and_decision():
    _, body = split_doc(TEMPLATE_FILES["use-case"])
    need = section(body, "What you need")
    assert [tbl[0] for tbl in tables(need)] == [COMPONENT_HEADER]
    assert any(t.type == "fence" and t.info.strip() == "text" for t in need)
    assert any(h.endswith("serving-routing-placement/README.md#key-flags-per-slot") for h in links(body_of(need)))
    assert any(t.type == "inline" and t.content.startswith("[ ] Decision engine:") for t in need)


def paragraphs(toks: list) -> list[str]:
    return [toks[i + 1].content for i, t in enumerate(toks) if t.type == "paragraph_open"]


def body_of(toks: list) -> str:
    """Inline text of a token list, so links() can scan one section."""
    return "\n".join(t.content for t in toks if t.type == "inline")


def test_template_components_convention():
    """Role + Red Hat product, no status column, and the standard line."""
    _, pbody = split_doc(TEMPLATE_FILES["platform"])
    comp = section(pbody, "Components")
    tbls = tables(comp)
    assert len(tbls) == 1 and tbls[0][0] == COMPONENT_HEADER
    assert STANDARD_LINE in paragraphs(comp)
    _, ubody = split_doc(TEMPLATE_FILES["use-case"])
    need = section(ubody, "What you need")
    assert STANDARD_LINE in paragraphs(need)
    assert any(t.type == "inline" and t.content.startswith("[ ] Components:") for t in need)


@pytest.mark.parametrize("name", ["platform", "use-case"])
def test_fixture_components_convention(name):
    _, body = split_doc(VALID / name / "README.md")
    title = "Components" if name == "platform" else "What you need"
    toks = section(body, title)
    assert STANDARD_LINE in paragraphs(toks)
    if name == "platform":
        assert tables(toks)[0][0] == COMPONENT_HEADER


@pytest.mark.parametrize(
    "section",
    BUDGETS["types"]["use-case"]["sections"],
    ids=lambda s: s["title"],
)
def test_use_case_template_budget_comments_match_budgets(section):
    text = TEMPLATE_FILES["use-case"].read_text()
    heading = f"\n## {section['title']}\n"
    assert heading in text, f"{section['title']} missing from the use-case template"
    start = text.index(heading)
    end = text.find("\n## ", start + 1)
    match = BUDGET_COMMENT.search(text, start, end if end != -1 else len(text))
    assert match, f"no budget comment in ## {section['title']}"
    comment = match.group(1)
    for unit, limit in section.items():
        if unit == "title":
            continue
        pat = rf"\b{limit} {UNIT_WORD[unit]}s?\b"
        assert re.search(pat, comment), f"{section['title']}: '{limit} {unit}' not in '{comment}'"


# ---------- valid fixtures ----------


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_fixture_front_matter_validates(name):
    fm, _ = split_doc(VALID / name / "README.md")
    kind = VALID_FIXTURES[name]
    errors = [e.message for e in schema_validator(SCHEMA_FILES[kind]).iter_errors(fm)]
    assert errors == []
    assert fm["type"] == kind


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_fixture_structure_matches_template(name):
    kind = VALID_FIXTURES[name]
    _, tbody = split_doc(TEMPLATE_FILES[kind])
    _, fbody = split_doc(VALID / name / "README.md")
    assert [t for t, _ in sections(fbody)] == [t for t, _ in sections(tbody)]
    vsec = sources_section(kind)
    assert tables(section(fbody, vsec))[0][0] == tables(section(tbody, vsec))[0][0]
    labels = [r[0] for r in tables(section(fbody, "At a glance"))[0][1]]
    assert labels == BUDGETS["types"][kind]["at_a_glance_rows"]


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_fixture_relative_links_resolve(name):
    base = VALID / name
    _, body = split_doc(base / "README.md")
    rel = [h for h in links(body) if not re.match(r"^[a-z]+:", h) and not h.startswith("#")]
    assert rel, "expected at least one relative link"
    for href in rel:
        target = (base / href.split("#", 1)[0]).resolve()
        assert target.exists(), f"{href} does not resolve from {base}"


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_fixture_is_marked_fictional(name):
    fm, body = split_doc(VALID / name / "README.md")
    assert "Fictional" in fm["title"] or "fictional" in fm["title"]
    first = body.strip().splitlines()[0]
    assert "Fictional" in first


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_fixture_sources_rows_cover_url_and_repo_file(name):
    kind = VALID_FIXTURES[name]
    _, body = split_doc(VALID / name / "README.md")
    toks = section(body, sources_section(kind))
    hrefs = links("".join(t.content + "\n" for t in toks if t.type == "inline"))
    assert any(h.startswith("https://") for h in hrefs)
    assert any(h.startswith("../../sources/") for h in hrefs)


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_fixture_within_page_word_budget(name):
    kind = VALID_FIXTURES[name]
    fm, body = split_doc(VALID / name / "README.md")
    budget = BUDGETS["types"][kind]["page_words"]
    if isinstance(budget, dict):
        budget = budget["recipe" if fm["depth"] == "recipe" else "entry"]
    assert prose_words(body) <= budget


def test_catalog_entry_stubs_only_optional_sections():
    fm, body = split_doc(VALID / "catalog-entry" / "README.md")
    assert fm["flagship"] is False and fm["depth"] == "entry"
    marker = BUDGETS["stub_marker"]
    required = BUDGETS["types"]["use-case"]["entry_required"]
    stubbed = []
    for title, toks in sections(body):
        inl = [t for t in toks if t.type == "inline"]
        is_stub = bool(inl) and inl[0].content.startswith(marker)
        if is_stub:
            stubbed.append(title)
        if title in required:
            assert not is_stub, f"{title} must be filled in a catalog entry"
    assert stubbed == ["How it works", "Deploy and verify"]


# ---------- catalog-entry template and the entry budget ----------

ENTRY_TEMPLATE = TEMPLATES / "use-case-entry.md"
ENTRY_MAX = FIXTURES / "budget/entry-max/README.md"
STYLE_GUIDE = REPO_ROOT / "framework/style-guide.md"
GATING_PAGE = REPO_ROOT / "platform/safety-autonomy-gating/README.md"
NO_COURSE_SENTENCE = "None: no agent-school course covers this use case yet"
MUST_ADD_HEADER = ["Gap", "What you add", "Source"]
MAX_SLOTS = {"embedding", "reranker", "safety", "decision", "llm", "classification"}
PAGE_WORDS = BUDGETS["types"]["use-case"]["page_words"]
# Telecom job titles stay out of templates; pages use generic roles.
JOB_TITLE = re.compile(
    r"noc-shift-lead|\bNOC lead|\bshift lead|operator risk owner|operator SME"
    r"|\bplatform engineers?\b|\bplatform owners?\b|\bautomation teams?\b"
    r"|\brisk and compliance leads?\b|\bnamed approver\b|\bsecurity architects?\b"
    r"|\bNOC engineers?\b",
    re.I,
)


def raw_section(body: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}[ \t]*$", body, re.M)
    assert m, f"no ## {title}"
    nxt = re.search(r"^## ", body[m.end() :], re.M)
    return body[m.end() : m.end() + nxt.start()] if nxt else body[m.end() :]


def raw_front_matter(path: pathlib.Path) -> str:
    return path.read_text().split("---\n", 2)[1]


def visible(text: str) -> str:
    """Text with HTML comments removed."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def gate_rule_sentences() -> list[str]:
    """First two sentences under "### Gate rules" on the gating page."""
    text = GATING_PAGE.read_text()
    m = re.search(r"^### Gate rules[ \t]*$", text, re.M)
    rest = text[m.end() :]
    nxt = re.search(r"^#{2,3} ", rest, re.M)
    block = re.sub(r"\s+", " ", rest[: nxt.start()] if nxt else rest).strip()
    return re.split(r"(?<=[.!?])\s+", block)[:2]


def must_add_rows(body: str) -> tuple[list[str], list[list[str]]] | None:
    need = raw_section(body, "What you need")
    m = re.search(r"^### What you must add[ \t]*$", need, re.M)
    if not m:
        return None
    found = tables(tokens(need[m.end() :]))
    return found[0] if found else None


def test_entry_template_shape():
    fm, body = split_doc(ENTRY_TEMPLATE)
    schema = json.loads((SCHEMAS / SCHEMA_FILES["use-case"]).read_text())
    assert set(fm) == set(schema["properties"])
    assert fm["depth"] == "entry" and fm["flagship"] is False
    assert [t for t, _ in sections(body)] == section_titles("use-case")
    for title in ("How it works", "Deploy and verify"):
        assert visible(raw_section(body, title)).strip().startswith("_Stub:"), title
    assert "```mermaid" not in ENTRY_TEMPLATE.read_text()
    head, rows = must_add_rows(body)
    assert head == MUST_ADD_HEADER and rows == []
    gov = section(body, "Governance")
    headers = [tbl[0] for tbl in tables(gov)]
    assert USE_CASE_ACTION_HEADER in headers and USE_CASE_PARAM_HEADER in headers
    assert any(NO_DEFAULT in p for p in paragraphs(gov))
    raw = raw_front_matter(ENTRY_TEMPLATE)
    assert 'depth: "entry"' in raw and "flagship: false" in raw
    assert NO_COURSE_SENTENCE in raw


def test_entry_template_framing():
    text = ENTRY_TEMPLATE.read_text()
    assert STANDARD_LINE in text
    assert not re.search(r"\b(GA|TP|DP)\b", text)
    assert not re.search(r"(?i)unverified|validated|production-ready|readiness level", text)
    assert JOB_TITLE.findall(text) == []


def test_use_case_template_depth_comment():
    raw = raw_front_matter(TEMPLATE_FILES["use-case"])
    line = next(ln for ln in raw.splitlines() if ln.startswith("depth:"))
    assert line.startswith('depth: "recipe"') and f"{PAGE_WORDS['recipe']} prose words" in line
    entry = raw_front_matter(ENTRY_TEMPLATE)
    line = next(ln for ln in entry.splitlines() if ln.startswith("depth:"))
    assert f"{PAGE_WORDS['entry']} prose words" in line
    for path, key in ((TEMPLATE_FILES["use-case"], "recipe"), (ENTRY_TEMPLATE, "entry")):
        stated = set(map(int, re.findall(r"Page budget: (\d+) prose words", path.read_text())))
        assert stated == {PAGE_WORDS[key]}, (path.name, stated)


@pytest.mark.parametrize("section", BUDGETS["types"]["use-case"]["sections"], ids=lambda s: s["title"])
def test_entry_template_budget_comments_match_budgets(section):
    text = ENTRY_TEMPLATE.read_text()
    heading = f"\n## {section['title']}\n"
    start = text.index(heading)
    end = text.find("\n## ", start + 1)
    match = BUDGET_COMMENT.search(text, start, end if end != -1 else len(text))
    assert match, f"no budget comment in ## {section['title']}"
    for unit, limit in section.items():
        if unit != "title":
            assert re.search(rf"\b{limit} {UNIT_WORD[unit]}s?\b", match.group(1)), (section["title"], unit)


def test_entry_budget_fixture_is_maximal():
    fm, body = split_doc(ENTRY_MAX)
    assert fm["depth"] == "entry" and fm["flagship"] is False
    assert set(fm["otel_slots"]) == MAX_SLOTS and len(fm["otel_slots"]) == 6
    assert fm["autonomy_ceiling"] == "recommend-with-approval" and fm["tmf_an_level_target"] == 2
    need = raw_section(body, "What you need")
    assert len(re.findall(r"^- \[ \] ", need, re.M)) == 12
    assert re.search(r"^- \[ \] Decision engine: ", need, re.M)
    assert "```text" in need and "# Decision (card recipe)" in need
    assert len(re.findall(r"^- ", raw_section(body, "Limitations"), re.M)) == 6
    head, rows = must_add_rows(body)
    assert head == MUST_ADD_HEADER and len(rows) >= 5
    problem = [ln for ln in raw_section(body, "Problem and value").splitlines() if ln.strip()]
    assert len(problem) == next(s["lines"] for s in BUDGETS["types"]["use-case"]["sections"] if s["title"] == "Problem and value")
    gov = raw_section(body, "Governance")
    actions = next(t for t in tables(tokens(gov)) if t[0] == USE_CASE_ACTION_HEADER)
    outcomes = " ".join(r[1] for r in actions[1])
    assert "NOTIFY" in outcomes and "REVIEW" in outcomes
    flat_gov = re.sub(r"\s+", " ", gov)
    for sentence in gate_rule_sentences():
        assert sentence in flat_gov, sentence


def test_entry_budget_fits_maximal_entry():
    from tools.tests.conftest import run_bplint

    assert run_bplint(ENTRY_MAX) == (0, [])
    _, body = split_doc(ENTRY_MAX)
    assert prose_words(body) <= PAGE_WORDS["entry"]


def test_style_guide_entry_budget_matches_budgets():
    text = STYLE_GUIDE.read_text()
    recipe = re.search(r"(\d+) prose words for a recipe", text)
    entry = re.search(r"(\d+) prose words for an entry", text)
    assert recipe and int(recipe.group(1)) == PAGE_WORDS["recipe"]
    assert entry and int(entry.group(1)) == PAGE_WORDS["entry"]
