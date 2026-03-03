# The Shadow Ledger, Part 7: The Fingerprint

# Part 7 of 7

**TL;DR:** Parts 1-6 mapped the system: phantom locates, the derivative trail, the Ouroboros, the Bitcoin checkmate, the BNY Mellon bridge, and the Dreyfus cash engine powering it all. This final post identifies the machine that operationalizes the domestic compliance loop. Using 2,038 days of tick-level OPRA data, I isolated a DMA routing fingerprint, 1-lot trades, inverted-fee venue concentration, monotonic sequencing, tied-to-stock condition codes, operating across 31 U.S. equities and ETFs. On liquid mega-caps (SPY, AAPL), the algo runs with zero FTD (Failure to Deliver, when the seller doesn't deliver shares
within the settlement deadline) correlation. On borrow-constrained stocks (GME, AMC), the same hardware shows t = +3.86 FTD correlation at exactly the T-5 to T-7 [Reg SHO](https://www.ecfr.gov/current/title-17/section-242.204) close-out window. A natural experiment confirms it: on BBBY, the algo ran 3x its normal pace during bankruptcy, *inverted* its FTD relationship (deferring rather than resolving failures), and ceased on the exact date of options delisting. The delisting trigger was the options chain. The operator runs on only two exchanges, the only two with [inverted fee models](https://www.sec.gov/comments/s7-18-19/s71819.htm), where 4,307 daily trades generate rebate
revenue instead of fees. Wolverine Trading, the confirmed DPM for GME options on [Cboe](https://www.cboe.com/), was previously fined by [FINRA](https://www.finra.org/) for using buy-write transactions to improperly address Reg SHO close-out obligations, the identical mechanical profile.

> **📄 Full academic paper:** [Compliance-as-a-Service (Paper VIII)](https://github.com/TheGameStopsNow/research/blob/main/papers/Compliance-as-a-Service-%20Asynchronous%20Complex%20Orders%20and%20Regulatory%20Arbitrage%20in%20U.S.%20Equity%20Settlement.pdf?raw=1)

*[Part 1](01_the_fake_locates.md) presented evidence of phantom locates. [Part 2](02_the_6_trillion_swap.md) traced the risk transfer. [Part 3](03_the_ouroboros.md) followed the funding. [Part 4](04_the_reflexive_trap.md) mapped the endgame. [Part 5](05_the_bridge.md) connected the layers. [Part 6](06_the_cash_engine.md) followed the money. This post identifies the machine.*

---

## 1. The Host Infrastructure

Some background: every options trade in the U.S. is reported through [OPRA](https://www.opraplan.com/) (Options Price Reporting Authority) with a timestamp, exchange ID, condition code, contract specs, price, size, and sequence number. Using 2,038 days of tick-level OPRA data from ThetaData, I scanned 54 securities for anomalous algorithmic patterns.

I found one. It operates on 31 of 54 securities scanned.

### The Fingerprint Definition

![### The Fingerprint Definition](figures/table_01_07_the_fingerprint.png)

The 90%+ monotonic rate means these trades arrive in strict sequential order without interleaving from other market participants. For comparison, organic options trading exhibits monotonic rates of 40-55%. This is consistent with a dedicated execution channel operating in isolation from organic order flow.

### Cross-Asset Universality

![### Cross-Asset Universality](figures/table_02_07_the_fingerprint.png)

*Source: ThetaData OPRA historical options trades, February 2019 - February 2026.*

![Cross-Asset DMA Fingerprint Detection](figures/chart_cross_asset_detection.png)

The presence on SPY (the most liquid ETF in the world), AAPL, NVDA, and MSFT eliminates the hypothesis that this is a bespoke tool targeting meme stocks. This is standard Tier-1 market-making infrastructure. The question is not whether it exists, it does, across 31 securities. The question is what triggers it on specific tickers.

---

## 2. The Trigger Discriminator: Same Hardware, Different Software

If this infrastructure serves exclusively for legitimate market-making, daily volume should be driven by market activity (total options volume, volatility). FTD levels should have zero predictive power.

I ran OLS regressions on each security:

### Placebo Securities (Liquid, No Borrow Constraints)

![### Placebo Securities (Liquid, No Borrow Constraints)](figures/table_03_07_the_fingerprint.png)

Adding FTDs does *nothing* to the model. On liquid securities, the algo runs based on market activity. Zero FTD signal.

### Treatment Securities (Borrow-Constrained)

![### Treatment Securities (Borrow-Constrained)](figures/table_04_07_the_fingerprint.png)

On borrow-constrained securities, lagged FTDs are highly significant (p < 0.001), positive (higher FTDs predict more algo trades), and peak at **T-6 to T-7 business days**, precisely within the Reg SHO Rule 204 close-out window.

![The Trigger Discriminator: Same Hardware, Different Software](figures/chart_trigger_discriminator.png)

The identical execution hardware produces zero FTD correlation on liquid securities and highly significant FTD correlation on borrow-constrained securities. **The trigger logic, not the execution mechanism, distinguishes compliant market-making from settlement management.**

> **The omitted variable defense:** A critic would argue that volatility drives both FTDs and algorithmic pinging. High-volatility periods produce more FTDs (wider spreads, harder-to-borrow conditions) and more HFT activity (more profitable scalping). Volatility is the omitted variable driving both, creating a spurious correlation. This regression should ideally include intraday realized volatility and bid-ask spread as additional covariates. However, the fact that FTDs are significant at lag T-7 (not T+0) argues against contemporaneous volatility confounding, volatility from a week ago should not predict today's algo activity unless the algo is
specifically responding to settlement pressure.

> **The maker-taker arbitrage defense:** Pearl and BX are inverted (taker-maker) venues. HFTs run 1-lot algorithms on these venues continuously to harvest sub-penny rebates, this is standard micro-scalping cost-optimization. The response: if it were standard rebate arbitrage, it would trigger on SPY and AAPL based on market volume. It does. But on GME and AMC, lagged FTDs add significant explanatory power (t=3.86, p<0.001) that doesn't exist on liquid securities. The rebate mechanism is real; the discriminant trigger is the finding.

---

## 3. The Venue Economics: Why Only Two Exchanges

**MIAX Pearl** and **Nasdaq BX** are the only two U.S. options exchanges operating an **inverted fee model**, where the liquidity *taker* earns a rebate:

![**MIAX Pearl** and **Nasdaq BX** are the only two U.S. options exchanges operating an **inverted fee model**, where the liquidity *taker* earns a rebate:](figures/table_05_07_the_fingerprint.png)

*Source: [MIAX Pearl Options Fee Schedule](https://www.miaxglobal.com/) and [Nasdaq BX Options Fee Schedule](https://nasdaqtrader.com/), January 2026.*

On a standard exchange, 4,307 trades in one day would cost approximately **$2,150** in exchange fees. On Pearl and BX, the same activity generates approximately **$650-$860 in rebate revenue**. The inverted fee model transforms the DMA algo from a cost center into a break-even or revenue-positive operation.

---

## 4. The Instrument Shift: It's Not Just Puts Anymore

The original hypothesis was that the algo operated primarily through deep OTM puts. Seven years of data revealed something more interesting: the algo is **instrument-agnostic**.

![The original hypothesis was that the algo operated primarily through deep OTM puts. Seven years of data revealed something more interesting: the algo is **instrument-agnostic**.](figures/table_06_07_the_fingerprint.png)

*Source: ThetaData OPRA historical options trades, GME, April 2019 - February 2026.*

![The Instrument Shift: Puts to Calls to Whatever's Cheapest](figures/chart_instrument_shift.png)

The algo shifted from predominantly puts (64-83%) in the Pearl-dominant era to predominantly calls (81-92%) in the BX-dominant era. The venue and instrument shifted together, consistent with an operator continuously optimizing for the cheapest fee schedule multiplied by the cheapest available premium.

---

## 5. The Delisting Trigger: BBBY Proves It

[Bed Bath & Beyond filed for Chapter 11](https://cases.ra.kroll.com/702702/) bankruptcy on April 23, 2023. During the bankruptcy, the identified fingerprint executed an average of **600+ qualifying trades per day** on BBBY, **3x its pre-bankruptcy average**. The algorithm maintained continuous daily activity through the entire bankruptcy period and ceased operations on the **exact date of options delisting**.

Not on the bankruptcy filing date. Not on the equity delisting date. On the day the listed options chain ceased to exist.

> **The tautology defense:** A critic would point out that it's mechanically tautological that an options-trading algorithm stops trading when the options cease to exist. Fair. The algorithm's *cessation* at delisting is trivially true. What's not trivially true is the **FTD inversion** documented below, the algorithm switched from *resolving* failures (as on AMC) to *deferring* them (on BBBY), and it ran at 3× capacity during bankruptcy. These behavioral signatures are the forensic findings, not the cessation date.

### The Inversion

On AMC, algo dates are followed by significantly *larger* FTD declines than control dates (p = 0.005), consistent with the algo resolving FTDs. On BBBY during bankruptcy, the relationship **inverted**:

![On AMC, algo dates are followed by significantly *larger* FTD declines than control dates (p = 0.005), consistent with the algo resolving FTDs. On BBBY during bankruptcy, the relationship **inverted**:](figures/table_07_07_the_fingerprint.png)

On BBBY, algorithmic dates are associated with *smaller* FTD drops at all tested windows and thresholds (p < 0.001). The algo was **actively deferring** settlement failures, not resolving them. With no shares available for genuine borrow during bankruptcy, the only way to maintain Reg SHO compliance without triggering Rule 204(b) lockout was to continuously manufacture synthetic locates, each resetting the close-out timer while leaving the net FTD balance unchanged.

This exhibits the structural signature of what I call *Settlement Deferral*, the rolling of FTD obligations through successive synthetic locate transactions that satisfy the regulatory close-out clock without achieving actual delivery.

![The Delisting Trigger: BBBY Algo Activity vs Options Delisting](figures/chart_kill_switch.png)

---

## 6. The CHWY Cross-Ticker Validation

As an additional out-of-sample test, I examined **CHWY (Chewy Inc.)** around its IPO on June 14, 2019. Under Reg SHO 203(b)(3), a bona fide market maker receives a **35 calendar-day exemption** from close-out requirements for IPO allocations. June 14 + 35 = July 19, 2019.

![As an additional out-of-sample test, I examined **CHWY (Chewy Inc.)** around its IPO on June 14, 2019. Under Reg SHO 203(b)(3), a bona fide market maker receives a **35 calendar-day exemption** from close-out requirements for IPO allocations. June 14 + 35 = July 19, 2019.](figures/table_08_07_the_fingerprint.png)

*Source: ThetaData OPRA historical options trades, CHWY, Jun 14 - Jul 31, 2019.*

The DMA fingerprint ramped **7.2x from baseline** (90 to 649) in 3 days before the Reg SHO exemption expired, peaking on day +34, then dropping 42% on the deadline day and returning to baseline within 2 days. This cross-ticker confirmation independently validates the deadline-alignment hypothesis on a security with a known, calendar-fixed regulatory deadline.

![CHWY: IPO + 35 Day DMA Fingerprint Ramp](figures/chart_chwy_deadline.png)

---

## 7. Operator Candidacy

Who runs this? Public OPRA data is anonymized, but three facts narrow the field:

**Wolverine Trading** is the confirmed **[Designated Primary Market Maker (DPM)](https://www.cboe.com/us/options/membership/market_maker/)** for GME options on Cboe. In 2011, [FINRA fined Wolverine $500,000 with $1.9 million in disgorgement](https://www.finra.org/) for using buy-write transactions to improperly address Reg SHO close-out obligations on threshold securities, the identical mechanical profile observed in the DMA fingerprint. In 2021, FINRA fined Wolverine Execution Services $170,000 for inaccurately marking sell orders as long (rather than short) and failing to document locate compliance between 2016-2019.

Based on confirmed exchange memberships, DPM assignments, and the MIAX Pearl/Nasdaq BX venue constraint, the candidate set narrows to three firms:

![Based on confirmed exchange memberships, DPM assignments, and the MIAX Pearl/Nasdaq BX venue constraint, the candidate set narrows to three firms:](figures/table_09_07_the_fingerprint.png)

Definitive identification requires the [MIAX Pearl](https://www.miaxglobal.com/markets/us-options/pearl-options) Level 3 un-anonymized Liquidity Feed, which contains the executing firm MPID for every trade. It costs approximately $2,000.

---

## The Complete System: Seven Parts, One Machine

Across seven posts, here is the publicly verifiable architecture:

![Across seven posts, here is the publicly verifiable architecture:](figures/table_10_07_the_fingerprint.png)

Each data source operates under independent regulatory oversight. No single regulator (the SEC, BaFin, FDIC, FCA, OFR, CFTC, or the federal courts) maintains visibility across all seven layers simultaneously. This fragmentation is not incidental. It is the structural feature that enables the system to operate at scale without triggering automated surveillance.

---

## What Would Falsify This

1. **If the FTD-algo correlation on GME dissolves with additional controls.** Adding intraday realized volatility and bid-ask spread as covariates could absorb the lagged FTD signal. If the t=3.86 drops below significance after controlling for these, the trigger discriminator fails.

2. **If the placebo securities develop FTD sensitivity.** The thesis depends on the algo being FTD-insensitive on liquid stocks and FTD-sensitive on borrow-constrained ones. If future data shows SPY or AAPL developing lagged FTD correlations, the discriminator isn't about borrow constraints, it's about something else.

3. **If the BBBY FTD inversion replicates on non-bankruptcy securities.** The BBBY kill-switch finding depends on the inversion being specific to a stock with no borrowable shares. If other non-bankrupt tickers show the same inverted FTD pattern, the interpretation (synthetic locate manufacturing) weakens.

4. **If the MIAX Pearl Level 3 feed reveals the operator is not a Tier-1 market maker.** If the executing MPID belongs to a retail-facing broker or a non-DPM firm, the entire "compliance infrastructure" framing collapses into a simpler explanation.

---

## The Ask

The next step is definitive operator identification. The MIAX Pearl Level 3 un-anonymized Liquidity Feed (~$2,000) would contain the executing MPID for every qualifying trade. The SEC's Consolidated Audit Trail (CAT) contains the `complexOrderID` and `parentOrderID` fields that would link the options leg to the equity dark-pool leg. And the NSCC's CNS settlement records would show whether the executing entity's net obligation consistently nets to zero following high-activity algorithmic days.

If you're a financial regulator, attorney, or data provider reading this: the subpoena roadmap is in [Paper VIII, Section 6.2](https://github.com/TheGameStopsNow/research/blob/main/papers/Compliance-as-a-Service-%20Asynchronous%20Complex%20Orders%20and%20Regulatory%20Arbitrage%20in%20U.S.%20Equity%20Settlement.pdf?raw=1).

**[github.com/TheGameStopsNow/research](https://github.com/TheGameStopsNow/research)**


