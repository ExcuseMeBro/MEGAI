#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { connectAsana, privateRoot, saveJson, hash, paginate } from './asana_plane_export.mjs';
import { downloadAttachment } from './asana_plane_files.mjs';

export const TASK_FIELDS = 'gid,name,notes,html_notes,completed,completed_at,created_at,modified_at,assignee.gid,assignee.name,assignee.email,assignee_status,assignee_section,parent.gid,parent.name,memberships.project.gid,memberships.project.name,memberships.section.gid,memberships.section.name,due_on,due_at,start_on,start_at,resource_subtype,approval_status,custom_fields,tags.gid,tags.name,dependencies.gid,dependents.gid,followers.gid,followers.name,permalink_url,num_subtasks,num_likes,num_hearts,actual_time_minutes,hearted,hearts,liked,likes,projects.gid,projects.name,workspace.gid,resource_type,custom_type,custom_type_status';
const PROJECT_FIELDS = 'gid,name,notes,html_notes,archived,created_at,modified_at,start_on,due_on,completed,completed_at,owner.gid,owner.name,owner.email,members.gid,members.name,members.email,team.gid,team.name,color,icon,permalink_url,privacy_setting,default_view,custom_fields,custom_field_settings,project_brief.gid,current_status,current_status_update';
const STORY_FIELDS = 'gid,created_at,created_by.gid,created_by.name,created_by.email,resource_subtype,type,text,html_text,is_edited,target.gid';
const ATTACHMENT_FIELDS = 'gid,name,created_at,resource_subtype,download_url,permanent_url,view_url,host,size,parent.gid';
const validId = id => typeof id === 'string' && /^\d+$/.test(id);

export function mergeTask(tasks, task, gaps) {
  if (!validId(task.gid)) throw new Error('Invalid source task identity');
  const previous = tasks.get(task.gid);
  if (previous && previous.modified_at !== task.modified_at) gaps.push({ kind: 'source_changed_during_export', task_gid: task.gid });
  // Keep fields from both response shapes, not whichever has more keys.
  const merged = { ...previous, ...task };
  for (const key of Object.keys(task)) {
    if (previous?.[key] && task[key] && !Array.isArray(task[key]) && typeof task[key] === 'object') merged[key] = { ...previous[key], ...task[key] };
  }
  tasks.set(task.gid, merged);
}

export async function exportSnapshot(client, root, { sourceWorkspace, concurrency = 3, downloader = downloadAttachment } = {}) {
  if (!validId(sourceWorkspace)) throw new Error('An explicit source workspace ID is required');
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 4) throw new Error('Invalid export concurrency');
  const lock = path.join(root, 'export.lock');
  if (fs.existsSync(lock)) {
    const stat = fs.lstatSync(lock);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.uid !== process.getuid() || (stat.mode & 0o077)) throw new Error('Unsafe existing export lock');
    const oldLock = JSON.parse(fs.readFileSync(lock, 'utf8'));
    if (oldLock.host !== os.hostname() || !Number.isInteger(oldLock.pid) || oldLock.pid <= 0) throw new Error('Existing lock requires explicit ownership reconciliation');
    try { process.kill(oldLock.pid, 0); throw new Error('Export is already running'); }
    catch (error) { if (error.code !== 'ESRCH') throw error; }
    fs.renameSync(lock, lock + '.stale-' + crypto.randomUUID());
  }
  const lockId = crypto.randomUUID();
  const lockFd = fs.openSync(lock, 'wx', 0o600); fs.writeFileSync(lockFd, JSON.stringify({ pid: process.pid, host: os.hostname(), id: lockId, started_at: new Date().toISOString() })); fs.fsyncSync(lockFd);
  const manifest = { schema_version: 2, started_at: new Date().toISOString(), status: 'running', source_workspace_gid: null, projects: [], tasks: [], attachments: [], gaps: [], coverage_gaps: [], export_complete: false, full_account_export_complete: false };
  const oldManifestPath = path.join(root, 'source/manifest.json');
  if (fs.existsSync(oldManifestPath)) {
    const original = JSON.parse(fs.readFileSync(oldManifestPath, 'utf8'));
    saveJson(root, `source/revisions/manifests/${hash(JSON.stringify(original))}.json`, original);
  }
  const changedTasks = new Set();
  const previousTask = gid => {
    const file = path.join(root, `source/tasks/${gid}.json`);
    return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : null;
  };
  const cacheRoot = 'source/requests';
  const cached = async (name, args = {}, fresh = false) => {
    const key = hash(JSON.stringify({ name, args })); const file = `${cacheRoot}/${key}.json`; const full = path.join(root, file);
    if (!fresh && fs.existsSync(full)) {
      if (fs.lstatSync(full).isSymbolicLink()) throw new Error('Symlink cache file');
      const old = JSON.parse(fs.readFileSync(full, 'utf8'));
      if (old.key !== key || old.name !== name) throw new Error('Cache identity mismatch');
      return old.result;
    }
    let result;
    try { result = await client.call(name, args); }
    catch (error) {
      if (error.privateResult) saveJson(root, `source/failures/${key}.json`, { name, args, result: error.privateResult });
      throw error;
    }
    if (fs.existsSync(full)) {
      const previous = JSON.parse(fs.readFileSync(full, 'utf8'));
      if (JSON.stringify(previous.result) !== JSON.stringify(result)) saveJson(root, `source/revisions/requests/${key}-${hash(JSON.stringify(previous.result))}.json`, previous);
    }
    saveJson(root, file, { key, name, args, fetched_at: new Date().toISOString(), result }); return result;
  };
  const all = (name, args, fresh = false) => paginate(page => cached(name, page, fresh), args);
  const checkpoint = () => saveJson(root, 'source/manifest.json', manifest);
  try {
    const me = await cached('get_me', {}, true);
    if (!Array.isArray(me.data?.workspaces) || me.data.workspaces.length !== 1) throw new Error('Source workspace ambiguous or missing');
    manifest.source_workspace_gid = me.data.workspaces[0].gid;
    if (manifest.source_workspace_gid !== sourceWorkspace) throw new Error('Connected Asana workspace differs from approved source');
    saveJson(root, 'source/user.json', me);
    const projects = [...await all('get_projects', { archived: false, opt_fields: PROJECT_FIELDS }, true), ...await all('get_projects', { archived: true, opt_fields: PROJECT_FIELDS }, true)];
    if (new Set(projects.map(p => p.gid)).size !== projects.length) throw new Error('Duplicate source project inventory');
    saveJson(root, 'source/projects.json', projects);
    const tasks = new Map();
    for (const project of projects) {
      if (!validId(project.gid)) throw new Error('Invalid source project identity');
      const defaultDetail = await cached('get_project', { project_id: project.gid, include_sections: true }, true);
      const detail = { data: { ...defaultDetail.data, ...project, sections: defaultDetail.data?.sections, task_counts: defaultDetail.data?.task_counts } };
      if (detail.data?.sections === null || !Array.isArray(detail.data?.sections)) throw new Error('Project section export incomplete');
      const projectTasks = await all('get_tasks', { project: project.gid, completed_since: '1970-01-01T00:00:00.000Z', opt_fields: TASK_FIELDS }, true);
      for (const task of projectTasks) mergeTask(tasks, task, manifest.gaps);
      const expected = detail.data.task_counts?.num_tasks;
      if (expected == null || expected !== projectTasks.length) manifest.gaps.push({ kind: 'project_task_count_mismatch', project_gid: project.gid, expected, observed: projectTasks.length });
      const projectPath = path.join(root, `source/projects/${project.gid}.json`);
      if (fs.existsSync(projectPath)) {
        const original = JSON.parse(fs.readFileSync(projectPath, 'utf8'));
        saveJson(root, `source/revisions/projects/${project.gid}-${hash(JSON.stringify(original))}.json`, original);
      }
      saveJson(root, `source/projects/${project.gid}.json`, { ...detail.data, task_gids: projectTasks.map(t => t.gid) });
      manifest.projects.push({ gid: project.gid, archived: project.archived, task_memberships: projectTasks.length });
      checkpoint();
    }
    const myTasks = await all('get_my_tasks', { completed_since: '1970-01-01T00:00:00.000Z', opt_fields: TASK_FIELDS }, true);
    saveJson(root, 'source/my-tasks.json', myTasks);
    for (const task of myTasks) mergeTask(tasks, task, manifest.gaps);
    if (client.catalog?.some(tool => ['get_users', 'asana_get_users'].includes(tool.name))) {
      const users = await all('get_users', { opt_fields: 'gid,name,email' }, true);
      saveJson(root, 'source/users.json', users);
      for (const user of users) {
        try {
          const assigned = await all('get_tasks', { assignee: user.gid, completed_since: '1970-01-01T00:00:00.000Z', opt_fields: TASK_FIELDS }, true);
          for (const task of assigned) mergeTask(tasks, task, manifest.gaps);
        } catch { manifest.coverage_gaps.push({ kind: 'assigned_user_tasks_not_enumerable', user_gid: user.gid }); }
      }
    }
    manifest.coverage_gaps.push({ kind: 'unassigned_projectless_tasks_not_enumerable_with_available_tools' }, { kind: 'historical_project_status_stream_not_exposed_by_available_tools' });
    const pending = [...tasks.keys()]; const expanded = new Set();
    for (let index = 0; index < pending.length; index++) {
      const gid = pending[index]; const task = tasks.get(gid);
      if (expanded.has(gid)) continue; expanded.add(gid);
      if (task.num_subtasks === 0) continue;
      const detail = await cached('get_task', { task_id: gid, include_comments: false, include_subtasks: true, opt_fields: TASK_FIELDS }, true);
      if (detail.data?.gid !== gid) throw new Error('Task hydration identity mismatch');
      mergeTask(tasks, detail.data, manifest.gaps);
      const subtasks = detail.data?.subtasks;
      const expectedSubtasks = detail.data?.num_subtasks ?? task.num_subtasks;
      if (!Array.isArray(subtasks) || expectedSubtasks == null || subtasks.length !== expectedSubtasks) {
        manifest.gaps.push({ kind: 'subtasks_incomplete', task_gid: gid, expected: detail.data?.num_subtasks, observed: subtasks?.length ?? null });
      }
      for (const subtask of subtasks ?? []) {
        if (!validId(subtask.gid)) throw new Error('Invalid subtask identity');
        if (!tasks.has(subtask.gid)) {
          const full = await cached('get_task', { task_id: subtask.gid, include_comments: false, include_subtasks: true, opt_fields: TASK_FIELDS }, true);
          if (full.data?.gid !== subtask.gid) throw new Error('Subtask identity mismatch');
          mergeTask(tasks, full.data, manifest.gaps); pending.push(subtask.gid);
        }
      }
    }
    for (const [gid, task] of tasks) {
      const old = previousTask(gid);
      if (!old || old.modified_at == null || task.modified_at == null || old.modified_at !== task.modified_at) changedTasks.add(gid);
      if (old) saveJson(root, `source/revisions/tasks/${gid}-${hash(JSON.stringify(old))}.json`, old);
      saveJson(root, `source/tasks/${gid}.json`, task);
    }
    manifest.tasks = [...tasks.keys()]; checkpoint();
    console.log(JSON.stringify({ stage: 'inventory', projects: projects.length, unique_tasks: tasks.size, gaps: manifest.gaps.length }));
    const units = [...projects.map(p => ({ kind: 'project', gid: p.gid })), ...[...tasks.keys()].map(gid => ({ kind: 'task', gid }))];
    let next = 0; let completed = 0;
    async function worker() {
      while (next < units.length) {
        const unit = units[next++];
        try {
          if (unit.kind === 'task') {
            const stories = await all('get_task_stories', { task_id: unit.gid, opt_fields: STORY_FIELDS }, changedTasks.has(unit.gid));
            saveJson(root, `source/stories/${unit.gid}.json`, stories);
          }
          // Reuse only unchanged task indexes; a missing/expired file triggers a fresh index below.
          const attachmentArgs = { parent: unit.gid, opt_fields: ATTACHMENT_FIELDS };
          let attachments = await all('get_attachments', attachmentArgs, unit.kind === 'project' || changedTasks.has(unit.gid));
          if (attachments.some(a => !fs.existsSync(path.join(root, `source/file-receipts/${a.gid}.json`)))) attachments = await all('get_attachments', attachmentArgs, true);
          saveJson(root, `source/attachments/${unit.gid}.json`, attachments);
          for (const attachment of attachments) {
            if (!validId(attachment.gid)) throw new Error('Invalid attachment identity');
            const relative = `source/files/${attachment.gid}.bin`; const file = path.join(root, relative); const receiptFile = path.join(root, `source/file-receipts/${attachment.gid}.json`);
            let receipt;
            try {
              if (fs.existsSync(receiptFile) && fs.existsSync(file)) {
                if (fs.lstatSync(receiptFile).isSymbolicLink() || fs.lstatSync(file).isSymbolicLink()) throw new Error('Symlink attachment cache');
                receipt = JSON.parse(fs.readFileSync(receiptFile, 'utf8'));
                const bytes = fs.readFileSync(file);
                if (receipt.sha256 !== hash(bytes) || receipt.bytes !== bytes.length || receipt.gid !== attachment.gid) {
                  const quarantine = '.corrupt-' + crypto.randomUUID();
                  fs.renameSync(file, file + quarantine); fs.renameSync(receiptFile, receiptFile + quarantine);
                  const fresh = (await all('get_attachments', attachmentArgs, true)).find(a => a.gid === attachment.gid);
                  if (!fresh?.download_url) throw new Error('No downloadable URL to repair cached attachment');
                  const downloaded = await downloader(fresh.download_url, file);
                  receipt = { gid: attachment.gid, parent_gid: unit.gid, name: attachment.name, path: relative, ...downloaded };
                  saveJson(root, `source/file-receipts/${attachment.gid}.json`, receipt);
                }
              } else {
                if (!attachment.download_url) throw new Error('No downloadable source attachment URL');
                const downloaded = await downloader(attachment.download_url, file);
                receipt = { gid: attachment.gid, parent_gid: unit.gid, name: attachment.name, path: relative, ...downloaded };
                saveJson(root, `source/file-receipts/${attachment.gid}.json`, receipt);
              }
              manifest.attachments.push({ gid: attachment.gid, parent_gid: unit.gid, bytes: receipt.bytes, sha256: receipt.sha256 });
            } catch (error) {
              manifest.gaps.push({ kind: 'attachment_unavailable', parent_gid: unit.gid, attachment_gid: attachment.gid, reason: error.message });
            }
          }
        } catch (error) { manifest.gaps.push({ kind: 'record_export_failed', resource: unit.kind, gid: unit.gid, reason: error.message }); }
        completed++; checkpoint();
        if (completed % 50 === 0) console.log(JSON.stringify({ stage: 'details', completed, total: units.length, files: manifest.attachments.length, gaps: manifest.gaps.length }));
      }
    }
    await Promise.all(Array.from({ length: concurrency }, worker));
    // Project briefs and historical project status streams lack dedicated read tools.
    for (const project of projects) if (project.project_brief?.gid) manifest.gaps.push({ kind: 'project_brief_content_not_exposed', project_gid: project.gid, brief_gid: project.project_brief.gid });
    // Fresh readback proves that cached histories correspond to the current task versions.
    for (const project of projects) {
      const current = await all('get_tasks', { project: project.gid, completed_since: '1970-01-01T00:00:00.000Z', opt_fields: 'gid,modified_at' }, true);
      const expected = JSON.parse(fs.readFileSync(path.join(root, `source/projects/${project.gid}.json`), 'utf8')).task_gids;
      if (JSON.stringify(current.map(t => t.gid).sort()) !== JSON.stringify([...expected].sort())) manifest.gaps.push({ kind: 'project_membership_drift', project_gid: project.gid });
      for (const task of current) if (tasks.get(task.gid)?.modified_at !== task.modified_at) manifest.gaps.push({ kind: 'source_changed_during_export', task_gid: task.gid });
    }
    const finalProjects = [...await all('get_projects', { archived: false, opt_fields: 'gid,archived' }, true), ...await all('get_projects', { archived: true, opt_fields: 'gid,archived' }, true)];
    if (JSON.stringify(finalProjects.map(p => `${p.gid}:${p.archived}`).sort()) !== JSON.stringify(projects.map(p => `${p.gid}:${p.archived}`).sort())) manifest.gaps.push({ kind: 'project_inventory_drift' });
    manifest.completed_at = new Date().toISOString();
    manifest.scope = 'Enumerated accessible projects, their tasks/subtasks, and discoverable assigned tasks. See coverage_gaps for categories not enumerable through this connection.';
    manifest.status = manifest.gaps.length ? 'incomplete' : 'scoped-exported';
    manifest.export_complete = manifest.gaps.length === 0;
    manifest.full_account_export_complete = manifest.export_complete && manifest.coverage_gaps.length === 0;
    manifest.task_content_hashes = Object.fromEntries([...tasks].map(([gid, task]) => [gid, hash(JSON.stringify(task))]));
    checkpoint(); return manifest;
  } catch (error) {
    manifest.status = 'failed'; manifest.gaps.push({ kind: 'fatal', reason: error.message }); checkpoint(); throw error;
  } finally {
    fs.closeSync(lockFd);
    if (fs.existsSync(lock) && JSON.parse(fs.readFileSync(lock, 'utf8')).id === lockId) fs.unlinkSync(lock);
  }
}

async function main() {
  if (!process.argv[2] || !process.argv[3]) throw new Error('Usage: node lib/asana_plane_snapshot.mjs PRIVATE_EXPORT_DIR SOURCE_WORKSPACE_GID');
  const root = privateRoot(process.argv[2]);
  const client = await connectAsana();
  const manifest = await exportSnapshot(client, root, { sourceWorkspace: process.argv[3] });
  console.log(JSON.stringify({ status: manifest.status, projects: manifest.projects.length, tasks: manifest.tasks.length, files: manifest.attachments.length, gaps: manifest.gaps.length }));
  if (!manifest.export_complete) process.exitCode = 2;
}
if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) main().catch(error => { console.error(error.message); process.exitCode = 1; });
