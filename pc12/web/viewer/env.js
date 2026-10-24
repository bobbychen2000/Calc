// The day the parked aircraft sits in: outside air temperature, field elevation, the altimeter setting (QNH), the wind,
// the fuel on board and ground power -- the viewer's Environment knobs (Animate tab) -- and the ISA atmosphere they
// make.  Pure JS (no three.js): the engine model (engine.js), the avionics pages (avionics.js) and the node unit test
// (test/avx_model_test.mjs) all read it.
//
// The knobs flow through first principles, never patched onto a gauge: OAT + elevation + QNH -> station pressure,
// pressure / density altitude, delta / theta / sigma -> the engine (engine.js) and the air data (the PFD's altimeter,
// SAT / ISA box, the cabin altitude); the wind -> the pitot (IAS from the headwind component) and the map's barb; the
// fuel mass -> the tank volumes at the fuel's temperature (~ OAT parked).
//
// Persistence: localStorage 'pc12.viewer.env' (every access in try / catch: private windows, blocked storage); URL
// parameters ?oat= ?elev= ?qnh= (< 100 = inHg) ?wind=dir/kt ?fuel=lb ?gpu=1 ?hdg= ?baro=std override for the session
// and are never stored.

const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
export const HPA_PER_INHG = 33.8639;

// fuel: two wing tanks of 201 US gal usable [S POH 1-4]; Jet-A density 6.725 lb / US gal at 15 C (POH 2,703.6 lb /
// 402 gal) x (1 - 0.00092 (T - 15)) [D: ASTM 54B volume correction, Measurement Canada VCF table]
export const FUEL = { galSide: 201, rho15: 6.725, vcf: 0.00092, lowLbSide: 134 };
export const fuelDensity = (tC) => FUEL.rho15 * (1 - FUEL.vcf * (tC - 15));
export const fuelMaxLb = (tC) => 2 * FUEL.galSide * fuelDensity(tC);

export const ENV_DEFAULTS = Object.freeze({
  oat: 22,          // C   -- T1 22 in P1046410 (EDNY, AERO 2025); under the 23 C dry-motoring threshold
  elev: 1370,       // ft  -- EDNY, the photo session's field
  qnh: 1013,        // hPa -- P1046408's 1013
  qnhUnit: 'inHg',  // the altimeter readout's unit (inHg / hPa)
  windDir: 200,     // deg true, from
  windKt: 6,
  fuelLb: 2170,     // lb  -- QTY 2172 in P1046410
  gpu: false,       // ground power unit connected
});
export const ENV_LIMITS = Object.freeze({
  oat: [-40, 50, 1], elev: [0, 10000, 10], qnh: [948, 1050, 1], windDir: [0, 360, 10], windKt: [0, 50, 1],
  fuelLb: [0, 2850, 10],
});
// not knobs (tests): the aircraft heading (the apron has no north: 180 makes the interior sun, az 20 / el 30 from the
// nose, a plausible mid-October early-afternoon sun at ~47.6 N -- research_pages sec. 8) and the baro mode
export const ENV_FIXED = { hdg: 180, baro: 'qnh' };

// ------------------------------------------------------------------ ISA
// standard formulas; elev in ft, qnh / baro in hPa, oat in C
export function isa({ oat = 15, elev = 0, qnh = 1013.25, baro = null } = {}) {
  const pStn = qnh * Math.pow(1 - K_H * elev, N_P);          // station pressure: QNH reduced along the lapse
  const delta = pStn / 1013.25, T = oat + 273.15, theta = T / 288.15, sigma = delta / theta;
  const pa = altOf(delta);                                                 // pressure altitude, ft
  const tIsa = 15 - 1.98 * pa / 1000;
  const B = baro == null ? qnh : baro;
  return {
    oat, elev, qnh, pStn, delta, theta, sigma, rho: 1.225 * sigma, pa, tIsa, isaDev: oat - tIsa,
    da: 145442.16 * (1 - Math.pow(sigma, 0.234969)),                      // density altitude, ft
    indAlt: altOf(pStn / B),                                               // the altimeter at baro setting B
  };
}
// the ISA pressure-height law and its exact inverse (so the altimeter set to QNH reads the field elevation to the foot)
const K_H = 6.87559e-6, N_P = 5.25588;
export const altOf = (ratio) => (1 - Math.pow(ratio, 1 / N_P)) / K_H;
// the altimeter reading for a baro setting (hPa) at station pressure pStn
export const indicatedAlt = (pStn, baro) => altOf(pStn / baro);

// the parked aircraft's air data from the wind: the relative wind and the pitot's indicated airspeed (headwind component
// x sqrt(sigma); a tailwind gives nothing), kt
export function airData(env, atm, hdg = ENV_FIXED.hdg) {
  const rel = ((env.windDir - hdg) % 360 + 540) % 360 - 180;               // -180 .. 180, + = from the right
  const head = env.windKt * Math.cos(rel * Math.PI / 180), cross = env.windKt * Math.sin(rel * Math.PI / 180);
  const ias = Math.max(0, head) * Math.sqrt(atm.sigma);
  return { rel, head, cross, ias, tas: ias / Math.sqrt(atm.sigma) };
}

// ------------------------------------------------------------------ query / storage
const STORE = 'pc12.viewer.env';
function num(v) { const x = parseFloat(v); return Number.isFinite(x) ? x : null; }

export function parseEnvQuery(search) {
  const q = new URLSearchParams(search || ''), o = {};
  const n = (k) => (q.has(k) ? num(q.get(k)) : null);
  if (n('oat') != null) o.oat = n('oat');
  if (n('elev') != null) o.elev = n('elev');
  if (n('qnh') != null) { const v = n('qnh'); o.qnh = v < 100 ? v * HPA_PER_INHG : v; if (v < 100) o.qnhUnit = 'inHg'; }
  if (q.has('wind')) {
    const m = String(q.get('wind')).split(/[/@,]/).map(num);
    if (m[0] != null) o.windDir = m[0];
    if (m[1] != null) o.windKt = m[1];
  }
  if (n('fuel') != null) o.fuelLb = n('fuel');
  if (q.has('gpu')) o.gpu = q.get('gpu') === '1' || q.get('gpu') === 'true';
  const fixed = {};
  if (n('hdg') != null) fixed.hdg = ((n('hdg') % 360) + 360) % 360;
  if (q.get('baro') === 'std') fixed.baro = 'std';
  return { env: o, fixed };
}

export class Environment {
  constructor({ search = typeof location !== 'undefined' ? location.search : '', storage = true } = {}) {
    this.v = { ...ENV_DEFAULTS };
    this.storage = storage;
    this.listeners = [];
    if (storage) this._load();
    this.base = { ...this.v };              // the stored values the URL's session overrides sit on
    const { env, fixed } = parseEnvQuery(search);
    this.url = env;
    this.urlKeys = new Set(Object.keys(env));
    this.fixed = { ...ENV_FIXED, ...fixed };
    this._apply(env);
    this.atm = this._atm();
  }

  _apply(o) {
    const v = this.v;
    for (const k of ['oat', 'elev', 'qnh', 'windDir', 'windKt']) if (o[k] != null && Number.isFinite(+o[k])) {
      const [a, b] = ENV_LIMITS[k];
      v[k] = clamp(+o[k], a, b);
    }
    if (v.windDir >= 360) v.windDir = 360;
    if (o.qnhUnit === 'inHg' || o.qnhUnit === 'hPa') v.qnhUnit = o.qnhUnit;
    if (o.gpu != null) v.gpu = !!o.gpu;
    if (o.fuelLb != null && Number.isFinite(+o.fuelLb)) v.fuelLb = +o.fuelLb;
    v.fuelLb = clamp(v.fuelLb, 0, this.fuelMax());
  }
  // the usable fuel at the fuel's temperature (parked: the OAT): the mass the 402 US gal hold
  fuelMax() { return Math.floor(fuelMaxLb(this.v.oat)); }

  _atm() {
    const v = this.v, a = isa({ oat: v.oat, elev: v.elev, qnh: v.qnh });
    a.baroMode = this.fixed.baro;
    a.baro = this.fixed.baro === 'std' ? 1013.25 : v.qnh;
    a.indAlt = indicatedAlt(a.pStn, a.baro);
    a.hdg = this.fixed.hdg;
    a.air = airData(v, a, this.fixed.hdg);
    return a;
  }

  get() { return { ...this.v, hdg: this.fixed.hdg, baro: this.fixed.baro }; }

  // o: any of the knobs; {instant: true} also snaps the engine's and the air data's lags (tests); {store: false}
  // leaves localStorage alone
  set(o = {}, { instant = false, store = true } = {}) {
    if (o.hdg != null) this.fixed.hdg = ((+o.hdg % 360) + 360) % 360;
    if (o.baro != null) this.fixed.baro = o.baro === 'std' ? 'std' : 'qnh';
    this._apply(o);
    for (const k of Object.keys(o)) this.urlKeys.delete(k);
    this.atm = this._atm();
    if (store) this._save();
    for (const f of this.listeners) f(this.atm, { instant });
    return this.get();
  }
  reset({ instant = false } = {}) {
    this.v = { ...ENV_DEFAULTS };
    this.fixed = { ...ENV_FIXED };
    this.urlKeys.clear();
    return this.set({}, { instant });
  }
  onChange(f) { this.listeners.push(f); }

  _load() {
    try {
      const s = localStorage.getItem(STORE);
      if (!s) return;
      const o = JSON.parse(s);
      if (o && o.v === 1) this._apply(o);
    } catch (e) { /* storage refused: the defaults */ }
  }
  _save() {
    if (!this.storage) return;
    try {
      // the URL's overrides are session values: a stored copy keeps what the knobs set before them
      const s = { v: 1, ...this.v };
      for (const k of this.urlKeys) s[k] = this.base[k];
      localStorage.setItem(STORE, JSON.stringify(s));
    } catch (e) { /* storage refused */ }
  }
}
