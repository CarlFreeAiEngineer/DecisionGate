// Serve a staged browser build cross-origin isolated, run the 87 fixtures, report timing and the answers.
import { chromium, firefox, webkit } from '../../web/node_modules/playwright/index.mjs';
import { createServer } from 'node:http';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
const [dir, browserName, out] = process.argv.slice(2);
const fixtures = JSON.parse(await readFile(new URL('../../web/tests/fixtures.json', import.meta.url))).filter(f => 'pYes' in f);
const types = { '.js': 'text/javascript', '.mjs': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.html': 'text/html' };
const server = createServer(async (req, res) => {
  try { const file = path.join(dir, decodeURIComponent(new URL(req.url, 'http://x').pathname).replace(/^\//, '') || 'index.html');
    const body = await readFile(file);
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] ?? 'application/octet-stream', 'Cross-Origin-Opener-Policy': 'same-origin', 'Cross-Origin-Embedder-Policy': 'require-corp' }); res.end(body);
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const browser = await { chromium, firefox, webkit }[browserName].launch();
const page = await browser.newPage();
page.on('pageerror', e => console.error(e));
await page.goto(`http://127.0.0.1:${server.address().port}/`);
const result = await page.evaluate(async fixtures => {
  const dg = await import('./index.js');
  await dg.isYesP(fixtures[0].content, fixtures[0].question, { criteria: fixtures[0].criteria });
  const ps = [], ms = [];
  for (const f of fixtures) { const t = performance.now(); ps.push(await dg.isYesP(f.content, f.question, { criteria: f.criteria })); ms.push(performance.now() - t); }
  ms.sort((a, b) => a - b);
  return { isolated: self.crossOriginIsolated, p50: ms[Math.floor(ms.length / 2)], ps };
}, fixtures);
await writeFile(out, JSON.stringify(result));
console.log(browserName, 'isolated', result.isolated, 'p50', Math.round(result.p50), 'ms');
await browser.close(); server.close();
