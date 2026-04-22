# Superpower Adapter 快速使用手册

这份文档只保留最终用户最需要的内容：

1. 怎么安装
2. 怎么初始化 spec
3. 怎么一键更新 spec
4. 怎么做发布前检查
5. Superpowers 升级后怎么重装

如果你需要完整设计说明、流程图和实现细节，请看：

- [`ADAPTER_INTEGRATION_CN.md`](./ADAPTER_INTEGRATION_CN.md)

---

## 1. 这套东西是干什么的

这套 `superpower-adapter` 的作用是：

- 让 **Superpowers 继续作为主插件**
- 给项目增加一套 `.superpowers/spec/` 规范系统
- 支持 **渐进式披露**：启动时只注入摘要树，真正实现时再按需读取具体 spec
- 提供一个接近 Trellis 风格的 `update-spec` 体验

一句话：

> 它把 `.superpowers/spec/` 变成一套可安装、可升级重放、支持按需读取的项目规范系统。

---

## 2. 安装前提

在使用前，需要满足：

### 2.1 已安装 Superpowers Claude Code 插件

例如你已经执行过：

```bash
/plugin install superpowers@claude-plugins-official
```

当前 adapter 默认会优先修改**用户本地已安装的 Superpowers 插件目录**。

如果没有检测到已安装插件，才会回退到当前仓库里的 `./superpowers`。

### 2.2 当前项目根目录可写

因为 spec 会放在：

```text
.superpowers/spec/
```

---

## 3. 第一次安装 adapter

在当前仓库根目录执行：

```bash
./superpower-adapter/install.sh
./superpower-adapter/verify.sh
```

或者：

```bash
./superpower-adapter/manage.sh install
./superpower-adapter/manage.sh verify
```

### 安装后会发生什么

adapter 会把 overlay 写进已安装的 Superpowers 插件目录，包括：

- `commands/update-spec.md`
- `hooks/session-spec-index`
- `scripts/update-spec.py`
- `scripts/spec-context.py`
- `scripts/spec_update_run.py`
- 以及其他相关脚本

同时会 patch：

- `hooks/hooks.json`
- `hooks/hooks-cursor.json`

让 SessionStart 时自动注入 `.superpowers/spec` 的轻量摘要树，以及当前 plan sidecar 的轻量状态。

---

## 4. 初始化 `.superpowers/spec`

### 最小初始化

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project
```

会创建：

- `.superpowers/spec/index.md`
- `.superpowers/spec/.adapter-ignore`

### 用 preset 初始化

#### Web 项目

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project --preset web
```

生成：
- `frontend/`
- `guides/`

#### Backend 项目

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project --preset backend
```

生成：
- `backend/`
- `guides/`

#### Fullstack 项目

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project --preset fullstack
```

生成：
- `backend/`
- `frontend/`
- `guides/`

### 混合自定义目录

```bash
./superpower-adapter/manage.sh bootstrap-spec /path/to/project --preset backend api-contracts
```

这个命令会：
- 创建 `backend/`
- 创建 `guides/`
- 再额外创建 `api-contracts/`

而且**不会覆盖已有文件**。

---

## 5. 日常怎么用 spec

### 5.1 如果任务由 Superpowers plan 驱动，先初始化 plan sidecar

保留原生 plan 文件路径不变，例如：

```text
docs/superpowers/plans/2026-04-22-example.md
```

为它初始化 sidecar：

```bash
python3 superpowers/scripts/plan-context.py init docs/superpowers/plans/2026-04-22-example.md --set-current
```

这会创建：

```text
docs/superpowers/plans/2026-04-22-example.context/
├── plan.jsonl
├── implement.jsonl
├── review.jsonl
└── state.json
```

并写入：

```text
.superpowers/current-plan
```

在 planning 阶段，把选中的 spec 写入 `plan.jsonl`；实现和评审阶段优先消费 sidecar，而不是重新从 `.superpowers/spec` 自由选择。

Git 建议：
- 建议把 `docs/superpowers/plans/<stem>.context/` 一起提交，保证 planning-selected context 可复现
- 建议把 `.superpowers/current-plan` 视为本地工作状态，并加入 `.gitignore`

### 5.2 平时不用全文加载

正常情况下：

- 启动时只拿到摘要树
- 真正实现时再按需读：
  - `.superpowers/spec/index.md`
  - 子目录 `index.md`
  - 具体 leaf spec 文件

### 5.3 在实现和评审前渲染 sidecar context

```bash
python3 superpowers/scripts/plan-context.py render --phase implement
python3 superpowers/scripts/plan-context.py render --phase review
```

可以用下面的命令校验当前 plan sidecar 是否完整：

```bash
python3 superpowers/scripts/plan-context.py verify --current
```

### 5.4 什么时候该更新 spec

当一次任务结束后，如果你学到了下面这些内容，就应该更新 spec：

- 新的实现规则
- 新的 contract / payload 约束
- 新的 validation / error behavior
- 重要设计决策
- 项目约定
- 非显而易见的 gotcha
- 跨层 checklist（这种通常放到 `guides/`）

判断规则：

- **这是怎么安全实现** → 写到 `backend/*.md` 或 `frontend/*.md`
- **这是实现前要考虑什么** → 写到 `guides/*.md`

### 5.5 一键更新 spec（推荐）

如果你已经知道 hint、标题、why 和规则内容，直接用：

```bash
python3 superpowers/scripts/spec_update_run.py \
  "error handling" \
  "Error normalization" \
  "Prevent inconsistent backend error shapes." \
  "Normalize backend error payloads" \
  "Keep user-facing messages stable"
```

它会自动：

1. 选择目标 spec 文件
2. 把结构化更新块写入正文
3. 刷新索引链
4. 输出最终命中的 spec 文件

### 5.6 如果你想手动分步控制

#### 选目标 spec

```bash
python3 superpowers/scripts/spec_select_target.py "error handling"
```

#### 生成更新提示

```bash
python3 superpowers/scripts/spec_update_prompt.py backend/error-handling.md
```

#### 生成更新模板

```bash
python3 superpowers/scripts/spec_update_template.py backend/error-handling.md "Error normalization" "Prevent inconsistent backend error shapes."
```

#### 自动写入正文

```bash
python3 superpowers/scripts/spec_apply_update.py \
  backend/error-handling.md \
  "Error normalization" \
  "Prevent inconsistent backend error shapes." \
  "Normalize backend error payloads" \
  "Keep user-facing messages stable"
```

#### 刷新索引链

```bash
python3 superpowers/scripts/update-spec.py
```

### 5.7 更新 spec 时要注意什么

- 不要把详细规则都写进 `index.md`
- `index.md` 负责导航，叶子文件负责正文内容
- 优先写“未来还会用到”的知识
- 写清楚 **为什么**，不只是 **是什么**
- 更新正文后要刷新索引链

---

## 6. 忽略目录怎么配

默认忽略这些目录：

- `draft`
- `archive`
- `examples`

如果还想忽略更多目录，编辑：

```text
.superpowers/spec/.adapter-ignore
```

格式是每行一个目录名，例如：

```text
# custom ignored dirs
private-notes
old-specs
scratch
```

这些忽略规则会影响：

- `update-spec.py`
- `spec-context.py --tree`
- SessionStart 注入摘要树
- manifest 的 effective view

---

## 7. 检查当前状态

### 查看安装状态

```bash
./superpower-adapter/manage.sh status
```

### 做健康检查

```bash
./superpower-adapter/manage.sh doctor /path/to/project
```

它会检查：

- adapter 文件是否齐全
- hook patch 是否存在
- `.superpowers/spec/index.md` 是否存在
- ignore 配置是否合理
- rawView / effectiveView 差异是否异常
- 有无缺失的 index 链

### 导出快照

```bash
./superpower-adapter/manage.sh export-manifest /path/to/project ./superpower-adapter/manifest-output.json
```

这个文件可以用于：

- 升级前后对比
- 排查忽略规则
- 记录当前 spec 结构状态

---

## 8. 发布前检查

在准备把这套 adapter 视为当前稳定状态前，跑：

```bash
./superpower-adapter/manage.sh release-check /path/to/project
```

它会自动执行：

- `verify`
- `doctor`
- `self-test`
- `export-manifest`

这是最推荐的最终检查入口。

---

## 9. Superpowers 升级后怎么做

如果 Superpowers 插件升级了，不需要重新手工改插件目录，直接重跑：

```bash
./superpower-adapter/install.sh
./superpower-adapter/verify.sh
```

或者直接：

```bash
./superpower-adapter/manage.sh release-check /path/to/project
```

adapter 会把 overlay 重新安装回新的插件版本。

---

## 10. 最短使用路径

如果你只记 4 条命令，记这几条就够了：

### 第一次初始化

```bash
./superpower-adapter/manage.sh install
./superpower-adapter/manage.sh bootstrap-spec /path/to/project --preset fullstack
```

### 日常沉淀 spec

```bash
python3 superpowers/scripts/spec_update_run.py \
  "error handling" \
  "Error normalization" \
  "Prevent inconsistent backend error shapes." \
  "Normalize backend error payloads"
```

### 发布前检查

```bash
./superpower-adapter/manage.sh release-check /path/to/project
```

### 插件升级后重装

```bash
./superpower-adapter/install.sh
./superpower-adapter/verify.sh
```

---

## 11. 一句话总结

> 这套 adapter 现在已经可以默认作用于已安装的 Superpowers 插件，并提供一条真正可用的“一键 update-spec”链路：选目标、写正文、刷新索引，一步完成。
