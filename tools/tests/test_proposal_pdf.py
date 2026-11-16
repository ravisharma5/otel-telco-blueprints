"""Proposal PDF (tools/site/build_pdf.py).

Tests marked pdf build the PDF with WeasyPrint. They skip when Pango is missing,
and fail instead when REQUIRE_PDF=1 (set in the Pages workflow and by make test-pdf).
"""

from __future__ import annotations

import hashlib
import re
import socket

import pytest

from tools.site import build_pdf
from tools.tests.conftest import REPO_ROOT

PROPOSAL = REPO_ROOT / "proposal/index.md"
FACTS = REPO_ROOT / "data/facts-check.yaml"
PRINT_CSS = REPO_ROOT / "tools/site/proposal-print.css"


def _checked() -> str:
    m = re.search(r'(?m)^checked:\s*"(\d{4}-\d{2}-\d{2})"', FACTS.read_text(encoding="utf-8"))
    assert m, "data/facts-check.yaml has no checked date"
    return m.group(1)


def _flagship_titles() -> list[str]:
    text = PROPOSAL.read_text(encoding="utf-8")
    block = text.split("<!-- generated:flagships start -->", 1)[1].split(
        "<!-- generated:flagships end -->", 1
    )[0]
    return re.findall(r"(?m)^\| \[([^\]]+)\]\(", block)


def _squash(text: str) -> str:
    """Drop whitespace and hyphens, so line breaks and hyphenation in cells don't matter."""
    return re.sub(r"[\s\-­‐]+", "", text)


@pytest.fixture(scope="module")
def built_pdf(tmp_path_factory):
    out = tmp_path_factory.mktemp("pdf") / "proposal.pdf"
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):
        return None  # the autouse pdf gate skips or fails each test
    build_pdf.build(PROPOSAL, out)
    return out


def _reader(path):
    from pypdf import PdfReader

    return PdfReader(str(path))


def _text(path) -> str:
    return "\n".join(page.extract_text() or "" for page in _reader(path).pages)


# ---------- runs without Pango ----------


def test_print_css_table_rules():
    css = PRINT_CSS.read_text(encoding="utf-8")
    assert "table-layout: fixed" in css
    assert re.search(r"table\s*\{[^}]*width:\s*100%", css)
    assert re.search(r"(?s)th,\s*td\s*\{[^}]*(overflow-wrap:\s*anywhere|word-break:\s*break-word)", css)
    assert "display: table-header-group" in css


def test_live_url_mapping():
    site = build_pdf.SITE_URL
    assert build_pdf.live_url("../platform/adaptation/README.md") == site + "platform/adaptation/"
    assert build_pdf.live_url("../architecture/placement.md") == site + "architecture/placement/"
    assert (
        build_pdf.live_url("../catalog/security/security-triage/README.md#sources")
        == site + "recipes/security/security-triage/#sources"
    )
    assert build_pdf.live_url("https://example.org/x") == "https://example.org/x"
    assert build_pdf.live_url("#top") == "#top"


def test_markdown_drops_download_line_and_comments():
    html = build_pdf.render_html(PROPOSAL)
    assert build_pdf.PDF_NAME not in html
    assert "<!--" not in html
    assert '<html lang="en">' in html
    assert "<title>" in html
    assert f'name="dcterms.created" content="{_checked()}"' in html


# ---------- builds the PDF ----------


@pytest.mark.pdf
def test_pdf_builds_offline(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("network access during the PDF build")

    monkeypatch.setattr(socket, "socket", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket, "getaddrinfo", no_network)
    out = tmp_path / "p.pdf"
    build_pdf.build(PROPOSAL, out)
    assert out.read_bytes()[:4] == b"%PDF"


@pytest.mark.pdf
@pytest.mark.parametrize(
    "src",
    [
        "https://example.com/x.png",
        "http://example.com/x.png",
        # A relative path that leaves the repository (markdown-it drops file: links).
        "../" * 40 + "etc/hosts",
    ],
)
def test_pdf_blocks_remote_resources(tmp_path, src):
    from weasyprint.urls import FatalURLFetchingError

    page = tmp_path / "page.md"
    page.write_text(f"# Test page\n\n![remote]({src})\n", encoding="utf-8")
    with pytest.raises(FatalURLFetchingError):
        build_pdf.build(page, tmp_path / "out.pdf")
    assert not (tmp_path / "out.pdf").exists()


@pytest.mark.pdf
def test_pdf_contains_stamp_and_summary(built_pdf):
    text = _squash(_text(built_pdf))
    assert _squash(f"Facts checked as of {_checked()}") in text
    assert _squash("Sources and evidence summary") in text
    assert _squash("Model card") in text
    titles = _flagship_titles()
    assert len(titles) == 4
    for title in titles:
        assert _squash(title) in text, title


@pytest.mark.pdf
def test_pdf_fonts_vendored(built_pdf):
    names = set()
    for page in _reader(built_pdf).pages:
        fonts = page.get("/Resources", {}).get("/Font", {})
        for ref in fonts.values():
            names.add(str(ref.get_object()["/BaseFont"]))
    assert names, "no fonts found"
    # Subset prefix plus the family, for example /ABCDEF+Red-Hat-Text-Bold.
    assert all("RedHat" in n.replace("-", "") for n in names), names


@pytest.mark.pdf
def test_pdf_reproducible(built_pdf, tmp_path):
    second = tmp_path / "again.pdf"
    build_pdf.build(PROPOSAL, second)
    a = hashlib.sha256(built_pdf.read_bytes()).hexdigest()
    b = hashlib.sha256(second.read_bytes()).hexdigest()
    assert a == b
    meta = _reader(second).metadata
    stamp = "D:" + _checked().replace("-", "")
    assert str(meta["/CreationDate"]).startswith(stamp)
    assert str(meta["/ModDate"]).startswith(stamp)


@pytest.mark.pdf
def test_pdf_links_absolute(built_pdf):
    uris = []
    for page in _reader(built_pdf).pages:
        for annot in page.get("/Annots") or []:
            action = annot.get_object().get("/A")
            if action and "/URI" in action:
                uris.append(str(action["/URI"]))
    assert uris, "no link annotations found"
    for uri in uris:
        assert re.match(r"^(https?|mailto):", uri), uri
        assert not re.search(r"\.md(#|$)", uri), uri
    assert any(u.startswith(build_pdf.SITE_URL + "recipes/") for u in uris)


@pytest.mark.pdf
def test_pdf_tables_fit_page():
    from weasyprint.formatting_structure.boxes import TableBox

    document = build_pdf.document(PROPOSAL).render()
    tables = 0
    evidence = 0
    for page in document.pages:
        box = page._page_box
        right = box.content_box_x() + box.width
        for desc in box.descendants():
            if not isinstance(desc, TableBox):
                continue
            tables += 1
            edge = desc.border_box_x() + desc.border_width()
            assert edge <= right + 0.5, f"table overflows the page by {edge - right:.1f}px"
            if "evidence" in (desc.element.get("class") or ""):
                evidence += 1
            for inner in desc.descendants():
                if getattr(inner, "width", None) is None or not hasattr(inner, "position_x"):
                    continue
                inner_edge = inner.position_x + inner.margin_width()
                assert inner_edge <= edge + 0.5, (
                    f"content overflows a table cell by {inner_edge - edge:.1f}px"
                )
    assert tables >= 5
    assert evidence >= 1, "evidence summary table not found"


def test_cli_skips_without_weasyprint(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(build_pdf, "weasyprint_available", lambda: (False, "no pango"))
    monkeypatch.delenv("REQUIRE_PDF", raising=False)
    out = tmp_path / "p.pdf"
    assert build_pdf.main(["--out", str(out)]) == 0
    assert "skipped" in capsys.readouterr().out
    assert not out.exists()
    monkeypatch.setenv("REQUIRE_PDF", "1")
    assert build_pdf.main(["--out", str(out)]) == 1


@pytest.mark.site_output
@pytest.mark.pdf
def test_proposal_pdf_in_site(site_dir):
    pdf = site_dir / "proposal" / build_pdf.PDF_NAME
    assert pdf.is_file(), "make site did not build the proposal PDF"
    assert pdf.read_bytes()[:4] == b"%PDF"
    page = (site_dir / "proposal/index.html").read_text(encoding="utf-8")
    assert f'href="{build_pdf.PDF_NAME}"' in page


def test_proposal_links_pdf_once():
    lines = PROPOSAL.read_text(encoding="utf-8").splitlines()
    assert sum(build_pdf.PDF_NAME in ln for ln in lines) == 1
