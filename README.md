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
- Keep planning-selected spec context in a plan sidecar directory alongside `docs/superpowers/plans/*.md`
- Check workflow readiness before planning, implementation, review, or completion
- Keep `/import-spec`, `/init-spec`, and `/update-spec` as standalone adapter commands that do not trigger Superpowers completion verification
- Recommend spec candidates from `.superpowers/spec/` and optionally write them into the plan sidecar
- Check whether a task likely produced durable implementation knowledge before updating spec
- Reinstall the same overlay after upgrading `superpowers/`

## Install

```bash
./superpower-adapter/install.sh
./superpower-adapter/verify.sh
```

Install-related commands still target the user's installed Superpowers Claude Code plugin by default. Commands that read or write `.superpowers/spec/` now require an explicit project root argument.

## Bootstrap specs

Import a spec template into a target project without overwriting existing user files:

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project
```

In non-interactive environments, pass a named template:

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project --template standard
```

Templates are listed from `https://github.com/YWJ-hy/superpowers-spec-adapter/tree/main/spec-template`. Each directory under `spec-template/` is a template name. The selected template is imported into `.superpowers/spec/` and must contain an entry `index.md`.

Template structure is index-driven:
- `index.md` is the entry index for the template.
- Any child directory can contain its own `index.md`.
- Leaf spec files are discoverable only when linked from `index.md` or a child index.
- `index.md` may link to same-level or deep files/directories; scripts do not assume fixed spec directories.

Existing files are never overwritten. If a target file exists with different content, bootstrap exits with a conflict list before copying anything.

## Initialize starter spec knowledge

After bootstrapping the directory structure, initialize first-pass spec content from the current project:

```bash
./superpower-adapter/manage.sh init-spec /path/to/project
./superpower-adapter/manage.sh init-spec /path/to/project "payments and order workflow"
```

This command:
- ensures `.superpowers/spec/` exists
- uses the existing `.superpowers/spec` topic files as the initialization targets
- analyzes the visible repository shape
- appends first-pass initialization knowledge without overwriting existing user-authored spec files
- refreshes the progressive-disclosure index chain

Use this only to help the user initialize spec knowledge.
During ongoing development, continue writing durable knowledge with `update-spec`.
The installed `/init-spec` command is standalone: after it initializes spec content and refreshes indexes, it should stop without invoking Superpowers completion verification or other development workflow checks.

## Import existing specs

For normal use in Claude Code or similar tools, use the installed Superpowers command:

```text
/import-spec path/to/original-spec-dir
/import-spec path/to/original-spec-dir --hint "api contract"
```

The import recursively scans source spec files, routes each file to an adapter leaf spec, and refreshes `.superpowers/spec` indexes.
Use this for one-time conversion of existing spec directories; use `update-spec` for ongoing durable knowledge updates.
The installed `/import-spec` command is standalone: after it imports specs and refreshes indexes, it should stop without invoking Superpowers completion verification or other development workflow checks.
For adapter debugging, run the installed execution-layer script from the Superpowers plugin directory rather than a project-relative `superpowers/scripts` path.

## Update specs

For normal use in Claude Code or similar tools, use the installed Superpowers command `/update-spec`; see [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md). The installed `/update-spec` command is standalone: after it checks duplicates, writes durable spec knowledge, and refreshes indexes, it should stop without invoking Superpowers completion verification or other development workflow checks. The Python commands below are the execution layer behind the adapter command and are mainly useful for adapter development or debugging.

Resolve the installed Superpowers target first, then run execution-layer scripts from a project root that contains or should contain `.superpowers/spec/`:

```bash
TARGET_DIR="$(python3 ./superpower-adapter/lib/resolve_target.py | python3 -c 'import json,sys; print(json.load(sys.stdin)["target"])')"
```

1. use the one-shot command when you already know the hint, title, why, and rules

```bash
python3 "$TARGET_DIR/scripts/spec_update_run.py" "error handling" "Error normalization" "Prevent inconsistent API error shapes." "Normalize API error payloads" "Keep user-facing messages stable"
```

2. or use the staged path for more control

```bash
python3 "$TARGET_DIR/scripts/spec_select_target.py" "error handling"
python3 "$TARGET_DIR/scripts/spec_update_prompt.py" <target-spec-relative-path>
python3 "$TARGET_DIR/scripts/spec_update_template.py" <target-spec-relative-path> "Error normalization" "Prevent inconsistent API error shapes."
python3 "$TARGET_DIR/scripts/spec_apply_update.py" <target-spec-relative-path> "Error normalization" "Prevent inconsistent API error shapes." "Normalize API error payloads" "Keep user-facing messages stable"
python3 "$TARGET_DIR/scripts/update-spec.py"
```

3. indexes are refreshed automatically in the one-shot path

Repeated updates with the same `Update` title now merge: `Why` is refreshed, `Rules / Contracts` are merged/deduped, and existing validation notes are preserved.

```bash
python3 "$TARGET_DIR/scripts/update-spec.py"
```

The script maintains only sections between:

```markdown
<!-- superpower-adapter:auto:start -->
<!-- superpower-adapter:auto:end -->
```

Human-authored content outside those markers is preserved.
It also extracts simple summaries from child `index.md` files and leaf spec files using their first heading and first non-empty line.
Directories named `draft`, `archive`, and `examples` are ignored by default during index and summary tree generation.
You can extend this list with `.superpowers/spec/.adapter-ignore` where each non-empty, non-comment line is a directory name to ignore.

## Progressive disclosure

The installed `spec-progressive-disclosure` skill tells the agent to:

1. Read `.superpowers/spec/index.md`
2. Follow the index to narrower indexes or files
3. Read only the files needed for the current task
4. Avoid full-tree spec loading unless explicitly requested

The session hook injects a lightweight recursive summary tree by default, not the full spec text.
The adapter now ships a shared `spec_common.py` helper so `update-spec.py` and `spec-context.py` reuse the same traversal, ignore, and summary logic.

## Workflow gate

The workflow gate is normally invoked by the adapter's SessionStart hook and `plan-context-sidecar` skill. Use it manually when automatic preparation is blocked or ambiguous:

```bash
python3 "$TARGET_DIR/scripts/workflow-gate.py" planning --plan docs/superpowers/plans/<stem>.md
python3 "$TARGET_DIR/scripts/workflow-gate.py" implement --json
python3 "$TARGET_DIR/scripts/workflow-gate.py" review --json
python3 "$TARGET_DIR/scripts/workflow-gate.py" completion --summary "<task summary>"
```

This surfaces `OK`, `WARN`, or `BLOCK` so the agent can repair missing plan state or sidecar state before proceeding.

## Spec selector

Recommend spec candidates for the current task:

```bash
python3 "$TARGET_DIR/scripts/spec_select_context.py" "error handling" --phase implement --limit 5
python3 "$TARGET_DIR/scripts/spec_select_context.py" "error handling" --phase implement --json
```

You can also write the selected candidates directly into the sidecar for the current or explicit plan:

```bash
python3 "$TARGET_DIR/scripts/spec_select_context.py" "error handling" --phase implement --write-sidecar
python3 "$TARGET_DIR/scripts/spec_select_context.py" "error handling" --phase review --plan docs/superpowers/plans/<stem>.md --write-sidecar --limit 3
```

## Spec update check

Before deciding whether to update `.superpowers/spec/`, run:

```bash
python3 "$TARGET_DIR/scripts/spec_update_check.py" --summary "normalize api error contract"
python3 "$TARGET_DIR/scripts/spec_update_check.py" --summary "normalize api error contract" --changed-file src/api/error_handler.py --json
```

This returns `NO_UPDATE_NEEDED`, `RECOMMEND_UPDATE`, or `STRONGLY_RECOMMEND_UPDATE`.

## Plan sidecar context

When a task is driven by a Superpowers plan file, keep the primary plan file unchanged:

```text
docs/superpowers/plans/YYYY-MM-DD-<feature>.md
```

Store planning-selected task context in the matching sidecar directory:

```text
docs/superpowers/plans/YYYY-MM-DD-<feature>.context/
├── plan.jsonl
├── implement.jsonl
├── review.jsonl
└── state.json
```

Track the active plan with:

```text
.superpowers/current-plan
```

Useful diagnostic commands:

```bash
python3 "$TARGET_DIR/scripts/workflow-gate.py" planning --plan docs/superpowers/plans/<stem>.md --hint "<task keywords>"
python3 "$TARGET_DIR/scripts/plan-context.py" render --phase implement
python3 "$TARGET_DIR/scripts/plan-context.py" render --phase review
python3 "$TARGET_DIR/scripts/plan-context.py" verify --current
```

SessionStart and the `plan-context-sidecar` skill normally initialize the sidecar, recommend indexed specs, and write planning context into `plan.jsonl` automatically for the current plan. `plan-context.py` remains an execution-layer helper, not a user-facing slash command.

Git recommendation:

- Commit `docs/superpowers/plans/<stem>.context/` with the plan so planning-selected context stays reproducible.
- Treat `.superpowers/current-plan` as local working state; prefer adding it to `.gitignore` unless your team explicitly wants to share the active pointer.

## Export manifest

Export adapter and spec state for upgrade-time comparison:

```bash
./superpower-adapter/manage.sh export-manifest /path/to/project ./superpower-adapter/manifest-output.json
```

The manifest includes installed adapter files, patched hook files, and a `.superpowers/spec` snapshot with both raw and ignore-filtered effective views. The effective view applies both default ignored directories and any custom entries from `.adapter-ignore`.

## Release check

Run the full local validation flow before treating the adapter state as releasable:

```bash
./superpower-adapter/manage.sh release-check /path/to/project
```

This runs:
- `verify`
- `doctor`
- `self-test`
- `export-manifest`

The self-test now covers:
- repeated `spec_update_run.py` merge behavior
- `plan-context.py` smoke and regression flows
- `workflow-gate.py` readiness checks
- `spec_select_context.py` recommendation and sidecar writes
- `spec_update_check.py` durable-knowledge recommendations

## Upgrade workflow

After upgrading `superpowers/`, run:

```bash
./superpower-adapter/install.sh
./superpower-adapter/verify.sh
```

Managed files contain the marker `Generated by superpower-adapter`. The installer refuses to overwrite unmarked files.
The `doctor` command also checks spec health: entry index presence, ignore configuration, raw vs effective view drift, and missing index chains for effective leaf specs.
