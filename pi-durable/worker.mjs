import { existsSync, fstatSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createModels, getSupportedThinkingLevels } from '@earendil-works/pi-ai/models';
import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import { AssistantEntry } from '@earendil-works/pi-durable';
import { assert, atomicJson, checkRecovery, context, openRuntime, readJson, reconcile,
  RecoveryBlocked, submit, unsafeTasks, validateConfig } from './runtime.mjs';

const [command, taskDir, payloadJson] = process.argv.slice(2);
const payload = JSON.parse(payloadJson || '{}');
const emit = value => process.stdout.write(JSON.stringify(value) + '\n');
const lockFd = Number(process.env.MEGAI_DURABLE_LOCK_FD);
assert(Number.isInteger(lockFd) && lockFd >= 3 && fstatSync(lockFd).isFile(), 'Use launcher.py: storage lock required');
process.umask(0o077);
let runtime;
let closing = false;
let stopTimer;
let view;
let closePromise;
const close = () => {
  closing = true;
  closePromise ??= runtime ? runtime.harness.close(context) : Promise.resolve();
  return closePromise;
};
const requestClose = () => { void close().catch(error => emit({ event: 'diagnostic', message: String(error) })); };
process.on('SIGINT', requestClose);
process.on('SIGTERM', requestClose);
try {
  const configPath = join(taskDir, 'config.json');
  if (command === 'init') {
    assert(!existsSync(configPath), 'Task already initialized; never overwrite');
    atomicJson(configPath, validateConfig(payload));
    emit({ status: 'initialized', task: taskDir, config: payload });
  } else {
    const config = validateConfig(readJson(configPath));
    // Tests inject a module only when the caller explicitly invokes this internal worker; public CLI has no plugin flag.
    const fixture = process.env.MEGAI_DURABLE_TEST_MODULE;
    const injected = fixture ? await (await import(fixture)).create(config, taskDir) : undefined;
    const models = injected?.models ?? (['status', 'reconcile', 'cancel'].includes(command) ? createModels()
      : await ModelRuntime.create({ authPath: join(config.agentDir, 'auth.json'), modelsPath: join(config.agentDir, 'models.json'),
        modelsStorePath: join(config.agentDir, 'models-store.json'), allowModelNetwork: false }));
    if (!['status', 'reconcile', 'cancel'].includes(command)) {
      const model = models.getModel(config.provider, config.model);
      assert(model, `Model unavailable: ${config.provider}/${config.model}. Check the standalone agentDir catalog/auth; no fallback performed.`);
      assert(getSupportedThinkingLevels(model).includes(config.thinking), `Unsupported thinking level ${config.thinking}; no silent clamping`);
      assert(await models.checkAuth(config.provider), `Provider not configured: ${config.provider}`);
    }
    runtime = await openRuntime(taskDir, { models, tools: injected?.tools,
      onReport: error => emit({ event: 'diagnostic', message: String(error) }) });
    if (command === 'status') {
      const inspection = await runtime.harness.inspect(context);
      emit({ status: 'offline', unsafe: await unsafeTasks(runtime), inspection, usage: await runtime.harness.usage(context) });
    } else if (command === 'reconcile') {
      emit({ status: 'reconciled', tasks: await reconcile(runtime, payload.note) });
    } else if (command === 'cancel') {
      await checkRecovery(runtime);
      assert(typeof payload.note === 'string' && payload.note.trim().length >= 10 && payload.note.length <= 8000, 'Cancellation note required (10–8000 characters)');
      await runtime.root.abort(context);
      await runtime.root.commit(tx => tx.appendEntry(runtime.root.id, { kind: 'megai.cancellation', data: { note: payload.note } }), context);
      emit({ status: 'cancelled', transcriptRetained: true });
    } else if (command === 'doctor') {
      emit({ status: 'ready', version: '1.1.0', model: `${config.provider}/${config.model}`,
        thinking: config.thinking, allowWrite: config.allowWrite, durability: 'SQLite WAL/FULL', unsafe: await unsafeTasks(runtime) });
    } else if (command === 'run' || command === 'resume') {
      await checkRecovery(runtime);
      const runId = process.env.MEGAI_DURABLE_RUN_ID;
      stopTimer = setInterval(() => {
        try {
          const path = join(taskDir, 'stop.json');
          if (existsSync(path) && readJson(path).runId === runId) requestClose();
        } catch (error) { emit({ event: 'diagnostic', message: String(error) }); requestClose(); }
      }, 200);
      view = await runtime.root.viewState(context);
      view.subscribe(value => {
        const live = value.docs['pi.live'];
        atomicJson(join(taskDir, 'progress.json'), { schema: 1, runId, workerPid: process.pid,
          updatedAt: new Date().toISOString(), live, usage: value.docs['pi.usage'] });
      });
      let request;
      if (command === 'run') {
        request = { requestId: payload.requestId, content: readFileSync(payload.promptFile, 'utf8') };
        const active = join(taskDir, 'active.json');
        if (existsSync(active)) {
          const old = readJson(active);
          assert(old.requestId === request.requestId && old.content === request.content,
            'Existing active request: resume it before submitting a new request');
        } else atomicJson(active, request);
      } else {
        assert(existsSync(join(taskDir, 'active.json')), 'No active request to resume');
        request = readJson(join(taskDir, 'active.json'));
      }
      emit({ event: 'admitting', requestId: request.requestId, workerPid: process.pid });
      const submission = await submit(runtime, request);
      emit({ event: 'admitted', submissionId: submission.id, requestId: request.requestId });
      const settled = await submission.wait(context);
      let answer;
      if (settled.status === 'done') answer = await runtime.root.commit(tx => tx.entry(AssistantEntry, settled.answer), context);
      emit({ event: 'settled', submission: settled, answer: answer?.model });
      atomicJson(join(taskDir, 'result.json'), { requestId: request.requestId, submission: settled, answer: answer?.model ?? null });
      // An immutable request archive makes retries safe, while active.json is removed only by the locked launcher after a clean success.
      process.exitCode = settled.status === 'done' ? 0 : 1;
    } else throw new Error('Unknown worker command');
  }
} catch (error) {
  if (error instanceof RecoveryBlocked) { emit({ status: 'blocked', message: error.message, tasks: error.tasks }); process.exitCode = 2; }
  else if (closing) { emit({ status: 'stopped', message: 'Pending work retained; explicit resume required' }); process.exitCode = 130; }
  else { emit({ status: 'error', message: String(error) }); process.exitCode = 1; }
} finally {
  clearInterval(stopTimer);
  view?.dispose();
  await close();
}
