# The Riemann Hypothesis and a claimed proof: a narrated explainer

A ~12½-minute 1920×1080 / 30 fps MP4 with burned-in captions: the zeta function, the Riemann
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
| `script_zh.py`, `i18n/` | the Mandarin version: the narration (same scene ids and cues), the on-screen strings (`i18n/zh.json`, exact strings + digit templates, applied by a `Text.set_text` hook in `render.py`) and the glossary they follow |
| `voice_zh2.py` | the Mandarin voice: Qwen3-TTS 1.7B CustomVoice, voice Serena → `audio_zh/<scene>.wav` + `.json` (same schema), one sentence at a time with an ASR quality gate and forced-aligned captions / cues; `research/tts_zh/` has the model evaluation |
| `voice_zh.py` | the first Mandarin voice (Kokoro-82M-v1.1-zh, clause by clause); its parser, caption merging and jieba word breaks are shared with `voice_zh2.py` |
| `artifact.py`, `web/player.html` | the interactive player (one clip per chapter, English / 中文 toggle) |
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

Mandarin: `RH_LANG=zh` switches `render.py` to `script_zh.py`, `audio_zh/` and `out_zh/` (Noto Sans
CJK SC; mathtext keeps STIX italics for symbols):

```bash
# Qwen3-TTS venv: uv pip install torch torchaudio (CPU wheels) qwen-tts funasr cn2an pypinyin jieba jiwer
~/venv-qwen/bin/python voice_zh2.py               # ~70 min on 4 CPU cores (weights: Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice)
RH_LANG=zh python3 render.py                      # -> out_zh/rh_explainer.mp4
python3 artifact.py en && python3 artifact.py zh  # -> out/web/ (index.html + clips per language)
```

## Voice

Kokoro-82M (Apache-2.0), voice `af_heart`, speed 1.0, through the PyTorch `KPipeline` (misaki G2P;
its duration predictor gives each word's start and end, which drive the captions and cues). It
replaced the earlier hand-built formant synthesizer. `research/tts_eval.md` compares it with the other
open models that run on a 4-core CPU: automatic MOS (UTMOS22) 4.52–4.54 for `af_heart` against
4.43–4.52 for Phonon-31m and 4.32–4.50 for Chatterbox, with the lowest ASR word error rate; neither
alternative met the switch rule (+0.3 MOS, no worse WER). Names the default G2P gets wrong are fixed
in `script.LEXICON` (misaki phonemes; Alpöge as Wikipedia's American "AL-poh-gay", unsourced there).

The Mandarin voice is Qwen3-TTS-12Hz-1.7B-CustomVoice (Qwen, Apache-2.0), preset voice Serena with
the instruction 用平稳、清晰、温和的科普讲解语气，语速适中，娓娓道来。 (bf16 on CPU, ~4x real time).
- It replaced Kokoro-82M-v1.1-zh after a trial of seven voices from four open models; the method and
  scores are in `research/tts_zh/README.md`.
- Each sentence is synthesised whole. Paraformer-zh transcribes every take back, and a take with a
  misread syllable (compared in toneless pinyin) or an implausible pace is redone with a new seed.
- FunASR's fa-zh forced aligner times the caption chunks and cues inside each sentence.
- Greek letters and symbols are written out for the voice (`[ζ|zeta]`), and Alpöge is read as in English.

## QA

`qa.py` (run in a venv with faster-whisper) transcribes each scene and compares the ASR word times
with `audio/<scene>.json` (caption / cue sync), the word error rate, and how each proper noun was
heard; `qa_zh.py` does the same for Mandarin (Whisper small, character alignment, CER).
`research/factcheck.md` records the adversarial fact-check of the script and on-screen text.
