#!/usr/bin/env bash
# Behavior smoke test for the post-merge update-wiki PostToolUse hook.
# Feeds synthesized PostToolUse payloads to the installed hook script and asserts
# when it injects an update-wiki reminder and when it stays silent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
TARGET_DIR="$(cd "${TARGET_INPUT}" && pwd)"

HOOK="${TARGET_DIR}/hooks/post-merge-update-wiki"
if [[ ! -f "$HOOK" ]]; then
  printf 'Expected installed hook script: %s\n' "$HOOK" >&2
  exit 1
fi

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

# Build a PostToolUse JSON payload for a Bash command run in a given cwd.
build_json() { # $1=command  $2=cwd
  CMD="$1" CWD="$2" python3 -c '
import json, os
print(json.dumps({
    "hook_event_name": "PostToolUse",
    "tool_name": "Bash",
    "cwd": os.environ["CWD"],
    "tool_input": {"command": os.environ["CMD"]},
    "tool_response": {"stdout": "", "stderr": "", "interrupted": False},
}))'
}

run_hook() { # $1=command  $2=cwd  -> prints hook stdout
  build_json "$1" "$2" | env -u CURSOR_PLUGIN_ROOT -u COPILOT_CLI CLAUDE_PLUGIN_ROOT=test bash "$HOOK"
}

assert_fires() { # $1=command  $2=cwd  $3=label
  local out
  out="$(run_hook "$1" "$2")"
  if ! grep -Fq 'update-wiki' <<<"$out"; then
    printf 'FAIL [%s]: expected reminder for command %q in %s\nGot: %s\n' "$3" "$1" "$2" "$out" >&2
    exit 1
  fi
  if ! grep -Fq 'additionalContext' <<<"$out"; then
    printf 'FAIL [%s]: reminder missing additionalContext for %q\nGot: %s\n' "$3" "$1" "$out" >&2
    exit 1
  fi
  printf 'ok (fires): %s\n' "$3"
}

assert_silent() { # $1=command  $2=cwd  $3=label
  local out
  out="$(run_hook "$1" "$2")"
  if [[ -n "$out" ]]; then
    printf 'FAIL [%s]: expected no reminder for command %q in %s\nGot: %s\n' "$3" "$1" "$2" "$out" >&2
    exit 1
  fi
  printf 'ok (silent): %s\n' "$3"
}

git_init() { # $1=path
  git -c init.defaultBranch=main init -q "$1"
  git -C "$1" -c user.email=a@b.c -c user.name=test commit -q --allow-empty -m init
}

# --- Repo with a project wiki, no worktree metadata -------------------------
REPO="$WORK/repo"
git_init "$REPO"
mkdir -p "$REPO/.superpowers/wiki"

# Finalize direction: merging a feature branch into the current branch -> fire.
assert_fires "git merge feature" "$REPO" "merge feature into main"
assert_fires "git merge --no-ff feature/login" "$REPO" "merge feature with --no-ff"
assert_fires "git checkout iter-2026 && git merge feature/login" "$REPO" "compound checkout + merge into iteration branch"
assert_fires "gh pr merge 42 --squash" "$REPO" "gh pr merge"

# Sync direction without metadata: merging the trunk INTO the branch -> silent.
assert_silent "git merge main" "$REPO" "sync main into feature"
assert_silent "git merge master" "$REPO" "sync master into feature"
assert_silent "git merge origin/main" "$REPO" "sync origin/main into feature"

# Non-merge and abort commands -> silent.
assert_silent "git status" "$REPO" "non-merge git command"
assert_silent "git commit -m done" "$REPO" "commit is not a merge"
assert_silent "git merge --abort" "$REPO" "merge --abort"

# --- Missing project wiki -> always silent ----------------------------------
NOWIKI="$WORK/nowiki"
git_init "$NOWIKI"
assert_silent "git merge feature" "$NOWIKI" "no .superpowers/wiki present"

# --- Worktree origin metadata: exact direction check ------------------------
# The user's case: a worktree created from an iteration branch (not main),
# finalized by merging back into that iteration branch. The trunk heuristic
# cannot recognize the iteration branch, so the metadata must drive the call.
META="$WORK/meta"
git_init "$META"
mkdir -p "$META/.superpowers/wiki"
GIT_DIR_ABS="$(git -C "$META" rev-parse --absolute-git-dir)"
mkdir -p "$GIT_DIR_ABS/superpower-adapter"
cat >"$GIT_DIR_ABS/superpower-adapter/worktree-origin.json" <<'JSON'
{
  "schemaVersion": 1,
  "adapter": "superpower-adapter",
  "featureBranch": "feature/login",
  "originalBranch": "iter-2026-q2",
  "originalWorktree": "/tmp/orig",
  "originalHead": "deadbeef"
}
JSON

# Finalize: merging the feature branch into the iteration branch -> fire.
assert_fires "git merge feature/login" "$META" "metadata finalize (feature -> iteration branch)"
# Sync: merging the recorded iteration branch back in -> silent, even though
# the iteration branch name is not a trunk name.
assert_silent "git merge iter-2026-q2" "$META" "metadata sync (iteration branch -> feature)"

# --- Conflict guard: do not nag while a merge is unfinished ------------------
CONFLICT="$WORK/conflict"
git -c init.defaultBranch=main init -q "$CONFLICT"
gitc() { git -C "$CONFLICT" -c user.email=a@b.c -c user.name=test -c commit.gpgsign=false "$@"; }
printf 'A\n' >"$CONFLICT/file.txt"
gitc add file.txt
gitc commit -q -m base
mkdir -p "$CONFLICT/.superpowers/wiki"
gitc checkout -q -b feature
printf 'B\n' >"$CONFLICT/file.txt"
gitc commit -q -am feature-change
gitc checkout -q main
printf 'C\n' >"$CONFLICT/file.txt"
gitc commit -q -am main-change
# This merge conflicts and leaves MERGE_HEAD set.
if gitc merge feature >/dev/null 2>&1; then
  printf 'FAIL: expected merge to conflict for the conflict-guard case\n' >&2
  exit 1
fi
assert_silent "git merge feature" "$CONFLICT" "conflict in progress (MERGE_HEAD set)"
gitc merge --abort

printf 'post-merge update-wiki hook smoke test complete\n'
