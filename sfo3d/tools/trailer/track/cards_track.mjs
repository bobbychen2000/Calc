// Overlay cards (1920x1080, transparent PNG) for the tracking films: per-shot phase label + time-lapse badge, film title,
// end card with data credits. Same type and colours as the 6-min video's chapter cards (tools/trailer/long/cards.mjs).
import { createRequire } from 'module'; const require = createRequire(import.meta.url); const { chromium } = require('playwright');
import fs from 'fs';
const [SHOTS, OUT] = process.argv.slice(2);
const S = JSON.parse(fs.readFileSync(SHOTS, 'utf8'));
const css = `html,body{margin:0;width:1920px;height:1080px;background:transparent;font-family:Inter,'Inter Display',sans-serif;color:#fff;-webkit-font-smoothing:antialiased}
.sh{text-shadow:0 2px 16px rgba(0,0,0,.6),0 0 2px rgba(0,0,0,.5)}
.lab{position:absolute;left:84px;bottom:78px} .lab .p{font-size:30px;font-weight:650;letter-spacing:.2px} .lab .bar{width:46px;height:4px;background:#ffb547;margin-bottom:12px}
.badge{position:absolute;right:84px;bottom:82px;font-size:20px;font-weight:650;letter-spacing:3px;padding:8px 14px;border-radius:6px;background:rgba(0,0,0,.38);color:#ffd28a}
.badge.rt{color:#cfe6ff}
.title{position:absolute;left:0;top:0;width:1500px;height:560px;box-sizing:border-box;padding:96px 0 0 96px;background:radial-gradient(ellipse 100% 100% at 0% 0%,rgba(0,0,0,.46) 0%,rgba(0,0,0,.30) 38%,rgba(0,0,0,.10) 70%,rgba(0,0,0,0) 100%)} .title .k{font-size:22px;letter-spacing:6px;color:#ffb547;font-weight:600} .title .t{font-size:64px;font-weight:750;letter-spacing:-1px;margin-top:8px}
.title .s{font-size:28px;font-weight:500;margin-top:10px;opacity:.95} .title .m{font-size:23px;font-weight:550;margin-top:14px;opacity:.95}
.end{position:absolute;left:0;top:0;width:1920px;height:1080px;background:#06080c;display:flex;flex-direction:column;align-items:center;justify-content:center}
.end .t{font-size:58px;font-weight:750} .end .s{font-size:24px;margin-top:14px;opacity:.85} .end .c{font-size:17px;margin-top:46px;opacity:.6;max-width:1500px;text-align:center;line-height:1.6}`;
const LAB = { approach: 'Approach over San Francisco Bay', final: 'Final approach, runway 28R', touchdown: 'Landing, runway 28R', rollout: 'Rollout',
  taxi: 'Taxi', gate: 'Arriving at gate G7', dock: 'Jet bridge docking', push: 'Pushback', pushstart: 'Bridges retract, pushback', lineup: 'Lining up, runway 28R', takeoff: 'Take-off, runway 28R', climb: 'Climb-out',
  'gate-dep': 'At gate G13', 'taxi-dep': 'Taxi to runway 28R' };
const FILM = {
  arr: { k: 'ARRIVAL', t: 'UAL900 · London → San Francisco', s: 'Boeing 787-9 · N71112 · United Airlines', m: 'Followed from the bay to the gate · recorded ADS-B, 8 Nov 2026' },
  dep: { k: 'DEPARTURE', t: 'UAL857 · San Francisco → Shanghai', s: 'Boeing 777-300ER · N2639U · United Airlines', m: 'Followed from pushback to climb-out · recorded ADS-B, 8 Nov 2026' } };
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
const shot = async (html, f) => { await p.setContent(`<style>${css}</style>${html}`); await p.waitForTimeout(150); await p.screenshot({ path: `${OUT}/${f}`, omitBackground: true }); };
for (const s of S) {
  const key = s.film === 'dep' && (s.cap === 'gate' || s.cap === 'taxi') ? s.cap + '-dep' : s.cap;
  const sp = s.speed === 1 ? '<div class="badge rt sh">REAL TIME</div>' : `<div class="badge sh">${String(s.speed).replace('.5', '½')}× TIME-LAPSE</div>`;
  await shot(`<div class="lab sh"><div class="bar"></div><div class="p">${LAB[key]}</div></div>${sp}`, `lab_${s.id}.png`);
}
for (const [f, v] of Object.entries(FILM)) await shot(`<div class="title sh"><div class="k">${v.k}</div><div class="t">${v.t}</div><div class="s">${v.s}</div><div class="m">${v.m}</div></div>`, `title_${f}.png`);
await shot(`<div class="end"><div class="t">SFO Live 3D</div><div class="s">Real ADS-B traffic, physically simulated and rendered in the browser</div>
<div class="c">Aircraft data: ADSB.lol (ODbL 1.0) and adsb.fi open data · Routes: Virtual Radar Server standing data (CC0) · Weather: NOAA/NWS AWC<br>
Traffic recorded 8 Nov 2026, 12:46–13:26 PST; lighting set to late afternoon · Time-lapse segments are marked on screen</div></div>`, 'end.png');
await b.close(); console.log('cards ok', S.length);
