"""Each glob group binds the front matter `type` values its pages may declare.

The page's own `type` picks its schema, budgets, and validation-table rule.
Without a binding, a blueprint could declare `type: reference` and skip the
validation table and readiness facets. These tests pin the binding for
discovery runs and for explicit paths inside a glob group.
"""

from __future__ import annotations

import argparse

import pytest
import yaml

from tools.bplint.cli import ConfigError, build_context, discover_groups
from tools.bplint.loader import load_yaml
from tools.tests.conftest import FIXTURES, REPO_ROOT, run_bplint

MISPLACED = FIXTURES / "misplaced-type/catalog/demo/widget/README.md"
VALID_REFERENCE = FIXTURES / "valid/reference/README.md"
VALID_PLATFORM = FIXTURES / "valid/platform/README.md"

GROUP_TYPES = {
    "blueprint_globs": ["platform", "use-case"],
    "reference_globs": ["reference"],
    "doc_globs": [],
}


def _rel(p):
    return p.relative_to(REPO_ROOT).as_posix()


def _config(tmp_path, **groups):
    cfg = {
        "schemas_dir": "schemas",
        "budgets": "tools/bplint/budgets.yaml",
        "validation_table": "schemas/validation-table.yaml",
        "blueprint_globs": [],
        "reference_globs": [],
        "doc_globs": [],
        "exclude_globs": [],
        "group_types": GROUP_TYPES,
        "facet_fields": ["model_readiness", "evidence_level", "autonomy_ceiling", "placement_tier"],
    }
    cfg.update(groups)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    return path


def _fm002(findings):
    return [f["message"] for f in findings if f["code"] == "FM002"]


def test_repo_config_binds_types_to_groups():
    config = load_yaml(REPO_ROOT / "tools/bplint/config.yaml")
    assert config["group_types"] == GROUP_TYPES


def test_blueprint_folder_page_cannot_declare_reference(tmp_path):
    cfg = _config(tmp_path, blueprint_globs=["tools/tests/fixtures/misplaced-type/catalog/*/*/README.md"])
    rc, findings = run_bplint(MISPLACED, config=cfg)
    msgs = _fm002(findings)
    assert rc == 1
    assert msgs and "'reference' is not allowed here" in msgs[0], findings
    assert "'platform', 'use-case'" in msgs[0]


def test_blueprint_folder_binding_holds_in_discovery(tmp_path):
    cfg = _config(tmp_path, blueprint_globs=["tools/tests/fixtures/misplaced-type/catalog/*/*/README.md"])
    rc, findings = run_bplint(config=cfg)
    assert rc == 1
    assert any("'reference' is not allowed here" in m for m in _fm002(findings)), findings


def test_reference_glob_page_cannot_declare_platform(tmp_path):
    cfg = _config(tmp_path, reference_globs=[_rel(VALID_PLATFORM)])
    rc, findings = run_bplint(VALID_PLATFORM, config=cfg)
    msgs = _fm002(findings)
    assert rc == 1
    assert msgs and "'platform' is not allowed here" in msgs[0], findings


def test_doc_glob_page_cannot_declare_a_type(tmp_path):
    cfg = _config(tmp_path, doc_globs=[_rel(VALID_REFERENCE)])
    rc, findings = run_bplint(config=cfg)
    msgs = _fm002(findings)
    assert rc == 1
    assert msgs and "must not declare a type" in msgs[0], findings


def test_reference_glob_page_with_reference_type_is_clean(tmp_path):
    cfg = _config(tmp_path, reference_globs=[_rel(VALID_REFERENCE)])
    rc, findings = run_bplint(VALID_REFERENCE, config=cfg)
    assert (rc, findings) == (0, [])


def test_discover_groups_names_the_group(tmp_path):
    config = {
        "blueprint_globs": ["tools/tests/fixtures/misplaced-type/catalog/*/*/README.md"],
        "reference_globs": [_rel(VALID_REFERENCE)],
        "doc_globs": [_rel(VALID_REFERENCE)],
    }
    found = dict(discover_groups(config))
    assert found == {MISPLACED: "blueprint_globs", VALID_REFERENCE: "reference_globs"}


def _ns(cfg):
    return argparse.Namespace(config=str(cfg), today=None)


def test_config_without_binding_for_a_used_group_is_rejected(tmp_path):
    cfg = _config(
        tmp_path,
        reference_globs=["framework/index.md"],
        group_types={"blueprint_globs": ["platform", "use-case"], "doc_globs": []},
    )
    with pytest.raises(ConfigError, match="reference_globs"):
        build_context(_ns(cfg))


def test_config_binding_unknown_type_is_rejected(tmp_path):
    cfg = _config(tmp_path, group_types=dict(GROUP_TYPES, reference_globs=["essay"]))
    with pytest.raises(ConfigError, match="essay"):
        build_context(_ns(cfg))
