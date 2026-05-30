# Multica 中完整复刻 Superpowers + adapter 流程方案

本文说明如何把当前 `Superpowers + superpower-adapter` 的完整流程复刻进 Multica。目标是完整复刻，不删减任何能力；但本方案不要求用户本地 Claude Code 已安装 Superpowers plugin，也不把 adapter 简化成几个 Python 脚本。

新的目标形态是：**Multica 直接承载 Superpowers-compatible workflow runtime**，把 Superpowers + adapter 的流程、角色、门禁、wiki 机制、artifact contract 和执行边界复刻为 Multica-native workflow；MCP、本地文件、shell/git、任务隔离和 artifact 管理能力则作为 Multica agent runtime 的必备能力。

---

## 1. 结论

要在 Multica 中完整复刻当前流程，推荐直接采用第二版目标形态：

```text
Multica workspace / issues / comments / tasks / squads / autopilots
→ Multica-native Superpowers-compatible workflow runtime
→ Multica workflow graph / gates / role agents / artifact contracts
→ adapter tooling layer: wiki scripts / Lanhu tools / validators / MCP adapters
→ 目标项目中的 .superpowers/wiki/ 与 .shared-superpowers/wiki/
```

关键决策：

1. **Multica 不只是协作外壳，而是 workflow runtime。**
   - Multica 负责 issue、comment、agent、task、squad、autopilot。
   - Multica 同时负责 Superpowers workflow 的阶段图、状态机、门禁、任务拆分、角色分派和 artifact 管理。
   - Superpowers 的 brainstorming、writing-plans、executing-plans、subagent-driven-development、systematic-debugging、verification、finishing 等语义复刻为 Multica-native workflow。

2. **不要求用户本地 Claude Code 安装 Superpowers。**
   - 用户不需要在本机 Claude Code plugin 目录安装 Superpowers。
   - Multica 分发包内置 Superpowers-compatible prompts、agent roles、workflow definitions、schemas 和 adapter tools。
   - 上游 Superpowers skill 内容仍可作为构建来源，但构建产物是 Multica runtime 资源，不是 Claude Code plugin overlay。

3. **MCP 能力是 full fidelity 的必备 runtime 能力。**
   - Multica agent runtime 必须能消费 MCP。
   - Lanhu MCP、shared-wiki MCP、GitHub MCP 等具体 server 可按功能启用，但 runtime 层必须支持 MCP tool 调用。
   - 如果某个 Multica provider 不能调用 MCP、本地文件、shell/git 或 artifact API，则不属于 full fidelity mode。

4. **adapter Python 脚本仍是工具层，不是用户主入口。**
   - 用户入口是 Multica workflow、issue template、chat command 或 compatibility entrypoint。
   - `scripts/*.py` 作为 Multica tool runner 调用的执行层，负责机械文件操作、索引、验证、渲染和 patch 生成。
   - durable knowledge、ownership、semantic duplicate、shared neutrality 等判断仍由 agent 完成，不下放给 Python。

5. **原 Claude Code 内部 subagent-driven-development 提升为 Multica task graph。**
   - implementer、spec-document-reviewer、plan-document-reviewer、spec-compliance-reviewer、code-quality-reviewer、code-reviewer、wiki curator、debugger 等都成为 Multica role agents / task types。
   - 每个 leaf task 必须是 fresh context。
   - Multica 负责创建 task、注入输入 artifact、收集输出 artifact、推进 gate。

6. **触发方式 Multica-native 化，但统一归一到 WorkflowInvocation。**
   - 用户可以通过 issue template、quick action、自然语言、artifact next action 或兼容命令触发。
   - orchestrator 统一校验 artifact、gate、capability、MCP requirement 和 illegal transition rules。
   - intent router 只能建议或创建候选 workflow，不能绕过 Superpowers gate。

7. **保留 Superpowers + adapter 的所有产物结构。**
   - `.superpowers/wiki/` project wiki。
   - `.shared-superpowers/wiki/` shared wiki。
   - Lanhu evidence package。
   - spec / implementation plan。
   - schemaVersion 3 `.wiki-context.json`。
   - plan 中的 `Referenced Project Wiki`。
   - section marker、section index、hard constraint reread、root-specific authorization、shared neutrality。

---

## 2. 要完整复刻的流程范围

当前要复刻的是完整产品流程，而不是局部脚本能力：

```text
可选 Lanhu 原始需求证据包
→ Multica brainstorming workflow 写 spec
→ wiki-researcher 轻量披露 project/shared wiki
→ Multica writing-plans workflow 写 implementation plan
→ wiki-researcher 正式选择 wiki，生成 schemaVersion 3 .wiki-context.json
→ plan 写入 Referenced Project Wiki
→ Multica execution workflow 创建 implementer / spec-compliance-reviewer / code-quality-reviewer / code-reviewer task graph
→ 执行阶段只消费 plan 中已确认的 wiki context
→ bug 走 systematic-debugging workflow
→ systematic-debugging 修复并验证后进入 break-loop 复盘
→ update-wiki workflow 判断 durable implementation knowledge 并维护 project/shared wiki
→ 可选 shared wiki submodule 发布或 GitHub-backed shared-wiki MCP PR
```

必须保留的 adapter 增强点：

- `wiki-researcher` 渐进式选择 project/shared wiki。
- `.superpowers/wiki/` project wiki。
- `.shared-superpowers/wiki/` shared wiki。
- 可选 GitHub-backed shared-wiki MCP。
- 每个 wiki 叶子文档的 `<!-- wiki-section:... -->` section marker。
- 每个叶子文档伴随 `<stem>.index.md` section index。
- planning 阶段生成 schemaVersion 3 `.wiki-context.json`。
- plan 中保留轻量 `Referenced Project Wiki`。
- execution 阶段用 `wiki_context_render.py` 按 task / role 渲染约束。
- hard constraint section 强制回读 document context + selected section body。
- `update-wiki` agent-led durable knowledge 判断、语义去重、ownership 判断、shared neutrality、root-specific settings 授权策略。
- `break-loop` bug 后复盘。
- 可选 Lanhu 原始需求证据包流程。
- local shared wiki submodule publish 流程。
- GitHub-backed shared-wiki MCP validate patch + branch + PR 流程。

---

## 3. Multica 能力映射

| Superpowers + adapter 概念 | 当前承载 | Multica-native 复刻方式 |
|---|---|---|
| Superpowers 原生 workflow skills | `https://github.com/obra/superpowers.git` 中的 `skills/*/SKILL.md` | 构建为 Multica workflow definitions、role prompts、gate rules 和 artifact contracts |
| Superpowers enhanced standalone / maintenance skills | `overlays/skills/*/SKILL.md` | 构建为 Multica workflow entrypoints / compatibility commands / issue templates |
| adapter agents | `overlays/agents/*.md` | 转换为 Multica role agents，带独立 context、tool allowlist 和 artifact I/O |
| adapter scripts | `overlays/scripts/*.py` | 打包为 Multica tool runner 可调用的工具层 |
| native skill patch | `lib/native_skill_patch.py` | 构建时应用到 Multica workflow prompt source，而不是安装到 Claude Code plugin |
| hook patch | `lib/hook_patch.py` | Multica 版不依赖 Claude Code SessionStart hook；相同语义由 workflow preflight / gate 实现 |
| `.superpowers/wiki/` | project wiki root | 仍放在目标项目仓库 |
| `.shared-superpowers/wiki/` | shared wiki root / submodule | 仍放在目标项目仓库或 submodule |
| GitHub shared-wiki MCP | MCP server | 由 Multica runtime 直接消费 MCP |
| Superpowers worktree / finishing | native skills + adapter patch | 复刻为 Multica finishing workflow，底层仍使用 git/worktree/shell 能力 |
| Superpowers subagents | Claude Code 内部 subagents | 提升为 Multica task graph 中的 fresh role tasks |
| 自动周期任务 | 当前不是主流程 | 可选用 Multica Autopilot 做检查类任务，但不能替代主 workflow |

---

## 4. 推荐新增分发包

建议新建一个独立分发层，名称可以是：

```text
multica-superpowers-runtime/
```

它可以作为当前 adapter 的新增输出目标，也可以作为单独仓库存在。职责不是重写 adapter Python 执行层，而是把 `https://github.com/obra/superpowers.git` 和当前 `superpower-adapter` 组合成 Multica-native Superpowers-compatible workflow runtime。

推荐结构：

```text
multica-superpowers-runtime/
  manifest.json
  README.md
  build.sh
  verify.sh
  release-check.sh

  source/
    superpowers/                 # 从 https://github.com/obra/superpowers.git 获取，仅作为构建来源
    superpower-adapter/          # 当前 adapter 仓库

  dist/
    workflows/
      brainstorming.workflow.yaml
      writing-plans.workflow.yaml
      executing-plans.workflow.yaml
      subagent-driven-development.workflow.yaml
      systematic-debugging.workflow.yaml
      test-driven-development.workflow.yaml
      verification-before-completion.workflow.yaml
      finishing-a-development-branch.workflow.yaml
      update-wiki.workflow.yaml
      break-loop.workflow.yaml
      init-wiki.workflow.yaml
      import-wiki.workflow.yaml
      migrate-wiki.workflow.yaml
      lanhu-requirements.workflow.yaml
      shared-wiki-mcp.workflow.yaml
      publish-shared-wiki.workflow.yaml

    agents/
      superpowers-orchestrator.md
      brainstorming-agent.md
      planning-agent.md
      wiki-researcher.md
      implementer.md
      spec-document-reviewer.md
      plan-document-reviewer.md
      spec-compliance-reviewer.md
      code-quality-reviewer.md
      code-reviewer.md             # 包含 final-code-reviewer whole-implementation mode
      debugger.md
      break-loop-analyst.md
      wiki-curator.md
      finisher.md
      lanhu-frontend-requirements-analyst.md
      lanhu-backend-requirements-analyst.md
      shared-wiki-publisher.md

    gates/
      design-approval.yaml
      spec-approval.yaml
      lanhu-scope-confirmation.yaml
      wiki-update-authorization.yaml
      shared-wiki-publish-authorization.yaml
      external-pr-creation-authorization.yaml

    triggers/
      compatibility-commands.yaml
      issue-template-bindings.yaml
      intent-router.yaml
      artifact-next-actions.yaml
      illegal-transition-rules.yaml

    schemas/
      workflow-invocation.schema.json
      spec.schema.json
      implementation-plan.schema.json
      wiki-context-v3.schema.json
      lanhu-evidence-package.schema.json
      update-wiki-candidate.schema.json
      review-result.schema.json
      gate-state.schema.json

    tools/
      tool-manifest.json
      scripts/
        update-wiki.py
        wiki-context.py
        wiki_context_render.py
        wiki_common.py
        wiki_section.py
        wiki_read_section.py
        wiki_generate_section_index.py
        wiki_import.py
        init-wiki.py
        wiki_update_check.py
        wiki_select_target.py
        wiki_apply_update.py
        wiki_migrate_helper.py
        lanhu_settings.py
      validators/
        wiki-health-check.md
        runtime-capability-check.md
        neutrality-guard.md

    mcp/
      required-capabilities.yaml
      lanhu-mcp.example.yaml
      shared-wiki-mcp.example.yaml
      github-mcp.example.yaml

    multica/
      agent-instructions.md
      issue-templates/
        01-lanhu-requirements.md
        02-brainstorming.md
        03-writing-plan.md
        04-execute-plan.md
        05-debug-bug.md
        06-update-wiki.md
        07-shared-wiki-publish.md
      autopilots/
        wiki-health-check.md
        release-check.md
```

---

## 5. 构建策略

### 5.1 不要手工复制，新增构建入口

建议在当前 adapter 的 `manage.sh` 中新增命令：

```bash
./manage.sh build-multica-runtime https://github.com/obra/superpowers.git . ./dist/multica-superpowers-runtime
./manage.sh verify-multica-runtime ./dist/multica-superpowers-runtime
```

或在新仓库中提供：

```bash
./build.sh --superpowers https://github.com/obra/superpowers.git --adapter . --out ./dist
./verify.sh ./dist
```

构建动作：

1. 读取 Superpowers 原生 skill 目录作为 prompt source。
2. 解析原生 workflow skills 的规则、门禁、artifact 要求和禁止事项。
3. 应用当前 adapter 的 native skill patch。
4. 生成 Multica workflow definitions。
5. 生成 Multica role agents。
6. 复制 adapter overlay agents / skills / scripts。
7. 把 enhanced standalone skills 转换为 Multica workflow entrypoints。
8. 生成 gates、triggers、schemas、tool manifest、issue/chat templates。
9. 生成 `workflow-invocation.schema.json`、intent router 规则、artifact-driven next action 规则和 illegal transition rules。
10. 替换脚本 root 占位符。
11. 生成 Multica runtime instructions。
12. 生成 manifest。
13. 运行 runtime 级校验。

### 5.2 runtime-root 替换策略

当前 adapter 安装到 Claude Code plugin 后，会把：

```text
__SUPERPOWER_ADAPTER_PLUGIN_ROOT__
```

替换成实际 plugin root。

Multica-native 版不依赖 Claude Code plugin root，推荐替换为：

```text
$MULTICA_SUPERPOWERS_RUNTIME_ROOT/tools/scripts/wiki_context_render.py
```

并在 Multica agent custom env 或 tool runner 配置中提供：

```text
MULTICA_SUPERPOWERS_RUNTIME_ROOT=<Multica daemon 本地同步后的 runtime root>
```

verify 必须检查：

- `MULTICA_SUPERPOWERS_RUNTIME_ROOT` 存在。
- `tools/scripts/` 可读。
- Python 运行环境可用。
- scripts 可执行或可由 tool runner 调用。
- MCP capability 可用。
- 本地 repo 文件读写、shell、git 能力可用。
- 没有 unresolved `__SUPERPOWER_ADAPTER_PLUGIN_ROOT__`。
- 没有把 `python3 overlays/scripts/` 暴露为用户入口。

---

## 6. Multica-native workflow 与 agent taxonomy

### 6.1 主 orchestrator

建议创建一个主 orchestrator：

```text
Agent name: superpowers-orchestrator
Runtime: Multica-native agent runtime
Visibility: workspace
Responsibilities:
  - 识别用户意图并启动对应 workflow
  - 维护 workflow state
  - 创建 role tasks
  - 注入 artifact references
  - 推进 gates
  - 汇总结果到 issue/comment
  - 防止绕过 Superpowers-compatible workflow
Required capabilities:
  - local filesystem
  - shell/git/worktree
  - MCP client
  - task creation
  - artifact read/write
  - gate state management
```

orchestrator 不直接替代所有角色的工作。它负责控制平面，具体研究、计划、实现、review、debug、wiki 维护由 role agents 完成。

### 6.2 role agents

建议的 Multica role agents：

| Role agent | 职责 | Fresh context 要求 |
|---|---|---|
| `brainstorming-agent` | 与用户澄清需求、提出方案、写 spec | 每个 spec 独立 context |
| `planning-agent` | 读取确认后的 spec，写 implementation plan | 每个 plan 独立 context |
| `wiki-researcher` | 渐进式选择 project/shared wiki | 每次调用独立 context |
| `implementer` | 执行单个 plan task | 每个 task 独立 context |
| `spec-document-reviewer` | brainstorming 后审查 spec 文档是否完整、清晰、可进入 planning | 每个 spec 独立 context |
| `plan-document-reviewer` | writing-plans 后审查 implementation plan 是否完整、可执行、无遗漏 | 每个 plan 独立 context |
| `spec-compliance-reviewer` | 每个 implementer task 后审查实现是否符合 spec / plan / task contract | 每个 task 独立 context |
| `code-quality-reviewer` | spec compliance 通过后审查代码质量、风险、测试和可维护性 | 每个 task 独立 context |
| `code-reviewer` | 通用代码审查 template；final code review 是该 template 的 whole-implementation mode | 每次调用独立 context |
| `debugger` | systematic-debugging root cause 调查与修复 | 每个 bug 独立 context |
| `break-loop-analyst` | bug 后复盘与防复发判断 | 每次复盘独立 context |
| `wiki-curator` | update-wiki durable knowledge 审查和写入 | 每次 wiki update 独立 context |
| `finisher` | finishing-a-development-branch | 每次 branch finishing 独立 context |
| `lanhu-* analyst` | 按页面和角色生成 Lanhu evidence package | 每个 selected page 独立 context |
| `shared-wiki-publisher` | local submodule publish 或 MCP PR 准备 | 每次发布独立 context |

Reviewer 必须按 Superpowers 源 prompt 的 contract 细分。Multica UI 可以把这些 task 归到同一个 Reviewer group，但 workflow 内部不能把以下角色合并成一个泛化的 `spec-reviewer`：

- `spec-document-reviewer`：审查 spec 文档本身是否可进入 planning。
- `plan-document-reviewer`：审查 plan 文档本身是否可进入 execution。
- `spec-compliance-reviewer`：审查某个 task 的实现是否符合 spec / plan。
- `code-quality-reviewer`：在 spec compliance 通过后审查代码质量。
- `code-reviewer`：通用代码审查 template；`final-code-reviewer` 是它用于全量实现的运行模式，不是新的 Superpowers persona。

### 6.3 fresh context 规则

Multica 必须把以下边界实现为 task/context 隔离，而不是在一个长上下文里切换角色：

- 每个 implementer task。
- 每个 spec-document-reviewer task。
- 每个 plan-document-reviewer task。
- 每个 spec-compliance-reviewer task。
- 每个 code-quality-reviewer task。
- 每次 code-reviewer task，包括 final-code-reviewer mode。
- 每次 wiki-researcher 调用。
- 每个 Lanhu selected page analyst。
- 每次 debugger 调查。
- 每次 update-wiki candidate review。

### 6.4 execution 并发策略

第一版 Multica-native execution 默认应采用顺序执行：

```text
Task N implement
→ Task N spec compliance review
→ Task N code quality review
→ next task
→ final code review
```

只有当 plan 明确标记 task 互不冲突，且 Multica runtime 支持 worktree / patch queue / conflict resolution 时，才允许并行 implementer tasks。

并行执行必须满足：

- 每个 implementer 在独立 worktree 或 patch branch 中工作。
- reviewer review 对应 patch。
- orchestrator 负责合并顺序和冲突处理。
- 不允许多个 implementer 无隔离地同时写同一个 working tree。

---

## 7. Multica enhanced standalone workflow 设计

这些入口当前是 adapter standalone skills；迁移到 Multica 时改为 workflow entrypoints，但保留原 skill 名作为 compatibility command。

### 7.1 `init-wiki` workflow

Multica 用户入口：

```text
请使用 init-wiki 初始化当前项目的 project wiki。
```

或：

```text
请使用 init-wiki 初始化 shared wiki starter knowledge，重点关注前端公共组件约定。
```

必须保留规则：

- 这是 standalone workflow，不触发 development workflow。
- 不触发 planning / implementation / review / completion / verification。
- 先确认当前 repo root。
- 确认 `.superpowers/wiki/index.md` 或 `.shared-superpowers/wiki/index.md` 至少一个存在。
- 运行 inventory 脚本。
- agent 读取 relevant indexed wiki pages。
- agent 判断是否需要写 starter notes。
- Python 不判断 durable rules、不判断 ownership、不生成未验证硬约束。
- 写入前遵守 root-specific settings。
- shared wiki 内容必须中性、可迁移。
- 写入后刷新对应 root index。
- 完成后提醒后续 durable knowledge 用 `update-wiki` workflow。

### 7.2 `import-wiki` workflow

Multica 用户入口：

```text
请使用 import-wiki 把 docs/old-wiki 导入 .superpowers/wiki/。
```

必须保留规则：

- 结构导入，不做语义合并。
- 保留用户提供内容。
- 不覆盖已有不同内容。
- 默认 project wiki，除非用户明确 shared 或内容显然跨项目。
- shared import 必须 neutral。
- 遵守 `createNewDocument` 授权策略。
- 导入后刷新 index。
- 如果后续需要语义整理，交给 `update-wiki` workflow。

### 7.3 `migrate-wiki` workflow

Multica 用户入口：

```text
请使用 migrate-wiki 把现有 wiki 迁移到 section-marker 格式。
```

必须保留规则：

- 迁移叶子文档到 `<!-- wiki-section:... -->` 格式。
- 为每个 leaf page 生成 `<stem>.index.md`。
- 不把 index 当详细规则承载页。
- 不改变 project/shared ownership。
- 遵守 root settings。
- shared wiki 仍需 neutrality guard。

### 7.4 `lanhu-requirements` workflow

Multica 用户入口：

```text
请使用 lanhu-requirements 处理这个蓝湖链接，角色：前端，需求名：账户设置。
<蓝湖链接>
```

必须保留规则：

- Multica runtime 必须支持 MCP；Lanhu 功能需要 Lanhu MCP server 可用。
- role 必须先确定：frontend 或 backend。
- 如果 role 缺失且 `.superpowers/settings.json` 没配置，先问用户。
- 如果用户说全栈，要求先选一个角色，建议分两次生成。
- frontend 始终输出统一 `role-prd/` 包：`role-prd/prd.md`，以及仅在有设计稿或需要交互 demo 时输出的 `role-prd/design/index.html` / `assets/`。
- 已废弃的 `lanhu.frontend.output.format` 只允许作为兼容性 warning 被忽略，不能再改变 frontend 路由或产物结构。
- backend 永远 Markdown-only。
- URL 带 pageId 时，主会话只允许读取 lightweight page tree metadata。
- 主会话在派发 analyst 前不得调用 full scoped evidence。
- 每个 selected page 派发一个 role-and-format-specific analyst task。
- analyst task 才读取 scoped evidence。
- selective image analysis：图片默认只是候选证据，不全量视觉解析，不默认保存图片资产。
- 输出 `.lanhu/MM-DD-需求名称/` evidence package。
- `index.md` 是稳定入口。
- 多页面时 aggregate `index.md` 只做清单、关系、阅读顺序和确认状态，不从 compact summary 合成全局详细 HTML。
- Lanhu 包是 Superpowers-compatible workflow 输入证据，不是 spec、验收标准、测试计划、技术方案或 implementation plan。
- analyst 返回 `need_confirmation` 时，主会话只展示紧凑 blocking questions。
- `confirmationGate.status: clear` 且用户确认 `index.md` 和 `scopeConfirmationSummary` 后，才能进入 brainstorming workflow。

### 7.5 `shared-wiki-mcp` workflow

Multica 用户入口：

```text
请使用 shared-wiki-mcp 检查 GitHub shared wiki 是否已有关于表单 payload 的规则，如果没有，准备一个 PR。
```

必须保留规则：

- 只用于 GitHub-backed shared wiki MCP 手动流程。
- 不替代 normal `wiki-researcher` progressive selection。
- 不直接写 `.shared-superpowers/wiki/`。
- 不 merge PR。
- agent 判断 durable / shared ownership / neutrality。
- MCP 只做 read/search/validate patch/create PR 等机械动作。
- validate patch 通过后，且用户授权写入范围后，才 create patch PR。
- 返回 branch、PR URL、changed files、validation summary。
- 不声称 PR 已 merge 或 shared wiki 已发布。

### 7.6 `publish-shared-wiki` workflow

Multica 用户入口：

```text
请使用 publish-shared-wiki 发布本地 .shared-superpowers/wiki submodule 变更。
```

必须保留规则：

- 只用于本地 shared wiki submodule/repo 发布。
- 不用于 GitHub-backed MCP flow。
- 不替代 `update-wiki` durable knowledge review。
- 不自动 commit / push，必须确认 scope。
- 先运行 project-local verify hook。
- 再运行 shared wiki mechanical validator，包括 neutrality guard。
- 用户确认后运行 publish hook。
- 最后运行 status hook。
- 报告 parent repo submodule pointer 状态。

---

## 8. Multica runtime instructions 与 workflow 触发

### 8.1 触发入口归一化

Multica 中不应要求用户长期记忆完整 Superpowers workflow 名称。推荐提供多入口触发，但所有入口最终都归一为同一个 `WorkflowInvocation`，由 `superpowers-orchestrator` 统一校验 artifact、gate、capability 和 workflow state。

允许的触发入口：

1. **Compatibility commands**：保留 Superpowers 风格显式入口，降低迁移成本。
2. **Issue templates / quick actions**：让用户通过 Multica UI 选择任务类型，模板写入结构化 metadata。
3. **Natural language intent router**：根据自然语言建议 workflow，但不能越过 gate。
4. **Artifact-driven next actions**：根据已生成 artifact 和 gate 状态提示下一步。
5. **Workflow API / automation entrypoint**：供 Multica 内部 task、squad、autopilot 发起受限 workflow。

所有入口归一为：

```yaml
WorkflowInvocation:
  workflowId: brainstorming | writing-plans | execution | systematic-debugging | update-wiki | init-wiki | import-wiki | migrate-wiki | lanhu-requirements | shared-wiki-mcp | publish-shared-wiki
  triggerSource: compatibility-command | issue-template | quick-action | natural-language-router | artifact-next-action | workflow-api
  targetRepo: <repo root or workspace repo id>
  userIntent: <original user request>
  sourceArtifacts:
    - path: <spec / plan / lanhu package / wiki context / failure log>
      type: spec | implementation-plan | lanhu-evidence-package | wiki-context | failure-evidence | patch | wiki-page
  gates:
    required:
      - <gate id>
    satisfied:
      - <gate id>
  requiredCapabilities:
    - local-filesystem
    - shell-git
    - artifact-store
    - task-isolation
    - mcp-client
  mcpRequirements:
    - name: lanhu
      requiredFor: lanhu-requirements
      optionalOtherwise: true
  executionMode: multica-sdd-task-graph | inline-sequential | standalone | debug | maintenance
```

orchestrator 启动 workflow 前必须执行 preflight：

- 确认 `workflowId` 与用户意图匹配。
- 确认 target repo 可访问。
- 确认所需 artifact 存在且 schema 合法。
- 确认前置 gate 已通过，未通过则提示下一步而不是继续执行。
- 确认 required runtime capabilities 可用。
- 确认所需 MCP server 可用；如果缺失，只阻塞依赖该 MCP 的 workflow。
- 确认不会从 feature request 直接跳到 execution，或从 unconfirmed Lanhu evidence 直接跳到 brainstorming。

### 8.2 触发方式设计

#### Compatibility commands

保留以下显式入口：

```text
请进入 brainstorming workflow ...
请进入 writing-plans workflow ...
请执行这个 plan ...
请进入 systematic-debugging workflow ...
请使用 init-wiki ...
请使用 lanhu-requirements ...
请使用 update-wiki 检查是否需要沉淀长期知识 ...
```

这类入口可直接创建 `WorkflowInvocation`，但仍必须经过 orchestrator preflight 和 gate 校验。

#### Issue templates / quick actions

推荐提供 Multica-native 模板：

| Template / quick action | 默认 workflowId | 必填 artifact / metadata |
|---|---|---|
| New Feature / Behavior Change | `brainstorming` | targetRepo、需求描述、可选 Lanhu package |
| Write Implementation Plan | `writing-plans` | approved spec |
| Execute Approved Plan | `execution` | reviewed implementation plan、wiki context sidecar |
| Bug / Test Failure | `systematic-debugging` | failure evidence、复现步骤或日志 |
| Lanhu Requirement Intake | `lanhu-requirements` | Lanhu URL、role、需求名 |
| Wiki Initialization / Import | `init-wiki` 或 `import-wiki` | target wiki root、source path |
| Update Durable Knowledge | `update-wiki` | completed task summary、changed files、verification result |
| Publish Shared Wiki | `publish-shared-wiki` 或 `shared-wiki-mcp` | publish path 或 MCP target |

模板写入 metadata 后，用户不需要在正文中写 workflow 名称。

#### Natural language intent router

自然语言 router 只负责把用户意图映射到候选 workflow，并解释原因；在 workflow 不明确、artifact 缺失或 gate 未满足时，应先询问或提示下一步。

| 用户说法 | 候选 workflow | 约束 |
|---|---|---|
| “我要做一个新功能 / 改一个行为” | `brainstorming` | 不允许直接 execution |
| “基于这个需求写方案 / 写 spec” | `brainstorming` | 如果来自 Lanhu，必须先确认 evidence package |
| “spec 已确认，写计划” | `writing-plans` | 必须有 approved spec |
| “这个 plan 可以开始做” | `execution` | 必须有 reviewed plan 和 wiki context sidecar |
| “测试失败 / 线上 bug / 异常行为” | `systematic-debugging` | Phase 1 前不建议修复 |
| “沉淀一下经验 / 更新知识库” | `update-wiki` | 先判断 durable knowledge |
| “蓝湖链接 / 处理这个蓝湖需求” | `lanhu-requirements` | 需要 role gate 和 Lanhu MCP |
| “发布 shared wiki” | `publish-shared-wiki` 或 `shared-wiki-mcp` | 必须区分 local submodule 与 MCP PR path |

#### Artifact-driven next actions

这是 Multica-native 触发的主要优化。orchestrator 应根据 artifact 和 gate 状态在 issue/comment 中提示下一步：

```text
Lanhu package generated + confirmationGate: clear + user confirmed scope
→ Suggest: Start brainstorming

Spec document reviewer passed + user approved spec
→ Suggest: Write implementation plan

Plan document reviewer passed + .wiki-context.json exists
→ Suggest: Execute via Multica SDD task graph or inline sequential execution

All implementation tasks reviewed + final code review passed
→ Suggest: Finish branch

Finishing completed + verification passed
→ Suggest: Check update-wiki

Bug fixed + verified
→ Suggest: Run break-loop, then consider update-wiki
```

next action 只能建议或创建待确认 action；不得自动跳过需要用户确认的 gate。

#### 非法跳转拦截

orchestrator 必须拒绝或重定向以下请求：

- feature / behavior change 没有 spec 和 plan，却要求直接 implementation。
- Lanhu evidence package 未确认，却要求进入 brainstorming。
- plan 缺少 `.wiki-context.json` 或 `Referenced Project Wiki`，却要求 execution。
- systematic-debugging Phase 1 尚未完成，却提出修复方案。
- update-wiki 被当作 implementation completion proof。
- shared wiki publish / PR creation 未授权就执行外部可见副作用。

### 8.3 runtime instructions

建议给 `superpowers-orchestrator` 配置以下 instructions：

```markdown
你是 Multica 中的 Superpowers-compatible workflow orchestrator。

核心规则：

1. Multica 是 workflow runtime，不依赖用户本地 Claude Code 安装 Superpowers plugin。
2. 所有 feature / behavior change / creative work 必须先进入 brainstorming workflow。
3. 有确认后的 spec，才进入 writing-plans workflow。
4. 有 implementation plan，才进入 execution workflow 或 subagent-driven-development workflow。
5. bug、test failure、unexpected behavior 必须进入 systematic-debugging workflow，先查 root cause，再修复。
6. bug 修复并验证后，如需要复盘，进入 break-loop workflow。
7. 任务结束后判断是否存在 durable implementation knowledge；只有存在时才进入 update-wiki workflow。
8. Python scripts 是工具层，不是用户主入口。
9. project wiki 在 .superpowers/wiki/，shared wiki 在 .shared-superpowers/wiki/。
10. planning 阶段必须通过 wiki-researcher 正式选择 wiki，生成 schemaVersion 3 .wiki-context.json，并在 plan 中写 Referenced Project Wiki。
11. execution 阶段只消费 plan 中已确认的 Referenced Project Wiki，不重新选择 wiki。
12. shared wiki 内容必须保持中性、可迁移。
13. 遵守 .superpowers/settings.json 和 .shared-superpowers/settings.json 的 wiki.updateAuthorization 策略。
14. role agents 必须使用 fresh context；不要用一个长上下文模拟 implementer、各类 reviewer contract、debugger、wiki-curator。
15. 需要外部可见副作用时，必须通过对应 gate 获取用户授权，例如 commit/push、PR 创建、shared wiki publish。
16. 如果 runtime 缺少 MCP、本地文件、shell/git、artifact 或 task isolation 能力，必须报告 full fidelity 不满足，不要静默降级。
```

---

## 9. Multica 用户完整流程

### 9.1 一次性安装

```text
1. 安装 Multica CLI / Desktop。
2. 登录 Multica。
3. 启动 multica daemon。
4. 安装 multica-superpowers-runtime。
5. 注册 workflow definitions、role agents、gates、triggers、schemas、tool manifest。
6. 注册 issue templates、quick actions、intent router、artifact-driven next actions。
7. 配置 target repo access。
8. 配置 runtime env：MULTICA_SUPERPOWERS_RUNTIME_ROOT。
9. 配置必备 runtime capabilities：MCP、本地文件、shell/git、artifact、task isolation。
10. 配置可选 MCP server：Lanhu、shared-wiki、GitHub。
11. 运行 verify-multica-runtime。
12. 创建测试 issue。
```

### 9.2 初始化 wiki

用户在 Multica issue/chat 中说：

```text
请使用 init-wiki 初始化当前项目的 project wiki。
```

agent 行为：

1. orchestrator 启动 `init-wiki.workflow`。
2. 确认 repo root。
3. 检查 `.superpowers/wiki/index.md` 或 `.shared-superpowers/wiki/index.md`。
4. 如果没有，提示先 bootstrap。
5. 运行 inventory tool。
6. 派发 `wiki-curator` 读取 relevant indexed pages。
7. 判断是否写入 starter notes。
8. 遵守授权策略。
9. 刷新 index。
10. 报告写入文件和 caveats。

### 9.3 可选 Lanhu 证据包

用户创建 issue：

```text
请使用 lanhu-requirements 处理这个蓝湖链接，角色：前端，需求名：会员充值。
<蓝湖链接>
```

agent 行为：

1. orchestrator 启动 `lanhu-requirements.workflow`。
2. 确认 role。
3. 检查 Lanhu MCP server 可用。
4. 读取 Lanhu output settings。
5. 如 URL 带 pageId，只读 lightweight page tree。
6. 选择 selectedTargetPages。
7. 必要时让用户确认页面选择。
8. 每页创建对应 analyst task。
9. analyst 写 `.lanhu/.../` evidence package。
10. orchestrator 只接收轻量摘要。
11. 如有 blocking questions，等待用户回答并回传 analyst task。
12. `confirmationGate.status: clear` 后，让用户确认 `index.md` 和 `scopeConfirmationSummary`。
13. 用户确认后，才允许进入 brainstorming workflow。

### 9.4 brainstorming workflow

用户说：

```text
请基于 .lanhu/05-24-会员充值/index.md，进入 brainstorming workflow 生成 spec。
```

agent 行为：

1. orchestrator 创建 `brainstorming-agent` task。
2. brainstorming-agent 探索项目上下文。
3. 如果任务相关，orchestrator 创建 `wiki-researcher` task：

```yaml
task: <用户需求>
phase: brainstorm
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
sharedWikiSource: auto
maxWikiPages: 5
```

4. brainstorming 阶段只轻量披露 index / section index 信息，不读大量 section body。
5. brainstorming-agent 与用户一问一答明确需求。
6. 提出 2-3 个方案和 trade-off。
7. 用户确认设计。
8. 写 spec：

```text
docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md
```

9. spec self-review。
10. 创建 fresh `spec-document-reviewer` task，审查 spec 是否完整、清晰、可进入 planning。
11. spec-document-reviewer 通过后进入 spec approval gate，等待用户 review/approve。

### 9.5 writing-plans workflow

用户说：

```text
spec 已确认，请进入 writing-plans workflow 写 implementation plan。
```

agent 行为：

1. orchestrator 验证 spec approval gate 已通过。
2. 创建 `planning-agent` task。
3. 在拆任务前创建 `wiki-researcher phase: plan` task。
4. 从 `.superpowers/wiki/index.md` 和 selected shared source 渐进读取。
5. 只选择有 `<stem>.index.md` 的 leaf pages。
6. 对 candidate sections 读取 full text。
7. planning-agent 生成：

```text
docs/superpowers/plans/YYYY-MM-DD-<feature>-plan.md
docs/superpowers/plans/YYYY-MM-DD-<feature>-plan.wiki-context.json
```

8. `.wiki-context.json` 必须为 schemaVersion 3 page-rooted 结构。
9. 每个 page 只保留一份 bounded `documentContext`。
10. sections 保留：
    - sectionId
    - appliesTo
    - hardConstraint
    - categorized constraints：implementation / test / review / general
    - source anchors
    - caveats
11. plan 中写轻量入口：

```markdown
## Referenced Project Wiki

- Context sidecar: `docs/superpowers/plans/<plan>.wiki-context.json`
- Selected pages: ...
- Hard constraints: ...
```

12. 创建 fresh `plan-document-reviewer` task，审查 plan 是否完整、可执行、任务边界清晰、wiki context 引用正确。
13. plan-document-reviewer 通过后，用户选择执行策略：
    - Multica SDD task graph
    - Inline sequential execution workflow

### 9.6 执行 plan

#### 方式 A：Multica SDD task graph

agent 行为：

1. orchestrator 读取 plan。
2. 提取所有 tasks。
3. 创建 Multica task tracking。
4. 默认按 task 顺序执行。
5. 每个 task 创建 fresh `implementer` task。
6. implementer task 输入必须包含：
   - task text
   - relevant files
   - rendered wiki constraints
   - hard constraint reread content
   - allowed tools
   - expected output artifact
7. implementer 完成后创建 fresh `spec-compliance-reviewer` task。
8. spec-compliance-reviewer 通过后创建 fresh `code-quality-reviewer` task。
9. 任一 reviewer 不通过则回到 implementer 修复，并按原顺序重新 review。
10. 所有 task 完成后创建 fresh `code-reviewer` task，以 final-code-reviewer whole-implementation mode 审查全量实现。
11. final code review 通过后进入 finishing workflow。
12. 任务结束后考虑 update-wiki workflow。

#### 方式 B：inline sequential execution workflow

agent 行为：

1. orchestrator 创建一个 sequential execution task。
2. 读取 plan。
3. critical review。
4. 如无 blocker，逐 task 执行。
5. 每个 task 执行前用 `wiki_context_render.py` 渲染 task-specific constraints。
6. 不重新选择 wiki。
7. 执行 verification。
8. 完成后进入 finishing workflow。
9. 任务结束后考虑 update-wiki workflow。

### 9.7 bug / test failure

用户说：

```text
请进入 systematic-debugging workflow 调查这个失败。
```

agent 行为：

1. orchestrator 创建 `debugger` task。
2. Phase 1：复现、读错误、查近期变更、收集证据、trace data flow。
3. Phase 1 前不得提出修复。
4. 只有证据收窄到具体组件、契约、workflow 或 known gotcha 时，才创建 `wiki-researcher phase: debug` task：

```yaml
task: <bug 描述>
phase: debug
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
maxWikiPages: 2
```

5. debug 阶段 wiki 只是待验证线索。
6. 继续用代码、日志、测试、复现验证 root cause。
7. 写 failing test 或最小复现。
8. 修 root cause。
9. 验证 fix。
10. 如需要防复发复盘，创建 `break-loop-analyst` task。
11. `break-loop-analyst` 输出是否需要 handoff 给 `update-wiki`。
12. `update-wiki` 再独立判断是否写 wiki。

### 9.8 update-wiki workflow

agent 在任务结束后判断：

```text
这次工作是否产生了 durable implementation knowledge？
```

如果没有：

```text
No wiki update: <明确 skip reason>
```

如果有，进入 `update-wiki.workflow`：

1. 默认从不更新开始。
2. 只 promotion durable、reusable、future-useful knowledge。
3. 排除 local business logic、一次性 incident、代码显而易见事实、临时 plan/PR 信息。
4. 拆 atomic candidates。
5. 创建 `wiki-curator` task。
6. 读取 `.superpowers/wiki/index.md` 和 `.shared-superpowers/wiki/index.md`。
7. 渐进读取相关 indexed pages。
8. 检查语义重复。
9. 判断 target ownership。
10. shared wiki 内容必须 neutral。
11. 检查目标 page 是否过大或语义混杂。
12. 读取 root settings：

```text
.superpowers/settings.json
.shared-superpowers/settings.json
```

13. 遵守：

```text
wiki.updateAuthorization.updateExistingPage: skip | ask | refuse
wiki.updateAuthorization.createNewDocument: skip | ask | refuse
```

14. 如果 ask，进入 wiki update authorization gate。
15. 如果 refuse，停止写入并报告。
16. 编辑 leaf wiki page。
17. 保留或新增 section markers。
18. 生成 per-document section index。
19. 刷新对应 root index。
20. 运行 mechanical validator。
21. 报告更新文件和 caveats。

如果 target 是 GitHub-backed shared wiki MCP：

1. 不直接写本地 `.shared-superpowers/wiki/`。
2. 用 MCP read/search 查重复。
3. 准备 neutral unified diff。
4. 调 `shared_wiki_validate_patch`。
5. 通过后进入 external PR creation authorization gate。
6. 用户授权后调 `shared_wiki_create_patch_pr`。
7. 报告 branch、PR URL、changed files、validation summary。
8. 不声称已 merge。

---

## 10. Autopilot 使用边界

Multica Autopilot 可以增加辅助能力，但不能替代主流程。

允许使用 Autopilot：

- 定期 wiki health check。
- 定期 release-check。
- shared wiki index validation。
- stale section index audit。
- 每周提示未发布 shared wiki submodule 状态。
- runtime capability drift check。

不允许使用 Autopilot 自动执行：

- brainstorming。
- writing-plans。
- implementation。
- update-wiki 写入。
- shared wiki publish。
- GitHub shared wiki PR 创建。

原因：这些步骤都有用户确认、设计审批、授权策略或外部可见副作用，不能自动化跳过。

---

## 11. Squads 使用建议

Multica-native 方案中，squads 可以成为一等抽象：

```text
Squad: Superpowers Delivery Squad
Leader: superpowers-orchestrator
Members:
  - brainstorming-agent
  - planning-agent
  - wiki-researcher
  - implementer
  - spec-document-reviewer
  - plan-document-reviewer
  - spec-compliance-reviewer
  - code-quality-reviewer
  - code-reviewer
  - debugger
  - break-loop-analyst
  - wiki-curator
  - finisher
```

建议边界：

- Squad 用于 role taxonomy 和 issue-level / task-level routing。
- Workflow graph 仍由 `superpowers-orchestrator` 控制。
- role agents 不自行跳过 gates。
- implementer、各类 reviewer contract、debugger、wiki-curator 必须 fresh context。
- 涉及 shared state 的写操作由 orchestrator 串行化，避免多个 agents 同时写同一 working tree。

---

## 12. 实施阶段计划

### Phase 1：构建 Multica-native runtime

目标：生成可安装到 Multica 的 Superpowers-compatible runtime。

任务：

1. 新增 `build-multica-runtime`。
2. 从 `https://github.com/obra/superpowers.git` 获取 Superpowers 源码作为 prompt source。
3. 应用 adapter native skill patch。
4. 生成 workflow definitions。
5. 生成 role agents。
6. 生成 gates。
7. 生成 triggers：compatibility commands、issue-template bindings、intent router、artifact next actions、illegal transition rules。
8. 生成 schemas，包括 `workflow-invocation.schema.json`。
9. 复制 adapter scripts 到 tool layer。
10. 生成 tool manifest。
11. 生成 MCP capability manifest。
12. 生成 Multica runtime instructions。
13. 生成 issue templates。
14. 生成 manifest。
15. 新增 `verify-multica-runtime`。

验收：

```bash
./manage.sh build-multica-runtime https://github.com/obra/superpowers.git . ./dist/test
./manage.sh verify-multica-runtime ./dist/test
```

检查项：

- 所有 expected workflows 存在。
- 所有 expected role agents 存在。
- 所有 expected gates 存在。
- 所有 expected triggers 存在。
- 所有 expected schemas 存在，包括 `workflow-invocation.schema.json`。
- 所有 expected scripts 存在。
- 没有 unresolved `__SUPERPOWER_ADAPTER_PLUGIN_ROOT__`。
- 没有 `python3 overlays/scripts/`。
- 没有 `python3 superpowers/scripts/`。
- 没有用户项目相对 `python3 scripts/wiki_*`。
- 所有 standalone workflows 保留原边界、gates、禁止触发 completion 的规则，并包含 Multica 入口示例。
- patched Superpowers workflow prompts 包含 adapter 要求的 workflow 文案。
- runtime manifest 声明 MCP、本地文件、shell/git、artifact、task isolation 能力要求。

### Phase 2：Multica runtime 安装

目标：把 runtime 注册到 Multica workspace。

任务：

1. 登录 Multica。
2. 启动 daemon。
3. 安装 runtime bundle。
4. 注册 workflows。
5. 注册 role agents。
6. 注册 gates / triggers / schemas。
7. 注册 tool manifest。
8. 配置 `MULTICA_SUPERPOWERS_RUNTIME_ROOT`。
9. 配置 repo access。
10. 配置 MCP capability。
11. 配置 optional MCP servers。
12. 创建测试 issue。

验收：

- orchestrator 能启动 workflow。
- role agent task 能 fresh context 启动。
- runtime 能读取目标 repo。
- runtime 能执行 tool layer scripts。
- runtime 能调用 MCP。
- runtime 能读写 artifacts。
- gate 能阻塞和恢复 workflow。
- compatibility command、issue template、natural language router、artifact next action 都能生成合法 `WorkflowInvocation`。
- illegal transition rules 能拦截缺少 spec / plan / wiki context / user authorization 的跳转。

### Phase 3：standalone workflows 验证

目标：所有 enhanced standalone skills 都有 Multica-native workflow 入口。

逐一验证：

```text
init-wiki
import-wiki
migrate-wiki
lanhu-requirements
shared-wiki-mcp
publish-shared-wiki
```

每个入口至少用 Multica issue/chat 跑一次，不允许只直接执行 Python 脚本。

### Phase 4：核心 development workflow 验证

目标：跑通：

```text
brainstorming
→ writing-plans
→ .wiki-context.json
→ Multica SDD task graph 或 inline execution
→ finishing
→ update-wiki
```

验收重点：

- brainstorming 阶段创建 `wiki-researcher phase: brainstorm` task。
- brainstorming 不读大量 wiki full text。
- writing-plans 阶段创建 `wiki-researcher phase: plan` task。
- plan 生成 `.wiki-context.json`。
- plan 写 `Referenced Project Wiki`。
- execution 阶段不重新选择 wiki。
- hard constraints 可回读 section body。
- spec-document-reviewer、plan-document-reviewer、spec-compliance-reviewer、code-quality-reviewer、code-reviewer 都是独立 fresh role tasks。
- artifact-driven next actions 能从 Lanhu confirmation、spec approval、plan review、final code review、finishing 状态提示下一步。
- update-wiki 不默认写，先判断 durable knowledge。

### Phase 5：debug workflow 验证

目标：跑通：

```text
systematic-debugging
→ conditional wiki-researcher debug
→ fix + verify
→ break-loop
→ update-wiki
```

验收重点：

- Phase 1 前不创建 wiki-researcher task。
- debug wiki 查询最多少量页面。
- debug 不写 `.wiki-context.json`。
- break-loop 不直接编辑 wiki。
- update-wiki 独立做 durable / duplicate / ownership 判断。

### Phase 6：shared wiki 双路径验证

目标：保留两条 shared wiki 路径。

路径 A：local shared wiki submodule

```text
publish-shared-wiki
```

检查：

- verify hook。
- mechanical validator。
- neutrality guard。
- 用户确认 commit/push scope。
- publish hook。
- status hook。
- parent pointer 更新。

路径 B：GitHub-backed shared wiki MCP

```text
shared-wiki-mcp
或 update-wiki MCP path
```

检查：

- MCP status。
- tree/read/search。
- semantic duplicate 由 agent 判断。
- neutral diff。
- validate patch。
- create PR。
- 不 merge。
- 不写本地 shared wiki。

---

## 13. 不删减验收清单

### 13.1 Superpowers-compatible workflows 必须存在

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
- code review 相关 workflows

### 13.2 role agents 必须存在

- `superpowers-orchestrator`
- `brainstorming-agent`
- `planning-agent`
- `wiki-researcher`
- `implementer`
- `spec-document-reviewer`
- `plan-document-reviewer`
- `spec-compliance-reviewer`
- `code-quality-reviewer`
- `code-reviewer`
- `debugger`
- `break-loop-analyst`
- `wiki-curator`
- `finisher`
- `lanhu-frontend-requirements-analyst`
- `lanhu-backend-requirements-analyst`
- `shared-wiki-publisher`

### 13.3 enhanced maintenance workflows 必须存在

- `update-wiki`
- `break-loop`
- `wiki-progressive-disclosure`

### 13.4 standalone workflows 必须存在

- `init-wiki`
- `import-wiki`
- `migrate-wiki`
- `lanhu-requirements`
- `shared-wiki-mcp`
- `publish-shared-wiki`

### 13.5 wiki 能力必须保留

- `.superpowers/wiki/`
- `.shared-superpowers/wiki/`
- root `index.md`
- leaf page section markers
- `<stem>.index.md`
- schemaVersion 3 `.wiki-context.json`
- `Referenced Project Wiki`
- hardConstraint reread
- `wiki_context_render.py`
- project/shared ownership
- shared neutrality
- root-specific authorization settings

### 13.6 Lanhu 能力必须保留

- Multica MCP capability
- Lanhu MCP server integration
- frontend/backend role gate
- pageId lightweight tree selection
- selectedTargetPages
- per-page analyst dispatch
- selective image analysis
- unified frontend `role-prd/` package + backend Markdown package
- `.lanhu/MM-DD-需求名称/index.md`
- `.lanhu/MM-DD-需求名称/role-prd/prd.md`
- optional `.lanhu/MM-DD-需求名称/role-prd/design/index.html`
- multi-page aggregate package
- confirmationGate
- scopeConfirmationSummary

### 13.7 shared wiki 发布能力必须保留

- local submodule publish
- GitHub-backed MCP read/search/validate/PR
- 不自动 merge
- 不混用两条路径

### 13.8 workflow 触发能力必须保留

- compatibility commands
- issue templates / quick actions
- natural language intent router
- artifact-driven next actions
- `WorkflowInvocation` schema
- orchestrator preflight
- illegal transition rules
- gate-aware next action suggestions

---

## 14. 风险与处理

### 风险 1：Multica runtime 能力不足

处理：

- full fidelity mode 明确要求 MCP、本地文件、shell/git、artifact、task isolation。
- `verify-multica-runtime` 必须做 capability check。
- 缺少能力时直接失败，不静默降级。

### 风险 2：不依赖 Claude Code plugin 后，Superpowers 语义漂移

处理：

- 上游 Superpowers skills 作为构建来源。
- 构建时生成 workflow definitions，并保留来源版本和 patch 摘要。
- 新增 compatibility regression tests，对比核心门禁、禁止事项、artifact contract。

### 风险 3：role agents 在 Multica 中绕过 gate

处理：

- gate state 由 orchestrator 控制，不由 role agent 自行声明通过。
- role agent 只能提交 output artifact / review result。
- orchestrator 检查 gate 条件后推进 workflow。

### 风险 4：多个 implementer 同时写同一 working tree

处理：

- 默认顺序执行。
- 并行执行必须使用 worktree / patch branch / patch queue。
- orchestrator 负责合并顺序、冲突处理和 final code review 调度。

### 风险 5：update-wiki 被误用成任务完成证明

处理：

- 保留 maintenance boundary。
- `update-wiki` 只证明 wiki maintenance，不证明 implementation complete。
- development completion 仍由 originating workflow 的 verification 和 finishing gate 决定。

### 风险 6：shared wiki 污染项目私有信息

处理：

- 保留 semantic neutrality check。
- 保留 `.shared-superpowers/settings.json` blockedTerms / blockedPatterns。
- shared MCP patch validation 也必须执行 neutrality guard。

### 风险 7：Autopilot 被误用为自动开发

处理：

- Autopilot 只做检查类任务。
- 不自动跑 planning / implementation / publishing / wiki writing。

### 风险 8：MCP server 变成隐式依赖

处理：

- runtime manifest 明确区分：
  - 必备能力：MCP client capability。
  - 功能依赖：Lanhu MCP、shared-wiki MCP、GitHub MCP。
- workflow 启动时做 preflight。
- 缺失 server 时报告哪个功能不可用，以及如何安装。

### 风险 9：自然语言触发绕过 Superpowers gate

处理：

- intent router 只能生成候选 `WorkflowInvocation`，不能直接推进 workflow。
- orchestrator preflight 必须校验 artifact、gate、capability 和 illegal transition rules。
- artifact-driven next action 只能建议下一步或创建待确认 action，不能自动越过用户确认。
- 对缺少 spec、plan、wiki context、Lanhu confirmation 或外部副作用授权的请求必须阻塞并说明缺失项。

---

## 15. 推荐落地顺序

建议按以下顺序实施：

1. **实现 `build-multica-runtime` 与 `verify-multica-runtime`。**
   - 这是基础。没有 runtime bundle，后续会变成手工复制，难以长期维护。

2. **实现 Multica orchestrator + role agent taxonomy。**
   - 先把 Superpowers 的控制平面迁到 Multica。

3. **实现 workflow 触发层。**
   - compatibility commands、issue templates、intent router、artifact-driven next actions 全部归一到 `WorkflowInvocation`。

4. **先迁移 wiki 主链路。**
   - brainstorming → writing-plans → `.wiki-context.json` → execution → update-wiki。

5. **迁移 SDD task graph。**
   - implementer → spec-compliance-reviewer → code-quality-reviewer → final-code-reviewer mode。

6. **包装 standalone workflows。**
   - `init-wiki`、`import-wiki`、`migrate-wiki`。

7. **迁移 Lanhu。**
   - role gate、page selection、analyst fan-out、confirmationGate、HTML/Markdown 分支。

8. **最后迁移 shared wiki publish / MCP。**
   - 因为这涉及 commit、push、PR 等外部可见副作用，验收成本最高。

---

## 16. 最小可交付版本

如果要做一个最小但仍不删减架构的 MVP，范围应是：

```text
- 不依赖用户本地 Claude Code Superpowers plugin
- generated Multica-native runtime bundle
- workflow definitions for core Superpowers-compatible workflows
- role agents: orchestrator / wiki-researcher / planning-agent / implementer / spec-document-reviewer / plan-document-reviewer / spec-compliance-reviewer / code-quality-reviewer / code-reviewer / wiki-curator
- gates: design approval / spec approval / wiki authorization
- triggers: compatibility commands / issue templates / artifact-driven next actions / illegal transition rules
- `WorkflowInvocation` schema and orchestrator preflight
- scripts root env 解析
- project/shared local wiki
- writing-plans 生成 .wiki-context.json
- execution 消费 .wiki-context.json
- update-wiki durable knowledge 判断和本地 wiki 写入
- verify-multica-runtime capability check
```

MVP 可以暂缓真实跑 Lanhu 和 shared-wiki MCP，但不能在架构上删除它们；必须保留对应 workflows、agents、instructions、manifest、issue templates 和 verify placeholder，后续阶段补真实验收。

---

## 17. 最终目标形态

最终用户在 Multica 中看到的是：

```text
Multica issue / chat / assignment
→ superpowers-orchestrator
→ Multica-native Superpowers-compatible workflow
→ role agent task graph
→ wiki / Lanhu / shared-wiki enhancement
→ target repo files and wiki artifacts
→ Multica comments report progress and ask confirmations
```

最终用户不需要记住 Python 脚本，也不需要本地 Claude Code 安装 Superpowers plugin；多数情况下也不需要记住精确 workflow 名。用户可以通过 Multica issue template、quick action、自然语言或兼容命令触发：

```text
我要做一个会员充值新功能。
基于这个 Lanhu 包写需求方案。
spec 已确认，帮我写 implementation plan。
这个 plan 可以开始执行，用 SDD task graph。
这个测试失败了，帮我系统调查。
检查这次改动是否需要更新 wiki。
请使用 init-wiki 初始化 project wiki。
请使用 lanhu-requirements 处理这个蓝湖链接。
```

Multica 将这些入口归一为 `WorkflowInvocation`，由 orchestrator 校验 gate、artifact、capability 和 illegal transition rules 后启动对应 workflow。实际执行由 Multica-native runtime 承载，但能力边界和产物结构保持 Superpowers + adapter full fidelity。

---

## 18. 文档来源

本方案依据当前仓库文档和 Multica 文档整理：

- `CLAUDE.md`
- `ADAPTER_USER_FLOW_CN.md`
- `ADAPTER_DEVELOPMENT_CN.md`
- `overlays/agents/wiki-researcher.md`
- `overlays/skills/wiki-progressive-disclosure/SKILL.md`
- `overlays/skills/update-wiki/SKILL.md`
- `overlays/skills/break-loop/SKILL.md`
- `overlays/skills/init-wiki/SKILL.md`
- `overlays/skills/import-wiki/SKILL.md`
- `overlays/skills/lanhu-requirements/SKILL.md`
- `overlays/skills/shared-wiki-mcp/SKILL.md`
- `overlays/skills/publish-shared-wiki/SKILL.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/brainstorming/SKILL.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/brainstorming/spec-document-reviewer-prompt.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/writing-plans/SKILL.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/writing-plans/plan-document-reviewer-prompt.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/executing-plans/SKILL.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/subagent-driven-development/SKILL.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/subagent-driven-development/implementer-prompt.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/subagent-driven-development/spec-reviewer-prompt.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/subagent-driven-development/code-quality-reviewer-prompt.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/requesting-code-review/code-reviewer.md`
- `https://github.com/obra/superpowers.git` 中的 `skills/systematic-debugging/SKILL.md`
- Multica docs:
  - https://multica.ai/docs
  - https://multica.ai/docs/how-multica-works
  - https://multica.ai/docs/skills
  - https://multica.ai/docs/agents
  - https://multica.ai/docs/agents-create
  - https://multica.ai/docs/cli
  - https://multica.ai/docs/providers
  - https://multica.ai/docs/autopilots
  - https://multica.ai/docs/tasks
  - https://multica.ai/docs/squads
