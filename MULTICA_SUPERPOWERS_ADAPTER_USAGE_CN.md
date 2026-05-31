# Multica 中使用 Superpowers + adapter 团队指南

这是一份给团队使用者看的指南。它说明：不会 Multica 的成员如何理解基本概念、如何在 Multica 里发起 Superpowers + adapter 流程、触发后会发生什么、如何查看进度、如何补充信息和重跑。

本文不要求你理解 adapter 的内部实现。日常使用时，你只需要会创建 Multica issue、选择 assignee、查看 issue runs、在 issue 下评论补充信息。

---

## 1. 先理解几个 Multica 概念

如果你第一次使用 Multica，先记住这几个词：

| 概念 | 可以理解成 | 在本流程中的作用 |
|---|---|---|
| Workspace | 团队工作区 | 团队的 agent、issue、squad、skill 都在这里 |
| Issue | 一张任务卡 | 你通过 issue 发起需求、规划、执行、调试或 wiki 更新 |
| Agent | AI 队友 | 每个 `superpowers-*` agent 负责一个明确阶段 |
| Squad | AI 小队 | `superpowers-runtime-squad` 用来接收完整流程入口或需要分派的任务 |
| Skill | agent 的能力包 | `superpowers-adapter` skill pack 让 agent 知道 Superpowers + adapter 的规则 |
| Run / Task run | agent 执行记录 | issue 被 assign 后，Multica daemon 会创建一次 run |
| Comment | issue 评论 | 人补充信息、确认方向，agent 输出结果和 handoff |
| Rerun | 重新执行 | 信息补齐后，让同一个 issue 再跑一次 |
| Cancel | 取消执行 | 如果任务跑偏或输入错了，可以取消当前 run |

最重要的是：**在 Multica 中，Superpowers + adapter 不是一个 agent 一口气跑完，而是多个可见的 role agent 分阶段执行。**

---

## 2. 使用前需要确认什么

普通成员使用前，只需要确认这几件事：

1. 团队管理员已经在 Multica workspace 中安装好了 Superpowers + adapter 环境。
2. 你要操作的代码仓库路径是准确的，且 Multica 的 Claude Code runtime 能访问它。
3. 你知道本次要发起的是哪类任务：新功能、从蓝湖整理需求、写计划、执行计划、修 bug、更新 wiki、准备 shared wiki 发布等。
4. 如果任务涉及改代码、commit、push、PR、发布 shared wiki，需要在 issue 中明确授权；默认流程不会做这些外部副作用。

你不需要自己安装 Superpowers 插件，也不需要运行 adapter 仓库里的 Python 脚本。

---

## 3. 团队中有哪些 Superpowers agent

管理员配置完成后，workspace 中会有这些常用 agent：

| Agent / Squad | 负责什么 |
|---|---|
| `superpowers-runtime-squad` | 完整流程入口，小队分派 |
| `superpowers-wiki-researcher` | 查找和选择相关 project/shared wiki |
| `superpowers-brainstorming-agent` | 需求讨论、方案探索、产出 spec 草稿 |
| `superpowers-spec-document-reviewer` | 审查 spec 文档是否清晰、完整、可执行 |
| `superpowers-planning-agent` | 根据已确认 spec 写 draft/final implementation plan |
| `superpowers-source-of-truth-verifier` | 在 draft plan 后校验接口、类型、schema、权限、设计 token 等配置化真实源假设 |
| `superpowers-plan-document-reviewer` | 审查 final plan 是否可执行、任务拆分是否合理，并确认 source-truth 结果被正确消费 |
| `superpowers-implementer` | 按已批准 plan 实现 |
| `superpowers-spec-compliance-reviewer` | 检查实现是否符合 spec |
| `superpowers-code-quality-reviewer` | 检查代码质量、维护性和局部设计问题 |
| `superpowers-code-reviewer` | 最终代码审查 |
| `superpowers-finisher` | 开发分支收尾、合并/PR readiness 检查 |
| `superpowers-debugger` | 系统化调试 bug |
| `superpowers-break-loop-analyst` | 重复失败或调试循环后的复盘 |
| `superpowers-wiki-curator` | 判断并更新 project/shared wiki |
| `superpowers-shared-wiki-publisher` | shared wiki 发布 readiness / PR preparation |
| `superpowers-lanhu-frontend-requirements-analyst` | 蓝湖前端统一 `frontend-prd/` 需求输入包 |
| `superpowers-lanhu-backend-requirements-analyst` | 蓝湖后端需求证据包 |

日常使用时，如果你不确定该 assign 给谁，优先 assign 给：

```text
superpowers-runtime-squad
```

如果你只想跑某个明确阶段，比如只写计划或只修 bug，也可以直接 assign 给对应 role agent。

---

## 4. 最常用的触发方式：创建一个 Multica issue

### 4.1 在 Multica UI 中触发

适合大多数团队成员。

步骤：

1. 打开 Multica workspace。
2. 进入团队项目或 issue 看板。
3. 新建 issue。
4. 按本文后面的模板填写 issue 标题和正文。
5. Assign 给 `superpowers-runtime-squad`，或 assign 给某个具体 `superpowers-*` role agent。
6. 保存 issue。
7. Multica daemon 会自动为这个 assignment 创建 task run。
8. 在 issue 页面查看 run 状态和 agent 评论。

建议标题格式：

```text
[Superpowers] <任务类型>：<一句话目标>
```

例如：

```text
[Superpowers] 新功能：订单列表支持批量导出
[Superpowers] Bug 调试：支付回调偶发重复入账
[Superpowers] Wiki 更新：沉淀订单状态机约束
```

### 4.2 用 CLI 触发

适合熟悉命令行的人，或者由管理员帮团队创建入口 issue。

示例：创建一个 writing-plans issue：

```bash
./manage.sh multica-bootstrap create-issue \
  --target-repo /path/to/project \
  --issue-template writing-plans \
  --requirements-path /path/to/project/docs/prd.md \
  --dry-run
```

确认 issue body 没问题后，把 `--dry-run` 换成 `--apply`。

日常团队成员不一定需要会这条命令；会在 UI 中创建 issue 就够了。

---

## 5. Issue 正文应该怎么写

每个 Superpowers + adapter issue 最好都包含这些字段：

```markdown
Target repo: /path/to/project
Issue template: <模板 id>
Entrypoint: <入口说明，可选；不懂可以省略>

Background:
- 为什么要做这件事

Inputs:
- 需求文档：...
- Spec：...
- Plan：...
- Debug evidence：...
- 蓝湖链接：...

Expected output:
- 希望这个阶段产出什么

Safety:
- 默认不要 commit / push / 创建 PR / 发布 shared wiki
- 如果需要外部副作用，需要明确写授权范围
```

最关键的是：

- `Target repo:` 必须准确。
- `Issue template:` 要选对。
- 输入材料路径或链接要写清楚。
- 需要用户确认的地方，不要默认授权 agent 直接继续。

### 5.1 回复语言

Agent 会从用户写的 issue 标题、正文和后续评论中推导用户偏好的语言。用户用中文描述，agent 给用户看的评论、问题、总结、review 结论和 handoff 应该用中文；用户用英文描述，则用英文。代码标识符、命令、路径、日志、schema 字段和引用证据保持原文。

如果一个 issue 中中英文混用，agent 会优先使用最新用户评论中的主导语言。团队成员也可以在 issue 中显式写：

```markdown
Response language: 中文
```

或：

```markdown
Response language: English
```

---

## 6. 常用 Issue template 怎么选

| 你想做什么 | Issue template | 推荐 assignee |
|---|---|---|
| 只确认 Multica + skill pack 能跑 | `smoke` | `superpowers-superpowers-orchestrator` 或管理员指定的 smoke agent |
| 从蓝湖整理原始需求 | `lanhu-intake` | 对应 Lanhu analyst |
| 讨论需求、形成 spec | `brainstorming` | `superpowers-brainstorming-agent` 或 `superpowers-runtime-squad` |
| 根据 spec 写 plan | `writing-plans` | `superpowers-planning-agent`，中途可见 `superpowers-source-of-truth-verifier` |
| 审查 spec | `spec-document-review` | `superpowers-spec-document-reviewer` |
| 审查 plan | `plan-document-review` | `superpowers-plan-document-reviewer` |
| 执行已批准 plan | `execute-plan` | `superpowers-implementer` |
| 跑 SDD implementer/reviewer loop | `sdd-execution` | `superpowers-runtime-squad` 或 `superpowers-implementer` |
| 系统化调试 bug | `systematic-debugging` | `superpowers-debugger` |
| 重复失败后复盘 | `break-loop` | `superpowers-break-loop-analyst` |
| 任务结束后更新 wiki | `update-wiki` | `superpowers-wiki-curator` |
| 准备 shared wiki 发布 | `publish-shared-wiki` | `superpowers-shared-wiki-publisher` |
| 准备 GitHub-backed shared wiki PR | `shared-wiki-mcp-pr` | `superpowers-shared-wiki-publisher` |

如果你不知道选哪个，使用：

```text
Issue template: brainstorming
Assignee: superpowers-runtime-squad
```

并在正文里说明“请根据输入判断下一步是否需要拆成 spec review / planning / execution”。

---

## 7. 最推荐的完整新功能流程

这是团队中最常用的流程：从需求到实现、review、收尾、wiki 更新。

### 7.1 第一步：创建入口 issue

Assignee：

```text
superpowers-runtime-squad
```

Issue 示例：

```markdown
# [Superpowers] 新功能：订单列表支持批量导出

Target repo: /path/to/project
Issue template: brainstorming

Background:
- 运营需要在订单列表中批量导出订单数据，用于月底对账。

Inputs:
- 需求文档：/path/to/project/docs/order-export-prd.md
- 相关页面：订单列表
- 已知约束：导出必须受权限控制，不能导出未授权租户数据。

Expected output:
- 先进行 brainstorming，形成可确认的 spec。
- 如果需要项目约束，请让 wiki-researcher 选择相关 wiki。
- 不要直接开始实现。

Safety:
- 不要 commit / push / 创建 PR。
- 需要我确认 spec 后再进入 planning。
```

### 7.2 触发后会发生什么

你会在 Multica 中看到类似这样的阶段：

```text
入口 issue / squad dispatch
  -> superpowers-wiki-researcher
  -> superpowers-brainstorming-agent
  -> superpowers-spec-document-reviewer
  -> superpowers-planning-agent (draft plan)
  -> superpowers-source-of-truth-verifier
  -> superpowers-planning-agent (final plan revision)
  -> superpowers-plan-document-reviewer
  -> superpowers-implementer
  -> superpowers-spec-compliance-reviewer
  -> superpowers-code-quality-reviewer
  -> superpowers-code-reviewer
  -> superpowers-finisher
  -> superpowers-wiki-curator
```

每个阶段都应该是 Multica 中可见的 issue assignment / run，而不是一个 agent 内部悄悄跑完。

### 7.3 每个阶段你需要做什么

| 阶段 | Agent 做什么 | 你需要做什么 |
|---|---|---|
| Wiki research | 查相关项目/共享 wiki | 确认它选的 wiki 是否相关 |
| Brainstorming | 讨论需求、提出 spec | 回答开放问题，确认方向 |
| Spec review | 检查 spec 是否清晰 | 按评论补充或确认 spec |
| Planning | 写 draft plan，固化 wiki context；verifier 后修订 final plan | 审批 plan，确认任务拆分 |
| Source-truth verification | 校验 draft plan 中的真实源假设，输出 report/constraints sidecar | 处理 blocked 或 `edit: ask` 的确认问题 |
| Plan review | 检查 final plan 可执行性和 source-truth 结果消费是否正确 | 根据建议修改/确认 plan |
| Implementation | 按 plan 实现 | 等待结果，不要中途改输入范围 |
| Spec compliance review | 检查实现是否满足 spec | 如果失败，让 implementer 修复 |
| Code quality review | 检查代码质量 | 判断是否接受重构建议 |
| Final code review | 最终 review | 确认是否进入收尾 |
| Finisher | 检查分支、PR、合并 readiness | 明确是否授权 commit/push/PR |
| Wiki curator | 判断是否需要沉淀知识 | 确认是否写入 project/shared wiki |

---

## 8. 从蓝湖开始的流程

如果需求来自蓝湖，建议先不要直接进入开发，而是先生成“原始需求证据包”。

### 8.1 创建 Lanhu intake issue

根据需求类型 assign 给：

```text
superpowers-lanhu-frontend-requirements-analyst
superpowers-lanhu-backend-requirements-analyst
```

Issue 示例：

```markdown
# [Superpowers] Lanhu intake：订单导出需求

Target repo: /path/to/project
Issue template: lanhu-intake

Inputs:
- Lanhu URL: <蓝湖链接>
- Role: frontend

Expected output:
- 只整理蓝湖原始需求证据包。
- 输出 `.lanhu/.../index.md` 作为后续 Superpowers 输入入口。
- frontend 使用统一 `frontend-prd/` 包：`frontend-prd/prd.md`，以及仅在有设计稿或需要交互 demo 时输出的 `frontend-prd/design/index.html`。
- 如果有无法确认的源事实，请列出问题。

Safety:
- 不要写 spec。
- 不要写 implementation plan。
- 不要实现代码。
```

### 8.2 你确认 evidence package 后再进入 brainstorming

创建第二个 issue：

```markdown
# [Superpowers] Brainstorming：订单导出需求

Target repo: /path/to/project
Issue template: brainstorming

Inputs:
- Lanhu evidence package: /path/to/project/.lanhu/05-25-order-export/index.md

Expected output:
- 基于已确认的 Lanhu evidence package 讨论需求并形成 spec。
- 不要重新读取或重做蓝湖 intake。
```

---

## 9. 只执行已批准 plan 的流程

如果 spec 和 plan 已经确认，直接创建执行 issue。

Assignee：

```text
superpowers-implementer
```

Issue 示例：

```markdown
# [Superpowers] Execute plan：订单导出

Target repo: /path/to/project
Issue template: execute-plan

Inputs:
- Plan: /path/to/project/.superpowers/plans/order-export.md
- Wiki context: /path/to/project/.superpowers/plans/order-export.wiki-context.json
- Source-truth constraints: /path/to/project/.superpowers/plans/order-export.source-truth-constraints.json（如 plan 有该 sidecar）
- Approval: 用户已确认该 plan 可以执行。

Expected output:
- 按 plan 实现。
- 运行必要的本地检查。
- 输出改动摘要、验证结果、后续 review 建议。

Safety:
- 不要 commit / push / 创建 PR。
- 如果需要扩大实现范围，请先评论说明并等待确认。
```

如果执行 issue 包含 `Source-truth constraints`，agent 只应消费 `.source-truth-constraints.json` 的 task-specific 渲染结果；完整 `.source-truth-report.json` 是 planning/audit 资料，不是 implementer/reviewer 默认上下文。

触发后通常应该继续创建或进入 review 阶段：

```text
superpowers-spec-compliance-reviewer
superpowers-code-quality-reviewer
superpowers-code-reviewer
superpowers-finisher
superpowers-wiki-curator
```

---

## 10. 调试 bug 的流程

### 10.1 创建 systematic-debugging issue

Assignee：

```text
superpowers-debugger
```

Issue 示例：

```markdown
# [Superpowers] Debug：支付回调偶发重复入账

Target repo: /path/to/project
Issue template: systematic-debugging

Inputs:
- Bug 现象：支付回调偶发重复入账。
- 期望行为：同一支付流水只能入账一次。
- 复现材料：/path/to/project/docs/payment-duplicate-debug.md
- 相关日志：见 issue 附件或评论。

Expected output:
- 先复现或收窄失败边界。
- 再提出 root cause 假设。
- 修复前说明证据。
- 如果多次失败，请 handoff 给 break-loop。

Safety:
- 不要在证据不足时直接改代码。
- 不要 commit / push / 创建 PR。
```

### 10.2 如果调试反复失败

创建或 rerun 一个 break-loop issue：

```markdown
Target repo: /path/to/project
Issue template: break-loop

Inputs:
- Debug evidence: /path/to/project/docs/payment-duplicate-debug.md
- Failed attempts: 见前序 issue 评论和 run 记录。

Expected output:
- 复盘为什么重复失败。
- 输出新的诊断路径。
- 判断是否有 durable knowledge 需要交给 update-wiki。
```

---

## 11. 更新 project/shared wiki 的流程

任务完成后，如果这次工作产生了以后会复用的知识，可以创建 update-wiki issue。

Assignee：

```text
superpowers-wiki-curator
```

Issue 示例：

```markdown
# [Superpowers] Update wiki：订单导出权限约束

Target repo: /path/to/project
Issue template: update-wiki

Inputs:
- Completed work: 订单导出功能已实现并通过 review。
- Plan: /path/to/project/.superpowers/plans/order-export.md
- Important finding: 导出必须按租户和订单权限双重过滤。

Expected output:
- 判断是否需要更新 project wiki 或 shared wiki。
- 如果写 shared wiki，必须保持中性、可迁移。
- 输出更新了哪些 wiki 文件，或说明为什么跳过。

Safety:
- 创建新 wiki 文档前需要确认。
- 不要发布 shared wiki。
```

如果要发布 shared wiki，再单独创建：

```markdown
Target repo: /path/to/project
Issue template: publish-shared-wiki

Inputs:
- Shared wiki topic: portable export authorization rules

Expected output:
- 只做发布 readiness 检查。
- 如需 commit / push / PR，请先请求明确授权。
```

---

## 12. 怎么查看进度和结果

### 12.1 在 Multica UI 中看

进入对应 issue，重点看：

1. Assignee 是哪个 agent / squad。
2. Runs 区域是否出现 task run。
3. Run 状态是 running、completed、failed、cancelled 还是 blocked。
4. Agent 是否在评论区输出结果、问题或 handoff。
5. 下游 issue 是否已经创建或被建议创建。

### 12.2 用 CLI 看

如果你会命令行，可以运行：

```bash
multica issue runs <issue-id>
```

需要完整 run id 时：

```bash
multica issue runs <issue-id> --full-id --output json
```

如果一个 issue 失败后补充了信息，可以 rerun：

```bash
multica issue rerun <issue-id>
```

如果当前 run 明显跑错或输入错了，可以取消：

```bash
multica issue cancel-task <task-run-id> --issue <issue-id>
```

不熟悉 CLI 的成员，可以直接在 UI 中查看 run、评论补充信息，并让熟悉 Multica 的同事帮忙 rerun / cancel。

---

## 13. 失败了怎么办

### 13.1 issue 没有 run

可能原因：

- 没有 assign 给 agent / squad。
- Multica daemon 不在线。
- Claude Code runtime 不在线。
- workspace 中缺少对应 role agent。

处理方式：

1. 确认 issue 已 assign。
2. 找管理员确认 daemon/runtime 状态。
3. runtime 恢复后 rerun issue。

### 13.2 run 失败为 runtime offline

这通常说明 issue assignment 已成功，但本地 runtime 没接住任务。

处理方式：

1. 找管理员确认 runtime online。
2. 对失败 issue 执行 rerun。

### 13.3 agent 问你问题或标记 blocked

这通常是正常的，表示输入不足或需要人确认。

处理方式：

1. 在 issue 评论中补充答案。
2. 如果需要继续执行，rerun 该 issue。
3. 不要新建重复 issue，除非需要拆成新的阶段。

### 13.4 只看到一个 agent 在跑

如果完整开发流程只看到一个 agent 运行，通常说明触发方式不对。

正确的完整流程应该能看到多个 `superpowers-*` role agent 的 issue runs，例如：

```text
wiki-researcher
brainstorming-agent
spec-document-reviewer
planning-agent
source-of-truth-verifier
plan-document-reviewer
implementer
reviewers
finisher
wiki-curator
```

不要使用 `superpowers-adapter-orchestrator`。这个 adapter-specific 单 agent 路径已经移除。

---

## 14. 安全边界：什么时候需要明确授权

默认情况下，Superpowers + adapter 的 Multica issue 不应该做这些事：

- commit
- push
- 创建 PR
- 合并 PR
- 发布 shared wiki
- 删除文件
- destructive git operations
- 修改生产环境或共享基础设施

如果你确实希望 agent 做外部可见动作，请在 issue 中写清楚授权范围。例如：

```markdown
Authorization:
- 允许创建一个 draft PR。
- 不允许 merge。
- 不允许 force push。
- commit 范围仅限本 issue 相关文件。
```

如果没有明确授权，agent 应该只做 readiness / preparation，并在评论中请求你确认。

---

## 15. 团队推荐使用方式

### 新功能

```text
1. 创建 brainstorming issue → superpowers-runtime-squad
2. 确认 spec
3. 创建 writing-plans issue → superpowers-planning-agent，期间可见 source-of-truth-verifier
4. 确认 final plan 和 source-truth 状态
5. 创建 execute-plan / sdd-execution issue → implementer / squad
6. 跑 spec compliance review、code quality review、final code review
7. finisher 做收尾 readiness
8. update-wiki 判断是否沉淀知识
```

### 蓝湖需求

```text
1. lanhu-intake → Lanhu analyst
2. 人确认 evidence package
3. brainstorming → brainstorming-agent / squad
4. 后续同新功能流程
```

### Bug

```text
1. systematic-debugging → debugger
2. 必要时 wiki-researcher 查询项目约束
3. 修复或输出诊断路径
4. 多次失败则 break-loop
5. 有长期价值则 update-wiki
```

### Wiki 维护

```text
1. update-wiki → wiki-curator
2. shared wiki 内容必须中性化
3. publish-shared-wiki / shared-wiki-mcp-pr 只在明确需要发布时单独触发
```

---

## 16. 给团队成员的最短版操作口诀

1. **所有任务从 Multica issue 开始。**
2. **写清楚 `Target repo`、`Issue template`、输入材料和期望输出。**
3. **不确定 assign 给谁，就 assign 给 `superpowers-runtime-squad`。**
4. **完整流程应该看到多个 `superpowers-*` agent runs。**
5. **agent blocked 时，在 issue 评论补充信息，然后 rerun。**
6. **commit / push / PR / publish 默认都不做，除非你明确授权。**
7. **任务结束后，如果产生长期知识，单独触发 `update-wiki`。**
