"""YAML loading without date coercion, and front-matter splitting.

PyYAML's SafeLoader turns unquoted `2026-11-06` into a `datetime.date`, which
fails `"type": "string"` in the schemas (RESEARCH.md Pitfall 1). NoDatesLoader
is SafeLoader minus the timestamp implicit resolver. Never call `yaml.load`
with any other loader.

NoDatesLoader also rejects duplicate mapping keys. PyYAML keeps the
last value silently, so a reviewer could read `evidence_level: "E0"` while the
linter uses a later `evidence_level: "E1"`. A duplicate raises ConstructorError
(a yaml.YAMLError) at the second key, which split_front_matter reports as
FM001 and the CLI reports as a config error. Keys pulled in by a YAML merge key
(`<<`) may be overridden explicitly; only repeated explicit keys are rejected.
"""

from __future__ import annotations

from pathlib import Path

import yaml

_MERGE_TAG = "tag:yaml.org,2002:merge"


class NoDatesLoader(yaml.SafeLoader):
    """SafeLoader that keeps ISO dates as strings and rejects duplicate keys."""

    def construct_mapping(self, node, deep=False):
        if isinstance(node, yaml.MappingNode):
            seen = set()
            for key_node, _ in node.value:
                if key_node.tag == _MERGE_TAG:
                    continue
                key = self.construct_object(key_node, deep=deep)
                try:
                    hash(key)
                except TypeError:
                    continue  # SafeConstructor reports unhashable keys itself
                if key in seen:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        f"duplicate key '{key}'",
                        key_node.start_mark,
                    )
                seen.add(key)
        return super().construct_mapping(node, deep=deep)


NoDatesLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, NoDatesLoader.construct_yaml_map
)

NoDatesLoader.yaml_implicit_resolvers = {
    ch: [(tag, rx) for tag, rx in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for ch, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


class FrontMatterError(Exception):
    """Front matter YAML failed to parse. `line` is the 1-based file line."""

    def __init__(self, line: int, message: str):
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


def load_yaml_text(text: str):
    return yaml.load(text, Loader=NoDatesLoader)


def load_yaml(path) -> object:
    """Load a YAML file with NoDatesLoader."""
    return load_yaml_text(Path(path).read_text(encoding="utf-8"))


def split_front_matter(text: str):
    """Return (front_matter | None, body, body_line_offset).

    - No leading `---` line: (None, text, 0).
    - Unterminated block: (None, text, 0); callers report FM001.
    - YAML error: raises FrontMatterError with the file line of the problem.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text, 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            block = "".join(lines[1:i])
            try:
                fm = load_yaml_text(block)
            except yaml.YAMLError as exc:
                mark = getattr(exc, "problem_mark", None) or getattr(exc, "context_mark", None)
                line = (mark.line + 2) if mark is not None else 1
                raise FrontMatterError(line, str(exc).replace("\n", " ")) from exc
            if fm is None:
                fm = {}
            return fm, "".join(lines[i + 1 :]), i + 1
    return None, text, 0
