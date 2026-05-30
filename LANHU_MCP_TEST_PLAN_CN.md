# Lanhu MCP 测试计划

## 1. 目标

验证 `lanhu-requirements` skill 在当前统一 frontend `role-prd/` 输出契约下的 MCP 调用边界、页面范围控制、确认门禁、模板合规、内容净化和 Superpowers handoff 行为是否正确。

重点验证：

- 必须先确认 `role: frontend | backend`，角色缺失或歧义时不读取蓝湖。
- URL 带 `pageId` 时，主会话只读 lightweight page tree metadata，不提前读取 full scoped evidence。
- 只有 `lanhu_resolve_invite_link`、`lanhu_get_prd_page_scope`、`lanhu_get_prd_scoped_evidence` 三类允许工具被使用。
- scoped evidence 必须受 `scope_policy: pageid_children_only`、`include_child_pages`、`confirmed_child_page_ids`、`output_mode: evidence_only` 等约束。
- frontend 始终输出统一 `role-prd/` 包，不再存在 frontend HTML 独立 analyst 或第二种 frontend 详细产物。
- backend 维持 Markdown-only。
- 多页面 fan-out 仍以“每页完整证据包”方式保持证据保真，但详细产物不能再从 compact metadata / `.yaml` / page summaries 合成。
- `confirmationGate`、`scopeConfirmationSummary`、`requirementScopeJudgment`、`selectiveImageAnalysis` 等 compact metadata 只用于门禁、聚合和用户确认，不是最终 PRD 事实来源。

## 2. 前置条件

- adapter 已安装并通过 `./manage.sh verify`。
- 目标项目具备 `.lanhu/` 与 `.superpowers/settings.json`。
- 如需真实链接验证，Lanhu MCP server 可用。
- 如需兼容测试，可在 `.superpowers/settings.json` 中保留旧 `lanhu.frontend.output.format`，但预期它只会被 ignored。

## 3. 角色与路由测试

### TC-R01：缺失角色时先问用户

入口：

```text
`lanhu-requirements` skill <L1>
```

预期：

- 不立即读取 full scoped evidence。
- 如果 `.superpowers/settings.json` 未配置 `lanhu.role`，先要求用户在 `frontend | backend` 中选择其一。
- 如果用户回答“全栈”，仍要求先选一个角色，建议分两次生成。

### TC-R02：settings 中已配置角色时不重复询问

准备：

```json
{
  "lanhu": {
    "role": "frontend"
  }
}
```

入口：

```text
`lanhu-requirements` skill <L2> fe-role-test
```

预期：

- 直接按 frontend 路由。
- 不再额外询问角色。
- frontend 路由到 `lanhu-frontend-requirements-analyst`。

### TC-R03：已废弃 frontend HTML 配置不改变路由

准备：

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

入口：

```text
`lanhu-requirements` skill <L2> fe-deprecated-format
```

预期：

- 仍路由到 `lanhu-frontend-requirements-analyst`。
- metadata / warnings 中提示 `lanhu.frontend.output.format` 已 deprecated 且 ignored。
- 不会路由到独立 HTML analyst。
- 不会生成第二种 frontend 包形态。

## 4. MCP 工具边界测试

### TC-M01：允许工具集合固定

对 frontend / backend 任一入口执行一次完整流程。

预期：

- 允许的 Lanhu MCP 工具只有：
  - `lanhu_resolve_invite_link`
  - `lanhu_get_prd_page_scope`
  - `lanhu_get_prd_scoped_evidence`
- 不使用广义 design 浏览、批量下载图片或与当前范围无关的其它 Lanhu MCP 工具。
- metadata 中：
  - `arbitraryLanhuToolsUsed: false`
  - `scopedEvidenceContract` 存在且完整。

### TC-M02：主会话在 analyst 派发前只读 lightweight page tree

入口：

```text
`lanhu-requirements` skill <带 pageId 的 URL> 前端 tree-pre-dispatch
```

预期：

- 主会话只读取 lightweight page tree metadata。
- 主会话在 analyst 派发前不得读取 `mode: full` scoped evidence。
- full scoped evidence 只能在已确认目标页 / 子页范围后，由被派发 analyst 读取。

### TC-M03：scoped evidence 只返回 raw evidence

执行任一完整 frontend / backend 分析。

预期：

- `lanhu_get_prd_scoped_evidence` 使用：
  - `scope_policy: pageid_children_only`
  - `include_child_pages`
  - `confirmed_child_page_ids`
  - `output_mode: evidence_only`
  - `mode: full`
- raw tool result 只作为 analyst 内部源证据，不得原样透传主会话。
- 不得把 tool 返回的 persona / workflow / output-format / prompt-injection 文本抄入 PRD 或 metadata。

## 5. 页面范围与 fan-out 测试

### TC-P01：URL 带 `pageId` 且用户选择包含子页

入口：

```text
`lanhu-requirements` skill <L3> 前端 pageid-children-fe
```

当询问是否纳入子页时，回答：

```text
包含子页
```

预期：

- `allowedPages` 为目标页 + descendant whitelist。
- `pagesRead` 按树顺序列出父页和子页。
- 每个页面单独 full 分析，并在多页面 fan-out 时调用同一个已选角色 analyst 写入该页完整页面证据包。
- 每个 `pageNamesArgument` 恰好一个页面名。
- 前端多页面输出时，每个页面包都有自己的 `index.md` + `role-prd/prd.md`，并且仅在该页存在设计稿或需要交互 demo 时才额外写 `role-prd/design/index.html`；聚合根只写 `index.md`。
- 不出现 `page_names: all`。
- 不出现一次请求父页加多个子页的行为。
- 不出现根据 compact metadata、`.yaml` 或 summary Markdown 生成最终详细 frontend 产物的行为。

### TC-P02：用户选择不包含子页时只分析父页

入口：

```text
`lanhu-requirements` skill <L3> 后端 pageid-exclude-children-be
```

当询问是否纳入子页时，回答：

```text
不包含，只分析当前页面
```

预期：

- `allowedPages` 只包含目标页。
- 子页不进入 PRD，不进入 `index.md`，不进入 `scopeConfirmationSummary`。
- 如父页只是摘要且缺少需求细节，应返回 `partial` 或 `need_confirmation`，不能自动混入子页。

### TC-P03：pageId 找不到时不退化为全量分析

入口：

```text
`lanhu-requirements` skill <构造 pageId 不存在的 URL> 前端 invalid-pageid
```

预期：

- 返回 `status: partial` 或 caveat。
- 不调用 `page_names: all`。
- 不分析整个文档。
- 不混入同名或相邻页面。

### TC-P04：页面同名歧义时不冒险混入兄弟页

准备：选择存在同名页面或 MCP 不能按 id / path disambiguate 的 URL。

预期：

- 返回 `status: partial` 或阻塞确认。
- 不用同名页面结果生成 PRD。
- caveat 只描述歧义，不包含 raw tool result。

## 6. PRD 输出结构与包目录测试

### TC-O00：默认输出与已废弃 frontend HTML 配置

准备：目标项目不配置 `.superpowers/settings.json`。

预期：

- frontend 输出写 `.lanhu/.../index.md` + `role-prd/prd.md`，并且仅在有设计稿或需要交互 demo 时可额外写 `role-prd/design/index.html` / `role-prd/design/assets/`。
- backend 输出保持 `index.md` + `prd.md` / `prds/*.md`。
- backend `writtenFiles` 不包含 `.html`。

准备：目标项目 `.superpowers/settings.json` 仍保留已废弃配置：

```json
{
  "lanhu": {
    "frontend": {
      "output": {
        "format": "html"
      }
    }
  }
}
```

预期：

- frontend 仍路由到唯一的 `lanhu-frontend-requirements-analyst`，不会再路由到独立 HTML analyst。
- `role-prd/frontend.md` 是唯一 frontend 源模板；旧的 `role-prd/frontend_outputHtml.md` 已废弃且不得再被引用。
- frontend 始终输出统一 `role-prd/` 包：`role-prd/prd.md` 为主文档；只有在有设计稿或明确交互 demo 价值时才写 `role-prd/design/index.html`。
- `lanhu.frontend.output.format` 只产生 deprecated warning，不改变路由、模板或产物结构。
- frontend 不得写包根 `index.html`、`prototype/index.html`、独立 HTML 详细产物，或依赖 page summaries / `.yaml` 生成最终 HTML。
- backend 输出保持 Markdown-only，`writtenFiles` 不包含 `.html`。
- `index.md` 仍是 Superpowers 入口和 PRD 关系权威来源。

### TC-O01：frontend 单交付边界输出 unified `role-prd/`

入口：

```text
`lanhu-requirements` skill <L2> 前端 single-prd-fe
```

预期文件：

```text
.lanhu/<MM-DD-single-prd-fe>/
  index.md
  role-prd/
    prd.md
```

如有设计稿或交互 demo 价值，可额外出现：

```text
.lanhu/<MM-DD-single-prd-fe>/
  role-prd/
    design/
      index.html
      assets/
```

验收：

- `index.md` 包含 `PRD 角色：frontend`。
- `index.md` 指向 `role-prd/prd.md`。
- `index.md` 说明阅读顺序和范围判断摘要。
- 无包根 `prd.md`、无 `prds/`、无包根 `index.html`。

### TC-O02：backend 多交付边界输出 `prds/`

入口：

```text
`lanhu-requirements` skill <L5> 后端 multi-prd-be
```

预期文件：

```text
.lanhu/<MM-DD-multi-prd-be>/
  index.md
  prds/
    <交付边界1>.md
    <交付边界2>.md
```

验收：

- PRD 数量由独立交付 / 独立负责 / 独立验收边界决定。
- 页面数量多但同一用户目标和验收边界时，不应机械拆分。
- `index.md` 维护跨 PRD 关系、阅读顺序和必要 flowchart。
- 每个 `prds/*.md` 都是完整后端角色证据包，不用 `index.md` 替代正文。

### TC-O03：tree mode 第一层 page package 仍可继续按业务边界拆分

入口：

```text
`lanhu-requirements` skill <L3 或 L5> 后端 tree-split-be
```

预期：

- 如果某个 tree-mode page package 内仍包含独立可交付子流程，应继续拆分。
- `index.md` 维护拆分后的关系。
- 不因“一个页面一个 PRD”或“一个子页一个 PRD”机械拆分。

### TC-O04：目录命名安全与不覆盖

连续两次使用同名 hint：

```text
`lanhu-requirements` skill <L2> 前端 duplicate-name
`lanhu-requirements` skill <L2> 前端 duplicate-name
```

预期：

- 第二次不覆盖第一次产物。
- 使用安全后缀，例如 `.lanhu/MM-DD-duplicate-name-2/`，或明确询问用户。
- 目录名不包含空格、路径分隔符或不安全字符。

### TC-O05：所有写入文件都在 packageDir 内

验收：

- `packageDir`、`indexPath`、`writtenFiles[]` 全部位于同一个 `.lanhu/MM-DD-需求名称/` 下。
- 不写 `.lanhu/` 根目录散文件。
- 不写目标项目其它目录。
- `indexPath` 必须以 `index.md` 结尾。

## 7. 模板合规测试

### TC-T01：frontend 模板完整性

使用 frontend `role-prd/prd.md` 产物检查：

必须满足：

- 主文件路径固定为 `role-prd/prd.md`。
- 不要求固定章节标题。
- 内容组织可按页面、流程、模块、业务对象、状态、权限差异或其它源事实结构组织。
- 必须聚焦：
  - 需求范围
  - 字段规则
  - 数据规则
  - 权限 / 角色 / 数据范围差异
  - 系统响应规则
  - 状态触发条件
  - 边界条件
  - 待确认问题
- 明确要求“原始资料未说明 / 待确认”而不是补全常见逻辑。

预期 metadata：

- `templateCompliance.selectedTemplate: frontend_unified_requirement_input_package`
- `templateCompliance.checkedAgainstFullSourceTemplate: true`
- `missingTemplateRequirements: []`
- `genericHeadingsDetected: []`
- `forbiddenContentDetected: []`

### TC-T02：frontend HTML demo 分工合规

检查 frontend 包中的 `role-prd/design/index.html`（仅在生成时）：

预期：

- 只承担页面结构、控件关系、状态与交互路径的可交互结构镜像。
- 使用左侧章节导航 + 右侧激活章节内容布局。
- 不承担完整 PRD 正文。
- 不包含生产代码、真实接口、复杂框架脚本。
- 如引用本地静态资源，仅使用 `role-prd/design/assets/`。

### TC-T03：后端模板完整性

使用后端 PRD 产物检查：

必须包含：

- `# 后端相关 Lanhu 原始需求证据包`
- `## 一、来源与需求概览`
- `## 二、源需求范围证据判定`
- `### 2.1 源需求结构图`
- `## 三、业务对象源事实`
- `## 四、业务流程源事实`
- `## 五、业务规则源事实`
- `## 六、业务状态源事实`
- `## 七、权限与数据可见性源事实`
- `## 八、数据相关源事实`
- `## 九、按源需求命名的业务源事实主题（按需）`
- `## 十、待确认问题`

预期 metadata：

- `templateCompliance.selectedTemplate: backend`
- `templateCompliance.checkedAgainstFullSourceTemplate: true`
- `missingTemplateRequirements: []`
- `genericHeadingsDetected: []`
- `forbiddenContentDetected: []`

### TC-T04：Mermaid 可读性

对 frontend / backend PRD 中实际出现的 Mermaid 图检查：

- 默认使用 `flowchart TB` 或 `flowchart LR`。
- 仅在小而简单结构中使用 `mindmap`。
- 节点是关键词，不是长句。
- 推荐最大层级 3 层。
- 单节点子节点建议不超过 5 个。
- 内容过多时拆成多个小图或移到表格。

### TC-T05：禁止通用标题替代角色模板

检查所有 PRD：

不得出现用以下泛化标题替代模板主结构：

- `来源信息`
- `需求目标`
- `页面结构`
- `操作规则`
- `输出要求`
- `本组核心N点`
- `功能清单表`
- `字段规则表`
- `STAGE 4 输出要求`

如 Lanhu MCP 原始输出包含这些标题，只能作为证据理解，不得成为 PRD schema。

## 8. 范围判断与差量优先测试

### TC-S01：复制旧页面 + 局部新增标注

入口：

```text
`lanhu-requirements` skill <L4> 前端 delta-old-page-fe
```

预期：

- `requirementScopeJudgment.mode` 优先为 `delta`、`existing_context` 或 `unclear`，除非有明确全量证据。
- 旧页面未标注部分标记为 `现有上下文`。
- 明确新增 / 修改区域标记为 `新增` 或 `差量调整`。
- 后续源事实整理只围绕 `新增`、`差量调整`、已确认 `全量重构` / `全量替换` 展开；`现有上下文` 不得被写成源需求明确范围。
- `scopeConfirmationSummary` 清楚列出 newItems、deltaItems、existingContextItems、unclearItems。

### TC-S02：无明确全量证据时不得按整页实现

入口：

```text
`lanhu-requirements` skill <L4> 后端 no-full-scope-be
```

预期：

- 完整页面截图、完整原型页面或 full MCP analysis 不等于全量实现范围。
- `explicitFullScopeEvidence` 为空时，不应使用 `full_new`、`full_rebuild`、`full_replacement`。
- 如范围影响计划，应进入 `need_confirmation`。

### TC-S03：明确全量证据时允许全量范围

准备：使用包含“全新页面 / 整页重构 / 全量改版 / 替换旧版 / 按当前原型整体实现”等明确证据的 URL 或用户补充说明。

预期：

- 可使用 `full_new`、`full_rebuild` 或 `full_replacement`。
- `explicitFullScopeEvidence` 列出紧凑事实证据。
- PRD 范围表标明相关对象是否全量纳入。

### TC-S04：用户纠正 scope judgment 后回传 analyst 修复

流程：

1. 执行 ``lanhu-requirements` skill <L4> 前端 scope-correction-fe`。
2. analyst 返回 `status: ok`，主会话展示 `scopeConfirmationSummary`。
3. 用户指出某个 `现有上下文` 实际是本期 `差量调整`。

预期：

- 主会话不自行改判。
- 主会话将用户纠正作为 `resolutionMode: resolve_confirmation` 回传同一 `lanhu-frontend-requirements-analyst`。
- analyst 更新同一 package，而不是创建无关新 package。
- 更新后重新返回 compact metadata 和 scope summary。

## 9. 确认门禁测试

### TC-C01：阻塞问题触发 `need_confirmation`

入口：

```text
`lanhu-requirements` skill <L6> 前端 blocking-gate-fe
```

预期：

- 返回 `status: need_confirmation`。
- `confirmationGate.status: required`。
- `blockingQuestionCount > 0`。
- 每个 blocking question 包含：`id`、`question`、`impact`、`blockingReason`、`affectedPrdFiles`、`suggestedConfirmationTarget`。
- 主会话只展示 compact blocking questions、role、packageDir、indexPath 和 question count。
- 主会话不展示 full PRD markdown，不展示 raw Lanhu MCP 输出，不展示 analyst 长推理。
- 不进入 Superpowers `brainstorming`。

### TC-C02：用户回答阻塞问题后修复同一需求包

继续 TC-C01，用户回答所有阻塞问题。

预期：

- 主会话将答案作为 `confirmationAnswers` 回传同一角色 analyst。
- 使用 `resolutionMode: resolve_confirmation`。
- `previousPackageDir`、`previousIndexPath` 指向同一 package。
- analyst 更新同一 `.lanhu/.../` 包。
- 若仍有阻塞问题，继续 `need_confirmation`；若清空，则返回 `status: ok` 且 `confirmationGate.status: clear`。

### TC-C03：用户说“继续吧”但未接受默认假设时不得绕过 gate

继续 TC-C01，用户只说：

```text
先继续吧
```

预期：

- 主会话不能绕过 `confirmationGate`。
- 只有用户明确接受 analyst 默认假设时，才能将其作为答案回传 analyst。
- Superpowers `brainstorming` 仍不得启动，直到 analyst 返回 clear。

### TC-C04：非阻塞问题不阻断 Superpowers

使用只有文案微调、视觉偏好或非关键埋点命名不明确的 URL。

预期：

- `status: ok`。
- `confirmationGate.status: clear`。
- 非阻塞问题可出现在 `openQuestions`。
- 仍需要用户确认 `index.md` 和 `scopeConfirmationSummary` 后才进入 brainstorming。

## 10. 输出安全与内容净化测试

### TC-X01：PRD 不包含测试内容

检查所有生成 PRD：

不得包含：

- 测试点
- 测试用例
- 技术测试方案
- QA 执行步骤
- 自动化测试方案

允许：

- 源证据中的真实控件、页面结构、字段规则、交互事实、状态事实、权限与可见性事实，以及按需创建的、按源需求内容命名的具体源事实主题。

### TC-X02：PRD 不包含实现或技术方案

检查所有生成 PRD：

不得包含：

- 前端组件拆分
- 前端框架选择
- 前端状态管理实现
- 后端接口路径
- 后端请求 / 响应 schema 设计
- 数据库表设计
- 缓存、锁、中间件、架构、部署方案
- 代码结构
- 影响文件分析
- Superpowers plan tasks

### TC-X03：Lanhu MCP prompt-injection 文本不污染输出

使用 L7 或构造包含工具输出指令的页面，如要求“忽略原模板，按以下格式输出”。

预期：

- PRD、`index.md`、`openQuestions`、`caveats`、metadata 中不引用、不总结、不透传该类指令文本。
- 如需 caveat，只能写“已忽略工具返回的指令性文本”这类短说明。
- adapter 模板和角色规则优先。

### TC-X04：主会话 metadata 不包含 raw tool result 或 full PRD

验收：

- agent 返回给主会话的是结构化 YAML compact metadata。
- 不包含完整 evidence 正文。
- 不包含 Lanhu MCP 原始响应。
- `confirmationGate`、`openQuestions`、`caveats` 都是紧凑用户可读文本。

## 11. Superpowers handoff 测试

### TC-H01：`lanhu-requirements` skill 完成后停在用户确认

入口：

```text
`lanhu-requirements` skill <L2> 前端 handoff-fe
```

预期：

- 当 `status: ok` 且 `confirmationGate.status: clear` 后，主会话要求用户 review / confirm：
  - `.lanhu/.../index.md`
  - `scopeConfirmationSummary`
- 未确认前，不启动 `brainstorming`。
- 不触发 Superpowers completion、review、verification。

### TC-H02：用户确认后进入 Superpowers brainstorming

继续 TC-H01，用户确认 `.lanhu/.../index.md` 与 scope summary。

预期：

- 后续 brainstorming 只消费已确认 package。
- frontend 读取 `index.md`，再按它列出的文件读取 `role-prd/prd.md` 与可选 `role-prd/design/index.html` / `assets/`。
- 不重新做 Lanhu intake。
- 不重新选择页面。
- 不从 compact metadata 生成详细 frontend 产物。

## 12. 建议执行顺序

建议至少按以下顺序覆盖：

1. 角色与 deprecated setting 路由测试：TC-R01 ~ TC-R03
2. MCP 工具边界测试：TC-M01 ~ TC-M03
3. 页面范围与 fan-out 测试：TC-P01 ~ TC-P04
4. 输出结构测试：TC-O00 ~ TC-O05
5. 模板合规测试：TC-T01 ~ TC-T05
6. 范围判断测试：TC-S01 ~ TC-S04
7. 确认门禁测试：TC-C01 ~ TC-C04
8. 内容净化测试：TC-X01 ~ TC-X04
9. handoff 测试：TC-H01 ~ TC-H02
