// Compact skill catalog for Pi's system prompt. Pure functions, no I/O.
//
// Pi lists every skill as <skill><name/><description/><location/></skill> on every
// model request. With ~90 skills that is ~56k chars (~14k tokens) per turn, while
// sessions load only a handful. Frequently used skills keep their full entry; the
// rest become one short "name: trigger" line under a shared base directory. Every
// skill stays discoverable and loadable by path; nothing on disk changes.

export const SECTION = 'skill_catalog';

const BOILERPLATE = [
  /^this skill should be used when (?:the user )?(?:asks? (?:about|for|to)?|needs? to|needs|wants? to|wants|designs?|names?|is|has)?\s*/i,
  /^use (?:this skill )?(?:when|whenever|for|to)\s+/i,
  /^(?:mandatory prerequisite|important)[^.]*?[.:-]\s*/i,
];

/** Short routing trigger: drop boilerplate openers, keep the first ~limit chars. */
export function trigger(description, limit = 140) {
  let d = String(description ?? '').replace(/\s+/g, ' ').trim();
  for (const re of BOILERPLATE) d = d.replace(re, '');
  d = d.replace(/^["“]/, '"');
  if (d.length <= limit) return d;
  const cut = d.slice(0, limit);
  const at = cut.lastIndexOf(' ');
  return (at > limit * 0.6 ? cut.slice(0, at) : cut).replace(/[,;:—–-]+$/, '') + '…';
}

function dirOf(filePath) {
  const parts = String(filePath).split('/');
  return parts.length >= 3 ? parts.slice(0, -2).join('/') : '';
}

/**
 * @param {{name:string, description:string, filePath:string, disableModelInvocation?:boolean}[]} skills
 * @param {{ full?: string[], limit?: number, minSkills?: number }} config
 * @returns {{ compact: Set<string>, section: string } | null} null = leave the prompt alone
 */
export function buildCatalog(skills, config = {}) {
  const full = new Set(config.full ?? []);
  const visible = (skills ?? []).filter((s) => s && !s.disableModelInvocation && s.name && s.filePath);
  const rest = visible.filter((s) => !full.has(s.name));
  if (rest.length < (config.minSkills ?? 8)) return null;

  // Group by the directory that holds <name>/SKILL.md so paths are written once.
  const groups = new Map();
  for (const s of rest) {
    const base = dirOf(s.filePath);
    const conventional = s.filePath === `${base}/${s.name}/SKILL.md`;
    const key = conventional ? base : '';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(s);
  }

  const lines = [
    'More skills (same rules as available_skills: read the SKILL.md before acting when the task matches; one line each = name: trigger).',
  ];
  for (const [base, list] of groups) {
    lines.push(base ? `Path: ${base}/<name>/SKILL.md` : 'Path: as given after the name');
    for (const s of list.sort((a, b) => a.name.localeCompare(b.name))) {
      lines.push(base ? `- ${s.name}: ${trigger(s.description, config.limit)}` : `- ${s.name} (${s.filePath}): ${trigger(s.description, config.limit)}`);
    }
  }
  return { compact: new Set(rest.map((s) => s.name)), section: lines.join('\n') };
}
