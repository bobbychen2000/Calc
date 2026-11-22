# Third-party guides to the structure of Alpöge's claimed RH proof

Research notes for the explainer video. Compiled 2026-11-22 (UTC). Area: **guides**.

Rules followed: every claim below has a URL and a short verbatim quote. Items marked **[measured here]** are my own
read-only measurements of the published archive (downloaded, hashed, streamed through `tarfile`, never extracted,
built or executed; scripts in the session scratchpad). Items marked **[unverified]** come from a single secondary source,
or from a search-engine snippet of a page I could not open. Downloaded copies: `/home/user/rhwork/sources/guides/`.

---

## 1. Summary

* At least four substantial written guides to the *structure* of the proof exist. All appeared within ~36 hours
  of the announcement and were built by reading the Lean source with heavy AI help. **None of them compiled the
  archive itself** (Rubinstein links to his own separate verification run, though). **None of them derives the
  central inequality.** Each one takes it from the Lean code.
* **Best structural guide:** Manvir Jaswal, *The Riemann hypothesis for Dirichlet L-functions [after Levent
  Alpöge]*, 54 pp., v1, 21 Nov 2026. It traces the five theorems of `Main.lean` back to their inputs, giving the file
  and line for each step. It also sets Alpöge's 20 dated steps against the code and lists the statements it could
  not find in the literature.
* **Most readable for a non-specialist:** Michael Rubinstein's (Waterloo) 164-page working draft. Its one-page
  strategy calls the proof "Chebyshev's argument, run with a far better 'integer'" (§1.5). For the overall shape, the
  most compact source is Bartosz Naskręcki's 11-page architecture guide (riemann-rev).
* **The structure the guides agree on.** RH and GRH are reduced to one-sided bounds on a smoothed prime sum G(x).
  The bounds hold only on "windows" [Y, Y^{3/2}], and a localized Landau theorem turns them into a zero-free
  half-plane. The bound itself is a "divisibility ≤ size" comparison, the product formula / Bost slope inequality.
  It is made for maps between lattices given by a chain of m ≈ √x theta lifts between definite unitary groups over a
  CM field in a 2-power cyclotomic tower. Inputs come from Galois representations, local Langlands and an
  Iwasawa-theoretic bound ("weakening of Vandiver"). The √x chain length balances two error terms, x/m and m. That
  balance is where the exponent ½ comes from.
* **Where the guides disagree with the note's timeline:** some of its steps have no counterpart in the code. Jaswal
  found nothing for steps 1 and 4, and Rubinstein found nothing for steps 3, 4 and 6. Rubinstein could not reproduce
  the note's step-2 divisibility exponent on the simplest example. Jaswal finds two inputs proved in a weaker form
  than the published theorems, and his §1 says "This map is not the local Langlands correspondence".
* **Numbers.**
  * "17 million lines" is right: 17,374,215 lines in 175,187 `.lean` files **[measured here]**.
  * The "14 archives" are one tarball cut into 14 pieces.
  * "250,000+ pages" is Alpöge's unpublished informal write-up. It is not the Lean proof, and nobody has
    published it.
  * Tao did write "using an internal AI model". Alpöge's note names only "Claude".
* **News errors.**
  * BBC: calls the Lean proof "over 250,000 pages long" and misspells "Reimann" in the headline.
  * FourWeekMBA: says the 175,187 modules include Mathlib.
  * Scientific American: changed a headline to "proves", and says a comparator run "typically takes a matter of
    hours".
  * CASRAI: says the write-up "would span" 250,000 pages.
  * Section 8 has the full list.

---

## 2. The best structural guide: Jaswal, "[after Levent Alpöge]"

* **Where to get it:** https://manvirjaswal.github.io/papers/rh-dirichlet-after-alpoge/jaswal-rh-dirichlet-after-alpoge.pdf
  (54 pages, "Version 1, November 21, 2026").
  * His homepage gives DOI 10.5281/zenodo.24410056. His comment on Tao's blog gives zenodo.24410057, probably the
    version DOI. Zenodo blocked my fetches.
* **Who:** Manvir Jaswal. His homepage says "Independent researcher in number theory, Toronto". He describes himself
  as "a software engineer by background, built the AI system behind this work" (https://manvirjaswal.github.io/).
* **How it was produced:**
  * Tao-blog comment 699587: "I've been looking into the Lean source as text, with Claude Fable 5.2 and GPT Astra
    6.2, to get the strategy out of it."
    (https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/#comment-699587)
  * The guide itself: "We read the statements of the declarations cited and selected proof terms, not the proofs
    below them, and we have not compiled the archive."
  * The PDF does not itself disclose the AI assistance. That disclosure is only in the blog comment.
* **Possibly the same work:** an X post by "senno" describes "a map of Alpöge's Lean proof … follows it from
  Main.lean back to its inputs in 54 pages … with the files and line of every step"
  (https://x.com/senno_kai/status/2124026050669592812; search snippet only). The page count and wording match
  Jaswal's guide. **[unverified]** whether it is the same work or the same person.

**Jaswal's outline of the proof (his §1, "The proof runs as follows"), quoted in short pieces:**

1. Reduction to primitive characters: "Part (b) for primitive characters implies the rest of Theorem 1.1, by the
   Euler product and the functional equation". Here part (b) means no zeros with Re s > ½.
2. Analytic end: "A window form of Landau's theorem excludes zeros … when Gψ(x) ≤ x^θ for all x in windows [Y, Y^λ]".
   Gψ is a positive combination of "centered ramp sums" G(ξ,x) = Σ_{n≤x} Λ(n)ξ(n)(x/n − 1) + x·L′/L(1,ξ).
3. The window bound: "Alpöge bounds Gψ(x) by x^{1/2+O(ε)} for all x in windows [Y, Y^{3/2}] with Y arbitrarily
   large. The bound comes from an inequality (⋆) comparing divisibility with size on certain abelian CM fields, the
   host fields". In the final bound C = 9, i.e. x^{1/2+9ε}.
4. The heart: "The inequality (⋆) is proved along a chain of m ≈ √x lifts, from divisibility at the inert primes,
   size, a slope inequality, near-orthogonality and a covolume bound".
5. Arithmetic input: "The host fields come from a bound for Tate–Shafarevich groups of Tate twists, VWin". Alpöge's
   note calls this the "weakening of Vandiver".

**The idea in one line (Jaswal §1):**

* "A nonzero integral period has divisibility at most its size, the logarithm of its norm, by the product formula."
* "This is Chebyshev's argument, with a period in place of a ratio of factorials."
* The toy model is the a-th derivative of a theta function on a CM elliptic curve. That derivative is divisible at
  primes inert in Q(√−d) to order a/p + a/p³ + …, "much as log n! = Σ_p log p Σ_i ⌊n/p^i⌋" (his Tao comment).

**Three caveats Jaswal flags "from the start":**

* No code for two of the note's steps: "for two of the twenty steps … steps 1 and 4, we found no counterpart on the
  chain: no Stepanov determinant, and no determinant giving the positivity of step 4".
* The periods "are defined from the kernels".
* Weaker inputs: "two inputs are weaker in the archive than the published theorems, namely the Galois
  representations Row0b and the local parameters of RecTExists … This map is not the local Langlands
  correspondence".
* Also from his §2: one hypothesis-bundle field "named after the simple pole of the Siegel Eisenstein series …
  has type UnusedSlot72, which is True, so it asserts nothing."

**Where the code lives (his §2):**

* Most of the route is under `src/Development/AutomorphicArithmetic` and `Formalism/...`. Examples:
  * `everyCharacter` (CB/MainConclusion.lean:10)
  * `zeroFreeAll_of_topG` (CB/ZeroFreeAllOfTopG.lean:26)
  * `vwin_of_row` (…/VwinOfRow.lean:4)
* His §8 lists by-products in the archive:
  * Dedekind and Hecke L-function continuation and functional equations, via Tate's thesis.
  * A short-interval lower bound for split primes.
  * A Weil-conjectures "frame" that is **not** on the route.
* He also notes: "Beyond Q the archive states no Riemann hypothesis for a Dedekind zeta function".

**Statements on the chain with no known reference (his Table 1):**

* the central "divisibility at most size" inequality (`ch_balance`, `core_gm`);
* proportionality of theta integrals;
* seesaw identities along the whole chain;
* integrality of corrected theta kernels at inert p ≥ 5 over CM fields of growing degree;
* near-orthogonality between chains ("Theorem S");
* a point-sum bound for the cost of the m lifts.

---

## 3. Other guides: what they say and how they were made

**Michael O. Rubinstein (U. Waterloo), "The Alpöge–Claude proof … explained for the Riemann zeta function"**

* Where: https://www.math.uwaterloo.ca/~mrubinst/alpoge_claude_grh/zeta-paper.pdf, 164 pp., working draft dated 21 Nov.
* How produced: the byline reads "Claude Fable 5.2, Codex Astra 6.2, and Gemini Carbon at the behest of Michael O.
  Rubinstein".
* What it explains:
  * Strategy: "Chebyshev's argument, run with a far better 'integer'".
  * Two errors x/m and m, balanced at m ≈ √x (§I.8).
  * If the second error were m², the argument would give only Re s > 2/3. This explains the note's "stop at 2/3".
* Caveats:
  * "The proof of (M) is taken from the Lean development … (M) itself is not proved here."
  * On the note's step 2: "We could not confirm the stated exponent on the simplest example".
  * On step 3: "no trace of the identity or of a sixfold cover in the Lean development".
  * Steps 4 and 6 "were not found in the Lean development".

**Bartosz Naskręcki (riemann-rev), "… a guide to its architecture"**

* Where: https://nasqret.github.io/riemann-rev/guide/proof-guide.pdf, 11 pp., created 20 Nov 21:33 UTC. The site
  also has an atlas of "14 components … 107 declarations", a "book" and a dashboard.
* Who: authorship is "riemann-rev". Rubinstein's page identifies it as Bartosz Naskręcki's.
* How produced: "§§4–7 are read here from the Lean source and from the announcement, not re-derived." The site says
  it is "not a proof, not a referee report and not an endorsement". It does not say how much AI was used.
* What it explains:
  * "One hard estimate and two classical transformations of it."
  * A Stepanov-to-ℤ dictionary:
    * vanishing to order m → divisibility of an m-fold theta lift;
    * counting degrees → Bost slope;
    * extensions of 𝔽 → cyclotomic tower;
    * "upper bounds suffice" → Landau.
* Caveat: it is a snapshot of the checks as of 20 Nov 23:51 UTC.

**Gokhan Mergen, "Inside the Claimed Lean 4 Proof of GRH: A Reader's Guide"**

* Where: https://www.gokhanmergen.com/pubs/grh-reader-guide/GRH_Reader_Friendly_Guide.pdf, 43 pp., 21 Nov.
* How produced: the PDF metadata reads "Antigravity with Gemini Neon, prompted by Gokhan Mergen (not written or
  reviewed by L. Alpoge)". It was reconstructed "from direct static inspection" of the archive.
* What it explains: the most beginner-oriented guide, with analogies and worked examples. It gives a five-stage
  overview, (m, n, k) ≈ (x^{1/2}, x², x^{9/2}) and ε < 1/52.
* Caveats: "the Lean 4 codebase has not yet been independently kernel-compiled here" (now dated). AI-written and
  unreviewed.

**digestivo.dev (Powderworks)**

* Where: https://digestivo.dev/en/riemann; data in https://data.digestivo.dev/data/riemann/summary.json
* How produced: automatic "informalization": it parses the Lean and states each declaration in English. The HN
  author called it "a rough automatic informalization".
* What it provides: statistics and a "report card". Examples:
  * 1,057,877 declarations and 818,754 theorems;
  * `"documented": 0, "commentLines": 0`;
  * the community-pruned version is 164,464 files.
* Caveat: machine-generated.

**RH Lean Explorer (riemannhypothesissolved.com)**

* Where: https://riemannhypothesissolved.com/
* How produced: "Names and descriptions on this map are written by Claude from samples of the code and may be wrong."
* What it provides: a map of "175,027 Lean files … 2,647 clusters in 63 themes", with theme names such as "Siegel–Weil
  formula and theta kernels" and "See-saw dual pairs and lattice frames".
* Caveat: its file count, 175,027, is 160 below 175,187; it does not say why.

**riemann.world (linusheck)**

* Where: https://riemann.world
* How produced: a "zoomable nested-circle map" built by regex reading of the source (GitHub snippet only).
* What it provides: a code map with no mathematical narrative.

**Tao-blog comment by Jaswal (first pass)**

* Where: comment #699587 on Tao's post. It is a 1-page summary of the 54-page guide, with corrections in comment
  #699606: "Some small corrections. I conflated two terms above."

**Not opened** (github.com is out of scope; snippets only):

* jae-63/rh-alpoge-blueprint: "Human-readable blueprint … top-layer statements, crux vs. library, dependency graphs".
* keithadler's "reduced version (55% of declarations, 12.0M lines) … plus a proof map". This is Deicyde issue 3,
  cited as reference [53] in Jaswal's guide.
* harttraveller/riemann and moozilla/riemann-hypothesis-explainer: Claude-made manim explainer videos (HN).
* ishaan2006/rh-lean-reproduction. Its snippet says several of the note's key words (Stepanov, Guinand–Weil, relative
  trace formula, Vandiver) never appear in the code. It also claims a remaining gap: "one m used twice" (a genuine
  m²). **[unverified]** No other source repeats the gap claim. The keyword part matches my count in Section 7.

**Agreement between guides, checked against the code [measured here]:**

* Chain length. In `Development/AbelianVarietyTheory/Definitions/GlobalTwisting/PairRowIffQdRows.lean:28`,
  `RankVal` requires `Real.sqrt (s.x * s.delta1) ≤ R.m ≤ 2 * Real.sqrt (s.x * s.delta1)`. Elsewhere the code has
  `s.x * s.delta1 = s.x ^ (1 + -(s.eps / 8))`.
  * So m ≈ x^{1/2 − ε/16}. Jaswal and Naskręcki state this consistently.
  * The code also requires n ≈ x^{2+8ε} and k ≈ x^{9/2+10ε}, and many lemmas assume `eps < 1 / 52`. This matches
    Mergen and Naskręcki.

---

## 4. Lean Zulip, blogs and outlets searched

* **Lean Zulip** topic "Discussion: Alpöge Proves the Riemann Hypothesis" in #general: **not readable**.
  * The public archive (leanprover-community.github.io/archive) reads "Last updated: Feb 28 2026 at 14:05 UTC" and has
    no such topic (404).
  * The API answered "Not logged in: API authentication or user session required".
  * What is known secondhand:
    * Tao: the thread is "probably the best place to follow the efforts to verify the proof and extract the strategy
      of proof"; his update says "the moderators … are now focusing the discussion on the Lean-related aspects of the
      proof only."
    * SciAm quotes Buzzard there: "We still await a successful comparator run …".
    * Jaswal cites "S. Teżewski's recap of the independent checkers".
* **Terence Tao's blog** (20 Nov):
  * His post: "Levent Alpöge, using an internal AI model, has generated an (enormous) Lean-only proof of the
    Generalized Riemann Hypothesis".
  * Also from the post: "appears to use the full power of modern developments on the Langlands program and arithmetic
    geometry".
  * Tao in comment #699598: "It is very early days but it seems like the AI-generated proof uses all of these inputs."
  * His Mathstodon feed (API) has nothing newer than 10 Nov.
* **Xena (Buzzard):** the 12 Nov post (the four criteria) predates the announcement. The 21 Nov post is a guest
  piece by Mitchell Taylor and does not mention RH. Useful context from it: Mathlib "comprises over two million lines".
* **Peter Woit, Gil Kalai, Scott Aaronson, Lior Pachter, Quanta Magazine, New Scientist, alphaxiv:** no post or article
  on the Alpöge claim found (searches on 22 Nov).
  * A Tao-blog commenter says "Quanta reports the release is about 17 million lines". **[unverified]**
* **NYT** (Chang & Roberts, 20 Nov, per the Wikipedia citation) and **AP:** both gave 403, not read.
* **Hacker News** item 50574968: 2,863 points, 2,041 comments. Useful counts are in Section 6. No structural guide
  there beyond links to digestivo, Tao and Zulip.
* Background warning: Anthropic's **August 2026** result (67.25% of zeros on the line, which Alpöge and Furman
  examined) is a different, earlier result. Search engines and some explainers mix the two up.

---

## 5. Factual points to get right in the script

* **Scope.** Sutherland: "'GRH' here means Dirichlet L-functions: all moduli and all characters. Dedekind zeta
  functions, Hecke L-functions and automorphic L-functions in general are not among the statements that were checked."
  (https://math.mit.edu/~drew/grh/)
* **The note is unsigned and untitled.** lean4.dev: "The note is unsigned; Scientific American attributes it to
  Alpöge." **[measured here]**: the PDF's Title and Author metadata are empty. "Remark" is only the filename.
* **The timeline spans 41 days**, 6 Oct to 16 Nov (officechai: "That is 41 days from start to finish"). I checked
  the arithmetic and the note's dates: 4 steps are dated 10/6, 8 are dated 11/15, and step 20 ("GRH") is dated 11/16.
* **Clay status:** "Unsolved" (https://www.claymath.org/millennium/riemann-hypothesis/, fetched 22 Nov).

---

## 6. The circulating numbers, clarified

**"17 million lines"**

* Sources:
  * Lean FRO/Mathlib statement: "a Lean library comprising 17 million lines of code".
  * infero rebuild page: "17,374,215 lines in 175,187 files".
  * HN (user 1vuio0pswjnm7): 15,531,759 non-blank lines.
  * digestivo: 17,549,402.
  * Mergen: "17.37 million"; lean4.dev: "17.4 million".
* Resolved **[measured here]**:
  * 17,374,215 newline-terminated lines;
  * 15,531,759 non-blank lines;
  * 1,030,531,854 bytes of source (about 1.0 GB; "1.3G" on disk per HN).
  * digestivo's figure equals 17,374,215 + 175,187, i.e. one extra line counted per file. That is my inference.
  * The "~15M lines" heard on HN is the non-blank count.

**"175,187 modules / 175,000 files"**

* Sources:
  * Sutherland: "All 175,187 modules compile".
  * FourWeekMBA claims "The 175,187 is the whole build, Mathlib included".
* Resolved:
  * There are exactly 175,187 `.lean` files under `lean/src`, plus `lakefile.toml`, `lake-manifest.json` and
    `lean-toolchain` **[measured here]**.
  * Mathlib is **not** included. Sutherland lists "8,322 Mathlib and 378 dependency .olean files" separately.
  * "175,000" is a rounding.
  * About 70% of the files sit in `Development/AbelianVarietyTheory`: 99,187 files and 8.14M lines
    **[measured here]**.
  * The longest import chain is 203 files deep (infero; Luo via lilting.ch: "753,569 dependency edges, zero cycles").

**"14 archives"**

* Source: note fn. 1: "https://alpo.ge/lean.tar.gz.part01, . . . , https://alpo.ge/lean.tar.gz.part14."
* Resolved: it is **one** gzip tarball split into 14 byte-chunks, which must be concatenated.
  * Parts 01–13 are 18,000,000 bytes each and part 14 is 5,275,554 bytes.
  * Total 239,275,554 bytes, sha256 9631b4f0…c7fc. This matches Sutherland **[measured here]**.

**"250,000 pages"**

* Sources:
  * Note: "I of course amused myself, and hit 250, 000+ pages."
  * Note: "I decided to only present Lean."
  * Note: "Claude cutely called it the GRH . . . 'book'".
* Resolved: this is the informal write-up Alpöge generated and chose **not** to publish.
  * Wikipedia: "remains unpublished".
  * heise: "did not publish it".
  * No source I found has published it.
  * It is not the Lean proof (BBC and CASRAI get this wrong; see Section 8).

**Exported proof**

* Sutherland: 61,570,595,788 bytes unpacked (about 61.6 GB); 7.7 GB compressed.

**Declarations**

* The counts differ by source:
  * In the source, per digestivo: 1,057,877 declarations and 818,754 theorems.
  * In the export, per con-leche: "1,468,418 declarations accepted" (Sutherland).
  * nanoda in Rubinstein's run: "1,484,729".
  * nanoda in Naskręcki's run: "1,484,733".
* The export counts differ, probably because different export targets were used. **[unverified]**

**Comments in the code**

* digestivo: `"commentLines": 0`.
* Confirmed **[measured here]**: zero `--` lines, zero `/-` blocks, zero docstrings in all 175,187 files.

**Pruned versions**

* The leanprover-community version has "unreachable modules and imports pruned": 164,464 files and 16,753,162 lines
  (digestivo).
* keithadler's version: "55% of declarations, 12.0M lines" (Jaswal ref. [53]). **[unverified]**

**Dead modules?**

* HN (jychang): "204 dead modules that are not referenced anywhere".
* Jaswal ref. [49] (joni15): "no module lies outside Main's cone".
* Not reconciled. It may be the difference between import-reachable modules and modules actually used.

---

## 7. Keyword check of the source [measured here]

Case-insensitive occurrences in the 175,187 files:

* **No occurrences at all:**
  * "Stepanov": 0
  * "Vandiver": 0
  * "Guinand": 0
  * "Bost" (at a word start): 0
* **"relative trace":** 30 hits in 22 files. They appear to be field-trace names (e.g.
  `…ExistsIntegerOfRelativeTraceNormIntegralStatement.lean`), not a relative trace formula.
* **Present:**
  * "Behrend": 142
  * "Rallis": 1,056
  * "Chowla.?Selberg": 307
  * "Langlands": 7,571
  * "Iwasawa": 32,012
  * "theta": 217,138 (in 49,449 files)

So the note's vocabulary is only partly reflected in the code's names. That does not mean the ideas are absent:
Jaswal maps "Vandiver" to `VWin` and "Bost" to `slope_inequality_general`.

---

## 8. Factual errors and disputed claims in coverage

**BBC** (https://www.bbc.co.uk/news/articles/c6pqr2g7w059o)

* "The complete textual proof that Alpöge put forward in Lean … is over 250,000 pages long."
  Wrong: the 250,000+ pages are the unpublished informal draft. The Lean proof is 17.4M lines.
* Headline: "Anthropic may have solved major maths problem Reimann hypothesis". Misspelling.
* "Tao … said … that verification of the proof is still some way off."
  Tao wrote about *digestion* ("I imagine the digestion process will take some time"), not verification.
* "found using a non-public version of Anthropic's Claude".
  The note does not say this. It matches Tao's characterization only.

**Scientific American, Howlett** (https://www.scientificamerican.com/article/anthropic-mathematician-claims-to-prove-riemann-hypothesis-most-famous-problem-in-all-of-math/)

* Headline: "Anthropic mathematician proves Riemann hypothesis".
  The URL slug and the Wikipedia citation still read "claims to prove". The headline was strengthened after updates.
* "his proof confirms the 'Generalized Riemann Hypothesis'".
  No Dirichlet-only scope is given. Sutherland limits the checked GRH to Dirichlet L-functions.
* "tweeted a Claude-generated solution to the famous Jacobian conjecture".
  Wikipedia describes it as a counterexample.

**Scientific American, Moskowitz** (https://www.scientificamerican.com/article/the-ai-riemann-hypothesis-proof-is-almost-certainly-true-independent-mathematicians-attest/)

* "Mathematicians are now certain …".
  The slug says "almost-certainly-true … attest". What is certified is the formal proof. Experts quoted elsewhere
  (Nature) say understanding will "take a long time".
* "This process, called a 'comparator run,' typically takes a matter of hours."
  Sutherland's `lake comparator` was still "running" at 03:10 UTC on 22 Nov. He says its Lean kernel stages "are
  expected to take many hours".

**CASRAI** (https://casrai.org/news/anthropic-levent-alpoge-claude-lean-riemann-hypothesis-claim-2026)

* "an AI-generated natural-language exposition … would span more than 250,000 pages".
  The note says the pages were actually produced ("hit 250,000+ pages"), not hypothetical.
* "titled Remark".
  The PDF has no title (see Section 5).
* "a series of academic lectures, workshops, and forthcoming human-readable synthesis papers".
  The note says only "to speak about it, to write it properly". This is an embellishment.
* "a junior fellow at the Harvard Society of Fellows".
  Wikipedia: "from 2021 to 2025". His own homepage still lists "junior fellow, harvard sof". Disputed, not clearly
  wrong.

**FourWeekMBA** (https://fourweekmba.com/ai-riemann-proof-build-spans-175187-files-21x-all-of-mathlib/)

* "The 175,187 is the whole build, Mathlib included."
  Wrong: see Section 6. Its headline "21x all of Mathlib" is a file-count ratio, 175,187 / 8,322. By lines it is
  about 8–9x Mathlib's roughly 2M.

**Nature** (https://www.nature.com/articles/d41586-026-03812-7)

* "Anthropic has now claimed the top prize of them all".
  The claim is in Alpöge's personal note, and Nature itself adds "Anthropic did not respond immediately".
* "just days after Anthropic's initial public offering".
  SciAm, BBC and agentspulse say "a day after".

**Wikipedia, Levent Alpöge** (https://en.wikipedia.org/wiki/Levent_Alp%C3%B6ge)

* "Anthropic's Claude had found a proof".
  The note says "I believe I have, working with Claude, discovered a proof".

**kingy.ai** (https://kingy.ai/blog/levent-alpoge-claude-riemann-hypothesis-proof/)

* "Sutherland's report still lists a comparison of full proof exports from separate builds as an open
  reproducibility check."
  Outdated: Sutherland's sandboxed rebuild export is "identical" (finished 19:32:56 UTC, 21 Nov).

**HN commenters** (https://news.ycombinator.com/item?id=50574968)

* "The 250k pages is the 15M LOC of lean proof."
  Wrong: these are two different objects (Section 6).

**The note itself, as read by the guides**

* Step 2's exponent did not check out on Rubinstein's Z[i] model.
* Steps 1, 3, 4 and 6 have no counterpart in the code (Jaswal, Rubinstein).
* Alpöge warned in fn. 4 that parts paraphrase "a 'slop' summary, which might make zero sense".

**Tao's "internal AI model": verified as Tao's wording**

* Tao: "Levent Alpöge, using an internal AI model, has generated an (enormous) Lean-only proof…"
* The note says only "working with Claude".
* kingy: the note "does not identify a specific Claude model".
* Treat "internal/unreleased model" as Tao's characterization, repeated by BBC ("non-public") and Wikipedia
  ("unreleased"). Alpöge does not state it.

---

## 9. Context: the rival human-written claim

The same day, Ravi Vakil posted Alessandro Maria Masullo's human-written GRH preprint
(https://math216.wordpress.com/2026/11/20/hurried-announcement-alessandro-masullo-grh/; Nature, heise).

* A Tao-blog commenter: "The draft is incomplete, it includes footnotes like 'Correct statement', 'Insert statement'".
* heise: Conrad told SciAm "the manuscript is undergoing a major revision".

It is unrelated to the structure of Alpöge's proof. It is noted here so the script does not conflate the two.

---

## 10. Open questions

* Is the Zulip thread's own structural analysis (Elliot Glazer, Thomas Bloom, S. Teżewski and others) published
  anywhere readable without login?
* Do Jaswal's guide and the "senno" X post come from the same author?
* Why do the export declaration counts differ (1,468,418 vs 1,484,729 vs 1,484,733)?
* ishaan2006's claimed "one m used twice" gap: no independent confirmation, and no response found.
* "204 dead modules" vs "no module lies outside Main's cone" vs 10,723 files pruned by the community: these are not
  reconciled.
* Is the RH Lean Explorer's 175,027-file count a mistake or a different filter?
* No coverage found from Quanta, New Scientist or the named blogs (Woit, Kalai, Aaronson, Pachter). The NYT and AP
  texts were not readable.
