#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
TARGET_INPUT="$(cd "${TARGET_INPUT}" && pwd)"

LANHU_FRONTEND_AGENT="${TARGET_INPUT}/agents/lanhu-frontend-requirements-analyst.md"
LANHU_FRONTEND_HTML_AGENT="${TARGET_INPUT}/agents/lanhu-frontend-html-requirements-analyst.md"
LANHU_BACKEND_AGENT="${TARGET_INPUT}/agents/lanhu-backend-requirements-analyst.md"
LANHU_COMMAND="${TARGET_INPUT}/commands/lanhu-requirements.md"
BRAINSTORMING_SKILL="${TARGET_INPUT}/skills/brainstorming/SKILL.md"

for file in "$LANHU_FRONTEND_AGENT" "$LANHU_FRONTEND_HTML_AGENT" "$LANHU_BACKEND_AGENT" "$LANHU_COMMAND" "$BRAINSTORMING_SKILL"; do
  if [[ ! -f "$file" ]]; then
    printf 'Expected installed Lanhu selective image analysis target: %s\n' "$file" >&2
    exit 1
  fi
done

require_in_file() {
  local file="$1"
  local text="$2"
  if ! grep -Fq "$text" "$file"; then
    printf 'Expected %s to contain Lanhu selective image analysis text: %s\n' "$file" "$text" >&2
    exit 1
  fi
}

for agent in "$LANHU_FRONTEND_AGENT" "$LANHU_FRONTEND_HTML_AGENT" "$LANHU_BACKEND_AGENT"; do
  for required in \
    'Selective image analysis policy' \
    'designInfo.images' \
    'candidate evidence only' \
    'Do not parse every image resource returned by Lanhu' \
    'direct analysis' \
    'structured source facts' \
    'persistedImages: false' \
    'persistedImageFiles: []' \
    'unresolvedImageQuestions: []' \
    'lanhu_get_prd_scoped_evidence' \
    'output_mode: evidence_only' \
    'must not broaden the allowed Lanhu MCP tool set' \
    'Do not save Lanhu image files' \
    '.lanhu/.../assets/' \
    '.lanhu/.../images/' \
    'raw OCR dumps' \
    'exhaustive image inventories'
  do
    require_in_file "$agent" "$required"
  done
done

for required in \
  'selected/evidenced image regions' \
  'remote Lanhu images' \
  'base64 images' \
  'persisted image assets by default' \
  'selectiveImageAnalysisPolicyApplied: true' \
  'imageFactsAreStructured: true' \
  'remoteLanhuImagesEmbedded: []' \
  'persistedLanhuImageFiles: []' \
  'fullScreenshotParsingDetected: []' \
  'selected scoped/evidenced Lanhu requirement range'
do
  require_in_file "$LANHU_FRONTEND_HTML_AGENT" "$required"
done

for required in \
  '图片、截图和 `designInfo.images` 只在具备范围信号时选择性分析' \
  '默认不保存蓝湖图片文件' \
  '图片/截图/可视资源 + 标注/箭头/周边说明'
do
  require_in_file "$LANHU_FRONTEND_AGENT" "$required"
done

for required in \
  'selective image analysis policy' \
  'broad Lanhu design tools' \
  'selectiveImageAnalysis' \
  'persistedImages: false' \
  'Image files, base64 blobs, remote image references' \
  'Saving original images requires an explicit user request'
do
  require_in_file "$LANHU_COMMAND" "$required"
done

for required in \
  'selective image analysis' \
  'Do not broaden to design tools for images' \
  'persistedImages: false' \
  'compact `selectiveImageAnalysis` metadata' \
  'empty `remoteLanhuImagesEmbedded`' \
  'empty `persistedLanhuImageFiles`' \
  'empty `fullScreenshotParsingDetected`'
do
  require_in_file "$BRAINSTORMING_SKILL" "$required"
done

printf 'Lanhu selective image analysis smoke OK\n'
