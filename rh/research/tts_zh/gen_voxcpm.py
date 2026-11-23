"""VoxCPM2 on CPU. Voice design from a text description (in parentheses before the text); with
--ref WAV --ref-text TEXT the designed take is reused as the reference (continuation mode).
usage: venv-voxcpm/bin/python gen_voxcpm.py TAG [items...] [--design DESC] [--ref WAV --ref-text TEXT] [--steps N]"""
import json, os, sys, time, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, torch
torch.set_num_threads(int(os.environ.get("THREADS", "4")))
from voxcpm import VoxCPM
args = sys.argv[1:]
def opt(name, default=None):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return default
design, ref, ref_text, steps = opt("--design"), opt("--ref"), opt("--ref-text"), int(opt("--steps", "10"))
tag, items = args[0], args[1:]
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "testset.json")))
out = os.path.join(HERE, "out", tag); os.makedirs(out, exist_ok=True)
t0 = time.time()
m = VoxCPM.from_pretrained(os.path.join(HERE, "models", "VoxCPM2"), load_denoiser=False, optimize=False, device="cpu")
print("load", round(time.time() - t0, 1), flush=True)
statp = os.path.join(out, "rtf.json")
stats = json.load(open(statp)) if os.path.exists(statp) else {}
for k in (items or list(T)):
    torch.manual_seed(int(os.environ.get("SEED", "1")))
    t0 = time.time()
    text = T[k] if not design else f"({design}){T[k]}"
    kw = dict(text=text, inference_timesteps=steps, cfg_value=2.0)
    if ref:
        kw.update(prompt_wav_path=ref, prompt_text=ref_text)
    w = np.asarray(m.generate(**kw), dtype=np.float32).reshape(-1)
    sr = m.tts_model.sample_rate
    dt = time.time() - t0
    sf.write(os.path.join(out, f"{k}.wav"), w, sr)
    stats[k] = {"audio_s": round(len(w) / sr, 2), "synth_s": round(dt, 1), "rtf": round(dt / (len(w) / sr), 2)}
    print(k, stats[k], flush=True)
    json.dump(stats, open(statp, "w"), indent=1)
