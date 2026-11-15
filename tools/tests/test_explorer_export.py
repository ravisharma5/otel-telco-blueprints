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
from tools.tests.test_card_fields import flagship_pages, front_matter

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
    for path in flagship_pages():
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


# --- state matrix -----------------------------------------------------------


def test_forty_states(data):
    states = list(all_states(data))
    setups = SETUPS["setups"]
    assert len(data["use_cases"]) == len(flagship_pages())
    assert len(states) == len(data["use_cases"]) * len(setups) * len(BATCH)
    assert len(states) == 40
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
            weights = round(sum(s["weights_gb"] for s in f["slots"]), 1)
            assert f["weights_gb"] == weights
            assert f["pct"] == round(100 * weights / f["total_gb"])
            assert f["band"] == ex.band(f["pct"], BANDS)
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
        start_bands = [ex.band(round(100 * sum(w for _, w in b) / acc["memory_per_gpu_gb"]), BANDS) for b in start]
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


def test_regional_96_needs_no_swap_without_the_large_llm(data):
    """Data sanity check: a 96 GB GPU holds every regional map that leaves the 31B at the core."""
    checked = 0
    for uc, setup, batch, state in regional_states(data):
        if setup["id"] == "regional-96" and "llm-large" not in placed(uc["id"], "regional"):
            checked += 1
            assert not any(v["operator_made"] for v in state["variants"]), uc["id"]
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
            elif uc["id"] in helps:
                assert o["state"] == "helps"
                assert o["reason_text"] == helps[uc["id"]]
                assert o["reason_id"] is None
            else:
                assert o["state"] == "little"
                assert o["reason_text"] is None and o["reason_id"] is None


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
            reason = o["reason_text"].lower()
            for v in swapped:
                assert v["slot_name"].lower() in reason, (uc["id"], setup["id"], v["slot_name"], reason)
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
            if o["state"] == "helps":
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
    fms = {front_matter(p)["id"]: front_matter(p) for p in flagship_pages()}
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


def test_table_headers_shared(tmp_path):
    assert ex.EXPORTER_TABLE_HEADERS == CARD_TABLE_HEADERS
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "catalog", tmp_path / "catalog")
    page = tmp_path / "catalog/standards-knowledge/grounded-knowledge-assistant/README.md"
    page.write_text(page.read_text(encoding="utf-8").replace("| Who sets it |", "| Owner |", 1), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        ex.build_explorer_data(tmp_path)
    msg = str(exc.value)
    assert "grounded-knowledge-assistant/README.md" in msg and "Who sets it" in msg


def test_missing_variant_fails(tmp_path):
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "catalog", tmp_path / "catalog")
    path = tmp_path / "data/serving/slot-variants.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["variants"] = [v for v in doc["variants"] if v["role"] != "reranker"]
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        ex.build_explorer_data(tmp_path)
    assert "slot-variants.yaml" in str(exc.value) and "reranker" in str(exc.value)


def test_published_only_and_unique_slugs(data):
    ids = sorted(front_matter(p)["id"] for p in flagship_pages())
    assert sorted(uc["id"] for uc in data["use_cases"]) == ids
    slugs = [uc["slug"] for uc in data["use_cases"]]
    assert len(set(slugs)) == len(slugs)
    for uc in data["use_cases"]:
        assert uc["recipe_url"] == f"recipes/{uc['domain']}/{uc['slug']}/"
        assert (REPO_ROOT / "catalog" / uc["domain"] / uc["slug"] / "README.md").is_file()


def test_unpublished_page_skipped(tmp_path):
    shutil.copytree(REPO_ROOT / "data", tmp_path / "data")
    shutil.copytree(REPO_ROOT / "catalog", tmp_path / "catalog")
    page = tmp_path / "catalog/standards-knowledge/grounded-knowledge-assistant/README.md"
    text = page.read_text(encoding="utf-8")
    start = text.index("\ncard:")
    end = text.index("\nplacement:")
    page.write_text(text[:start] + text[end:], encoding="utf-8")
    ids = [uc["id"] for uc in ex.build_explorer_data(tmp_path)["use_cases"]]
    assert "UC-KNOW-01" not in ids and ids


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


def test_cli_writes_json(tmp_path, data):
    out = tmp_path / "x.json"
    subprocess.run(
        [sys.executable, "-m", "tools.site.export_explorer", "--out", str(out)],
        cwd=REPO_ROOT,
        check=True,
    )
    assert json.loads(out.read_text(encoding="utf-8")) == data
