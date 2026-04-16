#!/usr/bin/env python3
"""Check for broken internal markdown links in the Athanor repo.

Finds [text](relative/path) links in markdown files and verifies
the targets exist on disk. Only checks local relative paths — skips
URLs, mailto, and anchor-only references.

Usage:
    python3 scripts/check-doc-refs.py              # check all docs
    python3 scripts/check-doc-refs.py docs/         # specific subtree
    python3 scripts/check-doc-refs.py CLAUDE.md     # single file

Exit codes: 0 = clean, 1 = broken links found.

Run after restructuring docs/ or renaming files — this catches the
"file moved but references not updated" failure mode.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Default targets to scan when no argument given
DEFAULT_TARGETS = [
    REPO_ROOT / "docs",
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "MEMORY.md",
    REPO_ROOT / "STATUS.md",
]

# Markdown link pattern: [text](href)
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def is_local(href: str) -> bool:
    """Return True if href is a relative local file path."""
    if href.startswith(("http://", "https://", "ftp://", "mailto:")):
        return False
    if href.startswith("#"):
        return False
    return bool(href.strip())


def resolve_target(base_dir: Path, href: str) -> Path:
    """Resolve href relative to the markdown file's directory."""
    # Strip anchor fragment
    path_part = href.split("#")[0].strip()
    if not path_part:
        return None
    # href may be relative to file location or repo root
    candidate = (base_dir / path_part).resolve()
    return candidate


def check_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Return list of (lineno, link_text, href) for broken links."""
    broken = []
    try:
        lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:
        print(f"  Warning: could not read {filepath}: {e}", file=sys.stderr)
        return broken

    base = filepath.parent
    for lineno, line in enumerate(lines, 1):
        for m in LINK_RE.finditer(line):
            text, href = m.group(1), m.group(2).strip()
            if not is_local(href):
                continue
            target = resolve_target(base, href)
            if target is None:
                continue
            if not target.exists():
                broken.append((lineno, text, href))

    return broken


def collect_files(targets: list[Path]) -> list[Path]:
    """Collect all .md files from target paths."""
    files = []
    for t in targets:
        if not t.exists():
            print(f"  Warning: path does not exist: {t}", file=sys.stderr)
            continue
        if t.is_file() and t.suffix == ".md":
            files.append(t)
        elif t.is_dir():
            files.extend(sorted(t.rglob("*.md")))
    return files


def main():
    if len(sys.argv) > 1:
        targets = [Path(a) for a in sys.argv[1:]]
        # Resolve relative to CWD or repo root
        resolved = []
        for t in targets:
            if not t.is_absolute():
                t = REPO_ROOT / t
            resolved.append(t)
        targets = resolved
    else:
        targets = DEFAULT_TARGETS

    files = collect_files(targets)
    if not files:
        print("No markdown files found.")
        sys.exit(0)

    all_broken = []
    for f in files:
        broken = check_file(f)
        for lineno, text, href in broken:
            rel = f.relative_to(REPO_ROOT)
            all_broken.append((rel, lineno, text, href))

    if all_broken:
        print(f"Found {len(all_broken)} broken internal link(s) across {len(files)} files:\n")
        for rel, lineno, text, href in all_broken:
            print(f"  {rel}:{lineno}: [{text}]({href})")
        sys.exit(1)
    else:
        print(f"OK — {len(files)} files checked, no broken internal links.")


if __name__ == "__main__":
    main()
