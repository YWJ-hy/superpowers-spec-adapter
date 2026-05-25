# Superpowers + Adapter 用户流程说明

本文面向最终用户，说明 adapter 安装到 Superpowers 后，用户在 Claude Code、Cursor 等工具中应如何使用。

如果你是 adapter 开发者，请先读 [`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)。

---

## 1. 一句话理解

`superpower-adapter` 不替代 Superpowers，也不要求用户直接运行一组 Python 脚本。

它的定位是：

> adapter 为 Superpowers 提供项目 wiki 的渐进式披露能力，让 Superpowers 在编写本次 spec 和 implementation plan 时自然继承 `.superpowers/wiki/` 中的项目私有 wiki 知识，以及可选 `.shared-superpowers/wiki/` 中的跨项目共享 wiki 知识。

用户面对的主流程仍是 Superpowers：

- `brainstorming`：理解需求并写本次 Superpowers spec。
- `writing-plans`：根据已确认 spec 写 implementation plan。
- `executing-plans` 或 `subagent-driven-development`：按 plan 执行。

adapter 增强这些阶段：

- 安装 `wiki-researcher` agent，用于从 `.superpowers/wiki/index.md` 和 `.shared-superpowers/wiki/index.md` 开始渐进选择少量相关项目/共享 wiki 页面。
- 可选安装体验：如果用户已配置 lanhu-mcp，可用 `lanhu-requirements` skill 先确认前端/后端角色，再路由到 `lanhu-frontend-requirements-analyst`、`lanhu-frontend-html-requirements-analyst` 或 `lanhu-backend-requirements-analyst` 生成 `.lanhu/MM-DD-需求名称/` 蓝湖原始需求证据包。该包是 Superpowers 的需求输入，不是 Superpowers spec，不生成最终验收标准、测试计划、技术方案或实施任务。显式 `pageId` 链接会先由主会话把 URL 当作 `rootScopeUrl`、当前页当作 `rootPageId`，只调用 `lanhu_get_prd_page_scope` 获取当前页及子树的轻量 page tree metadata，再结合用户描述选择 `selectedTargetPages`；主会话在派发前不得调用 `lanhu_get_prd_scoped_evidence` 或读取完整页面 evidence。每个选中页面固定派发一个 analyst，analyst 才使用固定 scoped Lanhu MCP 序列读取自己的页面 evidence。蓝湖图片、截图和 `designInfo.images` 默认只作为候选证据；analyst 仅在标注、箭头、周边说明、用户点名、关键 UI 事实缺失等信号命中时选择性分析图片区域，默认不把图片资产保存到 `.lanhu/`。
- 蓝湖 frontend Markdown 证据包保留 XML-like 的 1:1 原始需求界面复刻，供 Superpowers/agent 稳定读取；frontend HTML 证据包使用 `index.html` 作为 evidence reader，并用 `prototype/index.html` 1:1 复刻蓝湖原始需求界面和真实控件。HTML 已有真实控件时，不再重复输出“控件类型”文案；HTML prototype 复刻的是 selected/evidenced 范围，不因为返回了图片资源就全量复刻整张图。蓝湖原始需求中的明确事实不得因模板主题装不下而丢失；analyst 可按源需求创建具体的源事实主题承接，例如“计费规则源事实”“消息通知源事实”“导入导出源事实”。如 analyst 返回 `status: need_confirmation`，主会话只展示紧凑阻塞问题并把用户答案回传 analyst；图片相关性、是否分析高成本图片区域或是否保存原图也应走同一确认门禁。`confirmationGate.status: clear` 且用户确认 `index.md` 和 `scopeConfirmationSummary` 后才进入 Superpowers `brainstorming`。
- 在 `brainstorming` 阶段轻量披露相关项目 wiki 页面。
- 在 `writing-plans` 阶段正式选择相关项目 wiki 页面，生成配套 schemaVersion 3 `.wiki-context.json` 约束产物，并要求 plan 写入轻量 `Referenced Project Wiki` 入口。JSON 以 wiki page 为根节点，每个 page 只保留一份来自伴随 `<stem>.index.md` 的有界 `documentContext`，选中的 sections 作为子节点并保留 implementation / test / review / general 分类约束。
- 在执行阶段只消费 plan 中已经确认的 `Referenced Project Wiki` 和其链接的 `.wiki-context.json`，并通过安装在 Superpowers plugin 内的 `wiki_context_render.py` 按 task / role 机械过滤和组装 implementer / reviewer 约束。对 `hardConstraint: true` 的 section，执行阶段会强制回读原始 wiki section 全文（通过 `<!-- wiki-section:xxx -->` 标记提取），并附带有界 `documentContext` 注入 implementer 和 spec-reviewer prompt，确保约束不因摘要信息衰减或 section 脱离页面主语而被误用。
- Wiki 文档使用 `<!-- wiki-section:section-id -->` / `<!-- /wiki-section:section-id -->` 标记包裹独立约束主题段落，每个叶子文档都必须有 `<stem>.index.md` 伴随索引；该索引包含文档级语义概览和 section 表格。`wiki-researcher` 通过读取 per-document index 快速判断文档和 section 相关性，未迁移到新格式的文档不参与 wiki-researcher 选择。用户可通过 `migrate-wiki` skill 将现有 wiki 迁移到 section-marker 格式。
- 在 `systematic-debugging` 中，只有 Phase 1 证据已经收窄到具体组件、契约、工作流或项目约定后，才允许条件式调用 `wiki-researcher` 查少量相关项目 wiki。wiki 只作为待验证线索，不替代 root cause evidence。
- `update-wiki` 写入前读取目标 root 的 settings：`.superpowers/settings.json` 控制 project wiki，`.shared-superpowers/settings.json` 控制 shared wiki；默认更新已有页面跳过授权，创建新 wiki 文档询问用户授权；写入 shared wiki 前必须把内容中性化，不能保留当前系统特有标识。如团队使用 GitHub-backed shared-wiki MCP，则 shared wiki 写入通过 MCP validate patch + branch + PR，不直接改本地 shared wiki。
- 安装 `break-loop` skill，用于 Superpowers `systematic-debugging` 修复并验证 bug 后做深度复盘，并在有长期价值时把候选交给 `update-wiki`。

`import-wiki` skill、`init-wiki` skill、`lanhu-requirements` skill 在自身产物完成前都是独立 adapter skill，不应自动触发 Superpowers 的 completion、review、verification 等收尾技能；只有 skill 明确交接且用户确认后才进入下一步 Superpowers workflow。`break-loop` 是 bug 修复后的 adapter skill：它衔接 Superpowers `systematic-debugging`，只在 bug 已修复并验证后做后置复盘。`update-wiki` 是自动触发的 adapter maintenance skill：任务完成、修 bug、评审或讨论后，如果 agent 判断产生了 durable implementation knowledge，才审查并更新合适的 wiki root（`.superpowers/wiki/` 或 `.shared-superpowers/wiki/`）；它的本地 wiki 校验不替代 Superpowers 实现验证。

Python 脚本是 skill / agent 背后的执行层，不是最终用户的主要交互入口。

---

## 2. adapter 插入 Superpowers 后发生了什么

安装 adapter 后，adapter 会把 overlay 写入用户已安装的 Superpowers 插件目录：

```text
Superpowers 插件目录
├── agents/
│   ├── wiki-researcher.md
│   ├── lanhu-frontend-requirements-analyst.md
│   ├── lanhu-frontend-html-requirements-analyst.md
│   └── lanhu-backend-requirements-analyst.md
├── skills/
│   ├── init-wiki/
│   │   └── SKILL.md
│   ├── import-wiki/
│   │   └── SKILL.md
│   ├── lanhu-requirements/
│   │   └── SKILL.md
│   ├── migrate-wiki/
│   │   └── SKILL.md
│   ├── publish-shared-wiki/
│   │   └── SKILL.md
│   ├── shared-wiki-mcp/
│   │   └── SKILL.md
│   ├── break-loop/
│   ├── wiki-progressive-disclosure/
│   └── update-wiki/
└── scripts/
    └── adapter 执行脚本
```

`wiki-progressive-disclosure` 会继续安装，但它只是说明性 / fallback skill；正常 `brainstorming` 和 `writing-plans` 流程由 `wiki-researcher` 直接完成 wiki 选择。

同时 adapter 会 patch Superpowers 的 native skills：

- `using-superpowers`：声明 adapter workflow boundary。standalone adapter skill 和 adapter maintenance skill 的本地完成，不等于 Superpowers development-task completion；正常 `brainstorming`、`writing-plans`、`executing-plans`、`subagent-driven-development`、`systematic-debugging` 流程仍保留自己的 verification 和后续 `update-wiki` 机制。
- `brainstorming`：如果用户给出蓝湖链接且 lanhu-mcp 可用，先确认前端/后端 evidence role，再路由到 `lanhu-frontend-requirements-analyst`、`lanhu-frontend-html-requirements-analyst` 或 `lanhu-backend-requirements-analyst` 直接生成 `.lanhu/MM-DD-需求名称/` 蓝湖原始需求证据包；主会话只接收 status、confirmationGate、packageDir、indexPath、writtenFiles、sourceFactCoverage、openQuestions、caveats 等轻量摘要，`index.md` 是用户确认和后续读取的入口。如用户直接引用已确认的 `.lanhu/.../index.md` 或已存在证据包，则不默认重新读蓝湖，而是先读 `index.md`，再按其中索引读取同包内 `prd.md`、`prds/*.md`、`index.html` 或 `prototype/index.html` 等详细证据来源，作为 Superpowers spec 的需求输入。Lanhu 包不得被复制为 final spec、验收标准、测试计划、技术方案或 implementation plan。
- `writing-plans`：在拆分任务前调用 `wiki-researcher` 正式选择项目/共享 wiki 页面，生成 `docs/superpowers/plans/<plan-stem>.wiki-context.json`，并要求 plan 写入轻量 `Referenced Project Wiki` 入口。
- `systematic-debugging`：Phase 1 先复现、收集错误、检查变更并收窄失败边界；只有怀疑项目特定契约、known gotcha、跨层边界或工作流约定时，才用 `phase: debug`、`maxWikiPages: 2` 条件式查询 wiki。
- `executing-plans`：执行前读取 plan 中的 `Referenced Project Wiki` 和链接的 `.wiki-context.json`，用 plugin-root `wiki_context_render.py` 按当前 task 渲染 implementer 约束，不重新选择 wiki 页面。
- `subagent-driven-development`：把 plan 中的 `Referenced Project Wiki` 和链接的 `.wiki-context.json` 通过 plugin-root `wiki_context_render.py` 分别渲染为 implementer / reviewer 的 task-specific 约束块，再传给 subagent。
- `using-git-worktrees`：创建 worktree 时把原始分支、原始 worktree 和原始 HEAD 记录到新 worktree 的 private git-dir metadata。
- `finishing-a-development-branch`：metadata 有效时，提供明确合并回创建 worktree 前原始分支的收尾选项。

当前流程不安装 SessionStart hook；`wiki-researcher` 会在 `brainstorming` 和 `writing-plans` 阶段按需读取 `.superpowers/wiki/` 和 `.shared-superpowers/wiki/`，并可在 `systematic-debugging` Phase 1 证据收窄后作为低噪音调试辅助被条件式调用。worktree origin metadata 是本地临时协调状态，不写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区。

---

## 3. 用户视角的完整推荐执行顺序

| 顺序 | 阶段 | 入口 | 是否每次都需要 | 目的 |
|---|---|---|---|---|
| 0 | 安装 Superpowers | `/plugin install superpowers@claude-plugins-official` | 只需一次 | 先安装 Superpowers 主插件 |
| 1 | 安装 adapter | `./manage.sh install` | 只需一次；Superpowers 升级后重跑 | 写入 adapter overlay、agent、skill、script；默认覆盖所有已安装 Superpowers 版本目录 |
| 2 | 校验 adapter | `./manage.sh verify` | 安装或升级后 | 确认安装产物和 native skill patch 完整 |
| 3 | 初始化 wiki 模板 | `./manage.sh bootstrap-wiki /path/to/project --template standard` | 每个目标项目一次 | 创建 `.superpowers/wiki/` wiki 目录；如需要共享知识库，可用 `--wiki-root shared` 创建 `.shared-superpowers/wiki/` |
| 4 | 导入已有 wiki | `import-wiki` skill | 有已有 wiki 或文档时才需要 | 把已有 wiki 或文档导入到 `.superpowers/wiki/`，或用 `--wiki-root shared` 导入 `.shared-superpowers/wiki/` |
| 4.5 | 可选 GitHub shared wiki MCP | `shared-wiki-mcp` skill | 使用独立 GitHub shared-wiki 仓库时 | 通过 copyable MCP server 读取 shared wiki，并把更新作为 branch + PR 提交 |
| 5 | 初始化 starter wiki | `init-wiki` skill | 每个目标项目首次使用时 | 从当前项目结构生成第一版轻量 wiki 知识 |
| 6 | 可选蓝湖原始需求证据包 | `lanhu-requirements skill <蓝湖链接> 前端/后端` | 有蓝湖链接且已配置 lanhu-mcp 时 | 先确认前端/后端角色；如 URL 带 pageId，主会话先读取 URL 当前页及子树的轻量 page tree metadata，并结合用户描述选择目标页面；每个目标页面由 analyst 直接生成 `.lanhu/MM-DD-需求名称/` 或 `pages/<page-slug>/` evidence package 并只向主会话返回路径摘要和确认门禁；图片默认只按标注/箭头/缺失关键事实等信号选择性分析，不保存图片资产；默认 Markdown-only，前端 html 模式生成 `index.html` evidence reader 和 `prototype/index.html` 1:1 原始需求界面复刻；阻塞确认点清零且用户确认 `index.md` 后作为 Superpowers 需求输入 |
| 7 | 描述需求并进入 `brainstorming` | Superpowers `brainstorming` | 复杂任务或需要设计时 | 写本次 Superpowers spec，并轻量参考项目 wiki |
| 8 | 写 implementation plan | Superpowers `writing-plans` | 有已确认 spec 后 | 正式选择项目/共享 wiki 页面，生成 `.wiki-context.json`，并在 plan 中写入轻量 `Referenced Project Wiki` |
| 9 | 执行 plan | `executing-plans` / `subagent-driven-development` | 有 plan 时 | 按 plan 执行，并消费 `Referenced Project Wiki` 和链接的 `.wiki-context.json` |
| 9.5 | worktree 收尾 | `finishing-a-development-branch` | 使用 Superpowers worktree 开发后 | metadata 有效时，可明确合并回创建 worktree 前的原始分支 |
| 10 | 修 bug 与复盘 | `systematic-debugging` → `break-loop` | bug 修复并验证后，且需要防复发分析时 | 先用 Superpowers 修对 bug；必要时在证据收窄后低噪音查 wiki，修复验证后再由 adapter 复盘 root cause、失败修复路径、防复发机制和可沉淀候选 |
| 11 | 任务后更新 wiki | `update-wiki` skill | 任务产生长期可复用知识时 | 审查并回写 durable implementation knowledge |
| 12 | 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者发布前 | 运行 verify、doctor、self-test、export-manifest |

用户日常在 Claude Code 中主要记住这条链：

```text
描述需求 / 可选蓝湖链接
→ 如果使用蓝湖，先确认前端/后端角色；如 URL 带 pageId，主会话先用轻量 page tree metadata 结合用户描述选择目标页面，再按页面路由 analyst 直接生成 .lanhu/MM-DD-需求名称/ 原始需求证据包，默认 Markdown-only；如目标项目配置前端 html，可生成 index.html evidence reader 和 prototype/index.html 1:1 原始需求界面复刻；主会话只接收路径摘要和紧凑确认门禁，index.md 是入口和文件关系权威来源
→ 如存在阻塞确认点，用户回答后由同一角色 analyst 修复 evidence package，直到 confirmationGate.status: clear
→ 用户确认 .lanhu 证据包的 index.md
→ Superpowers brainstorming
→ adapter 轻量披露相关项目 wiki 页面
→ Superpowers 写并确认本次 spec
→ Superpowers writing-plans
→ adapter 正式选择项目/共享 wiki，生成 .wiki-context.json，并在 plan 写入轻量 Referenced Project Wiki
→ Superpowers 直接读当前源码验证精确影响文件和任务步骤
→ Superpowers executing-plans / subagent-driven-development 按 plan 和 .wiki-context.json 执行
→ 遇到 bug 时先用 Superpowers systematic-debugging 复现、收集证据并收窄失败边界
→ 如果怀疑项目特定契约 / gotcha / 跨层边界，才条件式用 wiki-researcher 查少量 wiki，并继续用代码、日志、测试或复现验证
→ 修复后需要防复发分析时使用 break-loop
→ update-wiki skill 审查是否需要沉淀长期知识
```

---

## 4. 安装与初始化

### 4.1 安装 adapter

在 adapter 源码目录执行：

```bash
./manage.sh install
./manage.sh verify
```

如果本机同时保留多个 Superpowers 插件版本，默认会对 `installed_plugins.json` 中所有唯一的 Superpowers 安装目录执行安装和校验；如只想操作某一个版本，可显式传入该 Superpowers 目录。

当前 adapter 以 Superpowers 5.1.0 为适配基线；如果安装到更高版本的 Superpowers，`./manage.sh install` 会先给出兼容性警告，但仍会继续安装。安装时会优先读取目标目录里的 `package.json` 版本号。`superpowers@claude-plugins-official` 是当前自动发现安装目标的默认插件键；如果将来 Superpowers 改了这个安装记录键，显式传目标路径会更稳。上游 skill 标题和锚点如果变化，adapter 的 native patch 也需要同步检查。

高级配置：`adapter.config.json` 默认是 `{}`，不会改变任何 subagent 模型；adapter agent 会保持 `model: inherit`，Superpowers 上游 prompt template 也不会插入模型字段。如果需要为 `wiki-researcher`、Lanhu analyst 或 Superpowers 的 implementer / reviewer 类 prompt template 指定模型，可参考 `adapter.config.example.jsonc`，把需要的条目复制为无注释 JSON 后再运行 `./manage.sh install`。`subagentModels.agents` 写入 adapter 原生 agent frontmatter，允许类似 `deepseek-v4-pro[1m]` 的 Claude Code 方括号后缀模型名，但 install 会对非 `inherit` / `sonnet` / `opus` / `haiku` 值提示 warning，提醒确认当前 Claude Code 运行时支持该模型。`subagentModels.upstreamPromptTemplates` 会变成 Claude Code Task / Agent 的 `model` 参数；由于 Claude Code 当前只允许该字段使用 `sonnet`、`opus`、`haiku`，因此 install 会拒绝其它值。这样做是为了避免安装后的 markdown 看起来已经配置成功，但 Claude Code 运行时 subagent 忽略该字段、回退到其它模型或延后失败。其中 `final-code-reviewer` 只作用于 `subagent-driven-development` 所有任务完成后的最终整体评审；未配置时会降级使用 `code-reviewer` 的模型配置。Superpowers 升级后，如果某个已配置模型的上游 prompt template 结构变化导致无法应用，install 会一次性列出失败的 subagent id、目标路径和原因；未配置模型的 subagent 不会因为模板变化阻塞安装。

如果 adapter 是作为其他项目中的 `superpower-adapter/` 目录存在，也可以从宿主项目执行：

```bash
./superpower-adapter/manage.sh install
./superpower-adapter/manage.sh verify
```

### 4.1.1 可选：构建 Multica-native runtime bundle

如果团队希望在 Multica 中直接承载 Superpowers-compatible workflow runtime，而不是要求用户本地 Claude Code 安装 Superpowers plugin，可以从 adapter 仓库生成 Multica runtime bundle：

```bash
./manage.sh build-multica-runtime /path/to/superpowers . ./dist/multica-superpowers-runtime
./manage.sh verify-multica-runtime ./dist/multica-superpowers-runtime
./manage.sh install-multica-runtime ./dist/multica-superpowers-runtime --dry-run
```

生成产物包含 Multica workflow definitions、role agents、gates、triggers、schemas、MCP examples、issue templates、preflight contracts、离线 preflight validators、SDD task graph，以及 `dist/tools/scripts/` 下的 adapter 工具层。用户入口是 Multica workflow / issue template / quick action / natural language router / compatibility command；Python 脚本仍然只是 Multica tool runner 的执行层，不是普通用户主入口。当前 bundle 校验能离线检查 runtime capability 声明、WorkflowInvocation 合同和 SDD task graph；`install-multica-runtime` 会用 exact command help matching 探测当前官方 CLI，并用 documented Multica surface 实装运行层：创建 runtime registration issue，通过 issue metadata 存 WorkflowInvocation / gate / schema / runtime state，通过 issue comments/attachments 挂载 runtime contract artifacts，通过 issue assign/rerun 和 issue get/runs/run-messages 承载 fresh role task dispatch 与观察，通过 autopilot schedule/webhook triggers 承载触发器替代层。默认 dry-run；`--apply` 只执行官方 CLI 命令，不猜 undocumented API。

### 4.1.2 可选：接入真实 Multica workspace issue template flow

如果目标是先在真实 Multica 里跑通 Superpowers+adapter 用户入口，而不是继续扩展本地 bundle contract，可用 `multica-bootstrap` 生成 workspace skill pack，并通过官方 Multica CLI 创建/配置兼容 smoke agent、创建模板化 issue、assign 给 agent。完整产品验收不再以单个 `superpowers-adapter-orchestrator` 跑完整流程为标准；必须用 `multica-live-acceptance` 创建 A-H 可视化 stage issues，并分别 assign 给 `superpowers-*` role agents 或 `superpowers-runtime-squad`，让 Multica UI / CLI 能看到 wiki-researcher、brainstorming、spec-document-reviewer、planning、plan-document-reviewer、implementer、reviewers、finisher、debugger、wiki-curator 和 shared-wiki-publisher 的独立 runs。

先 dry-run，确认将生成的 skill pack、issue body 和计划执行的 Multica 命令：

```bash
./manage.sh multica-bootstrap \
  --superpowers-source /path/to/superpowers \
  --target-repo /path/to/project \
  --skill-pack-dir ./dist/multica-skill-pack \
  --dry-run
```

默认 `--issue-template smoke` 是只读任务，只要求 agent 确认 target repo、skill pack 可见性和 project/shared wiki root 状态；不得编辑代码、commit、push 或创建 PR。Multica agent 会从用户写的 issue 标题、正文和后续评论中推导用户偏好语言，用户可见的评论、问题、总结、review findings 和 handoff 应使用该语言；代码、命令、路径、日志和引用证据保持原文。后续可把同一真实 Multica 入口切到具体 Superpowers+adapter 流程：

| issue template | 对应入口 | 典型输入 |
|---|---|---|
| `lanhu-intake` | `skills/lanhu-requirements/SKILL.md` | `--lanhu-url` 或 `--requirements-path` |
| `brainstorming` | `upstream-superpowers/brainstorming.md` | 可选 `--requirements-path` / `--spec-path` |
| `writing-plans` | `upstream-superpowers/writing-plans.md` | `--spec-path` 或 `--requirements-path` |
| `execute-plan` | `upstream-superpowers/executing-plans.md` | `--plan-path`，可选 `--wiki-context-path` |
| `sdd-execution` | `upstream-superpowers/subagent-driven-development.md` | `--plan-path`，可选 `--wiki-context-path` |
| `systematic-debugging` | `upstream-superpowers/systematic-debugging.md` | `--debug-evidence` 或 `--requirements-path` |
| `break-loop` | `skills/break-loop/SKILL.md` | `--debug-evidence` |
| `update-wiki` | `skills/update-wiki/SKILL.md` | `--plan-path` 或 `--requirements-path` 描述已完成工作 |
| `publish-shared-wiki` | `skills/publish-shared-wiki/SKILL.md` | `--shared-wiki-topic` |
| `shared-wiki-mcp-pr` | `skills/shared-wiki-mcp/SKILL.md` | `--shared-wiki-topic` |

只创建 issue 的 dry-run 示例：

```bash
./manage.sh multica-bootstrap create-issue \
  --target-repo /path/to/project \
  --issue-template writing-plans \
  --requirements-path /path/to/project/docs/prd.md \
  --dry-run
```

当 `multica auth status`、`multica daemon status`、`multica runtime list` 都正常，且确认有 Claude Code runtime 后，只有在需要导入/更新 skill pack 或跑只读兼容 smoke 时才使用 `multica-bootstrap --apply`：

```bash
./manage.sh multica-bootstrap \
  --superpowers-source /path/to/superpowers \
  --target-repo /path/to/project \
  --issue-template smoke \
  --apply
```

`--apply` 会尝试把 `superpowers-adapter` skill pack 导入 Multica workspace、创建或复用兼容 smoke agent、attach skill、创建模板 issue 并 assign 给 agent，从而触发真实 Multica daemon task。bootstrap 命令本身不会 commit、push、创建 PR、发布 shared wiki 或调用 undocumented API；发布/PR 类模板默认带授权门，只有显式 `--allow-external-side-effects` 时才会把授权写入 issue body。如果当前 Multica CLI 没有提供可自动调用的本地 skill import / skill attach flag，命令会输出需要在 UI 或 CLI 中手动完成的步骤，而不会猜 undocumented API。

完整端到端 live acceptance 使用 `multica-live-acceptance` 先 dry-run 规划，再在 disposable target repo 上用 `--apply` 让 Multica 真实创建和分配 role-agent stage issues：

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

```bash
./manage.sh multica-live-acceptance \
  --target-repo /path/to/disposable/project \
  --case all \
  --requirements-path /path/to/disposable/project/docs/prd.md \
  --spec-path /path/to/disposable/project/docs/spec.md \
  --plan-path /path/to/disposable/project/.superpowers/plans/feature.md \
  --wiki-context-path /path/to/disposable/project/.superpowers/plans/feature.wiki-context.json \
  --debug-evidence /path/to/disposable/project/docs/debug-evidence.md \
  --shared-wiki-topic "portable API contracts" \
  --observe-runs \
  --apply
```

可选链路：`chain-a` wiki-aware feature development，`chain-b` Lanhu intake → Superpowers，`chain-c` brainstorming 多轮 → planning，`chain-d` SDD reviewer loop，`chain-e` systematic-debugging → break-loop → update-wiki，`chain-f` shared wiki local readiness，`chain-g` direct role/squad dispatch，`chain-h` blocked/comment/rerun/cancel recovery，`all` 全量 A-H。`multica-live-acceptance` 和 `multica-bootstrap` 都会拒绝 `--agent-name superpowers-adapter-orchestrator`，因为这个 adapter-specific 单 agent 路径已移除。

### 4.2 初始化 wiki 模板

```bash
./manage.sh bootstrap-wiki /path/to/project --template standard
./manage.sh bootstrap-wiki /path/to/project --template standard --wiki-root shared
```

第一条会在目标项目创建 `.superpowers/wiki/`；第二条会创建同级共享 wiki root `.shared-superpowers/wiki/`，并同时落地 `.shared-superpowers/scripts/`、`.shared-superpowers/settings.json` 和 `.shared-superpowers/settings.json.example`，方便用户把 shared wiki 作为项目本地 submodule 管理，并配置 shared wiki 更新授权。入口分别为：

```text
.superpowers/wiki/index.md
.shared-superpowers/wiki/index.md
.shared-superpowers/scripts/run-hook.py
```

### 4.3 配置 wiki 更新授权策略

Project wiki 与 shared wiki 分别读取自己的 settings：

- `.superpowers/settings.json` 控制 `.superpowers/wiki/`
- `.shared-superpowers/settings.json` 控制 `.shared-superpowers/wiki/`

可配置 schema：

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

允许值：`skip` 表示跳过授权，`ask` 表示写入前询问用户，`refuse` 表示拒绝该操作。settings 文件或字段缺失时使用默认值：更新已有 wiki page 为 `skip`，创建新 wiki 文档为 `ask`。`ask` 由 skill 在用户入口询问；执行层脚本用 `--authorized-update` 或 `--authorized-create` 表示已获得用户授权。`refuse` 会阻止写入。`sharedNeutrality` 主要用于 `.shared-superpowers/settings.json`：配置已知系统标识或正则后，执行层会拒绝把这些内容写入 shared wiki 的路径、正文、导入内容或刷新后的 index。仓库根目录的 `wiki-settings.example.jsonc` 提供可复制的带注释示例。

### 4.4 可选：同步 / 发布 shared wiki submodule

如果团队把 `.shared-superpowers/wiki/` 配成 git submodule，bootstrap 生成的 `.shared-superpowers/settings.json` 可以直接使用，也可参考 `.shared-superpowers/settings.json.example` 调整；进入 Superpowers 主流程前可运行：

```bash
python3 ./.shared-superpowers/scripts/run-hook.py sharedWikiSubmodule:sync
```

这只负责把 shared wiki submodule 拉到最新，不替代 `wiki-researcher` 的按需选择，也不替代 `update-wiki` 对 durable knowledge 的审查。

当 shared wiki 内容已经更新并需要推送远程、同时更新主项目 submodule 指针时，在 Claude Code 中使用：

```text
publish-shared-wiki skill
```

该 command 会先运行 shared wiki 机械校验（包括配置化中性化 guard），再确认 commit/push 范围，并通过 `.shared-superpowers/settings.json` 调用项目本地 runner 执行发布。

### 4.5 可选：GitHub shared wiki MCP

如果团队把 shared wiki 维护在独立 GitHub 仓库，可复制 adapter 仓库中的 MCP server：

```text
mcp/shared-wiki/
```

在复制后的目录运行：

```bash
npm install
npm run build
```

然后配置 `repoUrl` 和仓库默认分支，例如：

```text
repoUrl: https://github.com/YWJ-hy/shared-wiki.git
baseBranch: master
```

并把 build 后的 MCP server 加入 Claude Code MCP 配置。之后可在 Claude Code 中使用：

```text
shared-wiki-mcp skill
```

该 MCP server 负责读取 indexed shared wiki、校验 unified diff、创建 branch、push 并打开 GitHub PR；不会自动 merge。语义判断仍由 Superpowers / adapter agent 完成：是否是 durable knowledge、是否属于 shared wiki、是否已被现有 wiki 覆盖、是否已经中性化，都不能交给 MCP 决定。正常 brainstorming / writing-plans / debugging 的 shared wiki 披露仍统一由 `wiki-researcher` 承担，MCP 只是它可选的 shared source 之一。

这条流程与 `.shared-superpowers/wiki/` submodule 发布流程并存；不要把同一次 shared wiki 更新同时走 `publish-shared-wiki` skill 和 MCP PR flow。

### 4.6 可选：导入已有 wiki

```text
import-wiki skill path/to/original-wiki-dir
import-wiki skill path/to/original-wiki-dir --target imported
import-wiki skill path/to/original-wiki-dir --wiki-root shared --target imported
```

`import-wiki` skill 是独立 adapter skill，只做已有规范的结构导入、避免覆盖和索引刷新；因为导入会创建 wiki 文档，它会遵守目标 root 的 `createNewDocument` 策略，默认先询问用户授权。导入 shared wiki 的内容必须已经中性化，不能包含系统标识、内部 URL、环境名、本地路径或当前系统专属规则；如命中 `.shared-superpowers/settings.json` 的 `sharedNeutrality` 配置，执行层会拒绝导入。如果导入内容需要语义整理，后续由 `update-wiki` skill 判断写入 `.superpowers/wiki/` 还是 `.shared-superpowers/wiki/` 并审查更新。

### 4.7 可选：从蓝湖生成原始需求证据包

如果用户已配置 lanhu-mcp，可以用：

```text
lanhu-requirements skill <蓝湖链接> 前端 <可选需求命名>
lanhu-requirements skill <蓝湖链接> 后端 <可选需求命名>
lanhu-requirements skill --role frontend <蓝湖链接> <可选需求命名>
lanhu-requirements skill --role backend <蓝湖链接> <可选需求命名>
```

该命令会先确认本次要生成前端 Lanhu 原始需求证据包还是后端相关 Lanhu 原始需求证据包，再路由到对应 analyst 读取蓝湖内容并直接写入只包含蓝湖原始需求事实的 evidence package。它不生成最终验收标准、测试计划、技术方案或实施任务；这些由后续 Superpowers 流程基于输入自行产出。

```text
.lanhu/MM-DD-需求名称/
├── index.md
├── prd.md
└── prds/
    ├── <源需求边界1>.md
    └── <源需求边界2>.md
```

单个源需求边界使用 `prd.md`；多个源需求边界使用 `prds/`。是否拆分由源需求事实的连贯性决定，不由页面数量决定。`index.md` 是证据包入口和文件关系权威来源。

如果用户没有提供角色，或同时说“前后端都要 / 全栈”，adapter 会先询问本次生成哪一种 evidence package；在角色明确前，不调用任何 Lanhu analyst agent，也不读取或分析蓝湖。角色明确后才路由到对应的前端或后端专用 agent。需要前端和后端两份 evidence package 时，应分别运行两次命令。

如果蓝湖链接带有明确 `pageId`，adapter 会在角色确认后把该 URL 当作范围入口：先用 `lanhu_get_prd_page_scope` 只获取当前页及子树的轻量 page tree metadata，再结合用户描述选择目标页面。每个选中的页面单独派发 analyst，并由 analyst 用 `lanhu_get_prd_scoped_evidence` 读取 `output_mode: evidence_only` 的单页证据，固定 `include_child_pages: false`、`confirmed_child_page_ids: []`。相邻页面、同文档其它模块、父级流程页、未选中的子页、垃圾站 / 旧页面、导航关联页或 Lanhu AI 认为“相关”的页面不会进入该页面包。

`.lanhu/` 文档需要先通过 analyst 的确认门禁，再由用户确认 `index.md` 和 `scopeConfirmationSummary` 后，Superpowers 才基于它进入 `brainstorming`。如果 analyst 返回 `status: need_confirmation`，主会话只展示阻塞问题清单、packageDir 和 indexPath，不读取完整 evidence markdown、完整 HTML 或 Lanhu 原始输出；用户答案会回传同一角色 analyst 更新 evidence package，直到 `confirmationGate.status: clear`。缺少后端接口字段名、数据库列名、枚举编码或代码模型属性名不应阻塞 Lanhu 包，除非源证据连产品语义字段/控件含义、可见性、必填/默认/只读、校验、状态、权限、交互或范围都无法确认。

Frontend Markdown evidence package 会保留 XML-like 的 1:1 原始需求界面复刻。Frontend HTML evidence package 会生成 `index.html` evidence reader 和 `prototype/index.html` 1:1 原始需求界面复刻；prototype 使用真实 HTML 控件，因此 HTML 正文不需要重复输出“控件类型”文案。无设计稿时，原始需求界面布局就是后续开发布局依据；有设计稿时，布局可能由设计稿调整，但 UI 控件仍来自原始需求定义。HTML prototype 只允许简单 CSS/JS 用于阅读、核对、导航、基础显隐和状态可视化；具体交互流程必须在 `index.html` 中作为源事实表述，不能写成生产逻辑、业务流程实现或技术方案。

`role-prd/` 主题定义固定 PRD evidence package 结构和必覆盖维度；AI 可以自定义内容组织和表达，但不能改变包结构、章节职责、产物边界或后续 Superpowers 依赖的输入形态。蓝湖原始需求中的明确事实不得因模板主题分类装不下而遗失、弱化或合并成不可追溯摘要；analyst 可以按源需求创建具体源事实主题，例如“计费规则源事实”“消息通知源事实”“导入导出源事实”，但不能用“其他/杂项”泛化兜底。文档中不应包含最终验收标准、Given / When / Then、测试点、测试用例、技术测试方案、前端组件拆分、后端接口推测、数据库影响、实现方案、代码文件影响、前后端边界推断、异常/风险推断或 Superpowers plan tasks。

lanhu-mcp 没有安装或不可用时，不影响 adapter 使用；用户可以粘贴需求并按已确认角色生成 `.lanhu/` evidence package，或直接走普通 Superpowers 流程。

### 4.8 初始化项目 wiki 知识

```text
init-wiki skill
init-wiki skill payments and order workflow
```

这一步用于第一次从当前项目 inventory 中辅助 agent 生成轻量 starter wiki。脚本只提供语言、依赖、目录、样例文件和 indexed wiki page 候选；是否写入、写到哪里由 agent 判断，并遵守目标 root 的 `wiki.updateAuthorization`。写入 shared wiki 的 starter 内容也必须中性化；当前系统特有标识应留在 project wiki 或改写为中性术语。后续开发中不要把它当作日常维护入口，日常沉淀知识应由 `update-wiki` skill 判断写入 `.superpowers/wiki/` 还是 `.shared-superpowers/wiki/` 并审查。

---

## 5. 日常开发中的 wiki 披露

### 5.1 brainstorming 阶段

Superpowers `brainstorming` 在理解需求并提出设计方案前，会调用 `wiki-researcher`：

```yaml
task: <用户需求和当前理解>
phase: brainstorm
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
focus: <已知模块或关注点>
maxWikiPages: 3
```

`wiki-researcher` 会从存在的 project/shared root index 开始渐进读取，返回少量相关 wiki 页面。shared wiki 可以来自本地 `.shared-superpowers/wiki/`，也可以来自配置好的 GitHub-backed shared-wiki MCP。没有匹配项、MCP 不可用，或两个 wiki root 都没有 `index.md` 时，不阻塞 brainstorming，只说明 caveat 并继续。

### 5.2 writing-plans 阶段

Superpowers `writing-plans` 在拆分任务前，会调用 `wiki-researcher` 正式选择项目/共享 wiki 页面：

```yaml
task: <已确认 Superpowers spec 或需求摘要>
phase: plan
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
planPath: docs/superpowers/plans/<filename>.md
planSummary: <计划目标和任务区域>
maxWikiPages: 5
```

writing-plans 默认把详细约束写入与 plan 同名的 sidecar 文件；如果 shared wiki 页面来自 GitHub-backed MCP，sidecar 还要记录 source-aware metadata：

```text
docs/superpowers/plans/<plan-stem>.wiki-context.json
```

plan 必须包含轻量入口：

```markdown
## Referenced Project Wiki

Detailed wiki context: `docs/superpowers/plans/<plan-stem>.wiki-context.json`

- `.superpowers/wiki/domain/user.md` — applies to Tasks 1, 2, and 4; hard constraint: use `account_id` as the stable identity key.
```

`.wiki-context.json` 是 schemaVersion 3 的 source of truth，应使用 page-rooted `wikiPages` 结构：每个 page 包含路径、root、source、`displayPath`、本地 `localPath` 或 MCP `wikiPath` / `revision`、来自伴随 `<stem>.index.md` 的有界 `documentContext`，以及嵌套 `sections`。每个 section 包含 `sectionId` / `section_name`、适用任务、hard constraint 标记、必要原文锚点、caveats、section-level `reread` metadata，以及 `implementation` / `test` / `review` / `general` 分类约束；无法可靠分类但不能丢失的约束放入 `general`。`documentContext` 只用于保留页面级主语和适用范围，不能包含 sibling sections 或整页正文；对于 `source: github_mcp`，`.shared-superpowers/wiki/<path>.md` 是逻辑展示路径而不是本地文件路径。如果 selected wiki page 与本次 Superpowers spec 冲突，应先让用户确认是调整需求 spec 还是更新项目 wiki，再写 plan。


### 5.3 执行阶段

`executing-plans` 和 `subagent-driven-development` 执行前应读取 plan 中的 `Referenced Project Wiki`，定位其中链接的 `.wiki-context.json`，再用 plugin-root `wiki_context_render.py` 按 task / role 渲染约束块。硬约束 section 的 forced reread 应注入有界 document context 加选中 section 全文，而不是补读整页 wiki。

执行阶段不应默认：

- 重新从项目/共享 wiki root 选择 wiki 页面。
- 临时在执行阶段重新解释 wiki 约束，或绕过 planning 生成的 `.wiki-context.json`。
- 绕过 plan 中已经确认的 wiki 约束。

如果 plan 缺少 `Referenced Project Wiki`、链接的 `.wiki-context.json` 缺失，或 context 明显不足，应提示回到 planning 阶段补齐。

### 5.4 bug 调试中的 wiki 边界

`systematic-debugging` 仍以复现、证据收集、root cause 假设验证和修复验收为主。adapter 只在 Phase 1 已完成、失败边界已经收窄后提供条件式 wiki 辅助：

```yaml
task: <bug 现象、期望 / 实际行为、已收集证据>
phase: debug
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
focus: <已收窄的组件、契约、工作流或 gotcha>
changedFiles:
  - <已被证据关联的文件，可选>
maxWikiPages: 2
```

只有怀疑项目特定契约、known gotcha、跨层边界或工作流约定时才应调用；明显局部错误、泛型语言错误、宽泛“搜 wiki”、或 root cause evidence 前不应调用。

如果 bug 发生在执行某个 Superpowers plan 的过程中，应先读取当前 plan 的 `Referenced Project Wiki` 和链接的 `.wiki-context.json`。没有当前 plan 上下文时，不默认搜索旧 plan，也不扫描全 wiki。

wiki 结果只作为待验证线索，不是 root cause evidence。所有 wiki-derived idea 都必须继续用代码、日志、测试、复现或诊断验证；wiki 缺失、无相关页面或与运行时证据冲突时，不阻塞调试，并以当前运行时证据为准。调试阶段不生成 `.wiki-context.json`，不更新 `.superpowers/wiki/` 或 `.shared-superpowers/wiki/`；修复验证后如有复盘价值，再走 `break-loop`，只有 durable knowledge 才交给 `update-wiki`。

### 5.5 worktree 原始分支收尾

当 Superpowers 通过 `using-git-worktrees` 创建 linked worktree 时，adapter 会让它在新 worktree 的 private git-dir 中记录本地临时 metadata：原始分支、原始 worktree 和原始 HEAD。这个文件用于 `finishing-a-development-branch` 判断“这次 worktree 是从哪个分支创建的”。

如果 metadata 有效，收尾菜单会提供明确的“合并回原始分支”选项，并优先在原始 worktree 中执行 merge，避免在 feature worktree 中 checkout 已被其他 worktree 占用的分支。如果 metadata 缺失、损坏，或创建 worktree 时处于 detached HEAD，则回退到 Superpowers 原生 base branch 判断 / 询问流程。

该 metadata 不进入项目文档和版本控制；不要把它写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区。

### 5.6 手动 fallback：渐进读取 wiki

正常流程由 `wiki-researcher` 完成渐进选择。只有在排障、解释规则，或 `wiki-researcher` 不可用而需要手动 fallback 时，才按以下顺序读取：

1. `.superpowers/wiki/index.md` 和 `.shared-superpowers/wiki/index.md` 中存在的入口
2. 各 root 内相关子目录的 `index.md`
3. 任务真正需要的 leaf wiki page 文件；如果只需某个 section，优先带上 companion index 中的标题 / 概览作为有界上下文，而不是读取 sibling sections 或整页正文。

不要在会话开始时一次性读取整个 `.superpowers/wiki/` 或 `.shared-superpowers/wiki/` 目录。

---

## 6. 任务结束后更新 wiki

任务完成后，如果 agent 判断产生了未来还会复用的实现知识，安装后的 `update-wiki` skill 会审查并更新合适的 wiki root（`.superpowers/wiki/` 或 `.shared-superpowers/wiki/`）。没有值得沉淀的内容时，应明确说明无需更新，不强制写入。

适合回写的内容包括：

- API / payload / command contract
- validation 和 error behavior
- 非显而易见的实现约束
- 项目约定
- 调试 gotcha
- 跨层 checklist
- 重要设计决策及原因

不适合回写的内容包括：

- 临时任务过程
- 一次性修复流水账
- 可以从代码直接看出来的普通结构
- 没有验证过的猜测

`update-wiki` 是 adapter skill。触发后，agent 应读取 indexed wiki pages，做语义去重和归属判断，检查目标 leaf wiki page 是否过大或语义混杂，再更新 leaf wiki page 并刷新 index；写入 shared wiki 前必须把内容改写为中性、可迁移表述，不能出现系统特有标识。脚本只用于候选展示、路径安全、配置化中性化拒绝、格式校验、过大页面机械报告和索引刷新。

当目标 leaf wiki page 过大时，`update-wiki` 不应按固定 chunk 拆成 `part-1` / `part-2`，而应由 agent 按 ownership 拆分。默认优先在当前目录平铺创建少量 sibling leaf pages；只有原页面已经变成多个稳定子主题集合、需要局部导航，或拆分后会产生多个子页时，才创建主题目录和该目录下的 `index.md`。

---

## 7. 用户日常应该记住的入口

| 场景 | 用户入口 | 说明 |
|---|---|---|
| 安装 adapter | `./manage.sh install` | 将 overlay 写入 Superpowers 插件目录 |
| 校验安装 | `./manage.sh verify` | 检查 overlay、agent、native skill patch 和 hook 配置 |
| 初始化 wiki 模板 | `./manage.sh bootstrap-wiki /path/to/project --template standard` / `--wiki-root shared` | 创建 `.superpowers/wiki/` 或 `.shared-superpowers/wiki/`；shared root 会同时落地 `.shared-superpowers/scripts/` |
| 发布 shared wiki | `publish-shared-wiki` skill | 提交并推送 `.shared-superpowers/wiki` submodule，更新主项目 submodule 指针 |
| 导入已有 wiki | `import-wiki` skill | 有已有wiki 目录时在 Claude Code 中执行 |
| 初次生成 starter wiki | `init-wiki` skill | 在 Claude Code 中执行 |
| 设计阶段参考项目 wiki | Superpowers `brainstorming` + `wiki-researcher` | 自动轻量披露相关项目 wiki 页面 |
| 计划阶段固化项目 wiki | Superpowers `writing-plans` + `Referenced Project Wiki` + `.wiki-context.json` | 自动选择 wiki、生成详细约束产物，并在 plan 中写入轻量入口 |
| bug 调试辅助 | Superpowers `systematic-debugging` + `wiki-researcher` | Phase 1 证据收窄后才条件式查少量 wiki，wiki 线索必须继续验证 |
| 沉淀长期知识 | `update-wiki` skill | 由 agent 在任务后自动审查是否需要执行 |
| 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者使用 |
| Multica workspace issue flow | `./manage.sh multica-bootstrap --superpowers-source /path/to/superpowers --target-repo /path/to/project --issue-template smoke --dry-run`，具体流程切换 `--issue-template`，确认后加 `--apply` | 生成 workspace skill pack，并通过真实 Multica issue assignment 触发 Claude Code agent task |

---

## 8. 什么时候才需要看底层脚本

普通用户不需要直接调用 `superpowers/scripts/*.py`。

以下情况才需要查看或直接运行底层脚本：

- adapter 开发者正在调试某个 skill 的执行层。
- 自动化测试需要覆盖 command 背后的脚本行为。
- release-check / self-test 在本地验证 adapter 安装产物。
- 排查 manifest、native skill patch、hook 配置、wiki 索引等底层状态。

即使在这些情况下，也要记住：最终验收标准仍然是用户能否在 Claude Code 等工具里通过 Superpowers skill / agent 集成路径正常使用 Superpowers + adapter。
