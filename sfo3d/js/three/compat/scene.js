// Stand-in for js/scene.js under live3.html's import map. js/live/app.js uses: new Scene(R, world), scene.add(ac),
// scene.aircraft (LiveAircraft list), scene.staticLights (sprite sources), scene.gateSys, scene.frame(t, camPos),
// scene.commit(). The aircraft, bridges and GSE are drawn by js/three/renderer3.js from the same objects; this class
// only collects the light sprites exactly as the old Scene.frame did (aircraft lights, then the static sources).
export class Scene {
  constructor(R, world) {
    this.R = R; this.world = world; this.aircraft = []; this.staticLights = []; this.gateSys = null; this.smokeFns = []; this.extraItemFns = [];
    if (R.attachWorld) R.attachWorld(world, this);
  }
  add(ac) { this.aircraft.push(ac); return ac; }
  frame(t, camPos) {
    if (this.R.frameScene) this.R.frameScene(this, t, camPos); // bridges / GSE / aircraft objects; sets gateSys.sprites
    const sprites = [];
    for (const ac of this.aircraft) { const s = ac.lightSprites(t); for (let i = 0; i < s.length; i++) sprites.push(s[i]); }
    for (const L of this.staticLights) { if (typeof L === 'function') { const s = L(t); for (let i = 0; i < s.length; i++) sprites.push(s[i]); } else sprites.push(L); }
    return { sprites, t };
  }
  commit() { for (const ac of this.aircraft) ac.commit(); }
}
