import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { dependencies, evalSummary, FlowError, formatReceipt, isActive, isHumanWait, readiness, records, requiredChecks, SHA, taskNumber } from './core.mjs';
import { loadEval, reader } from './reader.mjs';

const HELP = 'Factory Flow (read-only): needs | ready | resume PROJECT#ID | receipt PROJECT#ID FULL_SHA | eval PATH';
const MAX_QUEUE = 24;
const MAX_DETAILS = 16;
const CONCURRENCY = 4;
const shown = (lines: string[]) => lines.join('\n');

export function registerFactoryFlow(pi: ExtensionAPI, api = reader()) {
  let busy = false;
  pi.registerCommand('factory-flow', {
    description: 'Read Brokan handoffs, dependency readiness, exact-SHA receipts or a paired eval',
    handler: async (input, ctx) => {
      if (busy) { ctx.ui.notify('Factory Flow is already reading.', 'warning'); return; }
      busy = true;
      try {
        const line = input.trim();
        const parts = line.split(/\s+/);
        const command = parts[0];
        if (command === '' || command === 'help') { ctx.ui.notify(HELP, 'info'); return; }
        if (command === 'eval') {
          const report = evalSummary(await loadEval(ctx.cwd, line.slice(4).trim()));
          const lines = report.summary.map(arm => `${arm.arm}: accepted ${arm.accepted}/${report.pairs} without regressions | regressions ${arm.regressions} | ${arm.medianMs} ms median | faster in ${arm.faster}/${report.pairs} | median cost ${arm.medianUsdMicros === null ? 'unavailable' : `$${(arm.medianUsdMicros / 1e6).toFixed(6)}`}`);
          ctx.ui.notify(shown([`Paired eval: ${report.pairs} pairs; comparable costs for ${report.costPairs}.`, ...lines]), 'info');
          return;
        }
        if (!((['needs', 'ready'].includes(command) && parts.length === 1) ||
              (command === 'resume' && parts.length === 2) ||
              (command === 'receipt' && parts.length === 3 && SHA.test(parts[2])))) throw new FlowError(HELP);
        const board = await api.board(ctx.cwd);
        const { project, tasks } = board;
        const openRead = async (id: number) => {
          const { value, comments } = await api.detail(project, id);
          return { value, state: records(comments, id) };
        };
        if (command === 'resume' || command === 'receipt') {
          const id = taskNumber(parts[1], project);
          const { value, state } = await openRead(id);
          if (command === 'receipt') { ctx.ui.notify(shown(formatReceipt(state, parts[2], requiredChecks(value.description))), 'info'); return; }
          const lines = [`${project}#${id} — ${value.status}${value.human ? ' (human-owned)' : ''}; read-only. Verify ownership and user approval before resuming.`];
          for (const wait of [...state.active.values()].slice(0, 6)) {
            lines.push(`${wait.key} [${wait.type}]: ${wait.blocked}`, `Question: ${wait.question}`, `Recommend: ${wait.recommendation}`, `Next after answer: ${wait.next}`);
          }
          for (const { wait, answer } of [...state.answered.values()].slice(-6)) lines.push(`${wait.key} [answer on task, not authorization]: ${answer}`, `Recorded next: ${wait.next}`);
          if (state.active.size > 6 || state.answered.size > 6) lines.push('Showing up to six of each; inspect the task for remaining records.');
          if (!state.active.size && !state.answered.size) lines.push('No Factory handoff has been recorded.');
          ctx.ui.notify(shown(lines), 'info');
          return;
        }
        const eligible = [...tasks.values()].filter(isActive);
        const queue = eligible.slice(0, MAX_QUEUE);
        const pending = queue.filter(item => item.comments > 0);
        const states = new Map<number, ReturnType<typeof records> | null>();
        for (let i = 0; i < Math.min(pending.length, MAX_DETAILS); i += CONCURRENCY) {
          await Promise.all(pending.slice(i, i + CONCURRENCY).map(async item => {
            try {
              const { value, state } = await openRead(item.id);
              // A changed snapshot isn't proof of readiness; redo this read manually.
              states.set(item.id, value.updated_at === item.updated_at && value.status === item.status && value.human === item.human &&
                value.description === item.description && value.comments === item.comments ? state : null);
            } catch { states.set(item.id, null); }
          }));
        }
        const lines = [`${project} — ${command === 'ready' ? 'dependency readiness (no dispatch)' : 'task handoffs'}`];
        if (command === 'needs') {
          let unknown = 0, count = 0;
          for (const item of pending) {
            const state = states.get(item.id);
            if (!state) { unknown++; continue; }
            if (!state.active.size) continue;
            const open = [...state.active.values()];
            for (const wait of open.slice(0, 3)) lines.push(`${project}#${item.id} — ${isHumanWait(wait) ? 'needs you' : 'waiting for resource/check'} [${wait.key}]: ${wait.question}`);
            if (open.length > 3) lines.push(`${project}#${item.id} — ${open.length - 3} more; use resume.`);
            count += open.length;
          }
          if (!count) lines.push(unknown || eligible.length > queue.length ? 'No open questions in the verified portion.' : 'No open Factory handoffs.');
          if (unknown) lines.push(`${unknown} tasks could not be checked; use resume for an exact task.`);
        } else {
          // Brokan may omit older Done items. Request only bounded, graph-reachable missing dependencies.
          const visited = new Set<number>();
          const missing = new Set<number>();
          const scan = (id: number) => {
            if (visited.has(id) || visited.size >= 160) return;
            visited.add(id);
            const value = tasks.get(id);
            if (!value) { missing.add(id); return; }
            try { for (const dep of dependencies(value.description, project)) scan(dep); }
            catch (err) { if (!(err instanceof FlowError)) throw err; }
          };
          if (board.doneHidden) {
            let budget = 12;
            for (let frontier = queue.map(item => item.id); frontier.length && budget > 0;) {
              for (const id of frontier) scan(id);
              const batch = [...missing].slice(0, Math.min(CONCURRENCY, budget));
              if (!batch.length) break;
              frontier = [];
              for (const id of batch) missing.delete(id);
              budget -= batch.length;
              await Promise.all(batch.map(async id => {
                try { const { value } = await api.detail(project, id); tasks.set(id, value); visited.delete(id); frontier.push(id); }
                catch { /* Unknown dependencies remain blocked. */ }
              }));
            }
          }
          for (const item of queue) {
            const state = item.comments > 0 ? (states.get(item.id) ?? null) : records([], item.id);
            const blockers = readiness(item, tasks, state);
            lines.push(`${project}#${item.id} — ${blockers.length ? `waiting: ${blockers.slice(0, 5).join('; ')}${blockers.length > 5 ? '; …' : ''}` : 'ready for manual review'}`);
          }
          if (!queue.length) lines.push('No agent-owned todo/doing candidates.');
          lines.push('A ready label is a snapshot, not an ownership check or permission to run.');
        }
        if (eligible.length > queue.length) lines.push(`Partial view: ${queue.length} of ${eligible.length} candidates.`);
        ctx.ui.notify(shown(lines), 'info');
      } catch (err) { ctx.ui.notify(err instanceof FlowError ? err.message : 'Factory Flow could not complete the read.', 'error'); }
      finally { busy = false; }
    },
  });
}

export default function (pi: ExtensionAPI) { registerFactoryFlow(pi); }
