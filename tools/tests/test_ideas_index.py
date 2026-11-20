"""The ideas index (catalog/ideas/index.md) and each idea page's idea block are generated.

tools/site/render_ideas.py writes a table of every idea page between the
generated:ideas markers, and a banner, reason, and promote checklist directly
after the H1 of every idea page, between the generated:idea markers. These
tests run the generator on small tmp catalogs and on the live repository.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.site import render_ideas
from tools.tests.conftest import REPO_ROOT, front_page_pages, idea_pages, use_case_pages

BANNER = (
    "> **Exploration idea, not a recipe.** Try it, test it, and contribute back. "
    "[How to promote an idea](../index.md#promote-an-idea)."
)
INDEX_TEXT = (
    "# Exploration ideas\n\nIntro.\n\n<!-- generated:ideas start -->\n<!-- generated:ideas end -->\n\n"
    "## Promote an idea\n\nSteps.\n"
)


def _page(uc_id: str, title: str, domain: str, idea: str = "", body: str = "") -> str:
    lines = [
        "---",
        f'id: "{uc_id}"',
        'type: "use-case"',
        f'title: "{title}"',
        f'domain: "{domain}"',
        'depth: "entry"',
        "sandbox:",
        '  fit: "none"',
        '  why: "Reads only"',
    ]
    if idea:
        lines.append(idea.rstrip("\n"))
    lines += ["---", "", f"# {title}", ""]
    return "\n".join(lines) + "\n" + (body or "Intro line.\n\n## At a glance\n\nText.\n")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


IDEA_MERGED = """idea:
  why: "Its scope now sits in the knowledge assistant"
  promote: ["A distinct operator need", "Measured gain over the host"]
  merged_into: "UC-OPS-01"
"""
IDEA_PLAIN = """idea:
  why: "Template mining is the usual baseline"
  promote: ["A measured comparison on your own logs"]
"""


@pytest.fixture
def catalog(tmp_path: Path) -> Path:
    cat = tmp_path / "catalog"
    _write(cat / "network-operations/host-page/README.md", _page("UC-OPS-01", "Host recipe", "network-operations"))
    _write(cat / "ideas/zeta-merged/README.md", _page("UC-OPS-12", "Merged idea", "network-operations", IDEA_MERGED))
    _write(cat / "ideas/alpha-log/README.md", _page("UC-AGOPS-09", "Site log reduction", "agentic-operations", IDEA_PLAIN))
    _write(cat / "ideas/index.md", INDEX_TEXT)
    return cat


def _block(text: str, name: str) -> str:
    start, end = f"<!-- generated:{name} start -->", f"<!-- generated:{name} end -->"
    assert text.count(start) == 1 and text.count(end) == 1, name
    return text.split(start, 1)[1].split(end, 1)[0]


# ---- live repository -------------------------------------------------------


def test_live_repo_has_no_drift():
    assert render_ideas.main(["--check"]) == 0


def test_live_ideas_index_matches_idea_pages():
    index = REPO_ROOT / "catalog/ideas/index.md"
    ideas = idea_pages()
    if not ideas:
        assert not index.exists()
        return
    table = _block(index.read_text(encoding="utf-8"), "ideas")
    for path in ideas:
        assert f"]({path.parent.name}/README.md)" in table
        assert BANNER in _block(path.read_text(encoding="utf-8"), "idea")


def test_page_helpers_split_the_use_case_glob():
    front, ideas = front_page_pages(), idea_pages()
    assert not set(front) & set(ideas)
    assert sorted(front + ideas) == use_case_pages()


def test_page_helpers_on_tmp_catalog(catalog: Path):
    _write(catalog / "demo/x/README.md", _page("UC-DEMO-01", "Demo", "demo"))
    front = [p.parent.name for p in front_page_pages(catalog)]
    ideas = [p.parent.name for p in idea_pages(catalog)]
    assert front == ["host-page"]
    assert sorted(ideas) == ["alpha-log", "zeta-merged"]
    assert sorted(front_page_pages(catalog) + idea_pages(catalog)) == use_case_pages(catalog)


# ---- tmp catalogs ----------------------------------------------------------


def test_no_ideas_and_no_index_is_a_noop(tmp_path: Path):
    cat = tmp_path / "catalog"
    host = _write(cat / "network-operations/host-page/README.md", _page("UC-OPS-01", "Host", "network-operations"))
    before = host.read_text(encoding="utf-8")
    assert render_ideas.main(["--check"], catalog=cat) == 0
    assert render_ideas.main([], catalog=cat) == 0
    assert host.read_text(encoding="utf-8") == before
    assert not (cat / "ideas/index.md").exists()


def test_index_table_rows(catalog: Path):
    assert render_ideas.main([], catalog=catalog) == 0
    table = _block((catalog / "ideas/index.md").read_text(encoding="utf-8"), "ideas")
    rows = [line for line in table.splitlines() if line.startswith("|")]
    assert rows[0] == "| Idea | Why it's an idea | What would promote it |"
    assert rows[2] == (
        "| [UC-AGOPS-09 Site log reduction](alpha-log/README.md) | Template mining is the usual baseline "
        "| A measured comparison on your own logs |"
    )
    assert rows[3] == (
        "| [UC-OPS-12 Merged idea](zeta-merged/README.md) | Its scope now sits in the knowledge assistant "
        "| A distinct operator need; Measured gain over the host |"
    )
    assert len(rows) == 4


def test_idea_block_after_h1(catalog: Path):
    render_ideas.main([], catalog=catalog)
    plain = (catalog / "ideas/alpha-log/README.md").read_text(encoding="utf-8")
    assert "# Site log reduction\n\n<!-- generated:idea start -->\n" in plain
    assert plain.index("<!-- generated:idea end -->") < plain.index("Intro line.")
    assert _block(plain, "idea") == (
        f"\n\n{BANNER}\n\n"
        "**Why it's an idea:** Template mining is the usual baseline\n\n"
        "**What would promote it:**\n\n"
        "- [ ] A measured comparison on your own logs\n\n"
    )
    assert "<!-- generated:idea end -->\n\nIntro line." in plain
    merged = (catalog / "ideas/zeta-merged/README.md").read_text(encoding="utf-8")
    block = _block(merged, "idea")
    assert "- [ ] A distinct operator need\n- [ ] Measured gain over the host\n" in block
    assert block.endswith(
        "Its scope now sits in [UC-OPS-01 Host recipe](../../network-operations/host-page/README.md).\n\n"
    )
    assert "Its scope now sits in" not in _block(plain, "idea")


def test_render_is_idempotent_and_check_catches_drift(catalog: Path, capsys):
    assert render_ideas.main(["--check"], catalog=catalog) == 1  # markers missing on first run
    assert "catalog/ideas/alpha-log/README.md" in capsys.readouterr().err
    render_ideas.main([], catalog=catalog)
    snapshot = {p: p.read_text(encoding="utf-8") for p in catalog.rglob("*.md")}
    render_ideas.main([], catalog=catalog)
    assert snapshot == {p: p.read_text(encoding="utf-8") for p in catalog.rglob("*.md")}
    assert render_ideas.main(["--check"], catalog=catalog) == 0

    page = catalog / "ideas/alpha-log/README.md"
    edited = page.read_text(encoding="utf-8").replace("idea:** Template mining", "idea:** Hand edit")
    page.write_text(edited, encoding="utf-8")
    assert render_ideas.main(["--check"], catalog=catalog) == 1
    assert "alpha-log/README.md: generated block out of date (idea)" in capsys.readouterr().err

    render_ideas.main([], catalog=catalog)
    index = catalog / "ideas/index.md"
    index.write_text(index.read_text(encoding="utf-8").replace("Merged idea]", "Edited]"), encoding="utf-8")
    assert render_ideas.main(["--check"], catalog=catalog) == 1
    assert "generated block out of date (ideas)" in capsys.readouterr().err


def test_check_does_not_write(catalog: Path):
    page = catalog / "ideas/alpha-log/README.md"
    before = page.read_text(encoding="utf-8")
    render_ideas.main(["--check"], catalog=catalog)
    assert page.read_text(encoding="utf-8") == before


def test_two_start_markers_fail(catalog: Path):
    page = catalog / "ideas/alpha-log/README.md"
    text = page.read_text(encoding="utf-8").replace(
        "Intro line.", "<!-- generated:idea start -->\n<!-- generated:idea start -->\n<!-- generated:idea end -->\nIntro line."
    )
    page.write_text(text, encoding="utf-8")
    with pytest.raises(SystemExit, match="exactly one start and one end marker"):
        render_ideas.main([], catalog=catalog)


def test_pipe_in_why_fails(catalog: Path):
    page = catalog / "ideas/alpha-log/README.md"
    page.write_text(page.read_text(encoding="utf-8").replace("usual baseline", "usual | baseline"), encoding="utf-8")
    before = (catalog / "ideas/zeta-merged/README.md").read_text(encoding="utf-8")
    with pytest.raises(SystemExit, match=r"cannot hold '\|'"):
        render_ideas.main([], catalog=catalog)
    assert (catalog / "ideas/zeta-merged/README.md").read_text(encoding="utf-8") == before


def test_missing_index_fails_when_ideas_exist(catalog: Path):
    (catalog / "ideas/index.md").unlink()
    with pytest.raises(SystemExit, match="catalog/ideas/index.md is missing"):
        render_ideas.main(["--check"], catalog=catalog)


def test_idea_outside_ideas_folder_fails(catalog: Path):
    _write(catalog / "security/stray/README.md", _page("UC-SEC-09", "Stray", "security", IDEA_PLAIN))
    with pytest.raises(SystemExit, match="catalog/ideas/"):
        render_ideas.main([], catalog=catalog)


def test_unknown_merge_host_fails(catalog: Path):
    page = catalog / "ideas/zeta-merged/README.md"
    page.write_text(page.read_text(encoding="utf-8").replace('"UC-OPS-01"\n', '"UC-OPS-99"\n'), encoding="utf-8")
    with pytest.raises(SystemExit, match="UC-OPS-99"):
        render_ideas.main([], catalog=catalog)
