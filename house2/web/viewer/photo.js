// Photo projection: the reference photographs cast onto the model through their registered cameras.
//
// meta.projectors = [{ name, image, masks: [[u0, v0, u1, v1], ...] (parts of the image never used, 0..1 from the
// top-left), cam: { w, h, f, cx, cy, k1, R (rows right / down / forward, world), C (world) } }].
// Every paintable material is patched: a fragment looks itself up in each photo (same pinhole + k1 as the survey
// tools), tests a depth map rendered from that camera (so a roof does not paint the ground under its eave) and
// takes the photos' colours weighted by how squarely each camera sees the surface.  The photo colour replaces the
// lit colour (it carries its own light and shadows); uMix fades it.  Plants, glass, water and furniture stay
// as modelled, and they are left out of the depth maps (the photos' trees are not where the model's twigs are).
import * as THREE from 'three';

const PAINT = new Set(['lawn', 'paver_drive', 'bluestone', 'concrete', 'mulch', 'soil', 'roof_shingle', 'roof_seam',
  'roof_flat', 'siding_lap', 'siding_bb', 'trim_white', 'soffit_white', 'stone_veneer', 'chimney_white']);
const SKIP_PARTS = new Set(['plants', 'trees', 'backdrop']);
const LAYER = 5;
const MAXP = 3;
const gl3 = (v) => new THREE.Vector3(v[0], v[2], -v[1]);          // world (x, y, z-up) -> three

export class PhotoLayer {
  constructor(renderer) {
    this.renderer = renderer;
    this.mix = { value: 0 };
    this.list = [];
    this.n = 0;
  }

  async load(meta, base) {
    const loader = new THREE.TextureLoader();
    for (const p of (meta.projectors || []).slice(0, MAXP)) {
      let tex;
      try { tex = await loader.loadAsync(base + p.image); } catch (e) { console.warn('photo layer: missing', p.image); continue; }
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.generateMipmaps = true;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
      tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
      const c = p.cam, R = c.R;
      const cam = new THREE.PerspectiveCamera(THREE.MathUtils.radToDeg(2 * Math.atan(c.h / 2 / c.f)), c.w / c.h, 0.5, 260);
      const right = gl3(R[0]), down = gl3(R[1]), fwd = gl3(R[2]);
      cam.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(right, down.clone().negate(), fwd.clone().negate()));
      cam.position.copy(gl3(c.C));
      cam.updateMatrixWorld(true);
      cam.layers.set(LAYER);
      const s = 2048 / Math.max(c.w, c.h);
      const rt = new THREE.WebGLRenderTarget(Math.round(c.w * s), Math.round(c.h * s), { depthBuffer: true });
      rt.depthTexture = new THREE.DepthTexture(rt.width, rt.height, THREE.UnsignedIntType);
      rt.depthTexture.minFilter = rt.depthTexture.magFilter = THREE.NearestFilter;
      const masks = [new THREE.Vector4(2, 2, 2, 2), new THREE.Vector4(2, 2, 2, 2), new THREE.Vector4(2, 2, 2, 2)];
      (p.masks || []).slice(0, 3).forEach((m, i) => masks[i].set(m[0], m[1], m[2], m[3]));
      this.list.push({
        name: p.name, cam, rt,
        u: {
          T: { value: tex }, D: { value: rt.depthTexture }, C: { value: gl3(c.C) },
          Rx: { value: right }, Ry: { value: down }, Rz: { value: fwd },
          K: { value: new THREE.Vector4(c.f, c.cx, c.cy, c.k1 || 0) }, S: { value: new THREE.Vector4(c.w, c.h, cam.near, cam.far) },
          M: { value: masks }, G: { value: p.gain === undefined ? 1 : p.gain }, V: { value: p.walls ? 1 : 0 },
        },
      });
    }
    this.n = this.list.length;
    return this.n;
  }

  // depth maps of the opaque built model, seen from every photo camera
  bake(scene, root) {
    if (!this.n) return;
    root.traverse((o) => {
      if (!o.isMesh) return;
      let part = o;
      while (part.parent && part.parent !== root) part = part.parent;
      const mat = o.userData.matName || '';
      if (SKIP_PARTS.has(part.name) || /glass|water|foliage|leaf|twig|bark|cushion|furn|rug/.test(mat)) return;
      o.layers.enable(LAYER);
    });
    const r = this.renderer, old = r.getRenderTarget(), bg = scene.background, ov = scene.overrideMaterial;
    scene.overrideMaterial = new THREE.MeshBasicMaterial({ colorWrite: false, side: THREE.DoubleSide });
    scene.background = null;
    for (const p of this.list) { r.setRenderTarget(p.rt); r.clear(); r.render(scene, p.cam); }
    scene.overrideMaterial = ov;
    scene.background = bg;
    r.setRenderTarget(old);
  }

  hook(material) {
    if (!this.n || material.userData.photoHook || material.isShaderMaterial || !PAINT.has(material.name)) return material;
    const prev = material.onBeforeCompile, prevKey = material.customProgramCacheKey, list = this.list, mix = this.mix, n = this.n;
    material.onBeforeCompile = function (shader, renderer) {
      if (prev) prev.call(this, shader, renderer);
      shader.uniforms.uPhMix = mix;
      let decl = 'uniform float uPhMix;\nvarying vec3 vPhW;\n', body = '';
      list.forEach((p, i) => {
        for (const k of Object.keys(p.u)) shader.uniforms[`uPh${k}${i}`] = p.u[k];
        decl += `uniform sampler2D uPhT${i}; uniform sampler2D uPhD${i}; uniform vec3 uPhC${i}, uPhRx${i}, uPhRy${i}, uPhRz${i};
uniform vec4 uPhK${i}, uPhS${i}; uniform vec4 uPhM${i}[3]; uniform float uPhG${i}, uPhV${i};\n`;
        body += `{
  vec3 d = vPhW - uPhC${i};
  vec3 q = vec3(dot(uPhRx${i}, d), dot(uPhRy${i}, d), dot(uPhRz${i}, d));
  if (q.z > 0.3) {
    vec2 xn = q.xy / q.z;
    vec2 px = uPhK${i}.x * xn * (1.0 + uPhK${i}.w * dot(xn, xn)) + uPhK${i}.yz;
    vec2 uv = px / uPhS${i}.xy;
    vec2 ud = vec2(0.5 + uPhK${i}.x * xn.x / uPhS${i}.x, 0.5 - uPhK${i}.x * xn.y / uPhS${i}.y);
    if (uv.x > 0.0 && uv.x < 1.0 && uv.y > 0.0 && uv.y < 1.0 && ud.x > 0.0 && ud.x < 1.0 && ud.y > 0.0 && ud.y < 1.0) {
      float cosv = dot(phN, normalize(-d));
      float zb = texture2D(uPhD${i}, ud).r;
      float zm = (uPhS${i}.z * uPhS${i}.w) / (uPhS${i}.w - zb * (uPhS${i}.w - uPhS${i}.z));
      float vis = step(q.z, zm + 0.07 + 0.004 * q.z + 0.05 * (1.0 - cosv) / max(cosv, 0.15));
      vec2 e = min(uv, 1.0 - uv);
      float w = pow(smoothstep(0.12, 0.45, cosv), 1.5) * vis * smoothstep(0.0, 0.03, min(e.x, e.y)) * uPhG${i};
      for (int k = 0; k < 3; k++) {
        vec4 m = uPhM${i}[k];
        w *= 1.0 - step(m.x, uv.x) * step(uv.x, m.z) * step(m.y, uv.y) * step(uv.y, m.w);
      }
      w *= mix(1.0, 1.0 - smoothstep(0.35, 0.6, abs(phN.y)), uPhV${i});
      if (w > 0.0) {
        vec3 c = texture2D(uPhT${i}, vec2(uv.x, 1.0 - uv.y)).rgb;
        w *= 1.0 - smoothstep(0.06, 0.14, min(c.r, c.b) - c.g);          // the key colour: parts of the photo never used
        phC += w * c; phW += w;
      }
    }
  }
}\n`;
      });
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vPhW;')
        .replace('#include <project_vertex>', '#include <project_vertex>\nvPhW = (modelMatrix * vec4(transformed, 1.0)).xyz;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\n' + decl)
        .replace('#include <tonemapping_fragment>', `#include <tonemapping_fragment>
if (uPhMix > 0.0) {
  vec3 phN = inverseTransformDirection(nonPerturbedNormal, viewMatrix);
  vec3 phC = vec3(0.0); float phW = 0.0;
  ${body}
  if (phW > 0.0) gl_FragColor.rgb = mix(gl_FragColor.rgb, phC / phW, uPhMix * smoothstep(0.0, 0.25, phW));
}`);
    };
    material.customProgramCacheKey = function () { return (prevKey ? prevKey.call(this) : '') + '|photo' + n; };
    material.userData.photoHook = true;
    material.needsUpdate = true;
    return material;
  }
}
