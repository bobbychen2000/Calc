# The Riemann Hypothesis and a claimed proof: a narrated explainer

A ~11-minute 1920×1080 / 30 fps MP4 with burned-in captions: the zeta function, the Riemann
Hypothesis, why primes care, the function-field world where it is proved, and the idea and
construction of the proof that Levent Alpöge announced, working with Claude, on 20 November 2026
(a claimed proof; see `research/status.md` for exactly what has and has not been checked).

Everything is generated from code in this folder:

| file | what it does |
|---|---|
| `script.py` | the narration: 16 scenes, `[display|spoken]` markup, `{cue}` sync points, pronunciation lexicon |
| `voice.py` | Kokoro-82M neural TTS (PyTorch pipeline) → `audio/<scene>.wav` + `.json` (word times from the model's duration predictor, caption chunks, cue times) |
| `zeta.py` | the numbers: Euler–Maclaurin ζ, Hardy Z(t), 1,069 zeros to t = 1500 (checked against mpmath and Odlyzko's table), prime sieve to 10⁶, li(x), the explicit formula for ψ(x), point counts of the curve 37.a1 mod p → `data/` |
| `scenes.py` | one matplotlib renderer per scene, driven by the cue times |
| `render.py` | frames → ffmpeg (x264 crf 18, yuv420p) per scene, concat with `-c copy`, mux the narration (loudness-normalised AAC) |
| `research/` | source notes: the note, the Lean/Mathlib statement, Sutherland's verification page, the Lean archive itself, third-party guides, background facts |

## Run

```bash
pip install numpy scipy matplotlib pillow mpmath soundfile
python3 zeta.py                                   # ~15 s, asserts every number it saves

# TTS: Kokoro needs Python 3.12 (its numpy pin); a separate venv
uv venv -p 3.12 ~/venv-tts && . ~/venv-tts/bin/activate
uv pip install torch --index-url https://download.pytorch.org/whl/cpu
uv pip install kokoro "misaki[en]" soundfile
python voice.py                                   # ~4 min on 4 CPU cores; weights from hf.co/hexgrad/Kokoro-82M
deactivate

python3 render.py --test                          # sample frames per scene -> out/test/
python3 render.py                                 # all scenes -> out/rh_explainer.mp4
```

The voice is Kokoro-82M (Apache-2.0), voice `af_heart`, chosen over the earlier formant
synthesizer; names it mispronounces are fixed in `script.LEXICON` (misaki phonemes).
