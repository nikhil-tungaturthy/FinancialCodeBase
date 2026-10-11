// Usage: node snap.mjs <url> <out.png> [width=1440] [height=900] [--full] [--click=<selector>] [--wait=<ms>]
// Captures a screenshot and prints console errors/warnings and failed network requests as JSON.
// Dev utility for visual QA. Example: node apps/web/scripts/snapshot.mjs http://localhost:5173/payments shots/payments.png 1440 900 --full
import { chromium } from '@playwright/test';

const [url, out, w = '1440', h = '900', ...rest] = process.argv.slice(2);
if (!url || !out) { console.error('usage: node snap.mjs <url> <out.png> [w] [h] [--full] [--click=sel] [--wait=ms]'); process.exit(2); }
const full = rest.includes('--full');
const click = (rest.find(a => a.startsWith('--click=')) || '').slice(8);
const wait = Number((rest.find(a => a.startsWith('--wait=')) || '--wait=1200').slice(7));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: Number(w), height: Number(h) } });
const consoleIssues = [];
const failedRequests = [];
page.on('console', m => { if (['error', 'warning'].includes(m.type())) consoleIssues.push({ type: m.type(), text: m.text().slice(0, 300) }); });
page.on('pageerror', e => consoleIssues.push({ type: 'pageerror', text: String(e).slice(0, 300) }));
page.on('requestfailed', r => failedRequests.push({ url: r.url(), failure: r.failure()?.errorText }));
page.on('response', r => { if (r.status() >= 400) failedRequests.push({ url: r.url(), status: r.status() }); });
await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
if (click) { await page.click(click); await page.waitForLoadState('networkidle'); }
await page.waitForTimeout(wait);
const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
await page.screenshot({ path: out, fullPage: full });
await browser.close();
console.log(JSON.stringify({ url, out, horizontalOverflow: overflow, consoleIssues, failedRequests }, null, 2));
