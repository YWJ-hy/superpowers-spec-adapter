#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
PROJECT_ROOT="${2:-${ROOT}/..}"
SPEC_ROOT="${PROJECT_ROOT}/.superpowers/spec"

mkdir -p "${SPEC_ROOT}/platform/api" "${SPEC_ROOT}/guides" "${SPEC_ROOT}/shared/deep" "${SPEC_ROOT}/unindexed"
cat > "${SPEC_ROOT}/index.md" <<'EOF'
# Project Specs

<!-- superpower-adapter:auto:start -->
- `platform/api/contract.md`
- `guides/`
- `shared/deep/rule.md`
<!-- superpower-adapter:auto:end -->
EOF
cat > "${SPEC_ROOT}/guides/index.md" <<'EOF'
# Guides

<!-- superpower-adapter:auto:start -->
- `debugging.md`
<!-- superpower-adapter:auto:end -->
EOF
printf '# API Contract\n\nContract behavior.\n' > "${SPEC_ROOT}/platform/api/contract.md"
printf '# Debugging\n\nDebugging behavior.\n' > "${SPEC_ROOT}/guides/debugging.md"
printf '# Deep Rule\n\nDeep indexed behavior.\n' > "${SPEC_ROOT}/shared/deep/rule.md"
printf '# Secret\n\nUnindexed behavior.\n' > "${SPEC_ROOT}/unindexed/secret.md"

tree_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec-context.py" --tree --depth 5)"
for expected in "platform/api/contract.md" "guides/index.md" "guides/debugging.md" "shared/deep/rule.md"; do
  case "${tree_output}" in
    *"${expected}"*) : ;;
    *) printf 'Expected index-driven tree to include %s\n%s\n' "${expected}" "${tree_output}" >&2; exit 1 ;;
  esac
done
case "${tree_output}" in
  *"unindexed/secret.md"*) printf 'Expected tree to exclude unindexed file\n' >&2; exit 1 ;;
  *) : ;;
esac

selector_json="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec_select_context.py" secret --json)"
python3 - <<'PY' "${selector_json}"
import json, sys
payload = json.loads(sys.argv[1])
paths = [item.get('path') for item in payload.get('candidates', [])]
if any('unindexed/secret.md' in path for path in paths):
    raise SystemExit(f'Unindexed file should not be selected: {paths}')
PY

printf 'spec-index-graph smoke test complete\n'
