"""Narration: script.py -> audio/<scene>.wav + audio/<scene>.json

Neural TTS: Kokoro-82M (hexgrad, Apache-2.0) through its PyTorch pipeline, which also
reports when every word is spoken (the duration predictor's own timestamps), so the
caption chunks and the {cue} sync points come from the model, not from estimates.

Run in the TTS venv (Python 3.12; see README.md):
    /home/user/rhwork/venv-tts/bin/python voice.py [scene_id ...]

JSON schema per scene:
  {"scene", "duration", "sr", "voice", "speed",
   "words":  [{"w": display word, "spoken": text sent to TTS, "start", "end"}],
   "chunks": [{"text": caption text, "start", "end"}],
   "cues":   {name: time}}
Times are seconds from the start of the scene's WAV (which includes LEAD silence).
"""
import json
import os
import re
import sys
import time
import unicodedata
import warnings

import numpy as np
import soundfile as sf

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import script as SCRIPT  # noqa: E402

AUDIO = os.path.join(HERE, "audio")
SR = 24000
VOICE = os.environ.get("RH_VOICE", "af_heart")
SPEED = float(os.environ.get("RH_SPEED", "1.0"))
LEAD, TAIL = 0.45, 0.75          # silence before / after each scene's narration (s)
PARA_GAP = 0.55                  # between paragraphs
CHUNK_GAP = 0.10                 # between pipeline chunks inside a paragraph
CAP_MAX_CHARS = 84               # caption chunk: at most 2 lines of ~42 characters
CAP_MAX_SECONDS = 5.5

# Pronunciation lexicon: word -> misaki phonemes (Kokoro's alphabet: A = eI, I = aI,
# O = oU, W = aU, Y = OI, T = flap; stress marks as IPA).  Filled from the
# pronunciation research in research/math_facts.md.
LEXICON = getattr(SCRIPT, "LEXICON", {})

SEG = re.compile(r"\[([^\]|]*)\|([^\]]*)\]|\{([A-Za-z0-9_]+)\}")


def parse(text):
    """Split one paragraph into segments: ('word', display, spoken), ('cue', name)."""
    out = []
    pos = 0
    last = {"group": False}

    def plain(chunk):
        # text glued to the previous [display|spoken] group without a space ("[1859|...]."
        # or "[x|y],") belongs to that word, in both its display and spoken forms
        # (after a {cue} it is simply the next word)
        if chunk and not chunk[0].isspace() and last["group"]:
            head = chunk.split()[0]
            prev = next((k for k in range(len(out) - 1, -1, -1) if out[k][0] == "word"), None)
            if prev is not None:
                _, d, sp = out[prev]
                out[prev] = ("word", d + head, sp + head)
                chunk = chunk[len(head):]
        for w in chunk.split():
            out.append(("word", w, w))

    for m in SEG.finditer(text):
        plain(text[pos:m.start()])
        if m.group(3):
            out.append(("cue", m.group(3)))
            last["group"] = False
        else:
            out.append(("word", m.group(1).strip(), m.group(2).strip()))
            last["group"] = True
        pos = m.end()
    plain(text[pos:])
    return out


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s.lower() if c.isalnum())


def tts_text(segs):
    """The string sent to Kokoro plus the char span of each word segment in it."""
    parts, spans, pos = [], [], 0
    for sg in segs:
        if sg[0] != "word":
            spans.append(None)
            continue
        spoken = sg[2]
        key = spoken.strip(".,;:!?\"'()").strip()
        mph = re.match(r"^/([^/]+)/(.*)$", spoken)
        if mph:  # [display|/phonemes/] : say these phonemes, align them to the display word
            word = re.sub(r"[^\w\-]", "", unicodedata.normalize("NFKD", sg[1]).encode("ascii", "ignore").decode()) or "x"
            spoken = f"[{word}](/{mph.group(1)}/)" + mph.group(2)
        elif key in LEXICON and spoken.startswith(key):
            # misaki inline override: [word](/phonemes/)
            spoken = f"[{key}](/{LEXICON[key]}/)" + spoken[len(key):]
        if spoken == "":
            spans.append((pos, pos))
            continue
        if parts:
            parts.append(" ")
            pos += 1
        spans.append((pos, pos + len(spoken)))
        parts.append(spoken)
        pos += len(spoken)
    return "".join(parts), spans


_PIPE = None


def pipeline():
    global _PIPE
    if _PIPE is None:
        import torch
        from kokoro import KPipeline
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        _PIPE = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    return _PIPE


def synth_paragraph(text):
    """Synthesize one paragraph; return audio and a list of (char_start, char_end, t0, t1)
    for every token the model spoke, in the coordinates of `text`."""
    pipe = pipeline()
    audio, toks, offset = [], [], 0.0
    cursor = 0
    plain = re.sub(r"\[([^\]]*)\]\(/[^/]*/\)", r"\1", text)  # what tokens' .text refers to
    for r in pipe(text, voice=VOICE, speed=SPEED, split_pattern=r"\n+"):
        a = r.audio.numpy().astype(np.float32)
        for tk in (r.tokens or []):
            if tk.start_ts is None or tk.end_ts is None:
                continue
            j = plain.find(tk.text, cursor)
            if j < 0:
                continue
            toks.append((j, j + len(tk.text), offset + tk.start_ts, offset + tk.end_ts))
            cursor = j + len(tk.text)
        audio.append(a)
        audio.append(np.zeros(int(CHUNK_GAP * SR), np.float32))
        offset += len(a) / SR + CHUNK_GAP
    return np.concatenate(audio[:-1]) if audio else np.zeros(0, np.float32), toks, plain


def plain_spans(text, spans):
    """Map char spans in the TTS text (with [w](/ph/) overrides) to the plain text."""
    out, shift, k = [], 0, 0
    overrides = [(m.start(), m.end(), len(m.group(1))) for m in re.finditer(r"\[([^\]]*)\]\(/[^/]*/\)", text)]
    for sp in spans:
        if sp is None:
            out.append(None)
            continue
        a, b = sp
        while k < len(overrides) and overrides[k][1] <= a:
            shift += (overrides[k][1] - overrides[k][0]) - overrides[k][2]
            k += 1
        a2 = a - shift
        # an override inside this span shortens it
        inner = sum((e - s) - L for s, e, L in overrides if s >= a and e <= b)
        out.append((a2, b - shift - inner))
    return out


def captions(words):
    """Group display words into caption chunks: break after sentence / clause punctuation,
    keep under CAP_MAX_CHARS and CAP_MAX_SECONDS."""
    chunks, cur = [], []

    def flush():
        if cur:
            chunks.append({"text": " ".join(w["w"] for w in cur),
                           "start": cur[0]["start"], "end": cur[-1]["end"]})
            cur.clear()

    for i, w in enumerate(words):
        if not w["w"]:
            continue
        cand = " ".join(x["w"] for x in cur + [w])
        if cur and (len(cand) > CAP_MAX_CHARS or w["end"] - cur[0]["start"] > CAP_MAX_SECONDS):
            # prefer to break at the last clause punctuation inside cur
            cut = None
            for j in range(len(cur) - 1, 0, -1):
                if re.search(r"[,;:—–]$", cur[j - 1]["w"]):
                    cut = j
                    break
            if cut and len(" ".join(x["w"] for x in cur[:cut])) > 25:
                rest = cur[cut:]
                del cur[cut:]
                flush()
                cur.extend(rest)
            else:
                flush()
        cur.append(w)
        if re.search(r"[.?!]['\")\]]*$", w["w"]) or (w.get("para_end")):
            flush()
        elif re.search(r"[,;:]$", w["w"]) and len(" ".join(x["w"] for x in cur)) > 48:
            flush()
    flush()
    return chunks


def voice_scene(sc):
    t0 = time.time()
    paras = [p.strip() for p in re.split(r"\n\s*\n", sc["text"].strip()) if p.strip()]
    pieces = [np.zeros(int(LEAD * SR), np.float32)]
    t = LEAD
    words, cues = [], {}
    pending = []
    for pi, para in enumerate(paras):
        segs = parse(" ".join(para.split()))
        text, spans = tts_text(segs)
        audio, toks, plain = synth_paragraph(text)
        pspans = plain_spans(text, spans)
        # time of each word segment from the tokens overlapping its char span
        wlist = []
        for sg, sp in zip(segs, pspans):
            if sg[0] == "cue":
                pending.append(sg[1])
                continue
            a, b = sp
            ov = [tk for tk in toks if tk[0] < b and tk[1] > a] if b > a else []
            if ov:
                ws, we = min(x[2] for x in ov), max(x[3] for x in ov)
            else:
                ws = we = None
            wlist.append({"w": sg[1], "spoken": sg[2], "start": ws, "end": we})
            for c in pending:
                cues[c] = ("word", len(words) + len(wlist) - 1)
            pending = []
        # fill words the model did not time (rare): interpolate between neighbours
        for i, w in enumerate(wlist):
            if w["start"] is None:
                prev = next((wlist[j]["end"] for j in range(i - 1, -1, -1) if wlist[j]["end"] is not None), 0.0)
                nxt = next((wlist[j]["start"] for j in range(i + 1, len(wlist)) if wlist[j]["start"] is not None), len(audio) / SR)
                w["start"], w["end"] = prev, max(prev, nxt)
        for w in wlist:
            w["start"] = round(t + w["start"], 3)
            w["end"] = round(t + w["end"], 3)
        if wlist:
            wlist[-1]["para_end"] = True
        words.extend(wlist)
        pieces.append(audio)
        t += len(audio) / SR
        if pi < len(paras) - 1:
            pieces.append(np.zeros(int(PARA_GAP * SR), np.float32))
            t += PARA_GAP
    for c in pending:  # cue at the very end
        cues[c] = ("time", t)
    pieces.append(np.zeros(int(TAIL * SR), np.float32))
    wav = np.concatenate(pieces)
    dur = len(wav) / SR
    cue_t = {}
    for name, (kind, v) in cues.items():
        cue_t[name] = round(words[v]["start"] if kind == "word" else v, 3)
    chunks = captions(words)
    for w in words:
        w.pop("para_end", None)
    os.makedirs(AUDIO, exist_ok=True)
    sf.write(os.path.join(AUDIO, f"{sc['id']}.wav"), wav, SR, subtype="PCM_16")
    meta = {"scene": sc["id"], "duration": round(dur, 3), "sr": SR, "voice": VOICE, "speed": SPEED,
            "words": words, "chunks": chunks, "cues": cue_t}
    with open(os.path.join(AUDIO, f"{sc['id']}.json"), "w") as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    print(f"{sc['id']}: {dur:6.1f} s, {len(words)} words, {len(chunks)} captions, "
          f"cues {list(cue_t)} ({time.time()-t0:.0f} s)", flush=True)
    return meta


def main(argv):
    want = set(argv)
    scenes = [s for s in SCRIPT.SCENES if not want or s["id"] in want]
    total = 0.0
    for sc in scenes:
        total += voice_scene(sc)["duration"]
    print(f"total {total/60:.2f} min")


if __name__ == "__main__":
    main(sys.argv[1:])
