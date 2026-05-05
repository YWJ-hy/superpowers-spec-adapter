# Superpowers Adapter 开发说明

本文面向 adapter 开发者，说明开发和测试 adapter 时应遵守的入口、验收和测试原则。

最终用户流程见 [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)。

---

## 1. 核心原则

adapter 的目标不是让用户直接使用 Python 脚本，而是增强用户在 Claude Code、Cursor 等工具中使用 Superpowers 的体验。

因此开发时必须遵守：

> adapter 功能的最终验收，应以 Claude Code 等工具中通过 Superpowers command / skill 发起的集成路径为准，不能只以直接执行 Python 脚本成功为准。

Python 脚本是执行层，command、skill、agent 才是用户实际接触到的产品入口。

---

## 2. 开发前必读顺序

在修改 adapter 功能前，先阅读：

1. [`ADAPTER_USER_FLOW_CN.md`](./ADAPTER_USER_FLOW_CN.md)
2. 本文档
3. 相关 overlay command、skill 或 agent，例如：
   - `overlays/skills/break-loop/SKILL.md`，这是 Superpowers `systematic-debugging` 修复并验证 bug 后的深度复盘入口
   - `overlays/skills/update-wiki/SKILL.md`
   - `overlays/commands/init-wiki.md`
   - `overlays/commands/import-wiki.md`
   - `overlays/commands/lanhu-requirements.md`，这是可选蓝湖角色 PRD 入口；必须先确认 `frontend` / `backend` 角色，无子级页时写入 `.lanhu/MM-DD-需求命名.md`，有子级页时写入 `.lanhu/MM-DD-父级需求名称/`，其中包含继承目录需求名的父级 PRD、各子级 PRD 和 `index.md`，然后等待用户确认
   - `overlays/agents/wiki-researcher.md`，这是正常流程的 wiki 选择入口
   - `overlays/agents/lanhu-requirements-analyst.md`，这是可选蓝湖角色 PRD 清洗入口，不做实现分析；其模板结构来源维护在 `role-prd/`
   - `overlays/agents/graphify-researcher.md`，这是可选 graphify 候选关系线索入口，不决定最终影响文件
   - `overlays/skills/wiki-progressive-disclosure/SKILL.md`，这是说明性 / fallback 规则文档

如果只读 `overlays/scripts/*.py`，容易把实现层误当成用户入口，导致测试方向错误。

---

## 3. 分层模型

adapter 分为四层：

| 层 | 代表文件 | 责任 | 测试关注点 |
|---|---|---|---|
| 用户入口层 | `overlays/commands/*.md`、`overlays/skills/*/SKILL.md`、`overlays/agents/*.md` | 定义 Claude Code 中用户如何调用能力 | 文案是否引导 agent 走正确流程 |
| Hook 配置层 | `lib/hook_patch.py` | 维护 adapter 的 SessionStart 兼容配置，确保当前流程不安装 adapter hook | 安装后 hook 配置是否符合当前流程 |
| 执行层 | `overlays/scripts/*.py` | 执行 wiki 初始化、导入、更新、索引和 manifest 等文件操作 | 脚本行为是否正确、可组合 |
| 安装层 | `install.sh`、`manage.sh`、`verify.sh`、`release-check.sh` | 把 overlay 和 native skill patch 写入 Superpowers 插件目录 | 安装产物和 patch 是否完整 |

开发时可以分别验证各层，但最终必须回到“用户入口层 + 安装后的 Superpowers 环境”确认。

---

## 4. 测试原则

### 4.1 单脚本测试只能证明执行层正确

可以直接运行 Python 脚本做快速定位，例如：

```bash
python3 overlays/scripts/wiki_update_check.py --json
```

但这只能说明脚本本身可执行，不能说明用户在 Claude Code 中可以正确使用 `update-wiki` skill 或 native skill 集成路径。

直接脚本测试不能替代集成验收。

### 4.2 集成测试必须覆盖安装后的 command / skill 路径

当改动影响用户功能时，至少要验证：

1. adapter 能安装到 Superpowers 插件目录
2. `verify` 能检查到安装产物和 hook patch
3. 对应 command、skill 或 agent 文档仍会引导 agent 走正确流程
4. 在目标项目中能通过 Superpowers command / skill / agent 集成路径完成用户场景

例如修改 `update-wiki` 相关能力时，不应只验证某个底层脚本能写入文件；脚本测试只能覆盖候选输出、路径安全、格式校验和索引刷新等机械能力。

还应确认安装后 `update-wiki` skill 会引导 agent 先判断是否存在 durable knowledge，再读取 indexed wiki pages、做语义去重、判断目标归属、检查目标 leaf page 是否过大或语义混杂、必要时按 ownership 拆分页面、编辑 leaf wiki page 并刷新索引。

### 4.3 self-test 是底层回归，不是完整产品验收

`./manage.sh self-test /path/to/project` 和 `./manage.sh release-check /path/to/project` 很重要，但它们主要验证安装产物和脚本回归。

它们不能完全替代 Claude Code 中的真实 command / skill 使用路径。

### 4.4 新增能力时先定义用户入口

新增 adapter 能力时，先回答：

- 用户在 Claude Code 中输入什么？
- 这是 command、skill、hook，还是已有 command 的扩展？
- command / skill 如何指导 agent 分析、确认、执行和验收？
- 底层脚本只是执行层，还是被错误地暴露成了用户入口？

只有在用户入口明确后，再实现或调整 `overlays/scripts/*.py`。涉及 wiki 内容判断的 command / skill 应优先由 agent 主导；Python 只做 inventory、copy、validate、refresh、过大页面统计等机械操作，不应独立判断 durable knowledge、target ownership、拆分边界或 contract 内容。

Lanhu 集成必须保持可选：不能要求用户安装 lanhu-mcp 才能使用 adapter；Lanhu 产物只能作为用户确认的角色 PRD 输入写入用户项目根目录。Lanhu URL 场景必须先确认 `role: frontend | backend`，command、agent 和 native patch 的输入示例都要携带该字段；角色缺失或歧义时先询问，不读取或分析蓝湖。无子级页时写 `.lanhu/MM-DD-需求命名.md`；有子级页时写 `.lanhu/MM-DD-父级需求名称/`，其中包含继承目录需求名的父级 PRD、各子级 PRD 和 `index.md`。用户确认后再进入 Superpowers `brainstorming`。无子级页时单文件 `.md` 是角色 PRD 入口；有子级页时 `index.md` 是入口，继承目录需求名的父级 PRD 和各子级 PRD 是详细需求来源。显式 `pageId` 的 tree mode 必须在页面树白名单确认后逐页 full 分析，不能一次性请求父页加多个子页；Lanhu MCP 自带的输出格式说明只作为证据，不作为落盘格式。`role-prd/` 是 Lanhu 角色 PRD 提示词维护源；安装后的 `lanhu-requirements-analyst` 必须内嵌从 `role-prd/` 提炼出的模板结构，不能依赖运行时读取 adapter 仓库模板文件。Lanhu 产物不得包含测试点、测试用例、技术测试方案、前端组件拆分、后端接口推测、数据库影响、实现方案或代码文件影响；模板要求的角色验收标准允许，但只能用 Given / When / Then 描述产品行为。Lanhu 产物也不得写入 `.superpowers/wiki/`、`Referenced Project Wiki` 或 plan sidecar。修改 `role-prd/` 模板结构或 Lanhu tree mode 结构时，必须同步更新 agent、command、native patch、`verify.sh` 和 smoke 测试。

Graphify 集成也必须保持可选：不能要求用户安装 graphify 才能使用 adapter，不能让用户承担“是否启用 graphify”的判断。graphify 只能由 agent 在需求已确认、源码已初步探索但关系边界仍不确定时作为 candidate hints 查询；最终影响文件必须由 Superpowers 直接读当前源码验证。用户手动触发 graphify 应视为独立图谱查询或维护，不能绕过 Superpowers `brainstorming` / `writing-plans` / execution。

新增 bug 调试辅助能力时，bug 修复过程仍由 Superpowers `systematic-debugging` 负责，wiki 或 graphify 查询只能在 Phase 1 证据收窄后条件式触发，不能成为默认前置步骤，不能写 `.wiki-context.md`，不能更新 `.superpowers/wiki/`；复盘由 `break-loop` 负责，wiki 写入仍由 `update-wiki` 负责。

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

5. 如果影响 command / skill，回到 Claude Code 中用对应 command 或 skill 做真实路径验证。

### 5.2 修改 command 或 skill 文档时

1. 阅读对应脚本，确认 command 文档没有描述不存在的能力。
2. 安装 adapter：

```bash
./manage.sh install
./manage.sh verify
```

3. 在 Claude Code 中触发对应 command 或 Superpowers skill，例如：

```text
systematic-debugging → break-loop → update-wiki
update-wiki skill
/import-wiki
/init-wiki
brainstorming
writing-plans
```

4. 确认 agent 实际走的是文档指定的分析、wiki-researcher 选择和 plan 引用流程；`brainstorming` / `writing-plans` 不应要求调用 `wiki-progressive-disclosure`。
5. 如果修改 planning wiki 披露流程，确认 plan 的 `Referenced Project Wiki` 是轻量入口，并正确链接 `docs/superpowers/plans/<plan-stem>.wiki-context.md`，执行阶段会读取该 sidecar context。
6. 如果修改 `systematic-debugging` wiki 辅助流程，确认它不在 Phase 1 前调用 `wiki-researcher`，只在证据收窄后使用 `phase: debug` 和少量 `maxWikiPages`，wiki 线索必须继续用代码、日志、测试或复现验证，且调试阶段不写 `.wiki-context.md`、不运行 `update-wiki`。

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
bash tests/native-wiki-patch-smoke.sh <installed-superpowers-target>
bash tests/wiki-update-check-smoke.sh <installed-superpowers-target> /path/to/project
bash tests/wiki-index-graph-smoke.sh <installed-superpowers-target> /path/to/project
```

注意：这些测试需要传入安装后的 Superpowers target 和目标项目 root，不能只在 adapter 源码目录里假设路径成立。

---

## 7. 文档更新要求

当改变用户可见流程时，同步更新：

- `ADAPTER_USER_FLOW_CN.md`
- `README.md`
- 对应 `overlays/commands/*.md` 或 `overlays/skills/*/SKILL.md`

当改变测试或验收方式时，同步更新本文档和 `CLAUDE.md` 中的开发要求。

---

## 8. 判断一次改动是否完成

一次 adapter 功能改动只有在以下条件满足时才算完成：

- 底层脚本行为正确
- overlay command / skill / agent 能正确引导用户路径
- 如涉及 wiki 披露主流程，验收重点是 `wiki-researcher`、plan 中的轻量 `Referenced Project Wiki`，以及其链接的 `.wiki-context.md` 约束产物；`wiki-progressive-disclosure` 只是说明性 / fallback，不是默认路径成功标志
- 如涉及 `systematic-debugging` wiki 辅助，验收重点是证据收窄后才条件式调用 `phase: debug`、少量读取 wiki、不把 wiki 当 root cause evidence、不生成 `.wiki-context.md`、不更新 wiki
- 如涉及 Superpowers worktree 收尾流程，验收重点是安装后的 `using-git-worktrees` 是否把 origin metadata 写入 linked worktree private git-dir，以及 `finishing-a-development-branch` 是否基于该 metadata 提供合并回原始分支的选项；不要把该临时 metadata 写入 `plan.md`、`spec.md`、`.superpowers/` 或仓库工作区
- adapter 能成功安装到 Superpowers 插件目录
- `verify` / 相关测试通过
- 如影响用户流程，已在 Claude Code 等工具中从 command / skill 入口验证
- 文档没有把“直接运行 Python 脚本”描述成普通用户的主要使用方式