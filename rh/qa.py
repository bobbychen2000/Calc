"""QA for the narration: transcribe each scene's WAV with faster-whisper (word timestamps)
and compare with audio/<scene>.json.

  * sync: ASR word start vs our word start (the times captions and cues use), matched by
    sequence alignment on normalised words; reports median / p95 / max offset per scene
  * intelligibility: word error rate of the ASR transcript against the spoken script
  * names: how the ASR heard each proper noun (a cheap mispronunciation detector)

Run in a venv with faster-whisper:  python qa.py [--model small.en] [scene ...]
Writes out/qa_sync.json.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "audio")
NAMES = ["Riemann", "zeta", "Euler", "Alpöge", "Levent", "Gauss", "Hardy", "Hilbert", "Mangoldt",
         "Hasse", "Weil", "Deligne", "Stepanov", "Bombieri", "Schmidt", "Chebyshev", "Lean", "Mathlib",
         "Claude", "Buzzard", "Dirichlet", "Galois", "Langlands", "theta"]


def norm(w):
    w = unicodedata.normalize("NFKD", w).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", w)


def main(argv):
    model_name = "small.en"
    if "--model" in argv:
        i = argv.index("--model")
        model_name = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    scenes = sorted(f[:-5] for f in os.listdir(AUDIO) if f.endswith(".json"))
    if argv:
        scenes = [s for s in scenes if any(s.startswith(a) for a in argv)]
    report = {}
    for sid in scenes:
        meta = json.load(open(os.path.join(AUDIO, f"{sid}.json")))
        pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(AUDIO, f"{sid}.wav"),
                              "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
        audio = np.frombuffer(pcm, dtype=np.float32)
        segs, _ = model.transcribe(audio, word_timestamps=True, beam_size=5, language="en", vad_filter=False)
        asr = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
        # our spoken words, split into tokens, each carrying its segment's start
        ours = []
        for w in meta["words"]:
            toks = [t for t in re.split(r"[\s\-]+", w["spoken"]) if norm(t)] if not w["spoken"].startswith("/") else [w["w"]]
            for k, t in enumerate(toks):
                ours.append((t, w["start"] if k == 0 else None, w["w"]))
        a_n = [norm(x[0]) for x in asr]
        o_n = [norm(x[0]) for x in ours]
        sm = difflib.SequenceMatcher(a=o_n, b=a_n, autojunk=False)
        offs, matched = [], 0
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                o, a = ours[blk.a + k], asr[blk.b + k]
                matched += 1
                if o[1] is not None:
                    offs.append(a[1] - o[1])
        # word error rate (Levenshtein on normalised tokens)
        n, m = len(o_n), len(a_n)
        d = list(range(m + 1))
        for i in range(1, n + 1):
            prev, d[0] = d[0], i
            for j in range(1, m + 1):
                cur = d[j]
                d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (o_n[i - 1] != a_n[j - 1]))
                prev = cur
        wer = d[m] / max(1, n)
        # how each name was heard: the ASR words aligned with it
        heard = {}
        ops = sm.get_opcodes()
        for tag, i1, i2, j1, j2 in ops:
            for i in range(i1, i2):
                disp = ours[i][2]
                for nm in NAMES:
                    if norm(nm) and norm(nm) in norm(disp):
                        if tag == "equal":
                            heard.setdefault(nm, []).append(asr[j1 + (i - i1)][0])
                        else:
                            heard.setdefault(nm, []).append(" ".join(x[0] for x in asr[j1:j2]) or "(missing)")
        offs_abs = sorted(abs(x) for x in offs)
        r = {
            "words": n, "asr_words": m, "matched": matched, "wer": round(wer, 3),
            "offset_median": round(sorted(offs)[len(offs) // 2], 3) if offs else None,
            "abs_offset_p95": round(offs_abs[int(0.95 * (len(offs_abs) - 1))], 3) if offs_abs else None,
            "abs_offset_max": round(offs_abs[-1], 3) if offs_abs else None,
            "heard": heard,
            "asr_text": " ".join(x[0] for x in asr),
        }
        report[sid] = r
        print(f"{sid}: WER {r['wer']:.3f}  offset median {r['offset_median']}  p95 {r['abs_offset_p95']}  "
              f"max {r['abs_offset_max']}  names {dict((k, sorted(set(v))) for k, v in heard.items())}", flush=True)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    with open(os.path.join(HERE, "out", "qa_sync.json"), "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
