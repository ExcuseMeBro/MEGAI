#!/usr/bin/env node
import { existsSync, mkdirSync, readFileSync, writeFileSync, writeSync } from 'node:fs';
import { join, relative, resolve, sep } from 'node:path';
import { CONFIG_FILE, applyBaseline, check, loadRules, toBaseline } from '../src/check.js';
import { inventory } from '../src/inventory.js';

const BASELINE = '.ai-design-check-baseline.json';

const HELP = `ai-design-check — design rules and a checker for AI-built product interfaces

Usage
  npx @enmera/ai-design-check [path …]           Check the project
  npx @enmera/ai-design-check inventory [path …] Count how many ways buttons, inputs, headings, badges and cards are written
  npx @enmera/ai-design-check rules [--tr]       List the rules
  npx @enmera/ai-design-check init               Write ${CONFIG_FILE} with the defaults
  npx @enmera/ai-design-check hook               For agent hooks: check the file named in the hook JSON on stdin
  npx @enmera/ai-design-check story <before> <after> [--out story.mp4] [--still frame.png] [--title name] [--music track.mp3]
                                                 Square before/after video with every finding marked (files or URLs;
                                                 needs Chrome and ffmpeg, nothing else)
  npx @enmera/ai-design-check narrow <file|url> [--width 320]
                                                 Render at phone width and report sideways scrolling, cut-off text,
                                                 text shrunk to fit and content hidden on phones (needs Chrome)
  npx @enmera/ai-design-check system [--character calm] [--brand "#1E5A63"] [--kind dashboard] [--out design-system]
                                                 Generate a design system: fonts, type scale, light and dark colors that
                                                 pass contrast, radius and spacing, as CSS, Tailwind, JSON, SwiftUI,
                                                 Compose and a preview page (--ui/--display pick fonts, --source any)
  npx @enmera/ai-design-check fonts [--character calm]
                                                 The characters and the font library behind system

Options
  --format text|json|github   Output (github: annotations on pull requests)
  --json                      Same as --format json
  --strict                    Exit 1 on warnings too (default: errors only)
  --quiet                     Only the summary line
  --write-baseline            Record current findings in ${BASELINE}; later runs report only new ones
  --no-baseline               Ignore the baseline file
  --tr                        Turkish rule texts

Inline ignore (a reason is required):
  // ai-design-check-ignore-next-line rule-id -- why
  // ai-design-check-ignore-file rule-id -- why

Rules and reasons: https://github.com/enmerasoftware/ai-design-check/blob/main/RULES.md`;

const args = process.argv.slice(2);
const flags = new Set(args.filter((arg) => arg.startsWith('--') && !arg.includes('=')));
const valueOf = (name) => {
    const inline = args.find((arg) => arg.startsWith(`--${name}=`));
    if (inline) return inline.split('=')[1];
    const index = args.indexOf(`--${name}`);

    return index >= 0 ? args[index + 1] : undefined;
};
const COMMANDS = ['check', 'rules', 'init', 'help', 'inventory', 'hook', 'story', 'narrow', 'system', 'fonts'];
const positional = args.filter((arg, index) => !arg.startsWith('--') && !['--format', '--out', '--still', '--title', '--music', '--width', '--character', '--brand', '--kind', '--ui', '--display', '--source'].includes(args[index - 1]));
// "ai-design-check src lang" is a check of those paths; the command word is optional.
const [command, ...named] = COMMANDS.includes(positional[0]) ? positional : ['check', ...positional];
// "./src/a.tsx" and absolute paths name the same file as "src/a.tsx"; the walker and the globs expect the last form.
const rest = named.map((path) => relative(process.cwd(), resolve(path)).split(sep).join('/') || '.');
const format = flags.has('--json') ? 'json' : (valueOf('format') ?? 'text');
const lang = flags.has('--tr') ? 'tr' : 'en';
const cwd = process.cwd();
const color = process.stdout.isTTY && !process.env.NO_COLOR;
const paint = (code, text) => (color ? `\x1b[${code}m${text}\x1b[0m` : text);
const SEVERITY = { error: (text) => paint(31, text), warn: (text) => paint(33, text), info: (text) => paint(36, text) };
// Output is collected and written once; exiting only after the write flushes keeps large piped output (--json) whole.
const lines = [];
const print = (...parts) => lines.push(parts.join(' '));
const done = (code) => {
    if (lines.length > 0) {
        // Synchronous write, retried while a non-blocking pipe is full, so nothing after done() runs and nothing is cut.
        const buffer = Buffer.from(`${lines.join('\n')}\n`);
        let offset = 0;
        while (offset < buffer.length) {
            try {
                offset += writeSync(1, buffer, offset);
            } catch (error) {
                if (error.code !== 'EAGAIN') throw error;
            }
        }
    }
    process.exit(code);
};

if (flags.has('--help') || flags.has('-h') || command === 'help') {
    print(HELP);
    done(0);
}

if (command === 'story') {
    if (named.length !== 2) {
        console.error('Usage: ai-design-check story <before.html|url> <after.html|url> [--out story.mp4]');
        done(1);
    }
    const { story } = await import('../src/story.js');
    try {
        const result = await story(named[0], named[1], { out: valueOf('out'), still: valueOf('still'), title: valueOf('title'), music: valueOf('music') });
        print(`${result.before} → ${result.after} findings, ${result.marked} marked on screen. Wrote ${relative(cwd, result.out)}`);
        done(0);
    } catch (error) {
        console.error(error.message);
        done(1);
    }
}

if (command === 'narrow') {
    if (named.length !== 1) {
        console.error('Usage: ai-design-check narrow <file.html|url> [--width 320]');
        done(1);
    }
    const { narrow } = await import('../src/narrow.js');
    try {
        const width = Number(valueOf('width') ?? 320);
        const results = await narrow(named[0], { width });
        if (format === 'json') print(JSON.stringify({ findings: results }, null, 2));
        else {
            for (const item of results) print(`  ${SEVERITY[item.severity](item.severity.padEnd(5))}  ${item.message}  ${paint(2, item.rule)}`);
            const errors = results.filter((item) => item.severity === 'error').length;
            print(`\n${results.length === 0 ? paint(32, `No problems at ${width} px.`) : `${errors} errors, ${results.length - errors} warnings and notes at ${width} px.`}`);
        }
        done(results.some((item) => item.severity === 'error') ? 1 : 0);
    } catch (error) {
        console.error(error.message);
        done(1);
    }
}

if (command === 'system') {
    const { designSystem, contrastReport } = await import('../src/system.js');
    const tokens = await import('../src/tokens.js');
    const { preview } = await import('../src/preview.js');
    try {
        let brand = valueOf('brand');
        if (brand !== undefined) {
            if (!/^#?[0-9a-f]{6}$/i.test(brand)) throw new Error(`--brand takes a hex color like "#1E5A63", got ${brand}`);
            brand = brand.startsWith('#') ? brand : `#${brand}`;
        }
        const system = designSystem({ character: valueOf('character'), kind: valueOf('kind'), brand, ui: valueOf('ui'), display: valueOf('display'), source: valueOf('source') });
        const outArg = valueOf('out');
        if (format === 'json' && !outArg) {
            print(tokens.json(system).trimEnd());
            done(0);
        }
        const out = resolve(outArg ?? 'design-system');
        mkdirSync(out, { recursive: true });
        const css = tokens.css(system);
        const files = {
            'tokens.css': css,
            'theme.css': tokens.tailwind(system),
            'tokens.json': tokens.json(system),
            'DesignSystem.swift': tokens.swift(system),
            'DesignSystem.kt': tokens.kotlin(system),
            'preview.html': preview(system, css),
        };
        for (const [name, content] of Object.entries(files)) writeFileSync(join(out, name), content);
        if (format === 'json') {
            print(tokens.json(system).trimEnd());
            done(0);
        }
        const low = (mode) => Math.min(...contrastReport(system.color[mode]).map((item) => item.ratio));
        print(`${system.character} · ${system.kind} · brand ${system.brand}`);
        print(`  Fonts     UI ${system.fonts.ui}, display ${system.fonts.display}, numbers ${system.fonts.numeric}, code ${system.fonts.mono}`);
        if (system.fonts.alternatives.ui.length) print(`            other UI fonts for ${system.character}: ${system.fonts.alternatives.ui.filter((name) => name !== system.fonts.ui).slice(0, 4).join(', ')}`);
        print(`  Type      ${Object.entries(system.type).map(([role, item]) => `${role} ${item.size}`).join(' · ')}`);
        print(`  Accent    ${system.color.light.accent} light, ${system.color.dark.accent} dark`);
        print(`  Contrast  lowest text pair ${low('light').toFixed(2)} light, ${low('dark').toFixed(2)} dark (WCAG 2, 4.5 for text)`);
        print(`  Radius    ${Object.entries(system.shape.radius).filter(([name]) => name !== 'full').map(([name, value]) => `${name} ${value}`).join(' · ')}`);
        print(`\nWrote ${Object.keys(files).join(', ')} to ${relative(cwd, out) || '.'}. Open preview.html to see both themes.`);
        done(0);
    } catch (error) {
        console.error(error.message);
        done(1);
    }
}

if (command === 'fonts') {
    const { library, fontsFor, CHARACTERS } = await import('../src/system.js');
    const lib = library();
    const character = valueOf('character');
    try {
        if (character) {
            const fonts = fontsFor(character, { source: 'any' });
            print(`${character}: ${lib.characters[character]}`);
            print(`  Pairing   UI ${fonts.ui.name}, display ${fonts.display.name}, numbers ${fonts.numeric.name}, code ${fonts.mono.name}`);
            print(`  Also      UI ${fonts.alternatives.ui.join(', ') || '-'}; display ${fonts.alternatives.display.join(', ') || '-'}`);
            if (fonts.alternatives.adobe.length) print(`  Adobe     ${fonts.alternatives.adobe.join(', ')} (Creative Cloud; web only, not for bundling in an app)`);
            done(0);
        }
        print('Characters (--character):');
        for (const name of Object.keys(CHARACTERS)) print(`  ${name.padEnd(12)} ${lib.characters[name]}`);
        print('\nFonts:');
        for (const item of lib.families) print(`  ${item.name.padEnd(22)} ${item.source.padEnd(7)} ${item.category.padEnd(6)} ${item.roles.join(', ').padEnd(24)} ${paint(2, item.characters.join(', '))}`);
        print(`\n${lib.families.filter((item) => item.source === 'google').length} Google Fonts (free to use and bundle), ${lib.families.filter((item) => item.source === 'adobe').length} Adobe Fonts (Creative Cloud, web only).`);
        done(0);
    } catch (error) {
        console.error(error.message);
        done(1);
    }
}

if (command === 'rules') {
    const { rules, areas } = loadRules();
    for (const rule of rules) {
        print(`${SEVERITY[rule.severity](rule.severity.padEnd(5))}  ${rule.id.padEnd(28)} ${areas[rule.area][lang].padEnd(20)} ${rule.title[lang]}${rule.check ? '' : paint(2, '  (review)')}`);
    }
    done(0);
}

if (command === 'init') {
    const file = join(cwd, CONFIG_FILE);
    if (existsSync(file)) {
        console.error(`${CONFIG_FILE} already exists.`);
        done(1);
    }
    const config = {
        include: ['resources/js', 'src'],
        ignore: [],
        i18n: { files: ['lang/*.json'], keysAreSource: true },
        properNouns: [],
        componentDirs: ['**/components/ui/**'],
        rules: {},
        allow: { 'type-scale': [], 'radius-scale': [], 'glow-in-charts-only': [] },
    };
    writeFileSync(file, `${JSON.stringify(config, null, 4)}\n`);
    print(`Wrote ${CONFIG_FILE}. Add exceptions under "allow" as "path/glob" or "path/glob:exact match".`);
    done(0);
}

if (command === 'inventory') {
    const result = inventory(cwd, rest.length > 0 ? { include: rest } : {});
    if (format === 'json') {
        print(JSON.stringify(result, null, 2));
        done(0);
    }
    const NAMES = { button: 'Buttons', input: 'Form fields', heading: 'Headings', badge: 'Badges', card: 'Cards and boxes' };
    for (const [kind, data] of Object.entries(result)) {
        print(`\n${paint(1, NAMES[kind])}  ${data.total} uses · ${data.distinct} different looks · ${data.raw} without a shared component`);
        for (const variant of data.variants.slice(0, flags.has('--all') ? Infinity : 8)) {
            print(`  ${String(variant.count).padStart(4)}×  ${variant.key.length > 110 ? `${variant.key.slice(0, 109)}…` : variant.key}  ${paint(2, variant.first)}`);
        }
    }
    print(`\nFewer looks is better: one input, a short heading scale, a few button and badge variants. ${paint(2, '--all lists every look')}`);
    done(0);
}

if (command === 'hook') {
    // Claude Code / Cursor / Codex post-edit hooks send JSON naming the edited file; exit 2 hands the findings back to the agent.
    let input = {};
    try {
        input = JSON.parse(readFileSync(0, 'utf8') || '{}');
    } catch {}
    const file = input.tool_input?.file_path ?? input.tool_input?.path ?? input.file_path ?? input.path;
    if (!file) done(0);
    const path = relative(cwd, file).split(sep).join('/');
    if (path.startsWith('..')) done(0);
    const findings = check(cwd, { include: [path] }).filter((item) => item.rule !== 'repeated-markup' && item.severity !== 'info');
    if (findings.length === 0) done(0);
    console.error(`ai-design-check found ${findings.length} design rule issue(s) in ${path}. Fix them, or add "// ai-design-check-ignore-next-line <rule> -- <reason>" when the rule does not apply:`);
    for (const item of findings) console.error(`  ${path}:${item.line}  ${item.rule}  ${item.message}`);
    console.error('Rules and how to fix them: npx @enmera/ai-design-check rules');
    done(2);
}

if (command !== 'check') {
    console.error(`Unknown command "${command}".\n\n${HELP}`);
    done(2);
}

let findings = check(cwd, rest.length > 0 ? { include: rest } : {});
const baselineFile = join(cwd, BASELINE);

if (flags.has('--write-baseline')) {
    writeFileSync(baselineFile, `${JSON.stringify({ version: 1, note: 'Findings that existed when the baseline was written; only new ones are reported.', counts: toBaseline(findings) }, null, 2)}\n`);
    print(`Wrote ${BASELINE} with ${findings.length} existing findings. Commit it; later runs report only new findings.`);
    done(0);
}

let baselined = 0;
if (!flags.has('--no-baseline') && existsSync(baselineFile)) {
    const before = findings.length;
    findings = applyBaseline(findings, JSON.parse(readFileSync(baselineFile, 'utf8')).counts ?? {});
    baselined = before - findings.length;
}

const count = (severity) => findings.filter((item) => item.severity === severity).length;
const { rules } = loadRules();
const review = rules.filter((rule) => !rule.check).length;

if (format === 'json') {
    print(JSON.stringify({ findings, errors: count('error'), warnings: count('warn'), notes: count('info'), baselined, reviewRules: review }, null, 2));
} else if (format === 'github') {
    const LEVEL = { error: 'error', warn: 'warning', info: 'notice' };
    for (const item of findings) print(`::${LEVEL[item.severity]} file=${item.path},line=${item.line},title=${item.rule}::${item.message.replace(/\n/g, ' ')}`);
} else {
    if (!flags.has('--quiet')) {
        let current = null;
        for (const item of findings) {
            if (item.path !== current) {
                current = item.path;
                print(`\n${paint(1, item.path)}`);
            }
            print(`  ${String(item.line).padStart(5)}  ${SEVERITY[item.severity](item.severity.padEnd(5))}  ${item.message}  ${paint(2, item.rule)}`);
        }
    }
    const summary = findings.length === 0 ? paint(32, 'No findings.') : `${count('error')} errors, ${count('warn')} warnings, ${count('info')} notes.`;
    print(`\n${summary}${baselined ? ` ${baselined} known findings hidden by the baseline.` : ''} ${paint(2, `${rules.length - review} rules checked automatically; ${review} need a look at the screen (npx @enmera/ai-design-check rules).`)}`);
}

done(count('error') > 0 || (flags.has('--strict') && count('warn') > 0) ? 1 : 0);
