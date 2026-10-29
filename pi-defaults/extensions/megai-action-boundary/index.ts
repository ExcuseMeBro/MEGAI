import { homedir } from 'node:os';
import { join } from 'node:path';
import type { ExtensionAPI } from '@mariozechner/pi-coding-agent';
import { createBoundary } from './boundary.mjs';

// This observes Pi's tool events only. It cannot constrain extension code that
// invokes the OS directly, other agents, terminal commands or plugin internals.
export default function (pi: ExtensionAPI) {
  const boundary = createBoundary({ traceDir: join(homedir(), '.megai', 'private', 'pi-tool-traces') });
  pi.on('tool_call', (event, ctx) => boundary.onToolCall(event, ctx));
  pi.on('tool_execution_end', (event) => boundary.onToolEnd(event));
  pi.on('session_shutdown', () => boundary.close());
}
