#!/usr/bin/env python3
"""Generate per-document section index files from wiki-section markers.

Usage:
  wiki_generate_section_index.py <wiki-file-path> [--wiki-root project|shared] [--project-root PATH]
  wiki_generate_section_index.py --all [--wiki-root project|shared|all] [--project-root PATH]

Scans section markers in wiki documents and generates companion .index.md files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wiki_section import extract_section, list_section_ids  # noqa: E402
from wiki_common import (  # noqa: E402
    build_wiki_index_graph,
    existing_wiki_roots,
    repo_root,
    select_wiki_root,
)

HARD_KEYWORDS = {"必须", "禁止", "MUST", "MUST NOT", "REQUIRED", "SHALL NOT"}
GENERATED_HEADER = "> Auto-generated from section markers. Do not edit manually.\n"


def detect_strength(content: str) -> str:
    upper = content.upper()
    for kw in HARD_KEYWORDS:
        if kw.upper() in upper:
            return "hard"
    return "soft"


def first_description(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            text = stripped.lstrip("#").strip()
            if text:
                return text[:80]
        elif stripped and not stripped.startswith("<!--"):
            return stripped[:80]
    return "(empty section)"


def generate_index(file_path: Path) -> str | None:
    """Generate index content for a wiki file. Returns None if no markers found."""
    text = file_path.read_text(encoding="utf-8")
    section_ids = list_section_ids(text)
    if not section_ids:
        return None

    title_line = ""
    for line in text.splitlines():
        if line.startswith("# "):
            title_line = line.lstrip("# ").strip()
            break
    if not title_line:
        title_line = file_path.stem

    lines = [
        f"# {title_line} — Section Index\n",
        GENERATED_HEADER,
        "| section | 描述 | 约束强度 |",
        "|---|---|---|",
    ]

    from wiki_section import extract_section as _extract  # noqa: F811

    for sid in section_ids:
        content = _extract(text, sid)
        if content is None:
            continue
        desc = first_description(content)
        strength = detect_strength(content)
        lines.append(f"| {sid} | {desc} | {strength} |")

    lines.append("")
    return "\n".join(lines)


def index_path_for(file_path: Path) -> Path:
    return file_path.parent / f"{file_path.stem}.index.md"


def process_file(file_path: Path) -> bool:
    """Process a single file. Returns True if index was written."""
    content = generate_index(file_path)
    if content is None:
        return False
    out = index_path_for(file_path)
    out.write_text(content, encoding="utf-8")
    print(f"  Generated: {out.name}")
    return True


def process_all(project_root: Path, wiki_root_selector: str) -> int:
    """Process all indexed leaf pages. Returns count of generated indexes."""
    roots = existing_wiki_roots(project_root) if wiki_root_selector == "all" else [select_wiki_root(project_root, wiki_root_selector)]
    count = 0
    for root in roots:
        if not (root.path / "index.md").is_file():
            continue
        graph = build_wiki_index_graph(root.path)
        for leaf in graph.leaves:
            if leaf.name == "index.md" or leaf.suffix == ".index.md":
                continue
            print(f"Scanning: {leaf.relative_to(root.path)}")
            if process_file(leaf):
                count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate section index files.")
    parser.add_argument("file_path", nargs="?", help="Wiki file path (relative to wiki root or absolute)")
    parser.add_argument("--all", action="store_true", help="Process all indexed leaf pages")
    parser.add_argument("--wiki-root", choices=["project", "shared", "all"], default="project")
    parser.add_argument("--project-root", default=None)
    args = parser.parse_args()

    project = Path(args.project_root) if args.project_root else repo_root(Path.cwd())

    if args.all:
        count = process_all(project, args.wiki_root)
        print(f"\nGenerated {count} section index file(s).")
    elif args.file_path:
        file_path = Path(args.file_path)
        if not file_path.is_absolute():
            wiki = select_wiki_root(project, args.wiki_root)
            file_path = wiki.path / file_path
        if not file_path.is_file():
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        if not process_file(file_path):
            print("No section markers found. No index generated.")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
