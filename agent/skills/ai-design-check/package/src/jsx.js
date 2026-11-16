import { balancedEnd, literals } from './classes.js';

/**
 * Small JSX/HTML element reader: opening tags with their attributes, and (for short elements) their children. Enough
 * for structural rules (icon-only buttons, shared components) without a parser dependency.
 */

/** Reads the opening tag that starts at `index` ("<Button …>"). */
export function readTag(source, index) {
    const head = /^<([A-Za-z][\w.-]*)/.exec(source.slice(index, index + 80));
    if (!head) return null;
    let i = index + head[0].length;
    const attrStart = i;
    while (i < source.length) {
        const char = source[i];
        if (char === '{') {
            const end = balancedEnd(source, i);
            if (end < 0) return null;
            i = end;
            continue;
        }
        if (char === '"' || char === "'") {
            const end = source.indexOf(char, i + 1);
            if (end < 0) return null;
            i = end + 1;
            continue;
        }
        if (char === '<' && i > attrStart) return null; // not a tag (comparison, generic type)
        if (char === '>') {
            const selfClosing = source[i - 1] === '/';
            return { name: head[1], attrs: source.slice(attrStart, selfClosing ? i - 1 : i), selfClosing, start: index, end: i + 1 };
        }
        i++;
    }

    return null;
}

/** Attribute map: a string for "…" (or {'…'}), { code } for any other {…} expression, true for a bare attribute. */
export function parseAttrs(attrs) {
    const out = {};
    const pattern = /([:@\w.-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|\{))?/g;
    let match;
    while ((match = pattern.exec(attrs))) {
        const [whole, name, double, single] = match;
        if (whole.endsWith('{')) {
            const open = match.index + whole.length - 1;
            const end = balancedEnd(attrs, open);
            const code = attrs.slice(open + 1, end < 0 ? attrs.length : end - 1).trim();
            const literal = /^(['"`])([^'"`$]*)\1$/.exec(code);
            out[name] = literal ? literal[2] : { code };
            pattern.lastIndex = end < 0 ? attrs.length : end;
        } else {
            out[name] = double ?? single ?? true;
        }
    }

    return out;
}

/** Every opening tag whose name matches `names` (array of exact names). */
export function* tags(source, names) {
    const wanted = new Set(names);
    for (const match of source.matchAll(/<([A-Za-z][\w.-]*)(?=[\s/>])/g)) {
        if (!wanted.has(match[1])) continue;
        const tag = readTag(source, match.index);
        if (tag) yield tag;
    }
}

/** Children of a non-self-closing element up to its closing tag (no nesting of the same name), at most `limit` chars. */
export function children(source, tag, limit = 1200) {
    if (tag.selfClosing) return '';
    const close = source.indexOf(`</${tag.name}>`, tag.end);
    if (close < 0 || close - tag.end > limit) return null;

    return source.slice(tag.end, close);
}

/** Visible text of JSX children: tags removed, {expressions} kept as a marker when they can render text. */
export function visibleText(markup) {
    let text = '';
    let i = 0;
    while (i < markup.length) {
        const char = markup[i];
        if (char === '{') {
            const end = balancedEnd(markup, i);
            const code = markup.slice(i + 1, end < 0 ? markup.length : end - 1).trim();
            // {/* comment */} and {icon} render nothing readable; t('…'), strings and other values may.
            if (code && !code.startsWith('/*') && !/^<\s*[A-Z]\w*Icon\b[^>]*\/>$/.test(code)) text += literals(code).join(' ').trim() || ' {expr} ';
            i = end < 0 ? markup.length : end;
            continue;
        }
        if (char === '<') {
            const end = markup.indexOf('>', i);
            const tagText = markup.slice(i, end < 0 ? markup.length : end + 1);
            if (/\bsr-only\b/.test(tagText)) text += ' {sr-only} ';
            i = end < 0 ? markup.length : end + 1;
            continue;
        }
        text += char;
        i++;
    }

    return text.replace(/\s+/g, ' ').trim();
}
