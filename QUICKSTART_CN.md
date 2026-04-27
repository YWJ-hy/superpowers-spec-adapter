# Superpower Adapter 快速使用手册

这份文档只保留最终用户最需要的内容：安装、初始化 wiki、让 Superpowers 渐进读取项目规范、更新 wiki、发布前检查。

如果你需要从 Claude Code 等工具中的用户操作流程开始，请先看：

- [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)

如果你在开发 adapter，请先看测试原则：

- [`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)

---

## 1. 这套东西是干什么的

`superpower-adapter` 的作用是：

- 让 **Superpowers 继续作为主插件**。
- 给项目增加一套 `.superpowers/wiki/` 规范系统。
- 支持 **渐进式披露**：Superpowers 写 spec / plan 时由 `wiki-researcher` 按需读取具体 wiki 页面。
- 安装 `wiki-researcher` agent，帮助 `brainstorming` 和 `writing-plans` 选择相关项目规范。
- 要求 implementation plan 用 `Referenced Project Wiki` 固化执行阶段要遵守的项目规范。
- 提供 `import-wiki`、`init-wiki`、`break-loop`、`update-wiki` 能力。

一句话：

> 它把 `.superpowers/wiki/` 变成一套可安装、可升级重放、支持按需读取的项目规范系统。

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

- `agents/wiki-researcher.md`
- `commands/import-wiki.md`
- `commands/init-wiki.md`
- `skills/break-loop/SKILL.md`
- `skills/wiki-progressive-disclosure/SKILL.md`
- `skills/update-wiki/SKILL.md`
- adapter 执行脚本

同时会 patch：

- `hooks/hooks.json`（维护 adapter SessionStart 兼容配置）
- `hooks/hooks-cursor.json`（维护 adapter sessionStart 兼容配置）
- `skills/brainstorming/SKILL.md`
- `skills/writing-plans/SKILL.md`
- `skills/executing-plans/SKILL.md`
- `skills/subagent-driven-development/SKILL.md`

---

## 3. 初始化 `.superpowers/wiki`

```bash
./manage.sh bootstrap-wiki /path/to/project --template standard
```

会创建 `.superpowers/wiki/index.md` 和模板 leaf wiki page。已有文件不会被覆盖。

---

## 4. 初始化或导入项目知识

在 Claude Code 中可使用：

```text
/init-wiki
/init-wiki payments and order workflow
/import-wiki path/to/original-wiki-dir
/import-wiki path/to/original-wiki-dir --target imported
```

`/init-wiki` 通过项目 inventory 辅助 agent 首次生成轻量 starter wiki；`/import-wiki` 用于一次性结构迁移已有规范，不做语义融合。两者都是独立 adapter command，完成后即可结束。

---

## 5. 日常怎么用 wiki

日常优先使用 Superpowers 主流程：

```text
用户描述需求
→ brainstorming 调用 wiki-researcher 轻量披露项目规范
→ writing-plans 调用 wiki-researcher 正式选择项目规范
→ plan 写入 Referenced Project Wiki
→ executing-plans / subagent-driven-development 消费 Referenced Project Wiki
→ 遇到 bug 时先用 Superpowers systematic-debugging 修复和验证
→ 修复后需要深度复盘时使用 break-loop
→ update-wiki skill 审查是否需要沉淀长期知识
```

plan 中应包含：

```markdown
## Referenced Project Wiki

- `.superpowers/wiki/quality/error-rules.md`
  - Applies to Tasks 1 and 3.
  - Constraints:
    - Keep error payloads stable.
```

执行和评审阶段读取这个小节，不重新选择 wiki 页面。

---

## 6. 平时不用全文加载

正常情况下：

- `brainstorming` / `writing-plans` 通过 `wiki-researcher` 按需读：
  - `.superpowers/wiki/index.md`
  - 子目录 `index.md`
  - 具体 leaf wiki page 文件
- 执行阶段读取 plan 的 `Referenced Project Wiki`。

开发调试时可以直接读取执行层输出：

```bash
TARGET_DIR="$(python3 ./superpower-adapter/lib/resolve_target.py | python3 -c 'import json,sys; print(json.load(sys.stdin)["target"])')"
python3 "$TARGET_DIR/scripts/wiki-context.py" --tree --depth 2
python3 "$TARGET_DIR/scripts/wiki-context.py" --file quality/error-rules.md
```

---

## 7. 什么时候该更新 wiki

当一次任务结束后，如果你学到了下面这些内容，就应该更新 wiki：

- 新的实现规则
- 新的 contract / payload 约束
- 新的 validation / error behavior
- 重要设计决策
- 项目约定
- 非显而易见的 gotcha
- 跨层 checklist

推荐入口是安装后的 `update-wiki` skill：由 agent 在任务完成后判断是否有 durable implementation knowledge 需要写入 `.superpowers/wiki/`。如果没有值得沉淀的内容，应明确跳过，不强制编辑。

对于 bug，正常链路是 `systematic-debugging` → `break-loop` → `update-wiki`：先用 Superpowers `systematic-debugging` 完成 root cause investigation、修复和验证；如果是重复 bug、多次失败修复、跨层 contract、隐含假设或测试缺口，再用 `break-loop` 做后置复盘；只有复盘提炼出长期规则、contract、gotcha、checklist 或设计决策时，才交给 `update-wiki` 持久化。

执行层调试入口只用于机械检查，不替 agent 判断是否需要更新或写到哪里：

```bash
python3 "$TARGET_DIR/scripts/wiki_select_target.py" --json
python3 "$TARGET_DIR/scripts/wiki_update_check.py" --json
python3 "$TARGET_DIR/scripts/update-wiki.py"
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
