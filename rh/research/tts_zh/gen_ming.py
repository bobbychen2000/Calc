"""Ming-3.0-tts-0.5B on CPU, built-in voice (task IP).
usage: venv-ming/bin/python gen_ming.py VOICE [items...] [--tag TAG]"""
import json, os, sys, time, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src", "ming"))
os.chdir(os.path.join(HERE, "src", "ming"))
import numpy as np, soundfile as sf, torch
torch.set_num_threads(int(os.environ.get("THREADS", "4")))
from ming_tts import MingTTS
args = sys.argv[1:]
tag = None
if "--tag" in args:
    i = args.index("--tag"); tag = args[i + 1]; del args[i:i + 2]
voice, items = args[0], args[1:]
T = json.load(open(os.path.join(HERE, "testset.json")))
name = tag or f"ming_{voice}"
out = os.path.join(HERE, "out", name); os.makedirs(out, exist_ok=True)
t0 = time.time()
tts = MingTTS(os.path.join(HERE, "models", "Ming-3.0-tts-0.5B"), device="cpu", text_normalization=False)
print("load", round(time.time() - t0, 1), flush=True)
statp = os.path.join(out, "rtf.json")
stats = json.load(open(statp)) if os.path.exists(statp) else {}
for k in (items or list(T)):
    t0 = time.time()
    with torch.autocast("cpu", dtype=torch.bfloat16):
        w = tts.synthesize(task="IP", text=T[k], controls={"ip": voice}, use_zero_spk_emb=True)
    w = w.float().cpu().numpy().reshape(-1)
    dt = time.time() - t0
    sr = tts.sample_rate
    sf.write(os.path.join(out, f"{k}.wav"), w, sr)
    stats[k] = {"audio_s": round(len(w) / sr, 2), "synth_s": round(dt, 1), "rtf": round(dt / (len(w) / sr), 2)}
    print(k, stats[k], flush=True)
    json.dump(stats, open(statp, "w"), indent=1)
