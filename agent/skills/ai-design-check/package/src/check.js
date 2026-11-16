import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { CLASS_FUNCTIONS, blankComments, classUnits, tokens, utility } from './classes.js';
import { children, parseAttrs, tags, visibleText } from './jsx.js';
import { LOOKS } from './looks.js';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));

/** Rule catalogue: the single source for docs, the checker and the agent skill. */
export function loadRules() {
    return JSON.parse(readFileSync(join(ROOT, 'rules.json'), 'utf8'));
}

export const CONFIG_FILE = 'ai-design-check.json';
/** Also read: the neutral dotfile and the name used by @enmera/design 0.1. */
export const CONFIG_FILES = [CONFIG_FILE, '.design-rules.json', 'enmera-design.json'];

const DEFAULT_IGNORE = ['**/node_modules/**', '**/vendor/**', '**/dist/**', '**/build/**', '**/public/build/**', '**/.git/**', '**/storage/**', '**/*.min.*', '**/Pods/**', '**/DerivedData/**', '**/.build/**', '**/.gradle/**', '**/generated/**'];

/** Names that keep their capitals inside a sentence-case label. Projects add their own in config.properNouns. */
const PROPER_NOUNS = [
    'Google', 'Apple', 'App Store', 'App Store Connect', 'Google Play', 'Search Console', 'Google Analytics', 'Meta', 'Facebook', 'Instagram', 'TikTok',
    'YouTube', 'Threads', 'Reddit', 'WhatsApp', 'Telegram', 'Slack', 'Bing', 'Cloudflare', 'Shopify', 'WordPress', 'Wix', 'Webflow', 'Ghost',
    'BigCommerce', 'GitHub', 'Claude', 'ChatGPT', 'Gemini', 'Perplexity', 'Copilot', 'OpenAI', 'Anthropic', 'Microsoft', 'Chrome', 'Safari',
    'Paddle', 'Stripe', 'PayPal', 'iyzico', 'PayTR', 'Trendyol', 'Hepsiburada', 'Amazon', 'Markdown', 'Enmera', 'Searvia', 'Enmera Commerce',
    'Türkçe', 'İngilizce', 'Almanca', 'Fransızca', 'İspanyolca', 'Portekizce', 'Japonca', 'Arapça', 'Rusça', 'Türkiye',
];

/** Raw element → the shared component that replaces it. */
const COMPONENTS = { button: 'Button', input: 'Input', select: 'Select', textarea: 'Textarea' };

/** Shared components whose look comes from props, not from className. */
const SHARED = ['Button', 'LinkButton', 'IconButton', 'Badge', 'StatusBadge', 'Input', 'Select', 'Textarea', 'Card', 'SectionCard', 'Tabs', 'TabsList', 'TabsTrigger'];

/** Utilities that change how a component looks (as opposed to where it sits). */
export const CONTAINER_VISUAL = /^(?:bg-|rounded|border(?!-[trblsexy]?-?0$)|ring|shadow|outline)/;
export const VISUAL = /^(?:bg-|text-(?!left$|right$|center$|start$|end$|justify$|wrap$|nowrap$|balance$|pretty$|ellipsis$|clip$)|font-|rounded|border|ring|shadow|p[xytrblse]?-|h-|size-|min-h-|gap-|tracking-|leading-|outline)/;

/** Turkish- and English-aware: small connectives that stay lower case inside a label. */
const SMALL = new Set(['a', 'an', 'the', 'and', 'or', 'for', 'of', 'on', 'in', 'to', 'by', 'with', 'vs', 've', 'ile', 'veya', 'ya', 'da', 'de', 'ki', 'mi', 'mı', 'mu', 'mü']);

const MARKUP = ['tsx', 'jsx', 'vue', 'svelte', 'html', 'blade.php'];
const JSX = ['tsx', 'jsx'];
/** Native app code: SwiftUI (swift) and Jetpack Compose (kt) read through each rule's check.native patterns. */
const NATIVE = ['swift', 'kt'];

export function loadConfig(cwd) {
    const file = CONFIG_FILES.map((name) => join(cwd, name)).find((path) => existsSync(path));
    const config = file ? JSON.parse(readFileSync(file, 'utf8')) : {};

    return {
        include: config.include ?? ['.'],
        ignore: [...DEFAULT_IGNORE, ...(config.ignore ?? [])],
        rules: config.rules ?? {},
        allow: config.allow ?? {},
        i18n: { files: config.i18n?.files ?? [], keysAreSource: config.i18n?.keysAreSource ?? true, framework: config.i18n?.framework ?? [] },
        labels: config.labels ?? true,
        properNouns: [...PROPER_NOUNS, ...(config.properNouns ?? [])],
        classFunctions: [...CLASS_FUNCTIONS, ...(config.classFunctions ?? [])],
        components: { ...COMPONENTS, ...(config.components ?? {}) },
        looks: Object.fromEntries(Object.entries(LOOKS).map(([kind, look]) => [kind, { ...look, component: config.looks?.[kind] ?? look.component }]).filter(([kind]) => config.looks?.[kind] !== false)),
        componentDirs: config.componentDirs ?? ['**/components/ui/**'],
        sharedComponents: config.sharedComponents ?? SHARED,
        containers: config.containers ?? ['Card', 'SectionCard', 'Tile', 'Panel', 'RowButton', 'RowLink', 'MetaRow', 'List', 'CardContent'],
    };
}

/** Two or more words that all start with a capital, apart from proper nouns and small connectives: "Yaklaşan Ödemeler". */
function titleCased(text, properNouns) {
    const words = text.replace(/[?!.:,]/g, ' ').split(/\s+/u).filter((word) => /^\p{L}/u.test(word));
    const rest = words.slice(1).filter((word) => !SMALL.has(word.toLocaleLowerCase('tr')) && !properNouns.includes(word));

    return words.length >= 2 && rest.length > 0 && rest.every((word) => /^\p{Lu}/u.test(word) && !/^\p{Lu}+$/u.test(word));
}

/** Minimal glob: ** any depth, * within a segment, ? one character. */
export function globToRegExp(glob) {
    let out = '';
    for (let i = 0; i < glob.length; i++) {
        const char = glob[i];
        if (char === '*' && glob[i + 1] === '*') {
            out += glob[i + 2] === '/' ? '(?:.*/)?' : '.*';
            i += glob[i + 2] === '/' ? 2 : 1;
        } else if (char === '*') out += '[^/]*';
        else if (char === '?') out += '[^/]';
        else out += char.replace(/[.+^${}()|[\]\\]/g, '\\$&');
    }

    return new RegExp(`^${out}$`);
}

export const matches = (globs, path) => globs.some((glob) => globToRegExp(glob).test(path) || globToRegExp(`${glob}/**`).test(path));

export function walk(cwd, start, ignore, files = []) {
    const full = join(cwd, start);
    if (!existsSync(full)) return files;
    if (statSync(full).isFile()) return [...files, start];

    for (const entry of readdirSync(full, { withFileTypes: true })) {
        const path = (start === '.' ? entry.name : `${start}/${entry.name}`).split(sep).join('/');
        if (matches(ignore, path)) continue;
        if (entry.isDirectory()) walk(cwd, path, ignore, files);
        else files.push(path);
    }

    return files;
}

export const extensionOf = (path) => (path.endsWith('.blade.php') ? 'blade.php' : path.split('.').pop());

const lineOf = (source, index) => source.slice(0, index).split('\n').length;

/** allow: { ruleId: ["glob", "glob:exact match"] } */
function allowed(config, rule, path, value) {
    return (config.allow[rule] ?? []).some((entry) => {
        const split = entry.lastIndexOf(':');
        const hasValue = split > 0 && !entry.slice(split).includes('/') && !entry.endsWith('**');
        const glob = hasValue ? entry.slice(0, split) : entry;

        return matches([glob], path) && (!hasValue || entry.slice(split + 1) === value);
    });
}

/**
 * Inline ignores, always with a reason after "--":
 *   ai-design-check-ignore-next-line rule-id[, rule-id] -- why
 *   ai-design-check-ignore-file rule-id -- why
 */
function ignores(source) {
    const lines = source.split('\n');
    const file = new Set();
    const byLine = new Map();
    lines.forEach((text, index) => {
        const match = /ai-design-check-ignore-(next-line|line|file)\s+([\w*,\s-]+?)\s+--\s*\S/.exec(text);
        if (!match) return;
        const ids = match[2].split(',').map((id) => id.trim()).filter(Boolean);
        if (match[1] === 'file') ids.forEach((id) => file.add(id));
        else if (match[1] === 'line') byLine.set(index + 1, [...(byLine.get(index + 1) ?? []), ...ids]);
        else {
            // next-line covers the whole next element: a tag spread over several lines ends at its first ">".
            for (let next = index + 1; next < Math.min(lines.length, index + 12); next++) {
                byLine.set(next + 1, [...(byLine.get(next + 1) ?? []), ...ids]);
                if (/>\s*$|\/>|>[^<]*</.test(lines[next])) break;
            }
        }
    });

    return (rule, line) => file.has(rule) || file.has('*') || (byLine.get(line) ?? []).some((id) => id === rule || id === '*');
}

const words = (text) => text.trim().split(/\s+/);

/** Short label: 2–5 words, no sentence punctuation, no placeholder sentence, no path separator. */
export function isLabel(text) {
    const count = words(text).length;

    return count >= 2 && count <= 5 && !/[.!?:,;›·(|]|\s:[a-z_]/u.test(text) && /^\p{Lu}/u.test(text);
}

/** Every word after the first (connectives aside) starts with a capital: "Takip Et", "High Impact". */
export function isTitled(text) {
    const rest = words(text).slice(1).filter((word) => /^\p{L}/u.test(word) && !SMALL.has(word.toLocaleLowerCase('tr')));

    return rest.length > 0 && rest.every((word) => /^\p{Lu}/u.test(word));
}

/** Capitals are justified: a proper noun, an acronym or a mixed-case word explains every capitalised word. */
export function justified(text, properNouns, source = '') {
    // Product and category names: a known brand anywhere ("Google Tag Manager") or an ampersand ("Health & Fitness").
    const single = new Set(properNouns.filter((name) => !name.includes(' ')));
    const brand = (word) => single.has(word.split(/['’]/u)[0]);
    if (/\s&\s/u.test(text) || words(text).some(brand) || properNouns.some((name) => name.includes(' ') && text.includes(name))) return true;

    const rest = words(text).slice(1).map((word) => word.replace(/^[("“'‘]+|[)"”'’.,:;!?]+$/gu, '').split(/['’]/u)[0]);

    return rest.every((word) => {
        if (!/^\p{Lu}/u.test(word)) return true;
        if (/[\p{Lu}\d]/u.test(word.slice(1))) return true; // AI, SERP, iOS, GA4
        if (source && new RegExp(`(^|\\s)${word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\s|$)`, 'u').test(source.split(/\s+/).slice(1).join(' '))) return true;

        return single.has(word) || properNouns.some((name) => name.includes(' ') && text.includes(name) && name.split(' ').includes(word));
    });
}

function checkI18n(config, path, source, report) {
    let dictionary;
    try {
        dictionary = JSON.parse(source);
    } catch {
        return;
    }

    for (const [key, value] of Object.entries(dictionary)) {
        if (typeof value !== 'string') continue;
        const line = lineOf(source, Math.max(0, source.indexOf(JSON.stringify(key))));

        if (config.i18n.keysAreSource && !config.i18n.framework.includes(key) && isLabel(key) && isTitled(key) && !justified(key, config.properNouns)) {
            report('sentence-case', path, line, key, `Source text in Title Case: "${key}"`);
        }
        // A translation may keep capitals that the source text also has (a proper noun translated with its official name).
        const sourceHasNames = config.i18n.keysAreSource && words(key).slice(1).some((word) => /^\p{Lu}/u.test(word));
        if (isLabel(value) && isTitled(value) && !sourceHasNames && !justified(value, config.properNouns)) {
            report('sentence-case', path, line, value, `Translation in Title Case: "${value}" (${key})`);
        }
    }
}

const LABEL_PATTERN = /\b(?:label|title|placeholder|aria-label|tooltip|description|heading)=\{?\s*(["'])([^"'{}\n]{3,60})\1|\bt\(\s*(["'])([^"'\n]{3,60})\3/g;

function checkLabels(config, path, source, report) {
    for (const match of source.matchAll(LABEL_PATTERN)) {
        const text = match[2] ?? match[4];
        if (isLabel(text) && isTitled(text) && !justified(text, config.properNouns)) {
            report('sentence-case', path, lineOf(source, match.index), text, `Label in Title Case: "${text}"`);
        }
    }
}

const NAME_ATTRS = ['aria-label', 'aria-labelledby', 'title', 'label', 'tooltip'];

function checkIconButtons(path, source, report) {
    for (const tag of tags(source, ['button', 'Button', 'IconButton', 'a', 'Link', 'LinkButton'])) {
        const attrs = parseAttrs(tag.attrs);
        // A spread may carry the label; a react-aria slot ("previous", "next") is labelled by its parent.
        if (NAME_ATTRS.some((name) => attrs[name] !== undefined) || attrs.slot !== undefined || /\{\s*\.\.\./.test(tag.attrs)) continue;
        const inner = children(source, tag);
        if (inner === null || inner === '') continue;
        const hasIcon = /<(?:svg|[A-Z]\w*Icon|Icon|[A-Z]\w*Logo)\b/.test(inner);
        if (hasIcon && visibleText(inner) === '') report('icon-button-name', path, lineOf(source, tag.start), tag.name, `Icon-only <${tag.name}> has no aria-label`);
    }
}

function checkSharedComponents(config, path, source, report) {
    if (matches(config.componentDirs, path)) return;
    for (const tag of tags(source, Object.keys(config.components))) {
        const type = parseAttrs(tag.attrs).type;
        if (tag.name === 'input' && ['hidden', 'file'].includes(type)) continue;
        report('use-shared-components', path, lineOf(source, tag.start), tag.name, `Raw <${tag.name}>: use <${config.components[tag.name]}>`);
    }
}

function checkLooks(config, path, source, report) {
    if (matches(config.componentDirs, path)) return;
    const looks = Object.values(config.looks);
    for (const tag of tags(source, looks.flatMap((look) => look.tags))) {
        const raw = parseAttrs(tag.attrs).className ?? parseAttrs(tag.attrs).class;
        if (raw === undefined) continue;
        const text = typeof raw === 'string' ? raw : classUnits(`className={${raw.code}}`, config.classFunctions).map((unit) => unit.text).join(' ');
        const look = looks.find((item) => item.tags.includes(tag.name) && item.test(text));
        if (look) report('use-shared-looks', path, lineOf(source, tag.start), `${look.name}:${tag.name}`, `Hand-written ${look.name} <${tag.name}>: use ${look.component}`);
    }
}

function checkOverrides(config, path, source, report) {
    // Inside the component folder components compose each other (a calendar's day Button, an input inside a group).
    if (matches(config.componentDirs, path)) return;
    for (const tag of tags(source, config.sharedComponents)) {
        const attrs = parseAttrs(tag.attrs);
        const raw = attrs.className;
        if (raw === undefined) continue;
        const text = typeof raw === 'string' ? raw : classUnits(`className={${raw.code}}`, config.classFunctions).map((unit) => unit.text).join(' ');
        // Containers (boxes, rows, lists) are laid out by their caller: padding, gap, height and text belong there.
        const look = config.containers.includes(tag.name) ? CONTAINER_VISUAL : VISUAL;
        const visual = tokens(text).filter((token) => look.test(utility(token)));
        if (visual.length > 0) report('no-style-overrides', path, lineOf(source, tag.start), visual.join(' '), `<${tag.name}> styled from outside: ${visual.join(' ')}`);
    }
}

/** Layout utilities do not make two copies look different; drop them before comparing class lists. */
export const LAYOUT = /^(?:w-|min-w-|max-w-|m[xytrblse]?-|-m|flex-1$|flex-none$|grow|shrink|self-|justify-self-|place-self-|order-|col-|row-|hidden$|block$|inline|absolute$|relative$|fixed$|sticky$|top-|right-|bottom-|left-|inset-|start-|end-|z-|transition|duration-|ease-|animate-|cursor-|select-|pointer-events-|truncate$|sr-only$)/;

const CLASS_TOKEN = /^!?-?[a-z0-9@[][\w:\-/.[\]%#()&,!*>+~=']*$/;

export const signature = (text) => [...new Set(tokens(text).filter((token) => CLASS_TOKEN.test(token) && /[-:[]|^(?:flex|grid|block|hidden|inline|border|rounded|shadow|truncate|uppercase|italic|underline|relative|absolute|sticky|fixed)$/.test(token) && !LAYOUT.test(utility(token))))].sort().join(' ');

/**
 * Runs every enabled check. Returns findings ({rule, severity, path, line, value, message}) sorted by path and line.
 * config.rules: { ruleId: "off" | "info" | "warn" | "error" } overrides a rule's severity.
 */
export function check(cwd, overrides = {}) {
    const catalogue = loadRules();
    const config = { ...loadConfig(cwd), ...overrides };
    const severityOf = (rule) => config.rules[rule.id] ?? rule.severity;
    const on = (id) => severityOf(catalogue.rules.find((rule) => rule.id === id)) !== 'off';
    const findings = [];
    let skip = () => false;
    const report = (id, path, line, value, message) => {
        const rule = catalogue.rules.find((item) => item.id === id);
        const severity = severityOf(rule);
        if (severity === 'off' || allowed(config, id, path, value) || skip(id, line)) return null;
        const finding = { rule: id, severity, path, line, value, message: message ?? rule.title.en };
        findings.push(finding);

        return finding;
    };

    const files = [...new Set(config.include.flatMap((start) => walk(cwd, start, config.ignore)))];
    const active = catalogue.rules.filter((rule) => rule.check && severityOf(rule) !== 'off');
    const classRules = active.filter((rule) => rule.check.type === 'class');
    const regexRules = active.filter((rule) => rule.check.type === 'regex');
    const repeated = active.find((rule) => rule.check.type === 'repeated-markup');
    const groups = new Map();

    for (const path of files) {
        const extension = extensionOf(path);
        const isI18n = config.i18n.files.length > 0 && matches(config.i18n.files, path);
        const markup = MARKUP.includes(extension);
        const regexFor = regexRules.filter((rule) => rule.check.files.includes(extension) && !(isI18n && !['no-buzzwords', 'error-copy', 'ellipsis-character'].includes(rule.id)));
        const nativeFor = NATIVE.includes(extension) ? active.filter((rule) => rule.check.native?.[extension]) : [];
        if (!markup && extension !== 'css' && regexFor.length === 0 && nativeFor.length === 0 && !isI18n) continue;

        const source = readFileSync(join(cwd, path), 'utf8');
        skip = ignores(source);

        if (markup) {
            for (const unit of classUnits(source, config.classFunctions)) {
                const line = lineOf(source, unit.index);
                for (const rule of classRules) {
                    if (rule.check.unless && new RegExp(rule.check.unless, 'u').test(unit.text)) continue;
                    if (rule.check.exceptElements && unit.element && new RegExp(rule.check.exceptElements).test(unit.element)) continue;
                    if (rule.check.onlyElements && !(unit.element && new RegExp(rule.check.onlyElements).test(unit.element))) continue;
                    // A wrapper just above may carry the style (focus-within: ring on the box around an input).
                    if (rule.check.unlessBefore && new RegExp(rule.check.unlessBefore, 'u').test(source.slice(Math.max(0, unit.index - 1500), unit.index))) continue;
                    for (const match of unit.text.matchAll(new RegExp(rule.check.pattern, 'gu'))) {
                        // Scale rules: a value on the scale (mt-[24px] on a 4 px grid) and hairlines (1–2 px) pass.
                        if (rule.check.notMultipleOf && (Number(match[1]) <= 2 || Number(match[1]) % rule.check.notMultipleOf === 0)) continue;
                        report(rule.id, path, line, match[0].trim(), `${rule.title.en}: ${match[0].trim()}`);
                    }
                }
                if (repeated) {
                    const key = signature(unit.text);
                    if (key.split(' ').length >= repeated.check.minTokens) groups.set(key, [...(groups.get(key) ?? []), { path, line, skip: skip('repeated-markup', line) }]);
                }
            }
        }
        // Class rules that also need the element's text (an all-caps label written by hand).
        if (markup) {
            for (const rule of classRules.filter((item) => item.check.markup)) {
                for (const match of source.matchAll(new RegExp(rule.check.markup, 'gu'))) report(rule.id, path, lineOf(source, match.index), match[1] ?? match[0], `${rule.title.en}: ${(match[1] ?? match[0]).trim()}`);
            }
        }
        if (extension === 'css') {
            for (const rule of classRules.filter((item) => item.check.css)) {
                for (const match of source.matchAll(new RegExp(rule.check.css, 'gu'))) report(rule.id, path, lineOf(source, match.index), match[0], `${rule.title.en}: ${match[0]}`);
            }
        }
        // Code rules read code and copy, not comments (inline ignores were read above, before blanking).
        const code = ['tsx', 'jsx', 'ts', 'js', 'vue', 'svelte', 'css', ...NATIVE].includes(extension) ? blankComments(source, extension !== 'css') : source;
        // Native rules: one pattern per platform; group 1 is the number when the rule checks a scale or a limit.
        for (const rule of nativeFor) {
            const native = typeof rule.check.native[extension] === 'string' ? { pattern: rule.check.native[extension] } : rule.check.native[extension];
            for (const match of code.matchAll(new RegExp(native.pattern, 'gmu'))) {
                const number = Number(match[1]);
                if (native.notMultipleOf && (number <= 2 || number % native.notMultipleOf === 0)) continue;
                if (native.min !== undefined && !(number >= native.min)) continue;
                if (native.titleCase && !titleCased(match[1], config.properNouns)) continue;
                if (native.unlessBefore && new RegExp(native.unlessBefore, 'u').test(code.slice(Math.max(0, match.index - 300), match.index))) continue;
                report(rule.id, path, lineOf(source, match.index), match[0].trim(), `${rule.title.en}: ${match[0].trim()}`);
            }
        }
        for (const rule of regexFor) {
            const pattern = new RegExp(rule.check.pattern, `g${rule.check.flags ?? ''}`.replace(/(.)(?=.*\1)/g, ''));
            const seen = new Set();
            for (const match of code.matchAll(pattern)) {
                const line = lineOf(source, match.index);
                if (seen.has(line)) continue; // one finding per line and rule
                seen.add(line);
                report(rule.id, path, line, match[0], `${rule.title.en}: ${match[0]}`);
            }
        }
        if (on('sentence-case') && isI18n) checkI18n(config, path, source, report);
        if (on('sentence-case') && config.labels && ['tsx', 'jsx', 'vue', 'svelte'].includes(extension)) checkLabels(config, path, source, report);
        if (JSX.includes(extension)) {
            if (on('icon-button-name')) checkIconButtons(path, source, report);
            if (on('use-shared-components')) checkSharedComponents(config, path, source, report);
            if (on('no-style-overrides')) checkOverrides(config, path, source, report);
            if (on('use-shared-looks')) checkLooks(config, path, source, report);
        }
    }

    if (repeated) {
        for (const [key, places] of groups) {
            const live = places.filter((place) => !place.skip);
            if (live.length < repeated.check.minCount) continue;
            const first = live[0];
            const where = [...new Set(live.map((place) => place.path))];
            skip = () => false;
            const finding = report('repeated-markup', first.path, first.line, key, `Same classes ${live.length}× in ${where.length} file(s), extract a component: ${key}`);
            if (finding) finding.places = live.map(({ path, line }) => ({ path, line }));
        }
    }

    return findings.sort((a, b) => a.path.localeCompare(b.path) || a.line - b.line);
}

/** Baseline: per file and rule, how many findings already existed. Only findings beyond those counts are reported. */
export function applyBaseline(findings, baseline) {
    const counts = new Map();
    for (const item of findings) counts.set(`${item.path}\u0000${item.rule}`, (counts.get(`${item.path}\u0000${item.rule}`) ?? 0) + 1);

    return findings.filter((item) => counts.get(`${item.path}\u0000${item.rule}`) > (baseline[`${item.path}\u0000${item.rule}`] ?? 0));
}

export function toBaseline(findings) {
    const out = {};
    for (const item of findings) out[`${item.path}\u0000${item.rule}`] = (out[`${item.path}\u0000${item.rule}`] ?? 0) + 1;

    return out;
}
