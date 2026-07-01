#!/usr/bin/env python3
"""Patch or verify Superpowers native skills for superpower-adapter wiki disclosure."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

START_PREFIX = '<!-- superpower-adapter:native-skill:'
END_PREFIX = '<!-- /superpower-adapter:native-skill:'


@dataclass(frozen=True)
class PatchSpec:
    skill: str
    anchor: str
    block_id: str
    content: str
    legacy_block_ids: tuple[str, ...] = ()
    fallback_anchors: tuple[str, ...] = ()

    @property
    def relative_path(self) -> Path:
        return Path('skills') / self.skill / 'SKILL.md'

    @property
    def start_marker(self) -> str:
        return f'{START_PREFIX}{self.block_id} -->'

    @property
    def end_marker(self) -> str:
        return f'{END_PREFIX}{self.block_id} -->'

    def rendered_block(self, target: Path) -> str:
        plugin_root = target.as_posix()
        body = self.content.replace('__SUPERPOWER_ADAPTER_PLUGIN_ROOT__', plugin_root)
        return f'{self.start_marker}\n{body.rstrip()}\n{self.end_marker}\n'


# Shared injected-prompt fragments: wording that must stay identical across more
# than one native-skill patch is defined once here so the copies cannot drift.
# (Only one of the executing-plans / SDD variants is injected per session, so
# extracting these is a maintenance guard against divergence, not a token change.)

# update-wiki keep-or-skip determination — identical across executing-plans,
# subagent-driven-development, and finishing-a-development-branch.
_UPDATE_WIKI_DETERMINATION = (
    'Reach this by actually invoking the skill so its judgment framework applies — do not '
    'pre-decide in the main loop that nothing is durable and bypass the skill. Do not treat an '
    'empty or absent candidates sidecar as proof there is nothing to record: candidate absence is '
    'not conclusive, because the skill also weighs the implemented changes and conversation '
    "context, not just the candidates sidecar. Skipping is a valid outcome, but only as the "
    "skill's own conclusion stated with an explicit reason, never as a reason to avoid invoking it."
)


def _preflight_fail(stop_before: str, deciders: str, mode: str) -> str:
    """Preflight-failure recovery; identical across executing-plans and SDD bar three words."""
    return (
        f'If the preflight fails because task text changed after plan review, stop before {stop_before} '
        'and refresh the binding on the planning side: confirm the selected wiki routing still applies to '
        'the changed task, then re-run `wiki_context_render.py <sidecar> --bind-fingerprints --strict '
        '--execution-ready --plan-path <plan>` to re-stamp fingerprints, and resume only after the preflight '
        'passes. Do not re-stamp to silence a mismatch without re-checking routing, reselect wiki pages, call '
        f'`wiki-researcher`, rewrite the plan, filter by task string, or let {deciders} decide routing during {mode}.'
    )


def _source_truth_task_lint(mode: str, reminder_when: str, reminder_target: str,
                            lint_when: str, task_ref: str, reviewer_note: str) -> str:
    """Post-task sourceOfTruth changed-path lint section; identical across executing-plans and SDD
    except the framing words (which phase, which prompt, which task, optional reviewer note)."""
    return f'''### Adapter Source-of-Truth Task Lint

Source-of-truth {mode} enforcement is post-task changed-path lint, not task-scoped constraint rendering. Before {reminder_when}, you may render the short execution reminder and include it in {reminder_target} only when stdout is non-empty:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/source_truth_settings.py <repo-root> --render-prompt execution-reminder
```

{lint_when}, lint the actual changed paths touched by {task_ref} against configured sourceOfTruth policy:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/source_truth_settings.py <repo-root> --lint-changed --changed-path <repo-relative-path> --format json
```

Use repeated `--changed-path` values or `--changed-paths-file` for the real changed-file list from git diff/tool context. If the user explicitly authorized a `truth/edit: ask` edit, pass that exact repo-relative path with `--authorized-truth-edit`; this authorization never bypasses `truth/edit: never`. If lint returns `block`, do not complete the task until the protected truth edit is reverted or routed through the upstream truth-source process. If lint returns `ask`, obtain explicit user authorization or revert before completion. `evidence` findings are warnings only.{reviewer_note} Do not use any sourceOfTruth renderer or sourceOfTruth sidecar flow.'''


PATCHES = [
    PatchSpec(
        skill='using-superpowers',
        # Superpowers 6.1.0 compressed the bootstrap and folded the standalone
        # "## Instruction Priority" section into "## User Instructions", so anchor there now.
        # Keep the old heading as a fallback for pre-6.1.0 Superpowers that still ship it.
        anchor='## User Instructions\n',
        fallback_anchors=('## Instruction Priority\n',),
        block_id='using-superpowers-adapter-workflow-boundary',
        content='''
## Adapter Workflow Boundary

Generated by superpower-adapter.

Standalone adapter skills have their own local workflow boundary: `init-wiki`, `import-wiki`, `migrate-wiki`, `lanhu-requirements`, `shared-wiki-mcp`, `publish-shared-wiki`, and `update-wiki` are adapter utilities only.

When one completes: Do not automatically invoke Superpowers planning, implementation, review, completion, or verification skills, and do not invoke `superpowers:verification-before-completion` or similar completion checks solely because the adapter skill ran. `publish-shared-wiki` still requires explicit confirmation of the commit/push scope before publishing.

This boundary does not apply to normal Superpowers development workflows such as `brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, or `systematic-debugging`; those keep their native Superpowers gates and may use adapter wiki/source context when patched instructions say so.
''',
    ),
    PatchSpec(
        skill='brainstorming',
        anchor='## The Process\n',
        block_id='brainstorming-wiki-disclosure',
        legacy_block_ids=('brainstorming-spec-disclosure',),
        content='''
#### Adapter Project Wiki Disclosure and Optional Requirements Inputs

Generated by superpower-adapter.

**Sequence gate — do not emit any candidate approach until you have called `wiki-researcher` (phase: brainstorm).** Fixed order: (1) explore project context exactly as this skill's process directs; (2) only then, before proposing approaches, call `wiki-researcher` with `phase: brainstorm` (it consumes what the exploration surfaced as its `task`/`focus`); it must not run before that native exploration step or replace it. If you reach drafting approaches without having called it, stop and call it now — having read a lot of code is not a reason to skip. The only exception: no project/shared wiki applies (none exists, MCP unavailable, or root indexes missing) — record that one-line N/A reason and continue.

After exploring project context and before proposing approaches, use the `wiki-researcher` agent to select relevant project/shared wiki context:

```yaml
task: <user request and current understanding>
phase: brainstorm
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
sharedWikiSource: auto
focus: <module, workflow, or concern if known>
```

Use the result as lightweight `Adapter Project Wiki Context` while designing the Superpowers spec. Wiki selection is strict and progressive: read indexes and companion section indexes first, select relevant sections only, and do not scan whole wiki trees without an explicit audit request. For `source: github_mcp`, treat `.shared-superpowers/wiki/<path>.md` as a logical display path, not a local file path. Do not block brainstorming if no relevant wiki exists, MCP is unavailable, or root indexes are missing; mention the caveat and continue. Do not write sidecar JSONL, `.wiki-selection.json`, or `.wiki-context.json` during brainstorming.

Do not run Lanhu intake inside `brainstorming`. If the user gives a Lanhu URL, invite link, or asks for Lanhu, pause and have them run the explicit skill first — `lanhu-requirements skill <Lanhu link> frontend|backend <optional requirement name>` — and continue only after they confirm the generated `.lanhu/.../index.md` package. If they point to an already confirmed `.lanhu/.../index.md` package, read that `index.md` first and follow only the files it lists. Use the package as Superpowers requirements input only: do not regenerate Lanhu output, do not call Lanhu MCP by default, and do not copy Lanhu content into project/shared wiki, plan sidecars, final acceptance criteria, test plans, technical solution, or implementation tasks. Lanhu MCP is optional — the user can paste requirements or continue with normal Superpowers brainstorming instead.

Before proposing approaches, render the configured source-of-truth spec policy with the installed plugin-root script:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/source_truth_settings.py <repo-root> --render-prompt spec-pre
```

If stdout is non-empty, include it as a short `Adapter Source-of-Truth Policy` prompt input while drafting the spec. If stdout is empty, sourceOfTruth is unconfigured; skip silently and do not add not-configured noise to the spec.
''',
    ),
    PatchSpec(
        skill='brainstorming',
        anchor='## After the Design\n',
        block_id='brainstorming-gitignored-spec-commit-policy',
        content='''
### Adapter Spec Commit Policy (gitignore-aware)

Generated by superpower-adapter.

Before committing the spec, check whether its path is git-ignored:

```bash
git check-ignore -q docs/superpowers/specs/<file>.md
```

- Exit `0` (ignored): Do not commit, and never `git add -f`. Replace the native "Spec written and committed to `<path>`" line: the spec was written but not committed because `.gitignore` excludes it, so the user must handle version control themselves to keep it. Then ask them to review before the plan.
- Exit non-zero (not ignored): Commit and announce per native behavior.
''',
    ),
    PatchSpec(
        skill='systematic-debugging',
        anchor='### Phase 2: Pattern Analysis\n',
        block_id='systematic-debugging-conditional-wiki-research',
        content='''
#### Adapter Conditional Project Wiki Research

Generated by superpower-adapter.

Do not call `wiki-researcher` at the start of debugging. Complete Phase 1 first: reproduce or otherwise evidence the failure, read the full error, inspect relevant logs/traces, check recent changes, and narrow the failing boundary.

After that evidence narrows the investigation to a specific component, file set, contract, workflow, or project convention, you may call `wiki-researcher` with `phase: debug` for a small targeted lookup when project-specific wiki could clarify a suspected contract, known gotcha, architectural boundary, or working pattern:

```yaml
task: <bug symptom, expected/actual behavior, and evidence gathered so far>
phase: debug
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
sharedWikiSource: auto
focus: <narrow suspected component, contract, workflow, or gotcha>
changedFiles:
  - <optional files already implicated by evidence>
```

Wiki context is only bounded project reference. Verify every wiki-derived idea against code, logs, tests, reproduction steps, or diagnostics before proposing a fix. If the bug is happening while executing a Superpowers plan, prefer that plan's `Referenced Project Wiki` and linked `.wiki-context.json` instead of reselecting wiki pages.

If no relevant wiki is available, continue systematic debugging without broad retries or requiring wiki initialization. During `systematic-debugging`, do not write `.wiki-context.json`, do not update `.superpowers/wiki/` or `.shared-superpowers/wiki/`, and do not run `update-wiki`. After the bug is fixed and verified, use `break-loop` when a retrospective is warranted; `break-loop` may hand durable candidates to `update-wiki`.
''',
    ),
    PatchSpec(
        skill='writing-plans',
        anchor='## File Structure\n',
        block_id='writing-plans-planning-gate',
        content='''
## Adapter Referenced Project Wiki

Generated by superpower-adapter.

Before decomposing tasks, use the `wiki-researcher` agent to formally select existing project/shared wiki sections that constrain this implementation plan. Project wiki is local `.superpowers/wiki/`; shared wiki may come from local `.shared-superpowers/wiki/` or a configured GitHub-backed shared-wiki MCP source:

```yaml
task: <confirmed Superpowers spec or requirements summary>
phase: plan
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
sharedWikiSource: auto
planPath: docs/superpowers/plans/<filename>.md
planSummary: <plan goal and likely task areas>
selectionOutputPath: docs/superpowers/plans/<plan-stem>.wiki-selection.json
```

`wiki-researcher` selects candidate pages and sections only. At plan phase it writes the JSON *selection* object (shape in `__SUPERPOWER_ADAPTER_PLUGIN_ROOT__/contracts/wiki-selection-v1.example.jsonc`) to the `selectionOutputPath` above itself, and returns only a compact summary (selected pages + counts + caveats) rather than echoing the full selection, so the large object stays out of context. The selection must not emit `destination`, `reread`, `taskRouting`, `taskWikiRefs`, `taskFingerprint`, or future task IDs. Wiki selection remains strict and progressive: use indexed wiki structure and companion section indexes; do not use unmigrated wiki pages or broad tree scans as formal planning constraints.

Do not hand-author the sidecar JSON. Generate it mechanically from the selection, then edit only the semantic routing:

1. Act on the `wiki-researcher` compact summary by its `status`:
   - `ok`/`partial` with selected pages: the researcher has already written the selection to `docs/superpowers/plans/<plan-stem>.wiki-selection.json` (it returns only the summary, not the full JSON, to keep the selection out of context) — confirm that file exists and do not re-author or echo it. This is a transient intermediate: the next step consumes it and removes it on success, so only the plan and its generated `.wiki-context.json` persist.
   - `missing_wiki_root`/`no_relevant_wiki` with no pages: no file was written — record the one-line N/A reason and skip the sidecar steps below (plan normally without wiki context).
   - fallback where the summary says the researcher could not write the file and returned the selection inline: save that inline JSON to the path yourself, then continue.
2. Generate the sidecar skeleton with the installed plugin-root script. It fills everything mechanical: schema constants, the `taskRouting` block, a `reread` block for every `hardConstraint` section, the top-level `sharedWiki` identity (taken from `shared_wiki_status`) when any `github_mcp` page is selected, and a default `destination.kind` per section (task-bound defaults also get an empty `destination.tasks` list). The generated sidecar is schemaVersion 4 JSON (`schemaVersion: 4`) with a page-rooted `wikiPages` tree, one bounded `documentContext` per page (page-level only), nested selected sections with hard constraint status, and categorized constraints (`implementation`, `test`, `review`, `general`).

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_context_render.py docs/superpowers/plans/<plan-stem>.wiki-context.json --scaffold docs/superpowers/plans/<plan-stem>.wiki-selection.json --strict --plan-path docs/superpowers/plans/<plan-stem>.md
```

3. Read the generated `docs/superpowers/plans/<plan-stem>.wiki-context.json` for its distilled constraints, use them like spec input while writing tasks, and include a lightweight `## Referenced Project Wiki` section in the plan that links the sidecar and summarizes selected pages/sections/counts without duplicating full context. Do not edit `destination` routing yet: all routing is assigned in a single pass after the plan stabilizes (below), so the Read-tracked sidecar is edited once for routing instead of here and again later.

If `--scaffold` reports a structural error it leaves the shallow `docs/superpowers/plans/<plan-stem>.wiki-selection.json` in place; fix that file and re-run `--scaffold` — do not patch the deep generated sidecar by hand. On success `--scaffold` consumes and removes the selection (only the plan and its `.wiki-context.json` remain); to reselect afterward, re-run `wiki-researcher` rather than hand-rebuilding the selection. Only as a last-resort fallback (e.g. the generator is unavailable) hand-author the sidecar from `__SUPERPOWER_ADAPTER_PLUGIN_ROOT__/contracts/wiki-context-v4.example.jsonc` and validate with `--validate-only --strict`.

Before decomposing tasks, render the configured source-of-truth planning policy with the installed plugin-root script:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/source_truth_settings.py <repo-root> --render-prompt plan-pre
```

If stdout is non-empty, include it as a short policy prompt input while drafting the implementation plan. The policy is a prompt guard only: do not add a mandatory sourceOfTruth section to the plan, do not run a semantic sourceOfTruth verifier agent, and do not create sourceOfTruth sidecar artifacts.

After complete draft plan, plan review revisions, and final task stabilization, assign all wiki routing in a single edit pass, then finalize it mechanically with one write.

First, edit each selected section's `destination` in the generated sidecar — do this once, now that task IDs are stable:
- Set `destination.kind`: `planning-only` for soft context the task text already embodies (not injected at execution/review, never for `hardConstraint`/`direct`); `global` for rules every task and reviewer needs; else `task-bound`.
- Write a one-line `destination.reason` for every selected section (the generator leaves it empty on purpose so you must justify routing).
- For every `task-bound` section, list the bare numeric plan task ids it applies to in `destination.tasks` (for example `["1", "3"]`, matching the plan's `### Task N` headings). There are no `globalWikiRefs` or per-task `wikiRefs` collections and no `sectionRef` to hand-write — the renderer derives each task's wiki scope straight from `destination.kind` and `destination.tasks`. For a reviewer-only check, keep the section `task-bound` and put it in the `review` constraint category instead of re-stating it to the implementer.
- Flip `taskRouting.status` to `confirmed` with `selectedSectionsFrozen: true`.
- For every `global` section, also fold a one-line summary into the plan's native `## Global Constraints` block, so the executor and every dispatched subagent pick it up through the path Superpowers already reads; the sidecar stays the authoritative source, the Global Constraints block is the human-visible cross-task surface.

Then finalize in one call. `--finalize` builds the `taskWikiRefs` roster (one `taskId`/`taskTitle` entry per stable `### Task N: <title>` heading, idempotent and preserving any prior `taskFingerprint`), stamps each `taskFingerprint` from the current plan task text, validates execution readiness, and writes the sidecar once:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_context_render.py docs/superpowers/plans/<plan-stem>.wiki-context.json --finalize --strict --plan-path docs/superpowers/plans/<plan-stem>.md
```

`--finalize` is the single source of truth for `taskFingerprint` and the task roster; never compute the sha256 by hand or hand-build `taskWikiRefs`. It refuses to write unless every plan task has exactly one roster entry and routing is execution-ready, so a clean finalize guarantees the execution/SDD `--fingerprint-preflight` will pass. After it prints its one-line summary, do not re-read the sidecar to "verify" — the transactional write already validated it, and re-reading only re-surfaces the whole file into context. You only edit the semantic routing in the generated sidecar; the generator owns the mechanical structure, so you never hand-build the envelope or infer the JSON format from `scripts/wiki_context_render.py`. If selected wiki conflicts with the confirmed Superpowers spec, stop and ask the user to resolve the conflict before finalizing the plan.

### Adapter Source-of-Truth Plan Policy

Source-of-truth is now settings-driven prompt policy plus task post-lint, not semantic verifier output. During plan review, render the plan-review checklist and pass any non-empty output to `plan-document-reviewer` through the normal review prompt:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/source_truth_settings.py <repo-root> --render-prompt plan-review
```

The reviewer should request revision or user confirmation if the plan explicitly or implicitly edits configured truth paths. Do not require a sourceOfTruth verification plan section, do not dispatch a semantic sourceOfTruth verifier agent, and do not create sourceOfTruth sidecar artifacts.
''',
    ),
    PatchSpec(
        skill='writing-plans',
        anchor='## Execution Handoff\n',
        block_id='writing-plans-gitignored-plan-commit-policy',
        content='''
### Adapter Plan Commit Policy (gitignore-aware)

Generated by superpower-adapter.

Before committing the plan, check whether its path is git-ignored:

```bash
git check-ignore -q docs/superpowers/plans/<filename>.md
```

- Exit `0` (ignored): Do not commit the plan or its `docs/superpowers/plans/<plan-stem>.wiki-context.json` sidecar, and never `git add -f`; leave them on disk (execution reads them in place or via `.worktreeinclude`). In the "Plan complete and saved to `<path>`" handoff, add that it was not committed because `.gitignore` excludes it, so the user must handle version control themselves to keep it.
- Exit non-zero (not ignored): Commit per native behavior.

The `.wiki-candidates.jsonl` sidecar is transient scratch and is never committed regardless.
''',
    ),
    PatchSpec(
        skill='executing-plans',
        anchor='### Step 2: Execute Tasks\n',
        block_id='executing-plans-implement-gate',
        content='''
### Adapter Task Context

Generated by superpower-adapter.

**Worktree first — before any step in this block, including the wiki fingerprint preflight.** Confirm `superpowers:using-git-worktrees` has already created or verified the isolated worktree, exactly as this skill's native "Required workflow skills" integration mandates ("creates one or verifies existing"); this precedes Step 2 execution. Being "already on a feature branch" or running the whole session in this directory does NOT satisfy it: a normal checkout on a feature branch is not an isolated worktree — `using-git-worktrees` Step 0 detects real isolation by `GIT_DIR != GIT_COMMON` (not by branch name), then creates or verifies one. The fingerprint preflight and task renderer below resolve the plan and `docs/superpowers/plans/<plan-stem>.wiki-context.json` from the working tree, so they must run inside the final worktree; the plan and sidecar (often git-ignored) must be present there, not only in the tree you launched from.

Before touching code, read the plan's `Referenced Project Wiki` section, locate the linked `docs/superpowers/plans/<plan-stem>.wiki-context.json`, and run exactly one wiki fingerprint preflight against the reviewed plan:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_context_render.py docs/superpowers/plans/<plan-stem>.wiki-context.json --fingerprint-preflight --strict --execution-ready --plan-path docs/superpowers/plans/<plan-stem>.md
```

''' + _preflight_fail('code changes', 'implementers', 'execution') + '''

For each current task, render task-scoped wiki constraints with the installed plugin-root renderer and inject stdout directly under `## Rendered Wiki Constraints for This Task`, together with `## Assigned Task` containing the current task's full plan text:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_context_render.py docs/superpowers/plans/<plan-stem>.wiki-context.json --task-id <current-task-id> --role implementer --strict --execution-ready
```

Do not persist rendered task-context Markdown files such as `.claude-*-wiki-task*-impl.md` or `.claude-*-source-task*-impl.md` during normal execution. If the linked wiki sidecar is missing, legacy-only, or insufficient, pause and ask whether to return to planning to add strict JSON project wiki references.

#### Hard Wiki Constraint Rereads

Before implementation, materialize this task's hard-constraint full-section rereads — both local project wiki and `source: github_mcp` shared wiki — with the single fixed fetcher, and inject its stdout directly after the rendered constraints under `## Hard Wiki Constraint Rereads`:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_materialize_task.py docs/superpowers/plans/<plan-stem>.wiki-context.json --task-id <current-task-id> --role implementer --project-root <project-root> --strict --execution-ready
```

This one command is the only reread fetcher: it lists the task-scoped hard-constraint rereads (the same selection behind `--reread-list`), extracts local sections straight from the filesystem, and for each `source: github_mcp` section invokes the shared-wiki MCP `read-sections` CLI (the same `loadConfig` + `readSectionsTool` the MCP server runs, resolved from this project's `wiki.sharedMcp`). It fails closed on shared-wiki rebinding drift (sidecar `sharedWiki.repoUrl` vs the connected repo), revision drift, section errors, or partial results — do not hand-fetch sections, call `shared_wiki_read_sections` yourself, or paste whole-page body text instead. The emitted rereads are authoritative hard constraints, not additional wiki search results; reviewers must verify compliance against this full section text without applying sibling sections or whole-page body.

''' + _source_truth_task_lint('execution', 'implementation', 'the current task prompt', 'After completing implementation for each task and before marking the task complete', 'the task', '') + '''

#### Durable-Knowledge Candidate Capture

While implementing a task, if you make a hard-to-reverse or surprising decision, resolve a non-obvious trade-off, or hit a durable gotcha that future sessions could rediscover incorrectly — and it is not already captured in the plan — append one JSONL line to `docs/superpowers/plans/<plan-stem>.wiki-candidates.jsonl` immediately, then keep coding. Each line carries: `taskId`, `kind` (decision|gotcha|contract|convention), `claim` (one line), `why` (one line, include rejected alternatives), `sourceRefs`, and `carveOut`.

Capture liberally and cheaply; do not run `update-wiki`, judge ownership, or check duplicates mid-flow — the end-of-flow review is the strict filter. Append-only; never rewrite earlier lines. This file is transient scratch: do not commit it.

After completing implementation, and before handing off to `finishing-a-development-branch` or otherwise removing/exiting the worktree, run the `update-wiki` skill to make the keep-or-skip determination about durable implementation knowledge for this work, consuming any `docs/superpowers/plans/<plan-stem>.wiki-candidates.jsonl` sidecar as candidate input. ''' + _UPDATE_WIKI_DETERMINATION + ''' The sidecar lives in the working tree and is deleted when the worktree is removed, so consume it here, inside the still-live worktree — not later: the post-merge `update-wiki` reminder is only a backstop for a skipped step, by which point the worktree (and the sidecar) is usually gone and update-wiki falls back to the merged diff and conversation context. Do not force a spec or wiki edit when the skill concludes there is nothing durable to record.
''',
    ),
    PatchSpec(
        skill='subagent-driven-development',
        anchor='## The Process\n',
        block_id='subagent-driven-development-implement-gate',
        content='''
## Adapter Task Context

Generated by superpower-adapter.

**Worktree first — before any step in this block, including the wiki fingerprint preflight.** Confirm `superpowers:using-git-worktrees` has already created or verified the isolated worktree, exactly as this skill's native "Required workflow skills" integration mandates ("creates one or verifies existing"). This is SDD's first action, ahead of the ledger check and the plan read. Being "already on a feature branch" or running the whole session in this directory does NOT satisfy it: a normal checkout on a feature branch is not an isolated worktree — `using-git-worktrees` Step 0 detects real isolation by `GIT_DIR != GIT_COMMON` (not by branch name), then creates or verifies one. Everything below resolves working-tree paths through `git rev-parse --show-toplevel` — the ledger, the rendered `$SDD_DIR` wiki files, and the native `task-brief`/`review-package` handoffs — so it must run inside the final worktree; starting it in the tree you launched from strands those files in the wrong tree.

When reading the implementation plan, extract its `Referenced Project Wiki` section and linked `docs/superpowers/plans/<plan-stem>.wiki-context.json`. After extracting stable task IDs and before dispatching the first subagent, run exactly one wiki fingerprint preflight against the reviewed plan:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_context_render.py docs/superpowers/plans/<plan-stem>.wiki-context.json --fingerprint-preflight --strict --execution-ready --plan-path docs/superpowers/plans/<plan-stem>.md
```

''' + _preflight_fail('dispatch', 'implementers/reviewers', 'SDD') + '''

Before dispatching each implementer or reviewer, render only that task's role-scoped wiki constraints to a file under the SDD handoff directory, then pass the subagent that file path. This follows the native Superpowers file-handoff model (`task-brief`, `review-package`): bulk context moves as files the subagent Reads in one call, never pasted through the controller's context. The native `task-brief` already delivers the assigned task's full text, so do not paste the task text or the rendered wiki constraints into the dispatch prompt:

```bash
SDD_DIR="$(git rev-parse --show-toplevel)/.superpowers/sdd"; mkdir -p "$SDD_DIR"
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_context_render.py docs/superpowers/plans/<plan-stem>.wiki-context.json --task-id <assigned-task-id> --role implementer --strict --execution-ready > "$SDD_DIR/task-<assigned-task-id>-wiki.md"
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_context_render.py docs/superpowers/plans/<plan-stem>.wiki-context.json --task-id <reviewed-task-id> --role reviewer --strict --execution-ready > "$SDD_DIR/task-<reviewed-task-id>-wiki-review.md"
```

In the implementer prompt, instruct the subagent to Read `$SDD_DIR/task-<assigned-task-id>-wiki.md` (its rendered wiki constraints) alongside its `task-brief` file. In the reviewer prompt, point the reviewer at `$SDD_DIR/task-<reviewed-task-id>-wiki-review.md` alongside its `review-package` file. These rendered wiki files are transient scratch in the working-tree SDD workspace `<repo-root>/.superpowers/sdd/` (the same directory native `task-brief`/`review-package` use via `sdd-workspace`, kept out of `.git/` because Claude Code denies subagent writes under the protected git-dir); the workspace's self-ignoring `.gitignore` keeps them out of commits, and do not pass legacy rendered context files such as `.claude-*-wiki-task*-impl.md`. If the plan lacks strict JSON wiki references or references only legacy context, pause and ask whether to update the plan before dispatching subagents.

### Hard Wiki Constraint Rereads

Before dispatching the implementer or reviewer for a task, materialize that task's hard-constraint full-section rereads — both local project wiki and `source: github_mcp` shared wiki — directly into the rendered wiki file the subagent already Reads, with the single fixed fetcher:

```bash
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_materialize_task.py docs/superpowers/plans/<plan-stem>.wiki-context.json --task-id <assigned-task-id> --role implementer --project-root "$(git rev-parse --show-toplevel)" --strict --execution-ready --append-to "$SDD_DIR/task-<assigned-task-id>-wiki.md"
python3 __SUPERPOWER_ADAPTER_PLUGIN_ROOT__/scripts/wiki_materialize_task.py docs/superpowers/plans/<plan-stem>.wiki-context.json --task-id <reviewed-task-id> --role reviewer --project-root "$(git rev-parse --show-toplevel)" --strict --execution-ready --append-to "$SDD_DIR/task-<reviewed-task-id>-wiki-review.md"
```

This one command is the only reread fetcher: it lists the task-scoped hard-constraint rereads (the same selection behind `--reread-list`), extracts local sections straight from the filesystem, and for each `source: github_mcp` section invokes the shared-wiki MCP `read-sections` CLI (the same `loadConfig` + `readSectionsTool` the MCP server runs, resolved from this project's `wiki.sharedMcp`). It appends the document context plus full section text under a `## Hard Wiki Constraint Rereads` heading in the same rendered file, and fails closed on shared-wiki rebinding drift (sidecar `sharedWiki.repoUrl` vs the connected repo), revision drift, section errors, or partial results — do not hand-fetch sections, call `shared_wiki_read_sections` yourself, or paste whole-page body text instead. These rereads are authoritative hard constraints, not additional wiki search results; reviewers must verify compliance against the full section text without applying sibling sections or whole-page body text.

''' + _source_truth_task_lint('SDD', 'dispatch', 'implementer/reviewer prompts', 'After each implementer returns and before marking its task complete', 'that task', ' Reviewers should check that any lint findings were resolved.') + '''

#### Durable-Knowledge Candidate Capture (via subagents)

Subagents must NOT write wiki pages or the candidates sidecar — parallel subagents would race on the file. Instead, instruct each implementer and reviewer subagent to end its bounded result with an optional `durableKnowledgeCandidates` list: hard-to-reverse or surprising decisions, non-obvious trade-offs, or durable gotchas it hit that are not already in the plan. Each entry carries `taskId`, `kind` (decision|gotcha|contract|convention), `claim`, `why` (include rejected alternatives), `sourceRefs`, and `carveOut`. If it surfaced nothing durable, it omits the field.

As each subagent returns, the main agent appends its candidates — one JSONL line each — to `docs/superpowers/plans/<plan-stem>.wiki-candidates.jsonl`. The main agent serializes these appends (append-only; transient scratch; never committed) and is the only writer of the sidecar under SDD.

After implementation and review, and before handing off to `finishing-a-development-branch` or otherwise removing/exiting the worktree, the main agent must run the `update-wiki` skill to make the keep-or-skip determination about durable implementation knowledge for this work, consuming the `docs/superpowers/plans/<plan-stem>.wiki-candidates.jsonl` sidecar as candidate input. ''' + _UPDATE_WIKI_DETERMINATION + ''' The sidecar lives in the working tree and dies with the worktree, so consume it here, inside the still-live worktree — not after a merge: the post-merge `update-wiki` reminder is only a backstop for a skipped step, by which point the worktree (and the sidecar) is usually gone and update-wiki falls back to the merged diff and conversation context. Subagents should not write wiki updates unless explicitly instructed.
''',
    ),
    PatchSpec(
        skill='finishing-a-development-branch',
        anchor='## The Process\n',
        block_id='finishing-a-development-branch-update-wiki-gate',
        content='''
## Adapter Durable-Knowledge Gate

Generated by superpower-adapter.

**Step 1 (Verify Tests) still comes first and is unchanged** — this adapter gate does not run ahead of it, replace it, or assert that tests pass. It is a knowledge-capture checkpoint layered onto this skill: before you execute a finishing option, confirm the `update-wiki` keep-or-skip determination about durable implementation knowledge has been made for the work being finished, while the worktree and any `docs/superpowers/plans/<plan-stem>.wiki-candidates.jsonl` sidecar are still alive. Options 1 and 4 remove a Superpowers-created worktree in Step 6, which deletes that sidecar, so this is the last reliable point to consume it.

- If `update-wiki` already ran for exactly this work at the end of `executing-plans` / `subagent-driven-development` (the normal path), just confirm that conclusion and continue — do not re-run the full review.
- Otherwise, run the `update-wiki` skill now, consuming the candidates sidecar if present. ''' + _UPDATE_WIKI_DETERMINATION + '''

This gate is knowledge-capture only: it does not assert implementation is verified or complete, and it never blocks a finishing option once the determination is made.
''',
    ),
]


def load_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def save_text(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')


def strip_block_by_id(text: str, skill: str, block_id: str) -> tuple[str, bool]:
    start_marker = f'{START_PREFIX}{block_id} -->'
    end_marker = f'{END_PREFIX}{block_id} -->'
    start = text.find(start_marker)
    if start == -1:
        return text, False
    end = text.find(end_marker, start)
    if end == -1:
        raise SystemExit(f'Malformed adapter native skill patch: missing end marker for {skill}')
    end += len(end_marker)
    if end < len(text) and text[end:end + 1] == '\n':
        end += 1
    if start > 0 and text[start - 1:start] == '\n':
        start -= 1
    return text[:start] + text[end:], True


def strip_block(text: str, spec: PatchSpec) -> tuple[str, bool]:
    removed_any = False
    for block_id in (*spec.legacy_block_ids, spec.block_id):
        text, removed = strip_block_by_id(text, spec.skill, block_id)
        removed_any = removed_any or removed
    return text, removed_any


def find_anchor(text: str, spec: PatchSpec) -> str:
    for anchor in (spec.anchor, *spec.fallback_anchors):
        if anchor in text:
            return anchor
    anchors = ', '.join(anchor.strip() for anchor in (spec.anchor, *spec.fallback_anchors))
    raise SystemExit(f'Missing anchor for {spec.skill}: {anchors}')


def apply_patch(path: Path, spec: PatchSpec, target: Path) -> bool:
    original = load_text(path)
    stripped, _removed = strip_block(original, spec)
    anchor = find_anchor(stripped, spec)
    anchor_index = stripped.find(anchor)
    insert_at = anchor_index + len(anchor)
    # rendered_block already ends in a single newline, and strip_block reclaims exactly one leading
    # and one trailing newline around the block. Inserting one leading newline and NO extra trailing
    # one therefore makes apply the precise inverse of strip, so re-installing is a byte-stable no-op.
    # (An earlier version appended a second trailing newline that strip could not reclaim, leaking one
    # blank line into the file on every re-install.)
    block = '\n' + spec.rendered_block(target)
    updated = stripped[:insert_at] + block + stripped[insert_at:]
    if updated != original:
        save_text(path, updated)
        return True
    return False


def remove_patch(path: Path, spec: PatchSpec) -> bool:
    text = load_text(path)
    updated, removed = strip_block(text, spec)
    if removed:
        save_text(path, updated)
    return removed


def verify_patch(path: Path, spec: PatchSpec, target: Path) -> None:
    text = load_text(path)
    expected = spec.rendered_block(target).rstrip()
    if expected not in text:
        raise SystemExit(f'Missing adapter native skill patch in {path}: {spec.block_id}')



def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace", newline="\n")
        except (OSError, ValueError):
            pass

def main() -> int:
    _configure_stdio()
    if len(sys.argv) != 3:
        raise SystemExit('Usage: native_skill_patch.py <install|uninstall|verify> <superpowers-dir>')

    mode = sys.argv[1]
    target = Path(sys.argv[2]).resolve()
    if mode not in {'install', 'uninstall', 'verify'}:
        raise SystemExit(f'Unsupported mode: {mode}')

    changed = False
    for spec in PATCHES:
        path = target / spec.relative_path
        if not path.is_file():
            raise SystemExit(f'Missing Superpowers native skill: {path}')
        if mode == 'install':
            changed |= apply_patch(path, spec, target)
        elif mode == 'uninstall':
            changed |= remove_patch(path, spec)
        else:
            verify_patch(path, spec, target)

    if mode == 'verify':
        print('Native skill patches OK')
    elif changed:
        print(f'Native skill patches updated via {mode}')
    else:
        print(f'Native skill patches already satisfied for {mode}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
