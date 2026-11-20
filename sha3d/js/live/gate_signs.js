// forked from sfo3d@e3218d6 js/live/signs.js (SIGN_VS / SIGN_FS and makeAtlas only)
// Sign faces of the gates package (js/live/gate_system.js): CAAC stand-number signs and the VDGS display text, drawn into
// one texture atlas, and the 'gsign' program that renders them (lit faces glow at night: internal lighting).
// sha3d changes: no FAA airfield signs here (sfo3d's mandatory / location / direction faces and its gate-number panels
// are dropped - the airfield signs belong to the markings package); program renamed 'gsign' so it cannot clash with the
// markings package's own sign program; face kinds:
//  - 'stand': CAAC MH 5001-2021 8.5 stand-number sign (机位号码标记牌): yellow background, black characters (8.5.4),
//    internally lit (8.5.4: 宜采用内部照明方式), the face shows the stand number only (8.5.5 / 8.5.8; the optional
//    latitude / longitude line is left out). Proportions (8.5.6, sign without lat / lon): horizontal margin >= 1/20 of the
//    face height, vertical margin >= 1/5 of the face height - so the numerals fill 0.55 of the face height here (<= 0.6;
//    the bridge-mounted prism faces of 8.5.8 want 1/2-3/4: 0.55 meets both). Numeral height on the apron: the caller sizes
//    the face (>= 600 mm numerals, 8.5.6). Colours from the standard's words (yellow / black); the exact CAAC colour
//    coordinates (app. I) are not transcribed: the sRGB values below are inf.
//  - 'vdgs': the docking display (MH 5001-2021 9.4 / 9.5: azimuth guidance and stop indication; an advanced VDGS shows the
//    aircraft type, 9.5.7): amber characters on black. The make and the display layout at ZSSS are unknown: inf.
import { gl } from '../gl.js';

export const GSIGN_VS = `
#include <common>
#include <vout>
layout(location=0) in vec3 aPos; layout(location=1) in vec3 aNrm; layout(location=2) in vec2 aUV; layout(location=4) in vec4 aExtra;
out vec3 vWP; out vec3 vN; out vec2 vUV; out vec4 vX;
void main(){ vWP = aPos; vN = aNrm; vUV = aUV; vX = aExtra; emitClip(aPos, aPos); }`;
export const GSIGN_FS = `
#include <common>
#include <shadow>
#include <fout>
in vec3 vWP; in vec3 vN; in vec2 vUV; in vec4 vX; // vX.x: 1 = sign face (lit), 0 = housing; vX.y: emissive scale (0 = 1.6)
uniform sampler2D uAtlas; uniform float uNight;
void main(){
  vec3 wp = vWP; vec3 V = uCamPos - wp; float dist = length(V); V /= dist;
  vec3 N = normalize(vN); if (dot(N, V) < 0.0) N = -N;
  vec3 alb; float rough = 0.6; vec3 emis = vec3(0);
  if (vX.x > 0.5) { alb = texture(uAtlas, vUV).rgb; rough = 0.35; emis = alb * mix(0.04, 1.0, uNight) * (vX.y > 0.0 ? vX.y : 1.6); }
  else { alb = vec3(0.05); rough = 0.5; }
  float sh = getShadow(wp, N, dist) * cloudShadow(wp);
  vec3 col = shadePBR(alb, N, V, rough, 0.0, sh, 1.0, 1.0) + emis;
  col = applyFog(col, wp);
  writeOut(col, wp, 1.0);
}`;

// colours (inf: from the standard's words, not its colour table)
export const STAND_SIGN = { bg: '#f2c40c', fg: '#0a0a0a', textFrac: 0.55, marginH: 1 / 20 };
const VDGS = { bg: '#050505', fg: '#ffb020' };

// faces: [{key, kind: 'stand' | 'vdgs', text}] -> {tex: {tex}, map: {key: {u0, v0, u1, v1, aspect}}}
export function makeGateAtlas(faces) {
  const Hf = 128, pad = 4, Wmax = 2048;
  const cv = document.createElement('canvas'); const cx = cv.getContext('2d');
  // numerals: a narrow sans (CAAC app. H gives the character shapes; not transcribed - inf)
  const font = (px, kind) => kind === 'vdgs' ? `bold ${px}px "Courier New", ui-monospace, monospace` : `bold ${px}px "Arial Narrow", "Liberation Sans Narrow", Arial, Helvetica, sans-serif`;
  // font size whose digit height is textFrac of the face (digit / cap height of these faces ~0.72 em)
  const standPx = Math.round(Hf * STAND_SIGN.textFrac / 0.72), vdgsPx = 70;
  const place = []; let x = pad, y = pad, rowH = 0;
  for (const f of faces) {
    cx.font = font(f.kind === 'stand' ? standPx : vdgsPx, f.kind);
    const tw = cx.measureText(f.text).width;
    // stand: horizontal margins of 1/20 face height minimum; 0.18 of the height is used (a fuller plate, as the photos)
    const w = Math.ceil(f.kind === 'stand' ? tw + 2 * Math.max(Hf * STAND_SIGN.marginH, Hf * 0.18) : tw + 44), h = Hf;
    if (x + w + pad > Wmax) { x = pad; y += rowH + pad; rowH = 0; }
    place.push({ ...f, x, y, w, h }); x += w + pad; rowH = Math.max(rowH, h);
  }
  const Ht = Math.pow(2, Math.ceil(Math.log2(Math.max(4, y + rowH + pad))));
  cv.width = Wmax; cv.height = Ht;
  cx.textAlign = 'center'; cx.textBaseline = 'middle';
  for (const f of place) {
    const st = f.kind === 'stand';
    cx.fillStyle = st ? STAND_SIGN.bg : VDGS.bg; cx.fillRect(f.x, f.y, f.w, f.h);
    cx.fillStyle = st ? STAND_SIGN.fg : VDGS.fg; cx.font = font(st ? standPx : vdgsPx, f.kind);
    if (!st) { cx.shadowColor = '#ff9a00'; cx.shadowBlur = 10; }
    cx.fillText(f.text, f.x + f.w / 2, f.y + f.h / 2 + (st ? 2 : 3)); cx.shadowBlur = 0;
  }
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  const levels = Math.floor(Math.log2(Math.max(Wmax, Ht))) + 1;
  gl.texStorage2D(gl.TEXTURE_2D, levels, gl.SRGB8_ALPHA8, Wmax, Ht);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, gl.RGBA, gl.UNSIGNED_BYTE, cv);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.generateMipmap(gl.TEXTURE_2D);
  const e = gl.getExtension('EXT_texture_filter_anisotropic'); if (e) gl.texParameterf(gl.TEXTURE_2D, e.TEXTURE_MAX_ANISOTROPY_EXT, 8);
  const map = {}; for (const f of place) map[f.key] = { u0: f.x / Wmax, v0: f.y / Ht, u1: (f.x + f.w) / Wmax, v1: (f.y + f.h) / Ht, aspect: f.w / f.h };
  cv.width = cv.height = 1;
  return { tex: { tex: t }, map };
}
