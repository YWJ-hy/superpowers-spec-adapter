# Superpowers + Adapter 用户流程说明

本文面向最终用户，说明 adapter 安装到 Superpowers 后，用户在 Claude Code、Cursor 等工具中应如何使用。

如果你是 adapter 开发者，请先读 [`ADAPTER_DEVELOPMENT_CN.md`](./ADAPTER_DEVELOPMENT_CN.md)。

---

## 1. 一句话理解

`superpower-adapter` 不替代 Superpowers，也不要求用户直接运行一组 Python 脚本。

它的定位是：

> adapter 为 Superpowers 提供项目 wiki 的渐进式披露能力，让 Superpowers 在编写本次 spec 和 implementation plan 时自然继承 `.superpowers/wiki/` 中的既有项目 wiki 知识。

用户面对的主流程仍是 Superpowers：

- `brainstorming`：理解需求并写本次 Superpowers spec。
- `writing-plans`：根据已确认 spec 写 implementation plan。
- `executing-plans` 或 `subagent-driven-development`：按 plan 执行。

adapter 增强这些阶段：

- 安装 `wiki-researcher` agent，用于从 `.superpowers/wiki/index.md` 开始渐进选择少量相关项目 wiki 页面。
- 在 `brainstorming` 阶段轻量披露相关项目 wiki 页面。
- 在 `writing-plans` 阶段正式选择相关项目 wiki 页面，生成配套 `.wiki-context.md` 约束产物，并要求 plan 写入轻量 `Referenced Project Wiki` 入口。
- 在执行阶段只消费 plan 中已经确认的 `Referenced Project Wiki` 和其链接的 `.wiki-context.md`。
- 安装 `break-loop` skill，用于 Superpowers `systematic-debugging` 修复并验证 bug 后做深度复盘，并在有长期价值时把候选交给 `update-wiki`。

`/import-wiki`、`/init-wiki` 是独立 adapter command。`break-loop` 是 bug 修复后的 adapter skill：它衔接 Superpowers `systematic-debugging`，只在 bug 已修复并验证后做后置复盘。`update-wiki` 是自动触发的 adapter skill：任务完成、修 bug、评审或讨论后，如果 agent 判断产生了 durable implementation knowledge，才审查并更新 `.superpowers/wiki/`。

Python 脚本是 command / skill / agent 背后的执行层，不是最终用户的主要交互入口。

---

## 2. adapter 插入 Superpowers 后发生了什么

安装 adapter 后，adapter 会把 overlay 写入用户已安装的 Superpowers 插件目录：

```text
Superpowers 插件目录
├── agents/
│   └── wiki-researcher.md
├── commands/
│   ├── init-wiki.md
│   └── import-wiki.md
├── skills/
│   ├── break-loop/
│   ├── wiki-progressive-disclosure/
│   └── update-wiki/
└── scripts/
    └── adapter 执行脚本
```

`wiki-progressive-disclosure` 会继续安装，但它只是说明性 / fallback skill；正常 `brainstorming` 和 `writing-plans` 流程由 `wiki-researcher` 直接完成 wiki 选择。

同时 adapter 会 patch Superpowers 的 native skills：

- `brainstorming`：在提出设计方案前调用 `wiki-researcher` 获取轻量项目 wiki上下文。
- `writing-plans`：在拆分任务前调用 `wiki-researcher` 正式选择项目 wiki 页面，生成 `docs/superpowers/plans/<plan-stem>.wiki-context.md`，并要求 plan 写入轻量 `Referenced Project Wiki` 入口。
- `executing-plans`：执行前读取 plan 中的 `Referenced Project Wiki` 和链接的 `.wiki-context.md`，不重新选择 wiki 页面。
- `subagent-driven-development`：把 plan 中的 `Referenced Project Wiki` 和链接的 `.wiki-context.md` 约束传给 implementer / reviewer subagent。
- `using-git-worktrees`：创建 worktree 时把原始分支、原始 worktree 和原始 HEAD 记录到新 worktree 的 private git-dir metadata。
- `finishing-a-development-branch`：metadata 有效时，提供明确合并回创建 worktree 前原始分支的收尾选项。

当前流程不安装 SessionStart hook；`wiki-researcher` 会在 `brainstorming` 和 `writing-plans` 阶段按需读取 `.superpowers/wiki/`。worktree origin metadata 是本地临时协调状态，不写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区。

---

## 3. 用户视角的完整推荐执行顺序

| 顺序 | 阶段 | 入口 | 是否每次都需要 | 目的 |
|---|---|---|---|---|
| 0 | 安装 Superpowers | `/plugin install superpowers@claude-plugins-official` | 只需一次 | 先安装 Superpowers 主插件 |
| 1 | 安装 adapter | `./manage.sh install` | 只需一次；Superpowers 升级后重跑 | 写入 adapter overlay、agent、command、skill、script |
| 2 | 校验 adapter | `./manage.sh verify` | 安装或升级后 | 确认安装产物和 native skill patch 完整 |
| 3 | 初始化 wiki 模板 | `./manage.sh bootstrap-wiki /path/to/project --template standard` | 每个目标项目一次 | 创建 `.superpowers/wiki/` wiki 目录 |
| 4 | 导入已有 wiki | `/import-wiki` | 有已有 wiki 或文档时才需要 | 把已有 wiki 或文档导入到 `.superpowers/wiki/` 格式 |
| 5 | 初始化 starter wiki | `/init-wiki` | 每个目标项目首次使用时 | 从当前项目结构生成第一版轻量 wiki 知识 |
| 6 | 描述需求并进入 `brainstorming` | Superpowers `brainstorming` | 复杂任务或需要设计时 | 写本次 Superpowers spec，并轻量参考项目 wiki |
| 7 | 写 implementation plan | Superpowers `writing-plans` | 有已确认 spec 后 | 正式选择项目 wiki 页面，生成 `.wiki-context.md`，并在 plan 中写入轻量 `Referenced Project Wiki` |
| 8 | 执行 plan | `executing-plans` / `subagent-driven-development` | 有 plan 时 | 按 plan 执行，并消费 `Referenced Project Wiki` 和链接的 `.wiki-context.md` |
| 8.5 | worktree 收尾 | `finishing-a-development-branch` | 使用 Superpowers worktree 开发后 | metadata 有效时，可明确合并回创建 worktree 前的原始分支 |
| 9 | 修 bug 后复盘 | `systematic-debugging` → `break-loop` | bug 修复并验证后，且需要防复发分析时 | 先用 Superpowers 修对 bug，再由 adapter 复盘 root cause、失败修复路径、防复发机制和可沉淀候选 |
| 10 | 任务后更新 wiki | `update-wiki` skill | 任务产生长期可复用知识时 | 审查并回写 durable implementation knowledge |
| 11 | 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者发布前 | 运行 verify、doctor、self-test、export-manifest |

用户日常在 Claude Code 中主要记住这条链：

```text
描述需求
→ Superpowers brainstorming
→ adapter 轻量披露相关项目 wiki 页面
→ Superpowers 写并确认本次 spec
→ Superpowers writing-plans
→ adapter 正式选择项目 wiki，生成 .wiki-context.md，并在 plan 写入轻量 Referenced Project Wiki
→ Superpowers executing-plans / subagent-driven-development 按 plan 和 .wiki-context.md 执行
→ 遇到 bug 时先用 Superpowers systematic-debugging 修复和验证
→ 修复后需要防复发分析时使用 break-loop
→ update-wiki skill 审查是否需要沉淀长期知识
```

---

## 4. 安装与初始化

### 4.1 安装 adapter

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

### 4.2 初始化 wiki 模板

```bash
./manage.sh bootstrap-wiki /path/to/project --template standard
```

这会在目标项目创建 `.superpowers/wiki/`，并保证入口为：

```text
.superpowers/wiki/index.md
```

### 4.3 可选：导入已有 wiki

```text
/import-wiki path/to/original-wiki-dir
/import-wiki path/to/original-wiki-dir --target imported
```

`/import-wiki` 是独立 adapter command，只做已有规范的结构导入、避免覆盖和索引刷新；如果导入内容需要语义整理，后续由 `update-wiki` skill 审查并更新。

### 4.4 初始化项目 wiki 知识

```text
/init-wiki
/init-wiki payments and order workflow
```

这一步用于第一次从当前项目 inventory 中辅助 agent 生成轻量 starter wiki。脚本只提供语言、依赖、目录、样例文件和 indexed wiki page 候选；是否写入、写到哪里由 agent 判断。后续开发中不要把它当作日常维护入口，日常沉淀知识应由 `update-wiki` skill 审查。

---

## 5. 日常开发中的 wiki 披露

### 5.1 brainstorming 阶段

Superpowers `brainstorming` 在理解需求并提出设计方案前，会调用 `wiki-researcher`：

```yaml
task: <用户需求和当前理解>
phase: brainstorm
wikiRoot: .superpowers/wiki
focus: <已知模块或关注点>
maxWikiPages: 3
```

`wiki-researcher` 会从 `.superpowers/wiki/index.md` 开始渐进读取，返回少量相关 wiki 页面。没有匹配项或没有 `.superpowers/wiki/index.md` 时，不阻塞 brainstorming，只说明 caveat 并继续。

### 5.2 writing-plans 阶段

Superpowers `writing-plans` 在拆分任务前，会调用 `wiki-researcher` 正式选择项目 wiki 页面：

```yaml
task: <已确认 Superpowers spec 或需求摘要>
phase: plan
wikiRoot: .superpowers/wiki
planPath: docs/superpowers/plans/<filename>.md
planSummary: <计划目标和任务区域>
maxWikiPages: 5
```

writing-plans 默认把详细约束写入与 plan 同名的 sidecar 文件：

```text
docs/superpowers/plans/<plan-stem>.wiki-context.md
```

plan 必须包含轻量入口：

```markdown
## Referenced Project Wiki

Detailed wiki context: `docs/superpowers/plans/<plan-stem>.wiki-context.md`

- `.superpowers/wiki/domain/user.md` — applies to Tasks 1, 2, and 4; hard constraint: use `account_id` as the stable identity key.
```

`.wiki-context.md` 应包含每个选中 wiki 页的路径、适用任务、具体实现 / 测试 / review 约束、硬约束标记、必要原文锚点和 caveats。如果 selected wiki page 与本次 Superpowers spec 冲突，应先让用户确认是调整需求 spec 还是更新项目 wiki，再写 plan。

### 5.3 执行阶段

`executing-plans` 和 `subagent-driven-development` 执行前应读取 plan 中的 `Referenced Project Wiki`，再读取其中链接的 `.wiki-context.md`。

执行阶段不应默认：

- 重新从 `.superpowers/wiki/` 选择 wiki 页面。
- 临时在执行阶段重新解释 wiki 约束，或绕过 planning 生成的 `.wiki-context.md`。
- 绕过 plan 中已经确认的 wiki 约束。

如果 plan 缺少 `Referenced Project Wiki`、链接的 `.wiki-context.md` 缺失，或 context 明显不足，应提示回到 planning 阶段补齐。

### 5.4 worktree 原始分支收尾

当 Superpowers 通过 `using-git-worktrees` 创建 linked worktree 时，adapter 会让它在新 worktree 的 private git-dir 中记录本地临时 metadata：原始分支、原始 worktree 和原始 HEAD。这个文件用于 `finishing-a-development-branch` 判断“这次 worktree 是从哪个分支创建的”。

如果 metadata 有效，收尾菜单会提供明确的“合并回原始分支”选项，并优先在原始 worktree 中执行 merge，避免在 feature worktree 中 checkout 已被其他 worktree 占用的分支。如果 metadata 缺失、损坏，或创建 worktree 时处于 detached HEAD，则回退到 Superpowers 原生 base branch 判断 / 询问流程。

该 metadata 不进入项目文档和版本控制；不要把它写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区。

### 5.5 手动 fallback：渐进读取 wiki

正常流程由 `wiki-researcher` 完成渐进选择。只有在排障、解释规则，或 `wiki-researcher` 不可用而需要手动 fallback 时，才按以下顺序读取：

1. `.superpowers/wiki/index.md`
2. 相关子目录的 `index.md`
3. 任务真正需要的 leaf wiki page 文件

不要在会话开始时一次性读取整个 `.superpowers/wiki/` 目录。

---

## 6. 任务结束后更新 wiki

任务完成后，如果 agent 判断产生了未来还会复用的实现知识，安装后的 `update-wiki` skill 会审查并更新 `.superpowers/wiki/`。没有值得沉淀的内容时，应明确说明无需更新，不强制写入。

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

`update-wiki` 是 adapter skill。触发后，agent 应读取 indexed wiki pages，做语义去重和归属判断，检查目标 leaf wiki page 是否过大或语义混杂，再更新 leaf wiki page 并刷新 index；脚本只用于候选展示、路径安全、格式校验、过大页面机械报告和索引刷新。

当目标 leaf wiki page 过大时，`update-wiki` 不应按固定 chunk 拆成 `part-1` / `part-2`，而应由 agent 按 ownership 拆分。默认优先在当前目录平铺创建少量 sibling leaf pages；只有原页面已经变成多个稳定子主题集合、需要局部导航，或拆分后会产生多个子页时，才创建主题目录和该目录下的 `index.md`。

---

## 7. 用户日常应该记住的入口

| 场景 | 用户入口 | 说明 |
|---|---|---|
| 安装 adapter | `./manage.sh install` | 将 overlay 写入 Superpowers 插件目录 |
| 校验安装 | `./manage.sh verify` | 检查 overlay、agent、native skill patch 和 hook 配置 |
| 初始化 wiki 模板 | `./manage.sh bootstrap-wiki /path/to/project --template standard` | 创建 `.superpowers/wiki/` |
| 导入已有 wiki | `/import-wiki` | 有已有wiki 目录时在 Claude Code 中执行 |
| 初次生成 starter wiki | `/init-wiki` | 在 Claude Code 中执行 |
| 设计阶段参考项目 wiki | Superpowers `brainstorming` + `wiki-researcher` | 自动轻量披露相关项目 wiki 页面 |
| 计划阶段固化项目 wiki | Superpowers `writing-plans` + `Referenced Project Wiki` + `.wiki-context.md` | 自动选择 wiki、生成详细约束产物，并在 plan 中写入轻量入口 |
| 沉淀长期知识 | `update-wiki` skill | 由 agent 在任务后自动审查是否需要执行 |
| 发布前检查 adapter | `./manage.sh release-check /path/to/project` | adapter 维护者使用 |

---

## 8. 什么时候才需要看底层脚本

普通用户不需要直接调用 `superpowers/scripts/*.py`。

以下情况才需要查看或直接运行底层脚本：

- adapter 开发者正在调试某个 command 的执行层。
- 自动化测试需要覆盖 command 背后的脚本行为。
- release-check / self-test 在本地验证 adapter 安装产物。
- 排查 manifest、native skill patch、hook 配置、wiki 索引等底层状态。

即使在这些情况下，也要记住：最终验收标准仍然是用户能否在 Claude Code 等工具里通过 Superpowers command / skill / agent 集成路径正常使用 Superpowers + adapter。
