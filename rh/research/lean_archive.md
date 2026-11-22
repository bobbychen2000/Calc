# The Lean archive of the claimed RH proof — what is actually in it

Area: lean. Researched 2026-11-22. All Lean quotes below are verbatim from the downloaded source (read as text only;
nothing was built or run). Archive: https://alpo.ge/lean.tar.gz.part01 … part14, joined.
Paths are relative to the archive's `lean/src/` unless they start with `lean/`.

## 1. Download and integrity

| check | result |
|---|---|
| parts | 14 files, 13 × 18,000,000 bytes + 5,275,554 bytes (part14) |
| joined size | **239,275,554 bytes**: matches Sutherland's page ("239,275,554 bytes") |
| sha256 | **9631b4f020199e580ba86178cb56c6e9b09f690c2369a80dc4334aa93f49c7fc**: matches https://math.mit.edu/~drew/grh/ |
| archive entries | 175,190 regular files, no symlinks, no absolute or `..` paths, all owner 0/0, all mtimes 1970-01-01 (a normalised archive) |
| uncompressed | 1,030,536,719 bytes (≈1.0 GB of text) |

## 2. Size: our counts vs. the published ones

| quantity | our count (this archive) | published |
|---|---|---|
| files | 175,190 = 175,187 `.lean` + `lean/lakefile.toml`, `lean/lean-toolchain`, `lean/lake-manifest.json` | — |
| `.lean` files (= modules) | **175,187** | Sutherland: "All 175,187 modules compile" |
| lines of `.lean` (`cat … \| wc -l`) | **17,374,215** | Lean community: "a Lean library comprising 17 million lines of code" |
| bytes of `.lean` | 1,030,531,854 | — |
| median file length | ~59 lines; 86 files > 100 kB; largest 913,995 bytes (`Formalism/HermitianCurvature/HermitianCurvatureProofs/IsAdmissibleSplittingCharPairMulTwist.lean`) | — |
| files named `*Statement.lean` | 46,610 (most results come as a `XStatement.lean` / `X.lean` pair) | — |
| lines starting `theorem …` (col. 0) | ~805,000 (rough count of top-level theorem lines) | Sutherland: 1,468,418 declarations in the whole export, Mathlib included |
| lines starting `def …` | ~212,000 | — |
| comments (`--`, `/- -/`), docstrings (`/--`) | **0**: the library has no comments and no docstrings at all | — |
| `sorry`, `admit`, `axiom` declarations | **0** each, by grep (consistent with Sutherland's axiom audit: "propext, Classical.choice, Quot.sound only") | — |
| README / docs | **none**: the only non-Lean files are the three build files below | — |

**Import graph** (parsed `import` lines, my own script): every one of the 175,187 modules is reachable from `Main`
(`Main` imports everything, directly or not); the deepest import chain is 43 modules long. The only outside imports are `Mathlib`
(156,238 import lines), `Lean` (12, in `BuildAid` and elsewhere) and `Batteries` (3). That fits the Lean community's statement that the
codebase "depends directly only on Mathlib".

## 3. Build files (verbatim, abridged)

`lean/lean-toolchain`: `leanprover/lean4:v4.33.1`

`lean/lakefile.toml` (package name `tree`):
```toml
name = "tree"
srcDir = "src"
defaultTargets = ["BuildAid", "CompanionTheory", "Development", "Formalism", "GroundTheory", "GroundTheoryFields", "Lemmata", "PositivityTheory", "ReciprocityTheory", "Supplements", "Main"]
moreLeanArgs = ["--tstack=400000"]
[leanOptions]  autoImplicit = false … maxHeartbeats = 4000000
[[require]]  name = "mathlib"  rev = "0df444a360eaa60ab8c11dca51a86af692955474"
[[lean_lib]] name = "Main"  roots = ["Statements", "Main"]
```
The Mathlib commit 0df444a3… matches Sutherland's "Mathlib tag v4.33.1 (0df444a3)". `lake-manifest.json` lists mathlib plus its
usual dependencies (plausible, LeanSearchClient, import-graph, ProofWidgets4, aesop, quote4, batteries, lean4-cli).

`BuildAid/D1..D5.lean` (4 lines each) only add namespaces to Lean's library-suggestion deny list, e.g.
`run_cmd Lean.modifyEnv fun env => Lean.LibrarySuggestions.nameDenyListExt.addEntry env "CompanionTheory"` (likewise
`CrystallineSemistableComparison`, `GlobalTheory`, `PositivityTheory`, `UpperTheory`).

## 4. Main.lean (verbatim, complete, 12 lines)

```lean
import Statements
import Supplements.Kernels.MainTheoremsAll

theorem riemannHypothesis : RiemannHypothesis := rhOfAll

theorem riemannZeta_eq_zero_re : RiemannZetaZerosOnLine := rhOfAll

theorem LFunction_ne_zero_of_half_lt_re : DirichletLNonvanishingRightOfHalf := allChi

theorem LFunction_eq_zero_re : DirichletLZerosOnLine := claimAll.2.1

theorem LFunction_eq_zero_re_of_isPrimitive : PrimitiveDirichletLZerosOnLine := critAll
```
`RiemannHypothesis` is Mathlib's own definition. `Statements.lean` (16 lines, `import Mathlib` only) defines the other four
propositions word for word as the statements on Sutherland's page, e.g.
```lean
def RiemannZetaZerosOnLine : Prop :=
  ∀ s : ℂ, riemannZeta s = 0 → (¬∃ n : ℕ, s = -2 * ((n : ℂ) + 1)) → s ≠ 1 → s.re = 1 / 2
```

## 5. Directory tree (lines of `.lean`)

Top level (`lean/src/`):

| directory | .lean files | lines | share |
|---|---:|---:|---:|
| Development | 141,928 | 12,232,663 | 70.4 % |
| Formalism | 18,254 | 3,200,748 | 18.4 % |
| GroundTheory | 8,507 | 1,119,138 | 6.4 % |
| ReciprocityTheory | 3,845 | 563,016 | 3.2 % |
| CompanionTheory | 2,027 | 194,218 | 1.1 % |
| PositivityTheory | 449 | 55,130 | 0.3 % |
| Lemmata | 167 | 9,232 | |
| BuildAid | 5 | 20 | |
| Supplements | 3 | 22 | |
| Main.lean, Statements.lean | 2 | 28 | |

There are 327 second-level directories (Formalism 107, ReciprocityTheory 24, Lemmata 167 small ones, GroundTheory 12, Development 7,
CompanionTheory 6, PositivityTheory 3). The largest second- and third-level directories:

| directory | files | lines |
|---|---:|---:|
| Development/AbelianVarietyTheory | 99,187 | 8,142,960 (46.9 % of the whole library) |
| … /AbelianVarietyTheory/Proofs | 95,418 | 7,436,698 |
| … … /Proofs/DivisorProofs | 42,424 | 2,848,282 |
| … … /Proofs/InertiaEigenvalues · IwasawaDecomposition · TwistedOperators | 8,951 · 7,769 · 6,642 | 676,661 · 600,348 · 548,833 |
| Development/AutomorphicArithmetic | 18,431 | 1,776,375 (sub-dirs AutomorphicVarieties 848,614; Foundations 419,572; ThetaCorrespondence 178,983; CharacterBoxes, the top of the proof) |
| Development/AutomorphicSpectrum | 15,147 | 1,195,844 |
| Development/WeilBound | 7,051 | 848,547 (CoreStatements 455,457; RepresentationTheoryGL 274,147; ThetaLifts 115,848) |
| Formalism/LocalToGlobal | 5,501 | 955,843 |
| Formalism/SharpRestriction | 3,093 | 709,436 |
| GroundTheory/HeightsAndTheta | 6,410 | 641,322 |
| Formalism/HermitianCurvature | 1,922 | 460,802 |
| Formalism/PeriodIntegrals | 4,350 | 451,856 |
| ReciprocityTheory/ReductiveGroups | 2,799 | 409,976 |
| Development/ResolutionOfSingularities · EtaleCohomology | 499 · 1,398 | 140,709 · 104,525 |
| small named topics in Formalism: BehrendSets, LatticeSlopes, ZeroFreeRegion, LandauZeroFreeBounds, GammaFactorNonvanishing, BesselPeriodGGP … | | |

Caveat: the directory names are labels chosen by the authors (or by Claude); they do not always say what the files contain.

## 6. The proof skeleton, followed from Main.lean (proof terms read, 1-6 levels down)

Each step names the declaration whose *proof term* the previous step uses.

| level | declaration (file) | what it says, in words |
|---|---|---|
| 0 | `riemannHypothesis := rhOfAll` and the four others (Main.lean) | the headline statements, each a one-line pointer |
| 1 | `allChi`, `rhOfAll`, `critAll`, `claimAll` (Supplements/Kernels/MainTheorems.lean) | `rhOfAll := Formalism.VW.rh_of_every allChi`; `allChi := UpperTheory.FinalTheorems.everyCharacter` |
| 2a | `Formalism.VW.rh_of_every`, `rh_of_right`, `critLine` (Formalism/GammaFactorNonvanishing/CritLine.lean, RhOfRight.lean) | "no zero to the right of 1/2" ⟹ RH, by the functional equation s ↦ 1−s (the left half mirrors the right) and Mathlib's Gamma factors. Opens with `rcases lt_trichotomy s.re (1 / 2)`, the "reals are totally ordered" step the note's footnote 2 jokes about |
| 2b | `UpperTheory.EveryCharacter` (Development/AutomorphicArithmetic/CharacterBoxes/EveryCharacter.lean) | the real target: for **every** Dirichlet character χ, L(χ,s) ≠ 0 when Re s > 1/2 (GRH in the right half-plane); RH is the case χ = 1 |
| 3 | `UpperTheory.FinalTheorems.everyCharacter := everyCharacter_of_row galoisLocalGlobalStrong_recParameter` (CharacterBoxes/MainConclusion.lean) | everything is fed by one input `Row0b`, supplied by `galoisRepresentations_of_thetaLift UpperTheory.TP.K.tLiftK` (Foundations/GaloisRepresentations/IntegralStructures/RowSrc.lean). By its type, `Row0b` asserts that Galois representations exist for regular algebraic polarized cuspidal representations over CM fields |
| 4 | `every_character_of_literature_of_vWin (O : OpenLiteratureStatements) (hV : VWin)` (ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean) | gathers dozens of standard theorems, each formalised inside the library and named after the literature (`deligne_ribet_of_literature`, `global_artin_reciprocity_of_literature`, `arith_hilbert_samuel_of_literature`, `grothendieck_messing_of_literature`, `kawamata_viehweg_of_literature`, …). The structure `OpenLiteratureStatements` has three fields (`caraianiLocalGlobalDual`, `localLanglandsExists`, `galoisRepOfPolarizedPairLit`), and all three are filled by proved theorems at level 3 (`⟨h, UpperTheory.Zero.LLC.recTExists, h⟩`), so none is an assumption |
| 4' | `UpperTheory.One.vwin_of_row` (…/DenseThresholdCases/VwinOfRow.lean) | `VWin` ("automorphic window" bounds for every primitive character, `VWinAt ψ 401`, CharacterBoxes/ExistsPageN.lean), from `Row0b` + base change |
| 5 | `UpperTheory.Lit.every_character_of_theta_integrals_local_matching` (…/ThirdPlaceSeries/SiegelEisensteinSecondTermHypotheses.lean) | from unitary-group hypotheses, theta local inputs, `ThetaIntegralsAgree`, `LocalMatching`, `CovolumeBoundOfX`, local Langlands existence (`RecTExists`) and `VWin` ⟹ `EveryCharacter`; uses Siegel–Weil, Howe duality, a Fourier-coefficient fit and "linked bundles" internally |
| 6 | `UpperTheory.Top.every_character_of_green_v_win` (…/ThirdPlaceSeries/TopPlug.lean) | `Green` + `VWin` + a nonempty family of "definite side" hypotheses ⟹ `ZeroFreeAll` (primitive characters) ⟹ via `UpperTheory.Top.imprimitive` all characters (an imprimitive L-function = primitive one × finitely many Euler factors, which do not vanish for Re s > 0) |
| 7 | `UpperTheory.Top.zeroFreeAll_of_topG` (CharacterBoxes/ZeroFreeAllOfTopG.lean) → `Formalism.HC.zeroFreeOn_of_tiedWin_cyc` (Formalism/SharpRestriction/RamificationFrobenius/TotientGaloisClasses/TopWin.lean), with `Tied := fun Fm => ChainTied Fm` | **the analytic endgame**: if a weighted Chebyshev-type prime sum `Λ.Gm x` is ≤ x^(1/2 + O(ε)) on windows of x (`ChebyshevInequalityOnWindows`), then there are no zeros to the right of 1/2 (`Landau.zero_free_of_Chebyshev_growth`, Landau.lean line 538). The bound is supplied by families of data `ChainTied` (GlobalSchurBounds/TieGlobal.lean) |
| 8 | `ChainTied` → `ChainCore` → `RestSize` (Formalism/SizeWindowBrackets/SChain.lean) | the data include a chain length **m with x^(1/2 − ε) ≤ m**, i.e. about √x (see §7) |

The prime sum at the bottom is exactly the note's timeline item 5 ("switch to Λ aka ∑ Λ(n)·(X/n − 1) − X log X + (1 + γ)·X"):
`Formalism.Gz` in Formalism/StatementOC.lean, and `Level.Gm y := Formalism.Gz y + ∑ ψ ∈ Λ.Nt, Λ.wt ψ * (An.gChi ψ.χ y).re`
(ExplicitFormulaErrorOfHostConditions.lean line 38) adds weighted character twists of the same sum.

So in plain words the skeleton is:
**(prime-sum bound of size √x) ⟹ (no zeros right of 1/2 for all Dirichlet L) ⟹ (functional equation) ⟹ RH**, where the
prime-sum bound comes from a large automorphic machine (theta lifts on unitary groups, Galois representations,
local Langlands, Siegel–Weil, covolumes, heights) that makes up nearly all of the 17 million lines.

## 7. Where the "√X-long chain of theta lifts" and "multiplicity" show up

* **Chain length ≈ √x**, on the traced path (level 8). `Formalism/SizeWindowBrackets/SChain.lean`, lines 53-58:
  ```lean
  def RestSize (ε x : ℝ) (n nT nT2 m : ℕ) (b k aE : ℝ) : Prop :=
    aE ≤ 2 * x * b ∧
    x ^ (-(ε / 8)) * n / 2 ≤ nT ∧
    x ^ (-ε) ≤ (nT2 : ℝ) / n ∧
    x ^ ((1 : ℝ) / 2 - ε) ≤ m ∧
    k ≤ (n : ℝ) ^ 2 * x ^ ((1 : ℝ) / 2 - ε)
  ```
  and in the same file `SizeWindowsSplit` also requires `(m : ℝ) ≤ x ^ ((1 : ℝ) / 2 + ε / 2)`, so m lies between x^(1/2−ε) and
  x^(1/2+ε/2). `TiePts` (TieGlobal.lean) ties this m to the datum: `(Fm.D x (pt u0)).R.m = m`. Here `D.R.m` is the number of lift
  steps in the theta-lift chains (`∀ k, k < D.R.m → …` in `NodeChainStatement`; `∀ j, j < D.R.m → …` in `DefiniteLiftChain`).
  This is the Lean version of the note's line "length of chain of theta lifts … was √X" (timeline item 8: "Time to take m like √X").
* **Iterated theta lifts as a definition.** `Development/AbelianVarietyTheory/BlockTheory/TwistedDiscreteSeries/IteratedLiftChains.lean`,
  lines 91-97: `inductive IsIterLift` (§8, snippet 5): step 0 is a cusp form, and step k+1 integrates step k against a theta kernel `th k`
  over a fundamental domain. Spaces `Yc D k` for k = 0, 1, …; `NodeChainStatement` quantifies `∀ k, k < D.R.m`.
  (This module is in Main's import closure; I did not check that this declaration appears in the final proof term.)
* `DefiniteLiftChain` (Formalism/SharpRestriction/Divisibility/FunctionModelRallisFromInputs.lean line 492): cuspidal π j for
  `j ≤ D.R.m`, each vector of π (j+1) a finite sum of theta lifts `X.th … (μ (j + 1))` of vectors in π j. This matches the note's
  "π ↦ π ⊞ μj" chain U(X0) → … → U(Xm). The character step is `chrStep μ η j := if Odd j then (μ j * η⁻¹, μ j) else (μ j, μ j * η⁻¹)`
  (Formalism/LocalToGlobal/IndefiniteReal/HasInfExpF.lean).
* Theorem `thetaChain_upward_induction_fixed_metric` (two copies, …/DecoratedLatticeProofs/ThetaChainUpwardInductionFixedMetric.lean
  and …/TwistedOperators/EvenRankThetaChainLiftSurjectiveOfAdjointNonzero.lean): induction up the chain `k ≤ D.R.m`.
* **"multiplicity"**: 776 file paths contain "Multiplicity" (258 in AbelianVarietyTheory/Proofs, 114 in ReciprocityTheory/ReductiveGroups/
  DiscreteSeries, e.g. `MultiplicityOne/…`), plus namespace `Formalism.IndefR.Mult` (IndefiniteReal/MultGood.lean, ScalarOnPartsFull.lean).
  I found **no single declaration that literally states "the m-fold lift wins multiplicity m"**: that link is the note's description.
* Name searches that came up **empty**: `Stepanov` (0 files), `Vandiver` (0), `Guinand` (0), `Lichtenbaum` (0), `IwasawaTower` (0).
  So the timeline's "Stepanov determinant", "Guinand–Weil", "weakening of Vandiver" cannot be found by name; if present they sit under
  other names.

## 8. Timeline items from the note → modules found *by name* (name matches only, not semantic verification)

| note timeline item | where something with that name lives |
|---|---|
| 5 von Mangoldt sum / Landau sign trick | `Formalism/StatementOC.lean` (`Sz`, `Gz`), `Formalism/StatementU.lean` (`ZetaLandau`: a one-sided bound `s₀ * Gz x ≤ C * x ^ θ` ⟹ ζ ≠ 0 for Re s > θ), `Formalism/ZetaNonvanishingChebyshevWeights.lean`; the used version is `Landau.zero_free_of_Chebyshev_growth` (…/TotientGaloisClasses/Landau.lean) |
| 5 explicit formula | `Formalism/PeriodIntegrals/ExplicitFormula.lean` (`PI.ExplicitFormulaWith`: ψ(u,χ) plus the sum over zeros, up to height T, of u^ρ/ρ, with an error bound); 63 paths contain "ExplicitFormula" (36 under PeriodIntegrals/UnitaryGroupMassFormula) |
| 7 GGP periods with interlacing weights | `Formalism/PeriodIntegrals/BesselPeriodGGP.lean` (`InterlacingCondition`), `…/TwistedOperators/ExistsGanGrossPrasadColumnWeights.lean`, `StrictInterlaceGanGrossPrasadBigSmall.lean`; 58 paths contain "Interlac" |
| 8 iterated theta lifts, definite unitary groups | §7; 1,321 paths contain "ThetaLift" (788 in Development/WeilBound/ThetaLifts) |
| 9 Chowla–Selberg, Siegel mass | 66 paths "ChowlaSelberg" (58 in GroundTheory/HeightsAndTheta/Heights); `theorem chowla_selberg` (…/HomogeneousIdeals/DedekindZetaEqSumRealEisenstein.lean line 325); 15 paths "SiegelMass" (Formalism/LocalToGlobal/SiegelLatticeTheory/SiegelMassRatios) |
| 12 seesaw / Rallis / Bessel periods | 452 paths "Seesaw" (440 in AbelianVarietyTheory/Proofs), 91 "Rallis", 65 "BesselPeriod" |
| 13 Bost slope inequality | `Formalism/LatticeSlopes/Statement.lean` line 75 `def SlopeInequality` (slope L ≤ μ_max M + log C for an injective map of norm ≤ C); proved as `slopeInequality` (…/DivisorProofs/SlopeAndEigenDegrees.lean line 136). "Bost" itself appears in no declaration name |
| 15 integral structure across Hecke characters | 180 paths "IntegralStructure" (175 in Development/AutomorphicArithmetic/Foundations, e.g. GaloisRepresentations/IntegralStructures, where `galoisLocalGlobalStrong_recParameter` lives) |
| 16 relative trace formula / Poincaré series | `Formalism/PeriodIntegrals/OrbitalBoundsConclusion/PoincareSeriesFinite.lean`, `PoincareSeriesInner.lean`, `PoincareSeriesMemLp.lean` |
| 18 covolumes | 666 paths "Covol"; `CovolumeBoundOfX` is an input at level 5 |
| 19 Iwasawa tower via Behrend | `Formalism/BehrendSets/` (14 files): `BehrendFree`, `BehrendBound` (sets of size N·exp(−C√(log N · log K)) with no nontrivial 3-term linear relations), next to `OrdGrp s := (ZMod (2 ^ (s + 2)))ˣ ⧸ …` (units mod 2^(s+2), a 2-power tower). "Iwasawa" paths (8,141) are mostly *Iwasawa decomposition* (Proofs/IwasawaDecomposition), a different notion |
| 2 invariant derivation on CM curves | 24 files mention `invariantDerivation`; 36 paths contain "CmCurve" (mostly Proofs/UnitaryExistence) |
| 1 Stepanov, 17 Vandiver | not found by name |

## 9. Short on-screen snippets (verbatim)

1. **Headline**: `Main.lean`, line 4
   ```lean
   theorem riemannHypothesis : RiemannHypothesis := rhOfAll
   ```
   Narration: "The whole 17-million-line library ends in one line: the Riemann Hypothesis, as Mathlib defines it."

2. **GRH, the real target**: `Development/AutomorphicArithmetic/CharacterBoxes/EveryCharacter.lean`, lines 13-14
   ```lean
   def UpperTheory.EveryCharacter : Prop :=
     ∀ (N : ℕ) [NeZero N] (χ : DirichletCharacter ℂ N) (s : ℂ), 1 / 2 < s.re → (χ ≠ 1 ∨ s ≠ 1) → DirichletCharacter.LFunction χ s ≠ 0
   ```
   "For every Dirichlet L-function there are no zeros to the right of the line Re s = 1/2."

3. **The prime sum**: `Formalism/StatementOC.lean`, lines 11-13
   ```lean
   def Sz (x : ℝ) : ℝ := ∑ n ∈ Finset.Icc 1 ⌊x⌋₊, Λ n * (x / n - 1)

   def Gz (x : ℝ) : ℝ := Sz x - x * Real.log x + (1 + Real.eulerMascheroniConstant) * x
   ```
   "A smoothed count of prime powers, minus what you'd expect; RH is about how small this leftover stays."

4. **Small leftover ⟹ no zeros**: `Formalism/SharpRestriction/RamificationFrobenius/TotientGaloisClasses/ExplicitFormulaErrorOfHostConditions.lean`, lines 40-41
   ```lean
   def ChebyshevGrowthImpliesZeroFree : Prop :=
     ∀ θ : ℝ, 0 < θ → θ < 1 → ∀ y0 : ℝ, (∀ y ≥ y0, Λ.Gm y ≤ y ^ θ) → Λ.ZeroFreeAbove θ
   ```
   (proved as `zero_free_of_Chebyshev_growth`, Landau.lean line 538). "If the prime-sum error grows no faster than y^θ, there are no zeros right of θ."

5. **Chain of theta lifts of length ≈ √x**: `Formalism/SizeWindowBrackets/SChain.lean`, line 57 (inside `RestSize`, §7)
   ```lean
     x ^ ((1 : ℝ) / 2 - ε) ≤ m ∧
   ```
   with the lift itself, `Development/AbelianVarietyTheory/BlockTheory/TwistedDiscreteSeries/IteratedLiftChains.lean`, lines 94-97:
   ```lean
     | step {k : ℕ} {u : GA D (Yc D k) → ℂ} (hu : IsIterLift k u) {Φ : WO (Yc D k) (Yc D (k + 1)) → ℂ}
         (hΦ : IsAdmDatum ψ (Yc D k) (Yc D (k + 1)) Φ)
         (hi : ∀ h, IntegrableOn (fun g => th k g h Φ * u g) (𝓕 k) (ν k)) :
         IsIterLift (k + 1) fun h => ∫ g in 𝓕 k, th k g h Φ * u g ∂ν k
   ```
   "Each step lifts a function from one group to the next by integrating it against a theta kernel, and the chain takes about √x such steps."

6. (optional) **Mirror step**: `Formalism/GammaFactorNonvanishing/RhOfRight.lean`, lines 5 and 8
   ```lean
   theorem Formalism.VW.rh_of_right (hz : ∀ s : ℂ, 1 / 2 < s.re → s ≠ 1 → riemannZeta s ≠ 0) : RiemannHypothesis := by
     rcases lt_trichotomy s.re (1 / 2) with hlt | heq | hgt
   ```
   "No zeros on the right means none on the left either: the functional equation mirrors them."

## 10. Things to keep in mind / not verified

* All checks here are textual. That the code compiles, and which axioms it uses, comes from Sutherland's page and the Lean community statement, not from me.
* The meanings I give for `Row0b`, `VWin`, `Green` and the "literature" theorems are read from their names and types. I did not trace their proofs.
* Timeline-to-module matches in §8 are by name only. Only the skeleton in §6 (levels 0-8) was followed through actual proof terms.
* `IsIterLift` is in the build, but I did not confirm that it appears in the final proof term.
