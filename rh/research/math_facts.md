# Math background facts: verification report (area: math)

Compiled 2026-11-22. Every fact has a URL and a short verbatim quote (30 words or fewer). Status values:
**verified** (a primary or reliable source says it), **corrected** (the claim as given needs a change, with the right value),
**reported** (secondary sources only), **unverified** (no source found).
Local copies of every source are in `/home/user/rhwork/sources/math/`.
Access problems: Odlyzko's site at umn.edu failed TLS verification, LMFDB's list pages and ams.org sent bot challenges,
and the Wayback Machine reset the connection. Where those sources were wanted, OEIS, arXiv copies, Crossref metadata
and a local mpmath 1.4.1 computation were used instead.

---

## 1. Riemann 1859: venue, date, length (status: **corrected**, length only)

- **Venue and date are right.** The paper was "first published in the Monatsberichte der Berliner Akademie, in November 1859."
  https://www.claymath.org/collections/riemanns-1859-manuscript/
  (D. R. Wilkins' edition says the same: https://www.maths.tcd.ie/pub/HistMath/People/Riemann/Zeta/)
- **The printed volume came out in 1860, on pp. 671–680, so the paper is 10 printed pages.** Bombieri's Clay
  reference reads: "Monat. der Königl. Preuss. Akad. der Wissen. zu Berlin aus der Jahre 1859 (1860), 671–680"
  https://www.claymath.org/wp-content/uploads/2022/05/riemann.pdf
  Gabcke gives the same pages: "Monatsberichte der Berliner Akademie 1859, Berlin, 1860, 671–680"
  https://www.claymath.org/wp-content/uploads/2023/04/Gabcke.pdf
- **"Six pages" refers to a manuscript, not the print.** Clay says: "Just six manuscript pages in length". That
  six-page manuscript is a fair copy, and both Clay and Gabcke now attribute it to Alfred Clebsch. Clay: "it is more
  plausible that MS A is not in Riemann's hand". Riemann's own draft, MS B, "is dated October 1859, the month in which
  Riemann submitted his paper".
  https://www.claymath.org/notes-on-the-1859-manuscript/
- **Reprints.** The *Werke* reprinted the paper on pp. 136–144 (1876) and pp. 145–155 (2nd ed., 1892), per Gabcke and
  Bombieri.
- **For narration:** "a ten-page paper" (printed), or "a short paper of about ten pages". Avoid "eight pages".

## 2. Euler (status: **verified**, with date nuance and one conflicting source)

- **Basel problem, ζ(2) = π²/6.** The English translation of E41 is footnoted "Presented to the St. Petersburg Academy
  on December 5, 1735." https://arxiv.org/pdf/math/0506415
  The Euler Archive record for E41 gives "Published Date 1740 / Written Date 1735".
  https://scholarlycommons.pacific.edu/euler-works/41/
  Lagarias: "Euler solved the Basel problem by 1735 with his famous result that ζ(2) = π²/6."
  https://arxiv.org/pdf/1303.1856 (Bull. AMS 2013)
  The often-quoted "1734" for the discovery itself comes from secondary sources (Wikipedia) and is **reported** only.
  Safe wording: "1735".
- **Euler product: 1737 is correct.** The Euler Archive record for E72 says: "This is the paper in which Euler product
  expansions first appeared." It lists "Written Date 1737", "Published Date 1744".
  https://scholarlycommons.pacific.edu/euler-works/72/
  Lagarias: "around 1737, not published until 1744, Euler [99, E72] obtained the 'Euler product' expansion of the
  zeta function." His reference list adds "(Presented April 25, 1737)". https://arxiv.org/pdf/1303.1856
  - **Conflicting source.** Bombieri's Clay description says the Euler product "appears for the first time in Euler's
    book Introductio in Analysin Infinitorum, published in 1748."
    https://www.claymath.org/wp-content/uploads/2022/05/riemann.pdf
    E72 (1737/1744) is the standard attribution, so use 1737.

## 3. Hilbert's 23 problems; RH is part of the 8th (status: **verified**)

- Newson's translation (Bull. AMS 8, 1902) has the heading "8. Problems of prime numbers". The problem asks Hilbert's
  audience to prove "an exceedingly important statement of Riemann, viz., that the zero points of the function ζ(s)
  ... all have the real part 1/2". The same problem also covers Goldbach and twin primes.
  https://mathcs.clarku.edu/~djoyce/hilbert/problems.html
- **Date of the lecture.** MacTutor: "David Hilbert gave a talk at the International Congress of Mathematicians in Paris
  on 8 August 1900 in which he described 10 from a list of 23 problems."
  https://mathshistory.st-andrews.ac.uk/Extras/Hilbert_Problems/
  Clay gives "August 9, 1900" (https://www.claymath.org/millennium-problems/). Use 8 August, or just "1900".
- **Only 10 problems were presented aloud;** all 23 were in the printed paper.

## 4. Clay Millennium Prize (status: **verified**)

- "The prizes were announced at a meeting in Paris, held on May 24, 2000 at the Collège de France."
  It is "a $7 million prize fund ... with $1 million allocated to the solution of each problem."
  https://www.claymath.org/millennium-problems/
- **Prize rules, useful context for the proof story.** "(i) the proposed solution must be published in a Qualifying
  Outlet ..., and (ii) at least two years must have passed since publication, and (iii) ... general acceptance".
  https://www.claymath.org/millennium-problems/rules/
- **Clay's RH page, as fetched today,** still labels the problem "Unsolved" and says: "This has been checked for the
  first 10,000,000,000,000 solutions." https://www.claymath.org/millennium/riemann-hypothesis/

## 5. Prime number theorem, 1896 (status: **verified**)

- Clay: "ideas which led, in 1896, to independent proofs by Hadamard and de la Vallée Poussin of the prime number
  theorem." https://www.claymath.org/collections/riemanns-1859-manuscript/
- **Hadamard's paper.** "Sur la distribution des zéros de la fonction ζ(s) et ses conséquences arithmétiques",
  Bull. SMF 24 (1896), 199–220 (Crossref DOI 10.24033/bsmf.545).
- **De la Vallée Poussin's paper.** "Recherches analytiques la théorie des nombres premiers." Ann. Soc. scient.
  Bruxelles 20, 183-256, 1896 (MathWorld bibliography). https://mathworld.wolfram.com/PrimeNumberTheorem.html

## 6. von Mangoldt's explicit formula (1895); ψ(x) = Σ_{n≤x} Λ(n) (status: **verified**)

- Moree, Petrykiewicz and Sedunova: the explicit formula "is called the 'explicit formula' and due to von Mangoldt. He
  showed in 1895 that for x > 1 and x not a prime power we have" ψ(x) = x − Σ_ρ x^ρ/ρ − ζ′(0)/ζ(0). Here the sum is
  over all zeros, trivial ones included. https://arxiv.org/pdf/1810.05244
  - The form with only the nontrivial zeros is ψ(x) = x − Σ_ρ x^ρ/ρ − log 2π − ½ log(1 − x⁻²).
    https://mathworld.wolfram.com/ExplicitFormula.html
- **The 1895 paper.** "Zu Riemanns Abhandlung 'Ueber die Anzahl der Primzahlen unter einer gegebenen Grösse'",
  J. reine angew. Math. 114 (1895), 255–305 (Crossref DOI 10.1515/crll.1895.114.255).
- **Definition of ψ.** Moree et al.: "One often sees the ψ-function defined as ψ(x) = Σ_{n≤x} Λ(n), where Λ(n), the von
  Mangoldt function, equals log p if n is a power of a prime p". https://arxiv.org/pdf/1810.05244
  Chebyshev's original form was ψ(x) = ϑ(x) + ϑ(x^{1/2}) + ϑ(x^{1/3}) + … (Bombieri, Clay PDF above).

## 7. RH equivalences (status: **verified**)

- **von Koch 1901.** Moree et al.: "von Koch, who showed in 1901 that the RH is equivalent to the formula π(x) = Li(x)
  + O(E(x)), E(x) = x^{1/2} log x." https://arxiv.org/pdf/1810.05244
  The paper is "Sur la distribution des nombres premiers", Acta Math. 24 (1901), 159–182 (Crossref DOI
  10.1007/BF02403071).
- **Li versus li.** Bombieri defines Li(x) = ∫₀^x dt/log t as a Cauchy principal value, which is the same function
  as li. Li from 2 differs from it only by a constant, so the O-term is unaffected.
- **Schoenfeld 1976 (π bound).** Johnston: "In 1976, Schoenfeld [Sch76, Corollary 1] proved that under assumption of
  the Riemann hypothesis, |π(x) − li(x)| < √x/8π log x, for x ≥ 2657." https://arxiv.org/pdf/2109.02249
  The paper is Math. Comp. 30 (1976), 337–360 (Crossref DOI 10.1090/S0025-5718-1976-0457374-X; ams.org itself was
  not reachable).
- **Schoenfeld 1976 (ψ bound).** Under RH, |ψ(x) − x| ≤ √x (log x)²/(8π) "for all x ≥ 73.2". Lee and Nosal collect
  this "from Schoenfeld [16] and Grenié–Molteni [9]". https://arxiv.org/pdf/2312.05628
- **ψ form of RH.** "the RH is equivalent with ψ(x) = x + O(x^{1/2} log² x)." https://arxiv.org/pdf/1810.05244

## 8. Zeros on the critical line (status: **verified**; the 2026 papers exist, with details below)

| Year | Result | Source and quote |
|---|---|---|
| 1914 | Hardy: infinitely many zeros on the line | "It was proved for the first time by Hardy [1] in 1914 that ζ(s) has infinitely many zeros on the critical line". Reference: C. R. 158 (1914), 1012–1014. Bombieri, Bourbaki exp. 465: https://www.numdam.org/item/SB_1974-1975__17__176_0.pdf |
| 1942 | Selberg: a positive proportion | "In 1942 Selberg showed that a positive fraction of all non-trivial zeros are critical". About 7·10⁻⁸ when made explicit. https://arxiv.org/pdf/1810.05244. Reference: Skr. Norske Vid. Akad. Oslo (1942) no. 10, 1–59 (Bourbaki 465). Bombieri's Clay PDF cites instead a 4-page note in Norske Vid. Selsk. Forh. 15 (1942), 59–62. |
| 1974 | Levinson: > 1/3 | Title: "More than one third of zeros of Riemann's zeta-function are on σ = 1/2", Adv. Math. 13 (1974), 383–436 (Crossref). The constant is "c2 = 0.3474" (arXiv 1810.05244). |
| 1989 | Conrey: > 2/5 | "More than two fifths of the zeros of the Riemann zeta function are on the critical line", J. reine angew. Math. 399 (1989), 1–26 (Crossref). The constant is 0.4088. Later records: "0.4105 by Bui, Conrey and Young [7], and 0.4128 by Feng [22]" (arXiv 1810.05244). |
| 2020 | Pratt, Robles, Zaharescu, Zeindler: > 5/12 | "More than five-twelfths of the zeros of ζ are on the critical line", Res. Math. Sci. 7 (2020) (Crossref DOI 10.1007/s40687-019-0199-8). |
| Aug 2026 | Alpöge & Furman: ≥ 2/3 simple and on the line | arXiv 2608.13637, submitted 13 Aug 2026: "at least two thirds ... are simple and lie on the critical line, and that at least five sixths are distinct; the previous unconditional records are 5/12 and 0.6603." With the Montgomery–Taylor window the constants are 0.6725 and 0.8362. The comments say: "Proof discovered autonomously by Claude (Anthropic)". https://arxiv.org/abs/2608.13637 . Anthropic's post of Aug 10, 2026: "it has increased this bound from 41.6% to 67.2%." https://www.anthropic.com/research/riemann-zeta |
| Sep 2026 | Lamzouri: a new proof | arXiv 2609.02882, submitted 2 Sep 2026: "more than 67.25% ... are simple and on the critical line, and that at least 83.62% ... are distinct", plus 88.76% "simple or lie on the critical line". https://arxiv.org/abs/2609.02882 |
| Sep 2026 | Biao Wang: + 6.67·10⁻⁸ | arXiv 2609.24167 (21 Sep 2026): improves C₀ = 0.67250… by "δ0 = 6.66624…×10⁻⁸". https://arxiv.org/abs/2609.24167 |
| Sep 2026 | **arXiv 2609.33043** | Kristian Muri Knausgård, "More than 83.69% of the zeros of the Riemann zeta function are distinct". Submitted 27 Sep 2026, v2 7 Oct 2026. The bound is "at least 0.8369928814…". This paper is about **distinct** zeros, not zeros on the critical line. https://arxiv.org/abs/2609.33043 |
| Oct 2026 | **arXiv 2610.08965** | Same author, title verified: "More than 83.9% of the zeros of the Riemann zeta function are distinct and more than 67.35% are simple and on the critical line". Submitted 6 Oct 2026. It proves "liminf N_0^s(T)/N(T) >= 0.67353...", and 88.93% simple or on the line. It is "proved in Lean 4 ... three axioms beyond those of Mathlib, one per inequality", each recording a search-program result. https://arxiv.org/abs/2610.08965 |
| Oct 2026 | Cobeli & Zaharescu: > 8/9 simple **or** on the line | arXiv 2610.23467 (16 Oct 2026): "simple or lie on the critical line, is greater than 8/9". 8/9 = 88.89%, which is numerically below Knausgård's 88.93%. https://arxiv.org/abs/2610.23467 |

Notes on these records:
- The 2026 papers are preprints and not refereed.
- **Best current unconditional figure** found for "simple and on the critical line" is **> 67.35 %** (Knausgård,
  2610.08965). It rests on computer-checked inequalities recorded as axioms, and its own abstract says the same as of
  writing.
- **Do not say "more than two thirds are on the line" without "simple and".**
- Bombieri's Clay text says only "more than 40 %"; it dates from 2000.

## 9. Numerical verification (status: **verified**)

- **Platt and Trudgian.** "Theorem 1. The Riemann hypothesis is true up to height 3 000 175 332 800. That is, the
  lowest 12 363 153 437 138 non-trivial zeroes ρ have ℜρ = 1/2." https://arxiv.org/pdf/2004.09765
  - Journal: Bull. London Math. Soc. 53(3), 792–797 (2021), per Crossref for DOI 10.1112/blms.12460.
  - **So: about 12.36 trillion zeros.**
  - The method is rigorous: "in a rigorous way using interval arithmetic" (arXiv abstract).
- **Gourdon (2004).** "verification of the Riemann Hypothesis on all the first 10^13 non trivial zeros"
  http://numbers.computation.free.fr/Constants/Miscellaneous/zetazeros1e13-1e24.pdf
  - Platt and Trudgian give Gourdon's height: "H = 2.44 . . . · 10^12".
  - On peer review they write: "neither has been published in a peer reviewed journal".
  - Gourdon also computed "two billion zeros from the 10^24-th zero".
- **Newer record: none found.** Searches on 2026-11-22 found no published verification beyond 3·10¹². The LMFDB
  dataset says: "the first 103,800,788,359 zeros ... all of which have real part 1/2"
  (https://www.lmfdb.org/zeros/zeta/). That is fewer zeros than Platt and Trudgian's.
  - Odlyzko checked selected intervals much higher up. Bombieri: "the Riemann hypothesis holds for over 3 × 10^8 zeros
    at heights up to 2 × 10^20" (Clay PDF).

## 10. First zeros, the 100th zero, and N(100) (status: **verified**; the 12-decimal values given are truncations)

Sources:
- Zeros 1–5: the OEIS decimal-expansion entries A058303, A065434, A065452, A065453 and A192492
  (https://oeis.org/A058303 and the others). A058303 is "Decimal expansion of the imaginary part of the first
  nontrivial zero".
- All of the values below: computed here with mpmath 1.4.1 `zetazero(n)` at 40 digits. The OEIS digits agree with
  them.
- Odlyzko's tables and LMFDB's list could not be fetched (see the note at the top).

| n | Im ρₙ (25 sig. digits, mpmath) | Value given in the claim | Rounded to 12 decimals |
|---|---|---|---|
| 1 | 14.13472514173469379045725 | 14.134725141734… ✓ | 14.134725141735 |
| 2 | 21.02203963877155499262848 | 21.022039638771… ✓ | 21.022039638772 |
| 3 | 25.01085758014568876321379 | 25.010857580145… ✓ | 25.010857580146 |
| 4 | 30.42487612585951321031190 | 30.424876125859… ✓ | 30.424876125860 |
| 5 | 32.93506158773918969066237 | 32.935061587739… ✓ | 32.935061587739 |
| 6 | 37.58617815882567125721776 | 37.586178158825… ✓ | 37.586178158826 |
| 7 | 40.91871901214749518739813 | 40.918719012147… ✓ | 40.918719012147 |
| 8 | 43.32707328091499951949612 | 43.327073280914… ✓ | 43.327073280915 |
| 9 | 48.00515088116715972794247 | 48.005150881167… ✓ | 48.005150881167 |
| 10 | 49.77383247767230218191678 | 49.773832477672… ✓ | 49.773832477672 |
| 100 | 236.5242296658162058024755 | 236.524229665816 ✓ | 236.524229665816 |

- **Every value in the claim is a correct truncation.** If you show them on screen, either keep the "…" or use the
  rounded column.
- **Number of zeros with 0 < t < 100 is 29.** OEIS A072080, "Number of (nontrivial) zeros of zeta(z) with
  0 < Im(z) < 10^n", begins 0, 29, 649, 10142 with offset 1, so the term for 10² is 29. https://oeis.org/A072080
  mpmath `nzeros(100)` also gives 29. The 29th zero is at 98.8311942…, the 30th at 101.3178510….
- **Nearest integers** to the zero heights: 14, 21, 25, 30, 33, 38, 41, 43, 48, 50 (OEIS A002410).

## 11. Function fields (status: **verified**, with date corrections for Hasse and Bombieri)

- **Hasse.** The dates are 1933 (announcement), 1934 and 1936, not "1933/1936" alone.
  - Roquette (in German) says "Schon im April 1933 legte Hasse eine Beweisskizze für elliptische Funktionenkörper vor",
    that is, already in April 1933 Hasse presented a proof sketch for elliptic function fields. It appeared "als
    'Vorläufige Mitteilung' in den Nachrichten ... zu Göttingen", Nachr. Ges. Wiss. Göttingen (1933) 253–262.
    https://www.mathi.uni-heidelberg.de/~roquette/hasse-rv.pdf
  - 1934: Abh. Math. Sem. Hamburg 10 (1934), 325–348 (Crossref).
  - 1936: the full algebraic proof, J. reine angew. Math. 175 (1936), parts I–III (Crossref).
  - Bombieri's Clay text: "If g = 1, a proof was obtained by Hasse in 1934."
  - **For narration:** "Hasse, 1933" is fine.
- **Weil.** 1940 is the announcement and 1948 the full proof, which matches the claim.
  - The 1940 note is "Sur les fonctions algébriques à corps de constantes fini", C. R. Acad. Sci. Paris 210 (1940),
    592–594. Hindry (in French) says it was a "note ... de trois pages" (a three-page note), "présentée ... lors de la
    séance du 22 avril 1940" (presented at the session of 22 April 1940), and written in Rouen prison.
    https://proceedings.centre-mersenne.org/item/10.5802/xups.2012-02.pdf
  - 1941: PNAS 27, 345–347 (Crossref).
  - 1948: Bombieri: "settled by Weil in the early 1940s ... his results were eventually published in book form in 1948".
- **Deligne.** "La conjecture de Weil : I", Publ. Math. IHÉS 43 (1974), 273–307 (Crossref DOI 10.1007/BF02684373).
  Weil II followed in 1980.
- **Stepanov 1969.** "On the number of points of a hyperelliptic curve over a finite prime field", Izv. Akad. Nauk SSSR
  Ser. Mat. 33 (1969). Bombieri gives pp. 1103–1114, and Crossref gives the same pages for the English translation in
  Math. USSR-Izv. 3. The Russian original's pagination was not checked.
- **Bombieri.** The claim's "1974" is the publication year; the talk was in 1973.
  - The talk: Séminaire Bourbaki exposé no. 430, "Counting points on curves over finite fields [d'après S. A.
    STEPANOV]", dated "Juin 1973", season 1972/73. It was printed in 1974 (Lecture Notes in Math. 383).
    https://www.numdam.org/item/SB_1972-1973__15__234_0.pdf
  - What it says about Stepanov and Schmidt: "a new approach to (3) invented by S. A. Stepanov ... a proof in the
    general case has been also obtained by W. Schmidt."
  - **The multiplicity link to Alpöge's remark.** Stepanov's function "vanishes at every k-rational point of C, of
    order ≥ m". In Bombieri's words: "In the final choice, m is about q^½." The ≥ sign and the exponent ½ are garbled
    in the scanned text layer of the numdam PDF, so check them against the page image before putting them on screen.
    Alpöge's remark speaks of "a divisor involving multiplicity" and a chain length of √X.
- **Schmidt.** W. M. Schmidt, *Equations over Finite Fields: An Elementary Approach*, LNM 536 (1976) (Crossref).

## 12. Montgomery, Dyson, Odlyzko, GUE (status: **verified**)

- **Montgomery 1973.** "The pair correlation of zeros of the zeta function", Proc. Sympos. Pure Math. 24 (1973),
  181–193 (Crossref DOI 10.1090/pspum/024/9944).
- **Conrey.** "In 1972 H. L. Montgomery announced a remarkable connection between the distribution of the zeros ... and
  the distribution of eigenvalues of large random Hermitian matrices." Also: "Dyson responded that the integrand was
  the pair-correlation function for eigenvalues of large random Hermitian matrices, or more specifically the Gaussian
  Unitary Ensemble, or GUE." https://arxiv.org/pdf/math/0005300
- **The tea.** Dartmouth Chance News: "In a brief conversation in the Institute tea room ... Dyson and Montgomery
  discovered that it looked as though they had been studying the same thing!"
  https://chance.dartmouth.edu/chance_news/recent_news/primes_part3/part3.html
  - Montgomery's own recollection is quoted from K. Sabbagh, *Dr. Riemann's Zeros* (2002), pp. 134–136: "As far as I
    know ... he didn't think about it after this five-minute conversation."
    https://empslocal.ex.ac.uk/people/staff/mrwatkin//zeta/dyson.htm
  - Brian Hayes' dramatised retellings of the scene are not verbatim records.
- **Odlyzko 1987.** "On the distribution of spacings between zeros of the zeta function", Math. Comp. 48 (1987),
  273–308. The abstract says the study is based on "the first 10^5 zeros and for zeros number 10^12 + 1 to
  10^12 + 10^5", and that "The agreement ... is generally good, and improves at larger heights."
  https://web.physics.rutgers.edu/grad/682/papers/zeta.pdf (a copy of the AMS paper)

## 13. Robin (1984) and Lagarias (2002) (status: **verified**)

- **Robin.** Lagarias: "Robin's criterion states that the Riemann hypothesis is true if and only if σ(n) < e^γ n log log
  n for all n ≥ 5041". That is the same as n > 5040.
  - Robin's paper: "Grandes valeurs de la fonction somme des diviseurs et hypothèse de Riemann", J. Math. Pures Appl.
    63 (1984), 187–213. https://arxiv.org/pdf/math/0008177
  - MathWorld lists the failures, which end at 5040: "... 720, 840, 2520, and 5040".
    https://mathworld.wolfram.com/RobinsTheorem.html
- **Lagarias.** "Let Hn = Σ 1/j. Show that, for each n ≥ 1, Σ_{d|n} d ≤ Hn + exp(Hn) log(Hn), with equality only for
  n = 1." This is "equivalent to the Riemann hypothesis".
  - Published in Amer. Math. Monthly 109 (2002), 534–543 (Crossref).
- **Link to the Lean proof.** Sutherland's page formalises both inequalities (`robin_inequality` for 5040 < n,
  `lagarias_inequality`) from the Lean proof of RH. See drew_grh.txt.

## 14. Riemann's Nachlass, Siegel (1932), Riemann–Siegel formula (status: **verified**)

- **Riemann computed zeros himself.** Bombieri: "the first numerical computation of the first few zeros of the zeta
  function already appears in Riemann's Nachlass". He adds that the Nachlass "was analyzed in depth by C.L. Siegel
  [Sie]".
  - Siegel's paper: "Über Riemanns Nachlaß zur analytischen Zahlentheorie", Quellen und Studien zur Geschichte der
    Mathematik, Astronomie und Physik 2 (1932), 45–80.
    https://www.claymath.org/wp-content/uploads/2022/05/riemann.pdf
- **How the formula was found.** Moree et al.: "In 1926, while in Göttingen, Bessel-Hagen discovered a previously
  unknown approximate formula in Riemann's notes. Siegel then analysed the notes ... and in 1932 published them."
  "One of these is now known as the Riemann-Siegel formula." https://arxiv.org/pdf/1810.05244

## 15. Mathlib's `RiemannHypothesis` (status: **verified**; it matches Sutherland's page)

The Mathlib documentation page, built from mathlib4 commit `a495318f…`, shows the definition verbatim:

```
def RiemannHypothesis : Prop
A formal statement of the Riemann hypothesis – constructing a term of this type is worth a million dollars.
Equations: RiemannHypothesis = ∀ (s : ℂ), riemannZeta s = 0 → (¬∃ (n : ℕ), s = -2 * (↑n + 1)) → s ≠ 1 → s.re = 1 / 2
```
https://leanprover-community.github.io/mathlib4_docs/Mathlib/NumberTheory/LSeries/RiemannZeta.html#RiemannHypothesis

Sutherland's page (`/home/user/rhwork/sources/drew_grh.txt`) gives the source form:

```
def RiemannHypothesis : Prop :=
  ∀ (s : ℂ) (_ : riemannZeta s = 0) (_ : ¬∃ n : ℕ, s = -2 * (n + 1)) (_ : s ≠ 1), s.re = 1 / 2
```

- **These are the same proposition.** In Lean, an anonymous binder `(_ : P)` is a non-dependent Π type, so the docs
  print it as the arrow `P → …`. `↑n` is the cast from ℕ to ℂ that elaboration inserts.
- The Lean FRO statement points to the same Mathlib declaration: "This statement is part of Mathlib: RiemannHypothesis
  and has been carefully vetted by experts".
- **Caveats.**
  - The docs page shows the current Mathlib master. The proof was built against Mathlib v4.33.1 (per Sutherland). I did
    not check that the docs commit is v4.33.1, but the definition text is the same.
  - The docstring's "million dollars" is a Mathlib joke, not a Clay statement.
  - The s ≠ 1 condition is there because "Mathlib assigns ζ a conventional value at its pole" (Sutherland).

## 16. Weil's positivity criterion (1952) and Guinand (1948) (status: **verified**)

- **Weil 1952.** "Sur les 'formules explicites' de la théorie des nombres premiers", Meddelanden Från Lunds Univ. Mat.
  Sem. (dédié à M. Riesz), (1952), 252–265 (Bombieri's Clay PDF, reference [We3]).
- **The criterion.** Bombieri: "Weil also proved that the Riemann hypothesis is equivalent to the negativity of the
  right-hand side for all functions f(x) of type f(x) = ∫₀^∞ g(xy) ḡ(y) dy" with ∫ g(x) dx/x = ∫ g(x) dx = 0.
  https://www.claymath.org/wp-content/uploads/2022/05/riemann.pdf
  - In Bombieri's sign convention the right-hand side is the prime side. With these conditions f̂(0) = f̂(1) = 0, so the
    criterion says the zero sum Σ_ρ f̂(ρ) is ≥ 0.
  - In plain words: RH holds if and only if a certain explicit-formula functional is nonnegative on test functions of
    the form f = g ∗ g̃. That is the claim as given.
- **Guinand 1948.** "A Summation Formula in the Theory of Prime Numbers", Proc. London Math. Soc. (2) 50 (1948),
  107–119 (Crossref DOI 10.1112/plms/s2-50.2.107).
- **Where it shows up in 2026.**
  - Anthropic's Aug 2026 post describes Claude's 2/3 result as using "a suitable space of functions with quadratic form
    induced by Weil".
  - Lamzouri's abstract: "a finite-dimensional matrix representation of Weil's Hermitian form".
  - Alpöge's remark: "Guinand-Weil had the sign".

## 17. Pronunciations for narration

Confidence scale: **H** means sourced IPA or standard dictionary usage; **M** means standard orthography of the
language but no specific source; **L** means a guess.

| Name | Respelling for narration | IPA | Source and confidence |
|---|---|---|---|
| Riemann | REE-mahn | /ˈriːmɑːn/ (also -mən); German [ˈʁiːman] | Wikipedia `{{IPAc-en|ˈ|r|iː|m|ɑː|n|...}}`. **H** |
| Euler | OY-ler | /ˈɔɪlər/ | Wikipedia: "the pronunciation /ˈjuːlər/ YOO-lər is considered incorrect". **H** |
| Gauss | GOWSS (rhymes with "house") | /ɡaʊs/; German [ɡaʊs] | Wikipedia. **H** |
| Dirichlet | DEER-ih-KLAY | /ˌdɪərɪˈkleɪ/; German [diʁiˈkleː] | Wiktionary and Wikipedia. **H** |
| Hadamard | ah-dah-MAR (English often HAD-uh-mar) | French [adamaʁ] | Wikipedia. **H** for the French |
| de la Vallée Poussin | duh lah vah-LAY poo-SAN (nasal final "n") | French [də la vale pusɛ̃] | Built from standard French readings of "vallée" and "Poussin"; no IPA on Wikipedia. **M** |
| von Mangoldt | fon MAHN-golt | German [fɔn ˈmaŋɡɔlt] | German orthography; no source IPA. **M** |
| Hasse | HAH-suh | German [ˈhasə] | Wikipedia. **H** |
| Weil | VAY | /veɪ/; French [vɛj] | Wikipedia (cites Dictionary.com). **H** |
| Deligne | duh-LEEN-yuh (or duh-LEEN) | French [dəliɲ] | Wikipedia. **H** |
| Stepanov | stih-PAH-nuf (stress on the 2nd syllable) | Russian Степа́нов [stʲɪˈpanəf] | English Wiktionary marks the stress: Степа́нов. **H** for the stress |
| Bombieri | bom-BYEH-ree | Italian [bomˈbjɛːri] | Italian orthography (penultimate stress); no source IPA. **M** |
| Montgomery | mont-GUM-uh-ree | /məntˈɡʌm(ə)ri/ | Wiktionary. **H** |
| Odlyzko | oh-DLIZ-koh (common US reading; unverified) | Polish original Odłyżko ≈ [ɔdˈwɨʂkɔ] | No source found for how he says it. Born Andrzej Odłyżko in Tarnów (Wikipedia mirror). **L** |
| Hilbert | HIL-bert | /ˈhɪlbərt/; German [ˈhɪlbɐt] | Wikipedia. **H** |
| Chebyshev | CHEB-ih-shef (usual English) or cheh-bih-SHOFF (Russian stress) | Russian Чебышёв [tɕɪbɨˈʂof] | Wikipedia gives the Russian. **H** for the Russian, **M** for the English |
| Mathlib | MATH-lib | /ˈmæθlɪb/ | Compound of "math" + "lib(rary)". **H** |
| Lean | LEEN | /liːn/ | The English word. **H** |
| **Levent Alpöge** | Turkish: leh-VENT ahl-pur-GYEH; American: leh-VENT AL-poh-gay | Turkish [alpøˈɟe]; American English /ˈælpoʊɡeɪ/ | See the notes below. **M** for the Turkish, **L–M** for how he says it in English |

Notes on "Levent Alpöge":
- **The Wikipedia IPA has no source.** English Wikipedia gives `{{IPA|tr|alpøˈɟe}} {{respell|ahl|pur|GYEH}}; American
  English: {{IPAc-en|ˈ|æ|l|p|oʊ|ɡ|eɪ}} {{respell|AL|poh|gay}}`, with no citation.
  https://en.wikipedia.org/wiki/Levent_Alp%C3%B6ge
- **No recording found.** I found no recording of Alpöge saying his own name: no talk with a self-introduction and no
  podcast. A languagehat.com commenter on 20 Nov 2026 wrote: "I know how to pronounce Alpöge in Turkish, but the
  dude's American — does anybody know how he says his name?" The only answer was an AI-generated guess: "leh-VENT
  ahl-PUH-geh ... [leˈvent aɫˈpøɟe] ... typically luh-VENT al-POH-gay in American English."
  https://languagehat.com/the-co-hyperonym-operation/
- **What his own page says.** His homepage (https://alpo.ge/) just says "hi im levent!!!". Wikipedia says he holds dual
  US and Turkish citizenship.
- **Turkish spelling.** "ö" is [ø], like German ö or the vowel in "fur". A "g" before a front vowel (e) is palatalised
  [ɟ], close to "gy". Surnames are usually stressed on the last syllable, which gives "ahl-pur-GYEH". "Levent" is
  [leˈvent], "leh-VENT", stressed on the last syllable (standard Turkish; no specific source).
- **Recommendation.** Use the American "leh-VENT AL-poh-gay" or the Turkish "ahl-pur-GYEH", and keep it the same
  throughout. Better still, record it from a talk by him if the production can find one. **Confidence: medium.**

---

## Summary of corrections to the brief

1. **Riemann's paper is 10 printed pages** (Monatsberichte 1859, printed 1860, pp. 671–680). "Six pages" refers to a
   manuscript fair copy now attributed to Clebsch.
2. **Basel problem: say 1735.** It was solved by 1735 and presented 5 Dec 1735; "1734" is secondary only. The Euler
   product (E72) is 1737, presented 25 Apr 1737 and published 1744. Bombieri's Clay text instead credits the
   *Introductio* (1748).
3. **Hilbert's lecture: 8 August 1900** (MacTutor); Clay says 9 August. He read 10 of the 23 problems aloud.
4. **Hasse: 1933 / 1934 / 1936.** The preliminary note was in April 1933, a paper followed in 1934 (Bombieri's date),
   and the full proof in 1936.
5. **Bombieri's Bourbaki talk was June 1973;** it was printed in 1974.
6. **The zero heights in the brief are truncations,** so keep the "…". Rounded to 12 decimals, zeros 1, 2, 3, 4, 6 and
   8 end one digit higher.
7. **arXiv 2609.33043 is about distinct zeros** (≥ 83.69 %), not zeros on the critical line. The "simple and on the
   critical line" record is arXiv 2610.08965 (≥ 67.353 %; Knausgård, 6 Oct 2026). It depends on computer-checked
   inequalities recorded as Lean axioms.
8. **Platt–Trudgian checked 12,363,153,437,138 zeros** up to height 3,000,175,332,800. No newer record was found.
   Gourdon (2004, not peer reviewed) checked 10¹³ zeros, up to about 2.44·10¹².
