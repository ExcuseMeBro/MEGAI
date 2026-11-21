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
    if os.environ.get("FAKE_MEM_FAIL"): sys.exit(1)
    print("System-wide memory free percentage: %s%%" % os.environ.get("FAKE_FREE", "60")); sys.exit(0)
if tool == "xcrun":
    assert a[0] == "simctl"; c = a[1:]
    if c[:2] == ["list", "runtimes"]:
        print(json.dumps({"runtimes": [{"identifier": RT, "platform": "iOS", "isAvailable": True, "version": "27.2",
            "supportedDeviceTypes": [{"identifier": "com.apple.CoreSimulator.SimDeviceType.iPhone-11", "productFamily": "iPhone"},
                                     {"identifier": "com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro", "productFamily": "iPhone"}]}]})); sys.exit(0)
    if c[:2] == ["list", "devices"] and os.environ.get("FAKE_SIMCTL_FAIL"): sys.exit(1)
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
    if c[:2] == ["keychain", c[1]] and c[2] == "reset": sys.exit(1 if os.environ.get("FAKE_KEYCHAIN_FAIL") else 0)
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

test('init creates dedicated pool sims, reuses only recorded UDIDs, never adopts by name', t => {
  const decoy = 'AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE';
  const s = setup(t, [{ udid: USER_SIM, name: 'iPhone 18 Pro', type: 'com.apple.CoreSimulator.SimDeviceType.iPhone-18-Pro', state: 'Shutdown', apps: ['com.user.app'] },
    { udid: decoy, name: 'sim-guard-1', type: 'com.apple.CoreSimulator.SimDeviceType.iPhone-11', state: 'Shutdown', apps: ['com.user.other'] }]);
  const r = s.run(['init']);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  const idle = s.run(['audit']);
  assert.equal(idle.status, 0); assert.doesNotMatch(idle.stdout + idle.stderr, /Traceback|TypeError/); assert.match(idle.stdout, /Booted simulators: 0/);
  const devs = s.read().devices;
  assert.deepEqual(devs.map(d => d.name), ['iPhone 18 Pro', 'sim-guard-1', 'sim-guard-1', 'sim-guard-2']);
  assert.ok(devs.slice(2).every(d => d.type.endsWith('iPhone-18-Pro')), 'newest supported iPhone type, not an older existing one');
  const pool = readFileSync(join(s.home, 'pool'), 'utf8');
  assert.ok(!pool.includes(USER_SIM) && !pool.includes(decoy), 'a user sim named sim-guard-1 is not adopted');
  assert.ok(!s.log().includes(`simslim on ${USER_SIM}`), 'user sim never slimmed');
  const again = s.run(['init']);
  assert.match(again.stdout, /Reusing pool sim/);
  assert.equal(s.read().devices.length, 4, 'no duplicates on re-init');
});

test('release refuses non-pool and malformed UDIDs; wipes and shuts down pool sims', t => {
  const s = setup(t);
  s.run(['init']);
  const user = s.run(['release', USER_SIM, '--recover']);
  assert.equal(user.status, 2); assert.match(user.stdout, /REFUSED/);
  assert.deepEqual(s.read().devices[0].apps, ['com.user.app'], 'user apps untouched');
  assert.equal(s.run(['release', 'x; rm -rf ~', '--recover']).status, 2);
  const a = s.run(['acquire']);
  assert.equal(a.status, 0, a.stdout);
  const [, u, token] = a.stdout.match(/ACQUIRED (\S+) ([0-9a-f]{32})/);
  assert.match(readFileSync(join(s.home, 'leases', u), 'utf8'), /^token=.*\nowner=/);
  const multi = s.run(['release', `${u}\n${USER_SIM}`, token]);
  assert.equal(multi.status, 2, 'multi-line UDID rejected');
  assert.equal(s.run(['release', u, 'f'.repeat(32)]).status, 2, 'wrong token refused');
  const fail = s.run(['release', u, token], { FAKE_KEYCHAIN_FAIL: '1' });
  assert.equal(fail.status, 1); assert.ok(existsSync(join(s.home, 'leases', u)), 'lease kept when cleanup fails');
  const st = s.read(); st.devices.find(d => d.udid === u).apps.push('com.test.app'); writeFileSync(s.env.FAKE_STATE, JSON.stringify(st));
  const rel = s.run(['release', u, token]);
  assert.equal(rel.status, 0, rel.stdout);
  const d = s.read().devices.find(d => d.udid === u);
  assert.deepEqual(d.apps, []); assert.equal(d.state, 'Shutdown');
  assert.equal(existsSync(join(s.home, 'leases', u)), false, 'lease dropped');
  assert.equal(s.run(['release', u, token]).status, 2, 'a delayed second release with the old token is refused');
});

test('a leased sim is never silently reassigned; --recover cleans it', t => {
  const s = setup(t);
  s.run(['init', '1']);
  const [, u] = s.run(['acquire']).stdout.match(/ACQUIRED (\S+) /);
  const st = s.read(); st.devices.find(d => d.udid === u).state = 'Shutdown'; st.devices.find(d => d.udid === u).apps.push('com.left.over'); writeFileSync(s.env.FAKE_STATE, JSON.stringify(st));
  const again = s.run(['acquire']);
  assert.equal(again.status, 1); assert.match(again.stdout, /booted or leased/);
  const rec = s.run(['release', u, '--recover']);
  assert.equal(rec.status, 0, rec.stdout);
  assert.deepEqual(s.read().devices.find(d => d.udid === u).apps, [], 'shut-down sim is booted and cleaned on recover');
  assert.match(s.run(['acquire']).stdout, /ACQUIRED/);
});

test('unreadable simulator or memory state blocks booting', t => {
  const s = setup(t);
  s.run(['init', '1']);
  const a = s.run(['acquire'], { FAKE_SIMCTL_FAIL: '1' });
  assert.equal(a.status, 1); assert.match(a.stdout, /can't read booted simulators/);
  const b = s.run(['preflight'], { FAKE_MEM_FAIL: '1' });
  assert.equal(b.status, 1); assert.match(b.stdout, /can't read free memory/);
  assert.equal(s.read().devices.filter(d => d.state === 'Booted').length, 0);
});

test('concurrent acquires get distinct sims and respect the cap', async t => {
  const s = setup(t);
  s.run(['init', '3']);
  const extra = { FAKE_BOOT_SECS: '1', SIM_CAP: '2' };
  const results = await Promise.all([1, 2, 3].map(() => s.runAsync(['acquire'], extra)));
  const got = results.map(r => (r.out.match(/ACQUIRED (\S+) /) || [])[1]).filter(Boolean);
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

test('kernel lock: a crashed holder leaves no lock; a live holder blocks until timeout', async t => {
  const s = setup(t);
  s.run(['init', '1']);
  const lockfile = join(s.home, 'lock');
  // A holder that dies while holding the lock: the next run proceeds immediately.
  spawnSync('python3', ['-c', `import fcntl,os; fd=os.open(${JSON.stringify(lockfile)}, os.O_RDWR|os.O_CREAT); fcntl.flock(fd, fcntl.LOCK_EX); os._exit(0)`]);
  const a = s.run(['acquire']);
  assert.equal(a.status, 0, a.stdout + a.stderr);
  const [, u, token] = a.stdout.match(/ACQUIRED (\S+) (\S+)/);
  const holder = spawn('python3', ['-c', `import fcntl,os,time; fd=os.open(${JSON.stringify(lockfile)}, os.O_RDWR|os.O_CREAT); fcntl.flock(fd, fcntl.LOCK_EX); print("held", flush=True); time.sleep(10)`]);
  await new Promise(r => holder.stdout.once('data', r));
  t.after(() => holder.kill());
  const blocked = s.run(['release', u, token], { SIM_GUARD_LOCK_WAIT: '1' });
  assert.equal(blocked.status, 1); assert.match(blocked.stdout, /held the lock/);
  holder.kill(); await new Promise(r => holder.once('close', r));
  assert.equal(s.run(['release', u, token]).status, 0);
});
