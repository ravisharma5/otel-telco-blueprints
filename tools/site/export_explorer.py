"""Export the use-case explorer's data from recipe front matter and serving data.

The explorer renders one JSON file and computes nothing itself. This module
joins each published use-case recipe (catalog/<domain>/<slug>/README.md with
`card` and `placement` in its front matter) with data/serving/*.yaml and the
recipe's own What you need and Governance tables, then precomputes every
use case x setup x batch state: tier cards, fit per GPU, key settings, model
variants, the quantized-check flag, and each advanced option's state.

Fit rule: count weights only. Start each slot at its smallest published GPU
build (the small LLM at its fit_reference build), pack the slots per GPU
largest first, and band each GPU by its share of memory. While a GPU is not in
the fits band, swap the heaviest slot on it that has an operator-made FP8 build
and pack again. Core setups use the published builds and show no fit bar.
A CPU-only setup has one state, shows no fit bar, and sums the weights of its
far-edge slots against the memory the operator sets aside. Its slots start at
their published CPU build where one exists, and a recipe that places a role at
the far edge outside the setup's cpu.roles stops the run.

Each use case also carries its story, read from the recipe body at build time:
the problem (the Problem and value paragraph up to its KPI sentence), the How it
works steps (first sentence of each numbered step), and the Worked example (its
title and up to three sentences of its first paragraph). A catalog entry stubs
How it works and has no worked example, so those blocks are left out, never invented.

Each use case carries its goal (card.goal, one id from data/explorer/goals.yaml)
and its recipe depth. The top-level goals list holds only goals that at least
one use case names, in file order, so the home page never shows an empty goal.

Any missing or inconsistent input stops the run with one line that names the
file and the key. A use-case page without `card` or `placement` stops the run
too; only pages of another type, and pages in the demo domain, are left out.

Usage:
    python -m tools.site.export_explorer [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt

from tools.bplint.ideas import IDEAS_DIR, is_idea
from tools.bplint.loader import load_yaml
from tools.bplint.markdown import parse_doc
from tools.site.render_bring import (
    CHANGE_LABELS,
    CHANGE_OF_RUNG,
    CHANGE_ORDER,
    EXPERTISE_LABELS,
    EXPERTISE_ORDER,
    RUNG_LABELS,
)
from tools.site.render_sandbox import FIT_LABELS, FIT_ORDER
from tools.site.render_serving import _source_labels

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "explorer/src/generated/explorer.json"
SERVING_PAGE = "platform/serving-routing-placement/README.md"
GOALS_FILE = "data/explorer/goals.yaml"
TRY_IT_FILE = "data/explorer/try-it.yaml"

TIERS = ("far-edge", "regional", "core")
BATCH_VALUES = ("yes", "no")
CPU_BATCH = "any"  # batch work changes nothing on a CPU-only site, so it has one state
FP8_ARCHES = ("ada", "hopper", "blackwell", "cdna3")

# Table headers the exporter parses on every recipe. The card-field tests hold
# the same tuples, so a header change fails both places.
EXPORTER_TABLE_HEADERS = {
    "components": ("Component role", "Red Hat product used"),
    "actions": ("Action", "Gate outcome (LOOK/NOTIFY/REVIEW/ACT/STOP)", "Approval", "AI Act class"),
    "parameters": ("Parameter", "What it controls", "Who sets it", "How to calibrate"),
}
TABLE_SECTIONS = {"components": "What you need", "actions": "Governance", "parameters": "Governance"}

DOMAIN_LABELS = {
    "standards-knowledge": "Standards and knowledge",
    "agentic-operations": "Agentic operations",
    "network-operations": "Network operations",
    "business-assurance": "Business assurance",
    "network-software": "Network software",
    "security": "Security",
    "research": "Research",
}
SKIPPED_DOMAINS = ("demo",)


# Recipe depth labels, shared with the Recipes overview (render_catalog imports them).
DEPTH_LABELS = {"recipe": "Full recipe", "entry": "Catalog entry"}

STAGE_IDS = {
    "inform": "inform",
    "notify": "inform",
    "recommend-with-approval": "recommend",
    "act-within-policy": "act",
}
STAGE_LABELS = {
    "inform": "Informs only",
    "recommend": "Recommends, a person approves",
    "act": "Acts within policy",
}

SLOT_NAMES = {
    "llm": "LLM",
    "embedding": "Embedding",
    "reranker": "Reranker",
    "safety": "Safety",
    "decision": "Decision",
    "classification": "Classification",
}
ROLE_NAMES = {
    "llm-large": "Large LLM",
    "llm-small": "Small LLM",
    "embedding": "Embedding",
    "reranker": "Reranker",
    "safety": "Safety",
    "decision": "Decision",
    "classification": "Classification",
}

REQUIRED_FM = (
    "id",
    "title",
    "domain",
    "doc_status",
    "otel_slots",
    "platform_blueprints",
    "placement_tier",
    "autonomy_ceiling",
    "depth",
    "adaptation",
    "sandbox",
)

_MD = MarkdownIt("commonmark")


# --- pure functions ---------------------------------------------------------


def _sandbox(sb, rel: str) -> dict:
    """The explorer's view of a use case's sandbox field: fit, its label, and the why line."""
    if not isinstance(sb, dict) or sb.get("fit") not in FIT_ORDER or sb.get("fit") not in FIT_LABELS:
        raise SystemExit(f"{rel}: sandbox.fit {(sb or {}).get('fit')!r} has no label")
    return {"fit": sb["fit"], "label": FIT_LABELS[sb["fit"]], "why": str(sb.get("why") or "").strip()}


def _adaptation(ad, rel: str) -> dict:
    """The explorer's view of a use case's adaptation field: rung, model change, and expertise labels."""
    if not isinstance(ad, dict) or ad.get("rung") not in RUNG_LABELS:
        raise SystemExit(f"{rel}: adaptation.rung {(ad or {}).get('rung')!r} has no label")
    chosen = ad.get("expertise") or []
    for e in chosen:
        if e not in EXPERTISE_LABELS:
            raise SystemExit(f"{rel}: adaptation.expertise {e!r} has no label")
    change = CHANGE_OF_RUNG[ad["rung"]]
    if change not in CHANGE_LABELS:
        raise SystemExit(f"{rel}: model change {change!r} has no label")
    return {
        "rung": ad["rung"],
        "change": change,
        "rung_label": RUNG_LABELS[ad["rung"]],
        "expertise": [{"id": e, "label": EXPERTISE_LABELS[e]} for e in EXPERTISE_ORDER if e in chosen],
    }


def band(pct: float, bands: dict) -> str:
    """Band word for a GPU at pct of its memory: fits, tight, or too-tight."""
    if pct <= bands["fits_max_pct"]:
        return "fits"
    if pct <= bands["tight_max_pct"]:
        return "tight"
    return "too-tight"


def pack(items, gpu_count: int, gpu_gb: float, fill_pct: float = 60, order=None):
    """Pack (name, weights_gb) items onto gpu_count GPUs, largest first.

    First fit within fill_pct of a GPU (the fits band); a slot that fits no
    GPU's band goes on the GPU with the most room, so the load spreads across
    GPUs instead of piling onto the first one. Ties in weight follow `order` (a list of
    names), else the name, so the result never depends on input order.
    Returns one list of (name, weights_gb) per GPU.
    """
    rank = {name: i for i, name in enumerate(order or [])}

    def key(item):
        name, weight = item
        return (-weight, rank.get(name, len(rank)), name)

    soft = gpu_gb * fill_pct / 100
    bins: list[list] = [[] for _ in range(gpu_count)]
    loads = [0.0] * gpu_count
    for name, weight in sorted(items, key=key):
        target = next((i for i in range(gpu_count) if loads[i] + weight <= soft), None)
        if target is None:
            target = max(range(gpu_count), key=lambda i: (gpu_gb - loads[i], -i))
        bins[target].append([name, weight])
        loads[target] += weight
    return [[(n, w) for n, w in b] for b in bins]


def _role_order(variants) -> list[str]:
    order: list[str] = []
    for v in variants:
        if v["role"] not in order:
            order.append(v["role"])
    return order


def _is_cpu(setup: dict) -> bool:
    """A CPU-only setup has no accelerators (and a cpu block instead)."""
    return setup["accelerators"] is None


def _start_variant(role: str, variants, cpu: bool = False) -> dict:
    """Smallest published GPU build for a role; the small LLM uses its fit_reference build.

    With cpu true, a role that has a published CPU build (gpu false) starts there.
    """
    if cpu:
        cpu_builds = [v for v in variants if v["role"] == role and not v["gpu"] and v["source"] == "published"]
        if cpu_builds:
            return min(cpu_builds, key=lambda v: v["weights_gb"])
    if role == "llm-small":
        refs = [v for v in variants if v["role"] == role and v.get("fit_reference")]
        if len(refs) != 1:
            raise SystemExit(
                f"data/serving/slot-variants.yaml: llm-small needs exactly one fit_reference variant, found {len(refs)}"
            )
        return refs[0]
    published = [v for v in variants if v["role"] == role and v["gpu"] and v["source"] == "published"]
    if not published:
        raise SystemExit(f"data/serving/slot-variants.yaml: no published GPU variant for role {role}")
    return min(published, key=lambda v: v["weights_gb"])


def _fp8_variant(role: str, variants) -> dict | None:
    builds = [
        v
        for v in variants
        if v["role"] == role and v["gpu"] and v["source"] == "operator-made" and v["precision"] == "fp8"
    ]
    return min(builds, key=lambda v: v["weights_gb"]) if builds else None


def _shown_pct(share: float, bands: dict) -> float:
    """Percent for display. Whole numbers, except one decimal (rounded up) when
    rounding would land on a band edge the share is past, so 60.2% never reads 60%."""
    pct = round(share)
    if pct in (bands["fits_max_pct"], bands["tight_max_pct"]) and share > pct:
        return math.ceil(share * 10) / 10
    return pct


def _smaller_fp8(role: str, current: dict, variants) -> dict | None:
    """The role's operator-made FP8 build, only when it is smaller than the current build."""
    build = _fp8_variant(role, variants)
    if build and build["id"] != current["id"] and build["weights_gb"] < current["weights_gb"]:
        return build
    return None


def _gpu_fit(bins, gpu_gb: float, bands: dict) -> list[dict]:
    """Fit per GPU. The band comes from the unrounded share; only display values round."""
    fit = []
    for i, b in enumerate(bins):
        total = sum(w for _, w in b)
        share = 100 * total / gpu_gb
        weights = round(total, 1)
        pct = _shown_pct(share, bands)
        fit.append(
            {
                "gpu_index": i + 1,
                "gpu_count": len(bins),
                "slots": [{"role": r, "slot_name": ROLE_NAMES[r], "weights_gb": w} for r, w in b],
                "weights_gb": weights,
                "total_gb": gpu_gb,
                "pct": pct,
                "band": band(share, bands),
            }
        )
    return fit


def choose_variants(roles, setup: dict, variants, bands: dict):
    """Pick a build per placed role for a setup. Returns (variants in role order, fit per GPU).

    Core setups keep the published builds and return no fit. Regional setups
    swap to operator-made FP8 builds, heaviest first on a GPU that is not in
    the fits band, until every GPU fits or no FP8 build is left.
    """
    current = {role: _start_variant(role, variants, cpu=_is_cpu(setup)) for role in roles}
    if setup["tier"] != "regional" or _is_cpu(setup) or not roles:
        return [current[r] for r in roles], []
    acc = setup["accelerators"]
    count, gpu_gb = acc["count_per_node"], acc["memory_per_gpu_gb"]
    order = _role_order(variants)
    swapped: set[str] = set()
    while True:
        bins = pack(
            [(r, current[r]["weights_gb"]) for r in roles], count, gpu_gb, bands["fits_max_pct"], order
        )
        fit = _gpu_fit(bins, gpu_gb, bands)
        if all(f["band"] == "fits" for f in fit) or acc["arch"] not in FP8_ARCHES:
            break
        candidate = None
        for b, f in zip(bins, fit):
            if f["band"] == "fits":
                continue
            options = [r for r, _ in b if r not in swapped and _smaller_fp8(r, current[r], variants)]
            if options:
                candidate = min(options, key=lambda r: (-current[r]["weights_gb"], order.index(r)))
                break
        if candidate is None:
            break
        current[candidate] = _fp8_variant(candidate, variants)
        swapped.add(candidate)
    fp8_arch = acc["arch"] in FP8_ARCHES
    for f in fit:
        fp8_left = fp8_arch and any(_smaller_fp8(s["role"], current[s["role"]], variants) for s in f["slots"])
        # A too-tight GPU suggests FP8 only while one of its slots still has an unused build.
        f["message_id"] = (
            ("too-tight" if fp8_left else "too-tight-after-fp8") if f["band"] == "too-tight" else f["band"]
        )
    return [current[r] for r in roles], fit


def _cpu_fit(roles, setup: dict, variants) -> dict | None:
    """Weights of the far-edge slots on a CPU-only setup, from their CPU-preferred builds.

    No band and no percent: the operator compares the sum with the memory set aside
    for AI (the setup's memory parameter, which has no default). None for GPU setups
    and when nothing runs at the setup's tier.
    """
    if not _is_cpu(setup) or not roles:
        return None
    slots = [
        {"role": r, "slot_name": ROLE_NAMES[r], "weights_gb": _start_variant(r, variants, cpu=True)["weights_gb"]}
        for r in roles
    ]
    return {
        "slots": slots,
        "weights_gb": round(sum(s["weights_gb"] for s in slots), 1),
        "memory_parameter": setup["cpu"]["memory_parameter"],
    }


FIT_NOTES = {"fits": None, "tight": "still-tight", "too-tight": "still-too-tight"}
BAND_ORDER = ("fits", "tight", "too-tight")


def worst_band(fit) -> str:
    """Tightest band across a state's GPUs; fits when there is no fit bar."""
    return max((f["band"] for f in fit), key=BAND_ORDER.index, default="fits")


def option_state(
    option: dict,
    setup: dict,
    batch: str,
    use_case_id: str,
    fp8_swap: bool = False,
    band_after: str = "fits",
    placement: dict | None = None,
    swapped_roles: list[str] | None = None,
) -> dict:
    """State of one advanced option for a use case at a setup and batch value.

    fp8_swap says whether the fit rule swapped in an FP8 build; band_after is the
    tightest band after the swaps. An option with an fp8_swap rule follows the
    fit: it helps only where builds were swapped, and its fit_note_id says when
    the setup is still tight or too tight.

    placement is the recipe's placement map. When given, an option helps only if
    a role its where_it_helps entry names, and the option does not exclude, runs
    at the setup's tier; if those roles run only at another tier, the option does
    not apply here and its reason id names that tier (helps-at-<tier>).

    swapped_roles lists the roles the fit rule swapped to FP8 builds, in placement
    order. A fit-dependent option that helps returns reason id fp8-swapped with
    those roles in reason_roles, so its reason names only the swapped slots.
    """
    props = {
        "tier": setup["tier"],
        "vendor": setup["accelerators"]["vendor"],
        "batch": batch,
        "arch": setup["accelerators"]["arch"],
        "fp8_swap": "yes" if fp8_swap else "no",
    }
    fit_dependent = any(r["rule"] == "fp8_swap" for r in option.get("applies_when") or [])
    helps = {w["use_case"]: w["reason"] for w in option.get("where_it_helps") or []}
    would_help = use_case_id in helps
    for rule in option.get("applies_when") or []:
        if rule["rule"] not in props:
            raise SystemExit(f"data/serving/options.yaml: {option['id']}.applies_when has unknown rule {rule['rule']}")
        if props[rule["rule"]] not in rule["allowed"]:
            return {
                "state": "not-applicable",
                "reason_id": rule["reason"],
                "reason_text": None,
                "reason_roles": [],
                "would_help": would_help,
                "fit_note_id": None,
            }
    if fit_dependent and not would_help:
        raise SystemExit(
            f"data/serving/options.yaml: {option['id']}.where_it_helps needs a reason for {use_case_id}, "
            "whose state swaps in FP8 builds"
        )
    if would_help and placement is not None:
        entry = next(w for w in option["where_it_helps"] if w["use_case"] == use_case_id)
        excluded = set(option.get("excluded_slots") or [])
        targets = [r for r in entry["roles"] if r not in excluded]
        if not targets:
            raise SystemExit(
                f"data/serving/options.yaml: {option['id']}.where_it_helps for {use_case_id} "
                "names only excluded slots"
            )
        runs_at = {t: set((placement.get(t) or {}).get("runs") or []) for t in TIERS}
        if not set(targets) & runs_at[setup["tier"]]:
            other = next((t for t in TIERS if set(targets) & runs_at[t]), None)
            if other is None:
                raise SystemExit(
                    f"data/serving/options.yaml: {option['id']}.where_it_helps for {use_case_id} "
                    f"names roles {', '.join(targets)} that its recipe places nowhere"
                )
            return {
                "state": "not-applicable",
                "reason_id": f"helps-at-{other}",
                "reason_text": None,
                "reason_roles": [],
                "would_help": True,
                "fit_note_id": None,
            }
    if would_help and fit_dependent and swapped_roles:
        # The reason names the slots this state swapped, not the use case's general text.
        return {
            "state": "helps",
            "reason_id": "fp8-swapped",
            "reason_text": None,
            "reason_roles": list(swapped_roles),
            "would_help": True,
            "fit_note_id": FIT_NOTES[band_after],
        }
    if would_help:
        return {
            "state": "helps",
            "reason_id": None,
            "reason_text": helps[use_case_id],
            "reason_roles": [],
            "would_help": True,
            "fit_note_id": FIT_NOTES[band_after] if fit_dependent else None,
        }
    return {
        "state": "little",
        "reason_id": None,
        "reason_text": None,
        "reason_roles": [],
        "would_help": False,
        "fit_note_id": None,
    }


# --- recipe pages -----------------------------------------------------------


def _plain(cell: str) -> str:
    """Inline markdown to plain text: link text kept, code spans unwrapped."""
    tokens = _MD.parseInline(cell)
    children = (tokens[0].children or []) if tokens else []
    parts = []
    for c in children:
        if c.type in ("text", "code_inline"):
            parts.append(c.content)
        elif c.type in ("softbreak", "hardbreak"):
            parts.append(" ")
    return "".join(parts).strip()


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"(])")
EXAMPLE_PREFIX = "Worked example:"
EXAMPLE_SENTENCES = 3


def _sentences(text: str) -> list[str]:
    """Split plain text into sentences: a stop, then space, then a capital, digit, quote, or bracket."""
    return [s for s in _SENTENCE_END.split(" ".join(text.split())) if s]


def _blocks(body: str):
    """Top-level blocks of a section body: ("p", text), ("ol", [item text]), ("h3", title)."""
    tokens = _MD.parse(body)
    out = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "paragraph_open" and t.level == 0:
            out.append(("p", _plain(tokens[i + 1].content)))
        elif t.type == "heading_open" and t.tag == "h3":
            out.append(("h3", tokens[i + 1].content.strip()))
        elif t.type == "ordered_list_open" and t.level == 0:
            items, depth = [], 0
            i += 1
            while tokens[i].type != "ordered_list_close" or depth:
                tk = tokens[i]
                if tk.type in ("ordered_list_open", "bullet_list_open"):
                    depth += 1
                elif tk.type in ("ordered_list_close", "bullet_list_close"):
                    depth -= 1
                elif tk.type == "list_item_open" and not depth:
                    items.append(None)
                elif tk.type == "inline" and not depth and items and items[-1] is None:
                    items[-1] = _plain(tk.content)
                i += 1
            out.append(("ol", [x or "" for x in items]))
        i += 1
    return out


def _story(doc, rel: str, depth: str) -> dict:
    """Problem, How it works steps, and worked example, as plain text from the recipe."""
    section = doc.section("Problem and value")
    paras = [b for kind, b in _blocks(section.body_text if section else "") if kind == "p"]
    if not paras:
        raise SystemExit(f"{rel}: Problem and value has no paragraph for the explorer story")
    problem = []
    for sentence in _sentences(paras[0]):
        if sentence.startswith("The KPI"):
            break
        problem.append(sentence)
    steps, example = [], None
    how = doc.section("How it works")
    blocks = _blocks(how.body_text) if how else []
    lists = [b for kind, b in blocks if kind == "ol"]
    if lists:
        steps = [_sentences(item)[0] for item in lists[0] if item]
    for i, (kind, value) in enumerate(blocks):
        if kind == "h3" and value.startswith(EXAMPLE_PREFIX):
            text = next((b for k, b in blocks[i + 1 :] if k == "p"), "")
            if text:
                example = {
                    "title": value[len(EXAMPLE_PREFIX) :].strip(),
                    "text": " ".join(_sentences(text)[:EXAMPLE_SENTENCES]),
                }
            break
    if depth == "recipe" and not (steps and example):
        raise SystemExit(f"{rel}: a full recipe needs numbered How it works steps and a {EXAMPLE_PREFIX} section")
    return {"problem": " ".join(problem), "steps": steps, "example": example}


def _table(doc, rel: str, key: str) -> list[list[str]]:
    section_name = TABLE_SECTIONS[key]
    expected = EXPORTER_TABLE_HEADERS[key]
    section = doc.section(section_name)
    tables = section.tables if section else []
    hits = [t for t in tables if tuple(t.header) == expected]
    if len(hits) != 1:
        near = [t for t in tables if t.header and t.header[0] == expected[0]]
        missing = [h for h in expected if not near or h not in near[0].header] or list(expected)
        raise SystemExit(
            f"{rel}: {section_name} needs one table with header {' | '.join(expected)}; "
            f"missing header {', '.join(missing)}"
        )
    rows = [[_plain(c) for c in r.cells] for r in hits[0].rows]
    if not rows:
        raise SystemExit(f"{rel}: {section_name} table {expected[0]} has no rows")
    return rows


def _load(repo_root: Path, name: str) -> dict:
    path = repo_root / "data/serving" / name
    if not path.is_file():
        raise SystemExit(f"data/serving/{name}: file not found")
    return load_yaml(path)


def _need(mapping: dict, key: str, where: str):
    if key not in mapping or mapping[key] is None:
        raise SystemExit(f"{where}: missing key {key}")
    return mapping[key]


def _tier_cards(placement: dict, setup: dict) -> list[dict]:
    cards = []
    for tier in TIERS:
        entry = placement.get(tier) or {}
        runs = entry.get("runs") or []
        cards.append(
            {
                "tier": tier,
                "used": bool(runs),
                "matches_setup": tier == setup["tier"],
                "slots": [{"role": r, "slot_name": ROLE_NAMES[r]} for r in runs],
                "note": entry.get("note") or "",
            }
        )
    return cards


def _setup_row_applies(row: dict, setup: dict, batch: str | None, roles: list[str], swapped: bool) -> bool:
    """A per-setup row shows for its setup and batch value, and only when its
    when_roles (a role placed at the tier) and when_fp8_swap (an FP8 build was
    swapped in) conditions hold."""
    return (
        row["setup"] == setup["id"]
        and row.get("when_batch") in (None, batch)
        and (not row.get("when_roles") or bool(set(row["when_roles"]) & set(roles)))
        and (not row.get("when_fp8_swap") or swapped)
    )


def _sources(urls: list[str], labels: dict[str, str], where: str) -> list[dict]:
    """URLs as {url, label}, each label read from the serving page Sources table."""
    missing = [u for u in urls if u not in labels]
    if missing:
        raise SystemExit(f"{where}: source missing from the {SERVING_PAGE} Sources table: {', '.join(missing)}")
    return [{"url": u, "label": labels[u]} for u in urls]


def _flags(flags: dict, setup: dict, batch: str | None, roles: list[str], swapped: bool, labels: dict) -> list[dict]:
    out = [
        {
            "setting": r["setting"],
            "value": r["value"],
            "why": r["why"],
            "scope": "setup",
            "sources": _sources([r["source"]], labels, f"data/serving/flags.yaml: per_setup {r['setting']}"),
        }
        for r in flags["per_setup"]
        if _setup_row_applies(r, setup, batch, roles, swapped)
    ]
    for block in flags["per_slot"]:
        if set(roles) & set(block["roles"]):
            sources = _sources(block["sources"], labels, f"data/serving/flags.yaml: per_slot {block['id']}")
            for line in block["lines"]:
                out += [
                    {
                        "setting": a["flag"],
                        "value": a["value"],
                        "why": a["why"],
                        "scope": block["comment"],
                        "sources": sources,
                    }
                    for a in line["args"]
                ]
    return out


def _variant_rows(chosen, tier: str) -> list[dict]:
    return [
        {
            "role": v["role"],
            "slot_name": ROLE_NAMES[v["role"]],
            "tier": tier,
            "variant_id": v["id"],
            "checkpoint": v["checkpoint"],
            "precision": v["precision"],
            "operator_made": v["source"] == "operator-made",
            "model_card": v["model_card"],
            "red_hat_build": v["red_hat_build"],
        }
        for v in chosen
    ]


OPTION_TEXT_KEYS = ("name", "engine", "tiers", "what", "set", "check", "limits", "related", "excluded_slots")


def _state(uc_id, placement, setup, batch, data) -> dict:
    roles = list((placement.get(setup["tier"]) or {}).get("runs") or [])
    chosen, fit = choose_variants(roles, setup, data["variants"], data["bands"])
    variants = _variant_rows(chosen, setup["tier"])
    # Slots at the other tiers keep their starting build, so Models shows every slot.
    other_tier_variants = []
    for tier in TIERS:
        if tier == setup["tier"]:
            continue
        runs = list((placement.get(tier) or {}).get("runs") or [])
        other_tier_variants += _variant_rows([_start_variant(r, data["variants"]) for r in runs], tier)
    swapped_roles = [v["role"] for v in variants if v["operator_made"]]
    swapped = bool(swapped_roles)
    cpu = _is_cpu(setup)
    options = []
    # A CPU-only setup has no advanced options: every option reads the setup's GPUs.
    for opt in [] if cpu else data["options"]:
        row = {"id": opt["id"], **{k: opt.get(k) for k in OPTION_TEXT_KEYS}}
        row["sources"] = _sources(opt["sources"], data["source_labels"], f"data/serving/options.yaml: {opt['id']}")
        row.update(option_state(opt, setup, batch, uc_id, swapped, worst_band(fit), placement, swapped_roles))
        options.append(row)
    return {
        "tiers": _tier_cards(placement, setup),
        "fit": fit,
        "runs_here": bool(roles),
        "cpu_fit": _cpu_fit(roles, setup, data["variants"]),
        "flags": _flags(data["flags"], setup, None if cpu else batch, roles, swapped, data["source_labels"]),
        "variants": variants,
        "other_tier_variants": other_tier_variants,
        "quantized_check": any(v["operator_made"] for v in variants),
        "options": options,
        "options_worth_testing": sum(1 for o in options if o["state"] == "helps"),
    }


def _batch_values(setup: dict) -> list[str]:
    return [CPU_BATCH] if _is_cpu(setup) else list(BATCH_VALUES)


def _front_matter(path: Path, repo_root: Path) -> dict:
    rel = path.relative_to(repo_root).as_posix()
    doc = parse_doc(path, path.read_text(encoding="utf-8"), display=rel)
    if doc.fm_error:
        raise SystemExit(f"{rel}: front matter line {doc.fm_error[0]}: {doc.fm_error[1]}")
    return doc.front_matter or {}


def _idea(path: Path, repo_root: Path, fm: dict) -> dict:
    """One Ideas sub-tab record; ideas never enter the gallery."""
    rel = path.relative_to(repo_root).as_posix()
    if fm.get("type") != "use-case":
        raise SystemExit(f"{rel}: an idea page must be type use-case")
    if path.parent.parent.name != IDEAS_DIR:
        raise SystemExit(f"{rel}: an idea page must sit in catalog/{IDEAS_DIR}/")
    for key in ("id", "title", "domain", "depth"):
        _need(fm, key, rel)
    domain, slug, idea = fm["domain"], path.parent.name, fm["idea"]
    if domain not in DOMAIN_LABELS:
        raise SystemExit(f"{rel}: domain {domain} has no explorer label")
    if fm["depth"] not in DEPTH_LABELS:
        raise SystemExit(f"{rel}: depth {fm['depth']} has no label")
    if not isinstance(idea.get("why"), str) or not idea["why"].strip():
        raise SystemExit(f"{rel}: idea.why must be a non-empty string")
    promote = idea.get("promote")
    if not isinstance(promote, list) or not promote or not all(isinstance(p, str) and p.strip() for p in promote):
        raise SystemExit(f"{rel}: idea.promote must be a non-empty list of strings")
    merged_into = idea.get("merged_into")
    if merged_into is not None and not isinstance(merged_into, str):
        raise SystemExit(f"{rel}: idea.merged_into must be a use-case id")
    return {
        "id": fm["id"],
        "title": fm["title"],
        "slug": slug,
        "domain": {"id": domain, "label": DOMAIN_LABELS[domain]},
        "depth": {"id": fm["depth"], "label": DEPTH_LABELS[fm["depth"]]},
        "why": idea["why"],
        "promote": list(promote),
        "merged_into": merged_into,
        "docs_url": f"recipes/{IDEAS_DIR}/{slug}/",
    }


def _use_case(path: Path, repo_root: Path, data: dict) -> dict | None:
    rel = path.relative_to(repo_root).as_posix()
    doc = parse_doc(path, path.read_text(encoding="utf-8"), display=rel)
    if doc.fm_error:
        raise SystemExit(f"{rel}: front matter line {doc.fm_error[0]}: {doc.fm_error[1]}")
    fm = doc.front_matter or {}
    if fm.get("type") != "use-case":
        return None  # only use-case pages belong in the explorer
    for key in ("card", "placement"):
        if not fm.get(key):
            raise SystemExit(f"{rel}: use-case front matter has no {key}; the explorer cannot show this page")
    for key in REQUIRED_FM:
        _need(fm, key, rel)
    domain, slug = path.parent.parent.name, path.parent.name
    if fm["domain"] != domain:
        raise SystemExit(f"{rel}: domain {fm['domain']} does not match its folder {domain}")
    if domain not in DOMAIN_LABELS:
        raise SystemExit(f"{rel}: domain {domain} has no explorer label")
    goal = fm["card"].get("goal")
    if goal not in data["goal_ids"]:
        raise SystemExit(f"{rel}: card.goal {goal} is not a goal id in {GOALS_FILE}")
    if fm["depth"] not in DEPTH_LABELS:
        raise SystemExit(f"{rel}: depth {fm['depth']} has no label")
    if fm["autonomy_ceiling"] not in STAGE_IDS:
        raise SystemExit(f"{rel}: autonomy_ceiling {fm['autonomy_ceiling']} has no stage label")
    adaptation = _adaptation(fm["adaptation"], rel)
    sandbox = _sandbox(fm["sandbox"], rel)
    placement = fm["placement"]
    known_roles = set(_role_order(data["variants"]))
    for tier, entry in placement.items():
        if tier not in TIERS:
            raise SystemExit(f"{rel}: placement has unknown tier {tier}")
        for role in (entry or {}).get("runs") or []:
            if role not in ROLE_NAMES:
                raise SystemExit(f"{rel}: placement.{tier} has unknown role {role}")
            if role not in known_roles:
                raise SystemExit(f"data/serving/slot-variants.yaml: no variant for role {role} placed by {rel}")
    for setup in data["setups"]:
        if not setup.get("cpu"):
            continue
        for role in (placement.get(setup["tier"]) or {}).get("runs") or []:
            if role not in setup["cpu"]["roles"]:
                raise SystemExit(
                    f"{rel}: placement.{setup['tier']} runs {role}, which {setup['id']} does not list in cpu.roles"
                )
    for slot in fm["otel_slots"]:
        if slot not in SLOT_NAMES:
            raise SystemExit(f"{rel}: otel_slots has unknown slot {slot}")
    stage_id = STAGE_IDS[fm["autonomy_ceiling"]]
    components = _table(doc, rel, "components")
    actions = _table(doc, rel, "actions")
    params = _table(doc, rel, "parameters")
    who = EXPORTER_TABLE_HEADERS["parameters"].index("Who sets it")
    for row in params:
        if not row[who]:
            raise SystemExit(f"{rel}: parameter {row[0]} has an empty Who sets it cell")
    states = {
        setup["id"]: {batch: _state(fm["id"], placement, setup, batch, data) for batch in _batch_values(setup)}
        for setup in data["setups"]
    }
    return {
        "id": fm["id"],
        "slug": slug,
        "domain": domain,
        "domain_label": DOMAIN_LABELS[domain],
        "title": fm["title"],
        "recipe_url": f"recipes/{domain}/{slug}/",
        "doc_status": fm["doc_status"],
        "stage": {"id": stage_id, "label": STAGE_LABELS[stage_id]},
        "goal": goal,
        "depth": {"id": fm["depth"], "label": DEPTH_LABELS[fm["depth"]]},
        "adaptation": adaptation,
        "sandbox": sandbox,
        "try_it_url": data["try_it"].get(fm["id"]),
        "card": fm["card"],
        "story": _story(doc, rel, fm["depth"]),
        "counts": {
            "slots": len(fm["otel_slots"]),
            "blueprints": len(fm["platform_blueprints"]),
            "tiers": len(fm["placement_tier"]),
        },
        "slot_names": [SLOT_NAMES[s] for s in fm["otel_slots"]],
        "platform_rows": [row[:2] for row in components],
        "approvals": [row[:3] for row in actions],
        "parameters": [[row[0], row[who]] for row in params],
        "states": states,
    }


# --- top level --------------------------------------------------------------


def _goal_ids(repo_root: Path) -> list[str]:
    path = repo_root / GOALS_FILE
    if not path.is_file():
        raise SystemExit(f"{GOALS_FILE}: file not found")
    goals = (load_yaml(path) or {}).get("goals")
    if not goals or not all(isinstance(g, str) for g in goals):
        raise SystemExit(f"{GOALS_FILE}: missing key goals (a list of ids)")
    if len(set(goals)) != len(goals):
        raise SystemExit(f"{GOALS_FILE}: goal ids must be unique")
    return goals


def _try_it(repo_root: Path) -> dict[str, str]:
    """Use-case id to reference-implementation URL; a missing file means no Try it links."""
    path = repo_root / TRY_IT_FILE
    if not path.is_file():
        return {}
    entries = load_yaml(path) or {}
    if not isinstance(entries, dict):
        raise SystemExit(f"{TRY_IT_FILE}: expected a map of use-case id to URL")
    for uc_id, url in entries.items():
        if not isinstance(url, str) or not url.startswith("https://"):
            raise SystemExit(f"{TRY_IT_FILE}: {uc_id} needs an https URL, got {url!r}")
    return entries


def _serving_data(repo_root: Path) -> dict:
    setups = _load(repo_root, "setups.yaml")
    variants = _need(_load(repo_root, "slot-variants.yaml"), "variants", "data/serving/slot-variants.yaml")
    flags = _load(repo_root, "flags.yaml")
    options = _need(_load(repo_root, "options.yaml"), "options", "data/serving/options.yaml")
    for key in ("default", "fit_bands", "setups"):
        _need(setups, key, "data/serving/setups.yaml")
    for key in ("per_slot", "per_setup"):
        _need(flags, key, "data/serving/flags.yaml")
    setup_ids = [s["id"] for s in setups["setups"]]
    for row in flags["per_setup"]:
        if row["setup"] not in setup_ids:
            raise SystemExit(f"data/serving/flags.yaml: per_setup names unknown setup {row['setup']}")
    if setups["default"]["setup"] not in setup_ids:
        raise SystemExit(f"data/serving/setups.yaml: default.setup {setups['default']['setup']} is not a setup")
    ids = [o["id"] for o in options]
    if len(set(ids)) != len(ids):
        raise SystemExit("data/serving/options.yaml: option ids must be unique")
    page = repo_root / SERVING_PAGE
    if not page.is_file():
        raise SystemExit(f"{SERVING_PAGE}: file not found")
    return {
        "source_labels": _source_labels(page.read_text(encoding="utf-8")),
        "setups_doc": setups,
        "setups": setups["setups"],
        "bands": setups["fit_bands"],
        "variants": variants,
        "flags": flags,
        "options": options,
    }


def build_explorer_data(repo_root: Path = ROOT) -> dict:
    """Everything the explorer renders, as one JSON-ready dict."""
    repo_root = Path(repo_root)
    data = _serving_data(repo_root)
    data["goal_ids"] = _goal_ids(repo_root)
    data["try_it"] = _try_it(repo_root)
    use_cases, ideas = [], []
    for path in sorted((repo_root / "catalog").glob("*/*/README.md")):
        if path.parent.parent.name in SKIPPED_DOMAINS:
            continue
        fm = _front_matter(path, repo_root)
        if is_idea(fm):
            ideas.append(_idea(path, repo_root, fm))
            continue
        uc = _use_case(path, repo_root, data)
        if uc is not None:
            use_cases.append(uc)
    domain_rank = list(DOMAIN_LABELS)
    use_cases.sort(key=lambda u: (domain_rank.index(u["domain"]), u["slug"]))
    unknown = sorted(set(data["try_it"]) - {u["id"] for u in use_cases})
    if unknown:
        raise SystemExit(f"{TRY_IT_FILE}: unknown use-case id {', '.join(unknown)}")
    for key in ("id", "slug"):
        values = [u[key] for u in use_cases]
        if len(set(values)) != len(values):
            raise SystemExit(f"catalog: use-case {key} values must be unique")
    ideas.sort(key=lambda i: i["id"])
    for key in ("id", "slug"):
        values = [i[key] for i in ideas]
        if len(set(values)) != len(values):
            raise SystemExit(f"catalog/{IDEAS_DIR}: idea {key} values must be unique")
    shared = sorted({i["slug"] for i in ideas} & {u["slug"] for u in use_cases})
    if shared:
        raise SystemExit(f"catalog/{IDEAS_DIR}: idea slug also used by a use case: {', '.join(shared)}")
    domains = {u["domain"] for u in use_cases}
    stages = {u["stage"]["id"] for u in use_cases}
    depths = {u["depth"]["id"] for u in use_cases}
    changes = {u["adaptation"]["change"] for u in use_cases}
    goal_counts = {g: sum(1 for u in use_cases if u["goal"] == g) for g in data["goal_ids"]}
    tiers = {
        c["tier"]
        for u in use_cases
        for by_batch in u["states"].values()
        for c in next(iter(by_batch.values()))["tiers"]
        if c["used"]
    }
    return {
        "setups": [
            {
                "id": s["id"],
                "label": s["label"],
                "tier": s["tier"],
                "ampere_note": s["ampere_note"],
                "gpu_count": 0 if _is_cpu(s) else s["accelerators"]["count_per_node"],
                "memory_per_gpu_gb": None if _is_cpu(s) else s["accelerators"]["memory_per_gpu_gb"],
                "vendor": None if _is_cpu(s) else s["accelerators"]["vendor"],
                "cpu_only": _is_cpu(s),
                "batch_values": _batch_values(s),
            }
            for s in data["setups"]
        ],
        "default": data["setups_doc"]["default"],
        "fit_bands": data["bands"],
        "goals": [{"id": g, "count": n} for g, n in goal_counts.items() if n > 0],
        "filters": {
            "domains": [{"id": d, "label": DOMAIN_LABELS[d]} for d in DOMAIN_LABELS if d in domains],
            "stages": [{"id": s, "label": STAGE_LABELS[s]} for s in STAGE_LABELS if s in stages],
            "tiers": [t for t in TIERS if t in tiers],
            "depths": [d for d in DEPTH_LABELS if d in depths],
            "changes": [c for c in CHANGE_ORDER if c in changes],
        },
        "use_cases": use_cases,
        "ideas": ideas,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output JSON path")
    args = parser.parse_args(argv)
    data = build_explorer_data(ROOT)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
