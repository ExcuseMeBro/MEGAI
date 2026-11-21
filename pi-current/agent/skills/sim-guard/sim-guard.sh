#!/bin/bash
# sim-guard: keep AI coding agents from overloading the Mac with iOS simulators.
# Adapted for MEGAI from https://github.com/annayal-consumerxai/sim-guard @5d706a4 (MIT, An Nayal).
# Changes: init creates dedicated "sim-guard-N" sims and never adopts existing ones; a global lock
# makes the cap and pool choice atomic across agents; per-sim leases record the owner; release
# refuses sims outside the pool; UDIDs match exactly.
#
#   sim-guard init [N]               create/reuse N dedicated pool sims on the newest iOS runtime and slim them (default: SIM_CAP)
#   sim-guard audit                  booted sims: RAM, CPU, slim or not, pool/lease or orphan
#   sim-guard preflight              audit, then exit 1 if at the cap or Mac memory is low
#   sim-guard acquire                preflight, then boot a free pool sim (slim) and print "ACQUIRED <udid>"
#   sim-guard release <udid> [--keep-apps]
#                                    pool sims only: remove user apps, reset keychain, shut down, drop the lease
#
# Settings (env vars):
#   SIM_CAP           max booted sims machine-wide (default 2)
#   MIN_FREE_PCT      refuse to boot below this % of free memory (default 25)
#   SIMSLIM_EXCEPT    simslim categories to keep on (default "store,web": StoreKit, push, universal links)
#   SIM_GUARD_HOME    state folder (default ~/.config/sim-guard): pool file, leases, lock
#   SIM_GUARD_OWNER   label written to the lease (default: agent name + parent PID)
#   SIM_GUARD_LOCK_WAIT  seconds to wait for the lock (default 900: a slim boot can take minutes)

set -u
CAP="${SIM_CAP:-2}"
MIN_FREE="${MIN_FREE_PCT:-25}"
EXCEPT="${SIMSLIM_EXCEPT:-store,web}"
HOME_DIR="${SIM_GUARD_HOME:-$HOME/.config/sim-guard}"
CONFIG="$HOME_DIR/pool"
LEASES="$HOME_DIR/leases"
LOCK="$HOME_DIR/lock"
LOCK_WAIT="${SIM_GUARD_LOCK_WAIT:-900}"
PREFIX="sim-guard-"
UDID_RE='^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$'

need() { command -v "$1" >/dev/null || { echo "missing: $1 ($2)"; exit 2; }; }
need xcrun "install Xcode"
need simslim "brew install mobai-app/tap/simslim"
need python3 "xcode-select --install"
case "$CAP" in ''|*[!0-9]*) echo "SIM_CAP must be a number"; exit 2 ;; esac
case "$MIN_FREE" in ''|*[!0-9]*) echo "MIN_FREE_PCT must be a number"; exit 2 ;; esac
mkdir -p "$HOME_DIR" "$LEASES" && chmod 700 "$HOME_DIR" 2>/dev/null

# Pool: one UDID per line (comments after #). Kept as a newline list (bash 3.2 safe).
pool_udids() { [ -f "$CONFIG" ] && sed -e 's/#.*//' -e 's/[[:space:]]//g' "$CONFIG" | grep -E "$UDID_RE" || true; }
in_pool() { pool_udids | grep -qx "$1"; }

free_pct() { memory_pressure 2>/dev/null | awk -F': ' '/free percentage/{gsub("%","",$2); print $2}'; }

booted_udids() {
  xcrun simctl list devices booted --json | python3 -c '
import json,sys
for devs in json.load(sys.stdin)["devices"].values():
    for d in devs:
        if d.get("state")=="Booted": print(d["udid"])'
}
is_booted() { booted_udids | grep -qx "$1"; }

# --- lock: mkdir is atomic; a lock whose holder PID is gone is stale and removed. ---
HAVE_LOCK=""
lock() {
  local waited=0 pid
  while ! mkdir "$LOCK" 2>/dev/null; do
    pid="$(cat "$LOCK/pid" 2>/dev/null || true)"
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
      echo "Removing stale sim-guard lock (pid $pid is gone)." >&2
      rm -rf "$LOCK"; continue
    fi
    if [ -z "$pid" ] && [ "$waited" -ge 5 ]; then rm -rf "$LOCK"; continue; fi  # half-written lock
    [ "$waited" -ge "$LOCK_WAIT" ] && { echo "BLOCKED: sim-guard lock busy for ${LOCK_WAIT}s (holder pid ${pid:-?})."; exit 1; }
    sleep 1; waited=$((waited + 1))
  done
  echo $$ > "$LOCK/pid"
  HAVE_LOCK=1
  trap unlock EXIT
  trap 'unlock; exit 130' INT TERM
}
unlock() { [ -n "$HAVE_LOCK" ] && rm -rf "$LOCK"; HAVE_LOCK=""; }

owner_label() { echo "${SIM_GUARD_OWNER:-$(ps -o comm= -p "$PPID" 2>/dev/null | xargs basename 2>/dev/null || echo agent)[$PPID]}"; }

init_pool() {
  local n="${1:-$CAP}"
  case "$n" in ''|*[!0-9]*|0) echo "usage: sim-guard init [N>0]"; return 2 ;; esac
  lock
  # Pick the newest iOS runtime and a device type: the newest existing iPhone's type there, else the highest-numbered iPhone.
  local plan
  plan="$(xcrun simctl list runtimes --json | python3 -c '
import json,re,sys
rts=[r for r in json.load(sys.stdin)["runtimes"] if r.get("platform")=="iOS" and r.get("isAvailable")]
if not rts: sys.exit("no iOS runtime installed")
def ver(r): return tuple(int(x) for x in re.findall(r"\d+", r.get("version","0")))
rt=max(rts,key=ver)
phones=[d["identifier"] for d in rt.get("supportedDeviceTypes",[]) if d.get("productFamily")=="iPhone"]
def num(t):
    m=re.search(r"iPhone-(\d+)",t); return int(m.group(1)) if m else 0
print(rt["identifier"], max(phones,key=lambda t:(num(t),"Pro" in t and "Max" not in t)) if phones else "")')" || return 1
  local runtime devtype; runtime="${plan%% *}"; devtype="${plan#* }"
  local existing
  existing="$(xcrun simctl list devices --json | RT="$runtime" PREFIX="$PREFIX" python3 -c '
import json,os,sys
devs=json.load(sys.stdin)["devices"]
rt=os.environ["RT"]
own={d["name"]:d["udid"] for d in devs.get(rt,[]) if d.get("isAvailable") and d["name"].startswith(os.environ["PREFIX"])}
other=[d for d in devs.get(rt,[]) if d.get("isAvailable") and d["name"].startswith("iPhone") and not d["name"].startswith(os.environ["PREFIX"])]
for name,u in sorted(own.items()): print("OWN", name, u)
if other: print("TYPE", other[-1]["deviceTypeIdentifier"])')"
  local t; t="$(echo "$existing" | awk '$1=="TYPE"{print $2}' | tail -1)"; [ -n "$t" ] && devtype="$t"
  [ -z "$devtype" ] && { echo "No iPhone device type for $runtime."; return 1; }
  local tmp="$CONFIG.tmp.$$" i name u
  echo "# sim-guard pool: dedicated sims for agents. Never put a sim you use by hand here." > "$tmp"
  i=1
  while [ "$i" -le "$n" ]; do
    name="${PREFIX}${i}"
    u="$(echo "$existing" | awk -v n="$name" '$1=="OWN" && $2==n {print $3}')"
    if [ -z "$u" ]; then
      u="$(xcrun simctl create "$name" "$devtype" "$runtime")" || { rm -f "$tmp"; return 1; }
      echo "Created $name $u (${devtype##*.}, ${runtime##*.})"
    else
      echo "Reusing $name $u"
    fi
    echo "$u # $name ${runtime##*.}" >> "$tmp"
    i=$((i + 1))
  done
  mv "$tmp" "$CONFIG"
  echo "Pool written to $CONFIG"
  for u in $(pool_udids); do
    echo "Slimming $u (keeps: $EXCEPT)..."
    simslim on "$u" --except "$EXCEPT" --preserve-boot-state | tail -1
  done
}

audit() {
  local snap; snap="$(simslim top --json 2>/dev/null)"
  SNAP="$snap" POOL_LIST="$(pool_udids)" LEASES="$LEASES" CAP="$CAP" python3 - <<'PY'
import json, os, subprocess
pool = set(os.environ["POOL_LIST"].split())
cap = int(os.environ["CAP"])
def lease(u):
    try: return open(os.path.join(os.environ["LEASES"], u)).read().strip()
    except OSError: return ""
try: sims = json.loads(os.environ["SNAP"] or "{}").get("sims") or []  # simslim prints null when none are booted
except Exception: sims = []
sims = [s for s in sims if s.get("state") == "Booted"]
total = sum(s.get("memory", {}).get("bytes", 0) for s in sims)
print(f"Booted simulators: {len(sims)} (cap {cap}), total RAM {total/1e9:.2f} GB")
if not pool: print("No pool yet. Run: sim-guard init")
orphans = []
for s in sims:
    mem = s.get("memory", {})
    dis, tot = s.get("managedDisabled", 0), s.get("managedTotal", 0) or 1
    slim = "slim" if dis / tot > 0.5 and mem.get("bytes", 0) < 1.5e9 else "NOT slim"
    if s["udid"] in pool: owner = "pool, lease: " + (lease(s["udid"]) or "none")
    else: owner = "orphan"; orphans.append(s)
    print(f"  {s['udid']}  {s['name']:<20} {s.get('platform','')} {s.get('osVersion',''):<5} "
          f"{mem.get('bytes',0)/1e9:5.2f} GB  {mem.get('processes',0):>3} procs  cpu {mem.get('cpu',0):.1f}%  {slim}  [{owner}]")
ps = subprocess.run(["ps","-axo","comm="], capture_output=True, text=True).stdout.lower()
hints = [n for n in ("xcodebuild","simulator","codex","claude","pi-bolt") if n in ps]
print("Agent/sim tooling running:", ", ".join(hints) or "none")
if orphans:
    print("Orphans (not in the pool; may be a sim the user or another tool is using). Ask before shutting down:")
    for s in orphans: print(f"  simslim shutdown {s['udid']}")
if len(sims) > cap: print(f"OVER CAP by {len(sims)-cap}.")
PY
  echo "Mac memory free: $(free_pct)% (floor ${MIN_FREE}%)"
}

check_capacity() {
  local n free; n=$(booted_udids | grep -c . | tr -d ' '); free=$(free_pct)
  if [ "$n" -ge "$CAP" ]; then
    echo "BLOCKED: $n sims booted, cap is $CAP. Reuse a pool sim you own, wait, or ask about an orphan."
    return 1
  fi
  if [ -n "$free" ] && [ "$free" -lt "$MIN_FREE" ]; then
    echo "BLOCKED: only ${free}% memory free. Close something before booting a sim."
    return 1
  fi
  echo "OK to boot one more sim."
}

preflight() { audit; check_capacity; }

acquire() {
  [ -z "$(pool_udids)" ] && { echo "No pool yet. Run: sim-guard init"; return 1; }
  lock   # held through the boot, so the cap and the pick are atomic across agents
  audit
  check_capacity || return 1
  local u
  for u in $(pool_udids); do
    is_booted "$u" && continue
    echo "owner=$(owner_label) since=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LEASES/$u"
    echo "Booting pool sim $u (slim)..."
    if ! simslim boot "$u" >/dev/null; then rm -f "$LEASES/$u"; echo "Boot failed for $u"; return 1; fi
    if ! simslim verify "$u" --except "$EXCEPT" >/dev/null 2>&1; then
      echo "Slim profile drifted, re-applying..."
      simslim on "$u" --except "$EXCEPT" >/dev/null || { rm -f "$LEASES/$u"; return 1; }
    fi
    simslim measure "$u"
    echo "ACQUIRED $u"
    return 0
  done
  echo "BLOCKED: every pool sim is already booted. Reuse one you own, or wait."
  return 1
}

release() {
  local u="${1:-}" keep="${2:-}"
  [ -z "$u" ] && { echo "usage: sim-guard release <udid> [--keep-apps]"; return 2; }
  echo "$u" | grep -Eq "$UDID_RE" || { echo "Not a simulator UDID: $u"; return 2; }
  in_pool "$u" || { echo "REFUSED: $u is not a sim-guard pool sim. sim-guard never wipes other simulators."; return 2; }
  [ -n "$keep" ] && [ "$keep" != "--keep-apps" ] && { echo "usage: sim-guard release <udid> [--keep-apps]"; return 2; }
  lock
  if [ "$keep" != "--keep-apps" ] && is_booted "$u"; then
    xcrun simctl listapps "$u" 2>/dev/null | plutil -convert json -o - - 2>/dev/null | python3 -c '
import json,sys
try: apps=json.load(sys.stdin)
except Exception: apps={}
for bid,a in apps.items():
    if a.get("ApplicationType")=="User": print(bid)' | while read -r bid; do
      echo "uninstall $bid"; xcrun simctl uninstall "$u" "$bid"
    done
    xcrun simctl keychain "$u" reset && echo "keychain reset"
  fi
  if is_booted "$u"; then simslim shutdown "$u" >/dev/null || { echo "Shutdown failed for $u"; return 1; }; fi
  rm -f "$LEASES/$u"
  echo "RELEASED $u"
}

case "${1:-audit}" in
  init) shift; init_pool "$@" ;;
  audit) audit ;;
  preflight) preflight ;;
  acquire) acquire ;;
  release) shift; release "$@" ;;
  *) sed -n 2,23p "$0"; exit 2 ;;
esac
