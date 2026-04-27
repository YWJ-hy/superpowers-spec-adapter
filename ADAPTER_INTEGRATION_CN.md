# Superpowers Adapter 集成说明

本文说明 `superpower-adapter` 如何接入 Superpowers，以及当前 spec 渐进式披露流程如何工作。

如果你想了解用户在 Claude Code 等工具中如何通过 Superpowers command / skill 使用 adapter，请先看：[`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)

如果你在开发 adapter 或设计测试，请先看：[`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)

---

## 1. 这套 adapter 改了什么

adapter 的目标是：

- 以 Superpowers 为主框架。
- 在项目侧增加 `.superpowers/spec/` 规范库。
- 从 `.superpowers/spec/index.md` 开始渐进披露项目规范。
- 通过 `spec-researcher` 在 Superpowers `brainstorming` 和 `writing-plans` 阶段选择相关项目规范。
- 通过 plan 的 `Referenced Project Specs` 小节把项目规范固化到执行阶段。

adapter 不是业务代码目录，而是一个本地 adapter 源码目录。它负责把 overlay 写入已安装的 Superpowers 插件目录，并在 Superpowers 升级后重新安装这些能力。

---

## 2. 安装到 Superpowers 的内容

adapter 会把以下 overlay 安装进 Superpowers：

```text
superpowers/
├── agents/spec-researcher.md
├── skills/spec-progressive-disclosure/SKILL.md
├── skills/update-spec/SKILL.md
├── commands/import-spec.md
├── commands/init-spec.md
├── scripts/update-spec.py
├── scripts/spec-context.py
├── scripts/spec_common.py
├── scripts/spec_import.py
├── scripts/init-spec.py
├── scripts/spec_update_check.py
├── scripts/spec_select_target.py
└── scripts/spec_apply_update.py
```

同时会修改：

- `superpowers/hooks/hooks.json`（维护 adapter SessionStart 兼容配置）
- `superpowers/hooks/hooks-cursor.json`（维护 adapter sessionStart 兼容配置）
- `superpowers/skills/brainstorming/SKILL.md`
- `superpowers/skills/writing-plans/SKILL.md`
- `superpowers/skills/executing-plans/SKILL.md`
- `superpowers/skills/subagent-driven-development/SKILL.md`

patch 都带有 `superpower-adapter` marker，可由安装器重复安装、校验和卸载。

---

## 3. spec 渐进式披露

核心原则：不把 `.superpowers/spec/` 全量加载进上下文。

读取顺序：

1. 先读 `.superpowers/spec/index.md`。
2. 再按 index 进入子目录 `index.md`。
3. 只在当前任务需要时读取 leaf spec。

入口约束：

```text
.superpowers/spec/index.md
```

其他目录结构不强制，可以按项目自己定义。

当前流程不安装 SessionStart hook。`spec-researcher` 会在 `brainstorming` 和 `writing-plans` 阶段按需读取 `.superpowers/spec/index.md`，再沿索引读取相关 leaf spec。

---

## 4. `spec-researcher` agent

`spec-researcher` 是默认 spec 选择路径。

它的输入形态：

```yaml
task: <用户需求或已确认 Superpowers spec>
phase: brainstorm | plan | implement | review
specRoot: .superpowers/spec
planPath: docs/superpowers/plans/<stem>.md
planSummary: <可选摘要>
changedFiles:
  - <可选相关文件>
focus: <可选关注范围>
maxSpecs: 5
```

它的输出形态：

```yaml
status: ok | partial | missing_spec_root | no_relevant_spec
query: <任务复述>
phase: brainstorm | plan | implement | review
selectedSpecs:
  - path: .superpowers/spec/<path>.md
    relevance: direct | supporting | phase_only
    readMode: summary | full
    confidence: high | medium | low
    reason: <选择原因>
indexesRead:
  - .superpowers/spec/index.md
rejectedSpecs: []
caveats: []
```

约束：

- 必须从 `.superpowers/spec/index.md` 开始。
- 不扫描全量 spec 树，除非用户明确要求 full audit。
- 不修改文件。
- 不实现代码。
- 不写持久 sidecar 状态。

---

## 5. Superpowers native skill patch

### 5.1 `brainstorming`

adapter 在 Superpowers 完成初步需求理解后、提出方案前注入：

```text
调用 spec-researcher
→ 读取少量相关项目 spec
→ 作为 Adapter Project Spec Context 参与设计
```

没有匹配 spec 或缺少 `.superpowers/spec/index.md` 时，不阻塞 brainstorming。

### 5.2 `writing-plans`

adapter 在拆分任务前注入正式 spec 选择：

```text
读取已确认 Superpowers spec
→ 调用 spec-researcher
→ 写 implementation plan
→ plan 包含 Referenced Project Specs
```

plan 小节示例：

```markdown
## Referenced Project Specs

- `.superpowers/spec/quality/error-rules.md`
  - Applies to Tasks 1 and 3.
  - Constraints:
    - Keep error payloads stable.
```

如果项目 spec 与本次 Superpowers spec 冲突，应先让用户确认或修改 spec。

### 5.3 `executing-plans`

执行前读取 plan 中的 `Referenced Project Specs`，并把它作为 selected project spec context。

执行阶段不重新选择 spec。

### 5.4 `subagent-driven-development`

分发 implementer / reviewer subagent 前，主 agent 应把 plan 的 `Referenced Project Specs` 放进 subagent prompt。

subagent 不应重新从 `.superpowers/spec/` 选择规范，除非主 agent 判断 plan 引用明显不足并回到 planning 修正。

---

## 6. command / skill 能力

### `/init-spec`

用于首次从当前项目 inventory 辅助 agent 生成轻量 starter spec。底层脚本只输出机械 inventory，不直接写 spec 内容。

底层脚本：

```bash
python3 "$TARGET_DIR/scripts/init-spec.py" . "optional focus" --json
```

### `/import-spec`

用于一次性结构导入已有规范目录或文件，不做语义融合。

底层脚本：

```bash
python3 "$TARGET_DIR/scripts/spec_import.py" path/to/original-spec-dir --target imported
```

### `update-spec` skill

用于任务完成、修 bug、评审或讨论后审查是否需要沉淀 durable implementation knowledge。该 skill 由 agent 先判断是否值得更新，再读取 indexed specs、语义去重、判断归属并直接编辑 leaf spec；底层脚本只提供候选列表、机械校验和索引刷新。

调试脚本示例：

```bash
python3 "$TARGET_DIR/scripts/spec_select_target.py" --json
python3 "$TARGET_DIR/scripts/spec_update_check.py" --json
python3 "$TARGET_DIR/scripts/update-spec.py"
```

`/init-spec` 和 `/import-spec` 是独立 adapter command，完成后不触发 Superpowers completion verification；`update-spec` 是自动触发 skill，不保留 slash command 入口。

---

## 7. 安装、校验和发布检查

常用命令：

```bash
./manage.sh install
./manage.sh verify
./manage.sh status
./manage.sh bootstrap-spec /path/to/project --template standard
./manage.sh init-spec /path/to/project "optional focus"
./manage.sh doctor /path/to/project
./manage.sh self-test /path/to/project
./manage.sh release-check /path/to/project
```

发布前：

```bash
./manage.sh release-check /path/to/project
```

它会运行：

- `verify`
- `doctor`
- `self-test`
- `export-manifest`

---

## 8. 验收重点

一次 adapter 改动完成前，应确认：

- `agents/spec-researcher.md` 已安装。
- 未安装 adapter SessionStart hook；spec 读取由 `spec-researcher` 按需触发。
- `brainstorming` patch 会调用 `spec-researcher` 获取轻量 spec context。
- `writing-plans` patch 会要求 `Referenced Project Specs`。
- `executing-plans` 和 `subagent-driven-development` 只消费 plan 引用，不重新选择 spec。
- `/import-spec`、`/init-spec` 仍作为独立 command 工作，`update-spec` 作为 skill 安装并能在任务后审查 durable knowledge。
- `verify`、`self-test`、`release-check` 通过。
