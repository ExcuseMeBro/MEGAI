#!/usr/bin/env python3
"""Bounded fresh Pi RPC load test; private logs, no model call or live-session mutation."""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = Path.home() / '.pi/agent'
BOLT = Path.home() / '.local/bin/pi-bolt'
EXT = ROOT / 'pi-defaults/extensions/megai-action-boundary'
INFO = '''import {writeFileSync} from 'node:fs';
export default function (pi) { pi.registerCommand('megai-boundary-info', {
  description: 'Private metadata only', handler: async (_, ctx) => {
    writeFileSync(process.env.MEGAI_BOUNDARY_INFO, JSON.stringify({
      provider: ctx.model?.provider, model: ctx.model?.id,
      registered: pi.getAllTools().map(x => x.name).sort(),
      active: pi.getActiveTools().sort(),
    }), {mode: 0o600});
  },
}); }
'''


def collect(out, variant):
    run = out / variant
    run.mkdir(mode=0o700)
    agent = run / 'agent'
    agent.mkdir(mode=0o700)
    (agent / 'npm').symlink_to(GLOBAL / 'npm', target_is_directory=True)
    (agent / 'extensions').mkdir(mode=0o700)
    (agent / 'extensions' / 'tgrep').symlink_to(GLOBAL / 'extensions' / 'tgrep', target_is_directory=True)
    if variant == 'candidate':
        shutil.copytree(EXT, agent / 'extensions' / 'megai-action-boundary')
    for name in ('settings.json', 'AGENTS.md', 'auth.json', 'models-store.json', 'models.json',
                 'antigravity-accounts.json', 'mcp.json'):
        src = GLOBAL / name
        if src.is_file():
            shutil.copyfile(src, agent / name)
            (agent / name).chmod(0o600)
    (run / 'info.mjs').write_text(INFO)
    env = os.environ.copy()
    for key in ('PI_SESSION_ID', 'PI_SESSION_FILE'):
        env.pop(key, None)
    env.update(PI_CODING_AGENT_DIR=str(agent), PI_SKIP_VERSION_CHECK='1',
               MEGAI_BOUNDARY_INFO=str(run / 'info.json'))
    cmd = [str(BOLT), '--mode', 'rpc', '--no-skills', '--no-prompt-templates',
           '--no-themes', '--session', str(run / 'session.jsonl'), '-e', str(run / 'info.mjs')]
    started = time.monotonic()
    warnings = []
    with (run / 'rpc.jsonl').open('wb') as raw, (run / 'stderr.log').open('wb') as err:
        proc = subprocess.Popen(cmd, cwd=run, env=env, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=err)
        (run / 'process.json').write_text(json.dumps({'pid': proc.pid, 'owned': True}))
        buffer = b''
        def wait_until(predicate, seconds):
            nonlocal buffer
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                ready, _, _ = select.select([proc.stdout], [], [], deadline - time.monotonic())
                if not ready:
                    break
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError(f'isolated Pi RPC EOF; exit={proc.poll()}')
                buffer += chunk
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    raw.write(line + b'\n')
                    event = json.loads(line)
                    if event.get('type') == 'extension_error':
                        warnings.append('extension_error')
                    if predicate(event):
                        return event
            raise TimeoutError('isolated Pi RPC deadline expired; inspect owned process before retry')
        try:
            proc.stdin.write(b'{"id":"state","type":"get_state"}\n')
            proc.stdin.flush()
            event = wait_until(lambda e: e.get('type') == 'response' and e.get('id') == 'state', 90)
            assert event.get('success'), 'Pi RPC get_state failed'
            state = event['data']
            startup = round(time.monotonic() - started, 3)
            proc.stdin.write(b'{"id":"info","type":"prompt","message":"/megai-boundary-info"}\n')
            proc.stdin.flush()
            wait_until(lambda e: (run / 'info.json').is_file() or
                       (e.get('type') == 'response' and e.get('id') == 'info' and not e.get('success')), 30)
            info = json.loads((run / 'info.json').read_text())
            proc.stdin.close()
            proc.wait(timeout=15)
            assert proc.returncode == 0, 'isolated Pi exited nonzero'
            assert not warnings, 'extension load error'
            assert (state['model']['provider'], state['model']['id'], state['thinkingLevel']) == (
                'openai-codex', 'gpt-6-sol', 'high'), 'selected model/provider/thinking changed'
            assert (info['provider'], info['model']) == ('openai-codex', 'gpt-6-sol')
            row = {'variant': variant, 'startup_s': startup, 'model': info['model'],
                   'provider': info['provider'], 'thinking': state['thinkingLevel'],
                   'active': info['active'], 'registered': info['registered'], 'extension_errors': len(warnings)}
            (run / 'result.json').write_text(json.dumps(row, sort_keys=True, indent=2))
            return row
        except BaseException:
            (run / 'incomplete.json').write_text(json.dumps({
                'pid': proc.pid, 'running': proc.poll() is None,
                'instruction': 'inspect this isolated process before retry; never stop a user session'}))
            raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    old = os.umask(0o077)
    try:
        out = args.out.resolve()
        out.mkdir(mode=0o700, parents=True, exist_ok=False)
        baseline = collect(out, 'baseline')
        candidate = collect(out, 'candidate')
        assert baseline['active'] == candidate['active'], 'active tool set changed'
        assert baseline['registered'] == candidate['registered'], 'registered tool set changed'
        print(json.dumps({'baseline_startup_s': baseline['startup_s'],
                          'candidate_startup_s': candidate['startup_s'],
                          'active_tools': len(candidate['active']),
                          'registered_tools': len(candidate['registered']),
                          'model': candidate['model'], 'extension_errors': candidate['extension_errors']}))
    finally:
        os.umask(old)


if __name__ == '__main__':
    main()
