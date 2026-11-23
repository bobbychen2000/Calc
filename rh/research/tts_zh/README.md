# Mandarin TTS evaluation (2026-11-22/23)

The first Mandarin narration used Kokoro-82M-v1.1-zh (voice `zf_003`), synthesised one clause at a
time with fixed gaps. It sounded choppy and not very natural. This folder records how a replacement was chosen.

## Constraints

- The machine: 4 CPU cores (Xeon, AVX-512 / AMX), 15 GB RAM, no GPU.
- Licence: the weights and terms must allow a public video. Non-commercial licences are out: Spark-TTS,
  F5-TTS, MaskGCT, ChatTTS, Fish-Speech / OpenAudio, Breeze TTS 2, OmniVoice, Higgs v3, Voxtral.
- Voice: a preset or designed voice, never a clone of a real person. That rules out zero-shot-only models
  without a licensed voice: CosyVoice 3, IndexTTS-2, GLM-TTS, LongCat, MegaTTS3. MegaTTS3 is also ByteDance's
  only open model; its encoder is withheld.
- Speed: synthesis no slower than about 8x real time.

## Shortlist and trial

A research round surveyed open and cloud models from primary sources, with an adversarial check of each
shortlisted model's licence, voices and CPU route.

Local trial models:
- Qwen3-TTS-12Hz 1.7B and 0.6B CustomVoice (Qwen, Apache-2.0; preset voices; the 1.7B also takes a style instruction).
- VoxCPM2 (OpenBMB, Apache-2.0; a voice designed from a text description, then held fixed as the reference).
- Ming-3.0-tts-0.5B (inclusionAI, MIT; built-in Chinese voices).

Method:
- Test set: `testset.json`, six passages from the script with names, English words, math words and
  polyphones (567 characters).
- Generators: `gen_*.py`, one model at a time (`queue.sh`). Two torch jobs at once on four cores slowed
  synthesis about 12x.
- Scoring (`eval_zh.py`):
  - Paraformer-zh ASR, giving the character error rate on the Chinese characters.
  - UTMOS22 (a naturalness predictor, trained mostly on English).
  - Meta Audiobox Aesthetics (CE / CU / PC / PQ).
  - Pace, pauses and pitch spread.
- The automatic scores are proxies; the final choice was made by listening.

Results (means over the six passages; speed is CPU seconds per second of audio, median):

| model / voice | char. error | UTMOS | Audiobox PQ | Audiobox CE | units/s | speed |
|---|---|---|---|---|---|---|
| Kokoro-82M-zh zf_003 (old pipeline) | 3.4 % | 3.13 | 7.69 | 5.97 | 3.77 | ~0.4x |
| **Qwen3-TTS 1.7B Serena + calm instruct** | 2.8 % | 3.73 | 7.85 | 6.06 | 3.95 | 3.9x |
| Qwen3-TTS 0.6B Serena | 2.6 % | 3.76 | 7.93 | 6.12 | 4.08 | 3.8x |
| VoxCPM2, designed female narrator | 2.6 % | 3.44 | 7.96 | 6.05 | 4.54 | 3.9x |
| Ming-3.0-tts 灵楷 (male) | 2.2 % | 3.41 | 7.44 | 5.77 | 4.45 | 3.5x |
| Ming-3.0-tts 灵朵儿 (female) | 4.1 % | 2.35 | 7.44 | 5.66 | 4.29 | 3.7x |
| Qwen3-TTS 1.7B Uncle_Fu + calm instruct | 3.7 % | 2.34 | 7.93 | 6.00 | 3.35 | 3.9x |

`scores_zh.json` holds the per-passage figures and transcripts. The 0.6B voice sweep (Serena, Vivian,
Uncle_Fu, Dylan, Eric) on two passages put Serena first. Dylan and Eric are dialect voices.

## Decision

Qwen3-TTS 1.7B CustomVoice, voice Serena, with the instruction "用平稳、清晰、温和的科普讲解语气，语速适中，娓娓道来。".
- Its scores are close to the 0.6B's, and it takes the style instruction.
- In bf16 on this CPU's AMX units it runs as fast as the 0.6B in fp32.

The narration pipeline changed with it (`voice_zh2.py`):
- **Sentences, not clauses.** A whole sentence is synthesised at a time, so the model shapes its intonation.
- **Quality gate.** Paraformer transcribes each take back, compared by toneless pinyin so homophones do
  not count. A take is redone with a new seed if a syllable is misread or the pace is off. An LLM TTS can
  stall, or run on to its length cap; a run-on is capped at 1.7x the expected length.
- **Alignment.** Captions and cues inside a sentence come from forced alignment (FunASR fa-zh).

## Cloud options (not used; need the user's account)

- **Doubao** (ByteDance Seed-TTS 2.0 / 3.0) through BytePlus.
  - A personal account with email, phone OTP and a card or PayPal, then an API key.
  - About US$0.25-0.45 per full pass, with a 20,000-character trial.
  - The China-site Volcengine contract licenses use only in mainland China.
- **Qwen cloud** (Alibaba Cloud Model Studio: qwen3-tts-flash, Qwen-Audio 3.1 TTS).
  - An international account and API key.
  - Well under US$1 per pass.
- MiniMax, Azure, Google and ElevenLabs were also reachable.

Every cloud route sends the script to a third party and needs a key supplied through the credential form.
