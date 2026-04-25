#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="${1:-$(mktemp -d)}"

"${ROOT}/bootstrap-spec.sh" "${PROJECT_ROOT}" --template standard > /dev/null

if [[ ! -f "${PROJECT_ROOT}/.superpowers/spec/index.md" ]]; then
  printf 'Expected imported index.md\n' >&2
  exit 1
fi
if [[ -d "${PROJECT_ROOT}/.superpowers/spec/categories" ]]; then
  printf 'Expected template import without categories wrapper\n' >&2
  exit 1
fi

printf '# User Index\n\nDo not overwrite.\n' > "${PROJECT_ROOT}/.superpowers/spec/index.md"
if "${ROOT}/bootstrap-spec.sh" "${PROJECT_ROOT}" --template standard > /dev/null 2>&1; then
  printf 'Expected bootstrap conflict to fail\n' >&2
  exit 1
fi
if ! grep -q 'Do not overwrite' "${PROJECT_ROOT}/.superpowers/spec/index.md"; then
  printf 'Expected bootstrap to preserve conflicting user file\n' >&2
  exit 1
fi

printf 'bootstrap-spec template import test complete\n'
