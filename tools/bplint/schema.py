"""JSON Schema validators with cross-file $ref through a local Registry."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMA_FILES = {
    "platform": "platform.schema.json",
    "use-case": "use-case.schema.json",
    "reference": "reference.schema.json",
}


def _registry(schema_dir: Path) -> Registry:
    reg = Registry()
    for p in sorted(schema_dir.glob("*.schema.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        reg = reg.with_resource(s["$id"], Resource.from_contents(s))
    return reg


def load_validators(schema_dir) -> dict[str, Draft202012Validator]:
    schema_dir = Path(schema_dir)
    reg = _registry(schema_dir)
    out = {}
    for key, name in SCHEMA_FILES.items():
        schema = json.loads((schema_dir / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        out[key] = Draft202012Validator(
            schema, registry=reg, format_checker=Draft202012Validator.FORMAT_CHECKER
        )
    return out


def load_enums(schema_dir) -> dict[str, list]:
    """Enum lists from common.schema.json $defs, in schema order."""
    common = json.loads((Path(schema_dir) / "common.schema.json").read_text(encoding="utf-8"))
    return {
        name: list(d["enum"]) for name, d in common.get("$defs", {}).items() if "enum" in d
    }
