#!/usr/bin/env python3
"""Real coding model benchmark with independent hidden acceptance, disposable repos.
Uses an existing Pi OAuth credential in a temporary 0600 file; never stores it
in evidence. No provider fallback, no automatic repair/retry after a failed run.
"""
import argparse
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time

from live_tasks import TASKS
from mac_workloads import TreeSampler

ROOT = Path(__file__).resolve().parent
MODEL = 'gpt-6.1-sol'
PROVIDER = 'openai-codex'
THINKING = 'medium'

ACCEPTANCE_RUNNER = '''import importlib.util, json, sys, unittest
sys.path.insert(0, sys.argv[1])
spec=importlib.util.spec_from_file_location('independent_acceptance',sys.argv[2])
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(m))
print(json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped),'passed':r.testsRun-len(r.failures)-len(r.errors)-len(r.skipped)}))
sys.exit(0 if r.wasSuccessful() else 1)
'''

def acceptance(cwd, artifact, task):
    suite = artifact / 'hidden_acceptance.py'
    suite.write_text(task['acceptance'])
    result = subprocess.run([sys.executable, '-c', ACCEPTANCE_RUNNER, str(cwd), str(suite)], capture_output=True, text=True, timeout=20)
    (artifact / 'acceptance.log').write_text(result.stdout + result.stderr)
    try:
        metrics = json.loads(result.stdout.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        metrics = {'tests': 0, 'passed': 0, 'errors': 1, 'failures': 0, 'skipped': 0}
    metrics['exit_code'] = result.returncode
    return metrics

def refactor_checks(cwd, task):
    source = (cwd / 'orders.py').read_text()
    problems = []
    if source == task['files']['orders.py']:
        problems.append('refactor left original implementation unchanged')
    try:
        tree = ast.parse(source)
        for field in ('qty', 'price', 'discount'):
            count = sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'get' and n.args and
                        isinstance(n.args[0], ast.Constant) and n.args[0].value == field for n in ast.walk(tree))
            if count > 1:
                problems.append(f'duplicated {field} extraction ({count} sites)')
    except SyntaxError:
        problems.append('refactored source has syntax error')
    return problems

def run(command, harness, task_name, iteration, dest, credential, deadline):
    task = TASKS[task_name]
    run_id = f'{iteration:02d}-{harness}-{task_name}'
    artifact = dest / run_id
    artifact.mkdir()
    (artifact / 'prompt.txt').write_text(task['prompt'] + '\n')
    with tempfile.TemporaryDirectory(prefix='pi-pig-live-') as temporary:
        home = Path(temporary)
        cwd = home / 'workspace'
        cwd.mkdir()
        for name, source in task['files'].items():
            (cwd / name).write_text(source)
        subprocess.run(['git', 'init', '-q', str(cwd)], check=True)
        subprocess.run(['git', '-C', str(cwd), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(cwd), '-c', 'user.name=Benchmark', '-c', 'user.email=benchmark@example.invalid',
                        '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture baseline'], check=True)
        agent = home / 'agent'
        agent.mkdir(mode=0o700)
        auth = agent / 'auth.json'
        auth.touch(mode=0o600)
        auth.write_text(json.dumps({PROVIDER: credential}))
        (agent / 'settings.json').write_text(json.dumps({'compaction': {'enabled': False}, 'enableInstallTelemetry': False}))
        # Explicit metadata prevents model-catalog drift between isolated homes.
        (agent / 'models.json').write_text(json.dumps({'providers': {PROVIDER: {'models': [{
            'id': MODEL, 'name': MODEL, 'reasoning': True, 'input': ['text'], 'contextWindow': 272000, 'maxTokens': 8192}]}}}))
        env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR', 'USER', 'SHELL')}
        env.update({'HOME': temporary, 'PI_OFFLINE': '1', 'PIG_OFFLINE': '1', 'PI_TELEMETRY': '0',
                    'PI_CODING_AGENT_DIR': str(agent), 'PIG_CODING_AGENT_DIR': str(agent), 'PIG_HOME': str(home / 'pig')})
        args = [command, '--offline', '--no-extensions', '--no-skills', '--no-prompt-templates', '--no-themes', '--no-context-files',
                '--no-approve', '--no-session', '--provider', PROVIDER, '--model', MODEL, '--thinking', THINKING,
                '--mode', 'json', '--tools', 'read,write,edit,bash', task['prompt']]
        events = []
        parsed_times = []
        parse_errors = []
        timed_out = threading.Event()
        started = time.perf_counter_ns()
        with (artifact / 'stdout.jsonl').open('w') as outfile, (artifact / 'stderr.txt').open('w') as errfile:
            process = subprocess.Popen(['/usr/bin/time', '-l', *args], cwd=cwd, env=env, stdout=subprocess.PIPE,
                                       stderr=errfile, text=True, start_new_session=True)
            def collect():
                for line in process.stdout:
                    outfile.write(line)
                    outfile.flush()
                    try:
                        events.append(json.loads(line))
                        parsed_times.append((time.perf_counter_ns() - started) / 1e6)
                    except json.JSONDecodeError:
                        parse_errors.append('non-JSON stdout')
            reader = threading.Thread(target=collect)
            reader.start()
            def kill():
                timed_out.set()
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            watchdog = threading.Timer(deadline, kill)
            watchdog.start()
            try:
                with TreeSampler(process.pid) as sampler:
                    code = process.wait()
                finished = time.perf_counter_ns()
            finally:
                watchdog.cancel(); watchdog.join()
                reader.join(timeout=5)
                process.stdout.close()
        wall_ms = (finished - started) / 1e6
        stderr = (artifact / 'stderr.txt').read_text()
        timing = re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys', stderr)
        cpu_ms = (float(timing[2]) + float(timing[3])) * 1000 if timing else None
        messages = [e['message'] for e in events if e.get('type') == 'message_end' and e.get('message', {}).get('role') == 'assistant']
        tools = [e for e in events if e.get('type') == 'tool_execution_end']
        model_ids = sorted({m.get('model', '') for m in messages})
        providers = sorted({m.get('provider', '') for m in messages})
        thinking_levels = sorted({m.get('thinkingLevel', '') for m in messages})
        first_delta_ms = next((t for e,t in zip(events, parsed_times) if e.get('type') == 'message_update' and
                              e.get('assistantMessageEvent', {}).get('type') in ('text_delta', 'thinking_delta')), None)
        usage = {k: sum(m.get('usage', {}).get(k, 0) for m in messages) for k in ('input', 'output', 'cacheRead', 'cacheWrite', 'totalTokens')}
        failed = list(parse_errors)
        if code != 0: failed.append(f'CLI exit {code}')
        if timed_out.is_set(): failed.append('deadline exceeded')
        if model_ids != [MODEL] or providers != [PROVIDER]: failed.append('model/provider identity mismatch or no response')
        if any(level and level != THINKING for level in thinking_levels): failed.append('reported thinking differs from requested medium')
        if not messages or messages[-1].get('stopReason') != 'stop': failed.append('no final successful stop')
        for name, source in task['files'].items():
            if name.startswith('test_') and (not (cwd/name).is_file() or (cwd/name).read_text() != source):
                failed.append('public test modified/deleted')
        check = acceptance(cwd, artifact, task)
        if check['exit_code'] or not check['tests'] or check['skipped']: failed.append('hidden acceptance failed')
        if task_name == 'order-refactor': failed.extend(refactor_checks(cwd, task))
        # Preserve generated fixture source, not credentials or user config.
        generated = artifact / 'workspace'
        generated.mkdir()
        for path in cwd.rglob('*'):
            if path.is_file() and '.git' not in path.relative_to(cwd).parts and '__pycache__' not in path.relative_to(cwd).parts:
                target = generated / path.relative_to(cwd)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        diff = subprocess.run(['git', '-C', str(cwd), 'diff', '--no-ext-diff'], capture_output=True, text=True)
        (artifact / 'changes.diff').write_text(diff.stdout)
        result = {'run_id': run_id, 'harness': harness, 'task': task_name, 'iteration': iteration, 'accepted': not failed,
                  'failures': failed, 'exit_code': code, 'timed_out': timed_out.is_set(), 'acceptance_tests': check,
                  'wall_ms': wall_ms, 'cpu_ms': cpu_ms, 'avg_cpu_one_core_pct': cpu_ms / wall_ms * 100 if cpu_ms is not None else None,
                  'sampled_tree_peak_rss_mib': sampler.peak / 1048576, 'memory_samples': sampler.samples,
                  'first_delta_ms': first_delta_ms, 'assistant_responses': len(messages), 'tools': len(tools),
                  'tool_errors': sum(bool(e.get('isError')) for e in tools), 'usage': usage,
                  'reported_models': model_ids, 'reported_providers': providers, 'reported_thinking': thinking_levels}
        (artifact / 'metrics.json').write_text(json.dumps(result, indent=2) + '\n')
        return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runs',type=int,default=2)
    parser.add_argument('--deadline',type=int,default=180)
    parser.add_argument('--task',choices=list(TASKS))
    args=parser.parse_args()
    pi,pig=shutil.which('pi'),shutil.which('pig')
    native=subprocess.check_output(['node','-e','console.log(require(process.argv[1]).resolveBinary(process.platform,process.arch))',str(Path(pig).resolve())],text=True).strip()
    commands={'pi':pi,'pig-native':native}
    auth_path=Path(os.environ.get('PI_CODING_AGENT_DIR',str(Path.home()/'.pi/agent')))/'auth.json'
    # Only this provider's credential is copied. Never emitted into evidence.
    credential=json.loads(auth_path.read_text()).get(PROVIDER)
    if not credential: raise SystemExit('Pi OAuth credential missing; no provider fallback')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest=ROOT/'results'/(stamp+'-live-coding');dest.mkdir(parents=True)
    metadata={'model':MODEL,'provider':PROVIDER,'thinking':THINKING,'runs_per_task_harness':args.runs,'deadline_seconds':args.deadline,
              'same_account':True,'credential_source':'existing Pi provider OAuth, ephemeral 0600 copy; secrets not in artifacts',
              'versions':{n:subprocess.check_output([p,'--version'],text=True).strip() for n,p in commands.items()},
              'task_prompt_sha256':{n:hashlib.sha256(t['prompt'].encode()).hexdigest() for n,t in TASKS.items()},
              'machine':subprocess.check_output(['sw_vers'],text=True).strip(),'arch':os.uname().machine,
              'scope':'Real model, actual coding/tools, 3 small Python tasks; n=2 is exploratory, not statistically decisive. System prompts/tool schemas remain harness defaults. No retry, repair, fallback or best-of selection. No browser.',
              'memory':'Sampled live process-tree RSS sum (~5ms), includes tool children, excludes observer; shared-page duplication possible.',
              'usage':'Provider-reported per-response token counters; no invoice/cost estimate for subscription calls.'}
    (dest/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    tasks=[args.task] if args.task else list(TASKS)
    # Record the original fixture acceptance before any model work.
    for name in tasks:
        before=dest/('baseline-'+name);before.mkdir()
        with tempfile.TemporaryDirectory(prefix='pi-pig-baseline-') as temporary:
            cwd=Path(temporary)
            for file,content in TASKS[name]['files'].items(): (cwd/file).write_text(content)
            check=acceptance(cwd,before,TASKS[name])
            (before/'metrics.json').write_text(json.dumps(check,indent=2)+'\n')
    print('ARTIFACTS',dest,flush=True)
    rows=[]
    rng=random.Random(73)
    try:
        for i in range(args.runs):
            jobs=[(n,t) for n in commands for t in tasks];rng.shuffle(jobs)
            for harness,task in jobs:
                print('START',i,harness,task,flush=True)
                result=run(commands[harness],harness,task,i,dest,credential,args.deadline)
                rows.append(result)
                (dest/'raw.json').write_text(json.dumps(rows,indent=2)+'\n')
                print('RESULT',json.dumps(result),flush=True)
                if not result['reported_models']:
                    raise RuntimeError('No verified real-model response; stop and reconcile rather than retry/fallback')
    finally:
        (dest/'raw.json').write_text(json.dumps(rows,indent=2)+'\n')
    summary=[]
    for task in tasks:
        for harness in commands:
            selected=[r for r in rows if r['task']==task and r['harness']==harness]
            summary.append({'task':task,'harness':harness,'n':len(selected),'accepted':sum(r['accepted'] for r in selected),
                            'median_seconds':statistics.median(r['wall_ms'] for r in selected)/1000,
                            'median_cpu_ms':statistics.median(r['cpu_ms'] for r in selected if r['cpu_ms'] is not None),
                            'median_peak_rss_mib':statistics.median(r['sampled_tree_peak_rss_mib'] for r in selected),
                            'median_output_tokens':statistics.median(r['usage']['output'] for r in selected)})
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['# Real-model coding benchmark on this Mac','',json.dumps(metadata['versions']),f'Model: {PROVIDER}/{MODEL}; thinking={THINKING}; same OAuth account.',
           '', '| Task | Harness | Acceptance | Median sec | CPU ms | Tree peak RSS MiB | Output tokens |','|---|---|---:|---:|---:|---:|---:|']
    for s in summary:
        lines.append(f"| {s['task']} | {s['harness']} | {s['accepted']}/{s['n']} | {s['median_seconds']:.2f} | {s['median_cpu_ms']:.0f} | {s['median_peak_rss_mib']:.1f} | {s['median_output_tokens']:.0f} |")
    lines+=['',metadata['scope'],'',metadata['memory'],'',metadata['usage'],'',
            'Acceptance: independent hidden tests, intact public tests, verified model/provider, final successful stop, no timeout. Refactor also requires a changed implementation and no duplicated qty/price/discount extraction sites (AST checks). Baseline tests and all failed runs retained. No acceptance-driven second chance.',
            '',f'Reproduce: `python3 benchmark/pi-vs-pig/mac_live_coding.py --runs {args.runs} --deadline {args.deadline}`']
    (dest/'report.md').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines),flush=True)

if __name__=='__main__':main()
