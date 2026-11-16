"""Proposal PDF (tools/site/build_pdf.py).

Tests marked pdf build the PDF with WeasyPrint. They run only when REQUIRE_PDF=1
(set in the Pages workflow and by make test-pdf) and then fail if Pango is missing;
otherwise they skip, so lint never builds the PDF.
"""

from __future__ import annotations

import hashlib
import os
import re
import socket
import subprocess
import sys

import pytest

from tools.site import build_pdf
from tools.tests.conftest import REPO_ROOT, pdf_or_skip

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
    # Module-scoped fixtures run before the autouse gate, so gate here too.
    pdf_or_skip()
    out = tmp_path_factory.mktemp("pdf") / "proposal.pdf"
    build_pdf.build(PROPOSAL, out)
    return out


def _reader(path):
    from pypdf import PdfReader

    return PdfReader(str(path))


def _text(path) -> str:
    return "\n".join(page.extract_text() or "" for page in _reader(path).pages)


def _font_names(path) -> set[str]:
    names = set()
    for page in _reader(path).pages:
        fonts = page.get("/Resources", {}).get("/Font", {})
        for ref in fonts.values():
            names.add(str(ref.get_object()["/BaseFont"]))
    return names


def _assert_red_hat_only(names: set[str]) -> None:
    assert names, "no fonts found"
    # Subset prefix plus the family, for example /ABCDEF+Red-Hat-Text-Bold.
    assert all(re.fullmatch(r"/[A-Z]{6}\+Red-Hat-[A-Za-z-]+", n) for n in names), names
    families = {n.split("+", 1)[1] for n in names}
    assert {"Red-Hat-Text", "Red-Hat-Display-Bold"} <= families, families


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
    # Python 3.12's urljoin turns the third case into file:etc/hosts; 3.14 gives
    # file:///etc/hosts. Both must stop the build.
    from weasyprint.urls import FatalURLFetchingError

    page = tmp_path / "page.md"
    page.write_text(f"# Test page\n\n![remote]({src})\n", encoding="utf-8")
    with pytest.raises(FatalURLFetchingError):
        build_pdf.build(page, tmp_path / "out.pdf")
    assert not (tmp_path / "out.pdf").exists()


@pytest.mark.pdf
@pytest.mark.parametrize(
    "url",
    [
        "file:etc/hosts",
        "file:///etc/hosts",
        "file://localhost/etc/hosts",
        "file://example.com" + str(REPO_ROOT / "README.md"),
        "file:README.md",
        (REPO_ROOT / "README.md").as_uri() + "/../../../../../../../../etc/hosts",
        "https://example.com/font.woff2",
        "ftp://example.com/x",
    ],
)
def test_fetcher_rejects_outside_repo(url):
    from weasyprint.urls import FatalURLFetchingError

    fetcher = build_pdf._fetcher_class()(REPO_ROOT)
    with pytest.raises(FatalURLFetchingError):
        fetcher.fetch(url)


@pytest.mark.pdf
def test_fetcher_allows_vendored_fonts():
    fetcher = build_pdf._fetcher_class()(REPO_ROOT)
    css = PRINT_CSS.read_text(encoding="utf-8")
    refs = re.findall(r'url\("([^"]+\.woff2)"\)', css)
    assert len(refs) == 3, refs
    for ref in refs:
        path = (PRINT_CSS.parent / ref).resolve()
        assert path.is_file(), ref
        assert path.parent == REPO_ROOT / "site-src/brand/fonts", ref
        response = fetcher.fetch(path.as_uri())
        try:
            assert response.read(4) == b"wOF2", ref
        finally:
            response.close()


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
    _assert_red_hat_only(_font_names(built_pdf))


@pytest.mark.pdf
def test_pdf_fonts_without_system_fonts(tmp_path):
    """Build with a fontconfig that knows no font directories at all.

    The only fonts left are the vendored ones loaded by @font-face, so a machine
    with Red Hat fonts installed system-wide cannot hide a broken @font-face.
    """
    cache = tmp_path / "fc-cache"
    cache.mkdir()
    conf = tmp_path / "fonts.conf"
    conf.write_text(
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
        f"<fontconfig><cachedir>{cache}</cachedir></fontconfig>\n",
        encoding="utf-8",
    )
    out = tmp_path / "isolated.pdf"
    env = {
        **os.environ,
        "FONTCONFIG_FILE": str(conf),
        "FONTCONFIG_PATH": str(tmp_path),
        "REQUIRE_PDF": "1",
    }
    proc = subprocess.run(
        [sys.executable, "-m", "tools.site.build_pdf", "--out", str(out)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    _assert_red_hat_only(_font_names(out))
    assert _squash(f"Facts checked as of {_checked()}") in _squash(_text(out))


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
def test_pdf_font_dates_pinned(built_pdf):
    """Embedded font instances carry the facts date, not the build time.

    WeasyPrint saves each variable font instance with fontTools, which writes the
    current time into head.modified unless SOURCE_DATE_EPOCH is set; two builds a
    second apart would then differ.
    """
    from datetime import datetime, timezone
    from io import BytesIO

    from fontTools.ttLib import TTFont

    # fontTools head dates count seconds from 1904-01-01.
    epoch_1904 = datetime(1904, 1, 1, tzinfo=timezone.utc)
    day = datetime.strptime(_checked(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    expected = int((day - epoch_1904).total_seconds())
    seen = 0
    reader = _reader(built_pdf)
    for page in reader.pages:
        for ref in page.get("/Resources", {}).get("/Font", {}).values():
            font = ref.get_object()
            for desc_font in font.get("/DescendantFonts", []):
                descriptor = desc_font.get_object()["/FontDescriptor"].get_object()
                stream = descriptor.get("/FontFile2")
                if stream is None:
                    continue
                head = TTFont(BytesIO(stream.get_object().get_data()))["head"]
                assert head.modified == expected, font["/BaseFont"]
                seen += 1
    assert seen, "no embedded TrueType fonts found"


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


def test_cli_skips_without_require_pdf(monkeypatch, tmp_path, capsys):
    # Skips even when WeasyPrint loads: only REQUIRE_PDF=1 builds the PDF.
    monkeypatch.setattr(build_pdf, "weasyprint_available", lambda: (True, ""))
    monkeypatch.setattr(build_pdf, "build", lambda *a: pytest.fail("built without REQUIRE_PDF"))
    monkeypatch.delenv("REQUIRE_PDF", raising=False)
    out = tmp_path / "p.pdf"
    assert build_pdf.main(["--out", str(out)]) == 0
    assert "skipped" in capsys.readouterr().out
    assert not out.exists()


def test_cli_fails_without_weasyprint_when_required(monkeypatch, tmp_path):
    monkeypatch.setattr(build_pdf, "weasyprint_available", lambda: (False, "no pango"))
    monkeypatch.setenv("REQUIRE_PDF", "1")
    out = tmp_path / "p.pdf"
    assert build_pdf.main(["--out", str(out)]) == 1
    assert not out.exists()


def test_pdf_tests_gated_on_require_pdf(monkeypatch):
    monkeypatch.delenv("REQUIRE_PDF", raising=False)
    with pytest.raises(pytest.skip.Exception):
        pdf_or_skip()


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
