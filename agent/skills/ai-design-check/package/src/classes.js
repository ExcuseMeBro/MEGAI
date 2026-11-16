/**
 * Class string extraction without a parser dependency. A "unit" is everything one element or one helper call puts on a
 * node: a class/className attribute, or a cn()/clsx()/cva()/twMerge() call. Rules that look at classes (scale, focus
 * ring, uppercase …) run on units, so text in comments, copy and unrelated strings no longer matches.
 */

export const CLASS_FUNCTIONS = ['cn', 'clsx', 'classnames', 'classNames', 'cva', 'twMerge', 'tv', 'cx'];

const STRING = /'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`/gsu;

/** Index after the matching close bracket, skipping string literals; -1 when unbalanced. */
export function balancedEnd(source, openIndex, open = '{', close = '}') {
    let depth = 0;
    for (let i = openIndex; i < source.length; i++) {
        const char = source[i];
        if (char === '"' || char === "'" || char === '`') {
            const quote = char;
            for (i++; i < source.length && source[i] !== quote; i++) {
                if (source[i] === '\\') i++;
                else if (quote !== '`' && source[i] === '\n') break;
            }
            continue;
        }
        if (char === open) depth++;
        else if (char === close && --depth === 0) return i + 1;
    }

    return -1;
}

/** Static parts of every string literal in a code fragment; template expressions are scanned for nested strings. */
export function literals(code) {
    const out = [];
    for (const match of code.matchAll(STRING)) {
        const raw = match[0];
        const body = raw.slice(1, -1);
        if (raw[0] !== '`') {
            out.push(body);
            continue;
        }
        out.push(body.replace(/\$\{[^}]*\}/g, ' '));
        for (const expression of body.matchAll(/\$\{([^}]*)\}/g)) out.push(...literals(expression[1]));
    }

    return out;
}

const clean = (parts) => parts.join(' ').replace(/\s+/g, ' ').trim();

/** @returns {{index: number, text: string, kind: 'attribute'|'call', element: string|null}[]} */
export function classUnits(source, functions = CLASS_FUNCTIONS) {
    const units = [];
    const covered = [];

    for (const match of source.matchAll(/\b(?:className|class|:class|ngClass)\s*=\s*(?=["'`{])/g)) {
        const start = match.index + match[0].length;
        const quote = source[start];
        let end;
        let text;
        if (quote === '{') {
            end = balancedEnd(source, start);
            if (end < 0) continue;
            text = clean(literals(source.slice(start, end)));
        } else {
            end = source.indexOf(quote, start + 1);
            if (end < 0) continue;
            end += 1;
            // Blade/Vue: keep the static text, drop {{ … }} and :binding expressions.
            text = clean([source.slice(start + 1, end - 1).replace(/\{\{[\s\S]*?\}\}|@\w+\([^)]*\)/g, ' ')]);
        }
        covered.push([start, end]);
        // Element that carries the attribute: the nearest "<Name" before it.
        const open = source.lastIndexOf('<', match.index);
        const element = open >= 0 ? (/^<([A-Za-z][\w.-]*)/.exec(source.slice(open, open + 60))?.[1] ?? null) : null;
        if (text) units.push({ index: match.index, text, kind: 'attribute', element });
    }

    const callPattern = new RegExp(`(?<![\\w.$])(?:${functions.map((name) => name.replace(/[$]/g, '\\$')).join('|')})\\s*\\(`, 'g');
    for (const match of source.matchAll(callPattern)) {
        if (covered.some(([from, to]) => match.index >= from && match.index < to)) continue;
        const open = match.index + match[0].length - 1;
        const end = balancedEnd(source, open, '(', ')');
        if (end < 0) continue;
        const text = clean(literals(source.slice(open, end)));
        if (text) units.push({ index: match.index, text, kind: 'call', element: null });
    }

    return units.sort((a, b) => a.index - b.index);
}

/** Tailwind class tokens of a unit; variant prefixes kept ("md:hover:bg-x"). */
export const tokens = (text) => text.split(/\s+/).filter(Boolean);

/** Utility without its variants: "md:hover:px-4" → "px-4", "!px-4" → "px-4". */
export const utility = (token) => token.split(':').pop().replace(/^!/, '').replace(/^-/, '');

/**
 * Comments replaced by spaces (newlines kept, so indexes and line numbers stay valid); strings are left intact, so a
 * URL's "//" is not mistaken for a comment. JSX {/* … *\/} comments are covered by the block form.
 */
export function blankComments(source, lineComments = true) {
    let out = '';
    for (let i = 0; i < source.length; i++) {
        const char = source[i];
        if (char === '"' || char === "'" || char === '`') {
            let j = i + 1;
            while (j < source.length && source[j] !== char) {
                if (source[j] === '\\') j++;
                else if (char !== '`' && source[j] === '\n') break;
                j++;
            }
            out += source.slice(i, j + 1);
            i = j;
            continue;
        }
        if (char === '/' && source[i + 1] === '*') {
            const end = source.indexOf('*/', i + 2);
            const stop = end < 0 ? source.length : end + 2;
            out += source.slice(i, stop).replace(/[^\n]/g, ' ');
            i = stop - 1;
            continue;
        }
        if (lineComments && char === '/' && source[i + 1] === '/' && source[i - 1] !== ':') {
            const end = source.indexOf('\n', i);
            const stop = end < 0 ? source.length : end;
            out += ' '.repeat(stop - i);
            i = stop - 1;
            continue;
        }
        out += char;
    }

    return out;
}
