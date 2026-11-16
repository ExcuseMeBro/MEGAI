import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { check, loadRules } from './check.js';

/**
 * Before/after story video: the before screen with every finding marked, a wipe to the after screen while the
 * count falls, and an end card. No dependencies: Chrome is driven over the DevTools protocol (Node's WebSocket)
 * and ffmpeg encodes the frames.
 */

const SIZE = 1080;
const FPS = 30;
const DURATION = 12;
const VIEW = { width: 1280, height: 1000 };

export function findChrome() {
    const candidates = [
        process.env.CHROME_PATH,
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    ].filter(Boolean);
    const found = candidates.find((path) => existsSync(path));
    if (found) return found;
    for (const name of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
        const which = spawnSync('which', [name], { encoding: 'utf8' });
        if (which.status === 0 && which.stdout.trim()) return which.stdout.trim();
    }

    return null;
}

export async function launch(chrome) {
    const profile = mkdtempSync(join(tmpdir(), 'ai-design-check-chrome-'));
    const proc = spawn(chrome, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--hide-scrollbars', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--allow-file-access-from-files', 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
    const endpoint = await new Promise((done, fail) => {
        let buffer = '';
        proc.stderr.on('data', (chunk) => {
            buffer += chunk;
            const match = /DevTools listening on (ws:\/\/\S+)/.exec(buffer);
            if (match) done(match[1]);
        });
        proc.on('exit', () => fail(new Error('Chrome exited before it opened the DevTools port')));
    });
    const targets = await (await fetch(`http://127.0.0.1:${new URL(endpoint).port}/json/list`)).json();
    const socket = new WebSocket(targets.find((target) => target.type === 'page').webSocketDebuggerUrl);
    await new Promise((done, fail) => {
        socket.onopen = done;
        socket.onerror = fail;
    });

    let id = 0;
    const pending = new Map();
    const listeners = new Map();
    socket.onmessage = ({ data }) => {
        const message = JSON.parse(data);
        if (message.id && pending.has(message.id)) {
            const { done, fail } = pending.get(message.id);
            pending.delete(message.id);
            message.error ? fail(new Error(message.error.message)) : done(message.result);
        } else if (message.method) (listeners.get(message.method) ?? []).splice(0).forEach((listener) => listener(message.params));
    };
    const send = (method, params = {}) => new Promise((done, fail) => {
        pending.set(++id, { done, fail });
        socket.send(JSON.stringify({ id, method, params }));
    });
    const once = (method, timeout = 20000) => new Promise((done) => {
        listeners.set(method, [...(listeners.get(method) ?? []), done]);
        setTimeout(done, timeout);
    });
    const evaluate = async (expression) => {
        const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
        if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description ?? 'Evaluation failed');

        return result.result.value;
    };
    await send('Page.enable');

    return {
        send,
        evaluate,
        async open(url, { width, height, settle = 1200, mobile = false }) {
            await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: mobile ? 2 : 1, mobile });
            const loaded = once('Page.loadEventFired');
            await send('Page.navigate', { url });
            await loaded;
            await new Promise((done) => setTimeout(done, settle)); // CDN styles and fonts
        },
        async close() {
            socket.close();
            const exited = new Promise((done) => proc.once('exit', done));
            proc.kill();
            // Chrome's helpers can outlive the main process for a moment (Linux); never let cleanup fail the run.
            const timer = setTimeout(() => proc.kill('SIGKILL'), 3000);
            await exited;
            clearTimeout(timer);
            try {
                rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
            } catch {
                // A leftover temp profile is harmless; the OS clears tmp.
            }
        },
    };
}

/** A local copy of the page for the checker, and the URL Chrome opens. */
async function source(input, work, name) {
    if (/^https?:\/\//.test(input)) {
        const html = await (await fetch(input)).text();
        writeFileSync(join(work, `${name}.html`), html);

        return { url: input, dir: work, file: `${name}.html` };
    }
    const path = resolve(input);
    if (!existsSync(path)) throw new Error(`Not found: ${input}`);

    return { url: pathToFileURL(path).href, dir: dirname(path), file: basename(path) };
}

/** Boxes on the screen for each finding: elements that carry the class, or the text that matched. */
const BOXES = (values, view) => `(() => {
    const values = ${JSON.stringify(values)};
    const boxes = [];
    const add = (raw) => {
        // Clamp to the screen; page-sized regions (the main column, the sidebar) would cover everything.
        const left = Math.max(0, raw.left), top = Math.max(0, raw.top);
        const rect = { left, top, width: Math.min(${view.width}, raw.right) - left, height: Math.min(${view.height}, raw.bottom) - top };
        if (rect.width < 2 || rect.height < 2 || rect.width * rect.height > ${view.width * view.height} * 0.12) return;
        boxes.push({ x: rect.left, y: rect.top, w: rect.width, h: rect.height });
    };
    // A blurred or hidden decoration has no visible edge to point at.
    const visible = (element) => {
        const style = getComputedStyle(element);
        return style.visibility !== 'hidden' && Number(style.opacity) > 0.05 && !/blur/.test(style.filter);
    };
    const all = [...document.querySelectorAll('body *')];
    for (const value of values) {
        if (!/\\s/.test(value) && /[-:[]/.test(value)) {
            all.filter((element) => element.classList.contains(value) && visible(element)).slice(0, 40).forEach((element) => add(element.getBoundingClientRect()));
            continue;
        }
        // Every place the text appears (the same emoji in each row), not only the first.
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let found = 0;
        while (walker.nextNode() && found < 20) {
            const text = walker.currentNode.textContent;
            for (let at = text.indexOf(value); at >= 0 && found < 20; at = text.indexOf(value, at + value.length)) {
                const range = document.createRange();
                range.setStart(walker.currentNode, at);
                range.setEnd(walker.currentNode, at + value.length);
                add(range.getBoundingClientRect());
                found++;
            }
        }
    }
    const seen = new Set();
    // Reading order, so the marks sweep down the screen.
    boxes.sort((a, b) => Math.round(a.y / 8) - Math.round(b.y / 8) || a.x - b.x);
    return boxes.filter((box) => {
        const key = [box.x, box.y, box.w, box.h].map(Math.round).join(',');
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    }).slice(0, 160);
})()`;

const STAGE = (data) => `<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#0e0f12">
<canvas id="c" width="${SIZE}" height="${SIZE}"></canvas>
<script>
const data = ${JSON.stringify(data)};
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const load = (src) => new Promise((done) => { const image = new Image(); image.onload = () => done(image); image.src = src; });
let before, after;
const ready = Promise.all([load(data.before), load(data.after)]).then(([a, b]) => { before = a; after = b; });
const ease = (x) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);
const span = (t, from, to) => ease((t - from) / (to - from));
const FONT = '-apple-system, "Segoe UI", Inter, system-ui, sans-serif';
const MONO = '"SF Mono", Menlo, Consolas, monospace';
const X = 40, Y = 170, W = 1000, H = W * ${VIEW.height} / ${VIEW.width}, S = W / ${VIEW.width};
function rounded(x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
function render(t) {
    ctx.clearRect(0, 0, ${SIZE}, ${SIZE});
    ctx.fillStyle = '#0e0f12'; ctx.fillRect(0, 0, ${SIZE}, ${SIZE});
    const fade = span(t, 0, 0.5);
    const wipe = span(t, 5.4, 7.6);
    const wipeX = X + W * wipe;
    const count = t < 5.4 ? Math.round(data.beforeCount * span(t, 0.6, 4.6)) : Math.round(data.beforeCount + (data.afterCount - data.beforeCount) * wipe);
    ctx.globalAlpha = fade;

    // Header: which screen and the live count.
    ctx.fillStyle = '#8b8f98'; ctx.font = '500 26px ' + FONT; ctx.textBaseline = 'alphabetic';
    ctx.fillText(t < 6.5 ? 'Before' : 'After', X, 82);
    ctx.fillStyle = '#eef0f5'; ctx.font = '600 34px ' + FONT;
    ctx.fillText(data.title, X, 128);
    ctx.textAlign = 'right';
    ctx.font = '500 26px ' + FONT; ctx.fillStyle = '#8b8f98';
    ctx.fillText(count === 1 ? 'finding' : 'findings', X + W, 128);
    const label = ctx.measureText(count === 1 ? 'finding' : 'findings').width;
    ctx.fillStyle = count === 0 && t > 6.5 ? '#4cc38a' : (count > 0 ? '#ff7a8a' : '#eef0f5');
    ctx.font = '600 84px ' + FONT;
    ctx.fillText(String(count), X + W - label - 16, 128);
    ctx.textAlign = 'left';

    // Screens: after on the left of the wipe, before on the right.
    ctx.save(); rounded(X, Y, W, H, 18); ctx.clip();
    ctx.drawImage(before, X, Y, W, H);
    if (wipe > 0) { ctx.save(); ctx.beginPath(); ctx.rect(X, Y, wipeX - X, H); ctx.clip(); ctx.drawImage(after, X, Y, W, H); ctx.restore(); }

    // Findings: pop in one by one; they live on the before screen only, so the wipe cuts them off.
    ctx.save(); ctx.beginPath(); ctx.rect(wipeX, Y, X + W - wipeX, H); ctx.clip();
    data.boxes.forEach((box, index) => {
        const appear = span(t, 0.6 + (3.6 * index) / Math.max(1, data.boxes.length), 0.95 + (3.6 * index) / Math.max(1, data.boxes.length));
        const x = X + box.x * S, y = Y + box.y * S, w = box.w * S, h = box.h * S;
        if (appear <= 0) return;
        const grow = 1 + (1 - appear) * 0.35;
        const cx = x + w / 2, cy = y + h / 2;
        rounded(cx - (w * grow) / 2 - 3, cy - (h * grow) / 2 - 3, w * grow + 6, h * grow + 6, 5);
        ctx.fillStyle = 'rgba(255, 92, 112, ' + 0.08 * appear + ')'; ctx.fill();
        ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(255, 92, 112, ' + appear + ')'; ctx.stroke();
    });
    ctx.restore();
    ctx.restore();
    if (wipe > 0 && wipe < 1) { ctx.fillStyle = '#eef0f5'; ctx.fillRect(wipeX - 1.5, Y - 10, 3, H + 20); }
    rounded(X, Y, W, H, 18); ctx.lineWidth = 1.5; ctx.strokeStyle = 'rgba(255,255,255,.12)'; ctx.stroke();

    // Footer: the command.
    ctx.fillStyle = '#eef0f5'; ctx.font = '500 30px ' + MONO;
    ctx.fillText('npx @enmera/ai-design-check', X, Y + H + 68);
    ctx.textAlign = 'right'; ctx.fillStyle = '#8b8f98'; ctx.font = '500 24px ' + FONT;
    ctx.fillText(data.rules + ' rules', X + W, Y + H + 66); ctx.textAlign = 'left';

    // End card.
    const end = span(t, 9.0, 9.8);
    if (end > 0) {
        ctx.fillStyle = 'rgba(14, 15, 18, ' + 0.9 * end + ')'; ctx.fillRect(0, 0, ${SIZE}, ${SIZE});
        ctx.globalAlpha = end; ctx.textAlign = 'center';
        ctx.fillStyle = '#eef0f5'; ctx.font = '600 120px ' + FONT;
        ctx.fillText(data.beforeCount + ' → ' + data.afterCount, ${SIZE / 2}, 470);
        ctx.fillStyle = '#8b8f98'; ctx.font = '500 34px ' + FONT;
        ctx.fillText('design findings in one pass', ${SIZE / 2}, 530);
        ctx.fillStyle = '#eef0f5'; ctx.font = '500 34px ' + MONO;
        ctx.fillText('npx @enmera/ai-design-check', ${SIZE / 2}, 660);
        ctx.fillStyle = '#8b8f98'; ctx.font = '400 26px ' + FONT;
        ctx.fillText('Rules, a checker and a fix skill for AI-built UI', ${SIZE / 2}, 712);
        ctx.textAlign = 'left';
    }
    ctx.globalAlpha = 1;
}
window.frame = async (t) => { await ready; render(t); return canvas.toDataURL('image/jpeg', 0.92); };
</script></body></html>`;

/**
 * @param {string} beforeInput file or URL
 * @param {string} afterInput file or URL
 * @param {{out?: string, still?: string, title?: string}} options
 */
export async function story(beforeInput, afterInput, { out = 'story.mp4', still, title, music } = {}) {
    if (music && !existsSync(resolve(music))) throw new Error(`Not found: ${music}`);
    const chrome = findChrome();
    if (!chrome) throw new Error('Chrome or Chromium not found; set CHROME_PATH');
    if (spawnSync('ffmpeg', ['-version']).status !== 0) throw new Error('ffmpeg not found on PATH');

    const work = mkdtempSync(join(tmpdir(), 'ai-design-check-story-'));
    const browser = await launch(chrome);
    try {
        const pages = [await source(beforeInput, work, 'before'), await source(afterInput, work, 'after')];
        const [beforeFindings, afterFindings] = pages.map((page) => check(page.dir, { include: [page.file] }));
        const shots = [];
        let boxes = [];
        for (const [index, page] of pages.entries()) {
            await browser.open(page.url, VIEW);
            if (index === 0) boxes = await browser.evaluate(BOXES([...new Set(beforeFindings.map((item) => item.value))], VIEW));
            const shot = await browser.send('Page.captureScreenshot', { format: 'png' });
            shots.push(`data:image/png;base64,${shot.data}`);
        }

        const stage = join(work, 'stage.html');
        const name = title ?? (await browser.evaluate('document.title')) ?? basename(beforeInput);
        writeFileSync(stage, STAGE({ before: shots[0], after: shots[1], boxes, beforeCount: beforeFindings.length, afterCount: afterFindings.length, title: name, rules: loadRules().rules.length }));
        await browser.open(pathToFileURL(stage).href, { width: SIZE, height: SIZE, settle: 100 });

        if (still) {
            const image = await browser.evaluate('frame(6.5)');
            writeFileSync(still, Buffer.from(image.split(',')[1], 'base64'));
        }
        // Music (optional) is cut to the video and faded out over the last second.
        const audio = music ? ['-i', resolve(music), '-map', '0:v', '-map', '1:a', '-af', `afade=t=out:st=${DURATION - 1}:d=1`, '-c:a', 'aac', '-b:a', '192k', '-shortest'] : [];
        const encoder = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', ...audio, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-movflags', '+faststart', resolve(out)], { stdio: ['pipe', 'inherit', 'inherit'] });
        const finished = new Promise((done, fail) => encoder.on('exit', (code) => (code === 0 ? done() : fail(new Error(`ffmpeg exited with ${code}`)))));
        for (let index = 0; index < FPS * DURATION; index++) {
            const image = await browser.evaluate(`frame(${index / FPS})`);
            if (!encoder.stdin.write(Buffer.from(image.split(',')[1], 'base64'))) await new Promise((done) => encoder.stdin.once('drain', done));
        }
        encoder.stdin.end();
        await finished;

        return { before: beforeFindings.length, after: afterFindings.length, marked: boxes.length, out: resolve(out) };
    } finally {
        await browser.close();
        rmSync(work, { recursive: true, force: true });
    }
}
