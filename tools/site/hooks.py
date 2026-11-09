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
"""

from __future__ import annotations

from pathlib import Path

from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[2]
INCLUDE = ["framework", "architecture", "platform", "catalog"]
SUFFIXES = {".md", ".svg", ".png", ".jpg", ".jpeg"}


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
