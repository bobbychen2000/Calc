// ------------------------------------------------------------------
// Unit studio: renders one unit on a neutral backdrop for design review (used during development)
// ------------------------------------------------------------------
function studioRender(app, geo, opts = {}) {
  const G = app.G, gl = G.gl, S = app.scene;
  const w = app.canvas.width, h = app.canvas.height;
  const m = G.mesh(geo, { instances: [M4.ident()] });
  if (!app._studioFloor) {
    const fb = new Builder();
    fb.add(gBox(12, 0.02, 12), M4.trs(0, -0.012, 0), { c: '#cfd3d8', r: 0.8 });
    app._studioFloor = G.mesh(fb.build(), { instances: [M4.ident()] });
  }
  const [mn, mx] = geo.bounds;
  const c = opts.target || [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2];
  const size = Math.max(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]);
  const az = opts.az ?? 0.7, el = opts.el ?? 0.25, dist = (opts.dist ?? 1.7) * size;
  let pos = [c[0] + dist * Math.cos(el) * Math.sin(az), c[1] + dist * Math.sin(el), c[2] + dist * Math.cos(el) * Math.cos(az)];
  let tgt = c;
  if (opts.eye) { pos = opts.eye; tgt = opts.look; }
  const view = M4.lookAt(pos, tgt, [0, 1, 0]);
  const proj = M4.perspective((opts.fov ?? 34) * DEG, w / h, 0.02, 100);
  gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  gl.viewport(0, 0, w, h);
  gl.clearColor(0.80, 0.83, 0.87, 1);
  gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  if (!S.shadow) S.renderShadow();
  G.use(S.progs.main);
  G.set('u_viewProj', M4.mul(proj, view));
  G.set('u_camPos', pos);
  G.set('u_sunDir', V3.norm(opts.key || [0.45, 0.8, 0.55]));
  G.set('u_sunCol', opts.keyCol || [2.3, 2.2, 2.1]);
  G.set('u_shadowMat', S.shadowMat);
  G.tex('u_shadow', 0, S.shadow.tex);
  G.set('u_shadowTexel', [1 / S.shadow.w, 1 / S.shadow.h]);
  G.set('u_hemiTop', [0.9, 0.9, 0.92]); G.set('u_hemiBot', [0.3, 0.3, 0.32]);
  G.set('u_wash', [0, 0, 0]); G.set('u_led', opts.led || [0.8, 0.85, 1.0]); G.set('u_winGlow', [0, 0, 0]);
  G.tex('u_ao', 1, S.ao.tex, gl.TEXTURE_3D); G.set('u_aoMin', S.ao.min); G.set('u_aoSize', S.ao.size);
  G.tex('u_detail', 2, S.tex.detail, gl.TEXTURE_2D_ARRAY);
  G.tex('u_photo', 5, S.tex.photo, gl.TEXTURE_2D_ARRAY); G.set('u_photoOn', PHOTO_PIX ? 1 : 0);
  const lp = new Float32Array(N_LAYERS * 4);
  for (const [kk, v] of Object.entries(LAYER_PARAMS)) lp.set(v, +kk * 4);
  G.set('u_layer', lp);
  G.tex('u_atlas', 3, S.tex.atlas); G.set('u_screenStep', ATL.screenStep);
  G.set('u_emisGain', 1.0); G.set('u_screenGain', 0.8);
  G.tex('u_win', 4, S.winTex); G.set('u_winZ', S.winZ);
  G.set('u_R', CAB.R); G.set('u_yc', CAB.yc);
  G.set('u_exposure', opts.exposure || 1.0); G.set('u_fill', opts.fill || 0);
  G.set('u_exterior', 1);
  G.set('u_skyTop', opts.fillTop || [0.62, 0.64, 0.68]); G.set('u_skyBot', opts.fillBot || [0.30, 0.30, 0.31]);
  G.set('u_detailOn', 1);
  if (!opts.noFloor) G.draw(app._studioFloor);
  G.draw(m);
  gl.finish();
  // free the temporary mesh
  gl.deleteVertexArray(m.vao);
}

// Extra review units: wing, a ceiling slice (bins + aisle panels + PSUs), a window bay with the three shade
// states, and the door-3 monument group (lavs + bar)
const STUDIO_UNITS = {
  wing: () => buildExterior(null).geo,
  ceiling: () => {
    const B = new Builder();
    const L = BIN.side;
    const zones = [{ type: 'seat', z0: -L, z1: L, cls: 'Y' }];
    buildCeilings(B, { zones, seats: [] });
    const side = { R: sideBinModule(1), L: sideBinModule(-1), C: centerBinModule() };
    for (const zc of [-L / 2, L / 2]) for (const k of ['R', 'L']) B.addBuilt(side[k], M4.trs(0, 0, zc));
    for (const zc of [-1.5, -0.5, 0.5, 1.5]) B.addBuilt(side.C, M4.trs(0, 0, zc * BIN.center));
    for (const x of [-2.2, 2.2]) B.addBuilt(psuModule(3), M4.trs(x, binBottomY(x) - 0.012, 0, 0, 0, Math.atan2(0.195, 1.315) * (x > 0 ? 1 : -1)));
    B.addBuilt(psuModule(4), M4.trs(0, 1.83, 0));
    return B.build();
  },
  windows: () => {
    const B = new Builder();
    const P = CAB.win.pitch;
    const pat = windowCellPattern(P, CAB.win.holeW, CAB.win.holeH, HOLE_R, CAB.win.yc);
    const g = raw();
    const zs = [-P * 2, -P, 0, P, P * 2];
    buildSidewallRun(g, -1, -P * 2.5, P * 2.5, zs, pat, WALL.vTop);
    fixWinding(g); B.add(g, null, MAT.sidewall);
    const wp = windowParts(-1);
    const states = [['manual', 0], ['manual', 0.5], ['manual', 1], ['sheer', 1], ['blackout', 1]];
    zs.forEach((z, k) => {
      B.add(wp.reveal, M4.trs(0, 0, z), MAT.reveal);
      const w = { z, side: -1 };
      const [kind, f] = states[k];
      const m = shadeMats(w, f, kind === 'blackout' ? -0.012 : 0);
      B.addBuilt(shadePanelGeo(kind), m.panel);
      B.addBuilt(shadeRailGeo(kind), m.rail);
      if (kind === 'sheer' || kind === 'blackout') {
        const F = M4.mul(M4.trs(0, 0, z), windowFrame(-1, -0.004));
        B.add(gRBox(0.06, 0.028, 0.008, 0.004, 1), M4.mul(F, M4.trs(0, -CAB.win.holeH / 2 - 0.05, 0)), { c: '#cfccc5', r: 0.4 });
      }
    });
    return B.build();
  },
  door3: () => {
    const L = buildLayout();
    const z3 = L.doorsZ[2][0];
    const mon = L.mon.filter((m) => Math.abs(m.z1 - z3) < 0.05 && m.z0 > z3 - 2);
    return buildMonuments(null, { ...L, mon }, { noDoors: true }).geo;
  },
  galley4: () => {
    const L = buildLayout();
    const mon = L.mon.filter((m) => m.z0 > L.doorsZ[3][0] - 3 && m.z1 < L.doorsZ[3][1] + 2);
    return buildMonuments(null, { ...L, mon }, { noDoors: true }).geo;
  },
};
