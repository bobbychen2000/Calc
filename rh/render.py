"""Render the explainer: per-scene matplotlib frames piped to ffmpeg, then concat + mux.

    python3 render.py                 # all scenes -> out/rh_explainer.mp4
    python3 render.py --test          # test frames at a few times per scene -> out/test/*.png
    python3 render.py --scenes s03 s07 --jobs 2
    python3 render.py --frames s08:12.5,s14:30    # single frames

Each scene's narration (audio/<id>.wav, padded here to a whole number of frames: 800
samples at 24 kHz) fixes the scene's frame count, so audio and video stay in step
scene by scene; the cue times in audio/<id>.json drive the animation.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
AUDIO = os.path.join(HERE, "audio")
OUT = os.path.join(HERE, "out")
W, H, FPS, SR = 1920, 1080, 30, 24000
SPF = SR // FPS  # samples per frame

# ---------------------------------------------------------------------------------- style
PAL = {
    "bg": "#0d1117", "bg2": "#161b26", "panel": "#1b2230", "grid": "#2a3242",
    "text": "#e8e6e3", "muted": "#8b94a7", "faint": "#4b5468",
    "gold": "#f2b134", "cyan": "#4cc9f0", "coral": "#ff6b6b", "green": "#7bd88f",
    "violet": "#b392f0", "white": "#ffffff", "blue": "#5b8def", "orange": "#ff9e4a",
}
matplotlib.rcParams.update({
    "font.family": ["Inter", "DejaVu Sans"],
    "mathtext.fontset": "stix",
    "font.size": 28,
    "axes.facecolor": PAL["bg"], "figure.facecolor": PAL["bg"],
    "axes.edgecolor": PAL["faint"], "axes.labelcolor": PAL["muted"],
    "xtick.color": PAL["muted"], "ytick.color": PAL["muted"],
    "text.color": PAL["text"], "axes.linewidth": 1.5,
    "xtick.labelsize": 22, "ytick.labelsize": 22,
    "savefig.facecolor": PAL["bg"],
})
MONO = ["DejaVu Sans Mono", "DejaVu Sans", "STIXGeneral"]


# ---------------------------------------------------------------------------------- timing helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ramp(t, t0, dur=0.6):
    """0 before t0, smooth 0 -> 1 over dur."""
    if dur <= 0:
        return 1.0 if t >= t0 else 0.0
    return ease((t - t0) / dur)


def window(t, t0, t1, fade=0.5):
    """Fade in at t0, fade out at t1."""
    return ramp(t, t0, fade) * (1 - ramp(t, t1 - fade, fade))


class Ctx:
    """What a scene's draw function gets: time, cue times, the scene's narration meta."""

    def __init__(self, meta, n_frames):
        self.meta = meta
        self.cues = meta.get("cues", {})
        self.duration = n_frames / FPS
        self.n_frames = n_frames

    def cue(self, name, default=None):
        if name in self.cues:
            return self.cues[name]
        if default is not None:
            return default
        raise KeyError(f"cue {name!r} missing in scene {self.meta.get('scene')}")


# ---------------------------------------------------------------------------------- drawing helpers
def overlay(fig):
    """Full-frame axes in pixel coordinates (x 0..1920, y 0..1080, y up), drawn on top."""
    ax = fig.add_axes([0, 0, 1, 1], zorder=50)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    ax.patch.set_alpha(0)
    return ax


def caption_lines(text, max_chars=46):
    """Split a caption into at most two balanced lines."""
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    best, best_cost = None, 1e9
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        cost = abs(len(a) - len(b)) + (0 if len(a) <= 50 and len(b) <= 50 else 100)
        if cost < best_cost:
            best, best_cost = [a, b], cost
    return best


def draw_captions(ov, ctx, t):
    for ch in ctx.meta.get("chunks", []):
        t0, t1 = ch["start"] - 0.05, ch["end"] + 0.25
        if t0 <= t <= t1:
            lines = caption_lines(ch["text"])
            a = clamp((t - t0) / 0.12) * clamp((t1 - t) / 0.12)
            ov.text(W / 2, 52, "\n".join(lines), ha="center", va="bottom", fontsize=33,
                    color=PAL["white"], alpha=a, zorder=60, fontweight="medium", linespacing=1.25,
                    multialignment="center",
                    bbox=dict(boxstyle="round,pad=0.35,rounding_size=0.4", fc="#000000",
                              ec="none", alpha=0.62 * a))
            break


def chapter_label(ov, text, a=1.0):
    ov.text(60, H - 52, text, fontsize=22, color=PAL["muted"], alpha=a, ha="left", va="center",
            fontweight="medium")


def fade_overlay(ov, ctx, t, fin=0.35, fout=0.45):
    a = 1 - min(clamp(t / fin), clamp((ctx.duration - t) / fout))
    if a > 0.002:
        ov.add_patch(plt.Rectangle((0, 0), W, H, color="black", alpha=a, zorder=100))


# ---------------------------------------------------------------------------------- scene plumbing
def load_meta(sid):
    with open(os.path.join(AUDIO, f"{sid}.json")) as f:
        return json.load(f)


def padded_audio(sid):
    """The scene's narration padded with silence to a whole number of frames."""
    wav, sr = sf.read(os.path.join(AUDIO, f"{sid}.wav"), dtype="float32")
    assert sr == SR, sr
    n = int(math.ceil(len(wav) / SPF))
    out = np.zeros(n * SPF, np.float32)
    out[:len(wav)] = wav
    return out, n


def scene_table():
    import scenes  # noqa: F401  (registers SCENE_FUNCS)
    import script
    return [(s["id"], s.get("title", ""), scenes.SCENE_FUNCS[s["id"]]) for s in script.SCENES]


def new_fig():
    return plt.figure(figsize=(W / 100, H / 100), dpi=100)


def render_frame(fig, func, ctx, t, title):
    fig.clf()
    func(fig, ctx, t)
    ov = overlay(fig)
    if title:
        chapter_label(ov, title, a=ramp(t, 0.2, 0.6))
    draw_captions(ov, ctx, t)
    fade_overlay(ov, ctx, t)
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())
    assert buf.shape == (H, W, 4), buf.shape
    return buf


def render_scene(args):
    sid, title, func_name = args
    import scenes
    func = scenes.SCENE_FUNCS[sid]
    meta = load_meta(sid)
    _, n = padded_audio(sid)
    ctx = Ctx(meta, n)
    os.makedirs(os.path.join(OUT, "scenes"), exist_ok=True)
    path = os.path.join(OUT, "scenes", f"{sid}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-r", str(FPS), "-g", str(FPS * 4), "-movflags", "+faststart", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    fig = new_fig()
    t0 = time.time()
    for i in range(n):
        buf = render_frame(fig, func, ctx, i / FPS, title)
        proc.stdin.write(buf.tobytes())
    proc.stdin.close()
    rc = proc.wait()
    plt.close(fig)
    assert rc == 0, f"ffmpeg failed for {sid}"
    print(f"{sid}: {n} frames in {time.time()-t0:.0f} s ({n/(time.time()-t0):.1f} fps)", flush=True)
    return sid, n


def render_png(sid, title, t, path):
    import scenes
    func = scenes.SCENE_FUNCS[sid]
    meta = load_meta(sid)
    _, n = padded_audio(sid)
    ctx = Ctx(meta, n)
    fig = new_fig()
    buf = render_frame(fig, func, ctx, min(t, ctx.duration - 1 / FPS), title)
    plt.close(fig)
    from PIL import Image
    Image.fromarray(buf[:, :, :3]).save(path)


def assemble(sids):
    """Concat the scene videos (-c copy), join the padded narration, normalise its
    loudness, mux."""
    lst = os.path.join(OUT, "scenes", "list.txt")
    with open(lst, "w") as f:
        for sid in sids:
            f.write(f"file '{sid}.mp4'\n")
    video = os.path.join(OUT, "video_only.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", video], check=True)
    parts = []
    for sid in sids:
        a, n = padded_audio(sid)
        parts.append(a)
    wav = np.concatenate(parts)
    raw = os.path.join(OUT, "narration_raw.wav")
    sf.write(raw, wav, SR, subtype="PCM_16")
    final = os.path.join(OUT, "rh_explainer.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", raw,
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", final],
                   check=True)
    print("wrote", final, f"{len(wav)/SR/60:.2f} min")
    return final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--scenes", nargs="*")
    ap.add_argument("--frames", default=None)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2)))
    ap.add_argument("--no-assemble", action="store_true")
    a = ap.parse_args()
    table = scene_table()
    if a.scenes:
        table = [x for x in table if any(x[0].startswith(p) for p in a.scenes)]
    if a.frames:
        os.makedirs(os.path.join(OUT, "test"), exist_ok=True)
        for spec in a.frames.split(","):
            sid_p, ts = spec.split(":")
            for sid, title, _ in table:
                if sid.startswith(sid_p):
                    p = os.path.join(OUT, "test", f"{sid}_{float(ts):06.2f}.png")
                    render_png(sid, title, float(ts), p)
                    print(p)
        return
    if a.test:
        os.makedirs(os.path.join(OUT, "test"), exist_ok=True)
        for sid, title, _ in table:
            meta = load_meta(sid)
            d = padded_audio(sid)[1] / FPS
            ts = sorted(set([1.0] + [v + 0.8 for v in meta["cues"].values()] + [d - 1.2]))
            for t in ts:
                p = os.path.join(OUT, "test", f"{sid}_{t:06.2f}.png")
                render_png(sid, title, t, p)
            print(sid, len(ts), "frames")
        return
    jobs = [(sid, title, None) for sid, title, _ in table]
    # longest scenes first, for a balanced pool
    jobs.sort(key=lambda j: -padded_audio(j[0])[1])
    with Pool(a.jobs) as pool:
        for r in pool.imap_unordered(render_scene, jobs):
            pass
    if not a.no_assemble and not a.scenes:
        import script
        assemble([s["id"] for s in script.SCENES])


if __name__ == "__main__":
    main()
