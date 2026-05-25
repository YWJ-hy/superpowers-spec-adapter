# superpower-adapter

This adapter keeps Superpowers as the primary workflow framework and adds a replayable overlay for project wiki pages under `.superpowers/wiki/` and shared wiki pages under `.shared-superpowers/wiki/`.

Chinese user flow guide: [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)
Chinese adapter development guide: [`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)
Chinese integration guide: [`ADAPTER_INTEGRATION_CN.md`](./ADAPTER_INTEGRATION_CN.md)
Chinese quickstart guide: [`QUICKSTART_CN.md`](./QUICKSTART_CN.md)

## Purpose

- Store project wiki pages in `.superpowers/wiki/` and optional neutral/portable shared wiki pages in `.shared-superpowers/wiki/` or a GitHub-backed shared-wiki repository accessed through the copyable MCP server
- Use `index.md` as the entry point
- Optionally turn Lanhu links into confirmed frontend/backend original-requirement evidence packages under `.lanhu/MM-DD-<requirement-name>/` before Superpowers brainstorming, with `index.md` as the entrypoint and relationship map; Lanhu images are analyzed selectively by evidence signal and are not saved as `.lanhu/` assets by default
- Load wiki details progressively instead of reading the full tree
- Install `agents/wiki-researcher.md` to select relevant project wiki pages progressively
- Patch Superpowers `brainstorming` so designs can see lightweight project wiki context and, when the user points to an existing confirmed `.lanhu/.../index.md` package, read that package as requirements input from its entrypoint instead of regenerating Lanhu output
- Patch Superpowers `writing-plans` so plans link lightweight `Referenced Project Wiki` entries to detailed schemaVersion 3 `.wiki-context.json` constraints with page-level bounded `documentContext` and nested sections
- Patch Superpowers `systematic-debugging` so it may conditionally use `wiki-researcher` after evidence narrows the suspected project contract or component, without making wiki lookup a default prerequisite
- Let implementation and review consume plan `Referenced Project Wiki` and mechanically rendered `.wiki-context.json` constraints instead of reselecting wiki pages at execution time
- Patch Superpowers `using-git-worktrees` and `finishing-a-development-branch` so worktree tasks can merge back to the branch that created them
- Keep standalone adapter skills such as `import-wiki`, `init-wiki`, and `lanhu-requirements` outside Superpowers completion/review/verification skills until they explicitly hand off to the next Superpowers workflow step
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

### Build a Multica runtime bundle

Multica can consume this adapter as a generated Superpowers-compatible runtime bundle instead of requiring the user to install the Claude Code Superpowers plugin locally:

```bash
./manage.sh build-multica-runtime /path/to/superpowers . ./dist/multica-superpowers-runtime
./manage.sh verify-multica-runtime ./dist/multica-superpowers-runtime
./manage.sh install-multica-runtime ./dist/multica-superpowers-runtime --dry-run
```

The generated bundle includes patched Superpowers-compatible workflow definitions, Multica role agents, gates, triggers, schemas, MCP examples, issue templates, preflight contracts, an explicit SDD task graph, and the adapter tool layer under `dist/tools/scripts/`. Adapter Python scripts remain Multica tool-runner internals; user entrypoints are Multica workflows, issue templates, quick actions, natural-language routing, or compatibility commands. Trigger artifacts now include machine-readable `issue-template-bindings.json` and `artifact-next-actions.json`, so issue templates and artifact-driven next actions are checked as WorkflowInvocation contracts rather than plain markdown placeholders. The generated validators `artifact_next_action_suggest.py` and `intent_router_suggest.py` can read artifact/gate state or natural-language requests and emit gate-aware next-action/workflow suggestions without auto-executing them. `workflow_invocation_validate.py` also distinguishes the required MCP client capability from concrete optional MCP servers, so Lanhu/shared-wiki/GitHub MCP availability only blocks workflows that depend on those servers. Gate artifacts include `gate-contracts.json`, `gate-transition-contract.json`, `gate_state_validate.py`, `gate_transition_validate.py`, and a concrete `gate-state.schema.json`, so approval/authorization gates declare owner roles, required artifacts, satisfied-by conditions, allowed status transitions, owner/orchestrator advancement rules, evidence requirements, and external side-effect boundaries. Role artifacts include `role-agent-contracts.json` and `role_task_validate.py`, and schema artifacts include `artifact-contracts.json` plus concrete spec/plan/Lanhu/update-wiki/review schemas, so role I/O, fresh-context task dispatch, source artifact injection, declared output boundaries, tool/capability boundaries, and artifact producers/consumers are checked as runtime contracts. Artifact persistence is also declared through `dist/preflight/artifact-store-contract.json` and `artifact_store_validate.py`, which define the `artifacts/superpowers/{workflowId}/{runId}/{artifactType}/{name}` path shape, status enum, SHA-256 checksum requirements for approved/current artifacts, and read/write policy boundaries. `verify-multica-runtime` checks expected runtime artifacts, source snapshots, tool-manifest/script consistency, runtime-root replacement, generated gate/trigger/schema contracts, trigger catalogs, role/artifact/store contracts, offline preflight validators, and task graph contracts before the bundle is treated as releasable. `install-multica-runtime` is the Phase 2 registration planner: it reruns the local verifier, checks Multica CLI/auth/daemon/runtime status, probes commands with exact help-output matching, then implements the runtime layer on documented Multica surfaces. When exact native runtime commands are absent, `--require-native-surfaces` is satisfied by executable substitutes: it creates a runtime registration issue, stores WorkflowInvocation/gate/schema/runtime state through issue metadata, attaches runtime contract artifacts through issue comments/attachments, uses issue assign/rerun plus issue get/run history for role-task dispatch and observation, and records autopilot schedule/webhook triggers as the trigger substitute. It defaults to dry-run; `--apply` is externally visible and only executes documented Multica CLI commands.

### Bootstrap a real Multica workspace flow

To exercise the real Multica execution surface, use `multica-bootstrap` for compatibility smoke/skill-pack setup, then use `multica-live-acceptance` for the product-level visual flow. `multica-bootstrap` prepares the workspace skill pack, imports it into Multica when `--apply` is used, and can still create a single smoke/template issue. Full Superpowers+adapter acceptance is not satisfied by one orchestrator issue: the visual flow must create stage issues assigned to `superpowers-*` role agents or `superpowers-runtime-squad`, so Multica UI/CLI shows independent runs for wiki research, brainstorming, planning, implementation, reviews, debugging, and wiki publishing readiness.

Dry-run first:

```bash
./manage.sh multica-bootstrap \
  --superpowers-source /path/to/superpowers \
  --target-repo /path/to/project \
  --skill-pack-dir ./dist/multica-skill-pack \
  --dry-run
```

The default `--issue-template smoke` is intentionally read-only: it asks the agent to confirm the target repo, skill pack visibility, and project/shared wiki roots, then post a Multica issue comment. Other templates create real Multica issue bodies for the Superpowers+adapter flow while keeping execution in the Multica daemon + Claude Code task path:

| Template | Entrypoint | Required input |
|---|---|---|
| `smoke` | root skill pack smoke | `--target-repo` |
| `lanhu-intake` | `skills/lanhu-requirements/SKILL.md` | `--lanhu-url` or `--requirements-path` |
| `brainstorming` | `upstream-superpowers/brainstorming.md` | target repo and optional requirements/spec |
| `writing-plans` | `upstream-superpowers/writing-plans.md` | `--spec-path` or `--requirements-path` |
| `execute-plan` | `upstream-superpowers/executing-plans.md` | `--plan-path` |
| `sdd-execution` | `upstream-superpowers/subagent-driven-development.md` | `--plan-path` |
| `systematic-debugging` | `upstream-superpowers/systematic-debugging.md` | `--debug-evidence` or `--requirements-path` |
| `break-loop` | `skills/break-loop/SKILL.md` | `--debug-evidence` |
| `update-wiki` | `skills/update-wiki/SKILL.md` | `--plan-path` or `--requirements-path` |
| `publish-shared-wiki` | `skills/publish-shared-wiki/SKILL.md` | `--shared-wiki-topic` |
| `shared-wiki-mcp-pr` | `skills/shared-wiki-mcp/SKILL.md` | `--shared-wiki-topic` |

Example issue-only dry-run:

```bash
./manage.sh multica-bootstrap create-issue \
  --target-repo /path/to/project \
  --issue-template writing-plans \
  --requirements-path /path/to/project/docs/prd.md \
  --dry-run
```

After `multica auth status`, `multica daemon status`, and `multica runtime list` show a Claude Code runtime, run `multica-bootstrap --apply` only when you need to import/update the workspace skill pack or run the read-only compatibility smoke:

```bash
./manage.sh multica-bootstrap \
  --superpowers-source /path/to/superpowers \
  --target-repo /path/to/project \
  --issue-template smoke \
  --apply
```

`--apply` can create/import skills, create/update agents, create issues, and assign issues, so it is externally visible. The bootstrap command itself never commits, pushes, opens PRs, publishes shared wiki changes, or calls undocumented Multica APIs. Publishing/PR templates include an authorization gate unless `--allow-external-side-effects` is explicitly passed, and even then the issue body only records that authorization for the Multica agent task. If the installed Multica CLI does not expose non-interactive local skill import or skill attach flags, the command reports the exact manual step instead of guessing an undocumented API.

For live acceptance, `multica-live-acceptance` plans or creates the A-H visual chains from `MULTICA_VISUAL_ACCEPTANCE_MATRIX_CN.md`. It defaults to dry-run. With `--apply`, it directly creates Multica stage issues and assigns each stage to the mapped role agent/squad, including spec document review, plan document review, implementation review, and finishing roles; it rejects `superpowers-adapter-orchestrator` because that adapter-specific single-agent path has been removed:

```bash
./manage.sh multica-live-acceptance \
  --target-repo /path/to/disposable/project \
  --case chain-a \
  --requirements-path /path/to/disposable/project/docs/prd.md \
  --plan-path /path/to/disposable/project/.superpowers/plans/feature.md \
  --wiki-context-path /path/to/disposable/project/.superpowers/plans/feature.wiki-context.json \
  --observe-runs \
  --dry-run
```

Key visual chains:

| Chain | Purpose |
|---|---|
| `chain-a` | Wiki-aware feature development: wiki research → brainstorming → spec review → planning → plan review → implementation → reviews → finishing → update-wiki |
| `chain-b` | Lanhu intake → Superpowers downstream roles, including document review and finishing |
| `chain-c` | Multi-turn brainstorming → spec document review → planning → plan document review |
| `chain-d` | SDD plan review, implementer/reviewer loop, final review, and finishing visibility |
| `chain-e` | Systematic debugging → break-loop → update-wiki |
| `chain-f` | Shared wiki local readiness without publish/PR side effects |
| `chain-g` | Direct role-agent and squad dispatch |
| `chain-h` | Blocked/comment/rerun/cancel recovery lifecycle |
| `all` | Full A-H visual acceptance |


### Optional subagent model configuration

By default, `adapter.config.json` is `{}` and the adapter does not change subagent model routing. Adapter agents keep `model: inherit`, and upstream Superpowers prompt templates keep their native `Task tool (general-purpose)` shape.

To pin models, copy the relevant entries from `adapter.config.example.jsonc` into `adapter.config.json` as standard JSON without comments:

```json
{
  "subagentModels": {
    "agents": {
      "wiki-researcher": "sonnet",
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

To publish shared wiki changes and update the parent repository pointer, use the installed `publish-shared-wiki` skill:

```text
publish-shared-wiki skill
```

The `publish-shared-wiki` skill confirms scope before commit/push and uses the project-local runner; it does not replace `update-wiki`, which still owns durable knowledge review.

### Optional GitHub shared-wiki MCP workflow

For teams that keep shared wiki in a standalone GitHub repository, this repo includes a copyable MCP server under:

```text
mcp/shared-wiki/
```

Copy that directory locally, run `npm install && npm run build`, configure `repoUrl` such as `https://github.com/YWJ-hy/shared-wiki.git` with the repository's default branch such as `master`, and add the built server to Claude Code MCP config. The MCP server exposes indexed read/search tools plus patch validation and branch+PR creation. It never merges PRs. Normal brainstorming, planning, and narrowed debugging still use `wiki-researcher` as the unified progressive disclosure path; when the MCP server is configured, it can serve as `wiki-researcher`'s GitHub-backed shared wiki source.

Use the installed `shared-wiki-mcp` skill when you explicitly want to inspect or submit shared wiki PRs through MCP:

```text
shared-wiki-mcp skill
```

`update-wiki` still owns durable knowledge review, semantic duplicate checks, target ownership, and shared-wiki neutrality. The MCP server only performs indexed read/search, mechanical validation, and GitHub PR plumbing. Plan `.wiki-context.json` files should record MCP-sourced shared wiki pages with source metadata, `wikiPath`, and revision because `.shared-superpowers/wiki/<path>.md` is only a logical display path in that mode.

## Initialize starter wiki knowledge

After bootstrapping the directory structure, use `init-wiki` skill in Claude Code to initialize first-pass wiki content from a mechanical project inventory. The script behind this skill reports languages, stack signals, top directories, sample files, and indexed wiki pages; the agent decides whether to write lightweight starter notes.

```bash
./manage.sh init-wiki /path/to/project
./manage.sh init-wiki /path/to/project "payments and order workflow"
```

Use this only to help the user initialize wiki knowledge. During ongoing development, let the `update-wiki` skill review whether durable knowledge should be written.

## Import existing wiki

For normal use in Claude Code or similar tools, use the installed `import-wiki` skill:

```text
import-wiki skill path/to/original-wiki-dir
import-wiki skill path/to/original-wiki-dir --target imported
```

The import recursively scans source wiki pages, copies each file into `.superpowers/wiki` by default or `.shared-superpowers/wiki` with `--wiki-root shared`, avoids overwriting different existing content, and refreshes indexes. Shared imports must already be neutral/portable and are rejected when configured shared neutrality guards match system-specific identifiers. Because imports create wiki documents, `import-wiki` skill honors the selected root's `wiki.updateAuthorization.createNewDocument` setting and asks by default before creating new files. Use this for one-time structural migration of existing wiki directories; use the `update-wiki` skill later for semantic consolidation.

### Migrating wiki to section-marker format

Use `migrate-wiki` skill in Claude Code to migrate existing wiki documents to the two-layer index structure with `<!-- wiki-section:xxx -->` markers. The AI agent analyzes each document semantically, identifies independent constraint units, inserts section markers, and generates per-document `<stem>.index.md` companion files that include a document-level overview plus a section table.

The mechanical helper is also available via CLI:

```bash
./manage.sh migrate-wiki-sections --inventory /path/to/project --wiki-root all
./manage.sh migrate-wiki-sections --validate /path/to/project --wiki-root project
./manage.sh migrate-wiki-sections --generate-indexes /path/to/project --wiki-root project
```

Documents without a companion `<stem>.index.md` are invisible to `wiki-researcher`, so every leaf wiki page should be migrated, including short or single-topic pages. Migration is required for wiki constraints to participate in the planning and execution flow. The companion index also supplies bounded `documentContext` so selected sections keep their page-level subject/scope without injecting sibling sections or the full page body.

## Optional Lanhu requirements intake

If the user provides a Lanhu link and Lanhu MCP tools are available, the installed `lanhu-requirements` skill confirms the evidence role and determines the matching `lanhu-frontend-requirements-analyst`, `lanhu-frontend-html-requirements-analyst`, or `lanhu-backend-requirements-analyst` according to role and output format.

The generated `.lanhu/` package is a **Lanhu original-requirement evidence package**, not a Superpowers spec. It preserves source-derived requirement facts, UI layout/control/interaction evidence, state/prompt facts, permission/visibility facts, and open questions. Superpowers uses it as requirements input and remains responsible for final spec structure, acceptance criteria, test strategy, technical solution, and implementation tasks.

Lanhu images, screenshots, and `designInfo.images` are candidate evidence only. Analysts use selective image analysis: they directly analyze an image region only when scoped evidence has a signal such as an annotation, arrow, nearby source text, user request, missing key UI fact, or layout ambiguity. By default the package stores structured source facts, caveats, and confirmation questions rather than image files; it does not write remote image references, base64 images, `.lanhu/.../assets/`, or `.lanhu/.../images/` unless the user explicitly asks for image preservation or confirms an offline-audit need.

For explicit `pageId` links, the URL is treated as `rootScopeUrl` and the current page as `rootPageId`, not necessarily as the final target page. The main session first uses only lightweight page tree metadata from `lanhu_get_prd_page_scope`, combines that tree with the user's description to select `selectedTargetPages`, and does not call `lanhu_get_prd_scoped_evidence` before dispatch. Each selected page is routed to exactly one specialized analyst with `childPagePolicy: exclude`; that analyst uses the fixed scoped Lanhu MCP sequence (`lanhu_resolve_invite_link` when needed, `lanhu_get_prd_page_scope`, then `lanhu_get_prd_scoped_evidence` with `scope_policy: pageid_children_only`, `include_child_pages: false`, `confirmed_child_page_ids: []`, and `output_mode: evidence_only`) for its own page only.

Role selection is required before Lanhu analysis, but it can be preconfigured with `lanhu.role` in `.superpowers/settings.json`. Default Lanhu output is Markdown-only. To generate a frontend HTML evidence package with `index.html` plus `prototype/index.html`, set `lanhu.frontend.output.format` to `html` in the target project's `.superpowers/settings.json`. Backend remains Markdown-only, and text-only frontend requirements may fall back to `prd.md`.

```text
lanhu-requirements skill <Lanhu link> 前端 <optional requirement name>
lanhu-requirements skill <Lanhu link> 后端 <optional requirement name>
lanhu-requirements skill --role frontend <Lanhu link> <optional requirement name>
lanhu-requirements skill --role backend <Lanhu link> <optional requirement name>
```

If the role is missing or ambiguous and `lanhu.role` is not configured, the skill asks whether to generate a 前端 Lanhu 原始需求证据包 or 后端相关 Lanhu 原始需求证据包 before reading or analyzing Lanhu. If both roles are needed, generate two separate evidence packages by running the skill twice.

Maintained source templates live in `role-prd/frontend.md`, `role-prd/backend.md`, and `role-prd/frontend_outputHtml.md`. These templates define fixed PRD evidence package structures and must-cover dimensions; AI may customize content organization and wording inside that structure, but must not change the package structure, section responsibilities, artifact boundaries, or the input shape that later Superpowers steps depend on. `./manage.sh install` generates self-contained Lanhu analyst agents from the shared skeleton and selected role template before installing; installed agents do not read the source files at runtime.

Frontend Markdown evidence packages preserve a low-fidelity XML-like 1:1 original-requirement UI structure for agent/Superpowers consumption. Frontend HTML evidence packages use `index.html` as an evidence reader and `prototype/index.html` as the 1:1 Lanhu original-requirement UI replica for the selected/evidenced requirement range. The prototype uses real HTML controls and should preserve source page regions, control placement, dialogs, drawers, tables, cards, and relative hierarchy, but it does not expand every returned screenshot into a full visual reconstruction by default. Because the HTML prototype contains real controls, the HTML evidence tables should not duplicate prose such as “UI 控件类型”. The prototype may use only simple CSS/JS for reading, review, navigation, basic visibility, and state visualization; concrete interaction flows belong in `index.html` as source facts, not in production logic or workflow implementation.

All explicit Lanhu original-requirement facts must be preserved. If a source fact does not fit fixed template themes, the analyst may create concrete AI-defined source fact sections such as `计费规则源事实`, `消息通知源事实`, `导入导出源事实`, `通知规则源事实`, or `结算规则源事实`; it must not drop the fact, weaken it into an untraceable summary, or force it into a generic “other/misc” bucket.

For URL-rooted selection that resolves to multiple Lanhu target pages, page fan-out is only an evidence-fidelity strategy. The selected role-and-format analyst is called once per selected page and writes a complete page package under `.lanhu/MM-DD-<requirement-name>/pages/<page-slug>/`. The aggregate package root keeps only a global `index.md` for page package listing, reading order, cross-page relationships, root tree selection summary, selectedTargetPages, aggregated scope summary, and confirmation status. Compact page metadata, `.yaml`, or summary Markdown are not evidence sources and must not be expanded into final HTML by the main session.

The user must resolve any analyst-classified blocking confirmation points, then review and confirm the `.lanhu/.../index.md` entry point before Superpowers continues. Until the confirmation gate is clear and `index.md` is confirmed, `lanhu-requirements` skill is a standalone adapter requirements-intake skill and should not trigger Superpowers completion, review, or verification skills. Missing implementation field names or technical data mappings are non-blocking implementation follow-up unless the product-level field/control meaning or behavior is unclear.

Lanhu output must not include final acceptance criteria, Given/When/Then, test cases, testing points, technical test plans, frontend components, backend API guesses, backend request/response field design, database column design, database impact guesses, implementation guesses, code architecture, affected file analysis, frontend/backend boundary inference, exception/risk inference, or Superpowers plan tasks. If Lanhu MCP is unavailable, the adapter flow does not fail; the user can paste requirements or continue with normal Superpowers brainstorming.

## Progressive disclosure

The default selection path is the installed `wiki-researcher` agent. The installed `wiki-progressive-disclosure` skill is a reference and fallback guide for manual troubleshooting; normal Superpowers `brainstorming` and `writing-plans` do not require calling it.

Progressive wiki reading still follows these rules:

1. Read existing root indexes: `.superpowers/wiki/index.md` and `.shared-superpowers/wiki/index.md`
2. Follow each root index to narrower indexes or per-document section indexes
3. During brainstorming, stay index-only and do not read section full text
4. During planning, read only candidate section full text and write schemaVersion 3 `.wiki-context.json` with one bounded `documentContext` per wiki page and nested selected sections
5. During implementation and review, use plan `Referenced Project Wiki` and render task/role-specific constraints from linked `.wiki-context.json`; hard-constraint rereads inject document context plus the selected section body only
6. Avoid full-tree wiki loading unless explicitly requested, and do not inject sibling sections or full pages just to recover section context

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
docs/superpowers/plans/<plan-stem>.wiki-context.json
```

Implementation and review consume this plan section and linked sidecar context instead of reselecting wiki pages from scratch. The sidecar is schemaVersion 3 JSON with page-rooted `wikiPages`, one bounded `documentContext` from `<stem>.index.md` per page, nested `sections`, and categorized implementation/test/review/general constraints. Use `wiki_context_render.py` to render task/role-specific constraint blocks; forced hard-constraint rereads use the page context with the selected section body, not sibling sections or whole pages.


## Worktree origin tracking

The adapter also patches Superpowers `using-git-worktrees` and `finishing-a-development-branch`. When a new linked worktree is created, the source branch, source worktree, and source HEAD are recorded as transient metadata in the new worktree's private git-dir under `superpower-adapter/worktree-origin.json`.

That metadata is not written to `plan.md`, `spec.md`, `.superpowers/`, or the repository working tree. At finishing time, Superpowers can offer an explicit option to merge the feature branch back into the original branch from the original worktree, which is safer for nested feature work and multiple concurrent sessions.

## Break the bug loop

For bugs, keep Superpowers `systematic-debugging` as the fix workflow. The adapter patch does not make wiki lookup an upfront debugging prerequisite: complete Phase 1 first, narrow the failing boundary with evidence, then use `wiki-researcher` only when a project-specific contract, known gotcha, cross-layer boundary, or workflow convention may clarify what to verify.

Debug wiki lookup uses `phase: debug` and should stay small, normally `maxWikiPages: 2`. If the bug happens while executing a Superpowers plan, read that plan's `Referenced Project Wiki` and linked `.wiki-context.json` first instead of reselecting wiki pages; without a current plan context, do not search old plans by default. Missing or irrelevant wiki does not block debugging, and wiki context is not root-cause evidence. Verify every wiki-derived idea against code, logs, tests, reproduction steps, or diagnostics.

During `systematic-debugging`, do not write `.wiki-context.json`, update `.superpowers/wiki/` or `.shared-superpowers/wiki/`, or run `update-wiki`. After the bug is fixed and verified, use the installed `break-loop` skill when the work needs a deeper retrospective: root cause category, failed attempts, prevention mechanisms, similar risks, and durable knowledge candidates.

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
- import skill path handling
- shared wiki submodule local runner and publish script smoke
- Multica runtime bundle build/verify smoke, including tool manifest, source snapshot, and generated trigger/schema contract checks
- Multica bootstrap dry-run smoke, including workspace skill pack generation, planned real CLI commands, issue template bodies, and required-input failures

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
