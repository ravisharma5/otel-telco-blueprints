"""MkDocs hook: add repo-root doc folders to the site file set.

MkDocs cannot use the repo root as ``docs_dir`` (the site would include
tools/, schemas/ and test fixtures, and ``site_dir`` would sit inside it).
So ``docs_dir`` is ``site-src/`` and this hook appends the public doc
folders in place, without moving them. Only an allowlist of folders and
file suffixes is added; tools/, schemas/ and templates/ never are.

Symlinks are refused: a symlinked file or folder anywhere under an allowlisted
folder (or the folder itself) stops the build, so a link cannot publish
content from outside the allowlist. Any path that resolves outside its folder
is skipped as a second line of defence.

Reference pages (front matter ``type: reference``) get a banner right after
the H1, chosen by ``doc_status``: draft and review pages show a fixed warning,
done pages show none. The text comes only from the BANNERS map, never from
front matter, and other doc types are left untouched.
"""

from __future__ import annotations

from pathlib import Path

from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[2]
INCLUDE = ["framework", "architecture", "platform", "catalog"]
SUFFIXES = {".md", ".svg", ".png", ".jpg", ".jpeg"}
BANNERS = {"draft": "Draft: content may change", "review": "In review"}


def _refuse_symlink(path):
    """Stop the build if path, or any folder between it and ROOT, is a symlink."""
    for part in [path, *path.parents]:
        if part == ROOT:
            return
        if part.is_symlink():
            raise SystemExit(
                f"site: symlink not allowed: {part.relative_to(ROOT).as_posix()}"
            )


def on_files(files, config):
    for top in INCLUDE:
        base = ROOT / top
        if base.is_symlink():
            raise SystemExit(f"site: symlink not allowed: {top}")
        if not base.is_dir():
            continue
        real_base = base.resolve()
        for path in sorted(base.rglob("*")):
            _refuse_symlink(path)
            if not path.is_file() or path.suffix.lower() not in SUFFIXES:
                continue
            if not path.resolve().is_relative_to(real_base):
                continue
            rel = path.relative_to(ROOT).as_posix()
            new = File(
                rel,
                src_dir=str(ROOT),
                dest_dir=config["site_dir"],
                use_directory_urls=config["use_directory_urls"],
            )
            clash = files.get_file_from_path(rel) or next(
                (f for f in files if f.dest_uri == new.dest_uri), None
            )
            if clash is not None:
                raise SystemExit(
                    f"site: {rel} collides with site-src/{clash.src_uri}; "
                    "remove the site-src stub"
                )
            files.append(new)
    return files


def on_page_markdown(markdown, page, config, files):
    """Reference pages only: a draft or review banner right after the H1."""
    meta = page.meta or {}
    if meta.get("type") != "reference":
        return markdown
    status = meta.get("doc_status")
    text = BANNERS.get(status) if isinstance(status, str) else None
    if text is None:  # done, or anything unexpected (a list, a mapping): no banner
        return markdown
    banner = f'!!! warning "{text}"\n\n'
    lines = markdown.splitlines(keepends=True)
    fence = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in ("```", "~~~"):
            if fence is None:
                fence = marker
            elif marker == fence:
                fence = None
            continue
        if fence is None and line.startswith("# "):
            head = "".join(lines[: i + 1])
            if not head.endswith("\n"):
                head += "\n"
            return head + "\n" + banner + "".join(lines[i + 1 :])
    return banner + markdown
