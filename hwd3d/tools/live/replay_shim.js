// In-page replay "relay" for Hayward Live 3D: answers the relay endpoints from a packed recording, so the app runs its
// LIVE code path (stream feed, interpolation, parking, physics) on real HWD traffic replayed at real speed, with no
// relay (the phone artifact's CSP blocks every fetch outside the artifact).
//
// Forked from sfo3d/tools/build3/replay_shim.js @ a967f9b. Kept: the fake EventSource, the fetch patch, the v2 field-
// delta expansion, the timing rule (every payload's `now` and each record's `_pt` move by `offset`; `dataNow` keeps the
// recording clock so the Sun, lights and METAR clock show the recorded time of day). Changed: an ES module with
// installReplay() (contract: docs/phase2_fork_map.md 2.2) instead of an IIFE reading window.SFO_REPLAY; hwd-pack/1
// (tools/live/build_replay.py); ping says {hwdlive: 1}; the replay clock starts `lookahead_s` into the window and every
// new stream first gets the payloads of the last lookahead_s + 5 s (the app displays lookahead_s behind the head, so the
// recorder's 46-s holes are interpolated between real fixes and the first frame does not wait); METAR filtered to the
// replay time; api/ident from the current records; a soft loop (an empty payload, then the window again) instead of a
// page reload; gzip detected by magic bytes (a server may already have decoded it). Dropped: routes, gates, the banner
// (the UI is P4's; it reads ping.features.replay).
//
//   import { installReplay } from '../../out/replay/replay_shim.js';
//   const info = await installReplay({ url: 'out/replay/pack.json.gz', loop: true });
//   // -> { from: ms, until: ms, lookahead_s, name, desc, d1 }   then detectRelay() etc. as live
//
// Endpoints answered: api/ping, api/adsb, api/stream (EventSource), api/metar, api/ident, api/status. Any other api/*
// -> 404 JSON. Non-api requests pass through.

let installed = null;

export async function installReplay({ url = 'out/replay/pack.json.gz', loop = true } = {}) {
  if (installed) return installed;
  const realFetch = window.fetch.bind(window);
  const res = await realFetch(url);
  if (!res.ok) throw new Error('replay pack HTTP ' + res.status + ' (' + url + ')');
  const buf = new Uint8Array(await res.arrayBuffer());
  let txt;
  if (buf[0] === 0x1f && buf[1] === 0x8b) {
    if (typeof DecompressionStream === 'undefined') throw new Error('replay: this browser has no DecompressionStream');
    txt = await new Response(new Blob([buf]).stream().pipeThrough(new DecompressionStream('gzip'))).text();
  } else txt = new TextDecoder().decode(buf);
  const pack = JSON.parse(txt);
  if (pack.v !== 'hwd-pack/1') throw new Error('replay: not an hwd-pack/1 file (' + pack.v + ')');
  const L = pack.lookahead_s || 60, ev = pack.events;
  const HIST = L + 5;
  let off = 0, idx = 0, st = {}, latest = null, seqBase = 0, lastSeq = 0, done = false;
  const sources = [], history = [];      // history: [{w: shifted now (s), data: JSON string}]

  function start() {   // the replay clock starts L s into the window: the first L s are delivered at once
    off = Date.now() / 1000 - (pack.from + L);
    idx = 0; st = {}; done = false;
  }
  function expand(p) {
    const ac = p.d.map(r => {
      const a = st[r[0]] || (st[r[0]] = { hex: r[0] }), ch = r[1];
      for (const k in ch) a[k] = ch[k];
      if (r[2]) for (const k of r[2]) delete a[k];
      return a;
    });
    // absent from p.d = gone from this payload (v2 semantics); its state is kept, because the builder encodes a
    // returning aircraft's delta against its last record
    return { now: p.now, dataNow: p.dataNow, seq: p.seq, _source: p._source, ac };
  }
  function shifted(p) {
    const ac = p.ac.map(a => { const b = Object.assign({}, a); if (typeof b._pt === 'number') b._pt += off; return b; });
    lastSeq = p.seq;
    return { now: Math.round(p.now + off * 1000), dataNow: p.dataNow, seq: seqBase + p.seq, total: ac.length,
             _source: p._source || 'adsb.lol', msg: 'No error', ac };
  }
  function push(payload) {
    latest = payload;
    const data = JSON.stringify(payload), w = payload.now / 1000;
    history.push({ w, data });
    while (history.length && w - history[0].w > HIST) history.shift();
    for (const s of sources.slice()) s._fire('adsb', data);
  }
  function tick() {
    const t = Date.now() / 1000 - off;
    while (idx < ev.length && ev[idx].T <= t) push(shifted(expand(ev[idx++].p)));
    if (idx >= ev.length && !done && t > pack.until + L + 2) {
      done = true;
      if (loop) {
        seqBase += lastSeq + 1;
        push({ now: Date.now(), dataNow: Math.round(pack.until * 1000), seq: seqBase, total: 0, _source: 'adsb.lol',
               msg: 'replay restarts', ac: [] });
        start();
      }
    }
  }
  start();
  tick();
  setInterval(tick, 200);

  function FakeES(u) {
    this.url = u; this.readyState = 0; this._l = {}; this.onerror = null; this.onopen = null; this.onmessage = null;
    this._q = [];                    // payloads pushed before the history was delivered keep their order behind it
    sources.push(this);
    const self = this, back = history.map(h => h.data);
    setTimeout(() => {               // like the relay's ?history: the recent payloads, oldest first
      if (self.readyState === 2) return;
      self.readyState = 1;
      if (self.onopen) self.onopen({ type: 'open' });
      for (const d of back) self._fire('adsb', d);
      for (const [t, d] of self._q.splice(0)) self._fire(t, d);
    }, 0);
  }
  FakeES.prototype.addEventListener = function (type, fn) { (this._l[type] = this._l[type] || []).push(fn); };
  FakeES.prototype.removeEventListener = function (type, fn) { const a = this._l[type] || []; const i = a.indexOf(fn); if (i >= 0) a.splice(i, 1); };
  FakeES.prototype.close = function () { this.readyState = 2; const i = sources.indexOf(this); if (i >= 0) sources.splice(i, 1); };
  FakeES.prototype._fire = function (type, data) {
    if (this.readyState === 0) { this._q.push([type, data]); return; }
    const e = { type, data };
    for (const fn of (this._l[type] || []).slice()) { try { fn(e); } catch (x) { console.error(x); } }
    if (type === 'message' && this.onmessage) this.onmessage(e);
  };
  FakeES.CONNECTING = 0; FakeES.OPEN = 1; FakeES.CLOSED = 2;
  const RealES = window.EventSource;
  window.EventSource = function (u, opt) { return /(^|\/)api\/stream/.test(String(u)) ? new FakeES(u) : new RealES(u, opt); };
  window.EventSource.CONNECTING = 0; window.EventSource.OPEN = 1; window.EventSource.CLOSED = 2;

  const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'Content-Type': 'application/json' } });
  const text = (s, status = 200) => new Response(s, { status, headers: { 'Content-Type': 'text/plain' } });
  const T = () => Date.now() / 1000 - off;                    // replay time (recording clock, s) of the stream head
  const replayInfo = () => ({ src: 'pack', name: pack.name, desc: pack.desc, from: Math.round(pack.from * 1000),
                              until: Math.round(pack.until * 1000), lookahead_s: L, pack: true, loop, speed: 1 });
  function ident(key) {
    const r = latest && latest.ac.find(a => a.hex === key);
    if (!r) return null;
    if (r._masked) return { key, masked: true, t: r.t || null, desc: r.desc || null, category: r.category || null };
    const mx = r._mx || {}, o = { key, masked: false, category: r.category || null };
    for (const [f, m] of [['r', 'r'], ['t', 't'], ['desc', 'd']]) {
      if (r[f]) { o[f] = r[f]; o[f + '_src'] = 'adsb'; } else if (mx[m]) { o[f] = mx[m]; o[f + '_src'] = 'mictronics'; }
    }
    if ((r.flight || '').trim()) o.flight = r.flight.trim();
    if (mx.op) { o.op = mx.op; o.op_src = 'mictronics'; }
    return o;
  }
  window.fetch = async function (input, init) {
    const u = String(input && input.url || input);
    const m = /(?:^|\/)api\/([a-z]+)(\?[^#]*)?/.exec(u);
    if (!m || u === url) return realFetch(input, init);
    const q = new URLSearchParams(m[2] || '');
    switch (m[1]) {
      case 'ping':
        return json({ hwdlive: 1, v: 'replay-pack', mode: 'replay', stream: true, delta: true, history: true,
          dataNow: Math.round(T() * 1000), center: pack.center,
          poll: { adsblol_s: null, adsbfi: false, quota: null },
          features: { metar: 'KHWD', taf: null, ident: pack.ident || null, ident_endpoint: true, d1: 'dbFlags & 12',
                      d1_mode: pack.d1 && pack.d1.ident, replay: replayInfo() },
          providers: ['adsb.lol'], attribution: pack.attribution_map || pack.attribution || null });
      case 'adsb':
        return json(latest || { ac: [], now: Date.now(), dataNow: Math.round(T() * 1000), seq: 0, total: 0, msg: 'waiting' });
      case 'metar': {
        if ((q.get('ids') || 'KHWD').toUpperCase() !== 'KHWD') return json({ error: 'only KHWD is served' }, 400);
        const t = T(), Lm = (pack.metar || []).filter(x => x.obsTime <= t && x.obsTime >= t - 3 * 3600)
          .sort((a, b) => b.obsTime - a.obsTime);
        if (!Lm.length || t - Lm[0].obsTime > 5400) return json({ error: 'no KHWD METAR within 90 min of the replay time' }, 502);
        return q.get('format') === 'json' ? json(Lm) : text(Lm.map(x => x.rawOb).join('\n'));
      }
      case 'ident': {
        const v = ident((q.get('key') || '').toLowerCase());
        return v ? json(v) : json({ error: 'not in the current picture' }, 404);
      }
      case 'status':
        return json({ relay: { v: 'replay-pack', replay: replayInfo() }, merge: { aircraft: latest ? latest.ac.length : 0,
          d1_mode: pack.d1 && pack.d1.ident, masked_now: latest ? latest.ac.filter(a => a._masked).length : 0 },
          sampling: pack.sampling });
      default:
        return json({ error: 'not in the replay' }, 404);
    }
  };
  installed = { from: Math.round(pack.from * 1000), until: Math.round(pack.until * 1000), lookahead_s: L,
                name: pack.name, desc: pack.desc, d1: pack.d1, sampling: pack.sampling };
  window.__hwdReplay = installed;
  return installed;
}
