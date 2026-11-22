"""Narration script: 16 scenes (~12.5 minutes at Kokoro af_heart, speed 1.0).

Markup inside "text":
  [display|spoken]   captions show `display`, the voice says `spoken`
                     (`spoken` = /phonemes/ forces a pronunciation, Kokoro/misaki alphabet)
  {cue}              a sync point for the visuals: the time the next word starts
  blank line         paragraph break (a longer pause)

Every factual claim is sourced in research/sources.md; the adversarial fact-check that
shaped this wording is summarised in research/factcheck.md.
"""

# Kokoro / misaki phonemes (A = eI, I = aI, O = oU, W = aU, Y = OI) for names the default
# English pronunciation gets wrong; see research/math_facts.md section 17 for the sources.
LEXICON = {
    "Riemann": "ɹˈimɑn",           # REE-mahn (Wikipedia /ˈriːmɑːn/)
    "Riemann's": "ɹˈimɑnz",
    "Levent": "lɛvˈɛnt",
    "Alpöge": "ˈælpOɡˌA",          # Wikipedia's American form AL-poh-gay (unsourced there; best guess)
    "Alpöge's": "ˈælpOɡˌAz",
    "Stepanov": "stəpˈɑnəf",
    "Stepanov's": "stəpˈɑnəfs",
    "Bombieri": "bɑmbjˈɛɹi",
    "Hasse": "hˈɑsə",
    "Weil": "vˈA",
    "Dirichlet": "dˌiɹiklˈA",
    "Mangoldt": "mˈɑŋɡɔlt",
    "Siegel": "zˈiɡəl",
}

SCENES = [
    {"id": "s01_open", "title": "", "text": """
{title}On November twentieth, [2026|twenty twenty-six], the mathematician Levent Alpöge posted a four-page note. He wrote that he believes that, working with Claude, he has found a proof of the Riemann Hypothesis, perhaps the most famous open problem in mathematics. {lean}Instead of a written proof, he posted [17 million|seventeen million] lines of Lean, a language in which a computer checks every step. {joint}A day later, the communities behind Lean and its shared math library, Mathlib, wrote, quote: we have full confidence that Alpöge's proof of the Riemann Hypothesis is correct.

{plan}Here's the road from the primes to that claim.
"""},
    {"id": "s02_primes", "title": "1 · Counting primes", "text": """
Start with the primes: two, three, five, seven, eleven, whole numbers above one with no divisors but one and themselves. {grid}Up close, they look random. {staircase}But count them. [π(x)|Pi of x] is the number of primes up to x. Its graph is a staircase, {zoom}and from far away the staircase looks astonishingly smooth.

{gauss}As a teenager, Gauss guessed that near x, roughly one number in [ln x|the natural log of x] is prime. Adding up those odds gives the logarithmic integral, [li(x).|L I of x.] {table}Up to a million there are [78,498|seventy-eight thousand, four hundred ninety-eight] primes, and L I is off by only about a hundred and thirty. {question}The real question is: how big can that error get?
"""},
    {"id": "s03_euler", "title": "2 · Euler's bridge", "text": """
Decades earlier, Leonhard Euler had studied a different sum. {basel}One, plus a quarter, plus a ninth: one over every square number. The total is exactly [π²/6.|pi squared over six.] {harmonic}With one over n itself, the sum grows forever, though slowly.

{product}Then Euler found the bridge to the primes. For s bigger than one, the sum of [1/nˢ|one over n to the s] equals a product over the primes. {expand}Expand each factor as one, plus p to the minus s, plus p to the minus two s, and so on, and multiply out: since every whole number splits into primes in exactly one way, each term appears exactly once. {zeta}That sum is the zeta function. One side is about all numbers; the other only about primes.
"""},
    {"id": "s04_complex", "title": "3 · Spinning arrows", "text": """
In [1859,|eighteen fifty-nine,] Bernhard Riemann made the move that changed everything: let s be a complex number. {phasor}If you've worked with phasors, you know what that does. Write s as [σ + it.|sigma plus i t.] Then [n⁻ˢ|n to the minus s] is an arrow of length [n^−σ,|n to the minus sigma,] turned by an angle of [t·ln n.|t times log n.]

{spiral}So zeta is a sum of spinning, shrinking arrows. Laid tip to tail, they form a spiral. {converge}When sigma is bigger than one, the arrows shrink fast enough for the spiral to wind into a single point: the value of zeta.
"""},
    {"id": "s05_continue", "title": "4 · The whole plane", "text": """
{diverge}When sigma is one or less, the arrows don't shrink fast enough, and the sum never settles. {geom}Think of one, plus x, plus x squared, and so on. It only works between minus one and one, but it clearly wants to be one over one minus x, which makes sense everywhere except x equals one.

{unique}In the same way, zeta has exactly one extension to the whole plane that stays complex-differentiable, its analytic continuation, everywhere but s equals one. {map}Here it is. Color shows the direction of zeta's value, and each ring doubles its size. {zeros}Where all the colors meet at a dark point, zeta is zero.
"""},
    {"id": "s06_zeros", "title": "5 · The zeros", "text": """
Some zeros are easy: {trivial}minus two, minus four, minus six, and so on, the trivial zeros. {strip}All the other zeros lie in a narrow band, the critical strip, where sigma is between zero and one.

{symmetry}An exact identity, the functional equation, ties zeta at s to zeta at one minus s. Together with zeta's up-down symmetry, that mirrors the zeros across the middle of the strip: {line}the critical line, real part one half. {first}The first zero above the axis sits at one half, plus fourteen point one three four seven i.
"""},
    {"id": "s07_rh", "title": "6 · The hypothesis", "text": """
{state}The Riemann Hypothesis: every nontrivial zero lies exactly on that middle line. Not near it. On it. {riemann}In his ten-page paper, Riemann called this very probable, and moved on.

{zplot}On the line, we can watch zeros happen. This is Hardy's Z function: real on the line, and zero exactly where zeta is. {counter}Fourteen point one three. Twenty-one point zero two. Twenty-five point zero one. {checked}Computers have checked more than twelve trillion zeros, in order: every one is on the line. {prizes}It was on Hilbert's famous list in [1900,|nineteen hundred,] and since [2000|two thousand] the Clay Institute has offered a million dollars for a proof.
"""},
    {"id": "s08_music", "title": "7 · Primes from waves", "text": """
Why would primes care where zeros are? {formula}Because of an exact formula, the explicit formula, from Riemann's paper, proved in this form by von Mangoldt. {psi}Count prime powers, each weighted by the log of its prime: that's [ψ(x),|psi of x,] a cleaner staircase. The formula says psi of x is x, minus one wave for each pair of zeros, plus a tiny correction.

{waves}A zero at one half plus i gamma, with its mirror partner, adds a wave that oscillates with frequency gamma in log x. {add0}Start with the smooth part. {add1}Add the first wave. {add10}Ten. {add100}A hundred. {add1000}A thousand. {jumps}The prime staircase comes out of pure waves. The zeros are the frequencies; the primes are the signal.
"""},
    {"id": "s09_sqrt", "title": "8 · Why the line matters", "text": """
Here's the point. {sizes}Each wave grows like x to the power of its zero's real part. A zero on the line makes a wave that grows like root x. A zero at three quarters would make one growing like x to the three quarters: far louder.

{rh_eq}So the Riemann Hypothesis says the error in counting primes stays as small as it possibly can: about root x, up to logarithms. {walk}That's the typical drift of a random walk of x coin flips. {bound}Assuming RH, there's even an explicit bound on the gap between pi of x and L I of x, from x equals [2657|twenty-six fifty-seven] on. {data}Up to a million, the primes stay inside it.
"""},
    {"id": "s10_curves", "title": "9 · A world where it's proved", "text": """
In a parallel world, the analogous hypothesis has been proved for decades. {clock}Do arithmetic on a clock with p hours, p prime, and count the solutions of [y² + y = x³ − x.|y squared, plus y, equals x cubed minus x.] {grid}For p equal to thirteen, there are fifteen, plus one extra point at infinity.

{count}Each x gives two, one or no values of y, one on average, so you'd expect about p plus one. {hasse}The surprise is how close it stays: the error is never more than two root p, for every prime. {weil}Hasse proved this for curves like this one in the [1930s,|nineteen thirties,] Weil the general version for every curve in the [1940s,|forties,] and Deligne went much further in [1974.|nineteen seventy-four.] Each such curve has a zeta function, and for this one, the bound is exactly its Riemann Hypothesis.
"""},
    {"id": "s11_stepanov", "title": "10 · Counting with multiplicity", "text": """
In [1969,|nineteen sixty-nine,] Sergei Stepanov found an elementary way to prove such bounds. Its engine is simple. {poly}A polynomial of degree D has at most D roots, counted with multiplicity: a double root counts twice.

{aux}So build an auxiliary polynomial, not identically zero, which is the hard part, that vanishes at every one of the N solutions, each to order m. {count}Counting roots gives N times m, at most D. {tune}Raising m spreads a fixed overhead thinner, about p over m, but every extra order of vanishing costs extra degree, about m. The two balance when m is about root p. {moral}Multiplicity of about root p yields an error of about root p.
"""},
    {"id": "s12_obstacle", "title": "11 · The integer version", "text": """
Stepanov detects multiplicity with derivatives: at a double root, f and its slope both vanish. {quote}Alpöge calls his argument a descendant of Stepanov's, but writes that multiplicity is hard to find over the integers, corresponding to something like differentiating whole numbers.

{cousin}Still, root counting has an old integer cousin. A whole number that isn't zero, but is divisible by many primes, must be large. {binom}Twenty choose ten is divisible by every prime between ten and twenty, yet it's less than four to the tenth, so those primes can't be too many. {dict}Each prime factor plays the role of a root, its power the role of multiplicity, and size, on a log scale, the role of degree. {cheb}Around [1850,|eighteen fifty,] Chebyshev used this idea, with ratios of factorials, to bound the primes, but only roughly: those numbers aren't divisible enough.
"""},
    {"id": "s13_theta", "title": "12 · The new idea", "text": """
Readers of the code describe the claimed proof as Chebyshev's idea, run with far better numbers, built from theta functions. {theta}The theta function has a hidden mirror symmetry, which Riemann used to prove zeta's own.

{lift}Functions with symmetries like this, automorphic forms, can be carried from one symmetry group to a partner group by integrating against a theta kernel, a many-variable cousin of theta: a theta lift. {chain}Chain m lifts and read off one number, a period. As the note and the guides describe it, it isn't zero, and it gets more divisible by certain primes with every lift: each lift mimics one more order of multiplicity. {weigh}Its divisibility is itself a weighted count of primes, so divisibility at most size caps that count.

{sqrt}How long a chain, for primes up to X? The guides, written from the code with AI help, describe two errors, as with Stepanov: about X over m, and about m. They balance at m about root X, leaving an error of about root X: what the Riemann Hypothesis demands. {table}Claude suggested root X. Alpöge's comment: and yet, what else could it be?
"""},
    {"id": "s14_build", "title": "13 · The construction", "text": """
{timeline}The note's rough timeline, which Alpöge says Claude compiled, runs from October sixth to November sixteenth. {lean}The result is a Lean library of [175,187|a hundred seventy-five thousand] files and [17.4 million|seventeen point four million] lines, without a single comment.

{skeleton}Read from the top, its skeleton is short. {step1}Last step: no zeros to the right of one half, plus the mirror symmetry, gives the Riemann Hypothesis. {step2}Before that: if weighted prime sums stay below about root x on long stretches, no zero can sit right of one half, since its louder wave would break the bound. That covers zeta and its cousins, the Dirichlet L-functions, which sort primes by remainder. {step3}The enormous middle, theta lifts plus heavy machinery from across number theory, proves that bound, {code}with chains at least [x^(1/2 − ε)|x to the power one half minus epsilon] long: just under root x. {caveat}Readers also report that a few steps in the note's timeline have no visible counterpart in the code.
"""},
    {"id": "s15_check", "title": "14 · Checking it", "text": """
How can anyone trust seventeen million lines that no human has read in full? {kernel}In Lean, every step must follow from earlier ones by fixed rules, and a small program, the kernel, checks them all. {four}Kevin Buzzard lists four questions to ask of AI-written Lean.

{q1}Is the statement right? Here it's the definition in Mathlib, Lean's shared library, written by people and vetted by experts. {q2}Does it compile? Dozens of people have rebuilt it. {q3}Does it prove exactly that statement, using only the standard axioms? Two independent tools say yes. {q4}Could it exploit a bug in Lean itself? Several independent checkers accepted it, two of them with a formal proof, relative to set theory, that they can't accept a false one.

{joint}That is the basis of the November twenty-first statement of full confidence.
"""},
    {"id": "s16_close", "title": "15 · Where this leaves us", "text": """
So where are we? {certified}What the Lean and Mathlib statement certifies is the classical Riemann Hypothesis. {dirichlet}Andrew Sutherland's verification page at [MIT|M I T] reports that the library also proves the same on-the-line statement for every Dirichlet L-function: the generalized hypothesis, in that sense. {notyet}Wider versions, for other kinds of L-functions, haven't been checked; Alpöge only expects one, the extended hypothesis, with more time. And there's no human-readable proof yet; he says he'll write it properly. {clay}And the Clay prize requires publication, then two years, then general acceptance.

{close}So for now, it's a claimed proof: checked by machines, not yet explained in human terms. If it holds, the zeros really do all sit on one line, and the reason may be an old idea, counting with multiplicity, finally made to work for the whole numbers.
"""},
]
