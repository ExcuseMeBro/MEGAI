/**
 * Hand-written looks that a shared component should own: a span styled as a badge, a div styled as a card, a heading
 * with its own size, a link styled as a button. Used by the checker (shared-looks) and by the inventory.
 */
const has = (pattern) => (text) => pattern.test(text);
const all = (...tests) => (text) => tests.every((test) => test(text));

export const LOOKS = {
    badge: {
        tags: ['span'],
        component: 'StatusBadge',
        name: 'badge',
        test: all(has(/(?:^|\s)rounded(?:-full|-md|-lg)?(?:\s|$)/), has(/(?:^|\s)text-(?:2xs|xs)(?:\s|$)/), has(/(?:^|\s)px-/), has(/(?:^|\s)(?:bg-|ring-)/)),
    },
    card: {
        tags: ['div', 'section', 'article', 'li'],
        component: 'Tile / SectionCard',
        name: 'box',
        test: all(has(/(?:^|\s)rounded-(?:xl|2xl|3xl|lg)(?:\s|$)/), has(/(?:^|\s)(?:border|ring-1|shadow)/), has(/(?:^|\s)bg-/)),
    },
    heading: {
        tags: ['h1', 'h2', 'h3', 'h4'],
        component: 'Heading',
        name: 'heading',
        test: has(/(?:^|\s)(?:[\w-]+:)*(?:text-(?:2xs|xs|sm|base|lg|[2-9]?xl)|text-\[\d[^\]]*\]|font-display)(?:\s|$)/),
    },
    link: {
        tags: ['a', 'Link'],
        component: 'LinkButton',
        name: 'button link',
        test: all(has(/(?:^|\s)rounded/), has(/(?:^|\s)bg-(?!transparent)/), has(/(?:^|\s)p[xy]?-/)),
    },
};
