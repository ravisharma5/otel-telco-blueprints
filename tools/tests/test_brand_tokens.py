"""Shared brand tokens: WCAG contrast, complete light and dark schemes, local fonts.

site-src/brand/tokens.css is the one token file for the docs site and the explorer.
These tests parse it and compute WCAG 2.x contrast for every token pair the design
contract names, so a color change that breaks AA fails here. Fonts are vendored with
their licence and a provenance file whose SHA-256 values must match the files.
"""

from __future__ import annotations

import hashlib
import re

import pytest

from tools.tests.conftest import REPO_ROOT

BRAND = REPO_ROOT / "site-src/brand"
TOKENS_PATH = BRAND / "tokens.css"
FONTS = BRAND / "fonts"
FONT_FILES = ("RedHatDisplay-VF.woff2", "RedHatText-VF.woff2", "RedHatMono-VF.woff2")
FONT_COMMIT = "6bb1048a6402b0076ea04f42951ec66263cd1437"
FONT_REPO = "RedHatOfficial/RedHatFont"

TEXT = 4.5
NON_TEXT = 3.0

COLOR_TOKENS = (
    "--color-bg",
    "--color-surface",
    "--color-surface-2",
    "--color-border",
    "--color-border-control",
    "--color-text",
    "--color-text-muted",
    "--color-primary",
    "--color-primary-hover",
    "--color-on-primary",
    "--color-primary-text",
    "--color-primary-soft",
    "--color-selected-border",
    "--color-focus",
    "--stage-inform-text",
    "--stage-inform-soft",
    "--stage-recommend-text",
    "--stage-recommend-soft",
    "--stage-act-text",
    "--stage-act-soft",
    "--fit-ok-fill",
    "--fit-tight-fill",
    "--fit-over-fill",
    "--fit-track",
    "--fit-ok-text",
    "--fit-tight-text",
    "--fit-over-text",
)

# (foreground, background, minimum ratio), checked in both schemes.
PAIRS = [
    ("--color-text", "--color-bg", TEXT),
    ("--color-text", "--color-surface", TEXT),
    ("--color-text", "--color-surface-2", TEXT),
    ("--color-text-muted", "--color-bg", TEXT),
    ("--color-text-muted", "--color-surface", TEXT),
    ("--color-text-muted", "--color-surface-2", TEXT),
    ("--color-on-primary", "--color-primary", TEXT),
    ("--color-on-primary", "--color-primary-hover", TEXT),
    ("--color-primary-text", "--color-bg", TEXT),
    ("--color-primary-text", "--color-surface", TEXT),
    ("--color-primary-text", "--color-primary-soft", TEXT),
    ("--color-text", "--color-primary-soft", TEXT),
    ("--color-bg", "--color-text", TEXT),  # selected filter chip (inverted)
    ("--stage-inform-text", "--stage-inform-soft", TEXT),
    ("--stage-recommend-text", "--stage-recommend-soft", TEXT),
    ("--stage-act-text", "--stage-act-soft", TEXT),
    ("--fit-ok-text", "--color-surface", TEXT),
    ("--fit-tight-text", "--color-surface", TEXT),
    ("--fit-over-text", "--color-surface", TEXT),
    ("--color-border-control", "--color-bg", NON_TEXT),
    ("--color-border-control", "--color-surface", NON_TEXT),
    ("--color-border-control", "--color-surface-2", NON_TEXT),
    ("--color-selected-border", "--color-bg", NON_TEXT),
    ("--color-selected-border", "--color-surface", NON_TEXT),
    ("--color-focus", "--color-bg", NON_TEXT),
    ("--color-focus", "--color-surface", NON_TEXT),
    ("--fit-ok-fill", "--fit-track", NON_TEXT),
    ("--fit-tight-fill", "--fit-track", NON_TEXT),
    ("--fit-over-fill", "--fit-track", NON_TEXT),
]

DECL_RE = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")
HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}")


def _css():
    return TOKENS_PATH.read_text(encoding="utf-8")


def _block_after(css, start):
    """Return the text between the brace that opens at or after `start` and its match."""
    i = css.index("{", start)
    depth = 0
    for j in range(i, len(css)):
        if css[j] == "{":
            depth += 1
        elif css[j] == "}":
            depth -= 1
            if depth == 0:
                return css[i + 1 : j]
    raise AssertionError("unbalanced braces in tokens.css")


def _schemes():
    css = re.sub(r"/\*.*?\*/", "", _css(), flags=re.S)
    light_at = re.search(r"(?m)^:root\s*\{", css)
    assert light_at, "no top-level :root block"
    light = dict(DECL_RE.findall(_block_after(css, light_at.start())))
    media = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{", css)
    assert media, "no prefers-color-scheme: dark block"
    inner = _block_after(css, media.start())
    root = re.search(r":root\s*\{", inner)
    assert root, "no :root inside the dark block"
    dark = dict(DECL_RE.findall(_block_after(inner, root.start())))
    return {"light": light, "dark": dark}


def _luminance(hex_color):
    rgb = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hex(tokens, name):
    value = tokens[name].strip()
    assert HEX_RE.fullmatch(value), f"{name} is not a 6-digit hex color: {value}"
    return value


def test_contrast_function_matches_known_values():
    assert round(contrast("#FFFFFF", "#000000"), 2) == 21.0
    assert round(contrast("#EE0000", "#FFFFFF"), 2) == 4.53
    assert round(contrast("#8A8D90", "#FFFFFF"), 2) == 3.34


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_tokens_complete(scheme):
    tokens = _schemes()[scheme]
    missing = [t for t in COLOR_TOKENS if t not in tokens]
    assert missing == [], f"{scheme} scheme is missing {missing}"


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_token_contrast(scheme):
    tokens = _schemes()[scheme]
    failures = []
    for fg, bg, minimum in PAIRS:
        ratio = contrast(_hex(tokens, fg), _hex(tokens, bg))
        if ratio < minimum:
            failures.append(f"{fg} on {bg}: {ratio:.2f} < {minimum}")
    assert failures == [], f"{scheme}: " + "; ".join(failures)


def test_fixed_values_from_the_contract():
    schemes = _schemes()
    assert schemes["light"]["--color-border-control"].strip().upper() == "#8A8D90"
    assert schemes["dark"]["--color-border-control"].strip().upper() == "#8A8A92"
    assert schemes["dark"]["--color-primary"].strip().upper() == "#EE0000"
    assert schemes["light"]["--stage-inform-text"].strip().upper() == "#2E6B28"
    assert schemes["light"]["--stage-recommend-text"].strip().upper() == "#8A6100"


def test_fonts_vendored():
    provenance = (FONTS / "PROVENANCE.txt").read_text(encoding="utf-8")
    assert FONT_REPO in provenance
    assert FONT_COMMIT in provenance
    for name in FONT_FILES:
        path = FONTS / name
        assert path.is_file(), name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        line = next((ln for ln in provenance.splitlines() if ln.startswith(name)), "")
        assert digest in line, f"{name}: SHA-256 {digest} not recorded in PROVENANCE.txt"
    assert "SIL OPEN FONT LICENSE" in (FONTS / "OFL.txt").read_text(encoding="utf-8").upper()


def test_font_faces_local():
    css = _css()
    faces = re.findall(r"@font-face\s*\{([^}]*)\}", css)
    assert len(faces) == 3, "expected one @font-face per family"
    for face in faces:
        urls = re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", face)
        assert urls, face
        for url in urls:
            assert re.fullmatch(r"fonts/[A-Za-z-]+\.woff2", url), url
        assert re.search(r"font-display\s*:\s*swap", face), face
    assert not re.search(r"fonts\.googleapis|fonts\.gstatic|@import\s+url\(\s*['\"]?https?:", css)
