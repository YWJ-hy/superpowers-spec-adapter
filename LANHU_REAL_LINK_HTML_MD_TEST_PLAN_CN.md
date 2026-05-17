# Lanhu 真实链接 HTML + Markdown 输出测试计划

## 1. 测试目标

使用真实蓝湖链接验证 `/lanhu-requirements` 在默认 Markdown-only 和前端 `html` 配置下的端到端输出质量，重点确认：

- `.lanhu/MM-DD-需求名称/` PRD 包是否完整、清晰、可交给 Superpowers 后续 brainstorming 使用。
- `index.md` 是否是稳定入口，并能清楚说明 PRD 文件关系、阅读顺序、范围判断和确认门禁状态。
- `prd.md` 或 `prds/*.md` 是否满足前端 / 后端角色 PRD 模板，内容是否完整、结构清晰、范围判定明确。
- 前端开启 `html` 后，`index.html` 是否作为完整 HTML PRD 主文档存在，`prototype/index.html` 是否作为目录化交互原型存在；HTML 是否使用左侧章节导航 + 右侧激活章节内容布局，并把第四部分页面展示规则转换为真实 HTML 控件和可核对交互结构。
- 后端角色是否始终 Markdown-only，不输出 HTML。
- Lanhu MCP 输出中的格式指令、AI 分析标题、测试/实现内容是否被正确剥离。

## 2. 测试前准备

### 2.1 安装并校验 adapter

在 adapter 源码 worktree 中执行：

```bash
./manage.sh install
./manage.sh verify
```

### 2.2 准备目标项目

选择一个真实业务项目作为 Lanhu 输出目标项目，记为：

```text
<TARGET_PROJECT_ROOT>
```

确保目标项目中已有或可创建：

```text
<TARGET_PROJECT_ROOT>/.lanhu/
<TARGET_PROJECT_ROOT>/.superpowers/settings.json
```

### 2.3 准备真实蓝湖链接

请准备至少 3 类真实蓝湖链接：

| 链接编号 | 链接类型 | 用途 | 示例占位 |
|---|---|---|---|
| L1 | 单页面 / 单交付边界 | 验证单 PRD 输出完整性 | `<LANHU_SINGLE_PAGE_URL>` |
| L2 | 带 `pageId` 且有子页面 | 验证 page tree / child page gating | `<LANHU_PAGE_TREE_URL>` |
| L3 | 多交付边界需求 | 验证 `prds/*.md` 拆分和 `index.md` 关系说明 | `<LANHU_MULTI_DELIVERY_URL>` |

如只有一个真实链接，也可以先覆盖 L1，再按实际情况补 L2 / L3。

## 3. 配置矩阵

### 3.1 默认 Markdown-only

目标项目不配置 Lanhu 输出格式，或 `.superpowers/settings.json` 中不包含 `lanhu.frontend.output.format`。

预期：

- 前端输出只包含 Markdown 包。
- 后端输出只包含 Markdown 包。
- `writtenFiles` 不包含 `.html`。

### 3.2 前端 HTML opt-in

在目标项目 `.superpowers/settings.json` 中配置：

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

- 前端输出包含 `index.md` + `index.html` + `prototype/index.html`；纯文字/无交互需求 fallback 时可改为 `index.md` + `prd.md`。
- 后端输出仍只包含 Markdown，不包含 `.html`。

## 4. 执行方式

在 Claude Code 中进入目标项目后执行：

```text
/lanhu-requirements <LANHU_URL> 前端 <测试需求名>
/lanhu-requirements <LANHU_URL> 后端 <测试需求名>
```

如果是 Superpowers brainstorming 中自动触发 Lanhu intake，也按同样标准验收，但本计划优先使用显式 `/lanhu-requirements`，便于观察输出路径和确认门禁。

## 5. 核心测试用例

### TC-01：默认前端 Markdown-only 单 PRD 输出

输入：

```text
/lanhu-requirements <LANHU_SINGLE_PAGE_URL> 前端 single-fe-md
```

配置：不设置 `lanhu.frontend.output.format`。

预期文件：

```text
.lanhu/MM-DD-single-fe-md/
  index.md
  prd.md
```

不得出现：

```text
.lanhu/MM-DD-single-fe-md/index.html
```

验收重点：

- `index.md` 存在，且包含：
  - PRD 角色：frontend
  - PRD 文件列表
  - 阅读顺序
  - 范围判断摘要
  - 如有多个文件关系，包含 Mermaid flowchart
- `prd.md` 存在，且包含完整前端 PRD 结构：
  - `## 一、需求概览`
  - `## 二、本次变更范围判定`
  - `### 2.1 需求思维导图`
  - `## 三、页面与入口范围`
  - `## 四、页面展示规则`
  - `### 4.1 页面布局结构草图`
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
- `prd.md` 中范围判定清楚区分：
  - `新增`
  - `差量调整`
  - `现有上下文`
  - `待确认`
  - `全量重构`
  - `全量替换`
- `现有上下文` 没有被写成实现任务或验收范围。

### TC-02：前端 `html` 单 PRD 输出

输入：

```text
/lanhu-requirements <LANHU_SINGLE_PAGE_URL> 前端 single-fe-html
```

配置：启用 `lanhu.frontend.output.format: html`。

预期文件：

```text
.lanhu/MM-DD-single-fe-html/
  index.md
  index.html
  prototype/
    index.html
```

验收重点：

- `index.md` 存在，且作为包入口、阅读顺序和范围判断摘要来源；它只说明文件角色和 AI 解读原则，不硬编码 HTML 内部章节清单。
- `index.html` 存在，且是完整前端 HTML PRD 主文档。
- `prototype/index.html` 存在，且是目录化交互原型，用于承载真实 HTML 控件、交互状态和可视化操作关系。
- `index.html` 和 `prototype/index.html` 可直接用浏览器打开。
- `index.html` 使用左侧章节导航 + 右侧正文内容布局，不是顶部导航 + 单列内容。
- `prototype/index.html` 应包含：
  - 真实 HTML 控件和交互结构，而不是 XML-like 文本草图
  - 与 Lanhu 需求 1:1 对应的关键按钮、输入框、链接、弹窗、抽屉或状态演示
  - `新增` / `差量调整` / `现有上下文` / `待确认` 标记
  - 控件可追溯到源需求对象，不虚构产品控件或业务区域
- HTML Mermaid 应通过 Mermaid CDN module script 和 `<pre class="mermaid">` 等浏览器可渲染容器展示；该 CDN 脚本是唯一允许的外部资源。
- HTML 不应包含：
  - XML-like 页面布局结构草图作为最终展示结构
  - 除 Mermaid CDN module script 之外的外部 CDN / 远程资源 / 真实接口请求 / 框架代码 / 生产架构说明
  - 真实表单提交、业务校验实现、持久化、埋点或生产交互脚本

### TC-03：后端在 `html` 配置下仍 Markdown-only

输入：

```text
/lanhu-requirements <LANHU_SINGLE_PAGE_URL> 后端 single-be-md
```

配置：启用 `lanhu.frontend.output.format: html`。

预期文件：

```text
.lanhu/MM-DD-single-be-md/
  index.md
  prd.md
```

不得出现：

```text
.lanhu/MM-DD-single-be-md/index.html
```

验收重点：

- `index.md` 包含 PRD 角色：backend。
- `prd.md` 满足后端 PRD 模板结构。
- 不包含前端 HTML 辅助输出内容。
- `writtenFiles` 不包含 `.html`。

### TC-04：带 `pageId` 且有子页面的 tree gating

输入：

```text
/lanhu-requirements <LANHU_PAGE_TREE_URL> 前端 tree-fe-html
```

配置：建议启用 `html`。

预期流程：

- analyst 先调用页面树读取能力。
- 识别 URL 中的 explicit pageId。
- 如目标页面有子页面，先询问是否包含子页面。
- 用户确认后，只分析目标页面及其子页面白名单。
- 不使用 `page_names: all`。
- 不混入兄弟页面、父级流程页、相邻模块、废弃页或 Lanhu AI 推荐相关页。

验收重点：

- `index.md` 清楚说明包含了哪些页面 / 子页面。
- `prd.md` 或 `prds/*.md` 中每个范围判断都有来源依据。
- 如输出 HTML，`index.html` 只展示纳入范围内的页面 / 交互，不展示未纳入的兄弟页内容。

### TC-05：多交付边界输出 `prds/*.md`

输入：

```text
/lanhu-requirements <LANHU_MULTI_DELIVERY_URL> 前端 multi-fe-html
```

配置：建议启用 `html`。

预期文件：

```text
.lanhu/MM-DD-multi-fe-html/
  index.md
  index.html
  prototype/
    index.html
```

验收重点：

- 业务交付边界分析基于可独立交付、负责或验收的子流程，而不是页面数量。
- `index.md` 说明：
  - 输出格式为 frontend HTML
  - `index.html` 是完整 HTML PRD 主文档
  - `prototype/index.html` 是目录化交互原型
  - 多交付边界之间的关系
  - 阅读顺序
  - 必要时有 Mermaid flowchart
- `index.html` 是整个 package 的完整 HTML PRD 主文档，需通过左侧导航组织章节和交付边界关系。
- `prototype/index.html` 应为纳入范围的页面输出真实 HTML 控件和可核对交互结构。

### TC-06：阻塞确认点 gating

输入：选择一个范围不明确、字段含义不明确、权限不明确或状态流转不明确的真实蓝湖链接。

预期：

- analyst 返回 `status: need_confirmation`。
- 主会话只展示 compact blocking questions，不粘贴完整 PRD 正文。
- 用户回答后，主会话把答案回传同一 role analyst。
- analyst 修复同一个 package，而不是重新生成无关目录。
- 只有 `confirmationGate.status: clear` 后，才允许继续 Superpowers brainstorming。

验收重点：

- `confirmationGate.blockingQuestions` 中的问题短小、明确、可回答。
- 每个阻塞问题有：
  - `id`
  - `question`
  - `impact`
  - `blockingReason`
  - `affectedPrdFiles`
  - `suggestedConfirmationTarget`
- `prd.md` 或 `prds/*.md` 的待确认问题表与 `confirmationGate.blockingQuestions` 一致。

## 6. PRD 包完整性与清晰度评分表

每个生成的 PRD 包至少按以下维度评分，建议 1–5 分：

| 维度 | 5 分标准 | 常见问题 |
|---|---|---|
| 入口清晰度 | `index.md` 能让读者快速知道读哪些文件、按什么顺序读、范围是什么 | 只有文件列表，没有关系说明 |
| 范围判定 | 明确区分新增、差量、现有上下文、待确认，并有依据 | 把整张旧页面都当本期实现 |
| 结构完整性 | PRD 章节完整，符合角色模板 | 缺少字段 UI、状态、异常、验收等章节 |
| 内容可执行性 | 前端/后端能据此理解要做什么、不做什么 | 只有可见文案，没有规则和边界 |
| 待确认质量 | 阻塞/非阻塞区分准确，问题可回答 | 所有问题都阻塞，或阻塞问题被遗漏 |
| 去实现化 | 不包含组件拆分、API 猜测、数据库设计、测试计划、代码文件影响 | Lanhu AI 的开发建议被照搬 |
| HTML 结构核对 | `index.html` 是完整 PRD 主文档，`prototype/index.html` 用真实 HTML 控件 1:1 映射需求交互 | 只有静态表格，没有控件核对区，或虚构控件 |
| HTML 可用性 | 可直接打开，左侧章节导航 + 右侧激活章节内容清楚，核心交互可点击，状态切换清楚；Mermaid 可在浏览器渲染 | 顶部导航单列长文档，或依赖 Mermaid CDN 以外的外部资源 |
| 后续交接 | 用户确认后能自然进入 Superpowers brainstorming | 入口不清楚，不知道交给 Superpowers 哪个文件 |

建议通过标准：

- 所有核心维度 ≥ 4 分。
- “范围判定”“结构完整性”“去实现化”“后续交接”必须为 5 分或接近 5 分。
- 如开启 HTML，“HTML 结构核对”和“HTML 可用性”必须 ≥ 4 分。

## 7. 手工检查清单

### 7.1 `index.md`

- [ ] 包含 PRD 角色。
- [ ] 包含需求名称和 package 说明。
- [ ] 包含 PRD 文件列表。
- [ ] 包含阅读顺序。
- [ ] frontend HTML 时说明 `index.html` 与 `prototype/index.html` 的文件角色，并要求 AI/Superpowers 动态解析 HTML 结构。
- [ ] 多 PRD 时包含关系说明。
- [ ] 多 PRD 或关系不明显时包含 Mermaid flowchart。
- [ ] 包含范围判断摘要。
- [ ] 不替代完整 PRD 正文。

### 7.2 `prd.md` / `prds/*.md`

- [ ] 章节完整。
- [ ] 范围判定表完整。
- [ ] 每个范围性质都有依据。
- [ ] `现有上下文` 没进入实现或验收范围。
- [ ] 字段 UI、交互、状态、权限、异常、验收标准清楚。
- [ ] 待确认问题区分阻塞 / 非阻塞。
- [ ] 没有测试用例、测试点、技术测试方案。
- [ ] 没有前端组件拆分、框架选型、状态管理实现。
- [ ] 没有后端 API 路径、接口 schema、数据库设计。
- [ ] 没有实现文件影响分析。

### 7.3 `index.html`

仅适用于 frontend `html`：

- [ ] `index.html` 文件存在于 package 根目录。
- [ ] `prototype/index.html` 文件存在于 `prototype/` 目录。
- [ ] 两个 HTML 文件均可直接浏览器打开。
- [ ] 除 Mermaid CDN module script 外无外部资源依赖。
- [ ] Mermaid 使用 `<pre class="mermaid">` 或等价容器并可在浏览器渲染。
- [ ] 无真实接口请求。
- [ ] 无 Vue / React / 组件库 / 构建工具。
- [ ] `index.html` 使用左侧章节导航 + 右侧激活章节内容布局。
- [ ] `prototype/index.html` 展示页面结构和关键交互。
- [ ] `prototype/index.html` 包含真实 HTML 控件核对区。
- [ ] 控件与 Lanhu 需求 1:1 对应，不虚构。
- [ ] 能切换或演示核心状态。
- [ ] 用 badge 或标记区分范围性质。
- [ ] 无 XML-like 文本草图作为最终展示结构。

## 8. 失败判定

出现以下任一情况，应判定为失败并修复 prompt / guardrail：

- 默认配置下前端输出了 `index.html`。
- 后端任意情况下输出了 `.html`。
- `index.md` 缺失或无法作为入口。
- `prd.md` / `prds/*.md` 缺少关键模板章节。
- 范围判定没有依据，或把明显旧页面误判为本期全量实现。
- HTML 缺少左侧章节导航 + 右侧激活章节内容布局。
- HTML 缺少 `prototype/index.html` 目录化交互原型。
- `prototype/index.html` 没有把页面展示规则转换为真实 HTML 控件和交互结构。
- HTML 控件与 Lanhu 需求不一致，或虚构源证据中不存在的产品控件。
- Mermaid 仍以不可渲染源码块输出，或缺少必需 Mermaid module script。
- HTML 包含真实接口、框架代码、Mermaid CDN 以外的外部资源或生产实现方案。
- Lanhu MCP 的输出格式说明、AI 建议、测试视角或开发方案进入最终 PRD schema。
- `status: need_confirmation` 时主会话粘贴完整 PRD 或绕过 analyst 的 confirmation gate。

## 9. 测试记录模板

| 测试编号 | Lanhu 链接 | 角色 | 配置 | 输出目录 | 结果 | 主要问题 | 是否通过 |
|---|---|---|---|---|---|---|---|
| TC-01 |  | frontend | markdown |  |  |  |  |
| TC-02 |  | frontend | html |  |  |  |  |
| TC-03 |  | backend | html |  |  |  |  |
| TC-04 |  | frontend | html |  |  |  |  |
| TC-05 |  | frontend | html |  |  |  |  |
| TC-06 |  | frontend/backend | 任意 |  |  |  |  |

## 10. 建议最终验收结论格式

```text
Lanhu 真实链接测试结论：通过 / 不通过

测试链接：
- L1: ...
- L2: ...
- L3: ...

通过项：
- ...

发现问题：
- ...

是否阻塞继续进入 Superpowers brainstorming：是 / 否

需要修复的 adapter prompt / guardrail：
- ...
```
