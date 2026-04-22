# superpower-adapter

This adapter keeps Superpowers as the primary workflow framework and adds a replayable overlay for project specs under `.superpowers/spec/`.

Chinese integration guide: [`ADAPTER_INTEGRATION_CN.md`](./ADAPTER_INTEGRATION_CN.md)
Chinese quickstart guide: [`QUICKSTART_CN.md`](./QUICKSTART_CN.md)

## Purpose

- Store project specs in `.superpowers/spec/`
- Use `index.md` as the entry point
- Load spec details progressively instead of reading the full tree
- Keep planning-selected spec context in a plan sidecar directory alongside `docs/superpowers/plans/*.md`
- Reinstall the same overlay after upgrading `superpowers/`

## Install

```bash
./superpower-adapter/install.sh
./superpower-adapter/verify.sh
```

Install-related commands still target the user's installed Superpowers Claude Code plugin by default. Commands that read or write `.superpowers/spec/` now require an explicit project root argument.

## Bootstrap specs

Initialize the minimum project spec structure without overwriting existing files:

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project
```

Optionally create starter category indexes in the same command:

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project backend frontend guides
```

Or use presets:

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project --preset web
./superpower-adapter/manage.sh bootstrap-spec /path/to/project --preset backend
./superpower-adapter/manage.sh bootstrap-spec /path/to/project --preset fullstack
```

Presets:
- `web` -> `frontend guides`
- `backend` -> `backend guides`
- `fullstack` -> `backend frontend guides`

Preset categories and explicit category arguments can be combined.
Preset-backed categories also get richer starter `index.md` content for `backend`, `frontend`, and `guides`.

This creates:
- `.superpowers/spec/index.md`
- `.superpowers/spec/.adapter-ignore`
- optional category directories with `index.md`

## Update specs

From a project root that contains or should contain `.superpowers/spec/`:

1. use the one-shot command when you already know the hint, title, why, and rules

```bash
python3 superpowers/scripts/spec_update_run.py "error handling" "Error normalization" "Prevent inconsistent backend error shapes." "Normalize backend error payloads" "Keep user-facing messages stable"
```

2. or use the staged path for more control

```bash
python3 superpowers/scripts/spec_select_target.py "error handling"
python3 superpowers/scripts/spec_update_prompt.py backend/error-handling.md
python3 superpowers/scripts/spec_update_template.py backend/error-handling.md "Error normalization" "Prevent inconsistent backend error shapes."
python3 superpowers/scripts/spec_apply_update.py backend/error-handling.md "Error normalization" "Prevent inconsistent backend error shapes." "Normalize backend error payloads" "Keep user-facing messages stable"
python3 superpowers/scripts/update-spec.py
```

3. indexes are refreshed automatically in the one-shot path

Repeated updates with the same `Update` title now merge: `Why` is refreshed, `Rules / Contracts` are merged/deduped, and existing validation notes are preserved.

```bash
python3 superpowers/scripts/update-spec.py
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

Useful commands:

```bash
python3 superpowers/scripts/plan-context.py init docs/superpowers/plans/<stem>.md --set-current
python3 superpowers/scripts/plan-context.py add --phase plan --spec .superpowers/spec/backend/example.md --reason "Why this spec matters"
python3 superpowers/scripts/plan-context.py render --phase implement
python3 superpowers/scripts/plan-context.py render --phase review
python3 superpowers/scripts/plan-context.py verify --current
```

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

## Upgrade workflow

After upgrading `superpowers/`, run:

```bash
./superpower-adapter/install.sh
./superpower-adapter/verify.sh
```

Managed files contain the marker `Generated by superpower-adapter`. The installer refuses to overwrite unmarked files.
The `doctor` command also checks spec health: entry index presence, ignore configuration, raw vs effective view drift, and missing index chains for effective leaf specs.
