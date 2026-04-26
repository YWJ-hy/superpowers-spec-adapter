# superpower-adapter 架构分析

本文记录当前 `superpower-adapter` 的架构。

## 一、总体结论

`superpower-adapter` 不改造 Superpowers 核心工作流，也不安装 SessionStart 上下文 hook。

它通过安装 overlay 文件和 patch Superpowers native skills，把项目级 `.superpowers/spec/` 规范库接入 Superpowers 的两个编写阶段：

1. `brainstorming`：轻量披露相关项目规范。
2. `writing-plans`：正式选择项目规范，并写入 implementation plan 的 `Referenced Project Specs`。

执行阶段不重新选择 spec，只消费 plan 中已经确认的 `Referenced Project Specs`。

## 二、核心组成

### 1. Agent 层

- `overlays/agents/spec-researcher.md`

`spec-researcher` 是默认 spec 选择入口。它从 `.superpowers/spec/index.md` 开始，按 index 渐进读取相关 leaf spec，输出结构化 YAML 选择结果。

### 2. Skill 层

- `overlays/skills/spec-progressive-disclosure/SKILL.md`

该 skill 约束 agent 不要全量读取 `.superpowers/spec/`，而是从入口 index 逐级下钻。

### 3. Command 层

- `overlays/commands/import-spec.md`
- `overlays/commands/init-spec.md`
- `overlays/commands/update-spec.md`

这些都是独立 adapter command，不串入 Superpowers completion verification。

### 4. Script 层

- `overlays/scripts/spec-context.py`
- `overlays/scripts/spec_common.py`
- `overlays/scripts/spec_import.py`
- `overlays/scripts/init-spec.py`
- `overlays/scripts/update-spec.py`
- `overlays/scripts/spec_update_check.py`
- `overlays/scripts/spec_select_target.py`
- `overlays/scripts/spec_update_prompt.py`
- `overlays/scripts/spec_update_template.py`
- `overlays/scripts/spec_apply_update.py`
- `overlays/scripts/spec_update_run.py`

脚本只作为 command 和测试背后的执行层。

### 5. Patch / 安装层

- `lib/native_skill_patch.py`：patch Superpowers native skills。
- `lib/hook_patch.py`：维护 adapter SessionStart 兼容配置，确保当前流程不安装 adapter hook。
- `manifest.json`：声明安装文件和已删除文件。
- `install.sh` / `verify.sh` / `uninstall.sh`：执行安装、校验和卸载。

## 三、spec 渐进式披露

读取规则：

1. 从 `.superpowers/spec/index.md` 开始。
2. 只沿 index 指向的路径继续读取。
3. 先读子目录 `index.md`，再读必要 leaf spec。
4. 不全量扫描 `.superpowers/spec/`，除非用户明确要求 full audit。

## 四、Superpowers native skill patch

### brainstorming

在提出方案前调用 `spec-researcher`：

```yaml
task: <用户需求和当前理解>
phase: brainstorm
specRoot: .superpowers/spec
maxSpecs: 3
```

结果作为轻量项目规范上下文参与设计。

### writing-plans

在拆分任务前调用 `spec-researcher`：

```yaml
task: <已确认 Superpowers spec 或需求摘要>
phase: plan
specRoot: .superpowers/spec
planPath: docs/superpowers/plans/<filename>.md
maxSpecs: 5
```

plan 必须包含：

```markdown
## Referenced Project Specs
```

并把每个 selected spec 的约束映射到具体 task。

### executing-plans / subagent-driven-development

执行阶段读取 plan 的 `Referenced Project Specs`，不重新选择 spec。

## 五、安装清单约束

当前安装清单由 `manifest.json` 定义：

- `installedPaths` 声明需要写入 Superpowers 插件目录的 agent、command、skill 和 script overlay。
- `optionalPatchedPaths` 声明安装器会维护的 Superpowers native skill 和 hook 配置文件。
- `removedPaths` 声明安装时需要确保不存在的 adapter 管理文件，避免安装目录残留非当前流程入口。

## 六、最终架构定义

`superpower-adapter` 是一个面向 Superpowers 的项目规范渐进披露 overlay。它通过 `spec-researcher` 和 native skill patch，在 spec / plan 编写期选择并固化项目规范；执行期只读取 plan 中的 `Referenced Project Specs`。
