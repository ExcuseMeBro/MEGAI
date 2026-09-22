#!/usr/bin/env bash
# Real local English + Uzbek-routed Laya smoke through one stdio bridge process.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
PY="${LAYA_PYTHON:-$MEGAI_HOME/venv/laya/bin/python}"

if [ ! -x "$PY" ]; then
  printf 'blocked: no owned Laya interpreter at %s — run `bash lib/install_laya.sh`\n' "$PY" >&2
  exit 2
fi

for pattern in 'import requests' 'urllib.request' 'http.client' 'typesafe' 'TYPESAFE_'; do
  if grep -qi -- "$pattern" "$ROOT/pi-skill/laya/bridge.py"; then
    printf 'FAIL: the bridge names a network client or hosted service: %s\n' "$pattern" >&2
    exit 1
  fi
done

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/request.jsonl" <<'JSONL'
{"id":"live-en","state":"The task is a routine documentation fix in one file.","questions":{"mode":{"type":"choice","instructions":"How should this be handled?","criteria":{"routine":"ordinary bounded work","guarded":"consequential work needing review"}},"effort":{"type":"score","instructions":"How much implementation work is this?","criteria":["one file","a few files","architecture"]},"continue":{"type":"noul","instructions":"Should the agent continue with this bounded task?"}}}
{"id":"live-uz","lang":"uz","state":"Bu bitta fayldagi oddiy hujjat tuzatishi.","questions":{"mode":{"type":"choice","instructions":"How should this be handled?","criteria":{"routine":"ordinary bounded work","guarded":"consequential work needing review"}},"effort":{"type":"score","instructions":"How much implementation work is this?","criteria":["one file","a few files","architecture"]},"continue":{"type":"noul","instructions":"Should the agent continue with this bounded task?"}}}
JSONL

started=$(date +%s)
env -u TYPESAFE_API_KEY -u TYPESAFE_ENDPOINT -u TYPESAFE_TIMEOUT_MS \
  -u JEV_LOG -u LAYA_LANG ${LAYA_DEVICE:+LAYA_DEVICE="$LAYA_DEVICE"} \
  "$PY" -B "$ROOT/pi-skill/laya/bridge.py" \
  < "$tmp/request.jsonl" > "$tmp/response.jsonl" 2> "$tmp/bridge.log"
elapsed=$(( $(date +%s) - started ))

python3 - "$tmp/response.jsonl" "$tmp/bridge.log" "$elapsed" <<'PY'
import json
import sys

responses = [json.loads(line) for line in open(sys.argv[1], encoding="utf-8") if line.strip()]
log = open(sys.argv[2], encoding="utf-8").read()
elapsed = sys.argv[3]
assert [item["id"] for item in responses] == ["live-en", "live-uz"], responses
assert all(item["ok"] for item in responses), responses
english, uzbek = responses
assert english["route"] == "english", english
assert uzbek["route"] == "multilingual" and uzbek["lang"] == "uz", uzbek
for response in responses:
    answers = response["answers"]
    assert answers["mode"]["type"] == "choice"
    assert answers["mode"]["choice"] in {"routine", "guarded"}
    assert answers["effort"]["type"] == "score"
    assert isinstance(answers["effort"]["score"], (int, float))
    assert answers["continue"]["type"] == "noul"
    assert 0.0 <= answers["continue"]["noul"] <= 1.0
    assert response["usage"]["output_tokens"] == 0
loads = [line for line in log.splitlines() if "laya: loaded " in line]
assert len(loads) == 2, f"expected exactly one load per route: {loads}"
assert sum("loaded english=" in line for line in loads) == 1, loads
assert sum("loaded multilingual=" in line for line in loads) == 1, loads
assert "typed-decisions" not in log.lower(), log
assert "typesafe" not in log.lower(), log
print(f"PASS: real local Laya router — routes=english,multilingual answers=choice/score/noul "
      f"output_tokens=0 loads=2 process=1 elapsed={elapsed}s")
PY
