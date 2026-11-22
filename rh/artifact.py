"""Package the finished videos as a claude.ai Artifact: per language, one MP4 clip per chapter
(each well under the 15 MB limit for a file published beside a page; ~38 MB per language) with a
thumbnail each, and one player page that plays any chapter, joins them into the whole film, and
switches language.

    python3 artifact.py            # every language whose render exists -> out/web/
    python3 artifact.py en         # only the clips of one language (the page lists all built ones)

Each clip is a scene video (copied, not re-encoded) plus a sample-exact slice of the same
loudness-normalised narration as the full MP4 (48 kHz: 1,600 samples per video frame), so the
clips butt together exactly; every cut falls on a scene's fade to black with silence.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

import script

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "out", "web")
# language -> (audio dir, render output dir, prefix of its files in the artifact, script module)
LANGS = {
    "en": ("audio", "out", "", "script"),
    "zh": ("audio_zh", "out_zh", "zh/", "script_zh"),
}
OPENING = {"en": "Opening", "zh": "开场"}


def frames(audio_dir, sid):
    return math.ceil(sf.info(os.path.join(HERE, audio_dir, f"{sid}.wav")).frames / 800)


def build(lang):
    audio_dir, out_dir, prefix, mod = LANGS[lang]
    sc = __import__(mod)
    out = os.path.join(HERE, out_dir)
    web = os.path.join(WEB, prefix)
    os.makedirs(os.path.join(web, "video"), exist_ok=True)
    os.makedirs(os.path.join(web, "thumb"), exist_ok=True)
    ids = [s["id"] for s in sc.SCENES]
    titles = {s["id"]: (s["title"] or OPENING[lang]) for s in sc.SCENES}
    norm = os.path.join(out, "narration_48k.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(out, "narration_raw.wav"),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000", "-ac", "1", norm], check=True)
    audio, sr = sf.read(norm, dtype="float32")
    assert sr == 48000
    start_f, segs, chapters = 0, [], []
    for k, sid in enumerate(ids):
        n = frames(audio_dir, sid)
        sl = audio[start_f * 1600:(start_f + n) * 1600]
        if len(sl) < n * 1600:
            sl = np.concatenate([sl, np.zeros(n * 1600 - len(sl), np.float32)])
        wav = os.path.join(web, "tmp.wav")
        sf.write(wav, sl, 48000, subtype="PCM_16")
        clip = os.path.join(web, "video", f"{k + 1:02d}.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(out, "scenes", f"{sid}.mp4"),
                        "-i", wav, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart", "-shortest", clip], check=True)
        os.remove(wav)
        size = os.path.getsize(clip)
        assert size < 15_000_000, (clip, size)
        # thumbnail: the scene's settled final picture, after its last caption, before the fade-out
        meta = json.load(open(os.path.join(HERE, audio_dir, f"{sid}.json")))
        last_end = max(c["end"] for c in meta["chunks"]) + 0.32
        tt = (last_end + n / 30 - 0.5) / 2 if n / 30 - 0.5 > last_end else n / 30 - 0.6
        thumb = os.path.join(web, "thumb", f"{k + 1:02d}.jpg")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{tt:.3f}", "-i", clip, "-frames:v", "1",
                        "-vf", "scale=480:-2", "-q:v", "4", thumb], check=True)
        segs.append({"src": f"{prefix}video/{k + 1:02d}.mp4", "thumb": f"{prefix}thumb/{k + 1:02d}.jpg",
                     "start": round(start_f / 30, 4), "dur": round(n / 30, 4), "bytes": size})
        chapters.append({"t": round(start_f / 30, 4), "title": titles[sid]})
        print(f"{lang} clip {k + 1:02d}: {sid:14} {n / 30:7.2f} s  {size / 1e6:5.2f} MB")
        start_f += n
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2.6", "-i", os.path.join(out, "rh_explainer.mp4"),
                    "-frames:v", "1", "-q:v", "3", os.path.join(web, "poster.jpg")], check=True)
    info = {"segments": segs, "chapters": chapters, "total": round(start_f / 30, 4), "poster": f"{prefix}poster.jpg"}
    with open(os.path.join(web, "lang.json"), "w") as f:
        json.dump(info, f)
    return info


def main(argv):
    want = argv or [k for k, v in LANGS.items() if os.path.exists(os.path.join(HERE, v[1], "rh_explainer.mp4"))]
    for lang in want:
        build(lang)
    # the page lists every language built so far
    langs = {}
    for lang, (_, _, prefix, _) in LANGS.items():
        p = os.path.join(WEB, prefix, "lang.json")
        if os.path.exists(p):
            langs[lang] = json.load(open(p))
    data = {"default": "en", "langs": langs}
    with open(os.path.join(HERE, "web", "player.html")) as f:
        page = f.read()
    with open(os.path.join(WEB, "index.html"), "w") as f:
        f.write(page.replace("/*DATA*/null", json.dumps(data)))
    print("page languages:", list(langs))


if __name__ == "__main__":
    main(sys.argv[1:])
