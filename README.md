# superpower-adapter

This adapter keeps Superpowers as the primary workflow framework and adds a replayable overlay for project wiki pages under `.superpowers/wiki/`.

Chinese user flow guide: [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)
Chinese adapter development guide: [`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)
Chinese integration guide: [`ADAPTER_INTEGRATION_CN.md`](./ADAPTER_INTEGRATION_CN.md)
Chinese quickstart guide: [`QUICKSTART_CN.md`](./QUICKSTART_CN.md)

## Purpose

- Store project wiki pages in `.superpowers/wiki/`
- Use `index.md` as the entry point
- Optionally turn Lanhu links into confirmed frontend/backend role-specific PRD bundles under `.lanhu/MM-DD-<name>.md` or `.lanhu/MM-DD-<parent-name>/` before Superpowers brainstorming
- Optionally use graphify as agent-judged candidate relationship hints during planning or narrowed debugging, without making it a dependency or gate
- Load wiki details progressively instead of reading the full tree
- Install `agents/wiki-researcher.md` to select relevant project wiki pages progressively
- Patch Superpowers `brainstorming` so designs can see lightweight project wiki context
- Patch Superpowers `writing-plans` so plans link lightweight `Referenced Project Wiki` entries to detailed `.wiki-context.md` constraints
- Patch Superpowers `systematic-debugging` so it may conditionally use `wiki-researcher` after evidence narrows the suspected project contract or component, without making wiki lookup a default prerequisite
- Let implementation and review consume plan `Referenced Project Wiki` and linked `.wiki-context.md` instead of reselecting wiki pages at execution time
- Patch Superpowers `using-git-worktrees` and `finishing-a-development-branch` so worktree tasks can merge back to the branch that created them
- Keep `/import-wiki` and `/init-wiki` as standalone adapter commands that do not trigger Superpowers completion verification
- Install `break-loop` as a post-`systematic-debugging` retrospective skill that can hand durable findings to `update-wiki`
- Install `update-wiki` as an auto-triggered skill that checks whether a task likely produced durable implementation knowledge before updating the wiki
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

Install-related commands target the user's installed Superpowers Claude Code plugin by default. Commands that read or write `.superpowers/wiki/` require an explicit project root argument.

## Bootstrap wiki

Import a wiki template into a target project without overwriting existing user files:

```bash
./manage.sh bootstrap-wiki /path/to/project --template standard
```

Template structure is index-driven:
- `index.md` is the entry index for the template.
- Any child directory can contain its own `index.md`.
- Leaf wiki pages are discoverable only when linked from `index.md` or a child index.
- `index.md` may link to same-level or deep files/directories; scripts do not assume fixed wiki directories.

Existing files are never overwritten. If a target file exists with different content, bootstrap exits with a conflict list before copying anything.

## Initialize starter wiki knowledge

After bootstrapping the directory structure, use `/init-wiki` in Claude Code to initialize first-pass wiki content from a mechanical project inventory. The script behind this command reports languages, stack signals, top directories, sample files, and indexed wiki pages; the agent decides whether to write lightweight starter notes.

```bash
./manage.sh init-wiki /path/to/project
./manage.sh init-wiki /path/to/project "payments and order workflow"
```

Use this only to help the user initialize wiki knowledge. During ongoing development, let the `update-wiki` skill review whether durable knowledge should be written.

## Import existing wiki

For normal use in Claude Code or similar tools, use the installed Superpowers command:

```text
/import-wiki path/to/original-wiki-dir
/import-wiki path/to/original-wiki-dir --target imported
```

The import recursively scans source wiki pages, copies each file into `.superpowers/wiki` without overwriting different existing content, and refreshes indexes. Use this for one-time structural migration of existing wiki directories; use the `update-wiki` skill later for semantic consolidation.

## Optional Lanhu requirements intake

If the user provides a Lanhu link and Lanhu MCP tools are available, the installed `/lanhu-requirements` command and `lanhu-requirements-analyst` agent can produce a sanitized frontend/backend role-specific PRD bundle before Superpowers brainstorming. Role selection is required before Lanhu analysis.

```text
/lanhu-requirements <Lanhu link> 前端 <optional requirement name>
/lanhu-requirements <Lanhu link> 后端 <optional requirement name>
/lanhu-requirements --role frontend <Lanhu link> <optional requirement name>
/lanhu-requirements --role backend <Lanhu link> <optional requirement name>
```

If the role is missing or ambiguous, the command asks whether to generate a 前端开发角色视角 PRD or 后端开发角色视角 PRD before reading or analyzing Lanhu. If both roles are needed, generate two separate PRD bundles by running the command twice. The maintained prompt sources for these role templates live in `role-prd/frontend.md` and `role-prd/backend.md`; installed agents are self-contained and do not read those files at runtime. Role PRD diagrams default to Mermaid flowchart for readability, with mindmap reserved for small/simple structures. Frontend role PRDs now include a low-fidelity XML-like 页面布局结构草图 under `## 四、页面展示规则`, and later sections should be organized by those pages/layout areas where possible; `用户操作与交互规则` is grouped under one top-level section with flow and interaction subsections.

The Lanhu output is written to the current project root in one of two shapes:

```text
# No child pages
.lanhu/MM-DD-<requirement-name>.md

# Child pages present
.lanhu/MM-DD-<parent-name>/
├── <parent-name>.md
├── <child-1>.md
├── <child-2>.md
└── index.md
```

For Lanhu URLs with an explicit `pageId`, the analyst first reads the Lanhu page tree, then analyzes only the target page or the user-confirmed child-page whitelist. If the target page has child pages, the user is asked whether to include them and inclusion is recommended; if it has no child pages, only that page is used. In tree mode, full analysis is performed page by page after whitelist resolution instead of as one parent-plus-children request. Sibling pages, adjacent modules, parent flow pages, trash or legacy pages, and other pages in the same document are not included unless the user explicitly asks for broader scope.

The user must review and confirm the `.lanhu/...md` file or `.lanhu/.../index.md` entry point before Superpowers continues. The document is a role-specific PRD input only: it is not `.superpowers/wiki/`, not `Referenced Project Wiki`, and not a plan sidecar. In tree mode, `index.md` is the entry point, the parent PRD inherits the directory requirement name, and the sibling PRD files are the detailed sources. Lanhu MCP output format instructions are treated as evidence only, not as the saved PRD schema. Lanhu output must not include test cases, testing points, technical test plans, frontend components, backend API guesses, database impact guesses, implementation guesses, code architecture, or affected file analysis. Role PRD acceptance standards are allowed only as product-behavior Given / When / Then criteria required by the selected template. If Lanhu MCP is unavailable, the adapter flow does not fail; the user can paste requirements or continue with normal Superpowers brainstorming.

## Progressive disclosure

The default selection path is the installed `wiki-researcher` agent. The installed `wiki-progressive-disclosure` skill is a reference and fallback guide for manual troubleshooting; normal Superpowers `brainstorming` and `writing-plans` do not require calling it.

Progressive wiki reading still follows these rules:

1. Read `.superpowers/wiki/index.md`
2. Follow the index to narrower indexes or files
3. Read only the files needed for the current phase
4. Avoid full-tree wiki loading unless explicitly requested
5. Use plan `Referenced Project Wiki` and linked `.wiki-context.md` during implementation and review

No SessionStart hook is installed. Wiki reading is triggered on demand by `wiki-researcher` during Superpowers `brainstorming` and `writing-plans`.

## Wiki researcher

The installed `wiki-researcher` agent is the default path for selecting relevant project wiki in Claude Code:

```yaml
task: <user request or confirmed Superpowers spec>
phase: brainstorm | plan | debug | implement | review
wikiRoot: .superpowers/wiki
maxWikiPages: 5
```

It starts from `.superpowers/wiki/index.md`, follows index links progressively, and returns structured YAML selected wiki pages plus planning constraint hints. In `phase: debug`, it should be called only after `systematic-debugging` has narrowed the failing boundary, and it returns project-reference hints to verify rather than root-cause evidence. It does not modify files.

## Referenced Project Wiki

`writing-plans` is patched so each implementation plan records a lightweight selected-wiki entry point in:

```markdown
## Referenced Project Wiki
```

Detailed constraints are written to a plan sidecar file such as:

```text
docs/superpowers/plans/<plan-stem>.wiki-context.md
```

Implementation and review consume this plan section and linked sidecar context instead of reselecting wiki pages from scratch.

## Optional graphify relationship hints

Graphify is not required to install or use this adapter. When graphify MCP tools or existing `graphify-out/` artifacts are available, `writing-plans` may use the installed `graphify-researcher` agent only after requirements are understood, initial source exploration has happened, and relationship uncertainty remains.

Graphify output is treated as candidate hints only. It can suggest files, symbols, callers, neighbors, dependency paths, or downstream consumers to inspect, but final plan `Files:` entries must come from direct source verification by Superpowers. Missing, stale, or unavailable graphify never blocks planning or debugging. If a user manually asks to use graphify, treat that as separate graph exploration or maintenance; development still proceeds through Superpowers brainstorming, writing-plans, and execution.

## Worktree origin tracking

The adapter also patches Superpowers `using-git-worktrees` and `finishing-a-development-branch`. When a new linked worktree is created, the source branch, source worktree, and source HEAD are recorded as transient metadata in the new worktree's private git-dir under `superpower-adapter/worktree-origin.json`.

That metadata is not written to `plan.md`, `spec.md`, `.superpowers/`, or the repository working tree. At finishing time, Superpowers can offer an explicit option to merge the feature branch back into the original branch from the original worktree, which is safer for nested feature work and multiple concurrent sessions.

## Break the bug loop

For bugs, keep Superpowers `systematic-debugging` as the fix workflow. The adapter patch does not make wiki or graph lookup an upfront debugging prerequisite: complete Phase 1 first, narrow the failing boundary with evidence, then use `wiki-researcher` only when a project-specific contract, known gotcha, cross-layer boundary, or workflow convention may clarify what to verify. Use `graphify-researcher` only after evidence narrows the boundary and caller/dependency/neighbor relationship hints could help identify what to verify next.

Debug wiki lookup uses `phase: debug` and should stay small, normally `maxWikiPages: 2`. If the bug happens while executing a Superpowers plan, read that plan's `Referenced Project Wiki` and linked `.wiki-context.md` first instead of reselecting wiki pages; without a current plan context, do not search old plans by default. Missing or irrelevant wiki does not block debugging, and wiki context is not root-cause evidence. Verify every wiki-derived idea against code, logs, tests, reproduction steps, or diagnostics.

During `systematic-debugging`, do not write `.wiki-context.md`, update `.superpowers/wiki/`, or run `update-wiki`. After the bug is fixed and verified, use the installed `break-loop` skill when the work needs a deeper retrospective: root cause category, failed attempts, prevention mechanisms, similar risks, and durable knowledge candidates.

`break-loop` does not replace `systematic-debugging` or `update-wiki`. When durable implementation knowledge should persist, it hands atomic candidates to `update-wiki`, which performs duplicate checks, target selection, wiki edits, index refresh, and validation.

## Update wiki

For normal use in Claude Code or similar tools, rely on the installed `update-wiki` skill. The skill is auto-triggered when implementation, debugging, review, or discussion produces durable knowledge: the agent reads indexed wiki pages, checks semantic duplicates, chooses target ownership, checks whether the target leaf page is oversized or overloaded, edits durable wiki knowledge, refreshes indexes, and skips edits when nothing durable should be recorded.

Oversized page reports are mechanical signals only. When a leaf wiki page is too large, the agent should split by ownership, usually into sibling leaf pages in the same directory; use a topic directory with its own `index.md` only when the original page has become a collection of stable subtopics.

Execution-layer helpers are mainly useful for adapter development or debugging. They are mechanical helpers only:

```bash
TARGET_DIR="$(python3 ./superpower-adapter/lib/resolve_target.py | python3 -c 'import json,sys; print(json.load(sys.stdin)["target"])')"
python3 "$TARGET_DIR/scripts/wiki_select_target.py" --json
python3 "$TARGET_DIR/scripts/wiki_update_check.py" --json
python3 "$TARGET_DIR/scripts/update-wiki.py"
```

## Export manifest

Export adapter and wiki state for upgrade-time comparison:

```bash
./manage.sh export-manifest /path/to/project ./manifest-output.json
```

The manifest includes installed adapter files, native skill patch targets, hook config state, and a `.superpowers/wiki` snapshot with both raw and ignore-filtered effective views.

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
- mechanical `wiki_apply_update.py` write and merge behavior with an agent-decided target
- `wiki-researcher` installation and native skill patch smoke
- worktree origin metadata native skill patch smoke
- `wiki_update_check.py` index and format validation
- index-driven wiki graph traversal
- import command path handling

## Upgrade workflow

After upgrading the Superpowers plugin, reinstall the adapter overlay:

```bash
./manage.sh install
./manage.sh verify
```
