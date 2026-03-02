# Posts Index

All DD posts organized by series. Each series builds on the previous one, forming a layered forensic case using publicly verifiable data.

---

## Table of Contents

1. [Series 1: The Strike Price Symphony](#series-1-the-strike-price-symphony) — Options microstructure forensics
2. [Series 2: Options & Consequences](#series-2-options--consequences) — Institutional flow, balance sheets, physical infrastructure, macro funding
3. [Series 3: The Failure Waterfall](#series-3-the-failure-waterfall) — Settlement lifecycle forensics: the 15-node regulatory cascade
4. [Series 4: Boundary Conditions](#series-4-boundary-conditions) — Cross-ticker overflow, cross-border export, and the coprime fix
5. [Series 5: The Shadow Ledger](#series-5-the-shadow-ledger) — Offshore fraud, derivative hiding, crypto plumbing, reflexive collateral
6. [Series 6: The Trojan Horse](#series-6-the-trojan-horse) — Endgame thesis: tZERO, digital dividends, acquisition mechanics

---

## Series 1: The Strike Price Symphony

The original DD series. Tick-level options forensics proving six anomalies across 80 million trades, a 37-ticker control panel, and 8 FINRA CAT queries that would identify the entity behind the manipulation.

| # | Post | Description |
|---|------|-------------|
| 1 | [The Machine Under the Market](01_strike_price_symphony/01_the_machine_under_the_market.md) | Six anomalies in GME options data that can't be explained by normal trading: $69.8M in worthless tail-bangs, wash trade clusters, 30% dark venue routing, IV injection → LEAPS loading, COB washes on single strikes, and the 499-lot tape smurfing pattern. Introduces the Long Gamma Default (92.7% dampened days across 37 tickers) and the Inventory Battery Effect. |
| 2 | [The Player Piano](01_strike_price_symphony/02_the_player_piano.md) | NMF decomposition proving ~25% of GME's equity volume variance is mechanically determined by the options chain from weeks earlier. Introduces the Gamma Reynolds Number phase transition model and 5 specific FINRA CAT queries to identify the puppet master. |
| 3 | [The Kill Zone](01_strike_price_symphony/03_the_kill_zone.md) | Millisecond-level cross-asset reconstruction of a single algorithmic strike: a 2-lot probe on an adjacent strike, 586ms wait, then a 1,056-contract sweep extracting 7.4× visible depth in 34ms. A $34M off-tape conversion confirmed via put-call parity and independently corroborated by Citadel's Q2 2024 13F (+426% puts). 3 new CAT queries. |

---

## Series 2: Options & Consequences

Follows the money from the trade tape to SEC filings, physical infrastructure, and macro funding. Traces 263M off-exchange shares to 24 firms, maps an offshore ISDA swap network, proves a 17-sigma algorithmic basket via nanosecond tick data, and identifies the yen carry trade as the funding mechanism.

| # | Post | Description |
|---|------|-------------|
| 1 | [Following the Money](02_options_and_consequences/01_following_the_money.md) | Traces 263M off-exchange GME shares to 24 internalizers. Names the ETF Authorized Participants who cannibalized XRT. Put-call parity predicts dark pool settlement price 3 days in advance (2.9% error). OCC origin codes prove the conversions were proprietary firm trades. Documents the 99.6% compliance flag evasion and the Rule 605 odd-lot loophole exploit. |
| 2 | [The Paper Trail](02_options_and_consequences/02_the_paper_trail.md) | Opens the SEC filing cabinets. Citadel Securities' $2.16T derivative book at 347× notional-to-capital. Citadel Advisors' puts *increased* 47% during Q1 2021 before migrating to Total Return Swaps. $108M in Fails to Receive. Robinhood's $4.9B customer reserve receipt. Offshore ISDA network mapped via UK Companies House (8 prime brokers, €8B+ uncleared derivatives). 10b-5 element mapping. |
| 3 | [The Systemic Exhaust](02_options_and_consequences/03_the_systemic_exhaust.md) | Lateral corroboration from systems Wall Street can't control. A 17-sigma Z-score proving a hardcoded algorithmic basket linking GME to BBBY at 1ms precision. 85 FCC-licensed microwave towers connecting CME to NYSE. A 5-year weather panel showing thunderstorms widen NJ spreads (p=0.009) while Chicago tightens (p=0.021). Robinhood's $57M synthetic share cleanup. Six years of SEC FOIA logs showing zero requests for Rule 605, odd lots, or SBSR. |
| 4 | [The Macro Machine](02_options_and_consequences/04_the_macro_machine.md) | How it was funded and why January 28. The yen carry trade activated on March 2, 2021 — five weeks after the buy button was turned off. CFTC data shows leveraged funds built to −110,635 contracts ($11.1B) by July 2024 before the BoJ rate hike forced a $10.8B unwind. January 28 was triggered by the NSCC VaR margin model — the $3B charge that would have forced the clearinghouse to buy GME at $483 if Robinhood defaulted. The NSCC Risk Management Committee, composed of the clearing members holding the short side, waived the charge instead. |

---

## Series 3: The Failure Waterfall

Maps the complete lifecycle of every Failure-to-Deliver through the settlement system. Built on hypotheses from beckettcat and TheUltimator5, validated through 19 independent statistical tests.

| # | Post | Description |
|---|------|-------------|
| 1 | [Where FTDs Go To Die](03_the_failure_waterfall/01_where_ftds_go_to_die.md) | The first empirical lifecycle map of delivery failures. 19 tests, 424 OI snapshots, 2,038 days of tick data reveal a 15-node regulatory cascade (T+3 to T+45) with 18.1× phantom OI enrichment at T+33. Three smoking guns eliminate all non-settlement explanations. The 6-share TRF vacuum shows how PFOF retail sells are weaponized for FTD close-outs. Post-splividend valve transfer confirms 89% of accommodation migrated to invisible dark pool channels. 2025 forward performance: 100% hit rate (4/4). |
| 2 | [The Resonance](03_the_failure_waterfall/02_the_resonance.md) | FTD-to-FTD resonance analysis across 4,234 records spanning 22 years. The settlement system retains ~86% of its echo amplitude per T+35 cycle (Q≈21). T+25 is the true fundamental (SEC Rule 204(a)(2)), the T+33 echo is a composite. LCM(35,21)=T+105 convergence amplifies above the seed. The January 2021 sneeze followed the harmonic series exactly. Obligation Echo Gauge tracks stored settlement energy. |
| 3 | [The Cavity](03_the_failure_waterfall/03_the_cavity.md) | Full periodogram spectral analysis across 8 securities. A dominant 630 BD (~2.5 year) macrocycle at 13.3× median noise. KOSS (no options chain) shares the spectral signature — phantom limb evidence of a TRS basket. Obligation Distortion Index proves nonlinear clipping at system boundaries. |
| 4 | [What the SEC Report Got Wrong](03_the_failure_waterfall/04_what_the_sec_report_got_wrong.md) | Seven claims from the SEC's October 2021 Staff Report tested against five years of post-hoc settlement data. "No gamma squeeze" missed the conversion mechanism. "FTDs cleared quickly" contradicted by accelerating enrichment (5.4× → 40.3×). "Shorten settlement cycle" failed — T+33 echo 100% in 2025 post-T+1. Five claims incomplete, two contradicted, zero accusations. |

---

## Series 4: Boundary Conditions

Follows the settlement energy when it crosses boundaries the waterfall was never designed to contain: adjacent tickers, sovereign debt, national borders, and cancelled securities. Culminates in an agent-based model proving the macrocycle emerges from regulatory deadlines alone — and a coprime fix that eliminates it.

| # | Post | Description |
|---|------|-------------|
| 1 | [The Overflow](04_the_boundary_conditions/01_the_overflow.md) | T+1 compressed GME's settlement frequencies by 92%, but KOSS amplified +1,051% at T+33 (z=1,050.9). GME uniquely Granger-causes U.S. Treasury settlement fails (F=19.20, p<0.0001). The December 2025 macrocycle window produced simultaneous GME FTD and Treasury fail spikes. ETF substitution channel confirmed: 57% hit rate for XRT echo following GME spikes. |
| 2 | [The Export](04_the_boundary_conditions/02_the_export.md) | 5,714:1 cost asymmetry between U.S. and EU settlement penalties creates rational incentive to export fails offshore. EU equity and ETF fails spike at U.S. stress events; EU government bonds do not. |
| 3 | [The Tuning Fork](04_the_boundary_conditions/03_the_tuning_fork.md) | Agent-based model with 3 agents and 4 regulatory deadlines spontaneously produces the 630-day macrocycle at 42.3x spectral power. LCM(6,13,35,10)=2,730 BD explains why. Under T+1, the LCM compresses to 1,020 BD — the macrocycle shifts from 2.5 years to annual. Coprime deadlines (7,11,37,13) push LCM to 37,037 BD (~147 years), eliminating the resonance cavity entirely. |

---

## Quick Reference

| Series | Posts | Core Evidence Layer |
|--------|:-----:|---------------------|
| The Strike Price Symphony | 3 | Options microstructure: tick-level forensics, 37-ticker panel, CAT queries |
| Options & Consequences | 4 | Institutional flow: FINRA data, SEC filings, FCC towers, CFTC positioning |
| The Failure Waterfall | 4 | Settlement lifecycle: 15-node cascade, phantom OI, TRF internalization, SEC report contrast |
| Boundary Conditions | 3 | Cross-boundary: ticker overflow, sovereign contamination, CSDR arbitrage, ABM emergence |
| **Total** | **14** | |

---

**Repository:** [github.com/TheGameStopsNow/research](https://github.com/TheGameStopsNow/research)

*Not financial advice. Forensic research using public data.*

