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
for expected in "Spec root: \`.superpowers/spec/\`" ".superpowers/spec/platform/api/contract.md" ".superpowers/spec/guides/index.md" ".superpowers/spec/guides/debugging.md" ".superpowers/spec/shared/deep/rule.md"; do
  case "${tree_output}" in
    *"${expected}"*) : ;;
    *) printf 'Expected index-driven tree to include %s\n%s\n' "${expected}" "${tree_output}" >&2; exit 1 ;;
  esac
done
case "${tree_output}" in
  *"unindexed/secret.md"*) printf 'Expected tree to exclude unindexed file\n' >&2; exit 1 ;;
  *) : ;;
esac

cat > "${SPEC_ROOT}/index.md" <<'EOF'
# Project Specs

<!-- superpower-adapter:auto:start -->
- `frontend/`
<!-- superpower-adapter:auto:end -->
EOF
mkdir -p "${SPEC_ROOT}/frontend/examples"
cat > "${SPEC_ROOT}/frontend/index.md" <<'EOF'
# Frontend Specs

<!-- superpower-adapter:auto:start -->
- `component-guidelines.md`
- `hook-guidelines.md`
- `type-safety.md`
- `examples/`
<!-- superpower-adapter:auto:end -->
EOF
cat > "${SPEC_ROOT}/frontend/examples/index.md" <<'EOF'
# Examples

Use this index to navigate the specs in this section.
EOF
printf '# Component Guidelines\n\nReusable Vue component props, emits, upload UI, and directory composition.\n' > "${SPEC_ROOT}/frontend/component-guidelines.md"
printf '# Hook Guidelines\n\nReusable useUpload composables and hook extraction patterns.\n' > "${SPEC_ROOT}/frontend/hook-guidelines.md"
printf '# Type Safety\n\nTypeScript contracts and Naive UI component declarations.\n' > "${SPEC_ROOT}/frontend/type-safety.md"
printf '# Example\n\nIgnored example content.\n' > "${SPEC_ROOT}/frontend/examples/example.md"
component_tree_output="$(cd "${PROJECT_ROOT}" && python3 "${TARGET_INPUT}/scripts/spec-context.py" --tree --depth 4)"
for expected in ".superpowers/spec/frontend/component-guidelines.md" ".superpowers/spec/frontend/hook-guidelines.md" ".superpowers/spec/frontend/type-safety.md"; do
  case "${component_tree_output}" in
    *"${expected}"*) : ;;
    *) printf 'Expected component tree to include %s\n%s\n' "${expected}" "${component_tree_output}" >&2; exit 1 ;;
  esac
done
case "${component_tree_output}" in
  *"frontend/examples/example.md"*) printf 'Expected tree to exclude ignored examples leaf\n' >&2; exit 1 ;;
  *) : ;;
esac

printf 'spec-index-graph smoke test complete\n'
