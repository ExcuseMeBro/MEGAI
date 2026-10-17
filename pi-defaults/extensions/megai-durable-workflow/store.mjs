// Private, repository-scoped execution metadata. Plane remains the task authority.
import { constants, closeSync, existsSync, fstatSync, fsyncSync, lstatSync, mkdirSync,
  openSync, readFileSync, readdirSync, realpathSync, renameSync, rmdirSync, unlinkSync,
  writeFileSync } from 'node:fs';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { dirname, isAbsolute, join, resolve } from 'node:path';

const MAX_FILE = 4 * 1024 * 1024;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const HASH = /^[0-9a-f]{64}$/;
const hash = value => createHash('sha256').update(value).digest('hex');
const fingerprint = value => hash(JSON.stringify(value));
const knowledgeDigest = data => fingerprint([data.id, data.projectId, data.taskId, data.title, data.content, data.evidence, data.source]);
function requireValue(condition, message) { if (!condition) throw new Error(message); }
function text(value, name, max = 8000) {
  requireValue(typeof value === 'string' && value.trim().length > 0 && value.length <= max, `Invalid ${name}`);
  return value;
}
function uuid(value) { requireValue(typeof value === 'string' && UUID.test(value), 'Expected lowercase UUID'); return value; }
function safePath(path) {
  requireValue(isAbsolute(path), 'Expected absolute path');
  for (let p = resolve(path); ; p = dirname(p)) {
    if (existsSync(p) || (() => { try { lstatSync(p); return true; } catch (e) { if (e.code === 'ENOENT') return false; throw e; } })()) {
      const s = lstatSync(p);
      requireValue(!s.isSymbolicLink() || p === '/tmp' || p === '/var', `Symlink refused: ${p}`);
    }
    if (dirname(p) === p) break;
  }
}
function artifact(path, withBytes = false) {
  safePath(path);
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const before = fstatSync(fd);
    requireValue(before.isFile() && before.size <= MAX_FILE, 'Artifact must be a bounded regular file');
    const bytes = readFileSync(fd);
    const after = fstatSync(fd);
    const current = lstatSync(path);
    requireValue(current.dev === before.dev && current.ino === before.ino && !current.isSymbolicLink(), 'Artifact path changed while reading');
    requireValue(bytes.length <= MAX_FILE && before.size === after.size && before.mtimeMs === after.mtimeMs
      && before.ctimeMs === after.ctimeMs, 'Artifact changed while reading');
    return { path: realpathSync(path), sha256: hash(bytes), ...(withBytes ? { bytes } : {}) };
  } finally { closeSync(fd); }
}
export function readArtifact(path) { return artifact(path); }
function verifyEvidence(evidence) {
  requireValue(Array.isArray(evidence) && evidence.length > 0 && evidence.length <= 20, 'Evidence required (1–20 artifacts)');
  return evidence.map(item => {
    requireValue(item && HASH.test(item.sha256), 'Expected artifact SHA256');
    text(item.observation, 'evidence observation');
    const actual = readArtifact(item.path);
    requireValue(actual.sha256 === item.sha256, `Evidence hash mismatch: ${item.path}`);
    return { ...actual, observation: item.observation };
  });
}
function git(cwd, ...args) {
  return execFileSync('git', ['-C', cwd, ...args], { encoding: 'utf8', timeout: 10000, maxBuffer: 16 * 1024 * 1024,
    env: { ...process.env, GIT_OPTIONAL_LOCKS: '0' }, stdio: ['ignore', 'pipe', 'pipe'] });
}
function gitRepository(cwd) {
  const root = realpathSync(git(cwd, 'rev-parse', '--show-toplevel').trim());
  const common = realpathSync(resolve(root, git(root, 'rev-parse', '--git-common-dir').trim()));
  return { root, common, scope: hash(common) };
}
// A declared coordination project is not itself a Git repository, even if an
// unrelated/unborn .git exists there. Never scan siblings or initialize Git.
function repository(cwd) {
  if (existsSync(cwd)) {
    const entry = lstatSync(cwd);
    requireValue(entry.isDirectory() || entry.isSymbolicLink(), 'repositoryPath must name a directory');
  }
  const config = join(resolve(cwd), '.pi/project.json');
  safePath(config);
  if (!existsSync(config)) return gitRepository(cwd);
  const manifest = artifact(config, true);
  const data = JSON.parse(manifest.bytes.toString('utf8'));
  if (data.layout !== 'multi') return gitRepository(cwd);
  // native realpath canonicalizes case on macOS (SPM and spm are one folder).
  // Keep legacy single-Git scope serialization untouched.
  const root = realpathSync.native(cwd);
  requireValue(Array.isArray(data.repositories) && data.repositories.length > 0
    && data.repositories.length <= 32, 'Multi project requires 1–32 declared repositories');
  const seen = new Set();
  const repositories = data.repositories.map(name => {
    text(name, 'component repository path', 2048);
    requireValue(!isAbsolute(name), 'Multi component must be a relative path');
    const path = resolve(root, name);
    requireValue(path.startsWith(root + '/'), 'Multi component path escape');
    safePath(path);
    const repo = gitRepository(path);
    requireValue(realpathSync.native(repo.root) === realpathSync.native(path), `Multi component must be an independent Git root: ${name}`);
    const common = realpathSync.native(repo.common);
    requireValue(!seen.has(common), 'Duplicate multi component repository');
    seen.add(common);
    requireValue(/^[0-9a-f]{40,64}$/.test(git(repo.root, 'rev-parse', '--verify', 'HEAD').trim()), `Multi component needs a commit: ${name}`);
    return { ...repo, root: realpathSync.native(repo.root), common, scope: hash(common) };
  }).sort((a, b) => a.root.localeCompare(b.root));
  return { kind: 'multi', root, common: root, scope: hash(`multi:${root}`), manifestSha256: manifest.sha256, repositories };
}
function validSource(value) {
  if (!value || !HASH.test(value.digest)) return false;
  if (value.kind !== 'multi') return /^[0-9a-f]{40,64}$/.test(value.head);
  return HASH.test(value.manifestSha256) && (value.policySha256 === null || HASH.test(value.policySha256))
    && Array.isArray(value.repositories) && value.repositories.length > 0 && value.repositories.length <= 32
    && value.repositories.every(v => typeof v.path === 'string' && isAbsolute(v.path)
      && typeof v.repository === 'string' && isAbsolute(v.repository) && !v.kind && validSource(v))
    && value.digest === fingerprint([value.manifestSha256, value.policySha256, value.repositories]);
}
function source(repo) {
  const capture = () => {
    if (repo.kind === 'multi') {
      // Resolve the declared vector afresh: changed manifests cannot reuse stale
      // component identities. The second full capture detects cross-repo races.
      const current = repository(repo.root);
      requireValue(current.kind === 'multi' && current.scope === repo.scope, 'Multi project identity changed');
      const policy = join(repo.root, 'AGENTS.md');
      safePath(policy);
      const policySha256 = existsSync(policy) ? readArtifact(policy).sha256 : null;
      const repositories = current.repositories.map(component => ({ path: component.root,
        repository: component.common, ...source(component) }));
      const manifestSha256 = current.manifestSha256;
      return { kind: 'multi', manifestSha256, policySha256, repositories,
        digest: fingerprint([manifestSha256, policySha256, repositories]) };
    }
    const head = git(repo.root, 'rev-parse', 'HEAD').trim();
    const status = git(repo.root, 'status', '--porcelain=v1', '-z', '--untracked-files=all');
    requireValue(!/(^|\0)(UU|AA|DD|AU|UA|DU|UD) /.test(status), 'Resolve Git conflicts first');
    const names = git(repo.root, 'ls-files', '--others', '--exclude-standard', '-z').split('\0').filter(Boolean).sort();
    requireValue(names.length <= 1000, 'Too many untracked files for a checkpoint');
    let size = 0;
    const untracked = names.map(name => {
      const path = resolve(repo.root, name);
      requireValue(path.startsWith(repo.root + '/'), 'Untracked path escape');
      const artifact = readArtifact(path);
      size += lstatSync(path).size;
      requireValue(size <= 32 * MAX_FILE, 'Untracked snapshot exceeds bound');
      return [name, artifact.sha256, lstatSync(path).mode & 0o777];
    });
    return { head, digest: fingerprint([head, status, git(repo.root, 'diff', '--no-ext-diff', '--no-textconv', '--binary', 'HEAD'),
      git(repo.root, 'diff', '--cached', '--no-ext-diff', '--no-textconv', '--binary'), untracked]) };
  };
  const first = capture();
  requireValue(fingerprint(first) === fingerprint(capture()), 'Source changed during snapshot');
  return first;
}

export class DurableStore {
  constructor({ root, cwd, sessionId }) {
    safePath(root);
    this.root = resolve(root);
    this.repo = repository(cwd);
    this.sessionId = text(sessionId, 'session identity', 200);
    this.directory = join(this.root, this.repo.scope);
  }
  initialize() {
    for (const p of [this.root, this.directory]) {
      safePath(p);
      mkdirSync(p, { recursive: true, mode: 0o700 });
      const s = lstatSync(p);
      requireValue(s.isDirectory() && s.uid === process.getuid() && (s.mode & 0o077) === 0, 'Store must be private and user-owned');
    }
  }
  read(name) {
    for (const p of [this.root, this.directory]) {
      safePath(p);
      if (existsSync(p)) {
        const s = lstatSync(p);
        requireValue(s.isDirectory() && s.uid === process.getuid() && (s.mode & 0o077) === 0, 'Store must be private and user-owned');
      }
    }
    safePath(join(this.directory, name));
    if (!existsSync(join(this.directory, name))) return null;
    const path = join(this.directory, name);
    const s = lstatSync(path);
    requireValue(s.isFile() && s.uid === process.getuid() && (s.mode & 0o077) === 0, 'Record must be private and user-owned');
    const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
    try {
      requireValue(fstatSync(fd).size <= MAX_FILE, 'Oversized record');
      const bytes = readFileSync(fd, 'utf8');
      requireValue(Buffer.byteLength(bytes) <= MAX_FILE, 'Oversized record');
      const data = JSON.parse(bytes);
      requireValue(data.schema === 1 && data.scope === this.repo.scope && data.repository === this.repo.common
        && Number.isSafeInteger(data.revision) && data.revision > 0, 'Invalid record schema/identity/revision');
      uuid(data.projectId); uuid(data.taskId);
      requireValue(validSource(data.source), 'Invalid source binding');
      if (name.startsWith('w-')) {
        requireValue(name === `w-${data.taskId}.json` && data.kind === 'checkpoint', 'Invalid checkpoint identity');
        text(data.phase, 'phase', 100); text(data.summary, 'summary'); text(data.nextAction, 'next action');
        requireValue(Array.isArray(data.uncertainOperations) && data.uncertainOperations.length <= 20, 'Invalid uncertain operations');
        data.uncertainOperations.forEach(v => text(v, 'uncertain operation'));
      } else {
        requireValue(name === `k-${uuid(data.id)}.json` && data.kind === 'knowledge'
          && ['candidate', 'reviewed', 'approved', 'revoked'].includes(data.state), 'Invalid knowledge record');
        text(data.title, 'title', 300); text(data.content, 'content', 16000);
        requireValue(Array.isArray(data.evidence) && data.evidence.length > 0 && data.evidence.length <= 20, 'Invalid evidence');
        if (['reviewed', 'approved'].includes(data.state)) {
          requireValue(data.review && HASH.test(data.review.sha256) && data.review.candidateDigest === knowledgeDigest(data), 'Missing or stale review binding');
        }
        if (data.state === 'approved') requireValue(data.approval?.actor === 'user-ui', 'Missing explicit user approval');
      }
      return data;
    } finally { closeSync(fd); }
  }
  write(name, data) {
    const bytes = JSON.stringify(data, null, 2) + '\n';
    requireValue(Buffer.byteLength(bytes) <= MAX_FILE, 'Record exceeds bound');
    const temporary = join(this.directory, `.tmp-${randomUUID()}`);
    const fd = openSync(temporary, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600);
    try { writeFileSync(fd, bytes); fsyncSync(fd); } finally { closeSync(fd); }
    try {
      renameSync(temporary, join(this.directory, name));
      const dir = openSync(this.directory, constants.O_RDONLY);
      try { fsyncSync(dir); } finally { closeSync(dir); }
    } finally { if (existsSync(temporary)) unlinkSync(temporary); }
  }
  mutate(operation) {
    this.initialize();
    const lock = join(this.directory, '.lock');
    try { mkdirSync(lock, { mode: 0o700 }); } catch (e) {
      if (e.code === 'EEXIST') throw new Error('Store busy or interrupted writer; reconcile ownership before removing .lock');
      throw e;
    }
    try { return operation(); } finally { rmdirSync(lock); }
  }
  // Read-only provenance diagnostic; never initializes the metadata store.
  snapshot() { return source(this.repo); }
  base(projectId, taskId) {
    return { schema: 1, scope: this.repo.scope, repository: this.repo.common,
      projectId: uuid(projectId), taskId: uuid(taskId), source: this.snapshot(),
      sessionId: this.sessionId, updatedAt: new Date().toISOString() };
  }
  checkpoint(input) {
    uuid(input.projectId); uuid(input.taskId);
    text(input.phase, 'phase', 100); text(input.summary, 'summary'); text(input.nextAction, 'next action');
    requireValue(Number.isSafeInteger(input.expectedRevision) && input.expectedRevision >= 0, 'Expected revision required');
    requireValue(Array.isArray(input.uncertainOperations) && input.uncertainOperations.length <= 20, 'Uncertain operations required');
    input.uncertainOperations.forEach(v => text(v, 'uncertain operation'));
    return this.mutate(() => {
      const name = `w-${input.taskId}.json`;
      const prior = this.read(name);
      requireValue((prior?.revision ?? 0) === input.expectedRevision, 'Stale checkpoint revision; read/reconcile before saving');
      requireValue(!prior || prior.projectId === input.projectId, 'Plane project mismatch');
      const data = { ...this.base(input.projectId, input.taskId), kind: 'checkpoint', revision: input.expectedRevision + 1,
        phase: input.phase, summary: input.summary, nextAction: input.nextAction, uncertainOperations: input.uncertainOperations };
      this.write(name, data); return data;
    });
  }
  getCheckpoint(taskId) { return this.read(`w-${uuid(taskId)}.json`); }
  resume(taskId) {
    const checkpoint = this.getCheckpoint(taskId);
    requireValue(checkpoint, 'Checkpoint not found in this repository');
    const sourceCurrent = fingerprint(checkpoint.source) === fingerprint(source(this.repo));
    return { checkpoint, readOnly: true, sourceCurrent,
      canContinue: sourceCurrent && checkpoint.uncertainOperations.length === 0,
      instruction: 'Revalidate Plane identity, current task authority and approvals. Reconcile source drift or uncertain mutations; never replay saved actions automatically.' };
  }
  records(prefix) {
    safePath(this.directory);
    if (!existsSync(this.directory)) return [];
    const s = lstatSync(this.directory);
    requireValue(s.isDirectory() && s.uid === process.getuid() && (s.mode & 0o077) === 0, 'Store must be private and user-owned');
    const names = readdirSync(this.directory).filter(n => n.startsWith(prefix) && n.endsWith('.json')).sort();
    requireValue(names.length <= 1000, 'Record list exceeds bound');
    return names.map(name => this.read(name));
  }
  checkpoints() { return this.records('w-').map(({ taskId, projectId, revision, phase, updatedAt }) => ({ taskId, projectId, revision, phase, updatedAt })); }
  stage(input) {
    text(input.title, 'title', 300); text(input.content, 'content', 16000);
    return this.mutate(() => {
      const data = { ...this.base(input.projectId, input.taskId), kind: 'knowledge', id: randomUUID(), revision: 1,
        state: 'candidate', title: input.title, content: input.content, evidence: verifyEvidence(input.evidence) };
      this.write(`k-${data.id}.json`, data); return data;
    });
  }
  knowledge(id) { return this.read(`k-${uuid(id)}.json`); }
  validate(id) {
    const data = this.knowledge(id);
    requireValue(data, 'Knowledge not found in this repository');
    verifyEvidence(data.evidence);
    return data;
  }
  review(id, revision, report, expected = null, confirmedReportHash = null) {
    const confirmed = confirmedReportHash ?? readArtifact(report).sha256;
    requireValue(HASH.test(confirmed), 'Expected confirmed review report SHA256');
    return this.mutate(() => {
      const data = this.validate(id);
      requireValue(data.revision === revision && data.state === 'candidate', 'Candidate changed or already reviewed');
      requireValue(expected === null || fingerprint(expected) === fingerprint(data), 'Candidate changed during confirmation');
      requireValue(fingerprint(data.source) === fingerprint(source(this.repo)), 'Source changed since staging; stage fresh knowledge');
      const artifact = readArtifact(report);
      requireValue(artifact.sha256 === confirmed, 'Review report hash mismatch after confirmation');
      requireValue(lstatSync(artifact.path).size > 0, 'Review report must not be empty');
      data.review = { ...artifact, candidateDigest: knowledgeDigest(data), actor: 'user-ui', sessionId: this.sessionId, at: new Date().toISOString() };
      data.state = 'reviewed'; data.revision++;
      this.write(`k-${id}.json`, data); return data;
    });
  }
  promote(id, revision, expected = null) {
    return this.mutate(() => {
      const data = this.validate(id);
      requireValue(data.revision === revision && data.state === 'reviewed', 'Reviewed candidate required; revision changed');
      requireValue(expected === null || fingerprint(expected) === fingerprint(data), 'Candidate changed during confirmation');
      requireValue(fingerprint(data.source) === fingerprint(source(this.repo)), 'Source changed since staging');
      requireValue(readArtifact(data.review.path).sha256 === data.review.sha256, 'Review hash mismatch');
      data.state = 'approved'; data.revision++;
      data.approval = { actor: 'user-ui', sessionId: this.sessionId, at: new Date().toISOString() };
      this.write(`k-${id}.json`, data); return data;
    });
  }
  revoke(id, revision) {
    return this.mutate(() => {
      const data = this.knowledge(id);
      requireValue(data && data.revision === revision, 'Knowledge changed or not found');
      data.state = 'revoked'; data.revision++;
      this.write(`k-${id}.json`, data); return data;
    });
  }
  listKnowledge() { return this.records('k-').map(({ id, title, state, revision }) => ({ id, title, state, revision })); }
  search(query) {
    text(query, 'query', 256);
    const terms = query.toLowerCase().split(/\s+/);
    return this.records('k-').filter(v => v.state === 'approved'
      && terms.every(t => `${v.title} ${v.content}`.toLowerCase().includes(t))).slice(0, 10).map(v => {
      verifyEvidence(v.evidence);
      requireValue(readArtifact(v.review.path).sha256 === v.review.sha256, 'Review hash mismatch');
      return v;
    });
  }
}
