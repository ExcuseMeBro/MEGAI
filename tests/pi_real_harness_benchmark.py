#!/usr/bin/env python3
"""Matched fresh-process Pi-Bolt coding trials; private receipts only, never live sessions."""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = Path.home() / '.pi/agent'
BOLT = Path.home() / '.local/bin/pi-bolt'
# Historical failing policy remains immutable when the candidate is committed.
BASELINE_SHA = '7955cbefe4068b019898baadedd1be1a9a80c36c'
PROMPT = (
    'This is a disposable local coding fixture. Change ONLY counter.py so '
    'next_count(None) returns 1 and next_count(nonnegative integer) returns '
    'the value plus 1. Run python3 -B -m unittest test_counter.py and report '
    'the result. Do not change the test, other files, config or settings.'
)
FIXTURE = 'def next_count(value):\n    return value + 1\n'
TEST = '''import unittest
from counter import next_count

class CounterTest(unittest.TestCase):
    def test_none(self):
        self.assertEqual(next_count(None), 1)

    def test_integer(self):
        self.assertEqual(next_count(2), 3)

if __name__ == '__main__':
    unittest.main()
'''
EXTENSION = '''import { writeFileSync } from 'node:fs';
export default function (pi) {
  pi.registerCommand('megai-benchmark-info', {
    description: 'Record private runtime metadata without a model call',
    handler: async (_args, ctx) => {
      writeFileSync(process.env.MEGAI_BENCH_INFO, JSON.stringify({
        provider: ctx.model?.provider, model: ctx.model?.id,
        registered: pi.getAllTools().map(t => t.name).sort(),
        active: pi.getActiveTools().sort(),
        node: process.version, bun: process.versions.bun ?? null,
      }), { mode: 0o600 });
    },
  });
}
'''


def record(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')
    path.chmod(0o600)


def event_stream(proc, log, deadline, buffer):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('RPC deadline expired; owned isolated process retained for reconciliation')
    ready, _, _ = select.select([proc.stdout], [], [], remaining)
    if not ready:
        raise TimeoutError('RPC deadline expired; owned isolated process retained for reconciliation')
    data = os.read(proc.stdout.fileno(), 65536)
    if not data:
        raise RuntimeError(f'RPC EOF; isolated process exit={proc.poll()}')
    buffer += data
    events = []
    while b'\n' in buffer:
        line, buffer = buffer.split(b'\n', 1)
        log.write(line + b'\n')
        events.append(json.loads(line))
    return events, buffer


def wait_for(proc, log, buffer, timeout, predicate, warnings):
    deadline = time.monotonic() + timeout
    while True:
        events, buffer = event_stream(proc, log, deadline, buffer)
        for event in events:
            if event.get('type') == 'extension_error':
                warnings.append(str(event.get('error', 'extension_error')))
            if predicate(event):
                return event, buffer


def trial(out, variant, rep, settings, extension):
    run = out / f'{rep}-{variant}'
    run.mkdir(mode=0o700)
    agent = run / 'agent'
    agent.mkdir(mode=0o700)
    (agent / 'npm').symlink_to(GLOBAL / 'npm', target_is_directory=True)
    (agent / 'extensions').mkdir()
    (agent / 'extensions' / 'tgrep').symlink_to(GLOBAL / 'extensions' / 'tgrep', target_is_directory=True)
    if variant == 'baseline':
        policy = subprocess.check_output(['git', '-C', str(ROOT), 'show',
            f'{BASELINE_SHA}:pi-defaults/AGENTS.md'])
    else:
        policy = (ROOT / 'pi-defaults/AGENTS.md').read_bytes()
    (agent / 'AGENTS.md').write_bytes(policy)
    for name in ('auth.json', 'models-store.json', 'models.json', 'antigravity-accounts.json', 'mcp.json'):
        src = GLOBAL / name
        if src.is_file():
            shutil.copyfile(src, agent / name)
            (agent / name).chmod(0o600)
    local_settings = dict(settings)
    local_settings['skills'] = []
    local_settings['prompts'] = []
    record(agent / 'settings.json', local_settings)
    (run / 'counter.py').write_text(FIXTURE)
    (run / 'test_counter.py').write_text(TEST)
    (run / 'extension.mjs').write_text(EXTENSION)
    env = os.environ.copy()
    for key in ('PI_SESSION_ID', 'PI_SESSION_FILE'):
        env.pop(key, None)
    env.update(PI_CODING_AGENT_DIR=str(agent), PI_SKIP_VERSION_CHECK='1',
               MEGAI_BENCH_INFO=str(run / 'info.json'))
    cmd = [str(BOLT), '--mode', 'rpc', '--no-skills', '--no-prompt-templates',
           '--no-themes', '--session', str(run / 'session.jsonl'), '-e', str(extension)]
    start = time.monotonic()
    warnings = []
    state = None
    with (run / 'rpc.jsonl').open('wb') as log, (run / 'stderr.log').open('wb') as err:
        proc = subprocess.Popen(cmd, cwd=run, env=env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=err)
        record(run / 'process.json', {'pid': proc.pid, 'owned': True, 'variant': variant})
        buffer = b''
        try:
            proc.stdin.write(b'{"id":"state","type":"get_state"}\n')
            proc.stdin.flush()
            event, buffer = wait_for(proc, log, buffer, 75,
                lambda e: e.get('type') == 'response' and e.get('id') == 'state', warnings)
            if not event.get('success'):
                raise RuntimeError('RPC get_state failed')
            state = event['data']
            startup = time.monotonic() - start
            model = state.get('model') or {}
            assert (model.get('provider'), model.get('id'), state.get('thinkingLevel')) == (
                'openai-codex', 'gpt-6-sol', 'high'), 'selected provider/model/thinking drift'
            proc.stdin.write(b'{"id":"info","type":"prompt","message":"/megai-benchmark-info"}\n')
            proc.stdin.flush()
            event, buffer = wait_for(proc, log, buffer, 30,
                lambda e: (run / 'info.json').is_file() or
                          (e.get('type') == 'response' and e.get('id') == 'info' and not e.get('success')),
                warnings)
            info = json.loads((run / 'info.json').read_text())
            if info['provider'] != model['provider'] or info['model'] != model['id']:
                raise AssertionError('info model mismatch')
            request = {'id': 'task', 'type': 'prompt', 'message': PROMPT}
            task_start = time.monotonic()
            proc.stdin.write((json.dumps(request) + '\n').encode())
            proc.stdin.flush()
            result, buffer = wait_for(proc, log, buffer, 240,
                lambda e: e.get('type') == 'agent_end', warnings)
            latency = time.monotonic() - task_start
            proc.stdin.close()
            proc.wait(timeout=15)
            if proc.returncode:
                raise RuntimeError(f'RPC exit {proc.returncode}')
            checked = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'test_counter.py'],
                cwd=run, capture_output=True, text=True, timeout=12, check=False)
            correct = checked.returncode == 0 and (run / 'test_counter.py').read_text() == TEST
            messages = result.get('messages') or []
            usage = {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0, 'cost': 0.0}
            for msg in messages:
                u = msg.get('usage') or {}
                for key in ('input', 'output', 'cacheRead', 'cacheWrite'):
                    usage[key] += u.get(key, 0) or 0
                cost = u.get('cost') or {}
                usage['cost'] += (cost.get('total', 0) or 0) if isinstance(cost, dict) else cost
            row = {'variant': variant, 'rep': rep, 'startup_s': startup, 'task_s': latency,
                   'correct': correct, 'test_exit': checked.returncode,
                   'registered': info['registered'], 'active': info['active'],
                   'model': model, 'thinking': state['thinkingLevel'],
                   'usage': usage, 'warnings': warnings, 'exit': proc.returncode}
            record(run / 'result.json', row)
            record(run / 'test-result.json', {'returncode': checked.returncode,
                'output': checked.stdout[-2000:] + checked.stderr[-2000:]})
            print(json.dumps({k: row[k] for k in ('variant', 'rep', 'startup_s',
                'task_s', 'correct', 'usage', 'warnings')}), flush=True)
            return row
        except BaseException as exc:
            record(run / 'incomplete.json', {'error': str(exc), 'pid': proc.pid,
                'process_running': proc.poll() is None, 'reason': 'reconcile before retry'})
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reps', type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.reps <= 6:
        parser.error('--reps must be between 1 and 6')
    out = args.out.resolve()
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    settings = json.loads((GLOBAL / 'settings.json').read_text())
    extension = out / 'extension.mjs'
    extension.write_text(EXTENSION)
    rows = []
    for rep in range(args.reps):
        for variant in (('baseline', 'candidate') if rep % 2 == 0 else ('candidate', 'baseline')):
            rows.append(trial(out, variant, rep, settings, extension))
    if any(not row['correct'] for row in rows):
        raise AssertionError('coding task correctness failed; inspect private trial receipts')
    baseline = [row for row in rows if row['variant'] == 'baseline']
    candidate = [row for row in rows if row['variant'] == 'candidate']
    if any(a['active'] != baseline[0]['active'] or
           a['registered'] != baseline[0]['registered'] for a in rows):
        raise AssertionError('tool inventory drift between matched trials')
    required = {'tool_search', 'memory_search', 'memory_save', 'generate_image',
                'web_enable', 'tgrep', 'bash', 'edit', 'read', 'write'}
    if not required.issubset(set(baseline[0]['active'])):
        raise AssertionError('required MCP bridge/web/image/context/coding tools unavailable')
    if any(a['warnings'] for a in rows):
        raise AssertionError('extension warning during matched trials')
    summary = {'baseline_source_sha': BASELINE_SHA,
               'candidate_source': 'pi-defaults/AGENTS.md in current task-owned worktree',
               'baseline': {'startup_median_s': statistics.median(r['startup_s'] for r in baseline),
                            'task_median_s': statistics.median(r['task_s'] for r in baseline)},
               'candidate': {'startup_median_s': statistics.median(r['startup_s'] for r in candidate),
                             'task_median_s': statistics.median(r['task_s'] for r in candidate)},
               'trials': len(rows), 'correct': sum(r['correct'] for r in rows)}
    record(out / 'summary.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
