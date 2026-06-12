# Superpowers Adapter 开发说明

本文面向 adapter 开发者，说明开发和测试 adapter 时应遵守的入口、验收和测试原则。

最终用户流程见 [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)。

---

## 1. 核心原则

adapter 的目标不是让用户直接使用 Python 脚本，而是增强用户在 Claude Code、Cursor 等工具中使用 Superpowers 的体验。

因此开发时必须遵守：

> adapter 功能的最终验收，应以 Claude Code 等工具中通过 Superpowers skill 发起的集成路径为准，不能只以直接执行 Python 脚本成功为准。

Python 脚本是执行层，skill、agent 才是用户实际接触到的产品入口。

---

## 2. 开发前必读顺序

在修改 adapter 功能前，先阅读：

1. [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)
2. 本文档
3. 相关 overlay skill 或 agent，例如：
   - `overlays/skills/break-loop/SKILL.md`，这是 Superpowers `systematic-debugging` 修复并验证 bug 后的深度复盘入口
   - `overlays/skills/update-wiki/SKILL.md`
   - `overlays/skills/init-wiki/SKILL.md`
   - `overlays/skills/import-wiki/SKILL.md`
   - `overlays/skills/lanhu-requirements/SKILL.md`，这是可选蓝湖原始需求输入包入口；必须先确认 `frontend` / `backend` 角色，统一写入 `.lanhu/MM-DD-需求名称/` package，`index.md` 是入口和文件关系权威来源，然后等待用户确认。Lanhu 包只作为 Superpowers 输入，不生成最终验收标准、测试计划、技术方案或实施任务
   - `overlays/agents/wiki-researcher.md`，这是正常流程的 wiki 选择入口
   - `overlays/scripts/source_truth_settings.py`，这是 sourceOfTruth settings-driven prompt policy / changed-path lint 的执行层；spec / plan pre 与 review 节点只消费短 prompt，执行 / SDD 阶段只对真实 changed files 做 lint
   - `overlays/agents/lanhu-frontend-requirements-analyst.md` / `overlays/agents/lanhu-backend-requirements-analyst.md`，这是可选蓝湖原始需求输入包清洗入口，不做实现分析；共享规则由 `overlays/agents/lanhu-requirements-analyst.common.md` 生成，角色模板来源维护在 `role-prd/`

如果只读 `overlays/scripts/*.py`，容易把实现层误当成用户入口，导致测试方向错误。

---

## 3. 分层模型

adapter 分为四层：

| 层 | 代表文件 | 责任 | 测试关注点 |
|---|---|---|---|
| 用户入口层 | `overlays/skills/*/SKILL.md`、`overlays/agents/*.md` | 定义 Claude Code 中用户如何调用能力 | 文案是否引导 agent 走正确流程 |
| Hook 配置层 | `lib/hook_patch.py` | 维护 adapter 的 SessionStart 兼容配置，确保当前流程不安装 adapter hook | 安装后 hook 配置是否符合当前流程 |
| 执行层 | `overlays/scripts/*.py` | 执行 wiki 初始化、导入、更新、索引、source-truth policy inspection/render 和 manifest 等文件操作 | 脚本行为是否正确、可组合 |
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

### 4.2 集成测试必须覆盖安装后的 skill 路径

如果用户提供了 Superpowers 源码目录，可以把它作为开发和调试时的初步测试目标，例如验证 overlay、patch 和脚本在源码树上是否能应用。但这只是辅助测试或非必要测试，不能替代最终验收。Superpowers 源码目录与 Claude Code 实际安装后的插件目录可能不完全相同，包括文件布局、插件缓存路径、安装记录、版本内容或运行时加载方式。

当改动影响用户功能时，必须验证安装后的 Superpowers 插件目录，至少要验证：

1. adapter 能安装到 Claude Code 实际发现的 Superpowers 插件目录；如额外验证源码目录，只能作为补充
2. `verify` 能检查到安装产物和 hook patch
3. 对应 skill 或 agent 文档仍会引导 agent 走正确流程
4. 在目标项目中能通过 Superpowers skill / agent 集成路径完成用户场景
5. 如果涉及 shared wiki submodule，先用项目本地 runner 完成同步，再验证 `publish-shared-wiki` skill 发布入口和主项目 submodule 指针更新

例如修改 `update-wiki` 相关能力时，不应只验证某个底层脚本能写入文件；脚本测试只能覆盖候选输出、路径安全、格式校验和索引刷新等机械能力。

还应确认安装后 `update-wiki` skill 会引导 agent 先判断是否存在 durable knowledge，再读取 indexed wiki pages、做语义去重、判断目标归属、检查目标 leaf page 是否语义混杂、必要时按 ownership 拆分页面、编辑 leaf wiki page 并刷新索引；不要因为文件行数或字符数大而拆分 wiki。

### 4.3 self-test 是底层回归，不是完整产品验收

`./manage.sh self-test /path/to/project` 和 `./manage.sh release-check /path/to/project` 很重要，但它们主要验证安装产物和脚本回归。

它们不能完全替代 Claude Code 中的真实 skill 使用路径。

### 4.4 新增能力时先定义用户入口

新增 adapter 能力时，先回答：

- 用户在 Claude Code 中输入什么？
- 这是 skill、hook，还是已有 skill 的扩展？
- skill 如何指导 agent 分析、确认、执行和验收？
- 底层脚本只是执行层，还是被错误地暴露成了用户入口？

只有在用户入口明确后，再实现或调整 `overlays/scripts/*.py`。涉及 wiki 内容判断的 skill 应优先由 agent 主导；Python 只做 inventory、copy、validate、refresh、section/index 结构检查和共享 wiki 中性化拒绝等机械操作，不应独立判断 durable knowledge、target ownership、拆分边界或 contract 内容。

### Wiki 文档 Section 标记规范

Wiki 叶子文档使用 `<!-- wiki-section:section-id -->` / `<!-- /wiki-section:section-id -->` HTML 注释标记包裹独立约束主题段落。Section ID 必须为 kebab-case（`[a-z0-9][a-z0-9_-]*`），反映约束的核心语义。任务绑定只在 final task 稳定后进行，执行前通过 `taskWikiRefs` / `globalWikiRefs` / `wiki/source task fingerprint` 固化到 `.wiki-context.json`，不再靠 `appliesTo` 早生成路由。

- 一个 section = 一个可独立引用的约束单元
- 多个 heading 描述同一约束主题时合并为一个 section
- 一个 heading 包含多个独立约束时拆分为多个 section
- 支持嵌套 section（父 section 包含子 section）
- hard-constraint section 在执行期会被**全文 reread**(含其标记 span 内的嵌套子 section,无长度上限),因此 hard 标记应紧包"规范规则 + 其 do/don't"。好做法 / 坏做法 / 常见错误属于同一约束单元,必须留在 hard 标记内,不得移出、不得有损摘要(尤其坏做法 / 禁止项是约束边界);只有与合规无关的背景 / 缘由 / 长篇示例画廊可放到页级 `documentContext` 概览或独立 soft 兄弟 section,避免每个 task、每个 role 反复全量注入大 section。嵌套子 section 只为独立引用,不会缩小父 section 的 reread(父 span 仍含子)。
- 每个叶子文档都必须有伴随的 `<stem>.index.md`，短文档和单一主题文档也不能跳过
- `<stem>.index.md` 必须包含文档级语义概览和 section 表格；`wiki_generate_section_index.py` 只负责刷新表格并保留已有概览
- planning 中选中的 wiki context 由 `wiki-researcher` 输出 JSON selection，主 agent 落 `.wiki-selection.json` 后用 plugin-root `wiki_context_render.py <sidecar> --scaffold <selection> --strict --plan-path <plan>` 机械生成 `.wiki-context.json` 骨架（自动补 schemaVersion 3 常量、`taskRouting`、每个 hardConstraint 的 `reread`、github_mcp 顶层 `sharedWiki`、默认 `destination.kind`），AI 只编辑语义路由，再用 plugin-root `wiki_context_render.py --validate-only --strict` 校验；`--scaffold` 成功后消费并删除 `.wiki-selection.json`（只留 plan 与 `.wiki-context.json`，`--keep-selection` 可保留），报结构错误则保留浅层 `.wiki-selection.json`、修复后重跑 `--scaffold`，仅在生成器不可用时回退手写 `contracts/wiki-context-v3.example.jsonc`；JSON 使用 page-rooted `wikiPages`，每个 page 只携带一份来自 `<stem>.index.md` 的有界 `documentContext`（标题 / 概览 / source metadata），sections 作为子节点保留 `relevanceTo`、hard constraint、reread、source anchors、caveats 和 implementation / test / review / general 分类约束；每个 `hardConstraint` section 必带 `reread` 块（由生成器自动补），否则 `--execution-ready` 校验失败；`appliesTo` 仅作为 legacy/optional metadata，不用于执行期路由；不得为了恢复上下文而注入 sibling sections 或整页正文
- `wiki-researcher` 只选择有 `<stem>.index.md` 的文档；未迁移的文档不参与选择
- 用户通过 `migrate-wiki` skill 将现有 wiki 迁移到 section-marker 格式

### Source-of-truth policy / lint 边界

sourceOfTruth 不再是独立语义 verifier / sidecar 执行约束系统。新的边界是：

- `.superpowers/settings.json.sourceOfTruth.sources` 仍是唯一配置入口。
- `source_truth_settings.py` 负责 settings 校验、路径分类、短 prompt policy 渲染和 changed-path lint。
- `brainstorming` / spec pre 与 spec review 节点只接收短 policy / checklist prompt；不要求 spec 输出新增固定区块。
- `writing-plans` / plan pre 与 plan review 节点只接收短 policy / checklist prompt；不要求 plan 输出固定真实源校验区块。
- execution / SDD 阶段不读取 sourceOfTruth sidecar，不渲染 task-scoped sourceOfTruth constraints；任务完成前只对真实 changed files 做确定性 lint。

开发时必须保持这些边界：

- `sourceOfTruth.heuristics` 目前不用于猜测真实源；truth 只来自显式 `sources` 配置。
- `paths` 使用 gitignore-style 语法，必须覆盖 `**`、前导 `/`、尾随 `/`、`!` 否定和后规则覆盖。
- `truth` 必须配置 `edit: never | ask`；`evidence` / `ignore` 不配置 `edit`。
- `truth/edit: never` 命中实际 changed path 时必须 block，授权参数也不能绕过。
- `truth/edit: ask` 命中实际 changed path 时必须有显式用户授权；执行层通过 `--authorized-truth-edit <path>` 只表示 skill/agent 已取得授权。
- `evidence` 只产生 warning/info，不作为 truth block，也不能被 prompt 当成 authoritative。
- prompt render 只能输出归一化 path pattern 和枚举 policy，不输出完整 settings JSON，不读取或输出文件内容，并控制长度。
- 不再安装或引用 sourceOfTruth verifier agent、report/constraints sidecar、sourceOfTruth renderer、task routing 或 source-truth fingerprint。

### Plugin-root 脚本执行边界

Superpowers skill / native patch 中需要执行 adapter 脚本时，必须执行安装到 Superpowers plugin 目录内的脚本，不能要求 agent 在用户项目内执行 adapter 脚本。source overlay 中应使用 `__SUPERPOWER_ADAPTER_PLUGIN_ROOT__` 占位符，安装阶段会解析为实际 plugin root。禁止在用户入口文档或 native patch 中出现 `python3 superpowers/scripts/...`、`python3 overlays/scripts/...`、`python3 scripts/...`、复制到 `docs/superpowers/plans/` 下再执行等用户项目相对路径。新增任何会被 skill 调用的脚本时，必须同步更新 `manifest.json`、`install.sh` chmod 列表、`verify.sh` 和 smoke 测试，确保安装产物存在且文档引用的是 plugin-root 脚本。

Lanhu 集成必须保持可选：不能要求用户安装 lanhu-mcp 才能使用 adapter；Lanhu 产物只能作为用户确认的原始需求输入包写入用户项目根目录，不是 Superpowers spec，也不能约束 Superpowers 后续输出。Lanhu URL 场景必须先解析 `role: frontend | backend`，skill、agent 和 native patch 的输入示例都要携带该字段；角色可由 `.superpowers/settings.json` 的 `lanhu.role` 预设，用户未显式给出角色且无配置时才询问，不读取或分析蓝湖。

显式 `pageId` 场景必须先把 Lanhu URL 当作 `rootScopeUrl`、当前页当作 `rootPageId`，由主会话只调用 `lanhu_get_prd_page_scope` 获取 URL 当前页及子树的轻量 page tree metadata，并结合用户描述选择 `selectedTargetPages`；主会话在派发前不得调用 `lanhu_get_prd_scoped_evidence` 或读取完整页面 evidence。每个选中页面必须固定使用一个 analyst subagent，subagent 再使用 scoped Lanhu MCP 工具序列：必要时 `lanhu_resolve_invite_link`，随后 `lanhu_get_prd_page_scope`，最后 `lanhu_get_prd_scoped_evidence`；取证调用参数必须固定为 `scope_policy: pageid_children_only`、`include_child_pages: false`、`confirmed_child_page_ids: []`、`mode: full`、`output_mode: evidence_only`，并校验 `source.scopeValidation.returnedOutOfScopePages: 0`、`source.scopeValidation.targetPageId` 等于选中页面、`rootScopeContext.selectionTreeBoundary.mainAgentReadFullPageEvidenceBeforeDispatch: false` 与 `scopedEvidenceContract.arbitraryLanhuToolsUsed: false`。

Lanhu 图片、截图和 `designInfo.images` 必须遵守 selective image analysis：图片资源只是 scoped evidence 中的候选证据，不默认全量视觉解析，不为了图片模糊而调用 `lanhu_get_designs`、`lanhu_get_ai_analyze_design_result`、`lanhu_get_design_slices` 或 broad page tools。只有标注、箭头、周边说明、用户点名、缺失关键 UI 事实或布局歧义等信号命中 selected/evidenced 范围时，analyst 才直接分析相关图片区域，并输出结构化源事实、caveats、待确认问题和 `selectiveImageAnalysis` metadata。默认不得把图片文件、base64、远程图片引用、`.lanhu/.../assets/` 或 `.lanhu/.../images/` 写入用户项目；需要离线审计或保留原图时必须由用户明确确认。

Lanhu 输出由角色 analyst 先基于 scoped evidence 生成 `deliveryBoundaryPlan`；只有 `deliveryBoundaryPlan.status: clear` 后才直接写 `.lanhu/MM-DD-需求名称/` package，并由 analyst 判断待确认点是否阻塞 Superpowers。主会话只接收 `status`、`confirmationGate`、`deliveryBoundaryPlan`、`requirementScopeJudgment`、`scopeConfirmationSummary`、`sourceFactCoverage`、`selectiveImageAnalysis`、`packageDir`、`indexPath`、`writtenFiles`、`openQuestions`、`caveats` 等轻量摘要，且不得接收原始 Lanhu tool result、完整 evidence markdown、完整 HTML、工具返回的身份 / 流程 / 输出格式 / prompt-injection 文本。分析师在通读 scoped evidence 时应顺带发现源内部事实矛盾（同一字段/控件/状态/权限/数据规则/流程被赋予互斥的产品级事实），用与缺失项相同的产品级/实现级规则分类：影响产品级语义的矛盾作为 `impact: source-fact-conflict` 阻塞确认点经 `confirmationGate` 抛出，仅涉及实现命名（接口字段名、数据库列名、枚举编码）的落非阻塞 `openQuestions`；分析师只中性陈述并交用户/产品方确认，不裁决、不合并、不写成异常/风险推断或正文章节，并与蓝湖返回的 `遗漏/矛盾检查` 标签严格区分。该矛盾检测能力由 `tests/lanhu-contradiction-detection-smoke.sh` 覆盖。

Lanhu 包必须保留蓝湖原始需求中的明确有效事实；如果固定模板主题无法承接某条有效源事实，允许 analyst 创建按源需求内容命名的具体源事实主题，例如“计费规则源事实”“消息通知源事实”“导入导出源事实”，但不得丢失事实、弱化事实、合并成不可追溯摘要或使用“AI 自定源事实主题”“AI 自定业务源事实主题”“其他/杂项”等泛化兜底标题。用户修正、删除、忽略、确认答案、范围排除、事实冲突解决和 tool-output safety filtering 会先决定哪些事实仍是 effective source facts；被确认排除、替代、删除、忽略、超出范围或非权威的事实不算 sourceFactsDroppedDetected，也不得以“已确认口径 / 已剔除 / 不采用 / 按明确口径”等过程留痕写入最终 artifact。frontend 只有一种输出形态：`.lanhu/MM-DD-需求名称/index.md` + `frontend-prd/prd.md` + 可选 `frontend-prd/design/index.html` / `frontend-prd/design/assets/`；`frontend-prd/prd.md` 不固定主题目录，按原始资料选择最清晰组织方式。Lanhu 包不得输出最终验收标准、Given / When / Then、测试点、测试用例、技术测试方案、前端组件拆分、后端接口推测、接口字段设计、数据库字段设计、数据库影响、实现方案、代码文件影响、前后端边界推断、异常/风险推断、独立证据映射表、用户修正/确认/排除/冲突解决过程或 Superpowers plan tasks；缺少这些技术字段名或映射信息不得作为 Lanhu 阻塞确认点.

Deprecated `lanhu.frontend.output.format` 不再决定前端输出；如目标项目仍配置该字段，`lanhu_settings.py` 只返回忽略 warning。frontend 始终由 `lanhu-frontend-requirements-analyst` 写统一 `frontend-prd/` 包：`frontend-prd/prd.md` 作为规则、约束、边界和待确认问题主文档；当存在设计稿或需要交互 demo 时，可写 `frontend-prd/design/index.html`，用于 1:1 映射页面结构、控件关系、状态和交互路径，但不追求像素级视觉、生产级响应式、真实接口或复杂脚本。HTML demo 已清楚呈现的布局、控件类型和点击路径，不应在 `prd.md` 中长篇重复。后端角色必须始终 Markdown-only。

多页面 Lanhu scope 可以使用 page fan-out，但这只是证据保真策略，不是摘要聚合策略：主会话应按 `selectedTargetPages` 调用同一个已选角色 analyst，每个页面 analyst 必须基于该页自己的 scoped Lanhu evidence 写完整页面 package；聚合根目录只写全局 `index.md`，用于页面包清单、阅读顺序、跨页面关系、root tree 选择摘要、范围摘要聚合和确认状态，不能根据 compact metadata、`.yaml` 或 summary Markdown 生成全局最终产物。只有 `confirmationGate.status: clear` 且用户确认 `index.md` 和 `scopeConfirmationSummary` 后，才能进入 Superpowers `brainstorming`。

`role-prd/` 是 Lanhu 包提示词维护源；`role-prd/frontend.md` 是唯一 frontend unified package 模板，`role-prd/backend.md` 是后端 Markdown evidence package 模板。修改 `role-prd/` 模板结构、Lanhu 输出结构或 Lanhu status schema 时，必须同步更新共享 analyst skeleton、生成后的前端/后端 analyst、skill、native patch、`verify.sh`、smoke 测试和用户流程文档。修改 clean effective PRD、effective source facts 或过程留痕规则后，必须运行 `python3 lib/sync_role_prd.py sync` / `check`，并用 Lanhu smoke 测试覆盖 forbidden process/history trace guardrails。


新增或修改 wiki 能力时，必须同时覆盖 `.superpowers/wiki/` 与 `.shared-superpowers/wiki/` 的行为边界：读取/候选可以同时查看两个 root，写入/导入/刷新必须明确目标 root，且两个 root 的 index graph 不得交叉污染。shared wiki 写入内容必须中性、可迁移，不能包含当前系统特有标识、内部 URL、环境名、本地路径、部署实例标识或当前系统专属业务规则；这些内容应留在 project wiki，或由 agent 改写为中性术语后再写入 shared wiki。写入类能力还必须遵守 root-specific settings：`.superpowers/settings.json` 控制 project wiki，`.shared-superpowers/settings.json` 控制 shared wiki；`wiki.updateAuthorization.updateExistingPage` 默认 `skip`，`wiki.updateAuthorization.createNewDocument` 默认 `ask`，允许值为 `skip` / `ask` / `refuse`；shared root 可用 `wiki.sharedNeutrality.blockedTerms` / `blockedPatterns` 配置已知系统标识的机械拒绝防线。`ask` 必须在 skill 入口先取得用户授权，再由执行层脚本通过 `--authorized-update` 或 `--authorized-create` 表示授权；`refuse` 必须阻止写入。shared wiki submodule 的同步由目标项目里的 `.shared-superpowers/settings.json` 和 `.shared-superpowers/scripts/run-hook.py` 触发，不通过 adapter 安装 SessionStart hook；发布入口使用 `publish-shared-wiki` skill，执行前必须完成 shared wiki 校验并确认 commit/push 范围。GitHub-backed shared-wiki MCP 是另一条可选后端：MCP server 必须保持 copyable，不依赖 adapter 仓库运行时路径；它只做 indexed read/search、机械校验、branch、commit、push、PR，不做 durable knowledge、target ownership 或中立化语义判断，也不能自动 merge。该后端的连接配置是**每项目**的：通用注册（不含 repo）+ server 启动时读 Claude Code 注入的 `CLAUDE_PROJECT_DIR` → 该项目 `.shared-superpowers/settings.json` 的 `wiki.sharedMcp` 自我配置（`mcp/shared-wiki/src/config.ts`），无声明则 fail-closed。改这条后端时，连接身份（`config.ts`，从消费项目读）与该 wiki 的治理（`src/wiki/policy.ts`，从 clone 出的 shared wiki 仓库读）必须分开：别把治理键塞进消费项目 settings，也别把 `cacheDir` 这类机器本地项放进项目配置；`config.ts` 改动后必须跑 `mcp/shared-wiki` 的 `npm run build` 与 `npm test`（vitest）。正常开发流程中的 shared wiki 渐进披露仍应统一由 `wiki-researcher` 发起；当 MCP 被用作 shared source 时，`.wiki-context.json` 必须记录 `source: github_mcp`、`wikiPath` 和 revision，不能把 `.shared-superpowers/wiki/<path>.md` 当成本地文件路径；选用 github_mcp 时还应在 sidecar 顶层记录 `sharedWiki` 身份（`repoUrl`+`revision`）以便执行层检测换绑漂移。

新增 bug 调试辅助能力时，bug 修复过程仍由 Superpowers `systematic-debugging` 负责，wiki 查询只能在 Phase 1 证据收窄后条件式触发，不能成为默认前置步骤，不能写 `.wiki-context.json`，不能更新 `.superpowers/wiki/` 或 `.shared-superpowers/wiki/`；复盘由 `break-loop` 负责，wiki 写入仍由 `update-wiki` 负责。

Standalone adapter skill 和 adapter maintenance skill 的本地完成不等于 Superpowers development-task completion。`init-wiki` skill、`import-wiki` skill、`lanhu-requirements` skill 以及 `update-wiki` 的本地检查、索引刷新、metadata gate 或 skip decision 不应自动触发 Superpowers completion/review/verification；但正常 `brainstorming → writing-plans → executing-plans/subagent-driven-development → verification-before-completion → update-wiki` 和 `systematic-debugging → break-loop → update-wiki` 流程不能被削弱。修改该边界时必须同步检查 `using-superpowers` native patch、相关 skill overlay、`README.md` / 用户流程文档，以及 smoke 测试。

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

5. 如果影响 skill，回到 Claude Code 中用对应 skill 做真实路径验证。

### 5.2 修改 skill 文档时

1. 阅读对应脚本，确认 skill 文档没有描述不存在的能力。
2. 安装 adapter：

```bash
./manage.sh install
./manage.sh verify
```

3. 在 Claude Code 中触发对应 adapter skill 或 Superpowers skill，例如：

```text
systematic-debugging → break-loop → update-wiki
update-wiki skill
import-wiki skill
init-wiki skill
brainstorming
writing-plans
```

4. 确认 agent 实际走的是文档指定的分析、wiki-researcher 选择和 plan 引用流程；`brainstorming` / `writing-plans` 不应要求调用已移除的 `wiki-progressive-disclosure`。
5. 如果修改 planning wiki 披露流程，确认 plan 的 `Referenced Project Wiki` 是轻量入口，并正确链接 `docs/superpowers/plans/<plan-stem>.wiki-context.json`；planning agent 由 `wiki-researcher` 输出 JSON selection，落 `.wiki-selection.json` 后用 plugin-root `wiki_context_render.py <sidecar> --scaffold <selection> --strict --plan-path <plan>` 机械生成 sidecar 骨架并只编辑语义路由（`--scaffold` 成功后消费并删除 selection，报错则保留浅层 selection、修复后重跑，生成器不可用才回退手写 `contracts/wiki-context-v3.example.jsonc`，无需读 `wiki_context_render.py` 源码反推格式）；sidecar 应使用 schemaVersion 3 page-rooted `wikiPages`，每个 page 只保留一份有界 `documentContext`，sections 保留 `relevanceTo`、分类约束、hard constraint、reread 和 anchors；final task 稳定后用 `wiki_context_render.py <sidecar> --scaffold-tasks --plan-path <plan>` 机械补 `taskWikiRefs` 脚手架（`taskId`/`taskTitle`，保留已填 `wikiRefs`），AI 再补 `taskRouting`、`globalWikiRefs` 和 `destination` 语义路由，并用 plugin-root `wiki_context_render.py <sidecar> --bind-fingerprints --strict --execution-ready --plan-path <plan>` 从 plan 任务文本机械 stamp `wiki/source task fingerprint` 并校验 sidecar 执行就绪（不得手写或复制指纹；copied placeholder 能过结构校验但会在执行期 preflight 失败），并把 selected wiki constraints 吸收到 plan/task 文本中；进入执行前先做一次 `wiki_context_render.py <sidecar> --fingerprint-preflight --execution-ready --strict --plan-path <plan>`，执行阶段必须通过 plugin-root `wiki_context_render.py --task-id <task-id> --role <role> --strict --execution-ready` 渲染 task-scoped constraints，不按 task string 过滤 wiki 约束，并通过 `--task-id <task-id> --reread-list --execution-ready` 只重读当前 task 选中的 hard section document context + section body，不注入 sibling sections 或整页正文。
6. 如果修改 source-truth 流程，确认 spec / plan pre 与 review 节点只注入 `source_truth_settings.py --render-prompt spec-pre|spec-review|plan-pre|plan-review` 的短 policy/checklist；未配置时静默跳过，不产生 not-configured 噪声；执行 / SDD 阶段只在 task 完成前用 `source_truth_settings.py --lint-changed` 检查真实 changed files。确认不再安装或引用 sourceOfTruth verifier agent、report/constraints sidecar、sourceOfTruth renderer、task routing 或 source-truth fingerprint。还要运行 `tests/source-truth-settings-smoke.sh` 和 native patch smoke，确认 prompt render、changed-path lint、removedPaths 清理和安装后 Superpowers 集成路径一致。
7. 如果修改 `systematic-debugging` wiki 辅助流程，确认它不在 Phase 1 前调用 `wiki-researcher`，只在证据收窄后使用 `phase: debug` 和 `sharedWikiSource: auto`，wiki 线索必须继续用代码、日志、测试或复现验证，且调试阶段不写 `.wiki-context.json`、不运行 `update-wiki`。debug wiki 选择没有页数上限，但仍必须渐进读取，不可无目标扫描整棵 wiki。

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
bash tests/source-truth-settings-smoke.sh
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
- 对应 `overlays/skills/*/SKILL.md`

当改变测试或验收方式时，同步更新本文档和 `CLAUDE.md` 中的开发要求。

---

## 8. 判断一次改动是否完成

一次 adapter 功能改动只有在以下条件满足时才算完成：

- 底层脚本行为正确
- overlay skill / agent 能正确引导用户路径
- 如涉及 wiki 披露主流程，验收重点是 `wiki-researcher`、plan 中的轻量 `Referenced Project Wiki`，以及其链接的 `.wiki-context.json` 约束产物；`wiki-progressive-disclosure` 已移除，不是验收标志
- 如涉及 `systematic-debugging` wiki 辅助，验收重点是证据收窄后才条件式调用 `phase: debug`、少量读取 wiki、不把 wiki 当 root cause evidence、不生成 `.wiki-context.json`、不更新 wiki
- 如涉及 Superpowers worktree 收尾流程，验收重点是安装后的 `using-git-worktrees` 是否把 origin metadata 写入 linked worktree private git-dir，以及 `finishing-a-development-branch` 是否基于该 metadata 提供合并回原始分支的选项；不要把该临时 metadata 写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区
- 如涉及合并后 `update-wiki` 提醒，验收重点是安装后的 `PostToolUse` hook（`hooks/post-merge-update-wiki`）在把开发分支合并进集成分支（含绕开 `finishing-a-development-branch` 的裸 `git merge` / `git merge --continue` / `gh pr merge`）后注入 `update-wiki` 提醒，对「主干/默认分支同步进当前分支」、冲突未完成（`MERGE_HEAD`）、abort/非合并静默；它不按本地 wiki 存在与否 gate（finalize 合并一律触发，由 update-wiki 内置 gate 决定写/skip，覆盖全局 MCP shared wiki 这种本地零标记的情况），且提醒不声称实现已通过验证；`tests/post-merge-update-wiki-hook-smoke.sh` 只证明判定逻辑，最终仍应在 Claude Code 中真实合并后确认提醒出现
- adapter 能成功安装到 Superpowers 插件目录
- `verify` / 相关测试通过
- 如影响用户流程，已在 Claude Code 等工具中从 skill 入口验证
- 文档没有把“直接运行 Python 脚本”描述成普通用户的主要使用方式