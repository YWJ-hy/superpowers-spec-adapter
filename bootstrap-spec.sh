#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s <project-root> [--preset web|backend|fullstack] [categories...]\n' "$0" >&2
  exit 1
}

if [[ $# -lt 1 || -z "${1:-}" ]]; then
  printf 'Missing required project root.\n' >&2
  usage
fi

REPO_ROOT="$(cd "$1" && pwd)"
shift
SPEC_ROOT="$REPO_ROOT/.superpowers/spec"
ENTRY_INDEX="$SPEC_ROOT/index.md"
IGNORE_FILE="$SPEC_ROOT/.adapter-ignore"
PRESET=""
CATEGORY_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --preset)
      PRESET="${2:-}"
      shift 2
      ;;
    *)
      CATEGORY_ARGS+=("$1")
      shift
      ;;
  esac
done

mkdir -p "$SPEC_ROOT"

if [[ ! -f "$ENTRY_INDEX" ]]; then
  cat > "$ENTRY_INDEX" <<'EOF'
# Project Specs

Use this file as the entry point for project-specific specs.

<!-- superpower-adapter:auto:start -->
<!-- superpower-adapter:auto:end -->
EOF
  printf 'Created %s\n' "$ENTRY_INDEX"
else
  printf 'Kept existing %s\n' "$ENTRY_INDEX"
fi

if [[ ! -f "$IGNORE_FILE" ]]; then
  cat > "$IGNORE_FILE" <<'EOF'
# one directory name per line
# default directories are already ignored by the adapter:
# draft
# archive
# examples
EOF
  printf 'Created %s\n' "$IGNORE_FILE"
else
  printf 'Kept existing %s\n' "$IGNORE_FILE"
fi

create_category() {
  local name="$1"
  local title
  title="$(python3 - <<'PY' "$name"
import sys
name = sys.argv[1].replace('-', ' ').replace('_', ' ')
print(name.title())
PY
)"
  local dir="$SPEC_ROOT/$name"
  local index="$dir/index.md"
  mkdir -p "$dir"
  if [[ ! -f "$index" ]]; then
    case "$name" in
      backend)
        cat > "$index" <<'EOF'
# Backend Specs

Document server-side rules that affect correctness, contracts, persistence, validation, and operational behavior.

Suggested topics:
- API contracts
- Error handling
- Database access
- Background jobs
- Configuration and env wiring
- Logging and observability

<!-- superpower-adapter:auto:start -->
<!-- superpower-adapter:auto:end -->
EOF
        ;;
      frontend)
        cat > "$index" <<'EOF'
# Frontend Specs

Document UI and client-side rules that affect structure, state, data fetching, accessibility, and user-facing behavior.

Suggested topics:
- Component patterns
- State management
- Data fetching
- Form behavior
- Accessibility
- Styling conventions

<!-- superpower-adapter:auto:start -->
<!-- superpower-adapter:auto:end -->
EOF
        ;;
      guides)
        cat > "$index" <<'EOF'
# Guides

Use guides for cross-cutting checklists and thinking prompts, not low-level implementation contracts.

Suggested topics:
- Cross-layer changes
- Release readiness
- Debugging checklists
- Migration review
- Performance review
- Security review

<!-- superpower-adapter:auto:start -->
<!-- superpower-adapter:auto:end -->
EOF
        ;;
      *)
        cat > "$index" <<EOF
# ${title} Specs

Summarize the scope of ${name} rules here.

<!-- superpower-adapter:auto:start -->
<!-- superpower-adapter:auto:end -->
EOF
        ;;
    esac
    printf 'Created %s\n' "$index"
  else
    printf 'Kept existing %s\n' "$index"
  fi
}

PRESET_CATEGORIES=()
case "$PRESET" in
  "")
    ;;
  web)
    PRESET_CATEGORIES=(frontend guides)
    ;;
  backend)
    PRESET_CATEGORIES=(backend guides)
    ;;
  fullstack)
    PRESET_CATEGORIES=(backend frontend guides)
    ;;
  *)
    printf 'Unknown preset: %s\n' "$PRESET" >&2
    exit 1
    ;;
esac

ALL_CATEGORIES=()
for category in "${PRESET_CATEGORIES[@]-}"; do
  [[ -n "$category" ]] && ALL_CATEGORIES+=("$category")
done
for category in "${CATEGORY_ARGS[@]-}"; do
  [[ -n "$category" ]] && ALL_CATEGORIES+=("$category")
done

SEEN=""
for category in "${ALL_CATEGORIES[@]-}"; do
  [[ -z "$category" ]] && continue
  case " $SEEN " in
    *" $category "*)
      continue
      ;;
  esac
  SEEN="$SEEN $category"
  create_category "$category"
done

printf 'bootstrap-spec complete\n'
