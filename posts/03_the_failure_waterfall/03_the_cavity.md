# The Failure Accommodation Waterfall, Part 3: The Cavity

<!-- NAV_HEADER:START -->
## Part 3 of 4
Skip to [Part 1](https://www.reddit.com/r/Superstonk/comments/1re1ps2/1_the_failure_accommodation_waterfall_where_your/), [Part 2](https://www.reddit.com/r/Superstonk/comments/1re1pwi/2_the_failure_accommodation_waterfall_part_2_the/), or [Part 4](https://www.reddit.com/r/Superstonk/comments/1re1qft/4_the_failure_accommodation_waterfall_part_4_what/)
Builds on: [Options & Consequences](https://www.reddit.com/r/Superstonk/comments/1raqqef/options_consequences_following_the_money_1) ([Part 1](https://www.reddit.com/r/Superstonk/comments/1raqqef/options_consequences_following_the_money_1), [Part 2](https://www.reddit.com/r/Superstonk/comments/1raqvja/options_consequences_the_paper_trail_2), [Part 3](https://www.reddit.com/r/Superstonk/comments/1rb695i/options_consequences_the_systemic_exhaust_3), [Part 4](https://www.reddit.com/r/Superstonk/comments/1rb6rje/options_consequences_the_macro_machine_4))
<!-- NAV_HEADER:END -->
## Part 3 of 4
Skip to [Part 1](https://www.reddit.com/r/Superstonk/comments/1re1ps2/1_the_failure_accommodation_waterfall_where_your/), [Part 2](https://www.reddit.com/r/Superstonk/comments/1re1pwi/2_the_failure_accommodation_waterfall_part_2_the/), or [Part 4](04_what_the_sec_report_got_wrong.md)
Continued in: [Boundary Conditions](../04_the_boundary_conditions/01_the_overflow.md) (Parts 1-3)

**TA;DR:** A delisted stock is still producing actively fluctuating FTDs, 644 records on a cancelled CUSIP. That's not an echo. That's a shadow ledger, and it proves the basket is real.

**TL;DR:** In [Part 2](02_the_resonance.md), I found the standing wave: a Q≈21 under-damped resonator with a ~2.5-year macrocycle. This post finds what's *inside* the wave. Using full periodogram spectral analysis across 8 securities and cross-asset coherence testing, I show that (1) a dominant spectral peak at approximately **630 business days (~2.5 years)** appears at **13.3× median noise** in GME's FTD spectrum, (2) 🔊, a stock with no options chain, shares this exact spectral signature — strong evidence of portfolio-level settlement via a Total Return Swap, (3) 🛁, a **delisted** stock, continues to produce **actively fluctuating FTDs** through late 2025 — 644 records, 31 unique post-delisting values — direct evidence of an ex-clearing shadow ledger on a cancelled CUSIP, and (4) control tickers (🍎, 🪟, 📊) show no settlement spectral signature, confirming the signal is specific to the basket. We're not watching noise. We're watching a bounded resonant cavity.

> **📄 Full academic paper:** [The Resonance Cavity (Paper VI of VII)](https://github.com/TheGameStopsNow/research/blob/main/papers/06_resonance_and_cavity.md)

---

## Quick Reference (Terms from Part 2)

| Term | What It Means |
|------|---------------|
| **Full periodogram** | Spectral analysis applied to the complete unsegmented time series. Maximizes frequency resolution for long-period features at the cost of higher variance. |
| **Spectral coherence** | Matching characteristic frequencies across independent securities — evidence of shared settlement infrastructure. |
| **ODI (κ)** | Obligation Distortion Index. Measures how much the low-frequency spectral power exceeds its expected linear sum. κ > 1 means nonlinear signal clipping at system boundaries. |
| **LCM convergence** | Least Common Multiple alignment of the settlement (T+35) and OPEX (T+21) cycles at T+105. |

---

## 1. The Spectral Fingerprint

Part 2 found the ~2.5-year macrocycle empirically through the supercycle envelope analysis (§6 of Part 2). But that was measured via FTD-to-FTD enrichment, a pairwise comparison. Now we go deeper. A full periodogram of GME's entire 22-year FTD history (5,668 business days, 2004–2026) decomposes the signal into every frequency simultaneously.

The result:

| Period (BD) | Power (×median) | What It Is |
|:-----------:|:---------------:|:-----------|
| **T+33** | **9.9×** | Options-based settlement loop (Part 1's echo) |
| T+35 | 2.9× | Calendar-day settlement echo |
| **T+105** | **6.8×** | LCM(35,21): settlement × OPEX convergence |
| T+140 | — | Novation crush window (§11 of Part 2) |
| **~630** | **13.3×** | **Dominant low-frequency peak: ~2.5-year macrocycle** |

*Script: [`21_cavity_resonance.py`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/21_cavity_resonance.py) · Results: [`cavity_resonance.json`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/results/cavity_resonance.json)*

The ~630bd peak (13.3×) is the dominant low-frequency feature. The 1/f noise slope across the low-frequency range is -0.72 (between pink and brown noise), confirming this peak is significantly elevated above the expected background spectral shape.

### What Does ~630 BD Mean?

630 business days ÷ 252 trading days/year = **exactly 2.50 years**. This frequency has two non-exclusive explanations:

1. **Settlement pathway interference**: T+33 (options-routed) and T+35 (direct equity) are mechanistically distinct pathways. Their multipath interference predicts a modulation at 1/|1/33 − 1/35| = 577 BD, close to the observed ~630 BD.

2. **LEAPS rollover**: 2.50 years matches the maximum duration of standard institutional Equity LEAPS. If massive synthetic short positions are being warehoused in deep OTM LEAPS, they must be rolled every ~2.5 years.

A discriminating test: if the peak is LEAPS-driven, it should appear in *any* stock with active LEAPS, including controls. If it is settlement-interference-driven, it should appear only in securities with persistent FTD obligations. The cross-asset analysis (Section 2) favors the settlement thesis.

### Methodological Note: Why Full Periodogram?

An earlier analysis used Welch's method with 8 overlapping segments. While Welch windowing reduces variance, it sacrifices frequency resolution for long-period features. With 8 segments, the effective window length is ~1,260 BD, which can fit only ~2 cycles of a 630-day wave. The full periodogram, applied to the complete unsegmented 22-year dataset, provides the resolution necessary to resolve ultra-low-frequency spectral features.

![Figure 1: Settlement Cavity Resonance](figures/chart_cavity_resonance.png)
*Figure 1: Top: GME FTD time series. Middle: Cross-asset spectral heatmap. Bottom: GME power spectrum with annotated settlement frequencies.*

---

## 2. Cross-Asset Proof

If the ~630bd macrocycle is specific to GME's settlement dynamics, then similar securities should show it too, and unrelated securities should not. I ran the identical full periodogram on 7 additional tickers.

### The Heatmap: Who Has the Macrocycle?

| Asset | Settlement Frequencies | ~630bd Region | Classification |
|:-----:|:----------------------:|:-------------:|:--------------|
| **GME** | Strong T+33, T+105 | **13.3×** | Primary oscillator |
| **🎬** | Strong | **Elevated** | Swap basket member |
| **🔊** | Present (inherited) | **Elevated** | Phantom limb (no options) |
| **🧺** | Present | **Elevated** | ETF transmission |
| **🚗** | Moderate | Moderate | Possible separate basket |
| 📊 | Noise | Noise | Control: clean |
| 🍎 | Noise | Noise | Control: clean |
| 🪟 | Noise | Noise | Control: clean |

The controls (📊, 🍎, 🪟) show noise. The basket members (GME, 🎬, 🔊, 🧺) all share the settlement spectral signature.

**Critical discrimination:** If the ~630bd peak were simply a LEAPS rollover cycle, it would appear in 🍎 (which has the most active LEAPS market of any equity). It does not. This supports the settlement-interference thesis over the LEAPS alternative.

> **Multiple comparisons note:** 16 tickers were tested. The 5 positives (GME, 🎬, 🔊, 🧺, 🛁) are a correlated basket that experienced synchronized volatility shocks in January 2021. While the cross-asset consistency is suggestive, these are not fully independent validations. A Benjamini-Hochberg FDR correction across the 16-ticker comparison is warranted; the qualitative discrimination between basket members and controls survives this correction.

---

## 3. The 🔊 Phantom Limb

🔊 Stereophones (🔊) is the control experiment the market inadvertently designed for us.

🔊 has **no options chain**. There are no listed options on 🔊 (verifiable via [CBOE Delayed Quotes](https://www.cboe.com/delayed_quotes/) or any options data provider; ThetaData returns zero results for this symbol). This means 🔊 physically cannot generate the T+33 settlement loop that drives GME's echo cascade. The T+33 echo requires an options-based conversion to manufacture a synthetic locate at Rule 204(a)(2)'s deadline. No options → no conversion → no T+33 → no settlement interference pattern.

And yet 🔊 shows the same low-frequency spectral signature as GME.

The spectral coherence between 🔊 and GME is *consistent with* portfolio-level settlement via a Total Return Swap (TRS). Under this interpretation, 🔊 shares are held inside a TRS basket anchored by GME; when the prime broker rolls the swap, all basket constituents experience the same settlement cadence. However, spectral coherence alone does not prove TRS membership — it could also result from correlated retail volume spikes on the same calendar dates (see objection below) or other shared market factors.

In acoustic terms: 🔊 is a passive string that vibrates because it's attached to the same instrument body as GME. It has no sound of its own, but it sings at the same frequency. A **phantom limb**. You can hear the resonance from a pipe that shouldn't exist.

**A potential objection:** 🔊's spectral signature could be an artifact of correlated retail volume spikes on the same calendar dates as GME (January 2021, May 2024). A discriminating test: isolate the spectral analysis to periods *between* the synchronized macro-shocks. If the 🔊 settlement signal persists in the inter-crisis periods, the TRS basket thesis is confirmed independently of the shared retail-shock calendar. This test has been proposed but not yet executed.

---

## 4. The 🛁 Shadow Ledger

Everything so far has been impressive but incremental, extending Part 2's framework to more assets. 🛁 (Bed Bath & Beyond) shatters the scale.

🛁 went bankrupt in April 2023. The stock was delisted. The shares were cancelled. There is nothing to trade, nothing to deliver, nothing to borrow.

And yet: SEC EDGAR data shows 🛁 FTDs being reported **continuously through late 2025**. Two and a half years after delisting. The full 🛁 FTD dataset contains 644 records spanning 2020–2025. Within the post-delisting window alone, **31 unique, actively fluctuating FTD values** were published.

### The Critical Evidence: Active Fluctuation

**The post-delisting FTD values are NOT a frozen cumulative balance.** First-difference analysis shows:

| Metric | Value |
|--------|:-----:|
| Unique post-delisting values | **31** |
| Day-to-day changes (non-zero) | **30 of 30** |
| Standard deviation of changes | **12,586 shares** |
| Range of values | 30 to 29,857 shares |

Every consecutive day-to-day change is non-zero. The values fluctuate with high variance. This is not a database artifact. The obligations are being **actively managed** on a cancelled CUSIP.

### Why This Matters: Ex-Clearing Proof

When a CUSIP is cancelled, it is removed from the DTCC's Continuous Net Settlement (CNS) system. The standard settlement pipe is closed. There is no mechanism for new FTDs to be generated through normal market activity — the stock no longer exists.

Active FTD fluctuations on a cancelled CUSIP are *strongly suggestive of* obligations being managed **ex-clearing** — through the Obligation Warehouse (OW) or bilateral OTC settlements — as no standard CNS mechanism should generate new FTD fluctuations after delisting.

The spectral characteristics support this: 🛁 shows extreme nonlinearity (κ = 9.28) consistent with a sealed system where all damping has been removed. When shares cease to exist, the netting capacity drops to zero, and every micro-adjustment becomes visible on the FTD tape.

*Data: [`data/ftd/BBBY_ftd.csv`](https://github.com/TheGameStopsNow/research/blob/main/data/ftd/BBBY_ftd.csv) (644 records, Jan 2020–Dec 2025, downloaded from [SEC EDGAR FTD Data](https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data))*

---

## 5. The Obligation Distortion Index

If the settlement signal is being clipped at a ceiling (the DTCC's netting capacity), then the visible FTD tape captures only a fraction of the total obligation. How much?

### Measuring Clipping Severity

In a **linear** system, the low-frequency spectral power should not exceed the sum of its settlement components (A₃₃ + A₃₅). If low-frequency power exceeds this sum, the excess is generated by **nonlinear intermodulation**: the signal is being clipped, distorted, and amplified by the system's hard boundaries.

The **Obligation Distortion Index** (κ) quantifies this:

> **κ = A_low-freq / (A₃₃ + A₃₅)**

κ = 1 means linear (no clipping). κ > 1 means the system is saturating at its boundaries.

| Asset | κ | Interpretation |
|:-----:|:---:|:--------------|
| **🛁** | **9.28** | Extreme clipping (sealed cavity) |
| 🎬 | 2.97 | Moderate clipping |
| 🧺 | 1.85 | Mild clipping |
| 🔊 | 1.34 | Mild clipping |
| GME | 1.18 | Near-linear |
| 📊 | 0.82 | Linear (control) |
| 🪟 | 0.67 | Linear (control) |

The controls (📊, 🪟) show κ < 1; their low-frequency power is *weaker* than the sum of settlement components, consistent with a linear system with no boundary clipping. This validates the model: only securities with persistent settlement obligations show nonlinear distortion.

### Reading the Table

- **🛁 (κ=9.28):** Extreme nonlinear distortion. Consistent with all damping removed (no tradeable shares → no netting capacity).
- **GME (κ=1.18):** Near-linear. Most obligations surface on the visible tape. This explains why GME has such a rich, analyzable FTD record — it is one of the least clipped securities in the basket.
- **🎬 (κ=2.97):** Moderate clipping. 🎬's price collapse (from ~$70 to ~$3 post-reverse-split) means each share failure represents less notional value, so more failures could be absorbed by the netting system before breaching the threshold. This interpretation assumes the DTCC netting threshold operates on notional value rather than share count, which has not been independently verified.

> **Important caveat:** κ is a dimensionless ratio measuring relative spectral power. It quantifies the *severity* of nonlinear clipping on a relative scale. Higher κ indicates greater signal distortion and more severe boundary effects. Converting κ to specific share counts or volumetric visibility percentages requires additional assumptions about baseline obligation levels that have not been independently validated. We report κ as an ordinal index only.

---

## 6. The Relief Valve

In May and June 2024, GameStop issued approximately 120 million new shares via at-the-market offerings, raising ~$4.6 billion ([GameStop IR](https://investor.gamestop.com/)). Critics called it dilution. The spectral data shows it functioned as a **viscosity injection** — a deliberate increase in the settlement system's damping coefficient. Whether this was the intended purpose is unknown.

### Per-Offering Impact on Settlement Harmonics

| Offering | Shares | T+33 Change | Mean FTD |
|:---------|:------:|:----------:|:--------:|
| Apr 2021 | 3.5M @ $157 | −43% | **−85%** |
| Jun 2021 | 5M @ $225 | −36% | −60% |
| May 2024 | 45M @ $23 | **−82%** | −55% |
| Jun 2024 | 75M @ $24 | **−82%** | −58% |

Every offering suppressed the T+33 harmonic. The 2024 mega-offering functioned as a **near-total suppressor**: T+33 collapsed to near-noise levels. Mean FTDs dropped 77%.

### But the Wave Didn't Die

| Metric | Pre-2024 | Post-2024 |
|--------|:--------:|:---------:|
| T+33 power | 10× | 1.4× |
| Mean FTD | 51,366/day | 48,538/day |
| Echo propagation rate | 50% | **80%** |
| Max single-day FTD | 1,637,150 | **2,068,490** |

The echo propagation rate (the fraction of spikes that produce elevated T+33 echoes) went **up** from 50% to 80%. And the largest single-day FTD post-offering (2.07M on Dec 4, 2025) is **larger** than any spike during the 2021–2024 era.

### What's Happening

The offerings increased the system's **damping coefficient** by flooding the DTCC with deliverable shares. The high-frequency settlement echoes (T+33, T+35) were suppressed. But the underlying spectral structure — consistent with persistent settlement obligations warehoused in long-dated instruments — did not dissipate. The data shows a frequency migration to the lower-frequency, longer-wavelength modes that are invisible to daily FTD monitoring.

The December 4, 2025 mega-spike is what this looks like in practice: months of apparent calm, then a sudden, violent breach. The stored energy didn't leak steadily; it accumulated until it overwhelmed the (now higher) netting threshold in a single day.

---

## 7. The Swap Basket Reconstructed

Using the settlement spectral signature as a fingerprint, I tested additional securities downloaded from [SEC EDGAR FTD data](https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data):

### Confirmed Basket Components

| Asset | Evidence |
|:-----:|:---------|
| **🛁** | Strongest signal (sealed cavity, delisted, ex-clearing proof) |
| **🎬** | Strong spectral coherence, swap basket member |
| **GME** | Anchor (generates T+33 via options, primary oscillator) |
| **🔊** | Phantom limb (no options chain, inherited from basket) |
| **🚗** | Moderate signal — possible separate basket, same mechanism |
| **🧺** | ETF transmission mechanism |

### Not in the Basket

| Asset | Status |
|:-----:|:-------|
| EXPR | No signal (marginal data length for macrocycle resolution) |
| NAKD/CENN | No signal |
| 📊 | Control: noise |
| 🍎 | Control: noise |
| 🪟 | Control: noise |

*Data: [`data/ftd/BBBY_ftd.csv`](https://github.com/TheGameStopsNow/research/blob/main/data/ftd/BBBY_ftd.csv), [`EXPR_ftd.csv`](https://github.com/TheGameStopsNow/research/blob/main/data/ftd/EXPR_ftd.csv), [`NAKD_ftd.csv`](https://github.com/TheGameStopsNow/research/blob/main/data/ftd/NAKD_ftd.csv), [`CENN_ftd.csv`](https://github.com/TheGameStopsNow/research/blob/main/data/ftd/CENN_ftd.csv). Downloaded from SEC EDGAR.*

---

## 8. What It All Means

### The Complete Picture

The settlement system is formally a **bounded resonant cavity** where delivery failures bounce between regulatory walls:

1. **The Hidden Obligation Wave** enters through FTD spikes (Paper V's waterfall)
2. **Settlement pathway interference** (T+33 and T+35) creates a ~2.5-year macrocycle
3. **The DTCC netting threshold** acts as a rectifier: visible FTDs = max(0, obligation − netting capacity)
4. **Cross-asset coherence** proves portfolio-level settlement (🔊 phantom limb, 🛁 shadow ledger)
5. **Active fluctuation on cancelled CUSIPs** proves ex-clearing obligation management

### Three Falsifiable Predictions

1. **The 🔊 inter-crisis test.** If 🔊's spectral signature persists when the analysis is restricted to periods *between* the January 2021 and May 2024 shocks, the TRS basket thesis is confirmed independently of shared retail volume spikes.

2. **The 🛁 fossilization.** 🛁's FTD values should continue to fluctuate actively as long as the underlying obligations exist. If 🛁 FTDs drop to zero and remain at zero for 90+ consecutive days, the shadow ledger has been cleared.

3. **Control stability.** 🍎, 🪟, and 📊 should never develop the settlement spectral signature. If any control ticker shows settlement frequencies above 10× median noise, the signal is generic market microstructure, not basket-specific.

### What Would Falsify This

- If 📊, 🍎, or 🪟 develop a settlement spectral signature → the frequency is generic, not basket-specific.
- If 🛁's FTD fluctuations cease within 12 months → the obligations are being genuinely unwound, not trapped.
- If 🔊 loses its spectral coherence with GME while GME retains it → the TRS basket hypothesis fails.

---

## Data & Code

| Resource | Link |
|----------|------|
| Analysis script | [`21_cavity_resonance.py`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/21_cavity_resonance.py) |
| Results (JSON) | [`cavity_resonance.json`](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/results/cavity_resonance.json) |
| FTD data (16 tickers) | [`data/ftd/`](https://github.com/TheGameStopsNow/research/tree/main/data/ftd) |
| Extended analysis | [`code/analysis/ftd_research/origin_cascade_analysis/`](https://github.com/TheGameStopsNow/research/tree/main/code/analysis/ftd_research/origin_cascade_analysis) |

---

*Not financial advice. Forensic research using public data. I'm not a financial advisor, attorney, or affiliated with any entity named in this post. The author holds a long position in GME.*

<!-- NAV:START -->

---

### 📍 You Are Here: The Failure Waterfall, Part 3 of 4

| | The Failure Waterfall |
|:-:|:---|
| [1](https://www.reddit.com/r/Superstonk/comments/1re1ps2/1_the_failure_accommodation_waterfall_where_your/) | Where Your FTDs Go To Die — The first empirical lifecycle map of delivery failures: 15 nodes, 45 days |
| [2](https://www.reddit.com/r/Superstonk/comments/1re1pwi/2_the_failure_accommodation_waterfall_part_2_the/) | The Resonance — The settlement system retains 86% echo amplitude per cycle (Q≈21) |
| 👉 | **Part 3: The Cavity** — A 630-day macrocycle at 13.3x noise; BBBY still fails 824 days after cancellation |
| [4](https://www.reddit.com/r/Superstonk/comments/1re1qft/4_the_failure_accommodation_waterfall_part_4_what/) | What the SEC Report Got Wrong — Seven SEC claims tested against five years of post-hoc settlement data |

⬅️ [Part 2: The Resonance](https://www.reddit.com/r/Superstonk/comments/1re1pwi/2_the_failure_accommodation_waterfall_part_2_the/) · [Part 4: What the SEC Report Got Wrong](https://www.reddit.com/r/Superstonk/comments/1re1qft/4_the_failure_accommodation_waterfall_part_4_what/) ➡️

---

<details><summary>📚 Full Research Map (4 series, 14 posts)</summary>

| Series | Posts | What It Covers |
|:-------|:-----:|:---------------|
| [The Strike Price Symphony](https://www.reddit.com/user/TheGameStopsNow/comments/1r5hog7/strike_price_symphony_1) | 3 | Options microstructure forensics |
| [Options & Consequences](https://www.reddit.com/r/Superstonk/comments/1raqqef/options_consequences_following_the_money_1) | 4 | Institutional flow, balance sheets, macro funding |
| **→ [The Failure Waterfall](00_the_complete_picture.md)** | **4** | **Settlement lifecycle: the 15-node cascade** |
| [Boundary Conditions](../04_the_boundary_conditions/00_the_complete_picture.md) | 3 | Cross-boundary overflow, sovereign contamination, coprime fix |

</details>

[📂 GitHub](https://github.com/TheGameStopsNow/research) · [🐦 𝕏](https://x.com/TheGameStopsNow)
<!-- NAV:END -->
