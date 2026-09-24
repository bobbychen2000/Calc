# Rendering engine for SFO Live 3D: evaluation and migration plan

Research note, 24 Sep 2026 (UTC). Scope: what the custom WebGL2 renderer does and where it limits the result, how
it maps to the QA pass-1 findings, which engine should replace or extend it, the role of Blender 5.0, and a phased
migration plan. The user's latest word on this task was **"Realtime!!!!"**, so every recommendation below is gated on
real-time frame rates on the user's phone first, visual quality second.

Labels used throughout:

- **Observed**: read in this repository's code, in a downloaded package's source, or measured by running it here
  (sandbox: 4 vCPU, no GPU, no browser runs allowed).
- **Documented**: quoted from the vendor's own page or source file, with its URL or path.
- **Inferred**: our estimate or interpretation.
- **Unverified**: we could not check it. Each one needs a test or a question to the user.

Everything downloaded for this note is under `refs/cache/engine/` (gitignored): npm tarballs of three 0.186.0,
@babylonjs/core 9.28.0, cesium 1.145.0, troika-three-text 0.52.5 and @takram/three-atmosphere 0.19.1; sparse clones of
the three.js r186 manual and the Filament repository; and archived copies of the cited web pages in
`refs/cache/engine/pages/`. The Blender test outputs are in `refs/cache/blender_test/`. Two tools were written for
this note: `tools/engine/blender_bake_test.py` and `tools/engine/glb_compress.mjs`.

---

## 1. Summary and recommendation

**Recommendation: migrate the renderer to three.js, pinned to r186, using `WebGPURenderer`.** It runs WebGPU where the
browser has it (Safari 26 or later on iPhone 11 and newer, and Chrome) and falls back automatically to WebGL 2
elsewhere.

- Port the custom GLSL to TSL (three.js's shading language). The largest piece is the SDF runway and ground-marking
  shader.
- Keep the app, traffic, physics, data and geometry-builder layers as they are.
- Author the airport buildings and equipment in Blender 5.0 with scripts, bake ambient occlusion, and export glTF
  with KTX2 textures and meshopt geometry. This pipeline was tested end-to-end in this sandbox (section 7).
- Keep the custom renderer running until the new one matches it on the QA views and on frame rate on the user's
  phone.

Why:

1. **Most of the pass-1 defects are about light and anti-aliasing, not data.**
   - The custom renderer has no screen-space AO, no temporal anti-aliasing, no prefiltered image-based lighting, no
     local reflections, no compressed textures, no normal maps and no texture-mapped PBR materials for world objects
     (Observed, section 2).
   - three.js r186 ships every one of these as maintained modules: GTAO, SSAO, SSGI, SSR, TRAA, TAAU, SMAA, FXAA,
     PMREM, KTX2 with Basis, meshopt, `BatchedMesh`, cascaded shadows (`CSMShadowNode` and the new `SunLight`), and AgX
     and Neutral tone mapping (Observed in the package).
2. **WebGPU reached iPhones in Safari 26.** WebKit: "now shipping in Safari 26.0 for macOS, iOS, iPadOS, and
   visionOS" (Documented). `WebGPURenderer` uses it there and falls back to WebGL 2 on older iOS, so one code path
   covers every device.
3. **Porting cost is moderate.** About 250 KB of `js/live` logic and all the geometry builders port as-is. About 80 KB
   of GLSL has to be rewritten in TSL. That is mostly mechanical math: SDF glyphs, `band()`, runway end markings and
   noise (section 6).
4. **The alternatives fit worse.**
   - Babylon.js 9 matches three.js on features. But its WebGPU engine downloads shader-compiler WASM from
     `cdn.babylonjs.com`, which the artifact CSP blocks. It would also mean a full rewrite of scene handling.
     **[corrected by verifier]** In 9.28 that download happens only when a GLSL shader has to be compiled on WebGPU
     (`_preparePipelineContextAsync` → `prepareGlslangAndTintAsync`). `initAsync` does not load it, and built-in
     materials use their WGSL shaders on WebGPU. Our custom GLSL would trigger it unless it is rewritten in WGSL.
   - CesiumJS and Google Photorealistic 3D Tiles are the only way to photoreal city context. But Google's terms forbid
     caching and offline use (so no snapshot artifact), and Cesium ion's free tier is non-commercial.
     **[corrected by verifier]** They are not the only way: section 4.3 notes that three.js can stream the same Google
     tiles with `3d-tiles-renderer`. The licence limits are the same either way.
   - deck.gl's WebGPU support is "experimental and … not yet recommended for production".
   - Filament's web build is stale: npm `filament` 1.53.4 is from Aug 2024, while the native library is at v1.77.
     **[corrected by verifier]** Only the npm package is stale. GitHub release v1.77.1 ships
     `filament-v1.77.1-web.tgz` (`filament.js` + `filament.wasm`, built 21 Sep 2026). The latest native tag is v1.77.1;
     v1.77.2 exists only as an `rc/1.77.2-cut` tag and a RELEASE_NOTES header.
   - Evolving the custom renderer would re-implement, alone, what three.js already maintains.

**Main risks and how to handle them.**

- The three.js manual still calls `WebGPURenderer` "still in an experimental state". Pin r186 and upgrade on purpose.
- Its WebGL 2 fallback can be slower than the classic `WebGLRenderer`, as the manual says. Benchmark on the user's
  phone before switching (phase 0). **[corrected by verifier]** The manual says `WebGPURenderer` in general may show
  "missing features or a better performance with `WebGLRenderer`", depending on the scene. It does not single out the
  WebGL 2 fallback.
- The headless QA harness will probably exercise only the WebGL 2 backend. *Unverified.* See section 8, phase 0.
- WASM decoders (Basis, meshopt) may be blocked by the artifact's CSP. *Unverified.* There is a no-WASM asset fallback
  (section 5).

---

## 2. What the custom renderer does today

Files read: `js/gl.js`, `js/renderer.js`, `js/scene.js`, `js/live/app.js`, `js/shaders/*.js`, `js/live/models.js`,
`world.js`, `gates.js`, `terminals.js`, `aircraft.js`, `markings.js`, `signs.js`, `controls.js`, `js/world/world.js`,
`terrain.js`, `textures.js`. Every item below is Observed unless it is marked otherwise.

### 2.1 Frame structure (`js/renderer.js` `render()`)

| Step | What happens |
|---|---|
| Shadow maps | 3 cascades, each drawn into its own `DEPTH_COMPONENT32F` texture (3072² on high, 2048² on medium and low), with polygon offset (1.5, 2.0) and face culling off. |
| Main pass, far | Into a multisampled FBO with two `RGBA16F` colour attachments (colour, plus aux = view distance and screen velocity) and a `DEPTH32F` renderbuffer. Draws items beyond the near/far split. |
| Sky | Fullscreen pass over the precomputed atmosphere, with clouds. Then the far blended items (cloud slabs). |
| Main pass, near | Depth is **cleared**, then the near range (camera near to `split × 1.08`) is drawn with its own projection. This "two-range depth" gives good depth precision from 0.25 m to 180 km. Then near blended items, sorted back to front. |
| Resolve | `blitFramebuffer` of both attachments (MSAA resolve). |
| Post | Optional motion blur (shutter is 0 in the live app). Bloom: 6-level dual-filter down/up chain. Final pass: exposure, lift/gain, saturation, ACES, vignette, grain, fixed chromatic aberration, 2-D overlay composite, dither. |
| Present | Blit to the canvas, with `LINEAR` upscaling when the dynamic resolution is below 1. |

### 2.2 Feature inventory

| Area | What the code does | Where |
|---|---|---|
| **Lighting / BRDF** | GGX (`D_GGX`), Smith visibility and Schlick Fresnel for one sun. Diffuse ambient is a 3-term hemisphere (sky-up, horizon, ground bounce), integrated once per sun change from a 64×32 readback of the sky. The ground shader uses Lambert plus a faint GGX sheen. | `shaders/common.js:74` `shadePBR`; `renderer.js` `setupSky` |
| **Environment / IBL** | Single-scattering Rayleigh + Mie sky precomputed into 1024×512 `RGBA16F`, composed with clouds into a 512×256 equirect with box-filtered mips (`generateMipmap`), sampled at `lod = roughness × 7`. **Not GGX-prefiltered and no irradiance map** (the hemisphere terms stand in for it). Reflections below the horizon are faked by a mirrored lookup blended to ground colour. No local reflections (no SSR, no probes). | `common.js` `skyEnv`, `env.js` `ENV_FS` |
| **Ambient occlusion** | None screen-space. Buildings: a height term `mix(0.55, 1, smoothstep(0, 4, wp.y − 3))`. Imported aircraft: a normal-based term `mix(0.72, 1, smoothstep(−0.7, 0.3, N.y))`. Ground: none. | `objects.js:145`, `aircraft_real.js:88` |
| **Shadows** | 3 cascades with bounding-sphere fit and texel snapping (stable under camera motion). Splits come from the orbit distance d: `[clamp(1.4d, 70, 1800), clamp(5d, 450, 7000), clamp(16d, 2500, 22000)]`. Filter: hardware 2×2 compare with 5 taps (centre ×2, plus 4 taps rotated by a per-pixel hash) at 1.5 texels, normal offset of 1.5 texels, per-cascade constant bias. The last cascade fades out; there is no blend between cascades 0/1 and 1/2. Aircraft cast shadows only within 1600/1100/700 m by tier. Cloud shadows come from a projected noise texture. | `renderer.js:148` `computeCascades`, `common.js:105` `sampleCascade`/`getShadow`, `controls.js:30` |
| **Anti-aliasing** | MSAA only: 4× on high and medium, 2× on low, on `RGBA16F` renderbuffers. No TAA, SMAA or FXAA, and no specular AA apart from distance fades written into individual procedural patterns. The motion vectors needed for TAA are already written to the aux target (`fout` chunk). | `gl.js:4` (`antialias:false`), `renderer.js:29` |
| **Tone mapping / grading** | The "ACES fitted" curve (RRT+ODT rational fit with input/output matrices). Exposure is a heuristic from sun elevation and cloud (`0.45 …`). Saturation 1.1, vignette 0.18. No auto-exposure or histogram. | `post.js:61–81`, `app.js:302` |
| **Materials** | World objects have **no textures**. Albedo, roughness and metalness come from vertex colour and a vertex "material id" (`aExtra.z`), which picks one of about 14 procedural GLSL patterns (glass curtain wall, concrete panels, garage, corrugated metal, roof, windows, foliage, tunnel ribs, cars, tower glass, service facade, hangar door). No normal maps, just a few analytic normal perturbations. Aircraft use a JPEG/PNG albedo plus livery recolouring by region in the shader. | `objects.js`, `aircraft_real.js` |
| **Ground** | Per-pixel procedural shader. Runway markings are analytic, including thresholds, TDZ, aiming point, displaced-threshold arrows and blast-pad chevrons. Runway numerals come from an **SDF glyph atlas** built at run time (canvas → EDT) with `fwidth` anti-aliasing. The airfield albedo is baked once to a texture at 0.8/1.0/1.25 m per texel by tier, and the procedural city is baked the same way. Taxiway lines are separate ribbon decals that widen to at least about 0.75 px on screen with alpha scaled down to match. | `ground.js`, `world/textures.js:5`, `markings.js` |
| **Instancing / batching** | `Mesh.setInstances` (3×4 matrix + vec4 data) for ground-service vehicles, light sprites (up to 20,000 billboards) and smoke. Everything else is merged: all buildings form one mesh and all bridges one static mesh. **While a bridge docks or undocks, the whole dynamic bridge mesh is rebuilt and re-uploaded every frame.** | `gl.js:112`, `gates.js:251`, `scene.js` |
| **Draw submission** | Per item: `useProgram`, uniform uploads (no UBOs; per-frame uniforms set once per program per pass), AABB frustum cull, one draw. Items are sorted by program priority once per frame. No state sorting by texture or material. | `renderer.js` `drawItems` |
| **Text** | Runway numerals: SDF, as above. Signs, VDGS and gate numbers: a Canvas2D atlas (bold Arial Narrow at 70 px on 96 px rows, 2048 wide), uploaded as a mip-mapped `SRGB8_ALPHA8` **bitmap, not SDF**, so it blurs with distance. Aircraft labels: DOM elements. | `signs.js:35–41` |
| **Texture formats** | `RGBA8`, `SRGB8_ALPHA8`, `RGBA16F` and `DEPTH32F`. **No compressed formats** (no KTX2/Basis, ASTC, ETC2 or BC). Aircraft textures are decoded from JPEG/PNG to RGBA8 with full mip chains. | `gl.js:143`, `models.js` |
| **LOD** | Aircraft: the imported model within 1800/1300/1000 m, a procedural body beyond that, nothing beyond 14 km. Terrain: one static grid with a 15/20/30 m step inside ±4.2 km, growing ×1.052 per step out to 60 km, split into 48-cell chunks. No CDLOD and no geomorphing. Markings fade out between 2.5 and 6 km. | `aircraft.js`, `terrain.js:195–202` |
| **Model format** | `.sfom`: gzip, quantised position (u16), normal (i8), uv (u16), materials baked per vertex, JPEG/PNG textures embedded. Triangles are regrouped into one draw per texture. | `models.js` |
| **Dynamic resolution** | EMA of the frame time. Above 36 ms, scale ×0.88; below 20 ms, ×1.08; checked every 2.5 s, clamped to 0.4–`scaleMax`. The target is 30 fps. **Every scale change calls `R.resize()`, which frees and reallocates every render target, including the MSAA ones.** **[corrected by verifier]** The EMA input is `performance.now() − tp`: the CPU time spent inside `tick()`, including WebGL command submission. It is not the display frame interval or GPU time, so a GPU-bound phone may never trip the 36 ms threshold. `resize()` returns early when the rounded render size is unchanged, for example while the `maxPx` cap binds. | `app.js:320–322`, `renderer.js` `resize` |

### 2.3 Draw calls (Inferred; not measured here because no GPU or browser was allowed)

Scenario: a gate view at the high tier with the recorded snapshot. The snapshot has 48 aircraft, 33 of them on the
ground or slow (Observed).

| Contribution | Estimate |
|---|---|
| Imported aircraft | Draws per airframe = number of texture groups: 1–14 by type, mean about 3.9 (Observed, table 2.5), plus about 3 procedural gear parts. So about 7 draws per aircraft and about 230 per main pass for 33 aircraft. The same aircraft are drawn again in up to 3 shadow cascades. **[corrected by verifier]** Re-parsing `data/models/*.sfom` gives 1–14 textures (mean 4.05). Every model also has one untextured group, so there are 2–15 draw groups per airframe, mean 5.05. Procedural gear is added only for gear-less models (0–3 parts). That makes about 5–8 draws per aircraft, or 165–265 per main pass. The total estimate below is unchanged in order of magnitude. |
| Terrain | 256 chunks on high (100 on low) (Observed). Chunks crossing the split are drawn in both the far and near pass. |
| Static world | About 10 items: water, 2 marking meshes, 2 sign meshes, masts, EMAS, buildings, piers, clouds. |
| Gate system | About 12 items: static bridges, dynamic bridges, signs, and the vehicle instance buckets. |
| **Total** | **About 500–1,200 draw calls per frame**, dominated by aircraft × (shadow + main passes). |

On WebGL in Safari each draw is translated to Metal. WebKit's Safari 26 post presents WebGPU as a better fit to Metal
with less validation overhead (Documented: "validation performed was streamlined recently to minimize overhead and
maintain closer to native application performance").

### 2.4 GPU memory by quality tier (Inferred from the allocation code; the aircraft textures in 2.5 come on top)

| Tier | Render targets (MSAA + resolve + bloom) | Shadows | Airfield bake | Aux | City bakes ×2 | Region | Terrain buffers | **Total** |
|---|---|---|---|---|---|---|---|---|
| high (3.2 MPx, 4×) | 358 MiB | 108 | 120 | 19 | 171 | 21 | 27 | **≈ 830 MiB** |
| medium (2.0 MPx, 4×) | 224 | 48 | 77 | 19 | 171 | 21 | 17 | **≈ 583 MiB** |
| low / mobile (1.1 MPx, 2×) | 81 | 48 | 49 | 19 | 43 | 21 | 10 | **≈ 277 MiB** |

Most of the render-target memory is the MSAA pair: 2 × `RGBA16F` + `D32F` = 20 B per sample. TRAA replaces MSAA and
needs roughly colour + history + velocity + depth ≈ 28 B per pixel, which would cut the high-tier render-target cost
by about two thirds (Inferred). **[corrected by verifier]** Replacing the 80 B-per-pixel MSAA pair with 28 B per pixel
takes 3.2 MPx from 244 MiB to about 85 MiB. The whole render-target column then goes from 358 to about 200 MiB, a cut of
about 45%. "Two thirds" applies only to the MSAA part. three's `TRAANode` also keeps a resolve target, and velocity
is usually RGBA16F, so 28 B per pixel is a lower bound. WebKit and Apple publish no per-tab GPU memory limit for iOS Safari that we could
find (**Unverified**). The app already handles `webglcontextlost` by telling the user to lower the quality setting.

### 2.5 Aircraft models (Observed; parsed from `data/models/*.sfom`)

The 21 models total 495,245 triangles and 11.9 MB on disk. **[corrected by verifier]** The 21 `.sfom` files total
12,077,852 B on disk, which is 12.1 MB or 11.5 MiB, not 11.9 MB. If every type is loaded, their textures take **≈ 340 MiB
of GPU memory as RGBA8 with mips**.

- Per type: 1–14 textures, mostly 1024².
- Heaviest: `b744` 28 MiB, `a333` 26 MiB (14 textures), `a388` 24 MiB.

As KTX2 transcoded to ASTC 4×4 (8 bpp) this would be about 85 MiB. As ETC1S transcoded to ETC2 RGB (4 bpp), about
43 MiB (Inferred from the format bit rates).

---

## 3. How the renderer's limits map to the QA pass-1 findings

`docs/qa/review_pass1.md`, top 15 plus the per-image notes. "Engine" means a renderer feature would fix it;
"content" means modelling or texturing; "data" means source geometry.

| Pass-1 finding | Root cause in today's code | Kind | What fixes it |
|---|---|---|---|
| #1 Grey-box materials everywhere (bridges, terminals, roofs, hangars) | The world shader has no texture inputs, only vertex colour and procedural patterns; no normal maps | engine + content | Textured PBR materials (baseColor/ORM/normal, KTX2) with Blender-authored assets (section 7) |
| #1 Facade glass "flat, reflectionless" | Reflections come only from the equirect sky; no SSR or probes; the glass has no depth | engine | SSR (`SSRNode`), a PMREM environment, and parallax "interior mapping" in a TSL material |
| #4 Washed-out tone, "nothing darkens where it touches the ground" | Ambient is a flat 3-term hemisphere with no AO except height/normal hacks; exposure is a heuristic; ACES fit | engine | GTAO/SSAO (screen space) plus baked AO (static assets), GGX-prefiltered IBL, AgX/Neutral tone mapping, optional auto-exposure |
| #5 Ground smear at grazing angles, blurry pavement edges | 0.8 m/texel airfield bake; anisotropy was 1 (since fixed) | content / data | Keep analytic SDF edges and markings in the shader; add vector pavement edges. TAA also helps. |
| #6 Missing "2", invisible centrelines | Thresholded mip-mapped glyph texture | engine (fixed) | Already fixed with SDF; the SDF approach ports to TSL unchanged |
| #10, #11 Hold-bar "sawtooth", crawling highlight on wing edges, dotted mast shadow, speckled bridge shadow | MSAA resolves only geometric edges; alpha-blended ribbons, specular highlights and procedural patterns alias; the 5-tap per-pixel-rotated shadow PCF is noisy and never accumulated over time | engine | TRAA (temporal accumulation with the existing velocity idea), specular AA, softer PCF/PCSS, cascade blending |
| #1, #2, #11 Moiré on corrugated walls and roll-up doors | Periodic patterns (0.25 m ribs, 0.14 m slats) computed in the shader without prefiltering | engine + content | Bake the patterns into mip-mapped normal and ORM maps in Blender; TAA |
| #4 (F10) Blocky mid-range shadows | Cascade 1 or 2 texels of about 0.2–1.7 m at mid range (Inferred from the split formula and resolutions) | engine | More cascades or larger maps at mid range; `CSMShadowNode` fade; contact shadows / GTAO |
| #15, #2, #5 Illegible gate signs and VDGS | 70 px Canvas2D bitmap atlas with mip blur; small panels | engine + content | MSDF atlas generated offline (the strings are fixed) and sampled in a TSL material; larger panels as the review suggests |
| #12 Tower "golf tee", #13 ITB "tarp" roof, confetti cars, garage facades | Geometry and procedural placeholders | content | Blender-authored tower, ITB roof and garages from reference drawings and photos (section 7) |
| Overview: coastline stair-steps, city tiling, streaked hills, "blob" vegetation | Terrain is procedural fbm with hand-drawn km polygons; region texture is 2048² over 120 km (≈ 58 m/texel); the city is a procedural hash grid | **data** | A real DEM and shoreline vectors, real building footprints or licensed 3-D tiles (sections 4.3 and 9). No engine fixes this. |
| #7 Liveries, #8 floating nav lights, #2 impossible poses, #14 GSE placement | Data and logic (mostly fixed; see HANDOFF §6) | data / logic | Not engine issues |
| Frame-time hitches (not in pass 1; Inferred) | Every dynamic-resolution step reallocates all FBOs; the bridge mesh is rebuilt every frame while docking | engine | Fixed-size targets with viewport scaling or TAAU upscaling; instanced or batched bridge parts moved by matrices |

Engine-level causes account for about half of the pass-1 top 15 (#1 lighting part, #4, #5 partly, #10, #11, #15);
content accounts for #1, #12, #13 and #14; and data for the overview items. **[corrected by verifier]** "About half"
overstates it. Of the top 15, only #4 and #11 are mainly engine issues. Four more are partly engine: #1 (glass and
lighting), #5, #10 (the hold-bar sawtooth; the one-sided and doubled dashes are a `markings.js` logic bug) and #15
(sign legibility; the reviewer's fix is mainly bigger characters, about 1 m). The overview row above is pass-1 #9 (data).
#3, blank aprons, is missing from the table; it is content (stand markings exist but are switched off). **Changing the engine alone will not make
the airport look real.** It removes the ceiling that currently makes even good content look flat.

---

## 4. Candidate engines

Versions and dates are Observed from the npm registry on 24 Sep 2026. Sizes are Observed from downloads, and gzip
sizes use `gzip -9`.

### 4.1 three.js r186 (npm 0.186.0, published 2026-09-08, MIT)

**Renderer status.** The manual page `manual/pages/webgpurenderer.html` at r186 says (Documented):

- "If a device/browser doesn't support WebGPU, the renderer can automatically fall back to using a WebGL 2 backend."
- "Custom materials based on `ShaderMaterial`, `RawShaderMaterial` and modifications of built-in materials via
  `onBeforeCompile()` are not supported in `WebGPURenderer`. This part of your application must be ported to node
  materials and TSL."
- "`EffectComposer` with its effect passes are not supported"; post effects are TSL nodes.
- "The renderer itself is still in an experimental state … depending on your application and scene setup, you will
  encounter missing features or a better performance with `WebGLRenderer`."
- `WebGLRenderer` "is still maintained and the recommended choice for pure WebGL 2 applications … there are no plans
  to add larger new features to the renderer".

**Features present in the r186 package (Observed).**

- **Shadows.**
  - `examples/jsm/csm/CSMShadowNode.js` works with WebGPURenderer only; its doc says "When using WebGLRenderer, use
    CSM instead". Defaults: 3 cascades, 'practical' splits, `maxFar` 100000.
  - New in r186: `examples/jsm/lights/SunLight.js` + `SunLightShadow.js`: "two cascaded shadow maps", "default
    mapSize is 1024x1024 per cascade". It must be registered with `renderer.library.addLight(SunLightNode, SunLight)`.
    **[corrected by verifier]** The registration is needed only "when used with `WebGPURenderer`" (SunLight.js doc).
    r186 also supports `SunLight` in the classic `WebGLRenderer`: `WebGLLights.js` `isSunLight`, and
    `shadowmap_pars_fragment` `SUN_LIGHT_CASCADES 2`. The release notes list it under WebGLRenderer as well.
  - PCF, PCFSoft and VSM shadow-map types. **[corrected by verifier]** `PCFSoftShadowMap` is "@deprecated since r186"
    (`src/constants.js`). Both renderers warn "PCFSoftShadowMap has been removed. Using PCFShadowMap instead." The
    usable types are Basic, PCF (with `shadow.radius`/`blurSamples`) and VSM.
- **AO and GI** (`examples/jsm/tsl/display/`): `GTAONode` (Activision GTAO), `SSAONode` (new in r186), `SSGINode`
  (SSRT3-style GI), and `DenoiseNode`.
- **Reflections:** `SSRNode`; `PMREMGenerator` gives GGX-prefiltered IBL.
- **Anti-aliasing:**
  - `TRAANode`: "Note: MSAA must be disabled when TRAA is in use."
  - `TAAUNode`: temporal AA plus upscaling from a lower internal resolution, "an alternative to FSR2/3".
  - `SMAANode` (SMAA 1x Medium), `FXAANode`, `FSR1Node`, `SSAAPassNode`.
- **Other post:** `BloomNode`, `OITPassNode` (weighted blended OIT; "MSAA is only supported with the WebGPU backend").
  Tone mappers include `AgXToneMapping` and `NeutralToneMapping`.
- **Lights:** `ClusteredLightsNode`, Forward+ clustered shading built on compute, so probably WebGPU-only (Inferred
  from its use of `renderer.compute`; not tested on the WebGL backend). `MeshPhysicalMaterial.retroreflectivity`
  (new in r186) suits signs and markings under landing lights.
- **Assets:** `KTX2Loader` detects ASTC, ETC2, BC and PVRTC on both backends and transcodes Basis in Web Workers.
  `libs/meshopt_decoder.module.js` embeds its WASM as base64 and calls `WebAssembly.instantiate`.
  **[corrected by verifier]** The WASM is embedded as an inline string in meshoptimizer's own packed text encoding,
  decoded by its `unpack()` function, not as base64. The point stands: there is no separate file, but it still needs
  `WebAssembly.instantiate`. `GLTFLoader` and
  `DRACOLoader` are included.
- **Batching:** `BatchedMesh` uses `WEBGL_multi_draw` on the WebGL backend. On WebGPU it issues one `drawIndexed` per
  sub-object inside one pass encoder. `InstancedMesh` works on both.
- **Depth:** `reversedDepthBuffer` on WebGPU. On the WebGL backend it needs `EXT_clip_control`, and falls back with a
  warning when that is missing. `logarithmicDepthBuffer` is also available.
- **API churn:** `PostProcessing` was renamed `RenderPipeline` in r183 (a deprecation warning in
  `renderers/common/PostProcessing.js`). Pin the version.
- **TSL escape hatches:** `glslFn` and `wgslFn` accept native code for one backend each
  (`src/nodes/code/FunctionNode.js`). Portable code has to be TSL.

**Text.**

- troika-three-text 0.52.5 derives materials through `onBeforeCompile` (`createDerivedMaterial` in troika-three-utils).
  It therefore does not work with `WebGPURenderer`, per the manual quote above (three.js issue #26719 discusses
  this).
- By default it fetches Roboto from Google Fonts and fallback fonts from jsDelivr (`README.md` lines 152 and 318–320).
  In an artifact those fetches are blocked, so the font would have to be bundled.
- Our sign strings are known at build time, so an **offline MSDF atlas and a small TSL material** is simpler and works
  on both backends (Inferred). The dynamic labels stay in the DOM, as they are today.

**Sky.** @takram/three-atmosphere 0.19.1 (MIT) implements Bruneton's precomputed scattering. It ships a WebGPU/TSL
implementation (`src/webgpu/`: `SkyNode`, `AerialPerspectiveNode`, `SkyEnvironmentNode`, `AtmosphereLight`, with
separate WebGL and WebGPU LUT paths). It is optional: our own sky precompute also ports.

**Bundle size (Observed; esbuild 0.28.2, minified ESM, tree-shaken).**

| Bundle | Minified | gzip |
|---|---|---|
| WebGPURenderer core set (renderer, node PBR material, `InstancedMesh`, `BatchedMesh`, `RenderPipeline`, `GLTFLoader`) | 1,143,609 B | 300,025 B |
| Plus `KTX2Loader`, meshopt decoder, `CSMShadowNode`, GTAO, TRAA, SMAA, bloom | 1,466,380 B | 419,911 B |
| Classic `WebGLRenderer` set (`CSM`, `EffectComposer`, GTAO, SMAA, TAA passes, troika) | 1,113,271 B | 329,513 B |
| For scale: today's app code bundled (without `data/`) | 322,134 B | 120,755 B |

**[corrected by verifier]** The app-code row reproduces exactly (esbuild 0.28.2, `js/live/entry.js`, `data/` external:
322,134 B / 120,755 B). The three.js rows could not be reproduced exactly because the entry files were not saved.
My reconstructions give 1,035,754 B / 269,602 B (core set with `MeshStandardNodeMaterial`), 1,157,326 B / 303,826 B (the
same plus `import * as TSL`) and 1,309,036 B / 374,969 B (plus KTX2, meshopt, CSM, GTAO, TRAA, SMAA, bloom). That is the
same range, 1.0–1.5 MB minified, so the conclusion holds.

Also Observed:

- The Basis transcoder WASM is 527,333 B.
- r186 ships **no UMD build**: `build/` has only ES modules and a 631-byte CJS stub.
- cdnjs carries only the 10 `build/` files, not `examples/jsm`. Its `three.webgpu.min.js` is actually unminified
  (2,284,823 B, the same as the raw file). jsDelivr's auto-minified copy is 820,842 B.

### 4.2 Babylon.js 9 (npm @babylonjs/core 9.28.0, published 2026-09-24, Apache-2.0)

- The 9.0 announcement (Microsoft, 26 Mar 2026; Documented) lists:
  - Clustered Lighting, "Works on both WebGPU and WebGL 2";
  - Volumetric Lighting ("WebGPU compute shaders and WebGL 2 fallbacks"); **[corrected by verifier]** That is a
    paraphrase, not a quote. The post says it "takes full advantage of WebGPU compute shaders for optimal performance.
    WebGL 2 is also supported with graceful fallbacks." Clustered Lighting reads "This system works on both WebGPU and
    WebGL 2".
  - Frame Graph v1;
  - textured area lights;
  - Gaussian splats with shadows.
- Present in the 9.28 package (Observed):
  - `CascadedShadowGenerator`, `SSAO2RenderingPipeline`, `SSRRenderingPipeline`, `TAARenderingPipeline`,
    `FxaaPostProcess`, `IBLShadowsRenderPipeline`, thin instances, `ClusteredLightContainer`;
  - a geospatial camera and geospatial math;
  - glTF `KHR_texture_basisu`, `EXT_meshopt_compression`, `KHR_draco_mesh_compression`;
  - `@babylonjs/addons` has a physically based atmosphere with aerial perspective (GLSL and WGSL).
- **Artifact blocker (Observed in source):** `WebGPUEngine.initAsync` loads glslang and twgsl WASM, by default from
  `Tools._DefaultCdnUrl = "https://cdn.babylonjs.com"` (`Engines/WebGPU/webgpuTintWASM.js`, `Misc/tools.pure.js`).
  That host is not on the artifact allowlist. The files would have to be self-hosted as artifact files, and that only
  works if WASM is allowed (Unverified). **[corrected by verifier]** In 9.28.0, `initAsync` only requests the
  adapter and device. glslang and twgsl are loaded lazily by `_preparePipelineContextAsync` when a pipeline's shader
  language is GLSL (`webgpuEngine.pure.js:1635`). On WebGPU, materials default to WGSL (`material.pure.js:763-766`),
  and the package ships 472 WGSL shader modules, including `pbr` and `openpbr`. So the CDN fetch is a blocker only for
  custom shaders kept in GLSL. It is conditional, not inherent. `@babylonjs/addons` 9.28 also ships an `msdfText`
  addon.
- **Size (Observed):**
  - `babylonjs@9.28.0/babylon.js` UMD: 8,592,001 B (1,847,970 B gzip).
  - Loaders: 848,814 B.
  - cdnjs lags behind at babylonjs 8.46.2.
- **Porting:** the whole scene layer would be rewritten against Babylon's scene graph (left-handed by default), and
  shaders re-expressed as `ShaderMaterial`, Node Materials or material plugins. GLSL is accepted, but on WebGPU it goes
  through the twgsl conversion above.

### 4.3 CesiumJS 1.145 (npm, published 2026-09-01, Apache-2.0), Google Photorealistic 3D Tiles, Cesium ion

- **What it is.** A WebGL globe engine for 3D Tiles, terrain, imagery and glTF models. CHANGES.md for 1.145
  (2026-09-02) has no WebGPU entries (Observed, grep).
- **Size (Observed, `Build/Cesium`):**
  - `Cesium.js` 6,018,837 B (1,753,479 B gzip);
  - Workers 1.1 MB, Assets 4.4 MB, ThirdParty 1.1 MB, Widgets 0.5 MB.
  - The static assets and Workers are loaded at run time from `CESIUM_BASE_URL`.
- **Google Photorealistic 3D Tiles (Map Tiles API policies page; Documented, archived in
  `pages/google_tile_policies.html`):**
  - "you must not pre-fetch, index, store, or cache any Content except under the limited conditions stated in the
    terms."
  - Prohibited uses include "Offline uses, including for any of the above", plus "Image analysis", "Machine
    interpretation", "Object detection or identification" and "Geodata extraction or resale".
  - "You may overlay your own 3D objects on Photorealistic 3D Tiles as long as the 3D objects aren't extracted, traced,
    or otherwise derived by hand or machine from Photorealistic 3D Tiles."
  - Attribution: "You must aggregate, sort, and display in a line, all attributions for displayed tiles", and "clear
    Google Maps attribution … in the form of the Google Maps logo whenever possible". **[corrected by verifier]** The
    exact wording is "You must include clear Google Maps attribution when displaying content from Google Maps Platform
    APIs in your app or website. Attribution should take the form of the Google Maps logo whenever possible." Page last
    updated 2026-09-17 UTC.
- **Cesium ion (pricing page; Documented):**
  - The Community plan is "Personal and non-commercial use", with 15 GB streaming a month and 1,000 Google
    Photorealistic 3D Tiles root tiles a month.
- **Consequences (Inferred):**
  - The snapshot artifact cannot use Google tiles at all: the CSP blocks the fetches, and storing tiles is forbidden.
  - The standalone app could stream them live with an API key, visible attribution and billing. That is a licensing
    decision for the owner, like the satellite imagery rule in CLAUDE.md.
  - Our own models must not be traced from the tiles.
  - Close-range apron rendering (materials, AO, AA) is not Cesium's strength, and the port would be a full rewrite.
  - 3D Tiles can also be streamed into three.js with the NASA-AMMOS `3d-tiles-renderer` (npm 0.5.3, Apache-2.0), so
    the same licensing choice does not require Cesium.

### 4.4 deck.gl 9.4 (published 2026-09-05, MIT)

- The whats-new page (Documented): "WebGPU support remains experimental and is not yet recommended for production.
  Some layers and features remain unavailable or only partially supported."
- Lighting is `LightingEffect`, whose shadows are an experimental `_shadow` flag on directional lights. glTF comes
  through `ScenegraphLayer`, and 3D Tiles through `Tile3DLayer`. (Inferred from a summary of the same page; the
  `_shadow` flag was not checked in the deck.gl source.) **[corrected by verifier]** The flag is documented on that
  page, in an older release's section: "As an experimental feature, the LightingEffect can now render shadows from up
  to two directional light sources. To enable shadows, set _shadow: true when constructing a DirectionalLight or
  SunLight."
- `dist.min.js` is 2,073,497 B (575,131 B gzip) (Observed).
- It is a data-visualisation framework and not built for a photoreal apron. It would suit a 2-D or 2.5-D map mode,
  which we do not need.

### 4.5 Filament (native v1.77.2; web build npm `filament` 1.53.4 from 2024-08-09; Apache-2.0)

**[corrected by verifier]** The latest native tag is v1.77.1 (`git ls-remote`, 24 Sep 2026). v1.77.2 exists only as
`rc/1.77.2-cut` and a RELEASE_NOTES header. A current web build is published: GitHub release v1.77.1 ships
`filament-v1.77.1-web.tgz` (1,943,721 B; `filament.js`, `filament.wasm`, `filament.d.ts`; tar dated 2026-09-21), and
`web/filament-js/package.json` on main is at 1.77.1. Only npm publishing stopped at 1.53.4.

- **Features.** `README.md` at HEAD (2026-09-23; Documented) lists:
  - a clustered forward renderer;
  - cascaded shadows with EVSM, PCSS, DPCF or PCF, plus contact shadows;
  - SSAO, SSR, IBL, specular anti-aliasing;
  - TAA, FXAA and MSAA;
  - GT7, PBR Neutral, AgX and ACES tone mappers;
  - FSR dynamic resolution;
  - glTF with `KHR_texture_basisu` and `EXT_meshopt_compression`.
  In short, the strongest PBR feature set of the candidates.
- **Backends:** "WebGPU for Android, Linux, macOS, and Windows" (native, not the browser) and "WebGL 2.0 for all
  browsers supporting it".
- **Web tooling:**
  - Materials ship as precompiled `.filamat` files (`web/examples/triangle.md`: `engine.createMaterial('triangle.filamat')`).
  - Our procedural shaders would have to become Filament material definitions compiled offline.
  - The npm web package is 25 minor versions behind native (Observed), so the web target gets little maintenance.
    **[corrected by verifier]** The npm lag is real, but the conclusion is refuted: the web build is versioned with
    native and attached to each GitHub release (see the note under the heading). Load it from a release asset, not
    npm.
  - It is a WASM runtime, so it depends on the unverified artifact WASM policy.

### 4.6 Keep and extend the custom renderer

This is possible, and some pieces are cheap:

- TAA: the motion vectors already exist.
- Fixed-size targets: stops the reallocation on every resolution change.
- Instanced bridge parts.

The expensive pieces each need their own mobile validation:

- a GGX-prefiltered IBL;
- an AO pass (needs a normal target);
- a KTX2 path (Basis transcoder integration plus compressed uploads for each format);
- a textured PBR material system with a glTF loader;
- MSDF text;
- a WebGPU backend, which would mean a rewrite.

The inferred effort is comparable to the whole three.js port, with no upstream maintenance afterwards, and one person
carries all the risk.

---

## 5. Artifact and delivery constraints

These come from this session's Artifact tool contract and artifact-design skill (Observed; not a public document).

- **Page size and files.**
  - The rendered page is at most 16 MB, and `data:` URIs count toward it.
  - Supporting files: at most 16 MB per text file and 15 MB per binary file, at most 255 files, and at most 64 MB per
    version.
  - `fetch()` of files published with the page works with relative URLs.
- **Scripts and fetches.**
  - External scripts load only from cdnjs.cloudflare.com, cdn.jsdelivr.net/npm/, unpkg.com, cdn.tailwindcss.com and
    code.jquery.com.
  - "Everything else is blocked … even on those CDNs, anything but a script — stylesheets, images, media,
    fetch/XHR/WebSocket, a library's runtime fetches." **[corrected by verifier]** The same contract has one exception
    this summary leaves out: "external stylesheets ONLY from https://fonts.googleapis.com, with the font files they
    pull from https://fonts.gstatic.com". Whether troika's own script fetch of a gstatic `.woff` is allowed, as
    opposed to one pulled by a CSS `@font-face`, is unverified. Bundling the font remains the safe choice.
  - Web Workers work "from your own files or `blob:` URLs".
- **Unverified: whether the CSP allows `WebAssembly.instantiate`** (for example `'wasm-unsafe-eval'`). The Basis
  transcoder (`KTX2Loader`), the meshopt decoder, Draco, Filament and Babylon's WebGPU compilers all depend on it.
  Phase 0 tests this with a one-line probe.
- **Unverified: whether ES-module `import` from jsDelivr passes the CSP.** It is a script load, so it probably does.
  The recommendation does not rely on it: **bundle three.js into the page** (1.1–1.5 MB minified, measured above).
  That removes the CDN dependency, avoids cdnjs's missing addons and unminified WebGPU build, and keeps the app well
  under 16 MB.
- **No-WASM fallback for the artifact**, if WASM turns out to be blocked:
  - textures as WebP or AVIF, decoded by the browser (more GPU memory; keep the 1024² caps);
  - geometry with `KHR_mesh_quantization` only, which needs no decoder;
  - models as `.glb` files published alongside the page.
- **CDN assets in the artifact.** Every asset (models, fonts, the transcoder) must be a file published with the page.
  No jsDelivr fetches.

---

## 6. Porting inventory for three.js (Observed code structure; effort is Inferred)

**Ports as-is (engine-independent JavaScript, about 250 KB in `js/live` plus `js/world` and `js/aircraft`
builders):**

**[corrected by verifier]** `js/live/*.js` totals 246,745 B, but that includes files that touch the renderer:
`app.js`, `world.js`, `gates.js` (item lists and per-frame mesh rebuilds), and `signs.js`/`markings.js`, which embed
about 2.8 KB of GLSL. The pure-logic modules listed next total 101,267 B (`traffic`, `ground`, `feed`, `lookup`, `ui`,
`about`, `airport`, `lights`, `items`). So "about 250 KB ports as-is" overstates the as-is share. The GLSL figure checks
out: `js/shaders/*.js` 76,822 B plus about 2.8 KB is about 80 KB.

- **Logic modules:** `traffic.js`, `ground.js` (GroundPhysics), `feed.js`, `lookup.js`, `ui.js`, `about.js`,
  `airport.js`, `lights.js` (positions), `items.js`, `geo.js`, `geom.js` (`Geo` → typed arrays), `math.js`.
- **Geometry builders.** These produce `{pos, nrm, uv, col, extra, idx}` typed arrays that map directly onto
  `BufferGeometry` attributes: `terminals.js`, the geometry half of `gates.js`, `markings.js` ribbons, `signs.js`
  panels, masts, EMAS, `terrain.js` chunks, and the `.sfom` decoder in `models.js`.
- **Build-time textures.** Canvas-built textures such as the runway SDF glyph atlas (`textures.js`, EDT) and the sign
  atlas become `DataTexture` or `CanvasTexture`.
- **Camera and app shell.** `controls.js` (CameraRig) and the app loop in `app.js`, with the renderer calls swapped.
  The `window.SFO.qa` hooks keep working, so the QA harness only changes its readiness checks.

**Rewritten in TSL (about 80 KB of GLSL in `js/shaders/` plus the marking and sign shaders):**

- **`ground.js`.** `glyph()`, `band()`, `endMarkings()`, `runwayAt()`, `grassCol()` and `nightLight()` are pure
  arithmetic, texture reads, `fwidth` and `smoothstep`, all of which exist in TSL (`Fn`, `If`, `Loop`,
  `uniformArray`). **The SDF marking logic ports line for line and keeps its analytic anti-aliasing.** It is the
  largest single port (about 450 lines).
- **Bakes.** The airfield and city bakes (`BAKE_*_FS`) become TSL passes rendered to texture with `QuadMesh`. Better:
  move them offline, to Python or Blender, and ship KTX2, which also removes the start-up GPU spike on phones.
- **Other shaders.**
  - `objects.js`: the procedural facade material ids. Most are superseded by Blender textures; keep a TSL fallback for
    the rest.
  - `aircraft_real.js`: the livery-by-region logic becomes a node material.
  - `markings.js` ribbon widening: vertex logic through `positionNode`.
  - `env.js`: water and cloud slabs; the sky can use the TSL port of our precompute or @takram/three-atmosphere.
  - `sprites.js`: instanced billboards.
- **Using `glslFn` would not help:** it runs on the WebGL backend only.

**Dropped (three.js provides these):**

- Cascade maths → `CSMShadowNode` or `SunLight`.
- MSAA FBO management → `RenderPipeline` with TRAA/TAAU.
- The bloom chain → `BloomNode`.
- ACES → AgX or Neutral.
- The two-range depth trick → `reversedDepthBuffer` (WebGPU) or `logarithmicDepthBuffer`.
- Per-item uniform plumbing → node uniforms.
- The texture-unit allocator.

**The classic WebGLRenderer alternative** would let the GLSL run nearly verbatim (`RawShaderMaterial` with
`glslVersion: GLSL3`, after expanding our `#include` chunks). But it has no TRAA: `TAARenderPass` says "no
reprojection so it is no TRAA implementation". There is no WebGPU path and no new renderer features. It would be
cheaper now and a dead end later, so it is not recommended. **[corrected by verifier]** "No new renderer features" is
too strong. r186 itself adds `SunLight` cascaded shadows to `WebGLRenderer`, and `WebGLRenderer` has a
`setNodesHandler` hook for limited node-material support. The manual's wording is "no plans to add *larger* new
features". The recommendation still holds on TRAA, TSL and WebGPU grounds.

---

## 7. Blender 5.0: role and test results

### 7.1 Role

1. **Scripted asset authoring (bpy), deterministic and driven by our data.**
   - Assets: the 2016 control tower, jet bridges, terminal façades and roofs (the ITB great hall), garages, GSE and
     light fixtures.
   - Geometry comes from the same sources as today (SFO Museum footprints, `build_terminal_parts.py`, the surveyed
     stands). Each asset records its sources in glTF `extras` (`src: 'obs' | 'inf'` plus URLs), following the
     observed/inferred rule.
   - Bridges are exported as separate nodes (rotunda, tunnels, cab, drive column) with their pivots, so the runtime
     moves them with matrices instead of rebuilding meshes.
2. **Bakes.**
   - **Sun-independent AO** (and optionally sky visibility) for static assets.
   - **Self-only AO** for movable parts.
   - Procedural detail (corrugation, panel seams, slats) baked to **mip-mapped normal and ORM maps**, which fixes the
     moiré.
   - **Do not bake sun lightmaps.** The app lights the scene with the real solar position and METAR clouds, so a baked
     sun would be wrong for most hours (Inferred).
3. **Export.** glTF 2.0 `.glb`, then glTF-Transform: KTX2 (ETC1S for AO and ORM, UASTC where quality matters),
   meshopt, `KHR_mesh_quantization`. Validate with the Khronos glTF-Validator.
4. **QA reference renders (Cycles, CPU).**
   - Render the QA views (same `qa.look` camera parameters, same sun vector from `solarPosition`) with a physical sky
     and AgX.
   - Give them to the adversarial reviewer next to the WebGL/WebGPU frames. They show how AO, shadow softness and
     exposure should look.
   - This needs the runtime scene in Blender: either a glTF export from the app (three's `GLTFExporter`) or a rebuild
     from `data/*.js` in bpy.

### 7.2 Test in this sandbox (Observed)

Commands:

```
python3 tools/engine/blender_bake_test.py refs/cache/blender_test
MODULES=refs/cache/engine/node node tools/engine/glb_compress.mjs refs/cache/blender_test/asset.glb refs/cache/blender_test/asset_ktx2_meshopt.glb
```

| Step | Result |
|---|---|
| bpy | 5.0.1, build hash a3db93c5b259 (2025-12-16), pip-installed |
| Scene | 8 objects from primitives (apron slab, tapered tower shaft, cab, roof disc, bridge tunnel, 2 legs, tug); materials are Principled BSDF; build time 0.1 s |
| UVs | `uv.smart_project` per object (a non-overlapping lightmap set) |
| AO bake | Cycles on the CPU, 64 samples, AO distance 12 m. Into 8 textures: apron 512², others 256². **8.7–20.5 s** over three runs on the shared 4 vCPU. The apron map shows contact darkening under the shaft, the legs and the tug; the tunnel underside is dark (`ao_contact.png`). Mean AO on UV islands: apron 0.976, shaft 0.890, tunnel 0.637, tug 0.629. |
| AO → glTF | The baked image is wired to the exporter's "glTF Material Output" group (Occlusion input, R channel). **All 8 materials export `occlusionTexture`.** |
| Export | `asset.glb` 313,424 B; generator "Khronos glTF Blender I/O v5.0.21"; PNG images; `TEXCOORD_0`; 0.06 s |
| Validation | Khronos glTF-Validator 2.0.0-dev.3.10: **0 errors, 0 warnings** |
| Compression | glTF-Transform 4.5.0 with ktx2-encoder 0.6.0 (basis_universal WASM, ETC1S q128, mips) and meshoptimizer: **101,060 B (0.32×)** in 1.5 s. `KHR_texture_basisu`, `EXT_meshopt_compression`, `KHR_mesh_quantization`. The validator reports 0 errors and 16 warnings, because it predates `image/ktx2`. |
| Cycles reference | 480×270, 32 spp, AgX, sun plus constant sky: 0.8–1.7 s (`ref_cycles.png`) |
| EEVEE headless | **Fails.** "Couldn't open libEGL.so.1", and the process aborts (exit 134 / −6). The probe runs in a child process so it cannot kill the test. Use Cycles only here. |
| Exporter limits | Image formats AUTO, JPEG, WEBP or NONE; **no KTX2**. Draco is available (`libextern_draco.so`). A `gltfpack` option exists but needs an external binary. |
| KTX-Software | The GitHub release download is blocked by the proxy (HTTP 403), so the npm `ktx2-encoder` (MIT, WASM) was used instead. **[corrected by verifier]** Refuted at 09:02 UTC: `https://github.com/KhronosGroup/KTX-Software/releases/download/v4.4.2/KTX-Software-4.4.2-Linux-x86_64.tar.bz2` downloaded through the proxy (HTTP 200 after redirect to release-assets.githubusercontent.com, 7,030,325 B, valid bzip2). Only the HTML release *pages* (`/releases/tag/…`, `/releases/latest`) return 403. The file was deleted, not kept. |

### 7.3 Constraints

- Blender licence (Documented, blender.org/about/license): "What you create with Blender is your sole property … free
  for you to use as you like", so the assets and renders are ours. But "such scripts (if published) are being shared
  under a GPL compliant license". **If the repository is ever published, tools that `import bpy` must be under a
  GPL-compatible licence.** **[corrected by verifier]** It is probably already published. `/home/user/Calc/pc12/CLAUDE.md`
  states "The repo is public" (origin github.com/bobbychen2000/Calc), and `sfo3d/` has 198 tracked files there.
  `tools/engine/` is untracked for now. Committing `blender_bake_test.py` would publish it, so choose its licence
  before that commit. (github.com returned HTTP 200 for the repo page through the proxy; that it is visible without
  authentication was not independently verified.)
- CPU-only Cycles: full-airport reference frames at 1280×720 will take minutes each (Inferred, not measured). Keep them
  to a few QA views at low sample counts. Whether the OIDN denoiser is available in the pip `bpy` is **Unverified**.
  **[corrected by verifier]** Now verified: `_cycles.with_openimagedenoise` is `True`, and a 64×64 Cycles CPU render
  with `denoiser='OPENIMAGEDENOISE'` completed in 0.23 s without warnings.
- The tower, ITB roof and garages need real reference material first, per the project rule "never make unverified key
  assumptions". See the open questions.

---

## 8. Comparison and phased plan

### 8.1 Matrix (Inferred scores, 5 = best; based on the evidence above)

| Criterion | Custom (today) | Custom (extended) | three.js WebGPURenderer | three.js WebGLRenderer | Babylon.js 9 | CesiumJS | deck.gl | Filament (web) |
|---|---|---|---|---|---|---|---|---|
| Visual ceiling: shadows, AO, reflections, IBL, AA | 2 | 3–4 | **5** (GTAO/SSGI/SSR/PMREM/TRAA/CSM) | 3–4 (no TRAA) | 5 | 3 close up (5 for city context, if licensed) | 2 | 5 |
| Mobile: iPhone WebGPU / WebGL 2 | 3 (WebGL only; about 830 MiB on high) | 3 | **4** (WebGPU on iOS 26+, WebGL 2 fallback; *Unverified* on device) | 3 | 4 (*Unverified*) | 2–3 | 3 | 3 (WebGL 2 only) |
| Bundle and artifact fit | 5 (0.32 MB) | 5 | **4** (1.1–1.5 MB; KTX2 and meshopt need WASM) | 4 | 2 (8.6 MB UMD; compiler WASM from a blocked host; **[corrected by verifier]** only for GLSL shaders, see 4.2) | 1 (6 MB + assets + workers; tiles cannot be stored) | 3 | 2 (WASM) |
| Porting cost (higher = cheaper) | 5 | 2 (writing an engine) | **3** (TSL rewrite of about 80 KB GLSL) | 4 (GLSL nearly verbatim) | 2 | 1 | 2 | 1 (`.filamat` materials) |
| Risk (higher = safer) | 3 (one maintainer) | 2 | **3** ("experimental"; API churn; mitigated by pinning and the fallback) | 4 now, 2 long-term | 4 | 3 (licensing) | 2 | 2 (stale web build; **[corrected by verifier]** npm is stale, but GitHub releases ship a current v1.77.1 web build, see 4.5) |

### 8.2 Phases, each gated on QA and real-time frame rate

The frame-rate gates for every phase use the recorded snapshot on the **user's phone** and on a desktop:

- ≥ 30 fps at the mobile tier in the overview, gate and hold views, with no context loss over 10 minutes;
- ≥ 60 fps on a desktop GPU.

The current code already targets 33 ms frames (`app.js:320`).

**Phase 0: spikes (about 1–2 days).**

- Build a `bench3.html` that renders today's terrain, markings and 33 snapshot aircraft with three.js r186 in three
  modes: WebGPU, `forceWebGL`, and the custom renderer.
  - It reports fps, draw calls (`renderer.info`) and memory.
  - The user runs it on their phone and reports back.
- Probe the artifact CSP with one small artifact:
  - ES-module import from jsDelivr;
  - `WebAssembly.instantiate` (meshopt);
  - a blob Worker;
  - fetch of a published `.ktx2`.
- Check whether headless Chromium in `livetest.mjs` exposes WebGPU (with SwiftShader or Vulkan flags). If it does not,
  every harness render comes from the WebGL backend and phone-side WebGPU needs its own spot checks.

Exit: a go/no-go on WebGPURenderer versus WebGLRenderer, backed by numbers.

**Phase 1: asset pipeline, independent of the engine (about 3–5 days, can run in parallel).**

- Blender scripts (`tools/blender/…`) for bridges and GSE first (clear dimensions), then the tower and ITB once
  references are available.
- Bakes, glb, glTF-Transform and validator in one script. A size budget for each asset.
- Convert the `.sfom` aircraft to `.glb` + KTX2 (the livery zones become a vertex attribute or mask texture).
- The current renderer can keep loading `.sfom` until the switch.

**Phase 2: three.js scaffold behind the existing item interface (about 2–3 days).**

- `WebGPURenderer`, created asynchronously with `forceWebGL` behind a setting.
- The camera rig, the app loop, `window.SFO.qa` and the quality tiers are mapped onto it.
- Terrain, water, buildings and bridges as `BufferGeometry` from the existing builders.
- Fixed-size render targets; dynamic resolution through `TAAUNode` or viewport scale, never reallocation.

**Phase 3: ground in TSL (about 4–6 days).**

- Port `groundfuncs`, the runway SDF, blast pads, markings ribbons and signs, with pixel-diff checks against the
  current renderer on the `thr_28L`, `thr_28R`, `hold:*` and overview views.
- Move the airfield and city bakes offline.

Exit: runway and marking crops that the reviewer cannot tell apart from, or judges better than, the pass-2 renders.

**Phase 4: light, shadow, post (about 2–3 days).**

- `CSMShadowNode` (3 cascades, with fade) or `SunLight` (2 cascades) per tier, plus soft PCF.
- PMREM from our sky, or @takram atmosphere.
- GTAO at half resolution on mobile, full on desktop.
- TRAA, with MSAA off.
- AgX tone mapping and bloom.
- Night lights as instanced sprites; clustered lights only on WebGPU.

Exit: Cycles reference comparison for the tower and gate views, and an adversarial review pass.

**Phase 5: aircraft and dynamic objects (about 2–3 days).**

- glTF aircraft with KTX2 textures and the livery node material.
- `InstancedMesh` or `BatchedMesh` for GSE, cars and bridge parts, with docking by matrices.
- Nav, strobe and beacon anchors taken from the glTF.

Exit: frame-rate gates with the full snapshot traffic.

**Phase 6: switch and package (about 2–3 days).**

- Retire `js/gl.js` and `js/renderer.js` once phases 3–5 pass.
- Bundle with esbuild.
- Artifact: page ≤ 16 MB, with the models, KTX2 textures and transcoder as published files, or the no-WASM fallback
  from section 5.

The whole plan comes to roughly **3–5 weeks of focused work** (Inferred). It can be cut short safely after phase 0 if
the numbers say otherwise, because phase 1 has value on either engine.

---

## 9. Open questions (for the user or a follow-up)

1. **Which iPhone and iOS version does the user have?** WebGPU needs iOS 26 or later, which means iPhone 11, iPhone SE (2nd
   generation) or newer (Documented, Apple's iOS 26 compatibility list). Anything older runs the WebGL 2 fallback.
2. **Will the user run the phase-0 benchmark page on the phone?** This sandbox cannot measure mobile GPU performance.
   Every mobile performance statement here is **Unverified**.
3. **Photoreal city context: Google 3D Tiles in the standalone app only** (live streaming, API key, billing,
   attribution; no caching; nothing in the artifact), or licence-clean sources? Candidates for the latter, not yet
   checked: USGS 3DEP terrain, shoreline vectors, open building footprints. This decides whether the "overview" defects
   are fixed with data or with licensed tiles.
4. **Artifact CSP:** is `WebAssembly.instantiate` allowed? This decides between KTX2 and meshopt or WebP and
   quantisation in the artifact (phase 0 probe).
5. **Reference material** for the 2016 SFO control tower and the ITB roof (drawings, dimensions, licensed photos),
   needed before the Blender work on them.
6. **Repository publication:** if the repository becomes public, the bpy tools must be GPL-compatible (Blender licence
   page). **[corrected by verifier]** The repository is documented as already public (see 7.3). The question is which
   GPL-compatible licence to use before `tools/engine/*.py` is committed.
7. **QA harness:** does headless Chromium here expose WebGPU? If not, how many phone-side checks does the user accept
   for WebGPU-only paths?

---

## 10. Sources

**Code and packages (Observed; local copies under `refs/cache/engine/`):**

- three.js r186, npm `three@0.186.0`:
  - `build/`
  - `src/renderers/webgpu/WebGPURenderer.js`
  - `src/renderers/webgl-fallback/WebGLBackend.js`
  - `src/renderers/webgpu/WebGPUBackend.js`
  - `src/objects/BatchedMesh.js`
  - `src/renderers/common/PostProcessing.js`
  - `src/materials/MeshPhysicalMaterial.js`
  - `src/nodes/code/FunctionNode.js`
  - `examples/jsm/{csm,lights,tsl/display,tsl/lighting,loaders,libs,postprocessing}`
- three.js manual, `manual/pages/webgpurenderer.html` at tag r186 (git clone of github.com/mrdoob/three.js).
  Web copy: https://threejs.org/manual/#en/webgpurenderer
- troika-three-text 0.52.5 (`README.md`, `dist/troika-three-text.esm.js`). three.js issue on onBeforeCompile and
  troika: https://github.com/mrdoob/three.js/issues/26719
- @takram/three-atmosphere 0.19.1 (`README.md`, `CHANGELOG.md`, `src/webgpu/`)
- @babylonjs/core 9.28.0 (`Engines/WebGPU/webgpuTintWASM.js`, `Engines/webgpuEngine.pure.js`, `Misc/tools.pure.js`,
  module list) and @babylonjs/addons 9.28.0
- cesium 1.145.0 (`CHANGES.md`, `Build/Cesium` sizes)
- Filament at HEAD a5e4a836 (2026-09-23): `README.md`, `RELEASE_NOTES.md`, `web/filament-js/package.json`,
  `web/examples/triangle.md`, from https://github.com/google/filament. npm `filament` metadata.
- npm registry metadata for all packages: https://registry.npmjs.org/
- cdnjs API: https://api.cdnjs.com/libraries/three.js
- jsDelivr files: https://cdn.jsdelivr.net/npm/three@0.186.0/

**Web pages (Documented; archived in `refs/cache/engine/pages/`):**

- WebKit, "WebKit Features in Safari 26.0" (15 Sep 2025): https://webkit.org/blog/17333/webkit-features-in-safari-26-0/
- Apple, iPhone models compatible with iOS 26: https://support.apple.com/guide/iphone/iphone-models-compatible-with-ios-26-iphe3fa5df43/26/ios/26
- Google Maps Platform, Map Tiles API policies: https://developers.google.com/maps/documentation/tile/policies
- Cesium ion pricing: https://cesium.com/platform/cesium-ion/pricing/
- Microsoft, "Announcing Babylon.js 9.0" (26 Mar 2026): https://blogs.windows.com/windowsdeveloper/2026/03/26/announcing-babylon-js-9-0/
- deck.gl, What's New (v9.4, 5 Sep 2026): https://deck.gl/docs/whats-new
- Blender licence: https://www.blender.org/about/license/
- three.js r186 release notes: https://github.com/mrdoob/three.js/releases/tag/r186 (read through WebFetch; the direct
  download returned 403 from the proxy)

**This session's Artifact tool contract and artifact-design skill:** the CSP allowlist, size limits and Worker/fetch
rules in section 5.

**Measurements (Observed, reproducible):**

- `tools/engine/blender_bake_test.py` → `refs/cache/blender_test/{report.json, asset.glb, ao_*.png, ref_cycles.png, scene.blend}`
- `tools/engine/glb_compress.mjs` → `refs/cache/blender_test/{asset_ktx2_meshopt.glb, compress.json}`
- Bundle sizes: esbuild 0.28.2 over three entry files (see section 4.1); the npm packages are in
  `refs/cache/engine/node/`.

---

## Verification (adversarial check)

Independent re-check on 24 Sep 2026, 08:55–09:10 UTC. Every cited source was fetched again from its original URL rather
than from `refs/cache/engine/pages/`:

- npm packages were downloaded fresh from registry.npmjs.org. The cached tarballs' SHA-1 values match the registry for
  three, cesium, @babylonjs/core, troika and @takram.
- The three.js r186 manual came from raw.githubusercontent.com at tag `r186`.
- The WebKit, Apple, Google, Cesium, Microsoft, deck.gl and Blender pages were fetched with curl. The three.js r186
  release page and issue #26719 were read through WebFetch, because github.com HTML pages return 403 from the proxy.
- `tools/engine/blender_bake_test.py` and `glb_compress.mjs` were re-run into a scratch directory, and repository code
  was read at the cited lines.

Scratch outputs were not kept in the repo. Verdicts: **confirmed** (re-observed), **refuted** (wrong or overstated;
fixed inline, marked [corrected by verifier]), **unverifiable** (could not be checked here).

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | Package versions, dates and licences: three 0.186.0 (2026-09-08, MIT), @babylonjs/core 9.28.0 (2026-09-24, Apache-2.0), cesium 1.145.0 (2026-09-01), deck.gl 9.4.0 (2026-09-05, MIT), filament 1.53.4 (2024-08-09), troika-three-text 0.52.5, @takram/three-atmosphere 0.19.1 (MIT), 3d-tiles-renderer 0.5.3 (Apache-2.0), ktx2-encoder 0.6.0, @gltf-transform/core 4.5.0, esbuild 0.28.2 | confirmed | registry.npmjs.org `dist-tags.latest`, `time`, `license` for each package |
| 2 | Manual quotes: automatic WebGL 2 fallback; ShaderMaterial, RawShaderMaterial and onBeforeCompile unsupported; EffectComposer unsupported; "still in an experimental state"; WebGLRenderer "recommended choice … no plans to add larger new features" | confirmed | raw.githubusercontent.com/mrdoob/three.js/r186/manual/pages/webgpurenderer.html; all five passages present verbatim |
| 3 | "Its WebGL 2 fallback can be slower than WebGLRenderer, as the manual says" | refuted (minor) | The manual says WebGPURenderer in general may have "missing features or a better performance with WebGLRenderer". It does not single out the fallback. Fixed inline. |
| 4 | CSMShadowNode is WebGPURenderer-only ("When using WebGLRenderer, use CSM instead"); defaults: 3 cascades, 'practical' splits, maxFar 100000 | confirmed | `examples/jsm/csm/CSMShadowNode.js` lines 41–42, 73, 81, 89 |
| 5 | SunLight is new in r186, with 2 cascades at 1024² and must be registered with `renderer.library.addLight` | confirmed, with a correction | Absent in 0.185.1, present in 0.186.0. `_cascadeCount = 2`; "default mapSize is 1024x1024 per cascade". Registration is required only "when used with WebGPURenderer". SunLight also works in the classic WebGLRenderer (`WebGLLights.js` `isSunLight`; `SUN_LIGHT_CASCADES 2` in `shadowmap_pars_fragment`; release notes). Fixed inline in 4.1 and 6. |
| 6 | "PCF, PCFSoft and VSM shadow-map types" | refuted | `src/constants.js`: `PCFSoftShadowMap` "@deprecated since r186". `Renderer.js:904` and `WebGLShadowMap.js:101` warn "PCFSoftShadowMap has been removed. Using PCFShadowMap instead." |
| 7 | GTAONode (Activision), SSAONode (new in r186), SSGINode (SSRT3), SSRNode, DenoiseNode, TRAANode ("MSAA must be disabled when TRAA is in use"), TAAUNode ("alternative to FSR2/3"), SMAANode ("SMAA 1x Medium"), FXAANode, FSR1Node, SSAAPassNode, BloomNode, OITPassNode ("MSAA is only supported with the WebGPU backend", new in r186), AgX and Neutral tone mapping | confirmed | File listing of `examples/jsm/tsl/display/` in 0.186.0 against 0.185.1; doc comments grepped; `constants.js:473,483` |
| 8 | `MeshPhysicalMaterial.retroreflectivity` is new in r186 | confirmed | 0 occurrences in 0.185.1, 7 in 0.186.0; release notes "Add support for retroreflectivity" |
| 9 | ClusteredLightsNode is probably WebGPU-only (inferred) | unverifiable | It calls `renderer.compute` and uses `attributeArray`. The WebGL backend implements `compute()` through transform feedback, so it may run there. Not executed (no browser). |
| 10 | KTX2Loader detects ASTC, ETC2, BC and PVRTC on both backends and transcodes in Workers | confirmed | `KTX2Loader.js:235–253` (`hasFeature` for WebGPU, `extensions.has` for WebGL), `WorkerPool` |
| 11 | The meshopt decoder "embeds its WASM as base64" | refuted (minor) | Custom packed text decoded by `unpack()` (`meshopt_decoder.module.js:35`); still calls `WebAssembly.instantiate`. Fixed inline. |
| 12 | BatchedMesh uses `WEBGL_multi_draw` on WebGL and one `drawIndexed` per sub-object on WebGPU | confirmed | `WebGLBackend.js:1056–1075`, `WebGLBufferRenderer.js:73`, `WebGPUBackend.js:2124–2135` |
| 13 | `reversedDepthBuffer` needs `EXT_clip_control` on WebGL and falls back with a warning; `logarithmicDepthBuffer` is available | confirmed | `WebGLBackend.js:278–284`; `Renderer.js:61,62,97` |
| 14 | `PostProcessing` was renamed `RenderPipeline` in r183 | confirmed | `renderers/common/PostProcessing.js:5,20` |
| 15 | `glslFn` / `wgslFn` are single-backend escape hatches | confirmed | `nodes/code/FunctionNode.js:177–178` |
| 16 | three.js r186 ships no UMD build; the CJS stub is 631 B; the Basis WASM is 527,333 B | confirmed | Fresh tarball: `build/` holds 6 ES modules plus `three.cjs` (631 B, re-exports the ESM); `libs/basis/basis_transcoder.wasm` is 527,333 B |
| 17 | cdnjs carries only the 10 `build/` files; its `three.webgpu.min.js` is unminified (2,284,823 B); jsDelivr's auto-minified copy is 820,842 B | confirmed | api.cdnjs.com asset list (10 files); the cdnjs file is byte-identical to `build/three.webgpu.js`; jsDelivr returns 820,842 B with a "Minified by jsDelivr using Terser" header; cdnjs `examples/jsm/...` returns 404 |
| 18 | Bundle sizes: WebGPU core 1,143,609 / 300,025 B; with add-ons 1,466,380 / 419,911 B; classic 1,113,271 / 329,513 B; app 322,134 / 120,755 B | app row confirmed; three rows unverifiable | The app bundle reproduces byte-exact. The three entry files were not saved. My reconstructions give 1.04–1.16 MB (270–304 KB gzip) for the core set and 1.31 MB (375 KB) with add-ons, the same order. Note added inline. |
| 19 | troika-three-text derives materials through `onBeforeCompile`; README line 152 (Roboto from Google Fonts) and line 320 (jsDelivr); issue #26719 | confirmed | jsDelivr README@0.52.5 lines 152 and 320; `troika-three-utils` `createDerivedMaterial` wraps `onBeforeCompile`. Issue #26719 "Custom shader support for WebGPURenderer" (closed) says "I found a problem rendering troika text in webgpu renderer." |
| 20 | In an artifact, troika's font fetches are blocked | unverifiable | The artifact contract allows font files from fonts.gstatic.com when a fonts.googleapis.com stylesheet pulls them. Whether a script `fetch` of a gstatic `.woff` passes was not tested. The report's CSP summary omitted this exception; fixed inline in section 5. |
| 21 | @takram/three-atmosphere 0.19.1 implements Bruneton scattering, with `src/webgpu/` `SkyNode`, `AerialPerspectiveNode`, `SkyEnvironmentNode`, `AtmosphereLight`, and separate WebGL/WebGPU LUTs | confirmed | Fresh tarball: `src/webgpu/` lists these files plus `AtmosphereLUTTexturesWebGL.ts` and `AtmosphereLUTTexturesWebGPU.ts`; README line 5 |
| 22 | Babylon 9.0 post (Microsoft, 26 Mar 2026): Clustered Lighting on WebGPU and WebGL 2, Volumetric Lighting, Frame Graph v1, textured area lights, splat shadows | confirmed; quote wording corrected | blogs.windows.com page fetched. The Volumetric Lighting "quote" was a paraphrase; fixed inline with the exact text. |
| 23 | Babylon 9.28 contains CascadedShadowGenerator, SSAO2, SSR, TAA, FXAA, IBL shadows, ClusteredLightContainer, GeospatialCamera, glTF basisu/meshopt/draco, and an addons atmosphere with aerial perspective | confirmed | Fresh @babylonjs/core, loaders and addons 9.28.0 tarballs, grepped. The addons package also ships `msdfText`. |
| 24 | Babylon's `WebGPUEngine.initAsync` loads glslang and twgsl WASM from cdn.babylonjs.com, which is an artifact blocker | refuted (overstated) | `initAsync` only requests the adapter and device. Loading is lazy, in `_preparePipelineContextAsync`, only for `ShaderLanguage.GLSL` (`webgpuEngine.pure.js:1635`). Materials switch to WGSL on WebGPU (`material.pure.js:763–766`). It blocks only custom GLSL shaders. Fixed inline (sections 1, 4.2 and matrix). |
| 25 | Babylon UMD `babylon.js` is 8,592,001 B (1,847,970 gzip); loaders 848,814 B; cdnjs at 8.46.2; left-handed by default | confirmed | jsDelivr babylonjs@9.28.0: 8,592,001 B (gzip -9 here 1,847,975 B; header bytes differ); `babylonjs.loaders.js` 848,814 B; api.cdnjs.com version 8.46.2; `scene.pure.js:1155` `_useRightHandedSystem = false` |
| 26 | Cesium 1.145 CHANGES (2026-09-02) has no WebGPU entries; `Cesium.js` 6,018,837 B (1,753,479 gzip); Workers 1.1, Assets 4.4, ThirdParty 1.1, Widgets 0.5 MB | confirmed | jsDelivr CHANGES.md: 0 WebGPU matches in the 1.145 section; `Cesium.js` 6,018,837 B (gzip -9 1,753,483 B); `du` of the extracted build: 1.11 / 4.38 / 1.10 / 0.52 MB |
| 27 | Google Map Tiles policies: no pre-fetch or cache; non-visualisation uses including "Offline uses" prohibited; overlay rule; attribution line; Google Maps logo | confirmed; one quote reworded | developers.google.com/maps/documentation/tile/policies (last updated 2026-09-17). The logo sentence reads "Attribution should take the form of the Google Maps logo whenever possible"; fixed inline. |
| 28 | Cesium ion Community plan: "Personal and non-commercial use", 15 GB/month streaming, 1,000 Google Photorealistic 3D Tiles root tiles a month | confirmed | cesium.com/platform/cesium-ion/pricing/ fetched |
| 29 | "CesiumJS and Google Photorealistic 3D Tiles are the only way to photoreal city context" | refuted | Contradicted by the report's own section 4.3. The 3d-tiles-renderer 0.5.3 README lists a three.js "Google Photorealistic Tiles" example. Fixed inline. |
| 30 | deck.gl 9.4 (5 Sep 2026): "WebGPU support remains experimental and is not yet recommended for production…"; `dist.min.js` 2,073,497 B (575,131 gzip) | confirmed | deck.gl/docs/whats-new; jsDelivr deck.gl@9.4.0 `dist.min.js` 2,073,497 B (gzip -9 575,137 B). The `_shadow` flag is documented on the same page; fixed inline. |
| 31 | Filament README features and backends; `triangle.filamat`; HEAD a5e4a836 (2026-09-23) | confirmed | raw README lines 88–132; `web/examples/triangle.md:47`; `git ls-remote` HEAD = a5e4a836aa0c… |
| 32 | Filament native is at v1.77.2 | refuted (minor) | The latest tag is v1.77.1. v1.77.2 exists only as `rc/1.77.2-cut` and a RELEASE_NOTES header. Fixed inline. |
| 33 | Filament's web build is stale and "gets little maintenance" | refuted | GitHub release asset `filament-v1.77.1-web.tgz` (1,943,721 B: `filament.js`, `filament.wasm`, `filament.d.ts`; tar dated 2026-09-21); `web/filament-js/package.json` at 1.77.1. Only npm lags. Fixed inline (sections 1, 4.5 and matrix). |
| 34 | WebKit, Safari 26.0 (15 Sep 2025): WebGPU "now shipping in Safari 26.0 for macOS, iOS, iPadOS, and visionOS"; "validation performed was streamlined recently to minimize overhead…" | confirmed | webkit.org/blog/17333 fetched; both sentences verbatim |
| 35 | iOS 26 runs on iPhone 11 and newer and iPhone SE (2nd gen), so WebGPU reaches those phones | confirmed (list documented; hardware link inferred) | The Apple support page lists iPhone 11 through 17e/Air and SE 2nd and 3rd gen. WebKit `Source/WebGPU/WebGPU/HardwareCapabilities.mm` (main) enables WebGPU for `MTLGPUFamilyApple4`+ (A11+), so every iOS 26 iPhone qualifies. That is main-branch source, not a statement about Safari 26.0 itself. The user's screenshots are 1290×2796 (HANDOFF §2), an iPhone class on the list (inferred). |
| 36 | "and Chrome" has WebGPU | confirmed with a caveat | On Android it depends on device. Chrome blog (WebGPU 121): "enabled by default in Chrome 121 on devices running Android 12 and greater powered by Qualcomm and ARM GPUs". Current Android coverage was not re-checked. |
| 37 | Blender licence: "What you create with Blender is your sole property…"; scripts "(if published) are being shared under a GPL compliant license" | confirmed | blender.org/about/license fetched; both verbatim |
| 38 | "If the repository is ever published…" | refuted (framing) | `/home/user/Calc/pc12/CLAUDE.md` says "The repo is public" (origin github.com/bobbychen2000/Calc); `git ls-files sfo3d` shows 198 tracked files; `tools/engine/` is untracked. Fixed inline in 7.3 and 9.6. Unauthenticated visibility was not independently confirmed. |
| 39 | bpy 5.0.1, hash a3db93c5b259 (2025-12-16); scene build, AO bake, `occlusionTexture` on all 8 materials; `asset.glb` 313,424 B; generator "Khronos glTF Blender I/O v5.0.21"; Cycles reference 0.8–1.7 s; EEVEE aborts with a libEGL error | confirmed | Re-run: `asset.glb` byte-identical to the cached one (313,424 B), 8/8 materials with occlusion, Cycles reference 1.46 s, EEVEE probe exit −6 "Couldn't open libEGL.so.1". The AO bake took **23.1 s** in my run, outside the quoted 8.7–20.5 s; timing depends on load on the shared CPU. |
| 40 | Mean AO on UV islands: apron 0.976, shaft 0.890, tunnel 0.637, tug 0.629 | confirmed | These are the means of non-zero texels in the cached `ao_*.png`. `report.json` `ao_stats` holds whole-texture means (0.971 / 0.461 / 0.394 / 0.336); the script does not compute island means. |
| 41 | Validator: 0 errors and 0 warnings on `asset.glb`; compressed file 101,060 B (0.32×), 16 warnings | confirmed | `glb_compress.mjs` re-run: 101,060 B, ETC1S q128. gltf-validator 2.0.0-dev.3.10: 0/0 and 0 errors / 16 warnings (UNSUPPORTED_EXTENSION, IMAGE_UNRECOGNIZED_FORMAT, VALUE_NOT_IN_LIST) |
| 42 | Exporter image formats AUTO, JPEG, WEBP or NONE; Draco available; a gltfpack option exists | confirmed | `bpy.ops.export_scene.gltf` RNA: enum items as listed; `export_draco_mesh_compression_enable`, `export_use_gltfpack` |
| 43 | KTX-Software release download blocked by the proxy (HTTP 403) | refuted | The v4.4.2 Linux asset downloaded (HTTP 200, 7,030,325 B, valid bzip2). Only github.com release HTML pages return 403. Fixed inline. |
| 44 | OIDN in the pip bpy is "Unverified" | resolved (available) | `_cycles.with_openimagedenoise == True`; a 64×64 render with `denoiser='OPENIMAGEDENOISE'` completed. Fixed inline. |
| 45 | Shadows: 3 D32F cascades (3072²/2048²/2048²), polygon offset (1.5, 2.0), culling off, split formula, 5-tap hash-rotated filter at 1.5 texels, normal offset 1.5 texels, per-cascade bias, only the last cascade fades, no 0/1 or 1/2 blend, aircraft shadows within 1600/1100/700 m | confirmed | `renderer.js:148–230`, `gl.js:182–186`, `common.js:105–130`, `controls.js:30`, `app.js:38–40` (`shadow`, `shadowDist`) |
| 46 | Mid-range shadow texels about 0.2–1.7 m (inferred) | confirmed (recomputed) | Using the code's own formulas (fov 50°): for orbit distance 40–150 m, cascade 1 ≈ 0.3–0.5 m and cascade 2 ≈ 1.6–1.7 m per texel; at d = 400 m, 1.3 / 4.3 m |
| 47 | MSAA only (4/4/2) on RGBA16F with `antialias:false`; ACES fitted curve; exposure 0.45, saturation 1.1, vignette 0.18 | confirmed | `gl.js:4`, `renderer.js:28–29`, `app.js:38–40,302`, `post.js:61–66` |
| 48 | GGX with Smith and Schlick; hemisphere ambient from a 64×32 sky readback; 512×256 equirect with `generateMipmap`, `lod = rough×7`; AO stand-ins at `objects.js:145` and `aircraft_real.js:88` | confirmed | `common.js:69–87`, `renderer.js:56–101`, `objects.js:145`, `aircraft_real.js:88` |
| 49 | Sign atlas is Canvas2D, bold Arial Narrow 70 px on 96 px rows, 2048 wide, mipmapped `SRGB8_ALPHA8`; "which is why the gate signs are illegible" (summary) | atlas confirmed; causal claim refuted (overstated) | `signs.js:35–51` and the `texStorage2D(SRGB8_ALPHA8)` upload. Tunnel gate panels are 0.85 m tall (`gates.js:168`), so glyphs are about 0.6 m. Pass-1 #15 asks for about 1 m characters, so size is at least as much a cause as bitmap blur. |
| 50 | The dynamic bridge mesh is rebuilt every frame while any bridge animates | confirmed | `gates.js:245–251` (`build(now, false)` while `moving`) |
| 51 | Dynamic resolution uses an "EMA of the frame time" and "every scale change" reallocates the targets; the app "targets 33 ms frames" | refuted (partly) | The EMA input is the CPU time of `tick()` (`app.js:320`), not the frame interval or GPU time. `resize()` returns early when the size is unchanged (`renderer.js:306`). Fixed inline. |
| 52 | The snapshot has 48 aircraft, 33 on the ground or slow | confirmed | `data/snapshot.js` via ESM import: 48 aircraft, 33 with `alt_baro == 'ground'` (the same 33 with gs < 50 kt or ground) |
| 53 | Terrain: 256 chunks on high, 100 on low | confirmed | Recomputed from `terrain.js:191–202`: 256 / 169 / 100 for steps 15 / 20 / 30 m |
| 54 | GPU memory per tier: render targets 358 / 224 / 81 MiB, shadows 108 / 48, airfield bake 120 / 77 / 49, aux 19, city 171 / 171 / 43, region 21 | confirmed (recomputed) | 117.3 B per pixel at 4× and 77.3 B at 2× (MSAA pair, 3 resolve targets, final, overlay, bloom chain); bakes are RGBA8 × 4/3 for mips (`world.js:68–96`, `airfield.js:5`, `terrain.js:4`). Terrain buffers not checked. The low tier's 1.1 MPx is the `maxPx` cap; a 390×844 pt phone at scale 0.8 renders about 0.84 MPx (inferred). |
| 55 | Aircraft models: 21 types, 495,245 triangles, about 340 MiB of RGBA8 mip textures; 1–14 textures; b744 28, a333 26 (14 textures), a388 24 MiB | confirmed | Parsed all `.sfom` files: 339.9 MiB, b744 28.0, a333 26.0, a388 24.3 |
| 56 | "11.9 MB on disk" | refuted (minor) | 12,077,852 B = 12.1 MB / 11.5 MiB. Fixed inline. |
| 57 | Draw groups per airframe "1–14, mean about 3.9" | refuted | 2–15 groups, mean 5.05 (every model has an untextured group); textures mean 4.05. Fixed inline; the 500–1,200 total stays in the same order. |
| 58 | KTX2 → ASTC 4×4 about 85 MiB; ETC1S → ETC2 RGB about 43 MiB | confirmed (arithmetic) | 340 MiB × 8/32 and × 4/32. Textures with alpha transcode to ETC2 RGBA at 8 bpp, so 43 MiB is a lower bound (inferred). |
| 59 | TRAA "would cut the high-tier render-target cost by about two thirds" | refuted | 358 → about 200 MiB is about 45%; two thirds applies only to the MSAA portion. Fixed inline. |
| 60 | "About half" of the pass-1 top 15 have engine-level causes | refuted (overstated) | Mainly engine: #4 and #11; partly engine: #1, #5, #10, #15. #9 (overview) is data, #3 (blank aprons) is missing from the mapping. Fixed inline. |
| 61 | About 250 KB of `js/live` ports as-is; about 80 KB of GLSL is rewritten | 80 KB confirmed; 250 KB overstated | `js/shaders` is 76,822 B plus about 2.8 KB GLSL in `signs.js`/`markings.js`. `js/live` is 246,745 B but includes renderer-coupled files; the pure-logic modules are 101,267 B. Note added inline. |
| 62 | Artifact contract: script CDN allowlist; "Everything else is blocked … even on those CDNs, anything but a script…"; Workers from own files or `blob:`; relative `fetch()`; 16 MB page, 16/15 MB file limits, 255 files, 64 MB per version | confirmed | Artifact tool description and the artifact-design skill, read in this session. The Google Fonts stylesheet and font exception was omitted; fixed inline. |
| 63 | `WebAssembly.instantiate` and ES-module imports from jsDelivr pass the artifact CSP | unverifiable | Neither the contract nor the skill says; no artifact was published for a probe (phase 0 as proposed). |
| 64 | Every mobile frame-rate, draw-call and memory-limit statement | unverifiable | No GPU here, and browsers were not allowed. This agrees with the report's own label. |
| 65 | Recommendation: three.js r186 `WebGPURenderer`, pinned, with Blender as the asset and QA tool | stands, with a caveat | None of the refutations rests the choice on false facts. They weaken two of the "alternatives fit worse" arguments (Babylon's CDN blocker is conditional; Filament's web build is current), so the matrix rows for Babylon (artifact fit) and Filament (risk) should be re-scored. Phase 4 "soft PCF" must use `PCFShadowMap` with a filter radius, since PCFSoft is gone in r186. |
