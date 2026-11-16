import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { findChrome, launch } from './story.js';

/**
 * Narrow-screen check: renders the page at a phone width and at a desktop width in Chrome and reports what only a
 * rendered page shows: the page scrolling sideways, text cut off, text made smaller to fit, and content that is
 * there on desktop but gone on the phone. Run it with the longest locale (German, Finnish) to find the breaks early.
 */

const MEASURE = `(() => {
    const path = (element) => {
        const parts = [];
        for (let node = element; node && node !== document.body; node = node.parentElement) parts.unshift([...node.parentElement.children].indexOf(node));
        return parts.join('.');
    };
    const ownText = (element) => [...element.childNodes].filter((node) => node.nodeType === 3).map((node) => node.textContent).join(' ').replace(/\\s+/g, ' ').trim();
    const name = (element, text) => element.tagName.toLowerCase() + (text ? ' "' + (text.length > 48 ? text.slice(0, 47) + '…' : text) + '"' : '');
    // Layout width, not window.innerWidth: a mobile browser zooms out to fit an overflowing page.
    const width = document.documentElement.clientWidth;
    const elements = [];
    for (const element of document.body.querySelectorAll('*')) {
        if (['SCRIPT', 'STYLE', 'TEMPLATE', 'NOSCRIPT', 'svg', 'path'].includes(element.tagName)) continue;
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        const text = ownText(element);
        const visible = style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
        // Inside a container that scrolls sideways on purpose (a wide table), overflow is the design.
        let scroller = false;
        for (let node = element.parentElement; node && node !== document.body; node = node.parentElement) {
            if (/(auto|scroll)/.test(getComputedStyle(node).overflowX)) { scroller = true; break; }
        }
        elements.push({
            key: path(element), label: name(element, text), text: text.length > 0, visible, scroller,
            right: rect.right, font: parseFloat(style.fontSize),
            clipped: text.length > 0 && visible && element.scrollWidth > element.clientWidth + 1 && /(hidden|clip)/.test(style.overflowX + style.overflow) && !element.title,
            ellipsis: text.length > 0 && visible && style.textOverflow === 'ellipsis' && element.scrollWidth > element.clientWidth + 1 && !element.title,
        });
    }
    return { width, scrollWidth: document.documentElement.scrollWidth, elements };
})()`;

const finding = (rule, severity, path, value, message) => ({ rule, severity, path, line: 0, value, message });

/**
 * @param {string} input file or URL
 * @param {{width?: number, desktop?: number}} options
 */
export async function narrow(input, { width = 320, desktop = 1280 } = {}) {
    const chrome = findChrome();
    if (!chrome) throw new Error('Chrome or Chromium not found; set CHROME_PATH');
    const url = /^https?:\/\//.test(input) ? input : pathToFileURL(resolve(input)).href;
    if (!/^https?:\/\//.test(input) && !existsSync(resolve(input))) throw new Error(`Not found: ${input}`);

    const browser = await launch(chrome);
    try {
        await browser.open(url, { width: desktop, height: 900 });
        const wide = await browser.evaluate(MEASURE);
        await browser.open(url, { width, height: 800, mobile: true });
        const phone = await browser.evaluate(MEASURE);
        const before = new Map(wide.elements.map((element) => [element.key, element]));
        const findings = [];

        if (phone.scrollWidth > phone.width + 1) {
            const culprits = phone.elements.filter((element) => element.visible && !element.scroller && element.right > phone.width + 1 && element.text).slice(0, 5);
            findings.push(finding('no-horizontal-overflow', 'error', input, `${phone.scrollWidth}px`, `Page is ${phone.scrollWidth} px wide at ${width} px; it scrolls sideways${culprits.length ? `: ${culprits.map((element) => element.label).join(', ')}` : ''}`));
        }
        for (const element of phone.elements) {
            if (element.clipped || element.ellipsis) findings.push(finding('text-not-clipped', 'warn', input, element.label, `Text cut off at ${width} px: ${element.label}`));
            const was = before.get(element.key);
            if (element.text && element.visible && element.font < 12) findings.push(finding('no-shrunk-text', 'error', input, element.label, `Text at ${element.font} px on a ${width} px screen: ${element.label}`));
            else if (element.text && element.visible && was?.visible && was.font <= 18 && element.font < was.font - 0.5) {
                findings.push(finding('no-shrunk-text', 'warn', input, element.label, `Text shrinks from ${was.font} px to ${element.font} px at ${width} px: ${element.label}`));
            }
            if (element.text && !element.visible && was?.visible && was.text) findings.push(finding('no-hidden-content-narrow', 'info', input, element.label, `Shown on desktop, hidden at ${width} px: ${element.label}`));
        }

        return findings;
    } finally {
        await browser.close();
    }
}
