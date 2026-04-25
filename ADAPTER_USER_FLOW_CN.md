# Superpowers + Adapter 用户流程说明

本文面向最终用户，说明 adapter 安装到 Superpowers 后，用户在 Claude Code、Cursor 等工具中应如何使用，以及 Superpowers + adapter 的整体工作流。

如果你是 adapter 开发者，请先读 [`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)。

---

## 1. 一句话理解

`superpower-adapter` 不是替代 Superpowers，也不是要求用户直接运行一组 Python 脚本。

它的定位是：

> 让 Superpowers 继续负责主工作流，adapter 通过安装 command、skill、hook 和脚本，增强 Superpowers 在 `.superpowers/spec/` 规范管理上的能力。

用户在 Claude Code 等工具里使用的是 Superpowers 暴露出来的 command / skill 能力，例如：

- `/init-spec`
- `/update-spec`
- `/check-workflow`
- adapter 安装的 `spec-progressive-disclosure` 与 `plan-context-sidecar` skills

Python 脚本是这些 command / hook 背后的执行层，不是最终用户的主要交互入口。

---

## 2. adapter 插入 Superpowers 后发生了什么

安装 adapter 后，adapter 会把 overlay 写入用户已安装的 Superpowers 插件目录：

```text
Superpowers 插件目录
├── commands/
│   ├── init-spec.md
│   ├── update-spec.md
│   ├── check-workflow.md
│   └── import-spec.md
├── skills/
│   ├── spec-progressive-disclosure/
│   └── plan-context-sidecar/
├── hooks/
│   ├── session-spec-index
│   └── session-plan-context
└── scripts/
    └── adapter 执行脚本
```

同时 adapter 会 patch Superpowers 的 SessionStart hook 配置，让会话启动时自动注入：

- `.superpowers/spec/` 的轻量摘要树
- 当前 plan sidecar 的轻量状态

因此用户进入 Claude Code 会话后，不需要先手动全文读取 spec。工具会先看到摘要，再按任务需要渐进读取具体 spec。

---

## 3. 用户视角的完整推荐执行顺序

本节按“第一次接入项目 → 日常任务 → 任务完成后沉淀知识”的顺序，说明用户在 Claude Code 等工具中使用 Superpowers + adapter 时，推荐如何调用所有 adapter command。

### 3.1 总览顺序

| 顺序 | 阶段 | 入口 | 是否每次都需要 | 目的 |
|---|---|---|---|---|
| 0 | 安装 Superpowers | `/plugin install superpowers@claude-plugins-official` | 只需一次 | 先安装 Superpowers 主插件 |
| 1 | 安装 adapter | `./manage.sh install` | 只需一次；Superpowers 升级后重跑 | 把 adapter overlay 写入 Superpowers 插件目录 |
| 2 | 校验 adapter | `./manage.sh verify` | 安装或升级后 | 确认 command、skill、hook、script 已安装 |
| 3 | 初始化 spec 模板 | `./manage.sh bootstrap-spec /path/to/project --template standard` | 每个目标项目一次 | 创建 `.superpowers/spec/` 规范目录 |
| 4 | 导入已有 spec | `/import-spec` | 有旧 spec 时才需要 | 把已有规范迁移到 adapter 的 `.superpowers/spec/` 格式 |
| 5 | 初始化 starter spec | `/init-spec` | 每个目标项目首次使用时 | 从当前项目结构生成第一版轻量 spec 知识 |
| 6 | 描述需求并进入 Superpowers plan 流程 | Superpowers 创建或选定 plan | 复杂任务或需要计划推进时 | 先由 Superpowers 生成或确定 `docs/superpowers/plans/<stem>.md` |
| 7 | 自动初始化 sidecar 并挑选 spec | `/check-workflow planning` | 已经有 Superpowers plan 时 | 自动创建 plan sidecar，并把推荐 spec context 写入 `plan.jsonl` |
| 8 | 阶段前检查 | `/check-workflow` | 进入 implement / review / completion 前推荐使用 | 检查当前 Superpowers + adapter 工作流是否可继续 |
| 9 | 按需读取 spec | `spec-progressive-disclosure` skill | 任务需要规范上下文时 | 从 index 到 leaf spec 渐进读取，不全文加载 |
| 10 | 任务后更新 spec | `/update-spec` | 任务产生长期可复用知识时 | 将 durable implementation knowledge 回写 `.superpowers/spec/` |
| 11 | 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者发布前 | 运行 verify、doctor、self-test、export-manifest |

用户日常在 Claude Code 中主要记住这条链：

```text
描述需求
→ Superpowers 判断是否需要 plan，并创建或选定 plan
→ /check-workflow planning（已有 plan 时自动准备 sidecar 和 plan.jsonl）
→ /check-workflow（后续阶段前）
→ 正常使用 Superpowers 执行任务，并按需读取 spec
→ /check-workflow（收尾前）
→ /update-spec（有长期知识时）
```

项目首次接入时，在描述具体开发需求前，可先执行：

```text
/import-spec（有旧 spec 时）
→ /init-spec（首次生成 starter spec）
```

关键点：用户不需要手动执行 `/plan-context`。Superpowers 已经创建或选定 plan 之后，使用 `/check-workflow planning` 自动初始化 sidecar、挑选相关 spec，并写入 `plan.jsonl`。底层 `plan-context.py` 仍作为执行层用于渲染和校验 sidecar，但不再暴露为用户 slash command。

### 3.2 安装 adapter

在 adapter 源码目录执行：

```bash
./manage.sh install
./manage.sh verify
```

如果 adapter 是作为其他项目中的 `superpower-adapter/` 目录存在，也可以从宿主项目执行：

```bash
./superpower-adapter/manage.sh install
./superpower-adapter/manage.sh verify
```

安装和校验是少数需要用户直接运行 shell 命令的步骤，因为此时 command / skill 还没有写入 Superpowers。

### 3.3 在目标项目初始化 spec 模板

```bash
./manage.sh bootstrap-spec /path/to/project --template standard
```

这会在目标项目创建 `.superpowers/spec/`，并保证入口为：

```text
.superpowers/spec/index.md
```

这一步通常在 Claude Code 会话外执行，因为它负责给目标项目创建初始 spec 文件结构。

### 3.4 可选：导入已有 spec

如果项目已经有旧规范目录、设计文档目录或其他格式的 spec，进入目标项目的 Claude Code 会话后，优先使用：

```text
/import-spec path/to/original-spec-dir
```

可选地带上主题提示：

```text
/import-spec path/to/original-spec-dir --hint "api contract"
```

导入流程会尽量把已有内容迁移到 `.superpowers/spec/` 的 leaf spec 中，并保留原始内容。这个 command 只用于一次性迁移；迁移后日常维护使用 `/update-spec`。

如果没有旧 spec，可以跳过这一步。

### 3.5 在 Claude Code 中初始化项目 spec 知识

进入目标项目的 Claude Code 会话后，使用 adapter 安装的 command：

```text
/init-spec
```

可选地带上关注范围：

```text
/init-spec payments and order workflow
```

这一步用于第一次从当前项目结构中生成轻量的 starter spec。后续开发中不要把它当作日常维护入口，日常沉淀知识应使用 `/update-spec`。

### 3.6 Superpowers 创建或选定 plan 后，由 `/check-workflow planning` 自动准备 sidecar

用户开启 Claude Code session 后，应先描述需求。只有当 Superpowers 已经为这个需求创建或选定了 plan，例如已经存在下面的文件时：

```text
docs/superpowers/plans/<stem>.md
```

才需要进入 plan sidecar 准备阶段。

如果当前任务由 Superpowers plan 驱动，建议在 plan 存在后使用：

```text
/check-workflow planning
```

它会自动：

- 初始化对应 sidecar。
- 根据 plan 标题或传入 hint，从 `.superpowers/spec/` 的索引图中推荐相关 spec。
- 把 planning 阶段选中的 spec context 写入 `plan.jsonl`。
- 设置 `.superpowers/current-plan`。

职责边界：

- `/check-workflow planning`：用户入口，负责自动准备 sidecar 和 planning-selected context。
- `spec-progressive-disclosure` / selector 执行层：帮助发现或推荐“哪些 spec 和当前任务相关”。
- `plan-context.py`：底层执行层，用于 sidecar 渲染、校验和测试，不再作为用户 slash command 暴露。

如果任务不使用 Superpowers plan，可以跳过这个阶段，但仍然可以按需读取 `.superpowers/spec/`。

### 3.7 日常任务前检查 workflow 状态

在进入规划、实现、评审或收尾阶段前，使用：

```text
/check-workflow
```

有 plan 的推荐调用顺序：

```text
描述需求
→ Superpowers 创建或选定 plan
→ /check-workflow planning（自动初始化 sidecar，并写入 planning spec context）
→ /check-workflow implement
→ 执行实现
→ /check-workflow review
→ 执行评审
→ /check-workflow completion
→ /update-spec（如果提示存在 durable knowledge）
```

无 plan 的简单任务可以跳过 planning sidecar 准备阶段，必要时只按需读取 `.superpowers/spec/` 并在任务结束后考虑 `/update-spec`。

它会通过 adapter 的执行层检查：

- 当前 plan 是否存在
- plan sidecar 是否初始化
- planning 阶段是否已经选择必要 spec context
- implement / review 阶段是否可以继续
- completion 阶段是否可能需要回写 durable knowledge

### 3.8 任务中按需读取 spec

正常情况下，Claude Code 会先看到 `.superpowers/spec/` 摘要树。

当任务需要规范上下文时，应该按以下顺序读取：

1. `.superpowers/spec/index.md`
2. 相关子目录的 `index.md`
3. 任务真正需要的 leaf spec 文件

不要在会话开始时一次性读取整个 `.superpowers/spec/` 目录。

### 3.9 任务结束后更新 spec

当任务产生了未来还会复用的实现知识时，在 Claude Code 中使用：

```text
/update-spec
```

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

---

## 4. Superpowers + adapter 的整体流程

```mermaid
flowchart TD
    A[安装 Superpowers 主插件] --> B[安装 adapter: manage.sh install]
    B --> C[校验 adapter: manage.sh verify]
    C --> D[初始化 spec 模板: manage.sh bootstrap-spec]
    D --> E[打开 Claude Code / Cursor 会话]
    E --> F[Superpowers SessionStart]
    F --> G[adapter hook 注入 spec 摘要树和 plan sidecar 状态]

    G --> H{是否是项目首次接入?}
    H -->|有旧 spec| I[/import-spec]
    H -->|需要 starter spec| J[/init-spec]
    H -->|否| K[用户描述需求]
    I --> J
    J --> K

    K --> L{Superpowers 是否创建或选定 plan?}
    L -->|是| M[/check-workflow planning 自动准备 sidecar]
    L -->|否| N[跳过 plan sidecar 准备]
    M --> O[/check-workflow 后续阶段检查]
    N --> O

    O --> P{是否可以进入当前阶段?}
    P -->|否| Q[按提示修复 plan / sidecar / context]
    Q --> O
    P -->|是| R[执行 Superpowers 常规任务]

    R --> S{任务是否需要项目规范?}
    S -->|否| V[继续实现 / 评审 / 收尾]
    S -->|是| T[读取 .superpowers/spec/index.md]
    T --> U[按索引进入子目录 index.md 和 leaf spec]
    U --> V

    V --> W[/check-workflow completion]
    W --> X{是否产生 durable knowledge?}
    X -->|否| Y[结束]
    X -->|是| Z[/update-spec]
    Z --> AA[更新 leaf spec 并刷新 index 链]
    AA --> Y
```

重点是：

- Superpowers 是用户面对的主流程。
- adapter 增强 Superpowers 的 command、skill、hook。
- `.superpowers/spec/` 是项目规范知识库。
- Python 脚本只作为 adapter command / hook 背后的执行层。

---

## 5. plan sidecar 在用户流程中的位置

如果任务由 Superpowers plan 驱动，主 plan 文件仍保留在：

```text
docs/superpowers/plans/<stem>.md
```

adapter 只是在旁边增加 sidecar：

```text
docs/superpowers/plans/<stem>.context/
├── plan.jsonl
├── implement.jsonl
├── review.jsonl
└── state.json
```

用户通常不需要直接编辑这些文件，也不需要手动执行 `/plan-context`；`/check-workflow planning` 会自动初始化 sidecar 并写入 planning context。

推荐语义：

- `plan.jsonl`：planning 阶段选定的共同上下文
- `implement.jsonl`：实现阶段额外上下文
- `review.jsonl`：评审阶段额外上下文
- `.superpowers/current-plan`：本地当前 plan 指针

---

## 6. 用户日常应该记住的入口

| 场景 | 用户入口 | 说明 |
|---|---|---|
| 安装 adapter | `./manage.sh install` | 将 overlay 写入 Superpowers 插件目录 |
| 校验安装 | `./manage.sh verify` | 检查 overlay 和 hook patch |
| 初始化 spec 模板 | `./manage.sh bootstrap-spec /path/to/project --template standard` | 创建 `.superpowers/spec/` |
| 导入已有 spec | `/import-spec` | 有旧规范目录时在 Claude Code 中执行 |
| 初次生成 starter spec | `/init-spec` | 在 Claude Code 中执行 |
| 自动准备 plan sidecar | `/check-workflow planning` | 有 Superpowers plan 时在 Claude Code 中执行 |
| 检查阶段状态 | `/check-workflow` | 在 Claude Code 中执行 |
| 沉淀长期知识 | `/update-spec` | 在 Claude Code 中执行 |
| 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者使用 |

---

## 7. 什么时候才需要看底层脚本

普通用户不需要直接调用 `superpowers/scripts/*.py`。

以下情况才需要查看或直接运行底层脚本：

- adapter 开发者正在调试某个 command 的执行层
- 自动化测试需要覆盖 command 背后的脚本行为
- release-check / self-test 在本地验证 adapter 安装产物
- 排查 hook patch、manifest、sidecar JSONL 等底层状态

即使在这些情况下，也要记住：最终验收标准仍然是用户能否在 Claude Code 等工具里通过 command / skill 正常使用 Superpowers + adapter。