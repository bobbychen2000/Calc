# Adversarial fact-check (2026-11-22)

Five independent reviewers checked the narration (`script.py`) and every on-screen string
(`scenes.py`) against the primary sources (`sources.md`), recomputed every number, and grepped every
Lean snippet against the archive. 99 issues were raised (23 major, 76 minor, no blockers); all
major ones and nearly all minor ones were applied. What changed, by theme:

## Scope and attribution (the claimed proof)
- **GRH scope.** The draft said "the wider generalized hypothesis that the note claims hasn't been
  checked". Wrong: the note claims "the so-called Generalized Riemann Hypothesis" (in standard usage,
  Dirichlet L-functions, which Sutherland's page reports as checked) and only *expects* the Extended RH
  "with more time". Now: certified = classical RH (Lean + Mathlib statement); reported by Sutherland's
  page = every Dirichlet L-function; not checked = other L-functions; the note only expects ERH.
- **The timeline** is "a rough timeline Claude provided" (the note), not "Alpöge's timeline".
- **The mechanism** (periods of chained theta lifts, divisibility growing with the chain, the X/m + m
  balance) is attributed to the note and to the *AI-assisted* guides that read the code (Jaswal,
  Rubinstein), never stated in the narrator's voice; the code itself has no declaration saying "the
  m-fold lift wins multiplicity m" (lean_archive.md §7).
- **"Local Langlands"** removed from the skeleton box: Jaswal's guide says the archive's map "is not the
  local Langlands correspondence" (its inputs are weaker than the published theorems).
- **Checkers**: Lean's own kernel and lean4lean checked module by module; nanoda, con-leche and con-ron
  the full export; Lean's kernel on the full export was still running at 04:35 UTC on 22 Nov.
  con-leche / con-ron's soundness proofs are "relative to set theory" (said aloud now).
- "no human has read" → "no human has read in full"; "not yet understood" → "not yet explained in human
  terms"; quotes made verbatim ("we have full confidence that Alpöge's proof of the Riemann Hypothesis is
  correct"); the statement is endorsed by the Lean FRO *and* the Mathlib Initiative; "depends directly
  only on Mathlib".

## Mathematics
- "exactly one smooth extension" was false (C∞ extensions are not unique): now "the one extension that
  stays complex-differentiable, its analytic continuation".
- s ↦ 1 − s is a point reflection; the left-right mirror of the zeros also needs ζ(s̄) = conj ζ(s).
- Each explicit-formula wave *grows like* x^Re ρ (its size is 2x^Re ρ/|ρ| per conjugate pair).
- Schoenfeld's bound is stated with its condition x ≥ 2657 in the narration too.
- Weil's general bound is 2g√p; "this bound is exactly its RH" is said for the genus-1 curve shown.
- Stepanov's method gives an error of order √p with a worse constant than Hasse's 2 (the schematic
  p/m + m no longer claims "2√p"); the auxiliary polynomial must be nonzero (the hard part).
- The polynomial ↔ integer dictionary: a prime factor ↔ a root, its power ↔ multiplicity, log size ↔ degree.
- The Euler product holds for s > 1; li(x) shown as 1.045… + ∫₂ˣ du/ln u (the bare ∫₀ˣ diverges at 1).
- Zero heights on screen are truncated (not rounded) before "…".
- Riemann's "roots are real" is glossed (roots t of ξ(t), s = ½ + it).

## Clarity for the viewer
- Definitions added: natural log, Mathlib, the functional equation, Dirichlet L-functions ("sort primes
  by remainder"), the two error terms in Stepanov's balance, why p + 1 is expected, why an upper bound
  on a prime sum rules out zeros (a louder wave would break it), x^(1/2 − ε) as "just under root x".
- The Euler-product step (expand each factor as a geometric series, multiply out) is narrated.

## Not applied (and why)
- Pronunciation of "Alpöge": no recording found; Wikipedia's unsourced American form (AL-poh-gay) is used.
- Length: the clarity additions put the narration at ~12 min (target ~10); the reviewers' additions were
  kept over a faster or terser read.
