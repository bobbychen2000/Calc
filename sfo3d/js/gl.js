// WebGL2 helpers
export let gl;
export function initGL(canvas) {
  gl = canvas.getContext('webgl2', { antialias: false, depth: false, alpha: false, preserveDrawingBuffer: false, powerPreference: 'high-performance' });
  if (!gl) throw new Error('no webgl2');
  if (!gl.getExtension('EXT_color_buffer_float')) gl.getExtension('EXT_color_buffer_half_float');
  gl.getExtension('OES_texture_float_linear');
  gl.getExtension('EXT_texture_filter_anisotropic');
  return gl;
}

const chunks = {};
// Texture units: samplers bound once per frame (shared by every program) get fixed low units; all other samplers are
// allocated per program above them and rebound with each draw's uniforms. Keeps every program within 16 units (iOS limit).
const FRAME_SAMPLERS = ['uShadow0', 'uShadow1', 'uShadow2', 'uSkyTex', 'uNoise', 'uCloudTex'];
function unitFor(name, prog) {
  const f = FRAME_SAMPLERS.indexOf(name); if (f >= 0) return f;
  if (!prog._units) prog._units = {}; if (name in prog._units) return prog._units[name];
  const u = FRAME_SAMPLERS.length + Object.keys(prog._units).length; if (u > 15) throw new Error('too many samplers in one program');
  prog._units[name] = u; return u;
}
export function defineChunk(name, src) { chunks[name] = src; }
function preprocess(src, defines) {
  const seen = new Set();
  for (let pass = 0; pass < 6 && /#include </.test(src); pass++)
    src = src.replace(/#include <(\w+)>/g, (m, n) => { if (!(n in chunks)) throw new Error('missing chunk ' + n); if (seen.has(n)) return ''; seen.add(n); return chunks[n]; });
  let head = '#version 300 es\nprecision highp float;\nprecision highp int;\nprecision highp sampler2D;\nprecision highp sampler2DShadow;\nprecision highp sampler2DArray;\n';
  for (const k in (defines || {})) head += `#define ${k} ${defines[k]}\n`;
  return head + src;
}
function compile(type, src) {
  const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(s);
    const lines = src.split('\n').map((l, i) => (i + 1) + ': ' + l);
    const m = /0:(\d+)/.exec(log); let ctx = '';
    if (m) { const ln = +m[1]; ctx = lines.slice(Math.max(0, ln - 4), ln + 2).join('\n'); }
    throw new Error('Shader compile error: ' + log + '\n' + ctx);
  }
  return s;
}
export class Program {
  constructor(vs, fs, defines) {
    this.p = gl.createProgram();
    gl.attachShader(this.p, compile(gl.VERTEX_SHADER, preprocess(vs, defines)));
    gl.attachShader(this.p, compile(gl.FRAGMENT_SHADER, preprocess(fs, defines)));
    // fixed attribute locations
    ['aPos', 'aNrm', 'aUV', 'aCol', 'aExtra', 'iM0', 'iM1', 'iM2', 'iData'].forEach((n, i) => gl.bindAttribLocation(this.p, i, n));
    gl.linkProgram(this.p);
    if (!gl.getProgramParameter(this.p, gl.LINK_STATUS)) throw new Error('link: ' + gl.getProgramInfoLog(this.p));
    this.u = {}; this.texUnit = {};
    const n = gl.getProgramParameter(this.p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < n; i++) {
      const info = gl.getActiveUniform(this.p, i); const name = info.name.replace(/\[0\]$/, '');
      this.u[name] = { loc: gl.getUniformLocation(this.p, info.name), type: info.type, size: info.size };
      if ([gl.SAMPLER_2D, gl.SAMPLER_2D_SHADOW, gl.SAMPLER_2D_ARRAY, gl.SAMPLER_CUBE, gl.SAMPLER_3D].includes(info.type)) {
        this.texUnit[name] = unitFor(name, this);
      }
    }
    gl.useProgram(this.p);
    for (const k in this.texUnit) gl.uniform1i(this.u[k].loc, this.texUnit[k]);
  }
  use() { gl.useProgram(this.p); return this; }
  set(name, v) {
    const u = this.u[name]; if (!u) return this;
    const l = u.loc;
    switch (u.type) {
      case gl.FLOAT: if (u.size > 1) gl.uniform1fv(l, v); else gl.uniform1f(l, v); break;
      case gl.FLOAT_VEC2: gl.uniform2fv(l, v); break;
      case gl.FLOAT_VEC3: gl.uniform3fv(l, v); break;
      case gl.FLOAT_VEC4: gl.uniform4fv(l, v); break;
      case gl.INT: case gl.BOOL: gl.uniform1i(l, v); break;
      case gl.FLOAT_MAT4: gl.uniformMatrix4fv(l, false, v); break;
      case gl.FLOAT_MAT3: gl.uniformMatrix3fv(l, false, v); break;
      default:
        if (u.type === gl.SAMPLER_2D || u.type === gl.SAMPLER_2D_SHADOW || u.type === gl.SAMPLER_2D_ARRAY || u.type === gl.SAMPLER_3D) {
          const unit = this.texUnit[name]; gl.activeTexture(gl.TEXTURE0 + unit);
          const target = u.type === gl.SAMPLER_2D_ARRAY ? gl.TEXTURE_2D_ARRAY : u.type === gl.SAMPLER_3D ? gl.TEXTURE_3D : gl.TEXTURE_2D;
          gl.bindTexture(target, v && v.tex ? v.tex : v);
        }
    }
    return this;
  }
  setAll(obj) { for (const k in obj) this.set(k, obj[k]); return this; }
}

// Mesh: attributes pos(3) nrm(3) uv(2) col(4) extra(4)
export class Mesh {
  constructor(data) {
    this.vao = gl.createVertexArray(); gl.bindVertexArray(this.vao); this.bufs = [];
    const attr = (loc, arr, size) => {
      if (!arr) { gl.disableVertexAttribArray(loc); return; }
      const b = gl.createBuffer(); this.bufs.push(b); gl.bindBuffer(gl.ARRAY_BUFFER, b);
      gl.bufferData(gl.ARRAY_BUFFER, arr instanceof Float32Array ? arr : new Float32Array(arr), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
    };
    attr(0, data.pos, 3); attr(1, data.nrm, 3); attr(2, data.uv, 2); attr(3, data.col, 4); attr(4, data.extra, 4);
    if (!data.nrm) gl.vertexAttrib3f(1, 0, 1, 0);
    if (!data.col) gl.vertexAttrib4f(3, 1, 1, 1, 1);
    if (!data.extra) gl.vertexAttrib4f(4, 0, 0, 0, 0);
    this.count = data.idx ? data.idx.length : data.pos.length / 3;
    if (data.idx) {
      const ib = gl.createBuffer(); this.bufs.push(ib); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib);
      const arr = data.idx instanceof Uint32Array ? data.idx : new Uint32Array(data.idx);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, arr, gl.STATIC_DRAW); this.indexed = true;
    }
    this.instanced = false; this.mode = data.mode || gl.TRIANGLES;
    this.bbox = data.bbox || null;
    gl.bindVertexArray(null);
  }
  // instance data: array of Float32 per-instance 16 floats: 3 rows of mat (12) + data(4)
  setInstances(f32, n) {
    gl.bindVertexArray(this.vao);
    if (!this.ibuf) this.ibuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, this.ibuf); gl.bufferData(gl.ARRAY_BUFFER, f32, gl.DYNAMIC_DRAW);
    for (let i = 0; i < 4; i++) {
      gl.enableVertexAttribArray(5 + i); gl.vertexAttribPointer(5 + i, 4, gl.FLOAT, false, 64, i * 16); gl.vertexAttribDivisor(5 + i, 1);
    }
    this.instanced = true; this.nInst = n; gl.bindVertexArray(null);
  }
  dispose() { for (const b of this.bufs || []) gl.deleteBuffer(b); if (this.ibuf) gl.deleteBuffer(this.ibuf); gl.deleteVertexArray(this.vao); this.bufs = []; }
  drawRange(first, count) {
    gl.bindVertexArray(this.vao);
    gl.drawElements(this.mode, count, gl.UNSIGNED_INT, first * 4);
  }
  draw() {
    gl.bindVertexArray(this.vao);
    if (this.instanced) {
      if (this.nInst <= 0) return;
      if (this.indexed) gl.drawElementsInstanced(this.mode, this.count, gl.UNSIGNED_INT, 0, this.nInst);
      else gl.drawArraysInstanced(this.mode, 0, this.count, this.nInst);
    } else {
      if (this.indexed) gl.drawElements(this.mode, this.count, gl.UNSIGNED_INT, 0);
      else gl.drawArrays(this.mode, 0, this.count);
    }
  }
}

export function texture(w, h, opts = {}) {
  const t = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, t);
  const ifmt = opts.internal || gl.RGBA8, fmt = opts.format || gl.RGBA, type = opts.type || gl.UNSIGNED_BYTE;
  const levels = opts.mips ? Math.floor(Math.log2(Math.max(w, h))) + 1 : 1;
  gl.texStorage2D(gl.TEXTURE_2D, levels, ifmt, w, h);
  if (opts.data) gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, w, h, fmt, type, opts.data);
  if (opts.source) gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, fmt, type, opts.source);
  const filt = opts.nearest ? gl.NEAREST : gl.LINEAR;
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, opts.mips ? gl.LINEAR_MIPMAP_LINEAR : filt);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filt);
  const wrap = opts.repeat ? gl.REPEAT : gl.CLAMP_TO_EDGE;
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap);
  if (opts.mips && (opts.data || opts.source)) gl.generateMipmap(gl.TEXTURE_2D);
  if (opts.aniso && window.ANISO > 1) { const e = gl.getExtension('EXT_texture_filter_anisotropic'); if (e) gl.texParameterf(gl.TEXTURE_2D, e.TEXTURE_MAX_ANISOTROPY_EXT, (window.ANISO||1)); }
  if (opts.compare) {
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_MODE, gl.COMPARE_REF_TO_TEXTURE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_FUNC, gl.LEQUAL);
  }
  return { tex: t, w, h };
}

export class FBO {
  // colors: array of {internal, format, type}, depth: 'tex' | 'rb' | null, msaa samples
  constructor(w, h, colors, depth, samples = 0) {
    this.w = w; this.h = h; this.fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, this.fb);
    this.tex = []; this.samples = samples;
    const bufs = [];
    colors.forEach((c, i) => {
      if (samples > 0) {
        const rb = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, rb);
        gl.renderbufferStorageMultisample(gl.RENDERBUFFER, samples, c.internal, w, h);
        gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0 + i, gl.RENDERBUFFER, rb);
        this.tex.push(rb);
      } else {
        const t = texture(w, h, c); gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0 + i, gl.TEXTURE_2D, t.tex, 0);
        this.tex.push(t);
      }
      bufs.push(gl.COLOR_ATTACHMENT0 + i);
    });
    if (colors.length) gl.drawBuffers(bufs); else { gl.drawBuffers([gl.NONE]); gl.readBuffer(gl.NONE); }
    if (depth) {
      if (samples > 0 || depth === 'rb') {
        const rb = gl.createRenderbuffer(); gl.bindRenderbuffer(gl.RENDERBUFFER, rb);
        if (samples > 0) gl.renderbufferStorageMultisample(gl.RENDERBUFFER, samples, gl.DEPTH_COMPONENT32F, w, h);
        else gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT32F, w, h);
        gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, rb); this.depthRB = rb;
      } else {
        const t = texture(w, h, { internal: gl.DEPTH_COMPONENT32F, format: gl.DEPTH_COMPONENT, type: gl.FLOAT, nearest: depth !== 'shadow', compare: depth === 'shadow' });
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, t.tex, 0); this.depth = t;
      }
    }
    const st = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
    if (st !== gl.FRAMEBUFFER_COMPLETE) throw new Error('FBO incomplete ' + st.toString(16));
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }
  bind() { gl.bindFramebuffer(gl.FRAMEBUFFER, this.fb); gl.viewport(0, 0, this.w, this.h); }
  dispose() {
    for (const t of this.tex) { if (t && t.tex) gl.deleteTexture(t.tex); else if (t) gl.deleteRenderbuffer(t); }
    if (this.depthRB) gl.deleteRenderbuffer(this.depthRB); if (this.depth) gl.deleteTexture(this.depth.tex);
    gl.deleteFramebuffer(this.fb);
  }
}

let fsTri = null;
export function fullscreen() {
  if (!fsTri) {
    fsTri = gl.createVertexArray(); gl.bindVertexArray(fsTri);
    const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 0, 3, -1, 0, -1, 3, 0]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
  }
  gl.bindVertexArray(fsTri); gl.drawArrays(gl.TRIANGLES, 0, 3);
}
