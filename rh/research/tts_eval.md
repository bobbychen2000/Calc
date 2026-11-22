# TTS evaluation for the ~10-minute narration (CPU only, this container)

Date: 2026-11-22. Area: tts. Everything below was either measured in this container or quoted from the URL given.
Quotes are verbatim and short; markdown link syntax inside a quoted line has been dropped.

## Bottom line

**Keep Kokoro-82M, voice `af_heart`, speed 0.9.** Run it through the PyTorch `KPipeline` (misaki G2P) that
`voice.py` already uses, and add two lexicon entries: `"Riemann": "ɹˈimɑn"` and `"Alpöge": "ˈælpOɡA"`.

* **No alternative met the switch rule** (UTMOS at least +0.3 with no worse WER). On the same texts the best
  alternatives scored *equal or lower* UTMOS than `af_heart`, and their word error rates were *higher*:
  * `af_heart` scored UTMOS 4.52-4.54 on every text. Its WER (small.en) was 0.015-0.031, and the errors were names.
  * Phonon-31m (Apache-2.0, released Oct 2026) scored UTMOS 4.43-4.52 with WER 0.034-0.108. It runs about 2x
    faster than Kokoro, but it drops or merges the single-letter variables the script relies on: "let s be" came out
    as "Let's be", "Write s as" as "Writes as", and "n" as "NIN".
  * Chatterbox (MIT, 0.5B) scored UTMOS 4.32-4.50 with WER 0.010-0.123. It needs 3.6-5.4 s of compute per second of
    audio and about 6.8 GB of RAM, and its maker has archived it.
* **The human-preference evidence points the other way, mildly.** A public benchmark trained on blind votes ranks
  Chatterbox (88) and Phonon-31m (85) above Kokoro (81). Phonon's own Elo table gives 2098 against 2043. UTMOS
  cannot see that gap, and nobody can listen here, so the measured evidence does not justify a switch. The
  "Alternatives" section has install code in case a human listener prefers one of them.
* **Why speed 0.9.** At speed 1.0, `af_heart` reads the script's real passages at 174-181 words per minute. Explainer
  guidance gives about 150 wpm as the baseline and 120-150 wpm for complex vocabulary. Speed 0.9 gives 162-169 wpm,
  with the same UTMOS (4.527-4.540) and WER. The narration gets about 7-10 % longer.
* **Pronunciation can be forced.** In the misaki pipeline use `[word](/phonemes/)`. In kokoro-onnx use
  `create(phonemes, is_phonemes=True)`. A phoneme recogniser confirmed both routes; see section 3.

## 1. Survey (late 2026): open TTS models and whether they fit

Main secondary source: **TTS Bench** (https://5uck1ess.github.io/tts-bench/), which tests 99 open models on the
same prompts and publishes speed, objective scores, licences and CPU support.
* Its definition of NAQ: "NAQ (default voice) = how natural it sounds to people: the chance, 0–100, that a listener
  picks this model over a typical bench model in a blind A/B." (scores.html)
* Its warning about UTMOS: "UTMOS = predicted naturalness, mostly how clean the audio is (higher better)". (scores.html)
* CPU speeds below are its Linux rig: "AMD Ryzen 9 5900XT 16-Core Processor" (linux-default/speed.html). RTFx means
  how many times faster than real time; higher is better.

| Model (size) | Licence (source) | Fits a published video? | CPU speed, TTS Bench RTFx (16-core) | NAQ / UTMOS / WER (TTS Bench, default voice) | Verdict here |
|---|---|---|---|---|---|
| **Kokoro-82M** (82M) | Apache-2.0: "This is an Apache-licensed model, and Kokoro has been deployed in numerous projects and commercial APIs." (hf.co/hexgrad/Kokoro-82M) | yes | 6.96x | 81 / 4.177 / 0.054 | baseline, **recommended** |
| **Phonon-31m-en** (31M + Mimi; q8 64.5 MB) | Apache-2.0: card YAML "license: apache-2.0"; "allows commercial use" (hf.co/gradium/phonon-31m-en) | yes | 8.35x | 85 / 4.424 / 0.073 | tested |
| Phonon-40m-en | CC BY-NC 4.0 (same card's family table) | non-commercial only | 6.97x | 86 / 4.252 / 0.079 | excluded (NC) |
| **Chatterbox** (0.5B Llama backbone) | MIT: "Licensed under MIT" (hf.co/ResembleAI/chatterbox); outputs carry a Perth watermark, "imperceptible neural watermarks that survive MP3 compression" | yes | 0.37x | 88 / 4.423 / 0.061 | tested |
| Chatterbox Turbo (744M) | MIT (TTS Bench capabilities) | yes | 0.69x | 77 / 4.274 / 0.074 | not tested (NAQ below Kokoro) |
| Chatterbox Nano (110M) | MIT; vendor: "3x realtime on CPU using 8 threads" (resemble.ai post below) | yes | not benchmarked | not benchmarked | not tested: the HF repo is gated (search-result title for hf.co/ResembleAI/chatterbox-nano: "You need to agree to share your contact information to access this model") |
| Pocket TTS (Kyutai, 100M) | Apache-2.0 (TTS Bench); README: "Faster than real-time, ~6x real-time on a CPU of MacBook Air M4" | yes; voice licences per voice | 4.01x | 65 / 3.991 / 0.070 | not tested (NAQ well below Kokoro) |
| Supertonic 3 (99M, ONNX) | "license: openrail" (hf.co/Supertone/supertonic-3); TTS Bench "MIT + OpenRAIL-M" | yes, with use restrictions | 5.89x | 71 / 4.080 / 0.054 | not tested |
| Soprano 1.1 (80M) | apache-2.0 (card) | yes | 3.01x | 63 / 4.116 / 0.059 | not tested |
| KittenTTS Nano 0.8 (15M) | apache-2.0 (card) | yes | 21.48x | 49 / 4.167 / 0.044 | not tested (NAQ low) |
| KittenTTS 2 (1.7B) | Stellon Labs Community: "the commercial grant ends once you or your affiliates pass USD $1,000,000 in annual revenue" (hf.co/KittenML/kitten-tts-2) | conditional | 0.30x | 46 / 4.289 / 0.035 | no |
| NeuTTS Air / Nano | Apache-2.0 (TTS Bench); HF card gated | yes | Air 2.16x, Nano 3.10x (Mac CPU) | cloning-only rows | not tested (cloning model, needs a reference voice) |
| StyleTTS 2 | MIT (TTS Bench) | yes | 3.82x (Mac CPU) | 47 / 4.259 / 0.158 | no |
| Piper | GPL-3.0 (TTS Bench) | yes, GPL code | 37.14x | 26 / 3.877 / 0.055 | no (quality) |
| XTTS-v2 | "This model is licensed under Coqui Public Model License" (hf.co/coqui/XTTS-v2); TTS Bench "CPML (non-commercial)" | **no** | 1.43x (Mac CPU) | 38 / 3.936 / 0.054 | excluded |
| F5-TTS | "license: cc-by-nc-4.0" (hf.co/SWivid/F5-TTS) | **no** | 0.09x (Mac CPU) | — | excluded |
| Fish Speech S2-Pro / OpenAudio | "Research and non-commercial use is permitted free of charge." (hf.co/fishaudio/s2-pro) | **no** | no CPU | — | excluded |
| Spark-TTS 0.5B | "license: cc-by-nc-sa-4.0" (hf.co/SparkAudio/Spark-TTS-0.5B) | **no** | — | — | excluded |
| Higgs Audio v3 (4B) | research / non-commercial, plus a "Creator Use Grant" covering "creative content for free — including monetized content" (hf.co/bosonai/higgs-audio-v3-tts-4b) | possibly, via the creator grant | no CPU support (TTS Bench) | 69 / 4.372 / 0.065 | no (4B, GPU) |
| IndexTTS-2 (1.5B) | "bilibili Model License" (TTS Bench; not read on the card) | unverified | 0.14x (Mac CPU) | cloning-only rows | no |
| Orpheus 3B | Apache-2.0 (TTS Bench; HF card gated) | yes | no CPU (TTS Bench) | 69 / 4.005 / 0.102 | no (3B) |
| Dia 1.6B | "license: apache-2.0" (card) | yes | no CPU (TTS Bench) | 28 / 2.387 / 0.317 | no |
| VibeVoice Realtime 0.5B | MIT, but "The VibeVoice-Realtime model is limited to research purposes" (hf.co/microsoft/VibeVoice-Realtime-0.5B) | doubtful | 0.36x (Mac CPU) | 57 / 4.043 / 0.148 | no |
| Kyutai TTS 1.6B | "license: cc-by-4.0" (hf.co/kyutai/tts-1.6b-en_fr) | yes, with attribution | not in the CPU tables | — | no (1.6-1.8B) |
| CosyVoice 3 0.5B | "license: apache-2.0" (card) | yes | no CPU (TTS Bench) | cloning-only rows | no |
| Qwen3-TTS 0.6B CustomVoice | Apache-2.0 (TTS Bench) | yes | 1.7B Base 0.24x (Mac CPU) | 60 / 4.268 / 0.110 | no (NAQ below Kokoro) |

The only permissively licensed local models with a higher NAQ than Kokoro are **Chatterbox (88)** and **Phonon-31m
(85)**. Underdog Woof (NAQ 71, UTMOS 4.442) is non-commercial ("Underdog Non-Commercial 1.0").

Other evidence:
* **Phonon card Elo table** (English US, "Elo from 468 raters, 8,290 votes"): "phonon-31m-en | 2098 | 1.5% | 0.51%"
  against "Kokoro | 2043 | 3.5% | 0.45%". The columns are Elo, hard-set LLM WER and Seed-TTS LLM WER. This is the
  vendor's own test.
* **Chatterbox status**: "As of August 2026, Chatterbox and Dramabox are retired commercially, but remain open
  source research." The code stays online "as an archive, with no support, updates, or paid tier."
  (https://www.resemble.ai/resources/chatterbox-nano-and-flash-speed-at-the-edge-throughput-at-scale)
* **Kokoro has no newer model.** I found no Kokoro release after v1.0. The model card's "Releases" table lists only
  "v1.0 | 2025 Jan 27" and the older v0.19 (2024 Dec 25) (hf.co/hexgrad/Kokoro-82M, read on the card).
* **A third-party 4-core CPU benchmark** (Xeon 8272CL, "CPU Cores | 4", "RAM | 15.6 GB", close to this machine)
  reports "Kokoro-82M (ONNX) | 0.6415 | 1.6× faster than real-time | 4.44", where 4.44 is UTMOS.
  (https://cdn.jsdelivr.net/gh/gauravvij/kokoro-tts-vs-supertonic-3-tts@main/results/benchmark_report.md)

## 2. Measurements in this container

### Method

**Machine.** 4 CPU cores, 15 GB RAM, no GPU. The machine was **shared**: another session was rendering video
(`render.py` + ffmpeg), and my own jobs overlapped. The 1-minute load average was logged with each run and ranged
from 1.3 to 6.3. Wall-clock RTF (seconds of compute per second of audio) is therefore an upper bound, and Chatterbox
in particular slowed 3-4x under load.

**Texts.**
* Test sentences A, B and C, exactly as given.
* Two real script passages, the spoken text of scenes `s01_open` (L1, 101 words) and `s04_complex` (L2, 100 words),
  to test long-form behaviour and the single-letter variables.

**Settings.**
* Kokoro, both runtimes: speed 1.0 unless stated.
* Phonon: default temperature 0.3 and the fixed default seed.
* Chatterbox: built-in voice, `exaggeration=0.5, cfg_weight=0.5`, plus a "narr" setting of 0.4 / 0.3. The long
  passages were synthesised sentence by sentence with 0.25 s gaps, since one call stops at 1000 speech tokens.

**Metrics.**
* **UTMOS22-strong**: the ONNX export `TigreGotico/utmos-onnx`, on 16 kHz input. Its card says it was "Verified
  against a fresh torch.hub load of the unpatched model on 21 cases", with "Max absolute MOS deviation: 6.20e-06."
  I used the ONNX export because torch.hub fetches from github.com.
* **WER**: faster-whisper `small.en`, CPU int8, beam 5, no prompt. `medium.en` was run as a second opinion on the
  main systems. Before scoring, digits were turned into words, case and punctuation were removed, and "non-trivial"
  was matched to "nontrivial".
* The proper names (Levent, Alpöge) count as errors whenever Whisper spells them differently. Every Kokoro or
  Phonon error on sentence C is such a name.

**Words per minute** were computed on the long passages from the generated audio, including the model's own pauses.

### Short sentences A + B + C (pooled)

| System | UTMOS mean [min] | WER small.en | WER medium.en | RTF wall (load) |
|---|---|---|---|---|
| Kokoro-onnx `af_heart` | **4.519** [4.516] | 0.015 | 0.015 | 0.23-0.50 (0.7-2) |
| Kokoro KPipeline `af_heart` | **4.532** [4.528] | 0.031 | 0.031 | 0.24 (1.3) |
| Kokoro-onnx `am_fenrir` | 4.491 [4.480] | 0.015 | 0.015 | 0.60 (load ~4) |
| Kokoro-onnx `am_michael` | 4.370 [4.317] | 0.031 | — | 0.57 |
| Kokoro-onnx `bf_emma` | 4.370 [4.309] | 0.015 | — | 0.58 |
| Kokoro-onnx `af_bella` | 4.352 [4.334] | 0.015 | — | 0.58 |
| Kokoro-onnx `bm_george` | 4.281 [4.246] | 0.015 | — | 0.53 |
| Phonon-31m Zoey | 4.518 [4.512] | 0.092 | 0.092 | 0.13 (1.8) |
| Phonon-31m Harper | 4.515 [4.502] | 0.108 | 0.062 | 0.12 |
| Phonon-31m Trevor / Easton / Micah / Juniper / Maeve / Hugh | 4.43-4.49 | 0.062-0.108 | — | 0.12-0.14 |
| Chatterbox default | 4.459 [4.424] | 0.062 | 0.031 | 5.40 (2.2-3.5) |
| Chatterbox narr (0.4 / 0.3) | 4.504 [4.495] | 0.123 | — | 15.5 (load ~6) |

### Long passages L1 + L2 (real script text)

| System | UTMOS mean [min] | WER small.en | WER medium.en | RTF wall | CPU-s per s of audio | wpm |
|---|---|---|---|---|---|---|
| Kokoro-onnx `af_heart` 1.0 | 4.530 [4.521] | 0.020 | 0.029 | 0.22 (load ~4.5) | 0.84 | 174 |
| Kokoro-onnx `af_heart` 0.95 | 4.532 [4.529] | 0.020 | — | 0.22 | 0.83 | 169 |
| **Kokoro-onnx `af_heart` 0.9** | **4.540** [4.536] | 0.015 | — | 0.22 | 0.84 | **162** |
| Kokoro-onnx `af_heart` 1.1 | 4.524 [4.521] | 0.025 | — | 0.24 | 0.89 | 183 |
| Kokoro KPipeline `af_heart` 1.0 | 4.529 [4.528] | 0.029 | 0.020 | 0.31 (load ~2) | 1.12 | 181 |
| **Kokoro KPipeline `af_heart` 0.9** | 4.527 [4.515] | 0.034 | — | 1.76 (heavy load, see note) | 3.49 | **169** |
| Kokoro-onnx `am_fenrir` / `am_michael` / `bm_george` | 4.489 / 4.372 / 4.181 | 0.015 / 0.034 / 0.020 | — | 0.21-0.22 | 0.81-0.85 | 186 / 159 / 167 |
| Phonon-31m Zoey | 4.514 [4.514] | 0.034 | 0.034 | 0.13 | 0.43 | 180 |
| Phonon-31m Harper | 4.507 [4.493] | 0.039 | 0.039 | 0.14 | 0.47 | 178 |
| Phonon-31m Easton | 4.443 [4.391] | 0.034 | — | 0.12 | 0.42 | 192 |
| Phonon-31m, L2 with letters respelled ("ess", "en", "tee", "eye tee") | Zoey 4.521 / Harper 4.490 / Easton 4.177 | 0.040 / 0.000 / 0.000 | — | 0.12-0.14 | 0.41-0.46 | 189-203 |
| Chatterbox default (sentence by sentence) | 4.323 [4.274] | 0.010 | 0.025 | 3.72 (load ~3.9) | 14.6 | 190 |

**Note on KPipeline at 0.9 / 0.95.** These were generated at 04:3x UTC, with load 4-5 from other sessions. The same
pipeline measured RTF 0.24-0.31 at load 1.3-2.2, and speed hardly changes the cost per second of audio (kokoro-onnx:
0.22 at every speed).

### Time to synthesise 10 minutes of narration (600 s of audio)

* **Kokoro.** RTF 0.22-0.31 at light to moderate load, so **about 2.2-3.1 min**. Under the heaviest load seen, RTF
  reached 1.8, so up to about 18 min.
* **Phonon-31m.** RTF 0.12-0.14, so **about 1.3 min**.
* **Chatterbox.** RTF 3.6-5.4 at load 2-4, so **about 36-54 min**, within the 90-minute limit. At load ~6 its RTF was
  10-23, so 100-230 min.

**Peak RAM:** kokoro-onnx 0.65 GB, Phonon 0.44 GB, Chatterbox 6.75 GB.

**Install size:**
* Kokoro: ONNX model 326 MB + voices 28 MB. The torch weights are 313 MB, plus the torch venv.
* Phonon: the `ptts` wheel is 7.5 MB with numpy as its only dependency; the PyPI summary reads "No PyTorch". The
  model is 63 MB.
* Chatterbox: 3.0 GB of weights plus a 1.6 GB venv, which pins torch 2.6.0 and transformers 5.2.0 and needs
  `setuptools<80` for the watermarker.

### Notes per system (artifacts and mispronunciations heard by the ASR)

**Kokoro-onnx (espeak G2P)**
* "phasors" comes out as "facers" or "fasces" with both ASR models. The package's espeak G2P gives `fˈæsɚz`, while
  misaki gives `fˈAzəɹz`, and the KPipeline audio is transcribed "phasors".
* "Alpöge" comes out as "Alperge" or "Alperj". The espeak phonemes are `ˈælpɜːdʒ`, roughly "AL-purj".
* "Levent" is read with stress on the first syllable (`lˈɛvɛnt`), which ASR sometimes writes "Leven" or "Levin".
* With an en-gb voice, `zeta` becomes `zˈiːtə` (ZEE-tuh). That is correct British, but it differs from the American
  voices' ZAY-tuh.
* Single-letter variables are read as letter names (`ˈɛs`, `ˈɛn`, `ˈaɪ tˈiː`) and survive ASR.

**Kokoro KPipeline (misaki G2P, the current `voice.py`)**
* "phasors" is correct.
* "Alpöge" is misread (`ˈælpɜɹʤ`) unless overridden.
* "let s be" is transcribed "Let us be" or "Let S be". That is ambiguous on paper; the phonemes are `lˈɛt ˈɛs bˈi`.
* "Claude" is once transcribed "clawed", a homophone, so not an error.

**Phonon-31m (no phoneme input)**
* Single letters get lost, systematically:
  * "a complex number s" → "complex numbers"
  * "to the power s" → "powers" or "power says"
  * "n" → "NIN"
  * L2: "Let's be", "Writes as"
* Respelling the letters fixes the WER for Harper and Easton. Easton's UTMOS then drops to 4.18, and Zoey reads "en"
  as "into".
* "Lean" is transcribed "lien" in 4 of 8 voices and "Liam" once.
* "Alpöge" is heard as "Alpoj" or "Alpoge". Respelling it "Leh-vent Al-poh-gay" works ("Levent Alpogay").

**Chatterbox**
* Fluent, and it read the L2 variables correctly.
* It dropped the letter in "complex number s" (sentence A) with both ASR models.
* Every rendering of "Alpöge" was wrong: "Alpege", "Elphage", "Alfage", and "Levant al-Fagay" with the narr
  setting.
* Its long-form UTMOS was lower (4.27-4.37), from joining sentence-level outputs.
* Every output carries the Perth watermark.

Wavs (139 files) are in `/home/user/rhwork/tts_eval/`. Raw per-file scores are in `scores.json`, the summaries in
`summary_small.en.json` and `summary_medium.en.json`, and the scripts in `/home/user/rhwork/tts_eval/scripts/`.

## 3. Kokoro pronunciation control

**kokoro-onnx 0.6.1**, read from the installed source (`site-packages/kokoro_onnx/__init__.py`, `tokenizer.py`):
* `create(text, voice, speed=1.0, lang="en-us", is_phonemes=False, trim=True, sentence_pause=0.25,
  clause_pause=0.1, continuous=False)`. With `is_phonemes=True` the string is used as-is
  (`phonemes = text if is_phonemes else self.tokenizer.phonemize(text, lang)`). It is then split into batches of at
  most 510 phonemes.
* Its own G2P is **espeak-ng** through `phonemizer`, called with `preserve_punctuation=True, with_stress=True`. The
  output is IPA with length marks and two-character diphthongs (`eɪ`, `oʊ`, `dʒ`).
* Tokenisation keeps one token per character in the model's 114-symbol vocabulary and **silently drops anything
  else** ("Map phonemes to token ids, dropping anything outside the vocabulary").
* That vocabulary contains both IPA and misaki's single-letter diphthongs: `A`=eɪ, `I`=aɪ, `O`=oʊ, `W`=aʊ, `Y`=ɔɪ,
  plus `ʤ`, `ʧ` and `ᵊ`. Espeak-style strings and misaki-style strings both work; tested below.

**Kokoro KPipeline (kokoro 0.9.4 + misaki 0.9.4)**
* Uses misaki's US alphabet `AIOWYbdfhijklmnpstuvwzæðŋɑɔəɛɜɡɪɹɾʃʊʌʒʔʤʧˈˌθᵊᵻ` (`misaki.en.US_VOCAB`), with no
  length marks.
* Overrides are inline: `[Alpöge](/ˈælpOɡA/)`. `voice.py` already does this from `script.LEXICON`.

**Target pronunciations, checked on Wikipedia (raw wikitext):**
* Riemann `{{IPAc-en|ˈ|r|iː|m|ɑː|n|,_|-|m|@|n}}`, i.e. REE-mahn, also -mən.
* Zeta `{{IPAc-en|UK|'|z|iː|t|ə}}`, `{{IPAc-en|US|'|z|eɪ|t|ə`.
* Euler `{{IPAc-en|ˈ|ɔɪ|l|ər}} {{respell|OY|lər}}`.
* Alpöge `{{IPA|tr|alpøˈɟe}} {{respell|ahl|pur|GYEH}}; American English: {{IPAc-en|ˈ|æ|l|p|oʊ|ɡ|eɪ}}
  {{respell|AL|poh|gay}}`. This Wikipedia IPA carries no citation; see `research/math_facts.md` section 17.

**Round trip.** Each variant was synthesised in a carrier sentence and played into the phoneme recogniser
`facebook/wav2vec2-lv-60-espeak-cv-ft`, which is "fine-tuned on CommonVoice to recognize phonetic labels in multiple
languages" (Apache-2.0), and into Whisper small.en. Stress marks are dropped in the "heard" column.

| Word | Phoneme string to use | Default G2P gives | Phones heard (af_heart; am_michael, bm_george agree) | Whisper |
|---|---|---|---|---|
| Riemann (REE-mahn) | kokoro-onnx `ɹˈiːmɑːn` · misaki `ɹˈimɑn` | espeak `ɹˈiːmən`, misaki `ɹˈimən` (REE-mən) | default `ɹiːmən`; both overrides `ɹiːmɑːn` ✔ | "Riemann" in every case |
| zeta (ZAY-tuh) | kokoro-onnx `zˈeɪtə` · misaki `zˈAtə` (= misaki default) | espeak en-us `zˈeɪɾə`, en-gb `zˈiːtə` | US voices `zeɪɾɐ` (American flap); bm_george default `ziːɾɚ` → override `zeɪɾɚ` ✔ | "zeta" |
| Euler (OY-ler) | kokoro-onnx `ˈɔɪlɚ` · misaki `ˈYləɹ` (= both defaults; en-gb gives `ˈɔɪlə`) | already right | `oːɹlɚ` / `oɪlɚ` for every variant (the recogniser's rendering of ɔɪ) | "Euler" in every case |
| Alpöge (AL-poh-gay) | kokoro-onnx `ˈælpoʊɡeɪ` · misaki `ˈælpOɡA` | espeak `ˈælpɜːdʒ`, misaki `ˈælpɜɹʤ` (AL-purj) ✘ | default `aʊlpɚdʒ`; override `aʊlpoʊɡeɪ` / `alpoʊɡeɪ` / `ælpoʊɡeɪ` ✔ | default "Alperj / Alperge"; override "Alpoghe", "Alpogé", "Alpogay", "Alpoguet" |
| Alpöge, Turkish-like | `ɑlpœɟˈe` | — | `ɑːlpᵻdʒe` / `aʊlpədʒe`: the ɟ becomes dʒ | "Alpijay", "Alpaje" (not recommended) |
| Levent (leh-VENT) | kokoro-onnx / misaki `lɛvˈɛnt` (already in `script.LEXICON`) | `lˈɛvɛnt` | — | default often "Leven / Levin"; with the override "Levent" |

**Full-sentence check with the overrides.**
* kokoro-onnx: sentence C → "In November 2026, Levent Alpogay announced a claimed proof, written with Claude and
  checked in the Lean Proof Assistant." UTMOS 4.528, unchanged.
* KPipeline: "Levent Alpoguet …" (medium.en), UTMOS 4.538.
* Sentence A with the Riemann override: WER 0.000 in both pipelines.

**Working code for kokoro-onnx.** Phonemize the whole sentence, then splice in the replacements. Phonemizing word by
word breaks function words: an isolated "a" becomes the letter name `ˈeɪ`.

```python
from kokoro_onnx import Kokoro
k = Kokoro('/home/user/rhwork/models/kokoro-v1.0.onnx', '/home/user/rhwork/models/voices-v1.0.bin')
OVR = {'Riemann': 'ɹˈiːmɑːn', 'zeta': 'zˈeɪtə', 'Levent': 'lɛvˈɛnt', 'Alpöge': 'ˈælpoʊɡeɪ'}
def phon(text, lang='en-us'):
    p = k.tokenizer.phonemize(text, lang)
    for w, custom in OVR.items():
        if w in text:
            p = p.replace(k.tokenizer.phonemize(w, lang), custom)
    return p
samples, sr = k.create(phon(text), voice='af_heart', speed=0.9, is_phonemes=True)
```

**For `voice.py` (KPipeline).** Add the following to `script.LEXICON`. `Levent` is already there. Euler and zeta are
right by default in misaki.

```python
"Riemann": "ɹˈimɑn",
"Alpöge": "ˈælpOɡA",
```

## 4. Recommendation

**Model, voice and speed:** Kokoro-82M (Apache-2.0), voice `af_heart`, **speed 0.9** (`RH_SPEED=0.9 python voice.py`).
Keep the misaki `KPipeline` route, because it pronounces "phasors" correctly and kokoro-onnx's espeak route does not.

**Evidence that `af_heart` is the right voice:**
* Highest or tied-highest UTMOS of every configuration tested here, at 4.52-4.54 on every text. Phonon Zoey came
  within 0.02.
* WER 0.015-0.034, with no errors outside the names except a "let s" / "let us" ambiguity. Chatterbox's long-form
  WER of 0.010 was lower, but its short-sentence WER of 0.062 was higher.
* Kokoro's own voice table grades `af_heart` "A". The other voices tested grade lower: `af_bella` A-, `bf_emma` B-,
  `am_fenrir` and `am_michael` C+, `bm_george` C (hf.co/hexgrad/Kokoro-82M VOICES.md).
* If a male voice is wanted, `am_fenrir` measured best (UTMOS 4.49).

**Evidence for speed 0.9:**
* It brings the long passages from 174-181 wpm down to 162-169 wpm, with no UTMOS or WER cost.
* Guidance: "A read around 150 words per minute is a strong baseline for general explainer content"
  (https://www.capcut.com/create/ai-voiceovers-natural-explainer-videos).
* Guidance: "If you use complex words with more syllables, stick to 120-150 wpm."
  (https://biteable.com/blog/video-word-count/)
* Cost: about 7-10 % longer audio (L1: 36.8 s → 39.4 s).
* If the 10-minute budget is tight, 1.0 is equally clean.

**Switch rule not met.** No alternative reached UTMOS +0.3 with no worse WER. The two best alternatives were within
±0.02 UTMOS of `af_heart` and had worse WER on this script's single-letter variables. If a human listener
nevertheless prefers one of them:

```bash
# Phonon-31m (Apache-2.0): ~1.3 min per 10 min of audio here. Respell single letters ("ess", "en") and names.
uv pip install ptts            # 7.5 MB wheel, numpy only; weights hf://gradium/phonon-31m-en (63 MB) on first use
python -c "import ptts; t=ptts.TTS('hf://gradium/phonon-31m-en', lang='en', quant='q8'); t.save('x.wav', 'Hello.', voice='Zoey')"
# Chatterbox (MIT, archived, watermarked): ~36-54 min per 10 min of audio here, 6.8 GB RAM.
uv venv -p 3.12 venv-cbx && uv pip install --python venv-cbx/bin/python chatterbox-tts "setuptools<80" \
   --extra-index-url https://download.pytorch.org/whl/cpu --index-strategy unsafe-best-match
# from chatterbox.tts import ChatterboxTTS; m = ChatterboxTTS.from_pretrained(device="cpu")
# wav = m.generate(sentence, exaggeration=0.5, cfg_weight=0.5)   # one sentence per call; join with short gaps
```

## Not verified / caveats

* **UTMOS saturates.** It sits at 4.4-4.54 for every good system here, and TTS Bench says it mostly measures
  cleanliness. Prosody and expressiveness, where Chatterbox and Phonon may beat Kokoro by human vote, were not
  measured.
* **No one listened** to any file.
* **Timings are noisy.** The machine was shared, with load averages up to 6.3, so treat RTF as an upper bound.
* **Sample size is small:** 3 sentences + 2 passages per system, with one seed for the stochastic models (Phonon
  temperature 0.3, Chatterbox seed 1234).
* **How Alpöge says his own name is unknown.** The American "AL-poh-gay" is the unsourced Wikipedia IPA. Nothing
  else was found; see `research/math_facts.md` section 17.
* **Several entries rest on TTS Bench alone** because the cards are gated or did not state them: the NeuTTS, Orpheus
  and Pocket TTS licences, and the IndexTTS-2 licence.
* **Not run:** Chatterbox Nano (gated repo), Pocket TTS and Supertonic, the last two because their published NAQ is
  well below Kokoro's.
