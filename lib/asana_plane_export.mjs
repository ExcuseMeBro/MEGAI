#!/usr/bin/env node
/** Read-only Asana MCP export. Private data never belongs in the checkout. */
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

export const ASANA_URL = 'https://mcp.asana.com/v2/mcp';
const READ_TOOLS = new Set(['get_me', 'get_projects', 'get_project', 'get_tasks', 'get_my_tasks', 'get_task', 'get_subtasks', 'get_stories', 'get_task_stories', 'get_attachments', 'get_attachment', 'get_users', 'get_tags', 'get_custom_fields', 'get_dependencies', 'get_dependents']);
export const hash = value => crypto.createHash('sha256').update(value).digest('hex');
export const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

export function privateRoot(directory) {
  const root = path.resolve(directory);
  for (let p = root;; p = path.dirname(p)) {
    if (fs.existsSync(path.join(p, '.git'))) throw new Error('Export storage must be outside a Git checkout');
    if (fs.existsSync(p) && fs.lstatSync(p).isSymbolicLink()) throw new Error('Symlink storage is not allowed');
    if (p === path.dirname(p)) break;
  }
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  const stat = fs.lstatSync(root);
  if (!stat.isDirectory() || (stat.mode & 0o077) || stat.uid !== process.getuid()) throw new Error('Export directory must be owned by this user and mode 0700');
  return root;
}

export function saveJson(root, relative, value) {
  const file = path.resolve(root, relative);
  if (!file.startsWith(root + path.sep)) throw new Error('Invalid export path');
  const parent = path.dirname(file);
  for (let p = parent; p.startsWith(root); p = path.dirname(p)) {
    if (fs.existsSync(p) && fs.lstatSync(p).isSymbolicLink()) throw new Error('Symlink export path');
    if (p === root) break;
  }
  fs.mkdirSync(parent, { recursive: true, mode: 0o700 });
  if (fs.existsSync(file) && fs.lstatSync(file).isSymbolicLink()) throw new Error('Symlink export file');
  const tmp = file + '.' + crypto.randomUUID() + '.tmp';
  const fd = fs.openSync(tmp, 'wx', 0o600);
  try { fs.writeFileSync(fd, JSON.stringify(value, null, 2) + '\n'); fs.fsyncSync(fd); }
  finally { fs.closeSync(fd); }
  fs.renameSync(tmp, file);
  const directoryFd = fs.openSync(parent, 'r');
  try { fs.fsyncSync(directoryFd); } finally { fs.closeSync(directoryFd); }
}

export function decodeRpc(text, id) {
  let values;
  try { values = [JSON.parse(text)]; }
  catch {
    values = text.split(/\r?\n\r?\n/).map(block => block.split(/\r?\n/).filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')).filter(Boolean).map(data => JSON.parse(data));
  }
  const result = values.find(value => value.id === id);
  if (!result) throw new Error('Missing matching JSON-RPC response');
  if (result.error) throw new Error(`MCP protocol error ${result.error.code ?? 'unknown'}`);
  return result.result;
}

export function toolData(result) {
  if (result?.isError) {
    const error = new Error('Asana read tool returned isError');
    Object.defineProperty(error, 'privateResult', { value: result });
    throw error;
  }
  let data = result?.structuredContent;
  if (!data) {
    const blocks = result?.content?.filter(block => block.type === 'text') ?? [];
    if (blocks.length !== 1) throw new Error('Expected one structured Asana tool result');
    data = JSON.parse(blocks[0].text);
  }
  if (!data || data.error || data.errors || data.success === false) throw new Error('Asana returned a nested error');
  return data;
}

export class ReadOnlyAsana {
  constructor(tokenProvider, { fetcher = fetch, delay = sleep, interval = 500 } = {}) {
    this.tokenProvider = tokenProvider; this.fetcher = fetcher; this.delay = delay; this.interval = interval;
    this.id = 0; this.nextAt = 0; this.catalog = []; this.session = undefined;
  }
  async rpc(method, params) {
    if (!['initialize', 'tools/list', 'tools/call'].includes(method)) throw new Error('Read-only MCP method rejected');
    if (method === 'tools/call' && !READ_TOOLS.has(String(params?.name).replace(/^asana_/, ''))) throw new Error('Asana mutation rejected at transport');
    const id = ++this.id;
    for (let attempt = 0; attempt < 5; attempt++) {
      const wait = Math.max(0, this.nextAt - Date.now());
      this.nextAt = Math.max(Date.now(), this.nextAt) + this.interval;
      if (wait) await this.delay(wait);
      const tokens = await this.tokenProvider();
      if (!tokens?.accessToken) throw new Error('Asana OAuth is unavailable; reauthenticate with the existing adapter');
      const headers = { Authorization: `Bearer ${tokens.accessToken}`, 'Content-Type': 'application/json', Accept: 'application/json, text/event-stream' };
      if (this.session) headers['Mcp-Session-Id'] = this.session;
      if (this.protocol) headers['MCP-Protocol-Version'] = this.protocol;
      let response;
      try {
        response = await this.fetcher(ASANA_URL, { method: 'POST', headers, redirect: 'error', signal: AbortSignal.timeout(120000), body: JSON.stringify({ jsonrpc: '2.0', id, method, params }) });
      } catch { if (attempt === 4) throw new Error('Asana read transport failed'); await this.delay(1000 * 2 ** attempt); continue; }
      if ([429, 502, 503, 504].includes(response.status) && attempt < 4) {
        const seconds = Number(response.headers.get('retry-after'));
        await response.body?.cancel();
        await this.delay(Math.min(120000, seconds > 0 ? seconds * 1000 : 1000 * 2 ** attempt)); continue;
      }
      if (!response.ok) { await response.body?.cancel(); throw new Error(`Asana HTTP ${response.status}`); }
      const session = response.headers.get('mcp-session-id'); if (session) this.session = session;
      return decodeRpc(await response.text(), id);
    }
  }
  async initialize() {
    const init = await this.rpc('initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'megai-readonly-export', version: '1.0.0' } });
    this.protocol = init.protocolVersion;
    let cursor; const seen = new Set();
    do {
      const response = await this.rpc('tools/list', cursor ? { cursor } : {});
      if (!Array.isArray(response.tools)) throw new Error('Invalid MCP catalog');
      this.catalog.push(...response.tools); cursor = response.nextCursor;
      if (cursor && seen.has(cursor)) throw new Error('Repeated catalog cursor');
      seen.add(cursor);
    } while (cursor);
  }
  resolve(name) {
    if (!READ_TOOLS.has(name)) throw new Error('Asana mutation or unsupported read rejected');
    const tool = this.catalog.find(t => t.name === name || t.name === `asana_${name}`);
    if (!tool) throw new Error(`Read tool unavailable: ${name}`);
    return tool;
  }
  async call(name, args = {}) {
    const tool = this.resolve(name);
    return toolData(await this.rpc('tools/call', { name: tool.name, arguments: args }));
  }
}

export async function paginate(call, args = {}) {
  const records = []; const seen = new Set(); let offset;
  do {
    const response = await call({ ...args, limit: 100, ...(offset ? { offset } : {}) });
    if (!Array.isArray(response.data)) throw new Error('Expected paginated data array');
    records.push(...response.data);
    if (!Object.hasOwn(response, 'next_page')) throw new Error('Missing pagination completion evidence');
    const next = response.next_page;
    if (next != null && (typeof next !== 'object' || typeof next.offset !== 'string' || !next.offset)) throw new Error('Malformed pagination cursor');
    offset = next?.offset;
    if (offset && seen.has(offset)) throw new Error('Repeated pagination cursor');
    if (offset) seen.add(offset);
  } while (offset);
  return records;
}

export function singleFlightTokens(load, now = Date.now) {
  let cached; let pending;
  return async () => {
    if (cached?.accessToken && Number(cached.expiresAt) * 1000 > now() + 60000) return cached;
    if (!pending) pending = Promise.resolve().then(load).then(value => { cached = value; return value; }).finally(() => { pending = undefined; });
    return pending;
  };
}

export async function connectAsana() {
  const adapter = path.join(os.homedir(), '.pi/agent/npm/node_modules/pi-mcp-adapter');
  const require = createRequire(path.join(adapter, 'package.json'));
  const { createJiti } = require('jiti');
  const jiti = createJiti(import.meta.url);
  const { getMcpOAuthTokensForUrl } = await jiti.import(path.join(adapter, 'oauth.ts'));
  const client = new ReadOnlyAsana(singleFlightTokens(() => getMcpOAuthTokensForUrl('asana', ASANA_URL)));
  await client.initialize(); return client;
}

async function main() {
  const [action, rootArg] = process.argv.slice(2);
  if (!rootArg || action !== 'catalog') throw new Error('Usage: node lib/asana_plane_export.mjs catalog PRIVATE_EXPORT_DIR');
  const root = privateRoot(rootArg); const client = await connectAsana();
  saveJson(root, 'asana-mcp-catalog.json', client.catalog);
  console.log(JSON.stringify({ readTools: client.catalog.filter(t => /get_|list_/.test(t.name)).map(t => ({ name: t.name, properties: Object.keys(t.inputSchema?.properties ?? {}) })) }));
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main().catch(error => { console.error(error.message); process.exitCode = 1; });
