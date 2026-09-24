// Text overlays drawn with Canvas2D (uploaded as texture, composited in final pass)
export class Overlay {
  constructor(W, H) { this.W = W; this.H = H; this.cv = document.createElement('canvas'); this.cv.width = W; this.cv.height = H; this.cx = this.cv.getContext('2d'); this.key = null; this.info = {}; }
  font(w, px) { return `${w} ${Math.round(px)}px "Noto Sans CJK SC", "DejaVu Sans", sans-serif`; }
  draw(o) {
    const key = o ? JSON.stringify(o, (k, v) => typeof v === 'number' ? Math.round(v * 100) / 100 : v) : 'none';
    if (key === this.key) return false; this.key = key;
    const { cx, W, H } = this; const S = H / 1080;
    cx.clearRect(0, 0, W, H);
    if (!o || o.alpha <= 0.001) return true;
    cx.save(); cx.globalAlpha = Math.min(1, o.alpha);
    cx.shadowColor = 'rgba(0,0,0,0.45)'; cx.shadowBlur = 10 * S; cx.shadowOffsetY = 1.5 * S;
    cx.fillStyle = '#fff'; cx.textBaseline = 'alphabetic';
    const spaced = (text, x, y, sp) => { let xx = x; for (const ch of text) { cx.fillText(ch, xx, y); xx += cx.measureText(ch).width + sp; } return xx; };
    const I = this.info;
    if (o.kind === 'title') {
      const x = 110 * S, y = H - 250 * S;
      cx.fillStyle = 'rgba(255,255,255,0.9)'; cx.fillRect(x, y - 92 * S, 3 * S, 150 * S);
      cx.fillStyle = '#fff'; cx.font = this.font(300, 28 * S); spaced('SAN FRANCISCO INTERNATIONAL AIRPORT', x + 30 * S, y - 55 * S, 5 * S);
      cx.font = this.font(700, 86 * S); spaced('SFO', x + 26 * S, y + 32 * S, 10 * S);
      cx.font = this.font(300, 24 * S); cx.fillStyle = 'rgba(255,255,255,0.85)';
      spaced('KSFO  ·  37.62° N  122.38° W  ·  ELEV 13 FT', x + 250 * S, y + 2 * S, 3 * S);
      if (I.conditions) spaced(I.conditions, x + 250 * S, y + 36 * S, 2 * S);
    } else if (o.kind === 'label') {
      const x = 110 * S, y = H - 150 * S;
      cx.fillStyle = 'rgba(255,255,255,0.9)'; cx.fillRect(x, y - 58 * S, 3 * S, 84 * S);
      cx.fillStyle = '#fff'; cx.font = this.font(500, 44 * S); cx.fillText(o.text, x + 26 * S, y - 12 * S);
      if (o.sub) { cx.font = this.font(300, 25 * S); cx.fillStyle = 'rgba(255,255,255,0.85)'; spaced(o.sub.toUpperCase(), x + 28 * S, y + 22 * S, 2.5 * S); }
    } else if (o.kind === 'end') {
      cx.textAlign = 'left';
      const cxm = W / 2;
      cx.font = this.font(700, 120 * S); const w1 = cx.measureText('SFO').width + 2 * 14 * S; spaced('SFO', cxm - w1 / 2, H * 0.47, 14 * S);
      cx.font = this.font(300, 30 * S); const t2 = 'SAN FRANCISCO INTERNATIONAL AIRPORT'; let w2 = 0; for (const ch of t2) w2 += cx.measureText(ch).width + 6 * S; spaced(t2, cxm - w2 / 2, H * 0.47 + 58 * S, 6 * S);
      cx.font = this.font(300, 22 * S); cx.fillStyle = 'rgba(255,255,255,0.8)';
      const t3 = I.endLine || 'Procedural 3D recreation · runways placed from FAA survey coordinates'; let w3 = 0; for (const ch of t3) w3 += cx.measureText(ch).width + 2 * S; spaced(t3, cxm - w3 / 2, H * 0.47 + 110 * S, 2 * S);
      if (I.endLine2) { let w4 = 0; for (const ch of I.endLine2) w4 += cx.measureText(ch).width + 2 * S; spaced(I.endLine2, cxm - w4 / 2, H * 0.47 + 145 * S, 2 * S); }
    }
    cx.restore();
    return true;
  }
}
