// Environment -> WebGL2 renderer glue (new for hwd3d, fork map 2.6): the work of sfo3d/js/live/app.js applyEnv() and
// setClouds() @ a967f9b (lines 181-258), moved out of the app shell so that P4 does not re-implement the fog, cloud and
// exposure logic. Kept from sfo3d (verbatim rules): the main cloud deck (lowest BKN/OVC <= 5,000 ft at its METAR base,
// else the lowest reported layer, layers < 100 ft are fog, not cloud), visibility 10SM / P6SM as lower bounds, the fog
// density from the EnvState surface extinction and the fog / sub-cloud top, the de-summed own cloud cover, the cloud
// drift = METAR surface wind, the night ambient floors, the night factor and the keyed exposure ramp, the 3-plane low
// cloud slab under a BKN/OVC deck below 5,000 ft. Changed: ground y = the HWD field (world.site / geo.js FIELD_ELEV_Y,
// not SFO's 3 m); no ground re-bake (the HWD ground shader has no sun-dependent bake); no water uniforms (no Bay water
// modelled); the windsock is turned by the METAR wind (world.setWind). Dropped: the SFO aircraft-light environment hook
// (P3 calls js/env/aircraft_lights.js setLightEnv itself) and the SFO airfield lighting.
//
//   applyEnvToRenderer(R, world, E, { quality, force = false }) -> { exposure, nightF, changed }
import { Mesh } from '../gl.js';
import { CLOUD_VS, CLOUD_FS } from '../shaders/env.js';
import { metarSummary } from './wx/metar.js';
import { FIELD_ELEV_Y, FT } from '../geo.js';
import { towerOpenAt } from '../live/lights.js';

const DEG = Math.PI / 180;
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const COVER = { FEW: 0.14, SCT: 0.4, BKN: 0.68, OVC: 0.95 };

export function applyEnvToRenderer(R, world, E, { quality = 'high', force = false } = {}) {
  const st = world._env || (world._env = { key: '', cloudItems: [], exposure: 0.45, nightF: 0 });
  const M = E.wx && E.wx.decoded ? metarSummary(E.wx.decoded) : null;
  R.envState = E;
  const sp = { az: E.sun.az, el: E.sun.el }, elN = E.sun.elTrue;
  const key = sp.az.toFixed(1) + ':' + sp.el.toFixed(1) + ':' + (M ? M.raw : '') + ':' + E.atm.sigmaSurface.toPrecision(2);
  if (!force && key === st.key) return { exposure: st.exposure, nightF: st.nightF, changed: false };
  st.key = key;
  const GY = world.site && world.site.groundY ? FIELD_ELEV_Y : FIELD_ELEV_Y;   // fog reference height: the field elevation
  const layers = M ? M.clouds.slice().sort((a, b) => a.ft - b.ft) : [];
  const cl = layers.filter(c => c.ft >= 100 && E.clouds.some(l => l.cover === c.cover && l.baseFt === c.ft));
  const main = cl.find(c => (c.cover === 'BKN' || c.cover === 'OVC') && c.ft <= 5000) || cl[0];
  const wdir = ((M && M.windDir) ?? 290) * DEG, wms = ((M && M.windKt) ?? 8) * 0.5144;
  const windTo = [-Math.sin(wdir), 0, Math.cos(wdir)];
  const lowSlab = !!(main && main.ft < 5000 && (main.cover === 'BKN' || main.cover === 'OVC'));
  const surf = E.atm.slabs.filter(sl => !/^(cloud|obscuration)/.test(sl.kind || ''));
  const fogTop = Math.max(5, (surf.length ? Math.max(...surf.map(sl => sl.y1)) : GY + 914) - GY);
  const ownOf = (c) => { const L = c && E.clouds.find(l => l.cover === c.cover && l.baseFt === c.ft); return L ? L.own : c ? COVER[c.cover] : 0; };
  const baseOf = (c) => { const L = c && E.clouds.find(l => l.cover === c.cover && l.baseFt === c.ft); return L ? L.base : c ? GY + c.ft * FT : 1500; };
  const env = {
    sunDir: E.sun.dir, mie: 21e-6, sunI: 20,
    fog: [E.atm.sigmaSurface * Math.exp(GY / fogTop), 1 / fogTop, 1.0, 1.0],
    cloud: [ownOf(main), main ? baseOf(main) : 1500, lowSlab ? 4200 : 14000, 0.5],
    cloudWind: [windTo[0] * wms, windTo[2] * wms], cloudTex: world.textures.clouds, noiseTex: world.textures.noise, refPos: [0, GY + 45, 0],
    slab: lowSlab, wind: [windTo[0] * wms, windTo[2] * wms],
  };
  R.setupSky(env);
  // night: a faint moon / city-glow ambient floor so silhouettes stay readable (sfo3d values)
  const nf = sstep(3, -9, elN);
  const floorUp = [0.010, 0.012, 0.018].map(v => v * nf), floorHz = [0.012, 0.011, 0.012].map(v => v * nf);
  R.light.skyUp = R.light.skyUp.map((v, i) => Math.max(v, floorUp[i])); R.light.skyHorizon = R.light.skyHorizon.map((v, i) => Math.max(v, floorHz[i]));
  R.light.ground = R.light.ground.map((v, i) => Math.max(v, floorHz[i] * 0.5));
  const nightF = sstep(6, -4, elN);
  const dark = sstep(2, -10, elN);
  const exposure = (0.45 + 0.25 * (env.cloud[0] > 0.6 ? 1 : 0) * (1 - dark)) * (1 - dark) + 2.4 * dark + sstep(8, 2, elN) * (1 - dark) * 0.25;
  R.extraCommon = Object.assign(R.extraCommon || {}, { uNight: nightF });
  setClouds(R, world, st, lowSlab ? { H: env.cloud[1], cov: env.cloud[0] } : null);
  if (world.setWind) world.setWind(E.wind && E.wind.fromTrue != null ? E.wind.fromTrue : null, E.wind ? E.wind.speed : 0, E.wind ? E.wind.sockExt : null);
  world.nightF = nightF; world.sunEl = elN;
  world.lightEnv = { sunEl: elN, nightW: E.photocell ? E.photocell.asosNightW : (elN < 0 ? 1 : 0), towerOpen: towerOpenAt(E.tEnv), sigma: E.atm.sigmaSurface, tEnv: E.tEnv };
  st.exposure = exposure; st.nightF = nightF;
  return { exposure, nightF, changed: true, metar: M };
}

function setClouds(R, world, st, slab) {
  world.items = world.items.filter(it => !st.cloudItems.includes(it)); st.cloudItems = [];
  if (!slab) return;
  if (!R.progs.cloud) R.addProgram('cloud', CLOUD_VS, CLOUD_FS);
  if (!setClouds.plane) {
    const N = 64, pos = [], idx = [];
    for (let j = 0; j <= N; j++) for (let i = 0; i <= N; i++) { const u = i / N * 2 - 1, v = j / N * 2 - 1; const f = (x) => Math.sign(x) * Math.pow(Math.abs(x), 2.2); pos.push(f(u), 0, f(v)); }
    for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) { const a = j * (N + 1) + i; idx.push(a, a + N + 1, a + 1, a + 1, a + N + 1, a + N + 2); }
    setClouds.plane = new Mesh({ pos: new Float32Array(pos), idx: new Uint32Array(idx) });
  }
  for (let k = 0; k < 3; k++) {
    const L = { H: slab.H + k * 32, cov: slab.cov, k: k / 2, off: 0, op: 0.55 };
    const it = { mesh: setClouds.plane, prog: 'cloud', blend: 'alpha', bothPasses: true, bbox: null, castShadow: false, noCull: true, sortKey: (cp) => Math.abs(cp[1] - L.H),
      uniforms: () => ({ uH: L.H, uExtent: 40000, uLayer: [L.cov, L.k, L.off, L.op], uCamDir: R.curCam.dir, uRange: R.curRange }) };
    st.cloudItems.push(it); world.items.push(it);
  }
}
