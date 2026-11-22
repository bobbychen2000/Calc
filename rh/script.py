"""Narration script: 16 scenes (~10 minutes at Kokoro af_heart, speed 1.0).

Markup inside "text":
  [display|spoken]   captions show `display`, the voice says `spoken`
                     (`spoken` = /phonemes/ forces a pronunciation, Kokoro/misaki alphabet)
  {cue}              a sync point for the visuals: the time the next word starts
  blank line         paragraph break (a longer pause)

Every factual claim is sourced in research/sources.md.
"""

# Kokoro / misaki phonemes (A = eI, I = aI, O = oU, W = aU, Y = OI) for names the default
# English pronunciation gets wrong; see research/math_facts.md for the sources.
LEXICON = {
    "Levent": "lɛvˈɛnt",
    "Alpöge": "ˈælpOɡˌA",          # Wikipedia's American form AL-poh-gay (unsourced there; best guess)
    "Alpöge's": "ˈælpOɡˌAz",
    "Stepanov": "stəpˈɑnəf",
    "Bombieri": "bɑmbjˈɛɹi",
    "Hasse": "hˈɑsə",
    "Weil": "vˈA",
    "Dirichlet": "dˌiɹiklˈA",
    "Mangoldt": "mˈɑŋɡɔlt",
    "Siegel": "zˈiɡəl",
}

SCENES = [
    {"id": "s01_open", "title": "", "text": """
{title}On November twentieth, [2026|twenty twenty-six], the mathematician Levent Alpöge posted a four-page note. He wrote that he believes that, working with Claude, he has found a proof of the Riemann Hypothesis, perhaps the most famous open problem in mathematics. {lean}Instead of a written proof, he posted [17 million|seventeen million] lines of Lean, a language in which a computer checks every step. {joint}A day later, the Lean and Mathlib communities wrote that they have, quote, full confidence that the proof is correct.

{plan}Let's see what the zeta function is, what the hypothesis says, why primes care, and the idea behind this claimed proof.
"""},
    {"id": "s02_primes", "title": "1 · Counting primes", "text": """
Start with the primes: two, three, five, seven, eleven, numbers with no divisors but one and themselves. {grid}Up close, they look random. {staircase}But count them. [π(x)|Pi of x] is the number of primes up to x. Its graph is a staircase, {zoom}and from far away the staircase looks astonishingly smooth.

{gauss}As a teenager, Gauss guessed that near x, roughly one number in [ln x|log x] is prime. Adding up those odds gives the logarithmic integral, [li(x).|L I of x.] {table}Up to a million there are [78,498|seventy-eight thousand, four hundred ninety-eight] primes, and L I is off by only about a hundred and thirty. {question}The real question is: how big can that error get?
"""},
    {"id": "s03_euler", "title": "2 · Euler's bridge", "text": """
Decades earlier, Leonhard Euler had studied a different sum. {basel}One, plus a quarter, plus a ninth: one over every square number. The total is exactly [π²/6.|pi squared over six.] {harmonic}With one over n itself, the sum grows forever, though slowly.

{product}Then Euler found the bridge to the primes. Since every whole number splits into primes in exactly one way, the sum of [1/nˢ|one over n to the s] over all whole numbers equals a product with one factor for each prime. {zeta}That sum is the zeta function. One side is about all numbers; the other only about primes.
"""},
    {"id": "s04_complex", "title": "3 · Spinning arrows", "text": """
In [1859,|eighteen fifty-nine,] Bernhard Riemann made the move that changed everything: let s be a complex number. {phasor}If you've worked with phasors, you know what that does. Write s as [σ + it.|sigma plus i t.] Then [n⁻ˢ|n to the minus s] is an arrow of length [n^−σ,|n to the minus sigma,] turned by an angle of [t·ln n.|t times log n.]

{spiral}So zeta is a sum of spinning, shrinking arrows. Laid tip to tail, they form a spiral. {converge}When sigma is bigger than one, the arrows shrink fast enough for the spiral to wind into a single point: the value of zeta.
"""},
    {"id": "s05_continue", "title": "4 · The whole plane", "text": """
{diverge}When sigma is one or less, the arrows don't shrink fast enough, and the sum never settles. {geom}Think of one, plus x, plus x squared, and so on. It only works between minus one and one, but it clearly wants to be one over one minus x, which makes sense almost everywhere.

{unique}In the same way, zeta has exactly one smooth extension to the whole complex plane, except the point s equals one. {map}Here it is. Color shows the direction of zeta's value, and each ring doubles its size. {zeros}Where all the colors meet, zeta is zero.
"""},
    {"id": "s06_zeros", "title": "5 · The zeros", "text": """
Some zeros are easy: {trivial}minus two, minus four, minus six, and so on, the trivial zeros. {strip}Every other zero lies in a narrow band, the critical strip, where sigma is between zero and one.

{symmetry}A functional equation ties zeta at s to zeta at one minus s, so the zeros are mirrored across the middle of the strip: {line}the critical line, real part one half. {first}The first zero above the axis sits at one half, plus fourteen point one three four seven i.
"""},
    {"id": "s07_rh", "title": "6 · The hypothesis", "text": """
{state}The Riemann Hypothesis: every nontrivial zero lies exactly on that middle line. Not near it. On it. {riemann}In his ten-page paper, Riemann called this very probable, and moved on.

{zplot}On the line, we can watch zeros happen. This is Hardy's Z function: real on the line, and zero exactly where zeta is. {counter}Fourteen point one three. Twenty-one point zero two. Twenty-five point zero one. {checked}Computers have checked more than twelve trillion zeros, in order: every one is on the line. {prizes}Hilbert put the problem on his famous list in [1900,|nineteen hundred,] and in [2000|two thousand] the Clay Institute offered a million dollars for a proof.
"""},
    {"id": "s08_music", "title": "7 · Primes from waves", "text": """
Why would primes care where zeros are? {formula}Because of an exact formula, the explicit formula, from Riemann's paper, proved in this form by von Mangoldt. {psi}Weight every prime power by the log of its prime, and count: that's [ψ(x),|psi of x,] a cleaner staircase. The formula says psi of x is x, minus one wave for every zero.

{waves}A zero at one half plus i gamma adds a wave that oscillates with frequency gamma in log x. {add0}Start with the smooth guess, x. {add1}Add the first wave. {add10}Ten. {add100}A hundred. {add1000}A thousand. {jumps}The prime staircase comes out of pure waves. The zeros are the frequencies; the primes are the signal.
"""},
    {"id": "s09_sqrt", "title": "8 · Why the line matters", "text": """
Here's the point. {sizes}Each wave's size is x to the power of its zero's real part. A zero on the line makes a wave about the size of root x. A zero at three quarters would make one of size x to the three quarters: far louder.

{rh_eq}So the Riemann Hypothesis says the error in counting primes stays as small as it possibly can: about root x, up to logarithms. {walk}That's the typical drift of a random walk of x coin flips. {bound}Assuming RH, the gap between pi of x and L I of x stays below root x, times log x, over eight pi. {data}Up to a million, it does.
"""},
    {"id": "s10_curves", "title": "9 · A world where it's proved", "text": """
In a parallel world, the analogous hypothesis has been proved for decades. {clock}Do arithmetic on a clock with p hours, p prime, and count the solutions of [y² + y = x³ − x.|y squared, plus y, equals x cubed minus x.] {grid}For p equal to thirteen, there are fifteen, plus one point at infinity.

{count}You'd expect about p plus one. {hasse}The surprise is how close it stays: the error is never more than two root p, for every prime. {weil}Hasse proved this for curves like this one in the [1930s,|nineteen thirties,] Weil for all curves in the [1940s,|forties,] and Deligne went much further in [1974.|nineteen seventy-four.] Each such equation has a zeta function, and this bound is exactly its Riemann Hypothesis.
"""},
    {"id": "s11_stepanov", "title": "10 · Counting with multiplicity", "text": """
In [1969,|nineteen sixty-nine,] Sergei Stepanov found an elementary way to prove such bounds, later extended to all curves by Bombieri and Schmidt. Its engine is simple. {poly}A polynomial of degree D has at most D roots, counted with multiplicity: a double root counts twice.

{aux}So build an auxiliary polynomial that vanishes at every one of the N solutions, each to order m. {count}Counting roots gives N times m, at most D. {tune}Push m up while keeping D in check, and the competing error terms balance when m is about root p. {moral}That's the moral: multiplicity of about root p is what yields an error of about root p.
"""},
    {"id": "s12_obstacle", "title": "11 · The integer version", "text": """
Over the whole numbers, there's nothing to differentiate. {quote}Alpöge's note puts it this way: multiplicity is hard to find over the integers, corresponding to something like differentiating whole numbers.

{cousin}But root counting has an old integer cousin. A whole number that isn't zero, but is divisible by many primes, must be large. {binom}Twenty choose ten is divisible by eleven, thirteen, seventeen and nineteen, so it's at least their product, and it's less than four to the tenth. {dict}Divisibility plays the role of multiplicity; size plays the role of degree. {cheb}Around [1850,|eighteen fifty,] Chebyshev used this idea, with ratios of factorials, to bound how many primes there are, but only roughly: those numbers aren't divisible enough.
"""},
    {"id": "s13_theta", "title": "12 · The new idea", "text": """
The claimed proof manufactures far better numbers, from theta functions. {theta}Theta of t adds up e to the minus pi n squared t, over all integers n. It has a hidden mirror symmetry, which Riemann used to prove zeta's own.

{lift}Functions with symmetries like this, called automorphic forms, can be carried from one symmetry group to a larger one by integrating against a theta function: a theta lift. {chain}Chain m lifts, take a special value called a period, and you get an algebraic number whose divisibility grows along the chain. In the note's analogy, each lift mimics one more order of multiplicity.

{sqrt}How long a chain? Readers of the code describe two competing errors, roughly X over m, and m. They balance at m equals root X, leaving an error of about root X, the size the Riemann Hypothesis demands. {table}Claude suggested root X. Alpöge's comment: and yet, what else could it be?
"""},
    {"id": "s14_build", "title": "13 · The construction", "text": """
The argument is not short. {timeline}Alpöge's timeline runs from October sixth to November sixteenth, through much of modern number theory. {lean}The result is a Lean library of [175,187|a hundred seventy-five thousand] files and [17.4 million|seventeen point four million] lines, without a single comment.

{skeleton}Read from the top, its skeleton is short. {step1}Last step: no zeros to the right of one half, plus the mirror symmetry, gives the Riemann Hypothesis. {step2}Before that: if a weighted prime sum stays below about root x, there can be no zeros to the right of one half, for zeta and for every Dirichlet L-function. {step3}And the enormous middle, built from theta lifts, Galois representations, and tools from the Langlands program, proves that bound, {code}with chains of length at least x to the one half minus epsilon. {caveat}Readers also report that a few steps in the note's timeline have no visible counterpart in the code.
"""},
    {"id": "s15_check", "title": "14 · Checking it", "text": """
How can anyone trust seventeen million lines no human has read? {kernel}In Lean, every step must follow from earlier ones by fixed rules, and a small program, the kernel, checks them all. {four}Kevin Buzzard lists four questions to ask of AI-written Lean.

{q1}Is the statement right? Here it is Mathlib's own definition of the Riemann Hypothesis, vetted by experts. {q2}Does it compile? Dozens of people have rebuilt it. {q3}Does it prove exactly that statement, using only the standard axioms? Two independent tools say yes. {q4}Could it exploit a bug in Lean itself? Several independent checkers accepted it, two of them formally proved unable to accept a false proof.

{joint}So on November twenty-first, the Lean and Mathlib communities wrote: we have full confidence that Alpöge's proof of the Riemann Hypothesis is correct.
"""},
    {"id": "s16_close", "title": "15 · Where this leaves us", "text": """
So where are we? {certified}What's been certified is the classical Riemann Hypothesis. {dirichlet}A verification page at [MIT|M I T] reports that the library also proves the generalized hypothesis for Dirichlet L-functions. {notyet}The wider generalized hypothesis that the note claims hasn't been checked, and there's no human-readable proof yet. Alpöge says he intends to understand it, explain it, and write it properly. {clay}The Clay prize requires publication, two years, and general acceptance, and Clay's president called the road to real understanding long and difficult.

{close}So for now, it's a claimed proof: checked by machines, not yet understood by people. If it holds, the zeros really do all sit on one line, and the reason may be an old idea, counting with multiplicity, finally made to work for the whole numbers.
"""},
]
