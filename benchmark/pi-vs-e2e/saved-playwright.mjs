import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto(process.env.BENCH_APP_URL + '/login');
  await page.getByLabel('Email', { exact: true }).fill('bench@example.test');
  await page.getByLabel('Password', { exact: true }).fill('demo-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('link', { name: 'New project', exact: true }).click();
  await page.getByLabel('Project name', { exact: true }).fill('Bench Project');
  await page.getByLabel('Description', { exact: true }).fill('Token and speed benchmark');
  await page.getByRole('button', { name: 'Create project', exact: true }).click();
  assert.equal(await page.getByRole('status').textContent(), 'Project created');
  assert.equal(await page.getByRole('heading', { level: 1 }).textContent(), 'Bench Project');
  console.log('PASS: signed in, project created, success status and project heading verified');
} finally { await browser.close(); }
