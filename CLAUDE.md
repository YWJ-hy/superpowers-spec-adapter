# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 必读文档

修改 adapter 功能前，必须先阅读：

1. `ADAPTER_DEVELOPMENT_CN.md`：adapter 开发和测试原则
2. `ADAPTER_USER_FLOW_CN.md`：Superpowers + adapter 的最终用户流程
3. 与当前改动相关的 `overlays/commands/*.md` 或 `overlays/skills/*/SKILL.md`

特别注意：adapter 的最终验收应以 Claude Code 等工具中通过 Superpowers command / skill 发起的集成路径为准，不能只以直接执行 Python 脚本成功为准。

## 常用命令

在 adapter 源码目录运行：

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

单个 smoke / regression 测试：

```bash
bash tests/native-wiki-patch-smoke.sh <installed-superpowers-target>
bash tests/wiki-update-check-smoke.sh <installed-superpowers-target> /path/to/project
bash tests/wiki-index-graph-smoke.sh <installed-superpowers-target> /path/to/project
bash tests/bootstrap-wiki-template-import.sh /path/to/project
```

发布前总检查：

```bash
./manage.sh release-check /path/to/project
```

## 架构概览

本仓库是 Superpowers 的 adapter 源码，不是业务项目代码。adapter 通过安装 overlay 来增强用户已安装的 Superpowers Claude Code 插件。

主要分层：

- `overlays/commands/`：安装到 Superpowers 的 slash command 文档，用于显式触发 init / import 等 adapter 能力。
- `overlays/agents/`：安装到 Superpowers 的 subagent，例如 `wiki-researcher`，负责渐进式选择相关项目 wiki 页面。
- `overlays/skills/`：安装到 Superpowers 的 skill，负责渐进式读取 wiki 和任务后 update-wiki 审查。
- `overlays/scripts/`：command / skill 背后的 Python 执行层，负责 wiki 初始化、导入、更新、索引和 manifest 等文件操作。
- `lib/`：adapter 自身的安装、manifest、hook 配置维护、native skill patch、目标 Superpowers 目录解析逻辑。
- `wiki-template/`：bootstrap 到目标项目 `.superpowers/wiki/` 的标准模板。
- `tests/`：面向安装后 Superpowers target 和目标项目 root 的 smoke / regression 测试。
- 根目录 `manage.sh`：统一入口，转发 install、verify、bootstrap-wiki、doctor、self-test、release-check 等操作。

## 用户流程模型

Superpowers 是主工作流，adapter 只增强 Superpowers：

1. 用户安装 adapter，adapter 把 agent、command、skill、script overlay 写入已安装的 Superpowers 插件目录，并维护 hook 兼容配置。
2. 用户在目标项目 bootstrap `.superpowers/wiki/`。
3. 用户在 Claude Code 等工具中通过 `/init-wiki`、`/import-wiki` 初始化或导入项目 wiki。
4. Superpowers `brainstorming` 通过 `wiki-researcher` 轻量披露相关项目 wiki 页面，`writing-plans` 正式选择并写入 `Referenced Project Wiki`。
5. 执行阶段只消费 plan 中的 `Referenced Project Wiki`，任务完成后如果产生 durable implementation knowledge，由 `update-wiki` skill 审查并回写 `.superpowers/wiki/`。

不要把 `python3 superpowers/scripts/*.py` 描述成普通用户的主要入口；它们是 command / skill / agent 的执行层。

## 开发和验收要求

- 改动用户可见行为时，同步检查或更新 `ADAPTER_USER_FLOW_CN.md`、相关 command / skill overlay，以及 `README.md` 中的入口说明。
- 改动测试原则或验收方式时，同步更新 `ADAPTER_DEVELOPMENT_CN.md`。
- 脚本级测试只能证明执行层正确，不能替代安装后 command / skill 集成路径验证。
- 修改 agent、hook 配置或安装逻辑后，至少运行 `./manage.sh install`、`./manage.sh verify`，并对目标项目运行 `./manage.sh release-check /path/to/project`。
- 修改 command / skill 后，应安装 adapter 并在 Claude Code 中从对应 command 或 skill 入口验证用户路径。