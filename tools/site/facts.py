"""Facts stamp: a digest of every cited source, and the scripted source re-check.

The digest is a SHA-256 over sorted lines, one per input:

- every data row of the Sources table on each blueprint page
  (platform/*/README.md and catalog/*/*/README.md), as
  "<relpath> | <cells joined by ' | '>"; the Sources section title per page type
  comes from tools/bplint/budgets.yaml (sources_section);
- every source URL in data/serving/*.yaml, as "data/serving/<file> | <url>";
- every extra URL in data/facts-check.yaml, as "data/facts-check.yaml | <url>".

It uses content only, never git dates, because CI clones are shallow.
tools/tests/test_proposal.py fails when the stored digest differs from the
recomputed one, so any Sources change after the re-check fails CI until the
re-check is redone and the stamp rewritten.

Usage:
    python -m tools.site.facts --urls                 # print every source URL
    python -m tools.site.facts --digest               # print the digest
    python -m tools.site.facts --check                # exit 1 if the stamp is stale
    python -m tools.site.facts --write [--checked YYYY-MM-DD] [--card MODEL=SHA ...]
    python -m tools.site.facts --recheck --report PATH [--only PATH]

--recheck opens the network: it fetches every URL (3 attempts with backoff on a
network error, timeout, 429, or 5xx) and reads the current sha of every linked
OTel model card, then writes a TSV triage report (failing URLs, cross-host
redirects, changed card revisions). Write the report outside the repository.
It is never run in CI, and tests inject their own fetch functions.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

from tools.bplint.markdown import parse_doc

ROOT = Path(__file__).resolve().parents[2]
FACTS_FILE = "data/facts-check.yaml"
BUDGETS_FILE = "tools/bplint/budgets.yaml"
SERVING_GLOB = "data/serving/*.yaml"
PAGE_GLOBS = ("platform/*/README.md", "catalog/*/*/README.md")
URL_RE = re.compile(r"https?://[^\s\"'<>)\]|]+")
CARD_RE = re.compile(r"^https://huggingface\.co/([A-Za-z0-9_.-]+/(OTel-[A-Za-z0-9_.-]+))$")
HF_API = "https://huggingface.co/api/models/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
PLAIN_AGENT = "curl/8.7.1"
# Card revisions (by model name) the pages were written against, before the
# first stamp. Revisions stored in data/facts-check.yaml take precedence.
CITED_REVISIONS = {
    "OTel-2.0-LLM-31B-IT": "dd9a4c46",
    "OTel-LLM-8.3B-Classification": "fdf15b1e",
    "OTel-LLM-12B-Safety": "47d4d617",
    "OTel-2.0-Decision-26B-A4B-4bit": "7ff608e3",
}
FACTS_HEADER = (
    "# Facts stamp. Written by `uv run python -m tools.site.facts --write` after the\n"
    "# source re-check; tools/tests/test_proposal.py fails when sources_digest no\n"
    "# longer matches the Sources tables, serving-data URLs, and extra_urls.\n"
)


# ---- offline inputs ------------------------------------------------------


def _load_facts(root: Path) -> dict:
    path = root / FACTS_FILE
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _pages(root: Path) -> list[Path]:
    found: set[Path] = set()
    for pattern in PAGE_GLOBS:
        found.update(root.glob(pattern))
    return sorted(found)


def _source_rows(root: Path) -> list[tuple[str, list[str], list[str]]]:
    """(relpath, cells, hrefs) for every Sources table data row."""
    budgets = yaml.safe_load((root / BUDGETS_FILE).read_text(encoding="utf-8"))
    types = budgets.get("types", {})
    out = []
    for page in _pages(root):
        rel = page.relative_to(root).as_posix()
        doc = parse_doc(page, page.read_text(encoding="utf-8"), display=rel)
        kind = (doc.front_matter or {}).get("type")
        title = types.get(kind, {}).get("sources_section")
        sec = doc.section(title) if title else None
        if sec is None:
            continue
        for table in sec.tables:
            for row in table.rows:
                hrefs = [h for group in row.hrefs for h in group if h]
                out.append((rel, row.cells, hrefs))
    return out


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from _strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from _strings(value)


def _serving_urls(root: Path) -> list[tuple[str, str]]:
    """(relpath, url) for every URL in any value of data/serving/*.yaml."""
    out = []
    for path in sorted(root.glob(SERVING_GLOB)):
        rel = path.relative_to(root).as_posix()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for text in _strings(data):
            out.extend((rel, url) for url in URL_RE.findall(text))
    return out


def _digest_lines(root: Path) -> list[str]:
    lines = [f"{rel} | {' | '.join(cells)}" for rel, cells, _ in _source_rows(root)]
    lines += [f"{rel} | {url}" for rel, url in _serving_urls(root)]
    lines += [f"{FACTS_FILE} | {url}" for url in _load_facts(root).get("extra_urls") or []]
    return sorted(lines)


def sources_digest(repo_root: Path = ROOT) -> str:
    """SHA-256 hex digest of every cited source (see the module docstring)."""
    blob = "\n".join(_digest_lines(Path(repo_root))).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _normalise(url: str) -> str:
    return urllib.parse.urldefrag(url.strip())[0]


def all_urls(repo_root: Path = ROOT) -> list[str]:
    """Unique, sorted http(s) URLs from the same inputs, fragments removed."""
    root = Path(repo_root)
    urls = {h for _, _, hrefs in _source_rows(root) for h in hrefs}
    urls |= {u for _, u in _serving_urls(root)}
    urls |= set(_load_facts(root).get("extra_urls") or [])
    return sorted({_normalise(u) for u in urls if u.startswith(("https://", "http://"))})


def card_repos(urls: list[str]) -> list[str]:
    """OTel model card repo ids (owner/OTel-name) linked from the URL list."""
    return sorted({m.group(1) for u in urls if (m := CARD_RE.match(u.rstrip("/")))})


def linked_card_repos(repo_root: Path = ROOT) -> list[str]:
    """OTel model card repo ids linked anywhere on the pages or in serving data."""
    root = Path(repo_root)
    files = _pages(root) + sorted(root.glob(SERVING_GLOB))
    urls = {
        _normalise(u)
        for path in files
        for u in URL_RE.findall(path.read_text(encoding="utf-8"))
    }
    return card_repos(sorted(urls))


# ---- network re-check (executor only, never in CI) ----------------------


@dataclass
class UrlResult:
    url: str
    final_url: str | None
    status: int | None
    attempts: int
    host_changed: bool
    ok: bool
    error: str = ""


def _host(url: str | None) -> str:
    host = (urllib.parse.urlsplit(url or "").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _fetch_with(url: str, timeout: float, agent: str) -> tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": agent,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(1024)
            return resp.status, resp.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.geturl() or url


def _default_fetch(url: str, timeout: float) -> tuple[int, str]:
    """GET with a browser user agent; on 401 or 403, try once with a plain one.

    Some hosts (3GPP) need a browser user agent; others (docs.redhat.com behind
    its CDN) refuse a browser user agent that a script sends but accept a plain
    client one.
    """
    status, final = _fetch_with(url, timeout, USER_AGENT)
    if status in (401, 403):
        status, final = _fetch_with(url, timeout, PLAIN_AGENT)
    return status, final


def _retryable(status: int | None) -> bool:
    return status is None or status == 429 or status >= 500


def _check_one(url, attempts, backoff, timeout, fetch, sleep) -> UrlResult:
    status = final = None
    error = ""
    tries = 0
    for tries in range(1, attempts + 1):
        try:
            status, final = fetch(url, timeout)
            error = ""
        except Exception as exc:  # network error or timeout: retry
            status, final, error = None, None, f"{type(exc).__name__}: {exc}"
        if not _retryable(status) or tries == attempts:
            break
        sleep(backoff[min(tries, len(backoff)) - 1])
    ok = status is not None and 200 <= status < 400
    changed = final is not None and _host(final) != _host(url)
    return UrlResult(url, final, status, tries, changed, ok, error)


def check_urls(
    urls,
    attempts: int = 3,
    backoff: tuple[float, ...] = (2, 4),
    timeout: float = 20,
    fetch=None,
    sleep=time.sleep,
    workers: int = 1,
) -> list[UrlResult]:
    """Fetch each URL, retrying on a network error, timeout, 429, or 5xx."""
    fetch = fetch or _default_fetch
    args = (attempts, backoff, timeout, fetch, sleep)
    if workers <= 1:
        return [_check_one(u, *args) for u in urls]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda u: _check_one(u, *args), urls))


def _default_fetch_json(url: str, timeout: float) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep((2, 4)[attempt])
    raise RuntimeError("unreachable")


def card_revisions(repo_ids, fetch_json=None, timeout: float = 20) -> dict[str, str]:
    """Current short sha (8 characters) of each model card, from the HF API."""
    fetch_json = fetch_json or _default_fetch_json
    return {repo: str(fetch_json(HF_API + repo, timeout)["sha"])[:8] for repo in repo_ids}


def triage_rows(results, card_changes) -> list[tuple[str, str, str]]:
    """Rows that need a human: failing URLs, cross-host redirects, changed cards."""
    rows = []
    for r in results:
        if not r.ok:
            detail = f"status {r.status}" if r.status is not None else r.error
            rows.append(("failing URL", r.url, f"{detail}; attempts {r.attempts}"))
        elif r.host_changed:
            rows.append(("cross-host redirect", r.url, f"-> {r.final_url}"))
    for repo, (cited, now) in sorted(card_changes.items()):
        rows.append(("changed card revision", repo, f"cited {cited}, now {now}"))
    return rows


# ---- facts file ----------------------------------------------------------


def write_facts(root: Path, checked: str | None = None, cards: dict | None = None) -> dict:
    data = _load_facts(root)
    data["checked"] = checked if checked is not None else data.get("checked", "")
    data["sources_digest"] = sources_digest(root)
    data["url_count"] = len(all_urls(root))
    merged = dict(data.get("card_revisions") or {})
    merged.update(cards or {})
    lines = [
        FACTS_HEADER.rstrip("\n"),
        f'checked: "{data["checked"]}"',
        f'sources_digest: "{data["sources_digest"]}"',
        f"url_count: {data['url_count']}",
    ]
    if merged:
        lines.append("card_revisions:")
        lines += [f'  {repo}: "{sha}"' for repo, sha in sorted(merged.items())]
    else:
        lines.append("card_revisions: {}")
    lines.append("extra_urls:")
    lines += [f"  - {url}" for url in data.get("extra_urls") or []]
    (root / FACTS_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


def _read_report_urls(path: Path) -> list[str]:
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0] in ("failing URL", "cross-host redirect"):
            urls.append(parts[1])
    return urls


def recheck(root: Path, report: Path, only: Path | None = None) -> int:
    urls = _read_report_urls(only) if only else all_urls(root)
    results = check_urls(urls, workers=8)
    repos = [] if only else linked_card_repos(root)
    baseline = {**CITED_REVISIONS, **(_load_facts(root).get("card_revisions") or {})}
    # Keyed by model name (the part after the owner), as in data/facts-check.yaml.
    current = {r.split("/", 1)[1]: sha for r, sha in card_revisions(repos).items()} if repos else {}
    changes = {
        repo: (baseline[repo], sha)
        for repo, sha in current.items()
        if repo in baseline and not sha.startswith(baseline[repo][:8])
    }
    rows = triage_rows(results, changes)
    report.parent.mkdir(parents=True, exist_ok=True)
    out = ["kind\turl\tdetail"] + ["\t".join(r) for r in rows]
    out += [f"card\t{repo}\t{sha}" for repo, sha in sorted(current.items())]
    report.write_text("\n".join(out) + "\n", encoding="utf-8")
    passed = sum(r.ok for r in results)
    retried = sum(r.attempts > 1 for r in results)
    print(
        f"checked {len(results)}; passed {passed}; retried {retried}; "
        f"still failing {len(results) - passed}; cross-host {sum(r.host_changed for r in results)}; "
        f"cards {len(current)}; changed cards {len(changes)}; report {report}"
    )
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.site.facts")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--urls", action="store_true", help="print every source URL")
    mode.add_argument("--digest", action="store_true", help="print the sources digest")
    mode.add_argument("--check", action="store_true", help="exit 1 if the stamp is stale")
    mode.add_argument("--write", action="store_true", help="rewrite digest and url_count")
    mode.add_argument("--recheck", action="store_true", help="network re-check (not in CI)")
    ap.add_argument("--report", type=Path, help="TSV triage report path (with --recheck)")
    ap.add_argument("--only", type=Path, help="re-check only the URLs in a previous report")
    ap.add_argument("--checked", help="check date YYYY-MM-DD (with --write)")
    ap.add_argument("--card", action="append", default=[], help="MODEL=SHA (with --write)")
    args = ap.parse_args(argv)

    if args.urls:
        print("\n".join(all_urls(ROOT)))
    elif args.digest:
        print(sources_digest(ROOT))
    elif args.check:
        stored = _load_facts(ROOT).get("sources_digest")
        now = sources_digest(ROOT)
        if stored != now:
            print(f"facts: stale stamp (stored {stored}, now {now}); redo the re-check")
            return 1
        print(f"facts: stamp current ({now})")
    elif args.write:
        cards = dict(c.split("=", 1) for c in args.card)
        data = write_facts(ROOT, args.checked, cards)
        print(f"facts: wrote {FACTS_FILE} ({data['url_count']} URLs, {data['sources_digest']})")
    else:
        if not args.report:
            ap.error("--recheck needs --report PATH")
        return recheck(ROOT, args.report, args.only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
