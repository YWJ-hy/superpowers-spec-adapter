# Multica Superpowers Adapter 已实现功能与进度

本文记录当前仓库中围绕 `MULTICA_SUPERPOWERS_ADAPTER_REPLICATION_PLAN_CN.md` 已完成的实现范围、验证情况、未完成事项和后续建议，便于在新 session 中继续实现剩余功能。

## 1. 当前结论

当前已实现三条 Multica 相关路径：

1. **Multica-native runtime bundle 的 Phase 1 可校验 + 离线 preflight contract 版**：可以从 Superpowers source / installed target 和当前 adapter assets 生成一个可校验、可离线 preflight 的 Multica runtime bundle 骨架。
2. **真实 Multica workspace bootstrap + issue template flow 初版**：可以生成 `superpowers-adapter` workspace skill pack，计划或执行官方 `multica` CLI 的 skill import、Claude Code agent 创建/配置、skill attach、模板化 issue create 和 issue assign，从而用真实 Multica daemon + Claude Code runtime 触发只读 smoke 或兼容 issue-template task。
3. **Multica 可视化 role-agent live acceptance**：`multica-live-acceptance` 已从单个 `superpowers-adapter-orchestrator` 委托模式切换为 A-H stage issue fanout，直接创建/规划独立 stage issue 并 assign 给 `superpowers-*` role agents 或 `superpowers-runtime-squad`，用于验证 Multica UI/CLI 中可见的多智能体 Superpowers+adapter 流程。

runtime bundle 已经覆盖：

- `build-multica-runtime` 命令入口。
- `verify-multica-runtime` 命令入口。
- runtime bundle 生成器和校验器。
- 复用现有 Superpowers native skill patch 内容。
- 把 adapter script 调用路径从 Claude Code plugin root 改为 Multica runtime root。
- 复制 adapter tool scripts 到 bundle 的 `dist/tools/scripts/`。
- 生成基础 workflows / agents / gates / triggers / schemas / MCP examples / issue templates / autopilots / validators。
- 生成机器可校验的 `dist/triggers/issue-template-bindings.json` 和 `dist/triggers/artifact-next-actions.json`，把 issue templates / quick actions / artifact-driven next actions 归一到 `WorkflowInvocation` contract。
- 生成机器可校验的 `dist/gates/gate-contracts.json`、`dist/preflight/gate-transition-contract.json`、`dist/agents/role-agent-contracts.json`、`dist/preflight/role-task-contract.json` 和 `dist/schemas/artifact-contracts.json`，把 gate 语义/状态转换、role fresh-context/I/O/tool 边界、orchestrator-created role task dispatch、artifact producer/consumer/schema 绑定纳入 runtime contract。
- 生成 `dist/preflight/` 离线 preflight contracts。
- 生成 `dist/tools/validators/` 下的 runtime capability / WorkflowInvocation 离线 validator scripts。
- 生成 `dist/task-graphs/subagent-driven-development.task-graph.json` SDD task graph contract。
- 强化 generated trigger/schema contract、trigger catalog 校验、tool manifest 防漏打包校验、source snapshot 校验、preflight contract 校验、task graph contract 校验和跨 artifact 结构化一致性校验。

真实 Multica bootstrap 初版已覆盖：

- `multica-bootstrap` 命令入口。
- 生成 Multica workspace skill pack：`SKILL.md`、adapter skills / agents / scripts、patched upstream Superpowers skills。
- dry-run 命令计划，不触发 workspace 写操作。
- `--apply` 外部可见路径：preflight `multica auth status` / `daemon status` / `runtime list`，导入 skill、创建/更新 Claude Code agent、attach skill、创建模板 issue 并 assign 给 agent。
- `smoke` issue 默认只读：确认 target repo、skill pack 可见性和 project/shared wiki root 状态，不编辑代码、不 commit、不 push、不创建 PR。
- 已内置真实 issue template bodies：`lanhu-intake`、`brainstorming`、`writing-plans`、`execute-plan`、`sdd-execution`、`systematic-debugging`、`break-loop`、`update-wiki`、`publish-shared-wiki`、`shared-wiki-mcp-pr`。
- dry-run smoke 覆盖 skill pack、CLI 命令计划、所有 issue template body 和关键缺参失败，并接入 `self-test.sh`。

当前官方 Multica CLI 已验证可走通 workspace skill + issue assignment 真实路径；Phase 3–6 端到端业务 workflow 已完成一次真实 `--apply --observe-runs` disposable target repo 验收：`phase3-lanhu-intake` WS-8、`phase3-brainstorming` WS-9、`phase3-writing-plans` WS-10、`phase4-execute-plan` WS-11、`phase4-sdd-execution` WS-12、`phase5-systematic-debugging` WS-13、`phase5-break-loop` WS-14、`phase6-update-wiki` WS-15、`phase6-publish-shared-wiki` WS-16、`phase6-shared-wiki-mcp-pr` WS-17 均创建/分配成功并观察到 run/task 输出。Phase 2 runtime install 也已用 `install-multica-runtime --dry-run --require-native-surfaces` 落到当前官方 CLI：exact native command probe 采用 help output 精确匹配；runtime registration issue 作为 runtime anchor，issue metadata 承载 WorkflowInvocation / gate / schema / runtime state，issue comments/attachments 承载 artifact contract references，issue assign/rerun 和 issue get/runs/run-messages 承载 fresh role task dispatch 与观察，autopilot schedule/webhook triggers 承载 trigger substitute。`--require-native-surfaces` 现在要求 exact native command 或 documented substitute surface 覆盖每个 runtime capability，当前 dry-run 已返回 planned 而非 blocked。

## 2. 已新增或修改的文件

### 2.1 新增文件

- `build-multica-runtime.sh`
  - shell wrapper，调用 Python builder。
- `verify-multica-runtime.sh`
  - shell wrapper，调用 Python verifier。
- `lib/multica_runtime_spec.py`
  - Multica runtime bundle 的共享常量：expected workflows、role agents、gates、triggers、schemas、MCP examples、capabilities、preflight artifacts、validator scripts、task graphs、forbidden strings 等。
- `lib/multica_runtime_builder.py`
  - 生成 Multica runtime bundle 的主实现，包括 preflight contracts、离线 validator scripts 和 SDD task graph contract。
- `lib/multica_runtime_verify.py`
  - 校验 Multica runtime bundle 的主实现，包括 preflight artifacts、validator scripts、task graph contract、trigger/gate/role/artifact catalogs 和跨 artifact 结构化一致性。
- `lib/multica_runtime_install.py`
  - Phase 2 runtime 安装规划器：默认 dry-run，先运行本地 verifier，再规划 Multica CLI preflight，并把 runtime registration / workflow / gate / schema / artifact / gate-state / fresh-role-task / MCP requirement 映射到当前官方 surface：runtime registration issue、issue metadata、issue comments/attachments、issue assign/rerun、issue get/runs/run-messages、autopilot triggers、agent/skill/project resource；不猜 undocumented API。
- `tests/multica-runtime-build-smoke.sh`
  - 端到端 smoke：构建临时 bundle、运行 verifier、检查 root replacement、forbidden strings、tool manifest / root manifest 脚本集合一致性、source snapshot、preflight artifacts、validator scripts、trigger/gate/role/artifact catalogs、SDD task graph，并验证 verifier 能拒绝 workflow metadata drift，再复用 `wiki-context-json-render-smoke.sh` 验证生成后的 tool layer。
- `tests/multica-runtime-install-dry-run-smoke.sh`
  - Phase 2 install planner smoke：构建临时 runtime，运行 `install-multica-runtime --dry-run --json` 和 `--require-native-surfaces`，验证本地 verifier check、Multica CLI preflight command plan、manifest 合同检查、runtime registration issue、issue metadata、issue comments/attachments、issue get/runs 和 autopilot substitute checks。
- `lib/multica_cli_bootstrap.py`
  - 真实 Multica workspace bootstrap 初版：生成 workspace skill pack，并通过官方 `multica` CLI dry-run 或 `--apply` 计划/执行 skill import、agent 创建/更新、skill attach、模板化 issue create、issue assign。
- `multica-bootstrap.sh`
  - shell wrapper，调用 Python bootstrap。
- `tests/multica-bootstrap-dry-run-smoke.sh`
  - dry-run smoke：生成 `superpowers-adapter` skill pack，验证 overlay assets、patched upstream Superpowers skills、root `SKILL.md`、计划中的真实 Multica CLI 命令、内置 issue template bodies 和关键缺参失败，不触发 workspace 写操作。
- `MULTICA_SUPERPOWERS_ADAPTER_PROGRESS_CN.md`
  - 本进度文件。

### 2.2 修改文件

- `manage.sh`
  - 新增命令：
    - `build-multica-runtime <superpowers-source-or-url> [adapter-root] <out>`
    - `verify-multica-runtime <runtime-root>`
    - `multica-bootstrap [bootstrap|create-issue|preflight|prepare-skill-pack] --superpowers-source <path> --target-repo <path> [--issue-template id] [--apply]`
- `self-test.sh`
  - 接入 `tests/multica-runtime-build-smoke.sh`。
  - 接入 `tests/multica-runtime-install-dry-run-smoke.sh`。
  - 接入 `tests/multica-bootstrap-dry-run-smoke.sh`。
- `README.md`
  - 增加 Multica runtime bundle 构建与校验说明。
  - 增加真实 Multica workspace bootstrap / issue template flow 说明。
- `ADAPTER_USER_FLOW_CN.md`
  - 增加可选 Multica-native runtime bundle 分发路径说明。
  - 增加真实 Multica workspace issue template flow 说明。
- `ADAPTER_DEVELOPMENT_CN.md`
  - 增加 Multica runtime bundle 与 Multica bootstrap 两条路径的开发/验证说明。
- `CLAUDE.md`
  - 增加常用命令、smoke test 和架构说明。

## 3. 已实现能力明细

### 3.1 命令入口

当前支持：

```bash
./manage.sh build-multica-runtime <superpowers-source-or-url> [adapter-root] <out>
./manage.sh verify-multica-runtime <runtime-root>
```

常用形式：

```bash
./manage.sh build-multica-runtime ../superpowers . ./dist/multica-superpowers-runtime
./manage.sh verify-multica-runtime ./dist/multica-superpowers-runtime
```

`build-multica-runtime.sh` 兼容两种参数形式：

```bash
./build-multica-runtime.sh <superpowers-source-or-url> <out>
./build-multica-runtime.sh <superpowers-source-or-url> <adapter-root> <out>
```

### 3.2 Superpowers source 解析

`lib/multica_runtime_builder.py` 当前支持：

- 本地 Superpowers source path。
- Git URL，例如 `https://github.com/obra/superpowers.git`。
- 对 Git URL 使用临时目录 shallow clone。
- 从 Superpowers `package.json` 读取 version。
- 如果本地 source 是 git repo，记录当前 revision。

### 3.3 输出 bundle 结构

当前 builder 生成：

```text
<out>/
  manifest.json
  source/
    superpowers/
    superpower-adapter/
  dist/
    workflows/
    agents/
    gates/
    triggers/
    schemas/
    preflight/
    task-graphs/
    tools/
      tool-manifest.json
      scripts/
      validators/
    mcp/
    multica/
      agent-instructions.md
      issue-templates/
      autopilots/
```

注意：这是一版 repo-local bundle 结构，`manifest.json` 在 root，主要 runtime artifacts 在 `dist/`。

### 3.4 workflow 生成

已生成以下 upstream Superpowers-compatible workflows：

- `using-superpowers`
- `brainstorming`
- `writing-plans`
- `executing-plans`
- `subagent-driven-development`
- `systematic-debugging`
- `test-driven-development`
- `verification-before-completion`
- `finishing-a-development-branch`
- `using-git-worktrees`
- `requesting-code-review`
- `receiving-code-review`

已生成以下 adapter / maintenance / standalone workflows：

- `update-wiki`
- `break-loop`
- `wiki-progressive-disclosure`
- `init-wiki`
- `import-wiki`
- `migrate-wiki`
- `lanhu-requirements`
- `shared-wiki-mcp`
- `publish-shared-wiki`

每个 `*.workflow.yaml` 当前包含：

- `workflowId`
- `sourceKind`
- `sourcePath`
- `executionMode`
- `requiredCapabilities`
- `requiredArtifacts`
- `outputArtifacts`
- `gates`
- `roleAgents`
- `patchSummary`
- `workflowBoundary`
- `prompt` 原文块

### 3.5 native skill patch 复用

当前 builder 复用：

- `lib/native_skill_patch.py`
  - `PATCHES`
  - `strip_block()`
  - `find_anchor()`

已实现 Multica 专用渲染：

```text
__SUPERPOWER_ADAPTER_PLUGIN_ROOT__
→ ${MULTICA_SUPERPOWERS_RUNTIME_ROOT}/tools
```

因此 workflow 中脚本调用会变成：

```text
python3 ${MULTICA_SUPERPOWERS_RUNTIME_ROOT}/tools/scripts/wiki_context_render.py
```

没有修改 Claude Code install path 使用的 `PatchSpec.rendered_block()` 语义。

### 3.6 role agents 生成

当前生成/复制的 role agents 包括：

- 模板生成：
  - `superpowers-orchestrator`
  - `brainstorming-agent`
  - `planning-agent`
  - `debugger`
  - `break-loop-analyst`
  - `wiki-curator`
  - `finisher`
  - `shared-wiki-publisher`
- 复制 adapter agent：
  - `wiki-researcher`
- 通过 `lib/sync_role_prd.py` 的 `render_agent()` 生成 Lanhu analyst：
  - `lanhu-frontend-requirements-analyst`
  - `lanhu-backend-requirements-analyst`
- 从 upstream Superpowers prompt 提取：
  - `spec-document-reviewer`
  - `plan-document-reviewer`
  - `implementer`
  - `spec-compliance-reviewer`
  - `code-quality-reviewer`
  - `code-reviewer`

当前 role agent 文件是可读 prompt/runtime contract 文档，尚不是 Multica 实际注册 API 的输出格式。

### 3.7 tool layer 生成

当前从 `manifest.json.installedPaths` 中复制所有 `scripts/*` 到：

```text
dist/tools/scripts/
```

并生成：

```text
dist/tools/tool-manifest.json
```

`tool-manifest.json` 声明：

- `runtimeRootEnv: MULTICA_SUPERPOWERS_RUNTIME_ROOT`
- `scripts` 是 `tool-runner-internal`
- `validatorScripts` 是 `preflight-validator`
- Python scripts 不是用户入口

### 3.8 preflight validators / SDD task graph

当前生成：

```text
dist/preflight/runtime-capabilities.json
dist/preflight/workflow-invocation-contract.json
dist/preflight/artifact-store-contract.json
dist/preflight/gate-transition-contract.json
dist/preflight/role-task-contract.json
dist/tools/validators/runtime_capability_preflight.py
dist/tools/validators/workflow_invocation_validate.py
dist/tools/validators/gate_transition_validate.py
dist/tools/validators/artifact_store_validate.py
dist/tools/validators/role_task_validate.py
dist/task-graphs/subagent-driven-development.task-graph.json
```

`runtime-capabilities.json` 声明离线/机械检查项：

- `MULTICA_SUPERPOWERS_RUNTIME_ROOT` env。
- runtime root path / `manifest.json` / `dist/tools/scripts/` 可读。
- tool scripts 可执行。
- `python3` / `/bin/sh` / `git` 可用。
- `artifact-store`、`task-isolation`、`mcp-client` 仍作为 provider-declared capabilities，不做 live probe。

`workflow-invocation-contract.json` 声明：

- 所有 workflow ID。
- execution mode。
- required / output artifacts。
- required gates。
- required capabilities。
- workflow-specific MCP dependency hints。
- artifact store contract。
- gate transition contract。
- illegal transition rules。

`gate-transition-contract.json` 声明 gate 状态推进边界：允许的 `pending → satisfied`、`pending → blocked`、`blocked → pending`、`blocked → satisfied` 转换，禁止 satisfied gate 未审计回退，要求 gate owner 或 orchestrator 推进，并要求转换 evidence；外部副作用必须满足对应 side-effect gate。

`artifact-store-contract.json` 声明 artifact 持久化边界：`artifacts/superpowers/{workflowId}/{runId}/{artifactType}/{name}` 路径模式、artifact 状态枚举、approved/current 状态的 SHA-256 checksum 要求、role-output-only 写策略，以及 orchestrator-injected-source-artifacts-only 读策略。

`runtime_capability_preflight.py` 可离线检查 runtime root、工具脚本和 provider-declared capabilities。

`workflow_invocation_validate.py` 可离线检查 `WorkflowInvocation` 的 top-level fields、workflow / trigger / execution mode / gate / capability / MCP enum、required artifacts、required gates、capabilities、MCP dependency hints 和关键 illegal transition rules。

`gate_transition_validate.py` 可离线检查 gate 状态转换、actor 是否为 owner/orchestrator、evidence 是否存在，以及外部副作用 gate 是否真正进入 satisfied 状态；它仍是 live Multica gate API 接入前的本地合同校验。

`artifact_store_validate.py` 可离线检查 artifact reference 的 type/path/status/checksum、producer/consumer 合同和读写策略；它仍是 live Multica artifact API 接入前的本地合同校验。

`subagent-driven-development.task-graph.json` 明确：

- `schemaVersion: 1`。
- `executionMode: multica-sdd-task-graph`。
- 默认顺序执行。
- required inputs：`implementation-plan`、`wiki-context`。
- `implementer` → `spec-compliance-reviewer` → `code-quality-reviewer` → `code-reviewer-final`。
- reviewer failed loop back to `implementer`。
- 每个 node `freshContext: required`。
- implementer 依赖 `${MULTICA_SUPERPOWERS_RUNTIME_ROOT}/tools/scripts/wiki_context_render.py`。

这些仍是离线 contract 和 validator，不是真实 Multica task API 调度。

### 3.9 gates / triggers / schemas / MCP / Multica templates

当前生成基础占位/契约文件：

Gates：

- `design-approval`
- `spec-approval`
- `lanhu-scope-confirmation`
- `wiki-update-authorization`
- `shared-wiki-publish-authorization`
- `external-pr-creation-authorization`

Triggers：

- `compatibility-commands`
- `issue-template-bindings`
- `intent-router`
- `artifact-next-actions`
- `illegal-transition-rules`

Schemas：

- `workflow-invocation.schema.json`
- `spec.schema.json`
- `implementation-plan.schema.json`
- `wiki-context-v3.schema.json`
- `lanhu-evidence-package.schema.json`
- `update-wiki-candidate.schema.json`
- `review-result.schema.json`
- `gate-state.schema.json`
- `sdd-task-graph.schema.json`
- `sdd-task-input.schema.json`
- `sdd-task-output.schema.json`

MCP examples：

- `required-capabilities.yaml`
- `lanhu-mcp.example.yaml`
- `shared-wiki-mcp.example.yaml`
- `github-mcp.example.yaml`

Trigger catalogs：

- `dist/triggers/issue-template-bindings.json`：声明每个 Multica issue template / quick action 的默认 workflow、允许 workflow、必需 metadata、必需 artifact、启动 gate 和 workflow-managed gate。
- `dist/triggers/artifact-next-actions.json`：声明从 Lanhu package、approved spec、reviewed plan、final review、verified work、verified bugfix、shared wiki candidate 等 artifact state 到下一步 workflow 的 gate-aware suggestion，明确 `autoExecute: false`。

Multica helpers：

- `dist/multica/agent-instructions.md`
- `dist/multica/issue-templates/*.md`
- `dist/multica/autopilots/*.md`
- `dist/tools/validators/*.md`

这些文件目前是 bundle 骨架和契约说明，不是已对接真实 Multica API 的注册产物。

## 4. 已实现 verifier 检查项

`lib/multica_runtime_verify.py` 当前会检查：

- root `manifest.json` 存在且 `generatedBy` 正确。
- manifest 声明必要 runtime capabilities：
  - `local-filesystem`
  - `shell-git`
  - `artifact-store`
  - `task-isolation`
  - `mcp-client`
- manifest 声明 `MULTICA_SUPERPOWERS_RUNTIME_ROOT`。
- root replacement 指向 `${MULTICA_SUPERPOWERS_RUNTIME_ROOT}/tools`。
- expected workflows / agents / gates / triggers / schemas / mcp examples / issue templates / autopilots / validators 全部存在。
- `dist/preflight/runtime-capabilities.json`、`dist/preflight/workflow-invocation-contract.json`、`dist/preflight/artifact-store-contract.json` 和 `dist/preflight/gate-transition-contract.json` 存在且与 manifest 同步。
- `dist/task-graphs/subagent-driven-development.task-graph.json` 存在且与 manifest 同步。
- 所有 adapter scripts 已复制到 `dist/tools/scripts/`。
- `dist/tools/tool-manifest.json.scripts` 与 adapter `manifest.json.installedPaths` 中的 `scripts/*` 完全一致，且 root `manifest.json.toolScripts` 同步一致。
- `dist/tools/tool-manifest.json.validatorScripts` 与 root `manifest.json.validatorScripts` 同步一致，validator runtimePath 指向 `${MULTICA_SUPERPOWERS_RUNTIME_ROOT}/tools/validators/...`。
- source snapshot 保留 `source/superpower-adapter/overlays/{agents,skills,scripts}` 和上游 `source/superpowers/skills` 关键入口。
- generated trigger YAML 包含 `requiredInputs`、`preflightChecks` 和 `WorkflowInvocation` schema 输出契约，`illegal-transition-rules.yaml` 包含关键非法跳转规则。
- `issue-template-bindings.json` / `artifact-next-actions.json` 与 root manifest、`workflow-invocation-contract.json`、issue template markdown 和 schema enum 保持同步；artifact next actions 必须 `gateAware: true` 且 `autoExecute: false`。
- `workflow-invocation.schema.json` 包含 workflow / issueTemplateId / artifactNextActionId / gate / capability enum、source artifact、MCP requirement 和 preflight metadata contract。
- `sdd-task-graph.schema.json` / `sdd-task-input.schema.json` / `sdd-task-output.schema.json` 可加载且包含关键字段。
- `workflow-invocation-contract.json` 覆盖所有 workflow、required capabilities、artifact store contract、gate transition contract 和 illegal transition rules。
- `gate-transition-contract.json` 与 root manifest / WorkflowInvocation contract / gate contracts 同步，且 allowed/forbidden transitions、owner/orchestrator advancement policy 和外部副作用 gate policy 符合 spec。
- `artifact-store-contract.json` 与 root manifest / WorkflowInvocation contract / artifact contracts 同步，且 pathPattern、approved/current checksum 要求和读写策略符合 spec。
- SDD task graph 覆盖 required input artifacts、fresh context nodes、reviewer failure loop 和 `wiki_context_render.py` 依赖。
- `dist/` 下没有 unresolved：
  - `__SUPERPOWER_ADAPTER_PLUGIN_ROOT__`
- `dist/` 下没有 forbidden script path：
  - `python3 overlays/scripts/`
  - `python3 superpowers/scripts/`
  - `python3 scripts/wiki_`
  - `python3 scripts/wiki-`
- 至少一个 workflow 引用了 `${MULTICA_SUPERPOWERS_RUNTIME_ROOT}/tools`。
- patched workflows 中包含 native patch marker。
- standalone workflows 中包含 standalone/boundary 相关内容。
- `writing-plans` workflow 包含 `schemaVersion: 3` 和 `Referenced Project Wiki`。
- execution workflows 包含 `wiki_context_render.py`。
- `systematic-debugging` 包含“不要一开始调用 wiki-researcher”的约束。
- `workflow-invocation.schema.json` 必含关键字段。
- `wiki-context-v3.schema.json` 要求 `schemaVersion const 3`。
- tool scripts 可读且可执行。
- `tool-manifest.json` 说明 scripts 不是用户入口。
- 结构化解析 generated workflow metadata，并交叉校验 `manifest.json`、workflow YAML、preflight contracts、`workflow-invocation.schema.json`、SDD task graph 和 `tool-manifest.json` 是否与 `multica_runtime_spec.py` 一致。
- 校验 workflow role agent / gate 引用都存在于 spec、manifest 和 `dist/agents` / `dist/gates`。
- 校验 `WorkflowInvocation` contract 中每个 workflow 的 execution mode、required/output artifacts、required gates、required capabilities 和 MCP dependency hints 与 spec 同步。
- 校验 SDD task graph 的 required inputs、node role agents、edge endpoints、fresh context 和 toolDependencies 与 workflow/tool manifest contract 同步。

## 5. 已执行验证

已经成功运行：

```bash
python3 -m py_compile lib/multica_runtime_spec.py lib/multica_runtime_builder.py lib/multica_runtime_verify.py
```

```bash
bash -n manage.sh build-multica-runtime.sh verify-multica-runtime.sh self-test.sh tests/multica-runtime-build-smoke.sh
```

```bash
bash tests/multica-runtime-build-smoke.sh ../superpowers
```

输出确认：

```text
Built Multica Superpowers runtime at <tmp>/multica-superpowers-runtime
Multica Superpowers runtime OK: <tmp>/multica-superpowers-runtime
wiki-context-json-render smoke test complete
multica-runtime-build smoke OK
```

`tests/multica-runtime-build-smoke.sh` 当前还会额外执行：

- `dist/tools/validators/runtime_capability_preflight.py` 成功样例。
- `dist/tools/validators/workflow_invocation_validate.py` 合法 SDD `WorkflowInvocation` 成功样例。
- 缺少 `wiki-context` 的非法 SDD `WorkflowInvocation` 失败样例。
- workflow metadata drift 负例：复制 bundle 后篡改 SDD workflow 的 `executionMode`，确认 `verify-multica-runtime` 会失败。
- SDD task graph 的 node、fresh context、review failure loop 和 `wiki_context_render.py` 引用检查。

也运行过：

```bash
./manage.sh verify
```

已安装 Superpowers adapter target 验证通过。

注意：

```bash
./manage.sh verify ../superpowers
```

失败过，原因是 `../superpowers` 是未安装 adapter overlay 的 upstream source tree，缺少 `agents/wiki-researcher.md` 等安装产物。这不是新 runtime 功能失败。

## 6. 当前未完成范围

与 `MULTICA_SUPERPOWERS_ADAPTER_REPLICATION_PLAN_CN.md` 的完整目标相比，以下仍未完成。

### 6.1 Multica runtime 注册与安装

未实现：

- 调用 Multica CLI / daemon 注册 bundle。
- 注册 workflows。
- 注册 role agents。
- 注册 gates / triggers / schemas。
- 注册 tool manifest。
- 配置 workspace / repo access。
- 配置 `MULTICA_SUPERPOWERS_RUNTIME_ROOT` 到 Multica runtime env。
- 真实 `--apply` 调用 Multica CLI / daemon 创建测试 issue。

已补充：`install-multica-runtime` dry-run 会结构化探测公开注册 surface；`multica-live-acceptance` dry-run 会按 Phase 3–6 规划可执行的真实 issue-assignment 验收命令；`--observe-runs` 会把验收切到 full bootstrap assignment 路径，并在 assignment 后通过公开只读 CLI surface 观察 issue runs。

### 6.2 真实 workflow runtime

未实现：

- `WorkflowInvocation` 在 Multica 中的真实创建、存储、校验和推进。
- orchestrator preflight 的真实运行逻辑。
- gate state 的真实阻塞/恢复。
- artifact store 的真实读写。
- workflow graph 的真实 stage transition。
- illegal transition rules 的真实 runtime enforcement。

当前已有 schema、trigger/gate 文件、orchestrator instructions、离线 `WorkflowInvocation` validator 和 preflight contract，但还没有接入真实 Multica runtime state / gate state / artifact API。

### 6.3 role task graph / fresh context

未实现：

- Multica task API 调用。
- fresh context role task 创建。
- implementer / reviewer / debugger / wiki-curator 的真实任务派发。
- task output artifact 收集。
- reviewer 不通过后回到 implementer 的循环。
- final-code-reviewer whole-implementation mode 的真实调度。

当前已有 role agent 文件、workflow YAML role references 和 `subagent-driven-development.task-graph.json` 合同，但还没有真实 Multica task API 调度或 fresh context task 创建。

### 6.4 SDD execution workflow

未实现真实执行：

- 读取 plan tasks。
- 顺序创建 implementer task。
- 每 task 调用 `wiki_context_render.py` 并注入 constraints。
- hardConstraint section 强制 reread 并注入 full section body。
- spec-compliance-reviewer / code-quality-reviewer 串联。
- final code review。
- finishing workflow handoff。

### 6.5 Lanhu Multica 端到端流程

未实现真实 Multica flow：

- Lanhu MCP capability preflight。
- role gate 在 Multica UI / issue 中确认。
- pageId lightweight tree selection 的实际 MCP 调用。
- per-page analyst fan-out task。
- analyst 写 `.lanhu/MM-DD-需求名称/` evidence package。
- confirmationGate 阻塞与恢复。
- 用户确认 `index.md` / `scopeConfirmationSummary` 后启动 brainstorming。

当前保留了 workflow / agents / instructions / MCP example，但没有真实运行。

### 6.6 shared wiki 双路径

未实现真实 Multica flow：

- local `.shared-superpowers/wiki` submodule publish workflow。
- shared wiki validators 在 Multica 中运行。
- publish hook / status hook 调用。
- GitHub-backed shared-wiki MCP read/search/validate/create PR。
- external PR creation authorization gate。
- branch / PR URL / changed files / validation summary 报告。

当前只有 workflow / role / MCP example / validator placeholder。

### 6.7 Autopilot

未实现真实 Autopilot：

- wiki health check 定期任务。
- release-check 定期任务。
- shared wiki index validation。
- stale section index audit。
- runtime capability drift check。

当前只有 autopilot markdown placeholder。

### 6.8 Multica UI / issue template / quick action / natural language router

未实现真实绑定：

- issue templates 注册到 Multica。
- quick actions 注册。
- natural language intent router 实现。
- artifact-driven next actions 实现。
- gate-aware next action suggestions。

当前只是生成对应 YAML/Markdown 文件。

### 6.9 完整 Phase 2–6 验收

已执行：

- Phase 3 standalone workflows 验证：WS-8 / WS-9 / WS-10。
- Phase 4 core development workflow 验证：WS-11 / WS-12。
- Phase 5 debug workflow 验证：WS-13 / WS-14。
- Phase 6 shared wiki 双路径验证：WS-15 / WS-16 / WS-17。

已执行：

- Phase 2 Multica runtime install substitute probe：`install-multica-runtime --dry-run --require-native-surfaces` 返回 `planned`，并生成 runtime registration issue、issue metadata set、issue comment attachment、issue get/runs、autopilot trigger substitute checks。每个 runtime capability 都要求 exact native command 或 documented substitute surface 覆盖；当前官方 CLI 下已由 substitute surface 覆盖并通过 smoke。

后续仅在官方 CLI 新增更专门的 runtime commands 时做无语义变化的迁移：

- 如果未来公开 exact native runtime-install/workflow/gate/trigger/schema/artifact/gate-state/MCP API，可把当前 issue metadata / run history / comment+attachment / autopilot trigger substitute 迁移到更专门的官方命令；当前 adapter 已提供可执行官方 CLI 路径。

## 7. 当前工作树状态提醒

当前有未提交改动，包括新增文件和文档修改。新 session 开始时建议先运行：

```bash
git status --short
```

预计会看到类似：

```text
 M ADAPTER_DEVELOPMENT_CN.md
 M ADAPTER_USER_FLOW_CN.md
 M CLAUDE.md
 M README.md
 M manage.sh
 M self-test.sh
?? build-multica-runtime.sh
?? multica-bootstrap.sh
?? lib/multica_runtime_builder.py
?? lib/multica_runtime_spec.py
?? lib/multica_runtime_verify.py
?? lib/multica_cli_bootstrap.py
?? tests/multica-runtime-build-smoke.sh
?? tests/multica-bootstrap-dry-run-smoke.sh
?? verify-multica-runtime.sh
?? MULTICA_SUPERPOWERS_ADAPTER_PROGRESS_CN.md
```

## 8. 新 session 建议继续方向

优先不要再新增本地 runtime 框架，也不要再把单个 `superpowers-adapter-orchestrator` 跑通全流程当作完成标准；该 adapter-specific 单 agent 路径已移除。当前下一步应沿真实 Multica role-agent/squad 用户路径推进，在一个已登录、daemon 在线、Claude Code runtime 可用且 role agents/squad 已安装的 workspace 中跑通 A-H 可视化验收。推荐顺序：

1. **更新真实 Multica workspace 资源**
   - 运行 `multica auth status`、`multica daemon status`、`multica runtime list`，确认 Claude Code runtime 在线。
   - 重新执行 `build-multica-runtime` / `install-multica-runtime --apply`，确保 `superpowers-*` role agents、`superpowers-runtime-squad` 和 `superpowers-adapter` skill pack 都是最新。
   - 如只需确认 skill pack 注入，可运行 `./manage.sh multica-bootstrap --superpowers-source <superpowers> --target-repo <disposable-project> --issue-template smoke --apply`，但这只算 compatibility smoke。

2. **执行 dry-run visual acceptance**
   - 运行 `./manage.sh multica-live-acceptance --target-repo <disposable-project> --case all ... --dry-run --json`。
   - 确认计划中包含 A-H stage issue fanout，assignee 覆盖 `superpowers-runtime-squad`、wiki-researcher、brainstorming、planning、implementer、reviewers、debugger、break-loop、wiki-curator、shared-wiki-publisher 等核心 role agents。
   - 确认没有任何 stage assign 给 `superpowers-adapter-orchestrator`。

3. **执行真实 A-H visual acceptance**
   - 对 disposable target repo 使用 `--apply --observe-runs`。
   - 用 `multica issue runs <stage-issue>` 确认每个 stage 产生对应 role-agent run。
   - blocked、user comment rerun、cancel、rerun 的生命周期必须停留在对应 stage issue，不得回退到单 agent 模式。

4. **基于真实结果修正 CLI flag / lifecycle 映射**
   - 如果 `issue create`、`issue assign`、`issue comment add`、`issue rerun`、`issue cancel-task` 或 `issue runs` 的 CLI flag 与当前假设不同，优先更新 `lib/multica_live_acceptance.py` 的探测和 manual step，不要绕 undocumented HTTP API。

5. **保留 runtime bundle contract 作为长期目标**
   - `build-multica-runtime` / `verify-multica-runtime` 继续作为 bundle contract 和未来 native runtime 注册目标。
   - 只有在 Multica 官方暴露 workflow/gate/schema 注册 API 或 CLI 后，再把现有 issue metadata / comments / runs / squad dispatch substitute 对齐到更专门的官方命令。

## 9. 关键代码入口

新 session 可优先阅读：

- `MULTICA_SUPERPOWERS_ADAPTER_REPLICATION_PLAN_CN.md`
  - 总目标和完整验收范围。
- `MULTICA_SUPERPOWERS_ADAPTER_PROGRESS_CN.md`
  - 当前进度。
- `lib/multica_runtime_spec.py`
  - expected artifacts 和常量。
- `lib/multica_runtime_builder.py`
  - bundle 生成逻辑。
- `lib/multica_runtime_verify.py`
  - bundle 校验逻辑。
- `tests/multica-runtime-build-smoke.sh`
  - runtime bundle smoke 验证路径。
- `lib/multica_cli_bootstrap.py`
  - 真实 Multica workspace bootstrap、skill pack 生成、CLI command planning / `--apply` 执行入口。
- `tests/multica-bootstrap-dry-run-smoke.sh`
  - workspace skill pack 和真实 CLI 命令计划 dry-run 验证路径。
- `lib/native_skill_patch.py`
  - 复用的 upstream skill patch source。
- `lib/sync_role_prd.py`
  - 复用的 Lanhu analyst agent 生成逻辑。
- `manifest.json`
  - adapter installed paths 和脚本清单来源。

## 10. 继续实现前建议验证命令

新 session 开始后建议先确认当前基础仍通过：

```bash
python3 -m py_compile lib/multica_runtime_spec.py lib/multica_runtime_builder.py lib/multica_runtime_verify.py lib/multica_cli_bootstrap.py
bash -n manage.sh build-multica-runtime.sh verify-multica-runtime.sh multica-bootstrap.sh self-test.sh tests/multica-runtime-build-smoke.sh tests/multica-bootstrap-dry-run-smoke.sh
bash tests/multica-runtime-build-smoke.sh ../superpowers
bash tests/multica-bootstrap-dry-run-smoke.sh ../superpowers
./manage.sh verify
```

如果有目标项目 root，也可以再运行：

```bash
./manage.sh release-check /path/to/project
```

但注意 `release-check` 会跑较多既有 smoke，并依赖已安装 Superpowers target 和目标项目状态。
