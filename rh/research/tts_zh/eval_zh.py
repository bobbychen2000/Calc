"""Score Mandarin TTS test outputs.
usage: venv-eval/bin/python eval_zh.py out/<model>/*.wav      (files named <item>.wav, item in testset.json)
Writes/updates scores_zh.json keyed by wav path:
  cer_cjk  character error rate on the Chinese characters only (Paraformer-zh ASR; robust to how
           English words / letters are transcribed), cer_all (all chars, digits -> Chinese numerals)
  utmos    UTMOS22-strong (English-trained naturalness predictor; a rough proxy only)
  aes_*    Meta Audiobox Aesthetics: CE content enjoyment, CU usefulness, PC complexity, PQ quality
  rate     spoken characters per second (CJK chars + Latin words), pauses (>=150 ms count / mean),
  f0_st_sd pitch spread in semitones, f0_step  median |semitone change| between voiced 10 ms frames
"""
import json, os, re, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, soundfile as sf, librosa
HERE = os.path.dirname(os.path.abspath(__file__))
TEST = json.load(open(os.path.join(HERE, "testset.json")))
DB = os.path.join(HERE, "scores_zh.json")
CJK = re.compile(r"[一-鿿]")


def to_cn_digits(s):
    import cn2an
    try:
        return cn2an.transform(s, "an2cn")
    except Exception:
        return s


def norm_all(s):
    s = to_cn_digits(s.lower())
    return re.sub(r"[^一-鿿a-z0-9]", "", s)


def cer(ref, hyp):
    import jiwer
    if not ref:
        return float("nan")
    return jiwer.cer(" ".join(ref), " ".join(hyp)) if hyp else 1.0


def prosody(y, sr):
    iv = librosa.effects.split(y, top_db=35, frame_length=1024, hop_length=256)
    gaps = [(iv[i + 1][0] - iv[i][1]) / sr for i in range(len(iv) - 1)]
    pauses = [g for g in gaps if g >= 0.15]
    y16 = librosa.resample(y, orig_sr=sr, target_sr=16000)
    f0, vflag, _ = librosa.pyin(y16, fmin=65, fmax=500, sr=16000, frame_length=1024, hop_length=160)
    st = 12 * np.log2(f0[vflag] / 100.0) if vflag.any() else np.array([0.0])
    steps = []
    for a, b, va, vb in zip(f0[:-1], f0[1:], vflag[:-1], vflag[1:]):
        if va and vb:
            steps.append(abs(12 * np.log2(b / a)))
    speech = (iv[-1][1] - iv[0][0]) / sr if len(iv) else 0
    return dict(speech_s=round(speech, 2), n_pause=len(pauses), pause_mean=round(float(np.mean(pauses)), 3) if pauses else 0.0,
                f0_st_sd=round(float(np.std(st)), 2), f0_step=round(float(np.median(steps)), 3) if steps else 0.0,
                f0_med_hz=round(float(np.median(f0[vflag])), 1) if vflag.any() else 0.0)


def main(wavs):
    from funasr import AutoModel
    import onnxruntime as ort
    from audiobox_aesthetics.infer import initialize_predictor
    asr = AutoModel(model="paraformer-zh", disable_update=True, log_level="ERROR")
    so = ort.SessionOptions(); so.intra_op_num_threads = 4
    utmos = ort.InferenceSession("/home/user/rhwork/models/eval/utmos22_strong.onnx", so, providers=["CPUExecutionProvider"])
    aes = initialize_predictor()
    db = json.load(open(DB)) if os.path.exists(DB) else {}
    for w in wavs:
        item = os.path.splitext(os.path.basename(w))[0]
        model = os.path.basename(os.path.dirname(w))
        if item not in TEST:
            continue
        y, sr = sf.read(w, dtype="float32")
        if y.ndim > 1:
            y = y.mean(1)
        y16 = librosa.resample(y, orig_sr=sr, target_sr=16000) if sr != 16000 else y
        hyp = "".join(r["text"] for r in asr.generate(input=y16, batch_size_s=300))
        hyp = hyp.replace(" ", "")
        ref = TEST[item]
        rc, hc = "".join(CJK.findall(ref)), "".join(CJK.findall(to_cn_digits(hyp)))
        mos = float(utmos.run(None, {"wave": y16[None, :].astype(np.float32)})[0][0])
        import torch
        a = aes.forward([{"path": torch.from_numpy(y)[None, :], "sample_rate": sr}])[0]
        dur = len(y) / sr
        nref = len(CJK.findall(ref)) + len(re.findall(r"[A-Za-z]+", ref))
        p = prosody(y, sr)
        rec = dict(model=model, item=item, dur=round(dur, 2), cer_cjk=round(cer(rc, hc), 4), cer_all=round(cer(norm_all(ref), norm_all(hyp)), 4),
                   utmos=round(mos, 3), **{f"aes_{k}": round(float(v), 3) for k, v in a.items()},
                   rate=round(nref / max(p["speech_s"], 0.1), 2), **p, hyp=hyp)
        db[w] = rec
        print(f"{model:24s} {item:12s} cer {rec['cer_cjk']:.3f} utmos {mos:.2f} CE {rec['aes_CE']:.2f} PQ {rec['aes_PQ']:.2f} "
              f"rate {rec['rate']:.2f} pauses {p['n_pause']} f0sd {p['f0_st_sd']}", flush=True)
        json.dump(db, open(DB, "w"), indent=1, ensure_ascii=False)


def summary():
    db = json.load(open(DB))
    by = {}
    for r in db.values():
        by.setdefault(r["model"], []).append(r)
    keys = ["cer_cjk", "cer_all", "utmos", "aes_CE", "aes_CU", "aes_PC", "aes_PQ", "rate", "n_pause", "pause_mean", "f0_st_sd", "f0_step"]
    print(f"{'model':26s} n " + " ".join(f"{k:>9s}" for k in keys))
    for m, rs in sorted(by.items()):
        print(f"{m:26s} {len(rs)} " + " ".join(f"{np.mean([r[k] for r in rs]):9.3f}" for k in keys))


if __name__ == "__main__":
    if sys.argv[1:] == ["--summary"]:
        summary()
    else:
        main(sys.argv[1:])
