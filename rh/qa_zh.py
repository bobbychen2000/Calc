"""QA for the Mandarin narration (run in a venv with faster-whisper): transcribe each scene of
audio_zh/ with Whisper (multilingual, language zh, word timestamps), align the transcript to the
spoken text character by character, and report
  * sync: ASR time of each chunk's first matched character vs the chunk start in the JSON
  * CER: character error rate against the spoken text (digits / Latin kept as they are)
  * the transcript, for reading
Writes out_zh/qa_sync.json.
"""
import difflib
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "audio_zh")
DROP = re.compile(r"[\s，。、；：？！,.;:?!“”\"'（）()《》·…—\-]")


def norm(s):
    return DROP.sub("", s.lower())


def main(argv):
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    scenes = sorted(f[:-5] for f in os.listdir(AUDIO) if f.endswith(".json"))
    if argv:
        scenes = [s for s in scenes if any(s.startswith(a) for a in argv)]
    report = {}
    for sid in scenes:
        meta = json.load(open(os.path.join(AUDIO, f"{sid}.json")))
        pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(AUDIO, f"{sid}.wav"), "-f", "f32le",
                              "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
        audio = np.frombuffer(pcm, dtype=np.float32)
        segs, _ = model.transcribe(audio, language="zh", word_timestamps=True, beam_size=5,
                                   initial_prompt="以下是普通话讲解：黎曼猜想、zeta 函数、素数、零点、临界线。")
        hyp_chars, hyp_t = [], []
        text = ""
        for s in segs:
            text += s.text
            for w in s.words:
                cs = norm(w.word)
                for k, c in enumerate(cs):
                    hyp_chars.append(c)
                    hyp_t.append(w.start + (w.end - w.start) * k / max(1, len(cs)))
        ref_chars, ref_chunk_start = [], []
        for w in meta["words"]:
            cs = norm(w["spoken"])
            ref_chunk_start.append(len(ref_chars))
            ref_chars.extend(cs)
        sm = difflib.SequenceMatcher(a=ref_chars, b=hyp_chars, autojunk=False)
        amap = {}
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                amap[blk.a + k] = blk.b + k
        offs = []
        for w, i0 in zip(meta["words"], ref_chunk_start):
            n = len(norm(w["spoken"]))
            for i in range(i0, i0 + min(n, 3)):  # first matched char among the chunk's first three
                if i in amap:
                    offs.append(hyp_t[amap[i]] - w["start"] - (i - i0) * 0.2)
                    break
        # CER
        a, b = ref_chars, hyp_chars
        d = list(range(len(b) + 1))
        for i in range(1, len(a) + 1):
            prev, d[0] = d[0], i
            for j in range(1, len(b) + 1):
                cur = d[j]
                d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (a[i - 1] != b[j - 1]))
                prev = cur
        cer = d[-1] / max(1, len(a))
        oa = sorted(abs(x) for x in offs)
        r = {"chunks": len(meta["words"]), "matched_chunks": len(offs), "cer": round(cer, 3),
             "offset_median": round(sorted(offs)[len(offs) // 2], 3) if offs else None,
             "abs_offset_p90": round(oa[int(0.9 * (len(oa) - 1))], 3) if oa else None, "asr_text": text}
        report[sid] = r
        print(f"{sid}: CER {r['cer']:.3f}  chunks {r['matched_chunks']}/{r['chunks']}  offset median "
              f"{r['offset_median']}  p90 {r['abs_offset_p90']}", flush=True)
    os.makedirs(os.path.join(HERE, "out_zh"), exist_ok=True)
    with open(os.path.join(HERE, "out_zh", "qa_sync.json"), "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
