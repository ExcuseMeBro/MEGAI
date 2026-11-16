/**
 * Color math with no dependencies: hex <-> OKLCH, gamut mapping by chroma reduction, WCAG 2 contrast. OKLCH keeps
 * lightness perceptual, so a ramp built on L steps looks even and a hue keeps its character when it gets lighter.
 */

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export function hexToRgb(hex) {
    const clean = hex.replace('#', '').trim();
    const full = clean.length === 3 ? [...clean].map((char) => char + char).join('') : clean;
    if (!/^[0-9a-f]{6}$/i.test(full)) throw new Error(`Not a hex color: ${hex}`);

    return [0, 2, 4].map((at) => parseInt(full.slice(at, at + 2), 16) / 255);
}

export const rgbToHex = (rgb) => `#${rgb.map((channel) => Math.round(clamp(channel, 0, 1) * 255).toString(16).padStart(2, '0')).join('')}`;

const toLinear = (channel) => (channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4);
const toGamma = (channel) => (channel <= 0.0031308 ? channel * 12.92 : 1.055 * channel ** (1 / 2.4) - 0.055);

function rgbToOklab([r, g, b]) {
    const [lr, lg, lb] = [r, g, b].map(toLinear);
    const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
    const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
    const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);

    return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s, 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s, 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
}

function oklabToLinear([L, a, b]) {
    const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;

    return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
}

/** @returns {{l: number, c: number, h: number}} */
export function hexToOklch(hex) {
    const [L, a, b] = rgbToOklab(hexToRgb(hex));
    const h = (Math.atan2(b, a) * 180) / Math.PI;

    return { l: L, c: Math.hypot(a, b), h: h < 0 ? h + 360 : h };
}

const inGamut = (linear) => linear.every((channel) => channel >= -0.0001 && channel <= 1.0001);

/** OKLCH to hex; a color outside sRGB keeps its lightness and hue and loses chroma until it fits. */
export function oklchToHex({ l, c, h }) {
    const lab = (chroma) => [l, chroma * Math.cos((h * Math.PI) / 180), chroma * Math.sin((h * Math.PI) / 180)];
    let low = 0;
    let high = c;
    if (!inGamut(oklabToLinear(lab(c)))) {
        for (let step = 0; step < 24; step++) {
            const mid = (low + high) / 2;
            if (inGamut(oklabToLinear(lab(mid)))) low = mid;
            else high = mid;
        }
        c = low;
    }

    return rgbToHex(oklabToLinear(lab(c)).map((channel) => toGamma(clamp(channel, 0, 1))));
}

export function luminance(hex) {
    const [r, g, b] = hexToRgb(hex).map(toLinear);

    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** WCAG 2 contrast ratio, 1 to 21. Text needs 4.5 (large text and UI parts 3). */
export function contrast(a, b) {
    const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x);

    return (high + 0.05) / (low + 0.05);
}

/**
 * Moves a color's lightness, keeping hue and chroma, until it reaches the contrast target against a background.
 * Direction comes from the background: darker on a light background, lighter on a dark one.
 */
export function withContrast(color, background, target) {
    const start = hexToOklch(color);
    if (contrast(color, background) >= target) return color;
    const darker = luminance(background) > 0.18;
    let { l } = start;
    for (let step = 0; step < 100; step++) {
        l = clamp(l + (darker ? -0.01 : 0.01), 0, 1);
        const candidate = oklchToHex({ ...start, l });
        if (contrast(candidate, background) >= target || l === 0 || l === 1) return candidate;
    }

    return oklchToHex({ ...start, l });
}

export const round = (value, digits = 2) => Math.round(value * 10 ** digits) / 10 ** digits;
