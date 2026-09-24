// ------------------------------------------------------------------
// Decal atlas: seatback screens, signage, row placards (drawn on a canvas at load)
// ------------------------------------------------------------------
const ATL = { rects: {}, canvas: null, screenStep: 0 };

function buildAtlas(layout) {
  const S = 1024;
  const cv = document.createElement('canvas');
  cv.width = S; cv.height = S;
  const g = cv.getContext('2d');
  g.fillStyle = '#808080'; g.fillRect(0, 0, S, S);
  const put = (name, x, y, w, h) => { ATL.rects[name] = [x / S, y / S, (x + w) / S, (y + h) / S]; };
  const font = (px, wt = 700) => `${wt} ${px}px "Helvetica Neue", Helvetica, Arial, sans-serif`;

  // ---- Seatback screens: 4 variants stacked (320x180 each) ----
  const SW = 320, SHh = 180;
  for (let v = 0; v < 4; v++) drawScreen(g, 0, v * SHh, SW, SHh, v);
  put('screen', 0, 0, SW, SHh);
  ATL.screenStep = SHh / S;

  // ---- Signs ----
  let x = 330, y = 0;
  // EXIT sign (lit): red letters on warm white
  g.fillStyle = '#f4f1ea'; g.fillRect(x, y, 200, 72);
  g.fillStyle = '#d11f1f'; g.font = font(50, 800); g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText('EXIT', x + 100, y + 38);
  put('exit', x, y, 200, 72);
  // LAV sign
  x = 540;
  g.fillStyle = '#1d232c'; g.fillRect(x, y, 150, 72);
  drawPerson(g, x + 38, y + 36, 1, '#e9edf2');
  drawPerson(g, x + 75, y + 36, 0, '#e9edf2');
  g.fillStyle = '#6ee68a'; g.beginPath(); g.arc(x + 118, y + 36, 11, 0, Math.PI * 2); g.fill();
  put('lav', x, y, 150, 72);
  // PSU icons: no smoking + fasten belt (glowing on dark)
  x = 700;
  g.fillStyle = '#0c0f13'; g.fillRect(x, y, 140, 64);
  g.strokeStyle = '#ffffff'; g.lineWidth = 4;
  g.beginPath(); g.arc(x + 34, y + 32, 22, 0, Math.PI * 2); g.stroke();
  g.fillStyle = '#ffffff'; g.fillRect(x + 20, y + 29, 26, 7);
  g.beginPath(); g.moveTo(x + 18, y + 16); g.lineTo(x + 50, y + 48); g.stroke();
  // seat belt icon
  g.beginPath(); g.moveTo(x + 84, y + 20); g.lineTo(x + 84, y + 48); g.lineTo(x + 124, y + 48); g.stroke();
  g.fillRect(x + 92, y + 34, 26, 6); g.fillRect(x + 101, y + 30, 8, 14);
  put('psuSigns', x, y, 140, 64);
  // Door placard: red handle arrow
  x = 850;
  g.fillStyle = '#eceae4'; g.fillRect(x, y, 170, 90);
  g.fillStyle = '#c81e1e'; g.font = font(17, 800); g.textAlign = 'center';
  g.fillText('EMERGENCY EXIT', x + 85, y + 18);
  g.strokeStyle = '#c81e1e'; g.lineWidth = 7; g.beginPath(); g.arc(x + 85, y + 62, 22, Math.PI * 1.05, Math.PI * 1.95); g.stroke();
  g.beginPath(); g.moveTo(x + 104, y + 44); g.lineTo(x + 115, y + 60); g.lineTo(x + 97, y + 60); g.closePath(); g.fillStyle = '#c81e1e'; g.fill();
  g.font = font(15, 800); g.fillText('OPEN', x + 85, y + 84);
  put('doorPlacard', x, y, 170, 90);
  // Crew rest door
  x = 330; y = 80;
  g.fillStyle = '#e7e4dd'; g.fillRect(x, y, 200, 60);
  g.fillStyle = '#2a2f37'; g.font = font(22, 800); g.textAlign = 'center';
  g.fillText('CREW REST', x + 100, y + 24); g.font = font(14, 600); g.fillText('CREW ONLY', x + 100, y + 46);
  put('crew', x, y, 200, 60);
  // Bassinet placard
  x = 540;
  g.fillStyle = '#d9d6cf'; g.fillRect(x, y, 90, 60);
  g.strokeStyle = '#5d6570'; g.lineWidth = 4; g.strokeRect(x + 16, y + 20, 58, 22);
  g.beginPath(); g.arc(x + 45, y + 20, 14, Math.PI, 0); g.stroke();
  put('bassinet', x, y, 90, 60);
  // Galley label strip (small placards)
  x = 640;
  g.fillStyle = '#1b1f25'; g.fillRect(x, y, 200, 40);
  g.fillStyle = '#9aa3ad'; g.font = font(16, 700); g.fillText('G  ·  OVEN  ·  CHILLER', x + 100, y + 22);
  put('galleyLbl', x, y, 200, 40);
  // Flight deck door keypad panel
  x = 850;
  g.fillStyle = '#2b3038'; g.fillRect(x, y, 80, 100);
  for (let r = 0; r < 4; r++) for (let c = 0; c < 3; c++) { g.fillStyle = '#56606c'; g.fillRect(x + 12 + c * 20, y + 16 + r * 20, 14, 14); }
  put('keypad', x, y, 80, 100);

  // ---- Row placards (bin edge): "27  A C" grouped by seat block (left / centre / right) ----
  const rows = [...new Set(layout.seats.map((s) => s.row))].sort((a, b) => a - b);
  const PW = 76, PH = 30;
  let px = 330, py = 190;
  for (const r of rows) {
    const rs = layout.seats.filter((s) => s.row === r);
    const groups = [rs.filter((s) => s.x < -1.1), rs.filter((s) => Math.abs(s.x) <= 1.1), rs.filter((s) => s.x > 1.1)].map((gr) => gr.map((s) => s.letter).sort());
    groups.forEach((gr, i) => {
      if (!gr.length) return;
      if (px + PW > S) { px = 330; py += PH + 2; }
      g.fillStyle = '#2a3140'; g.fillRect(px, py, PW, PH);
      g.fillStyle = '#eef2f7'; g.textAlign = 'left'; g.textBaseline = 'middle';
      g.font = font(19, 800); g.fillText(String(r), px + 5, py + PH / 2 + 1);
      g.font = font(12, 700); g.fillText(gr.join(' '), px + (r >= 10 ? 32 : 22), py + PH / 2 + 1);
      put(`row${r}_${i}`, px, py, PW, PH);
      px += PW + 2;
    });
  }
  // ---- seat number plaques on the First / Business shells ----
  px = 330; py += PH + 8;
  for (const s of layout.seats.filter((q) => q.cls === 'J' || q.cls === 'F')) {
    if (px + 50 > S) { px = 330; py += 28; }
    g.fillStyle = '#3a3531'; g.fillRect(px, py, 50, 26);
    g.fillStyle = '#efe7da'; g.font = font(16, 600); g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(s.id, px + 25, py + 14);
    put('tag' + s.id, px, py, 50, 26);
    px += 52;
  }
  // ---- washi-paper panel (backlit bar screens): fibres on warm white ----
  py += 34; px = 330;
  {
    const WS = 128;
    const img = g.createImageData(WS, WS);
    const rnd = mulberry32(99);
    const fib = new Float32Array(WS * WS);
    for (let f = 0; f < 260; f++) {
      let fx = rnd() * WS, fy = rnd() * WS, a = rnd() * Math.PI * 2;
      const len = 10 + rnd() * 40, wgt = 0.25 + rnd() * 0.5;
      for (let t = 0; t < len; t++) {
        a += (rnd() - 0.5) * 0.35; fx += Math.cos(a); fy += Math.sin(a);
        const ix = ((Math.round(fx) % WS) + WS) % WS, iy = ((Math.round(fy) % WS) + WS) % WS;
        fib[iy * WS + ix] += wgt;
      }
    }
    for (let j = 0; j < WS; j++) for (let i = 0; i < WS; i++) {
      const n = fbm(i / 16, j / 16, 8, 4, 5) * 0.5 + 0.5;
      const v = clamp(0.80 + 0.12 * n - 0.10 * Math.min(1, fib[j * WS + i]), 0, 1);
      const k = (j * WS + i) * 4;
      img.data[k] = 255 * v; img.data[k + 1] = 246 * v; img.data[k + 2] = 226 * v; img.data[k + 3] = 255;
    }
    g.putImageData(img, px, py);
    put('washi', px, py, WS, WS);
  }
  ATL.canvas = cv;
  return ATL;
}

function drawPerson(g, cx, cy, skirt, col) {
  g.fillStyle = col;
  g.beginPath(); g.arc(cx, cy - 17, 6, 0, Math.PI * 2); g.fill();
  if (skirt) { g.beginPath(); g.moveTo(cx - 5, cy - 9); g.lineTo(cx + 5, cy - 9); g.lineTo(cx + 11, cy + 8); g.lineTo(cx - 11, cy + 8); g.closePath(); g.fill(); g.fillRect(cx - 5, cy + 8, 3, 13); g.fillRect(cx + 2, cy + 8, 3, 13); }
  else { g.fillRect(cx - 7, cy - 9, 14, 17); g.fillRect(cx - 6, cy + 8, 5, 13); g.fillRect(cx + 1, cy + 8, 5, 13); }
}

// Seatback screen content. v: 0/1 moving map, 2 welcome, 3 film still (abstract)
function drawScreen(g, x, y, w, h, v) {
  g.save();
  g.beginPath(); g.rect(x, y, w, h); g.clip();
  if (v <= 1) {
    const img = g.createImageData(w, h);
    const zoom = v === 0 ? 1 : 2.2;
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      const u = (i / w) * 6 / zoom + (v ? 1.7 : 0), t = (j / h) * 3.4 / zoom + (v ? 0.6 : 0);
      const n = fbm(u, t, 64, 5, 777) + 0.18 * Math.sin(u * 0.9) - 0.12 * Math.cos(t * 1.3);
      const land = n > 0.56;
      const k = (j * w + i) * 4;
      let c;
      if (land) {
        const e = clamp((n - 0.56) * 5, 0, 1);
        c = [lerp(72, 150, e), lerp(98, 132, e), lerp(76, 96, e)];
        if (n < 0.575) c = [190, 205, 190];
      } else {
        const d = clamp((0.56 - n) * 4, 0, 1);
        c = [lerp(34, 12, d), lerp(78, 36, d), lerp(128, 84, d)];
      }
      img.data[k] = c[0]; img.data[k + 1] = c[1]; img.data[k + 2] = c[2]; img.data[k + 3] = 255;
    }
    g.putImageData(img, x, y);
    // graticule
    g.strokeStyle = 'rgba(200,220,255,0.15)'; g.lineWidth = 1;
    for (let i = 1; i < 6; i++) { g.beginPath(); g.moveTo(x + (i * w) / 6, y); g.lineTo(x + (i * w) / 6, y + h); g.stroke(); }
    for (let j = 1; j < 4; j++) { g.beginPath(); g.moveTo(x, y + (j * h) / 4); g.lineTo(x + w, y + (j * h) / 4); g.stroke(); }
    // route
    const ax = x + w * 0.12, ay = y + h * 0.62, bx = x + w * 0.88, by = y + h * 0.5, cx = x + w * 0.5, cy = y + h * 0.12;
    g.setLineDash([6, 5]); g.strokeStyle = 'rgba(255,255,255,0.75)'; g.lineWidth = 2.5;
    g.beginPath(); g.moveTo(ax, ay); g.quadraticCurveTo(cx, cy, bx, by); g.stroke(); g.setLineDash([]);
    const tt = v === 0 ? 0.58 : 0.5;
    const qx = (1 - tt) * (1 - tt) * ax + 2 * (1 - tt) * tt * cx + tt * tt * bx, qy = (1 - tt) * (1 - tt) * ay + 2 * (1 - tt) * tt * cy + tt * tt * by;
    g.strokeStyle = '#ffd24a'; g.lineWidth = 3.5; g.beginPath(); g.moveTo(ax, ay);
    for (let s = 0; s <= 30; s++) { const q = (s / 30) * tt; g.lineTo((1 - q) * (1 - q) * ax + 2 * (1 - q) * q * cx + q * q * bx, (1 - q) * (1 - q) * ay + 2 * (1 - q) * q * cy + q * q * by); }
    g.stroke();
    g.fillStyle = '#ffffff'; g.save(); g.translate(qx, qy); g.rotate(0.12);
    g.beginPath(); g.moveTo(10, 0); g.lineTo(-7, -9); g.lineTo(-4, 0); g.lineTo(-7, 9); g.closePath(); g.fill(); g.restore();
    for (const [px, py] of [[ax, ay], [bx, by]]) { g.fillStyle = '#ffffff'; g.beginPath(); g.arc(px, py, 4, 0, Math.PI * 2); g.fill(); }
    g.fillStyle = 'rgba(6,14,28,0.78)'; g.fillRect(x, y + h - 30, w, 30);
    g.fillStyle = '#e7eefb'; g.font = '600 13px Helvetica, Arial, sans-serif'; g.textAlign = 'left'; g.textBaseline = 'middle';
    g.fillText(v === 0 ? 'ALT 38,000 ft    GS 561 mph    −52°C' : 'Time to destination 6:48', x + 10, y + h - 15);
  } else if (v === 2) {
    const gr = g.createLinearGradient(x, y, x + w, y + h);
    gr.addColorStop(0, '#0b2a5c'); gr.addColorStop(0.6, '#1b4f9c'); gr.addColorStop(1, '#3f86d4');
    g.fillStyle = gr; g.fillRect(x, y, w, h);
    g.strokeStyle = 'rgba(255,255,255,0.18)'; g.lineWidth = 2;
    for (let i = 0; i < 7; i++) { g.beginPath(); g.ellipse(x + w * 0.75, y + h * 1.1, 60 + i * 26, 30 + i * 16, 0, Math.PI, Math.PI * 2); g.stroke(); }
    g.fillStyle = '#ffffff'; g.font = '700 26px Helvetica, Arial, sans-serif'; g.textAlign = 'left'; g.textBaseline = 'alphabetic';
    g.fillText('Welcome aboard', x + 18, y + 72);
    g.font = '500 14px Helvetica, Arial, sans-serif'; g.fillStyle = 'rgba(255,255,255,0.8)';
    g.fillText('Movies  ·  TV  ·  Music  ·  Map', x + 18, y + 98);
    for (let i = 0; i < 4; i++) { g.fillStyle = `rgba(255,255,255,${0.12 + i * 0.05})`; g.fillRect(x + 18 + i * 72, y + 120, 64, 40); }
  } else {
    const gr = g.createLinearGradient(x, y, x, y + h);
    gr.addColorStop(0, '#f2a15a'); gr.addColorStop(0.5, '#b8485c'); gr.addColorStop(1, '#2a1d46');
    g.fillStyle = gr; g.fillRect(x, y, w, h);
    g.fillStyle = '#ffe2a8'; g.beginPath(); g.arc(x + w * 0.62, y + h * 0.48, 26, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#1c1530';
    g.beginPath(); g.moveTo(x, y + h); g.lineTo(x, y + h * 0.7);
    for (let i = 0; i <= 16; i++) g.lineTo(x + (i / 16) * w, y + h * (0.7 - 0.12 * Math.abs(Math.sin(i * 1.7))));
    g.lineTo(x + w, y + h); g.closePath(); g.fill();
    g.fillStyle = 'rgba(0,0,0,0.55)'; g.fillRect(x, y + h - 16, w, 16);
    g.fillStyle = '#ffffff'; g.fillRect(x + 10, y + h - 9, w * 0.42, 3);
  }
  g.restore();
}

// Map a quad's uv (0..1, v up) into an atlas rect
function atlasUV(name) {
  const r = ATL.rects[name];
  return (k, g) => [r[0] + g.u[k * 2] * (r[2] - r[0]), r[1] + (1 - g.u[k * 2 + 1]) * (r[3] - r[1])];
}
