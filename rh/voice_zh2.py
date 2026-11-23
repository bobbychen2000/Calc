"""Mandarin narration, second generation: script_zh.py -> audio_zh/<scene>.wav + .json (same schema as voice.py).

Qwen3-TTS-12Hz-1.7B-CustomVoice (Qwen, Apache-2.0), preset speaker + a calm-narration instruction,
synthesised ONE SENTENCE AT A TIME (the Kokoro pipeline, voice_zh.py, spoke one clause at a time with
fixed gaps, which is what sounded choppy).  Each take passes a quality gate: Paraformer-zh (FunASR)
transcribes it back and the take is redone with a new seed if the Chinese characters do not match
(syllable error rate > MAX_CER) or the pace is off (an LLM TTS can stall or run on); the best of MAX_TAKES is kept.
Caption chunks and {cue}s inside a sentence are then timed by forced alignment (FunASR fa-zh: a
timestamp for every character / English word), so captions and animation cues stay exact.

    /home/user/rhwork/venv-qwen/bin/python voice_zh2.py [scene_id ...]
    /home/user/rhwork/venv-qwen/bin/python voice_zh2.py --retime [scene_id ...]   # re-time existing takes
    env: RH_TTS_MODEL (model dir), RH_TTS_SPEAKER (Serena), RH_TTS_INSTRUCT, RH_TTS_THREADS (4)
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
import voice_zh as V  # noqa: E402  (parse, captions, tidy, word breaks: shared with the Kokoro pipeline)

AUDIO = os.environ.get("RH_AUDIO_OUT", os.path.join(HERE, "audio_zh"))
GATE = os.path.join(HERE, "research", "tts_zh", "gate")   # per-sentence quality-gate log (every take)
MODEL = os.environ.get("RH_TTS_MODEL", "/home/user/rhwork/tts_zh/models/Qwen3-TTS-12Hz-1.7B-CustomVoice")
SPEAKER = os.environ.get("RH_TTS_SPEAKER", "Serena")
INSTRUCT = os.environ.get("RH_TTS_INSTRUCT", "用平稳、清晰、温和的科普讲解语气，语速适中，娓娓道来。")
SR = 24000
LEAD, TAIL = 0.45, 0.75
GAP = {"sentence": 0.32, "para": 0.60}
MAX_TAKES, MAX_CER = 4, 0.04
RATE = (2.4, 6.0)             # spoken units (Han chars + Latin words) per second accepted
CJK = re.compile(r"[一-鿿]")
TOK = re.compile(r"[一-鿿]|[A-Za-z]+(?:-[A-Za-z]+)*|[0-9]+")

# The spoken halves of script_zh.py's [display|spoken] markup carry fixes for Kokoro's G2P (a
# homophone for 行, 的 for the complement 得, a hyphen in Levent, an English name for 切比雪夫, 向量
# for 相量).  An LLM TTS reads the real words in context, so they are undone here.
UNDO = [("万航", "万行"), ("走的更远", "走得更远"), ("缩短的够快", "缩短得够快"), ("缩短的不够快", "缩短得不够快"),
        ("摊的越薄", "摊得越薄"), ("平滑的惊人", "平滑得惊人"), ("响亮的多", "响亮得多"), ("Le-vent", "Levent"),
        ("Chebyshev", "切比雪夫"), ("用过向量", "用过相量")]

_TTS = _ASR = _FA = None


def tts():
    global _TTS
    if _TTS is None:
        import torch
        from qwen_tts import Qwen3TTSModel
        torch.set_num_threads(int(os.environ.get("RH_TTS_THREADS", "4")))
        _TTS = Qwen3TTSModel.from_pretrained(MODEL, device_map="cpu", dtype=torch.bfloat16)
    return _TTS


def asr():
    global _ASR, _FA
    if _ASR is None:
        from funasr import AutoModel
        _ASR = AutoModel(model="paraformer-zh", disable_update=True, log_level="ERROR")
        _FA = AutoModel(model="fa-zh", disable_update=True, log_level="ERROR")
    return _ASR, _FA


def spoken_fix(s):
    for a, b in UNDO:
        s = s.replace(a, b)
    return s


def cn_digits(s):
    """Arabic numbers -> Chinese numerals (cn2an), as the voice reads them."""
    import cn2an
    try:
        return cn2an.transform(s, "an2cn")
    except Exception:
        return s


def units(s):
    s = cn_digits(s)
    return len(CJK.findall(s)) + len(re.findall(r"[A-Za-z]+", s))


def trim(a, thr=0.01, keep=0.04):
    idx = np.nonzero(np.abs(a) > thr)[0]
    if len(idx) == 0:
        return a[:0]
    return a[max(0, idx[0] - int(keep * SR)): min(len(a), idx[-1] + int(keep * SR))]


def resample16(a):
    import librosa
    return librosa.resample(a, orig_sr=SR, target_sr=16000)


def cer_cjk(ref, hyp):
    """Error rate over the toneless pinyin syllables of the Chinese characters: a misread or dropped
    syllable counts, an ASR homophone (复数 / 负数, 相量 / 向量, 它们 / 他们) does not."""
    import jiwer
    from pypinyin import lazy_pinyin
    ref, hyp = cn_digits(ref), cn_digits(hyp)
    r = lazy_pinyin("".join(CJK.findall(ref)))
    h = lazy_pinyin("".join(CJK.findall(hyp)))
    if not r:
        return 0.0
    return jiwer.wer(" ".join(r), " ".join(h)) if h else 1.0


def synth_sentence(text, log):
    """Best take of `text` by the quality gate: (cer, rate penalty) lowest; stop at the first good one."""
    import torch
    m = tts()
    a_model, _ = asr()
    best = None
    for take in range(MAX_TAKES):
        torch.manual_seed(1000 + take)
        wavs, sr = m.generate_custom_voice(text=text, language="Chinese", speaker=SPEAKER, instruct=INSTRUCT,
                                           max_new_tokens=int(units(text) / 3.0 * 12.5 * 1.7) + 60)
        a = trim(np.asarray(wavs[0], dtype=np.float32))
        dur = len(a) / SR
        hyp = "".join(r["text"] for r in a_model.generate(input=resample16(a), batch_size_s=300)).replace(" ", "")
        c = cer_cjk(text, hyp)
        rate = units(text) / max(dur, 0.1)
        pen = 0 if RATE[0] <= rate <= RATE[1] else 1
        score = (pen, round(c, 3))
        log.append({"take": take, "cer": round(c, 3), "rate": round(rate, 2), "dur": round(dur, 2), "hyp": hyp})
        if best is None or score < best[0]:
            best = (score, a)
        if pen == 0 and c <= MAX_CER:
            break
    return best[1], best[0]


def align(a, text):
    """Forced alignment: (start, end) in seconds for every token of TOK.findall(text).  The aligner
    tokenises on its own (it may split or merge Latin letters), so its tokens are matched back to ours
    with difflib and any token it skipped is interpolated between its neighbours."""
    import difflib
    _, fa = asr()
    toks = TOK.findall(text)
    res = fa.generate(input=(resample16(a), " ".join(toks)), data_type=("sound", "text"))
    got = res[0]["text"].split()
    ts = [(s / 1000.0, e / 1000.0) for s, e in res[0]["timestamp"]]
    got, ts = got[:len(ts)], ts[:len(got)]
    out = [None] * len(toks)
    sm = difflib.SequenceMatcher(a=[t.lower() for t in toks], b=[g.lower() for g in got], autojunk=False)
    for tag, i0, i1, j0, j1 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i1 - i0):
                out[i0 + k] = ts[j0 + k]
        elif tag == "replace" and j1 > j0:  # e.g. one Latin word aligned as letters: spread its span
            s0, e0 = ts[j0][0], ts[j1 - 1][1]
            n = i1 - i0
            for k in range(n):
                out[i0 + k] = (s0 + (e0 - s0) * k / n, s0 + (e0 - s0) * (k + 1) / n)
    dur = len(a) / SR
    for i in range(len(out)):  # interpolate what is still missing
        if out[i] is None:
            prev = next((out[j][1] for j in range(i - 1, -1, -1) if out[j]), 0.0)
            nxt = next((out[j][0] for j in range(i + 1, len(out)) if out[j]), dur)
            out[i] = (prev, max(prev, nxt))
    return toks, out


def gaps(a, min_len=0.06, rel_db=-30.0):
    """Silent stretches of a sentence take: (start, end) in seconds, frames 10 ms below rel_db of its loud frames."""
    hop, win = int(0.01 * SR), int(0.025 * SR)
    if len(a) < win:
        return []
    rms = np.sqrt(np.convolve(a.astype(np.float64) ** 2, np.ones(win) / win, mode="same"))[::hop]
    thr = np.percentile(rms, 95) * 10 ** (rel_db / 20)
    quiet = rms < thr
    out, k = [], 0
    while k < len(quiet):
        if quiet[k]:
            j = k
            while j < len(quiet) and quiet[j]:
                j += 1
            if (j - k) * 0.01 >= min_len:
                out.append((k * 0.01, j * 0.01))
            k = j
        else:
            k += 1
    return out


def asr_times(a, text):
    """Start time of every token of TOK.findall(text) per Paraformer's own character timestamps, where
    the recognised character matches ours (toneless pinyin, so homophones match); None elsewhere."""
    import difflib
    from pypinyin import lazy_pinyin
    a_model, _ = asr()
    r = a_model.generate(input=resample16(a))[0]
    hyp, hts = [], []
    for tok, (s0, _e) in zip(r["text"].split(), r.get("timestamp", [])):
        if CJK.fullmatch(tok):
            hyp.append(tok)
            hts.append(s0 / 1000.0)
    toks = TOK.findall(text)
    idx = [i for i, t in enumerate(toks) if CJK.fullmatch(t)]
    sm = difflib.SequenceMatcher(a=lazy_pinyin("".join(toks[i] for i in idx)), b=lazy_pinyin("".join(hyp)), autojunk=False)
    out = [None] * len(toks)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            out[idx[blk.a + k]] = hts[blk.b + k]
    return out


def chunk_times(a, spoken):
    """(start, end) of every caption chunk of one sentence take, in seconds from its start.  A chunk
    starts at Paraformer's timestamp of its first character when the recogniser heard that character
    (else at the forced aligner's), snapped to the end of the pause it falls in: chunks split at
    punctuation, where the voice pauses, and the aligner tends to put a clause's first character
    before that pause."""
    text = "".join(spoken)
    _, stamps = align(a, text)
    heard = asr_times(a, text)
    gs = gaps(a)
    dur = len(a) / SR
    out, k = [], 0
    for ci, sp in enumerate(spoken):
        n = len(TOK.findall(sp))
        if n == 0:
            st = stamps[k][0] if k < len(stamps) else dur
            out.append([st, st])
            continue
        st, en = stamps[k][0], stamps[k + n - 1][1]
        if ci > 0:
            if heard[k] is not None and abs(heard[k] - st) < 1.0:
                st = heard[k]
            near = [g for g in gs if g[0] - 0.25 <= st <= g[1] + 0.25]
            if near:
                g = min(near, key=lambda g: 0 if g[0] <= st <= g[1] else min(abs(st - g[0]), abs(st - g[1])))
                st = max(g[1] - 0.02, 0.0)
                out[-1][1] = min(out[-1][1], g[0] + 0.02)
            out[-1][1] = min(out[-1][1], st)
        out.append([st, max(en, st)])
        k += n
    out[0][0] = 0.0
    out[-1][1] = dur
    return out


def voice_scene(sc, retime=False):
    """Synthesise (or, with retime=True, re-time the existing audio_zh take of) one scene."""
    t0 = time.time()
    paras = [p.strip() for p in re.split(r"\n\s*\n", sc["text"].strip()) if p.strip()]
    if retime:
        old = json.load(open(os.path.join(AUDIO, f"{sc['id']}.json")))
        old_words = list(old["words"])
        wav, _ = sf.read(os.path.join(AUDIO, f"{sc['id']}.wav"), dtype="float32")
        gate_path = os.path.join(GATE, f"{sc['id']}.gate.json")
        gate = json.load(open(gate_path)) if os.path.exists(gate_path) else []
    else:
        pieces = [np.zeros(int(LEAD * SR), np.float32)]
        gate = []
    t = LEAD
    allch, cues, words = [], {}, []
    for pi, para in enumerate(paras):
        chs = V.parse(" ".join(para.split()))
        sents, cur = [], []  # sentences: runs of chunks up to a sentence end
        for c in chs:
            cur.append(c)
            if c["end"] == "sentence":
                sents.append(cur)
                cur = []
        if cur:
            sents.append(cur)
        for si, sent in enumerate(sents):
            spoken = [spoken_fix(c["spoken"]) for c in sent]
            text = "".join(spoken)
            if not text.strip():
                for c in sent:
                    for name in c["cues"]:
                        cues[name] = round(t, 3)
                    c["start"] = c["end_t"] = t
                continue
            if retime:
                mine = [old_words.pop(0) for c in sent if c["spoken"]]
                t = mine[0]["start"]
                a = wav[int(round(t * SR)): int(round(mine[-1]["end"] * SR))]
            else:
                log = []
                a, score = synth_sentence(text, log)
                gate.append({"text": text, "score": list(score), "takes": log})
            for c, (st, en) in zip(sent, chunk_times(a, spoken)):
                c["start"], c["end_t"] = round(t + st, 3), round(t + en, 3)
                for name in c["cues"]:
                    cues[name] = c["start"]
            for c, sp in zip(sent, spoken):
                if c["spoken"]:
                    words.append({"w": c["display"], "spoken": sp, "start": c["start"], "end": c["end_t"]})
            t += len(a) / SR
            if not retime:
                pieces.append(a)
                last = pi == len(paras) - 1 and si == len(sents) - 1
                if not last:
                    g = GAP["para"] if si == len(sents) - 1 else GAP["sentence"]
                    pieces.append(np.zeros(int(g * SR), np.float32))
                    t += g
        allch.extend(chs)
    os.makedirs(AUDIO, exist_ok=True)
    if not retime:
        pieces.append(np.zeros(int(TAIL * SR), np.float32))
        wav = np.concatenate(pieces)
        sf.write(os.path.join(AUDIO, f"{sc['id']}.wav"), wav, SR, subtype="PCM_16")
        os.makedirs(GATE, exist_ok=True)
        with open(os.path.join(GATE, f"{sc['id']}.gate.json"), "w") as f:
            json.dump(gate, f, indent=1, ensure_ascii=False)
    meta = {"scene": sc["id"], "duration": round(len(wav) / SR, 3), "sr": SR,
            "voice": f"{os.path.basename(MODEL)}/{SPEAKER}", "speed": "instruct", "instruct": INSTRUCT,
            "words": words, "chunks": V.captions(allch), "cues": cues}
    with open(os.path.join(AUDIO, f"{sc['id']}.json"), "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    retakes = sum(len(g["takes"]) - 1 for g in gate)
    worst = max((g["score"][1] for g in gate), default=0)
    print(f"{sc['id']}: {meta['duration']:6.1f} s, {len(gate)} sentences, {retakes} retakes, worst CER {worst:.3f}, "
          f"cues {list(cues)} ({time.time() - t0:.0f} s){' [retimed]' if retime else ''}", flush=True)
    return meta


def main(argv):
    retime = "--retime" in argv
    want = set(a for a in argv if not a.startswith("--"))
    total = 0.0
    for sc in SCRIPT.SCENES:
        if not want or sc["id"] in want:
            total += voice_scene(sc, retime=retime)["duration"]
    print(f"total {total / 60:.2f} min")


if __name__ == "__main__":
    main(sys.argv[1:])
