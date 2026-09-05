#!/usr/bin/env bash
# Real pinned CLI contract; offline after installation, no writes to the checkout.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$(command -v openspec)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" XDG_CONFIG_HOME="$TMP/config" OPENSPEC_TELEMETRY=0
mkdir -p "$HOME" "$TMP/repo"
cp -R "$ROOT/openspec" "$TMP/repo/"
cd "$TMP/repo"
[ "$("$CLI" --version)" = 1.12.0 ]
# Always exercise incomplete implementation, even after source tasks are checked.
python3 - <<'PY'
from pathlib import Path
p=Path('openspec/changes/selective-openspec/tasks.md')
p.write_text(p.read_text().replace('- [x]', '- [ ]'))
PY
"$CLI" validate selective-openspec --type change --strict --no-interactive --json >"$TMP/valid.json"
"$CLI" status --change selective-openspec --json >"$TMP/status.json"
"$CLI" instructions apply --change selective-openspec --json >"$TMP/apply.json"
"$CLI" instructions archive --change selective-openspec --json >"$TMP/archive.json"
"$CLI" instructions specs --change selective-openspec --json >"$TMP/specs.json"
python3 - "$TMP" <<'PY'
import json,sys
from pathlib import Path
base=Path(sys.argv[1])
def load(name): return json.loads((base/(name+'.json')).read_text())
status=load('status')
assert status['isPlanningComplete'] is True
assert all(x['status']=='done' for x in status['artifacts'])
apply=load('apply')
assert apply['tasks'] and all(not t['done'] for t in apply['tasks'])
assert 'Asana' in apply['context']
assert any('actual focused tests' in rule for rule in apply['operationGuidance'])
archive=load('archive')
assert any('explicit user approval' in rule for rule in archive['operationGuidance'])
assert any('completed=false' in rule for rule in archive['operationGuidance'])
assert any('WHEN/THEN' in rule for rule in load('specs')['rules'])
print('Real CLI: context/rules injected; planning complete with unchecked implementation tasks')
PY
printf '\n### Requirement: Missing scenario\nThe integration SHALL reject malformed requirements.\n' >>openspec/changes/selective-openspec/specs/selective-spec-workflow/spec.md
if "$CLI" validate selective-openspec --type change --strict --no-interactive --json >"$TMP/invalid.json"; then
  echo 'Malformed requirement unexpectedly validated' >&2
  exit 1
fi
python3 - "$TMP/invalid.json" <<'PY'
import json,sys
result=json.load(open(sys.argv[1]))
assert 'scenario' in json.dumps(result).lower(), result
print('Real CLI: missing-scenario spec rejected')
PY
