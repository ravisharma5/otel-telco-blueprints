"""Render the serving page's data-backed blocks from data/serving/*.yaml.

The serving page (platform/serving-routing-placement/README.md) holds generated
blocks between marker lines:

    <!-- generated:NAME start -->
    ...rendered text...
    <!-- generated:NAME end -->

Only the text between a start and an end marker is replaced; everything else on
the page is left alone. A missing or duplicated marker stops the run.

Usage:
    python -m tools.site.render_serving          # rewrite the page
    python -m tools.site.render_serving --check  # exit 1 if the page drifts
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data/serving"
PAGE = ROOT / "platform/serving-routing-placement/README.md"
SIZING_COLUMNS = (
    ("Slot", "slot"),
    ("Precision", "precision"),
    ("Weights", "weights"),
    ("Hardware class", "hardware_class"),
)
SETUP_COLUMNS = ("Setup", "Tier", "GPUs per node", "Memory per GPU", "Notes")
SETUP_FLAG_COLUMNS = ("Setup", "Setting", "Value", "Why")
AMPERE_NOTE = "Ampere cards use W4A16 instead of FP8"
OPTION_COLUMNS = (
    "Option",
    "What it does",
    "What to set",
    "How to check on your traffic",
    "Limits",
    "Source",
)
OPTION_FIT_COLUMNS = ("Option", "Use case", "Where it helps")


def _load(data_dir: Path, name: str):
    return yaml.safe_load((data_dir / name).read_text(encoding="utf-8"))


def _cell(text: str) -> str:
    if "|" in text or "\n" in text:
        raise SystemExit(f"render_serving: table cell cannot hold '|' or a newline: {text!r}")
    return text


def sizing_table(data_dir: Path = DATA_DIR) -> str:
    """The "Sizing by hardware class" table, one line per row."""
    rows = _load(data_dir, "slot-variants.yaml")["sizing_table"]
    lines = [
        "| " + " | ".join(h for h, _ in SIZING_COLUMNS) + " |",
        "|" + "---|" * len(SIZING_COLUMNS),
    ]
    for row in rows:
        lines.append("| " + " | ".join(_cell(row[key]) for _, key in SIZING_COLUMNS) + " |")
    return "\n".join(lines)


def flag_lines(block: dict) -> list[str]:
    """The flag lines of one per-slot block, without its "# " header line."""
    out = []
    for line in block["lines"]:
        text = " ".join(
            a["flag"] if a["value"] is None else f"{a['flag']} {a['value']}" for a in line["args"]
        )
        if line["continue"]:
            text += " \\"
        if line["trailing_comment"] is not None:
            pad = line["pad_to"] or len(text) + 1
            if len(text) >= pad:
                raise SystemExit(f"render_serving: {block['id']}: line is longer than pad_to {pad}")
            text = text.ljust(pad) + "# " + line["trailing_comment"]
        out.append(text)
    return out


def flags_fence(data_dir: Path = DATA_DIR) -> str:
    """The "Key flags per slot" text fence."""
    lines = ["```text"]
    for block in _load(data_dir, "flags.yaml")["per_slot"]:
        lines.append("# " + block["comment"])
        lines.extend(flag_lines(block))
    lines.append("```")
    return "\n".join(lines)


def _table(header: tuple[str, ...], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines.extend("| " + " | ".join(_cell(c) for c in row) + " |" for row in rows)
    return "\n".join(lines)


def _gb(x) -> str:
    return f"{x:g} GB"


def setups_table(data_dir: Path = DATA_DIR) -> str:
    """The "Setup profiles" table, one row per setup in setups.yaml order."""
    rows = []
    for s in _load(data_dir, "setups.yaml")["setups"]:
        acc = s["accelerators"]
        notes = acc["model_class"] + (f"; {AMPERE_NOTE}" if s["ampere_note"] else "")
        rows.append(
            [
                s["label"],
                s["tier"].capitalize(),
                str(acc["count_per_node"]),
                _gb(acc["memory_per_gpu_gb"]),
                notes,
            ]
        )
    return _table(SETUP_COLUMNS, rows)


def _code(text: str) -> str:
    if "`" in text:
        raise SystemExit(f"render_serving: cannot wrap text holding a backtick: {text!r}")
    return f"`{text}`"


def setup_flags_table(data_dir: Path = DATA_DIR) -> str:
    """The "Key settings per setup" table, rows in flags.yaml per_setup order.

    A setting that is a flag, and a value that is a flag value or a placeholder,
    render as code so angle brackets show as text.
    """
    labels = {s["id"]: s["label"] for s in _load(data_dir, "setups.yaml")["setups"]}
    rows = []
    for r in _load(data_dir, "flags.yaml")["per_setup"]:
        if r["setup"] not in labels:
            raise SystemExit(f"render_serving: per_setup row names unknown setup {r['setup']!r}")
        flag = r["setting"].startswith("--")
        setting = _code(r["setting"]) if flag else r["setting"]
        value = _code(r["value"]) if flag or "<" in r["value"] else r["value"]
        rows.append([labels[r["setup"]], setting, value, r["why"]])
    return _table(SETUP_FLAG_COLUMNS, rows)


def _source_labels(page_text: str) -> dict[str, str]:
    """Source URL -> link label, read from the page's Sources table."""
    labels: dict[str, str] = {}
    for line in page_text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].isdigit():
            for label, url in re.findall(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", cells[3]):
                labels.setdefault(url, label)
    return labels


def options_table(page_text: str, data_dir: Path = DATA_DIR) -> str:
    """The "Advanced serving options" table, one row per option in options.yaml order.

    Each source links with the label its row in the page's Sources table uses, so
    every option source must also be in that table.
    """
    labels = _source_labels(page_text)
    rows = []
    for o in _load(data_dir, "options.yaml")["options"]:
        missing = [u for u in o["sources"] if u not in labels]
        if missing:
            raise SystemExit(
                f"render_serving: option {o['id']!r} cites sources missing from the "
                f"Sources table: {', '.join(missing)}"
            )
        rows.append(
            [
                o["name"],
                o["what"],
                "; ".join(o["set"]),
                o["check"],
                " ".join(o["limits"]),
                "; ".join(f"[{labels[u]}]({u})" for u in o["sources"]),
            ]
        )
    return _table(OPTION_COLUMNS, rows)


def _use_cases() -> dict[str, tuple[str, str]]:
    """Use-case id -> (title, path relative to the repository root)."""
    out = {}
    for path in sorted((ROOT / "catalog").glob("*/*/README.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        fm = yaml.safe_load(text.split("---", 2)[1]) or {}
        if fm.get("id"):
            out[fm["id"]] = (fm["title"], path.relative_to(ROOT).as_posix())
    return out


def option_fit_table(data_dir: Path = DATA_DIR) -> str:
    """The "Where each option helps" table, one row per where_it_helps entry.

    Use-case links stay source-relative (../../catalog/...); the site hook remaps them.
    """
    use_cases = _use_cases()
    rows = []
    for o in _load(data_dir, "options.yaml")["options"]:
        for fit in o["where_it_helps"]:
            uc = fit["use_case"]
            if uc not in use_cases:
                raise SystemExit(f"render_serving: option {o['id']!r} names unknown use case {uc!r}")
            title, rel = use_cases[uc]
            rows.append([o["name"], f"[{uc} {title}](../../{rel})", fit["reason"]])
    return _table(OPTION_FIT_COLUMNS, rows)


def blocks(data_dir: Path = DATA_DIR, page_text: str = "") -> dict[str, str]:
    """Marker name -> rendered text. A blank line separates each block from its markers."""
    return {
        "sizing": f"\n{sizing_table(data_dir)}\n\n",
        "flags-per-slot": f"\n{flags_fence(data_dir)}\n\n",
        "setups": f"\n{setups_table(data_dir)}\n\n",
        "setup-flags": f"\n{setup_flags_table(data_dir)}\n\n",
        "advanced-options": f"\n{options_table(page_text, data_dir)}\n\n",
        "option-fit": f"\n{option_fit_table(data_dir)}\n\n",
    }


def _marker(name: str, edge: str) -> re.Pattern[str]:
    return re.compile(rf"^<!-- generated:{re.escape(name)} {edge} -->[ \t]*\n", re.M)


def render(page_text: str, data_dir: Path | None = None) -> str:
    """page_text with every generated block replaced by its render."""
    data_dir = data_dir or DATA_DIR
    out = page_text
    for name, content in blocks(data_dir, page_text).items():
        starts = list(_marker(name, "start").finditer(out))
        ends = list(_marker(name, "end").finditer(out))
        if len(starts) != 1 or len(ends) != 1:
            raise SystemExit(
                f"render_serving: need exactly one start and one end marker for "
                f"'{name}', found {len(starts)} and {len(ends)}"
            )
        start, end = starts[0], ends[0]
        if end.start() < start.end():
            raise SystemExit(f"render_serving: '{name}' end marker comes before its start")
        out = out[: start.end()] + content + out[end.start() :]
    return out


def _drifted(old: str, new: str) -> list[str]:
    names = []
    for name in blocks(page_text=old):
        pat = re.compile(
            rf"<!-- generated:{re.escape(name)} start -->(.*?)<!-- generated:{re.escape(name)} end -->",
            re.S,
        )
        a, b = pat.search(old), pat.search(new)
        if not a or not b or a.group(1) != b.group(1):
            names.append(name)
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the page drifts")
    args = parser.parse_args(argv)
    old = PAGE.read_text(encoding="utf-8")
    new = render(old)
    if args.check:
        if new != old:
            names = ", ".join(_drifted(old, new)) or "unknown block"
            print(
                f"{PAGE.relative_to(ROOT)}: generated block out of date ({names}); run `make render`",
                file=sys.stderr,
            )
            return 1
        return 0
    if new != old:
        PAGE.write_text(new, encoding="utf-8")
        print(f"rewrote {PAGE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
