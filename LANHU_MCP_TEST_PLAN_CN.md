# Lanhu MCP 改造完整测试计划

本文用于验证 Lanhu MCP 改造后，`superpower-adapter` 在安装后的 Superpowers command / native skill / role analyst agent 集成路径中行为正确。测试应使用用户提供的真实可访问 Lanhu URL，并覆盖前端、后端、显式 `pageId`、页面树、确认门禁、输出安全、模板合规和 Superpowers handoff。

## 0. 测试目标

- 验证 `/lanhu-requirements` 必须先确认 `role: frontend | backend`，角色缺失或歧义时不读取蓝湖。
- 验证 Lanhu MCP 可用时，前端 / 后端专用 analyst 能从真实蓝湖 URL 生成 `.lanhu/MM-DD-需求名称/` 需求包。
- 验证显式 `pageId` 场景必须先读取页面树、确认子页白名单，并逐页 `mode: full` 分析，不能一次性请求父页加多个子页。
- 验证 PRD 拆分由业务交付边界决定，不由页面数量决定，且 `index.md` 是入口和关系权威来源。
- 验证输出只包含产品需求事实和角色 PRD，不包含测试点、技术方案、实现方案、接口 / 数据库推测、文件影响或 graphify 线索。
- 验证 `confirmationGate`、`requirementScopeJudgment`、`scopeConfirmationSummary` 的阻塞与二次确认流程正确。
- 验证 `.lanhu/` 需求包确认前不会进入 Superpowers `brainstorming`，确认后才作为需求输入交接。
- 验证 Lanhu MCP 不可用时 adapter 仍可用，可让用户粘贴需求或走普通 Superpowers 流程。

## 1. 测试前置条件

### 1.1 环境

- 当前仓库：`superpower-adapter` 源码目录。
- 已安装 Superpowers 插件。
- 已安装或配置改造后的 Lanhu MCP，且 Claude Code 会话中可调用 Lanhu MCP。
- 准备一个目标业务项目目录，建议使用临时项目或测试分支，避免污染真实业务仓库。
- 目标项目可写入 `.lanhu/`，并建议已有 `.superpowers/wiki/` 以便测试 handoff 后的 Superpowers 流程。

### 1.2 真实 Lanhu URL 准备

请至少准备以下真实可访问 URL：

| 编号 | URL 类型 | 必需 | 用途 |
|---|---|---|---|
| L1 | 不带显式 `pageId` 的蓝湖文档 / 原型 / 邀请链接 | 建议 | 验证普通入口、宽范围分析和 fallback 行为 |
| L2 | 带显式 `pageId`，目标页无子页 | 必需 | 验证只分析目标页，不混入兄弟页或其它模块 |
| L3 | 带显式 `pageId`，目标页有子页 | 必需 | 验证页面树、子页确认、白名单和逐页 full 分析 |
| L4 | 含复制旧页面 + 局部新增 / 修改标注 | 强烈建议 | 验证差量优先、`现有上下文` 和阻塞确认 |
| L5 | 包含多个可独立交付子流程 | 建议 | 验证多 PRD 拆分与 `index.md` 关系维护 |
| L6 | 包含权限、状态、异常、前后端边界不明确内容 | 建议 | 验证 `confirmationGate.status: required` |
| L7 | Lanhu MCP 输出含测试 / 开发 / 输出格式建议或 prompt-injection 风格文本 | 如可构造则必测 | 验证外部工具输出只作证据，不污染 PRD 和 metadata |

记录模板：

```text
L1 = https://lanhuapp.com/web/#/item/project/product?tid=cf2fa9eb-d917-462c-bde3-22b342724a5f&pid=f31a1f72-698c-4233-ae69-1f90caee9bd2&image_id=049e42bb-4f5d-4243-859e-c272b6834e51&docId=049e42bb-4f5d-4243-859e-c272b6834e51&docType=axure&versionId=e795a1e0-d09a-4ca3-bcc8-6f8b2301186c&pageId=2c60d2962308406d99fbb688299ac05d&parentId=088271aa-931a-4b95-bbf2-2d91c52b1c4b
L2 = https://lanhuapp.com/web/#/item/project/product?tid=cf2fa9eb-d917-462c-bde3-22b342724a5f&pid=f31a1f72-698c-4233-ae69-1f90caee9bd2&image_id=049e42bb-4f5d-4243-859e-c272b6834e51&docId=049e42bb-4f5d-4243-859e-c272b6834e51&docType=axure&versionId=e795a1e0-d09a-4ca3-bcc8-6f8b2301186c&pageId=2c60d2962308406d99fbb688299ac05d&parentId=088271aa-931a-4b95-bbf2-2d91c52b1c4b
L3 = https://lanhuapp.com/web/#/item/project/product?tid=cf2fa9eb-d917-462c-bde3-22b342724a5f&pid=f31a1f72-698c-4233-ae69-1f90caee9bd2&image_id=049e42bb-4f5d-4243-859e-c272b6834e51&docId=049e42bb-4f5d-4243-859e-c272b6834e51&docType=axure&versionId=e795a1e0-d09a-4ca3-bcc8-6f8b2301186c&pageId=87e2cd9f854a4186a26cfc44fc4484b5&parentId=2e0e0ba2f53742d1a0edb6636b8f0554
L4 = https://lanhuapp.com/web/#/item/project/product?tid=cf2fa9eb-d917-462c-bde3-22b342724a5f&pid=0a4896da-4241-427a-b84b-0c63bf496640&image_id=fe776a81-01e9-412d-bd01-41b0289c509b&docId=fe776a81-01e9-412d-bd01-41b0289c509b&docType=axure&versionId=5dd46908-4cd7-4ba9-bdf1-6a0d5d818da0&pageId=a8d6d2b0e447481681708f01d1d9bb6a&parentId=6dc7f29e-688e-4284-9b40-b89b6a0ce1fa
L5 = <待填>
L6 = <待填>
L7 = <待填>
目标项目 = <待填>
Superpowers 安装目录 = <待填，如自动发现则可不填>
```

## 2. 安装与静态回归测试

### 2.1 生成 / 同步 role analyst

```bash
python3 lib/sync_role_prd.py check
```

预期：

- 前端 / 后端 Lanhu analyst 与 `role-prd/` 模板同步。
- 无 out-of-sync 提示。

如 check 失败，先运行：

```bash
python3 lib/sync_role_prd.py sync
```

然后重新检查 diff，确认生成结果符合预期。

### 2.2 安装 adapter 并验证 overlay

```bash
./manage.sh install
./manage.sh verify
./manage.sh status
```

预期：

- `commands/lanhu-requirements.md` 已安装。
- `agents/lanhu-frontend-requirements-analyst.md` 已安装。
- `agents/lanhu-backend-requirements-analyst.md` 已安装。
- native `brainstorming` / `using-superpowers` patch 中包含 Lanhu confirmation gate 与 handoff 边界。
- 当前流程不安装 adapter SessionStart hook。

### 2.3 Lanhu 静态 guardrail smoke

```bash
bash tests/lanhu-confirmation-gate-smoke.sh <installed-superpowers-target>
bash tests/lanhu-tree-prd-guardrails-smoke.sh <installed-superpowers-target>
```

预期：

- 两个 smoke 均通过。
- 安装后的 command / agents / native skills 包含 `confirmationGate`、`scopeConfirmationSummary`、`requirementScopeJudgment`、page-by-page full analysis、模板合规、禁止 raw Lanhu output 等关键规则。

### 2.4 全量 adapter 回归

```bash
./manage.sh release-check <目标项目路径>
```

预期：

- release-check 通过。
- 如失败，区分是 Lanhu 改造引入的问题，还是目标项目 wiki / 环境配置问题。

## 3. Claude Code 集成路径测试总则

以下测试必须在目标项目目录中，从 Claude Code 的 Superpowers command / skill 入口执行，不以直接运行 Python 脚本作为最终验收。

每个用例都记录：

```text
用例编号：
使用 URL：
入口：/lanhu-requirements ... 或 brainstorming 中贴 Lanhu URL
角色：frontend / backend / 缺失 / 歧义
是否显式 pageId：是 / 否
是否有子页：是 / 否
预期 status：ok / need_confirmation / partial / unavailable / need_role
生成目录：.lanhu/<...>/
最终结果：通过 / 失败
失败说明：
```

通用验收点：

- 主会话不能接收、粘贴或总结 raw Lanhu MCP tool result。
- 主会话不能接收完整 PRD markdown，只能接收 compact metadata。
- `.lanhu/` 之外不应有 Lanhu command 写入产物。
- 不应写 `.superpowers/wiki/`。
- 不应写 Superpowers spec、plan、plan sidecar 或 `Referenced Project Wiki`。
- 不应调用 graphify。
- 不应启动 implementation、verification、completion、review 等 Superpowers 收尾技能。
- `index.md` 必须存在，且作为入口和 PRD 关系权威来源。
- 用户确认 `index.md` 和 `scopeConfirmationSummary` 前，不得进入 Superpowers `brainstorming`。

## 4. 角色选择与入口行为测试

### TC-R01：缺失角色时不读取 Lanhu

入口：

```text
/lanhu-requirements <L2>
```

预期：

- 先询问：生成前端还是后端角色 PRD。
- 在用户回答前，不调用 Lanhu analyst，不调用 Lanhu MCP。
- 不创建 `.lanhu/` 需求包。

### TC-R02：歧义角色 / 全栈时要求选择一个

入口：

```text
/lanhu-requirements <L2> 前后端都要
/lanhu-requirements <L2> fullstack
```

预期：

- 询问本次先生成哪一种角色 PRD。
- 建议前端和后端分别运行两次。
- 在角色明确前，不读取蓝湖。

### TC-R03：前端角色路由正确

入口：

```text
/lanhu-requirements <L2> 前端 测试前端需求
```

预期：

- 路由到 `lanhu-frontend-requirements-analyst`。
- analyst 返回 `role: frontend`。
- `templateCompliance.selectedTemplate: frontend`。
- 生成 PRD 标题为 `# 前端开发角色视角 PRD`。

### TC-R04：后端角色路由正确

入口：

```text
/lanhu-requirements <L2> 后端 测试后端需求
```

预期：

- 路由到 `lanhu-backend-requirements-analyst`。
- analyst 返回 `role: backend`。
- `templateCompliance.selectedTemplate: backend`。
- 生成 PRD 标题为 `# 后端开发角色视角 PRD`。

### TC-R05：英文 role 参数兼容

入口：

```text
/lanhu-requirements --role frontend <L2> fe-role-test
/lanhu-requirements --role backend <L2> be-role-test
```

预期：

- `frontend`、`backend` 参数被正确识别。
- 产物和 TC-R03 / TC-R04 一致。

## 5. Lanhu MCP 可用性与失败路径

### TC-M01：Lanhu MCP 不可用不阻塞 adapter

准备：临时禁用 Lanhu MCP，或在无 Lanhu MCP 的会话中执行。

入口：

```text
/lanhu-requirements <L2> 前端
```

预期：

- 返回 `status: unavailable` 或说明 Lanhu MCP 不可用。
- 提示用户可粘贴需求，或继续普通 Superpowers 流程。
- 不要求安装 Lanhu MCP 才能使用 adapter 其它能力。
- 不写 `.superpowers/wiki/`。

### TC-M02：Lanhu MCP 部分失败返回 partial

准备：使用权限不足、失效、页面不可访问或部分页面读取失败的 URL。

入口：

```text
/lanhu-requirements <失效或部分不可访问 URL> 前端
```

预期：

- 不扩大范围去猜测其它页面。
- 返回 `status: partial` 或清晰 caveat。
- 若模板无法满足，不应写不完整 PRD 包；若已写，必须在 metadata 和 `index.md` 标明 caveat。

## 6. 显式 pageId 与页面树白名单测试

### TC-P01：显式 pageId，无子页，只分析目标页

入口：

```text
/lanhu-requirements <L2> 前端 pageid-no-child-fe
```

预期：

- analyst 先调用页面树读取能力，定位 `explicitPageId`。
- `source.allowedPages` 只包含目标页。
- `source.pagesRead` 只包含目标页。
- 每个 `pagesRead[].analysisMode` 为 `full`。
- `pageNamesArgument` 只含一个页面名。
- 不包含兄弟页、父流程页、相邻模块、旧页面、垃圾站或 Lanhu AI 认为相关的页面。

### TC-P02：显式 pageId，有子页，先询问是否纳入子页

入口：

```text
/lanhu-requirements <L3> 前端 pageid-with-children-fe
```

预期：

- 先调用页面树读取能力。
- 发现目标页有子页后，询问是否纳入子页，并推荐纳入。
- 用户确认前，不生成最终 `.lanhu/` PRD 包。
- 不直接请求父页 + 所有子页的 full 分析。

### TC-P03：用户选择包含子页后逐页 full 分析

继续 TC-P02，用户回答：

```text
包含子页
```

预期：

- `allowedPages` 为目标页 + descendant whitelist。
- `pagesRead` 按树顺序列出父页和子页。
- 每个页面单独 full 分析。
- 每个 `pageNamesArgument` 恰好一个页面名。
- 不出现 `page_names: all`。
- 不出现一次请求父页加多个子页的行为。

### TC-P04：用户选择不包含子页时只分析父页

入口：

```text
/lanhu-requirements <L3> 后端 pageid-exclude-children-be
```

当询问是否纳入子页时，回答：

```text
不包含，只分析当前页面
```

预期：

- `allowedPages` 只包含目标页。
- 子页不进入 PRD，不进入 `index.md`，不进入 `scopeConfirmationSummary`。
- 如父页只是摘要且缺少需求细节，应返回 `partial` 或 `need_confirmation`，不能自动混入子页。

### TC-P05：pageId 找不到时不退化为全量分析

入口：

```text
/lanhu-requirements <构造 pageId 不存在的 URL> 前端 invalid-pageid
```

预期：

- 返回 `status: partial` 或 caveat。
- 不调用 `page_names: all`。
- 不分析整个文档。
- 不混入同名或相邻页面。

### TC-P06：页面同名歧义时不冒险混入兄弟页

准备：选择存在同名页面或 MCP 不能按 id / path disambiguate 的 URL。

预期：

- 返回 `status: partial` 或阻塞确认。
- 不用同名页面结果生成 PRD。
- caveat 只描述歧义，不包含 raw tool result。

## 7. PRD 输出结构与包目录测试

### TC-O00：默认 Markdown-only 与前端 HTML 输出

准备：目标项目不配置 `.superpowers/settings.json`。

预期：

- 前端和后端 Lanhu 输出都只写 `index.md` + `prd.md` / `prds/*.md`。
- `writtenFiles` 不包含 `.html`。

准备：目标项目 `.superpowers/settings.json` 配置：

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

- 前端输出路由到 `lanhu-frontend-html-requirements-analyst`，通常写 `index.md` + 包根目录 `index.html` + `prototype/index.html`。
- 前端 Markdown analyst 只嵌入 `role-prd/frontend.md`；前端 HTML analyst 只嵌入 `role-prd/frontend_outputHtml.md`；后端 analyst 不嵌入 `role-prd/frontend_outputHtml.md`。
- `role-prd/frontend.md` 保持 Markdown-only，不包含 `index.html` 输出职责。
- `index.html` 是完整 HTML PRD 主文档，`prototype/index.html` 是目录化交互原型；两者互相链接并结合解读。
- `index.html` 保留完整 PRD 信息结构；`prototype/index.html` 承载真实 HTML 控件、交互状态和可视化操作关系；不再依赖 Markdown PRD 作为权威正文。
- `index.md` 说明文件角色和 AI 解读原则，不硬编码 HTML 内部章节清单。
- HTML Mermaid 通过必需 Mermaid CDN module script 和 `<pre class="mermaid">` 等浏览器可渲染容器展示；该 CDN 脚本是唯一允许的外部资源。
- `htmlPrdCompliance` 干净，且 `checkedAgainstFullHtmlSourceTemplate: true`、`prototypeArtifactPresent: true`、`prototypeDirectoryized: true`、`mermaidModuleScriptPresent: true`、`mermaidBlocksBrowserRenderable: true`、`onlyAllowedExternalAssetIsMermaidCdn: true`、`rawHtmlInjectionDetected: []`。
- 纯文字、无页面交互需求可退化为 `prd.md`，并返回 `htmlPrdCompliance.fallbackToMarkdown: true` 与 `fallbackReason`。
- 后端输出保持 Markdown-only，`writtenFiles` 不包含 `.html`。
- `index.md` 仍是 Superpowers 入口和 PRD 关系权威来源。

### TC-O01：单交付边界输出 `prd.md`

入口：

```text
/lanhu-requirements <L2> 前端 single-prd-fe
```

预期文件：

```text
.lanhu/<MM-DD-single-prd-fe>/
  index.md
  prd.md
```

验收：

- `index.md` 包含 `PRD 角色：frontend`。
- `index.md` 指向 `prd.md`。
- `index.md` 说明阅读顺序和范围判断摘要。
- 无 `prds/` 或 `prds/` 为空。

### TC-O02：多交付边界输出 `prds/`

入口：

```text
/lanhu-requirements <L5> 前端 multi-prd-fe
```

预期文件：

```text
.lanhu/<MM-DD-multi-prd-fe>/
  index.md
  prds/
    <交付边界1>.md
    <交付边界2>.md
```

验收：

- PRD 数量由独立交付 / 独立负责 / 独立验收边界决定。
- 页面数量多但同一用户目标和验收边界时，不应机械拆分。
- 列表页、详情弹窗、抽屉、跳转流程如果服务同一目标，应保留在同一个 PRD。
- `index.md` 维护跨 PRD 关系、阅读顺序和必要 flowchart。
- 每个 `prds/*.md` 都是完整角色 PRD，不用 `index.md` 替代正文。

### TC-O03：tree mode 第一层 PRD 仍可继续按业务边界拆分

入口：

```text
/lanhu-requirements <L3 或 L5> 后端 tree-split-be
```

预期：

- 如果某个 tree-mode PRD 内仍包含独立可交付子流程，应继续拆分。
- `index.md` 维护拆分后的关系。
- 不因“一个页面一个 PRD”或“一个子页一个 PRD”机械拆分。

### TC-O04：目录命名安全与不覆盖

连续两次使用同名 hint：

```text
/lanhu-requirements <L2> 前端 duplicate-name
/lanhu-requirements <L2> 前端 duplicate-name
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

## 8. 模板合规测试

### TC-T01：前端模板完整性

使用前端 PRD 产物检查：

必须包含：

- `# 前端开发角色视角 PRD`
- `## 一、需求概览`
- `## 二、本次变更范围判定`
- `### 2.1 需求思维导图`
- `## 三、页面与入口范围`
- `## 四、页面展示规则`
- `### 4.1 页面布局结构草图`
- `### 4.2 展示规则说明`
- `## 五、字段 UI 控件说明`
- `## 六、用户操作与交互规则`
- `### 6.1 用户操作流程`
- `### 6.2 交互规则`
- `## 七、页面状态流转`
- `## 八、权限与可见性`
- `## 九、前后端协作信息`
- `## 十、异常与边界场景`
- `## 十一、前端验收标准`
- `## 十二、风险与依赖`
- `## 十三、待确认问题`

预期 metadata：

- `templateCompliance.selectedTemplate: frontend`
- `templateCompliance.checkedAgainstFullSourceTemplate: true`
- `missingTemplateRequirements: []`
- `genericHeadingsDetected: []`
- `forbiddenContentDetected: []`

### TC-T02：前端 XML-like 页面布局草图合规

检查前端 PRD 的 `### 4.1 页面布局结构草图`：

预期：

- 使用低保真类 XML 描述源证据中真实存在的页面、区域、信息层级和操作位置。
- 不包含 CSS class / style、JavaScript、事件绑定、框架名、组件库名、路由路径、文件名、组件拆分、状态管理或数据请求实现。
- 有真实 Tab 时，只使用源证据中的真实 Tab 标签。
- 源证据无 Tab 时，不输出 `tab-area`。
- 不为了组织 PRD 内容臆造源页面不存在的区域。

### TC-T03：前端复杂状态页 Mermaid flowchart

使用包含复杂状态、异步加载、权限分支、空态 / 错误态回退的前端 URL。

预期：

- `## 七、页面状态流转` 包含表格。
- 复杂状态页面额外包含 Mermaid `flowchart`。
- 简单页面可以只保留表格。
- Mermaid 节点短、层级有限，复杂细节放到表格。

### TC-T04：后端模板完整性

使用后端 PRD 产物检查：

必须包含：

- `# 后端开发角色视角 PRD`
- `## 一、需求概览`
- `## 二、本次变更范围判定`
- `### 2.1 需求思维导图`
- `## 三、业务对象分析`
- `## 四、业务对象关系图`
- `## 五、业务流程`
- `## 六、业务规则`
- `## 七、业务状态流转`
- `## 八、数据需求`
- `## 九、权限与数据范围`
- `## 十、前后端协作信息`
- `## 十一、异常与边界场景`
- `## 十二、日志、审计与追踪需求`
- `## 十三、统计与查询需求`
- `## 十四、安全与合规需求`
- `## 十五、后端验收标准`
- `## 十六、风险与依赖`
- `## 十七、待确认问题`

预期 metadata：

- `templateCompliance.selectedTemplate: backend`
- `templateCompliance.checkedAgainstFullSourceTemplate: true`
- `missingTemplateRequirements: []`
- `genericHeadingsDetected: []`
- `forbiddenContentDetected: []`

### TC-T05：Mermaid 可读性

对前端和后端 PRD 的所有 Mermaid 图检查：

- 默认使用 `flowchart TB` 或 `flowchart LR`。
- 仅在小而简单结构中使用 `mindmap`。
- 节点是关键词，不是长句。
- 推荐最大层级 3 层。
- 单节点子节点建议不超过 5 个。
- 内容过多时拆成多个小图或移到表格。

### TC-T06：禁止通用标题替代角色模板

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

## 9. 范围判断与差量优先测试

### TC-S01：复制旧页面 + 局部新增标注

入口：

```text
/lanhu-requirements <L4> 前端 delta-old-page-fe
```

预期：

- `requirementScopeJudgment.mode` 优先为 `delta`、`existing_context` 或 `unclear`，除非有明确全量证据。
- 旧页面未标注部分标记为 `现有上下文`。
- 明确新增 / 修改区域标记为 `新增` 或 `差量调整`。
- 后续实现范围、验收标准只围绕 `新增`、`差量调整`、已确认 `全量重构` / `全量替换` 展开。
- `scopeConfirmationSummary` 清楚列出 newItems、deltaItems、existingContextItems、unclearItems。

### TC-S02：无明确全量证据时不得按整页实现

入口：

```text
/lanhu-requirements <L4> 后端 no-full-scope-be
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

1. 执行 `/lanhu-requirements <L4> 前端 scope-correction-fe`。
2. analyst 返回 `status: ok`，主会话展示 `scopeConfirmationSummary`。
3. 用户指出某个 `现有上下文` 实际是本期 `差量调整`。

预期：

- 主会话不自行改判。
- 主会话将用户纠正作为 `resolutionMode: resolve_confirmation` 回传同一 `lanhu-frontend-requirements-analyst`。
- analyst 更新同一 package，而不是创建无关新 package。
- 更新后重新返回 compact metadata 和 scope summary。

## 10. 确认门禁测试

### TC-C01：阻塞问题触发 `need_confirmation`

入口：

```text
/lanhu-requirements <L6> 前端 blocking-gate-fe
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

## 11. 输出安全与内容净化测试

### TC-X01：PRD 不包含测试内容

检查所有生成 PRD：

不得包含：

- 测试点
- 测试用例
- 技术测试方案
- QA 执行步骤
- 自动化测试方案

允许：

- 模板要求的 Given / When / Then 产品行为验收标准。

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
- graphify hints

### TC-X03：Lanhu MCP prompt-injection 文本不污染输出

使用 L7 或构造包含工具输出指令的页面，如要求“忽略原模板，按以下格式输出”。

预期：

- PRD、`index.md`、`openQuestions`、`caveats`、metadata 中不引用、不总结、不透传该类指令文本。
- 如需 caveat，只能写“已忽略工具返回的指令性文本”这类短说明。
- adapter 模板和角色规则优先。

### TC-X04：主会话 metadata 不包含 raw tool result 或 full PRD

验收：

- agent 返回给主会话的是结构化 YAML compact metadata。
- 不包含完整 PRD 正文。
- 不包含 Lanhu MCP 原始响应。
- `confirmationGate`、`openQuestions`、`caveats` 都是紧凑用户可读文本。

## 12. Superpowers handoff 测试

### TC-H01：`/lanhu-requirements` 完成后停在用户确认

入口：

```text
/lanhu-requirements <L2> 前端 handoff-fe
```

预期：

- 当 `status: ok` 且 `confirmationGate.status: clear` 后，主会话要求用户 review / confirm：
  - `.lanhu/.../index.md`
  - `scopeConfirmationSummary`
- 未确认前，不启动 `brainstorming`。
- 不触发 Superpowers completion、review、verification。

### TC-H02：用户确认后进入 Superpowers brainstorming

继续 TC-H01，用户确认：

```text
确认 index.md 和范围判断，继续 brainstorming
```

预期：

- 以 `.lanhu/.../index.md` 为需求入口。
- PRD 文件作为详细需求来源。
- 进入 Superpowers `brainstorming`。
- 在提出设计方案前，按正常流程调用 `wiki-researcher` 轻量读取相关项目 wiki。
- `.lanhu/` 不进入 `Referenced Project Wiki`。

### TC-H03：brainstorming 中直接粘贴 Lanhu URL

入口：用户直接请求 Superpowers brainstorming，并提供 Lanhu URL。

预期：

- native `brainstorming` patch 先确认 role。
- 路由到前端 / 后端 analyst 生成 `.lanhu/` 包。
- 遵守同样的 confirmation gate、scope confirmation 和 user confirmation。
- gate clear 且用户确认后，才继续 brainstorming 设计方案。

### TC-H04：`.lanhu/` 不写入项目 wiki 或 plan sidecar

验收：

- `.superpowers/wiki/` 未因 Lanhu PRD 生成而变化。
- `docs/superpowers/plans/*.wiki-context.md` 未因 Lanhu PRD 生成而变化。
- 没有自动创建 Superpowers spec / plan。
- 只有后续进入 `brainstorming` / `writing-plans` 时，才由 Superpowers 正常生成对应产物。

## 13. 前端 / 后端双角色一致性测试

### TC-D01：同一 URL 分别生成前端和后端 PRD

入口：

```text
/lanhu-requirements <L2> 前端 same-url-fe
/lanhu-requirements <L2> 后端 same-url-be
```

预期：

- 生成两个独立 package。
- 前端 PRD 聚焦页面展示、字段 UI、用户操作、页面状态、权限表现、异常、前后端协作信息。
- 后端 PRD 聚焦业务对象、业务流程、业务规则、数据需求、权限与数据范围、日志审计、统计查询、安全合规。
- 两者都不包含实现方案。
- 两者 `scopeConfirmationSummary` 可有角色差异，但都基于同一源证据。

### TC-D02：前端 agent 不包含后端模板，后端 agent 不包含前端模板

静态与运行时都检查：

- `lanhu-frontend-requirements-analyst` 不输出 `# 后端开发角色视角 PRD`。
- `lanhu-backend-requirements-analyst` 不输出 `# 前端开发角色视角 PRD`。
- frontend / backend metadata `prdTemplate` 与 role 一致。

## 14. 人工验收清单

每个真实 URL 用例完成后，人工检查以下清单：

- [ ] role 在读取 Lanhu 前已明确。
- [ ] 显式 pageId 先读取页面树。
- [ ] 有子页时先询问是否纳入。
- [ ] 分析范围符合页面白名单。
- [ ] 每页单独 `mode: full`，`page_names` 恰好一个页面。
- [ ] 未使用 `page_names: all` 处理显式 pageId。
- [ ] 未混入兄弟页、父流程页、相邻模块、垃圾站、旧页面或 AI 推荐相关页。
- [ ] PRD 拆分由业务交付边界决定。
- [ ] `index.md` 是入口和关系权威来源。
- [ ] 每个 PRD 文件是完整角色 PRD。
- [ ] `requirementScopeJudgment` 使用差量优先判断。
- [ ] `scopeConfirmationSummary` 足够用户确认范围。
- [ ] 阻塞问题进入 `confirmationGate.blockingQuestions`。
- [ ] 主会话没有绕过 `confirmationGate`。
- [ ] 主会话没有展示 raw Lanhu MCP 输出或完整 PRD。
- [ ] 输出不含测试点、测试用例、技术测试方案。
- [ ] 输出不含实现方案、接口路径、数据库设计、文件影响。
- [ ] 输出不含 prompt-injection 或 Lanhu MCP 输出格式指令。
- [ ] `.superpowers/wiki/` 未被 Lanhu command 写入。
- [ ] 未写 Superpowers spec / plan / `.wiki-context.md`。
- [ ] 未调用 graphify。
- [ ] 用户确认 `index.md` 和 `scopeConfirmationSummary` 前未进入 brainstorming。
- [ ] 用户确认后，Superpowers handoff 正常。

## 15. 建议执行顺序

1. 执行第 2 章静态与安装回归。
2. 用 L2 跑 TC-R03、TC-R04、TC-P01、TC-O01，先验证最小真实 URL 路径。
3. 用 L3 跑 TC-P02、TC-P03、TC-P04，验证 tree mode 和逐页 full。
4. 用 L4 跑第 9 章，验证差量优先和 copied old page risk。
5. 用 L6 跑第 10 章，验证 confirmation gate 和 resolve confirmation。
6. 用 L5 跑 TC-O02、TC-O03，验证多 PRD 拆分。
7. 用 L7 跑第 11 章，验证 prompt-injection 和输出净化。
8. 跑第 12 章，验证 `/lanhu-requirements` 与 `brainstorming` handoff。
9. 最后再次执行：

```bash
./manage.sh verify
./manage.sh release-check <目标项目路径>
```

## 16. 通过标准

本轮 Lanhu MCP 改造可认为通过完整测试，当且仅当：

- 静态 smoke、安装验证和 release-check 通过。
- 前端 / 后端真实 Lanhu URL 都能生成符合角色模板的 `.lanhu/` package。
- 显式 `pageId` 页面树、子页确认、白名单和逐页 full 分析全部符合预期。
- `confirmationGate` 和 `scopeConfirmationSummary` 的阻塞 / 清空 / 用户确认流程无绕过。
- 输出内容安全，未包含 raw MCP 输出、prompt-injection 文本、测试内容或实现方案。
- `.lanhu/` 需求包确认前不进入 Superpowers brainstorming；确认后 handoff 正常。
- Lanhu MCP 不可用或部分失败时不破坏 adapter 其它 Superpowers 主流程。
