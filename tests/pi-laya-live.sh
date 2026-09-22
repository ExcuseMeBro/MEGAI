#!/usr/bin/env bash
# Real local English -> Uzbek -> English -> Uzbek smoke through one owned bridge.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
PY="${LAYA_PYTHON:-$MEGAI_HOME/venv/laya/bin/python}"

if [ ! -x "$PY" ]; then
  printf 'blocked: no owned Laya interpreter at %s — run `bash lib/install_laya.sh`\n' "$PY" >&2
  exit 2
fi

for pattern in 'import requests' 'urllib.request' 'http.client' 'http://' 'https://'; do
  if grep -qi -- "$pattern" "$ROOT/pi-skill/laya/bridge.py"; then
    printf 'FAIL: the bridge names a network client or endpoint: %s\n' "$pattern" >&2
    exit 1
  fi
done

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# Start from an empty environment: no parent import override or credential can alter
# which package is imported. Preserve only cache locations and force cache-only mode.
run_env=(env -i "HOME=$HOME" "PATH=/usr/bin:/bin" "PYTHONNOUSERSITE=1"
  "HF_HUB_OFFLINE=1" "TRANSFORMERS_OFFLINE=1" "HF_HUB_DISABLE_TELEMETRY=1")
for name in TMPDIR LANG LC_ALL XDG_CACHE_HOME HF_HOME HF_HUB_CACHE TRANSFORMERS_CACHE TORCH_HOME; do
  if [ -n "${!name:-}" ]; then run_env+=("$name=${!name}"); fi
done
if [ -n "${LAYA_DEVICE:-}" ]; then run_env+=("LAYA_DEVICE=$LAYA_DEVICE"); fi

provenance="$("${run_env[@]}" "$PY" -I - <<'PY'
import importlib.metadata
import json
from pathlib import Path
import sys

import laya

prefix = Path(sys.prefix).resolve()
module = Path(laya.__file__).resolve()
version = importlib.metadata.version("laya")
assert (prefix / ".megai-owned").is_file(), f"unowned interpreter prefix: {prefix}"
assert module.is_relative_to(prefix), f"laya imported outside owned venv: {module}"
assert version == "0.3.5", f"unexpected laya version: {version}"
print(json.dumps({"prefix": str(prefix), "module": str(module), "version": version}))
PY
)"

cat > "$tmp/request.jsonl" <<'JSONL'
{"id":"live-en-1","state":"The task is a routine documentation fix in one file.","questions":{"mode":{"type":"choice","instructions":"How should this be handled?","criteria":{"routine":"ordinary bounded work","guarded":"consequential work needing review"}},"effort":{"type":"score","instructions":"How much implementation work is this?","criteria":["one file","a few files","architecture"]},"continue":{"type":"noul","instructions":"Should the agent continue with this bounded task?"}}}
{"id":"live-uz-1","lang":"uz","state":"Bu bitta fayldagi oddiy hujjat tuzatishi.","questions":{"mode":{"type":"choice","instructions":"How should this be handled?","criteria":{"routine":"ordinary bounded work","guarded":"consequential work needing review"}},"effort":{"type":"score","instructions":"How much implementation work is this?","criteria":["one file","a few files","architecture"]},"continue":{"type":"noul","instructions":"Should the agent continue with this bounded task?"}}}
{"id":"live-en-2","state":"The task is a routine documentation fix in one file.","questions":{"mode":{"type":"choice","instructions":"How should this be handled?","criteria":{"routine":"ordinary bounded work","guarded":"consequential work needing review"}},"effort":{"type":"score","instructions":"How much implementation work is this?","criteria":["one file","a few files","architecture"]},"continue":{"type":"noul","instructions":"Should the agent continue with this bounded task?"}}}
{"id":"live-uz-2","lang":"uz","state":"Bu bitta fayldagi oddiy hujjat tuzatishi.","questions":{"mode":{"type":"choice","instructions":"How should this be handled?","criteria":{"routine":"ordinary bounded work","guarded":"consequential work needing review"}},"effort":{"type":"score","instructions":"How much implementation work is this?","criteria":["one file","a few files","architecture"]},"continue":{"type":"noul","instructions":"Should the agent continue with this bounded task?"}}}
JSONL

started=$(date +%s)
"${run_env[@]}" "$PY" -I -B "$ROOT/pi-skill/laya/bridge.py" \
  < "$tmp/request.jsonl" > "$tmp/response.jsonl" 2> "$tmp/bridge.log"
elapsed=$(( $(date +%s) - started ))

python3 - "$tmp/response.jsonl" "$tmp/bridge.log" "$elapsed" "$provenance" <<'PY'
import json
import sys

responses = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
log = open(sys.argv[2], encoding="utf-8").read()
elapsed = sys.argv[3]
provenance = json.loads(sys.argv[4])
assert [item["id"] for item in responses] == ["live-en-1", "live-uz-1", "live-en-2", "live-uz-2"], responses
assert all(item["ok"] for item in responses), responses
assert [item["route"] for item in responses] == ["english", "multilingual", "english", "multilingual"], responses
assert [item["lang"] for item in responses] == [None, "uz", None, "uz"], responses
for response in responses:
    answers = response["answers"]
    assert answers["mode"]["type"] == "choice"
    assert answers["mode"]["choice"] in {"routine", "guarded"}
    assert answers["effort"]["type"] == "score"
    assert isinstance(answers["effort"]["score"], (int, float))
    assert answers["continue"]["type"] == "noul"
    assert 0.0 <= answers["continue"]["noul"] <= 1.0
    assert response["usage"]["output_tokens"] == 0
router_ready = [line for line in log.splitlines() if "laya: router ready " in line]
loads = [line for line in log.splitlines() if "laya: loaded " in line]
answered = [line for line in log.splitlines() if "laya: answered " in line]
assert len(router_ready) == 1, f"expected one Router/process: {router_ready}"
assert len(loads) == 2, f"expected exactly one load per route: {loads}"
assert sum("loaded english=" in line for line in loads) == 1, loads
assert sum("loaded multilingual=" in line for line in loads) == 1, loads
assert len(answered) == 4, answered
assert "typed-decisions" not in log.lower(), log
print(f"PASS: owned laya=={provenance['version']} ({provenance['module']}) — "
      f"routes=english,multilingual,english,multilingual answers=choice/score/noul "
      f"output_tokens=0 loads=2 routers=1 process=1 elapsed={elapsed}s")
PY
