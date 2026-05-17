# superpower-adapter

This adapter keeps Superpowers as the primary workflow framework and adds a replayable overlay for project wiki pages under `.superpowers/wiki/` and shared wiki pages under `.shared-superpowers/wiki/`.

Chinese user flow guide: [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)
Chinese adapter development guide: [`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)
Chinese integration guide: [`ADAPTER_INTEGRATION_CN.md`](./ADAPTER_INTEGRATION_CN.md)
Chinese quickstart guide: [`QUICKSTART_CN.md`](./QUICKSTART_CN.md)

## Purpose

- Store project wiki pages in `.superpowers/wiki/` and optional neutral/portable shared wiki pages in `.shared-superpowers/wiki/` or a GitHub-backed shared-wiki repository accessed through the copyable MCP server
- Use `index.md` as the entry point
- Optionally turn Lanhu links into confirmed frontend/backend role-specific PRD packages under `.lanhu/MM-DD-<requirement-name>/` before Superpowers brainstorming, with `index.md` as the entrypoint and relationship map
- Optionally use graphify as agent-judged candidate relationship hints during planning or narrowed debugging, without making it a dependency or gate
- Load wiki details progressively instead of reading the full tree
- Install `agents/wiki-researcher.md` to select relevant project wiki pages progressively
- Patch Superpowers `brainstorming` so designs can see lightweight project wiki context and, when the user points to an existing confirmed `.lanhu/.../index.md` package, read that package as requirements input from its entrypoint instead of regenerating Lanhu output
- Patch Superpowers `writing-plans` so plans link lightweight `Referenced Project Wiki` entries to detailed `.wiki-context.md` constraints
- Patch Superpowers `systematic-debugging` so it may conditionally use `wiki-researcher` after evidence narrows the suspected project contract or component, without making wiki lookup a default prerequisite
- Let implementation and review consume plan `Referenced Project Wiki` and linked `.wiki-context.md` instead of reselecting wiki pages at execution time
- Patch Superpowers `using-git-worktrees` and `finishing-a-development-branch` so worktree tasks can merge back to the branch that created them
- Keep standalone adapter commands such as `/import-wiki`, `/init-wiki`, and `/lanhu-requirements` outside Superpowers completion/review/verification skills until they explicitly hand off to the next Superpowers workflow step
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

Install-related commands target all unique installed Superpowers Claude Code plugin directories by default, so multiple installed versions are patched together. Pass an explicit Superpowers target path to operate on only one plugin directory. Commands that read or write `.superpowers/wiki/` or `.shared-superpowers/wiki/` require an explicit project root argument.

Current compatibility baseline: Superpowers 5.1.0. `./manage.sh install` warns, but does not block, when the detected target version is newer than the baseline. The compatibility check reads the installed Superpowers target's `package.json` version when available.

### Optional subagent model configuration

By default, `adapter.config.json` is `{}` and the adapter does not change subagent model routing. Adapter agents keep `model: inherit`, and upstream Superpowers prompt templates keep their native `Task tool (general-purpose)` shape.

To pin models, copy the relevant entries from `adapter.config.example.jsonc` into `adapter.config.json` as standard JSON without comments:

```json
{
  "subagentModels": {
    "agents": {
      "wiki-researcher": "sonnet",
      "graphify-researcher": "sonnet",
      "lanhu-frontend-requirements-analyst": "opus",
      "lanhu-frontend-html-requirements-analyst": "opus",
      "lanhu-backend-requirements-analyst": "opus"
    },
    "upstreamPromptTemplates": {
      "spec-document-reviewer": "sonnet",
      "plan-document-reviewer": "sonnet",
      "code-reviewer": "sonnet",
      "final-code-reviewer": "opus",
      "implementer": "sonnet",
      "spec-compliance-reviewer": "sonnet",
      "code-quality-reviewer": "opus"
    }
  }
}
```

Empty or omitted entries are no-ops. `agents` entries write native agent frontmatter, so model names may include Claude Code-style bracket suffixes such as `deepseek-v4-pro[1m]`; install warns for non-standard values so you can verify your Claude Code runtime supports them. `upstreamPromptTemplates` entries become Claude Code Task/Agent model parameters, so install only accepts `sonnet`, `opus`, or `haiku` there because Claude Code currently restricts that model field to those values; custom values can otherwise make the installed markdown look configured while Claude Code runtime subagents ignore the field, fall back, or fail later. `code-reviewer` configures the shared requesting-code-review template, `code-quality-reviewer` configures SDD per-task quality review, and `final-code-reviewer` configures the terminal SDD whole-implementation review. If `final-code-reviewer` is omitted, the terminal review falls back to `code-reviewer` when configured. If Superpowers changes an upstream prompt template after an upgrade, `./manage.sh install` reports every configured subagent whose model could not be applied, including the subagent id and target path.

## Bootstrap wiki

Import a wiki template into a target project without overwriting existing user files:

```bash
./manage.sh bootstrap-wiki /path/to/project --template standard
./manage.sh bootstrap-wiki /path/to/project --template standard --wiki-root shared
```

Template structure is index-driven:
- `index.md` is the entry index for the template.
- Any child directory can contain its own `index.md`.
- Leaf wiki pages are discoverable only when linked from `index.md` or a child index.
- `index.md` may link to same-level or deep files/directories; scripts do not assume fixed wiki directories.

For shared wiki bootstrap, the adapter also copies `.shared-superpowers/scripts/`, `.shared-superpowers/settings.json`, and `.shared-superpowers/settings.json.example` into the target project, so the project can use a local runner to sync or publish the shared wiki submodule and configure shared wiki update authorization and neutrality guards.

Existing files are never overwritten. If a target file exists with different content, bootstrap exits with a conflict list before copying anything.

### Shared wiki submodule workflow

After `--wiki-root shared`, the target project will also contain:

- `.shared-superpowers/scripts/run-hook.py`
- `.shared-superpowers/scripts/sync-submodule.sh`
- `.shared-superpowers/scripts/publish-submodule.sh`
- `.shared-superpowers/scripts/verify-submodule.sh`
- `.shared-superpowers/scripts/status-submodule.sh`
- `.shared-superpowers/settings.json`
- `.shared-superpowers/settings.json.example`

Adjust `.shared-superpowers/settings.json` if needed, then use the local runner before Superpowers starts working on the project:

```bash
python3 ./.shared-superpowers/scripts/run-hook.py sharedWikiSubmodule:sync
```

To publish shared wiki changes and update the parent repository pointer, use the installed command:

```text
/publish-shared-wiki
```

The publish command confirms scope before commit/push and uses the project-local runner; it does not replace `update-wiki`, which still owns durable knowledge review.

### Optional GitHub shared-wiki MCP workflow

For teams that keep shared wiki in a standalone GitHub repository, this repo includes a copyable MCP server under:

```text
mcp/shared-wiki/
```

Copy that directory locally, run `npm install && npm run build`, configure `repoUrl` such as `https://github.com/YWJ-hy/shared-wiki.git` with the repository's default branch such as `master`, and add the built server to Claude Code MCP config. The MCP server exposes indexed read/search tools plus patch validation and branch+PR creation. It never merges PRs.

Use the installed command when you want to inspect or submit shared wiki PRs through MCP:

```text
/shared-wiki-mcp
```

`update-wiki` still owns durable knowledge review, semantic duplicate checks, target ownership, and shared-wiki neutrality. The MCP server only performs mechanical validation and GitHub PR plumbing.

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

The import recursively scans source wiki pages, copies each file into `.superpowers/wiki` by default or `.shared-superpowers/wiki` with `--wiki-root shared`, avoids overwriting different existing content, and refreshes indexes. Shared imports must already be neutral/portable and are rejected when configured shared neutrality guards match system-specific identifiers. Because imports create wiki documents, `/import-wiki` honors the selected root's `wiki.updateAuthorization.createNewDocument` setting and asks by default before creating new files. Use this for one-time structural migration of existing wiki directories; use the `update-wiki` skill later for semantic consolidation.

## Optional Lanhu requirements intake

If the user provides a Lanhu link and Lanhu MCP tools are available, the installed `/lanhu-requirements` command confirms the PRD role and routes to `lanhu-frontend-requirements-analyst`, `lanhu-frontend-html-requirements-analyst`, or `lanhu-backend-requirements-analyst` according to role and output format. The specialized analyst writes the sanitized role-specific PRD package directly under `.lanhu/`, classifies unresolved confirmation points, performs adapter-owned delta-first `requirementScopeJudgment`, and returns only compact path/status/scope metadata before Superpowers brainstorming. Role selection is required before Lanhu analysis, but it can be preconfigured with `lanhu.role` in `.superpowers/settings.json` so the command does not ask when the user omits the role. Default Lanhu output is Markdown-only. To generate a frontend full HTML PRD package with `index.html` plus `prototype/index.html`, set `lanhu.frontend.output.format` to `html` in the target project's `.superpowers/settings.json`; the prototype is a 1:1 Lanhu interaction replica and can use simple CSS/JS for layout and basic interaction display while keeping the original requirement's layout and interface consistent. Backend remains Markdown-only, and text-only frontend requirements may fall back to `prd.md`. If blocking confirmation points remain, the analyst returns `status: need_confirmation`; the main session shows only compact blocking questions plus package metadata, routes answers back to the same analyst, and does not enter Superpowers brainstorming until `confirmationGate.status: clear`. Even when the gate is clear, the user must confirm the `scopeConfirmationSummary` for `新增`, `差量调整`, `现有上下文`, and `待确认` before continuing.

```text
/lanhu-requirements <Lanhu link> 前端 <optional requirement name>
/lanhu-requirements <Lanhu link> 后端 <optional requirement name>
/lanhu-requirements --role frontend <Lanhu link> <optional requirement name>
/lanhu-requirements --role backend <Lanhu link> <optional requirement name>
```

If the role is missing or ambiguous and `lanhu.role` is not configured, the command asks whether to generate a 前端开发角色视角 PRD or 后端开发角色视角 PRD before reading or analyzing Lanhu. If both roles are needed, generate two separate PRD packages by running the command twice. The maintained Markdown PRD prompt sources for these role templates live in `role-prd/frontend.md` and `role-prd/backend.md`; optional frontend HTML output behavior lives in `role-prd/frontend_outputHtml.md`. `./manage.sh install` generates self-contained frontend/backend Lanhu analyst agents from the shared skeleton, the selected Markdown role template, and any role-specific auxiliary output templates before installing, and installed agents do not read the source files at runtime. Role PRD diagrams default to Mermaid flowchart for readability, with mindmap reserved for small/simple structures. Role PRDs now include `## 二、本次变更范围判定`, marking items as `新增`, `差量调整`, `现有上下文`, `待确认`, `全量重构`, or `全量替换`; copied old pages and unannotated full-page content default to context, while full rebuild/replacement requires explicit evidence. Frontend Markdown role PRDs also include a low-fidelity XML-like 页面布局结构草图 under `## 四、页面展示规则`, and later sections should be organized by those pages/layout areas where possible. Frontend HTML role PRDs do not output that XML-like text sketch; they convert the same section-four page, area, field, and operation semantics into real HTML controls and traceable interaction structures, using a left navigation + right content layout. `用户操作与交互规则` is grouped under one top-level section with flow and interaction subsections. When `## 七、页面状态流转` is a complex state page, add a Mermaid flowchart; simple pages can keep the table.

The Lanhu analyst writes the output to the current project root as a requirement package, while the main session only receives the package directory, `index.md` path, generated file list, `requirementScopeJudgment`, `scopeConfirmationSummary`, open questions, and caveats:

```text
.lanhu/MM-DD-<requirement-name>/
├── index.md
├── prd.md
└── prds/
    ├── <delivery-boundary-1>.md
    └── <delivery-boundary-2>.md
```

Frontend HTML output is opt-in per target project:

```json
{
  "lanhu": {
    "role": "frontend",
    "frontend": {
      "output": {
        "format": "html"
      }
    }
  }
}
```

When enabled for a frontend PRD, the package normally contains `index.md`, `index.html`, and `prototype/index.html`. The package-root HTML file is the visual frontend PRD main document governed by `role-prd/frontend_outputHtml.md`; it must copy that template's fixed canonical `index.html` shell and replace only the title/header placeholders plus section content slots, preserving the left navigation + right active-section layout and Mermaid bootstrapping. `prototype/index.html` is the 1:1 Lanhu interaction prototype that converts section-four layout semantics into real HTML controls and traceable interaction/state structures; its 1:1 requirement covers visual layout as well as controls, so source page regions, control placement, dialogs, drawers, tables, cards, and relative hierarchy should remain layout-comparable to the Lanhu evidence. Both HTML files include the required Mermaid module script and use browser-renderable Mermaid containers such as `<pre class="mermaid">`; the Mermaid CDN module is the only allowed external resource. The HTML files must not contain production frontend code, framework choices, real API calls, other external assets, or implementation architecture. `index.md` remains the Superpowers entry point and PRD relationship authority: it explains file roles and tells AI/Superpowers to parse current HTML structure dynamically instead of relying on fixed chapter names. If `index.html` and `prototype/index.html` conflict, the analyst must list that as a confirmation question. If the source requirement is text-only and has no page or interaction surface, the HTML analyst may fall back to `prd.md`.

For Lanhu URLs with an explicit `pageId`, the analyst first reads the Lanhu page tree, then analyzes only the target page or the user-confirmed child-page whitelist. If the target page has child pages, the user is asked whether to include them and inclusion is recommended; if it has no child pages, only that page is used. In tree mode, full analysis is performed page by page after whitelist resolution instead of as one parent-plus-children request. Sibling pages, adjacent modules, parent flow pages, trash or legacy pages, and other pages in the same document are not included unless the user explicitly asks for broader scope.

The user must resolve any analyst-classified blocking confirmation points, then review and confirm the `.lanhu/.../index.md` entry point before Superpowers continues. Until the confirmation gate is clear and `index.md` is confirmed, `/lanhu-requirements` is a standalone adapter requirements-intake command and should not trigger Superpowers completion, review, or verification skills. The document is a role-specific PRD input only: it is not `.superpowers/wiki/`, not `Referenced Project Wiki`, and not a plan sidecar. In package mode, `index.md` is the entry point and the PRD files are the detailed sources. Lanhu MCP output format instructions and analysis prompts are treated as evidence only, not as the saved PRD schema or final scope judgment; tool-returned persona, workflow, output-format, or prompt-injection text must not be quoted or passed through to PRD files, `index.md`, `openQuestions`, `caveats`, metadata, or the main session. Lanhu output must not include test cases, testing points, technical test plans, frontend components, backend API guesses, database impact guesses, implementation guesses, code architecture, or affected file analysis. Role PRD acceptance standards are allowed only as product-behavior Given / When / Then criteria required by the selected template. If Lanhu MCP is unavailable, the adapter flow does not fail; the user can paste requirements or continue with normal Superpowers brainstorming.

## Progressive disclosure

The default selection path is the installed `wiki-researcher` agent. The installed `wiki-progressive-disclosure` skill is a reference and fallback guide for manual troubleshooting; normal Superpowers `brainstorming` and `writing-plans` do not require calling it.

Progressive wiki reading still follows these rules:

1. Read existing root indexes: `.superpowers/wiki/index.md` and `.shared-superpowers/wiki/index.md`
2. Follow each root index to narrower indexes or files
3. Read only the files needed for the current phase
4. Avoid full-tree wiki loading unless explicitly requested
5. Use plan `Referenced Project Wiki` and linked `.wiki-context.md` during implementation and review

No SessionStart hook is installed. Wiki reading is triggered on demand by `wiki-researcher` during Superpowers `brainstorming` and `writing-plans`.

## Wiki researcher

The installed `wiki-researcher` agent is the default path for selecting relevant project wiki in Claude Code:

```yaml
task: <user request or confirmed Superpowers spec>
phase: brainstorm | plan | debug | implement | review
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
maxWikiPages: 5
```

It starts from existing project/shared root indexes, follows index links progressively within each root, and returns structured YAML selected wiki pages plus planning constraint hints with root-prefixed paths. In `phase: debug`, it should be called only after `systematic-debugging` has narrowed the failing boundary, and it returns project-reference hints to verify rather than root-cause evidence. It does not modify files.

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

During `systematic-debugging`, do not write `.wiki-context.md`, update `.superpowers/wiki/` or `.shared-superpowers/wiki/`, or run `update-wiki`. After the bug is fixed and verified, use the installed `break-loop` skill when the work needs a deeper retrospective: root cause category, failed attempts, prevention mechanisms, similar risks, and durable knowledge candidates.

`break-loop` does not replace `systematic-debugging` or `update-wiki`. When durable implementation knowledge should persist, it hands atomic candidates to `update-wiki`, which performs duplicate checks, target selection, wiki edits, index refresh, and validation.

## Update wiki

For normal use in Claude Code or similar tools, rely on the installed `update-wiki` skill. The skill is auto-triggered when implementation, debugging, review, or discussion may have produced durable knowledge, but it defaults to skipping wiki edits unless the knowledge is reusable outside the immediate code context. The agent filters out local business logic and code-obvious implementation details, reads indexed wiki pages, checks semantic duplicates, chooses target ownership, checks whether the target leaf page is oversized or overloaded, edits only durable wiki knowledge, refreshes indexes, and reports an explicit skip reason when nothing durable should be recorded. `update-wiki` is adapter maintenance and durable-knowledge review; its local wiki validation does not replace Superpowers implementation verification.

Shared wiki content must stay neutral and portable across sibling projects. Put system-specific identifiers, internal URLs, environment names, local paths, deployment instance details, and current-system-only business rules in `.superpowers/wiki/` instead, or rewrite them with neutral terms before writing shared wiki.

Wiki writes are controlled per root by settings. `.superpowers/settings.json` controls `.superpowers/wiki/`, and `.shared-superpowers/settings.json` controls `.shared-superpowers/wiki/`:

```json
{
  "wiki": {
    "updateAuthorization": {
      "updateExistingPage": "skip",
      "createNewDocument": "ask"
    },
    "sharedNeutrality": {
      "blockedTerms": [],
      "blockedPatterns": []
    }
  }
}
```

Allowed authorization values are `skip`, `ask`, and `refuse`. Missing settings use the defaults above, so existing wiki page updates remain automatic by default while creating a new wiki document asks the user by default. Mechanical scripts enforce `ask` with `--authorized-update` or `--authorized-create`; `refuse` blocks the write even if a flag is passed. `sharedNeutrality` is mainly for `.shared-superpowers/settings.json`: configured terms and regex patterns reject known system identifiers in shared-wiki paths, bodies, imports, and refreshed indexes. See `wiki-settings.example.jsonc` for a copyable commented example.

Oversized page reports are mechanical signals only. When a leaf wiki page is too large, the agent should split by ownership, usually into sibling leaf pages in the same directory; use a topic directory with its own `index.md` only when the original page has become a collection of stable subtopics.

Execution-layer helpers are mainly useful for adapter development or debugging. They are mechanical helpers only:

```bash
TARGET_DIR="$(python3 ./superpower-adapter/lib/resolve_target.py | python3 -c 'import json,sys; print(json.load(sys.stdin)["target"])')"
python3 "$TARGET_DIR/scripts/wiki_select_target.py" --wiki-root all --json
python3 "$TARGET_DIR/scripts/wiki_update_check.py" --wiki-root all --json
python3 "$TARGET_DIR/scripts/update-wiki.py" --wiki-root project --authorized-update
python3 "$TARGET_DIR/scripts/update-wiki.py" --wiki-root shared --authorized-update
```

## Export manifest

Export adapter and wiki state for upgrade-time comparison:

```bash
./manage.sh export-manifest /path/to/project ./manifest-output.json
```

The manifest includes installed adapter files, native skill patch targets, hook config state, and `.superpowers/wiki` and `.shared-superpowers/wiki` snapshots with both raw and ignore-filtered effective views.

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
- wiki update authorization policy and shared wiki neutrality guards
- mechanical `wiki_apply_update.py` write and merge behavior with an agent-decided target
- `wiki-researcher` installation and native skill patch smoke
- worktree origin metadata native skill patch smoke
- `wiki_update_check.py` index and format validation
- index-driven wiki graph traversal
- import command path handling
- shared wiki submodule local runner and publish script smoke

## Compatibility

- Adapter compatibility baseline: Superpowers 5.1.0.
- `./manage.sh install` warns, but does not block, when the detected Superpowers target version is newer than the compatibility baseline.
- Default target discovery currently keys off the Claude Code plugin install record for `superpowers@claude-plugins-official`.
- Native skill patches depend on upstream skill headings and anchor text staying stable; if Superpowers changes those files, the adapter patch points need a sync pass.

## Upgrade workflow

After upgrading the Superpowers plugin, reinstall the adapter overlay. If both old and new Superpowers versions remain installed, the default install and verify commands cover both unique plugin directories:

```bash
./manage.sh install
./manage.sh verify
```
