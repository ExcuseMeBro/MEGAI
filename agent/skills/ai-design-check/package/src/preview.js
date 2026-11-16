import { contrastReport } from './system.js';

/**
 * One HTML page that shows a generated design system in both themes side by side: the type roles in their fonts,
 * every color with its contrast, and the components drawn from the component map (buttons, field, badges, card,
 * table, chart). Self-contained apart from the Google Fonts stylesheet.
 */

const kebab = (name) => name.replace(/([A-Z])/g, '-$1').toLowerCase();
const escape = (text) => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function variables(colors) {
    return Object.entries(colors).flatMap(([name, value]) => (Array.isArray(value) ? value.map((item, index) => `--c-${kebab(name)}${index + 1}: ${item};`) : [`--c-${kebab(name)}: ${value};`])).join(' ');
}

function typeRows(system) {
    return Object.entries(system.type).map(([role, item]) => {
        const sample = role === 'stat' ? '₺21.545,00' : role === 'caption' ? 'Updated 2 minutes ago' : role === 'label' ? 'Save changes' : role === 'body' ? 'Your balance went up this week because two invoices were paid.' : 'Monthly overview';
        const style = `font-family: var(--font-${role === 'stat' ? 'numeric' : item.font === system.fonts.display && item.font !== system.fonts.ui ? 'display' : 'ui'}); font-size: ${item.size}px; line-height: ${item.lineHeight}; letter-spacing: ${item.letterSpacing}em; font-weight: ${item.weight};${item.tabular ? ' font-variant-numeric: tabular-nums;' : ''}`;

        return `<div class="type-row"><div class="meta"><b>${role}</b><span>${item.size}/${item.lineHeight} · ${item.weight} · ${escape(item.font)}</span><span>iOS ${item.ios} · Android ${item.android}</span></div><div style="${style}">${sample}</div></div>`;
    }).join('\n');
}

function swatches(colors) {
    const names = Object.keys(colors).filter((name) => !Array.isArray(colors[name]));

    return names.map((name) => `<div class="swatch"><i style="background: var(--c-${kebab(name)})"></i><span>${name}</span><code>${colors[name]}</code></div>`).join('');
}

function pane(system, mode) {
    const colors = system.color[mode];
    const report = contrastReport(colors).map((item) => `<tr><td>${item.fg}</td><td>${item.bg}</td><td class="num">${item.ratio.toFixed(2)}</td></tr>`).join('');
    const bars = [62, 48, 80, 54, 92, 70].map((value, index) => `<i style="height: ${value}%; background: var(--c-${index === 4 ? 'chart-highlight' : 'chart-muted'})"></i>`).join('');

    return `<section class="pane" style="${variables(colors)}" data-mode="${mode}">
<h2>${mode === 'light' ? 'Light' : 'Dark'}</h2>
<div class="card">
    <div class="card-head"><div><div class="card-title">Revenue this month</div><div class="card-meta">Updated 2 minutes ago</div></div><span class="badge-accent">New</span></div>
    <div class="stat">$48,210</div>
    <div class="row"><span class="positive">+12.4%</span><span class="negative">−3 overdue</span><span class="badge">Draft</span></div>
    <div class="chart">${bars}</div>
</div>
<div class="row">
    <button class="primary">Save changes</button><button class="secondary">Cancel</button><button class="ghost">Export</button>
</div>
<label class="field">Workspace name<input placeholder="Acme Inc."></label>
<table><thead><tr><th>Invoice</th><th>Status</th><th class="num">Amount</th></tr></thead>
<tbody><tr><td>INV-2041</td><td><span class="positive">Paid</span></td><td class="num">$1,200.00</td></tr>
<tr><td>INV-2042</td><td><span class="warning">Due soon</span></td><td class="num">$860.50</td></tr></tbody></table>
<p class="body-text">Text on the page reads at full contrast. <a href="#">View all invoices</a></p>
<button class="danger">Delete workspace</button>
<h3>Colors</h3>
<div class="swatches">${swatches(colors)}</div>
<h3>Contrast (WCAG 2)</h3>
<table class="contrast"><thead><tr><th>Text</th><th>On</th><th class="num">Ratio</th></tr></thead><tbody>${report}</tbody></table>
</section>`;
}

export function preview(system, fontsCss) {
    const t = system.type;
    const radius = system.shape.radius;

    return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Design system · ${escape(system.character)} · ${escape(system.kind)}</title>
<style>
${fontsCss}
* { box-sizing: border-box; }
body { margin: 0; background: #f4f4f5; color: #18181b; font-family: var(--font-ui); }
header { padding: 32px 24px 8px; max-width: 1200px; margin: 0 auto; }
header h1 { font-family: var(--font-display); font-size: 28px; font-weight: 600; letter-spacing: -0.02em; margin: 0 0 8px; }
header p { margin: 0; color: #52525b; font-size: 14px; line-height: 1.5; }
.types { max-width: 1200px; margin: 24px auto; padding: 0 24px; }
.type-row { display: grid; grid-template-columns: 240px 1fr; gap: 24px; padding: 16px 0; border-top: 1px solid #e4e4e7; align-items: baseline; }
.meta { display: flex; flex-direction: column; gap: 2px; font-size: 12px; color: #71717a; }
.meta b { color: #18181b; font-size: 13px; font-weight: 600; }
.panes { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; max-width: 1200px; margin: 0 auto 48px; padding: 0 24px; }
.pane { background: var(--c-bg); color: var(--c-text); border-radius: ${radius.xl}px; padding: 24px; display: flex; flex-direction: column; gap: 16px; border: 1px solid var(--c-border); }
.pane h2 { margin: 0; font-size: ${t.heading.size}px; font-weight: ${t.heading.weight}; }
.pane h3 { margin: 8px 0 0; font-size: ${t.title.size}px; font-weight: ${t.title.weight}; }
.card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: ${radius.lg}px; padding: ${system.shape.cardPadding}px; display: flex; flex-direction: column; gap: 12px; }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.card-title { font-size: ${t.title.size}px; font-weight: ${t.title.weight}; line-height: ${t.title.lineHeight}; }
.card-meta { font-size: ${t.caption.size}px; color: var(--c-text-tertiary); }
.stat { font-family: var(--font-numeric); font-size: ${t.stat.size}px; font-weight: ${t.stat.weight}; letter-spacing: ${t.stat.letterSpacing}em; font-variant-numeric: tabular-nums; }
.row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.badge, .badge-accent, .positive, .negative, .warning { font-size: ${t.caption.size}px; font-weight: 500; padding: 2px 8px; border-radius: ${radius.full}px; }
.badge { background: var(--c-muted); color: var(--c-text-secondary); }
.badge-accent { background: var(--c-accent-soft); color: var(--c-accent-text); }
.positive { background: var(--c-success-soft); color: var(--c-success-text); }
.negative { background: var(--c-danger-soft); color: var(--c-danger-text); }
.warning { background: var(--c-warning-soft); color: var(--c-warning-text); }
.chart { display: flex; align-items: flex-end; gap: 8px; height: 72px; border-bottom: 1px solid var(--c-chart-grid); }
.chart i { flex: 1; border-radius: ${radius.sm}px ${radius.sm}px 0 0; }
button { font: inherit; font-size: ${t.label.size}px; font-weight: ${t.label.weight}; height: ${system.shape.controlHeight.md}px; padding: 0 16px; border-radius: ${radius.md}px; border: 1px solid transparent; cursor: pointer; }
.primary { background: var(--c-accent); color: var(--c-accent-ink); }
.primary:hover { background: var(--c-accent-hover); }
.secondary { background: var(--c-surface); color: var(--c-text); border-color: var(--c-border-strong); }
.ghost { background: transparent; color: var(--c-text-secondary); }
.danger { background: var(--c-danger); color: var(--c-danger-ink); align-self: flex-start; }
.field { display: flex; flex-direction: column; gap: 6px; font-size: ${t.label.size}px; font-weight: ${t.label.weight}; }
.field input { font: inherit; font-weight: 400; font-size: ${t.body.size}px; height: ${system.shape.controlHeight.md}px; padding: 0 12px; border-radius: ${radius.md}px; border: 1px solid var(--c-border-strong); background: var(--c-surface); color: var(--c-text); }
.field input::placeholder { color: var(--c-text-tertiary); }
.field input:focus { outline: 2px solid var(--c-focus); outline-offset: 1px; }
table { width: 100%; border-collapse: collapse; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: ${radius.md}px; overflow: hidden; font-size: ${t.body.size > 15 ? 15 : t.body.size}px; }
th { text-align: left; font-size: ${t.label.size}px; font-weight: ${t.label.weight}; color: var(--c-text-tertiary); padding: 8px 12px; }
td { padding: 10px 12px; border-top: 1px solid var(--c-border); }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.body-text { margin: 0; font-size: ${t.body.size}px; line-height: ${t.body.lineHeight}; }
a { color: var(--c-accent-text); }
.swatches { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.swatch { display: grid; grid-template-columns: 28px 1fr; grid-template-rows: auto auto; column-gap: 8px; font-size: 12px; }
.swatch i { grid-row: span 2; width: 28px; height: 28px; border-radius: ${radius.sm}px; border: 1px solid var(--c-border); }
.swatch code { color: var(--c-text-tertiary); font-family: var(--font-mono); font-size: 11px; }
.contrast { font-size: 12px; }
@media (max-width: 860px) { .panes { grid-template-columns: 1fr; } .type-row { grid-template-columns: 1fr; gap: 6px; } }
</style>
</head>
<body>
<header>
<h1>${escape(system.character[0].toUpperCase() + system.character.slice(1))} ${escape(system.kind)} system</h1>
<p>Brand ${escape(system.brand)} · UI ${escape(system.fonts.ui)} · display ${escape(system.fonts.display)} · numbers ${escape(system.fonts.numeric)} · code ${escape(system.fonts.mono)}.
Every text color is checked against its background and moved until it passes WCAG 2.</p>
</header>
<div class="types">
${typeRows(system)}
</div>
<div class="panes">
${pane(system, 'light')}
${pane(system, 'dark')}
</div>
</body>
</html>
`;
}
