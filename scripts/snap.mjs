// Screenshots at chosen scroll positions, with console/network errors.
//   node snap.mjs <base-url> <page> <w> <h> <out-prefix> [reduced|-] pos...
// pos: pixels, or "selector@f" = fraction f of that pinned section's scroll travel.
// playwright-core resolves from the folder you run this in, or any parent of it.
import path from 'node:path';
import { createRequire } from 'node:module';
const { chromium } = createRequire(path.join(process.cwd(), 'noop.js'))('playwright-core');
const CHROME = process.env.CHROME || {
  win32: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  darwin: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
}[process.platform] || '/usr/bin/google-chrome';
const [base, page = '', w = '1440', h = '900', out = 'lab/snap', reduced = '-', ...pos] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: CHROME });
const ctx = await b.newContext({ viewport: { width: +w, height: +h }, reducedMotion: reduced === 'reduced' ? 'reduce' : 'no-preference' });
const p = await ctx.newPage(); const errs = [];
p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
p.on('pageerror', (e) => errs.push(e.message));
p.on('requestfailed', (r) => errs.push('FAILED ' + r.url()));
await p.goto(base.replace(/\/$/, '') + '/' + page, { waitUntil: 'networkidle' });
await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(500);
let i = 0;
for (const s of pos.length ? pos : ['0']) {
  const y = await p.evaluate((s) => {
    if (!s.includes('@')) return parseFloat(s);
    const [sel, f] = s.split('@'); const r = document.querySelector(sel).getBoundingClientRect();
    return r.top + scrollY + Math.max(r.height - innerHeight, 0) * parseFloat(f);
  }, s);
  await p.evaluate((y) => scrollTo(0, y), y); await p.waitForTimeout(900);
  await p.screenshot({ path: `${out}-${String(i++).padStart(2, '0')}.jpg`, quality: 70, type: 'jpeg' });
}
console.log(errs.length ? errs.join('\n') : 'no console errors');
await b.close();
