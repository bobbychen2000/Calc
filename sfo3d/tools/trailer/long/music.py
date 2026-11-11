# quiet generative bed (self-made, no third-party audio): A - F#m - D - E pads, sub bass, soft plucked arpeggio, simple reverb
import numpy as np, wave, sys
sr = 44100; dur = float(sys.argv[2]); n = int(sr * dur); t = np.arange(n) / sr
mtof = lambda m: 440.0 * 2 ** ((m - 69) / 12)
prog = [[57, 61, 64, 69, 76], [54, 57, 61, 66, 73], [50, 54, 57, 62, 69], [52, 56, 59, 64, 71]]
seg = 8.0; out = np.zeros(n)
for k in range(int(dur / seg) + 2):
    c = prog[k % 4]; a = int(max(0, (k * seg - 2.5)) * sr); b = int(min(dur, k * seg + seg + 2.5) * sr)
    if a >= b: continue
    tt = t[a:b] - k * seg; env = np.clip((tt + 2.5) / 3.0, 0, 1) * np.clip((seg + 2.5 - tt) / 3.0, 0, 1)
    s = np.zeros(b - a)
    for j, m in enumerate(c[:4]):
        f = mtof(m); s += (0.5 * np.sin(2 * np.pi * f * tt + j) + 0.22 * np.sin(2 * np.pi * f * 1.004 * tt + 2 * j) + 0.08 * np.sin(2 * np.pi * 2 * f * tt)) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.1 * tt + j))
    s += 0.9 * np.sin(2 * np.pi * mtof(c[0] - 12) * tt)
    out[a:b] += 0.06 * s * env
    for i in range(int(seg * 2)):                                   # arpeggio: 2 notes / s, 5-note pattern
        st = k * seg + i * 0.5; i0 = int(st * sr)
        if i0 >= n: break
        L = min(int(1.6 * sr), n - i0); tp = np.arange(L) / sr; f = mtof(c[[0, 2, 4, 3, 1][i % 5]] + 12)
        out[i0:i0 + L] += 0.035 * np.sin(2 * np.pi * f * tp) * np.exp(-tp * 2.6) * (1 - np.exp(-tp * 60))
for d, g in ((0.113, 0.32), (0.229, 0.22), (0.371, 0.15), (0.59, 0.1)):   # cheap reverb
    k = int(d * sr); out[k:] += g * out[:-k]
out *= np.clip(t / 4, 0, 1) * np.clip((dur - t) / 6, 0, 1)
out = out / np.max(np.abs(out)) * 0.5
st = np.stack([out, np.roll(out, int(0.012 * sr))], 1)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes((st * 32767).astype(np.int16).tobytes())
print('music', dur)
