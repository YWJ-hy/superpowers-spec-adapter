#!/usr/bin/env bash
set -euo pipefail

REPO="${SUPERPOWER_SPEC_TEMPLATE_REPO:-YWJ-hy/superpowers-spec-adapter}"
REF="${SUPERPOWER_SPEC_TEMPLATE_REF:-main}"
TEMPLATE_NAME=""

usage() {
  printf 'Usage: %s <project-root> [--template name] [--ref ref]\n' "$0" >&2
  exit 1
}

if [[ $# -lt 1 || -z "${1:-}" ]]; then
  printf 'Missing required project root.\n' >&2
  usage
fi

REPO_ROOT="$(cd "$1" && pwd)"
shift
SPEC_ROOT="$REPO_ROOT/.superpowers/spec"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --template)
      TEMPLATE_NAME="${2:-}"
      shift 2
      ;;
    --ref)
      REF="${2:-}"
      shift 2
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage
      ;;
  esac
done

fetch_url() {
  local url="$1"
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    curl -fsSL -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github+json" "$url"
  else
    curl -fsSL -H "Accept: application/vnd.github+json" "$url"
  fi
}

list_templates() {
  local api_url="https://api.github.com/repos/${REPO}/contents/spec-template?ref=${REF}"
  local json
  if ! json="$(fetch_url "$api_url")"; then
    printf 'Failed to list templates from https://github.com/%s/tree/%s/spec-template\n' "$REPO" "$REF" >&2
    return 1
  fi
  python3 -c '
import json
import sys

try:
    items = json.loads(sys.argv[1])
except json.JSONDecodeError as exc:
    raise SystemExit(f"Invalid GitHub API response: {exc}")
if isinstance(items, dict) and items.get("message"):
    raise SystemExit(items["message"])
for item in items:
    if item.get("type") == "dir" and item.get("name"):
        print(item["name"])
' "$json"
}

select_template() {
  local templates=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && templates+=("$line")
  done < <(list_templates)

  if [[ ${#templates[@]} -eq 0 ]]; then
    printf 'No templates found under spec-template in %s@%s\n' "$REPO" "$REF" >&2
    exit 1
  fi

  if [[ -n "$TEMPLATE_NAME" ]]; then
    for template in "${templates[@]}"; do
      if [[ "$template" == "$TEMPLATE_NAME" ]]; then
        printf '%s\n' "$TEMPLATE_NAME"
        return
      fi
    done
    printf 'Unknown template: %s\n' "$TEMPLATE_NAME" >&2
    printf 'Available templates:\n' >&2
    for template in "${templates[@]}"; do
      printf '- %s\n' "$template" >&2
    done
    exit 1
  fi

  if [[ ! -t 0 ]]; then
    printf 'Missing --template in non-interactive mode. Available templates:\n' >&2
    for template in "${templates[@]}"; do
      printf '- %s\n' "$template" >&2
    done
    exit 1
  fi

  printf 'Available templates:\n' >&2
  local index=1
  for template in "${templates[@]}"; do
    printf '%d) %s\n' "$index" "$template" >&2
    index=$((index + 1))
  done

  local choice=""
  read -r -p 'Select template number: ' choice
  if ! [[ "$choice" =~ ^[0-9]+$ ]] || (( choice < 1 || choice > ${#templates[@]} )); then
    printf 'Invalid template selection: %s\n' "$choice" >&2
    exit 1
  fi
  printf '%s\n' "${templates[$((choice - 1))]}"
}

copy_template() {
  local template_dir="$1"
  local conflicts=()
  local files=()

  while IFS= read -r source; do
    files+=("$source")
    local relative="${source#$template_dir/}"
    local target="$SPEC_ROOT/$relative"
    if [[ -e "$target" ]] && ! cmp -s "$source" "$target"; then
      conflicts+=(".superpowers/spec/$relative")
    fi
  done < <(find "$template_dir" -type f | sort)

  if [[ ${#conflicts[@]} -gt 0 ]]; then
    printf 'Refusing to overwrite existing user files:\n' >&2
    for conflict in "${conflicts[@]}"; do
      printf '- %s\n' "$conflict" >&2
    done
    printf 'No files were changed.\n' >&2
    exit 1
  fi

  mkdir -p "$SPEC_ROOT"
  for source in "${files[@]}"; do
    local relative="${source#$template_dir/}"
    local target="$SPEC_ROOT/$relative"
    if [[ -e "$target" ]]; then
      printf 'Kept identical %s\n' "$target"
      continue
    fi
    mkdir -p "$(dirname "$target")"
    cp "$source" "$target"
    printf 'Created %s\n' "$target"
  done
}

SELECTED_TEMPLATE="$(select_template)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

ARCHIVE_URL="https://codeload.github.com/${REPO}/tar.gz/${REF}"
fetch_url "$ARCHIVE_URL" | tar -xz -C "$TMP_DIR"
ARCHIVE_ROOT="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
TEMPLATE_DIR="$ARCHIVE_ROOT/spec-template/$SELECTED_TEMPLATE"

if [[ ! -d "$TEMPLATE_DIR" ]]; then
  printf 'Template directory not found in archive: spec-template/%s\n' "$SELECTED_TEMPLATE" >&2
  exit 1
fi
if [[ ! -f "$TEMPLATE_DIR/index.md" ]]; then
  printf 'Template is missing index.md: %s\n' "$SELECTED_TEMPLATE" >&2
  exit 1
fi

copy_template "$TEMPLATE_DIR"
printf 'bootstrap-spec complete: imported template %s\n' "$SELECTED_TEMPLATE"
