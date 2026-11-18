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
    return [_key(s["id"], b) for s in data["setups"] for b in s["batch_values"]]


def _cpu_setups(data):
    return [s for s in data["setups"] if s["cpu_only"]]


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
        # At a glance keeps the domain, title, and stage; the counter tiles are gone.
        glance = rail.find_all(lambda n: n.has_class("glance"))
        assert len(glance) == 1, uc["slug"]
        assert uc["title"] in glance[0].text() and uc["stage"]["label"] in glance[0].text()
        assert rail.find_all(lambda n: "data-count" in n.attrs) == []
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
        default_setup = _setup(data, data["default"]["setup"])
        default_batch = setup_copy["batch_sentence"][data["default"]["batch"]]
        texts = notice[0].find_all(lambda n: "data-invalid" in n.attrs)
        assert sorted(t.attrs["data-invalid"] for t in texts) == ["batch", "both", "setup"]
        for t in texts:
            assert "hidden" in t.attrs
            want = setup_copy["notes"][f"invalid_{t.attrs['data-invalid']}"]
            want = want.replace("{setup}", default_setup["label"]).replace("{batch}", default_batch)
            assert t.text() == want
            assert "{" not in t.text()
        assert default_setup["label"] in texts[0].text() or default_batch in texts[0].text()
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
            if _setup(data, setup_id)["tier"] == "core" or not state["fit"]:
                assert bars == []
                assert _in_parts(tree, key, lambda n: n.has_class("fit-footnote")) == [], key
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
                ticks = bar.find_all(lambda n: n.has_class("fit-tick"))
                bands = data["fit_bands"]
                assert [t.attrs.get("style") for t in ticks] == [
                    f"left: {bands['fits_max_pct']}%",
                    f"left: {bands['tight_max_pct']}%",
                ], key
                graphic = bar.find_all(lambda n: n.has_class("fit-track"))
                assert graphic and graphic[0].attrs.get("aria-hidden") == "true"
                if entry["gpu_count"] > 1:
                    names = ", ".join(s["slot_name"] for s in entry["slots"])
                    title = fit["gpu_title"].replace("{n}", str(entry["gpu_index"])).replace(
                        "{count}", str(entry["gpu_count"])
                    ).replace("{slots}", names)
                    assert title in text
            notes = _in_parts(tree, key, lambda n: n.has_class("fit-footnote"))
            footnote = fit["footnote"].replace("{fits}", str(data["fit_bands"]["fits_max_pct"]))
            footnote = footnote.replace("{tight}", str(data["fit_bands"]["tight_max_pct"]))
            assert len(notes) == 1 and notes[0].text() == footnote
            found_footnote = True
    assert found_footnote


def test_fit_bands_never_typed():
    # The 60/80 band edges come from data/serving/setups.yaml through explorer.json.
    copy = _copy()
    footnote = copy["use_case"]["fit"]["footnote"]
    assert "{fits}" in footnote and "{tight}" in footnote
    assert not re.search(r"\d+%", footnote), footnote
    bar = (REPO_ROOT / "explorer/src/components/FitBar.astro").read_text(encoding="utf-8")
    assert not re.search(r"left:\s*\d", bar), "FitBar types a tick position"


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
            if not state["flags"]:
                assert tables == [], key
                continue
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


def _links(node):
    return [(a.attrs.get("href"), a.text()) for a in node.find_all(lambda n: n.tag == "a")]


@pytest.mark.site_output
def test_key_settings_link_their_sources(explorer_dist, data, copy):
    # Each per-setup row links its source; each slot block links its sources on its
    # group row. Link text is the label of that source's row in the serving page Sources table.
    external = copy["notes"]["external"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, state in _states(uc):
            if not state["flags"]:
                continue
            table = _in_parts(tree, key, lambda n: n.tag == "table" and n.has_class("settings-table"))[0]
            rows = table.find_all(lambda n: n.tag == "tr" and "data-flag" in n.attrs)
            for row, flag in zip(rows, state["flags"]):
                if flag["scope"] != "setup":
                    continue
                got = [(href, _squash(text)) for href, text in _links(row)]
                want = [(s["url"], _squash(f"{s['label']} ↗ {external}")) for s in flag["sources"]]
                assert got == want, (uc["slug"], key, flag["setting"])
            groups = table.find_all(lambda n: n.tag == "th" and n.attrs.get("scope") == "rowgroup")
            slot_flags = {}
            for flag in state["flags"]:
                if flag["scope"] != "setup":
                    slot_flags.setdefault(flag["scope"], flag["sources"])
            slot_groups = [g for g in groups if g.text().split(copy["use_case"]["settings"]["sources"])[0].strip() in slot_flags]
            assert len(slot_groups) == len(slot_flags), key
            for group in slot_groups:
                scope = group.text().split(copy["use_case"]["settings"]["sources"])[0].strip()
                assert [href for href, _ in _links(group)] == [s["url"] for s in slot_flags[scope]], (key, scope)


@pytest.mark.site_output
def test_option_sources_link_resolves(explorer_dist, site_dir, copy):
    # The options' sources note links the serving page's options table, which lists
    # every option's sources; the anchor must exist in the built docs.
    adv = copy["use_case"]["advanced"]
    path, _, anchor = adv["sources_path"].partition("#")
    page = site_dir / path / "index.html"
    assert page.is_file(), page
    assert f'id="{anchor}"' in page.read_text(encoding="utf-8")
    for html in (explorer_dist / "use-cases").rglob("index.html"):
        tree = _Tree()
        tree.feed(html.read_text(encoding="utf-8"))
        notes = tree.root.find_all(lambda n: n.has_class("option-sources"))
        assert len(notes) == 1 and _state_of(notes[0]) is None, html
        assert _links(notes[0]) == [(BASE + adv["sources_path"], adv["sources_link"])]


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
                    if option["reason_id"]:
                        phrases = [opt["slot_phrases"][r] for r in option["reason_roles"]]
                        assert phrases and all(_squash(p) in _squash(text) for p in phrases), (key, option["id"])
                        form = "one" if len(phrases) == 1 else "other"
                        lead = opt["helps_reasons"][option["reason_id"]][form].split("{")[0]
                        assert _squash(lead) in _squash(text), (key, option["id"])
                    else:
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


# Words that name a slot in card text, matched case-sensitively.
SLOT_WORDS = {
    "llm-large": r"\b(?:31B|large LLM)\b",
    "llm-small": r"\bsmall LLM\b",
    "decision": r"\bDecision\b",
    "safety": r"\bSafety\b",
    "classification": r"\bClassification\b",
    "embedding": r"\bEmbedding\b",
    "reranker": r"\bReranker\b",
}


@pytest.mark.site_output
def test_fp8_card_names_only_swapped_slots(explorer_dist, data):
    # Where FP8 builds help, the card's reason names exactly the slots that got an
    # FP8 build in this state (the Models card), and no other slot.
    seen = 0
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, state in _states(uc):
            swapped = {v["role"] for v in state["variants"] if v["operator_made"]}
            if not swapped:
                continue
            cards = _in_parts(tree, key, lambda n: n.attrs.get("data-option-id") == "fp8-regional")
            box = cards[0].find_all(lambda n: n.has_class("applicability"))[0].text()
            named = {role for role, pattern in SLOT_WORDS.items() if re.search(pattern, box)}
            assert named == swapped, (uc["slug"], key, box)
            seen += 1
    assert seen


@pytest.mark.site_output
def test_rail_count_matches_helps_cards(explorer_dist, data):
    # The rail's "options worth testing" number is the number of "Helps here" cards
    # the same state shows, counted in the built page.
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, _ in _states(uc):
            counts = _in_parts(tree, key, lambda n: n.has_class("count-number"))
            helps = _in_parts(tree, key, lambda n: n.has_class("option-card") and n.has_class("state-helps"))
            assert len(counts) == 1, key
            assert counts[0].text() == str(len(helps)), (uc["slug"], key)


@pytest.mark.site_output
def test_toggle_label_count(explorer_dist, data, copy):
    template = copy["buttons"]["show_all_options"]
    assert "{count}" in template
    cpu = {s["id"] for s in _cpu_setups(data)}
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, setup_id, state in _states(uc):
            toggles = _in_parts(tree, key, lambda n: n.tag == "button" and n.has_class("options-toggle"))
            if setup_id in cpu:
                assert toggles == [], key
                continue
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
            others = state["other_tier_variants"]
            assert len(rows) == len(state["variants"]) + len(others), key
            # One group row per tier, the setup's own tier first and marked as yours.
            groups = parts[0].find_all(lambda n: n.tag == "th" and n.attrs.get("scope") == "rowgroup")
            tiers = [state["variants"][0]["tier"]] if state["variants"] else []
            tiers += [t for t in dict.fromkeys(v["tier"] for v in others)]
            assert len(groups) == len(tiers), key
            tier_labels = copy["home"]["gallery"]["filters"]["tiers"]
            for group, tier in zip(groups, tiers):
                assert tier_labels[tier] in group.text()
            if state["variants"]:
                assert copy["use_case"]["tiers"]["your_setup"] in groups[0].text()
            for tier in dict.fromkeys(v["tier"] for v in others):
                assert models["other_tier"][tier] in text, (key, tier)
            for variant in others:
                assert variant["slot_name"] in text
                assert models["published"].replace("{checkpoint}", variant["checkpoint"]) in text
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
def test_no_readiness_question_text_on_any_page(explorer_dist):
    """The ten questions stay in the recipes: no built page reproduces one."""
    questions = _readiness_questions()
    for html in explorer_dist.rglob("*.html"):
        text = html.read_text(encoding="utf-8")
        for question in questions:
            assert question not in text, f"{html.relative_to(explorer_dist)}: {question}"


@pytest.mark.site_output
def test_depth_chip_in_header(explorer_dist, data, copy):
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        why = tree.root.find_all(lambda n: n.attrs.get("id") == "why")[0]
        chips = [n.text() for n in why.find_all(lambda n: n.has_class("depth-chip"))]
        assert chips == [copy["depth"][uc["depth"]["id"]]] == [uc["depth"]["label"]], uc["slug"]


@pytest.mark.site_output
def test_you_bring_row(explorer_dist, data, copy):
    why_copy = copy["use_case"]["why"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        why = tree.root.find_all(lambda n: n.attrs.get("id") == "why")[0]
        heads = why.find_all(lambda n: n.tag == "th" and n.text().strip() == why_copy["rows"]["bring"])
        assert len(heads) == 1, uc["slug"]
        row = heads[0].parent
        text = _squash(row.text())
        assert _squash(uc["adaptation"]["rung_label"]) in text, uc["slug"]
        assert copy["adaptation"]["rung"][uc["adaptation"]["rung"]] == uc["adaptation"]["rung_label"]
        for item in uc["adaptation"]["expertise"]:
            assert _squash(item["label"]).lower() in text.lower(), (uc["slug"], item["label"])
        links = [a.attrs.get("href", "") for a in row.find_all(lambda n: n.tag == "a")]
        assert links == [BASE + "platform/bring-your-own-data/"], (uc["slug"], links)


@pytest.mark.site_output
def test_sandbox_chip_in_header(explorer_dist, data, copy):
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        headers = tree.root.find_all(lambda n: n.has_class("header-chips"))
        assert len(headers) == 1, uc["slug"]
        chips = headers[0].find_all(lambda n: n.has_class("sandbox-chip"))
        fit = uc["sandbox"]["fit"]
        assert [c.text().strip() for c in chips] == [copy["sandbox"]["fit"][fit]], uc["slug"]
        assert chips[0].has_class(f"sandbox-{fit}"), uc["slug"]
        assert not chips[0].has_class("depth-chip")


@pytest.mark.site_output
def test_sandbox_row(explorer_dist, data, copy):
    why_copy = copy["use_case"]["why"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        why = tree.root.find_all(lambda n: n.attrs.get("id") == "why")[0]
        heads = why.find_all(lambda n: n.tag == "th" and n.text().strip() == why_copy["rows"]["sandbox"])
        assert len(heads) == 1, uc["slug"]
        text = _squash(heads[0].parent.text())
        assert _squash(uc["sandbox"]["label"]) in text, uc["slug"]
        assert _squash(uc["sandbox"]["why"]) in text, uc["slug"]
        links = [a.attrs.get("href", "") for a in heads[0].parent.find_all(lambda n: n.tag == "a")]
        assert links == [BASE + "platform/security-identity-sandbox/#when-a-use-case-needs-a-sandbox"], links


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


@pytest.mark.site_output
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
    helps_reasons = _copy()["use_case"]["advanced"]["helps_reasons"]
    assert sorted(ids - set(reasons) - set(helps_reasons)) == []


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


@pytest.mark.site_output
def test_toggle_hidden_and_section_nav_current(explorer_dist, data, copy):
    """Without scripts the options toggle does nothing, so it ships hidden. A use-case page
    sits in the Use cases section, so its nav link is the current section, not the page."""
    use_cases = next(i for i in copy["nav"]["items"] if i["path"] == "")
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        toggles = tree.root.find_all(lambda n: n.has_class("options-toggle"))
        assert toggles, uc["slug"]
        assert all("hidden" in t.attrs for t in toggles), uc["slug"]
        links = tree.root.find_all(lambda n: n.tag == "a" and n.attrs.get("href") == BASE + use_cases["path"])
        nav = [a for a in links if a.text().strip() == use_cases["label"]]
        assert nav, uc["slug"]
        assert all(a.attrs.get("aria-current") == "true" for a in nav), uc["slug"]
    home = _Tree()
    home.feed((explorer_dist / "index.html").read_text(encoding="utf-8"))
    links = home.root.find_all(lambda n: n.tag == "a" and n.attrs.get("aria-current"))
    assert [(a.text().strip(), a.attrs["aria-current"]) for a in links] == [(use_cases["label"], "page")]


TRY_IT_URL = "https://github.com/ravisharma5/otel-telco-blueprints-impl/tree/main/f2-closed-loop"


@pytest.mark.site_output
def test_try_it_link_only_on_f2(explorer_dist, data, copy):
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        impl = tree.root.find_all(lambda n: n.tag == "a" and "otel-telco-blueprints-impl" in n.attrs.get("href", ""))
        actions = tree.root.find_all(lambda n: n.tag in ("a", "button"))
        assert not [n for n in actions if n.text().lower().startswith("deploy")], uc["slug"]
        if uc["id"] != "UC-AGOPS-01":
            assert impl == [], uc["slug"]
            continue
        assert len(impl) == 1, impl
        link = impl[0]
        assert link.attrs["href"] == TRY_IT_URL
        assert "noopener" in link.attrs.get("rel", "")
        assert copy["buttons"]["try_it"] in link.text()
        assert copy["notes"]["external"] in link.text()
        assert _squash(copy["use_case"]["recipe"]["notes"]["try_it"]) in _squash(tree.root.text())


# ---------- story: the problem, how it works, example ----------


def _why(tree):
    return tree.root.find_all(lambda n: n.tag == "section" and n.attrs.get("id") == "why")[0]


def _story(tree):
    stories = _why(tree).find_all(lambda n: n.has_class("story"))
    assert len(stories) == 1
    return stories[0]


@pytest.mark.site_output
def test_story_comes_first(explorer_dist, data):
    """The story sits right after the title and summary, before Why do it and What it takes."""
    for uc in data["use_cases"]:
        why = _why(_page(explorer_dist, uc))
        marks = [
            n.attrs["class"].split()[0]
            for n in why.find_all(lambda n: n.tag == "h1" or n.has_class("lede") or n.has_class("story") or n.has_class("summary-grid"))
            if n.tag != "h1"
        ]
        assert marks == ["lede", "story", "summary-grid"], (uc["slug"], marks)
        assert _state_of(_story(_page(explorer_dist, uc))) is None


@pytest.mark.site_output
def test_story_blocks_render_from_recipe(explorer_dist, data, copy):
    heads = copy["use_case"]["story"]["headings"]
    for uc in data["use_cases"]:
        story = uc["story"]
        node = _story(_page(explorer_dist, uc))
        h3 = [h.text() for h in node.find_all(lambda n: n.tag == "h3")]
        want = [heads["problem"]]
        if story["steps"]:
            want.append(heads["steps"])
        if story["example"]:
            want.append(heads["example"].replace("{title}", story["example"]["title"]))
        assert h3 == want, (uc["slug"], h3)
        assert _squash(story["problem"]) in _squash(node.text()), uc["slug"]
        lists = node.find_all(lambda n: n.tag == "ol")
        assert len(lists) == (1 if story["steps"] else 0), uc["slug"]
        if story["steps"]:
            items = lists[0].find_all(lambda n: n.tag == "li")
            assert [_squash(li.text()) for li in items] == [_squash(s) for s in story["steps"]], uc["slug"]
        if story["example"]:
            assert _squash(story["example"]["text"]) in _squash(node.text()), uc["slug"]


@pytest.mark.site_output
def test_story_on_ran_energy_saving_and_an_entry(explorer_dist, data, copy):
    heads = copy["use_case"]["story"]["headings"]
    by_slug = {u["slug"]: u for u in data["use_cases"]}
    full = _story(_page(explorer_dist, by_slug["ran-energy-saving"]))
    text = full.text()
    assert "cells stay fully powered through quiet nights" in text
    assert "A scheduled run starts the planning agent hours before a low-traffic period." in text
    assert "nrcell-rural-b3" in text
    assert len(full.find_all(lambda n: n.tag == "li")) == 7
    entry = by_slug["security-triage"]
    assert entry["depth"]["id"] == "entry"
    node = _story(_page(explorer_dist, entry))
    assert [h.text() for h in node.find_all(lambda n: n.tag == "h3")] == [heads["problem"]]
    assert "Detectors raise more alerts" in node.text()
    assert "_Stub" not in node.text() and "Stub:" not in node.text()


@pytest.mark.site_output
def test_no_count_tiles_on_use_case_pages(explorer_dist, data, copy):
    words = copy["home"]["gallery"]["counts"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        assert tree.root.find_all(lambda n: n.has_class("count-tiles") or n.has_class("count-tile")) == []
        assert tree.root.find_all(lambda n: "data-count" in n.attrs) == []
        text = tree.root.text()
        n = uc["counts"]["blueprints"]
        assert f"{n} {words['blueprints']['one' if n == 1 else 'other']}" not in text.replace(
            fill_takes(copy, uc), ""
        ), uc["slug"]


def fill_takes(copy, uc):
    """The What it takes row names the counts in a sentence; only the tiles go."""
    words = copy["home"]["gallery"]["counts"]

    def plural(key):
        n = uc["counts"][key]
        return f"{n} {words[key]['one' if n == 1 else 'other']}"

    return copy["use_case"]["why"]["takes"].replace("{slots}", plural("slots")).replace(
        "{blueprints}", plural("blueprints")
    )


# ---------- CPU-only setups and the nothing-here note ----------


@pytest.mark.site_output
def test_single_cpu_state_block(explorer_dist, data, copy):
    cpu = _cpu_setups(data)
    assert cpu, "expected a CPU-only setup in the data"
    sections = copy["use_case"]["sections"]["notes"]
    batch_sentences = copy["use_case"]["setup"]["batch_sentence"].values()
    for setup in cpu:
        assert setup["batch_values"] == ["any"]
        for uc in data["use_cases"]:
            tree = _page(explorer_dist, uc)
            blocks = [b for b in _blocks(tree) if b.attrs["data-state"].startswith(setup["id"] + "|")]
            assert [b.attrs["data-state"] for b in blocks] == [_key(setup["id"], "any")], uc["slug"]
            sub = blocks[0].find_all(lambda n: n.has_class("sub"))[0].text()
            assert sub == sections["setup_sub_cpu"].replace("{setup}", setup["label"]), sub
            assert not any(sentence in sub for sentence in batch_sentences), sub


@pytest.mark.site_output
def test_batch_disabled_for_single_state(explorer_dist, data, copy):
    setup_copy = copy["use_case"]["setup"]
    single = [s["id"] for s in data["setups"] if s["batch_values"] == ["any"]]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        forms = tree.root.find_all(lambda n: "data-setup-form" in n.attrs)
        assert forms[0].attrs.get("data-single-ids", "").split() == single, uc["slug"]
        assert forms[0].attrs.get("data-announce-single") == setup_copy["announce_single"]
        notes = tree.root.find_all(lambda n: "data-batch-note" in n.attrs)
        assert len(notes) == 1 and "hidden" in notes[0].attrs, uc["slug"]
        assert notes[0].text() == setup_copy["notes"]["batch_na"]
        fieldset = tree.root.find_all(lambda n: n.tag == "fieldset")[0]
        assert notes[0].attrs.get("id") in fieldset.attrs.get("aria-describedby", "").split()
        script = _page_scripts(explorer_dist, tree)
        # Source check of the built script: single-state ids, disabled radios,
        # the batch note, and the batch-free announcement.
        for needle in ("singleIds", ".disabled", "data-batch-note", "announceSingle", "|any"):
            assert needle in script, (uc["slug"], needle)


@pytest.mark.site_output
def test_cpu_state_renders_compact(explorer_dist, data, copy):
    note = copy["use_case"]["advanced"]["notes"]["cpu_site"]
    for setup in _cpu_setups(data):
        key = _key(setup["id"], "any")
        for uc in data["use_cases"]:
            tree = _page(explorer_dist, uc)
            assert _in_parts(tree, key, lambda n: n.has_class("fit-bar")) == [], uc["slug"]
            assert _in_parts(tree, key, lambda n: n.has_class("option-card")) == [], uc["slug"]
            assert _in_parts(tree, key, lambda n: n.has_class("option-grid")) == [], uc["slug"]
            notes = _in_parts(tree, key, lambda n: n.has_class("cpu-options"))
            assert len(notes) == 1 and notes[0].text() == note, uc["slug"]
            text = " ".join(p.text() for p in _parts(tree, key))
            assert "%" not in text, uc["slug"]
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        assert len(tree.root.find_all(lambda n: n.has_class("cpu-options"))) == len(_cpu_setups(data))


@pytest.mark.site_output
def test_nothing_here_note(explorer_dist, data, copy):
    tiers_copy = copy["use_case"]["tiers"]
    tier_words = copy["use_case"]["advanced"]["tiers"]
    seen = 0
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, setup_id, state in _states(uc):
            notes = _in_parts(tree, key, lambda n: n.has_class("nothing-here"))
            if state["runs_here"]:
                assert notes == [], key
                continue
            tier = _setup(data, setup_id)["tier"]
            assert len(notes) == 1, (uc["slug"], key)
            text = notes[0].text()
            assert tiers_copy["nothing_here"].replace("{tier}", tier_words[tier]) in text
            assert _links(notes[0]) == [(f"{BASE}?tier={tier}#gallery", tiers_copy["nothing_here_link"])]
            seen += 1
    assert seen, "expected at least one state where nothing runs at the setup's tier"


@pytest.mark.site_output
def test_key_settings_absent_when_empty(explorer_dist, data, copy):
    heading = copy["use_case"]["sections"]["headings"]["settings"]
    seen = 0
    for uc in data["use_cases"]:
        tree = _page(explorer_dist, uc)
        for key, _, state in _states(uc):
            tables = _in_parts(tree, key, lambda n: n.tag == "table" and n.has_class("settings-table"))
            heads = [h for h in _in_parts(tree, key, lambda n: n.tag == "h3") if h.text() == heading]
            assert len(tables) == len(heads) == (1 if state["flags"] else 0), key
            seen += not state["flags"]
    assert seen, "expected a state with no Key settings"
