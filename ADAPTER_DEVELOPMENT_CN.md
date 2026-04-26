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
   - `overlays/commands/update-spec.md`
   - `overlays/commands/init-spec.md`
   - `overlays/commands/import-spec.md`
   - `overlays/agents/spec-researcher.md`，这是正常流程的 spec 选择入口
   - `overlays/skills/spec-progressive-disclosure/SKILL.md`，这是说明性 / fallback 规则文档

如果只读 `overlays/scripts/*.py`，容易把实现层误当成用户入口，导致测试方向错误。

---

## 3. 分层模型

adapter 分为四层：

| 层 | 代表文件 | 责任 | 测试关注点 |
|---|---|---|---|
| 用户入口层 | `overlays/commands/*.md`、`overlays/skills/*/SKILL.md`、`overlays/agents/*.md` | 定义 Claude Code 中用户如何调用能力 | 文案是否引导 agent 走正确流程 |
| Hook 配置层 | `lib/hook_patch.py` | 维护 adapter 的 SessionStart 兼容配置，确保当前流程不安装 adapter hook | 安装后 hook 配置是否符合当前流程 |
| 执行层 | `overlays/scripts/*.py` | 执行 spec 初始化、导入、更新、索引和 manifest 等文件操作 | 脚本行为是否正确、可组合 |
| 安装层 | `install.sh`、`manage.sh`、`verify.sh`、`release-check.sh` | 把 overlay 和 native skill patch 写入 Superpowers 插件目录 | 安装产物和 patch 是否完整 |

开发时可以分别验证各层，但最终必须回到“用户入口层 + 安装后的 Superpowers 环境”确认。

---

## 4. 测试原则

### 4.1 单脚本测试只能证明执行层正确

可以直接运行 Python 脚本做快速定位，例如：

```bash
python3 overlays/scripts/spec_update_check.py --summary "example"
```

但这只能说明脚本本身可执行，不能说明用户在 Claude Code 中可以正确使用 `/update-spec` 或 native skill 集成路径。

直接脚本测试不能替代集成验收。

### 4.2 集成测试必须覆盖安装后的 command / skill 路径

当改动影响用户功能时，至少要验证：

1. adapter 能安装到 Superpowers 插件目录
2. `verify` 能检查到安装产物和 hook patch
3. 对应 command、skill 或 agent 文档仍会引导 agent 走正确流程
4. 在目标项目中能通过 Superpowers command / skill / agent 集成路径完成用户场景

例如修改 `update-spec` 相关能力时，不应只验证：

```bash
python3 overlays/scripts/spec_update_run.py ...
```

还应确认安装后 `/update-spec` 的 command 文档、分析流程、去重要求、目标选择和索引刷新链路仍然一致。

### 4.3 self-test 是底层回归，不是完整产品验收

`./manage.sh self-test /path/to/project` 和 `./manage.sh release-check /path/to/project` 很重要，但它们主要验证安装产物和脚本回归。

它们不能完全替代 Claude Code 中的真实 command / skill 使用路径。

### 4.4 新增能力时先定义用户入口

新增 adapter 能力时，先回答：

- 用户在 Claude Code 中输入什么？
- 这是 command、skill、hook，还是已有 command 的扩展？
- command / skill 如何指导 agent 分析、确认、执行和验收？
- 底层脚本只是执行层，还是被错误地暴露成了用户入口？

只有在用户入口明确后，再实现或调整 `overlays/scripts/*.py`。

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

5. 如果影响 command / skill，回到 Claude Code 中用对应 slash command 做真实路径验证。

### 5.2 修改 command 或 skill 文档时

1. 阅读对应脚本，确认 command 文档没有描述不存在的能力。
2. 安装 adapter：

```bash
./manage.sh install
./manage.sh verify
```

3. 在 Claude Code 中触发对应 command 或 Superpowers skill，例如：

```text
/update-spec
/import-spec
/init-spec
brainstorming
writing-plans
```

4. 确认 agent 实际走的是文档指定的分析、spec-researcher 选择和 plan 引用流程；`brainstorming` / `writing-plans` 不应要求调用 `spec-progressive-disclosure`。

### 5.3 修改 hook 配置或安装逻辑时

1. 运行：

```bash
./manage.sh install
./manage.sh verify
./manage.sh status
```

2. 在目标项目新开 Claude Code 会话。
3. 确认当前流程不安装 adapter SessionStart hook；主流程应通过 `spec-researcher` 和 `Referenced Project Specs` 承载规范引用。
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
./manage.sh bootstrap-spec /path/to/project --template standard
./manage.sh init-spec /path/to/project "optional focus"
./manage.sh doctor /path/to/project
./manage.sh self-test /path/to/project
./manage.sh release-check /path/to/project
```

单个 smoke 测试示例：

```bash
bash tests/native-skill-patch-smoke.sh <installed-superpowers-target>
bash tests/spec-update-check-smoke.sh <installed-superpowers-target> /path/to/project
bash tests/spec-index-graph-smoke.sh <installed-superpowers-target> /path/to/project
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
- 如涉及 spec 披露主流程，验收重点是 `spec-researcher` 和 plan 中的 `Referenced Project Specs`；`spec-progressive-disclosure` 只是说明性 / fallback，不是默认路径成功标志
- adapter 能成功安装到 Superpowers 插件目录
- `verify` / 相关测试通过
- 如影响用户流程，已在 Claude Code 等工具中从 command / skill 入口验证
- 文档没有把“直接运行 Python 脚本”描述成普通用户的主要使用方式