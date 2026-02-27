# Boundary Conditions: The Complete Picture

**TL;DR:** The [Failure Waterfall](../03_the_failure_waterfall/01_where_ftds_go_to_die.md) series mapped a 15-node regulatory cascade inside a single stock's settlement plumbing. This series asks what happens when that plumbing springs a leak. Answer: the settlement energy floods into adjacent tickers, contaminates sovereign debt, crosses national borders, and persists on securities that no longer exist. Then I built a simulation from nothing but the SEC's own rules and watched the macrocycle emerge by itself. The fix is four numbers.

> **⚠️ Methodology Note:** This is a summary and interpretive synthesis. Where I state something as a data finding, the reproducible scripts and data are linked in the individual posts and the [public repository](https://github.com/TheGameStopsNow/research). Where I offer interpretation (clearly marked as "my take"), that is my inference from the patterns. All code is published. All data is sourced. If I'm wrong, show me where with data.

> **Position disclosure:** I hold a long position in GME. I am not a financial advisor, attorney, or affiliated with any entity named in this post.

---

![Settlement failure contagion — four channels radiating outward from GME: lateral to KOSS, vertical to U.S. Treasuries, cross-border to European CSDs, and zombie persistence on BBBY's cancelled CUSIP.](figures/chart_contagion_flow.png)

---

## What This Series Found

The Failure Waterfall mapped the *internal* dynamics of GME's settlement lifecycle. It was alarming. But I kept assuming the settlement energy stayed inside GME's plumbing.

It doesn't. It leaks everywhere. And "everywhere" includes places that should terrify you.

---

## Layer 1: The Overflow ([Part 1](01_the_overflow.md))

This is where I started to get nervous.

The settlement energy doesn't stay inside one stock. It floods outward through three channels, and I'm going to walk through each one because they're all independently alarming.

**Channel 1: Ticker migration.** When T+1 compressed GME's settlement frequencies by 92%, the same frequencies amplified by **+1,051%** in KOSS — a tiny headphone company with no options chain and no institutional coverage. I checked whether this could be a small-float denominator effect. It can't. The normalization constant cancels. Against control tickers, the KOSS amplification registers at **1,050 standard deviations**. For reference, a 5-sigma event is supposed to happen once every 3.5 million observations. This is 1,050 sigma. This is not noise. This is someone screaming.

**Channel 2: Sovereign contamination.** I ran a Granger causality test — basically asking "does knowing GME's past FTDs improve your prediction of Treasury settlement fails?" — across 7 equities using NY Federal Reserve data. Only GME is significant (F = 19.20, p < 0.0001). The relationship holds at every tested lag from 1 through 6 weeks. AMC, KOSS, TSLA, AAPL, MSFT: all non-significant. The proposed mechanism: GME FTD spikes trigger VaR margin calls, clearing members sell Treasuries to raise cash, and the sovereign debt market develops delivery failures one week later.

Let me put that in perspective. GME's total market cap is about $10 billion. The Treasury market moves $700 billion per day. And the video game store uniquely predicts when the government's IOUs won't settle on time. That's not supposed to happen.

**Channel 3: ETF substitution.** The XRT ETF creation/redemption mechanism allows Authorized Participants to create XRT shares, extract GME from the basket, and deliver those shares to satisfy FTD close-out deadlines. The SEC explicitly blessed this in a 2017 no-action letter to Latour Trading. The December 2020 GME spikes produced XRT FTD surges at +5.5 sigma on January 27, 2021 — the day before the buy-button removal.

### My take

In December 2025, the week after the GME spike hit +4.2 sigma, Treasury fails hit $290.5 billion at +4.0 sigma. The separation? Exactly one week. The Granger-optimal lag.

A single mid-cap stock is degrading sovereign debt settlement because it's connected to the Treasury market through the clearing infrastructure. The tail is wagging the dog. That's... not great.

---

## Layer 2: The Export ([Part 2](02_the_export.md))

The settlement boundary extends beyond U.S. borders. Because of course it does.

Here's a fun math problem. A 35-day settlement fail costs approximately $1,750 in Europe under CSDR cash penalties. The same fail in the U.S. results in a Reg SHO lockout costing approximately $10 million per day.

That's a **5,714:1 cost asymmetry**.

If you're a rational actor with an unresolvable U.S. delivery obligation and a European affiliate, the math is hard to argue with. You'd be *irrational* not to move the obligation offshore.

The selectivity test confirms it: when U.S. stress events occurred (the T+1 transition, the DFV return), European equity and ETF fail rates spiked. European government bond fail rates did not. If these spikes were caused by domestic European turmoil, sovereign bonds would be the first to show stress. The fact that only equities and ETFs reacted, and only during U.S. events, points in one direction.

And then, again, there's BBBY. The stock was delisted on September 29, 2023. The CUSIP was cancelled. The company doesn't exist anymore. There is nothing to trade. Nothing to deliver. Nothing to borrow.

SEC data shows 31 unique, actively fluctuating FTD values reported continuously through late 2025. That's 824 days after cancellation. 43% are block-sized changes exceeding 10,000 shares. Alternating injection and extraction. These are not database artifacts. Someone is actively managing delivery obligations on a security that no longer exists.

### My take

The BBBY finding bothers me more than anything else in this series. Not because it's the largest by dollar value — it isn't. It bothers me because it reveals something fundamental about the plumbing.

**The system has no garbage collection.** When a security ceases to exist, the obligation doesn't get cancelled. It doesn't get written off. It doesn't get flagged for resolution. It just sits there, actively cycling between counterparties, forever, because nobody wrote the code to handle this edge case. This is 50-year-old infrastructure that was never designed for a world where obligations could outlive the securities they reference.

As a software engineer, this is the kind of bug that keeps me up at night. Not because it's complicated. Because it's obvious. And nobody fixed it.

---

## Layer 3: The Tuning Fork ([Part 3](03_the_tuning_fork.md))

Okay. This is my favorite part. Stay with me.

If the macrocycle is real, and it's caused by the regulatory structure rather than by any specific market participant, then I should be able to build a simulation from nothing but the SEC's own rules and watch the cycle emerge on its own. No market data. No FTD history. No cycle length specified anywhere. Just the rules.

So I did. Three software agents. Four coded regulatory deadlines (T+6, T+13, T+35, 10-day RECAPS cycle). Hit "run."

The 630-day macrocycle appeared as the dominant spectral peak at **42.3x mean power**. It survived Welch PSD decontamination, which is specifically designed to eliminate the most common FFT windowing artifact. And the math explaining why is almost embarrassingly clean:

> LCM(6, 13, 35, 10) = 2,730 business days; 4th harmonic = 682.5 bd (~2.7 years)

That's it. The macrocycle exists because the regulatory deadlines share common factors. 6 and 10 are both divisible by 2. 35 and 10 are both divisible by 5. Those shared factors keep the LCM small enough that its harmonics land on market-observable timescales. Every 2,730 business days, all four regulatory clocks reset to zero simultaneously. The system has a heartbeat, and it's set by arithmetic.

Now here's the punchline.

Under T+1, the deadlines shift to (5, 12, 34, 10). The LCM drops to 1,020. The 4th harmonic: **255 business days. Exactly one trading year.** The SEC shortened settlement to reduce risk. The math says they compressed the macrocycle from 2.5 years to 1 year. Settlement stress that previously accumulated over 2.5 years will now compound annually.

And the fix? Choose deadlines that share no common factors. Replace (5, 12, 34, 10) with **(7, 11, 37, 13)**. The LCM jumps to 37,037 business days. The 4th harmonic: 9,259 business days. About 37 years. No standing wave can form at any frequency that matters.

### My take

This is the part that gives me hope. The system's oscillation is not a conspiracy. It's not a cabal of evil short sellers coordinating in a smoke-filled room. It's *math*. The SEC's close-out deadlines share common factors, and those common factors produce harmonics at market-observable frequencies. Any system with these deadlines will oscillate, regardless of who participates.

And if it's math, the fix is also math. Four numbers. That's all. Change the BFMM close-out from T+5 to T+7. Change the Threshold trigger from T+12 to T+11. Change the hard deadline from T+34 to T+37. Change the RECAPS cycle from 10 to 13 business days. Preserve all existing regulatory intent. Change nothing about market structure. Just make the gears stop meshing.

Four numbers. I know it sounds too simple. But the Martian atmosphere is 96% CO₂, and the fix for that was a box of lithium hydroxide and some duct tape. Sometimes the answer *is* simple. The hard part is knowing which four numbers to change.

---

## The Combined Falsification Battery

I want to talk about how I tried to prove myself wrong, because I think that matters.

Across Parts 1 through 3, I ran five adversarial tests, each designed to kill the thesis. Each null hypothesis was given a generous prior probability:

| Test | Null Hypothesis | Method | Result |
|:----:|:----------------|--------|:------:|
| (a) | Granger causality is macro noise | 7-equity panel | Only GME significant (F=19.20) |
| (b) | KOSS is small-float noise | Float normalization | z = 1,050.9 against controls |
| (c) | BBBY is database artifacts | Block-size analysis | 0% admin noise, 43% block-sized |
| (d) | ABM macrocycle is FFT artifact | Welch PSD | Power *increases* to 42.3x |
| (e) | EU spikes are domestic turmoil | Asset class selectivity | Only eq/ETF spiked; bonds didn't |

Combined probability that all five nulls simultaneously explain the data: **< 0.03%**.

None of them worked. And believe me, I wanted at least one of them to work, because "you made a math error" is a much simpler conclusion than "the settlement system is a resonant cavity contaminating sovereign debt."

---

## What Would Change My Mind

Science doesn't work if you don't say what would prove you wrong. So here's my list:

1. **If April-May 2026 passes with zero anomalous activity.** The Spring 2026 convergence prediction fails. Major problem.
2. **If multiple equities Granger-cause Treasury fails.** The GME-specific channel dissolves into generic macro noise. Less interesting. Also less alarming.
3. **If the annual compression doesn't appear in 2-3 years of T+1 data.** The LCM model is wrong. Back to the drawing board.
4. **If BBBY FTDs drop to zero for 90+ consecutive days.** The zombie obligations are being genuinely unwound. The zombie is actually dead.

As of this writing, none of these have occurred. I'll be the first to tell you if they do.

---

## The Series at a Glance

| Part | Title | One-Sentence Summary |
|:----:|:------|:---------------------|
| [1](01_the_overflow.md) | **The Overflow** | Settlement energy migrates to adjacent tickers and contaminates sovereign debt |
| [2](02_the_export.md) | **The Export** | Obligations cross national borders and persist on securities that no longer exist |
| [3](03_the_tuning_fork.md) | **The Tuning Fork** | An agent-based model proves the macrocycle emerges from regulation alone; coprime deadlines eliminate it |

⬅️ **Previously:** [The Failure Waterfall](../03_the_failure_waterfall/01_where_ftds_go_to_die.md) (Parts 1–4)

---

## Credits

This research was built on hypotheses from the community: **Richard Newton** originated the T+33 echo concept, **beckettcat** brought it to my attention and independently identified the Threshold List as a regulatory constraint, and **TheUltimator5** contributed settlement cycle mechanics. Their work gave me the testable hypotheses. The boundary condition tests, agent-based model, cross-border analysis, and coprime fix are my contribution.

The full test battery, scripts, and pre-computed results are in the [public repository](https://github.com/TheGameStopsNow/research).

---

*Not financial advice. Forensic research using public data. I'm not a financial advisor, attorney, or affiliated with any entity named in this post, including the SEC or ESMA. The author holds a long position in GME.*

*"The Martian atmosphere is 96% CO₂. So, basically, if you want to breathe, you're going to have to science the shit out of it."*
*— Andy Weir, paraphrased*
