# Sources for every factual claim in the video

Fetched 2026-11-22. Full notes with longer quotes: `status.md`, `guides.md`, `lean_archive.md`, `math_facts.md`,
`intuition.md` (written by research agents that fetched the pages; spot-checked by hand where noted ✔).
Primary documents (local copies kept out of the repo):

| | document | URL |
|---|---|---|
| N | Alpöge's 4-page note, 20 Nov 2026 ✔ | https://alpo.ge/remark.pdf |
| L | Joint statement of the Lean and Mathlib communities, endorsed by the Lean FRO and the Mathlib Initiative, 21 Nov 2026 ✔ | https://leanprover-community.github.io/blog/posts/riemann-hypothesis/ |
| S | A. Sutherland (MIT), verification files and checks, updated 22 Nov 2026 03:10 UTC ✔ | https://math.mit.edu/~drew/grh/ |
| X | K. Buzzard, "…and the proof is checked in Lean", Xena, 12 Nov 2026 ✔ | https://xenaproject.wordpress.com/2026/11/12/and-the-proof-is-checked-in-lean/ |
| A | The Lean archive itself (14 parts joined; size 239,275,554 B, sha256 9631b4f0…7fc = S) ✔ | https://alpo.ge/lean.tar.gz.part01 … part14 |
| J | M. Jaswal, "The Riemann hypothesis for Dirichlet L-functions [after Levent Alpöge]", v1, 21 Nov 2026 | https://manvirjaswal.github.io/papers/rh-dirichlet-after-alpoge/jaswal-rh-dirichlet-after-alpoge.pdf |
| R | M. O. Rubinstein, working draft, 21 Nov 2026 | https://www.math.uwaterloo.ca/~mrubinst/alpoge_claude_grh/zeta-paper.pdf |
| C | Clay Mathematics Institute, Millennium Prize rules | https://www.claymath.org/millennium-problems/rules/ |

## The claimed proof (scenes 1, 11–15)

| claim in the video | source and quote |
|---|---|
| 20 Nov 2026, a four-page note; "working with Claude" | N (PDF: 4 pages, created 2026-11-20): "I believe I have, working with Claude, discovered a proof of the Riemann Hypothesis." |
| no written proof, only Lean | N: "I decided to only present Lean." |
| 17 million lines; 175,187 files; 17.4 M lines; no comments | L: "17 million lines of code"; S: "All 175,187 modules compile"; A (counted ✔): 175,187 `.lean` files, 17,374,215 lines, 0 comment lines |
| "full confidence … correct" (quoted, attributed) | L: "We have full confidence that Alpöge's proof of the Riemann Hypothesis is correct" |
| the statement is Mathlib's, vetted by experts | L: "This statement is part of Mathlib: RiemannHypothesis and has been carefully vetted by experts in Lean and number theory." |
| dozens of rebuilds | L: "dozens of people have reported correct compilation of the codebase" |
| two independent tools: exactly that statement, standard axioms | L: "two independent tools (comparator and con-leche –compare)"; S: "propext, Classical.choice, Quot.sound only" |
| several independent checkers; two formally proved unable to accept a false proof | L: "several proof checkers, including Lean's official kernel, the con-leche and con-ron checkers…"; "con-leche and con-ron come with a formal proof, relative to set theory, that they cannot accept a false proof" |
| four questions | X: Q1 statement, Q2 compile, Q3 proves the theorem as stated (comparator), Q4 kernel bugs |
| GRH for Dirichlet L-functions reported by the MIT page; wider GRH not checked | S: "'GRH' here means Dirichlet L-functions… Dedekind zeta functions, Hecke L-functions and automorphic L-functions in general are not among the statements that were checked." L does not mention GRH. N claims GRH ("resolving the so-called Generalized Riemann Hypothesis"). |
| no human-readable proof yet; he intends to write it properly | N: "I intend to do my best to understand and impart understanding of this argument … to write it properly." |
| Clay: publication, two years, general acceptance | C: "(i) … published in a Qualifying Outlet …, (ii) at least two years must have passed since publication, and (iii) … general acceptance in the global mathematics community" |
| Clay's president: road to real understanding long and difficult | M. Bridson, statement quoted by AP (21 Nov): "the journey from today's announcement to a place of real understanding will be long and difficult" (status.md) |
| "multiplicity is hard to find over the integers, corresponding to something like differentiating whole numbers" | N, verbatim |
| chained theta lifts, each mimicking multiplicity; Claude suggested √X; "And yet, what else could it be?" | N: "Claude's suggested length of chain of theta lifts, in view of each mimicking multiplicity, was √X. (And yet, what else could it be?)" |
| timeline Oct 6 → Nov 16 | N, items 1 (10/6/26) … 20 (11/16/26: GRH) |
| skeleton: prime-sum bound ⇒ no zeros right of ½ (ζ and every Dirichlet L) ⇒ mirror ⇒ RH | A (proof terms traced from Main.lean, lean_archive.md §6); J §1 |
| chain length at least x^(1/2 − ε) | A: `Formalism/SizeWindowBrackets/SChain.lean` line 57, `x ^ ((1 : ℝ) / 2 - ε) ≤ m ∧` ✔ |
| two competing errors X/m and m, balanced at √X (readers of the code) | R §I.8: "Two errors x/m and m, balanced at m ≈ √x" (guides.md) |
| a period's divisibility grows along the chain; "Chebyshev's argument … a period in place of a ratio of factorials" | J §1: "A nonzero integral period has divisibility at most its size"; "This is Chebyshev's argument, with a period in place of a ratio of factorials." R: "Composing m lifts multiplies the matrices, so the exponents add: this is the analogue of a function vanishing to order m" |
| some timeline steps have no counterpart in the code | J: "steps 1 and 4, we found no counterpart on the chain: no Stepanov determinant"; R: steps 3, 4, 6 "not found in the Lean development" |
| Galois representations, tools from the Langlands program | A (`Row0b`: Galois representations; local Langlands inputs); Tao, 20 Nov: "the full power of modern developments on the Langlands program" (status.md) |

## Background mathematics (scenes 2–12)

| claim | source |
|---|---|
| Gauss at 15–16 (1792/93) guessed density 1/log x | Wikipedia, Prime number theorem: "Gauss considered the same question at age 15 or 16 'in the year 1792 or 1793', according to his own recollection in 1849" ✔ |
| π(10⁶) = 78,498; li(10⁶) ≈ 78,627.5 | computed (`zeta.py`, asserted against OEIS A006880 and mpmath.li) |
| ζ(2) = π²/6 (Euler, 1735); Euler product (1737) | math_facts.md §2 |
| Riemann 1859, a ten-page paper (Monatsberichte, pp. 671–680) | math_facts.md §1 |
| "it is very probable that all roots are real" | Riemann 1859, tr. D. R. Wilkins, maths.tcd.ie/pub/HistMath/People/Riemann/Zeta/EZeta.pdf ✔ |
| trivial zeros, critical strip, functional equation, first zero ½ + 14.134725…i | computed (`zeta.py`, against Odlyzko's table / mpmath.zetazero) |
| > 12 trillion zeros checked | Platt & Trudgian, Bull. LMS 2021: "the lowest 12 363 153 437 138 non-trivial zeroes ρ have ℜρ = 1/2" |
| Hilbert 1900 (8th problem); Clay 2000, $1 M | math_facts.md §3–4 |
| explicit formula (von Mangoldt 1895) | math_facts.md §6; reconstruction computed with 1,000 zeros |
| RH ⇔ error ≈ √x up to logs; cannot be smaller | math_facts.md §7; Schmidt: ψ(x) − x ≠ o(√x) (intuition.md §4) |
| Schoenfeld 1976: |π(x) − li(x)| < √x log x/(8π) for x ≥ 2657 under RH | math_facts.md §7; checked numerically to 10⁶ in `zeta.py` |
| y² + y = x³ − x mod 13: 15 affine solutions + ∞; |N − (p+1)| ≤ 2√p | computed (brute force), LMFDB 37.a1 a_p checked |
| Hasse (1930s), Weil (1940s), Deligne (1974) | math_facts.md §11 |
| Stepanov 1969; extended by Bombieri and Schmidt; multiplicity ≈ √p | math_facts.md §11 (Bombieri, Bourbaki 430: "a proof in the general case has been also obtained by W. Schmidt"; "m is about q^½"); intuition.md §3 |
| C(20,10) = 184,756 = 2²·11·13·17·19 < 4¹⁰ | computed |
| Chebyshev, around 1850: 0.92 x/ln x < π(x) < 1.11 x/ln x for large x | Wikipedia, Pafnuty Chebyshev: "bounded above and below by 0.92129 and 1.10555, for all sufficiently large x"; papers of 1848 and 1850 ✔ |
| θ(1/t) = √t θ(t); Riemann used it for the functional equation | intuition.md §5; checked numerically in `zeta.py` |
