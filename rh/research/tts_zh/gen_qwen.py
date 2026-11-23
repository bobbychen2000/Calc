"""Qwen3-TTS CustomVoice on CPU: synthesise the test set.
usage: venv-qwen/bin/python gen_qwen.py MODEL_DIR SPEAKER [items...] [--instruct TEXT] [--tag TAG]"""
import json, os, sys, time, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, torch
torch.set_num_threads(int(os.environ.get("THREADS", "4")))
from qwen_tts import Qwen3TTSModel
args = sys.argv[1:]
instruct = None; tag = None
if "--instruct" in args:
    i = args.index("--instruct"); instruct = args[i + 1]; del args[i:i + 2]
if "--tag" in args:
    i = args.index("--tag"); tag = args[i + 1]; del args[i:i + 2]
mdir, spk, items = args[0], args[1], args[2:]
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "testset.json")))
name = tag or f"qwen{'17' if '1.7B' in mdir else '06'}_{spk.lower()}"
out = os.path.join(HERE, "out", name); os.makedirs(out, exist_ok=True)
t0 = time.time()
DT = torch.bfloat16 if os.environ.get("BF16") else torch.float32
model = Qwen3TTSModel.from_pretrained(mdir, device_map="cpu", dtype=DT)
print("load", round(time.time() - t0, 1), "s", flush=True)
stats = json.load(open(os.path.join(out, "rtf.json"))) if os.path.exists(os.path.join(out, "rtf.json")) else {}
for k in (items or list(T)):
    t0 = time.time()
    torch.manual_seed(int(os.environ.get("SEED", "1")))
    kw = dict(text=T[k], language="Chinese", speaker=spk, max_new_tokens=int(len(T[k]) / 3.0 * 12.5 * 1.7) + 60)
    if instruct:
        kw["instruct"] = instruct
    wavs, sr = model.generate_custom_voice(**kw)
    dt = time.time() - t0
    w = np.asarray(wavs[0], dtype=np.float32)
    sf.write(os.path.join(out, f"{k}.wav"), w, sr)
    stats[k] = {"audio_s": round(len(w) / sr, 2), "synth_s": round(dt, 1), "rtf": round(dt / (len(w) / sr), 2)}
    print(k, stats[k], flush=True)
    json.dump(stats, open(os.path.join(out, "rtf.json"), "w"), indent=1)
