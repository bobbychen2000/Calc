// Picture: progressive refinement when nothing moves.  Each pass renders the scene into a linear half-float
// target with (1) a sub-pixel camera jitter, (2) the sun moved within its disc and (3) part of the sky's light
// delivered by ONE shadow-casting directional light from a random sky direction instead of the image-based
// light; the passes are averaged in scene-referred light and tone mapped once.  Converged, that is antialiased,
// has soft sun shadows and real sky-light shadowing (under eaves, in the porch, between buildings).
import * as THREE from 'three';

const NEUTRAL = /* glsl */`
vec3 neutral(vec3 color) {
  const float startCompression = 0.8 - 0.04;
  const float desaturation = 0.15;
  float x = min(color.r, min(color.g, color.b));
  float offset = x < 0.08 ? x - 6.25 * x * x : 0.04;
  color -= offset;
  float peak = max(color.r, max(color.g, color.b));
  if (peak < startCompression) return color;
  float d = 1.0 - startCompression;
  float newPeak = 1.0 - d * d / (peak + d - startCompression);
  color *= newPeak / peak;
  float g = 1.0 - 1.0 / (desaturation * (peak - newPeak) + 1.0);
  return mix(color, vec3(newPeak), g);
}`;

const QUAD_VERT = /* glsl */`varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

function halton(i, b) { let f = 1, r = 0; while (i > 0) { f /= b; r += f * (i % b); i = Math.floor(i / b); } return r; }

export class Picture {
  constructor(stage) {
    this.stage = stage;
    this.passes = 48;            // passes to convergence (the page shows the running average meanwhile)
    this.skyShare = 0.7;         // share of the sky's diffuse light delivered by shadowed sky samples
    this.sunRadius = 0.6;        // degrees: half-angle of the sun's disc (a little hazy, as the photos' shadow edges)
    this.n = 0;
    this.enabled = true;
    const r = stage.renderer;
    this.type = r.capabilities.isWebGL2 && r.extensions.get('EXT_color_buffer_float') ? THREE.HalfFloatType : THREE.UnsignedByteType;
    this.cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2));
    this.quadScene = new THREE.Scene();
    this.quadScene.add(this.quad);
    // running average: out = mix(prev, frame, 1 / (n + 1))
    this.blend = new THREE.ShaderMaterial({ vertexShader: QUAD_VERT, depthTest: false, depthWrite: false,
      uniforms: { tPrev: { value: null }, tFrame: { value: null }, uW: { value: 1 } },
      fragmentShader: `varying vec2 vUv; uniform sampler2D tPrev, tFrame; uniform float uW;
        void main() { gl_FragColor = mix(texture2D(tPrev, vUv), texture2D(tFrame, vUv), uW); }` });
    // display: tone map the opaque part (alpha 1), pass the sky's display colour through (alpha 0)
    this.show = new THREE.ShaderMaterial({ vertexShader: QUAD_VERT, depthTest: false, depthWrite: false,
      uniforms: { tAcc: { value: null }, uExposure: { value: 1 } },
      fragmentShader: `varying vec2 vUv; uniform sampler2D tAcc; uniform float uExposure; ${NEUTRAL}
        void main() {
          vec4 c = texture2D(tAcc, vUv);
          vec3 lit = neutral(max(c.rgb, 0.0) * uExposure);
          gl_FragColor = vec4(mix(c.rgb, lit, clamp(c.a, 0.0, 1.0)), 1.0);
          #include <colorspace_fragment>
        }` });
    this.skyLight = new THREE.DirectionalLight(0xffffff, 0);
    this.skyLight.castShadow = true;
    const s = stage.sun.shadow;
    this.skyLight.shadow.mapSize.copy(s.mapSize).multiplyScalar(0.5);
    Object.assign(this.skyLight.shadow.camera, { left: s.camera.left, right: s.camera.right, top: s.camera.top, bottom: s.camera.bottom, near: s.camera.near, far: s.camera.far });
    this.skyLight.shadow.bias = s.bias;
    this.skyLight.shadow.normalBias = s.normalBias * 1.5;
    this.skyLight.shadow.radius = 3;
    // the sky light joins the scene on the first refinement pass only: until then it would cost a shadow map and a
    // shadow lookup per fragment for nothing (one recompile of the programs then, in the ?hq= mode only)
    this.skyOff = { value: new THREE.Color(0, 0, 0) };   // shared uniform: sky irradiance taken out of the image-based diffuse light in a pass
    this.sunHome = new THREE.Vector3();
  }

  // every lit material gets the shared uniform (see the ShaderChunk patch in stage.js)
  hook(material) {
    if (material.userData.pictureHook || material.isShaderMaterial) return material;
    const prev = material.onBeforeCompile;
    const u = this.skyOff;
    material.onBeforeCompile = function (shader, renderer) {
      if (prev) prev.call(this, shader, renderer);
      shader.uniforms.uSkyOff = u;
    };
    material.userData.pictureHook = true;
    return material;
  }

  size(w, h) {
    const o = { type: this.type, depthBuffer: true, samples: 0, colorSpace: THREE.LinearSRGBColorSpace };
    for (const k of ['frame', 'a', 'b']) if (this[k]) this[k].dispose();
    this.frame = new THREE.WebGLRenderTarget(w, h, o);
    this.a = new THREE.WebGLRenderTarget(w, h, { ...o, depthBuffer: false });
    this.b = new THREE.WebGLRenderTarget(w, h, { ...o, depthBuffer: false });
    this.w = w; this.h = h;
    this.n = 0;
  }

  reset() { this.n = 0; }

  get done() { return this.n >= this.passes; }

  // one refinement pass; returns true while more are wanted
  pass() {
    const st = this.stage, r = st.renderer, cam = st.camera, i = this.n;
    if (!this.skyLight.parent) st.scene.add(this.skyLight, this.skyLight.target);
    r.shadowMap.needsUpdate = true;                   // the sun and the sky light move from pass to pass
    const pr = r.getPixelRatio(), W = Math.round(st.canvas.clientWidth * pr), H = Math.round(st.canvas.clientHeight * pr);
    if (!this.frame || this.w !== W || this.h !== H) this.size(W, H);
    // (1) sub-pixel jitter
    const jx = i ? halton(i, 2) - 0.5 : 0, jy = i ? halton(i, 3) - 0.5 : 0;
    cam.setViewOffset(W, H, jx, jy, W, H);
    // (2) the sun within its disc
    const sun = st.sun, home = this.sunHome.copy(sun.position);
    const dir = home.clone().sub(sun.target.position), dist = dir.length();
    dir.normalize();
    const t1 = new THREE.Vector3().crossVectors(dir, Math.abs(dir.y) < 0.9 ? new THREE.Vector3(0, 1, 0) : new THREE.Vector3(1, 0, 0)).normalize();
    const t2 = new THREE.Vector3().crossVectors(dir, t1);
    const rr = Math.sqrt(halton(i + 1, 5)) * Math.tan(THREE.MathUtils.degToRad(this.sunRadius)), th = 2 * Math.PI * halton(i + 1, 7);
    sun.position.copy(sun.target.position).addScaledVector(dir.clone().addScaledVector(t1, rr * Math.cos(th)).addScaledVector(t2, rr * Math.sin(th)).normalize(), dist);
    // (3) one sky sample, uniform over the upper hemisphere (pdf 1 / 2pi): a directional light of intensity
    //     2pi L(w) has the sky's irradiance as its expectation on any surface
    const u1 = halton(i + 1, 11), u2 = halton(i + 1, 13), phi = 2 * Math.PI * u2;
    const sinE = 0.03 + 0.97 * u1, cosE = Math.sqrt(1 - sinE * sinE);
    const d = new THREE.Vector3(cosE * Math.cos(phi), sinE, cosE * Math.sin(phi));
    this.skyLight.color.copy(st.skyRadiance(d));
    this.skyLight.intensity = 2 * Math.PI * this.skyShare;
    this.skyLight.position.copy(sun.target.position).addScaledVector(d, dist);
    this.skyLight.target.position.copy(sun.target.position);
    // ... and that much of the sky's part of the image-based diffuse light is taken out (uniform-sky estimate:
    // a surface with world normal n sees (1 + n.y) / 2 of the sky)
    this.skyOff.value.copy(st.skyMean).multiplyScalar(Math.PI * this.skyShare);
    st.sky.mat.uniforms.uAlpha.value = 0;
    const tm = r.toneMapping;
    r.toneMapping = THREE.NoToneMapping;
    r.setRenderTarget(this.frame);
    r.setClearColor(0x000000, 0);
    r.clear();
    r.render(st.scene, cam);
    // average
    const prev = i % 2 ? this.a : this.b, next = i % 2 ? this.b : this.a;
    this.quad.material = this.blend;
    this.blend.uniforms.tPrev.value = prev.texture;
    this.blend.uniforms.tFrame.value = this.frame.texture;
    this.blend.uniforms.uW.value = 1 / (i + 1);
    r.setRenderTarget(next);
    r.render(this.quadScene, this.cam);
    // show
    r.setRenderTarget(null);
    this.quad.material = this.show;
    this.show.uniforms.tAcc.value = next.texture;
    this.show.uniforms.uExposure.value = r.toneMappingExposure;
    r.render(this.quadScene, this.cam);
    // restore
    r.toneMapping = tm;
    cam.clearViewOffset();
    sun.position.copy(home);
    this.skyLight.intensity = 0;
    this.skyOff.value.set(0, 0, 0);
    st.sky.mat.uniforms.uAlpha.value = 1;
    this.n = i + 1;
    return this.n < this.passes;
  }
}
