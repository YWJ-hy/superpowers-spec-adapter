# Superpower Adapter 快速使用手册

这份文档只保留最终用户最需要的内容：安装、初始化 spec、让 Superpowers 渐进读取项目规范、更新 spec、发布前检查。

如果你需要从 Claude Code 等工具中的用户操作流程开始，请先看：

- [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)

如果你在开发 adapter，请先看测试原则：

- [`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)

---

## 1. 这套东西是干什么的

`superpower-adapter` 的作用是：

- 让 **Superpowers 继续作为主插件**。
- 给项目增加一套 `.superpowers/spec/` 规范系统。
- 支持 **渐进式披露**：Superpowers 写 spec / plan 时由 `spec-researcher` 按需读取具体 spec。
- 安装 `spec-researcher` agent，帮助 `brainstorming` 和 `writing-plans` 选择相关项目规范。
- 要求 implementation plan 用 `Referenced Project Specs` 固化执行阶段要遵守的项目规范。
- 提供 `import-spec`、`init-spec`、`update-spec` 能力。

一句话：

> 它把 `.superpowers/spec/` 变成一套可安装、可升级重放、支持按需读取的项目规范系统。

---

## 2. 第一次安装 adapter

如果当前就在 adapter 仓库根目录，执行：

```bash
./manage.sh install
./manage.sh verify
```

如果 adapter 作为宿主项目中的 `superpower-adapter/` 子目录存在，从宿主项目执行：

```bash
./superpower-adapter/manage.sh install
./superpower-adapter/manage.sh verify
```

安装后会写入：

- `agents/spec-researcher.md`
- `commands/import-spec.md`
- `commands/init-spec.md`
- `commands/update-spec.md`
- `skills/spec-progressive-disclosure/SKILL.md`
- adapter 执行脚本

同时会 patch：

- `hooks/hooks.json`（清理旧 adapter SessionStart hook）
- `hooks/hooks-cursor.json`（清理旧 adapter sessionStart hook）
- `skills/brainstorming/SKILL.md`
- `skills/writing-plans/SKILL.md`
- `skills/executing-plans/SKILL.md`
- `skills/subagent-driven-development/SKILL.md`

---

## 3. 初始化 `.superpowers/spec`

```bash
./manage.sh bootstrap-spec /path/to/project --template standard
```

会创建 `.superpowers/spec/index.md` 和模板 leaf spec。已有文件不会被覆盖。

---

## 4. 初始化或导入项目知识

在 Claude Code 中可使用：

```text
/init-spec
/init-spec payments and order workflow
/import-spec path/to/original-spec-dir
/import-spec path/to/original-spec-dir --hint "api contract"
```

`/init-spec` 用于首次生成 starter spec；`/import-spec` 用于一次性迁移已有规范。两者都是独立 adapter command，完成后即可结束。

---

## 5. 日常怎么用 spec

日常优先使用 Superpowers 主流程：

```text
用户描述需求
→ brainstorming 调用 spec-researcher 轻量披露项目规范
→ writing-plans 调用 spec-researcher 正式选择项目规范
→ plan 写入 Referenced Project Specs
→ executing-plans / subagent-driven-development 消费 Referenced Project Specs
→ /update-spec（有长期知识时）
```

plan 中应包含：

```markdown
## Referenced Project Specs

- `.superpowers/spec/quality/error-rules.md`
  - Applies to Tasks 1 and 3.
  - Constraints:
    - Keep error payloads stable.
```

执行和评审阶段读取这个小节，不重新选择 spec。

---

## 6. 平时不用全文加载

正常情况下：

- `brainstorming` / `writing-plans` 通过 `spec-researcher` 按需读：
  - `.superpowers/spec/index.md`
  - 子目录 `index.md`
  - 具体 leaf spec 文件
- 执行阶段读取 plan 的 `Referenced Project Specs`。

开发调试时可以直接读取执行层输出：

```bash
TARGET_DIR="$(python3 ./superpower-adapter/lib/resolve_target.py | python3 -c 'import json,sys; print(json.load(sys.stdin)["target"])')"
python3 "$TARGET_DIR/scripts/spec-context.py" --tree --depth 2
python3 "$TARGET_DIR/scripts/spec-context.py" --file quality/error-rules.md
```

---

## 7. 什么时候该更新 spec

当一次任务结束后，如果你学到了下面这些内容，就应该更新 spec：

- 新的实现规则
- 新的 contract / payload 约束
- 新的 validation / error behavior
- 重要设计决策
- 项目约定
- 非显而易见的 gotcha
- 跨层 checklist

推荐入口：

```text
/update-spec
```

执行层调试入口：

```bash
python3 "$TARGET_DIR/scripts/spec_update_check.py" --summary "normalize backend error contract"
python3 "$TARGET_DIR/scripts/spec_update_run.py" \
  "error handling" \
  "Error normalization" \
  "Prevent inconsistent backend error shapes." \
  "Normalize backend error payloads" \
  "Keep user-facing messages stable"
```

---

## 8. 发布前检查

```bash
./manage.sh release-check /path/to/project
```

这会运行：

- `verify`
- `doctor`
- `self-test`
- `export-manifest`

---

## 9. Superpowers 升级后重装

Superpowers 升级后在 adapter 仓库根目录重新运行：

```bash
./manage.sh install
./manage.sh verify
```
