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
- 可选安装体验：如果用户已配置 lanhu-mcp，可用 `/lanhu-requirements` 先确认前端/后端角色，再路由到 `lanhu-frontend-requirements-analyst` 或 `lanhu-backend-requirements-analyst`，由专用 analyst 直接写入 `.lanhu/MM-DD-需求名称/` 需求包、判断待确认点是否阻塞 Superpowers，并只向主会话返回路径 / 状态 / 范围判断摘要；单个交付边界写 `prd.md`，多个交付边界写入 `prds/`，并用 `index.md` 作为入口和 PRD 关系权威来源。PRD 会显式标记 `新增`、`差量调整`、`现有上下文`、`待确认`、`全量重构`、`全量替换`，先由 analyst 自行判断，再把 `scopeConfirmationSummary` 交给用户二次确认。前端角色 PRD 会在 `## 二、本次变更范围判定` 和 `## 四、页面展示规则` 下加入低保真 XML-like 页面布局结构草图，并把 `用户操作与交互规则` 作为一个主题集中展开；当 `## 七、页面状态流转` 是复杂状态页面时，会补一张 Mermaid flowchart，简单页面可只保留表格。如 analyst 返回 `status: need_confirmation`，主会话只展示紧凑阻塞问题并把用户答案回传 analyst 修复 PRD；`confirmationGate.status: clear` 且用户确认 `index.md` 和 `scopeConfirmationSummary` 后才进入 Superpowers `brainstorming`。
- 可选图谱辅助：如果项目已有 graphify 能力或 `graphify-out/` 产物，`graphify-researcher` 只在 agent 判断需要关系线索时提供 candidate hints，不作为必经步骤。
- 在 `brainstorming` 阶段轻量披露相关项目 wiki 页面。
- 在 `writing-plans` 阶段正式选择相关项目 wiki 页面，生成配套 `.wiki-context.md` 约束产物，并要求 plan 写入轻量 `Referenced Project Wiki` 入口。
- 在执行阶段只消费 plan 中已经确认的 `Referenced Project Wiki` 和其链接的 `.wiki-context.md`。
- 在 `systematic-debugging` 中，只有 Phase 1 证据已经收窄到具体组件、契约、工作流或项目约定后，才允许条件式调用 `wiki-researcher` 查少量相关项目 wiki；只有证据已收窄且需要调用方、依赖或邻近模块线索时，才可条件式调用 `graphify-researcher`。wiki 和 graphify 都只作为待验证线索，不替代 root cause evidence。
- `update-wiki` 写入前读取目标 root 的 settings：`.superpowers/settings.json` 控制 project wiki，`.shared-superpowers/settings.json` 控制 shared wiki；默认更新已有页面跳过授权，创建新 wiki 文档询问用户授权；写入 shared wiki 前必须把内容中性化，不能保留当前系统特有标识。如团队使用 GitHub-backed shared-wiki MCP，则 shared wiki 写入通过 MCP validate patch + branch + PR，不直接改本地 shared wiki。
- 安装 `break-loop` skill，用于 Superpowers `systematic-debugging` 修复并验证 bug 后做深度复盘，并在有长期价值时把候选交给 `update-wiki`。

`/import-wiki`、`/init-wiki`、`/lanhu-requirements` 在自身产物完成前都是独立 adapter command，不应自动触发 Superpowers 的 completion、review、verification 等收尾技能；只有命令明确交接且用户确认后才进入下一步 Superpowers workflow。`break-loop` 是 bug 修复后的 adapter skill：它衔接 Superpowers `systematic-debugging`，只在 bug 已修复并验证后做后置复盘。`update-wiki` 是自动触发的 adapter maintenance skill：任务完成、修 bug、评审或讨论后，如果 agent 判断产生了 durable implementation knowledge，才审查并更新合适的 wiki root（`.superpowers/wiki/` 或 `.shared-superpowers/wiki/`）；它的本地 wiki 校验不替代 Superpowers 实现验证。

Python 脚本是 command / skill / agent 背后的执行层，不是最终用户的主要交互入口。

---

## 2. adapter 插入 Superpowers 后发生了什么

安装 adapter 后，adapter 会把 overlay 写入用户已安装的 Superpowers 插件目录：

```text
Superpowers 插件目录
├── agents/
│   ├── wiki-researcher.md
│   ├── lanhu-frontend-requirements-analyst.md
│   ├── lanhu-backend-requirements-analyst.md
│   └── graphify-researcher.md
├── commands/
│   ├── init-wiki.md
│   ├── import-wiki.md
│   └── lanhu-requirements.md
├── skills/
│   ├── break-loop/
│   ├── wiki-progressive-disclosure/
│   └── update-wiki/
└── scripts/
    └── adapter 执行脚本
```

`wiki-progressive-disclosure` 会继续安装，但它只是说明性 / fallback skill；正常 `brainstorming` 和 `writing-plans` 流程由 `wiki-researcher` 直接完成 wiki 选择。

同时 adapter 会 patch Superpowers 的 native skills：

- `using-superpowers`：声明 adapter workflow boundary。standalone adapter command 和 adapter maintenance skill 的本地完成，不等于 Superpowers development-task completion；正常 `brainstorming`、`writing-plans`、`executing-plans`、`subagent-driven-development`、`systematic-debugging` 流程仍保留自己的 verification 和后续 `update-wiki` 机制。
- `brainstorming`：如果用户给出蓝湖链接且 lanhu-mcp 可用，先确认前端/后端 PRD 角色，再路由到 `lanhu-frontend-requirements-analyst` 或 `lanhu-backend-requirements-analyst` 直接生成 `.lanhu/MM-DD-需求名称/` 蓝湖角色 PRD 需求包；主会话只接收 status、confirmationGate、packageDir、indexPath、writtenFiles、openQuestions、caveats 等轻量摘要，`index.md` 是用户确认和后续读取的入口。如存在阻塞确认点，先让 analyst 清空 `confirmationGate`，再让用户确认 `index.md`；随后在提出设计方案前调用 `wiki-researcher` 获取轻量项目 wiki 上下文。
- `writing-plans`：在拆分任务前调用 `wiki-researcher` 正式选择项目/共享 wiki 页面，生成 `docs/superpowers/plans/<plan-stem>.wiki-context.md`，并要求 plan 写入轻量 `Referenced Project Wiki` 入口；在需求已确认、源码已初步探索但关系边界仍不确定时，才可调用 `graphify-researcher` 获取候选关系线索。
- `systematic-debugging`：Phase 1 先复现、收集错误、检查变更并收窄失败边界；只有怀疑项目特定契约、known gotcha、跨层边界或工作流约定时，才用 `phase: debug`、`maxWikiPages: 2` 条件式查询 wiki；只有已收窄到具体边界且需要调用方 / 依赖 / 邻近模块线索时，才条件式查询 graphify。
- `executing-plans`：执行前读取 plan 中的 `Referenced Project Wiki` 和链接的 `.wiki-context.md`，不重新选择 wiki 页面。
- `subagent-driven-development`：把 plan 中的 `Referenced Project Wiki` 和链接的 `.wiki-context.md` 约束传给 implementer / reviewer subagent。
- `using-git-worktrees`：创建 worktree 时把原始分支、原始 worktree 和原始 HEAD 记录到新 worktree 的 private git-dir metadata。
- `finishing-a-development-branch`：metadata 有效时，提供明确合并回创建 worktree 前原始分支的收尾选项。

当前流程不安装 SessionStart hook；`wiki-researcher` 会在 `brainstorming` 和 `writing-plans` 阶段按需读取 `.superpowers/wiki/` 和 `.shared-superpowers/wiki/`，并可在 `systematic-debugging` Phase 1 证据收窄后作为低噪音调试辅助被条件式调用。worktree origin metadata 是本地临时协调状态，不写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区。

---

## 3. 用户视角的完整推荐执行顺序

| 顺序 | 阶段 | 入口 | 是否每次都需要 | 目的 |
|---|---|---|---|---|
| 0 | 安装 Superpowers | `/plugin install superpowers@claude-plugins-official` | 只需一次 | 先安装 Superpowers 主插件 |
| 1 | 安装 adapter | `./manage.sh install` | 只需一次；Superpowers 升级后重跑 | 写入 adapter overlay、agent、command、skill、script；默认覆盖所有已安装 Superpowers 版本目录 |
| 2 | 校验 adapter | `./manage.sh verify` | 安装或升级后 | 确认安装产物和 native skill patch 完整 |
| 3 | 初始化 wiki 模板 | `./manage.sh bootstrap-wiki /path/to/project --template standard` | 每个目标项目一次 | 创建 `.superpowers/wiki/` wiki 目录；如需要共享知识库，可用 `--wiki-root shared` 创建 `.shared-superpowers/wiki/` |
| 4 | 导入已有 wiki | `/import-wiki` | 有已有 wiki 或文档时才需要 | 把已有 wiki 或文档导入到 `.superpowers/wiki/`，或用 `--wiki-root shared` 导入 `.shared-superpowers/wiki/` |
| 4.5 | 可选 GitHub shared wiki MCP | `/shared-wiki-mcp` | 使用独立 GitHub shared-wiki 仓库时 | 通过 copyable MCP server 读取 shared wiki，并把更新作为 branch + PR 提交 |
| 5 | 初始化 starter wiki | `/init-wiki` | 每个目标项目首次使用时 | 从当前项目结构生成第一版轻量 wiki 知识 |
| 6 | 可选蓝湖角色 PRD | `/lanhu-requirements <蓝湖链接> 前端/后端` | 有蓝湖链接且已配置 lanhu-mcp 时 | 先确认前端/后端角色；由角色 analyst 直接生成 `.lanhu/MM-DD-需求名称/` 需求包并只向主会话返回路径摘要和确认门禁；单个交付边界写 `prd.md`，多个交付边界写 `prds/`，`index.md` 作为入口和 PRD 关系权威来源；阻塞确认点清零且用户确认 `index.md` 后作为 Superpowers 需求输入 |
| 7 | 描述需求并进入 `brainstorming` | Superpowers `brainstorming` | 复杂任务或需要设计时 | 写本次 Superpowers spec，并轻量参考项目 wiki |
| 8 | 写 implementation plan | Superpowers `writing-plans` | 有已确认 spec 后 | 正式选择项目/共享 wiki 页面，生成 `.wiki-context.md`，必要时用 graphify 候选线索辅助关系判断，并在 plan 中写入轻量 `Referenced Project Wiki` |
| 9 | 执行 plan | `executing-plans` / `subagent-driven-development` | 有 plan 时 | 按 plan 执行，并消费 `Referenced Project Wiki` 和链接的 `.wiki-context.md` |
| 9.5 | worktree 收尾 | `finishing-a-development-branch` | 使用 Superpowers worktree 开发后 | metadata 有效时，可明确合并回创建 worktree 前的原始分支 |
| 10 | 修 bug 与复盘 | `systematic-debugging` → `break-loop` | bug 修复并验证后，且需要防复发分析时 | 先用 Superpowers 修对 bug；必要时在证据收窄后低噪音查 wiki 或 graphify 候选关系线索，修复验证后再由 adapter 复盘 root cause、失败修复路径、防复发机制和可沉淀候选 |
| 11 | 任务后更新 wiki | `update-wiki` skill | 任务产生长期可复用知识时 | 审查并回写 durable implementation knowledge |
| 12 | 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者发布前 | 运行 verify、doctor、self-test、export-manifest |

用户日常在 Claude Code 中主要记住这条链：

```text
描述需求 / 可选蓝湖链接
→ 如果使用蓝湖，先确认前端/后端角色；/lanhu-requirements 路由角色 analyst 直接生成 .lanhu/MM-DD-需求名称/ 需求包，主会话只接收路径摘要和紧凑确认门禁，index.md 是入口和 PRD 关系权威来源
→ 如存在阻塞确认点，用户回答后由同一角色 analyst 修复 PRD 包，直到 confirmationGate.status: clear
→ 用户确认 .lanhu 需求包的 index.md
→ Superpowers brainstorming
→ adapter 轻量披露相关项目 wiki 页面
→ Superpowers 写并确认本次 spec
→ Superpowers writing-plans
→ adapter 正式选择项目/共享 wiki，生成 .wiki-context.md，并在 plan 写入轻量 Referenced Project Wiki
→ 如果源码初探后仍有关系边界不确定，agent 可条件式用 graphify-researcher 获取候选线索
→ Superpowers 直接读当前源码验证精确影响文件和任务步骤
→ Superpowers executing-plans / subagent-driven-development 按 plan 和 .wiki-context.md 执行
→ 遇到 bug 时先用 Superpowers systematic-debugging 复现、收集证据并收窄失败边界
→ 如果怀疑项目特定契约 / gotcha / 跨层边界，才条件式用 wiki-researcher 查少量 wiki；如果需要调用方 / 依赖关系线索，才条件式用 graphify-researcher，并继续用代码、日志、测试或复现验证
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

高级配置：`adapter.config.json` 默认是 `{}`，不会改变任何 subagent 模型；adapter agent 会保持 `model: inherit`，Superpowers 上游 prompt template 也不会插入模型字段。如果需要为 `wiki-researcher`、`graphify-researcher`、Lanhu analyst 或 Superpowers 的 implementer / reviewer 类 prompt template 指定模型，可参考 `adapter.config.example.jsonc`，把需要的条目复制为无注释 JSON 后再运行 `./manage.sh install`。`subagentModels.agents` 写入 adapter 原生 agent frontmatter，允许类似 `deepseek-v4-pro[1m]` 的 Claude Code 方括号后缀模型名，但 install 会对非 `inherit` / `sonnet` / `opus` / `haiku` 值提示 warning，提醒确认当前 Claude Code 运行时支持该模型。`subagentModels.upstreamPromptTemplates` 会变成 Claude Code Task / Agent 的 `model` 参数；由于 Claude Code 当前只允许该字段使用 `sonnet`、`opus`、`haiku`，因此 install 会拒绝其它值。这样做是为了避免安装后的 markdown 看起来已经配置成功，但 Claude Code 运行时 subagent 忽略该字段、回退到其它模型或延后失败。其中 `final-code-reviewer` 只作用于 `subagent-driven-development` 所有任务完成后的最终整体评审；未配置时会降级使用 `code-reviewer` 的模型配置。Superpowers 升级后，如果某个已配置模型的上游 prompt template 结构变化导致无法应用，install 会一次性列出失败的 subagent id、目标路径和原因；未配置模型的 subagent 不会因为模板变化阻塞安装。

如果 adapter 是作为其他项目中的 `superpower-adapter/` 目录存在，也可以从宿主项目执行：

```bash
./superpower-adapter/manage.sh install
./superpower-adapter/manage.sh verify
```

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

允许值：`skip` 表示跳过授权，`ask` 表示写入前询问用户，`refuse` 表示拒绝该操作。settings 文件或字段缺失时使用默认值：更新已有 wiki page 为 `skip`，创建新 wiki 文档为 `ask`。`ask` 由 command / skill 在用户入口询问；执行层脚本用 `--authorized-update` 或 `--authorized-create` 表示已获得用户授权。`refuse` 会阻止写入。`sharedNeutrality` 主要用于 `.shared-superpowers/settings.json`：配置已知系统标识或正则后，执行层会拒绝把这些内容写入 shared wiki 的路径、正文、导入内容或刷新后的 index。仓库根目录的 `wiki-settings.example.jsonc` 提供可复制的带注释示例。

### 4.4 可选：同步 / 发布 shared wiki submodule

如果团队把 `.shared-superpowers/wiki/` 配成 git submodule，bootstrap 生成的 `.shared-superpowers/settings.json` 可以直接使用，也可参考 `.shared-superpowers/settings.json.example` 调整；进入 Superpowers 主流程前可运行：

```bash
python3 ./.shared-superpowers/scripts/run-hook.py sharedWikiSubmodule:sync
```

这只负责把 shared wiki submodule 拉到最新，不替代 `wiki-researcher` 的按需选择，也不替代 `update-wiki` 对 durable knowledge 的审查。

当 shared wiki 内容已经更新并需要推送远程、同时更新主项目 submodule 指针时，在 Claude Code 中使用：

```text
/publish-shared-wiki
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
/shared-wiki-mcp
```

该 MCP server 负责读取 indexed shared wiki、校验 unified diff、创建 branch、push 并打开 GitHub PR；不会自动 merge。语义判断仍由 Superpowers / adapter agent 完成：是否是 durable knowledge、是否属于 shared wiki、是否已被现有 wiki 覆盖、是否已经中性化，都不能交给 MCP 决定。

这条流程与 `.shared-superpowers/wiki/` submodule 发布流程并存；不要把同一次 shared wiki 更新同时走 `/publish-shared-wiki` 和 MCP PR flow。

### 4.6 可选：导入已有 wiki

```text
/import-wiki path/to/original-wiki-dir
/import-wiki path/to/original-wiki-dir --target imported
/import-wiki path/to/original-wiki-dir --wiki-root shared --target imported
```

`/import-wiki` 是独立 adapter command，只做已有规范的结构导入、避免覆盖和索引刷新；因为导入会创建 wiki 文档，它会遵守目标 root 的 `createNewDocument` 策略，默认先询问用户授权。导入 shared wiki 的内容必须已经中性化，不能包含系统标识、内部 URL、环境名、本地路径或当前系统专属规则；如命中 `.shared-superpowers/settings.json` 的 `sharedNeutrality` 配置，执行层会拒绝导入。如果导入内容需要语义整理，后续由 `update-wiki` skill 判断写入 `.superpowers/wiki/` 还是 `.shared-superpowers/wiki/` 并审查更新。

### 4.7 可选：从蓝湖生成角色 PRD

如果用户已配置 lanhu-mcp，可以用：

```text
/lanhu-requirements <蓝湖链接> 前端 <可选需求命名>
/lanhu-requirements <蓝湖链接> 后端 <可选需求命名>
/lanhu-requirements --role frontend <蓝湖链接> <可选需求命名>
/lanhu-requirements --role backend <蓝湖链接> <可选需求命名>
```

该命令会先确认本次要生成前端开发角色视角 PRD 还是后端开发角色视角 PRD，再路由到对应 analyst 读取蓝湖内容并直接写入只包含产品需求事实和角色 PRD 信息的需求包；PRD 会通过 `## 二、本次变更范围判定` 标记 `新增`、`差量调整`、`现有上下文`、`待确认`、`全量重构`、`全量替换`；主会话只接收 packageDir、indexPath、writtenFiles、requirementScopeJudgment、scopeConfirmationSummary、openQuestions 和 caveats 等摘要：

```text
.lanhu/MM-DD-需求名称/
├── index.md
├── prd.md
└── prds/
    ├── <交付边界1>.md
    └── <交付边界2>.md
```

单个交付边界使用 `prd.md`；多个交付边界使用 `prds/`。是否拆分 PRD 由业务交付边界决定，不由页面数量决定。列表页、详情弹窗、抽屉或跳转流程如果服务同一个用户目标和验收边界，应保留在同一个 PRD；只有子流程可独立交付、负责或验收时才拆分。tree mode 只是第一层结构化分析，tree mode 中的任意 PRD 如果仍包含独立子流程，也要继续拆分，并由 `index.md` 维护关系。

如果用户没有提供角色，或同时说“前后端都要 / 全栈”，adapter 会先询问本次生成哪一种角色 PRD；在角色明确前，不调用任何 Lanhu analyst agent，也不读取或分析蓝湖。角色明确后才路由到对应的前端或后端专用 agent。需要前端和后端两份 PRD 时，应分别运行两次命令。

如果蓝湖链接带有明确 `pageId`，adapter 会在角色确认后先读取蓝湖页面树，再按页面树收敛范围：目标页有子级时，会询问是否纳入子级并推荐纳入；目标页无子级时，只分析该页面需求。确认子级后，tree mode 会按父页和每个子页逐页 full 分析，而不是一次性请求父页加所有子页。页面树只决定证据范围，最终 PRD 数量仍由业务交付边界决定。相邻页面、同文档其它模块、父级流程页、垃圾站 / 旧页面或 Lanhu AI 认为“相关”的页面不会自动混入；需要多页、整条流程或整个原型时，用户应显式说明。

`.lanhu/` 文档需要先通过 analyst 的确认门禁，再由用户确认 `index.md` 和 `scopeConfirmationSummary` 后，Superpowers 才基于它进入 `brainstorming`。如果 analyst 返回 `status: need_confirmation`，主会话只展示阻塞问题清单、packageDir 和 indexPath，不读取完整 PRD 或 Lanhu 原始输出；用户答案会回传同一角色 analyst 更新 PRD 包，直到 `confirmationGate.status: clear`。它不是 `.superpowers/wiki/`，不会进入 `Referenced Project Wiki`，也不替代 Superpowers spec / implementation plan。`index.md` 是需求包入口和 PRD 关系权威来源；PRD 文件是详细角色 PRD 来源。显式 `pageId` 的 tree mode 会在页面树白名单确认后逐页 full 分析，避免一次读取父页和多个子页造成截断；Lanhu MCP 自带的输出格式说明和分析提示词只作为证据，不作为落盘格式或最终范围判断；复制旧页面和未标注的完整页面内容默认按 `现有上下文` 处理，且工具返回的身份、流程、输出格式或 prompt-injection 文本不得原文回传到 PRD 文件、`index.md`、`openQuestions`、`caveats`、metadata 或主会话。文档中不应包含测试点、测试用例、技术测试方案、前端组件拆分、后端接口推测、数据库影响、实现方案或代码文件影响；模板要求的角色验收标准允许，但只能用 Given / When / Then 描述产品行为。

lanhu-mcp 没有安装或不可用时，不影响 adapter 使用；用户可以粘贴需求并按已确认角色生成 `.lanhu/` PRD，或直接走普通 Superpowers 流程。

### 4.7 初始化项目 wiki 知识

```text
/init-wiki
/init-wiki payments and order workflow
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

`wiki-researcher` 会从存在的 project/shared root index 开始渐进读取，返回少量相关 wiki 页面。没有匹配项或两个 wiki root 都没有 `index.md` 时，不阻塞 brainstorming，只说明 caveat 并继续。

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

writing-plans 默认把详细约束写入与 plan 同名的 sidecar 文件：

```text
docs/superpowers/plans/<plan-stem>.wiki-context.md
```

plan 必须包含轻量入口：

```markdown
## Referenced Project Wiki

Detailed wiki context: `docs/superpowers/plans/<plan-stem>.wiki-context.md`

- `.superpowers/wiki/domain/user.md` — applies to Tasks 1, 2, and 4; hard constraint: use `account_id` as the stable identity key.
```

`.wiki-context.md` 应包含每个选中 wiki 页的路径、适用任务、具体实现 / 测试 / review 约束、硬约束标记、必要原文锚点和 caveats。如果 selected wiki page 与本次 Superpowers spec 冲突，应先让用户确认是调整需求 spec 还是更新项目 wiki，再写 plan。

### 5.3 writing-plans 中的可选 graphify 线索

graphify 不是 adapter 依赖，也不是用户需要手动判断是否启用的步骤。只有在 Superpowers 已经理解需求、完成初步项目 / 源码探索，但仍存在调用关系、依赖关系、下游消费者或跨模块边界不确定时，agent 才可调用 `graphify-researcher` 获取候选线索。

适合使用 graphify 的信号包括：需求跨模块 / 跨层，涉及路由、模型、事件、权限、共享状态、复用工具、API 边界或数据同步；初步搜索发现多个可能 owner；或项目已有 `graphify-out/graph.json` / `GRAPH_REPORT.md` 且查询成本低。

不适合使用 graphify 的情况包括：单文件、单页面、文案、样式、docs-only、局部配置修改；源码探索已经足够；graphify 不可用或需要先生成 / 更新图谱。graphify 输出只作为 candidate hints，最终 plan 的精确文件和任务步骤必须由 Superpowers 直接读当前源码验证。

如果用户手动触发 graphify，应视为用户独立做图谱查询或维护；如果随后要开发，仍需回到 Superpowers `brainstorming`、`writing-plans` 和执行流程。

### 5.4 执行阶段

`executing-plans` 和 `subagent-driven-development` 执行前应读取 plan 中的 `Referenced Project Wiki`，再读取其中链接的 `.wiki-context.md`。

执行阶段不应默认：

- 重新从项目/共享 wiki root 选择 wiki 页面。
- 临时在执行阶段重新解释 wiki 约束，或绕过 planning 生成的 `.wiki-context.md`。
- 绕过 plan 中已经确认的 wiki 约束。

如果 plan 缺少 `Referenced Project Wiki`、链接的 `.wiki-context.md` 缺失，或 context 明显不足，应提示回到 planning 阶段补齐。

### 5.5 bug 调试中的 wiki / graphify 边界

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

如果 bug 发生在执行某个 Superpowers plan 的过程中，应先读取当前 plan 的 `Referenced Project Wiki` 和链接的 `.wiki-context.md`。没有当前 plan 上下文时，不默认搜索旧 plan，也不扫描全 wiki。

wiki 结果只作为待验证线索，不是 root cause evidence。所有 wiki-derived idea 都必须继续用代码、日志、测试、复现或诊断验证；wiki 缺失、无相关页面或与运行时证据冲突时，不阻塞调试，并以当前运行时证据为准。调试阶段不生成 `.wiki-context.md`，不更新 `.superpowers/wiki/` 或 `.shared-superpowers/wiki/`；修复验证后如有复盘价值，再走 `break-loop`，只有 durable knowledge 才交给 `update-wiki`。

### 5.6 worktree 原始分支收尾

当 Superpowers 通过 `using-git-worktrees` 创建 linked worktree 时，adapter 会让它在新 worktree 的 private git-dir 中记录本地临时 metadata：原始分支、原始 worktree 和原始 HEAD。这个文件用于 `finishing-a-development-branch` 判断“这次 worktree 是从哪个分支创建的”。

如果 metadata 有效，收尾菜单会提供明确的“合并回原始分支”选项，并优先在原始 worktree 中执行 merge，避免在 feature worktree 中 checkout 已被其他 worktree 占用的分支。如果 metadata 缺失、损坏，或创建 worktree 时处于 detached HEAD，则回退到 Superpowers 原生 base branch 判断 / 询问流程。

该 metadata 不进入项目文档和版本控制；不要把它写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区。

### 5.7 手动 fallback：渐进读取 wiki

正常流程由 `wiki-researcher` 完成渐进选择。只有在排障、解释规则，或 `wiki-researcher` 不可用而需要手动 fallback 时，才按以下顺序读取：

1. `.superpowers/wiki/index.md` 和 `.shared-superpowers/wiki/index.md` 中存在的入口
2. 各 root 内相关子目录的 `index.md`
3. 任务真正需要的 leaf wiki page 文件

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
| 发布 shared wiki | `/publish-shared-wiki` | 提交并推送 `.shared-superpowers/wiki` submodule，更新主项目 submodule 指针 |
| 导入已有 wiki | `/import-wiki` | 有已有wiki 目录时在 Claude Code 中执行 |
| 初次生成 starter wiki | `/init-wiki` | 在 Claude Code 中执行 |
| 设计阶段参考项目 wiki | Superpowers `brainstorming` + `wiki-researcher` | 自动轻量披露相关项目 wiki 页面 |
| 计划阶段固化项目 wiki | Superpowers `writing-plans` + `Referenced Project Wiki` + `.wiki-context.md` | 自动选择 wiki、生成详细约束产物，并在 plan 中写入轻量入口 |
| bug 调试辅助 | Superpowers `systematic-debugging` + `wiki-researcher` | Phase 1 证据收窄后才条件式查少量 wiki，wiki 线索必须继续验证 |
| 沉淀长期知识 | `update-wiki` skill | 由 agent 在任务后自动审查是否需要执行 |
| 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者使用 |

---

## 8. 什么时候才需要看底层脚本

普通用户不需要直接调用 `superpowers/scripts/*.py`。

以下情况才需要查看或直接运行底层脚本：

- adapter 开发者正在调试某个 command 的执行层。
- 自动化测试需要覆盖 command 背后的脚本行为。
- release-check / self-test 在本地验证 adapter 安装产物。
- 排查 manifest、native skill patch、hook 配置、wiki 索引等底层状态。

即使在这些情况下，也要记住：最终验收标准仍然是用户能否在 Claude Code 等工具里通过 Superpowers command / skill / agent 集成路径正常使用 Superpowers + adapter。
