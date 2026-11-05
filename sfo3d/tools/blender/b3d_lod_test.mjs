// LOD logic test (node tools/blender/b3d_lod_test.mjs) of js/three/buildings3d.js on synthetic node trees shaped like the GLBs (no loading, no rendering)
globalThis.location = { search: '' }; globalThis.window = {};
const { THREE } = await import(new URL('../../js/three/lib.js', import.meta.url).href);
const { Buildings3D } = await import(new URL('../../js/three/buildings3d.js', import.meta.url).href);
const box = (w, h, d, x, z, name, ud = {}) => { const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial()); m.position.set(x, h / 2, z); m.name = name; m.userData = ud; return m; };
const R = { engine: { scene: new THREE.Scene() }, tier: 'high', Q: { lod: 1800 }, staticGroup: new THREE.Group(), world: { towerPos: [0, 0, 0] } };
const B = new Buildings3D(R);
// tower-like set: root -> LOD0 / LOD1 / LOD2 with switch_m arrays
const tower = new THREE.Group(); tower.name = 'tower'; tower.position.set(-740, 3, 324);
const L = (k, sw, kids) => { const g = new THREE.Group(); g.name = 'LOD' + k; g.userData = { lod: k, switch_m: sw }; kids.forEach(c => g.add(c)); return g; };
tower.add(L(0, [0, 350], [box(20, 70, 20, 0, 0, 'L0_shaft'), box(10, 5, 10, 0, 0, 'L0_cab')]), L(1, [350, 1200], [box(20, 70, 20, 0, 0, 'L1_shaft')]), L(2, [1200, -1], [box(20, 70, 20, 0, 0, 'L2_shaft')]));
// domestic-like set: per-building units
const dom = new THREE.Group(); dom.name = 'domestic'; dom.position.set(-896, 3, 336);
dom.add(L(0, 0, [box(100, 15, 400, -300, 0, 'L0_A_shell', { building: 'A' }), box(100, 15, 400, 300, 0, 'L0_B_shell', { building: 'B' }), box(5, 2, 5, 300, 0, 'L0_B_detail', { building: 'B' })]),
  L(1, 380, [box(100, 15, 400, -300, 0, 'L1_A_shell', { building: 'A' }), box(100, 15, 400, 300, 0, 'L1_B_shell', { building: 'B' })]), L(2, 1300, [box(700, 15, 400, 0, 0, 'L2_dom')]));
const root = new THREE.Group(); root.add(tower, dom); root.updateMatrixWorld(true);
B._lodSets('tower', tower); B._lodSets('domestic', dom);
const vis = (o) => { let v = o.visible, p = o.parent; while (p) { v = v && p.visible; p = p.parent; } return v; };
const shown = () => { const s = []; root.traverse(o => { if (o.isMesh && vis(o)) s.push(o.name); }); return s.join(','); };
const cams = [['at tower base', [-740, 5, 360]], ['600 m E of tower', [-140, 50, 324]], ['2 km away', [1300, 100, 324]], ['at domestic A west end', [-1300, 10, 336]], ['back to 600 m', [-140, 50, 324]]];
for (const [n, p] of cams) { B.update(p); B.update(p); console.log(n.padEnd(26), shown()); }
console.log('sets', B.sets.length, 'units', B.sets.map(S => S.units.map(u => u.key).join('|')).join(' ; '));
// hysteresis: unit at exactly the switch distance must not flicker
const S = B.sets[0]; const d0 = 350; const pA = [-740 + 10 + d0 * 1.02, 40, 324]; const seq = [];
B.update([-740, 5, 360]); seq.push(S.units[0].cur); for (let i = 0; i < 3; i++) { B.update(pA); seq.push(S.units[0].cur); }
B.update([-740 + 10 + d0 * 1.06, 40, 324]); seq.push(S.units[0].cur); for (let i = 0; i < 2; i++) { B.update(pA); seq.push(S.units[0].cur); }
console.log('hysteresis (near, 1.02x x3, 1.06x, 1.02x x2; expect 0,0,0,0,1,1,1):', seq.join(','), seq.join(',') === '0,0,0,0,1,1,1' ? 'OK' : 'FAIL');
