# The Failure Accommodation Waterfall, Part 4: What I Think the SEC Report Got Wrong

<!-- NAV_HEADER:START -->
## Part 4 of 4
Skip to [Part 1](https://www.reddit.com/r/Superstonk/comments/1re1ps2/1_the_failure_accommodation_waterfall_where_your/), [Part 2](https://www.reddit.com/r/Superstonk/comments/1re1pwi/2_the_failure_accommodation_waterfall_part_2_the/), or [Part 3](https://www.reddit.com/r/Superstonk/comments/1re1q0f/3_the_failure_accommodation_waterfall_part_3_the/)
Builds on: [Options & Consequences](https://www.reddit.com/r/Superstonk/comments/1raqqef/options_consequences_following_the_money_1) ([Part 1](https://www.reddit.com/r/Superstonk/comments/1raqqef/options_consequences_following_the_money_1), [Part 2](https://www.reddit.com/r/Superstonk/comments/1raqvja/options_consequences_the_paper_trail_2), [Part 3](https://www.reddit.com/r/Superstonk/comments/1rb695i/options_consequences_the_systemic_exhaust_3), [Part 4](https://www.reddit.com/r/Superstonk/comments/1rb6rje/options_consequences_the_macro_machine_4))
Continued in: [Boundary Conditions](https://www.reddit.com/r/Superstonk/comments/1rgrvuw/boundary_conditions_part_1_the_overflow/) (Parts 1-3)
<!-- NAV_HEADER:END -->
## Part 4 of 4 ([Part 1](01_where_ftds_go_to_die.md) · [Part 2](02_the_resonance.md) · [Part 3](03_the_cavity.md))
Continued in: [Boundary Conditions](../04_the_boundary_conditions/01_the_overflow.md) (Parts 1-3)

**TA;DR:** The SEC's 2021 GameStop report made 7 key claims. I tested all of them with 5 years of new data. Five are incomplete, two are flat wrong. The SEC wasn't corrupt, they just didn't have the tools yet.

**TL;DR:** The SEC's October 2021 Staff Report on GameStop is the most complete official analysis of January 2021. It was also written without the tools or data that now exist to test its conclusions. Using five years of post-hoc settlement data, 19 independent statistical tests, and microsecond-level trade forensics, I identify seven specific claims in the SEC report and test each one against the empirical evidence. Five are incomplete. Two are directly contradicted. Nothing here accuses the SEC of wrongdoing; the staff worked with what they had. But the conclusions drawn in 2021 cannot survive the evidence that has accumulated since.

> **📄 SEC Report:** [Staff Report on Equity and Options Market Structure Conditions in Early 2021](https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf) (October 18, 2021, 45 pages)
>
> **📄 Full academic paper:** [The Failure Accommodation Waterfall (Paper V of IX)](https://github.com/TheGameStopsNow/research/blob/main/papers/05_failure_accommodation_waterfall.md)

---

## A Note on Tone

The SEC staff report is not the enemy. It represents the honest work of career professionals analyzing an unprecedented event in near-real-time. Many of its observations (the identification of 80% internalization, the 🧺 creation/redemption dynamics, the NSCC margin mechanics) are genuinely useful and form the foundation of the forensic work in this series.

What follows is not an accusation. It is a scientific test. The SEC published specific claims. Five years of additional data now exist. The claims either survive the data or they don't.

---

## Key Terms for This Post

Some of these were defined in Part 1, but here's a refresher for the terms specific to this post:

| Term | What It Means |
|------|---------------|
| **Gamma Squeeze** | When market makers buy stock to hedge options they've written, which pushes the price up further, forcing them to buy even more. A self-reinforcing feedback loop. |
| **Delta Hedge** | When a market maker buys or sells shares proportional to their options exposure to stay "neutral." If they write 100 call options, they buy shares to offset the risk. |
| **Put-Call Parity** | A mathematical relationship between put prices, call prices, and stock prices. If it breaks, someone is doing something unusual. |
| **Conversion** | A specific options trade: buy call + sell put + sell stock simultaneously. It creates a synthetic position that can be used to manufacture settlement locates. |
| **CAT** | Consolidated Audit Trail. FINRA's database that tracks every order and trade in U.S. markets. The SEC used it for this report. |
| **FDID** | Firm Designated ID. A unique identifier for a trading account in the CAT system. Think of it as a trader's fingerprint. |
| **ECP Charge** | Excess Capital Premium. An NSCC charge imposed when a clearing member's risk-to-capital ratio gets dangerously high. |
| **OCC** | Options Clearing Corporation. The central counterparty that guarantees every options trade settles. |
| **NSCC** | National Securities Clearing Corporation. The central counterparty that guarantees every stock trade settles. |

---

## Claim 1: "Staff did not find evidence of a gamma squeeze"

**What the SEC said (p. 30, §3.4):**
> "Staff did not find evidence of a gamma squeeze in GME during January 2021... this increase in options trading volume was mostly driven by an increase in the buying of put, rather than call, options. Further, data show that market-makers were buying, rather than writing, call options."

**What the evidence shows:**

The SEC looked for a *textbook* gamma squeeze: retail buys calls, market makers write calls, market makers delta-hedge by buying stock, stock goes up. They didn't find it because that's not what happened.

What actually occurred was a **conversion-driven settlement architecture** (see Key Terms above):

| Metric | Value | Source |
|--------|------:|--------|
| OCC Origin Code breakdown (June 2024) | 49.4% of Firm (F) volume = single conversion | [OCC Volume Query](https://www.theocc.com/Market-Data/Market-Data-Reports/Volume-and-Open-Interest/Volume-Query) (parameters: GME, June 2024, all exchanges, grouped by Origin Code) |
| Synthetic price from put-call parity | $35.00 (predicted 3 days early, 2.9% error) | ThetaData tick data; Script: [`14_deep_otm_puts.py`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/14_deep_otm_puts.py); Results: [`deep_otm_puts.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/deep_otm_puts.json) |
| Lit vs. dark price gap (May 17, 2024) | $12.13 for 4.5 minutes | Polygon.io v3 Trades API, GME, May 17 2024, `exchange=4` vs lit exchanges; Results: [`settlement_architecture.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/settlement_architecture.json) |
| Compliance flag evasion | 99.6% of dark prints missing OPT flag | FINRA TRF data via Polygon.io (`exchange=4`); [FINRA Rule 6380A](https://www.finra.org/rules-guidance/rulebooks/finra-rules/6380a) requires the OPT modifier for options-related equity trades |

**What's an OCC Origin Code?** When an options trade happens, the OCC records *who* initiated it: "C" for customer, "F" for firm (the broker-dealer trading for its own book), "M" for market maker. Origin Code "F" with a conversion pattern means the *firm itself* is doing the trade, not a customer.

The SEC found that "market-makers were buying, rather than writing, call options" (p. 30). That's *consistent* with a conversion: the market maker buys the call and sells the put simultaneously to manufacture a synthetic long. A conversion is delta-neutral by definition, which means it does NOT produce the self-reinforcing stock-buying feedback loop that characterizes a textbook gamma squeeze. In this narrow sense, the SEC's conclusion was correct: there was no gamma squeeze.

However, the SEC interpreted the absence of a gamma squeeze as evidence that nothing unusual was happening in the options market. The conversion concentration is *consistent with* settlement accommodation, though conversions are also used for legitimate arbitrage and market-making purposes. What distinguishes this activity from standard conversion usage is its temporal correlation with FTD settlement dates and its concentration in anomalous instrument classes (deep OTM puts with zero control-day trades).

**In plain English:** The SEC looked for customers (retail) driving a gamma squeeze. They found institutions (firms) running conversions. They correctly declared "no gamma squeeze" because the retail-driven version didn't show up. But they missed what the institutional conversion activity actually was: a settlement mechanism, not a hedge.

---

## Claim 2: "Short covering was a small fraction of overall buy volume"

**What the SEC said (p. 27, Figure 6, §3.3):**
> "Figure 6 shows that the run-up in GME stock price coincided with buying by those with short positions. However, it also shows that such buying was a small fraction of overall buy volume... it was the positive sentiment, not the buying-to-cover, that sustained the weeks-long price appreciation."

**What the evidence shows:**

The SEC's analysis used CAT data beginning December 24, 2020; only 22 trading days of inventory history. Their own footnote 78 (p. 29) acknowledges: *"Since the CAT sample only begins on December 24, 2020, we are not able to include FDIDs' inventory positions accumulated prior to this date."*

**Why this matters:** GME short interest exceeded 100% of float for months before December 2020 (see SEC Report Figure 5, p. 28). Any firm that established its short position before late December would be *invisible* to the SEC's "large short position" filter. The CAT data started on Dec 24, so any short position opened on Dec 23 or earlier simply wouldn't show up, even if it was massive.

More importantly, the Failure Accommodation Waterfall (Part 1 of this series) demonstrates that delivery obligations don't resolve in days. They surf a 15-node regulatory cascade over 45 business days:

| Waterfall Node | Offset | Enrichment | What It Means |
|:---------------|:------:|:----------:|:-------------|
| CNS netting | T+3 | 5.4× | Synthetic locate manufactured *before* deadline ([NSCC Rule 11, §III](https://www.dtcc.com/~/media/Files/Downloads/legal/rules/nscc_rules.pdf)) |
| Post-BFMM spillover | T+6 | 7.4× | Failures surviving the T+5 BFMM close-out deadline ([17 CFR § 242.204(a)(3)](https://www.ecfr.gov/current/title-17/chapter-II/part-242/subject-group-ECFR34d2b065684a41c/section-242.204)) |
| Volume mode | **T+33** | **18.1×** | Maximum absolute reset volume (Script: [`04_t33_echo_cascade.py`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/04_t33_echo_cascade.py)) |
| Convergent margin pressure | **T+40** | **40.3×** | Terminal peak: NSCC VaR charges + 15c3-1 capital haircuts make maintaining positions economically destructive ([NSCC Rule 4, §A](https://www.dtcc.com/~/media/Files/Downloads/legal/rules/nscc_rules.pdf); [15c3-1(c)(2)(ix)](https://www.ecfr.gov/current/title-17/chapter-II/part-240/subject-group-ECFR856033ddd8a8a42/section-240.15c3-1)) |
| Terminal boundary | T+45 | 0.0× | All obligations resolve under convergent regulatory pressure (Multiple: [15c3-1](https://www.ecfr.gov/current/title-17/chapter-II/part-240/subject-group-ECFR856033ddd8a8a42/section-240.15c3-1), [NSCC Rule 11](https://www.dtcc.com/~/media/Files/Downloads/legal/rules/nscc_rules.pdf)) |

*Full waterfall: [`settlement_architecture.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/settlement_architecture.json)*

**New evidence from Part 2:** The resonance analysis confirms that accommodation doesn't just persist for 45 days — it echoes for **over a year**. The system's Q-factor of ≈21 means approximately 86% of settlement echo amplitude is retained per T+35 cycle. Furthermore, at T+140 (28 weeks after the original fail), a statistically significant **−6.1% negative return** (p < 0.001) is *consistent with* the **"Novation Crush"**: the physical unwind of 6-month OTC swaps used to warehouse the original obligation. Under this interpretation, delivery obligations don't simply resolve at T+45 — they may transform into swap instruments, which then drive a price crush at T+140.

The SEC concluded that shorts covered because *visible* short interest declined. The waterfall demonstrates that most settlement obligations are accommodated through phantom OI, dark pool internalization, and ETF operational shorting: channels that don't appear in standard short interest reports.

**The SEC measured the iceberg above the waterline. The waterfall maps what's below.**

---

## Claim 3: "GME did not experience persistent fails to deliver at the individual clearing member level"

**What the SEC said (p. 30, fn. 81, §3.4):**
> "Based on the staff's review of the available data, GME did not experience persistent fails to deliver at the individual clearing member level. Specifically, staff observed that most clearing members were able to clear any fails relatively quickly, i.e., within a few days."

The SEC footnotes this as: *"Staff conducted this analysis using data provided by the NSCC."* (fn. 81, p. 30)

**What the evidence shows:**

This is the claim that the Failure Accommodation Waterfall most directly contradicts.

The SEC observed that individual clearing members resolved their specific fails "within a few days." This is technically true, and profoundly misleading. Here's the analogy: imagine a game of hot potato where everyone holds the potato for only 2 seconds, then passes it. No *individual* player held it for long. But the potato never stopped moving.

Individual clearing members *do* resolve their specific obligations, by manufacturing phantom OI (one-day-and-gone options positions) that transfers the settlement burden to the next participant in the cascade.

The waterfall data, covering 2,038 trading days and 6,163 FTD records ([`GME_ftd.csv`](https://github.com/TheGameStopsNow/research/blob/main/data/ftd/GME_ftd.csv): 1,127 records), demonstrates:

- **84% of FTD mega-spikes** produce measurable phantom OI echoes at exactly T+33 (Results: [`t33_echo_cascade.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/t33_echo_cascade.json))
- **Zero control-day trades** in the instruments used for phantom OI absorption: deep OTM puts, $20 strike (Results: [`deep_otm_puts.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/deep_otm_puts.json))
- **Enrichment accelerates continuously** from T+3 (5.4×) through T+40 (40.3×); the *opposite* of what "clearing quickly" would produce (Results: [`settlement_architecture.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/settlement_architecture.json))

If fails genuinely cleared "within a few days," the enrichment curve would decay, not accelerate. The continuous acceleration through T+40 is the mathematical signature of obligation rotation: Member A clears their fail by passing it to Member B through a synthetic locate, who clears their fail by passing it to Member C, producing an exponentially rising accommodation cost.

The SEC correctly observed that *no individual member* had persistent fails. The waterfall data suggests that the *system* had persistent fails; they just moved faster than any single snapshot could capture.

---

## Claim 4: "NSCC exercised rules-based discretion to waive the ECP charge"

**What the SEC said (p. 32, §3.5):**
> "Because these members' ratios of excess risk versus capital were not driven by individual clearing member actions, but by extreme volatility in individual cleared equities, NSCC exercised its rules-based discretion to waive the ECP charge for all members on January 28, 2021. Absent this waiver, one retail broker-dealer would have had an additional ECP charge of more than double its margin requirement of $1.4 billion."

**What's the ECP charge?** When a clearing member's risk (the potential loss on their unsettled trades) gets too large relative to their capital (the money they have on hand), the NSCC imposes an Excess Capital Premium charge. Think of it as a penalty for being too leveraged. If you can't pay it, you can default, and the clearinghouse has to clean up your mess.

**What the evidence shows:**

The SEC report accurately describes the mechanism but omits a critical structural fact: **the NSCC Risk Management Committee is composed of representatives from its clearing members** (see [NSCC Rules & Procedures](https://www.dtcc.com/~/media/Files/Downloads/legal/rules/nscc_rules.pdf), Article VII, §2 "Board of Directors and Committees"). In other words, the people who *vote* on waiving the charge are the same firms that held the short positions creating the volatility.

The SEC notes that "one retail broker-dealer" (widely understood to be Robinhood; see [Robinhood SEC Filing, Jan 28 2021 events](https://www.sec.gov/Archives/edgar/data/1783879/000162828021003168/robinhoods-1.htm)) would have faced a charge of more than double its $1.4 billion margin requirement. The total intraday margin call across 36 members was $6.9 billion, of which $4.8 billion was the special ECP charge (SEC Report, p. 32). The SEC also cites DTCC CEO Michael Bodson's [February 18, 2021 letter to Congress](https://www.dtcc.com/-/media/Files/PDFs/DTCC-Statement-February-2021-Mike-Bodson.pdf) (fn. 86, p. 32).

**What would have happened without the waiver?** If Robinhood defaulted on a ~$3 billion charge, the NSCC would have been obligated to buy GME shares at market price (~$483) to complete the settlement. The clearing members who *sat on the committee that waived the charge* were the same entities whose short positions would have been forced into a buy-in at that price. This is documented in [Options & Consequences Part 4: The Macro Machine](https://github.com/TheGameStopsNow/research/blob/main/posts/02_options_and_consequences/04_the_macro_machine.md).

The SEC calls this "rules-based discretion." The evidence shows it was a committee of interested parties voting to waive a charge whose enforcement would have forced heavily short clearing members to cover at the worst possible price.

This isn't an accusation of illegality. NSCC *does* have the authority to waive ECP charges under its rules. But a "rules-based" action can still be a conflict of interest, and the SEC report treats this as a mechanical process rather than a governance question.

---

## Claim 5: "Fails to deliver can occur either with short or long sales, making them an imperfect measure of naked short selling"

**What the SEC said (p. 30, fn. 79-80, §3.4):**
> "When a naked short sale occurs, the seller fails to deliver the securities to the buyer, and staff did observe spikes in fails to deliver in GME. However, fails to deliver can occur either with short or long sales, making them an imperfect measure of naked short selling."

**What's a "naked short"?** Normally, before you short a stock, you have to "locate" shares to borrow (Reg SHO Rule 203, [17 CFR § 242.203](https://www.ecfr.gov/current/title-17/chapter-II/part-242/subject-group-ECFR34d2b065684a41c/section-242.203)). A "naked" short skips this step: you sell shares you haven't borrowed and may never deliver. The SEC's point is that FTDs can also happen from long sales (e.g., a broker sells shares they *thought* were in a customer's account but weren't), so FTDs alone don't prove naked shorting.

**What the evidence shows:**

This framing is technically correct but functionally dismissive. Yes, FTDs can sometimes come from long-side mistakes. But the *pattern* of FTDs in GME makes this explanation difficult to sustain.

Three patterns suggest the FTDs are settlement-mechanism-driven, not random operational noise:

1. **The T+33 echo (84% hit rate).** Random long-sale FTDs would not produce a statistically significant echo at a specific settlement offset. The T+33 periodicity tracks individual FTD spikes, not calendar events. (Script: [`04_t33_echo_cascade.py`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/04_t33_echo_cascade.py); Results: [`t33_echo_cascade.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/t33_echo_cascade.json))

2. **The phantom OI instrument class.** The instruments absorbing the settlement burden ($20 strike deep OTM puts) had zero open interest on control days. If FTDs were from routine long-sale errors, the resolution would use normal hedging instruments, not zero-delta phantom positions that appear for one day and vanish. (Script: [`14_deep_otm_puts.py`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/14_deep_otm_puts.py); Results: [`deep_otm_puts.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/deep_otm_puts.json))

3. **The inverse volatility relationship.** Phantom OI enrichment is 18.1× on settlement dates but 0.5× on FOMC days (Federal Reserve rate decisions, some of the highest-volatility events on the calendar). If these were operational errors, they'd cluster around chaotic high-volume days. Instead, they cluster around quiet settlement deadline days. (Script: [`15_settlement_validation.py`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/15_settlement_validation.py); Results: [`settlement_validation.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/settlement_validation.json))

The SEC report uses the "long or short" observation to suggest FTDs are noisy and unreliable. The waterfall data demonstrates they are *highly structured*, clustering at specific regulatory checkpoints with 84% predictability.

---

## Claim 6: "Internalization was approximately 80%, with Citadel Securities accounting for nearly 50%"

**What the SEC said (pp. 38-39, Figure 7-8, §3.8):**
> "The vast majority of GME stock trades executed off exchange in January 2021 were internalized (approximately 80%)... Citadel Securities accounted for nearly 50% of internalizer dollar volume during the month."

**What's "internalization"?** When you buy or sell a stock through your broker (e.g., Robinhood), your order often doesn't go to the NYSE or Nasdaq. Instead, your broker sells the order to a wholesale market maker like Citadel Securities (this is PFOF: Payment for Order Flow). That market maker executes your trade "internally" (off-exchange) and reports it to the TRF. The SEC is saying that 80% of GME trades went through this off-exchange channel.

The SEC notes this data was sourced from the TRF (fn. 98, p. 37: *"TRF refers to the Trade Reporting Facility for the reporting of transactions effected otherwise than on an exchange."*).

**What the evidence shows:**

The SEC correctly identified the internalization concentration. What the report couldn't know is that **this same internalization infrastructure is still operating identically five years later**, and now serves as the primary channel for FTD close-out accommodation.

Test 18 (Polygon.io TRF internalization data, December 2022; Script: [`19_polygon_forensics.py`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/19_polygon_forensics.py)) reveals the microstructure:

| Date | Event | TRF % | TRF Median | Lit Median | Fragmentation Ratio |
|:----:|:-----:|:-----:|:----------:|:----------:|:-------------------:|
| 12/19/2022 | T+35 close-out threshold | **41.2%** | **6 shares** | 35 shares | **5.8×** |
| 12/22/2022 | T+35 deadline | **41.1%** | 10 | 46 | 4.6× |
| 12/05/2022 | Control | 35.2% | 12 | 40 | 3.3× |

*Source: Polygon.io v3 Trades API, GME, Dec 2022, `exchange=4` (FINRA TRF). FTD data: SEC EDGAR, CUSIP 36467W109.*

**What's the "fragmentation ratio"?** It's the difference between the typical trade size on the TRF (dark pool) vs. lit exchanges. When the TRF trade size drops to 6 shares while lit trades are 35 shares, that 5.8× ratio means the off-exchange market is processing abnormally tiny orders on settlement deadline dates. The data is consistent with retail sell orders being internalized and applied toward delivery obligations rather than routed to lit exchanges where they would contribute to visible price formation.

The SEC identified internalization as a *market structure question* (SEC Report, §3.8, pp. 37-39). The post-hoc data suggests it may also function as a *settlement accommodation channel*. The 80% internalization rate isn't just a feature of how retail orders are handled; the data is consistent with it functioning as a mechanism by which aged FTDs are satisfied using aggregate retail sell flow.

---

## Claim 7: "One method to mitigate the systemic risk... is to shorten the settlement cycle"

**What the SEC said (p. 45, §4, Conclusion #1):**
> "One method to mitigate the systemic risk posed by such entities to the clearinghouse and other participants is to shorten the settlement cycle."

**What did the SEC mean?** In 2021, when you bought a stock, it took 2 business days (T+2) to officially settle (transfer shares and money between accounts). The SEC suggested moving to T+1 (one day) to reduce the window of risk.

**What Part 2 revealed:** The settlement system has a Quality Factor of **Q≈21** — it retains approximately 86% of its echo amplitude per cycle. Shortening T+2 to T+1 compressed only the *front end* of the waterfall (the first 5 days). The deep cascade (T+13 through T+45) is pegged to **Trade Date**, not Settlement Date, and is completely immune to T+1 compression. The resonance data in [Part 2](02_the_resonance.md) shows T+1 did not reduce stored energy — echo amplitude remains elevated today relative to 2024.

**What happened:**

The SEC recommended shortening the settlement cycle. The industry moved to T+1 on May 28, 2024 ([SEC Release No. 34-96930](https://www.sec.gov/files/rules/final/2024/34-99763.pdf); [17 CFR § 240.15c6-1](https://www.ecfr.gov/current/title-17/chapter-II/part-240/subject-group-ECFRc8863a0094f1b59/section-240.15c6-1)). Did it work?

**No.** Here's why: the Failure Accommodation Waterfall operates on **business-day offsets** measured from the original Trade Date (T+N BD). T+1 compressed the front-end close-out windows (the 204(a)(3) BFMM deadline shifted from T+5 to T+4), but the deep-cascade nodes (T+13 through T+45) are pegged to the originating Trade Date, not the Settlement Date. The 2025 out-of-sample data (4/4 at T+33 BD) proves the deeper accommodation architecture is immune to T+1 compression:

| Node | Pre-T+1 | Post-T+1 | Change |
|------|:-------:|:--------:|:------:|
| Initial settlement | T+2 | T+1 | Compressed |
| BFMM close-out ([§ 242.204(a)(3)](https://www.ecfr.gov/current/title-17/chapter-II/part-242/subject-group-ECFR34d2b065684a41c/section-242.204)) | T+5 | T+4 | Compressed |
| T+13 threshold through T+45 death | **Unchanged** | **Unchanged** | None |

The accommodation architecture from T+13 onward (including the T+33 echo at 18.1×, the T+35 red zone at 23.4×, and the T+40 convergent margin pressure at 40.3×) is anchored to Trade Date, not Settlement Date; T+1 did not affect it.

The 2025 out-of-sample data confirms this: **T+33 echo hit rate is 100% (4/4) in 2025**, *after* T+1 implementation. The waterfall's architecture is unchanged. The SEC's primary structural recommendation had zero effect on the settlement evasion mechanism it was intended to address.

*Results: [`dual_valve_validation.json`](https://github.com/TheGameStopsNow/research/blob/main/results/ftd_research/dual_valve_validation.json)*

---

## What the SEC Couldn't Have Known

Three categories of evidence were unavailable to the SEC staff in October 2021:

**1. Five years of post-hoc settlement data.** The waterfall requires multi-year statistical analysis to distinguish signal from noise. With data only through early 2021, the T+33 echo (which requires at least 6 mega-spikes to establish the 84% hit rate) was invisible. Full dataset: [`GME_ftd.csv`](https://github.com/TheGameStopsNow/research/blob/main/data/ftd/GME_ftd.csv) (1,127 records, Dec 2020 through Jan 2026).

**2. The ThetaData OI dataset.** The 424 daily OI snapshots ([`gme_options_oi_daily.csv`](https://github.com/TheGameStopsNow/research/blob/main/data/ftd/gme_options_oi_daily.csv)) that reveal phantom OI concentration in deep OTM puts at specific settlement offsets did not exist as a compiled dataset in 2021. The instrument-class specificity (zero control-day trades) requires this granularity.

**3. The post-splividend valve transfer.** The July 2022 [4:1 stock split via dividend](https://investor.gamestop.com/news-releases/news-release-details/gamestop-announces-four-one-stock-split) created a natural experiment that revealed the 89% migration of settlement accommodation from options to dark pool equity channels (Script: [`16_dual_valve_validation.py`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/16_dual_valve_validation.py)). This behavior change, which confirms the mechanism by demonstrating its adaptation, occurred a year after the report.

The SEC did not get these conclusions wrong because of bias or complicity. They got them wrong because the data to test them didn't exist yet. It does now.

---

## Summary: Seven Claims, Five Years Later

| # | SEC Claim (2021) | Page | Post-Hoc Verdict | Key Evidence |
|:-:|:-----------------|:----:|:----------------:|:-------------|
| 1 | No gamma squeeze evidence | 30 | **Correct conclusion, missed mechanism** | SEC correctly found no gamma squeeze. But the conversion activity they observed was settlement accommodation, not neutral hedging. |
| 2 | Short covering was small fraction of volume | 27 | **Incomplete** | Only 22 days of CAT history (fn. 78). Waterfall shows obligations rotate, not resolve. |
| 3 | FTDs cleared quickly at clearing member level | 30 | **Incomplete** | The SEC's CNS-level accounting is technically correct: at the line-item level, fails are resolved or transferred. But the enrichment data shows the obligation *accelerates* from T+3 to T+40 (5.4× to 40.3×) — consistent with obligation rotation (hot-potato passing), not genuine resolution. The SEC measured CNS line-items; we measured systemic economic exposure. |
| 4 | NSCC used rules-based discretion for ECP waiver | 32 | **Incomplete** | Committee included interested clearing members whose shorts would have been force-covered. |
| 5 | FTDs are imperfect measure of naked shorting | 30 | **Incomplete** | The SEC is correct that raw FTD counts are noisy. But structured analysis (84% echo hit rate, zero control trades, inverse volatility) reveals FTDs are highly organized, not random noise. The SEC's characterization was technically accurate at the aggregate level but missed the fine-grained temporal structure. |
| 6 | 80% internalization, Citadel 50% | 38 | **Confirmed but understated** | Same infrastructure still operating. Now serves as primary FTD close-out channel (6-share TRF vacuum). |
| 7 | Shortening settlement cycle would reduce risk | 45 | **Failed** | T+35 statutory deadline is calendar days. T+33 echo rate 100% in 2025 post-T+1. |

---

## Credits

- **SEC Staff** for publishing the most comprehensive official analysis available, including data that enabled much of this follow-up work
- **Richard Newton** for originating the T+33 echo concept that produced the strongest finding contradicting Claim 3
- **beckettcat** for bringing Richard Newton's T+33 work to my attention, and for independently identifying the Reg SHO Threshold Security List ([17 CFR § 242.203(b)(3)](https://www.ecfr.gov/current/title-17/chapter-II/part-242/subject-group-ECFR34d2b065684a41c/section-242.203)) as a regulatory constraint: the data is consistent with operators keeping FTDs below the Threshold List trigger because landing on it risks losing the BFMM exemption
- **TheUltimator5** for the settlement cycle mechanics that informed the waterfall architecture

All scripts, data, and pre-computed results: [github.com/TheGameStopsNow/research](https://github.com/TheGameStopsNow/research)

| Resource | Link |
|----------|------|
| SEC Report (PDF) | [`references/staff-report-...early-2021.pdf`](https://github.com/TheGameStopsNow/research/blob/main/references/staff-report-equity-options-market-struction-conditions-early-2021.pdf) |
| Scripts (19 tests) | [`code/analysis/ftd_research/`](https://github.com/TheGameStopsNow/research/tree/main/code/analysis/ftd_research) |
| Results (JSON) | [`results/ftd_research/`](https://github.com/TheGameStopsNow/research/tree/main/results/ftd_research) |
| FTD data (9 tickers) | [`data/ftd/`](https://github.com/TheGameStopsNow/research/tree/main/data/ftd) |
| Full paper (Paper V) | [`05_failure_accommodation_waterfall.md`](https://github.com/TheGameStopsNow/research/blob/main/papers/05_failure_accommodation_waterfall.md) |

---

*Not financial advice. Forensic research using public data. I'm not a financial advisor, attorney, or affiliated with any entity named in this post, including the SEC. The author holds a long position in GME.*

*"The good thing about science is that it's true whether or not you believe in it."*
*Neil deGrasse Tyson*

<!-- NAV:START -->

---

### 📍 You Are Here: The Failure Waterfall, Part 4 of 4

| | The Failure Waterfall |
|:-:|:---|
| [1](https://www.reddit.com/r/Superstonk/comments/1re1ps2/1_the_failure_accommodation_waterfall_where_your/) | Where Your FTDs Go To Die — The first empirical lifecycle map of delivery failures: 15 nodes, 45 days |
| [2](https://www.reddit.com/r/Superstonk/comments/1re1pwi/2_the_failure_accommodation_waterfall_part_2_the/) | The Resonance — The settlement system retains 86% echo amplitude per cycle (Q≈21) |
| [3](https://www.reddit.com/r/Superstonk/comments/1re1q0f/3_the_failure_accommodation_waterfall_part_3_the/) | The Cavity — A 630-day macrocycle at 13.3x noise; BBBY still fails 824 days after cancellation |
| 👉 | **Part 4: What the SEC Report Got Wrong** — Seven SEC claims tested against five years of post-hoc settlement data |

⬅️ [Part 3: The Cavity](https://www.reddit.com/r/Superstonk/comments/1re1q0f/3_the_failure_accommodation_waterfall_part_3_the/)

---

<details><summary>📚 Full Research Map (4 series, 14 posts)</summary>

| Series | Posts | What It Covers |
|:-------|:-----:|:---------------|
| [The Strike Price Symphony](https://www.reddit.com/user/TheGameStopsNow/comments/1r5hog7/strike_price_symphony_1) | 3 | Options microstructure forensics |
| [Options & Consequences](https://www.reddit.com/r/Superstonk/comments/1raqqef/options_consequences_following_the_money_1) | 4 | Institutional flow, balance sheets, macro funding |
| **→ [The Failure Waterfall](https://www.reddit.com/r/Superstonk/comments/1re1ps2/1_the_failure_accommodation_waterfall_where_your/)** | **4** | **Settlement lifecycle: the 15-node cascade** |
| [Boundary Conditions](https://www.reddit.com/r/Superstonk/comments/1rgrvuw/boundary_conditions_part_1_the_overflow/) | 3 | Cross-boundary overflow, sovereign contamination, coprime fix |

</details>

[📂 GitHub](https://github.com/TheGameStopsNow/research) · [🐦 𝕏](https://x.com/TheGameStopsNow)
<!-- NAV:END -->
