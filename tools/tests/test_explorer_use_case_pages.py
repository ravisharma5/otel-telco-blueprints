"""Built use-case pages of the explorer.

Each published use case gets one page at use-cases/<slug>/ holding every setup
state (setups x batch values) the exporter wrote to explorer.json. Setup-dependent
parts carry `data-state` (the main block in "Recommended for your setup") or
`data-for-state` (the rail options count, the thresholds quantized line, the
advanced options, and the Models card) with the value "<setup>|<batch>". Only the
default state lacks `hidden`; the page script only toggles hidden, selected,
checked, and aria attributes.

Every expected string is read from explorer.json or copy.md; counts are never
typed here, so the page stays right with or without an option.
"""

from __future__ import annotations

import re

import pytest
import yaml

from tools.tests.conftest import REPO_ROOT
from tools.tests.test_explorer_pages import BASE, COPY_PATH, _data, _Node, _Tree

# Provisional uncompressed ceiling per built use-case page, in kilobytes. Set to the
# measured maximum plus 25%, rounded up to the next 25 KB, capped at 400.
PAGE_SIZE_LIMIT_KB = 350
FRAMEWORK_INDEX = REPO_ROOT / "framework/index.md"
SECTION_IDS = ["why", "setup", "needs", "recipe"]
PLAYBOOKS = "https://github.com/openshift-psap/inference-playbooks/"
UNSAFE_DOM = ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write")


def _copy():
    text = COPY_PATH.read_text(encoding="utf-8")
    return yaml.safe_load(re.match(r"^---\n(.*?)\n---\n", text, re.S).group(1))


def _plain(text):
    """Data text as the page shows it: code spans lose their backticks."""
    return " ".join(text.replace("`", "").split())


def _squash(text):
    """Text with all whitespace removed; the tree joins inline children with spaces."""
    return re.sub(r"\s+", "", text)


def _num(value):
    return f"{value:g}"


def _key(setup, batch):
    return f"{setup}|{batch}"


def _keys(data):
    return [_key(s["id"], b) for s in data["setups"] for b in ("yes", "no")]


def _default_key(data):
    return _key(data["default"]["setup"], data["default"]["batch"])


def _states(uc):
    for setup, by_batch in uc["states"].items():
        for batch, state in by_batch.items():
            yield _key(setup, batch), setup, state


def _page_path(dist, uc):
    return dist / "use-cases" / uc["slug"] / "index.html"


def _page(dist, uc):
    tree = _Tree()
    tree.feed(_page_path(dist, uc).read_text(encoding="utf-8"))
    return tree


def _blocks(tree):
    return tree.root.find_all(lambda n: "data-state" in n.attrs)


def _parts(tree, key):
    """Every setup-dependent element for one state key."""
    return tree.root.find_all(
        lambda n: n.attrs.get("data-state") == key or n.attrs.get("data-for-state") == key
    )


def _in_parts(tree, key, pred):
    hits = []
    for part in _parts(tree, key):
        hits += part.find_all(pred)
    return hits


def _state_of(node):
    while node is not None:
        if isinstance(node, _Node):
            key = node.attrs.get("data-state") or node.attrs.get("data-for-state")
            if key:
                return key
        node = node.parent
    return None


def _setup(data, setup_id):
    return next(s for s in data["setups"] if s["id"] == setup_id)


def _band_word(copy, band):
    return copy["use_case"]["fit"]["bands"][band]


def _option_order(options):
    helps = [o for o in options if o["state"] == "helps"]
    na_help = [o for o in options if o["state"] == "not-applicable" and o["would_help"]]
    rest = [o for o in options if o not in helps and o not in na_help]
    return helps + na_help + rest


def _shown_by_default(option):
    return option["state"] == "helps" or (option["state"] == "not-applicable" and option["would_help"])


def _readiness_questions():
    text = FRAMEWORK_INDEX.read_text(encoding="utf-8")
    table = text.split("### The ten questions", 1)[1].split("###", 1)[0]
    questions = []
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].isdigit():
            questions.append(cells[1])
    assert questions, "no readiness questions found in framework/index.md"
    return questions


@pytest.fixture(scope="module")
def data():
    return _data()


@pytest.fixture(scope="module")
def copy():
    return _copy()


# ---------- pages and state blocks ----------


@pytest.mark.site_output
def test_one_page_per_use_case(explorer_dist, data):
    root = explorer_dist / "use-cases"
    built = sorted(p.name for p in root.iterdir() if p.is_dir())
    assert built == sorted(uc["slug"] for uc in data["use_cases"])
    assert [p.name for p in root.iterdir() if p.is_file()] == []
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        title = tree.root.find_all(lambda n: n.tag == "title")[0].text()
        assert title == f"{uc['title']} · OTel Telco Blueprints"
        h1 = tree.root.find_all(lambda n: n.tag == "h1")
        assert len(h1) == 1 and h1[0].text() == uc["title"]


@pytest.mark.site_output
def test_every_state_block_present(explorer_dist, data):
    default = _default_key(data)
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        blocks = _blocks(tree)
        keys = [b.attrs["data-state"] for b in blocks]
        assert sorted(keys) == sorted(_keys(data)), uc["slug"]
        assert len(keys) == len(set(keys))
        visible = [b.attrs["data-state"] for b in blocks if "hidden" not in b.attrs]
        assert visible == [default]
        for part in tree.root.find_all(lambda n: "data-for-state" in n.attrs):
            assert ("hidden" in part.attrs) == (part.attrs["data-for-state"] != default)
            assert part.attrs["data-for-state"] in keys


@pytest.mark.site_output
def test_sections_in_order(explorer_dist, data, copy):
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        sections = [n for n in tree.root.find_all(lambda n: n.tag == "section" and "id" in n.attrs)]
        assert [s.attrs["id"] for s in sections if s.attrs["id"] in SECTION_IDS] == SECTION_IDS
        for section in sections:
            if section.attrs["id"] not in SECTION_IDS:
                continue
            heads = section.find_all(lambda n: n.tag in {"h1", "h2"})
            assert heads and heads[0].attrs.get("tabindex") == "-1", section.attrs["id"]
        h2 = [n.text() for n in tree.root.find_all(lambda n: n.tag == "h2")]
        headings = copy["use_case"]["sections"]["headings"]
        for key in ("setup", "needs", "recipe"):
            assert headings[key] in h2


# ---------- rail ----------


@pytest.mark.site_output
def test_rail_contents(explorer_dist, data, copy):
    rail_copy = copy["use_case"]["rail"]
    setup_copy = copy["use_case"]["setup"]
    nav_labels = copy["use_case"]["sections"]["nav"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        asides = tree.root.find_all(
            lambda n: n.tag == "aside" and n.attrs.get("aria-label") == rail_copy["label"]
        )
        assert len(asides) == 1, uc["slug"]
        rail = asides[0]
        for key in ("slots", "blueprints", "tiers"):
            tile = rail.find_all(lambda n, k=key: n.attrs.get("data-count") == k)
            assert len(tile) == 1
            number = tile[0].find_all(lambda n: n.has_class("count-number"))
            assert number and number[0].text() == str(uc["counts"][key])
        # Setup select, with the five setups in order and a visible label.
        selects = rail.find_all(lambda n: n.tag == "select")
        assert len(selects) == 1
        select = selects[0]
        labels = rail.find_all(lambda n: n.tag == "label" and n.attrs.get("for") == select.attrs.get("id"))
        assert len(labels) == 1 and labels[0].text() == setup_copy["headings"]["question"]
        options = select.find_all(lambda n: n.tag == "option")
        assert [(o.attrs["value"], o.text()) for o in options] == [(s["id"], s["label"]) for s in data["setups"]]
        assert [o.attrs["value"] for o in options if "selected" in o.attrs] == [data["default"]["setup"]]
        forms = rail.find_all(lambda n: "data-setup-ids" in n.attrs)
        assert len(forms) == 1
        assert forms[0].attrs["data-setup-ids"].split() == [s["id"] for s in data["setups"]]
        # Ampere helper sits with the select, tied by aria-describedby.
        helper_id = select.attrs.get("aria-describedby")
        assert helper_id
        helper = rail.find_all(lambda n, i=helper_id: n.attrs.get("id") == i)
        assert helper and setup_copy["notes"]["ampere"] in helper[0].text()
        # Batch question: a fieldset with a legend and two radios.
        fieldsets = rail.find_all(lambda n: n.tag == "fieldset")
        assert len(fieldsets) == 1
        legend = fieldsets[0].find_all(lambda n: n.tag == "legend")
        assert legend and legend[0].text() == setup_copy["headings"]["batch"]
        radios = fieldsets[0].find_all(lambda n: n.tag == "input" and n.attrs.get("type") == "radio")
        assert [r.attrs["value"] for r in radios] == ["yes", "no"]
        assert len({r.attrs["name"] for r in radios}) == 1
        assert [r.attrs["value"] for r in radios if "checked" in r.attrs] == [data["default"]["batch"]]
        texts = fieldsets[0].text()
        for value in ("yes", "no"):
            assert setup_copy["batch_options"][value] in texts
        # Options count per state.
        for key, _, state in _states(uc):
            counts = [
                n for n in rail.find_all(lambda n, k=key: n.attrs.get("data-for-state") == k)
                if n.has_class("options-count")
            ]
            assert len(counts) == 1, key
            number = counts[0].find_all(lambda n: n.has_class("count-number"))
            assert number[0].text() == str(state["options_worth_testing"])
            assert setup_copy["count_caption"] in counts[0].text()
        # Live region and the invalid-setup notice.
        live = rail.find_all(lambda n: n.attrs.get("aria-live") == "polite")
        assert len(live) == 1 and live[0].text() == ""
        notice = rail.find_all(lambda n: "data-invalid-notice" in n.attrs)
        assert len(notice) == 1
        assert notice[0].attrs.get("role") == "status" and "hidden" in notice[0].attrs
        assert setup_copy["notes"]["invalid"] in notice[0].text()
        # On this page.
        navs = rail.find_all(lambda n: n.tag == "nav" and n.attrs.get("aria-label") == rail_copy["headings"]["nav"])
        assert len(navs) == 1
        links = navs[0].find_all(lambda n: n.tag == "a")
        assert [a.attrs["href"] for a in links] == ["#" + s for s in SECTION_IDS]
        assert [a.text() for a in links] == [nav_labels[s] for s in SECTION_IDS]
        # Recipe button.
        primary = rail.find_all(lambda n: n.tag == "a" and n.has_class("primary-button"))
        assert len(primary) == 1
        assert primary[0].attrs["href"] == BASE + uc["recipe_url"]
        assert copy["buttons"]["open_recipe"] in primary[0].text()


# ---------- recommended for your setup ----------


@pytest.mark.site_output
def test_tier_cards_match_state(explorer_dist, data, copy):
    tier_labels = copy["home"]["gallery"]["filters"]["tiers"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, state in _states(uc):
            cards = _in_parts(tree, key, lambda n: n.has_class("tier-card"))
            assert [c.attrs["data-tier"] for c in cards] == [t["tier"] for t in state["tiers"]], key
            for card, tier in zip(cards, state["tiers"]):
                text = card.text()
                assert tier_labels[tier["tier"]] in text
                assert tier["note"] in text
                tagged = copy["use_case"]["tiers"]["your_setup"] in text
                assert tagged == tier["matches_setup"], (key, tier["tier"])
                for slot in tier["slots"]:
                    assert slot["slot_name"] in text


@pytest.mark.site_output
def test_fit_bars_match_state(explorer_dist, data, copy):
    fit = copy["use_case"]["fit"]
    found_footnote = False
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, setup_id, state in _states(uc):
            bars = _in_parts(tree, key, lambda n: n.has_class("fit-bar"))
            assert len(bars) == len(state["fit"]), key
            if _setup(data, setup_id)["tier"] == "core":
                assert bars == []
                continue
            for bar, entry in zip(bars, state["fit"]):
                text = bar.text()
                weights = fit["weights"].replace("{gb}", _num(entry["weights_gb"])).replace(
                    "{total}", _num(entry["total_gb"])
                )
                assert weights in text, (key, text)
                pct = fit["pct"].replace("{pct}", str(entry["pct"])).replace(
                    "{band}", _band_word(copy, entry["band"])
                )
                assert pct in text, (key, text)
                assert fit["messages"][entry["message_id"]] in text
                if entry["message_id"] == "too-tight-after-fp8":
                    assert "Use FP8" not in text, (key, text)
                assert len(bar.find_all(lambda n: n.has_class("fit-tick"))) == 2
                graphic = bar.find_all(lambda n: n.has_class("fit-track"))
                assert graphic and graphic[0].attrs.get("aria-hidden") == "true"
                if entry["gpu_count"] > 1:
                    names = ", ".join(s["slot_name"] for s in entry["slots"])
                    title = fit["gpu_title"].replace("{n}", str(entry["gpu_index"])).replace(
                        "{count}", str(entry["gpu_count"])
                    ).replace("{slots}", names)
                    assert title in text
            notes = _in_parts(tree, key, lambda n: n.has_class("fit-footnote"))
            assert len(notes) == 1 and notes[0].text() == fit["footnote"]
            found_footnote = True
    assert found_footnote


@pytest.mark.site_output
def test_too_tight_is_stated(explorer_dist, data, copy):
    # A setup that cannot hold the use case says so in words, never hides it.
    fit = copy["use_case"]["fit"]
    seen = 0
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, state in _states(uc):
            for entry in state["fit"]:
                if entry["band"] != "too-tight":
                    continue
                text = " ".join(p.text() for p in _parts(tree, key))
                assert _band_word(copy, "too-tight") in text
                assert fit["messages"][entry["message_id"]] in text
                seen += 1
    assert seen, "expected at least one too-tight state in the data"


@pytest.mark.site_output
def test_key_settings_match_state(explorer_dist, data, copy):
    cols = copy["use_case"]["settings"]["columns"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, state in _states(uc):
            tables = _in_parts(tree, key, lambda n: n.tag == "table" and n.has_class("settings-table"))
            assert len(tables) == 1, key
            heads = [th.text() for th in tables[0].find_all(lambda n: n.tag == "th" and n.attrs.get("scope") == "col")]
            assert heads == [cols["setting"], cols["value"], cols["why"]]
            rows = tables[0].find_all(lambda n: n.tag == "tr" and "data-flag" in n.attrs)
            assert len(rows) == len(state["flags"]), key
            for row, flag in zip(rows, state["flags"]):
                text = _squash(row.text())
                assert _squash(_plain(flag["setting"])) in text
                assert _squash(_plain(flag["why"])) in text
                if flag["value"]:
                    assert _squash(_plain(flag["value"])) in text


@pytest.mark.site_output
def test_thresholds_have_no_values(explorer_dist, data, copy):
    th_copy = copy["use_case"]["thresholds"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        tables = tree.root.find_all(lambda n: n.tag == "table" and n.has_class("thresholds-table"))
        assert len(tables) == 1, "the thresholds table renders once, outside the state blocks"
        assert _state_of(tables[0]) is None
        heads = [th.text() for th in tables[0].find_all(lambda n: n.tag == "th" and n.attrs.get("scope") == "col")]
        assert heads == [th_copy["columns"]["parameter"], th_copy["columns"]["owner"]]
        rows = tables[0].find_all(lambda n: n.tag == "tr" and n.find_all(lambda c: c.tag == "td"))
        assert [[c.text() for c in r.children if isinstance(c, _Node)] for r in rows] == uc["parameters"]
        page_text = tree.root.text()
        assert th_copy["notes"]["no_defaults"] in page_text
        lines = tree.root.find_all(lambda n: n.has_class("quantized-check"))
        keys = sorted(_state_of(n) for n in lines)
        expected = sorted(k for k, _, s in _states(uc) if s["quantized_check"])
        assert keys == expected, uc["slug"]
        assert all(n.text() == th_copy["notes"]["quantized"] for n in lines)


@pytest.mark.site_output
def test_option_cards(explorer_dist, data, copy):
    opt = copy["use_case"]["advanced"]
    reasons = copy["use_case"]["reasons"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, state in _states(uc):
            cards = _in_parts(tree, key, lambda n: n.has_class("option-card"))
            assert len(cards) == len(state["options"]), key
            expected = _option_order(state["options"])
            assert [c.attrs["data-option-id"] for c in cards] == [o["id"] for o in expected], key
            for card, option in zip(cards, expected):
                text = card.text()
                assert option["name"] in text
                assert option["engine"] in text
                assert ("hidden" in card.attrs) == (not _shown_by_default(option)), (key, option["id"])
                if option["state"] == "helps":
                    assert opt["helps"].split("{")[0].strip() in text
                    assert _squash(_plain(option["reason_text"])) in _squash(text)
                elif option["state"] == "little":
                    assert opt["little"] in text
                else:
                    assert opt["not_applicable"].split("{")[0].strip() in text
                    reason = option["reason_text"] or reasons[option["reason_id"]]
                    assert _squash(_plain(reason)) in _squash(text)
                if option.get("fit_note_id"):
                    note = copy["use_case"]["advanced"]["fit_notes"][option["fit_note_id"]]
                    assert _squash(note) in _squash(text), (key, option["id"])
                assert _squash(_plain(option["what"])) in _squash(text)
                assert _squash(_plain(option["check"])) in _squash(text)
                for related in option["related"]:
                    links = card.find_all(lambda n, u=related["url"]: n.tag == "a" and n.attrs.get("href") == u)
                    assert len(links) == 1, (key, option["id"])
                    assert related["url"].startswith(PLAYBOOKS)
                    assert related["title"] in links[0].text()
                    hidden = links[0].find_all(lambda n: n.has_class("visually-hidden"))
                    assert hidden and hidden[0].text() == copy["notes"]["external"]


@pytest.mark.site_output
def test_toggle_label_count(explorer_dist, data, copy):
    template = copy["buttons"]["show_all_options"]
    assert "{count}" in template
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, state in _states(uc):
            toggles = _in_parts(tree, key, lambda n: n.tag == "button" and n.has_class("options-toggle"))
            assert len(toggles) == 1, key
            toggle = toggles[0]
            assert toggle.text() == template.replace("{count}", str(len(state["options"])))
            assert toggle.attrs.get("aria-pressed") == "false"
            target = toggle.attrs.get("aria-controls")
            assert target and tree.root.find_all(lambda n, t=target: n.attrs.get("id") == t)
    for html in (explorer_dist / "use-cases").rglob("*.html"):
        assert "{count}" not in html.read_text(encoding="utf-8"), html


# ---------- what you need and the recipe ----------


@pytest.mark.site_output
def test_model_variants(explorer_dist, data, copy):
    models = copy["use_case"]["models"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, state in _states(uc):
            parts = [p for p in _parts(tree, key) if p.has_class("models-part")]
            assert len(parts) == 1, key
            text = parts[0].text()
            rows = parts[0].find_all(lambda n: n.tag == "tr" and n.find_all(lambda c: c.tag == "td"))
            assert len(rows) == len(state["variants"])
            for variant in state["variants"]:
                assert variant["slot_name"] in text
                if variant["operator_made"]:
                    template = models["operator_made"].replace(
                        "{precision}", models["precision"][variant["precision"]]
                    )
                else:
                    template = models["published"]
                assert template.replace("{checkpoint}", variant["checkpoint"]) in text, (key, variant)


@pytest.mark.site_output
def test_platform_and_approvals_once(explorer_dist, data, copy):
    needs = copy["use_case"]["needs"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for cls, rows in (("platform-table", uc["platform_rows"]), ("approvals-table", uc["approvals"])):
            tables = tree.root.find_all(lambda n, c=cls: n.tag == "table" and n.has_class(c))
            assert len(tables) == 1 and _state_of(tables[0]) is None
            body = tables[0].find_all(lambda n: n.tag == "tr" and n.find_all(lambda c: c.tag == "td"))
            assert len(body) == len(rows)
            for tr, row in zip(body, rows):
                for cell in row:
                    assert _squash(_plain(cell)) in _squash(tr.text())
        assert needs["notes"]["replaceable"] in tree.root.text()


@pytest.mark.site_output
def test_why_section(explorer_dist, data, copy):
    stages = copy["use_case"]["stages"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        section = tree.root.find_all(lambda n: n.tag == "section" and n.attrs.get("id") == "why")[0]
        text = section.text()
        for value in (uc["card"]["summary"], uc["card"]["outcome"], uc["card"]["audience"], uc["card"]["risk"]):
            assert value in text
        assert " · ".join(uc["card"]["measures"]) in text
        assert stages[uc["stage"]["id"]] in text
        assert _state_of(section) is None


@pytest.mark.site_output
def test_no_readiness_questions(explorer_dist, data, copy):
    questions = _readiness_questions()
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        text = tree.root.text()
        assert "The ten questions" not in text
        for question in questions:
            assert question not in text, question
        cards = tree.root.find_all(lambda n: n.has_class("recipe-card"))
        assert len(cards) == 1
        assert "readiness questions" in cards[0].text()
        assert copy["use_case"]["recipe"]["title"].replace("{title}", uc["title"]) in cards[0].text()


@pytest.mark.site_output
def test_no_overlay_and_clean_recipe_links(explorer_dist, data):
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        recipe_links = [
            a.attrs["href"]
            for a in tree.root.find_all(lambda n: n.tag == "a" and "recipes/" in n.attrs.get("href", ""))
        ]
        assert BASE + uc["recipe_url"] in recipe_links
        assert all("?" not in href and "#" not in href for href in recipe_links)
        assert not tree.root.find_all(lambda n: n.has_class("setup-overlay"))


# ---------- copy, no-JS, size, script ----------


def test_reason_ids_have_copy():
    data = _data()
    reasons = _copy()["use_case"]["reasons"]
    ids = {
        o["reason_id"]
        for uc in data["use_cases"]
        for _, _, state in _states(uc)
        for o in state["options"]
        if o["reason_id"]
    }
    assert ids, "expected reason ids in the data"
    assert sorted(ids - set(reasons)) == []


@pytest.mark.site_output
def test_no_js_notes(explorer_dist, data, copy):
    notes = copy["notes"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        noscript = tree.root.find_all(lambda n: n.tag == "noscript")
        text = " ".join(n.text() for n in noscript)
        assert notes["no_js"] in text and notes["no_js_link"] in text, uc["slug"]
        forms = tree.root.find_all(lambda n: "data-setup-form" in n.attrs)
        assert len(forms) == 1 and "hidden" in forms[0].attrs
        toggles = tree.root.find_all(lambda n: n.has_class("options-toggle"))
        assert toggles and all(_state_of(t) for t in toggles)


@pytest.mark.site_output
def test_use_case_page_size(explorer_dist, data):
    sizes = {}
    for uc in data["use_cases"]:
        sizes[uc["slug"]] = _page_path(explorer_dist, uc).stat().st_size / 1024
    over = {slug: round(kb) for slug, kb in sizes.items() if kb > PAGE_SIZE_LIMIT_KB}
    assert over == {}, f"pages over {PAGE_SIZE_LIMIT_KB} KB: {over}"


def _page_scripts(explorer_dist, tree):
    text = "".join(tree.scripts)
    for node in tree.root.find_all(lambda n: n.tag == "script" and "src" in n.attrs):
        src = node.attrs["src"]
        assert src.startswith(BASE), src
        text += (explorer_dist / src[len(BASE):]).read_text(encoding="utf-8")
    return text


@pytest.mark.site_output
def test_script_safety(explorer_dist, data):
    for uc in data["use_cases"]:
        script = _page_scripts(explorer_dist, _page(explorer_dist, uc))
        assert "URLSearchParams" in script and "replaceState" in script, uc["slug"]
        assert "pushState" not in script
        for banned in UNSAFE_DOM + ("localStorage", "sessionStorage", "document.cookie", "fetch("):
            assert banned not in script, f"{uc['slug']}: {banned}"
    for js in explorer_dist.rglob("*.js"):
        text = js.read_text(encoding="utf-8")
        for banned in UNSAFE_DOM:
            assert banned not in text, f"{js.name}: {banned}"
