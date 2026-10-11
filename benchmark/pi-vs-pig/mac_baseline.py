#!/usr/bin/env python3
"""Local installed-version baseline. No model requests or user config changes."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent

def output(args):
    return subprocess.check_output(args, text=True).strip()

def main():
    pi, pig = shutil.which('pi'), shutil.which('pig')
    if not pi or not pig:
        raise SystemExit('Both pi and pig must be installed')
    launcher = Path(pig).resolve()
    native = output(['node', '-e', 'console.log(require(process.argv[1]).resolveBinary(process.platform,process.arch))', str(launcher)])
    commands = {'pi-installed': pi, 'pig-installed': pig, 'pig-native': native}
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest = ROOT / 'results' / stamp
    dest.mkdir(parents=True)
    metadata = {
        'timestamp_utc': stamp,
        'machine': {'arch': output(['uname', '-m']), 'macos': output(['sw_vers']),
                    'model': output(['sysctl', '-n', 'hw.model']),
                    'ram_bytes': int(output(['sysctl', '-n', 'hw.memsize'])),
                    'cpus': int(output(['sysctl', '-n', 'hw.ncpu']))},
        'node': output(['node', '--version']), 'measured_runs': 30, 'warmups': 3,
        'commands': {name: {'path': path, 'version': output([path, '--version']),
                           'sha256': hashlib.sha256(Path(path).resolve().read_bytes()).hexdigest()}
                     for name, path in commands.items()},
        'scope': 'Installed versions, warm filesystem cache; no model/task-quality measurement. macOS time maximum RSS is a per-process maximum, NOT summed process-tree memory.',
    }
    rows = []
    with tempfile.TemporaryDirectory(prefix='pi-pig-baseline-') as temporary:
        env = os.environ.copy()
        env.update({'PI_OFFLINE': '1', 'PIG_OFFLINE': '1', 'PI_TELEMETRY': '0',
                    'PI_CODING_AGENT_DIR': temporary + '/pi-agent',
                    'PIG_CODING_AGENT_DIR': temporary + '/pig-agent', 'PIG_HOME': temporary + '/pig'})
        cases = {'version': ['--version'], 'help': ['--help']}
        jobs = [(name, case) for name in commands for case in cases]
        def run(name, case, index):
            started = time.perf_counter_ns()
            result = subprocess.run(['/usr/bin/time', '-l', commands[name], *cases[case]],
                                    cwd=temporary, env=env, capture_output=True, text=True, timeout=30)
            wall = (time.perf_counter_ns() - started) / 1e6
            if result.returncode or not result.stdout.strip():
                raise RuntimeError(f'{name}/{case} failed: {result.stderr}')
            timing = re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys', result.stderr)
            rss = re.search(r'(\d+)\s+maximum resident set size', result.stderr)
            if not timing or not rss:
                raise RuntimeError('Unable to parse macOS time output: ' + result.stderr)
            return {'harness': name, 'case': case, 'iteration': index, 'wall_ms': wall,
                    'cpu_ms': (float(timing[2]) + float(timing[3])) * 1000,
                    'max_process_rss_mib': int(rss[1]) / (1024 * 1024)}
        for name, case in jobs:
            for i in range(3):
                run(name, case, -i - 1)
        rng = random.Random(42)
        for i in range(30):
            rng.shuffle(jobs)
            for name, case in jobs:
                rows.append(run(name, case, i))
    summary = []
    for name in commands:
        for case in cases:
            selected = [r for r in rows if r['harness'] == name and r['case'] == case]
            walls = sorted(r['wall_ms'] for r in selected)
            summary.append({'harness': name, 'case': case, 'n': len(selected),
                            'median_ms': statistics.median(walls), 'p90_ms': walls[26],
                            'median_cpu_ms': statistics.median(r['cpu_ms'] for r in selected),
                            'median_max_process_rss_mib': statistics.median(r['max_process_rss_mib'] for r in selected)})
    (dest / 'raw.json').write_text(json.dumps({'metadata': metadata, 'runs': rows, 'summary': summary}, indent=2) + '\n')
    lines = ['# Pi vs PiG — local Mac baseline', '', 'Installed versions: ' + ', '.join(f"{n}: {v['version']}" for n, v in metadata['commands'].items()), '',
             '30 interleaved runs per case, 3 warmups; no paid API calls. Different upstream versions; this is not an equal-version parity comparison.', '',
             '| Harness | Case | Median ms | p90 ms | CPU ms | Max-process RSS MiB |', '|---|---|---:|---:|---:|---:|']
    for s in summary:
        lines.append(f"| {s['harness']} | {s['case']} | {s['median_ms']:.1f} | {s['p90_ms']:.1f} | {s['median_cpu_ms']:.1f} | {s['median_max_process_rss_mib']:.1f} |")
    lines += ['', 'RSS is NOT total process-tree memory. Wall time includes the time wrapper and process startup. Warm-cache startup does not establish coding speed, task quality, or cold-boot performance.', '', 'Reproduce: `python3 benchmark/pi-vs-pig/mac_baseline.py`']
    (dest / 'report.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('\nArtifacts:', dest)

if __name__ == '__main__':
    main()
