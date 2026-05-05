#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
TARGET_INPUT="$(cd "${TARGET_INPUT}" && pwd)"

LANHU_AGENT="${TARGET_INPUT}/agents/lanhu-requirements-analyst.md"
LANHU_COMMAND="${TARGET_INPUT}/commands/lanhu-requirements.md"
BRAINSTORMING_SKILL="${TARGET_INPUT}/skills/brainstorming/SKILL.md"

for file in "$LANHU_AGENT" "$LANHU_COMMAND" "$BRAINSTORMING_SKILL"; do
  if [[ ! -f "$file" ]]; then
    printf 'Expected installed Lanhu guardrail target: %s\n' "$file" >&2
    exit 1
  fi
done

require_in_file() {
  local file="$1"
  local text="$2"
  if ! grep -Fq "$text" "$file"; then
    printf 'Expected %s to contain Lanhu tree guardrail: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

for required in \
  'page-by-page full analysis' \
  'mode: full' \
  'page_names` containing exactly that one page' \
  'one full analysis request for the parent plus all descendants' \
  'one combined parent+children MCP response' \
  'raw evidence labels or external tool commentary only' \
  'not the output schema' \
  '## 四、页面展示规则' \
  '### 4.1 页面布局结构草图' \
  '## 六、用户操作与交互规则' \
  '### 6.1 用户操作流程' \
  '### 6.2 交互规则' \
  '本组核心N点' \
  '功能清单表' \
  '字段规则表' \
  'STAGE 4 输出要求' \
  '.lanhu/MM-DD-账单寄送/账单寄送.md' \
  'index.md` is never a substitute' \
  'Mermaid flowchart' \
  'mindmap only for small/simple structures' \
  'short node labels' \
  'limited depth' \
  'Split dense diagrams' \
  'move details to tables'
do
  require_in_file "$LANHU_AGENT" "$required"
done

for required in \
  'page-by-page full analysis' \
  'mode: full' \
  'page_names` containing exactly one page' \
  'one full request for the parent plus descendants' \
  'one combined MCP response to generate multiple PRD files' \
  'raw evidence only' \
  'not the adapter output schema' \
  'Role PRD heading validation' \
  '# 前端开发角色视角 PRD' \
  '# 后端开发角色视角 PRD' \
  '<父级需求名称>.md' \
  'index.md` is never a substitute' \
  'Mermaid flowchart' \
  'mindmap only for small/simple structures' \
  'short node labels' \
  'limited depth' \
  'dense details to tables'
do
  require_in_file "$LANHU_COMMAND" "$required"
done

for required in \
  'page-by-page full analysis' \
  'mode: full' \
  'page_names` containing exactly that one page' \
  'one full request for the parent plus descendants' \
  'one combined MCP response to generate multiple PRD files' \
  'raw evidence only' \
  'not the adapter output schema' \
  '本组核心N点' \
  '功能清单表' \
  '字段规则表' \
  'STAGE 4 输出要求' \
  '<父级需求名称>.md' \
  'Every parent and child PRD file must be a complete selected-role PRD' \
  'index.md` is never a substitute' \
  'Mermaid flowchart' \
  'mindmap is allowed only for small/simple structures' \
  'short node labels' \
  'limited depth' \
  'Split dense diagrams' \
  'move details to tables'
do
  require_in_file "$BRAINSTORMING_SKILL" "$required"
done

printf 'Lanhu tree PRD guardrails smoke OK\n'
