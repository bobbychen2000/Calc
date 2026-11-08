// In-page replay "relay" for the phone artifact (tools/build3/replay_pack.py makes the data; phone_artifact_page.py
// inlines this script before the app when REPLAY=<pack> is set). The artifact CSP blocks fetches outside the artifact, so
// the page cannot reach sfo_live_server.py; this shim answers the relay endpoints the app calls from a packed recording of
// the relay's own merged stream, so the app runs its LIVE code path (stream feed, Hermite interpolation, stand matching,
// bridges) on real traffic, replayed at real speed:
//   api/ping      -> {sfolive: 1, mode: 'replay', stream: true, features: {gates: false, routes: true, metar: true, taf: false}}
//   api/stream    -> a fake EventSource that sends each recorded 'adsb' event at its recorded time + offset
//   api/adsb      -> the latest event (poll fallback)
//   api/metar     -> the METARs recorded with the window; api/routeset -> the routes recorded with the window
// Timing: offset = page start - first event. Every payload's `now` (ms) and each aircraft's `_pt` (s) move by the offset
// (as the relay's own --replay re-times records to wall time); `dataNow` keeps the recording's clock, so the Sun, the
// lights and the METAR clock show the recorded time of day (environment_spec.md 3.2). At the end of the window the page
// reloads and the replay starts again.
// Pack v2 (replay_pack.py step 4) stores each event's aircraft as field deltas p.d = [[hex, changed, removed?], ...];
// expand() rebuilds the full records event by event as the replay reaches them (v1 packs carry p.ac and pass through).
(function () {
  var R = window.SFO_REPLAY; if (!R || !R.url) return;
  window.SFO_MODE = 'live';
  var pack = null, off = 0, idx = 0, latest = null, sources = [], st = {};
  var ready = (async function () {
    var r = await window.fetch(R.url); if (!r.ok) throw new Error('replay data HTTP ' + r.status);
    var txt = await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text();
    pack = JSON.parse(txt); off = Date.now() / 1000 - pack.from + 0.5;
    banner();
    return pack;
  })();
  ready.catch(function (e) { window.__sfoError = 'replay: ' + (e && e.message || e); });
  function expand(p) {
    if (p.ac) return p;
    var ac = p.d.map(function (r) {
      var a = st[r[0]] || (st[r[0]] = { hex: r[0] }), ch = r[1], k;
      for (k in ch) a[k] = ch[k];
      if (r[2]) r[2].forEach(function (k) { delete a[k]; });
      return a;
    });
    return { now: p.now, dataNow: p.dataNow, seq: p.seq, _source: p._source, ac: ac };
  }
  function shifted(p) {
    var ac = p.ac.map(function (a) { var b = Object.assign({}, a); if (typeof b._pt === 'number') b._pt += off; return b; });
    return { now: p.now + off * 1000, dataNow: p.dataNow, seq: p.seq, _source: p._source, ac: ac };
  }
  function tick() {
    if (!pack) return;
    var t = Date.now() / 1000 - off, ev = pack.events;
    while (idx < ev.length && ev[idx].T <= t) {
      latest = shifted(expand(ev[idx].p)); var data = JSON.stringify(latest); idx++;
      sources.forEach(function (s) { s._fire('adsb', data); });
    }
    if (idx >= ev.length && t > pack.until + 20) location.reload();
  }
  setInterval(tick, 200);
  function FakeES(url) {
    this.url = url; this.readyState = 0; this._l = {}; this.onerror = null; this.onopen = null; this.onmessage = null;
    var self = this; sources.push(this);
    ready.then(function () { self.readyState = 1; if (self.onopen) self.onopen({}); }, function () { if (self.onerror) self.onerror({}); });
  }
  FakeES.prototype.addEventListener = function (type, fn) { (this._l[type] = this._l[type] || []).push(fn); };
  FakeES.prototype.removeEventListener = function (type, fn) { var a = this._l[type] || []; var i = a.indexOf(fn); if (i >= 0) a.splice(i, 1); };
  FakeES.prototype.close = function () { this.readyState = 2; var i = sources.indexOf(this); if (i >= 0) sources.splice(i, 1); };
  FakeES.prototype._fire = function (type, data) {
    var e = { type: type, data: data }; (this._l[type] || []).forEach(function (fn) { try { fn(e); } catch (x) { } });
    if (type === 'message' && this.onmessage) this.onmessage(e);
  };
  var RealES = window.EventSource;
  window.EventSource = function (url, opt) { return /api\/stream/.test(String(url)) ? new FakeES(url) : new RealES(url, opt); };
  var realFetch = window.fetch.bind(window);
  function json(o, status) { return new Response(JSON.stringify(o), { status: status || 200, headers: { 'Content-Type': 'application/json' } }); }
  window.fetch = async function (input, init) {
    var u = String(input && input.url || input);
    if (!/(^|\/)api\//.test(u) || u === R.url) return realFetch(input, init);
    try { await ready; } catch (e) { return json({ error: 'no replay data' }, 503); }
    if (/api\/ping/.test(u)) return json({ sfolive: 1, v: 'replay', mode: 'replay', stream: true, delta: true,
      dataNow: Math.round((Date.now() / 1000 - off) * 1000),
      features: { gates: false, routes: true, metar: true, taf: false, replay: { from: pack.from, until: pack.until } },
      providers: ['adsb.lol', 'adsb.fi'], attribution: pack.attribution || null });
    if (/api\/adsb/.test(u)) return latest ? json(latest) : json({ ac: [], now: Date.now() });
    if (/api\/metar/.test(u)) return json(pack.metar || []);
    if (/api\/routeset/.test(u)) {
      var want = {}; try { (JSON.parse(init && init.body || '{}').planes || []).forEach(function (p) { want[p.callsign] = 1; }); } catch (e) { }
      return json((pack.routes || []).filter(function (r) { return want[r.callsign]; }));
    }
    return json({ error: 'not in the replay' }, 404);
  };
  function hhmm(t) { return new Date(t * 1000).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'America/Los_Angeles' }); }
  function banner() {
    var b = document.createElement('div'); b.id = 'replay-banner';
    var ago = Math.max(0, Math.round((pack.packed - pack.until) / 60));
    b.textContent = (window.SFO_LITE ? 'Lite \u00b7 ' : '') + 'Replay of real SFO traffic recorded ' + hhmm(pack.from) + '\u2013' + hhmm(pack.until) + ' PT by the cloud relay' +
      (ago ? ' (packed ' + ago + ' min after)' : '') + ' \u00b7 loops';
    b.setAttribute('style', 'position:fixed;left:50%;transform:translateX(-50%);top:calc(env(safe-area-inset-top,0px) + 106px);' +
      'z-index:50;max-width:92vw;padding:3px 10px;border-radius:999px;background:rgba(10,14,20,.78);color:#e8edf3;' +
      'font:500 11px/1.35 "IBM Plex Mono",ui-monospace,monospace;text-align:center;pointer-events:none');
    (document.body ? Promise.resolve() : new Promise(function (r) { document.addEventListener('DOMContentLoaded', r); }))
      .then(function () { document.body.appendChild(b); });
  }
})();
