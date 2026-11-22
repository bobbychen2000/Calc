# Status of the claimed proof of the Riemann Hypothesis (as of 2026-11-22, ~03:30 UTC)

Area: status. Every statement below comes from a page fetched for this report on 2026-11-22. Copies are in
`/home/user/rhwork/sources/status/` (plus the four pre-fetched files in `/home/user/rhwork/sources/`).
All quotes are short and verbatim. **Status labels:** VERIFIED = read on the primary source itself;
REPORTED = a secondary outlet says so, and I could not reach the original; UNVERIFIED = not found; CONTRADICTED = sources disagree.

---

## 0. One-paragraph summary

On 2026-11-20 Levent Alpöge (Anthropic) posted a 4-page note claiming that he, "working with Claude", found a proof of
RH and of "the so-called Generalized Riemann Hypothesis". He released only a Lean formalization of about 17 million lines. He did not release a
human-readable proof. On 2026-11-21 the Lean and Mathlib communities published a joint statement, endorsed by the
Lean FRO and the Mathlib Initiative. It "certif[ies]" that the statement (Mathlib's `RiemannHypothesis`) and the Lean proof are
correct. That statement says **nothing about GRH**. Andrew Sutherland's MIT page adds that the same checks cover
four further theorems: GRH **for Dirichlet L-functions only**. The page states the scope explicitly, and several long-running kernel and comparator runs were still
in progress at 03:10 UTC on 22 Nov. No informal (human-readable) proof exists yet. Alpöge says he intends to "write it
properly". The Clay Mathematics Institute's rules require publication in a qualifying outlet, two years, and general acceptance.
CMI's president called it "an announcement of historic significance" but said "the journey ... to a place of real understanding will be long and difficult". I found no
Anthropic statement on anthropic.com, and Nature, AFP and AP all report no response from Anthropic.

---

## 1. The Lean / Mathlib joint statement: what it certifies, and what it leaves out

Source: https://leanprover-community.github.io/blog/posts/riemann-hypothesis/ (author field "Lean and Mathlib communities",
published 2026-11-21T13:55:00Z per the page metadata and its Markdown source). VERIFIED.

**Who is speaking.** The statement is "Joint statement by the Lean and Mathlib communities, endorsed by the Lean FRO and the Mathlib Initiative."
It is not a statement *by* the Lean FRO alone; the FRO endorses it. Some press, e.g. Startup Fortune, calls it a statement by the FRO and the
Initiative.

**What it certifies (verbatim):**
- "We have full confidence that Alpöge's proof of the Riemann Hypothesis is correct, and we congratulate him on this achievement."
- "We hereby certify that both the statement and the proof of the Riemann Hypothesis are correct."
- "The four criteria in https://xenaproject.wordpress.com/2026/11/12/and-the-proof-is-checked-in-lean/ are all satisfied."
- On the statement: "This statement is part of Mathlib: RiemannHypothesis and has been carefully vetted by experts in Lean and number theory."
- On compilation: "dozens of people have reported correct compilation of the codebase, reproducing the same raw proof export file."
- On statement-matching: it was checked with "two independent tools (comparator and con-leche –compare), both confirming that the theorem proved in Alpöge's library is exactly Mathlib's statement".
- On the kernel: the export "has been checked by several proof checkers, including Lean's official kernel, the con-leche and con-ron checkers, and several independent checkers".
- On soundness: con-leche and con-ron "come with a formal proof, relative to set theory, that they cannot accept a false proof".
- Size: "a Lean library comprising 17 million lines of code"; "The codebase depends directly only on Mathlib."
- Closing line: "We look forward to all the activity in the mathematical community that will help explain the new ideas in this proof."

**What it does NOT mention** (I checked the rendered page and its Markdown source; the only "grh" string is in Sutherland's URL `math.mit.edu/~drew/grh/`):
- It says nothing about the **Generalized** Riemann Hypothesis, Dirichlet characters or L-functions. It certifies RH only.
- It makes no claim about a human-readable proof, about the mathematical ideas, or about peer review or publication. It is
  explicitly about the Lean statement and the Lean proof.
- It does not mention the Clay prize.

**Nuance for narration (VERIFIED by comparing the two pages).** The joint statement lists "Lean's official kernel" among the checkers.
Sutherland's table (03:10 UTC, 22 Nov) shows a Lean-kernel *module-by-module replay* ("leanchecker kernel replay of every
module ... pass") as complete. The run of "Lean default kernel and Lean paranoid kernel on the export" is still "running ... no verdict yet". So the
remaining runs are additional checks on the 61.6 GB export, not the first check by Lean's kernel.

## 2. Andrew Sutherland's verification page (MIT)

Source: https://math.mit.edu/~drew/grh/ ("Andrew Sutherland (MIT), checks run with Claude Code. Page last updated 2026-11-22 03:10 UTC").
Re-fetched for this report: still 03:10 UTC. VERIFIED.

**Summary line (quote):** "The published Lean source compiles without errors, the five headline theorems depend only on the three standard axioms, every module has been replayed through the Lean kernel".
In addition: "two independently written kernels, nanoda and con-leche, accept the full exported proof".

**The five theorems** ("Their statements are below exactly as they appear in the challenge file, which imports only Mathlib"):
1. `riemannHypothesis : RiemannHypothesis`. This is Mathlib's own definition: "every zero of ζ other than the trivial zeros −2, −4, −6, … has real part 1/2".
   The `s ≠ 1` condition is there "because Mathlib assigns ζ a conventional value at its pole."
2. `riemannZeta_eq_zero_re`: "The same statement written out in the submission's own words."
3. `LFunction_ne_zero_of_half_lt_re`: "For every modulus N ≥ 1 and every Dirichlet character χ modulo N, primitive or not, L(χ, s) ≠ 0 whenever Re s > 1/2."
4. `LFunction_eq_zero_re`: "Zeros in the critical strip lie on the critical line, for every Dirichlet L-function."
5. `LFunction_eq_zero_re_of_isPrimitive`: the same for primitive characters, "the form in which the Generalized Riemann Hypothesis for Dirichlet L-functions is usually stated."

**Scope note (verbatim):** "Scope. "GRH" here means Dirichlet L-functions: all moduli and all characters. Dedekind zeta functions,
Hecke L-functions and automorphic L-functions in general are not among the statements that were checked."

**Axioms:** "propext, Classical.choice, Quot.sound only". Also: "15 axioms in the environment, all in Init".

**Checks that pass or accept** (selection): all 175,187 modules compile on Lean/Mathlib v4.33.1. An independent sandboxed rebuild on a
separate machine produced an export that is "identical", 61,570,595,788 bytes. leanchecker replay passed 175,187 of 175,187. nanoda accepts, as does
con-leche master (1,468,418 declarations). con-leche --compare and con-ron --compare: "all five theorems "justified by the solution"". lean4lean passed
175,187 of 175,187, five of them only after a raised step limit.

**Still running at 03:10 UTC, 22 Nov (verbatim rows):**
- "Lean default kernel and Lean paranoid kernel on the export: running ... single-threaded; no verdict yet"
- "lake comparator (Lean v4.36.0) end to end: running ... statement comparison and axiom check already passed in one run; kernels in progress"
- The combined RH + Robin1984 export's lake comparator: "running", "expected to take many hours".
- The page says it "will be updated as the remaining checks finish."

**An extra sanity check that does not depend on Mathlib's zeta.** The proof was combined with an independent formalization of Robin's and Lagarias's
criteria (kimihiro64/Robin1984). The result is two divisor-sum inequalities "with no hypotheses and no mention of zeta". con-leche, con-ron and nanoda accept them;
lake comparator on that combination is still running.

**The page's own caveat (verbatim):** "A passing check shows that the formal statements, as written in Lean against Mathlib's definitions,
follow from the three standard axioms according to the kernels used. It relies on those kernels and on Mathlib's definitions being what they are intended to be."

**Provenance detail worth knowing.** The original build "ran on cloud machines without a sandbox" and was repeated in a
"bubblewrap sandbox: no network, the source tree read-only". "The export made inside that sandbox is byte-identical to the published one."
"Checks run with Claude Code" means Claude Code ran the scripts. The checkers themselves (nanoda, con-leche, con-ron,
lean4lean, Lean's kernel) are separate programs.

## 3. Reactions of named mathematicians (only what I found)

| Person | What they said | Where | Label |
|---|---|---|---|
| **Terence Tao** (UCLA) | "Levent Alpöge, using an internal AI model, has generated an (enormous) Lean-only proof of the Generalized Riemann Hypothesis." | https://terrytao.wordpress.com/2026/11/20/unforced-euler-singularity-unforced-navier-stokes-singularity-and-the-generalized-riemann-hypothesis/ | VERIFIED |
| Tao (same post) | The strategy "appears to use the full power of modern developments on the Langlands program and arithmetic geometry". | same | VERIFIED |
| Tao (same post) | "I imagine the digestion process will take some time, though in this case at least we have a human author to communicate with to assist with this task." | same (also quoted by BBC) | VERIFIED |
| **Kevin Buzzard** (Imperial) | The four criteria (post of 12 Nov): (1) "Does the Lean statement match the informal statement?" (2) "does the code compile?" (3) "does the code prove the theorem as stated?" (4) "does the code exploit a bug in Lean's official kernel?" | https://xenaproject.wordpress.com/2026/11/12/and-the-proof-is-checked-in-lean/ | VERIFIED |
| Buzzard (same post) | "Even if the Lean code compiles and passes all these tests ... this does not mean that any corresponding pdf also contains a correct proof!" | same | VERIFIED |
| Buzzard (Lean Zulip, 20 Nov, before the comparator finished) | "We still await a successful comparator run, which will check that (a) the code does not do anything nefarious like redefine the meaning of any of the symbols" | quoted in SciAm: https://www.scientificamerican.com/article/the-ai-riemann-hypothesis-proof-is-almost-certainly-true-independent-mathematicians-attest/ | REPORTED (Zulip needs a login) |
| **James Maynard** (Oxford, Fields 2022) | "If this fully checks out, it is clearly a historic milestone in mathematics" | Nature https://www.nature.com/articles/d41586-026-03812-7 ; IBM Think https://www.ibm.com/think/news/anthropic-claude-riemann-hypothesis-math-proof | VERIFIED (both outlets) |
| Maynard | "I suspect that the proof will turn out to be correct, although even checking the Lean verification will take some time" | IBM Think (Nature has the first half) | VERIFIED |
| Maynard | "assuming we do get the corresponding understanding, this will surely be viewed as one of the absolute pinnacles of mathematical results" | Nature | VERIFIED |
| Maynard | "98 or 99 percent" certain | attributed to The New York Times by TNW https://thenextweb.com/news/anthropic-alpoge-claude-riemann-hypothesis-proof-lean and bdnews24 | REPORTED (NYT not reached) |
| **Andrew Granville** (Montréal) | "What he released is garbled." Nature also writes that he "cites the downturn in the company's stock value as the reason for the timing". | Nature | VERIFIED |
| **Maksym Radziwiłł** (NYU; thanked in Alpöge's note) | "If the symbols are right and follow the rules, then the symbols are a valid proof." and "The object of mathematics as the rest of science is really the question 'why?' and this doesn't answer it at all." | Quanta (K. Kakaes), https://www.quantamagazine.org/update/169569/ | VERIFIED |
| **Brian Conrey** (AIM, RH specialist) | "It's a monumental moment in human history. It's really the biggest thing I think that's ever happened in mathematics". He also said he had not yet seen a manuscript and "there will be simpler ways to do it". | AFP via Yahoo https://tech.yahoo.com/ai/claude/articles/anthropic-researcher-says-claude-solved-183242612.html | VERIFIED (AFP text) |
| **Brian Conrad** (Stanford) | Releasing a proof the author does not fully understand is "frankly completely outrageous" | attributed to the NYT by TNW; Asia Business Daily's translation reads "completely absurd" | REPORTED |
| **Andrew Sutherland** (MIT) | "Honestly the chance that anything is fishy here is approximately zero." and "This is indeed an historic moment" | SciAm (both articles) | VERIFIED |
| **Tristan Buckmaster** (NYU) | "At the moment, it apparently is crazily complicated. It's going to take a long time for mathematicians to digest" | Nature | VERIFIED |
| **Alex Kontorovich** (Rutgers) | "Does that mean I understand it? Not yet. But the computer is extraordinarily picky, way pickier than I am" | AP via KCRA https://www.kcra.com/article/anthropic-claude-riemann-hypothesis-proof/74497243 | VERIFIED (AP text) |
| **Youness Lamzouri** (Lorraine) | "Mathematics is mainly about understanding why something is true" (he expects months or even years) | IBM Think | VERIFIED |
| **Simon DeDeo** (CMU) | "I'd be very surprised if there were any secret tricks" | Quanta | VERIFIED |
| **Filippo Nuccio** (Saint-Étienne) | "it basically contains all number theory produced in the last 50 years, in all branches of the discipline." | Quanta | VERIFIED |
| **Hector Pasten**, **Carlo Pagano** | "If the proof is correct and understood, this completes a dictionary ... something like a Rosetta Stone." (Pasten); Pagano: "If true ... brand new avenues of thinking" | SciAm https://www.scientificamerican.com/article/anthropic-mathematician-claims-to-prove-riemann-hypothesis-most-famous-problem-in-all-of-math/ | VERIFIED |
| **Scott Aaronson** (computer scientist) | Update of 21 Nov: "This is a much higher degree of verification than a typical human paper accepted to a math journal. The proof is correct." He also expects human distillation "will probably take years". | https://scottaaronson.blog/?p=10344 | VERIFIED |
| **Martin Bridson** (President, CMI) | see §4 | AP | VERIFIED (AP text) |
| **Association for Human Mathematics** (an organization, not one person) | "At this time, no human being can reasonably claim to be responsible for, or even to understand, such a document." | https://www.ahmath.org/statements | VERIFIED |

**Not found** (searched; no on-record reaction to this claim): Peter Sarnak and Manjul Bhargava (both are only *thanked* in Alpöge's
note, which does not imply endorsement), Kannan Soundararajan, Jordan Ellenberg. Buzzard has no post after the certification on Xena or Bluesky
(his latest Bluesky post is from Dec 2025); his Zulip comments need a login. Tao's latest Mastodon post is 2026-11-10, so nothing there on RH.

## 4. Clay Mathematics Institute: rules, and its statement

**Rules.** Sources: https://www.claymath.org/millennium-problems/rules/ and the full rules PDF linked from it,
https://www.claymath.org/wp-content/uploads/2022/03/millennium_prize_rules_0.pdf ("adopted by the Board of Directors ... on 26 September, 2018"). VERIFIED.
- Web page: "CMI does not accept direct submission of proposed solutions."
- Web page: "(i) the proposed solution must be published in a Qualifying Outlet (see §6), and (ii) at least two years must have passed since publication, and (iii)
  the proposed solution must have received general acceptance in the global mathematics community"
- PDF §4(c): "the Proposed Solution has achieved general acceptance in the global mathematics community, as determined in the sole discretion of CMI"
- PDF §6(a)(i): a Qualifying Outlet is "a refereed mathematics publication of worldwide repute". §6(a)(ii) allows "a relaxed set of conditions approved by the BOD" on the SAB's recommendation.
- PDF §7(a)(i)(2): "The Proposed Solution must survive rigorous examination by the global mathematics community for a minimum of two (2) years."
- PDF §7(a)(i)(3): "No CMI-affiliated entity will accept invitations, requests or demands to recognize the status of a Proposed Solution."
- PDF §7(a)(ii)(3): then "a special advisory committee ... no fewer than three (3) members, at least two of which are experts in the area".
- PDF §8(b): CMI will consider whether a solution "depends crucially on insights published prior". §8(c) allows "no Prize" if CMI cannot decide on correctness or attribution.
- Implication (my reading, not CMI's words): a Lean archive on a personal website is not, by itself, publication in a Qualifying Outlet. The two-year clock
  has not started under the written rules.

**CMI on this claim.** Martin Bridson, president of the institute, "in a statement" (quoted by AP, updated 5:21 AM PST 21 Nov):
"This is an announcement of historic significance, which holds the promise of a dramatic transformation in the perception of what is possible".
And: "But the journey from today's announcement to a place of real understanding will be long and difficult." AP also writes:
"Hours after the announcement, the Riemann Hypothesis remained listed as unsolved on the Clay Mathematics Institute's website."
https://www.kcra.com/article/anthropic-claude-riemann-hypothesis-proof/74497243 . REPORTED (quoted by AP; it is not on claymath.org).
- claymath.org itself (fetched 22 Nov) has **no** news item on RH. The RH problem page was last modified 2023-05-24.
- Precedent: CMI's "Navier-Stokes Announcement" (2026-09-11) said the problem "has apparently been settled" and "The process is
  deliberately unhurried, but we will provide updates." https://www.claymath.org/news/navier-stokes-announcement/ . VERIFIED.
- Press paraphrases of the rules are looser. AFP: "a solution must be published in a peer-reviewed journal and withstand two years of scrutiny".
  Use CMI's own wording.

## 5. Anthropic and Dario Amodei

- **anthropic.com:** the News and Research index pages (fetched 22 Nov) have **no** item on this RH claim. The latest items concern the IPO.
  The only RH-related Anthropic post is the August one, https://www.anthropic.com/research/riemann-zeta (a lower bound for the share of zeros on the line,
  41.6% -> 67.2%). It is a different, earlier result, and that post said its techniques were not expected to prove RH. UNVERIFIED that any statement exists. None found.
- Nature: "Anthropic did not respond immediately to Nature's request for comment." AFP: "Anthropic did not immediately respond to a request for
  comment from AFP." AP: "Anthropic did not respond to an email from The Associated Press requesting comment". VERIFIED (as reported text).
- **Amodei:** no public comment found. Alpöge's note says "I messaged Dario, "Hypothetically, if I were to have . . . ", eventually asking about my
  ability to announce" and "there was a constraint to respect". AP, AFP and BBC identify "Dario" as CEO Dario Amodei. Alpöge also writes:
  "Our leadership and the few trusted mathematicians I consulted hold extremely similar views on the right things to do".
  Alpöge on the timing: "There is an obvious cynical view, to do with the timing, but it is false". The note came one day after Anthropic's IPO debut (BBC, AP).

## 6. Is there a human-readable proof?

**No, not as of 22 Nov.** From Alpöge's note (https://alpo.ge/remark.pdf). VERIFIED:
- "It being obviously inappropriate to attempt to post some massive unreadable travesty of "slop", I decided to only present Lean."
- "while its formalization is finished and it is routine to produce a huge, unreadable document containing sufficient detail".
- Promise: "I intend to do my best to understand and impart understanding of this argument and its certain simplifications, to speak about it, to write it properly."
- He also writes "I will do a proper job in a proper writeup" (about the acknowledgments).
- Footnote 2: "I of course amused myself, and hit 250, 000+ pages." This 250,000+-page AI-written text was **not** released.
- He admits "presenting the world with a complete argument before having mastered a massive neighbourhood around its mathematics."
- The note's timeline is one "Claude provided after a thorough search". Footnote 4: parts of it are "paraphrasing a "slop" summary, which might make zero sense".
- Scope claimed by Alpöge: "the method easily extends much further, resolving the so-called Generalized Riemann Hypothesis, and I expect, with more time, the
  Extended Riemann Hypothesis too." ERH is **not** claimed as done.
- CONTRADICTED in the press: BBC wrote "The complete textual proof that Alpöge put forward in Lean ... is over 250,000 pages long".
  https://www.bbc.com/news/articles/c6pqr2g7w059o . The note says the 250,000+ pages were a document he did not post. What was released is Lean code.
- Partial human digests exist in blog comments (e.g. on Tao's post). They are anonymous, describe themselves as unverified, and are not a proof.

## 7. A rival claim the same day (context, if the video mentions "a proof")

Ravi Vakil (AMS president, Stanford) posted a 940-page all-human draft by Alessandro Maria Masullo claiming GRH:
https://math216.wordpress.com/2026/11/20/hurried-announcement-alessandro-masullo-grh/ . VERIFIED. He wrote: "It is all human, with no AI."
His update about 8 hours later: "Several people have contacted me to report problems in the proposed proof, identified with the assistance of different AI models." and
"(I make no claim as to the correctness of the proof strategy.)" Nature's headline covers both claims.

## 8. Recommended wording for the video

**Status paragraph (about 90 words, 4 sentences):**
> On November 20th, 2026, Anthropic mathematician Levent Alpöge announced a claimed proof of the Riemann Hypothesis, found working with Claude
> and released only as about 17 million lines of Lean code, a language a computer can check step by step. The next day the Lean and Mathlib
> communities, in a statement endorsed by the Lean FRO and the Mathlib Initiative, said they "certify" that the Lean statement and its proof are correct.
> A verification page at MIT reports that the same code also proves the Generalized Riemann Hypothesis for Dirichlet L-functions, and a few slow checks were still running.
> But there is no human-readable proof yet, and the Clay Institute's prize rules require publication in a qualifying outlet, two years, and general acceptance
> by mathematicians, so for now it is a claimed proof that has passed an unusually strong machine check.

**Shorter alternative (2 sentences):** "It is, for now, a claimed proof. The computer checks have come back clean, but no mathematician has yet
read a human proof, because none has been written."

**Use:**
- "claimed proof", "a proof that has been machine-checked in Lean", "formally verified by independent proof checkers".
- Attribute "full confidence" and "certify" to the *Lean and Mathlib communities' statement*, in quotation marks. Do not make them the narrator's words.
- "Alpöge says the method also gives the Generalized Riemann Hypothesis. The checked Lean theorems cover the version for Dirichlet L-functions."
- "Alpöge, working with Claude" (his own words). Not "Claude alone" and not "Alpöge alone".

**Avoid:**
- "proved" or "solved" as the narrator's own unqualified verdict ("RH is proved", "RH has been solved").
- "peer-reviewed", "published", "accepted by mathematicians", "confirmed by mathematicians" (SciAm's headline says "independent mathematicians confirm"; what was confirmed is
  the formal proof, by Lean checkers, not a reading of the mathematics).
- "Clay certified", "won the million-dollar prize", "the prize clock has started". CMI says "the journey ... will be long and difficult" and requires a Qualifying Outlet, two years, and general acceptance.
- "the Lean FRO certified" (it *endorsed* a community statement), and "the Lean community certified GRH" (the statement covers RH only).
- "proved GRH" without the qualifier "for Dirichlet L-functions". Dedekind, Hecke and automorphic L-functions "are not among the statements that were checked".
- "a 250,000-page proof was published" (it was not published).
- "nobody understands it" as a flat fact. Say instead "no human-readable proof has been released; experts expect understanding to take a long time".
- "AI proved RH by itself", "Anthropic announced". Alpöge announced on his personal site, and Anthropic has made no statement that I could find.
- "verification complete". As of 03:10 UTC 22 Nov the Lean default and paranoid kernels on the export and the end-to-end lake comparator were "running".

## Sources fetched (local copies in /home/user/rhwork/sources/status/)
alpo.ge/remark.pdf; leanprover-community blog statement; math.mit.edu/~drew/grh; Xena 2026-11-12; Nature d41586-026-03812-7 (Castelvecchi, 20 Nov, updated 21 Nov);
SciAm (Howlett, 20 Nov; Moskowitz, 20 Nov, updated 21 Nov); BBC c6pqr2g7w059o (Kali Hays, 20 Nov); Tao's blog 20 Nov; Quanta updates 169564 / 169569 (Kakaes, 20 Nov);
AFP via Yahoo (20 Nov); AP via KCRA (updated 21 Nov); IBM Think; TNW (21 Nov); Vakil's math216 post; Aaronson ?p=10344; AHM statements; Clay rules page + PDF, news, RH page,
Navier-Stokes announcement; anthropic.com/news and /research indexes; Wikipedia (Alpöge; doctoral advisor Manjul Bhargava).
Not reached: The New York Times (quotes above are second-hand), Science (Cloudflare block), TechCrunch (block), the Lean Zulip (login).
