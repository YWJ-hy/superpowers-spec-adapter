#!/usr/bin/env python3
"""Export self-contained, repo-local wiki maintenance skills into a wiki repository.

A standalone wiki repository (wiki content at the repo root) cannot use the
adapter's installed Superpowers skills directly. This stamps two self-contained
skills plus a shared vendored toolchain into the repo's `.claude/`, so anyone who
clones the repo and opens Claude Code there can maintain the wiki consistently
with zero dependency on superpower-adapter at runtime:

  .claude/wiki-tools/scripts/        # vendored mechanical helpers (single copy)
  .claude/wiki-tools/.export-manifest.json
  .claude/skills/update-wiki/        # author-side incremental maintenance
  .claude/skills/migrate-wiki/       # section-ify + typed graph enrichment

Re-run to refresh the vendored scripts after the adapter's logic changes. Files
are managed (they carry the adapter's generated marker); the export refuses to
overwrite any pre-existing unmanaged file.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

# The dependency closure the two skills need. wiki_common / wiki_section are the
# libraries; the other three are the CLI entry points the SKILL.md commands call.
VENDORED_SCRIPTS = [
    "wiki_common.py",
    "wiki_section.py",
    "wiki_generate_section_index.py",
    "wiki_update_check.py",
    "wiki_migrate_helper.py",
]
SKILLS = ["update-wiki", "migrate-wiki"]
TOOLS_REL = Path(".claude") / "wiki-tools"
SCRIPTS_REL = TOOLS_REL / "scripts"
SKILLS_REL = Path(".claude") / "skills"
MANIFEST_REL = TOOLS_REL / ".export-manifest.json"


def _marker(adapter_root: Path) -> str:
    sys.path.insert(0, str(adapter_root / "lib"))
    from adapter_manifest import generated_marker  # noqa: E402

    return generated_marker(adapter_root)


def _is_managed(path: Path, marker: str) -> bool:
    """A target is safe to write if it does not exist or carries the adapter marker."""
    if not path.exists():
        return True
    try:
        return marker in path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False


def _skill_files(skills_src: Path, skill: str) -> list[tuple[Path, Path]]:
    """(source, relative) pairs for every file under one skill source dir."""
    base = skills_src / skill
    return [(src, src.relative_to(base)) for src in sorted(base.rglob("*")) if src.is_file()]


def export(adapter_root: Path, repo_root: Path) -> dict:
    adapter_root = adapter_root.resolve()
    repo_root = repo_root.resolve()
    scripts_src = adapter_root / "overlays" / "scripts"
    skills_src = adapter_root / "overlays" / "wiki-repo-skills"
    marker = _marker(adapter_root)
    manifest = json.loads((adapter_root / "manifest.json").read_text(encoding="utf-8"))

    scripts_dst = repo_root / SCRIPTS_REL
    skills_dst = repo_root / SKILLS_REL

    # Pre-flight: never clobber a file we did not generate.
    targets: list[Path] = [scripts_dst / name for name in VENDORED_SCRIPTS]
    targets.append(repo_root / MANIFEST_REL)
    for skill in SKILLS:
        for _src, rel in _skill_files(skills_src, skill):
            targets.append(skills_dst / skill / rel)
    blocked = [str(t) for t in targets if not _is_managed(t, marker)]
    if blocked:
        raise SystemExit(
            "Refusing to overwrite unmanaged file(s) (missing adapter marker):\n  "
            + "\n  ".join(blocked)
        )

    # Vendored scripts (verbatim — they carry no install-time placeholders).
    scripts_dst.mkdir(parents=True, exist_ok=True)
    script_hashes: dict[str, str] = {}
    for name in VENDORED_SCRIPTS:
        data = (scripts_src / name).read_bytes()
        (scripts_dst / name).write_bytes(data)
        script_hashes[name] = hashlib.sha256(data).hexdigest()

    # Skill packs.
    for skill in SKILLS:
        for src, rel in _skill_files(skills_src, skill):
            dst = skills_dst / skill / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    export_manifest = {
        "generatedMarker": marker,
        "adapterName": manifest.get("name"),
        "adapterVersion": manifest.get("version", ""),
        "toolsDir": SCRIPTS_REL.as_posix(),
        "skills": SKILLS,
        "scripts": script_hashes,
    }
    manifest_path = repo_root / MANIFEST_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(export_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return export_manifest


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: export_wiki_skills.py <adapter-root> <wiki-repo-root>", file=sys.stderr)
        return 1
    adapter_root = Path(argv[1])
    repo_root = Path(argv[2])
    if not repo_root.is_dir():
        print(f"Wiki repository root not found: {repo_root}", file=sys.stderr)
        return 1

    result = export(adapter_root, repo_root)
    print(f"Exported repo-local wiki skills to {repo_root}")
    print(f"  adapter: {result['adapterName']} {result['adapterVersion']}")
    print(f"  toolchain: {result['toolsDir']} ({len(result['scripts'])} scripts)")
    print(f"  skills: {', '.join(result['skills'])} (under .claude/skills/)")

    settings = repo_root / ".shared-superpowers" / "settings.json"
    if not settings.is_file():
        print(
            "\nHint: no .shared-superpowers/settings.json found. Add one with "
            "wiki.sharedNeutrality.blockedTerms / blockedPatterns to enable mechanical "
            "neutrality guards, and wiki.updateAuthorization to govern writes.",
        )
    print("\nThese skills are edit-only: they regenerate indexes/graph and validate, but never commit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
