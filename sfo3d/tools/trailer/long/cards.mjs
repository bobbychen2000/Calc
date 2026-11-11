import { createRequire } from 'module'; const require = createRequire(import.meta.url); const { chromium } = require('playwright');
const OUT = process.argv[2];
const css = `html,body{margin:0;width:1920px;height:1080px;background:transparent;font-family:Inter,'Inter Display',sans-serif;color:#fff;-webkit-font-smoothing:antialiased}
.ch{position:absolute;left:96px;bottom:150px;text-shadow:0 2px 18px rgba(0,0,0,.65)} .n{font-size:22px;letter-spacing:6px;color:#ffb547;font-weight:600} .t{font-size:58px;font-weight:700;letter-spacing:-1px;margin-top:6px}
.bar{width:64px;height:4px;background:#ffb547;margin-bottom:18px}`;
const chapters = [['01', 'The airport'], ['02', 'Live arrivals'], ['03', 'On the ground'], ['04', 'Departures'], ['05', 'Built from real data'], ['06', 'Light & weather'], ['07', 'Night']];
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
for (const [n, t] of chapters) { await p.setContent(`<style>${css}</style><div class="ch"><div class="bar"></div><div class="n">${n}</div><div class="t">${t}</div></div>`); await p.waitForTimeout(250); await p.screenshot({ path: `${OUT}/ch${+n}.png`, omitBackground: true }); }
await b.close(); console.log('cards ok');
