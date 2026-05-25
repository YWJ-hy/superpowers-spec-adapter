# Multica 可视化多智能体 Superpowers+adapter 验收链路

目标：废弃“单个 `superpowers-adapter-orchestrator` 在一个 Claude Code runtime 内跑完整流程”的验收标准，改为验证 Multica 层可见的 squad / role-agent 分派。每条链路必须在 Multica UI / CLI 中看到对应 `superpowers-*` role agent 的独立 issue run，不能只看到 `superpowers-adapter-orchestrator`。

## 通用验收标准

每条链路都必须满足：

1. 主 workflow issue 可创建并关联本次验收 run id。
2. 阶段任务使用 child issue 或独立 stage issue 表示，title/body 明确 stage、上游输入和期望输出。
3. 阶段任务 assign 给对应 `superpowers-*` role agent 或 `superpowers-runtime-squad`，而不是默认全部 assign 给 `superpowers-adapter-orchestrator`。
4. 每个阶段至少产生一个 Multica run，`multica issue runs <issue>` 可看到对应 role agent 名称。
5. 阶段产物通过 issue comment / metadata / attachment path 传递给下游。
6. 失败、阻塞、等待用户确认必须停在对应阶段 issue，不得由 orchestrator 静默吞掉。
7. 发布、push、PR、merge、shared-wiki 外部副作用默认只到 readiness / authorization gate；真实外部发布另行授权。

## 角色映射

| Superpowers 阶段 | Multica assignee |
|---|---|
| Lanhu frontend intake | `superpowers-lanhu-frontend-requirements-analyst` |
| Lanhu frontend HTML intake | `superpowers-lanhu-frontend-html-requirements-analyst` |
| Lanhu backend intake | `superpowers-lanhu-backend-requirements-analyst` |
| Brainstorming | `superpowers-brainstorming-agent` |
| Wiki research | `superpowers-wiki-researcher` |
| Writing plans | `superpowers-planning-agent` |
| Spec document review | `superpowers-spec-document-reviewer` |
| Plan document review | `superpowers-plan-document-reviewer` |
| Implement plan task | `superpowers-implementer` |
| Spec compliance review | `superpowers-spec-compliance-reviewer` |
| Code quality review | `superpowers-code-quality-reviewer` |
| Final code review | `superpowers-code-reviewer` |
| Finish development branch | `superpowers-finisher` |
| Systematic debugging | `superpowers-debugger` |
| Break-loop retrospective | `superpowers-break-loop-analyst` |
| Update wiki | `superpowers-wiki-curator` |
| Shared wiki publish readiness | `superpowers-shared-wiki-publisher` |
| Flow orchestration only | `superpowers-superpowers-orchestrator` or `superpowers-runtime-squad` leader |

`superpowers-adapter-orchestrator` 已移除；bootstrap 兼容 smoke 也不得创建或 assign 给它，完整验收只能使用 role agents / squad fanout。

## 必测链路 A：Wiki-aware feature development 主链路

```text
A0 main workflow issue → superpowers-runtime-squad
A1 wiki-researcher/spec-context → superpowers-wiki-researcher
A2 brainstorming/spec discussion → superpowers-brainstorming-agent
A2r spec document review → superpowers-spec-document-reviewer
A3 wiki-researcher/plan-context → superpowers-wiki-researcher
A4 writing-plans → superpowers-planning-agent
A4r plan document review → superpowers-plan-document-reviewer
A5 implement plan → superpowers-implementer
A6 spec compliance review → superpowers-spec-compliance-reviewer
A7 code quality review → superpowers-code-quality-reviewer
A8 final review → superpowers-code-reviewer
A9 finishing-a-development-branch → superpowers-finisher
A10 update-wiki → superpowers-wiki-curator
```

验收断言：

- A1/A3 分别产生 wiki-researcher runs。
- A4 的 plan 包含 `Referenced Project Wiki`。
- A4 生成 schemaVersion 3 `.wiki-context.json`。
- A2r 必须由 `superpowers-spec-document-reviewer` 审查 spec 文档后才能进入 planning。
- A5 执行只消费 A4 plan 和 `.wiki-context.json`。
- A4r 必须由 `superpowers-plan-document-reviewer` 审查 plan 文档后才能进入 execution。
- A6/A7/A8 都有独立 reviewer runs。
- A9 必须由 `superpowers-finisher` 执行 finishing-a-development-branch readiness，外部副作用仍需授权。
- A10 判断是否写 wiki；可 skip，但必须由 `superpowers-wiki-curator` 独立 run 完成。

## 必测链路 B：Lanhu intake → Superpowers 主链路

```text
B1 lanhu-intake/frontend → superpowers-lanhu-frontend-requirements-analyst
B2 user confirms evidence package → rerun same analyst if needed
B3 brainstorming → superpowers-brainstorming-agent
B3r spec document review → superpowers-spec-document-reviewer
B4 writing-plans → superpowers-planning-agent
B4r plan document review → superpowers-plan-document-reviewer
B5 implement + review fanout → implementer + reviewers
B6 finishing-a-development-branch → superpowers-finisher
B7 update-wiki → superpowers-wiki-curator
```

验收断言：

- 缺少 role 时停在 B1，补充 `Role: frontend|backend` 后 rerun 恢复。
- `.lanhu/.../index.md` 和 `prd.md` 由 Lanhu role agent 产出。
- 后续 Superpowers 阶段不由 Lanhu agent 或 adapter orchestrator 代跑。

## 必测链路 C：Brainstorming 多轮交互 → Planning

```text
C1 brainstorming initial → superpowers-brainstorming-agent
C2 user follow-up comment → rerun superpowers-brainstorming-agent
C2r spec document review → superpowers-spec-document-reviewer
C3 approved direction → writing-plans assigned to superpowers-planning-agent
C3r plan document review → superpowers-plan-document-reviewer
C4 plan context wiki research → superpowers-wiki-researcher
```

验收断言：

- C2 不进入实现，不写 plan。
- C3/C4 是新的 Multica runs，不是同一个 agent 内部继续执行。

## 必测链路 D：SDD reviewer loop 可视化

```text
D0 plan document review → superpowers-plan-document-reviewer
D1 implementer task 1 → superpowers-implementer
D2 spec compliance review task 1 → superpowers-spec-compliance-reviewer
D3 code quality review task 1 → superpowers-code-quality-reviewer
D4 implementer fix if review requests changes → superpowers-implementer
D5 final code review → superpowers-code-reviewer
D6 finishing-a-development-branch → superpowers-finisher
```

验收断言：

- plan document review 必须先由 `superpowers-plan-document-reviewer` 独立 run 完成。
- reviewer loop 每一轮都出现在 Multica runs 中。
- review 失败时下游不继续，必须回到 implementer。
- final review 通过后必须先进入 `superpowers-finisher` readiness，之后才允许 update-wiki。

## 必测链路 E：Systematic debugging → Break loop → Update wiki

```text
E1 systematic-debugging → superpowers-debugger
E2 optional wiki debug context → superpowers-wiki-researcher
E3 fix/recommendation handoff → superpowers-implementer or issue comment
E4 break-loop retrospective → superpowers-break-loop-analyst
E5 update-wiki → superpowers-wiki-curator
```

验收断言：

- E2 只在证据收窄后触发。
- E4 不直接修代码，只输出复盘和 update-wiki handoff。

## 必测链路 F：Shared wiki 本地 readiness

```text
F1 local shared wiki review → superpowers-wiki-researcher or superpowers-wiki-curator
F2 publish-shared-wiki readiness → superpowers-shared-wiki-publisher
```

验收断言：

- 只检查本地 `.shared-superpowers/wiki` 和 settings。
- 不调用 shared-wiki MCP。
- 不 publish / commit / push / PR。
- 输出 neutrality / authorization gate / missing hook readiness report。

## 必测链路 G：Direct role-agent 与 squad dispatch

```text
G1 direct brainstorming issue → superpowers-brainstorming-agent
G2 direct planning issue → superpowers-planning-agent
G3 direct squad issue → superpowers-runtime-squad → selected role agent
```

验收断言：

- role agent 直接作为 assignee 时能跑。
- squad assignment 会产生 squad leader run 和至少一个 role-agent run。

## 必测链路 H：Failure recovery 生命周期

```text
H1 missing required input → stage issue blocked
H2 user adds required input comment → rerun same role agent
H3 cancel running task → cancelled run visible
H4 rerun cancelled issue → new role-agent run completed
```

验收断言：

- blocked/cancelled/rerun 都在 Multica issue runs 中可见。
- 恢复后不能回退到 `superpowers-adapter-orchestrator` 单 agent 模式。

## 最终完成标准

只有当 A-H 全部通过，并且 CLI 汇总显示每个核心 role agent 都至少产生一次真实 run，才认为 Multica Superpowers+adapter 可视化多智能体流程完成。
