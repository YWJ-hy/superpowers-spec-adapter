# superpower-adapter 架构分析

本文记录当前 `superpower-adapter` 的架构。

## 一、总体结论

`superpower-adapter` 不改造 Superpowers 核心工作流，也不安装 SessionStart 上下文 hook。

它通过安装 overlay 文件和 patch Superpowers native skills，把项目级 `.superpowers/wiki/` 规范库接入 Superpowers 的两个编写阶段：

1. `brainstorming`：轻量披露相关项目规范。
2. `writing-plans`：正式选择项目规范，并写入 implementation plan 的 `Referenced Project Wiki`。

执行阶段不重新选择 wiki 页面，只消费 plan 中已经确认的 `Referenced Project Wiki`。

## 二、核心组成

### 1. Agent 层

- `overlays/agents/wiki-researcher.md`

`wiki-researcher` 是默认 wiki 选择入口。它从 `.superpowers/wiki/index.md` 开始，按 index 渐进读取相关 leaf wiki page，输出结构化 YAML 选择结果。

### 2. Skill 层

- `overlays/skills/wiki-progressive-disclosure/SKILL.md`
- `overlays/skills/update-wiki/SKILL.md`

`wiki-progressive-disclosure` 约束 agent 不要全量读取 `.superpowers/wiki/`，而是从入口 index 逐级下钻。`update-wiki` 在任务后审查 durable implementation knowledge，并由 agent 判断是否需要更新 leaf wiki page。

### 3. Command 层

- `overlays/commands/import-wiki.md`
- `overlays/commands/init-wiki.md`

这些是独立 adapter command，不串入 Superpowers completion verification。`update-wiki` 不再保留 command 入口。

### 4. Script 层

- `overlays/scripts/wiki-context.py`
- `overlays/scripts/wiki_common.py`
- `overlays/scripts/wiki_import.py`
- `overlays/scripts/init-wiki.py`
- `overlays/scripts/update-wiki.py`
- `overlays/scripts/wiki_update_check.py`
- `overlays/scripts/wiki_select_target.py`
- `overlays/scripts/wiki_apply_update.py`

脚本只作为 command / skill 和测试背后的执行层。`update-wiki` 相关脚本只做候选输出、路径安全、格式校验和索引刷新，不替 agent 做 durable knowledge 判断、语义去重或目标归属判断。

### 5. Patch / 安装层

- `lib/native_skill_patch.py`：patch Superpowers native skills。
- `lib/hook_patch.py`：维护 adapter SessionStart 兼容配置，确保当前流程不安装 adapter hook。
- `manifest.json`：声明安装文件和已删除文件。
- `install.sh` / `verify.sh` / `uninstall.sh`：执行安装、校验和卸载。

## 三、wiki 渐进式披露

读取规则：

1. 从 `.superpowers/wiki/index.md` 开始。
2. 只沿 index 指向的路径继续读取。
3. 先读子目录 `index.md`，再读必要 leaf wiki page。
4. 不全量扫描 `.superpowers/wiki/`，除非用户明确要求 full audit。

## 四、Superpowers native skill patch

### brainstorming

在提出方案前调用 `wiki-researcher`：

```yaml
task: <用户需求和当前理解>
phase: brainstorm
wikiRoot: .superpowers/wiki
maxWikiPages: 3
```

结果作为轻量项目 wiki 上下文参与设计。

### writing-plans

在拆分任务前调用 `wiki-researcher`：

```yaml
task: <已确认 Superpowers spec 或需求摘要>
phase: plan
wikiRoot: .superpowers/wiki
planPath: docs/superpowers/plans/<filename>.md
maxWikiPages: 5
```

plan 必须包含：

```markdown
## Referenced Project Wiki
```

并把每个 selected wiki page 的约束映射到具体 task。

### executing-plans / subagent-driven-development

执行阶段读取 plan 的 `Referenced Project Wiki`，不重新选择 wiki 页面。

## 五、安装清单约束

当前安装清单由 `manifest.json` 定义：

- `installedPaths` 声明需要写入 Superpowers 插件目录的 agent、command、skill 和 script overlay。
- `optionalPatchedPaths` 声明安装器会维护的 Superpowers native skill 和 hook 配置文件。
- `removedPaths` 声明安装时需要确保不存在的 adapter 管理文件，避免安装目录残留非当前流程入口。

## 六、最终架构定义

`superpower-adapter` 是一个面向 Superpowers 的项目 wiki 渐进披露 overlay。它通过 `wiki-researcher` 和 native skill patch，在 spec / plan 编写期选择并固化项目 wiki 约束；执行期只读取 plan 中的 `Referenced Project Wiki`。
