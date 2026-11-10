"""Tests for the bplint CLI and report formatting."""

import json
import subprocess
import sys

import pytest

from tools.bplint import checks, cli
from tools.bplint.report import Finding, exit_code, format_json, format_text
from tools.tests.conftest import FIXTURES, REPO_ROOT, run_bplint

W = Finding("a.md", 3, 1, "warning", "CR001", "warn")
E = Finding("a.md", 1, 1, "error", "FM001", "err")


def test_format_text():
    assert format_text([E]) == "a.md:1:1: error FM001 err"


def test_format_json_is_list():
    data = json.loads(format_json([E, W]))
    assert isinstance(data, list) and data[0]["code"] == "FM001"


def test_exit_code_rules():
    assert exit_code([]) == 0
    assert exit_code([W]) == 0
    assert exit_code([W, E]) == 1


def test_missing_config_exits_2():
    rc, _ = run_bplint(config="/nonexistent/config.yaml")
    assert rc == 2


def test_missing_explicit_path_exits_2(tmp_path):
    rc, _ = run_bplint(tmp_path / "nope.md")
    assert rc == 2


def test_json_output_on_empty_run():
    rc, findings = run_bplint()
    assert rc == 0
    assert findings == []


def _blueprint(tmp_path):
    p = tmp_path / "bp.md"
    p.write_text("---\ntype: use-case\n---\n## At a glance\n")
    return p


def test_cli_warnings_only_exit_0(tmp_path, monkeypatch, capsys):
    def warn(doc, ctx):
        return [Finding(doc.path, 1, 1, "warning", "CR001", "only a warning")]

    monkeypatch.setattr(checks, "DOC_CHECKS", [warn])
    rc = cli.main(["--config", str(FIXTURES / "config.yaml"), "--format", "json", str(_blueprint(tmp_path))])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out[0]["severity"] == "warning"


def test_cli_any_error_exit_1(tmp_path, monkeypatch, capsys):
    def err(doc, ctx):
        return [Finding(doc.path, 1, 1, "error", "FM001", "boom")]

    monkeypatch.setattr(checks, "DOC_CHECKS", [err])
    rc = cli.main(["--config", str(FIXTURES / "config.yaml"), str(_blueprint(tmp_path))])
    assert rc == 1
    assert "error FM001 boom" in capsys.readouterr().out


def test_repo_root_is_project_root():
    assert (REPO_ROOT / "tools" / "bplint").is_dir()


# Duplicate keys in front matter and config.


def test_duplicate_front_matter_key_is_fm001(tmp_path):
    src = (FIXTURES / "valid/use-case/README.md").read_text()
    dup = src.replace('evidence_level: "E1"\n', 'evidence_level: "E0"\nevidence_level: "E1"\n', 1)
    assert dup != src
    p = tmp_path / "README.md"
    p.write_text(dup)
    rc, findings = run_bplint(p)
    assert rc == 1
    # The copy sits outside the fixture folder, so link/diagram findings also
    # appear; only the front-matter finding matters here.
    fm = [f for f in findings if f["code"] == "FM001"]
    assert len(fm) == 1
    assert "duplicate key 'evidence_level'" in fm[0]["message"]
    assert fm[0]["line"] == 11


def _run_raw(*args):
    return subprocess.run(
        [sys.executable, "-m", "tools.bplint", *map(str, args)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def _write_config(tmp_path, *, budgets=None, vt_spec=None):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        f"schemas_dir: {REPO_ROOT / 'schemas'}\n"
        f"budgets: {budgets or REPO_ROOT / 'tools/bplint/budgets.yaml'}\n"
        f"validation_table: {vt_spec or REPO_ROOT / 'schemas/validation-table.yaml'}\n"
        "blueprint_globs: []\ndoc_globs: []\n"
    )
    return cfg


def test_duplicate_config_key_exits_2(tmp_path):
    cfg = _write_config(tmp_path)
    cfg.write_text(cfg.read_text() + "doc_globs: []\n")
    proc = _run_raw("--config", cfg)
    assert proc.returncode == 2
    assert "bplint:" in proc.stderr and "duplicate key" in proc.stderr


def test_duplicate_budgets_key_exits_2(tmp_path):
    budgets = tmp_path / "budgets.yaml"
    src = (REPO_ROOT / "tools/bplint/budgets.yaml").read_text()
    budgets.write_text(src + "\ntypes: {}\n")
    proc = _run_raw("--config", _write_config(tmp_path, budgets=budgets))
    assert proc.returncode == 2
    assert "bplint:" in proc.stderr and "duplicate key" in proc.stderr


# Undecodable files and incomplete validation-table specs.


def test_io001_non_utf8_file_is_finding_not_traceback(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"---\nid: x\n---\n\xff\xfe broken\n")
    good = FIXTURES / "broken/no-front-matter/README.md"
    rc, findings = run_bplint(bad, good)
    assert rc == 1
    io = [f for f in findings if f["code"] == "IO001"]
    assert len(io) == 1
    assert io[0]["line"] == 1 and io[0]["severity"] == "error"
    assert "cannot read file as UTF-8 text" in io[0]["message"]
    # The other file in the same run is still linted.
    assert any(f["code"] != "IO001" for f in findings)
    proc = _run_raw("--config", FIXTURES / "config.yaml", bad)
    assert proc.returncode == 1
    assert "Traceback" not in proc.stderr


@pytest.mark.parametrize("drop", ["Load-bearing", "E-level", "Evidence", "Release / revision"])
def test_vt_spec_missing_required_column_exits_2(tmp_path, drop):
    src = (REPO_ROOT / "schemas/validation-table.yaml").read_text()
    spec = tmp_path / "vt.yaml"
    spec.write_text(src.replace(f'  - "{drop}"\n', "", 1))
    assert spec.read_text() != src
    proc = _run_raw("--config", _write_config(tmp_path, vt_spec=spec))
    assert proc.returncode == 2
    assert drop in proc.stderr
    assert "Traceback" not in proc.stderr


@pytest.mark.parametrize(
    "old,new,name",
    [
        ('raising_column: "Our operator-task eval"', 'raising_column: "Our eval"', "Our eval"),
        ('  - "GSMA external"\n\n', '  - "GSMA ext"\n\n', "GSMA ext"),
    ],
)
def test_vt_spec_unknown_raising_or_context_column_exits_2(tmp_path, old, new, name):
    src = (REPO_ROOT / "schemas/validation-table.yaml").read_text()
    spec = tmp_path / "vt.yaml"
    spec.write_text(src.replace(old, new, 1))
    assert spec.read_text() != src
    proc = _run_raw("--config", _write_config(tmp_path, vt_spec=spec))
    assert proc.returncode == 2
    assert name in proc.stderr


def test_schema_type_without_budgets_entry_exits_2(tmp_path):
    import yaml

    data = yaml.safe_load((REPO_ROOT / "tools/bplint/budgets.yaml").read_text())
    del data["types"]["reference"]
    budgets = tmp_path / "budgets.yaml"
    budgets.write_text(yaml.safe_dump(data))
    proc = _run_raw("--config", _write_config(tmp_path, budgets=budgets))
    assert proc.returncode == 2
    assert "bplint:" in proc.stderr and "reference" in proc.stderr
