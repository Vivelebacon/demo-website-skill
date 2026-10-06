// Full-page captures after walking each page (fires every entrance), plus horizontal overflow.
//   node full.mjs <base-url> <w> <h> <out-prefix> page...
// Fixed headers land mid-page in full-page captures: that is the capture, not the site.
// playwright-core resolves from the folder you run this in, or any parent of it.
import path from 'node:path';
import { createRequire } from 'node:module';
const { chromium } = createRequire(path.join(process.cwd(), 'noop.js'))('playwright-core');
const CHROME = process.env.CHROME || {
  win32: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  darwin: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
}[process.platform] || '/usr/bin/google-chrome';
const [base, w, h, prefix, ...pages] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: CHROME });
const ctx = await b.newContext({ viewport: { width: +w, height: +h } });
for (const pg of pages.length ? pages : ['']) {
  const p = await ctx.newPage(); const errs = [];
  p.on('pageerror', (e) => errs.push(e.message)); p.on('requestfailed', (r) => errs.push('FAILED ' + r.url()));
  p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(base.replace(/\/$/, '') + '/' + pg, { waitUntil: 'networkidle' });
  await p.evaluate(async () => { await document.fonts.ready; for (let y = 0; y < document.body.scrollHeight; y += 300) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } });
  await p.waitForTimeout(1200);
  const overflow = await p.evaluate(() => document.documentElement.scrollWidth - innerWidth);
  await p.screenshot({ path: `${prefix}-${pg.replace(/\.html$/, '').replace(/\W+/g, '-') || 'home'}.jpg`, fullPage: true, quality: 60, type: 'jpeg' });
  console.log(pg || '/', 'overflow', overflow, errs.join(' | ') || 'ok');
  await p.close();
}
await b.close();
