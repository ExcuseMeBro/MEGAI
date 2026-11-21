import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const script = fileURLToPath(new URL('../agent/skills/sim-guard/sim-guard.sh', import.meta.url));
const USER_SIM = '46D622F2-AD60-4C1A-AEB0-9985D4BE62B1';

// Fake xcrun/simslim/memory_pressure backed by one JSON state file. Never touches real simulators.
const FAKE = String.raw`#!/usr/bin/env python3
import json, os, sys, time, uuid, fcntl
st_path = os.environ["FAKE_STATE"]
def load():
    with open(st_path) as f: return json.load(f)
def save(s):
    with open(st_path, "w") as f: json.dump(s, f)
def locked(fn):
    with open(st_path + ".lk", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX); s = load(); r = fn(s); save(s); return r
tool = os.path.basename(sys.argv[0]); a = sys.argv[1:]
log = open(os.environ["FAKE_LOG"], "a"); log.write(tool + " " + " ".join(a) + "\n"); log.close()
RT = "com.apple.CoreSimulator.SimRuntime.iOS-27-2"
def devices(s, booted_only=False):
    out = {RT: []}
    for d in s["devices"]:
        if booted_only and d["state"] != "Booted": continue
        out[RT].append({"udid": d["udid"], "name": d["name"], "state": d["state"], "isAvailable": True,
                        "deviceTypeIdentifier": d["type"]})
    return {"devices": out}
if tool == "memory_pressure":
    print("System-wide memory free percentage: %s%%" % os.environ.get("FAKE_FREE", "60")); sys.exit(0)
if tool == "xcrun":
    assert a[0] == "simctl"; c = a[1:]
    if c[:2] == ["list", "runtimes"]:
        print(json.dumps({"runtimes": [{"identifier": RT, "platform": "iOS", "isAvailable": True, "version": "27.2",
            "supportedDeviceTypes": [{"identifier": "com.apple.CoreSimulator.SimDeviceType.iPhone-11", "productFamily": "iPhone"},
                                     {"identifier": "com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro", "productFamily": "iPhone"}]}]})); sys.exit(0)
    if c[:2] == ["list", "devices"]:
        print(json.dumps(devices(load(), "booted" in c))); sys.exit(0)
    if c[0] == "create":
        u = str(uuid.uuid4()).upper()
        locked(lambda s: s["devices"].append({"udid": u, "name": c[1], "type": c[2], "state": "Shutdown", "apps": []}))
        print(u); sys.exit(0)
    if c[0] == "listapps":
        d = next(d for d in load()["devices"] if d["udid"] == c[1])
        apps = {b: {"ApplicationType": "User"} for b in d["apps"]}; apps["com.apple.Preferences"] = {"ApplicationType": "System"}
        import plistlib; sys.stdout.buffer.write(plistlib.dumps(apps)); sys.exit(0)
    if c[0] == "uninstall":
        locked(lambda s: [d["apps"].remove(c[2]) for d in s["devices"] if d["udid"] == c[1]]); sys.exit(0)
    if c[:2] == ["keychain", c[1]] and c[2] == "reset": sys.exit(0)
    sys.exit("unknown xcrun " + " ".join(a))
if tool == "simslim":
    if a[0] == "boot":
        time.sleep(float(os.environ.get("FAKE_BOOT_SECS", "0")))
        locked(lambda s: [d.update(state="Booted") for d in s["devices"] if d["udid"] == a[1]]); sys.exit(0)
    if a[0] == "shutdown":
        locked(lambda s: [d.update(state="Shutdown") for d in s["devices"] if d["udid"] == a[1]]); sys.exit(0)
    if a[0] in ("on", "verify", "measure"): print("ok"); sys.exit(0)
    if a[0] == "top":
        s = load()
        if not any(d["state"] == "Booted" for d in s["devices"]): print(json.dumps({"sims": None})); sys.exit(0)
        print(json.dumps({"sims": [{"udid": d["udid"], "name": d["name"], "state": d["state"], "memory": {"bytes": 4e8, "processes": 57, "cpu": 1},
            "managedDisabled": 9, "managedTotal": 10} for d in s["devices"]]})); sys.exit(0)
    sys.exit("unknown simslim " + " ".join(a))
`;

function setup(t, devices = [{ udid: USER_SIM, name: 'iPhone 18 Pro', type: 'com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro', state: 'Shutdown', apps: ['com.user.app'] }]) {
  const root = mkdtempSync(join(tmpdir(), 'sim-guard-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const bin = join(root, 'bin'); mkdirSync(bin);
  for (const tool of ['xcrun', 'simslim', 'memory_pressure']) { writeFileSync(join(bin, tool), FAKE); chmodSync(join(bin, tool), 0o755); }
  const state = join(root, 'state.json'); writeFileSync(state, JSON.stringify({ devices }));
  const env = { ...process.env, PATH: `${bin}:/usr/bin:/bin:/usr/sbin:/sbin`, FAKE_STATE: state, FAKE_LOG: join(root, 'log'),
    SIM_GUARD_HOME: join(root, 'home'), HOME: root };
  const run = (args, extra = {}) => spawnSync('/bin/bash', [script, ...args], { env: { ...env, ...extra }, encoding: 'utf8' });
  const runAsync = (args, extra = {}) => new Promise(resolve => {
    const c = spawn('/bin/bash', [script, ...args], { env: { ...env, ...extra } });
    let out = ''; c.stdout.on('data', d => out += d); c.stderr.on('data', d => out += d);
    c.on('close', status => resolve({ status, out }));
  });
  const read = () => JSON.parse(readFileSync(state, 'utf8'));
  return { root, env, run, runAsync, read, home: join(root, 'home'), log: () => readFileSync(join(root, 'log'), 'utf8') };
}

test('init creates dedicated pool sims, reuses them, never adopts the user sim', t => {
  const s = setup(t);
  const r = s.run(['init']);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  const idle = s.run(['audit']);
  assert.equal(idle.status, 0); assert.doesNotMatch(idle.stdout + idle.stderr, /Traceback|TypeError/); assert.match(idle.stdout, /Booted simulators: 0/);
  const devs = s.read().devices;
  assert.deepEqual(devs.map(d => d.name), ['iPhone 18 Pro', 'sim-guard-1', 'sim-guard-2']);
  assert.ok(devs.slice(1).every(d => d.type.endsWith('iPhone-18-Pro')), 'copies the existing iPhone device type');
  const pool = readFileSync(join(s.home, 'pool'), 'utf8');
  assert.ok(!pool.includes(USER_SIM));
  assert.ok(!s.log().includes(`simslim on ${USER_SIM}`), 'user sim never slimmed');
  const again = s.run(['init']);
  assert.match(again.stdout, /Reusing sim-guard-1/);
  assert.equal(s.read().devices.length, 3, 'no duplicates on re-init');
});

test('release refuses non-pool and malformed UDIDs; wipes and shuts down pool sims', t => {
  const s = setup(t);
  s.run(['init']);
  const user = s.run(['release', USER_SIM]);
  assert.equal(user.status, 2); assert.match(user.stdout, /REFUSED/);
  assert.deepEqual(s.read().devices[0].apps, ['com.user.app'], 'user apps untouched');
  assert.equal(s.run(['release', 'x; rm -rf ~']).status, 2);
  const a = s.run(['acquire']);
  assert.equal(a.status, 0, a.stdout);
  const u = a.stdout.match(/ACQUIRED (\S+)/)[1];
  assert.match(readFileSync(join(s.home, 'leases', u), 'utf8'), /^owner=/);
  const st = s.read(); st.devices.find(d => d.udid === u).apps.push('com.test.app'); writeFileSync(s.env.FAKE_STATE, JSON.stringify(st));
  const rel = s.run(['release', u]);
  assert.equal(rel.status, 0, rel.stdout);
  const d = s.read().devices.find(d => d.udid === u);
  assert.deepEqual(d.apps, []); assert.equal(d.state, 'Shutdown');
  assert.equal(existsSync(join(s.home, 'leases', u)), false, 'lease dropped');
});

test('concurrent acquires get distinct sims and respect the cap', async t => {
  const s = setup(t);
  s.run(['init', '3']);
  const extra = { FAKE_BOOT_SECS: '1', SIM_CAP: '2' };
  const results = await Promise.all([1, 2, 3].map(() => s.runAsync(['acquire'], extra)));
  const got = results.map(r => (r.out.match(/ACQUIRED (\S+)/) || [])[1]).filter(Boolean);
  assert.equal(got.length, 2, results.map(r => r.out).join('\n---\n'));
  assert.notEqual(got[0], got[1]);
  assert.ok(results.some(r => r.status === 1 && /BLOCKED/.test(r.out)));
  assert.equal(s.read().devices.filter(d => d.state === 'Booted').length, 2);
});

test('user-booted sims count toward the cap; low memory blocks; exact UDID match', t => {
  const s = setup(t);
  s.run(['init', '1']);
  const st = s.read(); st.devices[0].state = 'Booted'; writeFileSync(s.env.FAKE_STATE, JSON.stringify(st));
  assert.equal(s.run(['preflight'], { SIM_CAP: '1' }).status, 1);
  assert.match(s.run(['audit']).stdout, new RegExp(`${USER_SIM}.*\\[orphan\\]`));
  assert.equal(s.run(['preflight'], { FAKE_FREE: '10' }).status, 1);
  // Exact match: a booted sim whose UDID contains the pool UDID as a substring must not hide it.
  const pool = readFileSync(join(s.home, 'pool'), 'utf8').match(/^([0-9A-F-]{36})/m)[1];
  const st2 = s.read(); st2.devices.push({ udid: pool.slice(0, 35) + 'Z', name: 'decoy', type: 't', state: 'Booted', apps: [] }); writeFileSync(s.env.FAKE_STATE, JSON.stringify(st2));
  const a = s.run(['acquire'], { SIM_CAP: '5' });
  assert.match(a.stdout, /ACQUIRED/);
});

test('stale lock from a dead process is recovered; a live lock blocks until timeout', t => {
  const s = setup(t);
  s.run(['init', '1']);
  mkdirSync(join(s.home, 'lock')); writeFileSync(join(s.home, 'lock', 'pid'), '999999');
  const a = s.run(['acquire']);
  assert.equal(a.status, 0, a.stdout + a.stderr); assert.match(a.stderr, /stale sim-guard lock/);
  assert.equal(existsSync(join(s.home, 'lock')), false, 'lock released after run');
  mkdirSync(join(s.home, 'lock')); writeFileSync(join(s.home, 'lock', 'pid'), String(process.pid));
  const blocked = s.run(['release', readFileSync(join(s.home, 'pool'), 'utf8').match(/^([0-9A-F-]{36})/m)[1]], { SIM_GUARD_LOCK_WAIT: '1' });
  assert.equal(blocked.status, 1); assert.match(blocked.stdout, /lock busy/);
});
