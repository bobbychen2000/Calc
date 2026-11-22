# Intuition for the claimed proof: from Stepanov to chained theta lifts

Research notes for the explainer video. Compiled 2026-11-22. Area: **intuition**.

**Rules followed**

* Every fact has a URL and a short verbatim quote (30 words or fewer).
* Extracted PDF text garbles fractions and radicals. Where a quote contains "1/2", "√" or similar, the typeset symbol
  has been restored; these quotes are marked *(symbols restored)*.
* **[computed here]** marks numbers I computed myself, read-only, from the stated formulas. The scripts are in the
  session scratchpad at `/tmp/claude-0/-home-user-Calc/b315d339-0a3b-5a60-9c53-2198ec574f3c/scratchpad/tools/`.
* **[unverified]** marks things I could not confirm.
* Downloaded copies are in `/home/user/rhwork/sources/intuition/`. The third-party guides were already in
  `/home/user/rhwork/sources/guides/`, fetched by the guides area.

---

## 0. Three levels of certainty

Keep these levels separate in every sentence of the script.

| Level | What it covers | Source |
|---|---|---|
| **Established (formally)** | A Lean proof of Mathlib's statement `RiemannHypothesis` compiles and is accepted by several independent kernels. Five theorems are checked: RH, plus RH for **Dirichlet** L-functions (GRH in that sense only). | Lean/Mathlib statement; Sutherland |
| **Established (classical math)** | Hasse–Weil, i.e. RH for curves over finite fields; Stepanov's method; RH ⇔ ψ(X) = X + O(√X log²X); Jacobi's theta symmetry; the explicit formula; Weil's positivity criterion; the theta correspondence. | textbooks / surveys below |
| **Sketch / reading** | *Why* the proof works, i.e. "multiplicity via chained theta lifts, chain length √X". This comes from Alpöge's informal 4-page note, which hedges heavily, and from third-party guides written with heavy AI help and not peer-reviewed, which read the Lean code. | note; Rubinstein, Jaswal, Naskręcki, Mergen guides |

* Lean statement: "We have full confidence that Alpöge's proof of the Riemann Hypothesis is correct".
  * It ends: "We look forward to all the activity in the mathematical community that will help explain the new ideas
    in this proof."
  * https://leanprover-community.github.io/blog/posts/riemann-hypothesis/
* Sutherland on the scope of "GRH": "'GRH' here means Dirichlet L-functions: all moduli and all characters."
  * His caveat: "A passing check shows that the formal statements, as written in Lean against Mathlib's definitions,
    follow from the three standard axioms according to the kernels used."
  * https://math.mit.edu/~drew/grh/
* Tao, 20 Nov 2026: "I imagine the digestion process will take some time"
  (https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/).

---

## 1. The note's key paragraph and its own hedges (source: https://alpo.ge/remark.pdf)

**The key paragraph, quoted in pieces:**

* "In Stepanov’s argument resolving Riemann over function fields one uses a divisor involving multiplicity."
* "multiplicity is hard to find over the integers, corresponding to something like differentiating whole numbers."
* "led us to examine chaining theta lifts if we were to have the same tricks recur but work in a natively automorphic
  manner."
* "for the von Mangoldt sum of length X, Claude’s suggested length of chain of theta lifts, in view of each mimicking
  multiplicity, was √X." It continues: "(And yet, what else could it be?)"
  * The PDF typesets the radical above the line, so text extraction separates "√" from "X". It reads "√X" in the
    typeset note.

**Timeline steps relevant to intuition (pp. 3–4):**

* Step 8 (11/15/26): "Iterated theta lifts U (X0 ) → U (X1 ) → · · · → U (Xm ) between totally definite unitary
  groups … wins multiplicity m. Time to take m like √X. . ." *(symbols restored)*
* Step 4 (10/6/26+): "W (1S ) ≥ 0 via a determinant, interpret as Stepanov with multiplicity one again; bootstrap!!"
* Step 5 (10/20/26): the switch to the smoothed sum Σ_{n≤X} Λ(n)(X/n − 1) − X log X + (1+γ)X. The step says
  "Guinand-Weil had the sign, variance test function trick".
* Step 14: "precise computation of the "cost" of each lift, showing that one would stop at 2/3 a priori".

**Hedges that the script must reflect:**

* Length: "The argument is incredibly long at the moment".
* Suboptimal choices: "I may have baked lots of strange suboptimal choices into the argument".
* Simplification expected: "My intuition insists it will be massively simplified, likely immediately."
* About Claude's parts (fn. 4): "I am sort of paraphrasing a "slop" summary, which might make zero sense, and I
  apologize".
* Mastery: "presenting the world with a complete argument before having mastered a massive neighbourhood around its
  mathematics."
* His own expertise: "I personally have little mastery of automorphic forms on higher rank groups".
* Collaboration: "I believe I have, working with Claude, discovered a proof". It was a collaboration, not "the AI
  alone".

---

## 2. Function-field RH: Hasse–Weil *is* the Riemann hypothesis for a curve

**The bound**

* Wikipedia, Hasse's theorem: "|N - (q+1)| \le 2 \sqrt{q}".
* Its explanation: the error term is "the sum of two complex numbers, each of absolute value \sqrt{q}".
* The genus-g version: "|\#C(\mathbb{F}_q) - (q+1)| \le 2g \sqrt{q}." Wikipedia calls this "the analogue of the
  Riemann hypothesis for the function field".
* https://en.wikipedia.org/wiki/Hasse%27s_theorem_on_elliptic_curves

**The zeta function**

* Local zeta function: Z(t) = P(t)/((1−t)(1−qt)), with P(t) = ∏_{i=1}^{2g}(1 − ω_i t).
* Wikipedia: "the Riemann hypothesis for curves over finite fields states |\omega_i|=q^{1/2}."
* https://en.wikipedia.org/wiki/Local_zeta_function

**Why this *is* RH**

* Bombieri (Clay problem description): "The Riemann hypothesis for ζ(s, C) is the statement that all its zeros have real
  part equal to 1/2".
* Continued: in terms of Z(t, C), "which has a numerator of degree 2g, has zeros of absolute value q^{-1/2}"
  *(symbols restored)*.
* https://www.claymath.org/wp-content/uploads/2022/05/riemann.pdf
* My one-line derivation: zeros of Z are t = 1/ω_i, so |t| = q^{−1/2}. With t = q^{−s}, |q^{−s}| = q^{−Re s}, hence
  Re s = 1/2.
* Weil conjectures statement: "all zeros of P_k(T) lie on the "critical line" of complex numbers s with real part k/2"
  (https://en.wikipedia.org/wiki/Weil_conjectures). For a curve k = 1, so Re s = 1/2.
* Point count over every extension: N_m = 1 − α^m − β^m + q^m, "where α and β are complex conjugates with absolute
  value √q" *(symbols restored)* (same Weil conjectures page, elliptic-curve case).

**History**

* Hasse settled g = 1 "in 1934". The general case was "finally settled by Weil in the early 1940s" (Bombieri, Clay).
* **Date conflict:** Wikipedia says "It was proven by Helmut Hasse in 1933, with the proof published in a series of papers in 1936." Say "Hasse, 1930s" in the script.
* Bombieri on the relevance: "the analogies are too compelling to be dismissed outright."

---

## 3. Stepanov's method, precisely enough to animate

**The engine: count zeros with multiplicity**

* Hanson: "if r(x) is a non-zero polynomial of degree D and r(x) has a zero of order l at distinct values x1, . . . ,
  xn then n ≤ D/l."
  * "This fact is basically just the prime factorization of polynomials."
  * https://personal.science.psu.edu/rcv4/stepanovs-method-hyperelliptic.pdf
* So, with N points, multiplicity m and degree D: **N·m ≤ D**, i.e. N ≤ D/m.
* The art is to build a nonzero auxiliary polynomial whose degree D is only a little more than q·m.

**What is being counted (prime field, y² = f(x))**

* x gives a point iff f(x)^{(p−1)/2} = 1 (Euler's criterion; Hanson: "if f(x) = y^2 then f(x)^{(p−1)/2} = y^{p−1}
  = 1" *(symbols restored)*).
* Croot: g1(x) := f(x)^{(p−1)/2} − 1. One must show it has at most p/2 + O(√p) roots mod p, by producing r(x) that
  "vanishes to order M at all the mod p roots of g_i(x), at least when M ∼ c√p" *(symbols restored)*.
* The degree is deg r ≤ pM/2 + O(M√p).
* https://ecroot.math.gatech.edu/stepanov4.pdf (E. Croot, "Stepanov’s Method for Elliptic Curves", 2007)

**Why derivatives and Frobenius make it work**

* High-order vanishing means checking that derivatives vanish.
* The Frobenius power x^p is a "constant" for differentiation in characteristic p.
  * Croot: "the derivative of terms cx^{kp} is 0 mod p."
* So you can differentiate a polynomial built from blocks x^{kp}·k_i(x) many times without the x^{kp} parts growing.
  The relation f^{(p−1)/2} = 1 at the points keeps the derivatives' degrees small.
* Snag: in characteristic p, k! can vanish. Hanson: "We run into trouble with this fact over Fp because d/dx(x^p) =
  px^{p−1} = 0." *(symbols restored)*
* The fix is the Hasse derivative D^{(r)}X^n = C(n,r) X^{n−r}. In characteristic 0 it equals (1/r!)(d/dX)^r
  (https://en.wikipedia.org/wiki/Hasse_derivative).
* For multiplicities m < p, ordinary derivatives suffice. Stepanov's m ~ √p is below p.

**The surface picture (Tao's survey)**

* Tao: "the idea is to use the polynomial method and locate a polynomial P on C × C that does not vanish identically
  on C2, but vanishes to high order on C1".
* Here C1 is the diagonal and C2 is the graph of Frobenius. Their intersection is exactly the F_q-points.
* The two lemmas:
  * Lemma 4.7: an interpolating P exists when "(q − 10m)(d − 10) > m(q + 10d + 20m)".
  * Prop. 4.5 then gives "|C1 ∩ C2| ≤ (dq + q)/m + 3" *(symbols restored)*.
* Tao: "One can optimise this bound by setting m := C^{-1}√q and d := C^{-1}√q + C" *(symbols restored)*.
* https://arxiv.org/pdf/1310.6482 (Tao, "Algebraic combinatorial geometry", §4)

**Where √q comes from: a balance of two errors [computed here]**

* From Lemma 4.7 the smallest admissible d is d ≈ m + 10 + O(m²/q), so the bound is
  **q(d+1)/m ≈ q + 11q/m + 40m**. That is my expansion of Tao's inequality.
  * q/m is a fixed overhead paid once and divided by the multiplicity.
  * m is the cost that grows with the multiplicity, because vanishing to order m imposes about m² extra conditions.
* Minimising gives m ≈ √(11q/40) ≈ **0.52√q** and an error of about 42√q. The constant is crude, but the order is √q.
* Exact optimum over integer (m, d) from Tao's inequality:

| q | best m | m/√q | d | bound − q | (bound − q)/√q | Hasse 2√q |
|---|---|---|---|---|---|---|
| 10^4 | 44 | 0.44 | 63 | 4,548.5 | 45.5 | 200 |
| 10^6 | 520 | 0.52 | 541 | 42,310.7 | 42.3 | 2,000 |
| 10^8 | 5,240 | 0.524 | 5,261 | 419,850.3 | 42.0 | 20,000 |

* Multiplicity is the engine. At q = 10^6 the bound / q is:

| m | 1 | 2 | 10 | 100 | **520** | 3,000 | 30,000 |
|---|---|---|---|---|---|---|---|
| bound / q | 13.0 | 7.0 | 2.2 | 1.12 | **1.042** | 1.13 | 4.0 |

  * With bounded multiplicity the error is a fixed *fraction* of q, no better than the trivial 2q.
  * Only m growing like √q gives q + O(√q).
  * This is a U-shaped curve, ideal for animation.

**Getting from the upper bound to the full Hasse–Weil**

* The upper bound comes first; a lower bound needs a trick.
  * Tao (2014 blog): "there is a Galois-theoretic trick to convert (a slight generalisation of) this upper bound to a
    matching lower bound".
  * The sharp 2g√q then follows from the trace formula and "the “tensor power trick” of sending n to infinity".
  * https://terrytao.wordpress.com/2014/05/02/the-bombieri-stepanov-proof-of-the-hasse-weil-bound/
* In the survey's elementary version, the lower bound uses the "dilated curve" y² = a·f(x) with a a non-residue.
  Together the two curves count 2q + O(1).

**Nuance for the script**

* Tao's 2014 blog presents Bombieri's version for q a perfect square, where first-order vanishing suffices.
  * Quote: "In Bombieri’s original argument, one required vanishing to high order on the C_1 side". In his own
    presentation a Frob_{√q} factor "removes this high order vanishing condition".
  * There √q enters through Frob_{√q}.
* In Stepanov's original prime-field, hyperelliptic version, √p enters through the multiplicity M ~ √p.
* Safe phrasing: "in Stepanov's version, the multiplicity is about √p".

**Primary references** (as cited by the surveys; not fetched)

* S. A. Stepanov, "On the number of points of a hyperelliptic curve over a finite prime field", Izv. Akad. Nauk SSSR
  (1969).
* E. Bombieri, "Counting points on curves over finite fields (d'après S. A. Stepanov)", Sém. Bourbaki (1973/74).

---

## 4. Over the integers: RH as square-root cancellation in the "von Mangoldt sum of length X"

**The equivalence**

* RH ⇒ the bound: Schoenfeld (1976) "showed that the Riemann hypothesis implies |\psi(x) - x| < \frac{1}{8\pi}
  \sqrt{x} \log^2 x for all x\geq 73.2"
  (https://en.wikipedia.org/wiki/Riemann_hypothesis, §Distribution of prime numbers).
* The bound ⇒ RH: "Proposition 1. If ψ(x) = x + Oε(x^{1/2+ε}) for all ε > 0, then the Riemann hypothesis holds."
  *(symbols restored)*
  * The same notes: "the Riemann hypothesis implies that ψ(x) = x + O(√x log² x)" *(symbols restored)*.
  * https://personal.math.ubc.ca/~gerg/teaching/539-Winter2020/Mar17.pdf
* **So RH ⇔ ψ(X) = X + O(X^{1/2+ε}) for every ε, and RH gives the O(√X log²X) form.**
* The π(x) version: π(x) = Li(x) + O(√x log x), "(this last estimate is in fact equivalent to the Riemann
  hypothesis)" (https://en.wikipedia.org/wiki/Prime_number_theorem).

**Why √X is the natural size**

* It cannot be beaten, unconditionally.
  * Schmidt: "\psi(x)-x \ne o\left(\sqrt{x}\,\right)".
  * Hardy–Littlewood: "\psi(x)-x \ne o\left(\sqrt{x}\,\log\log\log x\right)".
  * https://en.wikipedia.org/wiki/Chebyshev_function
* The random-walk heuristic: for the Möbius function, RH "is in some sense equivalent to saying that μ(x) behaves like
  a random sequence of coin tosses" (Wikipedia, Riemann hypothesis, Denjoy's argument). A random walk of X steps
  wanders about √X.
* Naskręcki's guide states it compactly: "RH is square-root cancellation among the primes."
  (https://nasqret.github.io/riemann-rev/guide/proof-guide.pdf)

**Real numbers [computed here, primes up to 2·10^6]**

| x | ψ(x) − x | (ψ(x) − x)/√x |
|---|---|---|
| 10^4 | 13.4 | 0.134 |
| 10^5 | 51.6 | 0.163 |
| 10^6 | −413.4 | −0.413 |
| 2·10^6 | 115.0 | 0.081 |

* In every row the error stays far below √x log²x/(8π), which at 10^6 is 7,594.

**The note's sum: the smoothed statistic**

* The "von Mangoldt sum of length X" in the note's step 5 is a *smoothed* version:
  G(x) = Σ_{n≤x} Λ(n)(x/n − 1) − x log x + (1+γ)x.
* Rubinstein defines exactly this and names it "§I.1: this is G(X)" in his dictionary with the note.
* Its explicit formula is G(x) = log 2π − Σ_ρ x^ρ/(ρ(ρ−1)) + O(x^{−2}), which converges absolutely: "that is the
  benefit of smoothing".
* Rubinstein's sanity check: "G(10^4) = 1.749, G(10^5) = 3.671, G(10^6) = 11.040, G(2 · 10^6) = −12.268"
  *(symbols restored)*. **I reproduced all four values exactly [computed here].**
* Under RH, |G(x) − log 2π| ≤ 0.0462√x for large x.
* https://www.math.uwaterloo.ca/~mrubinst/alpoge_claude_grh/zeta-paper.pdf (working draft, 21 Nov 2026; byline
  "Claude Fable 5.2, Codex Astra 6.2, and Gemini Carbon at the behest of Michael O. Rubinstein")

---

## 5. Theta functions, the functional equation, theta lifts (cartoon level, not misleading)

**Jacobi's symmetry**

* With Θ(t) = Σ_{n∈ℤ} e^{−πn²t}, Poisson summation gives
  "\sum_{n=-\infty}^\infty e^{ - n^2 \pi x } = \frac{ 1 }{ \sqrt{x} } \sum_{n=-\infty}^\infty e^{ -\frac{ n^2 \pi }{ x } }".
  So Θ(1/t) = √t·Θ(t) (https://en.wikipedia.org/wiki/Riemann_zeta_function, proof of the functional equation).
* Numerical check [computed here]: Θ(1/2) = 1.41950 = √2·Θ(2), with Θ(2) = 1.00373. Θ(1/0.3) = 1.0000566 = √0.3·Θ(0.3).

**Riemann's use of it (his "second proof")**

* "was used by Riemann to prove the functional equation for the Riemann zeta function, by means of the Mellin
  transform" (https://en.wikipedia.org/wiki/Theta_function, §Relation to the Riemann zeta function).
* The integral Γ(s/2)π^{−s/2}ζ(s) = ½∫(ϑ(0;it) − 1)t^{s/2} dt/t "can be shown to be invariant under substitution of s
  by 1 − s".
* Whether to call this "Riemann's second proof" is standard textbook usage (Titchmarsh §2.6), not checked here.
  Say "Riemann used theta's symmetry to prove the functional equation".

**Dual pairs and the theta correspondence**

* "the theta correspondence or Howe correspondence is a mathematical relation between representations of two groups of
  a reductive dual pair" (https://en.wikipedia.org/wiki/Theta_correspondence).
* Gan's lectures, for unitary groups U(V) × U(W) inside one symplectic group: "The images of U(V) and U(W) are in fact
  mutual commutants of each other in the symplectic group, and such a pair of groups is called a reductive dual pair."

**The global theta lift**

* Gan's definition: θ(φ, f)(g) = ∫_{[U(V)]} θ(φ)(g, h)·f(h) dh.
* Then: "Then θ(ϕ, f) is an automorphic form on U(W)."
* That is, a lift is an integral against a theta kernel that carries a form on one group to a form on the other.
* https://arxiv.org/pdf/2303.14918 (W. T. Gan, "Automorphic forms and the theta correspondence", §3.6)

**For the "totally definite" unitary groups of the note**

* Rubinstein: "a “function on the group” is a function on a finite set of lattices". "So a theta lift is a matrix of
  derivatives of theta functions, between two spaces that carry natural integer lattices". This is a reading of the
  proof's objects, from his guide.

**A "chain" of lifts**

* The note: U(X_0) → U(X_1) → … → U(X_m) (step 8).
* Rubinstein: "Composing m lifts multiplies the matrices, so the exponents add: this is the analogue of a function
  vanishing to order m in Stepanov’s proof".
* Caution from Jaswal: the archive's objects are "kernels, which Alpöge describes as theta lifts and which are built
  from theta functions". Say "what the note calls theta lifts".

---

## 6. Explicit formula, Weil positivity, and what a one-sided sign buys

**The explicit formula**

* Wikipedia: "Roughly speaking, the explicit formula says the Fourier transform of the zeros of the zeta function is the
  set of prime powers plus some elementary factors."
* https://en.wikipedia.org/wiki/Explicit_formulae_for_L-functions
* Classical form: ψ₀(x) = x − Σ_ρ x^ρ/ρ − ζ′(0)/ζ(0) − ½ log(1 − x^{−2}) (https://en.wikipedia.org/wiki/Chebyshev_function).

**Guinand–Weil**

* "The classical Guinand-Weil explicit formula [3, Lemma 5] establishes the relation between the zeros of a primitive
  Dirichlet character modulo q and the primes that are coprime to q."
* https://arxiv.org/pdf/2005.02393 (Chirre, Pereira Júnior, de Laat)

**Weil's positivity criterion**

* "It takes the form of an equivalent statement, to the effect that a certain generalized function is positive definite"
  (https://en.wikipedia.org/wiki/Weil%27s_criterion).
* Bombieri: "Weil also proved that the Riemann hypothesis is equivalent to the negativity of the right-hand side for all
  functions f(x) of type" f = ∫ g(xy)·ḡ(y) dy. That is an "autocorrelation", so a sum of squares.
* Bombieri, function-field side: "In the geometric case of curves over a finite field, this negativity is a rather easy
  consequence of the algebraic index theorem for surfaces".
* So in the toy world the needed *sign* comes from geometry. Over ℚ, no such source of positivity was known.

**What a one-sided bound buys (this is what the proof uses, per the guides)**

* Rubinstein: "One side is enough."
  * A zero with real part β > 1/2 and its conjugate together give a term ~ x^β cos(γ log x + φ). It "oscillates and
    takes both signs".
  * So "an upper bound for G should already exclude it", by a theorem of Landau on Mellin transforms of functions of
    one sign.
* The guides' reduction: an upper bound G(x) ≤ x^{1/2+ε} holding only on windows [Y, Y^{3/2}] (Y arbitrarily large)
  already gives no zeros with Re s > 1/2.
  * Rubinstein: "Lemma (the same, on intervals)".
  * Jaswal: "A window form of Landau's theorem excludes zeros".
* The functional equation then reflects to Re s < 1/2.
* Naskręcki's table: "“upper bounds suffice” ⟶ a theorem of Landau type".

**How the note's signs relate (hedged)**

* The note's "W(1_S) ≥ 0 via a determinant" (step 4) and "W(1_(0,1] + (∼X^η)·1_(0,1/X]) ≥ 0 gives > 1 − η"
  (step 6) look like positivity of a Weil-type explicit-formula functional W on chosen test functions.
* Jaswal reads step 6 as "in our reading, no zeros with Re s > 1 − η". **[unverified interpretation]**
* **Neither guide found step 4 in the code.**
  * Jaswal: "for two of the twenty steps … steps 1 and 4, we found no counterpart on the chain: no Stepanov
    determinant, and no determinant giving the positivity of step 4".
  * Jaswal: "The sign on the chain is that of ch_top, by which divisibility minus size is at most an error, with ramp
    test functions."
  * Rubinstein: steps 4 and 6 "were not found in the Lean development".
* So describe these steps as part of *how the idea was found*, not as how the final proof runs.
* Jaswal PDF: https://manvirjaswal.github.io/papers/rh-dirichlet-after-alpoge/jaswal-rh-dirichlet-after-alpoge.pdf

---

## 7. The core analogy, as the guides read it (hedged: AI-assisted guides, not peer-reviewed)

**Chebyshev's idea: "divisibility ≤ size"**

* Rubinstein: "The proof of the Riemann hypothesis described here is Chebyshev’s argument, run with a far better
  “integer”."
* "Divisibility is a statement about each prime separately; size is a statement about the real numbers."
* If p^{e_p} divides a nonzero integer Δ, then Σ e_p log p ≤ log|Δ|. Rubinstein calls this "the arithmetic analogue of
  Stepanov’s count of zeros with multiplicity".
* Jaswal: "A nonzero integral period has divisibility at most its size, the logarithm of its norm, by the product
  formula."
  * "This is Chebyshev’s argument, with a period in place of a ratio of factorials."
* Mergen: "Over Z, a prime p plays the role of a point, and divisibility p^j | n plays the role of vanishing to order
  j." (https://www.gokhanmergen.com/pubs/grh-reader-guide/GRH_Reader_Friendly_Guide.pdf; its metadata says AI-written:
  "Antigravity with Gemini Neon, prompted by Gokhan Mergen".)

**"Differentiating whole numbers" made concrete (Rubinstein §I.3)**

* The lemniscate sine's derivatives at 0, A_n = sl^{(n)}(0), are integers: "A1 = 1, A5 = −12, A9 = 3024, A13 =
  −4390848, A17 = 21224560896".
* A prime p ≡ 3 mod 4 (inert in ℤ[i]) divides A_n to about n·p/(p²−1) = n(1/p + 1/p³ + …).
  * "Only odd powers of p appear. That is the signature of an inert prime."
  * "The split primes 5, 13, 17, 29 divide none of these A_n."
* **Reproduced [computed here]**, as (exponent of p in A_n; n·p/(p²−1)):

| n | p = 3 | p = 7 | p = 11 | exponent of 5 | exponent of 13 |
|---|---|---|---|---|---|
| 17 | 6; 6.38 | 2; 2.48 | 1; 1.56 | 0 | 0 |
| 49 | 19; 18.38 | 7; 7.15 | 4; 4.49 | 0 | 0 |
| 101 | 37; 37.88 | 14; 14.73 | 9; 9.26 | 0 | 0 |
| 201 | 75; 75.38 | 29; 29.31 | 18; 18.43 | 0 | 0 |

* What this toy does and does not achieve:
  * It gives smooth exponents, which Rubinstein calls wish (W1).
  * Its size is too big: "The inequality (I.6) is true and useless: it is off by a factor 2 in the leading term."
  * The real proof replaces this toy by theta-series objects. That replacement is "quoted, not reproved" by him.

**The chain and the exponent 1/2**

* Rubinstein §I.8:
  * "x/m: errors made once, in the sizes of the lattices at the two ends of the chain of maps".
  * "m: errors accumulated over the m steps".
  * "The terms x/m and m are balanced when m ≈ √x, and both equal √x. That is where the exponent 1/2 comes from."
    *(symbols restored)*
* With a cost of m² instead: "x/m + m², balanced at m = x^{1/3}". That would give only Re s > 2/3, matching the
  note's "stop at 2/3" *(symbols restored)*.
* Jaswal (Remark 3.6): "The exponent 1/2 comes from two places." The first is the chain length, balancing x/m and m.
  The second is the twisted ramp sums of auxiliary characters, bounded "on average" via a mean square and Markov's
  inequality.
* The code itself: "The archive takes x^{1/2−ε/16} ≤ m ≤ 2x^{1/2−ε/16}" (Jaswal) *(symbols restored)*. The guides
  area also checked this independently in the source.

**Naskręcki's dictionary**

| Stepanov, over 𝔽 | The announced proof, over ℤ |
|---|---|
| "vanishing to order m" | "divisibility of an m-fold iterated theta lift" |
| "counting degrees" | "Bost’s slope inequality" |
| "the finite extensions of 𝔽" | "the layers of a cyclotomic tower of fields" |
| "“upper bounds suffice”" | "a theorem of Landau type" |

**Caveats on all of this**

* Rubinstein: "(M) itself is not proved here." The central inequality is taken from the Lean code.
* Jaswal: "We read the statements of the declarations cited and selected proof terms, not the proofs below them".
* Rubinstein on the note's step 2: "We could not confirm the stated exponent on the simplest example" (his §I.9).

---

## (a) Intuition beats, in order

### Beat 1. RH is a statement about square-root-sized errors

* **Safe:**
  * Count primes with weights log p (Chebyshev's ψ). RH is equivalent to the error ψ(X) − X being at most about √X,
    up to log factors.
  * No smaller error is possible even in principle: ψ(x) − x ≠ o(√x).
* **Hedge:** "about √X" means O(X^{1/2+ε}), or √X log²X under RH. It does not mean O(√X).
* **Analogy:** a fair coin flipped X times drifts about √X from even. RH says primes are "that random" and no worse.
* **Visualization:**
  * Left: ψ(x) − x for x ≤ 2·10^6 (data in §4) between the curves ±√x. Show the four tabled points.
  * Right: five random ±1 walks, with a ±√n envelope.

### Beat 2. A world where RH is already a theorem: curves over finite fields

* **Safe:**
  * Count solutions of y² + y = x³ − x mod p. The count N is always within 2√p of p + 1 (Hasse, 1930s). For genus g
    the bound is 2g√q (Weil, 1940s).
  * This *is* the Riemann hypothesis for that curve's zeta function: its zeros satisfy |t| = q^{−1/2}, i.e.
    Re s = 1/2.
* **Hedge:** this is an analogue. It does not imply the classical RH.
* **Analogy:** a "clock-arithmetic" universe with p hours, where the curve's points can be counted exactly and the
  square-root law can be checked by hand.
* **Visualization:**
  * The 13×13 grid of (x, y) with the 15 solutions lit (table in (c)).
  * A scatter of a_p/(2√p) for 667 primes up to 5,000 (zeta.py: max ratio 0.9965), all inside [−1, 1].
  * Inset: the two zeros of P(T) = 1 + 2T + 13T² on the circle |T| = 13^{−1/2}.

### Beat 3. Stepanov's trick: a polynomial with too many high-order zeros

* **Safe:**
  * A nonzero polynomial of degree D has at most D roots counted with multiplicity.
  * Build one (by linear algebra: more unknown coefficients than conditions) that vanishes to order m at every point
    you want to count. Then N·m ≤ D, so N ≤ D/m.
  * Stepanov (1969) did this for y² = f(x). Bombieri extended it to all curves.
* **Hedge:**
  * Stepanov's polynomial gives the *upper* bound q + O(√q) with a worse constant than 2√q.
  * The lower bound needs a second trick (the twisted curve).
  * The sharp 2g√q needs the trace formula and the tensor-power trick.
* **Analogy:** a budget. Degree is money; each point costs m. If you can afford only D, you can buy at most D/m points.
  Raising m makes every point expensive.
* **Visualization:**
  * A polynomial curve touching the axis at several points, drawn with higher-order tangency (flatter and flatter) as
    m = 1, 2, 3.
  * A bar "degree budget D" split into N blocks of width m.

### Beat 4. Why √q: two errors in balance

* **Safe:**
  * The final error is about q/m (overhead paid once, divided by m) plus about m (conditions that grow with m).
  * Best m is about √q, and then the error is about √q.
  * With Tao's published constants: best m ≈ 0.52√q, error ≈ 42√q.
  * Derivatives work because the Frobenius power x^p differentiates to 0 mod p (Hasse derivatives handle the
    factorials).
* **Hedge:**
  * The constants (11, 40, 42) come from one textbook-style version of the argument, not from Stepanov's sharpest one.
  * In Bombieri's square-q version, √q enters via a square-root Frobenius rather than via the multiplicity.
* **Analogy:** a funnel or lens with an optimal setting. Too little multiplicity and the overhead dominates; too much
  and the conditions swamp you.
* **Visualization:** the U-shaped curve of (bound − q)/√q against m at q = 10^6, using the m-table in §3. Its minimum
  is at m = 520 ≈ 0.52·√(10^6). Overlay the approximation 11q/m + 40m.

### Beat 5. Over the integers there is no "degree", but there is "size"

* **Safe:**
  * The integer analogue of "N·m ≤ degree" is Σ_p e_p log p ≤ log|Δ|.
  * If p^{e_p} divides a nonzero integer Δ, the primes cannot outweigh its size.
  * Chebyshev and Erdős used this to bound primes. For example, C(20,10) = 184,756 is divisible by 11·13·17·19 =
    46,189 and is at most 4^{10} = 1,048,576.
  * Over ℤ, "vanishing to order m at a point" becomes "divisible by p^m".
* **Hedge:** this classical method alone gives only c₁X ≤ ψ(X) ≤ c₂X. Rubinstein: "Chebyshev’s method yields
  c1 n ≤ ψ(n) ≤ c2 n and no more."
* **Analogy:** a crate's weight limits how many heavy bricks (primes, weighted by log p) can be inside it.
* **Visualization:** a log-scale bar showing C(20,10) with the four primes stacked inside, and the 4^{10} ceiling.

### Beat 6. "Differentiating whole numbers": derivatives that come out divisible

* **Safe (per the guides):**
  * Derivatives of special functions of arithmetic origin can be integers with predictable prime divisibility.
  * The lemniscate sine's n-th derivative at 0 is divisible by 3 about 3n/8 times, by 7 about 7n/48 times, and so on.
    This holds for primes p ≡ 3 mod 4.
  * Primes p ≡ 1 mod 4 are not forced to divide.
  * Differentiating many times *creates* divisibility, the integer stand-in for multiplicity.
* **Hedge:**
  * This toy model is the guides' illustration (Rubinstein §I.3; Jaswal's "toy model").
  * The proof's actual objects are theta-series periods / lattice maps.
  * The divisibility statements for them are taken from the Lean code, not proven in the guides.
* **Analogy:** each derivative is a "turn of a crank" that adds a predictable number of factors of p.
* **Visualization:** a bar chart of the exponent of 3 in A_n against the line 3n/8 for n = 17, 49, 101, 201, with 5
  and 13 at zero.

### Beat 7. Theta functions: symmetric sums of Gaussians

* **Safe:**
  * Θ(t) = Σ_n e^{−πn²t} satisfies Θ(1/t) = √t·Θ(t) (Poisson summation).
  * Riemann used this to prove ζ's functional equation, the s ↔ 1 − s symmetry about the critical line.
  * Theta series count lattice points weighted by a Gaussian, so they carry integers (arithmetic) and Gaussian sizes
    at once. These are exactly the two properties "divisibility ≤ size" needs.
* **Hedge:** the "Gaussian size / integer coefficients" point is Rubinstein's framing.
* **Analogy:** a sum of Gaussian bumps at the integers looks the same after rescaling t ↔ 1/t, up to √t. It is like a
  crystal whose diffraction pattern is another crystal.
* **Visualization:**
  * Plot Θ(t) and √(1/t)·Θ(1/t) on a log t axis; they coincide.
  * Mark t = 0.5 / 2 with Θ = 1.4195 / 1.0037.

### Beat 8. A theta lift is a bridge between two groups; the new idea is a chain of them

* **Safe:**
  * A theta lift turns an automorphic form on one group into one on a partner group. It is an integral against a
    theta kernel, for groups forming a "dual pair", e.g. two unitary groups (Howe; Gan's definition).
  * The note's idea: chain lifts U(X₀) → U(X₁) → … → U(X_m), "each mimicking multiplicity".
  * Per the guides, composing m lifts makes the divisibility exponents add, the analogue of vanishing to order m.
* **Hedge:**
  * The note itself describes Claude's technical parts as a paraphrased "slop" summary "which might make zero sense".
  * The guides read "kernels, which Alpöge describes as theta lifts".
  * Nobody has yet written a human-checked account of why the chain gives the divisibility.
* **Analogy:** relay runners. Each handoff (lift) adds one "order" of divisibility, as each derivative adds one order
  of vanishing. But each handoff also costs a little.
* **Visualization:**
  * A row of m boxes labelled U(X₀) … U(X_m) linked by arrows.
  * Two meters fill as the chain grows: "divisibility gained" grows linearly in m; "accumulated cost" also grows.
  * A final number line of exponents adding.

### Beat 9. Why the chain length is √X

* **Safe:**
  * In the guides' accounting the final error has two parts.
    * One is paid once (at the chain's ends) and shared over m steps: about X/m.
    * One grows with each step: about m.
  * They balance at m ≈ √X, giving an error of about √X, which is exactly RH's size.
  * The Lean code takes m between X^{1/2−ε/16} and 2X^{1/2−ε/16}.
  * If each step cost m² instead, the balance would be at X^{1/3}, giving only "no zeros beyond 2/3". The note says
    "one would stop at 2/3 a priori".
* **Hedge:**
  * Jaswal says the exponent 1/2 enters in two places; the second is the auxiliary twisted sums.
  * The X/m + m accounting is the guides' reading of the code.
* **Analogy:** the same funnel as Beat 4. q ↔ X, multiplicity ↔ chain length, √q ↔ √X.
* **Visualization:**
  * Two curves on one plot: X/m + m (minimum at √X) and X/m + m² (minimum at X^{1/3}), for X = 10^6.
  * Then the side-by-side U-curve from Beat 4 for the finite-field case.

### Beat 10. One-sided is enough, and what is and is not established

* **Safe:**
  * The explicit formula ties primes to zeros. A zero off the line would force the smoothed prime sum to swing above
    X^{1/2+ε}, in both directions.
  * So an *upper* bound alone, on long windows [Y, Y^{3/2}], rules out zeros to the right of 1/2. The functional
    equation handles the left.
  * The formal Lean proof is certified by the Lean/Mathlib communities, with RH and RH for all Dirichlet L-functions
    checked.
* **Hedge:**
  * The *explanation* is not yet in human hands. Tao: "I imagine the digestion process will take some time".
  * The note expects big simplifications.
  * Two of the note's 20 steps (the Stepanov determinant and the positivity W(1_S) ≥ 0) were not found in the code by
    Jaswal.
* **Analogy:** Mergen's "strobe light that only checks the ceiling". A wildly swinging pendulum would eventually hit
  the ceiling during one of the flashes.
* **Visualization:**
  * Real G(x) − log 2π against ±0.0462√x (G values in §4).
  * Overlay a fake off-line zero term x^{0.6}cos(14.13 log x)/|ρ(ρ−1)|. It escapes the √x band upward.
  * End card: three-tier "certainty ladder" (formal proof checked / classical math / sketch and readings).

---

## (b) Tempting but WRONG simplifications to avoid

1. **"RH means ψ(X) = X + O(√X)."** Wrong. The equivalence needs X^{1/2+ε} (or √X log²X under RH). Even √X log log log X
   is too small, by Hardy–Littlewood.
2. **"The function-field RH implies, or was extended to, the classical RH."** No. It is an analogy (Bombieri: "too
   compelling to be dismissed"), not a logical step.
3. **"Stepanov's method gives the sharp 2√q bound directly."** It gives q + O(√q) as an upper bound with a worse
   constant. The lower bound and the sharp 2g√q need further tricks: the twisted curve, the trace formula, the
   tensor-power trick.
4. **"Multiplicity is always ~√q in Stepanov/Bombieri."** In Bombieri's square-q version, as Tao presents it, the
   vanishing is first order and √q enters through Frob_{√q}. Say "in Stepanov's version".
5. **"Theta lifts literally create zeros of high multiplicity" / "the proof differentiates integers."** No.
   * Per the guides, the chain produces *divisibility by primes* (p-adic "multiplicity").
   * The derivatives are of theta functions, whose values are then divisible.
   * "Differentiating whole numbers" is the note's figure of speech for what is missing over ℤ.
6. **"A theta function and a theta lift are the same thing."** No. A theta function is a series. A theta lift is an
   integral transform with a theta kernel, between the two groups of a dual pair.
7. **"The √X chain length is where the zeros on the critical line come from" / "√X counts something about zeros."**
   No. It is the balance point of two error terms, X/m against m, in an inequality about primes.
8. **"The proof uses Weil's positivity criterion / the Guinand–Weil sign / a Stepanov determinant."** These appear in
   the note's timeline of discovery.
   * Jaswal found no counterpart in the code for steps 1 and 4.
   * Rubinstein did not find steps 3 (most of it), 4 and 6.
   * The final route is a one-sided "divisibility ≤ size" bound plus Landau-type theorems.
9. **"Humans have checked and understood the proof."** What is certified is the *formal* Lean proof.
   * The note: "before having mastered a massive neighbourhood around its mathematics".
   * The guides that explain it were produced with heavy AI help and read statements, not all proofs.
10. **"It proves GRH for all L-functions."** The checked statements cover ζ and Dirichlet L-functions only
    (Sutherland). The note's "Extended Riemann Hypothesis" is only an expectation: "I expect, with more time".
11. **"Claude proved it alone."** The note: "working with Claude"; Alpöge guided the strategy ("I guided us to the
    right situation analogous to that toy setting").
12. **"The 17M lines / 250,000+ pages show the idea is irreducibly complicated."**
    * The note: "incredibly long at the moment", "strange suboptimal choices", "massively simplified, likely
      immediately".
    * The 250,000+ pages are the unpublished informal write-up, not the Lean code (see guides.md §6).
13. **"Every zero has been shown numerically to be on the line" as the proof.** Numerical verification is not the
    proof. The proof is a formal, analytic and arithmetic argument.
14. **"The functional equation alone puts zeros on the line."** It only gives the symmetry s ↔ 1 − s. The proof needs
    the one-sided bound for Re s > 1/2; the symmetry then gives Re s < 1/2.

---

## (c) Worked numeric examples (all numbers [computed here])

### C1. Points of y² + y = x³ − x over 𝔽₁₃

* This is the same curve that `rh/zeta.py` uses (labelled 37.a1 there).
* LMFDB blocked my fetch with a CAPTCHA, so the label was not rechecked. The counts below are brute force and agree
  with zeta.py's (p, N, a_p) = (13, 16, −2).

| x | x³ − x mod 13 | y with y² + y ≡ that (mod 13) | # |
|---|---|---|---|
| 0 | 0 | 0, 12 | 2 |
| 1 | 0 | 0, 12 | 2 |
| 2 | 6 | 2, 10 | 2 |
| 3 | 11 | — | 0 |
| 4 | 8 | — | 0 |
| 5 | 3 | 6 | 1 |
| 6 | 2 | 1, 11 | 2 |
| 7 | 11 | — | 0 |
| 8 | 10 | — | 0 |
| 9 | 5 | — | 0 |
| 10 | 2 | 1, 11 | 2 |
| 11 | 7 | 4, 8 | 2 |
| 12 | 0 | 0, 12 | 2 |

* Check one row by hand: x = 2 gives 8 − 2 = 6. y = 2 gives 4 + 2 = 6 ✓. y = 10 gives 110 = 8·13 + 6 ✓.
* x = 5 has one y (y = 6: 42 = 3·13 + 3), the double root of y² + y − 3. 4·3 + 1 = 13 ≡ 0, so the discriminant
  vanishes.
* **Totals:**
  * Affine solutions = 15; plus the point at infinity, **N = 16**.
  * q + 1 = 14, so |N − (q+1)| = **2 ≤ 2√13 = 7.211** ✓.
  * a₁₃ = q + 1 − N = −2.
* **Zeta zeros:**
  * P(T) = 1 − a·T + 13T² = 1 + 2T + 13T².
  * Roots T = (−2 ± i√48)/26 = −0.07692 ± 0.26647i.
  * **|T| = 0.27735 = 13^{−1/2}**. Exactly: |T|² = (4 + 48)/676 = 1/13.
  * So Re s = 0.5000 for T = 13^{−s}.
  * Inverse roots α, β = −1 ∓ 3.4641i, with |α| = √13 = 3.6056.
* **Over 𝔽₁₆₉ (= 𝔽₁₃[i], i² = 2; 2 is a non-residue mod 13):**
  * Brute force gives **N₂ = 192**.
  * Prediction: 13² + 1 − (α² + β²) = 170 − (−22) = 192 ✓.
  * |N₂ − 170| = 22 ≤ 2·13 = 26 ✓.
* **Larger primes, same curve:**

| p | N | N − (p+1) | 2√p | ratio |
|---|---|---|---|---|
| 101 | 99 | −3 | 20.10 | 0.149 |
| 1,009 | 1,057 | 47 | 63.53 | 0.740 |
| 10,007 | 9,942 | −66 | 200.07 | 0.330 |

* zeta.py: 667 primes ≤ 5,000, max |a_p|/(2√p) = 0.9965.

### C2. Stepanov parameters: where √q comes from

* Source: Tao's survey, Lemma 4.7 and Prop. 4.5 (C affine, y² = f(x), f cubic, q odd).
* If (q − 10m)(d − 10) > m(q + 10d + 20m), then N ≤ (dq + q)/m + 3.
* Approximation: bound ≈ q + 11q/m + 40m, minimised at m ≈ √(11q/40) ≈ 0.524√q, giving error ≈ 2√(440q) ≈ 42√q.
  The exact integer optimum agrees (table in §3: m = 520 at q = 10^6).
* At q = 10^6:
  * m = 1: N ≤ 13q.
  * m = 10: N ≤ 2.2q.
  * m = 100: N ≤ 1.12q.
  * m = 520: N ≤ 1.0423q, i.e. q + 42,311.
  * m = 3,000: N ≤ 1.13q.
  * The Hasse bound is q + 2,000 (affine count up to ±1).

### C3. Chebyshev / Erdős "divisibility ≤ size" in one line

* C(20,10) = 184,756 = 4 × 46,189.
* 46,189 = 11·13·17·19, the product of the primes in (10, 20].
* So 46,189 ≤ 184,756 ≤ 4^{10} = 1,048,576.

### C4. The note's smoothed sum G(x) (Rubinstein's statistic)

* G(10^4) = 1.749, G(10^5) = 3.671, G(10^6) = 11.040, G(2·10^6) = −12.268.
* Compare log 2π = 1.838 and 0.0462√x = 4.6 / 14.6 / 46.2 / 65.3.

### C5. Theta symmetry

* Θ(0.5) = 1.4195, Θ(2) = 1.0037, and √0.5 × 1.4195 = 1.0037.

---

## Open questions / not verified

* Whether "Riemann's second proof" is the right name for the theta proof of the functional equation (standard usage;
  not checked against Riemann 1859 here).
* The exact meaning of the note's W(·) functional and of "Guinand-Weil had the sign". These are only interpretations;
  the guides did not find steps 4 and 6 in the code.
* Whether the X/m + m accounting in Rubinstein / Jaswal is the *whole* story of the exponent 1/2. Jaswal names a second
  place: the auxiliary twisted sums.
* LMFDB label 37.a1 not re-verified (CAPTCHA). The point counts are self-verified by brute force.
* Iwaniec–Kowalski ch. 11 was not consulted. Tao's survey, Croot's and Hanson's notes and Tao's 2014 post were used
  instead.
