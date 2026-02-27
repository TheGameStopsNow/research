# The Failure Accommodation Waterfall: The Complete Picture

**TA;DR:** Your shares aren't late — they're surfing a 45-day regulatory loophole that functions as a hidden short-selling machine, and the echoes never fully die. Four posts, 22 years of data, nine tickers, one standing wave.

**TL;DR:** I spent months tracing every Failure-to-Deliver in the GME settlement system from birth to death across 22 years and nine tickers. Four posts. A lot of math. This is my best attempt to explain the whole thing in one place without making your eyes glaze over. The investigation continues in [Boundary Conditions](../04_the_boundary_conditions/01_the_overflow.md), which follows the settlement energy across national borders, adjacent tickers, and sovereign debt.

> **⚠️ Methodology Note:** This is a summary and interpretive synthesis. Where I state something as a data finding, the reproducible scripts and data are linked in the individual posts and the [public repository](https://github.com/TheGameStopsNow/research). Where I offer interpretation (clearly marked as "my take"), that is my inference from the patterns. All code is published. All data is sourced. If I'm wrong, show me where with data.

> **Position disclosure:** I hold a long position in GME. I am not a financial advisor, attorney, or affiliated with any entity named in this post.

---

## What This Series Found

Okay. So imagine you sell someone a house, they pay you, and you just... never give them the keys. You pocket the money and walk away. In the stock market, that's called a Failure-to-Deliver, or FTD. You sold shares. You didn't deliver them. The buyer has a receipt for something they never received.

The SEC publishes FTD data. Academics have studied FTD spikes. But here's the thing nobody had done: trace what happens to a specific FTD *after* it fails. Like, where does it go? Does it just sit in a database somewhere? Does someone eventually deliver? Does it get shuffled around? Does it die?

I spent months finding out. Here's the complete picture.

---

## Layer 1: The Waterfall ([Part 1](https://www.reddit.com/r/Superstonk/comments/1re1ps2/1_the_failure_accommodation_waterfall_where_your/))

Every undelivered share enters what I'm calling the Failure Accommodation Waterfall: a 15-node regulatory cascade that takes 45 business days to traverse. Think of it like a pinball machine. The ball (the FTD) drops in at the top, and at each bumper (regulatory checkpoint), it either gets resolved or bounces to the next one.

Three things jumped out of the data:

**First: the T+33 Echo.** Phantom options open interest — OI that appears for exactly one day and vanishes — is 18.1 times more likely to show up exactly 33 business days after an FTD spike than on any random day. Not "somewhat more likely." Eighteen times. It hit 84% of mega-spikes in-sample, and went 4-for-4 on out-of-sample 2025 predictions I hadn't seen yet when I built the model.

**Second: zero on control days.** The deep out-of-the-money puts used for settlement accommodation had literally zero open interest on control days. Not "low." Not "negligible." Zero. The options exist on settlement dates and don't exist on non-settlement dates. I don't know of an economic explanation for that besides settlement mechanics.

**Third: inverse to volatility.** On FOMC days, when volatility is high, the enrichment drops to 0.5x. On settlement dates, when volatility is low, it's 18.1x. If this were hedging, you'd expect it to follow volatility. It follows the settlement calendar instead.

The fundamental frequency is T+25 business days — the hard close-out deadline under SEC Rule 204(a)(2). The observed T+33 echo is a composite: T+25 plus about 10 business days of options clearing transit time. Someone who can't close at T+25 executes a synthetic options roll, buys about 10 days of transit, and the obligation pops back up at T+33-35. It's like watching a submarine: it dives at T+25 and surfaces at T+33.

After the July 2022 splividend, 89% of this activity migrated from the options tape to dark pool equity channels. On phantom settlement dates, the FINRA TRF median trade size dropped to **6 shares** while lit-exchange medians sat at 35. The pipeline didn't shrink. It just went dark.

### My take

Here's where I want to be careful. The waterfall is not a failure of regulation. It *is* the regulation. The SEC designed a graduated enforcement system with increasing penalties at each checkpoint, and the data shows it eventually works: everything resolves by T+45. The system operates as designed.

The problem is that "as designed" includes a 45-day window where you can hold undelivered shares if you can afford the carrying costs. That's 45 business days of free float for anyone willing to pay the freight. And everyone who can't see the shadow inventory? They're on the wrong side of an information asymmetry they don't even know exists.

---

## Layer 2: The Standing Wave ([Part 2](https://www.reddit.com/r/Superstonk/comments/1re1pwi/2_the_failure_accommodation_waterfall_part_2_the/))

FTDs don't arrive one at a time. This is where things get interesting.

When successive waterfalls overlap, the echoes stack. I measured the decay rate: the system retains approximately **86% of its signal amplitude per T+35 cycle**. In engineering terms, that's a Q-factor of about 21.

For context: a well-designed clearinghouse should have a Q-factor of 0.5 or less. That means it absorbs a shock in less than one cycle. Done. Over. The GME settlement system has a Q of 21. A single FTD spike echoes for over a year. That's not a clearinghouse. That's a bell.

But here's where my jaw hit the desk.

At **T+105**, the third echo, the signal doesn't just persist. It *amplifies above the original*. The math is actually clean. T+105 is the Least Common Multiple of 35 (the settlement cycle) and 21 (the approximate OPEX cycle). At that offset, two independent clocks align for the first time and constructively interfere. It's not magic. It's the same reason you can push a kid on a swing set with one hand and get them going higher than their initial amplitude. You just have to push at the right frequency.

Look at the January 2021 timeline:

```text
Sep 3, 2020:   783,719 FTD  →  Seed
Oct 22, 2020:  168,358 FTD  →  T+35: damped (0.21x seed)
Dec 10, 2020:  605,975 FTD  →  T+70: re-amplifying (0.77x seed)
Jan 28, 2021: 1,032,986 FTD →  T+105: EXCEEDS seed (1.32x)
```

Four months. Four echoes. Each one building on the last. By the time retail buying hit in late January, the system was already loaded like a spring.

### My take

I think this reframes the entire January 2021 narrative. Retail buying was the catalyst, not the cause. The standing wave had been building for months before anyone on Reddit noticed GME. DFV's thesis was correct on fundamentals, and retail's concentrated buying happened to overlap with a resonance amplification that started in September 2020.

The system didn't buckle because of a Reddit post. It buckled because the standing wave's stored energy exceeded the clearinghouse's absorption capacity, and retail buying was the straw that broke the camel's back. Worst possible timing. Or best, depending on your perspective.

---

## Layer 3: The Cavity ([Part 3](https://www.reddit.com/r/Superstonk/comments/1re1q0f/3_the_failure_accommodation_waterfall_part_3_the/))

I zoomed out further. Like, way out. Full spectral analysis of 22 years of FTD data.

A dominant peak showed up at approximately **630 business days — about 2.5 years** — towering at 13.3x median noise. That's not subtle. That's a freight train.

This macrocycle appears in the basket members: GME, AMC, KOSS, BBBY. It does not appear in AAPL, MSFT, or SPY. At all. And I need you to sit with that for a second, because it's important. Whatever is causing this 2.5-year cycle in GME settlement data is also causing it in a headphone company with no options chain and zero institutional coverage, and it is completely absent in the three largest, most liquid securities in the market. No amount of LEAPS rollover or retail enthusiasm explains that pattern.

KOSS is the smoking gun. It has no listed options chain. Zero. Without options, KOSS physically cannot generate the T+33 settlement loop that drives GME's echo cascade. And yet it shares the exact same spectral fingerprint. The simplest explanation: KOSS sits inside a Total Return Swap basket anchored by GME. When the prime broker rolls the swap, all basket constituents experience the same settlement cadence. One heartbeat, many bodies.

And then there's BBBY.

The stock was delisted and the CUSIP was cancelled in September 2023. There is nothing to trade. Nothing to deliver. Nothing to borrow. The company doesn't exist anymore.

SEC data shows 31 unique, actively fluctuating FTD values reported continuously through late 2025. That's 824 days after cancellation. Zero of the day-to-day changes are administrative noise. 43% are block-sized changes exceeding 10,000 shares, alternating between injection and extraction. These are not database artifacts. Someone is actively managing delivery obligations on a security that no longer exists.

### My take

This is the hardest thing to explain to people who haven't followed the series, so let me just say it plainly.

There is a shadow ledger of delivery obligations sitting in DTCC's Obligation Warehouse, and it extends beyond the borders of reality itself. BBBY shares don't exist. The obligation to deliver them does. And it is being actively cycled between counterparties, because there is no mechanism to resolve a delivery failure on a cancelled security, and nobody has the authority or incentive to forgive it.

The stock died. The debt didn't.

---

## Layer 4: The SEC's Blind Spot ([Part 4](https://www.reddit.com/r/Superstonk/comments/1re1qft/4_the_failure_accommodation_waterfall_part_4_what/))

The SEC's October 2021 Staff Report on GameStop is the most complete official analysis of January 2021. I took seven specific claims from the report and tested each one against five years of post-hoc data that didn't exist when they wrote it.

Five are incomplete. Two are directly contradicted.

The SEC found "no gamma squeeze." They were right, but for the wrong reason. They found institutional conversion activity and correctly declared it wasn't retail-driven gamma. What they missed is that conversions *are* how settlement accommodation works: buy the call, sell the put, manufacture a synthetic long, reset the Rule 204 clock. The gamma squeeze isn't hiding. The settlement pipeline is.

The SEC found that "FTDs cleared quickly at the individual clearing member level." Also technically correct. No single member held a fail for long. But the waterfall data shows the *system* had persistent fails. They just moved faster than any single snapshot could capture. Think of it this way: you've got a game of hot potato. Everyone holds it for two seconds. If you check any single player at any given moment, they're not holding the potato. But the potato never stops moving.

The SEC recommended shortening the settlement cycle from T+2 to T+1. The industry implemented this on May 28, 2024. My data shows the deep cascade (T+13 through T+45) is anchored to Trade Date, not Settlement Date. It's completely immune to the compression. The 2025 out-of-sample data confirms it: T+33 echo hit rate is 100% (4/4) after T+1. The recommendation had zero effect on the mechanism it targeted.

### My take

I don't think the SEC got it wrong because of malice or capture. I think they got it wrong because the data to test their conclusions didn't exist yet. They analyzed an unprecedented event with 22 days of audit trail data. I analyzed it with five years. They measured the iceberg above the waterline. This series maps what's below.

---

## What Comes Next

So. The waterfall maps how a single stock's settlement machinery works. Pretty alarming on its own. But settlement energy doesn't respect ticker boundaries any more than water respects property lines.

In the [Boundary Conditions](../04_the_boundary_conditions/01_the_overflow.md) series, I follow the pressure when it starts leaking out of the plumbing:

- **[The Overflow](../04_the_boundary_conditions/01_the_overflow.md):** The settlement energy migrates to adjacent tickers (KOSS amplifies +1,051%), contaminates sovereign debt (GME uniquely Granger-causes Treasury fails), and exploits ETF creation baskets. A $10 billion stock is degrading the $700 billion/day Treasury market. That's... not great.
- **[The Export](../04_the_boundary_conditions/02_the_export.md):** It costs $1,750 to fail in Europe for 35 days. It costs $10 million per day to fail in the U.S. That's a 5,714:1 cost asymmetry. Guess which direction the obligations flow. Also, BBBY's cancelled CUSIP is still generating active FTDs 824 days after the company ceased to exist. The system has no garbage collection.
- **[The Tuning Fork](../04_the_boundary_conditions/03_the_tuning_fork.md):** I built a simulation with nothing but the SEC's own rules. The 630-day macrocycle emerged on its own. It's not a conspiracy. It's arithmetic. And the fix is four numbers.

---

## What Would Change My Mind

Science doesn't work if you don't say what would prove you wrong. So here's my list:

1. **If a control ticker (AAPL, MSFT) develops the same 15-node waterfall pattern.** That would mean the effect is generic market microstructure, not GME-specific. I'd have to start over.
2. **If Q drops below 5 in a future measurement using only post-2024 data.** The standing wave is naturally decaying, and I was measuring a transient, not a steady state.
3. **If BBBY FTDs drop to zero for 90+ consecutive days.** The obligations are being genuinely unwound. The zombie is actually dead.

As of this writing, none of these have occurred. I'll be the first to tell you if they do.

---

## The Series at a Glance

| Part | Title | One-Sentence Summary |
|:----:|:------|:---------------------|
| [1](https://www.reddit.com/r/Superstonk/comments/1re1ps2/1_the_failure_accommodation_waterfall_where_your/) | **Where FTDs Go To Die** | Every FTD surfs a 15-node, 45-day regulatory cascade producing phantom OI exhaust at each checkpoint |
| [2](https://www.reddit.com/r/Superstonk/comments/1re1pwi/2_the_failure_accommodation_waterfall_part_2_the/) | **The Resonance** | Overlapping waterfalls create a Q=21 standing wave with a ~2.5-year macrocycle |
| [3](https://www.reddit.com/r/Superstonk/comments/1re1q0f/3_the_failure_accommodation_waterfall_part_3_the/) | **The Cavity** | Spectral analysis confirms the macrocycle, identifies the swap basket, and finds a shadow ledger on a cancelled stock |
| [4](https://www.reddit.com/r/Superstonk/comments/1re1qft/4_the_failure_accommodation_waterfall_part_4_what/) | **What the SEC Report Got Wrong** | Five of seven SEC staff report claims are incomplete or contradicted by post-hoc data |

➡️ **Continued in:** [Boundary Conditions](../04_the_boundary_conditions/01_the_overflow.md) (Parts 1–3)

---

## Credits

This research was built on hypotheses from the community: **Richard Newton** originated the T+33 echo concept, **beckettcat** brought it to my attention and independently identified the Threshold List as a regulatory constraint, and **TheUltimator5** contributed settlement cycle mechanics. Their work gave me the testable hypotheses. The 19-test battery, cross-asset validation, resonance analysis, and spectral cavity mapping are my contribution.

The full test battery, scripts, and pre-computed results are in the [public repository](https://github.com/TheGameStopsNow/research).

---

*Not financial advice. Forensic research using public data. I'm not a financial advisor, attorney, or affiliated with any entity named in this post, including the SEC or ESMA. The author holds a long position in GME.*

*"The Martian atmosphere is 96% CO2. So, basically, if you want to breathe, you're going to have to science the shit out of it."*
*— Andy Weir, paraphrased*
