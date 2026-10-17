#!/usr/bin/env python3
"""Actual CLI/tool/session workloads with a deterministic loopback model.
Not an LLM coding-quality benchmark. Uses isolated homes and disposable fixtures.
"""
import argparse
import ctypes
import datetime as dt
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import random
import re
import shutil
import statistics
import subprocess
import tempfile
import threading
import time
import uuid

ROOT = Path(__file__).resolve().parent

class TaskInfo(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in ('virtual', 'resident', 'user', 'system', 'threads_user', 'threads_system')] + [(n, ctypes.c_int32) for n in ('policy', 'faults', 'pageins', 'cow', 'sent', 'received', 'mach', 'unix', 'csw', 'threads', 'running', 'priority')]

class TreeSampler:
    """macOS libproc: summed live process-tree RSS sampled every 5 ms."""
    def __init__(self, pid):
        self.pid = pid
        self.lib = ctypes.CDLL('/usr/lib/libproc.dylib')
        self.lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
        self.lib.proc_listpids.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int]
        self.stop = threading.Event()
        self.peak = 0
        self.samples = 0
        self.max_processes = 0
        self.thread = threading.Thread(target=self.loop, daemon=True)
    def children(self, pid):
        buffer = (ctypes.c_int * 1024)()
        size = self.lib.proc_listpids(6, pid, buffer, ctypes.sizeof(buffer))
        return [x for x in buffer[:max(0, size) // 4] if x > 0]
    def loop(self):
        while not self.stop.is_set():
            pending, seen, rss, processes = [self.pid], set(), 0, 0
            while pending:
                pid = pending.pop()
                if pid in seen:
                    continue
                seen.add(pid)
                pending.extend(self.children(pid))
                info = TaskInfo()
                if self.lib.proc_pidinfo(pid, 4, 0, ctypes.byref(info), ctypes.sizeof(info)) == ctypes.sizeof(info):
                    rss += info.resident
                    processes += 1
            self.peak = max(self.peak, rss)
            self.max_processes = max(self.max_processes, processes)
            self.samples += 1
            self.stop.wait(.005)
    def __enter__(self):
        self.thread.start()
        return self
    def __exit__(self, *_):
        self.stop.set()
        self.thread.join()

class ModelServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self):
        super().__init__(('127.0.0.1', 0), ModelHandler)
        self.lock = threading.Lock()
        self.records = {}

class ModelHandler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def do_POST(self):
        raw = self.rfile.read(int(self.headers['Content-Length']))
        body = json.loads(raw)
        users = [m for m in body['messages'] if m['role'] == 'user']
        text = users[-1]['content']
        if isinstance(text, list):
            text = ' '.join(c.get('text', '') for c in text)
        match = re.search(r'BENCH_CASE=(\S+) BENCH_RUN=(\S+)', text)
        if not match:
            self.send_error(400, 'missing benchmark marker')
            return
        case, run_id = match.groups()
        tool_messages = [m for m in body['messages'] if m['role'] == 'tool']
        n = len(tool_messages)
        calc = 'def add(a, b):\n    return a - b\n'
        tests = 'import unittest\nfrom calc import add\nclass TestAdd(unittest.TestCase):\n    def test_add(self):\n        for a, b in [(2, 3), (-1, 4), (0, 0), (-5, -2)]:\n            self.assertEqual(add(a, b), a + b)\n'
        plans = {
            'tool-cycle': [('read', {'path': 'calc.py'}), ('edit', {'path': 'calc.py', 'oldText': 'return a - b', 'newText': 'return a + b'}), ('write', {'path': 'test_calc.py', 'content': tests}), ('bash', {'command': 'python3 -m unittest -q'})],
            'error-recovery': [('edit', {'path': 'calc.py', 'oldText': 'NO_SUCH_TEXT', 'newText': 'return a + b'}), ('edit', {'path': 'calc.py', 'oldText': 'return a - b', 'newText': 'return a + b'}), ('bash', {'command': "python3 -c 'from calc import add; assert add(2,3)==5; print(\"RECOVERED\")'"})],
            'read-large': [('read', {'path': 'large.txt'})],
        }
        calls = []
        if case in plans and n < len(plans[case]):
            name, args = plans[case][n]
            calls = [(name, args)]
        elif case == 'parallel-tools' and n == 0:
            calls = [('bash', {'command': f"python3 -c 'import time; time.sleep(0.1); print(\"PARALLEL_{i}\")'"}) for i in range(4)]
        delta = {'role': 'assistant'}
        if calls:
            delta['tool_calls'] = [{'index': i, 'id': f'call_{n}_{i}', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}} for i, (name, args) in enumerate(calls)]
        else:
            delta['content'] = 'BENCH_OK'
        record = {'received_ns': time.perf_counter_ns(), 'request_bytes': len(raw), 'messages': len(body['messages']),
                  'tools_returned': n, 'tool_results': tool_messages, 'requested_calls': [name for name, _ in calls],
                  'history_present': any('HISTORY_0000' in str(m.get('content')) for m in body['messages'])}
        with self.server.lock:
            self.server.records.setdefault(run_id, []).append(record)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Connection', 'close')
        self.end_headers()
        def chunk(d, finish=None):
            event = {'id': 'chatcmpl-local', 'object': 'chat.completion.chunk', 'created': 1, 'model': 'bench-local',
                     'choices': [{'index': 0, 'delta': d, 'finish_reason': finish}]}
            self.wfile.write(('data: ' + json.dumps(event) + '\n\n').encode())
            self.wfile.flush()
        try:
            if case == 'stream' and not calls:
                chunk({'role': 'assistant'})
                for _ in range(128):
                    chunk({'content': 'x' * 32})
                    time.sleep(.002)
                chunk({'content': 'BENCH_OK'})
            else:
                chunk(delta)
            chunk({}, 'tool_calls' if calls else 'stop')
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True

def make_session(path, cwd):
    timestamp = '2026-01-01T00:00:00.000Z'
    entries = [{'type': 'session', 'version': 3, 'id': str(uuid.uuid4()), 'timestamp': timestamp, 'cwd': str(cwd)}]
    parent = None
    for i in range(2000):
        for role in ('user', 'assistant'):
            identifier = f'{i:07d}{role[0]}'
            text = f'HISTORY_{i:04d} ' + ('context ' * 8)
            message = {'role': role, 'content': text if role == 'user' else [{'type': 'text', 'text': text}], 'timestamp': 1}
            if role == 'assistant':
                message.update({'api': 'openai-completions', 'provider': 'bench', 'model': 'bench-local', 'stopReason': 'stop',
                                'usage': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0, 'totalTokens': 0,
                                          'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0, 'total': 0}}})
            entries.append({'type': 'message', 'id': identifier, 'parentId': parent, 'timestamp': timestamp, 'message': message})
            parent = identifier
    path.write_text(''.join(json.dumps(x) + '\n' for x in entries))

def execute(command, case, run_id, dest, server):
    artifact = dest / run_id
    artifact.mkdir()
    with tempfile.TemporaryDirectory(prefix='pi-pig-workload-') as temporary:
        home = Path(temporary)
        cwd = home / 'workspace'
        cwd.mkdir()
        (cwd / 'calc.py').write_text('def add(a, b):\n    return a - b\n')
        (cwd / 'large.txt').write_text('LARGE_MARKER\n' + 'sample data\n' * 100000)
        port = server.server_address[1]
        config = {'providers': {'bench': {'baseUrl': f'http://127.0.0.1:{port}/v1', 'api': 'openai-completions', 'apiKey': 'local-dummy',
                   'models': [{'id': 'bench-local', 'name': 'Deterministic benchmark fixture', 'reasoning': False, 'input': ['text'],
                               'contextWindow': 1000000, 'maxTokens': 8192, 'cost': {'input': 0, 'output': 0, 'cacheRead': 0, 'cacheWrite': 0}}]}}}
        for name in ('pi-agent', 'pig-agent'):
            agent = home / name
            agent.mkdir()
            (agent / 'models.json').write_text(json.dumps(config))
            (agent / 'settings.json').write_text(json.dumps({'compaction': {'enabled': False}, 'enableInstallTelemetry': False}))
        # Fresh environment: no provider credentials, user extensions, or shared homes.
        env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR', 'USER', 'SHELL')}
        env.update({'HOME': temporary, 'PI_OFFLINE': '1', 'PIG_OFFLINE': '1', 'PI_TELEMETRY': '0',
                    'PI_CODING_AGENT_DIR': str(home / 'pi-agent'), 'PIG_CODING_AGENT_DIR': str(home / 'pig-agent'), 'PIG_HOME': str(home / 'pig')})
        args = [command, '--offline', '--no-extensions', '--no-skills', '--no-prompt-templates', '--no-themes', '--no-context-files',
                '--no-approve', '--provider', 'bench', '--model', 'bench-local', '--thinking', 'off', '--mode', 'json',
                '--tools', 'read,write,edit,bash']
        if case == 'resume-2000':
            session = cwd / 'history.jsonl'
            make_session(session, cwd)
            args += ['--session', str(session)]
        else:
            args += ['--no-session']
        args += [f'BENCH_CASE={case} BENCH_RUN={run_id}']
        started = time.perf_counter_ns()
        with (artifact / 'stdout.jsonl').open('w') as stdout, (artifact / 'stderr.txt').open('w') as stderr:
            proc = subprocess.Popen(['/usr/bin/time', '-l', *args], cwd=cwd, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            # Blocking wait avoids Python's timeout-wait polling (up to 50ms),
            # which otherwise quantizes these sub-second benchmark results.
            def timeout_kill():
                import signal
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            watchdog = threading.Timer(30, timeout_kill)
            watchdog.start()
            try:
                with TreeSampler(proc.pid) as sampler:
                    exit_code = proc.wait()
            finally:
                watchdog.cancel()
                watchdog.join()
        wall_ms = (time.perf_counter_ns() - started) / 1e6
        output = (artifact / 'stdout.jsonl').read_text()
        stderr = (artifact / 'stderr.txt').read_text()
        events, parse_errors = [], 0
        for line in output.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                parse_errors += 1
        tool_ends = [e for e in events if e.get('type') == 'tool_execution_end']
        assistant_messages = [e.get('message', {}) for e in events if e.get('type') == 'message_end' and e.get('message', {}).get('role') == 'assistant']
        final_ok = any('BENCH_OK' in str(m.get('content')) and m.get('stopReason') == 'stop' for m in assistant_messages)
        with server.lock:
            records = list(server.records.get(run_id, []))
        reasons = []
        if exit_code != 0: reasons.append('nonzero exit')
        if parse_errors: reasons.append('non-JSON protocol output')
        if not final_ok: reasons.append('missing successful final assistant response')
        expected = {'text': (1, 0), 'stream': (1, 0), 'resume-2000': (1, 0), 'read-large': (2, 1),
                    'tool-cycle': (5, 4), 'error-recovery': (4, 3), 'parallel-tools': (2, 4)}[case]
        if (len(records), len(tool_ends)) != expected:
            reasons.append(f'request/tool counts: {(len(records), len(tool_ends))} != {expected}')
        expected_names = {'text': [], 'stream': [], 'resume-2000': [], 'read-large': ['read'],
                          'tool-cycle': ['read', 'edit', 'write', 'bash'],
                          'error-recovery': ['edit', 'edit', 'bash'], 'parallel-tools': ['bash'] * 4}[case]
        if [e.get('toolName') for e in tool_ends] != expected_names:
            reasons.append('unexpected executed tool sequence')
        if case != 'error-recovery' and any(e.get('isError') for e in tool_ends):
            reasons.append('unexpected tool error')
        if case == 'tool-cycle':
            if (cwd / 'calc.py').read_text() != 'def add(a, b):\n    return a + b\n': reasons.append('incorrect edit')
            if not (cwd / 'test_calc.py').exists(): reasons.append('test file not written')
            else:
                check = subprocess.run(['python3', '-m', 'unittest', '-q'], cwd=cwd, capture_output=True, text=True)
                (artifact / 'acceptance-unittest.txt').write_text(check.stdout + check.stderr)
                if check.returncode: reasons.append('independent unit tests failed')
            if any(e.get('isError') for e in tool_ends): reasons.append('unexpected tool error')
        if case == 'error-recovery':
            if not tool_ends or not tool_ends[0].get('isError'): reasons.append('expected edit failure not signalled')
            if any(e.get('isError') for e in tool_ends[1:]): reasons.append('recovery failed')
            if 'return a + b' not in (cwd / 'calc.py').read_text(): reasons.append('recovery edit missing')
            if not records or 'RECOVERED' not in json.dumps(records[-1]['tool_results']): reasons.append('recovery assertion did not finish')
        if case == 'parallel-tools':
            returned = json.dumps(records[-1]['tool_results']) if records else ''
            if any(f'PARALLEL_{i}' not in returned for i in range(4)): reasons.append('parallel result missing')
        if case == 'read-large':
            returned = json.dumps(records[-1]['tool_results']) if records else ''
            if 'LARGE_MARKER' not in returned: reasons.append('read content missing')
        if case == 'resume-2000' and (not records or not records[0]['history_present'] or records[0]['messages'] < 4000):
            reasons.append('full history not resumed')
        if case == 'stream':
            deltas = [e for e in events if e.get('type') == 'message_update' and e.get('assistantMessageEvent', {}).get('type') == 'text_delta']
            if len(deltas) < 128: reasons.append('stream deltas missing')
        timing = re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys', stderr)
        rss = re.search(r'(\d+)\s+maximum resident set size', stderr)
        cpu_ms = (float(timing[2]) + float(timing[3])) * 1000 if timing else None
        result = {'run_id': run_id, 'case': case, 'accepted': not reasons, 'failures': reasons, 'exit_code': exit_code,
                  'wall_ms': wall_ms, 'cpu_ms': cpu_ms, 'avg_cpu_one_core_pct': cpu_ms / wall_ms * 100 if cpu_ms is not None else None,
                  'sampled_tree_peak_rss_mib': sampler.peak / 1048576, 'sample_count': sampler.samples, 'max_tree_processes': sampler.max_processes,
                  'time_max_process_rss_mib': int(rss[1]) / 1048576 if rss else None,
                  'first_request_ms': (records[0]['received_ns'] - started) / 1e6 if records else None,
                  'requests': len(records), 'tool_ends': len(tool_ends), 'request_bytes': [r['request_bytes'] for r in records]}
        (artifact / 'requests.json').write_text(json.dumps(records, indent=2) + '\n')
        (artifact / 'metrics.json').write_text(json.dumps(result, indent=2) + '\n')
        return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=int, default=10)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    pi, pig = shutil.which('pi'), shutil.which('pig')
    native = subprocess.check_output(['node', '-e', 'console.log(require(process.argv[1]).resolveBinary(process.platform,process.arch))', str(Path(pig).resolve())], text=True).strip()
    commands = {'pi-installed': pi, 'pig-installed': pig, 'pig-native': native}
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest = ROOT / 'results' / (stamp + ('-smoke' if args.smoke else '-workloads'))
    dest.mkdir(parents=True)
    metadata = {'timestamp_utc': stamp, 'runs': args.runs, 'warmups': 0 if args.smoke else 1,
                'model': 'deterministic loopback OpenAI SSE fixture; no inference or paid calls',
                'memory': 'live process-tree RSS sum sampled at ~5ms, shared pages may be counted more than once; short-lived peaks can be missed; excludes observer/model server',
                'cpu': 'macOS time user+sys cumulative CPU; 10ms granularity. CPU% = CPU time / wall time, 100% is one core, can exceed 100%.',
                'scope': 'warm-cache installed CLI comparison, differing upstream versions; no TUI, MCP, custom extensions, live-model quality, or security isolation claims',
                'versions': {n: subprocess.check_output([p, '--version'], text=True).strip() for n, p in commands.items()},
                'binary_sha256': {n: hashlib.sha256(Path(p).resolve().read_bytes()).hexdigest() for n, p in commands.items()},
                'machine': subprocess.check_output(['sw_vers'], text=True).strip(), 'arch': os.uname().machine}
    (dest / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    server = ModelServer()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    rows = []
    cases = ['text', 'stream', 'tool-cycle', 'error-recovery', 'parallel-tools', 'read-large', 'resume-2000']
    jobs = [(name, case) for name in commands for case in cases]
    rng = random.Random(42)
    try:
        if not args.smoke:
            for name, case in jobs:
                result = execute(commands[name], case, f'warmup-{name}-{case}', dest, server)
                if not result['accepted']:
                    raise RuntimeError(f'Warmup acceptance failed: {result}')
        for i in range(args.runs):
            rng.shuffle(jobs)
            for name, case in jobs:
                result = execute(commands[name], case, f'{i:02d}-{name}-{case}', dest, server)
                result['harness'] = name
                rows.append(result)
                print(f"{name:15} {case:16} {result['wall_ms']:7.1f}ms {'PASS' if result['accepted'] else result['failures']}", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        (dest / 'raw.json').write_text(json.dumps(rows, indent=2) + '\n')
    summary = []
    for case in cases:
        for name in commands:
            selected = [r for r in rows if r['case'] == case and r['harness'] == name]
            values = sorted(r['wall_ms'] for r in selected)
            summary.append({'case': case, 'harness': name, 'accepted': sum(r['accepted'] for r in selected), 'n': len(selected),
                            'median_ms': statistics.median(values), 'p90_ms': values[max(0, int(.9 * len(values) + .999) - 1)],
                            **{k: statistics.median(r[k] for r in selected if r[k] is not None) for k in
                               ['cpu_ms', 'avg_cpu_one_core_pct', 'sampled_tree_peak_rss_mib', 'first_request_ms']}})
    (dest / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    lines = ['# Pi vs PiG — Mac workload benchmark', '', json.dumps(metadata['versions']), '',
             'Actual CLI, streamed protocol, file tools, shell tests and session loading. Deterministic local model, NOT real LLM coding quality.', '',
             '| Case | Harness | Accept | Median ms | p90 ms | CPU ms | CPU % / core | Tree peak RSS MiB |',
             '|---|---|---:|---:|---:|---:|---:|---:|']
    for s in summary:
        lines.append(f"| {s['case']} | {s['harness']} | {s['accepted']}/{s['n']} | {s['median_ms']:.1f} | {s['p90_ms']:.1f} | {s['cpu_ms']:.1f} | {s['avg_cpu_one_core_pct']:.1f} | {s['sampled_tree_peak_rss_mib']:.1f} |")
    lines += ['', '## Method and limitations', '', metadata['memory'], '', metadata['cpu'], '', metadata['scope'], '',
              'The stream fixture deliberately sends 128 chunks 2ms apart. Read-large uses ~1.1MB text. Resume uses 2,000 user/assistant exchanges. Parallel-tools requests four 100ms bash jobs in one response; scheduling remains the harness default.', '',
              'Acceptance checks exit status, valid JSONL, final stop response, exact request/tool counts, streamed deltas, edit-error signalling/recovery, returned read/parallel markers and full resumed history. Tool-cycle independently reruns four arithmetic unittest cases outside the timed region.', '',
              'Fixture preparation and independent post-run acceptance are excluded from elapsed time. Process launch, provider requests, tool work, session loading and teardown are included. One warmup per harness/case; measured order is shuffled each repetition. Failed runs are retained, not dropped.', '',
              f'Reproduce: `python3 benchmark/pi-vs-pig/mac_workloads.py --runs {args.runs}`']
    (dest / 'report.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print('Artifacts:', dest)
    if any(not r['accepted'] for r in rows):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
