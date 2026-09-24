// ------------------------------------------------------------------
// Tiny WebGL2 engine: programs, meshes with instancing, textures
// ------------------------------------------------------------------
const ATTR = { pos: 0, nrm: 1, uv: 2, col: 3, mat: 4, i0: 5, i1: 6, i2: 7, i3: 8, tint: 9 };

class GL {
  constructor(canvas, opts = {}) {
    const gl = canvas.getContext('webgl2', {
      antialias: opts.antialias !== false, alpha: false, depth: true, stencil: false,
      powerPreference: 'high-performance', preserveDrawingBuffer: !!opts.preserve,
    });
    if (!gl) throw new Error('WebGL2 unavailable');
    this.gl = gl;
    this.canvas = canvas;
    this.maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE);
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);
    gl.frontFace(gl.CCW);
    this.stats = { calls: 0, tris: 0 };
  }

  program(vs, fs, defines = {}) {
    const gl = this.gl;
    const head = '#version 300 es\n' + Object.entries(defines).map(([k, v]) => `#define ${k} ${v}\n`).join('');
    const mk = (type, src) => {
      const s = gl.createShader(type);
      gl.shaderSource(s, head + src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        const log = gl.getShaderInfoLog(s);
        const lines = (head + src).split('\n').map((l, i) => (i + 1) + ': ' + l).join('\n');
        console.error(log + '\n' + lines);
        throw new Error('Shader compile failed: ' + log);
      }
      return s;
    };
    const p = gl.createProgram();
    gl.attachShader(p, mk(gl.VERTEX_SHADER, vs));
    gl.attachShader(p, mk(gl.FRAGMENT_SHADER, fs));
    for (const [n, loc] of Object.entries(ATTR)) gl.bindAttribLocation(p, loc, 'a_' + n);
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('Link failed: ' + gl.getProgramInfoLog(p));
    const uni = {};
    const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) {
      const info = gl.getActiveUniform(p, i);
      const name = info.name.replace(/\[0\]$/, '');
      uni[name] = { loc: gl.getUniformLocation(p, info.name), type: info.type, size: info.size };
    }
    return { p, uni, units: {} };
  }

  use(prog) { this.gl.useProgram(prog.p); this.cur = prog; }

  // set uniform by name, inferring from type
  set(name, v) {
    const u = this.cur.uni[name];
    if (!u) return;
    const gl = this.gl, l = u.loc;
    switch (u.type) {
      case gl.FLOAT: u.size > 1 ? gl.uniform1fv(l, v) : gl.uniform1f(l, v); break;
      case gl.FLOAT_VEC2: gl.uniform2fv(l, v); break;
      case gl.FLOAT_VEC3: gl.uniform3fv(l, v); break;
      case gl.FLOAT_VEC4: gl.uniform4fv(l, v); break;
      case gl.FLOAT_MAT4: gl.uniformMatrix4fv(l, false, v); break;
      case gl.INT: case gl.BOOL: gl.uniform1i(l, v); break;
      default: gl.uniform1i(l, v);
    }
  }
  tex(name, unit, texture, target) {
    const gl = this.gl, u = this.cur.uni[name];
    if (!u) return;
    gl.activeTexture(gl.TEXTURE0 + unit);
    gl.bindTexture(target || gl.TEXTURE_2D, texture);
    gl.uniform1i(u.loc, unit);
  }

  // geo: {pos, nrm, uv, col(u8x4), mat(u8x4), idx}
  mesh(geo, opts = {}) {
    const gl = this.gl;
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const nv = geo.pos.length / 3;
    const fbuf = new Float32Array(nv * 8);
    for (let i = 0; i < nv; i++) {
      fbuf[i * 8] = geo.pos[i * 3]; fbuf[i * 8 + 1] = geo.pos[i * 3 + 1]; fbuf[i * 8 + 2] = geo.pos[i * 3 + 2];
      fbuf[i * 8 + 3] = geo.nrm[i * 3]; fbuf[i * 8 + 4] = geo.nrm[i * 3 + 1]; fbuf[i * 8 + 5] = geo.nrm[i * 3 + 2];
      fbuf[i * 8 + 6] = geo.uv ? geo.uv[i * 2] : 0; fbuf[i * 8 + 7] = geo.uv ? geo.uv[i * 2 + 1] : 0;
    }
    const vb = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vb);
    gl.bufferData(gl.ARRAY_BUFFER, fbuf, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(ATTR.pos); gl.vertexAttribPointer(ATTR.pos, 3, gl.FLOAT, false, 32, 0);
    gl.enableVertexAttribArray(ATTR.nrm); gl.vertexAttribPointer(ATTR.nrm, 3, gl.FLOAT, false, 32, 12);
    gl.enableVertexAttribArray(ATTR.uv); gl.vertexAttribPointer(ATTR.uv, 2, gl.FLOAT, false, 32, 24);
    const bbuf = new Uint8Array(nv * 8);
    for (let i = 0; i < nv; i++) {
      for (let k = 0; k < 4; k++) {
        bbuf[i * 8 + k] = geo.col ? geo.col[i * 4 + k] : 255;
        bbuf[i * 8 + 4 + k] = geo.mat ? geo.mat[i * 4 + k] : (k === 0 ? 200 : 0);
      }
    }
    const cb = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, cb);
    gl.bufferData(gl.ARRAY_BUFFER, bbuf, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(ATTR.col); gl.vertexAttribPointer(ATTR.col, 4, gl.UNSIGNED_BYTE, true, 8, 0);
    gl.enableVertexAttribArray(ATTR.mat); gl.vertexAttribPointer(ATTR.mat, 4, gl.UNSIGNED_BYTE, true, 8, 4);
    // instance buffer: mat4 + tint
    const ib = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, ib);
    for (let c = 0; c < 4; c++) {
      gl.enableVertexAttribArray(ATTR.i0 + c);
      gl.vertexAttribPointer(ATTR.i0 + c, 4, gl.FLOAT, false, 80, c * 16);
      gl.vertexAttribDivisor(ATTR.i0 + c, 1);
    }
    gl.enableVertexAttribArray(ATTR.tint);
    gl.vertexAttribPointer(ATTR.tint, 4, gl.FLOAT, false, 80, 64);
    gl.vertexAttribDivisor(ATTR.tint, 1);
    const idx = geo.idx;
    const big = nv > 65535;
    const ebo = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ebo);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, big ? new Uint32Array(idx) : new Uint16Array(idx), gl.STATIC_DRAW);
    gl.bindVertexArray(null);
    const m = {
      vao, ib, count: idx.length, type: big ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT, instances: 0,
      tris: idx.length / 3, name: opts.name || '', layer: opts.layer || 'main', visible: true,
      castShadow: opts.castShadow !== false, doubleSided: !!opts.doubleSided, idata: null,
      bounds: geo.bounds || null,
    };
    this.setInstances(m, opts.instances || [M4.ident()], opts.tints);
    return m;
  }

  // mats: array of Float32Array(16); tints: array of [r,g,b,a]
  setInstances(m, mats, tints) {
    const gl = this.gl;
    const n = mats.length;
    const d = new Float32Array(n * 20);
    for (let i = 0; i < n; i++) {
      d.set(mats[i], i * 20);
      const t = tints && tints[i] ? tints[i] : [1, 1, 1, 0];
      d[i * 20 + 16] = t[0]; d[i * 20 + 17] = t[1]; d[i * 20 + 18] = t[2]; d[i * 20 + 19] = t[3];
    }
    m.idata = d;
    m.instances = n;
    gl.bindBuffer(gl.ARRAY_BUFFER, m.ib);
    gl.bufferData(gl.ARRAY_BUFFER, d, gl.DYNAMIC_DRAW);
  }
  // upload a raw instance buffer (n instances of 20 floats)
  setInstancesRaw(m, data, n) {
    const gl = this.gl;
    m.idata = data;
    m.instances = n;
    gl.bindBuffer(gl.ARRAY_BUFFER, m.ib);
    gl.bufferData(gl.ARRAY_BUFFER, data.subarray(0, Math.max(1, n) * 20), gl.DYNAMIC_DRAW);
  }
  // update tint of one instance
  setTint(m, i, t) {
    const gl = this.gl;
    m.idata[i * 20 + 16] = t[0]; m.idata[i * 20 + 17] = t[1]; m.idata[i * 20 + 18] = t[2]; m.idata[i * 20 + 19] = t[3];
    gl.bindBuffer(gl.ARRAY_BUFFER, m.ib);
    gl.bufferSubData(gl.ARRAY_BUFFER, (i * 20 + 16) * 4, m.idata, i * 20 + 16, 4);
  }
  setMatrix(m, i, mat) {
    const gl = this.gl;
    m.idata.set(mat, i * 20);
    gl.bindBuffer(gl.ARRAY_BUFFER, m.ib);
    gl.bufferSubData(gl.ARRAY_BUFFER, i * 20 * 4, m.idata, i * 20, 16);
  }

  draw(m) {
    if (!m.visible || m.instances === 0) return;
    const gl = this.gl;
    gl.bindVertexArray(m.vao);
    gl.drawElementsInstanced(gl.TRIANGLES, m.count, m.type, 0, m.instances);
    this.stats.calls++;
    this.stats.tris += m.tris * m.instances;
  }

  texture2D(src, opts = {}) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    if (src instanceof HTMLCanvasElement || (typeof ImageBitmap !== 'undefined' && src instanceof ImageBitmap)) {
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, !!opts.flipY);
      gl.texImage2D(gl.TEXTURE_2D, 0, opts.srgb ? gl.SRGB8_ALPHA8 : gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, src);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    } else {
      gl.texImage2D(gl.TEXTURE_2D, 0, opts.internal || gl.RGBA8, opts.w, opts.h, 0, opts.format || gl.RGBA, opts.type || gl.UNSIGNED_BYTE, src);
    }
    const mip = opts.mip !== false;
    if (mip) gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, opts.nearest ? gl.NEAREST : mip ? gl.LINEAR_MIPMAP_LINEAR : gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, opts.nearest ? gl.NEAREST : gl.LINEAR);
    const wrap = opts.clamp ? gl.CLAMP_TO_EDGE : gl.REPEAT;
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap);
    const af = gl.getExtension('EXT_texture_filter_anisotropic');
    if (af && mip) gl.texParameterf(gl.TEXTURE_2D, af.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(8, gl.getParameter(af.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));
    return t;
  }

  textureArray(layers, size) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, t);
    gl.texImage3D(gl.TEXTURE_2D_ARRAY, 0, gl.RGBA8, size, size, layers.length, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    layers.forEach((data, i) => gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, i, size, size, 1, gl.RGBA, gl.UNSIGNED_BYTE, data));
    gl.generateMipmap(gl.TEXTURE_2D_ARRAY);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_T, gl.REPEAT);
    const af = gl.getExtension('EXT_texture_filter_anisotropic');
    if (af) gl.texParameterf(gl.TEXTURE_2D_ARRAY, af.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(8, gl.getParameter(af.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));
    return t;
  }

  texture3D(data, nx, ny, nz) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_3D, t);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texImage3D(gl.TEXTURE_3D, 0, gl.R8, nx, ny, nz, 0, gl.RED, gl.UNSIGNED_BYTE, data);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 4);
    gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_3D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    for (const w of [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T, gl.TEXTURE_WRAP_R]) gl.texParameteri(gl.TEXTURE_3D, w, gl.CLAMP_TO_EDGE);
    return t;
  }

  shadowTarget(w, h) {
    const gl = this.gl;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.DEPTH_COMPONENT24, w, h);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_MODE, gl.COMPARE_REF_TO_TEXTURE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_FUNC, gl.LEQUAL);
    const fb = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, t, 0);
    gl.drawBuffers([gl.NONE]);
    gl.readBuffer(gl.NONE);
    const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return { tex: t, fb, w, h, ok };
  }
}
