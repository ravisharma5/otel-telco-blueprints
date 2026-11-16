"""Explorer UI copy: one front-matter file, word limits, and banned terms.

Every explorer UI string lives in explorer/src/content/copy.md, which Vale lints
through DOC_DIRS. Strings under a key named `buttons`, `headings`, or `notes`
(at any depth) carry word limits. No string may use a support or validation
label, a filler word the style guide bans, a planning id, or a phase number.
"""

from __future__ import annotations

import re

import pytest
import yaml

from tools.guards.patterns import PLANNING_ID_RE
from tools.tests.conftest import REPO_ROOT

COPY_PATH = REPO_ROOT / "explorer/src/content/copy.md"
EXPLORER_SRC = REPO_ROOT / "explorer/src"
LIMITS = {"buttons": 4, "headings": 8, "notes": 25}
PHASE_NUMBER = re.compile(r"(?i)\bphases? [0-9]")
# GA is matched case-sensitively so "gateway" or "ga" inside words never trip it.
BANNED_CASED = [re.compile(r"\bGA\b")]
BANNED = [
    "Technology Preview",
    "Developer Preview",
    "production-ready",
    "supported by Red Hat",
    "validated",
    "unverified",
    "proven",
    "seamless",
    "robust",
    "Coming soon",
    "Click here",
    "Send to team",
]


def _copy():
    text = COPY_PATH.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, "copy.md has no front matter"
    data = yaml.safe_load(match.group(1))
    assert isinstance(data, dict)
    return data


def _strings(node, path=()):
    """Yield (key path, string) for every string leaf."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, path + (str(key),))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _strings(value, path + (str(i),))
    elif isinstance(node, str):
        yield path, node


def _words(text):
    return len([w for w in text.split() if re.search(r"\w", w)])


def _banned_hits(text):
    hits = [p.pattern for p in BANNED_CASED if p.search(text)]
    hits += [term for term in BANNED if term.lower() in text.lower()]
    if PLANNING_ID_RE.search(text):
        hits.append("planning id")
    if PHASE_NUMBER.search(text):
        hits.append("phase number")
    return hits


def test_copy_loads():
    data = _copy()
    assert data["home"]["hero"]["headline"]
    assert data["site"]["skip_link"] == "Skip to content"


def test_word_limits():
    over = []
    for path, text in _strings(_copy()):
        limits = [LIMITS[k] for k in path if k in LIMITS]
        if limits and _words(text) > min(limits):
            over.append(f"{'.'.join(path)}: {_words(text)} words > {min(limits)}")
    assert over == []


@pytest.mark.parametrize(
    "text,limit_key",
    [("Open the recipe now please", "buttons"), (" ".join(["word"] * 9), "headings")],
)
def test_word_limit_check_bites(text, limit_key):
    assert _words(text) > LIMITS[limit_key]


def test_no_banned_terms():
    hits = []
    for path, text in _strings(_copy()):
        for hit in _banned_hits(text):
            hits.append(f"{'.'.join(path)}: {hit}")
    assert hits == []


@pytest.mark.parametrize(
    "sample", ["Now GA on the platform", "a seamless rollout", "Coming soon", "see Phase 5"]
)
def test_banned_check_bites(sample):
    assert _banned_hits(sample)


def test_no_prose_in_astro_files():
    # The hero and footer strings must come from copy.md, never be typed into a template.
    data = _copy()
    samples = [
        data["home"]["hero"]["headline"],
        data["home"]["hero"]["notes"]["lede"],
        data["footer"]["notes"]["otel"],
        data["site"]["skip_link"],
    ]
    for astro in EXPLORER_SRC.rglob("*.astro"):
        text = astro.read_text(encoding="utf-8")
        for sample in samples:
            assert sample not in text, f"{astro.relative_to(REPO_ROOT)} hard-codes: {sample}"


# Home sections the page renders; each lives under copy.home.
HOME_SECTIONS = ["hero", "how", "goals", "gallery", "architects", "note"]
COPY_REF = re.compile(r"(?<![/\w.])copy(?!\.md\b)((?:\.[A-Za-z_][\w]*|\[['\"][\w-]+['\"]\])+)")


def _ref_path(ref):
    return [p for p in re.split(r"\.|\[['\"]|['\"]\]", ref) if p]


def test_home_copy_sections():
    home = _copy()["home"]
    missing = [s for s in HOME_SECTIONS if s not in home]
    assert missing == []


# `const s = copy.use_case.setup;` (optionally `as Type`) names an alias for a copy path.
COPY_ALIAS = re.compile(r"\bconst\s+([A-Za-z_]\w*)\s*=\s*copy((?:\.[A-Za-z_][\w]*)+)\s*(?:as\s[^;\n]+)?;")


def _alias_refs(text):
    """(alias, full copy path) for each `alias.key...` use of a copy alias in one file."""
    out = []
    for alias, base in COPY_ALIAS.findall(text):
        use = re.compile(rf"(?<![\w.$]){re.escape(alias)}((?:\.[A-Za-z_][\w]*|\[['\"][\w-]+['\"]\])+)")
        for match in use.finditer(text):
            out.append((alias, base + match.group(1)))
    return out


def _resolve(data, ref):
    """True when every key in ref resolves; stops at a method or index on a string or list."""
    node = data
    for key in _ref_path(ref):
        if not isinstance(node, dict):
            return True
        if key not in node:
            return False
        node = node[key]
    return True


def test_copy_keys_used():
    # Every copy.<path> referenced by an explorer template resolves in copy.md,
    # including paths reached through an alias such as `const s = copy.use_case.setup`.
    data = _copy()
    refs = aliased = 0
    bad = []
    for astro in EXPLORER_SRC.rglob("*.astro"):
        text = astro.read_text(encoding="utf-8")
        for match in COPY_REF.finditer(text):
            refs += 1
            if not _resolve(data, match.group(1)):
                bad.append(f"{astro.name}: copy{match.group(1)}")
        for alias, ref in _alias_refs(text):
            aliased += 1
            if not _resolve(data, ref):
                bad.append(f"{astro.name}: {alias} -> copy{ref}")
    assert refs, "no copy references found"
    assert aliased, "no aliased copy references found"
    assert bad == []


def test_alias_resolution_bites():
    text = "const s = copy.use_case.setup;\nconst x = s.no_such_key;"
    assert any(not _resolve(_copy(), ref) for _, ref in _alias_refs(text))


def test_unused_regional_only_copy_removed():
    # No serving rule uses the regional-only reason, so its copy line is gone.
    assert "regional-only" not in COPY_PATH.read_text(encoding="utf-8")


def test_no_home_prose_in_astro_files():
    # Any home string of three or more words typed into a template is a copy leak.
    samples = [text for _, text in _strings(_copy()["home"]) if _words(text) >= 3]
    for astro in EXPLORER_SRC.rglob("*.astro"):
        text = astro.read_text(encoding="utf-8")
        for sample in samples:
            assert sample not in text, f"{astro.relative_to(REPO_ROOT)} hard-codes: {sample}"


def test_copy_never_types_a_setup():
    # The default setup comes from data/serving/setups.yaml through placeholders, so
    # no copy string may type a setup's label or GPU memory size and drift from it.
    setups = yaml.safe_load((REPO_ROOT / "data/serving/setups.yaml").read_text(encoding="utf-8"))["setups"]
    needles = set()
    for setup in setups:
        needles.add(setup["label"].lower())
        needles.add(f"{setup['accelerators']['memory_per_gpu_gb']} gb")
    hits = [
        f"{'.'.join(path)}: {needle}"
        for path, text in _strings(_copy())
        for needle in needles
        if needle in text.lower()
    ]
    assert hits == []


# ---------- text the explorer shows from data, not copy.md ----------
# Recipe card fields and placement notes (front matter, which Vale skips), and
# flag whys and option text from data/serving/*.yaml (some shown nowhere else)
# reach the page through explorer.json, so they get the same checks as copy.md.


def _exported_strings(repo_root=REPO_ROOT):
    """(key path, string) for every string the exporter emits, minus URLs."""
    from tools.site.export_explorer import build_explorer_data

    for path, text in _strings(build_explorer_data(repo_root)):
        if text.startswith("https://") or path[-1] in ("url", "model_card", "red_hat_build", "recipe_url"):
            continue
        yield path, text


def _exported_prose(repo_root=REPO_ROOT):
    """Unique prose strings shown on use-case pages, in first-seen order."""
    from tools.site.export_explorer import build_explorer_data

    seen = {}
    for uc in build_explorer_data(repo_root)["use_cases"]:
        for value in uc["card"].values():
            for text in value if isinstance(value, list) else [value]:
                seen.setdefault(text, None)
        for by_batch in uc["states"].values():
            for state in by_batch.values():
                for tier in state["tiers"]:
                    seen.setdefault(tier["note"], None)
                for flag in state["flags"]:
                    seen.setdefault(flag["why"], None)
                for option in state["options"]:
                    for key in ("what", "check", "reason_text"):
                        seen.setdefault(option[key], None)
                    for text in option["set"] + option["limits"]:
                        seen.setdefault(text, None)
    return [t for t in seen if t]


def test_no_banned_terms_in_exported_text():
    hits = [f"{'.'.join(path[-4:])}: {hit}" for path, text in _exported_strings() for hit in _banned_hits(text)]
    assert hits == []


def test_exported_text_check_bites(tmp_path):
    import shutil

    for name in ("data", "catalog"):
        shutil.copytree(REPO_ROOT / name, tmp_path / name)
    dest = tmp_path / "platform/serving-routing-placement"
    dest.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "platform/serving-routing-placement/README.md", dest / "README.md")
    page = tmp_path / "catalog/standards-knowledge/grounded-knowledge-assistant/README.md"
    text = page.read_text(encoding="utf-8")
    page.write_text(text.replace('  risk: "', '  risk: "A validated, seamless flow. ', 1), encoding="utf-8")
    hits = [hit for _, t in _exported_strings(tmp_path) for hit in _banned_hits(t)]
    assert "validated" in hits and "seamless" in hits


def test_exported_prose_passes_vale():
    # The same Vale config as repo prose; errors and warnings fail, as in make lint-prose.
    import json
    import subprocess

    from tools.tests.conftest import vale_or_skip

    vale = vale_or_skip()
    body = "# Explorer text from data\n\n" + "\n\n".join(_exported_prose()) + "\n"
    proc = subprocess.run(
        [vale, "--config", ".vale.ini", "--ext=.md", "--output=JSON"],
        cwd=REPO_ROOT,
        input=body,
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), proc.stderr
    alerts = [a for found in json.loads(proc.stdout or "{}").values() for a in found]
    lines = body.splitlines()
    bad = [
        f"{a['Severity']} {a['Check']}: {lines[a['Line'] - 1][:80]}"
        for a in alerts
        if a["Severity"] in ("error", "warning")
    ]
    assert bad == []
