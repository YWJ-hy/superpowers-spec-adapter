#!/usr/bin/env python3
"""Mechanical helper for wiki section migration.

Usage:
  wiki_migrate_helper.py --inventory <project-root> [--wiki-root project|shared|all]
  wiki_migrate_helper.py --validate <project-root> [--wiki-root project|shared|all]
  wiki_migrate_helper.py --generate-indexes <project-root> [--wiki-root project|shared|all]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wiki_common import (  # noqa: E402
    build_wiki_index_graph,
    existing_wiki_roots,
    repo_root,
    select_wiki_root,
    selected_wiki_roots,
)
from wiki_section import list_section_ids, validate_section_markers  # noqa: E402


def heading_structure(text: str) -> list[dict]:
    """Extract heading structure from a markdown document."""
    headings = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            headings.append({"level": len(m.group(1)), "text": m.group(2).strip(), "line": i})
    return headings


def inventory(project_root: Path, wiki_root_selector: str) -> list[dict]:
    """List all indexed leaf pages with metadata."""
    roots = selected_wiki_roots(project_root, wiki_root_selector)
    results = []
    for root in roots:
        if not (root.path / "index.md").is_file():
            continue
        graph = build_wiki_index_graph(root.path)
        for leaf in graph.leaves:
            if leaf.name == "index.md":
                continue
            if leaf.suffix != ".md" or leaf.stem.endswith(".index"):
                continue
            text = leaf.read_text(encoding="utf-8")
            line_count = len(text.splitlines())
            headings = heading_structure(text)
            section_ids = list_section_ids(text)
            rel = leaf.relative_to(root.path).as_posix()
            results.append({
                "root": root.name,
                "path": rel,
                "lines": line_count,
                "headings": headings,
                "existingSections": section_ids,
                "hasSectionMarkers": len(section_ids) > 0,
            })
    return results


def validate(project_root: Path, wiki_root_selector: str) -> list[dict]:
    """Validate section markers in all indexed leaf pages."""
    roots = selected_wiki_roots(project_root, wiki_root_selector)
    issues = []
    for root in roots:
        if not (root.path / "index.md").is_file():
            continue
        graph = build_wiki_index_graph(root.path)
        for leaf in graph.leaves:
            if leaf.name == "index.md" or leaf.stem.endswith(".index"):
                continue
            text = leaf.read_text(encoding="utf-8")
            errors = validate_section_markers(text)
            if errors:
                rel = leaf.relative_to(root.path).as_posix()
                issues.append({"root": root.name, "path": rel, "errors": errors})
    return issues


def generate_indexes(project_root: Path, wiki_root_selector: str) -> int:
    """Generate section indexes for all documents with markers. Returns count."""
    from wiki_generate_section_index import process_all
    return process_all(project_root, wiki_root_selector)


def main() -> None:
    parser = argparse.ArgumentParser(description="Wiki section migration helper.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--inventory", metavar="PROJECT_ROOT", help="List indexed leaf pages with metadata")
    group.add_argument("--validate", metavar="PROJECT_ROOT", help="Validate section markers")
    group.add_argument("--generate-indexes", metavar="PROJECT_ROOT", help="Generate .index.md files")
    parser.add_argument("--wiki-root", choices=["project", "shared", "all"], default="all")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.inventory:
        project = Path(args.inventory).resolve()
        results = inventory(project, args.wiki_root)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            for item in results:
                markers = f" [{len(item['existingSections'])} sections]" if item["hasSectionMarkers"] else ""
                print(f"  {item['root']}:{item['path']} ({item['lines']} lines){markers}")
                for h in item["headings"]:
                    indent = "    " + "  " * (h["level"] - 1)
                    print(f"{indent}L{h['line']}: {'#' * h['level']} {h['text']}")
            print(f"\nTotal: {len(results)} leaf page(s)")

    elif args.validate:
        project = Path(args.validate).resolve()
        issues = validate(project, args.wiki_root)
        if args.json:
            print(json.dumps(issues, indent=2, ensure_ascii=False))
        else:
            if not issues:
                print("All section markers are valid.")
            else:
                for item in issues:
                    print(f"  {item['root']}:{item['path']}:")
                    for err in item["errors"]:
                        print(f"    - {err}")
                print(f"\n{len(issues)} file(s) with issues.")
                sys.exit(1)

    elif args.generate_indexes:
        project = Path(args.generate_indexes).resolve()
        count = generate_indexes(project, args.wiki_root)
        print(f"Generated {count} section index file(s).")


if __name__ == "__main__":
    main()
