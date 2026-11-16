"""Build the proposal PDF offline from proposal/index.md.

The PDF and the site section come from the same markdown, so they cannot drift.
Steps: strip the front matter, HTML comments, and the PDF download line; render
the markdown with markdown-it-py; rewrite relative .md links to absolute URLs on
the live site (recipes/ for catalog pages, as tools/site/hooks.py publishes them);
apply tools/site/proposal-print.css with the vendored Red Hat fonts; write the PDF
with WeasyPrint.

Offline: RepoOnlyFetcher allows data: URLs and file: URLs inside the repository,
and raises FatalURLFetchingError for anything else, so a remote image or stylesheet
stops the build instead of being fetched.

Reproducible: the creation and modification dates come from data/facts-check.yaml
(dcterms.created and dcterms.modified meta, read by WeasyPrint), so two builds of
the same source give the same bytes.

WeasyPrint needs Pango (brew install pango; pinned apt packages in pages.yml). When
it cannot load, the build prints a skip notice and exits 0, unless REQUIRE_PDF=1.

Usage:
    python -m tools.site.build_pdf [--out PATH] [--source PATH]
"""

from __future__ import annotations

import argparse
import html
import math
import os
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "proposal/index.md"
PRINT_CSS = ROOT / "tools/site/proposal-print.css"
FACTS_FILE = ROOT / "data/facts-check.yaml"
PDF_NAME = "otel-telco-blueprints-proposal.pdf"
DEFAULT_OUT = ROOT / "site/proposal" / PDF_NAME
SITE_URL = "https://ravisharma5.github.io/otel-telco-blueprints/"
DOC_TITLE = "OTel Telco Production Blueprints"
# A URL with a scheme (https:, mailto:, data:, ...).
SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
COMMENT = re.compile(r"<!--.*?-->", re.S)
# Header text that marks the Sources and evidence summary table.
EVIDENCE_HEADER = "Model card"


# ---------- markdown to HTML ----------


def _dest_for(rel: str) -> str | None:
    # Same mapping as the MkDocs hook; imported lazily so the CLI needs no MkDocs
    # import at module load (tests import this module without the site extra).
    from tools.site.hooks import _dest_for as dest

    return dest(rel)


def live_url(href: str, page_dir: str = "proposal") -> str:
    """Absolute live-site URL for a relative link; other links are returned unchanged."""
    if not href or href.startswith("#") or SCHEME.match(href) or href.startswith("//"):
        return href
    parts = urlsplit(href)
    rel = posixpath.normpath(posixpath.join(page_dir, unquote(parts.path)))
    if rel == ".." or rel.startswith("../"):
        raise SystemExit(f"pdf: link {href!r} points outside the repository")
    dest = _dest_for(rel)
    if dest is None:
        stem, ext = posixpath.splitext(rel)
        if ext.lower() == ".md":
            head, name = posixpath.split(stem)
            dest = posixpath.join(head, "" if name in ("README", "index") else name, "index.html")
        else:
            dest = rel
    if dest.endswith("index.html"):
        dest = dest[: -len("index.html")]
    fragment = f"#{parts.fragment}" if parts.fragment else ""
    return SITE_URL + dest + fragment


def _strip_source(text: str) -> str:
    """Drop the front matter, HTML comments, and the PDF download line."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        end = next((i for i, ln in enumerate(lines[1:], 1) if ln.strip() == "---"), None)
        if end is None:
            raise SystemExit("pdf: front matter is not closed")
        lines = lines[end + 1 :]
    lines = [ln for ln in lines if PDF_NAME not in ln]
    return COMMENT.sub("", "\n".join(lines) + "\n")


def _mark_evidence_table(tokens) -> None:
    """Add class="evidence" to the table whose header has the Model card column."""
    for i, tok in enumerate(tokens):
        if tok.type != "table_open":
            continue
        for nxt in tokens[i + 1 :]:
            if nxt.type == "thead_close":
                break
            if nxt.type == "inline" and nxt.content.strip() == EVIDENCE_HEADER:
                tok.attrSet("class", "evidence")
                break


def _cell_text(inline) -> str:
    return "".join(
        c.content for c in inline.children or [] if c.type in ("text", "code_inline")
    )


def _column_widths(tokens) -> None:
    """Give each header cell a width share from its column's text length.

    With table-layout: fixed and no widths every column gets an equal share, so a
    short "#" column takes as much room as a long description. The evidence table
    keeps the widths set in proposal-print.css.
    """
    i = 0
    while i < len(tokens):
        if tokens[i].type != "table_open" or tokens[i].attrGet("class") == "evidence":
            i += 1
            continue
        heads, lengths, col = [], {}, 0
        j = i + 1
        while tokens[j].type != "table_close":
            tok = tokens[j]
            if tok.type == "tr_open":
                col = 0
            elif tok.type in ("th_open", "td_open"):
                if tok.type == "th_open":
                    heads.append(tok)
                text = _cell_text(tokens[j + 1])
                longest = max((len(w) for w in text.split()), default=1)
                # Long text wraps, so it counts less than linearly; the longest word
                # sets a floor so a header never breaks mid-word.
                lengths.setdefault(col, []).append(max(longest, min(len(text), 60) ** 0.8))
                col += 1
            j += 1
        weights = [max(3.0, sum(v) / len(v)) for _, v in sorted(lengths.items())]
        total = sum(weights)
        for head, weight in zip(heads, weights):
            # Keep any alignment style markdown-it set for the column.
            align = head.attrGet("style")
            # Rounded down, so the shares never add up to more than 100%.
            width = f"width: {math.floor(1000 * weight / total) / 10}%"
            head.attrSet("style", f"{align}; {width}" if align else width)
        i = j + 1


def _sections(body: str) -> str:
    """Wrap the opening and each h2 section in <section>; the evidence one gets class="wide".

    Every section gets a page name in the print CSS, because WeasyPrint does not
    switch back from a named page to an unnamed one.
    """
    parts = re.split(r"(?=<h2[ >])", body)
    out = [f"<section>\n{parts[0]}</section>\n"]
    for part in parts[1:]:
        cls = ' class="wide"' if 'class="evidence"' in part else ""
        out.append(f"<section{cls}>\n{part}</section>\n")
    return "".join(out)


def _checked(facts_file: Path = FACTS_FILE) -> str:
    m = re.search(
        r'(?m)^checked:\s*"(\d{4}-\d{2}-\d{2})"', facts_file.read_text(encoding="utf-8")
    )
    if not m:
        raise SystemExit(f"pdf: no checked date in {facts_file.relative_to(ROOT)}")
    return m.group(1)


def render_html(source: Path = SOURCE) -> str:
    """The proposal as one HTML document, ready for WeasyPrint."""
    md = MarkdownIt("commonmark", {"html": False}).enable("table")
    tokens = md.parse(_strip_source(source.read_text(encoding="utf-8")))
    page_dir = "proposal"
    try:
        page_dir = posixpath.dirname(source.resolve().relative_to(ROOT).as_posix())
    except ValueError:
        pass  # a page outside the repo (tests): links resolve as if under proposal/
    title = DOC_TITLE
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open" and tok.tag == "h1" and title == DOC_TITLE:
            title = tokens[i + 1].content
        for child in tok.children or []:
            if child.type == "link_open":
                child.attrSet("href", live_url(child.attrGet("href") or "", page_dir))
    _mark_evidence_table(tokens)
    _column_widths(tokens)
    online = (
        f'<p class="online">Online version: <a href="{SITE_URL}proposal/">'
        f"{SITE_URL}proposal/</a></p>\n"
    )
    body = _sections(md.renderer.render(tokens, md.options, {}) + online)
    checked = _checked()
    esc = html.escape
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{esc(title)}</title>\n"
        f'<meta name="author" content="{esc(DOC_TITLE)}">\n'
        f'<meta name="dcterms.created" content="{checked}">\n'
        f'<meta name="dcterms.modified" content="{checked}">\n'
        "</head>\n<body>\n"
        f"{body}"
        "</body>\n</html>\n"
    )


# ---------- offline rendering ----------


def _fetcher_class():
    from weasyprint.urls import FatalURLFetchingError, URLFetcher

    class RepoOnlyFetcher(URLFetcher):
        """Allows data: URLs and file: URLs inside the repository; nothing else."""

        def __init__(self, root: Path, **kwargs):
            super().__init__(allowed_protocols=("file", "data"), **kwargs)
            self.root = root.resolve()

        def fetch(self, url, headers=None):
            scheme = url.split(":", 1)[0].lower()
            if scheme == "data":
                return super().fetch(url, headers)
            if scheme == "file":
                path = Path(unquote(urlsplit(url).path)).resolve()
                if path.is_relative_to(self.root):
                    return super().fetch(url, headers)
            raise FatalURLFetchingError(f"pdf: refusing to fetch {url}")

    return RepoOnlyFetcher


def document(source: Path = SOURCE, root: Path = ROOT):
    """A WeasyPrint HTML object for the page, with the offline fetcher and print CSS."""
    from weasyprint import CSS, HTML

    fetcher = _fetcher_class()(root)
    return _Doc(
        HTML(
            string=render_html(source),
            base_url=source.resolve().as_uri(),
            url_fetcher=fetcher,
        ),
        CSS(filename=str(PRINT_CSS), url_fetcher=fetcher),
    )


class _Doc:
    """HTML plus its stylesheet, so render() and write_pdf() always use both."""

    def __init__(self, html_doc, css):
        self.html = html_doc
        self.css = css

    def render(self):
        return self.html.render(stylesheets=[self.css], pdf_variant="pdf/ua-1")

    def write_pdf(self, target):
        return self.html.write_pdf(target, stylesheets=[self.css], pdf_variant="pdf/ua-1")


def build(source: Path = SOURCE, out: Path = DEFAULT_OUT) -> Path:
    """Write the PDF to out (atomically: a failed build leaves no file)."""
    doc = document(source)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    try:
        doc.write_pdf(str(tmp))
        os.replace(tmp, out)
    finally:
        if tmp.exists():
            tmp.unlink()
    return out


def weasyprint_available() -> tuple[bool, str]:
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError) as exc:
        return False, str(exc).splitlines()[0] if str(exc) else type(exc).__name__
    return True, ""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    ok, why = weasyprint_available()
    if not ok:
        if os.environ.get("REQUIRE_PDF") == "1":
            print(f"pdf: WeasyPrint cannot load ({why}) and REQUIRE_PDF=1", file=sys.stderr)
            return 1
        print(f"pdf: skipped, WeasyPrint or Pango not installed ({why})")
        return 0
    out = build(args.source, args.out)
    try:
        shown = out.resolve().relative_to(ROOT)
    except ValueError:
        shown = out
    print(f"pdf: wrote {shown} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
