import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { classUnits, tokens, utility } from './classes.js';
import { CONTAINER_VISUAL, VISUAL, extensionOf, loadConfig, matches, signature, walk } from './check.js';
import { parseAttrs, tags } from './jsx.js';
import { LOOKS } from './looks.js';

/**
 * Inventory: how many different ways each kind of element is written. A healthy system has one or two button
 * looks, one input look, a short heading scale, a few badge tones and one card. Counts above that are drift.
 */

const KINDS = {
    button: { raw: ['button'], components: ['Button', 'LinkButton', 'IconButton'] },
    input: { raw: ['input', 'select', 'textarea'], components: ['Input', 'Select', 'Textarea', 'SelectField', 'TextField'] },
    heading: { raw: LOOKS.heading.tags, components: ['Heading'] },
    badge: { raw: LOOKS.badge.tags, components: ['Badge', 'StatusBadge'], rawFilter: LOOKS.badge.test },
    card: { raw: LOOKS.card.tags, components: ['Card', 'SectionCard', 'Tile', 'Panel'], rawFilter: LOOKS.card.test },
};

const PROP_KEYS = ['variant', 'size', 'tone', 'color', 'intent', 'appearance'];

const classText = (attrs, functions) => {
    const raw = attrs.className ?? attrs.class;
    if (raw === undefined) return '';

    return typeof raw === 'string' ? raw : classUnits(`className={${raw.code}}`, functions).map((unit) => unit.text).join(' ');
};

export function inventory(cwd, overrides = {}) {
    const config = { ...loadConfig(cwd), ...overrides };
    const files = [...new Set(config.include.flatMap((start) => walk(cwd, start, config.ignore)))].filter((path) => ['tsx', 'jsx', 'vue', 'svelte', 'html', 'blade.php'].includes(extensionOf(path)));
    const result = {};

    for (const kind of Object.keys(KINDS)) result[kind] = { total: 0, variants: new Map() };

    for (const path of files) {
        const source = readFileSync(join(cwd, path), 'utf8');
        const lineOf = (index) => source.slice(0, index).split('\n').length;
        const insideComponents = matches(config.componentDirs, path);

        for (const [kind, spec] of Object.entries(KINDS)) {
            for (const tag of tags(source, [...spec.raw, ...spec.components])) {
                const attrs = parseAttrs(tag.attrs);
                const text = classText(attrs, config.classFunctions);
                let key;
                if (spec.components.includes(tag.name)) {
                    const props = PROP_KEYS.filter((name) => typeof attrs[name] === 'string').map((name) => `${name}=${attrs[name]}`);
                    // A component's look is its props plus any look classes added from outside; placement and inner layout do not count.
                    const look = config.containers.includes(tag.name) ? CONTAINER_VISUAL : VISUAL;
                    const extra = [...new Set(tokens(text).filter((token) => look.test(utility(token))))].sort().join(' ');
                    key = `<${tag.name}${props.length ? ` ${props.join(' ')}` : ''}>${extra ? ` + ${extra}` : ''}`;
                } else {
                    if (insideComponents) continue; // the component's own definition is the one allowed raw copy
                    if (spec.rawFilter && !spec.rawFilter(text)) continue;
                    if (tag.name === 'input' && ['hidden', 'file', 'checkbox', 'radio'].includes(attrs.type)) continue;
                    key = `<${tag.name}> ${signature(text) || '(no classes)'}`;
                }
                const bucket = result[kind];
                bucket.total++;
                const variant = bucket.variants.get(key) ?? { key, count: 0, first: `${path}:${lineOf(tag.start)}`, files: new Set() };
                variant.count++;
                variant.files.add(path);
                bucket.variants.set(key, variant);
            }
        }
    }

    return Object.fromEntries(
        Object.entries(result).map(([kind, bucket]) => [
            kind,
            {
                total: bucket.total,
                distinct: bucket.variants.size,
                raw: [...bucket.variants.values()].filter((variant) => !KINDS[kind].components.some((name) => variant.key.startsWith(`<${name}`))).reduce((sum, variant) => sum + variant.count, 0),
                variants: [...bucket.variants.values()].sort((a, b) => b.count - a.count).map((variant) => ({ ...variant, files: variant.files.size })),
            },
        ]),
    );
}

/** Tokens that differ between two class lists: what makes two copies of the same element look different. */
export function difference(a, b) {
    const left = new Set(tokens(a).map(utility));
    const right = new Set(tokens(b).map(utility));

    return { only: [...left].filter((token) => !right.has(token)), other: [...right].filter((token) => !left.has(token)) };
}
