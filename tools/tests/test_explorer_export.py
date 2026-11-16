"""Explorer data export: front matter and serving data to precomputed states.

The explorer only renders what tools/site/export_explorer.py computes, so every
rule an operator sees (fit per GPU, FP8 swaps, key settings, model variants,
option applicability) is checked here. Tests read the data files and pages at
run time and assert rules, not hand-copied numbers.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

import pytest
import yaml

from tools.bplint.markdown import parse_doc
from tools.tests.conftest import REPO_ROOT
from tools.tests.test_card_fields import EXPORTER_TABLE_HEADERS as CARD_TABLE_HEADERS
from tools.tests.test_card_fields import GOAL_IDS
from tools.tests.test_card_fields import exported_pages, front_matter

from tools.site import export_explorer as ex

DATA = REPO_ROOT / "data/serving"
SERVING_PAGE = REPO_ROOT / "platform/serving-routing-placement/README.md"
TIERS = ("far-edge", "regional", "core")
BATCH = ("yes", "no")


def load(name):
    return yaml.safe_load((DATA / name).read_text(encoding="utf-8"))


SETUPS = load("setups.yaml")
VARIANTS = load("slot-variants.yaml")["variants"]
OPTIONS = load("options.yaml")["options"]
BANDS = SETUPS["fit_bands"]
SETUP_BY_ID = {s["id"]: s for s in SETUPS["setups"]}
VARIANT_BY_ID = {v["id"]: v for v in VARIANTS}
OPTION_IDS = [o["id"] for o in OPTIONS]


@pytest.fixture(scope="module")
def data():
    return ex.build_explorer_data(REPO_ROOT)


def all_states(data):
    for uc in data["use_cases"]:
        for setup_id, by_batch in uc["states"].items():
            for batch, state in by_batch.items():
                yield uc, SETUP_BY_ID[setup_id], batch, state


def regional_states(data):
    return [t for t in all_states(data) if t[1]["tier"] == "regional"]


def placed(uc_id, tier):
    for path in exported_pages():
        fm = front_matter(path)
        if fm["id"] == uc_id:
            return list(((fm.get("placement") or {}).get(tier) or {}).get("runs") or [])
    raise AssertionError(f"no flagship {uc_id}")


def unswapped_weights(roles):
    """Weights of the starting variant per role: smallest published GPU build, fit_reference for llm-small."""
    out = []
    for role in roles:
        if role == "llm-small":
            v = next(v for v in VARIANTS if v.get("fit_reference"))
        else:
            v = min(
                (v for v in VARIANTS if v["role"] == role and v["gpu"] and v["source"] == "published"),
                key=lambda v: v["weights_gb"],
            )
        out.append((role, v["weights_gb"]))
    return out


# --- pure functions ---------------------------------------------------------


def test_band_boundaries():
    assert BANDS["fits_max_pct"] == 60 and BANDS["tight_max_pct"] == 80  # bands under test
    assert ex.band(60, BANDS) == "fits"
    assert ex.band(61, BANDS) == "tight"
    assert ex.band(80, BANDS) == "tight"
    assert ex.band(81, BANDS) == "too-tight"


@pytest.mark.parametrize(
    "weights,gpu_gb,expected",
    [(28.8, 48, "fits"), (28.9, 48, "tight"), (38.4, 48, "tight"), (38.5, 48, "too-tight")],
)
def test_band_uses_the_unrounded_share(weights, gpu_gb, expected):
    # 28.9 GB of 48 GB is 60.2%: over the fits edge, so Tight, though it rounds to 60%.
    fit = ex._gpu_fit([[("safety", weights)]], gpu_gb, BANDS)[0]
    assert fit["band"] == expected
    edges = (BANDS["fits_max_pct"], BANDS["tight_max_pct"])
    # The percent shown never sits on an edge the band is past.
    if fit["band"] != ex.band(fit["pct"], BANDS):
        raise AssertionError(f"{fit['pct']}% shown with band {fit['band']}")
    assert fit["pct"] not in edges or 100 * weights / gpu_gb <= fit["pct"]


def test_pack_first_fit_decreasing():
    items = [("a", 17), ("b", 17), ("c", 8), ("d", 1.2), ("e", 1.2)]
    bins = ex.pack(items, 2, 48)
    assert len(bins) == 2
    assert sorted(n for b in bins for n, _ in b) == ["a", "b", "c", "d", "e"]
    assert all(sum(w for _, w in b) <= 48 for b in bins)
    assert all(b for b in bins), "two GPUs: both carry slots when the slots do not fit one GPU's fits band"
    assert ex.pack(list(reversed(items)), 2, 48) == bins, "assignment must not depend on input order"
    assert ex.pack(items, 2, 48) == bins


def test_choose_variants_swaps_largest_first():
    setup = SETUP_BY_ID["regional-48"]
    chosen, _ = ex.choose_variants(["safety", "llm-small", "decision"], setup, VARIANTS, BANDS)
    by_role = {v["role"]: v for v in chosen}
    # 17 + 8 + 17 = 42 GB on 48 GB is too tight, so Safety (largest with an FP8 build) swaps first.
    assert by_role["safety"]["source"] == "operator-made"
    assert by_role["decision"]["source"] == "published", "Decision has no FP8 build"


def test_fp8_swap_never_grows_a_slot():
    # An operator-made FP8 build bigger than the current build (an FP8 Decision at
    # about 26 GB against the 17 GB W4A16) is never swapped in or suggested.
    big = {
        **VARIANT_BY_ID["decision-26b-a4b-w4a16"],
        "id": "decision-fp8-test",
        "precision": "fp8",
        "weights_gb": 26,
        "source": "operator-made",
    }
    variants = VARIANTS + [big]
    setup = SETUP_BY_ID["regional-48"]
    chosen, fit = ex.choose_variants(["safety", "llm-small", "decision"], setup, variants, BANDS)
    by_role = {v["role"]: v for v in chosen}
    assert by_role["decision"]["id"] == "decision-26b-a4b-w4a16"
    chosen, fit = ex.choose_variants(["decision"], setup, variants, BANDS)
    assert chosen[0]["id"] == "decision-26b-a4b-w4a16"
    # Too tight with only a bigger FP8 build left: the message must not suggest FP8.
    small = {**SETUP_BY_ID["regional-48"], "accelerators": {**setup["accelerators"], "memory_per_gpu_gb": 20}}
    chosen, fit = ex.choose_variants(["decision"], small, variants, BANDS)
    assert chosen[0]["id"] == "decision-26b-a4b-w4a16"
    assert fit[0]["band"] == "too-tight" and fit[0]["message_id"] == "too-tight-after-fp8"


# --- state matrix -----------------------------------------------------------


def test_ten_states_per_use_case(data):
    states = list(all_states(data))
    setups = SETUPS["setups"]
    assert len(data["use_cases"]) == len(exported_pages())
    assert len(setups) * len(BATCH) == 10
    assert len(states) == len(exported_pages()) * len(setups) * len(BATCH)
    for uc in data["use_cases"]:
        assert list(uc["states"]) == [s["id"] for s in setups]
        for by_batch in uc["states"].values():
            assert sorted(by_batch) == sorted(BATCH)
    for uc, setup, batch, state in states:
        assert [t["tier"] for t in state["tiers"]] == list(TIERS)
        assert isinstance(state["flags"], list) and state["flags"]
        assert state["variants"], f"{uc['id']} {setup['id']}: no variants"
        assert [o["id"] for o in state["options"]] == OPTION_IDS
        assert len(state["options"]) == len(OPTIONS)
        helps = sum(1 for o in state["options"] if o["state"] == "helps")
        assert state["options_worth_testing"] == helps


def test_tier_cards(data):
    for uc, setup, batch, state in all_states(data):
        for card in state["tiers"]:
            runs = placed(uc["id"], card["tier"])
            assert card["used"] == bool(runs)
            assert card["matches_setup"] == (card["tier"] == setup["tier"])
            assert [s["role"] for s in card["slots"]] == runs


def test_small_llm_uses_fit_reference(data):
    ref = [v for v in VARIANTS if v.get("fit_reference")]
    assert len(ref) == 1 and ref[0]["role"] == "llm-small"
    ref = ref[0]
    fp8 = [v["id"] for v in VARIANTS if v["role"] == "llm-small" and v["source"] == "operator-made"]
    seen = 0
    for uc, setup, batch, state in regional_states(data):
        for v in state["variants"]:
            if v["role"] == "llm-small":
                seen += 1
                assert v["variant_id"] == ref["id"] or v["variant_id"] in fp8
                if not v["operator_made"]:
                    assert v["variant_id"] == ref["id"]
    assert seen, "no regional state places the small LLM"


def test_variants_match_placement(data):
    for uc, setup, batch, state in all_states(data):
        roles = placed(uc["id"], setup["tier"])
        assert [v["role"] for v in state["variants"]] == roles
        for v in state["variants"]:
            src = VARIANT_BY_ID[v["variant_id"]]
            assert v["role"] == src["role"] and v["tier"] == setup["tier"]
            assert v["checkpoint"] == src["checkpoint"]
            assert v["precision"] == src["precision"]
            assert v["model_card"] == src["model_card"]
            assert v["red_hat_build"] == src["red_hat_build"]
            assert v["operator_made"] == (src["source"] == "operator-made")
            assert v["slot_name"]


def test_two_gpu_setup_never_pools(data):
    for uc, setup, batch, state in all_states(data):
        if setup["id"] == "regional-2x48":
            assert len(state["fit"]) == 2
            assert all(f["total_gb"] == 48 and f["gpu_count"] == 2 for f in state["fit"])
            assert [f["gpu_index"] for f in state["fit"]] == [1, 2]
        for f in state["fit"]:
            assert not (f["total_gb"] == 96 and f["gpu_count"] == 2)


def test_fit_entries_follow_rules(data):
    for uc, setup, batch, state in regional_states(data):
        acc = setup["accelerators"]
        assert len(state["fit"]) == acc["count_per_node"]
        slots_on_gpus = []
        for f in state["fit"]:
            assert f["total_gb"] == acc["memory_per_gpu_gb"]
            total = sum(s["weights_gb"] for s in f["slots"])
            share = 100 * total / f["total_gb"]
            assert f["weights_gb"] == round(total, 1)
            assert abs(f["pct"] - share) < 0.5 + 1e-9
            assert f["band"] == ex.band(share, BANDS), "band from the unrounded share"
            assert ex.band(f["pct"], BANDS) == f["band"], "shown percent agrees with the band"
            slots_on_gpus += [s["role"] for s in f["slots"]]
        assert sorted(slots_on_gpus) == sorted(placed(uc["id"], "regional"))
        weights_by_role = {v["role"]: VARIANT_BY_ID[v["variant_id"]]["weights_gb"] for v in state["variants"]}
        for f in state["fit"]:
            for s in f["slots"]:
                assert s["weights_gb"] == weights_by_role[s["role"]]


def test_fit_message_never_suggests_applied_fp8(data):
    # A too-tight GPU suggests FP8 builds only while one of its slots still has an
    # unused FP8 build; once they are all in, the message suggests something else.
    seen = set()
    for uc, setup, batch, state in regional_states(data):
        chosen = {v["role"]: v["variant_id"] for v in state["variants"]}
        fp8_arch = setup["accelerators"]["arch"] in ex.FP8_ARCHES
        for f in state["fit"]:
            fp8_left = fp8_arch and any(
                v["role"] == s["role"]
                and v["source"] == "operator-made"
                and v["precision"] == "fp8"
                and v["gpu"]
                and v["id"] != chosen[s["role"]]
                for s in f["slots"]
                for v in VARIANTS
            )
            if f["band"] == "too-tight":
                expected = "too-tight" if fp8_left else "too-tight-after-fp8"
            else:
                expected = f["band"]
            assert f["message_id"] == expected, (uc["id"], setup["id"], f["gpu_index"])
            seen.add(f["message_id"])
    assert "too-tight-after-fp8" in seen, "expected alarm triage on one 48 GB GPU to need it"


def test_every_placed_slot_has_a_model_row(data):
    # Models shows the full picture: the setup tier's builds plus every slot that
    # runs at another tier, at that tier's starting (published) build.
    for uc, setup, batch, state in all_states(data):
        others = state["other_tier_variants"]
        for v in state["variants"]:
            assert v["tier"] == setup["tier"]
        for v in others:
            assert v["tier"] != setup["tier"]
            assert v["operator_made"] is False
            assert v["variant_id"] == ex._start_variant(v["role"], VARIANTS)["id"]
        got = sorted((v["tier"], v["role"]) for v in state["variants"] + others)
        want = sorted((tier, role) for tier in TIERS for role in placed(uc["id"], tier))
        assert got == want, (uc["id"], setup["id"])
        tiers = [v["tier"] for v in others]
        assert tiers == sorted(tiers, key=TIERS.index), "other tiers follow far edge, regional, core"


def test_core_has_no_fit_and_no_swaps(data):
    for uc, setup, batch, state in all_states(data):
        if setup["tier"] != "core":
            continue
        assert state["fit"] == []
        assert not any(v["operator_made"] for v in state["variants"])
        assert state["quantized_check"] is False
        for v in state["variants"]:
            if v["role"] == "llm-large":
                assert VARIANT_BY_ID[v["variant_id"]]["precision"] == "bf16"


def test_fp8_swap_only_when_needed(data):
    for uc, setup, batch, state in regional_states(data):
        acc = setup["accelerators"]
        roles = placed(uc["id"], "regional")
        start = ex.pack(
            unswapped_weights(roles),
            acc["count_per_node"],
            acc["memory_per_gpu_gb"],
            fill_pct=BANDS["fits_max_pct"],
        )
        start_bands = [ex.band(100 * sum(w for _, w in b) / acc["memory_per_gpu_gb"], BANDS) for b in start]
        swapped = [v for v in state["variants"] if v["operator_made"]]
        if swapped:
            assert any(b != "fits" for b in start_bands), f"{uc['id']} {setup['id']}: FP8 swap without need"
            for v in swapped:
                assert VARIANT_BY_ID[v["variant_id"]]["precision"] == "fp8"
        if any(f["band"] != "fits" for f in state["fit"]):
            # Stopped short of fitting: every slot on a crowded GPU with an FP8 build is already swapped.
            fp8_roles = {v["role"] for v in VARIANTS if v["source"] == "operator-made" and v["precision"] == "fp8"}
            by_role = {v["role"]: v for v in state["variants"]}
            for f in state["fit"]:
                if f["band"] != "fits":
                    for s in f["slots"]:
                        if s["role"] in fp8_roles:
                            assert by_role[s["role"]]["operator_made"], (
                                f"{uc['id']} {setup['id']}: {s['role']} left unswapped on a crowded GPU"
                            )


def test_regional_96_fits_without_the_large_llm(data):
    """Data sanity check: a 96 GB GPU holds every regional map that leaves the 31B at the core.

    A map with four or more mid-size slots (Classification beside Safety and Decision)
    may need an FP8 build to reach the fits band; only the 31B may stay out of it.
    """
    checked = 0
    for uc, setup, batch, state in regional_states(data):
        if setup["id"] == "regional-96" and "llm-large" not in placed(uc["id"], "regional"):
            checked += 1
            assert not any(v["operator_made"] and v["role"] == "llm-large" for v in state["variants"]), uc["id"]
            assert all(f["band"] == "fits" for f in state["fit"]), uc["id"]
    assert checked


def test_quantized_check_matches_variants(data):
    for uc, setup, batch, state in all_states(data):
        assert state["quantized_check"] == any(v["operator_made"] for v in state["variants"])


# Words that name a slot in a Key settings row (setting, value, or why). Matched
# case-sensitively, so "reranker score" in a pooling flag's why names no slot.
SLOT_WORDS = {
    "llm-large": (r"\b31B\b", r"\blarge LLM\b"),
    "llm-small": (r"\bsmall LLM\b",),
    "decision": (r"\bDecision\b",),
    "safety": (r"\bSafety\b",),
    "classification": (r"\bClassification\b",),
    "embedding": (r"\bEmbedding\b",),
    "reranker": (r"\bReranker\b",),
}


def _row_text(flag):
    return " ".join(str(flag[k] or "") for k in ("setting", "value", "why"))


def test_settings_name_only_placed_slots(data):
    # A Key settings row that names a slot (the 31B, Decision, ...) shows only on a
    # setup whose tier runs that slot, read from the recipe's placement.
    bad = []
    for uc, setup, batch, state in all_states(data):
        roles = set(placed(uc["id"], setup["tier"]))
        for flag in state["flags"]:
            text = _row_text(flag)
            for role, patterns in SLOT_WORDS.items():
                if role not in roles and any(re.search(p, text) for p in patterns):
                    bad.append(f"{uc['id']} {setup['id']}|{batch}: {flag['setting']} names {role}")
    assert bad == []


def test_decision_only_settings_need_decision(data):
    for uc, setup, batch, state in all_states(data):
        if "decision" in placed(uc["id"], setup["tier"]):
            continue
        rows = [f["setting"] for f in state["flags"] if "Decision slot only" in f["why"]]
        assert rows == [], (uc["id"], setup["id"], batch)


def _start_bands(uc_id, setup):
    """Bands per GPU with every placed slot at its starting build, from the data files."""
    acc = setup["accelerators"]
    weights = unswapped_weights(placed(uc_id, setup["tier"]))
    bins = ex.pack(weights, acc["count_per_node"], acc["memory_per_gpu_gb"], fill_pct=BANDS["fits_max_pct"])
    return [ex.band(100 * sum(w for _, w in b) / acc["memory_per_gpu_gb"], BANDS) for b in bins]


def test_fp8_build_row_only_where_fp8_is_used(data):
    # No "Model build: FP8" row where the full-precision builds fit, where the FP8
    # option says it is not needed, or where Models lists no FP8 build.
    bad = []
    for uc, setup, batch, state in all_states(data):
        rows = [f for f in state["flags"] if f["setting"] == "Model build" and "FP8" in f["value"]]
        if not rows:
            continue
        where = f"{uc['id']} {setup['id']}|{batch}"
        fp8_models = [v for v in state["variants"] if VARIANT_BY_ID[v["variant_id"]]["precision"] == "fp8"]
        if not fp8_models:
            bad.append(f"{where}: FP8 build row, but Models lists no FP8 build")
        if option(state, "fp8-regional")["state"] != "helps":
            bad.append(f"{where}: FP8 build row, but the FP8 option says it is not needed")
        if setup["tier"] != "regional" or all(b == "fits" for b in _start_bands(uc["id"], setup)):
            bad.append(f"{where}: FP8 build row, but the full-precision builds fit")
    assert bad == []


def test_setup_rows_follow_setup_and_batch(data):
    # Every per-setup row shown belongs to the setup and its batch value.
    flags = load("flags.yaml")
    for uc, setup, batch, state in all_states(data):
        allowed = {
            (r["setting"], r["value"], r["why"])
            for r in flags["per_setup"]
            if r["setup"] == setup["id"] and r["when_batch"] in (None, batch)
        }
        for f in state["flags"]:
            if f["scope"] == "setup":
                assert (f["setting"], f["value"], f["why"]) in allowed, (uc["id"], setup["id"], batch)


def _serving_source_labels():
    from tools.site.render_serving import _source_labels

    return _source_labels(SERVING_PAGE.read_text(encoding="utf-8"))


def test_every_setting_and_option_carries_its_sources(data):
    # Every Key settings row and option card the explorer shows names its sources,
    # with the label of that source's row in the serving page Sources table.
    labels = _serving_source_labels()
    flags = load("flags.yaml")
    slot_sources = {b["comment"]: b["sources"] for b in flags["per_slot"]}
    by_id = {o["id"]: o for o in OPTIONS}
    for uc, setup, batch, state in all_states(data):
        for f in state["flags"]:
            assert f["sources"], (uc["id"], setup["id"], f["setting"])
            for src in f["sources"]:
                assert src["label"] == labels[src["url"]], src
            if f["scope"] != "setup":
                assert [s["url"] for s in f["sources"]] == slot_sources[f["scope"]]
        for o in state["options"]:
            assert [s["url"] for s in o["sources"]] == by_id[o["id"]]["sources"]
            for src in o["sources"]:
                assert src["label"] == labels[src["url"]], src


# --- options ----------------------------------------------------------------


def option(state, oid):
    return next(o for o in state["options"] if o["id"] == oid)


def test_option_reasons(data):
    core_only = [o["id"] for o in OPTIONS if any(r["reason"] == "core-only" for r in o["applies_when"])]
    assert core_only
    for uc, setup, batch, state in all_states(data):
        if setup["id"] == "core-amd":
            assert option(state, "pd-split")["state"] == "not-applicable"
            assert option(state, "pd-split")["reason_id"] == "not-amd-paths"
        if setup["tier"] == "core" and batch == "no":
            assert option(state, "priority-bands")["reason_id"] == "batch-only"
        if setup["tier"] == "regional":
            for oid in core_only:
                o = option(state, oid)
                assert o["state"] == "not-applicable" and o["reason_id"] == "core-only"
        if setup["tier"] == "core":
            o = option(state, "fp8-regional")
            assert o["state"] == "not-applicable" and o["reason_id"] == "not-needed-at-core"


def test_option_states_follow_rules(data):
    for uc, setup, batch, state in all_states(data):
        props = {
            "tier": setup["tier"],
            "vendor": setup["accelerators"]["vendor"],
            "batch": batch,
            "arch": setup["accelerators"]["arch"],
            "fp8_swap": "yes" if any(v["operator_made"] for v in state["variants"]) else "no",
        }
        for src, o in zip(OPTIONS, state["options"]):
            for key in ("name", "engine", "tiers", "what", "set", "check", "limits", "related"):
                assert o[key] == src[key], f"{src['id']}.{key} not copied from options.yaml"
            helps = {w["use_case"]: w["reason"] for w in src["where_it_helps"]}
            failing = [r for r in src["applies_when"] if props[r["rule"]] not in r["allowed"]]
            assert o["would_help"] == (uc["id"] in helps)
            if failing:
                assert o["state"] == "not-applicable"
                assert o["reason_id"] == failing[0]["reason"]
                assert o["reason_text"] is None
            elif uc["id"] in helps and not set(_helps_roles(src, uc["id"])) & set(placed(uc["id"], setup["tier"])):
                assert o["state"] == "not-applicable" and o["reason_id"].startswith("helps-at-")
            elif uc["id"] in helps and props["fp8_swap"] == "yes" and src["id"] == "fp8-regional":
                assert o["state"] == "helps" and o["reason_id"] == "fp8-swapped"
            elif uc["id"] in helps:
                assert o["state"] == "helps"
                assert o["reason_text"] == helps[uc["id"]]
                assert o["reason_id"] is None
            else:
                assert o["state"] == "little"
                assert o["reason_text"] is None and o["reason_id"] is None


def _helps_roles(src, uc_id):
    """Slots an option's where_it_helps reason is about for a use case, minus excluded slots."""
    entry = next((w for w in src["where_it_helps"] if w["use_case"] == uc_id), None)
    return [r for r in (entry["roles"] if entry else []) if r not in src["excluded_slots"]]


def test_helps_only_where_a_target_slot_runs(data):
    # "Helps here" needs a slot the reason is about running at the setup's tier,
    # read from the recipe placement and options.yaml; excluded slots never count.
    bad = []
    for uc, setup, batch, state in all_states(data):
        roles = set(placed(uc["id"], setup["tier"]))
        for src in OPTIONS:
            o = option(state, src["id"])
            if o["state"] == "helps" and not set(_helps_roles(src, uc["id"])) & roles:
                bad.append(f"{src['id']} for {uc['id']} on {setup['id']}|{batch}")
    assert bad == []


def test_option_helping_at_another_tier_says_so(data):
    # An option that helps this use case only at another tier reads "doesn't apply"
    # on this setup, never "little benefit", and its reason names that tier.
    seen = 0
    for uc, setup, batch, state in all_states(data):
        roles = set(placed(uc["id"], setup["tier"]))
        for src in OPTIONS:
            targets = set(_helps_roles(src, uc["id"]))
            o = option(state, src["id"])
            if not targets or targets & roles:
                continue
            seen += 1
            assert o["state"] == "not-applicable", (src["id"], uc["id"], setup["id"], batch)
            assert o["would_help"] is True
            others = [t for t in TIERS if t != setup["tier"] and targets & set(placed(uc["id"], t))]
            if o["reason_id"].startswith("helps-at-"):
                assert o["reason_id"] == f"helps-at-{others[0]}", (src["id"], uc["id"], setup["id"])
    assert seen


def test_helps_roles_are_never_excluded():
    for src in OPTIONS:
        for entry in src["where_it_helps"]:
            assert not set(entry["roles"]) & set(src["excluded_slots"]), (src["id"], entry["use_case"])


def test_options_worth_testing_counts_helps(data):
    for uc, setup, batch, state in all_states(data):
        assert state["options_worth_testing"] == sum(o["state"] == "helps" for o in state["options"])


def worst_band(fit):
    order = ["fits", "tight", "too-tight"]
    return max((f["band"] for f in fit), key=order.index, default="fits")


def test_fp8_option_follows_fit(data):
    # The FP8 option helps exactly where FP8 builds were swapped in, says when the
    # setup is still tight or too tight, and is "not needed" where bf16 fits.
    seen = {"helps": 0, "fits-without-fp8": 0, "still-tight": 0, "still-too-tight": 0}
    for uc, setup, batch, state in all_states(data):
        o = option(state, "fp8-regional")
        for other in state["options"]:
            assert "fit_note_id" in other
            if other["id"] != "fp8-regional":
                assert other["fit_note_id"] is None
        if setup["tier"] != "regional":
            assert o["fit_note_id"] is None
            continue
        swapped = [v for v in state["variants"] if v["operator_made"]]
        if swapped:
            assert o["state"] == "helps", (uc["id"], setup["id"])
            seen["helps"] += 1
            # The reason names exactly the slots swapped in this state, in placement order.
            assert o["reason_id"] == "fp8-swapped" and o["reason_text"] is None
            assert o["reason_roles"] == [v["role"] for v in swapped], (uc["id"], setup["id"])
            band = worst_band(state["fit"])
            expected = {"fits": None, "tight": "still-tight", "too-tight": "still-too-tight"}[band]
            assert o["fit_note_id"] == expected, (uc["id"], setup["id"])
            if expected:
                seen[expected] += 1
        else:
            assert o["state"] == "not-applicable" and o["reason_id"] == "fits-without-fp8", (uc["id"], setup["id"])
            assert o["fit_note_id"] is None
            seen["fits-without-fp8"] += 1
    assert all(seen.values()), seen


def test_fp8_swap_needs_a_reason():
    # A use case whose state swaps in FP8 builds must have a where_it_helps reason,
    # so the option never reads "little benefit" next to an FP8 build.
    serving = ex._serving_data(REPO_ROOT)
    for o in serving["options"]:
        if o["id"] == "fp8-regional":
            o["where_it_helps"] = [w for w in o["where_it_helps"] if w["use_case"] != "UC-OPS-01"]
    placement = {"regional": {"runs": placed("UC-OPS-01", "regional")}}
    with pytest.raises(SystemExit, match="UC-OPS-01"):
        ex._state("UC-OPS-01", placement, SETUP_BY_ID["regional-48"], "yes", serving)


def test_option_state_function():
    pd = next(o for o in OPTIONS if o["id"] == "pd-split")
    s = ex.option_state(pd, SETUP_BY_ID["core-amd"], "yes", "UC-KNOW-01")
    assert s["state"] == "not-applicable" and s["reason_id"] == "not-amd-paths" and s["would_help"] is True
    s = ex.option_state(pd, SETUP_BY_ID["core-nvidia"], "yes", "UC-KNOW-01")
    assert s["state"] == "helps" and s["reason_text"]


def test_helps_text_from_page(data):
    doc = parse_doc(SERVING_PAGE, SERVING_PAGE.read_text(encoding="utf-8"))
    rows = []
    for sec in doc.sections:
        for t in sec.tables:
            if tuple(t.header) == ("Option", "Use case", "Where it helps"):
                rows += [tuple(r.cells) for r in t.rows]
    assert rows, "serving page has no Where each option helps table"
    names = {o["id"]: o["name"] for o in OPTIONS}
    seen = 0
    for uc, setup, batch, state in all_states(data):
        for o in state["options"]:
            if o["state"] == "helps" and o["reason_text"] is not None:
                seen += 1
                hits = [
                    r for r in rows if r[0] == names[o["id"]] and uc["id"] in r[1] and r[2] == o["reason_text"]
                ]
                assert hits, f"{o['id']} for {uc['id']}: reason not on the serving page"
    assert seen


# --- use-case fields --------------------------------------------------------


STAGES = {
    "inform": "Informs only",
    "notify": "Informs only",
    "recommend-with-approval": "Recommends, a person approves",
    "act-within-policy": "Acts within policy",
}


def test_counts_and_stage(data):
    fms = {front_matter(p)["id"]: front_matter(p) for p in exported_pages()}
    for uc in data["use_cases"]:
        fm = fms[uc["id"]]
        assert uc["counts"] == {
            "slots": len(fm["otel_slots"]),
            "blueprints": len(fm["platform_blueprints"]),
            "tiers": len(fm["placement_tier"]),
        }
        assert uc["stage"]["label"] == STAGES[fm["autonomy_ceiling"]]
        assert uc["doc_status"] == fm["doc_status"]
        assert uc["card"] == fm["card"]
        assert uc["title"] == fm["title"]
        assert uc["domain"] == fm["domain"]
        assert len(uc["slot_names"]) == len(fm["otel_slots"])


def test_tables_from_recipe(data):
    for uc in data["use_cases"]:
        assert uc["platform_rows"] and all(len(r) == 2 and all(r) for r in uc["platform_rows"])
        assert uc["approvals"] and all(len(r) == 3 and r[0] and r[1] for r in uc["approvals"])
        assert uc["parameters"] and all(len(r) == 2 for r in uc["parameters"])
        for name, owner in uc["parameters"]:
            assert name.strip() and owner.strip()
        assert all("](" not in c for r in uc["platform_rows"] + uc["approvals"] for c in r), "markdown links left in cells"


def _copy_serving_page(tmp_path):
    """The exporter reads source labels from the serving page's Sources table."""
    dest = tmp_path / "platform/serving-routing-placement"
    dest.mkdir(parents=True)
    shutil.copy(SERVING_PAGE, dest / "README.md")


def test_table_headers_shared(tmp_path):
    assert ex.EXPORTER_TABLE_HEADERS == CARD_TABLE_HEADERS
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "catalog", tmp_path / "catalog")
    _copy_serving_page(tmp_path)
    page = tmp_path / "catalog/standards-knowledge/grounded-knowledge-assistant/README.md"
    page.write_text(page.read_text(encoding="utf-8").replace("| Who sets it |", "| Owner |", 1), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        ex.build_explorer_data(tmp_path)
    msg = str(exc.value)
    assert "grounded-knowledge-assistant/README.md" in msg and "Who sets it" in msg


def test_missing_variant_fails(tmp_path):
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "catalog", tmp_path / "catalog")
    _copy_serving_page(tmp_path)
    path = tmp_path / "data/serving/slot-variants.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["variants"] = [v for v in doc["variants"] if v["role"] != "reranker"]
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        ex.build_explorer_data(tmp_path)
    assert "slot-variants.yaml" in str(exc.value) and "reranker" in str(exc.value)


def test_published_only_and_unique_slugs(data):
    ids = sorted(front_matter(p)["id"] for p in exported_pages())
    assert sorted(uc["id"] for uc in data["use_cases"]) == ids
    slugs = [uc["slug"] for uc in data["use_cases"]]
    assert len(set(slugs)) == len(slugs)
    for uc in data["use_cases"]:
        assert uc["recipe_url"] == f"recipes/{uc['domain']}/{uc['slug']}/"
        assert (REPO_ROOT / "catalog" / uc["domain"] / uc["slug"] / "README.md").is_file()


def test_filters_only_present_values(data):
    used_tiers = {t for uc in data["use_cases"] for t in TIERS if placed(uc["id"], t)}
    assert data["filters"]["tiers"] == [t for t in TIERS if t in used_tiers]
    assert "far-edge" not in data["filters"]["tiers"]
    assert {d["id"] for d in data["filters"]["domains"]} == {uc["domain"] for uc in data["use_cases"]}
    assert {s["id"] for s in data["filters"]["stages"]} == {uc["stage"]["id"] for uc in data["use_cases"]}


def test_top_level(data):
    assert data["default"] == SETUPS["default"]
    assert data["fit_bands"] == BANDS
    assert [s["id"] for s in data["setups"]] == [s["id"] for s in SETUPS["setups"]]
    for out, src in zip(data["setups"], SETUPS["setups"]):
        assert out["label"] == src["label"] and out["tier"] == src["tier"]
        assert out["ampere_note"] == src["ampere_note"]


GOALS_FILE = REPO_ROOT / "data/explorer/goals.yaml"
DEPTH_LABELS = {"recipe": "Full recipe", "entry": "Catalog entry"}


def test_goals_file():
    doc = yaml.safe_load(GOALS_FILE.read_text(encoding="utf-8"))
    assert list(doc) == ["goals"]
    assert doc["goals"] == GOAL_IDS
    assert len(set(doc["goals"])) == len(doc["goals"])


def test_unknown_goal_fails(tmp_path):
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "catalog", tmp_path / "catalog")
    _copy_serving_page(tmp_path)
    page = tmp_path / "catalog/standards-knowledge/grounded-knowledge-assistant/README.md"
    text = page.read_text(encoding="utf-8")
    assert 'goal: "answer"' in text
    page.write_text(text.replace('goal: "answer"', 'goal: "nope"', 1), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        ex.build_explorer_data(tmp_path)
    msg = str(exc.value)
    assert "grounded-knowledge-assistant/README.md" in msg and "nope" in msg, msg


def test_goals_exported(data):
    counts = {}
    for uc in data["use_cases"]:
        assert uc["goal"] == front_matter(REPO_ROOT / "catalog" / uc["domain"] / uc["slug"] / "README.md")["card"]["goal"]
        counts[uc["goal"]] = counts.get(uc["goal"], 0) + 1
    assert data["goals"] == [{"id": g, "count": counts[g]} for g in GOAL_IDS if counts.get(g)]
    assert all(g["count"] > 0 for g in data["goals"])
    assert sum(g["count"] for g in data["goals"]) == len(data["use_cases"])


def test_every_goal_has_a_use_case(data):
    """Every goal tile the home page offers has at least one use case behind it."""
    goals = yaml.safe_load(GOALS_FILE.read_text(encoding="utf-8"))["goals"]
    counts = {g["id"]: g["count"] for g in data["goals"]}
    missing = [g for g in goals if counts.get(g, 0) < 1]
    assert missing == [], f"goals with no use case: {missing}"


def test_depth_exported(data):
    for uc in data["use_cases"]:
        fm = front_matter(REPO_ROOT / "catalog" / uc["domain"] / uc["slug"] / "README.md")
        assert uc["depth"] == {"id": fm["depth"], "label": DEPTH_LABELS[fm["depth"]]}
    present = {uc["depth"]["id"] for uc in data["use_cases"]}
    assert data["filters"]["depths"] == [d for d in ("recipe", "entry") if d in present]
    assert ex.DEPTH_LABELS == DEPTH_LABELS


def test_adaptation_exported(data):
    from tools.site.render_bring import (
        CHANGE_LABELS,
        CHANGE_OF_RUNG,
        CHANGE_ORDER,
        EXPERTISE_LABELS,
        EXPERTISE_ORDER,
        RUNG_LABELS,
    )

    for uc in data["use_cases"]:
        fm = front_matter(REPO_ROOT / "catalog" / uc["domain"] / uc["slug"] / "README.md")
        ad = fm["adaptation"]
        expertise = [e for e in EXPERTISE_ORDER if e in ad["expertise"]]
        assert uc["adaptation"] == {
            "rung": ad["rung"],
            "change": CHANGE_OF_RUNG[ad["rung"]],
            "rung_label": RUNG_LABELS[ad["rung"]],
            "expertise": [{"id": e, "label": EXPERTISE_LABELS[e]} for e in expertise],
        }, uc["slug"]
    present = {uc["adaptation"]["change"] for uc in data["use_cases"]}
    assert data["filters"]["changes"] == [c for c in CHANGE_ORDER if c in present]
    assert set(CHANGE_LABELS) == set(CHANGE_ORDER) == {"none", "retrain"}


def test_cli_writes_json(tmp_path, data):
    out = tmp_path / "x.json"
    subprocess.run(
        [sys.executable, "-m", "tools.site.export_explorer", "--out", str(out)],
        cwd=REPO_ROOT,
        check=True,
    )
    assert json.loads(out.read_text(encoding="utf-8")) == data


@pytest.mark.parametrize("key", ["card", "placement"])
def test_exporter_raises_without_card_or_placement(tmp_path, key):
    """A use-case page the explorer cannot show stops the export instead of dropping out."""
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "catalog", tmp_path / "catalog")
    _copy_serving_page(tmp_path)
    page = tmp_path / "catalog/standards-knowledge/grounded-knowledge-assistant/README.md"
    _, fm_text, rest = page.read_text(encoding="utf-8").split("---\n", 2)
    fm = yaml.safe_load(fm_text)
    del fm[key]
    page.write_text("---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n" + rest, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        ex.build_explorer_data(tmp_path)
    msg = str(exc.value)
    assert "grounded-knowledge-assistant/README.md" in msg and key in msg, msg


def test_exporter_docstring_matches_skip_rule():
    assert "nothing is skipped silently" not in (ex.__doc__ or "")


LINK = re.compile(r"https://github\.com/[^\s'\"]+")


def test_options_links_pinned():
    """Related links point at a commit, so the target cannot change under the page."""
    text = (REPO_ROOT / "data/serving/options.yaml").read_text(encoding="utf-8")
    links = LINK.findall(text)
    assert links
    floating = [u for u in links if re.search(r"/(blob|tree)/(main|master)/", u)]
    assert floating == [], floating
    for url in links:
        if "/blob/" in url or "/tree/" in url:
            assert re.search(r"/(blob|tree)/[0-9a-f]{40}/", url), url


def test_fill_matches_own_keys_only():
    """A {constructor} placeholder must not render a prototype function."""
    src = (REPO_ROOT / "explorer/src/lib/data.ts").read_text(encoding="utf-8")
    body = src.split("export function fill", 1)[1].split("\n}\n", 1)[0]
    assert "Object.hasOwn(values, name)" in body, body
    assert " in values" not in body, body
