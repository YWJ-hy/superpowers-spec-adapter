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
- 安装 `source_truth_settings.py` 执行层脚本，并 patch Superpowers spec / plan pre 与 review 节点：当目标项目配置了 `.superpowers/settings.json` 的 `sourceOfTruth.sources` 时，向 spec / plan 注入短 policy / checklist prompt；执行任务完成前再按真实 changed files 做确定性 sourceOfTruth lint。未配置时静默跳过，不安装独立 verifier agent，也不生成 report / constraints sidecar。
- 可选安装体验：如果用户已配置 lanhu-mcp 并明确调用 `lanhu-requirements` skill，可先确认前端/后端角色，再路由到 `lanhu-frontend-requirements-analyst` 或 `lanhu-backend-requirements-analyst` 生成 `.lanhu/MM-DD-需求名称/` 蓝湖原始需求证据包。`brainstorming` 不执行新的蓝湖采集，只消费用户已确认的 `.lanhu/.../index.md` 包。该包是 Superpowers 的需求输入，不是 Superpowers spec，不生成最终验收标准、测试计划、技术方案或实施任务；最终 PRD artifact 只保留清洗后的生效需求，不保留用户修正、删除、忽略、确认、来源排除或冲突取舍的过程留痕。显式 `pageId` 链接会先由主会话把 URL 当作 `rootScopeUrl`、当前页当作 `rootPageId`，只调用 `lanhu_get_prd_page_scope` 获取当前页及子树的轻量 page tree metadata，再结合用户描述选择 `selectedTargetPages`；主会话在派发前不得调用 `lanhu_get_prd_scoped_evidence` 或读取完整页面 evidence。每个选中页面固定派发一个 analyst，analyst 才使用固定 scoped Lanhu MCP 序列读取自己的页面 evidence。蓝湖图片、截图和 `designInfo.images` 默认只作为候选证据；analyst 仅在标注、箭头、周边说明、用户点名、关键 UI 事实缺失等信号命中时选择性分析图片区域，默认不把图片资产保存到 `.lanhu/`。
- 蓝湖 frontend 只有一种 `frontend-prd/` 需求输入包：`frontend-prd/prd.md` 承载规则、约束、边界、系统响应和待确认问题；当存在设计稿或需要交互 demo 时，`frontend-prd/design/index.html` 作为可交互结构镜像，用真实控件 1:1 映射原始页面结构、控件关系、状态和交互路径，但不作为生产前端实现或第二份完整 PRD。蓝湖原始需求中的明确事实不得因模板主题装不下而丢失；analyst 可按源需求创建具体的源事实主题承接，例如“计费规则源事实”“消息通知源事实”“导入导出源事实”，但“AI 自定源事实主题”只是能力说明，不应作为实际标题、导航或正文主题输出。如 analyst 返回 `status: need_confirmation`，主会话只展示紧凑阻塞问题并把用户答案回传 analyst；图片相关性、是否分析高成本图片区域或是否保存原图也应走同一确认门禁。`confirmationGate.status: clear` 且用户确认 `index.md` 和 `scopeConfirmationSummary` 后才进入 Superpowers `brainstorming`。
- 在 `brainstorming` 阶段轻量披露相关项目 wiki 页面。
- 在 `writing-plans` 阶段正式选择相关项目 wiki 页面，由 `wiki-researcher` 返回 JSON selection（结构见 `contracts/wiki-selection-v1.example.jsonc`），主 agent 落到 `docs/superpowers/plans/<plan-stem>.wiki-selection.json` 后用 plugin-root `wiki_context_render.py <sidecar> --scaffold <selection> --strict --plan-path <plan>` 机械生成成形的 `.wiki-context.json` 骨架（自动补常量、`taskRouting`、每个 hardConstraint 的 `reread`、github_mcp 的顶层 `sharedWiki` 身份、默认 `destination.kind`），AI 只编辑语义路由（每段 `destination.reason`、`wikiRefs`、`globalWikiRefs`、`taskRouting.status`），并要求 plan 写入轻量 `Referenced Project Wiki` 入口。JSON 以 wiki page 为根节点，每个 page 只保留一份来自伴随 `<stem>.index.md` 的有界 `documentContext`，选中的 sections 作为子节点并保留 implementation / test / review / general 分类约束；final task 稳定后先用 `wiki_context_render.py <sidecar> --scaffold-tasks --plan-path <plan>` 从 plan 任务标题机械补 `taskId`/`taskTitle`（保留已填 `wikiRefs`），再用 `wiki_context_render.py <sidecar> --bind-fingerprints --strict --execution-ready --plan-path <plan>` 从 plan 任务文本机械 stamp `wiki/source task fingerprint` 并校验执行就绪（不手写或复制指纹）。`--scaffold` 成功后消费并删除该 selection（只留 plan 与 `.wiki-context.json`，`--keep-selection` 可保留），报结构错误时保留浅层 selection、修复后重跑 `--scaffold`，仅在生成器不可用时才回退手写 `contracts/wiki-context-v3.example.jsonc`。
- 在执行阶段只消费 plan 中已经确认的 `Referenced Project Wiki` 和其链接的 `.wiki-context.json`。`writing-plans` 在 final task 稳定后才把 selected wiki sections 绑定到 task，执行 / SDD 只按 `--task-id <stable-task-id>` 渲染该 task 的 wiki 约束，并在进入执行前先做一次 fingerprint preflight；renderer stdout 会由主 agent 捕获，并带 `## Rendered Wiki Constraints for This Task` 等边界标注直接注入当前 task / subagent prompt，不作为 `.claude-*-wiki-task*-impl.md` 或 `.claude-*-source-task*-impl.md` 这类 rendered Markdown 上下文文件持久化。如果 plan 在审核后被手工修改，先确认 selected wiki routing 仍适用于改动的 task，再重新运行 `wiki_context_render.py <sidecar> --bind-fingerprints` 刷新 `wiki/source task fingerprint`，不重写 plan。对 `hardConstraint: true` 的 section，执行阶段会通过 `--task-id <stable-task-id> --reread-list --execution-ready` 强制回读当前 task 对应的原始 wiki section 全文（通过 `<!-- wiki-section:xxx -->` 标记提取），并附带有界 `documentContext` 在 `## Hard Wiki Constraint Rereads` 边界下注入 implementer 和 reviewer prompt，确保约束不因摘要信息衰减或 section 脱离页面主语而被误用。
- Wiki 文档使用 `<!-- wiki-section:section-id -->` / `<!-- /wiki-section:section-id -->` 标记包裹独立约束主题段落，每个叶子文档都必须有 `<stem>.index.md` 伴随索引；该索引包含文档级语义概览和 section 表格。`wiki-researcher` 通过读取 per-document index 快速判断文档和 section 相关性，未迁移到新格式的文档不参与 wiki-researcher 选择。用户可通过 `migrate-wiki` skill 将现有 wiki 迁移到 section-marker 格式。
- 在 `systematic-debugging` 中，只有 Phase 1 证据已经收窄到具体组件、契约、工作流或项目约定后，才允许条件式调用 `wiki-researcher` 查少量相关项目 wiki。wiki 只作为待验证线索，不替代 root cause evidence。
- `update-wiki` 写入前读取目标 root 的 settings：`.superpowers/settings.json` 控制 project wiki，`.shared-superpowers/settings.json` 控制 shared wiki；默认更新已有页面跳过授权，创建新 wiki 文档询问用户授权；写入 shared wiki 前必须把内容中性化，不能保留当前系统特有标识。如团队使用 GitHub-backed shared-wiki MCP，则 shared wiki 写入通过 MCP validate patch + branch + PR，不直接改本地 shared wiki。
- 安装 `break-loop` skill，用于 Superpowers `systematic-debugging` 修复并验证 bug 后做深度复盘，并在有长期价值时把候选交给 `update-wiki`。
- 安装 `scaffold-practice-skill` skill，把可复用的工程实践（管理页布局、微应用 host/child 文件结构、固定审查流程等）固化为 `.claude/skills/<name>/` 的**分层技能包**：唯一固定的是薄路由 `SKILL.md`，其余 `implement.md`/`review.md`/`rules.md`/`scripts/` 等是按需加载的开放集合（目的是渐进披露、省 token，并保证脱离 Superpowers 也能独立使用）。它也支持把现有单体 skill **非破坏式**转换为该结构（搬运全部附属文件、报告未覆盖内容、用户确认后才替换原件），并在项目 wiki `guides/skills.md` 机械登记**发现卡片**（含 companion 索引与索引链路修复），让 `wiki-researcher` 在计划阶段选中并绑定「必须使用 skill X」。关系是单向的：wiki 关联 skill，skill 不反向硬编码 wiki 路径。

`import-wiki` skill、`init-wiki` skill、`lanhu-requirements` skill 在自身产物完成前都是独立 adapter skill，不应自动触发 Superpowers 的 completion、review、verification 等收尾技能；只有 skill 明确交接且用户确认后才进入下一步 Superpowers workflow。`break-loop` 是 bug 修复后的 adapter skill：它衔接 Superpowers `systematic-debugging`，只在 bug 已修复并验证后做后置复盘。`update-wiki` 是自动触发的 adapter maintenance skill：任务完成、修 bug、评审或讨论后，如果 agent 判断产生了 durable implementation knowledge，才审查并更新合适的 wiki root（`.superpowers/wiki/` 或 `.shared-superpowers/wiki/`）；它的本地 wiki 校验不替代 Superpowers 实现验证。其中可复用的工作流程/流程性知识会被识别为 skill-pack 候选并移交 `scaffold-practice-skill`，而不是写成 wiki 叶子页；`update-wiki` 只路由、不创建 skill，且不绕过授权策略。

Python 脚本是 skill / agent 背后的执行层，不是最终用户的主要交互入口。

---

## 2. adapter 插入 Superpowers 后发生了什么

安装 adapter 后，adapter 会把 overlay 写入用户已安装的 Superpowers 插件目录：

```text
Superpowers 插件目录
├── agents/
│   ├── wiki-researcher.md
│   ├── lanhu-frontend-requirements-analyst.md
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
│   ├── scaffold-practice-skill/
│   │   └── SKILL.md
│   ├── break-loop/
│   └── update-wiki/
└── scripts/
    └── adapter 执行脚本
```

`wiki-progressive-disclosure` skill 已移除；正常 `brainstorming` 和 `writing-plans` 流程统一由 `wiki-researcher` 直接完成 wiki 选择，并通过严格 schemaVersion 3 `.wiki-context.json` 进入执行期。

同时 adapter 会 patch Superpowers 的 native skills：

- `using-superpowers`：声明 adapter workflow boundary。standalone adapter skill 和 adapter maintenance skill 的本地完成，不等于 Superpowers development-task completion；正常 `brainstorming`、`writing-plans`、`executing-plans`、`subagent-driven-development`、`systematic-debugging` 流程仍保留自己的 verification 和后续 `update-wiki` 机制。
- `brainstorming`：不执行新的蓝湖采集；如果用户给出蓝湖链接，提示先显式运行 `lanhu-requirements skill <蓝湖链接> 前端/后端`。如用户直接引用已确认的 `.lanhu/.../index.md` 或已存在证据包，则不默认重新读蓝湖，而是先读 `index.md`，再按其中索引读取同包内 `frontend-prd/prd.md`、可选 `frontend-prd/design/index.html`，或后端 `backend-prd/prd.md` / `backend-prd/prds/*.md` 等详细证据来源，作为 Superpowers spec 的需求输入。Lanhu 包不得被复制为 final spec、验收标准、测试计划、技术方案或 implementation plan。写完 spec 后按 gitignore-aware 策略决定是否提交：commit 前 `git check-ignore -q docs/superpowers/specs/<file>.md`，被忽略则不提交、禁 `git add -f`，并把「Spec written and committed」播报改为「已写入但未提交，请自行处理版本控制」；未忽略按 native 提交。
- `writing-plans`：在拆分任务前调用 `wiki-researcher` 正式选择项目/共享 wiki 页面，由 `wiki-researcher` 输出 JSON selection，主 agent 落 `docs/superpowers/plans/<plan-stem>.wiki-selection.json` 后用 `wiki_context_render.py <sidecar> --scaffold <selection> --strict --plan-path <plan>` 机械生成 `docs/superpowers/plans/<plan-stem>.wiki-context.json` 骨架并只编辑语义路由（`--scaffold` 成功后消费并删除 selection，报错则保留浅层 selection、修复后重跑，生成器不可用才回退手写 `contracts/wiki-context-v3.example.jsonc`） 补 task 脚手架、再用 `wiki_context_render.py <sidecar> --bind-fingerprints --strict --execution-ready --plan-path <plan>` 从 plan 任务文本机械 stamp `wiki/source task fingerprint` 并校验执行就绪（不手写指纹），并要求 plan 写入轻量 `Referenced Project Wiki` 入口；如果 `.superpowers/settings.json.sourceOfTruth.sources` 已配置，则在 plan pre/review 节点通过 `source_truth_settings.py --render-prompt plan-pre|plan-review` 注入短 policy / checklist。未配置时静默跳过，不调用独立 sourceOfTruth verifier，也不生成 report / constraints sidecar。plan 同样按 gitignore-aware 策略：handoff 前 `git check-ignore -q docs/superpowers/plans/<filename>.md`，被忽略则不提交 plan 及其 `.wiki-context.json` sidecar、禁 `git add -f`，仅留磁盘（执行期就地读取或经 `.worktreeinclude` 带入），并在「Plan complete and saved」播报补一句未提交、请自行处理；未忽略按 native 提交。`.wiki-candidates.jsonl` 始终从不提交。
- `plan-document-reviewer`：不重新做真实源调查，只在调用方提供 sourceOfTruth checklist 时检查 final plan 是否会直接或隐式修改 configured truth paths；`truth/edit: never` 要求修订 plan，`truth/edit: ask` 要求用户明确确认。
- `systematic-debugging`：Phase 1 先复现、收集错误、检查变更并收窄失败边界；只有怀疑项目特定契约、known gotcha、跨层边界或工作流约定时，才用 `phase: debug` 条件式查询 wiki；debug wiki 选择没有页数上限，但仍必须渐进读取并保持小范围。
- `executing-plans`：执行前读取 plan 中的 `Referenced Project Wiki` 和链接的 `.wiki-context.json`，先做一次 plugin-root `wiki_context_render.py <sidecar> --fingerprint-preflight --strict --execution-ready --plan-path <plan>`，再用 plugin-root `wiki_context_render.py --task-id <task-id> --role implementer --strict --execution-ready` 渲染 task-scoped 约束；renderer stdout 直接带 task/role/source sidecar 边界标注注入当前任务，不持久化为 rendered `.md` 上下文文件。sourceOfTruth 不再有 task-scoped renderer；任务完成前改为对本任务真实 changed paths 运行 `source_truth_settings.py --lint-changed`，按 `block` / `ask` / `warn` 结果处理后才能标记完成。
- `subagent-driven-development`：把 plan 中的 `Referenced Project Wiki` 和 `.wiki-context.json` 通过 plugin-root `wiki_context_render.py` 渲染为 task-scoped wiki 约束块；主 agent 捕获 stdout，带 task/role/source sidecar 边界标注直接注入 subagent prompt，不把 rendered Markdown 保存为 `.claude-*-wiki-task*-impl.md` 等上下文文件；dispatch 前同样先做 wiki fingerprint preflight。SDD 的 subagent 是叶子节点，只消费主 agent 注入的 task/wiki/source-truth 上下文并返回结果，禁止在 subagent 内继续派发 nested subagent 或调用 `Task` / `Agent` / `Workflow` 做二次委托；该限制不禁止主会话按 SDD 节点派发多个同级 implementer / reviewer subagents。sourceOfTruth enforcement 由任务完成前的 changed-path lint 负责，不传递 source-truth sidecar 或 rendered Markdown。
- `using-git-worktrees`：创建 worktree 时把原始分支、原始 worktree 和原始 HEAD 记录到新 worktree 的 private git-dir metadata。
- `finishing-a-development-branch`：metadata 有效时，提供明确合并回创建 worktree 前原始分支的收尾选项。

当前流程不安装 SessionStart hook，但会安装一个 PostToolUse hook（matcher 为 `Bash`，脚本 `hooks/post-merge-update-wiki`）：当某次 Bash 命令把开发分支合并进其集成分支（裸 `git merge`、`git merge --continue` 或 `gh pr merge`，含 `git -C <dir> merge`）时，hook 注入一条 `update-wiki` 提醒，让主 agent 在收尾前审查是否产生 durable knowledge。它只针对「工作被接受/合并」这个动作，不依赖固定目标分支名——所以无论合回 `main` 还是迭代分支都生效；被跳过的只是「把主干/默认分支合进当前分支」的同步方向（存在 worktree origin metadata 时按 `originalBranch` 精确判向，否则按 `main`/`master`/默认分支启发式判断）、冲突未完成（存在 `MERGE_HEAD`）和 abort/非合并命令。它**不按本地 wiki 是否存在来 gate**：shared wiki 可能是全局配置的 MCP、本地零标记，任何文件系统判断都会漏，所以 finalize 合并一律触发，是否真要回写交给 `update-wiki` 自身 gate 决定（默认 skip，对项目 wiki、本地 shared、远程 MCP shared 都是 present 才读，无可写内容或无 wiki 时干净跳过）。这条提醒只补上「合并即接受」这一步的知识沉淀，覆盖用户绕开 `finishing-a-development-branch` 直接合并的情况，不代表实现已通过验证，也无法捕获在 GitHub 网页上点击 Merge 的合并。`wiki-researcher` 会在 `brainstorming` 和 `writing-plans` 阶段按需读取 `.superpowers/wiki/` 和 `.shared-superpowers/wiki/`，并可在 `systematic-debugging` Phase 1 证据收窄后作为低噪音调试辅助被条件式调用。worktree origin metadata 是本地临时协调状态，不写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区。

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
| 6 | 可选蓝湖原始需求证据包 | `lanhu-requirements skill <蓝湖链接> 前端/后端` | 有蓝湖链接且已配置 lanhu-mcp 时 | 先确认前端/后端角色；如 URL 带 pageId，主会话先读取 URL 当前页及子树的轻量 page tree metadata，并结合用户描述选择目标页面；每个目标页面由 analyst 直接生成 `.lanhu/MM-DD-需求名称/` 或 `pages/<page-slug>/` evidence package 并只向主会话返回路径摘要和确认门禁；图片默认只按标注/箭头/缺失关键事实等信号选择性分析，不保存图片资产；frontend 生成统一 `frontend-prd/` 包；阻塞确认点清零且用户确认 `index.md` 后作为 Superpowers 需求输入 |
| 7 | 描述需求并进入 `brainstorming` | Superpowers `brainstorming` | 复杂任务或需要设计时 | 写本次 Superpowers spec，并轻量参考项目 wiki |
| 8 | 写 implementation plan | Superpowers `writing-plans` | 有已确认 spec 后 | 正式选择项目/共享 wiki 页面，生成 `.wiki-context.json`；如配置 `sourceOfTruth.sources`，注入短 plan policy / review checklist，不生成 sourceOfTruth sidecar |
| 9 | 执行 plan | `executing-plans` / `subagent-driven-development` | 有 plan 时 | 按 plan 执行，并消费 `Referenced Project Wiki` 和链接的 `.wiki-context.json`；任务完成前对真实 changed paths 做 sourceOfTruth lint |
| 9.5 | worktree 收尾 | `finishing-a-development-branch` | 使用 Superpowers worktree 开发后 | metadata 有效时，可明确合并回创建 worktree 前的原始分支 |
| 10 | 修 bug 与复盘 | `systematic-debugging` → `break-loop` | bug 修复并验证后，且需要防复发分析时 | 先用 Superpowers 修对 bug；必要时在证据收窄后低噪音查 wiki，修复验证后再由 adapter 复盘 root cause、失败修复路径、防复发机制和可沉淀候选 |
| 11 | 任务后更新 wiki | `update-wiki` skill | 任务产生长期可复用知识时 | 审查并回写 durable implementation knowledge；执行/SDD 末尾会提示本步，把开发分支合并进集成分支（含绕开 `finishing-a-development-branch` 的裸 `git merge` / `gh pr merge`）后 PostToolUse hook 也会自动提醒触发本步 |
| 12 | 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者发布前 | 运行 verify、doctor、self-test、export-manifest |

用户日常在 Claude Code 中主要记住这条链：

```text
描述需求 / 可选蓝湖链接
→ 如果使用蓝湖，先显式调用 lanhu-requirements skill；该 skill 确认前端/后端角色，如 URL 带 pageId，主会话先用轻量 page tree metadata 结合用户描述选择目标页面，再按页面路由 analyst 直接生成 .lanhu/MM-DD-需求名称/ 原始需求证据包，frontend 生成统一 frontend-prd 包（frontend-prd/prd.md + 可选 frontend-prd/design/index.html）；主会话只接收路径摘要和紧凑确认门禁，index.md 是入口和文件关系权威来源
→ 如存在阻塞确认点，用户回答后由同一角色 analyst 修复 evidence package，直到 confirmationGate.status: clear
→ 用户确认 .lanhu 证据包的 index.md
→ Superpowers brainstorming
→ adapter 轻量披露相关项目 wiki 页面
→ Superpowers 写并确认本次 spec
→ Superpowers writing-plans
→ adapter 正式选择项目/共享 wiki，生成 .wiki-context.json，并在 plan 写入轻量 Referenced Project Wiki
→ writing-plans 写完整 draft plan；如 sourceOfTruth.sources 已配置，注入短 plan policy / review checklist，避免 plan 直接或隐式修改受保护真实源
→ plan-document-reviewer 审查 final plan 是否违反 configured truth path policy；未配置时不产生 sourceOfTruth 噪声
→ Superpowers 直接读当前源码验证精确影响文件和任务步骤
→ Superpowers executing-plans / subagent-driven-development 按 plan 和 .wiki-context.json 执行；任务完成前对真实 changed paths 做 sourceOfTruth lint
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

### 4.4 可选：配置真实源校验

如果项目中有由脚本生成的 service、TypeScript 类型、OpenAPI schema、权限表、设计 token 或其它不能由 AI 直接脑补/修改的权威文件，可以在 `.superpowers/settings.json` 配置 `sourceOfTruth`：

```json
{
  "sourceOfTruth": {
    "heuristics": false,
    "sources": [
      {"paths": ["src/services/generated/**", "src/types/generated/**"], "role": "truth", "edit": "never"},
      {"paths": ["openapi/**"], "role": "truth", "edit": "ask"},
      {"paths": ["src/mocks/**", "**/*.fixture.ts"], "role": "evidence"},
      {"paths": ["dist/**", "node_modules/**"], "role": "ignore"}
    ]
  }
}
```

`heuristics` 默认关闭；未显式配置时，adapter 不会因为看到已有接口调用、mock、fixture 或组件用法就把它当成真实源。`paths` 使用 gitignore-style 语法，支持 `**`、前导 `/`、尾随 `/`、`!` 否定和后规则覆盖。

`truth + edit: never` 表示 plan 不能要求实现 agent 修改这些真实源；如果需求中字段缺失或契约不匹配，应提示用户缺了什么或回到真实源生成链路。`truth + edit: ask` 表示必须先询问用户：是修订 plan，还是把修改真实源纳入本次任务。`evidence` 只能作为线索，不能单独证明事实成立；`ignore` 不参与校验。

配置存在时，adapter 只把归一化 path pattern 和枚举 policy 渲染成短 prompt：`brainstorming` / spec review 使用 `spec-pre` / `spec-review`，`writing-plans` / plan review 使用 `plan-pre` / `plan-review`。这些 prompt 是 guard/checklist，不要求 spec 或 plan 新增固定 sourceOfTruth 区块，也不会创建 verifier report、constraints sidecar 或 task-scoped sourceOfTruth routing。

执行阶段不渲染 sourceOfTruth task constraints。每个任务完成前，执行 / SDD flow 应把本任务真实改动的 repo-relative paths 传给 `source_truth_settings.py --lint-changed`：命中 `truth/edit: never` 必须 block，命中 `truth/edit: ask` 时必须有显式用户授权（通过 `--authorized-truth-edit <path>` 传入，且不能绕过 `never`），命中 `evidence` 只给 warning。

### 4.5 可选：同步 / 发布 shared wiki submodule

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

### 4.6 可选：GitHub shared wiki MCP

如果团队把 shared wiki 维护在独立 GitHub 仓库，可复制 adapter 仓库中的 MCP server：

```text
mcp/shared-wiki/
```

在复制后的目录运行：

```bash
npm install
npm run build
```

然后做两步配置：

1. **注册一份通用 server（注册一次，user 级）**：用 `./manage.sh shared-wiki-registration` 生成一份**不含 repo 信息**的注册（`command: node`、`args: [.../dist/index.js]`，无 env），加入 Claude Code MCP 配置。server 启动时读 Claude Code 注入的 `CLAUDE_PROJECT_DIR` 自我定位项目。
2. **每个项目绑定 shared wiki**：在使用 shared wiki 的项目里写 `.shared-superpowers/settings.json` 的 `wiki.sharedMcp` 块，例如：

```jsonc
{
  "wiki": {
    "sharedMcp": {
      "repoUrl": "https://github.com/YWJ-hy/shared-wiki.git",
      "baseBranch": "master"
    }
  }
}
```

因此一份注册服务所有项目，不同项目可指向不同 shared wiki；没有声明 `wiki.sharedMcp` 的项目拿不到 MCP shared wiki（fail-closed）。注意：注册里**不要**加 `SHARED_WIKI_MCP_*` 环境变量（会覆盖每项目设置）；治理键（`updateAuthorization` / `sharedNeutrality`）属于 shared wiki 仓库内的 settings，不是消费项目的。之后可在 Claude Code 中使用：

```text
shared-wiki-mcp skill
```

该 MCP server 负责读取 indexed shared wiki、校验 unified diff、创建 branch、push 并打开 GitHub PR；不会自动 merge。语义判断仍由 Superpowers / adapter agent 完成：是否是 durable knowledge、是否属于 shared wiki、是否已被现有 wiki 覆盖、是否已经中性化，都不能交给 MCP 决定。正常 brainstorming / writing-plans / debugging 的 shared wiki 披露仍统一由 `wiki-researcher` 承担，MCP 只是它可选的 shared source 之一。

这条流程与 `.shared-superpowers/wiki/` submodule 发布流程并存；不要把同一次 shared wiki 更新同时走 `publish-shared-wiki` skill 和 MCP PR flow。

### 4.7 可选：导入已有 wiki

```text
import-wiki skill path/to/original-wiki-dir
import-wiki skill path/to/original-wiki-dir --target imported
import-wiki skill path/to/original-wiki-dir --wiki-root shared --target imported
```

`import-wiki` skill 是独立 adapter skill，只做已有规范的结构导入、避免覆盖和索引刷新；因为导入会创建 wiki 文档，它会遵守目标 root 的 `createNewDocument` 策略，默认先询问用户授权。导入 shared wiki 的内容必须已经中性化，不能包含系统标识、内部 URL、环境名、本地路径或当前系统专属规则；如命中 `.shared-superpowers/settings.json` 的 `sharedNeutrality` 配置，执行层会拒绝导入。如果导入内容需要语义整理，后续由 `update-wiki` skill 判断写入 `.superpowers/wiki/` 还是 `.shared-superpowers/wiki/` 并审查更新。

### 4.8 可选：从蓝湖生成原始需求证据包

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
├── frontend-prd/
│   ├── prd.md
│   └── design/
│       └── index.html      # 可选
└── backend-prd/
    ├── prd.md
    └── prds/
        ├── <源需求边界1>.md
        └── <源需求边界2>.md
```

前端使用 `frontend-prd/prd.md`，并按需生成 `frontend-prd/design/index.html`；后端单个源需求边界使用 `backend-prd/prd.md`，多个源需求边界使用 `backend-prd/prds/`。是否拆分由源需求事实的连贯性决定，不由页面数量决定。`index.md` 是轻量入口和文件关系权威来源，不复制详细范围审计表。

如果用户没有提供角色，或同时说“前后端都要 / 全栈”，adapter 会先询问本次生成哪一种 evidence package；在角色明确前，不调用任何 Lanhu analyst agent，也不读取或分析蓝湖。角色明确后才路由到对应的前端或后端专用 agent。需要前端和后端两份 evidence package 时，应分别运行两次命令。

如果蓝湖链接带有明确 `pageId`，adapter 会在角色确认后把该 URL 当作范围入口：先用 `lanhu_get_prd_page_scope` 只获取当前页及子树的轻量 page tree metadata，再结合用户描述选择目标页面。每个选中的页面单独派发 analyst，并由 analyst 用 `lanhu_get_prd_scoped_evidence` 读取 `output_mode: evidence_only` 的单页证据，固定 `include_child_pages: false`、`confirmed_child_page_ids: []`。相邻页面、同文档其它模块、父级流程页、未选中的子页、垃圾站 / 旧页面、导航关联页或 Lanhu AI 认为“相关”的页面不会进入该页面包。

`.lanhu/` 文档需要先通过 analyst 的确认门禁，再由用户确认 `index.md` 和 `scopeConfirmationSummary` 后，Superpowers 才基于它进入 `brainstorming`。如果 analyst 返回 `status: need_confirmation`，主会话只展示阻塞问题清单、packageDir 和 indexPath，不读取完整 evidence markdown、完整 HTML 或 Lanhu 原始输出；用户答案会回传同一角色 analyst 更新 evidence package，直到 `confirmationGate.status: clear`。缺少后端接口字段名、数据库列名、枚举编码或代码模型属性名不应阻塞 Lanhu 包，除非源证据连产品语义字段/控件含义、可见性、必填/默认/只读、校验、状态、权限、交互或范围都无法确认。分析师在通读 scoped evidence 时如顺带发现源内部自相矛盾（同一字段/控件/状态/权限/流程被赋予互斥的产品级事实），应中性陈述冲突并作为 `impact: source-fact-conflict` 的阻塞确认点交用户/产品方确认，自己不裁决、不合并，也不写成正文章节或异常/风险推断；仅涉及实现命名（接口字段名、数据库列名、枚举编码）的矛盾落非阻塞 `openQuestions`。

Frontend 统一输出 `frontend-prd/prd.md`，并在存在设计稿或需要交互 demo 时输出 `frontend-prd/design/index.html`。`prd.md` 聚焦规则、约束、边界、系统响应和待确认问题，不固定章节；HTML demo 用真实控件 1:1 映射原始页面结构、控件关系、状态和交互路径，但不是生产前端实现，也不是第二份完整 PRD。用户对原始需求的补充、修正、删减、忽略和确认答案直接反映到清洗后的有效 PRD 中，不保留过程留痕；被用户确认排除、替代、删除、忽略、超出范围或判定非权威的来源事实不会以“已剔除 / 不采用 / 已确认口径”等历史说明写入最终 artifact。如果该修改会影响 analyst 已分析出的其它字段、功能、交互、状态、权限、业务规则或数据语义，必须进入确认门禁让用户决定，不得私自级联修改；确认后只保留生效需求结论。

`frontend-prd/` / `backend-prd/` 主题定义固定 PRD evidence package 结构和必覆盖维度；AI 可以自定义内容组织和表达，但不能改变包结构、章节职责、产物边界或后续 Superpowers 依赖的输入形态。蓝湖原始需求中的明确有效事实不得因模板主题分类装不下而遗失、弱化或合并成不可追溯摘要；analyst 可以按源需求创建具体源事实主题，例如“计费规则源事实”“消息通知源事实”“导入导出源事实”，但不能把“AI 自定源事实主题 / AI 自定业务源事实主题”当成实际主题标题，也不能用“其他/杂项”泛化兜底。文档中不应包含最终验收标准、Given / When / Then、测试点、测试用例、技术测试方案、前端组件拆分、后端接口推测、数据库影响、实现方案、代码文件影响、前后端边界推断、异常/风险推断、Superpowers plan tasks，或用户修正 / 确认 / 排除 / 冲突解决的过程性留痕。

lanhu-mcp 没有安装或不可用时，不影响 adapter 使用；用户可以粘贴需求并按已确认角色生成 `.lanhu/` evidence package，或直接走普通 Superpowers 流程。

### 4.9 初始化项目 wiki 知识

```text
init-wiki skill
init-wiki skill payments and order workflow
```

这一步用于第一次从当前项目 inventory 中辅助 agent 生成轻量 starter wiki。脚本只提供语言、依赖、目录、样例文件和 indexed wiki page 候选；是否写入、写到哪里由 agent 判断，并遵守目标 root 的 `wiki.updateAuthorization`。写入 shared wiki 的 starter 内容也必须中性化；当前系统特有标识应留在 project wiki 或改写为中性术语。后续开发中不要把它当作日常维护入口，日常沉淀知识应由 `update-wiki` skill 判断写入 `.superpowers/wiki/` 还是 `.shared-superpowers/wiki/` 并审查。

---

## 5. 日常开发中的 wiki 披露

### 5.1 brainstorming 阶段

Superpowers `brainstorming` 在理解需求并提出设计方案前，会调用 `wiki-researcher`。wiki 选择不设页数上限，但仍必须渐进读取 index 和 section index，不能无目标扫描整棵 wiki：

```yaml
task: <用户需求和当前理解>
phase: brainstorm
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
sharedWikiSource: auto
focus: <已知模块或关注点>
```

`wiki-researcher` 会从存在的 project/shared root index 开始渐进读取，返回少量相关 wiki 页面。shared wiki 可以来自本地 `.shared-superpowers/wiki/`，也可以来自配置好的 GitHub-backed shared-wiki MCP。没有匹配项、MCP 不可用，或两个 wiki root 都没有 `index.md` 时，不阻塞 brainstorming，只说明 caveat 并继续。wiki 选择没有页面数量上限，但仍必须渐进读取 index 和 section index，不能无目标扫描整棵 wiki。

### 5.2 writing-plans 阶段

Superpowers `writing-plans` 在拆分任务前，会调用 `wiki-researcher` 正式选择项目/共享 wiki 页面。wiki 选择不设页数上限，但仍必须渐进读取 index 和 section index，不能无目标扫描整棵 wiki：

```yaml
task: <已确认 Superpowers spec 或需求摘要>
phase: plan
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
sharedWikiSource: auto
planPath: docs/superpowers/plans/<filename>.md
planSummary: <计划目标和任务区域>
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

`.wiki-context.json` 是 schemaVersion 3 的 source of truth，应使用 page-rooted `wikiPages` 结构：每个 page 包含路径、root、source、`displayPath`、本地 `localPath` 或 MCP `wikiPath` / `revision`、来自伴随 `<stem>.index.md` 的有界 `documentContext`，以及嵌套 `sections`。每个 section 包含 `sectionId` / `section_name`、`relevanceTo` 描述、hard constraint 标记、必要原文锚点、caveats、section-level `reread` metadata，以及 `implementation` / `test` / `review` / `general` 分类约束；无法可靠分类但不能丢失的约束放入 `general`。`taskRouting`、`taskWikiRefs`、`globalWikiRefs` 和 `destination` 在 final task 稳定后由 `wiki_context_render.py <sidecar> --scaffold-tasks` 机械补脚手架、planning agent 编辑语义路由，`wiki/source task fingerprint` 则由 `wiki_context_render.py <sidecar> --bind-fingerprints` 从 plan 任务文本机械 stamp（不手写或复制），`appliesTo` 仅作为 legacy/optional metadata，不用于执行期路由。`documentContext` 只用于保留页面级主语和适用范围，不能包含 sibling sections 或整页正文；对于 `source: github_mcp`，`.shared-superpowers/wiki/<path>.md` 是逻辑展示路径而不是本地文件路径。如果 selected wiki page 与本次 Superpowers spec 冲突，应先让用户确认是调整需求 spec 还是更新项目 wiki，再写 plan。


### 5.3 sourceOfTruth policy prompt / lint 阶段

sourceOfTruth 不再是独立 verifier / report / constraints sidecar / renderer 流程。唯一配置入口是 `.superpowers/settings.json.sourceOfTruth.sources`；未配置时，spec、plan 和执行阶段都静默跳过 sourceOfTruth，不输出 not-configured 噪声。

配置存在时，adapter 在 spec / plan 的 pre 与 review 节点渲染短 prompt：

```bash
python3 <plugin-root>/scripts/source_truth_settings.py <repo-root> --render-prompt spec-pre
python3 <plugin-root>/scripts/source_truth_settings.py <repo-root> --render-prompt spec-review
python3 <plugin-root>/scripts/source_truth_settings.py <repo-root> --render-prompt plan-pre
python3 <plugin-root>/scripts/source_truth_settings.py <repo-root> --render-prompt plan-review
```

这些 prompt 只包含归一化 path pattern、`truth/edit: never`、`truth/edit: ask`、`evidence` 和 `ignore` 等枚举 policy，用来提醒 agent / reviewer 不要直接或隐式修改受保护真实源。prompt 不读取文件内容，不输出完整 settings JSON，不要求 spec 或 plan 新增固定 sourceOfTruth 区块。

执行 / SDD 阶段可以在任务开始前渲染一次短 reminder，但真正 enforcement 发生在任务完成前的 changed-path lint：

```bash
python3 <plugin-root>/scripts/source_truth_settings.py <repo-root> --lint-changed --changed-path <repo-relative-path> --format json
```

changed paths 必须来自本任务实际 git diff / tool context。`truth/edit: never` 命中时必须 block，授权参数也不能绕过；`truth/edit: ask` 命中时必须先取得用户显式授权，并用 `--authorized-truth-edit <path>` 传入；`evidence` 只产生 warning/info，不能当作 authoritative truth。

### 5.4 执行阶段

`executing-plans` 和 `subagent-driven-development` 执行前应读取 plan 中的 `Referenced Project Wiki`，定位其中链接的 `.wiki-context.json`，再用 plugin-root `wiki_context_render.py` 先做一次 `wiki_context_render.py <sidecar> --fingerprint-preflight --execution-ready --strict --plan-path` 校验，再按 `--task-id <stable-task-id>` 渲染 selected role 约束块。主 agent / orchestrator 应捕获 renderer stdout，并在 prompt 中以 `## Rendered Wiki Constraints for This Task` 标注 source sidecar、task id、role 和 fingerprint-preflight 状态后直接注入；正常执行不应写入或传递 `.claude-*-wiki-task*-impl.md`、`.claude-*-source-task*-impl.md` 等 rendered task-context Markdown 文件。硬约束 section 的 forced reread 应通过 `--task-id <stable-task-id> --reread-list --execution-ready` 找到当前 task 的 selected hard constraints，并在 `## Hard Wiki Constraint Rereads` 下直接注入有界 document context 加选中 section 全文，而不是补读整页 wiki；多个 hard rereads 可按该 JSONL 列表批量处理，本地 wiki 使用 `wiki_read_section.py --batch-jsonl`，GitHub-backed shared wiki 优先使用 `shared_wiki_read_sections`，但注入时必须保持原始 reread-list 顺序并只包含 selected sections。renderer stdout 注入和 hard reread 是互补关系：前者是 planning 冻结后的结构化约束视图，后者是 hard section 原文权威回读。执行阶段不按 task string 模糊过滤，也不重新匹配 wiki；如果 plan 审核后被手工修改，先确认 routing 仍适用于改动的 task，再重新运行 `wiki_context_render.py <sidecar> --bind-fingerprints` 刷新 fingerprint，不重写 plan。

sourceOfTruth 执行期只做 changed-path lint，不读取 sourceOfTruth sidecar、不渲染 sourceOfTruth task constraints，也不把旧 verifier 推理作为 implementer / reviewer 默认上下文。如果 lint 返回 `block`，必须回退受保护真实源改动或转回上游真实源链路；如果返回 `ask`，必须先取得用户授权或回退；如果只有 `evidence` warning，可以继续但应在 review 中说明。

执行阶段不应默认：

- 重新从项目/共享 wiki root 选择 wiki 页面。
- 临时在执行阶段重新解释 wiki 约束，或绕过 planning 生成的 `.wiki-context.json`。
- 绕过 plan 中已经确认的 wiki 约束。

如果 plan 缺少 `Referenced Project Wiki`、链接的 `.wiki-context.json` 缺失，或 context 明显不足，应提示回到 planning 阶段补齐。

### 5.5 bug 调试中的 wiki 边界

`systematic-debugging` 仍以复现、证据收集、root cause 假设验证和修复验收为主。adapter 只在 Phase 1 已完成、失败边界已经收窄后提供条件式 wiki 辅助；debug wiki 选择没有页数上限，但仍必须渐进读取并保持小范围：

```yaml
task: <bug 现象、期望 / 实际行为、已收集证据>
phase: debug
wikiRoots:
  - .superpowers/wiki
  - .shared-superpowers/wiki
sharedWikiSource: auto
focus: <已收窄的组件、契约、工作流或 gotcha>
changedFiles:
  - <已被证据关联的文件，可选>
```

只有怀疑项目特定契约、known gotcha、跨层边界或工作流约定时才应调用；明显局部错误、泛型语言错误、宽泛“搜 wiki”、或 root cause evidence 前不应调用。

如果 bug 发生在执行某个 Superpowers plan 的过程中，应先读取当前 plan 的 `Referenced Project Wiki` 和链接的 `.wiki-context.json`。没有当前 plan 上下文时，不默认搜索旧 plan，也不扫描全 wiki。

wiki 结果只作为待验证线索，不是 root cause evidence。所有 wiki-derived idea 都必须继续用代码、日志、测试、复现或诊断验证；wiki 缺失、无相关页面或与运行时证据冲突时，不阻塞调试，并以当前运行时证据为准。调试阶段不生成 `.wiki-context.json`，不更新 `.superpowers/wiki/` 或 `.shared-superpowers/wiki/`；修复验证后如有复盘价值，再走 `break-loop`，只有 durable knowledge 才交给 `update-wiki`。

### 5.6 worktree 原始分支收尾

当 Superpowers 通过 `using-git-worktrees` 创建 linked worktree 时，adapter 会让它在新 worktree 的 private git-dir 中记录本地临时 metadata：原始分支、原始 worktree 和原始 HEAD。这个文件用于 `finishing-a-development-branch` 判断“这次 worktree 是从哪个分支创建的”。

如果 metadata 有效，收尾菜单会提供明确的“合并回原始分支”选项，并优先在原始 worktree 中执行 merge，避免在 feature worktree 中 checkout 已被其他 worktree 占用的分支。如果 metadata 缺失、损坏，或创建 worktree 时处于 detached HEAD，则回退到 Superpowers 原生 base branch 判断 / 询问流程。

该 metadata 不进入项目文档和版本控制；不要把它写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区。

### 5.7 手动 fallback：渐进读取 wiki

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

`update-wiki` 是 adapter skill。触发后，agent 应读取 indexed wiki pages，做语义去重和归属判断，检查目标 leaf wiki page 是否语义混杂，再更新 leaf wiki page 并刷新 index；写入 shared wiki 前必须把内容改写为中性、可迁移表述，不能出现系统特有标识。脚本只用于候选展示、路径安全、配置化中性化拒绝、格式校验、section/index 结构检查和索引刷新。

两层索引结构下，wiki 文件可以很大；`update-wiki` 不应按行数、字符数或固定 chunk 拆成 `part-1` / `part-2`。只有页面 owner 已经语义过载时，才由 agent 按 ownership 拆分。默认优先在当前目录平铺创建少量 sibling leaf pages；只有原页面已经变成多个稳定子主题集合、需要局部导航，或拆分后会产生多个子页时，才创建主题目录和该目录下的 `index.md`。

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
| 真实源 policy / lint | Superpowers spec/plan pre/review + execution changed-path lint | 配置 `sourceOfTruth.sources` 后注入短 policy/checklist；执行任务完成前按真实 changed paths lint，不生成 sidecar |
| bug 调试辅助 | Superpowers `systematic-debugging` + `wiki-researcher` | Phase 1 证据收窄后才条件式查少量 wiki，wiki 线索必须继续验证 |
| 沉淀长期知识 | `update-wiki` skill | 由 agent 在任务后自动审查是否需要执行 |
| 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者使用 |

---

## 8. 什么时候才需要看底层脚本

普通用户不需要直接调用 `superpowers/scripts/*.py`。

以下情况才需要查看或直接运行底层脚本：

- adapter 开发者正在调试某个 skill 的执行层。
- 自动化测试需要覆盖 command 背后的脚本行为。
- release-check / self-test 在本地验证 adapter 安装产物。
- 排查 manifest、native skill patch、hook 配置、wiki 索引等底层状态。

即使在这些情况下，也要记住：最终验收标准仍然是用户能否在 Claude Code 等工具里通过 Superpowers skill / agent 集成路径正常使用 Superpowers + adapter。
