// Side-panel content: parts tree + info card, drawing viewer (pan / zoom / pinch), specs.
import { SOURCED, ESTIMATED, ANIMATION_NOTES } from './sources.js';

const $ = (id) => document.getElementById(id);
const el = (tag, attrs = {}, ...kids) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') e.className = v;
    else if (k === 'text') e.textContent = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const k of kids) if (k != null) e.append(k);
  return e;
};
const fmt = (n) => Number(n).toLocaleString('en-US');

// ------------------------------------------------------------------------ parts
export class PartsPanel {
  constructor({ meta, onSelect }) {
    this.meta = meta;
    this.onSelect = onSelect;
    this.bom = new Map(meta.bom.map((b) => [b.id, b]));
    this.tree = $('partTree');
    this.search = $('partSearch');
    this.items = new Map();
    const groups = new Map();
    for (const b of meta.bom) {
      if (!groups.has(b.group)) groups.set(b.group, []);
      groups.get(b.group).push(b);
    }
    for (const [g, list] of groups) {
      const ul = el('ul', { role: 'group' });
      for (const b of list) {
        const btn = el('button', { type: 'button', role: 'treeitem', 'data-id': b.id, onclick: () => this.onSelect(b.id) },
          el('span', { class: 'pname', text: b.name }), el('span', { class: 'pid', text: b.id }));
        const li = el('li', {}, btn);
        ul.append(li);
        this.items.set(b.id, { li, btn, text: (b.name + ' ' + b.id + ' ' + (b.note || '') + ' ' + g).toLowerCase() });
      }
      const det = el('details', { open: '' }, el('summary', {}, el('span', { text: g }), el('span', { class: 'cnt', text: String(list.length) })), ul);
      det.dataset.group = g;
      det.dataset.total = String(list.length);
      this.tree.append(det);
    }
    $('pCount').textContent = `${meta.bom.length} parts`;
    // 'input' misses the native clear of type=search (Escape / the x button): listen to all three
    const refilter = () => this.filter(this.search.value);
    for (const ev of ['input', 'search', 'change']) this.search.addEventListener(ev, refilter);
    // Escape: first clears the query (and the filter), a second Escape leaves the field
    this.search.addEventListener('keydown', (e) => {
      if (e.key !== 'Escape' || !this.search.value) return;
      e.preventDefault();
      e.stopPropagation();
      this.search.value = '';
      this.filter('');
    });
  }

  filter(q) {
    q = q.trim().toLowerCase();
    let n = 0;
    for (const [, it] of this.items) {
      const m = !q || q.split(/\s+/).every((w) => it.text.includes(w));
      it.li.hidden = !m;
      if (m) n++;
    }
    for (const det of this.tree.querySelectorAll('details')) {
      const shown = [...det.querySelectorAll('li')].filter((li) => !li.hidden).length;
      det.hidden = !shown;
      if (q && shown) det.open = true;
      det.querySelector('.cnt').textContent = q ? `${shown} / ${det.dataset.total}` : det.dataset.total;
    }
    $('pCount').textContent = q ? `${n} of ${this.meta.bom.length} parts` : `${this.meta.bom.length} parts`;
  }

  setCurrent(id) {
    for (const [pid, it] of this.items) {
      if (pid === id) { it.btn.setAttribute('aria-current', 'true'); }
      else it.btn.removeAttribute('aria-current');
    }
    const it = id && this.items.get(id);
    if (it && !it.li.hidden && it.li.offsetParent) it.btn.scrollIntoView({ block: 'nearest' });
  }

  setHidden(hiddenSet) {
    for (const [pid, it] of this.items) it.li.classList.toggle('hidden-part', hiddenSet.has(pid));
  }
}

export class InfoCard {
  constructor({ meta }) {
    this.meta = meta;
    this.bom = new Map(meta.bom.map((b) => [b.id, b]));
    this.steps = new Map(meta.steps.map((s, i) => [s.key, { ...s, i }]));
    this.root = $('infoCard');
    // compact card on phones: name, hint and actions; the details fold out
    this.more = $('icMore');
    this.more.addEventListener('click', () => this.setExpanded(!this.root.classList.contains('expanded')));
  }

  setExpanded(on) {
    this.root.classList.toggle('expanded', on);
    this.more.setAttribute('aria-expanded', String(on));
    this.more.textContent = on ? 'Less' : 'Details';
  }

  show(id, { hint = '' } = {}) {
    const b = this.bom.get(id);
    if (!b) { this.hide(); return; }
    $('icName').textContent = b.name;
    $('icMeta').textContent = `${b.id} · ${b.group} · qty ${b.qty}`;
    $('icNote').textContent = b.note || '';
    const dl = $('icInfo');
    dl.replaceChildren();
    const add = (k, v) => dl.append(el('dt', { text: k }), el('dd', { text: v }));
    for (const [k, v] of Object.entries(b.info || {})) add(k, String(v));
    const st = this.steps.get(b.step);
    add('build step', st ? `${st.i + 1}. ${st.title}` : b.step);
    add('triangles', fmt(b.tris));
    if (b.materials && b.materials.length) add('materials', b.materials.join(', '));
    $('icHint').hidden = !hint;
    $('icHint').textContent = hint;
    this.root.hidden = false;
  }

  hide() { this.root.hidden = true; }
}

// ------------------------------------------------------------------------ drawings
export class DrawingViewer {
  constructor({ sheets, onChange }) {
    this.sheets = sheets;          // [{url, title, desc}]
    this.view = $('drawingView');
    this.pane = $('drawingPane');
    this.img = $('drawingImg');
    this.s = 1; this.x = 0; this.y = 0;
    this.nat = { w: 1, h: 1 };
    this.fitS = 1;
    this.cur = -1;
    this.pointers = new Map();
    this.onChange = onChange;
    this.img.addEventListener('load', () => {
      this.nat.w = this.img.naturalWidth || 1189;
      this.nat.h = this.img.naturalHeight || 841;
      this.loaded = true;
      this.fit();
    });
    this.img.addEventListener('error', () => {
      this.loaded = false;
      $('dDesc').textContent = `Could not load ${this.sheets[this.cur].url}`;
    });
    const p = this.pane;
    p.addEventListener('wheel', (e) => {
      e.preventDefault();
      const r = p.getBoundingClientRect();
      this.zoomAt(Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0015)), e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });
    p.addEventListener('pointerdown', (e) => {
      p.setPointerCapture(e.pointerId);
      this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      p.classList.add('grabbing');
    });
    p.addEventListener('pointermove', (e) => {
      const prev = this.pointers.get(e.pointerId);
      if (!prev) return;
      if (this.pointers.size === 1) {
        this.x += e.clientX - prev.x; this.y += e.clientY - prev.y;
        prev.x = e.clientX; prev.y = e.clientY;
        this.apply();
      } else if (this.pointers.size === 2) {
        // pinch: scale by the change in finger distance about the midpoint
        const [a, b] = [...this.pointers.values()];
        const d0 = Math.hypot(a.x - b.x, a.y - b.y), mx0 = (a.x + b.x) / 2, my0 = (a.y + b.y) / 2;
        prev.x = e.clientX; prev.y = e.clientY;
        const d1 = Math.hypot(a.x - b.x, a.y - b.y), mx1 = (a.x + b.x) / 2, my1 = (a.y + b.y) / 2;
        const r = p.getBoundingClientRect();
        this.x += mx1 - mx0; this.y += my1 - my0;
        if (d0 > 0) this.zoomAt(d1 / d0, mx1 - r.left, my1 - r.top);
        else this.apply();
      }
    });
    const up = (e) => { this.pointers.delete(e.pointerId); if (!this.pointers.size) p.classList.remove('grabbing'); };
    p.addEventListener('pointerup', up);
    p.addEventListener('pointercancel', up);
    p.addEventListener('dblclick', (e) => { const r = p.getBoundingClientRect(); this.zoomAt(2, e.clientX - r.left, e.clientY - r.top); });
    p.addEventListener('keydown', (e) => {
      const r = p.getBoundingClientRect();
      if (e.key === '+' || e.key === '=') this.zoomAt(1.25, r.width / 2, r.height / 2);
      else if (e.key === '-') this.zoomAt(0.8, r.width / 2, r.height / 2);
      else if (e.key === '0') this.fit();
      else if (e.key.startsWith('Arrow')) {
        const d = 40;
        if (e.key === 'ArrowLeft') this.x += d; if (e.key === 'ArrowRight') this.x -= d;
        if (e.key === 'ArrowUp') this.y += d; if (e.key === 'ArrowDown') this.y -= d;
        this.apply();
      } else return;
      e.preventDefault();
      e.stopPropagation();
    });
    new ResizeObserver(() => { if (!this.view.hidden && this.loaded) this.fit(); }).observe(this.pane);
  }

  select(i) {
    i = Math.max(0, Math.min(this.sheets.length - 1, i | 0));
    const sh = this.sheets[i];
    for (const b of document.querySelectorAll('[data-sheet]')) b.setAttribute('aria-pressed', String(+b.dataset.sheet === i));
    $('dOpen').href = sh.url;
    $('dDesc').textContent = sh.desc;
    this.img.alt = sh.title;
    if (i !== this.cur) {
      this.cur = i;
      this.loaded = false;
      this.img.src = sh.url;
    }
  }

  show(on) {
    this.view.hidden = !on;
    if (on) {
      if (this.cur < 0) this.select(0);
      else if (this.loaded) requestAnimationFrame(() => this.fit());
    }
  }

  fit() {
    const r = this.pane.getBoundingClientRect();
    if (!r.width || !r.height) return;
    this.fitS = Math.min(r.width / this.nat.w, r.height / this.nat.h) * 0.94;
    this.s = this.fitS;
    this.x = (r.width - this.nat.w * this.s) / 2;
    this.y = (r.height - this.nat.h * this.s) / 2;
    this.apply();
  }

  zoomAt(f, cx, cy) {
    const s1 = Math.min(this.fitS * 10, Math.max(this.fitS * 0.5, this.s * f));
    const k = s1 / this.s;
    this.x = cx - (cx - this.x) * k;
    this.y = cy - (cy - this.y) * k;
    this.s = s1;
    this.apply();
  }

  zoomCentre(f) {
    const r = this.pane.getBoundingClientRect();
    this.zoomAt(f, r.width / 2, r.height / 2);
  }

  // layout-size zoom (not a CSS scale) so the SVG re-rasterises crisply
  apply() {
    const im = this.img.style;
    im.width = `${(this.nat.w * this.s).toFixed(1)}px`;
    im.height = `${(this.nat.h * this.s).toFixed(1)}px`;
    im.transform = `translate(${Math.round(this.x)}px, ${Math.round(this.y)}px)`;
  }
}

// ------------------------------------------------------------------------ specs
export function buildSpecs(meta) {
  const t = $('checksTable');
  const head = el('thead', {}, el('tr', {}, el('th', { text: 'Check' }), el('th', { text: 'Official' }), el('th', { text: 'Model' }), el('th', { text: 'Δ mm' })));
  const body = el('tbody');
  for (const c of meta.checks || []) {
    const area = /m\^2|area/i.test(c.check);
    const unit = area ? ' m²' : ' m';
    const min = c.kind === 'min';                       // a lower bound (e.g. floor width >= 1.30 m)
    const d = Math.abs(c.delta_mm ?? 0);
    const cls = (c.ok ?? (d <= 2)) ? 'd-ok' : d <= 10 ? 'd-warn' : 'd-bad';
    const sgn = (v) => (v > 0 ? '+' : v < 0 ? '−' : '');
    const dtxt = area ? (c.delta == null ? '—' : sgn(c.delta) + Math.abs(c.delta).toFixed(3) + ' m²')
      : sgn(c.delta_mm) + Math.abs(c.delta_mm).toFixed(1);
    body.append(el('tr', {},
      el('td', { text: c.check.replace(/\s*\(m\^2\)/, '') }),
      el('td', { text: (min ? '≥ ' : '') + c.official.toFixed(area ? 2 : 3) + unit }),
      el('td', { text: c.model.toFixed(area ? 2 : 3) + unit }),
      el('td', { class: cls, text: dtxt })));
  }
  t.replaceChildren(head, body);

  const kv = (dl, rows) => { dl.replaceChildren(); for (const [k, v] of rows) dl.append(el('dt', { text: k }), el('dd', { text: v })); };
  const w = meta.wing || {};
  const mm = (x) => (x == null ? '—' : fmt(Math.round(x * 1000)) + ' mm');
  kv($('wingList'), [
    ['Semi-span (to winglet root)', mm(w.semi_span)],
    ['Root chord', mm(w.root_chord)],
    ['Tip chord', mm(w.tip_chord)],
    ['MAC', mm(w.mac)],
    ['LEMAC', w.lemac == null ? '—' : 'STA ' + fmt(Math.round(w.lemac * 1000))],
    ['MAC quarter-chord', w.x_qc == null ? '—' : 'STA ' + fmt(Math.round(w.x_qc * 1000))],
  ]);
  const s = meta.stats || {};
  kv($('statsList'), [
    ['Parts', fmt(s.parts ?? meta.bom.length)],
    ['Triangles', fmt(s.triangles ?? 0)],
    ['Vertices', fmt(s.vertices ?? 0)],
    ['GLB size', s.glb_bytes ? (s.glb_bytes / 1048576).toFixed(1) + ' MB (' + (s.glb_encoding || 'KHR_mesh_quantization') + ')' : '—'],
    ['Build steps', String(meta.steps.length)],
  ]);
  const src = $('sourcesList');
  src.replaceChildren(...SOURCED.map((g) => el('div', { class: 'src' }, el('b', { text: g.source }),
    el('ul', {}, ...g.facts.map((f) => el('li', { text: f }))))));
  $('estList').replaceChildren(...ESTIMATED.map((f) => el('li', { text: f })));
  $('animList').replaceChildren(...ANIMATION_NOTES.map((f) => el('li', { text: f })));
}
