#!/bin/bash
# sim-guard: keep AI coding agents from overloading the Mac with iOS simulators.
# Adapted for MEGAI from https://github.com/annayal-consumerxai/sim-guard @5d706a4 (MIT, An Nayal).
# Changes: init creates dedicated sims and records their UDIDs (never adopts a sim by name); a kernel
# lock (flock, released when the holder dies) makes the cap and pool pick atomic across agents; each
# acquisition gets a lease token that release must present; unreadable telemetry blocks instead of
# allowing a boot; cleanup failures keep the lease; release refuses sims outside the pool.
#
#   sim-guard init [N]               create N dedicated pool sims on the newest iOS runtime and slim them (default: SIM_CAP)
#   sim-guard audit                  booted sims: RAM, CPU, slim or not, pool lease or orphan
#   sim-guard preflight              audit, then exit 1 if at the cap, memory is low, or state can't be read
#   sim-guard acquire                boot a free pool sim and print "ACQUIRED <udid> <lease-token>"
#   sim-guard release <udid> <lease-token> [--keep-apps]
#                                    remove user apps, reset keychain, shut down, drop the lease
#   sim-guard release <udid> --recover
#                                    clear a stale lease (holder gone); still cleans the sim
#
# Settings (env vars):
#   SIM_CAP           max booted sims machine-wide (default 2)
#   MIN_FREE_PCT      refuse to boot below this % of free memory (default 25)
#   SIMSLIM_EXCEPT    simslim categories to keep on (default "store,web": StoreKit, push, universal links)
#   SIM_GUARD_HOME    state folder (default ~/.config/sim-guard): pool file, leases, lock file
#   SIM_GUARD_OWNER   label written to the lease (default: parent command + PID)
#   SIM_GUARD_LOCK_WAIT  seconds to wait for the lock (default 900: a slim boot can take minutes)

set -u
set -o pipefail
CAP="${SIM_CAP:-2}"
MIN_FREE="${MIN_FREE_PCT:-25}"
EXCEPT="${SIMSLIM_EXCEPT:-store,web}"
HOME_DIR="${SIM_GUARD_HOME:-$HOME/.config/sim-guard}"
CONFIG="$HOME_DIR/pool"
LEASES="$HOME_DIR/leases"
LOCKFILE="$HOME_DIR/lock"
LOCK_WAIT="${SIM_GUARD_LOCK_WAIT:-900}"
PREFIX="sim-guard-"
UDID_RE='^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$'
TOKEN_RE='^[0-9a-f]{32}$'

need() { command -v "$1" >/dev/null || { echo "missing: $1 ($2)"; exit 2; }; }
need xcrun "install Xcode"
need simslim "brew install mobai-app/tap/simslim"
need python3 "xcode-select --install"
case "$CAP" in ''|*[!0-9]*) echo "SIM_CAP must be a number"; exit 2 ;; esac
case "$MIN_FREE" in ''|*[!0-9]*) echo "MIN_FREE_PCT must be a number"; exit 2 ;; esac
case "$LOCK_WAIT" in ''|*[!0-9]*) echo "SIM_GUARD_LOCK_WAIT must be a number"; exit 2 ;; esac
mkdir -p "$HOME_DIR" "$LEASES" && chmod 700 "$HOME_DIR" 2>/dev/null

# --- lock: re-exec under an exclusive flock on a file that is never deleted. The kernel drops it when
# this process dies, so there is no stale-lock cleanup to race on. fd 9 holds it; child tools get 9 closed.
CMD="${1:-audit}"
case "$CMD" in init|acquire|release)
  if [ -z "${SIM_GUARD_LOCKED:-}" ]; then
    exec python3 -c '
import fcntl, os, sys, time
path, wait = sys.argv[1], int(sys.argv[2])
fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
start = time.time()
while True:
    try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); break
    except BlockingIOError:
        if time.time() - start >= wait:
            print(f"BLOCKED: another sim-guard operation has held the lock for {wait}s."); sys.exit(1)
        time.sleep(0.5)
os.dup2(fd, 9); os.set_inheritable(9, True)
os.environ["SIM_GUARD_LOCKED"] = "1"
os.execv("/bin/bash", ["/bin/bash"] + sys.argv[3:])' "$LOCKFILE" "$LOCK_WAIT" "$0" "$@"
  fi ;;
esac
xcrun() { command xcrun "$@" 9>&-; }
simslim() { command simslim "$@" 9>&-; }

# Pool: "UDID # name runtime" per line, written only by init for sims it created.
pool_udids() { [ -f "$CONFIG" ] && sed -e 's/#.*//' -e 's/[[:space:]]//g' "$CONFIG" | grep -E "$UDID_RE" || true; }
in_pool() { pool_udids | grep -qx "$1"; }
valid_udid() { [[ "$1" =~ $UDID_RE ]]; }

# Free memory % or empty on failure; callers treat empty as "unknown".
free_pct() { memory_pressure 2>/dev/null | awk -F': ' '/free percentage/{gsub("%","",$2); print $2}' | grep -E '^[0-9]+$' || true; }

# Booted UDIDs; exit status 1 when simctl or its JSON can't be read.
booted_udids() {
  local json; json="$(xcrun simctl list devices booted --json)" || return 1
  JSON="$json" python3 -c '
import json,os,sys
try: devs = json.loads(os.environ["JSON"])["devices"]
except Exception: sys.exit(1)
for v in devs.values():
    for d in v:
        if d.get("state")=="Booted": print(d["udid"])'
}

owner_label() { echo "${SIM_GUARD_OWNER:-$(basename "$(ps -o comm= -p "$PPID" 2>/dev/null)" 2>/dev/null || echo agent)[$PPID]}"; }
lease_token() { sed -n 's/^token=//p' "$LEASES/$1" 2>/dev/null; }

init_pool() {
  local n="${1:-$CAP}"
  case "$n" in ''|*[!0-9]*|0) echo "usage: sim-guard init [N>0]"; return 2 ;; esac
  local plan
  plan="$(xcrun simctl list runtimes --json | python3 -c '
import json,re,sys
rts=[r for r in json.load(sys.stdin)["runtimes"] if r.get("platform")=="iOS" and r.get("isAvailable")]
if not rts: sys.exit("no iOS runtime installed")
def ver(r): return tuple(int(x) for x in re.findall(r"\d+", r.get("version","0")))
rt=max(rts,key=ver)
phones=[d["identifier"] for d in rt.get("supportedDeviceTypes",[]) if d.get("productFamily")=="iPhone"]
if not phones: sys.exit("no iPhone device type for " + rt["identifier"])
def rank(t):
    m=re.search(r"iPhone-(\d+)",t); base=t.rsplit(".",1)[-1]
    return (int(m.group(1)) if m else 0, base.endswith("-Pro"), not base.endswith("-Max"))
print(rt["identifier"], max(phones,key=rank))')" || return 1
  local runtime devtype; runtime="${plan%% *}"; devtype="${plan#* }"
  # Reuse only UDIDs this guard recorded earlier that still exist on this runtime.
  local alive
  alive="$(xcrun simctl list devices --json | RT="$runtime" python3 -c '
import json,os,sys
for d in json.load(sys.stdin)["devices"].get(os.environ["RT"],[]):
    if d.get("isAvailable"): print(d["udid"])')" || return 1
  local tmp="$CONFIG.tmp.$$" i=1 u failed=0 kept=""
  echo "# sim-guard pool: sims created by sim-guard init. Never add a sim you use by hand." > "$tmp"
  for u in $(pool_udids); do
    [ "$i" -gt "$n" ] && break
    echo "$alive" | grep -qx "$u" || continue
    kept="$kept $u"; echo "$u # ${PREFIX}${i} ${runtime##*.}" >> "$tmp"; echo "Reusing pool sim $u"; i=$((i + 1))
  done
  while [ "$i" -le "$n" ]; do
    u="$(xcrun simctl create "${PREFIX}${i}" "$devtype" "$runtime")" && valid_udid "$u" || { echo "Could not create ${PREFIX}${i}"; rm -f "$tmp"; return 1; }
    echo "Created ${PREFIX}${i} $u (${devtype##*.}, ${runtime##*.})"
    echo "$u # ${PREFIX}${i} ${runtime##*.}" >> "$tmp"; i=$((i + 1))
  done
  mv "$tmp" "$CONFIG"
  echo "Pool written to $CONFIG"
  for u in $(pool_udids); do
    echo "Slimming $u (keeps: $EXCEPT)..."
    simslim on "$u" --except "$EXCEPT" --preserve-boot-state >/dev/null || { echo "FAILED to slim $u: it stays in the pool and acquire re-applies the profile."; failed=1; }
  done
  [ "$failed" -eq 0 ] || return 1
}

audit() {
  local snap; snap="$(simslim top --json 2>/dev/null)"
  SNAP="$snap" POOL_LIST="$(pool_udids)" LEASES="$LEASES" CAP="$CAP" python3 - <<'PY'
import json, os, subprocess
pool = set(os.environ["POOL_LIST"].split())
cap = int(os.environ["CAP"])
def lease(u):
    try:
        lines = open(os.path.join(os.environ["LEASES"], u)).read().split("\n")
        return " ".join(l for l in lines if l and not l.startswith("token="))
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
for u in sorted(pool):
    l = lease(u)
    if l and u not in {s["udid"] for s in sims}: print(f"  {u}  leased but not booted: {l}")
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

# Capacity from one validated snapshot; unknown state blocks.
check_capacity() {
  local booted n free
  booted="$(booted_udids)" || { echo "BLOCKED: can't read booted simulators (simctl failed)."; return 1; }
  n=$(printf '%s\n' "$booted" | grep -c . | tr -d ' ')
  free=$(free_pct)
  [ -z "$free" ] && { echo "BLOCKED: can't read free memory (memory_pressure)."; return 1; }
  if [ "$n" -ge "$CAP" ]; then
    echo "BLOCKED: $n sims booted, cap is $CAP. Reuse a pool sim you hold, wait, or ask about an orphan."
    return 1
  fi
  if [ "$free" -lt "$MIN_FREE" ]; then
    echo "BLOCKED: only ${free}% memory free. Close something before booting a sim."
    return 1
  fi
  BOOTED="$booted"
  echo "OK to boot one more sim."
}

preflight() { audit; check_capacity; }

acquire() {
  [ -z "$(pool_udids)" ] && { echo "No pool yet. Run: sim-guard init"; return 1; }
  audit
  BOOTED=""
  check_capacity || return 1
  local u token
  for u in $(pool_udids); do
    printf '%s\n' "$BOOTED" | grep -qx "$u" && continue
    [ -f "$LEASES/$u" ] && continue   # leased (maybe crashed): needs release --recover, never silent reuse
    token="$(python3 -c 'import secrets; print(secrets.token_hex(16))')"
    printf 'token=%s\nowner=%s\nsince=%s\n' "$token" "$(owner_label)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LEASES/$u"
    echo "Booting pool sim $u (slim)..."
    if ! simslim boot "$u" >/dev/null; then rm -f "$LEASES/$u"; echo "Boot failed for $u"; return 1; fi
    if ! simslim verify "$u" --except "$EXCEPT" >/dev/null 2>&1; then
      echo "Slim profile drifted, re-applying..."
      if ! simslim on "$u" --except "$EXCEPT" >/dev/null; then
        simslim shutdown "$u" >/dev/null && rm -f "$LEASES/$u" || echo "Shutdown failed: lease kept for recovery."
        echo "Could not slim $u."; return 1
      fi
    fi
    simslim measure "$u"
    echo "ACQUIRED $u $token"
    return 0
  done
  echo "BLOCKED: every pool sim is booted or leased. Reuse one you hold, wait, or run audit."
  return 1
}

release() {
  local u="${1:-}" proof="${2:-}" keep="${3:-}"
  local usage="usage: sim-guard release <udid> <lease-token> [--keep-apps] | sim-guard release <udid> --recover"
  [ $# -ge 2 ] && [ $# -le 3 ] || { echo "$usage"; return 2; }
  valid_udid "$u" || { echo "Not a simulator UDID."; return 2; }
  in_pool "$u" || { echo "REFUSED: $u is not a sim-guard pool sim. sim-guard never wipes other simulators."; return 2; }
  [ -n "$keep" ] && [ "$keep" != "--keep-apps" ] && { echo "$usage"; return 2; }
  if [ "$proof" = "--recover" ]; then
    [ -n "$keep" ] && { echo "$usage"; return 2; }
    echo "Recovering $u (stale lease: $(sed -n 's/^owner=//p' "$LEASES/$u" 2>/dev/null || echo none))."
  else
    [[ "$proof" =~ $TOKEN_RE ]] || { echo "$usage"; return 2; }
    [ "$(lease_token "$u")" = "$proof" ] || { echo "REFUSED: lease token does not match the current lease of $u (released already or held by another agent)."; return 2; }
  fi
  local booted; booted="$(booted_udids)" || { echo "Can't read simulator state; lease kept."; return 1; }
  if [ "$keep" != "--keep-apps" ]; then
    if ! printf '%s\n' "$booted" | grep -qx "$u"; then
      simslim boot "$u" >/dev/null || { echo "Can't boot $u to clean it; lease kept."; return 1; }
    fi
    local apps
    apps="$(xcrun simctl listapps "$u" | plutil -convert json -o - - | python3 -c '
import json,sys
for bid,a in json.load(sys.stdin).items():
    if a.get("ApplicationType")=="User": print(bid)')" || { echo "Can't list apps on $u; lease kept."; return 1; }
    local bid
    for bid in $apps; do
      echo "uninstall $bid"; xcrun simctl uninstall "$u" "$bid" || { echo "Uninstall failed; lease kept."; return 1; }
    done
    xcrun simctl keychain "$u" reset || { echo "Keychain reset failed; lease kept."; return 1; }
    echo "keychain reset"
  fi
  booted="$(booted_udids)" || { echo "Can't read simulator state; lease kept."; return 1; }
  if printf '%s\n' "$booted" | grep -qx "$u"; then simslim shutdown "$u" >/dev/null || { echo "Shutdown failed; lease kept."; return 1; }; fi
  rm -f "$LEASES/$u"
  echo "RELEASED $u"
}

case "$CMD" in
  init) shift; init_pool "$@" ;;
  audit) audit ;;
  preflight) preflight ;;
  acquire) acquire ;;
  release) shift; release "$@" ;;
  *) sed -n 2,26p "$0"; exit 2 ;;
esac
