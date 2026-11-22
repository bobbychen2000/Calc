"""Collect every on-screen string the scenes draw (for translation): render frames every
second and just after every cue with matplotlib's Text.set_text hooked, then drop captions,
chapter labels, pure numbers and tick labels.  Writes i18n/strings_en.json:
  {"exact": [...], "templates": [...]}   (templates: strings with changing digits, digits -> #)
"""
import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.text  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SEEN = set()
_orig = matplotlib.text.Text.set_text


def hooked(self, s):
    if s is not None:
        SEEN.add(str(s))
    return _orig(self, s)


matplotlib.text.Text.set_text = hooked

import render  # noqa: E402
import script  # noqa: E402


def main():
    import matplotlib.pyplot as plt
    skip = set()
    for s in script.SCENES:
        skip.add(s["title"])
        meta = render.load_meta(s["id"])
        for ch in meta["chunks"]:
            skip.add(ch["text"])
            skip.update(render.caption_lines(ch["text"]))
            skip.add("\n".join(render.caption_lines(ch["text"])))
    fig = render.new_fig()
    import scenes
    for sid, title, func in render.scene_table():
        meta = render.load_meta(sid)
        _, n = render.padded_audio(sid)
        ctx = render.Ctx(meta, n)
        ts = sorted(set([x * 1.0 for x in range(int(ctx.duration))] +
                        [v + d for v in meta["cues"].values() for d in (0.4, 1.0, 2.5, 4.0, 6.5)]))
        for t in ts:
            if t < ctx.duration:
                render.render_frame(fig, func, ctx, t, title)
        print(sid, len(SEEN), flush=True)
    plt.close(fig)
    out = set()
    for s in SEEN:
        s2 = s.strip()
        if not s2 or s2 in skip:
            continue
        if re.fullmatch(r"[\s\d.,−\-+$^{}\\a-zA-Z_()·×=]*", s2) and not re.search(r"[a-zA-Z]{3,}", s2):
            continue  # numbers, tick labels, bare symbols
        out.add(s)
    templ = {}
    for s in out:
        key = re.sub(r"\d[\d,]*(\.\d+)?", "#", s)
        templ.setdefault(key, []).append(s)
    exact = sorted(k for k, v in templ.items() if len(v) == 1 and "#" not in k or len(v) == 1)
    exact = sorted(v[0] for k, v in templ.items() if len(v) == 1)
    templates = sorted(k for k, v in templ.items() if len(v) > 1)
    os.makedirs(os.path.join(HERE, "i18n"), exist_ok=True)
    with open(os.path.join(HERE, "i18n", "strings_en.json"), "w") as f:
        json.dump({"exact": exact, "templates": templates}, f, indent=1, ensure_ascii=False)
    print(len(exact), "exact strings,", len(templates), "templates")


if __name__ == "__main__":
    main()
