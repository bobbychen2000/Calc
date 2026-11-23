"""Baseline: the current pipeline (Kokoro-82M-v1.1-zh, zf_003, one chunk at a time with fixed pauses)."""
import json, os, sys, time
import numpy as np, soundfile as sf
sys.path.insert(0, "/home/user/Calc/rh")
import voice_zh as V
HACK = [("一千七百万行", "一千七百万航"), ("摊得", "摊的"), ("Levent", "Le-vent")]
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "kokoro_zf003")
os.makedirs(out, exist_ok=True)
T = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "testset.json")))
tot_a = tot_t = 0
for k, text in T.items():
    for a, b in HACK:
        text = text.replace(a, b)
    t0 = time.time()
    chs = V.parse(text)
    pieces = []
    for i, c in enumerate(chs):
        if not c["spoken"]:
            continue
        pieces.append(V.synth(c["spoken"]))
        if i < len(chs) - 1:
            pieces.append(np.zeros(int(V.PAUSE[c["end"]] * V.SR), np.float32))
    wav = np.concatenate(pieces)
    sf.write(os.path.join(out, f"{k}.wav"), wav, V.SR)
    dt = time.time() - t0
    tot_a += len(wav) / V.SR; tot_t += dt
    print(k, round(len(wav) / V.SR, 1), "s audio", round(dt, 1), "s")
json.dump({"rtf": round(tot_t / tot_a, 3), "audio_s": round(tot_a, 1)}, open(os.path.join(out, "rtf.json"), "w"))
print("RTF", tot_t / tot_a)
