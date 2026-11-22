"""Mandarin narration: script_zh.py -> audio_zh/<scene>.wav + .json (same schema as voice.py).

Kokoro-82M-v1.1-zh (hexgrad, Apache-2.0), voice zf_003, through the PyTorch KPipeline with
misaki's Chinese G2P and an English G2P for Latin-script words.  The Chinese pipeline reports no
word timestamps, so the text is synthesised one caption chunk at a time (split at Chinese
punctuation and at {cue}s) and the timings come from the chunk durations: every cue falls on a
chunk start, every caption is one or two chunks.

    /home/user/rhwork/venv-tts/bin/python voice_zh.py [scene_id ...]
    /home/user/rhwork/venv-tts/bin/python voice_zh.py --breaks   # caption word breaks only
"""
import json
import os
import re
import sys
import time
import warnings

import numpy as np
import soundfile as sf

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import script_zh as SCRIPT  # noqa: E402

AUDIO = os.path.join(HERE, "audio_zh")
SR = 24000
REPO = "hexgrad/Kokoro-82M-v1.1-zh"
VOICE = os.environ.get("RH_VOICE_ZH", "zf_003")
LEAD, TAIL = 0.45, 0.75
PAUSE = {"sentence": 0.30, "clause": 0.12, "cue": 0.05, "para": 0.55}
CAP_MAX = 24            # characters per caption (two lines of ~12-14 at 33 pt fit easily)
SEG = re.compile(r"\[([^\]|]*)\|([^\]]*)\]|\{([A-Za-z0-9_]+)\}")
SENT_END = "。？！?!"
CLAUSE_END = "，；：、,;:"

_PIPE = None


def speed_callable(len_ps):
    """The model author's recommended pacing for the zh model (slows long inputs)."""
    speed = 0.8
    if len_ps <= 83:
        speed = 1
    elif len_ps < 183:
        speed = 1 - (len_ps - 83) / 500
    return speed * 1.1


def pipeline():
    global _PIPE
    if _PIPE is None:
        import torch
        from kokoro import KModel, KPipeline
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        model = KModel(repo_id=REPO).eval()
        en = KPipeline(lang_code="a", repo_id=REPO, model=False)

        def en_callable(text):
            return next(en(text)).phonemes

        _PIPE = KPipeline(lang_code="z", repo_id=REPO, model=model, en_callable=en_callable)
    return _PIPE


def parse(text):
    """Paragraph -> list of chunks [{display, spoken, cue_before: [...], end: 'sentence'|'clause'|'cue'}]."""
    items = []  # ('t', display, spoken) | ('cue', name)
    pos = 0
    for m in SEG.finditer(text):
        if m.start() > pos:
            items.append(("t", text[pos:m.start()], text[pos:m.start()]))
        if m.group(3):
            items.append(("cue", m.group(3)))
        else:
            items.append(("t", m.group(1), m.group(2)))
        pos = m.end()
    if pos < len(text):
        items.append(("t", text[pos:], text[pos:]))
    chunks, cur_d, cur_s, cues = [], "", "", []

    def close(kind):
        nonlocal cur_d, cur_s, cues
        if cur_d.strip() or cur_s.strip():
            chunks.append({"display": cur_d.strip(), "spoken": cur_s.strip(), "cues": cues, "end": kind})
            cues = []
        cur_d, cur_s = "", ""

    for it in items:
        if it[0] == "cue":
            close("cue")
            cues.append(it[1])
            continue
        _, d, s = it
        if d == s:  # plain text: split at punctuation
            buf = ""
            for ch in d:
                buf += ch
                if ch in SENT_END or ch in CLAUSE_END:
                    cur_d += buf
                    cur_s += buf
                    buf = ""
                    close("sentence" if ch in SENT_END else "clause")
            cur_d += buf
            cur_s += buf
        else:  # [display|spoken]: never split inside; trailing punctuation in display ends a chunk
            cur_d += d
            cur_s += s
            if d and (d[-1] in SENT_END or d[-1] in CLAUSE_END):
                close("sentence" if d[-1] in SENT_END else "clause")
    close("sentence")
    if cues:  # cue at the very end of the paragraph
        chunks.append({"display": "", "spoken": "", "cues": cues, "end": "cue"})
    return chunks


def trim(a, thr=0.012, keep=0.03):
    idx = np.nonzero(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a[:0]
    s = max(0, idx[0] - int(keep * SR))
    e = min(len(a), idx[-1] + int(keep * SR))
    return a[s:e]


def synth(spoken):
    pipe = pipeline()
    parts = [r.audio.numpy().astype(np.float32) for r in pipe(spoken, voice=VOICE, speed=speed_callable)]
    return trim(np.concatenate(parts)) if parts else np.zeros(0, np.float32)


def captions(chs):
    """Merge chunks into captions of at most CAP_MAX characters, never across a sentence end."""
    caps, cur = [], []
    for c in chs:
        if not c["display"]:
            continue
        if cur and (len("".join(x["display"] for x in cur + [c])) > CAP_MAX or cur[-1]["end"] == "sentence"):
            caps.append(cur)
            cur = []
        cur.append(c)
    if cur:
        caps.append(cur)
    out = []
    for g in caps:
        text = "".join(x["display"] for x in g)
        text = tidy(re.sub(r"[，、；：,;:]$", "", text))  # no dangling clause punctuation on screen
        out.append({"text": text, "start": g[0]["start"], "end": g[-1]["end_t"], "breaks": word_breaks(text)})
    return out


_JIEBA = None
EXTRA_WORDS = ["钟面", "钟点", "四分之三次方", "黎曼猜想", "临界线", "临界带", "非平凡零点", "解析延拓",
               "显式公式", "随机游走", "辅助多项式", "待确认的证明", "广义黎曼猜想", "扩展黎曼猜想"]


def _jieba():
    """jieba with the glossary's Chinese terms as words (so 黎曼猜想 is never split)."""
    global _JIEBA
    if _JIEBA is None:
        import jieba
        jieba.setLogLevel(60)
        g = json.load(open(os.path.join(HERE, "i18n", "glossary_zh.json")))["glossary"]
        for term in [t["zh"] for t in g] + EXTRA_WORDS:
            for w in re.split(r"[\s/（）()，、：；·]+", term):
                if 2 <= len(w) <= 6 and re.fullmatch(r"[\u4e00-\u9fff]+", w):
                    jieba.add_word(w, freq=200000)
        _JIEBA = jieba
    return _JIEBA


CJK_SPACE = re.compile(r"(?<=[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef]) +(?=[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef])")


def tidy(text):
    """No spaces between two Chinese characters on screen (the [display|spoken] markup leaves some)."""
    return CJK_SPACE.sub("", text)


def word_breaks(text):
    """Character offsets between words (jieba), for the renderer's caption line breaking."""
    out, pos = [], 0
    for w in _jieba().cut(text):
        pos += len(w)
        out.append(pos)
    return out[:-1]


def add_breaks():
    """Recompute the caption breaks of the voiced scenes without re-synthesising."""
    for f in sorted(os.listdir(AUDIO)):
        if f.endswith(".json"):
            path = os.path.join(AUDIO, f)
            meta = json.load(open(path))
            for ch in meta["chunks"]:
                ch["text"] = tidy(ch["text"])
                ch["breaks"] = word_breaks(ch["text"])
            with open(path, "w") as fh:
                json.dump(meta, fh, indent=1, ensure_ascii=False)


def voice_scene(sc):
    t0 = time.time()
    paras = [p.strip() for p in re.split(r"\n\s*\n", sc["text"].strip()) if p.strip()]
    pieces = [np.zeros(int(LEAD * SR), np.float32)]
    t = LEAD
    allch, cues, words = [], {}, []
    for pi, para in enumerate(paras):
        chs = parse(" ".join(para.split()))
        for k, c in enumerate(chs):
            for name in c["cues"]:
                cues[name] = round(t, 3)
            if not c["spoken"]:
                c["start"] = c["end_t"] = t
                continue
            a = synth(c["spoken"])
            c["start"] = round(t, 3)
            pieces.append(a)
            t += len(a) / SR
            c["end_t"] = round(t, 3)
            words.append({"w": c["display"], "spoken": c["spoken"], "start": c["start"], "end": c["end_t"]})
            last = k == len(chs) - 1 or all(not x["spoken"] for x in chs[k + 1:])
            if not last:
                gap = PAUSE[c["end"]]
                pieces.append(np.zeros(int(gap * SR), np.float32))
                t += gap
        allch.extend(chs)
        if pi < len(paras) - 1:
            pieces.append(np.zeros(int(PAUSE["para"] * SR), np.float32))
            t += PAUSE["para"]
    pieces.append(np.zeros(int(TAIL * SR), np.float32))
    wav = np.concatenate(pieces)
    os.makedirs(AUDIO, exist_ok=True)
    sf.write(os.path.join(AUDIO, f"{sc['id']}.wav"), wav, SR, subtype="PCM_16")
    meta = {"scene": sc["id"], "duration": round(len(wav) / SR, 3), "sr": SR, "voice": VOICE, "speed": "speed_callable",
            "words": words, "chunks": captions(allch), "cues": cues}
    with open(os.path.join(AUDIO, f"{sc['id']}.json"), "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    print(f"{sc['id']}: {meta['duration']:6.1f} s, {len(words)} chunks, {len(meta['chunks'])} captions, "
          f"cues {list(cues)} ({time.time() - t0:.0f} s)", flush=True)
    return meta


def main(argv):
    if argv == ["--breaks"]:
        return add_breaks()
    want = set(argv)
    total = 0.0
    for sc in SCRIPT.SCENES:
        if not want or sc["id"] in want:
            total += voice_scene(sc)["duration"]
    print(f"total {total / 60:.2f} min")


if __name__ == "__main__":
    main(sys.argv[1:])
