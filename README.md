# superpower-adapter

This adapter keeps Superpowers as the primary workflow framework and adds a replayable overlay for project specs under `.superpowers/spec/`.

Chinese user flow guide: [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)
Chinese adapter development guide: [`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)
Chinese integration guide: [`ADAPTER_INTEGRATION_CN.md`](./ADAPTER_INTEGRATION_CN.md)
Chinese quickstart guide: [`QUICKSTART_CN.md`](./QUICKSTART_CN.md)

## Purpose

- Store project specs in `.superpowers/spec/`
- Use `index.md` as the entry point
- Load spec details progressively instead of reading the full tree
- Install `agents/spec-researcher.md` to select relevant project specs progressively
- Patch Superpowers `brainstorming` so designs can see lightweight project spec context
- Patch Superpowers `writing-plans` so plans record selected specs in `Referenced Project Specs`
- Let implementation and review consume plan `Referenced Project Specs` instead of reselecting specs at execution time
- Keep `/import-spec`, `/init-spec`, and `/update-spec` as standalone adapter commands that do not trigger Superpowers completion verification
- Check whether a task likely produced durable implementation knowledge before updating spec
- Reinstall the same overlay after upgrading `superpowers/`

## Install

```bash
./manage.sh install
./manage.sh verify
```

If this adapter lives as `superpower-adapter/` inside another project, run the same entrypoint from the host project:

```bash
./superpower-adapter/manage.sh install
./superpower-adapter/manage.sh verify
```

Install-related commands target the user's installed Superpowers Claude Code plugin by default. Commands that read or write `.superpowers/spec/` require an explicit project root argument.

## Bootstrap specs

Import a spec template into a target project without overwriting existing user files:

```bash
./manage.sh bootstrap-spec /path/to/project --template standard
```

Template structure is index-driven:
- `index.md` is the entry index for the template.
- Any child directory can contain its own `index.md`.
- Leaf spec files are discoverable only when linked from `index.md` or a child index.
- `index.md` may link to same-level or deep files/directories; scripts do not assume fixed spec directories.

Existing files are never overwritten. If a target file exists with different content, bootstrap exits with a conflict list before copying anything.

## Initialize starter spec knowledge

After bootstrapping the directory structure, initialize first-pass spec content from the current project:

```bash
./manage.sh init-spec /path/to/project
./manage.sh init-spec /path/to/project "payments and order workflow"
```

Use this only to help the user initialize spec knowledge. During ongoing development, continue writing durable knowledge with `/update-spec`.

## Import existing specs

For normal use in Claude Code or similar tools, use the installed Superpowers command:

```text
/import-spec path/to/original-spec-dir
/import-spec path/to/original-spec-dir --hint "api contract"
```

The import recursively scans source spec files, routes each file to an adapter leaf spec, and refreshes `.superpowers/spec` indexes. Use this for one-time conversion of existing spec directories.

## Progressive disclosure

The default selection path is the installed `spec-researcher` agent. The installed `spec-progressive-disclosure` skill is a reference and fallback guide for manual troubleshooting; normal Superpowers `brainstorming` and `writing-plans` do not require calling it.

Progressive spec reading still follows these rules:

1. Read `.superpowers/spec/index.md`
2. Follow the index to narrower indexes or files
3. Read only the files needed for the current phase
4. Avoid full-tree spec loading unless explicitly requested
5. Use plan `Referenced Project Specs` during implementation and review

No SessionStart hook is installed. Spec reading is triggered on demand by `spec-researcher` during Superpowers `brainstorming` and `writing-plans`.

## Spec researcher

The installed `spec-researcher` agent is the default path for selecting relevant project specs in Claude Code:

```yaml
task: <user request or confirmed Superpowers spec>
phase: brainstorm | plan | implement | review
specRoot: .superpowers/spec
maxSpecs: 5
```

It starts from `.superpowers/spec/index.md`, follows index links progressively, and returns structured YAML selected specs. It does not modify files.

## Referenced Project Specs

`writing-plans` is patched so each implementation plan records selected project specs in:

```markdown
## Referenced Project Specs
```

Implementation and review consume this plan section instead of reselecting specs from scratch.

## Update specs

For normal use in Claude Code or similar tools, use the installed Superpowers command `/update-spec`. The installed `/update-spec` command is standalone: after it checks duplicates, writes durable spec knowledge, and refreshes indexes, it should stop without invoking Superpowers completion verification or other development workflow checks.

Execution-layer helpers are mainly useful for adapter development or debugging:

```bash
TARGET_DIR="$(python3 ./superpower-adapter/lib/resolve_target.py | python3 -c 'import json,sys; print(json.load(sys.stdin)["target"])')"
python3 "$TARGET_DIR/scripts/spec_update_check.py" --summary "normalize api error contract"
python3 "$TARGET_DIR/scripts/spec_update_run.py" "error handling" "Error normalization" "Prevent inconsistent API error shapes." "Normalize API error payloads"
```

## Export manifest

Export adapter and spec state for upgrade-time comparison:

```bash
./manage.sh export-manifest /path/to/project ./manifest-output.json
```

The manifest includes installed adapter files, native skill patch targets, hook config state, and a `.superpowers/spec` snapshot with both raw and ignore-filtered effective views.

## Release check

Run the full local validation flow before treating the adapter state as releasable:

```bash
./manage.sh release-check /path/to/project
```

This runs:
- `verify`
- `doctor`
- `self-test`
- `export-manifest`

The self-test covers:
- repeated `spec_update_run.py` merge behavior
- `spec-researcher` installation and native skill patch smoke
- `spec_update_check.py` durable-knowledge recommendations
- index-driven spec graph traversal
- import command path handling

## Upgrade workflow

After upgrading the Superpowers plugin, reinstall the adapter overlay:

```bash
./manage.sh install
./manage.sh verify
```
