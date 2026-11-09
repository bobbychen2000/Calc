import { createRequire } from 'module'; const require = createRequire(import.meta.url); const { chromium } = require('playwright');
const OUT = process.argv[2];
const css = `html,body{margin:0;width:1920px;height:1080px;background:transparent;font-family:Inter,'Inter Display',sans-serif;color:#fff;-webkit-font-smoothing:antialiased}
.t{position:absolute;left:0;right:0;text-align:center} .sfo{color:#ffb547}`;
const cards = {
  title: `<div class="t" style="top:430px;font-size:132px;font-weight:700;letter-spacing:-2px;text-shadow:0 4px 40px rgba(0,0,0,.55)"><span class="sfo">SFO</span> Live 3D</div>
          <div class="t" style="top:600px;font-size:38px;font-weight:400;letter-spacing:6px;text-transform:uppercase;opacity:.92;text-shadow:0 2px 18px rgba(0,0,0,.7)">San Francisco International · in real time</div>`,
  credit: `<div class="t" style="top:1040px;font-size:17px;font-weight:400;opacity:.78;text-shadow:0 1px 4px rgba(0,0,0,.9)">Aircraft data: ADSB.lol (ODbL) · adsb.fi open data · © OpenStreetMap contributors (ODbL) · SFO Museum · FAA · USDA NAIP · Models: FlightGear / FlightAirMap (GPL)</div>`,
  end: `<div style="position:absolute;inset:0;background:#05080d"></div>
        <div class="t" style="top:330px;font-size:120px;font-weight:700;letter-spacing:-2px"><span class="sfo">SFO</span> Live 3D</div>
        <div class="t" style="top:490px;font-size:36px;font-weight:400;letter-spacing:5px;text-transform:uppercase;opacity:.9">Live ADS-B · real weather · in your browser</div>
        <div class="t" style="top:700px;font-size:20px;line-height:34px;opacity:.72;padding:0 220px">Traffic: real ADS-B recorded at SFO on 8 Nov 2026, 12:46–1:26 PM PT, lit at sunset and at night with the app's time control.<br>
        Aircraft data: ADSB.lol — contains information from ADSB.lol, made available under the ODbL · adsb.fi open data (personal, non-commercial use)<br>
        Stands, taxiways and aprons © OpenStreetMap contributors (ODbL) · Airport geometry: SFO Museum (CDLA-Permissive-1.0) · FAA NASR / AL-375 · USDA NAIP (public domain)<br>
        Weather: NOAA/NWS Aviation Weather Center · Aircraft models: FlightGear / FlightAirMap (GPL v2) · Voice: Kokoro-82M (Apache-2.0)</div>`,
};
const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
for (const [k, html] of Object.entries(cards)) { await p.setContent(`<style>${css}</style>${html}`); await p.waitForTimeout(300); await p.screenshot({ path: `${OUT}/${k}.png`, omitBackground: k !== 'end' }); console.log(k); }
await b.close();
