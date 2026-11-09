"""Tests for the YAML loader and front-matter split."""

import pytest

from tools.bplint.loader import FrontMatterError, load_yaml, split_front_matter


def test_split_returns_dict_body_and_offset():
    text = "---\nid: UC-DEMO-01\ntitle: Demo\n---\n# Heading\nBody\n"
    fm, body, offset = split_front_matter(text)
    assert fm == {"id": "UC-DEMO-01", "title": "Demo"}
    assert body == "# Heading\nBody\n"
    assert offset == 4


def test_unquoted_date_stays_string():
    fm, _, _ = split_front_matter("---\nstatus_verified_on: 2026-11-06\n---\n")
    assert fm["status_verified_on"] == "2026-11-06"
    assert isinstance(fm["status_verified_on"], str)


def test_no_front_matter():
    text = "# Just a heading\n"
    assert split_front_matter(text) == (None, text, 0)


def test_unterminated_front_matter_returns_none():
    text = "---\nid: x\n# never closed\n"
    fm, body, offset = split_front_matter(text)
    assert fm is None
    assert body == text
    assert offset == 0


def test_empty_front_matter_is_empty_dict():
    fm, body, offset = split_front_matter("---\n---\nbody\n")
    assert fm == {}
    assert body == "body\n"
    assert offset == 2


def test_yaml_error_raises_front_matter_error_with_file_line():
    text = "---\nid: ok\nbad: [unclosed\nother: 1\n---\n"
    with pytest.raises(FrontMatterError) as exc:
        split_front_matter(text)
    assert exc.value.line >= 3


def test_load_yaml_keeps_dates_as_strings(tmp_path):
    p = tmp_path / "x.yaml"
    p.write_text("date_checked: 2026-01-02\n")
    assert load_yaml(p) == {"date_checked": "2026-01-02"}


# Duplicate keys must not silently keep the last value.


def test_duplicate_key_raises_with_line_of_second_occurrence():
    text = '---\nid: x\nevidence_level: "E0"\nevidence_level: "E1"\n---\n'
    with pytest.raises(FrontMatterError) as exc:
        split_front_matter(text)
    assert "duplicate key 'evidence_level'" in exc.value.message
    assert exc.value.line == 4


def test_nested_duplicate_key_raises():
    text = "---\nouter:\n  a: 1\n  a: 2\n---\n"
    with pytest.raises(FrontMatterError) as exc:
        split_front_matter(text)
    assert "duplicate key 'a'" in exc.value.message
    assert exc.value.line == 4


def test_merge_key_is_not_a_duplicate():
    text = "---\nbase: &b\n  a: 1\nchild:\n  <<: *b\n  c: 2\n---\n"
    fm, _, _ = split_front_matter(text)
    assert fm["child"] == {"a": 1, "c": 2}


def test_load_yaml_duplicate_key_raises(tmp_path):
    import yaml

    p = tmp_path / "x.yaml"
    p.write_text("a: 1\na: 2\n")
    with pytest.raises(yaml.YAMLError):
        load_yaml(p)
