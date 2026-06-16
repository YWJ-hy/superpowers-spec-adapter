# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 必读文档

修改 adapter 功能前，必须先阅读：

1. `ADAPTER_DEVELOPMENT_CN.md`：adapter 开发和测试原则
2. `ADAPTER_USER_FLOW_CN.md`：Superpowers + adapter 的最终用户流程
3. 与当前改动相关的 `overlays/skills/*/SKILL.md`

特别注意：adapter 的最终验收应以 Claude Code 等工具中通过 Superpowers skill 发起的集成路径为准，不能只以直接执行 Python 脚本成功为准。

## 常用命令

在 adapter 源码目录运行：

```bash
./manage.sh install
./manage.sh verify
./manage.sh status
./manage.sh bootstrap-wiki /path/to/project --template standard
./manage.sh init-wiki /path/to/project "optional focus"
./manage.sh export-wiki-skills /path/to/wiki-repo
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
bash tests/export-wiki-skills-smoke.sh
```

发布前总检查：

```bash
./manage.sh release-check /path/to/project
```

## 架构概览

本仓库是 Superpowers 的 adapter 源码，不是业务项目代码。adapter 通过安装 overlay 来增强用户已安装的 Superpowers Claude Code 插件。

主要分层：

- - `overlays/agents/`：安装到 Superpowers 的 subagent，例如 `wiki-researcher`，负责渐进式选择相关项目 wiki 页面。
- `overlays/skills/`：安装到 Superpowers 的 skill，负责显式入口（如 Lanhu/import/init/shared-wiki MCP）、任务后 update-wiki 审查，以及把可复用实践固化/转换为分层技能包并登记 wiki 发现卡片的 `scaffold-practice-skill`。
- `overlays/scripts/`：skill 背后的 Python 执行层，负责 wiki 初始化、导入、更新、索引和 manifest 等文件操作。其中 `wiki_generate_section_index.py` / `wiki_update_check.py` / `wiki_migrate_helper.py` 支持 `--wiki-dir`，把指定目录当作 wiki 根直接处理（仓库根即 wiki 的布局），不依赖 `.superpowers/wiki/` 嵌套。
- `overlays/wiki-repo-skills/`：独立 wiki 仓库（仓库根即 wiki）用的 repo-local skill 源码（`update-wiki` 作者侧增量维护、`migrate-wiki` section 化+图谱）。不安装进 Superpowers，由 `export-wiki-skills` 连同 vendored 脚本闭包钉版本写入目标仓库 `.claude/`，运行时零依赖 adapter，且只改不提交。
- `lib/`：adapter 自身的安装、manifest、hook 配置维护、native skill patch、目标 Superpowers 目录解析逻辑；`export_wiki_skills.py` 是 `export-wiki-skills` 的导出引擎（含 marker 防覆盖与脚本哈希 manifest）。
- `wiki-template/`：bootstrap 到目标项目 `.superpowers/wiki/` 的标准模板。
- `tests/`：面向安装后 Superpowers target 和目标项目 root 的 smoke / regression 测试。
- 根目录 `manage.sh`：统一入口，转发 install、verify、bootstrap-wiki、export-wiki-skills、doctor、self-test、release-check 等操作。

## 用户流程模型

Superpowers 是主工作流，adapter 只增强 Superpowers：

1. 用户安装 adapter，adapter 把 agent、skill、script overlay 写入已安装的 Superpowers 插件目录，并维护 hook 兼容配置。
2. 用户在目标项目 bootstrap `.superpowers/wiki/`。
3. 用户在 Claude Code 等工具中通过 `init-wiki`、`import-wiki` skills 初始化或导入项目 wiki；如有蓝湖链接，显式调用 `lanhu-requirements` skill 生成并确认 `.lanhu/.../index.md` 证据包。
4. Superpowers `brainstorming` 通过 `wiki-researcher` 轻量披露相关项目 wiki 页面，`writing-plans` 正式选择并写入 `Referenced Project Wiki`；source-of-truth 仅在配置或用户显式要求时运行。
5. 执行阶段只消费 plan 中的 `Referenced Project Wiki` 和已链接的约束 sidecar，任务完成后如果产生 durable implementation knowledge，由 `update-wiki` skill 审查并回写 `.superpowers/wiki/` 或通过授权的 shared-wiki MCP PR 路径处理 `.shared-superpowers/wiki/`；其中可复用的工作流程/流程性知识由 `update-wiki` 移交 `scaffold-practice-skill` 固化为 `.claude/skills/<name>/` 分层技能包（薄 `SKILL.md` 路由 + 按需文件的开放集合，convert 非破坏），并在 `guides/skills.md` 登记发现卡片，供下次 `wiki-researcher` 选中绑定「必须使用 skill X」。wiki 单向关联 skill，skill 不反向硬编码 wiki 路径。

不要把 `python3 superpowers/scripts/*.py` 描述成普通用户的主要入口；它们是 skill / agent 的执行层。

## 开发和验收要求

- 改动用户可见行为时，同步检查或更新 `ADAPTER_USER_FLOW_CN.md`、相关 skill overlay，以及 `README.md` 中的入口说明。
- 改动测试原则或验收方式时，同步更新 `ADAPTER_DEVELOPMENT_CN.md`。
- 脚本级测试只能证明执行层正确，不能替代安装后 skill 集成路径验证。
- 修改 agent、hook 配置或安装逻辑后，至少运行 `./manage.sh install`、`./manage.sh verify`，并对目标项目运行 `./manage.sh release-check /path/to/project`。
- 修改 skill 后，应安装 adapter 并在 Claude Code 中从对应 skill 入口验证用户路径。
- wiki 写入策略由 root-specific settings 控制：`.superpowers/settings.json` 控制 project wiki，`.shared-superpowers/settings.json` 控制 shared wiki；`wiki.updateAuthorization.updateExistingPage` 默认 `skip`，`createNewDocument` 默认 `ask`，允许 `skip` / `ask` / `refuse`。执行层脚本的 `--authorized-update` / `--authorized-create` 只表示 skill 已取得用户授权，不能绕过 `refuse`。
- GitHub-backed shared wiki 的连接是**每项目**的：消费项目在自己的 `.shared-superpowers/settings.json` 的 `wiki.sharedMcp`（`repoUrl`/`baseBranch`/`remote`/`wikiRoot`/`displayRoot`/`draftPr`）声明连哪个 shared wiki。MCP server 注册为**一份通用、不含 repo 的注册**，启动时读 Claude Code 注入的 `CLAUDE_PROJECT_DIR`，从该项目 settings 自我配置（`mcp/shared-wiki/src/config.ts`）。没有声明的项目 fail-closed（无 MCP shared wiki）。注意区分两个同名文件：消费项目的 `wiki.sharedMcp` 是“连接”，shared wiki 仓库内的 `.shared-superpowers/settings.json` 才是该 wiki 的“治理”（server 从 clone 读，`src/wiki/policy.ts`）。`cacheDir` 是机器本地项，不进项目配置；`SHARED_WIKI_MCP_*` 环境变量仅供测试/全局覆盖，注册里设它会覆盖每项目设置。`wiki-context` sidecar 在选用 github_mcp 时记录顶层 `sharedWiki` 身份（`repoUrl`+`revision`），执行层 reread 前据此检测换绑漂移。`./manage.sh doctor` 会报告本项目的 `wiki.sharedMcp` 绑定状态。
- shared wiki 必须保持中性、可迁移，不能包含当前系统特有标识、内部 URL、环境名、本地路径、部署实例标识或当前系统专属业务规则；这些内容应留在 project wiki，或由 agent 改写为中性术语。`.shared-superpowers/settings.json` 可用 `wiki.sharedNeutrality.blockedTerms` / `blockedPatterns` 配置已知系统标识的机械拒绝防线。