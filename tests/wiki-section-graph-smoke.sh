#!/usr/bin/env bash
set -euo pipefail

# Smoke test for the section-level knowledge graph: [[page#section]] edge parsing,
# .graph.json output, .index.md cross-reference columns, and dangling-link lint.
# Exercises the installed Superpowers target scripts.
# Usage: bash tests/wiki-section-graph-smoke.sh [superpowers-target] [project-root]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_INPUT="${1:-${ROOT}/../superpowers}"
SCRIPTS="${TARGET_INPUT}/scripts"

TMP_PROJECT="$(mktemp -d)"
trap 'rm -rf "${TMP_PROJECT}"' EXIT

W="${TMP_PROJECT}/.superpowers/wiki"
mkdir -p "${W}/backend"

cat > "${W}/index.md" <<'MD'
# Project Wiki
- `backend/`
MD

cat > "${W}/backend/index.md" <<'MD'
# Backend
- `contract.md`
- `data.md`
MD

cat > "${W}/backend/contract.md" <<'MD'
# Contract
<!-- wiki-section:response-format -->
## Response
必须 follow [[backend/data#tx-rules]] and see the whole page [[backend/data]].
Broken section [[backend/data#nope]] and missing page [[backend/ghost#x]].
Inline `[[not-an-edge#z]]` and a plain link [text](backend/data.md#tx-rules) are ignored.
<!-- /wiki-section:response-format -->
MD

cat > "${W}/backend/data.md" <<'MD'
# Data
<!-- wiki-section:tx-rules -->
## Tx
rules here
<!-- /wiki-section:tx-rules -->
MD

# --- Build the graph (--all) ---
python3 "${SCRIPTS}/wiki_generate_section_index.py" --all --wiki-root project --project-root "${TMP_PROJECT}" >/dev/null

GRAPH="${W}/.graph.json"
if [[ ! -f "${GRAPH}" ]]; then
  printf 'Expected .graph.json to be generated\n' >&2
  exit 1
fi

python3 - <<'PY' "${GRAPH}"
import json, sys
g = json.loads(open(sys.argv[1], encoding="utf-8").read())

src = "backend/contract.md#response-format"
edges = {(e["from"], e["to"]) for e in g["edges"]}
assert (src, "backend/data.md#tx-rules") in edges, "missing section edge"
assert (src, "backend/data.md") in edges, "missing page-level edge"
# Inline-code and plain markdown links must not become edges.
assert all("not-an-edge" not in e["to"] for e in g["edges"]), "inline-code link leaked"
assert len(g["edges"]) == 2, f"unexpected edge count: {g['edges']}"

assert g["backlinks"].get("backend/data.md#tx-rules") == [src], "missing section backlink"
assert g["backlinks"].get("backend/data.md") == [src], "missing page backlink"

reasons = sorted(d["reason"] for d in g["dangling"])
assert len(g["dangling"]) == 2, f"unexpected dangling count: {g['dangling']}"
assert any("section 'nope' not found" in r for r in reasons), "missing dangling-section reason"
assert any("page does not exist" in r for r in reasons), "missing dangling-page reason"
print("graph.json OK")
PY

# --- .index.md cross-reference columns ---
contract_index="$(cat "${W}/backend/contract.index.md")"
data_index="$(cat "${W}/backend/data.index.md")"
case "${contract_index}" in
  *"| 引用 | 被引用 |"*) : ;;
  *) printf 'Expected cross-reference columns in contract.index.md\n' >&2; exit 1 ;;
esac
case "${contract_index}" in
  *"backend/data.md#tx-rules"*) : ;;
  *) printf 'Expected outgoing reference in contract.index.md\n' >&2; exit 1 ;;
esac
case "${data_index}" in
  *"backend/contract.md#response-format"*) : ;;
  *) printf 'Expected backlink in data.index.md\n' >&2; exit 1 ;;
esac

# --- Single-file mode also rebuilds the root graph (update-wiki uses this path) ---
rm -f "${GRAPH}"
python3 "${SCRIPTS}/wiki_generate_section_index.py" backend/contract.md --wiki-root project --project-root "${TMP_PROJECT}" >/dev/null
if [[ ! -f "${GRAPH}" ]]; then
  printf 'Expected single-file mode to rebuild .graph.json\n' >&2
  exit 1
fi
python3 - <<'PY' "${GRAPH}"
import json, sys
g = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert len(g["edges"]) == 2, "single-file rebuild lost edges"
assert len(g["dangling"]) == 2, "single-file rebuild lost dangling"
print("single-file rebuild OK")
PY

# --- Dangling links are reported as warnings by the validator ---
check_json="$(cd "${TMP_PROJECT}" && python3 "${SCRIPTS}/wiki_update_check.py" --wiki-root project --json)"
python3 - <<'PY' "${check_json}"
import json, sys
r = json.loads(sys.argv[1])
assert r["status"] == "warning", f"expected warning status, got {r['status']}"
root = r["roots"][0]
assert root.get("danglingSectionLinks") == 2, f"expected 2 dangling links, got {root.get('danglingSectionLinks')}"
dangling_warnings = [w for w in r["warnings"] if "dangling section link" in w]
assert len(dangling_warnings) == 2, f"expected 2 dangling warnings, got {dangling_warnings}"
print("dangling-link lint OK")
PY

printf 'wiki-section-graph-smoke complete\n'
