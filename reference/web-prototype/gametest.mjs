// node gametest.mjs steps.json  — steps: [{eval:"code"}, {wait:ms}, {shot:"file.png"}, {waitFor:"expr"}, {click:"#sel"}, {key:"KeyE"}]
import { chromium } from '/opt/npm-tools/node_modules/playwright/index.mjs';
import fs from 'fs';
const steps = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const W = +(process.argv[3] || 960), H = +(process.argv[4] || 540);
const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'] });
const p = await b.newPage({ viewport: { width: W, height: H } });
const logs = [];
p.on('console', (m) => { if (m.type() !== 'debug') logs.push(m.type() + ': ' + m.text()); });
p.on('pageerror', (e) => logs.push('PAGEERROR: ' + e.message + '\n' + (e.stack || '').slice(0, 800)));
await p.goto('http://127.0.0.1:8123/dist/local.html');
const t0 = Date.now();
for (const s of steps) {
  try {
    if (s.eval) { const r = await p.evaluate(s.eval); if (r !== undefined) console.log('eval>', JSON.stringify(r).slice(0, 400)); }
    if (s.wait) await p.waitForTimeout(s.wait);
    if (s.waitFor) await p.waitForFunction(s.waitFor, null, { timeout: s.timeout || 180000, polling: 500 });
    if (s.click) await p.click(s.click);
    if (s.key) await p.keyboard.press(s.key);
    if (s.shot) { await p.screenshot({ path: s.shot, timeout: 180000, animations: 'allow', caret: 'initial' }); console.log('shot', s.shot, ((Date.now() - t0) / 1000).toFixed(0) + 's'); }
  } catch (e) { console.log('STEP FAIL', JSON.stringify(s).slice(0, 200), e.message.slice(0, 300)); }
}
for (const l of logs.slice(0, 40)) console.log(l.slice(0, 900));
await b.close();
