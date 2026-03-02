# Boundary Conditions: Summary Post

A lot of people have asked me to simplify my research and offer my interpretation of it — something that explains my take without requiring a statistics degree to follow. So that's what this is. This post is my speculative interpretation of what the data shows, written in plain language and staying away from the heavier jargon. If you want the actual evidence, I encourage you to dig into the DD posts linked throughout. And if you *really* want more, the full papers with all the math, code, and reproducible scripts are on [GitHub](https://github.com/TheGameStopsNow/research).

**TL;DR:** I found out that when GME's settlement system gets squeezed, the pressure doesn't just disappear. It floods into other stocks, breaks government bond settlement, crosses national borders, and crosses national borders. Then I built a computer simulation using nothing but the SEC's own rules, and the system's heartbeat appeared on its own. The fix? Change four numbers. That's it.

> **Position disclosure:** I hold a long position in GME. I am not a financial advisor, attorney, or affiliated with any entity named in this post.

---

![Settlement failure contagion — four channels radiating outward from GME: lateral to KOSS, vertical to U.S. Treasuries, cross-border to European CSDs, and cross-border settlement export to European CSDs.](figures/chart_contagion_flow.png)

---

## Okay, So What Am I Looking At?

My [last series](../03_the_failure_waterfall/01_where_ftds_go_to_die.md) was about what happens *inside* GME's settlement plumbing. I mapped a 15-node regulatory cascade that FTDs bounce through over 45 business days. It was alarming, but I made one comforting assumption: the pressure stays inside GME's pipes.

It does not.

The pressure leaks out of GME and into places it has no business being. This series is about where it goes, how I know, and — surprisingly — how to fix it with math that fits on the back of a napkin.

---

## Part 1: The Overflow — [Full Post](https://www.reddit.com/r/Superstonk/comments/1rgrvuw/boundary_conditions_part_1_the_overflow/)

### The short version

Imagine you squeeze a water balloon. The water doesn't vanish. It squirts out wherever the rubber is thinnest.

In May 2024, the SEC shortened stock settlement from two days to one day. The naive expectation: less time to settle = fewer problems. What actually happened: the settlement pressure inside GME collapsed by 92%. Sounds great, right?

Except the *same pressure* showed up in KOSS — a tiny headphone company nobody covers — amplified by over **1,000%**. Same frequencies. Same patterns. Just a different ticker symbol. The pressure didn't disappear. It squirted out the thinnest part of the rubber.

Why KOSS? Because KOSS has no options chain. No analyst coverage. No regulatory eyeballs. If you were looking for the path of least resistance to park unresolved obligations, you would literally design KOSS. Whether this is deliberate or emergent, I can't tell from the data. The data just says it happened, and it happened at a statistical significance of 1,050 standard deviations (p < 0.0001). For context, physicists get excited about 5 sigma. This is not subtle.

### But wait, it gets worse

I also found that GME's settlement failures *predict* U.S. Treasury bond settlement failures one week in advance (Granger causality test: F = 19.20, p < 0.0001). Let me say that again. A $10 billion video game retailer predicts when the U.S. government's $700 billion-per-day bond market will have delivery problems. It's the only stock out of seven I tested that does this.

> **Update:** A reader asked about the small sample size. I expanded the test to **15,916 tickers** using the full SEC FTD universe. Result: 16% of equities show significant Granger causality with Treasury fails (vs 5% expected by chance), with 228 surviving Bonferroni correction. The signal is systemic, not GME-specific -- which actually strengthens the core thesis that equity settlement stress contaminates sovereign debt markets. [Expanded analysis in the repo.](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/granger_panel_expanded.py)

The proposed mechanism isn't magic. When GME FTDs spike, clearing members get hit with margin calls. They need to post high-quality collateral — Treasuries — fast. That fire sale creates delivery failures in the bond market one week later. The plumbing connects them.

In December 2025, GME FTDs spiked to +4.2 sigma (p < 0.0001). One week later, Treasury fails spiked to +4.0 sigma (p < 0.0001), $290.5 billion in a single week. The lag matched perfectly.

The tail is wagging the dog. [The full data and statistical tests are in Part 1.](https://www.reddit.com/r/Superstonk/comments/1rgrvuw/boundary_conditions_part_1_the_overflow/)

---

## Part 2: The Export — [Full Post](https://www.reddit.com/r/Superstonk/comments/1rgrvz5/boundary_conditions_part_2_the_export/)

### The short version

Here's a fun game. You have an unresolvable delivery obligation in the United States. Penalty: roughly $10 million per day (Reg SHO lockout). You also have an office in Europe. Penalty for the same failure in Europe: roughly $1,750 total for 35 days (CSDR cash penalties).

That's a **5,714:1 cost difference**.

If you're rational and you have a European affiliate, you don't need a conspiracy. You need a calculator.

I tested whether European settlement failures spike during *U.S.* stress events (and not European ones). They do. And they do it selectively — only equities and ETFs spike; European government bonds don't. If Europe were just having its own bad week, sovereign bonds would spike first. The selectivity is the fingerprint.

> **⚠️ Correction (Mar 2, 2026):** This section originally described BBBY generating zombie FTDs "824 days" after its CUSIP was cancelled. This was incorrect — caused by a ticker symbol collision when Beyond, Inc. (Overstock) reclaimed the BBBY ticker in August 2025 under a different CUSIP. The original BBBYQ CUSIP's FTDs ceased within days of cancellation. See [Correction #22](https://github.com/TheGameStopsNow/research/blob/main/papers/corrections.md). [Full analysis in Part 2.](https://www.reddit.com/r/Superstonk/comments/1rgrvz5/boundary_conditions_part_2_the_export/)

---

## Part 3: The Tuning Fork — [Full Post](https://www.reddit.com/r/Superstonk/comments/1rgrwaa/boundary_conditions_part_3_the_tuning_fork/)

### The short version

This is the part that made me sit back in my chair and say something I can't print here.

If the macrocycle is real, and it's caused by the rules rather than by any specific bad actor, then I should be able to build a simulation using *only* the SEC's regulatory deadlines — no market data, no FTD history, no cycle length specified anywhere — and the cycle should emerge on its own. Like dropping a tuning fork and hearing the note without anyone playing it.

So I built three software agents. Gave them four regulatory deadlines. Hit "run."

The 630-day macrocycle appeared at 42 times the background noise. Unprompted. Uncalibrated. Just the rules.

### Why it happens

The math is almost embarrassingly simple. The four key regulatory deadlines are T+6, T+13, T+35, and a 10-day review cycle. They share common factors — 6 and 10 are both divisible by 2, 35 and 10 share a factor of 5. Because of that, the Least Common Multiple (think of it as the first time all four clocks strike midnight simultaneously) is 2,730 business days.

That's the system's heartbeat. It's not a conspiracy. It's arithmetic.

### The T+1 punchline

Under the new T+1 rules, those deadlines shift to 5, 12, 34, and 10. The system's heartbeat compresses from roughly 2.5 years to **exactly one trading year**. The SEC shortened settlement to reduce risk. The math says they made the cycle faster. Settlement stress that used to spread over 2.5 years now compounds annually.

This is like fixing a car that overheats every 100 miles by making it overheat every 40 miles instead.

### The fix

Choose deadlines that share no common factors: **7, 11, 37, and 13**. The heartbeat stretches to 37 years. No standing wave can form at any frequency that matters. Same regulatory intent. Same number of deadlines. Just different numbers. [The full model and math are in Part 3.](https://www.reddit.com/r/Superstonk/comments/1rgrwaa/boundary_conditions_part_3_the_tuning_fork/)

---

## How I Tried to Prove Myself Wrong

I ran five tests specifically designed to kill my own thesis. Here's what I threw at it:

1. **"The Treasury thing is just general market noise."** → First tested 7 stocks. Only GME predicted Treasury fails (F = 19.20, p < 0.0001). Then a reader said 7 wasn't enough, so I tested **15,916**. Turns out 16% of all stocks predict Treasury fails — way more than the 5% you'd expect by random chance. It's not just GME. It's the whole system leaking into sovereign debt.
2. **"KOSS is just small-float weirdness."** → Float-normalized it. Still 1,050 sigma above controls. Not weirdness.
3. ~~**"BBBY is a database glitch."**~~ → **Retracted.** This was a ticker collision artifact. See [Correction #22](https://github.com/TheGameStopsNow/research/blob/main/papers/corrections.md).
4. **"The simulation cycle is an artifact of the math."** → Applied a decontamination algorithm that's specifically designed to kill artifacts. The signal got *stronger*.
5. **"The European spikes are their own problem."** → Only equities spiked. Government bonds didn't. It's not domestic.

Combined odds that the remaining four alternative explanations are simultaneously correct remain negligible.

I genuinely wanted at least one to work. "You made a math error" is a much more comfortable conclusion than "the settlement system is a leaky resonant cavity that contaminates sovereign debt." But here we are.

---

## What Would Change My Mind

1. If **April-May 2026** passes with zero anomalous activity, the next convergence prediction fails.
2. If **other stocks** start predicting Treasury fails, the GME signal is just generic market noise.
3. If the **annual compression** doesn't appear in a few years of T+1 data, the model is wrong.
4. ~~If **BBBY FTDs** hit zero and stay there for 90 days, the zombie is actually dead.~~ **Retracted** — see Correction #22.

I'll be the first to tell you if any of these happen.

> [!NOTE]
> **Timing footnote:** On **April 3, 2025** — two days into what this research identifies as the beginning of the Spring 2026 macrocycle convergence window (where 6-year terminal swap maturities, LEAPS roll cycles, and the T+525 harmonic align) — Ryan Cohen posted: *"Now we know why Buffett is sitting on 300 billion."* Three days later: *"BREAKING: Jim Cramer saves the stock market by predicting Black Monday 2025."* If RC is aware of the settlement mechanics documented in this series, "Buffett sitting on 300 billion" isn't commentary on Berkshire's earnings. It's commentary on what *Buffett sees coming* that would justify hoarding cash of that magnitude — and the timing against the macrocycle convergence window is either coincidental or telling.

---

## The Series

| Part | Title | One Sentence |
|:----:|:------|:-------------|
| [1](https://www.reddit.com/r/Superstonk/comments/1rgrvuw/boundary_conditions_part_1_the_overflow/) | **The Overflow** | Settlement pressure migrates to other stocks and predicts Treasury fails |
| [2](https://www.reddit.com/r/Superstonk/comments/1rgrvz5/boundary_conditions_part_2_the_export/) | **The Export** | Obligations cross borders and persist on cancelled securities |
| [3](https://www.reddit.com/r/Superstonk/comments/1rgrwaa/boundary_conditions_part_3_the_tuning_fork/) | **The Tuning Fork** | The macrocycle is arithmetic; four numbers kill it |

⬅️ **Previously:** [The Failure Waterfall](../03_the_failure_waterfall/01_where_ftds_go_to_die.md) (Parts 1–4)

---

All code, data, and results: [github.com/TheGameStopsNow/research](https://github.com/TheGameStopsNow/research)

---

*Not financial advice. Forensic research using public data. I'm not a financial advisor, attorney, or affiliated with any entity named in this post. The author holds a long position in GME.*

*"I'm going to have to science the shit out of this."*
*— Mark Watney*
