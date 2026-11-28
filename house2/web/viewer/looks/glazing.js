// Look module "glazing": glass, window / door frames and door hardware (see ../materials.js for the contract).
// Geometry comes from model/openings.py.  Door PAINTS (door_navy, door_wood, door_garage) are the surfaces family's.
//
// GLASS  -- one opaque shader, no extra passes, no textures:
//   * behind the pane a ROOM is ray-cast in the fragment shader (interior mapping): back wall with a doorway and a
//     picture, side walls, wood floor, ceiling with down-lights, a sofa, a low table, a lit lamp, sometimes a
//     roller shade half down.  It has parallax, and it is a different room per opening.
//   * over it a Fresnel REFLECTION of the surroundings: the sky of the image-based light, a procedural tree line
//     and ground (the env map holds the sky only), the sun's glint; the pane's normal wobbles a little, as
//     insulated units do, so neighbouring panes do not mirror as one sheet.
//   * DAY: the room is dim (daylight falling in through the opening + its lamps at a tenth), so the reflection
//     dominates; DUSK: the lamps are on and the rooms glow warm (p01: lit panes read sRGB ~ (247, 206, 144),
//     the warmest (211, 159, 68)), the reflection is a faint veil.
//   * a roller shade is real diffuse fabric behind the glass: sunlit and shadowed by day, back-lit at dusk.
//   The pane's place in its room is packed into its UVs by openings.py (_GlassCode):
//       u = 0.25 + x + 16 * (seed % 32 + 32 * wcode)          x: metres along the unit
//       v = 0.25 + z + 8 * (shade + 10 * room + 40 * hcode)   z: metres above the room's floor
//   wcode = unit width / 0.5, hcode = (head height - 1.9) / 0.05, shade: 0 automatic, 1 none, n: (n - 1) * 0.3 m down,
//   room: 0 living, 1 bare (garage), 2 dark (lights off), 3 hall.
// The room is evaluated at 4 sub-pixel positions (1 on the low tier): its edges are procedural, MSAA does not see them.

const PARS_VERTEX = /* glsl */`
varying vec2 vGlzUv;
varying vec3 vGlzW;
varying vec3 vGlzN;
`;

const MAIN_VERTEX = /* glsl */`
  vGlzUv = uv;
  vGlzW = (modelMatrix * vec4(position, 1.0)).xyz;
  vGlzN = normalize(mat3(modelMatrix) * normal);
`;

const PARS_FRAGMENT = /* glsl */`
uniform float uGlzDusk;      // 0 day, 1 dusk
uniform float uGlzEnvK;      // 1 / gain of the image-based light: reflections match the sky as it looks
varying vec2 vGlzUv;
varying vec3 vGlzW;
varying vec3 vGlzN;

float glzH(float n) { return fract(sin(n * 91.3458) * 47453.5453); }
float glzH2(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float glzN2(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(glzH2(i), glzH2(i + vec2(1.0, 0.0)), f.x), mix(glzH2(i + vec2(0.0, 1.0)), glzH2(i + vec2(1.0, 1.0)), f.x), f.y);
}
float glzF2(vec2 p) { return 0.5 * glzN2(p) + 0.27 * glzN2(p * 2.07 + 13.1) + 0.15 * glzN2(p * 4.13 + 5.7) + 0.08 * glzN2(p * 8.3 + 1.9); }

// ray / box (slab test): distance to the entry point or -1; m = 1 on the axis that was hit
float glzBox(vec3 ro, vec3 inv, vec3 lo, vec3 hi, out vec3 m) {
  vec3 t0 = (lo - ro) * inv, t1 = (hi - ro) * inv;
  vec3 tn = min(t0, t1), tf = max(t0, t1);
  float a = max(tn.x, max(tn.y, tn.z)), b = min(tf.x, min(tf.y, tf.z));
  m = step(vec3(a), tn);
  return (a > b || a < 0.0) ? -1.0 : a;
}

// The room behind a pane.  ro = (x along the unit, height above the floor, 0), rd = view ray (x right, y up,
// z into the room), both in metres.  Returns the radiance seen through the glass in rgb and, in a, how much of
// the pixel is roller shade (lit as a diffuse surface by the caller).
vec4 glzRoom(vec3 ro, vec3 rd, float seed, float W, float head, float kind, float shade, vec3 skyAmb, float aa) {
  float h1 = glzH(seed + 0.13), h2 = glzH(seed * 1.7 + 2.31), h3 = glzH(seed * 2.3 + 4.57), h4 = glzH(seed * 3.1 + 6.11);
  float h5 = glzH(seed * 4.3 + 8.23), h6 = glzH(seed * 5.9 + 9.71), h7 = glzH(seed * 6.7 + 11.3), h8 = glzH(seed * 7.9 + 13.7);
  bool bare = kind > 0.5 && kind < 1.5, dark = kind > 1.5 && kind < 2.5, hall = kind > 2.5;
  float H = bare ? 2.95 : head + 0.40 + 0.30 * h1;                       // ceiling
  float D = bare ? 6.2 : (hall ? 2.6 + 1.8 * h2 : 3.6 + 2.8 * h2);       // depth
  float xL = -(0.5 + 1.6 * h3), xR = W + 0.5 + 1.6 * h4;                 // side walls
  // lamps: colour and level of the lit walls at dusk (scene-referred, measured on p01)
  vec3 lampCol = bare ? vec3(1.0, 0.66, 0.24) : mix(vec3(1.0, 0.67, 0.27), vec3(1.0, 0.54, 0.12), h5 * h5);
  float lampK = dark ? 0.0 : (bare ? 2.0 : 0.95 + 0.80 * h6) * mix(0.03, 1.0, uGlzDusk);
  vec3 lamp = lampCol * lampK;

  vec3 d = rd;
  d += step(abs(d), vec3(1e-5)) * 1e-5;
  vec3 inv = 1.0 / d;
  float tx = ((d.x > 0.0 ? xR : xL) - ro.x) * inv.x;
  float ty = ((d.y > 0.0 ? H : 0.0) - ro.y) * inv.y;
  float tz = D * inv.z;
  float t = min(tx, min(ty, tz));
  vec3 hp = ro + d * t;
  float fp = aa * (1.0 + t * 0.35);                                      // footprint of a pixel at the hit, metres
  vec3 wallAlb = bare ? vec3(0.74, 0.74, 0.72) : vec3(0.86, 0.84, 0.79);
  vec3 alb = wallAlb, glow = vec3(0.0);
  float lit = 1.0, day = 0.045 + 0.34 * exp(-hp.z * 0.55);
  if (t == tz) {                                                         // back wall
    float u = hp.x, v = hp.y;
    lit = 0.62 + 0.38 * smoothstep(0.0, H, v) + 0.22 * exp(-(H - v) * 1.7) * (0.5 + 0.5 * cos(6.2832 * (u / 1.25 + h1)));
    lit *= 1.0 - 0.22 * exp(-min(min(v, H - v), min(u - xL, xR - u)) * 3.0);
    // a doorway into the next room
    float dx0 = mix(xL + 0.45, xR - 1.5, h7), dw = bare ? 0.9 : 0.95, dh = 2.15;
    float inD = smoothstep(-fp, fp, min(min(u - dx0, dx0 + dw - u), dh - v));
    float inC = smoothstep(-fp, fp, min(min(u - dx0 + 0.075, dx0 + dw + 0.075 - u), dh + 0.075 - v));
    float nextK = bare ? 0.25 : 0.25 + 1.05 * h8;
    vec3 through = h8 > 0.6 && !bare ? mix(vec3(0.46, 0.54, 0.44) * 1.1, vec3(0.05, 0.06, 0.10), uGlzDusk) : vec3(0.0);
    lit = mix(lit, mix(lit * 1.06, nextK * (0.75 + 0.25 * v / dh), inD), inC);
    alb = mix(alb, vec3(0.80, 0.78, 0.72), inD);
    glow += through * inD * smoothstep(0.9, 1.0, v) * (1.0 - smoothstep(dh - 0.25, dh - 0.2, v)) * step(abs(u - dx0 - dw * 0.5), dw * 0.32);
    // a framed picture on the other half of the wall
    if (!bare) {
      float pc = mix(xL + 0.9, xR - 0.9, fract(h7 + 0.5)), pw = 0.32 + 0.3 * h8, ph = 0.34 + 0.12 * h2;
      float e = max(abs(u - pc) - pw, abs(v - 1.55) - ph);
      float fr = smoothstep(fp, -fp, e) * (1.0 - inC);
      float inn = smoothstep(fp, -fp, e + 0.035) * (1.0 - inC);
      vec3 art = mix(vec3(0.56, 0.50, 0.41), vec3(0.11, 0.10, 0.09), smoothstep(0.42, 0.58, glzN2(vec2(u, v) * 3.1 + seed)));
      alb = mix(alb, vec3(0.03), fr);
      alb = mix(alb, art, inn);
    }
  } else if (t == tx) {                                                  // side wall
    float u = hp.z, v = hp.y;
    lit = 0.58 + 0.38 * smoothstep(0.0, H, v) + 0.2 * exp(-(H - v) * 1.7) * (0.5 + 0.5 * cos(6.2832 * (u / 1.25 + h2)));
    lit *= 1.0 - 0.22 * exp(-min(min(v, H - v), D - u) * 3.0);
  } else if (d.y > 0.0) {                                                // ceiling with its down-lights
    alb = vec3(0.90, 0.89, 0.86);
    lit = 0.80;
    day *= 0.7;
    vec2 g = vec2(hp.x - xL, hp.z) / 1.25 + vec2(h3, 0.35);
    vec2 c = (fract(g) - 0.5) * 1.25;
    float r = length(c);
    glow += lampCol * (dark ? 0.0 : mix(1.1, 7.0, uGlzDusk)) * smoothstep(0.065 + fp, 0.065 - fp, r) * min(1.0, 0.065 / max(fp, 0.065));
    lit += 0.35 * exp(-r * r * 9.0);
  } else {                                                               // floor: oak boards running into the room
    float pl = floor(hp.x / 0.19);
    alb = vec3(0.44, 0.31, 0.19) * (0.86 + 0.28 * glzH(pl * 1.31 + seed)) * (bare ? vec3(0.9, 1.05, 1.3) : vec3(1.0));
    lit = 0.50 + 0.14 * cos(6.2832 * (hp.x - xL) / 1.25 + 6.2832 * h3) * cos(6.2832 * hp.z / 1.25 + 2.2);
    lit *= 1.0 - 0.25 * exp(-min(min(hp.x - xL, xR - hp.x), D - hp.z) * 3.0);
    day *= 1.5;
  }
  // furniture
  vec3 m;
  float tb;
  if (!bare) {
    float sx = mix(xL + 0.3, xR - 2.5, h8), sz = hall ? D - 0.5 : D - 1.75;
    if (!hall) {
      tb = glzBox(ro, inv, vec3(sx, 0.0, sz), vec3(sx + 2.2, 0.70, sz + 1.0), m);              // sofa: seat
      if (tb > 0.0 && tb < t) { t = tb; alb = vec3(0.80, 0.76, 0.68); lit = 0.42 + 0.34 * m.y + 0.10 * m.z; day = 0.045 + 0.34 * exp(-sz * 0.55); glow = vec3(0.0); }
      tb = glzBox(ro, inv, vec3(sx, 0.0, sz + 0.72), vec3(sx + 2.2, 1.02, sz + 1.0), m);       // ... and back
      if (tb > 0.0 && tb < t) { t = tb; alb = vec3(0.80, 0.76, 0.68); lit = 0.46 + 0.30 * m.y + 0.10 * m.z; day = 0.045 + 0.34 * exp(-sz * 0.55); glow = vec3(0.0); }
      float tx0 = mix(xL + 0.6, xR - 1.9, h3);
      tb = glzBox(ro, inv, vec3(tx0, 0.0, 1.25), vec3(tx0 + 1.25, 0.43, 1.95), m);            // low table
      if (tb > 0.0 && tb < t) { t = tb; alb = vec3(0.10, 0.075, 0.055); lit = 0.4 + 0.5 * m.y; day = 0.16; glow = vec3(0.0); }
    } else {
      tb = glzBox(ro, inv, vec3(sx + 0.3, 0.0, D - 0.45), vec3(sx + 1.7, 0.86, D), m);        // console
      if (tb > 0.0 && tb < t) { t = tb; alb = vec3(0.09, 0.07, 0.055); lit = 0.4 + 0.5 * m.y; day = 0.12; glow = vec3(0.0); }
    }
    float lx = h5 > 0.5 ? sx + 2.35 : sx - 0.6, lz = D - 0.75;
    tb = glzBox(ro, inv, vec3(lx, 1.22, lz - 0.19), vec3(lx + 0.38, 1.58, lz + 0.19), m);     // lamp shade
    if (tb > 0.0 && tb < t) { t = tb; alb = vec3(0.85, 0.80, 0.70); lit = 0.6; day = 0.1; glow = lampCol * (dark ? 0.0 : mix(0.35, 2.6, uGlzDusk)); }
    tb = glzBox(ro, inv, vec3(lx + 0.17, 0.0, lz - 0.02), vec3(lx + 0.21, 1.22, lz + 0.02), m);   // ... and its stem
    if (tb > 0.0 && tb < t) { t = tb; alb = vec3(0.05); lit = 0.5; day = 0.1; glow = vec3(0.0); }
  } else {
    tb = glzBox(ro, inv, vec3(xR - 0.55, 0.0, 1.2), vec3(xR, 1.95, 5.2), m);                  // garage shelving
    if (tb > 0.0 && tb < t) { t = tb; alb = vec3(0.30, 0.30, 0.31); lit = 0.45 + 0.3 * m.y; day = 0.1; glow = vec3(0.0); }
  }
  vec3 col = alb * (lamp * lit + skyAmb * day) + glow;

  // roller shade: explicit length, or a few of the automatic seeds
  float L = shade > 0.5 ? (shade - 1.0) * 0.3 : (glzH(seed * 9.7 + 3.3) > 0.82 ? 0.4 + 1.0 * glzH(seed * 11.3 + 5.1) : 0.0);
  float zs = head - L;
  float blind = L > 0.01 ? smoothstep(zs - aa, zs + aa, ro.y) : 0.0;
  float hem = 1.0 - 0.45 * (1.0 - smoothstep(zs + 0.028 - aa, zs + 0.028 + aa, ro.y));
  vec3 back = lamp * vec3(1.0, 0.93, 0.80) * 0.46 * hem;                 // fabric back-lit by the room
  return vec4(mix(col, back, blind), blind * hem);
}

// Rounded crowns side by side round the horizon.  x = azimuth in cells (N cells per turn, periodic); returns the
// crown line 0..1 with u = the place across the winning crown (-1..1) and id = its cell.
float glzCrowns(float x, float N, float sd, out float u, out float id) {
  float best = 0.0, xf = floor(x);
  u = 0.0; id = 0.0;
  for (int k = -1; k <= 1; k++) {
    float c = xf + float(k), ci = mod(c, N);
    float r1 = glzH(ci * 1.71 + sd), r2 = glzH(ci * 2.93 + sd + 3.1), r3 = glzH(ci * 4.17 + sd + 7.3);
    float uu = (x - (c + 0.5 + (r1 - 0.5) * 0.7)) / (0.5 + 0.6 * r2);
    float e = (0.3 + 0.7 * r3) * (r3 > 0.8 ? max(0.0, 1.0 - abs(uu) * 1.6) * 1.25 : sqrt(max(0.0, 1.0 - uu * uu)));
    if (e > best) { best = e; u = uu; id = ci; }
  }
  return best;
}

// What a pane mirrors: the sky of the image-based light, a line of trees (round crowns, a few conifers, the fresh
// greens of spring), neighbouring houses between them, a clipped screen and hedge at their foot, lawn and paving below.
vec3 glzWorld(vec3 P, vec3 R, vec3 sunDir, vec3 sunCol, vec3 skyAmb, float aa, float tk) {
  vec3 col = vec3(0.0);
  #ifdef ENVMAP_TYPE_CUBE_UV
    col = textureCubeUV(envMap, normalize(vec3(R.x, max(R.y, 0.0), R.z)), 0.02).rgb * uGlzEnvK;
  #endif
  col = max(mix(vec3(dot(col, vec3(0.2126, 0.7152, 0.0722))), col, 1.0 + 0.6 * (1.0 - uGlzDusk)), 0.0);   // the lighting sky is greyer than the sky looks
  float hl = max(length(R.xz), 1e-4);
  vec2 Rh = R.xz / hl;
  float tn = R.y / hl;                                                   // tangent of the elevation
  vec3 sunE = sunCol * 0.3183;
  vec3 flatL = sunE * max(sunDir.y, 0.0) + skyAmb;                       // light on the ground
  float side = dot(sunDir.xz, vec2(-Rh.y, Rh.x));                        // sun to the left / right of what is mirrored
  float front = 0.2 + 0.8 * smoothstep(-0.4, 0.6, dot(-Rh, sunDir.xz));  // ... and how much it faces the sun
  float xa = (atan(Rh.y, Rh.x) + dot(P.xz, vec2(0.006, 0.004))) / 6.2832;  // turns; shifts with the pane (parallax)
  float fine = smoothstep(0.03, 0.006, aa);
  // large trees
  float u1, id1;
  float c1 = glzCrowns(xa * 34.0, 34.0, 1.0, u1, id1);
  float sk = (0.05 + 0.40 * c1) * tk + 0.03 * fine * (glzF2(vec2(xa * 700.0, tn * 30.0)) - 0.5);
  float tree = (1.0 - smoothstep(sk - aa, sk + aa, tn)) * step(0.02, c1);
  float v1 = clamp(tn / max(sk, 0.01), 0.0, 1.0);
  float clump = mix(0.5, glzF2(vec2(xa * 520.0, tn * 46.0) + id1), fine);
  float kind = glzH(id1 * 7.7 + 0.3);
  vec3 leaf = kind > 0.8 ? vec3(0.030, 0.062, 0.030) : mix(vec3(0.055, 0.105, 0.028), vec3(0.12, 0.20, 0.045), clump);
  leaf = mix(leaf, mix(vec3(0.20, 0.27, 0.05), vec3(0.15, 0.20, 0.06), step(0.55, kind)), step(0.36, kind) * step(kind, 0.66) * smoothstep(0.2, 0.55, clump));
  leaf = mix(vec3(dot(leaf, vec3(0.30, 0.59, 0.11))), leaf, tk);           // seen dimly in a dark pane: a grey-green
  float shade = clamp(0.25 + 0.55 * v1 + 0.30 * u1 * side, 0.08, 1.0) * (0.45 + 1.1 * clump);
  vec3 treeCol = leaf * (sunE * 2.4 * front * shade + skyAmb * (0.45 + 0.55 * v1));
  treeCol = mix(treeCol, col, 0.35 * fine * smoothstep(0.62, 0.8, clump) * smoothstep(0.35, 0.9, v1));   // sky through the crown
  col = mix(col, treeCol, tree);
  // neighbouring houses: a gabled box every other 30 degrees, white or blue-grey, dark roof, a row of windows
  float hx = xa * 12.0 + 0.37, hc = floor(hx), hi = mod(hc, 12.0), hf = hx - hc;
  float q1 = glzH(hi * 3.3 + 0.7), q2 = glzH(hi * 5.1 + 1.9), q3 = glzH(hi * 6.7 + 4.3);
  float hw = 0.2 + 0.2 * q2, du = abs(hf - 0.5) / hw, wallH = 0.085 + 0.05 * q3, ea = aa / (0.5236 * hw);
  float roofH = wallH + 0.085 * max(0.0, 1.0 - du) * (0.5 + 0.5 * q2);
  float inX = (1.0 - smoothstep(1.0 - ea, 1.0 + ea, du)) * step(0.4, q1);
  vec3 wallC = (q2 > 0.5 ? vec3(0.80, 0.79, 0.76) : vec3(0.31, 0.36, 0.41)) * (sunE * front + skyAmb);
  float sx = (hf - 0.5) / hw * 2.6, wy = tn / wallH;
  float win = (1.0 - smoothstep(0.26 - ea * 2.6, 0.26 + ea * 2.6, abs(fract(sx + 0.5) - 0.5))) * smoothstep(0.34 - aa * 8.0, 0.34 + aa * 8.0, wy) * (1.0 - smoothstep(0.74 - aa * 8.0, 0.74 + aa * 8.0, wy));
  wallC = mix(wallC, vec3(0.04, 0.05, 0.06) + 0.12 * skyAmb, win * fine);
  vec3 roofC = vec3(0.10, 0.10, 0.11) * (sunE * max(sunDir.y, 0.0) * 1.4 + skyAmb);
  col = mix(col, roofC, inX * (1.0 - smoothstep(roofH - aa, roofH + aa, tn)));
  col = mix(col, wallC, inX * (1.0 - smoothstep(wallH - aa, wallH + aa, tn)));
  // hedge and cedar fence at the foot
  float u2, id2;
  float c2 = glzCrowns(xa * 90.0 + 0.3, 90.0, 5.0, u2, id2);
  float fz = 0.062;
  vec3 fence = vec3(0.045, 0.08, 0.03) * (0.85 + 0.3 * glzH(floor(xa * 2600.0)) * fine) * (sunE * front + skyAmb);
  fence *= 1.0 - 0.5 * fine * (1.0 - smoothstep(0.0, 0.0012 + aa * 0.16, abs(fract(xa * 65.0) - 0.5)));          // posts
  col = mix(col, fence, (1.0 - smoothstep(fz - aa, fz + aa, tn)) * step(0.3, glzN2(vec2(xa * 9.0, 2.0))));
  float hk = 0.015 + 0.075 * c2 * step(0.45, glzH(id2 * 1.9 + 2.0));
  vec3 hedge = mix(vec3(0.035, 0.075, 0.025), vec3(0.085, 0.15, 0.04), mix(0.5, glzF2(vec2(xa * 900.0, tn * 80.0)), fine)) * (sunE * 2.0 * front * clamp(0.3 + 0.7 * tn / hk, 0.0, 1.0) + skyAmb * 0.7);
  col = mix(col, hedge, 1.0 - smoothstep(hk - aa, hk + aa, tn));
  // ground: lawn and paving
  vec2 gp = P.xz + R.xz * (P.y + 0.3) / max(-R.y, 0.03);
  float lawn = smoothstep(0.35, 0.65, glzN2(gp * 0.06 + 3.7));
  vec3 ground = mix(vec3(0.19, 0.20, 0.21), vec3(0.070, 0.125, 0.040), lawn) * flatL;
  col = mix(col, ground, 1.0 - smoothstep(-0.012 - aa, aa, tn));
  // the sun itself, where nothing hides it (day only: at dusk the "sun" light is the bright sky)
  float mu = max(dot(normalize(R), sunDir), 0.0);
  col += sunCol * (1.0 - uGlzDusk) * (1.0 - tree) * step(sk, tn) * (24.0 * smoothstep(0.99955, 0.99992, mu) + 0.35 * pow(mu, 220.0));
  return col;
}
`;

const MAIN_FRAGMENT = /* glsl */`
  vec3 glzSpec = vec3(0.0);
  {
    vec2 gE = vec2(vGlzUv.x, -vGlzUv.y);
    float gCu = floor(gE.x / 16.0), gCv = floor(gE.y / 8.0);
    vec2 gP = vec2(gE.x - gCu * 16.0 - 0.25, gE.y - gCv * 8.0 - 0.25);
    float gSeed = mod(gCu, 32.0), gWc = floor(gCu / 32.0 + 0.01);
    float gShade = mod(gCv, 10.0), gKind = mod(floor(gCv / 10.0 + 0.01), 4.0), gHc = floor(gCv / 40.0 + 0.01);
    float gW = gWc * 0.5, gHead = 1.9 + 0.05 * gHc;
    float gS = gSeed + 3.7 * gWc + 1.3 * gHc;                             // equal seeds still differ by size
    vec3 gNw = normalize(vGlzN);
    vec3 gT = normalize(cross(vec3(0.0, 1.0, 0.0), gNw));                 // "right" seen from outside
    float gPlain = step(gWc, 0.5), gUp = step(3.6, vGlzW.y);
    if (gWc < 0.5) {                                                      // a pane without the code in its UVs: no room to cast -- a dark interior by day, a warm glow at dusk
      float gx = dot(vGlzW, gT);
      gP = vec2(mod(gx, 4.0), vGlzW.y - mix(0.45, 3.75, gUp));
      gW = 4.0; gHead = 2.4; gShade = 1.0; gKind = 0.0;
      gS = mod(floor(gx / 4.0) * 3.0 + gUp * 11.0 + floor(gNw.x * 2.0 + 0.5) * 5.0 + floor(gNw.z * 2.0 + 0.5) * 13.0, 32.0);
    }
    vec3 gV = normalize(vGlzW - cameraPosition);
    vec3 gRd = vec3(dot(gV, gT), gV.y, max(-dot(gV, gNw), 0.02));
    vec2 gDx = dFdx(gP), gDy = dFdy(gP);
    float gAA = clamp(max(length(gDx), length(gDy)), 0.0005, 0.25);       // metres per pixel on the pane
    vec3 gSky = vec3(0.3);
    #ifdef ENVMAP_TYPE_CUBE_UV
      gSky = textureCubeUV(envMap, vec3(0.0, 1.0, 0.0), 1.0).rgb;
    #endif
    vec4 gRoom = vec4(0.0);
    #if GLZ_SS > 1
      vec3 gRx = dFdx(gRd), gRy = dFdy(gRd);
      for (int i = 0; i < 4; i++) {
        vec2 o = i == 0 ? vec2(-0.125, -0.375) : (i == 1 ? vec2(0.375, -0.125) : (i == 2 ? vec2(-0.375, 0.125) : vec2(0.125, 0.375)));
        gRoom += glzRoom(vec3(gP + gDx * o.x + gDy * o.y, 0.0), normalize(gRd + gRx * o.x + gRy * o.y), gS, gW, gHead, gKind, gShade, gSky, gAA * 0.5);
      }
      gRoom *= 0.25;
    #else
      gRoom = glzRoom(vec3(gP, 0.0), normalize(gRd), gS, gW, gHead, gKind, gShade, gSky, gAA);
    #endif
    if (gPlain > 0.5) gRoom = vec4(mix(vec3(0.016, 0.018, 0.020), vec3(0.95, 0.70, 0.40) * (0.35 + 0.65 * glzH(gS + 0.5)), uGlzDusk), 0.04);
    // reflection: the pane is not quite flat (a plain pane a little flatter: its warped bands read as a swirl)
    float gWob = mix(1.0, 0.35, gPlain);
    vec3 gNn = normalize(gNw + gWob * gT * (0.011 * sin(gP.x * 2.3 + gS) + 0.006 * sin(gP.y * 3.1 + gS * 1.7))
      + gWob * vec3(0.0, 1.0, 0.0) * (0.008 * sin(gP.y * 1.9 + gP.x * 0.7 + gS * 2.3)));
    float gC = clamp(dot(-gV, gNn), 0.0, 1.0);
    float gF = 0.15 + 0.85 * pow(1.0 - gC, 5.0);                          // insulated unit: four surfaces
    vec3 gR = reflect(gV, gNn);
    vec3 gSunD = vec3(0.0, 1.0, 0.0), gSunC = vec3(0.0);
    #if NUM_DIR_LIGHTS > 0
      gSunD = inverseTransformDirection(directionalLights[0].direction, viewMatrix);
      gSunC = directionalLights[0].color;
    #endif
    float gRA = clamp(length(fwidth(gR)) * 1.2, 0.003, 0.2);
    if (gPlain < 0.5) {
      glzSpec = glzWorld(vGlzW, gR, gSunD, gSunC, gSky, gRA, 1.0) * gF;
    } else {
      // No room behind (uncoded panes): the pane is a dark mirror.  A low, grey-green tree line in it (tk 0.3).
      vec3 gW = glzWorld(vGlzW, gR, gSunD, gSunC, gSky, gRA, mix(0.3, 0.5, gUp));      // upper: the tree line to ~13 deg
      float gTn = gR.y / max(length(gR.xz), 1e-4);
      float gL;
      if (gUp > 0.5) {
        // UPPER STOREY: open sky above -- the panes mirror it deep blue at ~0.55 of the sky they face (hero: upper
        // panes sRGB 75-84 122-142 175-221 under a sky of 127 168 239), the ground below the horizon only at the
        // pane's Fresnel (seen from the drone the windows stay dark, p28 / p29); a knee for the sun's glint
        // the sky in the pane is deeper than the sky beside it (polarised by the reflection): its blue pushed to the
        // hero's (0.33, 1.04, 2.4) x luminance -- the trees and houses mirrored keep their own colours
        float gLw = max(dot(gW, vec3(0.2126, 0.7152, 0.0722)), 1e-4);
        float gBlue = smoothstep(0.05, 0.35, (gW.b - gW.r) / gLw) * smoothstep(-0.02, 0.08, gTn);
        gW = mix(gW, gLw * vec3(0.33, 1.04, 2.4), gBlue);
        glzSpec = gW * mix(gF, mix(0.55, 0.46, gBlue), smoothstep(-0.03, 0.12, gTn));
        gL = dot(glzSpec, vec3(0.2126, 0.7152, 0.0722));
        glzSpec /= 1.0 + max(gL - 0.6, 0.0) * 1.5;
      } else {
        // GROUND FLOOR: every ground-floor window and door of this house stands under a porch roof (the wraparound
        // front porch, the rear loggia, the north porch): above eye level the pane mirrors the porch ceiling in shade,
        // the sunlit garden only in a band about the horizon, the porch floor below -- the panes read near black
        // (hero: 32 31 31), the door's lites catch the garden as light glints, never a green sheet
        vec3 gCeil = vec3(0.80, 0.78, 0.72) * gSky * 0.08;
        float gBand = smoothstep(0.10, 0.03, gTn) * smoothstep(-0.09, -0.02, gTn);
        vec3 gFloor = gW * 0.35;
        glzSpec = mix(mix(gFloor, gCeil, smoothstep(-0.02, 0.06, gTn)), gW * 0.65, gBand);
        gL = dot(glzSpec, vec3(0.2126, 0.7152, 0.0722));
        glzSpec = mix(vec3(gL), glzSpec, 0.4) * gF;                     // dimly seen: a grey-green, not a green
      }
    }
    totalEmissiveRadiance += gRoom.rgb * (1.0 - gF) * vec3(0.87, 0.91, 0.89);
    diffuseColor.rgb = vec3(0.80, 0.78, 0.73) * gRoom.a * (1.0 - gF) * 0.9;
    roughnessFactor = 1.0;
    metalnessFactor = 0.0;
  }
`;

function glassMaterial(ctx, shared) {
  const { THREE } = ctx;
  const m = new THREE.MeshStandardMaterial({ color: 0x000000, roughness: 1.0, metalness: 0.0 });
  const ss = ctx.quality === 'low' ? 1 : 4;
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uGlzDusk = shared.uGlzDusk;
    shader.uniforms.uGlzEnvK = shared.uGlzEnvK;
    shader.vertexShader = shader.vertexShader
      .replace('void main() {', PARS_VERTEX + 'void main() {')
      .replace('#include <fog_vertex>', '#include <fog_vertex>\n' + MAIN_VERTEX);
    shader.fragmentShader = shader.fragmentShader
      .replace('void main() {', `#define GLZ_SS ${ss}\n` + PARS_FRAGMENT + 'void main() {')
      .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n' + MAIN_FRAGMENT)
      // the mirror image is ours (sky, trees, sun): no specular from the scene's lights, whose tight lobes on a
      // perfectly smooth pane would only add fireflies
      .replace('vec3 totalSpecular = reflectedLight.directSpecular + reflectedLight.indirectSpecular;', 'vec3 totalSpecular = glzSpec;');
  };
  m.customProgramCacheKey = () => 'glazing-glass-8-' + ss;
  return m;
}

export function register(lib) {
  const shared = { uGlzDusk: { value: 0 }, uGlzEnvK: { value: 1 } };
  const metals = [];
  const sync = (t) => {
    const k = 1 / (lib.ctx.envGain || 1);
    shared.uGlzDusk.value = t === 'dusk' ? 1 : 0;
    shared.uGlzEnvK.value = k;
    for (const m of metals) m.envMapIntensity = k;
  };
  lib.onTime(sync);

  lib.add('glass', (ctx) => { sync(ctx.time); return glassMaterial(ctx, shared); }, { glass: true });

  // Clad frames, sashes, muntin bars: satin black.  Photos: in shade #1b1a1a .. #272324, sunlit ~#3a3a3b, and a
  // strong sky sheen at grazing angles (#5c6975 on the upper windows of p02) -- a smooth coating, not a matte one.
  lib.add('frame_black', (ctx) => new ctx.THREE.MeshStandardMaterial({ color: 0x1b1c1e, roughness: 0.36, metalness: 0.0 }));

  const metal = (color, roughness, metalness) => (ctx) => {
    const m = new ctx.THREE.MeshStandardMaterial({ color, roughness, metalness });
    m.envMapIntensity = 1 / (ctx.envGain || 1);
    metals.push(m);
    return m;
  };
  // lever handles, flush pulls: black satin metal; door sills / slider tracks: dark bronze anodised aluminium
  lib.add('hardware_black', metal(0x18181a, 0.34, 0.85));
  lib.add('threshold_bronze', metal(0x3a342d, 0.42, 0.8));
}
