# Shared Wiki MCP

把这个目录复制到本机任意位置，配置 shared-wiki Git 仓库后，就可以作为 MCP server 启动。server 会读取 indexed shared wiki 页面，也可以把 wiki 修改通过 branch + commit + GitHub PR 的方式提交。

GitHub 仓库是 shared wiki 的事实源。这个 MCP server 不会 merge PR，也不会判断某条知识是否应该进入 shared wiki；这些语义判断必须先由调用它的 agent 或 `update-wiki` skill 完成。

## 安装

```bash
npm install
npm run build
cp examples/shared-wiki-mcp.config.example.json shared-wiki-mcp.config.json
```

编辑 `shared-wiki-mcp.config.json`：

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

## Claude Code MCP 配置

使用 build 后 server 的绝对路径：

```json
{
  "mcpServers": {
    "shared-wiki": {
      "command": "node",
      "args": ["/absolute/path/to/shared-wiki-mcp/dist/index.js"],
      "env": {
        "SHARED_WIKI_MCP_CONFIG": "/absolute/path/to/shared-wiki-mcp/shared-wiki-mcp.config.json"
      }
    }
  }
}
```

## 工具列表

- `shared_wiki_status`：检查配置、clone 状态、策略、工具可用性和 wiki 校验摘要。
- `shared_wiki_tree`：返回基于 `index.md` 链接图的 shared wiki 树。
- `shared_wiki_read`：读取一个已 indexed 的 markdown 页面。
- `shared_wiki_search`：在已 indexed 的 markdown 页面中做有界搜索并返回片段。
- `shared_wiki_validate_patch`：校验 unified diff，不 push、不创建 PR。
- `shared_wiki_create_patch_pr`：把已校验 patch 应用到新 branch，push 后创建 GitHub PR。

## 写入策略

server 会从 clone 后的仓库按以下顺序读取 wiki 策略：

1. `<repo>/<wikiRoot>/.shared-superpowers/settings.json`
2. `<repo>/.shared-superpowers/settings.json`
3. `<repo>/settings.json`
4. 默认值

策略格式：

```json
{
  "wiki": {
    "updateAuthorization": {
      "updateExistingPage": "skip",
      "createNewDocument": "ask"
    },
    "sharedNeutrality": {
      "blockedTerms": [],
      "blockedPatterns": []
    }
  }
}
```

`ask` 要求 MCP 调用方传入 `authorizedCreate` 或 `authorizedUpdate`。`refuse` 不能通过授权绕过。`sharedNeutrality` 中的词和正则只是机械防线；调用方在提交 patch 前仍然必须先把项目专属标识改写成中性、可迁移的表达。

## GitHub PR 要求

`shared_wiki_create_patch_pr` 需要：

- `git`
- GitHub CLI `gh`
- `gh auth status` 对目标仓库有效
- 有 push branch 和创建 PR 的权限

这个工具只创建 branch 和 PR，永远不会 merge。
