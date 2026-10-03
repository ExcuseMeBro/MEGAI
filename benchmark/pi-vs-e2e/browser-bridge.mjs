import http from 'node:http';
import { chromium } from 'playwright';

export async function startBridge(appUrl) {
  let browser;
  let page;
  const operations = [];
  const errors = [];
  const server = http.createServer(async (req, res) => {
    try {
      let body = '';
      for await (const chunk of req) body += chunk;
      const commands = JSON.parse(body);
      if (!Array.isArray(commands)) throw new Error('Expected array');
      for (const command of commands) {
        operations.push(command);
        if (command.op === 'open') {
          if (browser) throw new Error('Already opened');
          browser = await chromium.launch({ headless: true });
          page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
          page.on('pageerror', (e) => errors.push(e.message));
          await page.goto(appUrl + '/login');
        } else if (command.op === 'fill') {
          await page.getByLabel(command.label, { exact: true }).fill(command.value);
        } else if (command.op === 'click') {
          await page.getByRole(command.role ?? 'button', { name: command.name, exact: true }).click();
          await page.waitForLoadState();
        } else if (command.op === 'snapshot') {
          if (!page) throw new Error('Open first');
        } else if (command.op === 'assert') {
          const locator = page.getByRole(command.role, { name: command.name, exact: true });
          await locator.waitFor({ state: 'visible' });
        } else throw new Error('Unknown operation');
      }
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ url: page.url(), snapshot: await page.locator('body').ariaSnapshot(), errors }));
    } catch (e) {
      res.writeHead(400, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ error: e.message }));
    }
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  return {
    url: 'http://127.0.0.1:' + server.address().port, operations, errors,
    close: async () => { if (browser) await browser.close(); await new Promise((resolve) => server.close(resolve)); },
  };
}
