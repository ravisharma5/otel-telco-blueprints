"""Architecture diagrams: safety checks for the overview diagram files.

The overview diagram is authored with archify. Its HTML source and input JSON
are committed next to the page but never published, and the exported SVG is
the only file the site serves.
"""

from __future__ import annotations

import re

import pytest

from tools.site import hooks
from tools.tests.conftest import REPO_ROOT

DIAGRAMS = REPO_ROOT / "architecture/diagrams"
SOURCES = [DIAGRAMS / "overview.html", DIAGRAMS / "candidate.json"]
# Local home folders on macOS and Linux. The character classes keep the
# literal paths out of this file, so it passes the public-tree term checks.
LOCAL_PATH_RE = re.compile(r"/(?:[U]sers|[h]ome)/")


@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_diagram_sources_have_no_local_paths(path):
    text = path.read_text(encoding="utf-8")
    assert not LOCAL_PATH_RE.search(text)


def test_diagram_sources_not_published():
    assert ".html" not in hooks.SUFFIXES
    assert ".json" not in hooks.SUFFIXES
