#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/overlays}"
TARGET_DIR="$(cd "${TARGET_INPUT}" && pwd)"
TMP_PROJECT="$(mktemp -d)"
trap 'rm -rf "${TMP_PROJECT}"' EXIT

mkdir -p "${TMP_PROJECT}/.superpowers/wiki" "${TMP_PROJECT}/.shared-superpowers/wiki"
cat > "${TMP_PROJECT}/.superpowers/wiki/index.md" <<'MD'
# Project Wiki

<!-- superpower-adapter:auto:start -->
- `existing.md`
<!-- superpower-adapter:auto:end -->
MD
cat > "${TMP_PROJECT}/.superpowers/wiki/existing.md" <<'MD'
# Existing

Existing detail.
MD
cat > "${TMP_PROJECT}/.shared-superpowers/wiki/index.md" <<'MD'
# Shared Wiki

<!-- superpower-adapter:auto:start -->
<!-- superpower-adapter:auto:end -->
MD

(cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_apply_update.py" existing.md Existing "Update existing without settings." "Existing updates default to skip")

if (cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_apply_update.py" new-default.md NewDefault "Create without approval." "Should fail"); then
  printf 'Expected default create policy to require authorization\n' >&2
  exit 1
fi
(cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_apply_update.py" --authorized-create new-default.md NewDefault "Create with approval." "Authorized creates succeed")

cat > "${TMP_PROJECT}/.superpowers/settings.json" <<'JSON'
{
  "wiki": {
    "updateAuthorization": {
      "updateExistingPage": "ask",
      "createNewDocument": "ask"
    }
  }
}
JSON
if (cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_apply_update.py" existing.md ExistingAsk "Update without approval." "Should fail"); then
  printf 'Expected updateExistingPage=ask to require authorization\n' >&2
  exit 1
fi
(cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_apply_update.py" --authorized-update existing.md ExistingAsk "Update with approval." "Authorized updates succeed")

cat > "${TMP_PROJECT}/.superpowers/settings.json" <<'JSON'
{
  "wiki": {
    "updateAuthorization": {
      "createNewDocument": "refuse"
    }
  }
}
JSON
if (cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_apply_update.py" --authorized-create refused.md Refused "Create refused." "Should fail"); then
  printf 'Expected createNewDocument=refuse to reject even with authorization\n' >&2
  exit 1
fi

cat > "${TMP_PROJECT}/.shared-superpowers/settings.json" <<'JSON'
{
  "wiki": {
    "updateAuthorization": {
      "createNewDocument": "skip"
    }
  }
}
JSON
if (cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_apply_update.py" --wiki-root project --authorized-create project-refused.md ProjectRefused "Project refused." "Should fail"); then
  printf 'Expected project create refusal to stay root-specific\n' >&2
  exit 1
fi
(cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_apply_update.py" --wiki-root shared shared-allowed.md SharedAllowed "Shared allowed." "Shared create skip policy succeeds")
if [[ -e "${TMP_PROJECT}/.superpowers/wiki/shared-allowed.md" ]]; then
  printf 'Expected shared policy write not to touch project wiki\n' >&2
  exit 1
fi

mkdir -p "${TMP_PROJECT}/source"
printf '# Imported\n\nImported detail.\n' > "${TMP_PROJECT}/source/imported.md"
cat > "${TMP_PROJECT}/.superpowers/settings.json" <<'JSON'
{
  "wiki": {
    "updateAuthorization": {
      "createNewDocument": "ask"
    }
  }
}
JSON
if (cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_import.py" source --target imported-policy --merge-existing); then
  printf 'Expected wiki_import.py to require create authorization\n' >&2
  exit 1
fi
(cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_import.py" source --target imported-policy --merge-existing --authorized-create)
printf '# Imported\n\nDifferent detail.\n' > "${TMP_PROJECT}/source/imported.md"
if (cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/wiki_import.py" source --target imported-policy --merge-existing --authorized-create); then
  printf 'Expected wiki_import.py to keep refusing conflicting content\n' >&2
  exit 1
fi

cat > "${TMP_PROJECT}/.superpowers/settings.json" <<'JSON'
{
  "wiki": {
    "updateAuthorization": {
      "updateExistingPage": "ask",
      "createNewDocument": "skip"
    }
  }
}
JSON
cat > "${TMP_PROJECT}/.superpowers/wiki/summary-target.md" <<'MD'
# Summary Target

New summary text.
MD
cat > "${TMP_PROJECT}/.superpowers/wiki/index.md" <<'MD'
# Project Wiki

<!-- superpower-adapter:auto:start -->
- `summary-target.md` — Old summary text.
<!-- superpower-adapter:auto:end -->
MD
if (cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/update-wiki.py" --wiki-root project); then
  printf 'Expected update-wiki.py to require update authorization for changed indexes\n' >&2
  exit 1
fi
(cd "${TMP_PROJECT}" && python3 "${TARGET_DIR}/scripts/update-wiki.py" --wiki-root project --authorized-update)
if ! grep -Fq 'New summary text.' "${TMP_PROJECT}/.superpowers/wiki/index.md"; then
  printf 'Expected authorized index refresh to update summary\n' >&2
  exit 1
fi

printf 'wiki authorization policy smoke test complete\n'
