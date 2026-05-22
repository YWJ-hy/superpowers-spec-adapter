# Superpowers Adapter 开发说明

本文面向 adapter 开发者，说明开发和测试 adapter 时应遵守的入口、验收和测试原则。

最终用户流程见 [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)。

---

## 1. 核心原则

adapter 的目标不是让用户直接使用 Python 脚本，而是增强用户在 Claude Code、Cursor 等工具中使用 Superpowers 的体验。

因此开发时必须遵守：

> adapter 功能的最终验收，应以 Claude Code 等工具中通过 Superpowers command / skill 发起的集成路径为准，不能只以直接执行 Python 脚本成功为准。

Python 脚本是执行层，command、skill、agent 才是用户实际接触到的产品入口。

---

## 2. 开发前必读顺序

在修改 adapter 功能前，先阅读：

1. [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)
2. 本文档
3. 相关 overlay command、skill 或 agent，例如：
   - `overlays/skills/break-loop/SKILL.md`，这是 Superpowers `systematic-debugging` 修复并验证 bug 后的深度复盘入口
   - `overlays/skills/update-wiki/SKILL.md`
   - `overlays/commands/init-wiki.md`
   - `overlays/commands/import-wiki.md`
   - `overlays/commands/lanhu-requirements.md`，这是可选蓝湖原始需求证据包入口；必须先确认 `frontend` / `backend` 角色，统一写入 `.lanhu/MM-DD-需求名称/` evidence package，`index.md` 是入口和文件关系权威来源，然后等待用户确认。Lanhu 包只作为 Superpowers 输入，不生成最终验收标准、测试计划、技术方案或实施任务
   - `overlays/agents/wiki-researcher.md`，这是正常流程的 wiki 选择入口
   - `overlays/agents/lanhu-frontend-requirements-analyst.md` / `overlays/agents/lanhu-frontend-html-requirements-analyst.md` / `overlays/agents/lanhu-backend-requirements-analyst.md`，这是可选蓝湖原始需求证据包清洗入口，不做实现分析；共享规则由 `overlays/agents/lanhu-requirements-analyst.common.md` 生成，角色模板来源维护在 `role-prd/`
   - `overlays/agents/graphify-researcher.md`，这是可选 graphify 候选关系线索入口，不决定最终影响文件
   - `overlays/skills/wiki-progressive-disclosure/SKILL.md`，这是说明性 / fallback 规则文档

如果只读 `overlays/scripts/*.py`，容易把实现层误当成用户入口，导致测试方向错误。

---

## 3. 分层模型

adapter 分为四层：

| 层 | 代表文件 | 责任 | 测试关注点 |
|---|---|---|---|
| 用户入口层 | `overlays/commands/*.md`、`overlays/skills/*/SKILL.md`、`overlays/agents/*.md` | 定义 Claude Code 中用户如何调用能力 | 文案是否引导 agent 走正确流程 |
| Hook 配置层 | `lib/hook_patch.py` | 维护 adapter 的 SessionStart 兼容配置，确保当前流程不安装 adapter hook | 安装后 hook 配置是否符合当前流程 |
| 执行层 | `overlays/scripts/*.py` | 执行 wiki 初始化、导入、更新、索引和 manifest 等文件操作 | 脚本行为是否正确、可组合 |
| 安装层 | `install.sh`、`manage.sh`、`verify.sh`、`release-check.sh` | 把 overlay 和 native skill patch 写入 Superpowers 插件目录 | 安装产物和 patch 是否完整 |

开发时可以分别验证各层，但最终必须回到“用户入口层 + 安装后的 Superpowers 环境”确认。

当前兼容性边界：adapter 以 Superpowers 5.1.0 为适配基线；`./manage.sh install` 发现目标 Superpowers 版本更高时只警告、不拦截，并优先读取目标安装目录里的 `package.json` 版本。自动发现安装目标目前依赖 `superpowers@claude-plugins-official` 的安装记录；native skill patch 依赖上游 skill 标题和锚点文本稳定，所以升级 Superpowers 后要重点复核这些 patch 位置。

Subagent 模型配置由 `adapter.config.json` 控制，默认 `{}` 表示不改变模型路由；完整可配置 id 维护在 `adapter.config.example.jsonc`。配置会在安装阶段投射到 adapter agent frontmatter 和 Superpowers 上游 prompt template。adapter agent frontmatter 允许非标准模型名但 install 必须 warning；Superpowers 上游 prompt template 会变成 Claude Code Task / Agent 的 `model` 参数；由于 Claude Code 当前只允许该字段使用 `sonnet` / `opus` / `haiku`，其它值会让安装后的 markdown 看似配置成功但在 Claude Code 运行时被忽略、回退或延后失败，所以 install 必须硬失败。修改 `lib/subagent_models.py`、`lib/subagent_model_patch.py`、安装脚本或相关 prompt template 匹配逻辑时，必须验证空配置 no-op、配置后可应用、清空配置可移除、adapter agent 非标准模型 warning、upstream 非标准模型 hard fail、Superpowers 上游模板变化时 install 能列出所有已配置但失败的 subagent。

---

## 4. 测试原则

### 4.1 单脚本测试只能证明执行层正确

可以直接运行 Python 脚本做快速定位，例如：

```bash
python3 overlays/scripts/wiki_update_check.py --json
```

但这只能说明脚本本身可执行，不能说明用户在 Claude Code 中可以正确使用 `update-wiki` skill 或 native skill 集成路径。

直接脚本测试不能替代集成验收。

### 4.2 集成测试必须覆盖安装后的 command / skill 路径

如果用户提供了 Superpowers 源码目录，可以把它作为开发和调试时的初步测试目标，例如验证 overlay、patch 和脚本在源码树上是否能应用。但这只是辅助测试或非必要测试，不能替代最终验收。Superpowers 源码目录与 Claude Code 实际安装后的插件目录可能不完全相同，包括文件布局、插件缓存路径、安装记录、版本内容或运行时加载方式。

当改动影响用户功能时，必须验证安装后的 Superpowers 插件目录，至少要验证：

1. adapter 能安装到 Claude Code 实际发现的 Superpowers 插件目录；如额外验证源码目录，只能作为补充
2. `verify` 能检查到安装产物和 hook patch
3. 对应 command、skill 或 agent 文档仍会引导 agent 走正确流程
4. 在目标项目中能通过 Superpowers command / skill / agent 集成路径完成用户场景
5. 如果涉及 shared wiki submodule，先用项目本地 runner 完成同步，再验证 `/publish-shared-wiki` 发布入口和主项目 submodule 指针更新

例如修改 `update-wiki` 相关能力时，不应只验证某个底层脚本能写入文件；脚本测试只能覆盖候选输出、路径安全、格式校验和索引刷新等机械能力。

还应确认安装后 `update-wiki` skill 会引导 agent 先判断是否存在 durable knowledge，再读取 indexed wiki pages、做语义去重、判断目标归属、检查目标 leaf page 是否过大或语义混杂、必要时按 ownership 拆分页面、编辑 leaf wiki page 并刷新索引。

### 4.3 self-test 是底层回归，不是完整产品验收

`./manage.sh self-test /path/to/project` 和 `./manage.sh release-check /path/to/project` 很重要，但它们主要验证安装产物和脚本回归。

它们不能完全替代 Claude Code 中的真实 command / skill 使用路径。

### 4.4 新增能力时先定义用户入口

新增 adapter 能力时，先回答：

- 用户在 Claude Code 中输入什么？
- 这是 command、skill、hook，还是已有 command 的扩展？
- command / skill 如何指导 agent 分析、确认、执行和验收？
- 底层脚本只是执行层，还是被错误地暴露成了用户入口？

只有在用户入口明确后，再实现或调整 `overlays/scripts/*.py`。涉及 wiki 内容判断的 command / skill 应优先由 agent 主导；Python 只做 inventory、copy、validate、refresh、过大页面统计等机械操作，不应独立判断 durable knowledge、target ownership、拆分边界或 contract 内容。

### Wiki 文档 Section 标记规范

Wiki 叶子文档使用 `<!-- wiki-section:section-id -->` / `<!-- /wiki-section:section-id -->` HTML 注释标记包裹独立约束主题段落。Section ID 必须为 kebab-case（`[a-z0-9][a-z0-9_-]*`），反映约束的核心语义。

- 一个 section = 一个可独立引用的约束单元
- 多个 heading 描述同一约束主题时合并为一个 section
- 一个 heading 包含多个独立约束时拆分为多个 section
- 支持嵌套 section（父 section 包含子 section）
- 每个叶子文档都必须有伴随的 `<stem>.index.md`，短文档和单一主题文档也不能跳过
- `<stem>.index.md` 必须包含文档级语义概览和 section 表格；`wiki_generate_section_index.py` 只负责刷新表格并保留已有概览
- `wiki-researcher` 只选择有 `<stem>.index.md` 的文档；未迁移的文档不参与选择
- 用户通过 `/migrate-wiki` command 将现有 wiki 迁移到 section-marker 格式

Lanhu 集成必须保持可选：不能要求用户安装 lanhu-mcp 才能使用 adapter；Lanhu 产物只能作为用户确认的原始需求证据包输入写入用户项目根目录，不是 Superpowers spec，也不能约束 Superpowers 后续输出。Lanhu URL 场景必须先解析 `role: frontend | backend`，command、agent 和 native patch 的输入示例都要携带该字段；角色可由 `.superpowers/settings.json` 的 `lanhu.role` 预设，用户未显式给出角色且无配置时才询问，不读取或分析蓝湖。

显式 `pageId` 场景必须先把 Lanhu URL 当作 `rootScopeUrl`、当前页当作 `rootPageId`，由主会话只调用 `lanhu_get_prd_page_scope` 获取 URL 当前页及子树的轻量 page tree metadata，并结合用户描述选择 `selectedTargetPages`；主会话在派发前不得调用 `lanhu_get_prd_scoped_evidence` 或读取完整页面 evidence。每个选中页面必须固定使用一个 analyst subagent，subagent 再使用 scoped Lanhu MCP 工具序列：必要时 `lanhu_resolve_invite_link`，随后 `lanhu_get_prd_page_scope`，最后 `lanhu_get_prd_scoped_evidence`；取证调用参数必须固定为 `scope_policy: pageid_children_only`、`include_child_pages: false`、`confirmed_child_page_ids: []`、`mode: full`、`output_mode: evidence_only`，并校验 `source.scopeValidation.returnedOutOfScopePages: 0`、`source.scopeValidation.targetPageId` 等于选中页面、`rootScopeContext.selectionTreeBoundary.mainAgentReadFullPageEvidenceBeforeDispatch: false` 与 `scopedEvidenceContract.arbitraryLanhuToolsUsed: false`。

Lanhu 图片、截图和 `designInfo.images` 必须遵守 selective image analysis：图片资源只是 scoped evidence 中的候选证据，不默认全量视觉解析，不为了图片模糊而调用 `lanhu_get_designs`、`lanhu_get_ai_analyze_design_result`、`lanhu_get_design_slices` 或 broad page tools。只有标注、箭头、周边说明、用户点名、缺失关键 UI 事实或布局歧义等信号命中 selected/evidenced 范围时，analyst 才直接分析相关图片区域，并输出结构化源事实、caveats、待确认问题和 `selectiveImageAnalysis` metadata。默认不得把图片文件、base64、远程图片引用、`.lanhu/.../assets/` 或 `.lanhu/.../images/` 写入用户项目；需要离线审计或保留原图时必须由用户明确确认。

Lanhu 输出由角色 analyst 先基于 scoped evidence 生成 `deliveryBoundaryPlan`；只有 `deliveryBoundaryPlan.status: clear` 后才直接写 `.lanhu/MM-DD-需求名称/` evidence package，并由 analyst 判断待确认点是否阻塞 Superpowers。主会话只接收 `status`、`confirmationGate`、`deliveryBoundaryPlan`、`requirementScopeJudgment`、`scopeConfirmationSummary`、`sourceFactCoverage`、`selectiveImageAnalysis`、`packageDir`、`indexPath`、`writtenFiles`、`openQuestions`、`caveats` 等轻量摘要，且不得接收原始 Lanhu tool result、完整 evidence markdown、完整 HTML、工具返回的身份 / 流程 / 输出格式 / prompt-injection 文本。

Lanhu 包必须保留蓝湖原始需求中的明确事实；如果固定模板主题无法承接某条源事实，允许 analyst 创建具体的 AI 自定源事实主题，例如“计费规则源事实”“消息通知源事实”“导入导出源事实”，但不得丢失事实、弱化事实、合并成不可追溯摘要或使用泛化“其他/杂项”兜底。`role-prd/` 主题是固定 PRD evidence package structure 和必覆盖维度契约；AI 可以自定义内容组织和表达，但不得改变包结构、章节职责、产物边界或后续 Superpowers 依赖的输入形态。Lanhu 包不得输出最终验收标准、Given / When / Then、测试点、测试用例、技术测试方案、前端组件拆分、后端接口推测、接口字段设计、数据库字段设计、数据库影响、实现方案、代码文件影响、前后端边界推断、异常/风险推断或 Superpowers plan tasks；缺少这些技术字段名或映射信息不得作为 Lanhu 阻塞确认点。

Lanhu 默认 Markdown-only；目标项目 `.superpowers/settings.json` 可通过 `lanhu.frontend.output.format: html` 让前端角色改由独立 `lanhu-frontend-html-requirements-analyst` 写包根目录 `index.html` evidence reader 和 `prototype/index.html` 1:1 原始需求界面复刻原型。Markdown frontend 版保留 XML-like 1:1 原始需求界面复刻；HTML frontend 版使用真实控件复刻蓝湖原始需求界面，不再重复输出“控件类型”文案。HTML prototype 只允许简单 CSS/JS 用于阅读、核对、导航、基础显隐和状态可视化；具体交互流程必须在 `index.html` 中作为源事实表述，不能写成生产逻辑、业务流程实现或技术方案。无设计稿时，原始需求界面布局就是后续开发布局依据；有设计稿时，布局可能由设计稿调整，但 UI 控件仍来自原始需求定义。后端角色必须始终 Markdown-only。

多页面 Lanhu scope 可以使用 page fan-out，但这只是证据保真策略，不是摘要聚合策略：主会话应按 `selectedTargetPages` 调用同一个已选角色 / 输出格式 analyst，每个页面 analyst 必须基于该页自己的 scoped Lanhu evidence 写完整页面 evidence package；聚合根目录只写全局 `index.md`，用于页面包清单、阅读顺序、跨页面关系、root tree 选择摘要、范围摘要聚合和确认状态，不能根据 compact metadata、`.yaml` 或 summary Markdown 生成全局最终 HTML。只有 `confirmationGate.status: clear` 且用户确认 `index.md` 和 `scopeConfirmationSummary` 后，才能进入 Superpowers `brainstorming`。

`role-prd/` 是 Lanhu 证据包提示词维护源；`role-prd/frontend.md` 和 `role-prd/backend.md` 是 Markdown evidence package 模板，`role-prd/frontend_outputHtml.md` 是前端 HTML evidence package 模板。修改 `role-prd/` 模板结构、Lanhu 输出结构或 Lanhu status schema 时，必须同步更新共享 analyst skeleton、生成后的前端/后端 analyst、command、native patch、`verify.sh`、smoke 测试和用户流程文档。

Graphify 集成也必须保持可选：不能要求用户安装 graphify 才能使用 adapter，不能让用户承担“是否启用 graphify”的判断。graphify 只能由 agent 在需求已确认、源码已初步探索但关系边界仍不确定时作为 candidate hints 查询；最终影响文件必须由 Superpowers 直接读当前源码验证。用户手动触发 graphify 应视为独立图谱查询或维护，不能绕过 Superpowers `brainstorming` / `writing-plans` / execution。


新增或修改 wiki 能力时，必须同时覆盖 `.superpowers/wiki/` 与 `.shared-superpowers/wiki/` 的行为边界：读取/候选可以同时查看两个 root，写入/导入/刷新必须明确目标 root，且两个 root 的 index graph 不得交叉污染。shared wiki 写入内容必须中性、可迁移，不能包含当前系统特有标识、内部 URL、环境名、本地路径、部署实例标识或当前系统专属业务规则；这些内容应留在 project wiki，或由 agent 改写为中性术语后再写入 shared wiki。写入类能力还必须遵守 root-specific settings：`.superpowers/settings.json` 控制 project wiki，`.shared-superpowers/settings.json` 控制 shared wiki；`wiki.updateAuthorization.updateExistingPage` 默认 `skip`，`wiki.updateAuthorization.createNewDocument` 默认 `ask`，允许值为 `skip` / `ask` / `refuse`；shared root 可用 `wiki.sharedNeutrality.blockedTerms` / `blockedPatterns` 配置已知系统标识的机械拒绝防线。`ask` 必须在 command / skill 入口先取得用户授权，再由执行层脚本通过 `--authorized-update` 或 `--authorized-create` 表示授权；`refuse` 必须阻止写入。shared wiki submodule 的同步由目标项目里的 `.shared-superpowers/settings.json` 和 `.shared-superpowers/scripts/run-hook.py` 触发，不通过 adapter 安装 SessionStart hook；发布入口使用 `/publish-shared-wiki`，执行前必须完成 shared wiki 校验并确认 commit/push 范围。GitHub-backed shared-wiki MCP 是另一条可选后端：MCP server 必须保持 copyable，不依赖 adapter 仓库运行时路径；它只做 indexed read/search、机械校验、branch、commit、push、PR，不做 durable knowledge、target ownership 或中立化语义判断，也不能自动 merge。正常开发流程中的 shared wiki 渐进披露仍应统一由 `wiki-researcher` 发起；当 MCP 被用作 shared source 时，`.wiki-context.md` 必须记录 `source: github_mcp`、`wikiPath` 和 revision，不能把 `.shared-superpowers/wiki/<path>.md` 当成本地文件路径。

新增 bug 调试辅助能力时，bug 修复过程仍由 Superpowers `systematic-debugging` 负责，wiki 或 graphify 查询只能在 Phase 1 证据收窄后条件式触发，不能成为默认前置步骤，不能写 `.wiki-context.md`，不能更新 `.superpowers/wiki/` 或 `.shared-superpowers/wiki/`；复盘由 `break-loop` 负责，wiki 写入仍由 `update-wiki` 负责。

Standalone adapter command 和 adapter maintenance skill 的本地完成不等于 Superpowers development-task completion。`/init-wiki`、`/import-wiki`、`/lanhu-requirements` 以及 `update-wiki` 的本地检查、索引刷新、metadata gate 或 skip decision 不应自动触发 Superpowers completion/review/verification；但正常 `brainstorming → writing-plans → executing-plans/subagent-driven-development → verification-before-completion → update-wiki` 和 `systematic-debugging → break-loop → update-wiki` 流程不能被削弱。修改该边界时必须同步检查 `using-superpowers` native patch、相关 command/skill overlay、`README.md` / 用户流程文档，以及 smoke 测试。

---

## 5. 推荐验证顺序

### 5.1 修改脚本执行层时

1. 运行最小脚本级验证，快速定位语法或行为问题。
2. 运行相关 smoke / regression 测试。
3. 运行安装校验：

```bash
./manage.sh install
./manage.sh verify
```

4. 在目标项目执行：

```bash
./manage.sh release-check /path/to/project
```

5. 如果影响 command / skill，回到 Claude Code 中用对应 command 或 skill 做真实路径验证。

### 5.2 修改 command 或 skill 文档时

1. 阅读对应脚本，确认 command 文档没有描述不存在的能力。
2. 安装 adapter：

```bash
./manage.sh install
./manage.sh verify
```

3. 在 Claude Code 中触发对应 command 或 Superpowers skill，例如：

```text
systematic-debugging → break-loop → update-wiki
update-wiki skill
/import-wiki
/init-wiki
brainstorming
writing-plans
```

4. 确认 agent 实际走的是文档指定的分析、wiki-researcher 选择和 plan 引用流程；`brainstorming` / `writing-plans` 不应要求调用 `wiki-progressive-disclosure`。
5. 如果修改 planning wiki 披露流程，确认 plan 的 `Referenced Project Wiki` 是轻量入口，并正确链接 `docs/superpowers/plans/<plan-stem>.wiki-context.md`，执行阶段会读取该 sidecar context。
6. 如果修改 `systematic-debugging` wiki 辅助流程，确认它不在 Phase 1 前调用 `wiki-researcher`，只在证据收窄后使用 `phase: debug` 和少量 `maxWikiPages`，wiki 线索必须继续用代码、日志、测试或复现验证，且调试阶段不写 `.wiki-context.md`、不运行 `update-wiki`。

### 5.3 修改 hook 配置或安装逻辑时

1. 运行：

```bash
./manage.sh install
./manage.sh verify
./manage.sh status
```

2. 在目标项目新开 Claude Code 会话。
3. 确认当前流程不安装 adapter SessionStart hook；主流程应通过 `wiki-researcher` 和 `Referenced Project Wiki` 承载规范引用。
4. 运行：

```bash
./manage.sh release-check /path/to/project
```

---

## 6. 常用命令

在 adapter 源码目录：

```bash
./manage.sh install
./manage.sh verify
./manage.sh status
./manage.sh bootstrap-wiki /path/to/project --template standard
./manage.sh init-wiki /path/to/project "optional focus"
./manage.sh doctor /path/to/project
./manage.sh self-test /path/to/project
./manage.sh release-check /path/to/project
```

单个 smoke 测试示例：

```bash
bash tests/native-wiki-patch-smoke.sh <installed-superpowers-target>
bash tests/subagent-model-config-smoke.sh <installed-superpowers-target>
bash tests/wiki-update-check-smoke.sh <installed-superpowers-target> /path/to/project
bash tests/wiki-index-graph-smoke.sh <installed-superpowers-target> /path/to/project
bash tests/shared-wiki-submodule-smoke.sh
```

注意：这些测试需要传入安装后的 Superpowers target 和目标项目 root，不能只在 adapter 源码目录里假设路径成立。传入 Superpowers 源码目录只能作为开发期初筛；发布或完成前必须对 Claude Code 实际安装后的 Superpowers 插件目录运行安装和验证。

---

## 7. 文档更新要求

当改变用户可见流程时，同步更新：

- `ADAPTER_USER_FLOW_CN.md`
- `README.md`
- 对应 `overlays/commands/*.md` 或 `overlays/skills/*/SKILL.md`

当改变测试或验收方式时，同步更新本文档和 `CLAUDE.md` 中的开发要求。

---

## 8. 判断一次改动是否完成

一次 adapter 功能改动只有在以下条件满足时才算完成：

- 底层脚本行为正确
- overlay command / skill / agent 能正确引导用户路径
- 如涉及 wiki 披露主流程，验收重点是 `wiki-researcher`、plan 中的轻量 `Referenced Project Wiki`，以及其链接的 `.wiki-context.md` 约束产物；`wiki-progressive-disclosure` 只是说明性 / fallback，不是默认路径成功标志
- 如涉及 `systematic-debugging` wiki 辅助，验收重点是证据收窄后才条件式调用 `phase: debug`、少量读取 wiki、不把 wiki 当 root cause evidence、不生成 `.wiki-context.md`、不更新 wiki
- 如涉及 Superpowers worktree 收尾流程，验收重点是安装后的 `using-git-worktrees` 是否把 origin metadata 写入 linked worktree private git-dir，以及 `finishing-a-development-branch` 是否基于该 metadata 提供合并回原始分支的选项；不要把该临时 metadata 写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区
- adapter 能成功安装到 Superpowers 插件目录
- `verify` / 相关测试通过
- 如影响用户流程，已在 Claude Code 等工具中从 command / skill 入口验证
- 文档没有把“直接运行 Python 脚本”描述成普通用户的主要使用方式