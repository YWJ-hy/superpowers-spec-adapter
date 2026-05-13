# Shared Wiki MCP 待补充测试清单

以下测试点本轮尚未完整执行，后续重新验收时按需补跑。

## 已知前置条件

真实 GitHub PR 流程需要本机安装并登录 GitHub CLI：

```bash
brew install gh
gh auth login
```

确认登录状态：

```bash
gh auth status
```

测试仓库：

```text
https://github.com/YWJ-hy/shared-wiki.git
```

当前远程默认分支检测结果为：

```text
master
```

因此测试配置中的 `baseBranch` 应使用 `master`，除非后续仓库默认分支已改为其他名称。

## 尚未完成的测试点

### 1. 真实 GitHub draft PR 创建测试

本轮未执行原因：本机缺少 `gh`，无法调用 `gh pr create`。

待测目标：

- 使用 `shared_wiki_create_patch_pr` 对 `https://github.com/YWJ-hy/shared-wiki.git` 创建测试 branch。
- 创建 GitHub draft PR。
- 确认返回结果包含：
  - branch name
  - commit SHA
  - PR URL
  - changed files
  - validation summary
- 确认 MCP 不会自动 merge PR。

注意：测试 PR 创建后应人工检查内容，并手动关闭或处理测试 PR。

### 2. Claude Code MCP 真实工具调用路径

待测目标：

1. 复制 `mcp/shared-wiki/` 到本地独立目录。
2. 在复制后的目录运行：

```bash
npm install
npm run build
```

3. 配置 `shared-wiki-mcp.config.json`：

```json
{
  "repoUrl": "https://github.com/YWJ-hy/shared-wiki.git",
  "baseBranch": "master",
  "remote": "origin",
  "wikiRoot": ".",
  "displayRoot": ".shared-superpowers/wiki",
  "cacheDir": "~/.cache/superpower-adapter/shared-wiki-mcp",
  "draftPr": true
}
```

4. 在 Claude Code MCP 配置中启用该 server。
5. 在 Claude Code 中确认以下 MCP tools 可用并能正常返回：
   - `shared_wiki_status`
   - `shared_wiki_tree`
   - `shared_wiki_read`
   - `shared_wiki_search`
   - `shared_wiki_validate_patch`
   - `shared_wiki_create_patch_pr`

### 3. `/shared-wiki-mcp` command 集成路径

待测目标：

- 安装 adapter 后，在 Claude Code 中触发：

```text
/shared-wiki-mcp
```

- 确认 command 文档会引导 agent：
  - 先调用 `shared_wiki_status`
  - 再读取 tree/read/search
  - 写入前先做 durable knowledge、语义去重、shared ownership、中立化和授权判断
  - 只通过 MCP 创建 branch + PR
  - 不声称 PR 已 merge 或 shared wiki 已发布

### 4. `update-wiki` + shared-wiki MCP 路径

待测目标：

- 构造一个跨项目可复用的 durable knowledge 候选。
- 触发 `update-wiki` skill。
- 确认 skill 在 GitHub-backed shared wiki 场景下：
  - 不直接编辑本地 `.shared-superpowers/wiki/`
  - 使用 MCP read/search 检查已有 indexed shared wiki
  - 准备 neutral unified diff
  - 调用 `shared_wiki_validate_patch`
  - 调用 `shared_wiki_create_patch_pr`
  - 最终只报告 PR URL / branch / validation summary

### 5. 完整 adapter self-test

本轮只单独跑了 MCP package tests、MCP smoke tests 和 `manage.sh install && manage.sh verify`。

待测命令：

```bash
./manage.sh self-test /path/to/project
```

期望：

- 原有 adapter smoke tests 通过。
- 新增 deterministic MCP smoke tests 通过：
  - `tests/shared-wiki-mcp-policy-smoke.sh`
  - `tests/shared-wiki-mcp-pr-smoke.sh`

### 6. 完整 release-check

待测命令：

```bash
./manage.sh release-check /path/to/project
```

期望：

- install / verify / doctor / self-test / export-manifest 全链路通过。
- 新增 `/shared-wiki-mcp` command 已被安装和 verify 覆盖。

## 本轮已通过的测试记录

本轮已经通过：

```bash
npm test --prefix mcp/shared-wiki
npm run build --prefix mcp/shared-wiki
bash tests/shared-wiki-mcp-copyable-smoke.sh
bash tests/shared-wiki-mcp-policy-smoke.sh
bash tests/shared-wiki-mcp-pr-smoke.sh
./manage.sh install
./manage.sh verify
```

并已做只读远程检查：

```bash
git ls-remote --heads https://github.com/YWJ-hy/shared-wiki.git
```

结果显示远程存在 `refs/heads/master`。
