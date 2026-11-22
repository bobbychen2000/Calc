"""Mandarin narration (Simplified Chinese, mainland 普通话): the same 16 scenes, cues and order as
script.py, translated for meaning (not word order) for an engineer who is rusty on college math.

Voiced by voice_zh.py (Kokoro-82M-v1.1-zh, misaki Chinese G2P + an English G2P for Latin-script
words), which synthesises one caption chunk at a time: the text is split at Chinese punctuation
(，。；：、？！) and at {cue}s, and each chunk becomes one caption (<= ~24 characters).

Markup inside "text" (as in script.py):
  [display|spoken]   captions show `display`, the voice says `spoken` (never split inside; a chunk
                     ends there when `display` ends in punctuation)
  {cue}              a sync point for the visuals: the time the next chunk starts
  blank line         paragraph break (a longer pause)

TTS rules followed here (misaki zh G2P, checked 2026-11-22):
  * Greek letters and math symbols (ζ π σ ψ γ θ ε √ ≤ ∑, super/subscripts) are dropped by the
    voice, and "Alpöge" is mangled: every symbol, formula and that name is [display|spoken], Greek
    letters spoken as the English words zeta, sigma, psi, gamma, epsilon, π as 派, "Alpöge" as
    "Alpogay" (AL-poh-gay, as script.LEXICON).  θ is the exception, spoken 西塔 (the usual
    Chinese reading): through this voice the English "theta" came out as "fei-ta" / "C-de" (Whisper
    small heard 飞的 / C的 / feta / zeta), which a listener could take for zeta; 西塔 was heard 稀塔.
  * Years in Arabic numerals are read as cardinals (1859 年 -> 一千八百五十九年), so every year is
    [1859 年|一八五九年]; month / day dates (11 月 20 日) are read correctly and stay plain.
  * The middle dot of transliterated names (欧拉, 黎曼, 冯·曼戈尔特, 斯捷潘诺夫) is an unknown
    token for the voice: those names are [display|spoken] without it.
  * Numbers over 100 that are not dates carry a spoken form in Chinese numerals.
  * Polyphones the G2P gets wrong (pypinyin via misaki, checked chunk by chunk): 行 as the measure
    word for lines (háng) is read xíng, so "1700 万行" is spoken with the homophone 航; 相量 (phasor)
    is read xiāng-, so it is spoken 向量 (the same sound, xiàngliàng); 为 in 约为 / 为零 is read
    wèi, so the text says 是 / 等于; the verb 数 (shǔ) is read shù, so counting is 统计 / 计数;
    重 in 计重数 / m 重零点 is read zhòng, so the text says 按重数计数 / m 阶零点; 长 in 链长 /
    很长 is read zhǎng, so 链的长度 / 漫长; 处处 is read chǔchu, so 在哪里都; 倒数 (dàoshù) is
    read dàoshǔ, so 一除以每个平方数; 好得多 is read hǎo dé duō, so 好很多.
  * Closing quotation marks sit before the sentence-ending punctuation (a chunk must not start
    with a lone ”).

Wording follows i18n/glossary_zh.json and keeps every hedge and attribution of
research/factcheck.md: a claimed proof (待确认的证明 / 他相信), the Lean + Mathlib statement
certifies the classical RH only ("完全确信" only inside their quote), Sutherland's page reports
the Dirichlet L-functions (这一意义上的广义黎曼猜想), other L-functions not checked, the note only
expects the Extended RH, Clay's three conditions, the mechanism attributed to the note and the
AI-assisted guides, the timeline compiled by Claude per the note.
"""

LEXICON = {}

SCENES = [
    {"id": "s01_open", "title": "", "text": """
{title}[2026 年 11 月 20 日，|二零二六年十一月二十日，]数学家 [Levent Alpöge|Le-vent Alpogay] 发布了一篇四页的短文。他写道，他相信自己与 Claude 合作，找到了黎曼猜想的一个证明。黎曼猜想或许是数学中最著名的未解决问题。{lean}他没有给出书面证明，而是发布了 [1700 万行|一千七百万航] Lean 代码；Lean 是一种由计算机检查每一步推理的语言。{joint}一天后，在一份联合声明中，Lean 及其共享数学库 Mathlib 的两个社区写道，[原话是（译文）：|原话是：]“我们完全确信，[Alpöge|Alpogay] 对黎曼猜想的证明是正确的”。

{plan}下面，我们从素数出发，一步步走到这个主张。
"""},
    {"id": "s02_primes", "title": "1 · 数素数", "text": """
先说素数：[2、3、5、7、11……|二、三、五、七、十一，]它们是大于 1 的整数，只有 1 和它本身两个因数。{grid}近看，它们显得杂乱无章。{staircase}但我们来统计一下。[π(x)|派 x] 是不超过 x 的素数个数。它的图像是一道阶梯，{zoom}从远处看，却[平滑得惊人。|平滑的惊人。]

{gauss}高斯少年时猜测：x 附近的数是素数的概率，大约是 [1/ln x。|x 的自然对数分之一。]把这些概率加起来，就是对数积分 [li(x)。|L I x。]{table}一百万以内有 [78,498|七万八千四百九十八] 个素数，而 [li(x)|L I x] 的误差只有一百三十左右。{question}真正的问题是：这个误差最大能有多大？
"""},
    {"id": "s03_euler", "title": "2 · 欧拉的桥梁", "text": """
比这早几十年，[莱昂哈德·欧拉|莱昂哈德欧拉]研究过另一个无穷级数。{basel}一加四分之一，加九分之一：一除以每个平方数，全部加起来。它恰好等于 [π²/6。|派的平方除以六。]{harmonic}如果换成 n 分之一本身，这个和就会无限增长，只是很慢。

{product}接着，欧拉找到了通往素数的桥梁。当 s 大于一时，[1/nˢ|n 的 s 次方分之一] 的和，等于对全体素数的一个连乘积。{expand}[把每个因子展开成 1 + p⁻ˢ + p⁻²ˢ + …，|把每个因子展开成一，加 p 的负 s 次方，加 p 的负二 s 次方，等等，]再全部乘开：每个正整数分解成素数的方式只有一种，所以每一项恰好出现一次。{zeta}这个和就是 [ζ 函数。|zeta 函数。]一边关乎所有正整数，另一边只关乎素数。
"""},
    {"id": "s04_complex", "title": "3 · 旋转的箭头", "text": """
[1859 年，|一八五九年，][伯恩哈德·黎曼|伯恩哈德黎曼]迈出了改变一切的一步：让 s 取复数。{phasor}如果你用过[相量|向量]，就知道这意味着什么。把 s 写成 [σ + it。|sigma 加 i t。]那么 [n⁻ˢ|n 的负 s 次方] 是一个箭头：长度是 [n^−σ，|n 的负 sigma 次方，]转过的角度是 [t·ln n。|t 乘 n 的自然对数。]

{spiral}所以，[ζ|zeta] 是一串一边旋转一边缩短的箭头之和。首尾相接，它们排成一条螺旋。{converge}当 [σ|sigma] 大于一，箭头[缩短得够快，|缩短的够快，]螺旋就收拢到一点：那就是 [ζ|zeta] 的值。
"""},
    {"id": "s05_continue", "title": "4 · 整个复平面", "text": """
{diverge}当 [σ|sigma] 不超过一，箭头[缩短得不够快，|缩短的不够快，]和就永远稳定不下来。{geom}想想一加 x，加 x 平方，一直加下去。它只在负一到一之间成立，但显然“想”等于 [1/(1 − x)，|一除以一减 x 的差值，]而这个式子除了 x 等于一，在哪里都有意义。

{unique}同样，[ζ|zeta] 要延拓到整个复平面、又保持复可微，方式恰好只有一种，这就是它的解析延拓：除了 s 等于一，在哪里都有定义。{map}这就是延拓后的 [ζ|zeta]。颜色表示 [ζ|zeta] 值的方向，每过一道环，值的大小就翻一倍。{zeros}在所有颜色交汇的暗点，[ζ|zeta] 等于零。
"""},
    {"id": "s06_zeros", "title": "5 · 零点", "text": """
有些零点很好找：{trivial}[−2、−4、−6，|负二、负四、负六，]等等，叫作平凡零点。{strip}其余的零点都在一条窄带里，叫临界带，那里 [σ|sigma] 介于零和一之间。

{symmetry}有一个精确的恒等式，叫作函数方程，它把 [ζ(s)|s 处的 zeta 值] 和 [ζ(1 − s)|一减 s 处的 zeta 值] 联系起来。加上 [ζ|zeta] 的上下对称，零点就关于临界带的中线左右镜像对称：{line}这条中线就是临界线，实部是二分之一。{first}实轴上方的第一个零点，位于 [½ + 14.1347 i。|二分之一加十四点一三四七 i。]
"""},
    {"id": "s07_rh", "title": "6 · 猜想", "text": """
{state}黎曼猜想：每个非平凡零点，都恰好落在这条中线上。不是在附近，而是就在这条线上。{riemann}黎曼在他那篇十页的论文里说，这“很可能”成立，然后就转而讨论别的问题了。

{zplot}在这条线上，我们能亲眼看到零点出现。这是哈代 Z 函数：它在临界线上取实数值，等于零的地方，恰好就是 [ζ|zeta] 在这条线上等于零的地方。{counter}[14.13，|十四点一三，][21.02，|二十一点零二，][25.01。|二十五点零一。]{checked}计算机已按顺序检验了超过十二万亿个零点：无一例外，都在临界线上。{prizes}[1900 年，|一九零零年，]它被列入希尔伯特著名的 [23 个问题；|二十三个问题；][2000 年|二零零零年]起，克雷数学研究所为它的证明悬赏一百万美元。
"""},
    {"id": "s08_music", "title": "7 · 由波生成素数", "text": """
素数为什么会在意零点在哪里？{formula}因为有一个精确的公式：显式公式。它出自黎曼的论文，这种形式由[冯·曼戈尔特|冯曼戈尔特]证明。{psi}这次改成统计素数幂，每个都用它底数的对数加权：这就是 [ψ(x)，|psi x，]一道更干净的阶梯。公式说，[ψ(x)|psi x] 等于 x，减去每对零点贡献的一个波，再加一个微小的修正。

{waves}位于 [½ + iγ|二分之一加 i gamma] 的零点和它的镜像伙伴，会贡献一个波：把 [ln x|x 的自然对数] 看作时间，它的振荡频率就是 [γ。|gamma。]{add0}先画光滑部分。{add1}加第一个波。{add10}十个。{add100}一百个。{add1000}一千个。{jumps}素数的阶梯，就从纯粹的波里浮现出来。零点是频率；素数是信号。
"""},
    {"id": "s09_sqrt", "title": "8 · 那条线为何重要", "text": """
关键在于：{sizes}每个波都像 x 的某次方那样增长，指数是它的零点的实部。零点在临界线上，它的波就像根号 x 那样增长；要是零点的实部是四分之三，波就会像 x 的四分之三次方那样增长：[响亮得多。|响亮的多。]

{rh_eq}所以，黎曼猜想是说，素数计数的误差小到不能再小：大约是根号 x，至多相差对数因子。{walk}这正是抛 x 次硬币时，随机游走通常偏离的幅度。{bound}假设黎曼猜想成立，[π(x)|派 x] 与 [li(x)|L I x] 的差距甚至有一个显式界，从 x 等于 [2657|两千六百五十七] 起成立。{data}一百万以内，素数始终在界内。
"""},
    {"id": "s10_curves", "title": "9 · 类似猜想已被证明的世界", "text": """
在一个平行世界里，类似的猜想几十年前就已被证明。{clock}在有 p 个钟点的钟面上做算术，p 是素数，统计 [y² + y = x³ − x|y 平方加 y，等于 x 立方减 x] 有多少个解。{grid}p 等于十三时，有十五个解，外加一个无穷远点。

{count}每个 x 对应两个或一个 y 值，或者没有，平均一个，所以预期点数大约是 p 加一。{hasse}惊人的是，实际点数离 p 加一有多近：对每个素数，误差都不超过两倍根号 p。{weil}[20 世纪 30 年代，|二十世纪三十年代，]哈塞对这类曲线证明了这一点。[40 年代，|四十年代，]韦伊证明了适用于所有曲线的一般版本。[1974 年，|一九七四年，]德利涅[走得更远。|走的更远。]每条这样的曲线都有 [ζ 函数；|zeta 函数；]对这一条，这个界恰好就是它的黎曼猜想。
"""},
    {"id": "s11_stepanov", "title": "10 · 计重数", "text": """
[1969 年，|一九六九年，][谢尔盖·斯捷潘诺夫|谢尔盖斯捷潘诺夫]找到了证明这类界的初等方法。原理很简单。{poly}一个 D 次多项式，按重数计数，最多有 D 个根：二重根算两次。

{aux}于是构造一个辅助多项式：它不恒等于零，这正是难点；它在全部 N 个解处都等于零，而且每处都是 m 阶零点。{count}统计根的个数，就得到 N 乘 m 不超过 D。{tune}m 越大，一笔固定开销[摊得越薄，|摊的越薄，]大约是 p 除以 m；但零点每多一阶，次数也要跟着增加，这一项大约是 m。m 约等于根号 p 时，两者平衡。{moral}约根号 p 的重数，带来约根号 p 的误差。
"""},
    {"id": "s12_obstacle", "title": "11 · 整数版本", "text": """
斯捷潘诺夫用导数探测重数：在二重根处，f 和它的斜率都等于零。{quote}[Alpöge|Alpogay] 说，自己的论证脱胎于斯捷潘诺夫的论证，但他也写道：在整数上很难找到重数，这相当于要对整数求导之类的事情。

{cousin}不过，根的计数法在整数上有个古老的“近亲”：一个非零整数，若能被许多素数整除，就一定很大。{binom}[C(20,10)|二十取十的组合数] 能被十到二十之间的每个素数整除，却小于 [4¹⁰，|四的十次方，]所以这样的素数不可能太多。{dict}每个素因子相当于一个根，它的幂次相当于重数，取对数后的大小相当于次数。{cheb}[1850 年前后，|一八五零年前后，][切比雪夫|Chebyshev]就用这个想法，借助阶乘之比，给素数的个数定出了上下界，但界很粗：这些数的可除性还不够高。
"""},
    {"id": "s13_theta", "title": "12 · 新想法", "text": """
研读代码的人说，这份待确认的证明，相当于把[切比雪夫|Chebyshev]的想法用在了好很多的数上，而这些数是用 [θ 函数|西塔函数]构造的。{theta}[θ 函数|西塔函数]有一种隐藏的镜像对称，黎曼正是用它证明了 [ζ|zeta] 自身的对称。

{lift}具有这类对称性的函数叫作自守形式，它们可以从一个对称变换群，搬到与它配对的另一个群上：办法是乘上 [θ 核|西塔核]再积分，[θ 核|西塔核]是 [θ 函数|西塔函数]的多变量“近亲”。这叫 [θ 提升。|西塔提升。]{chain}把 m 次提升串联起来，再读出一个数，也就是所谓的“周期”。按短文和导读的描述，它不等于零，而且每提升一次，对某些素数的可除性就更高：每次提升都模仿多一阶重数。{weigh}它的可除性本身就是素数的加权计数，所以“可除性不超过大小”给这个计数设了上限。

{sqrt}对不超过 X 的素数，链的长度要多少？有几份导读是借助 AI 根据代码写成的，它们说：和斯捷潘诺夫的方法一样，误差有两项，一项约是 X 除以 m，另一项约是 m。两者在 m 约等于根号 X 时平衡，留下约根号 X 的误差：正是黎曼猜想所要求的。{table}Claude 建议链的长度取根号 X。[Alpöge 对此写道（译文）：|Alpogay 对此写道：]可是它还能是别的什么呢？
"""},
    {"id": "s14_build", "title": "13 · 构造", "text": """
{timeline}短文里有一份粗略时间线，[Alpöge|Alpogay] 说是 Claude 整理的，从 10 月 6 日到 11 月 16 日。{lean}成果是一个 Lean 代码库：[175,187|十七万五千多] 个文件，[1740 万行|一千七百四十万航]，没有一条注释。

{skeleton}从顶层读下来，骨架很短。{step1}最后一步：二分之一右侧没有零点，加上镜像对称，就得到黎曼猜想。{step2}再往前：如果加权素数和在很宽的区间上，都保持在大约根号 x 以下，二分之一右侧就不可能有零点，因为这样的零点产生的波更响亮，会打破这个界。这涵盖了 [ζ 函数|zeta 函数]和它的近亲狄利克雷 L 函数，后者按余数给素数分类。{step3}庞大的中间部分，用 [θ 提升|西塔提升]加上来自数论各领域的重型工具，证明了这个界，{code}所用链的长度至少是 [x^(1/2 − ε)：|x 的二分之一减 epsilon 次方：]略小于根号 x。{caveat}研读代码的人还报告：短文时间线中有几步，在代码里找不到明显的对应。
"""},
    {"id": "s15_check", "title": "14 · 检验", "text": """
[1700 万行|一千七百万航]没人完整读过的代码，怎么能信任它？{kernel}在 Lean 里，每一步都必须按固定规则从前面的步骤推出，再由一个小程序——内核——全部检查一遍。{four}检验 AI 写的 Lean 代码，Kevin Buzzard 列出了四个问题。

{q1}命题表述对吗？这里用的是 Mathlib 里的定义，Mathlib 即 Lean 的共享数学库；定义由人编写，经专家审核。{q2}能编译通过吗？已有数十人重新构建过它。{q3}它证明的恰好是这个命题，且只用了标准公理吗？两个独立工具都说是。{q4}会不会利用了 Lean 自身的漏洞？多个独立检查器都接受了它，其中两个检查器还附有形式化证明：在集合论框架下，它们绝不会接受错误的证明。

{joint}11 月 21 日那份表示“完全确信”的声明，依据的就是这些。
"""},
    {"id": "s16_close", "title": "15 · 现状", "text": """
那么，现状如何？{certified}Lean 与 Mathlib 的声明所认证的，是经典黎曼猜想。{dirichlet}Andrew Sutherland 在 [MIT|麻省理工学院] 的验证页面报告称，这个代码库对每个狄利克雷 L 函数，也证明了同样的“零点都在临界线上”的命题，也就是这一意义上的广义黎曼猜想。{notyet}至于其他类型 L 函数的更广版本，还没有经过检查；[Alpöge|Alpogay] 只是预期，假以时日也能得到其中之一——扩展黎曼猜想。而且还没有供人阅读的证明；他说会好好写出来。{clay}此外，克雷奖要求：先发表，再过两年，然后获得普遍认可。

{close}所以目前，这是一份待确认的证明：经过了机器检查，但还没有用人类的语言解释清楚。如果它成立，非平凡零点就真的全都落在同一条线上；而背后的原因也许是：一个古老的想法，“按重数计数”，终于在整数上奏效了。
"""},
]
