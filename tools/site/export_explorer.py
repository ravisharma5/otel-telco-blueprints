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

Any missing or inconsistent input stops the run with one line that names the
file and the key; nothing is skipped silently.

Usage:
    python -m tools.site.export_explorer [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from markdown_it import MarkdownIt

from tools.bplint.loader import load_yaml
from tools.bplint.markdown import parse_doc

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "explorer/src/generated/explorer.json"

TIERS = ("far-edge", "regional", "core")
BATCH_VALUES = ("yes", "no")
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
)

_MD = MarkdownIt("commonmark")


# --- pure functions ---------------------------------------------------------


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


def _start_variant(role: str, variants) -> dict:
    """Smallest published GPU build for a role; the small LLM uses its fit_reference build."""
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


def _gpu_fit(bins, gpu_gb: float, bands: dict) -> list[dict]:
    fit = []
    for i, b in enumerate(bins):
        weights = round(sum(w for _, w in b), 1)
        pct = round(100 * weights / gpu_gb)
        fit.append(
            {
                "gpu_index": i + 1,
                "gpu_count": len(bins),
                "slots": [{"role": r, "slot_name": ROLE_NAMES[r], "weights_gb": w} for r, w in b],
                "weights_gb": weights,
                "total_gb": gpu_gb,
                "pct": pct,
                "band": band(pct, bands),
            }
        )
    return fit


def choose_variants(roles, setup: dict, variants, bands: dict):
    """Pick a build per placed role for a setup. Returns (variants in role order, fit per GPU).

    Core setups keep the published builds and return no fit. Regional setups
    swap to operator-made FP8 builds, heaviest first on a GPU that is not in
    the fits band, until every GPU fits or no FP8 build is left.
    """
    current = {role: _start_variant(role, variants) for role in roles}
    if setup["tier"] != "regional" or not roles:
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
            options = [r for r, _ in b if r not in swapped and _fp8_variant(r, variants)]
            if options:
                candidate = min(options, key=lambda r: (-current[r]["weights_gb"], order.index(r)))
                break
        if candidate is None:
            break
        current[candidate] = _fp8_variant(candidate, variants)
        swapped.add(candidate)
    return [current[r] for r in roles], fit


def option_state(option: dict, setup: dict, batch: str, use_case_id: str) -> dict:
    """State of one advanced option for a use case at a setup and batch value."""
    props = {
        "tier": setup["tier"],
        "vendor": setup["accelerators"]["vendor"],
        "batch": batch,
        "arch": setup["accelerators"]["arch"],
    }
    helps = {w["use_case"]: w["reason"] for w in option.get("where_it_helps") or []}
    would_help = use_case_id in helps
    for rule in option.get("applies_when") or []:
        if rule["rule"] not in props:
            raise SystemExit(f"data/serving/options.yaml: {option['id']}.applies_when has unknown rule {rule['rule']}")
        if props[rule["rule"]] not in rule["allowed"]:
            return {"state": "not-applicable", "reason_id": rule["reason"], "reason_text": None, "would_help": would_help}
    if would_help:
        return {"state": "helps", "reason_id": None, "reason_text": helps[use_case_id], "would_help": True}
    return {"state": "little", "reason_id": None, "reason_text": None, "would_help": False}


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


def _flags(flags: dict, setup: dict, batch: str, roles: list[str]) -> list[dict]:
    out = [
        {"setting": r["setting"], "value": r["value"], "why": r["why"], "scope": "setup"}
        for r in flags["per_setup"]
        if r["setup"] == setup["id"] and r.get("when_batch") in (None, batch)
    ]
    for block in flags["per_slot"]:
        if set(roles) & set(block["roles"]):
            for line in block["lines"]:
                out += [
                    {"setting": a["flag"], "value": a["value"], "why": a["why"], "scope": block["comment"]}
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
    options = []
    for opt in data["options"]:
        row = {"id": opt["id"], **{k: opt.get(k) for k in OPTION_TEXT_KEYS}}
        row.update(option_state(opt, setup, batch, uc_id))
        options.append(row)
    return {
        "tiers": _tier_cards(placement, setup),
        "fit": fit,
        "flags": _flags(data["flags"], setup, batch, roles),
        "variants": variants,
        "quantized_check": any(v["operator_made"] for v in variants),
        "options": options,
        "options_worth_testing": sum(1 for o in options if o["state"] == "helps"),
    }


def _use_case(path: Path, repo_root: Path, data: dict) -> dict | None:
    rel = path.relative_to(repo_root).as_posix()
    doc = parse_doc(path, path.read_text(encoding="utf-8"), display=rel)
    if doc.fm_error:
        raise SystemExit(f"{rel}: front matter line {doc.fm_error[0]}: {doc.fm_error[1]}")
    fm = doc.front_matter or {}
    if fm.get("type") != "use-case" or not fm.get("card") or not fm.get("placement"):
        return None  # only published use cases with card and placement are exported
    for key in REQUIRED_FM:
        _need(fm, key, rel)
    domain, slug = path.parent.parent.name, path.parent.name
    if fm["domain"] != domain:
        raise SystemExit(f"{rel}: domain {fm['domain']} does not match its folder {domain}")
    if domain not in DOMAIN_LABELS:
        raise SystemExit(f"{rel}: domain {domain} has no explorer label")
    if fm["autonomy_ceiling"] not in STAGE_IDS:
        raise SystemExit(f"{rel}: autonomy_ceiling {fm['autonomy_ceiling']} has no stage label")
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
        setup["id"]: {batch: _state(fm["id"], placement, setup, batch, data) for batch in BATCH_VALUES}
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
        "card": fm["card"],
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
    return {
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
    use_cases = []
    for path in sorted((repo_root / "catalog").glob("*/*/README.md")):
        if path.parent.parent.name in SKIPPED_DOMAINS:
            continue
        uc = _use_case(path, repo_root, data)
        if uc is not None:
            use_cases.append(uc)
    domain_rank = list(DOMAIN_LABELS)
    use_cases.sort(key=lambda u: (domain_rank.index(u["domain"]), u["slug"]))
    for key in ("id", "slug"):
        values = [u[key] for u in use_cases]
        if len(set(values)) != len(values):
            raise SystemExit(f"catalog: use-case {key} values must be unique")
    domains = {u["domain"] for u in use_cases}
    stages = {u["stage"]["id"] for u in use_cases}
    tiers = {c["tier"] for u in use_cases for s in u["states"].values() for c in s["yes"]["tiers"] if c["used"]}
    return {
        "setups": [
            {
                "id": s["id"],
                "label": s["label"],
                "tier": s["tier"],
                "ampere_note": s["ampere_note"],
                "gpu_count": s["accelerators"]["count_per_node"],
                "memory_per_gpu_gb": s["accelerators"]["memory_per_gpu_gb"],
                "vendor": s["accelerators"]["vendor"],
            }
            for s in data["setups"]
        ],
        "default": data["setups_doc"]["default"],
        "fit_bands": data["bands"],
        "filters": {
            "domains": [{"id": d, "label": DOMAIN_LABELS[d]} for d in DOMAIN_LABELS if d in domains],
            "stages": [{"id": s, "label": STAGE_LABELS[s]} for s in STAGE_LABELS if s in stages],
            "tiers": [t for t in TIERS if t in tiers],
        },
        "use_cases": use_cases,
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
