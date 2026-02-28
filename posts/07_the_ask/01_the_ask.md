# The Ask

**The question I get more than any other: "What would you tell a regulator?"**

This is my answer.

I've spent the past year building a nine-paper, publicly reproducible forensic analysis of the U.S. equity settlement system. Every script is published. Every dataset is sourced. Every claim is falsifiable. Across six DD series and 25+ posts, I've documented what I believe is the most detailed empirical mapping of settlement infrastructure vulnerabilities ever assembled from public data.

People have asked me to package it up. So here it is — the five things I would ask a regulator to do, the evidence behind each one, and a downloadable package that anyone in a position of authority can verify independently.

> **Position disclosure:** I hold a long position in GME. I am not a financial advisor, attorney, or affiliated with any entity named in this post.

---

## The 30-Second Version

A meme stock's delivery failures **predict U.S. Treasury settlement failures one week in advance** (Granger causality, F = 19.20, p < 0.0001). When expanded to the full SEC FTD universe (15,916 tickers), 16% of equities show significant Granger causality with Treasury fails — 3.2× the rate expected by random chance, with 228 surviving Bonferroni correction. In December 2025, both markets simultaneously produced >4-sigma stress events separated by exactly one week.

Settlement failures don't disappear — they surf a 15-node regulatory cascade over 45 business days, migrating across tickers, asset classes, and national borders. An algorithm using a single DMA routing fingerprint deploys identically across 31 securities, but its relationship to settlement failures flips from *zero* on liquid stocks to *statistically significant* on borrow-constrained ones (p < 0.001). A cancelled stock is still actively failing 824 days after its CUSIP was erased from existence.

These are not theories. They are empirical observations from public data, validated across 2,038 trading days, 9 tickers, 424 options OI snapshots, and 113 pre-computed result files that anyone can verify without an API key.

The system isn't broken. It's working exactly as designed. The design just has exploitable bugs.

---

## The Evidence Map

Every finding below links to the specific paper, section, and public data source. Nothing is behind a paywall. Nothing requires special access to verify.

| Finding | Key Statistic | Source | Paper |
|---------|:------------:|--------|:-----:|
| **Options market-making creates measurable price dampening** | Negative ACF₁ in 76% of IPOs, 37 tickers | ThetaData SIP, Polygon | [I](https://github.com/TheGameStopsNow/research/blob/main/papers/01_theory_options_hedging_microstructure.md) |
| **An algorithm with six forensic signatures targets catalyst dates** | p < 10⁻⁶ for the `[100,102,100]` jitter on catalysts only | ThetaData OPRA | [II](https://github.com/TheGameStopsNow/research/blob/main/papers/02_forensic_trade_analysis.md) |
| **Surveillance thresholds are systematically evaded** | 7.5:1 asymmetry at 499 vs. 500 contracts | ThetaData OPRA | [II](https://github.com/TheGameStopsNow/research/blob/main/papers/02_forensic_trade_analysis.md) |
| **FTDs propagate through a 15-node, 45-day regulatory cascade** | 18.1× phantom OI enrichment at T+33, p < 0.0001 | SEC FTD data, ThetaData OI | [V](https://github.com/TheGameStopsNow/research/blob/main/papers/05_failure_accommodation_waterfall.md) |
| **~18% of the free float exists in settlement limbo at any time** | ~69.4M share-equivalents in shadow inventory | SEC FTD data | [V](https://github.com/TheGameStopsNow/research/blob/main/papers/05_failure_accommodation_waterfall.md) |
| **89% of settlement burden shifted to opaque channels post-split** | Phantom OI: 10.17× → 2.0×; TRF blocks spike to 1.6M shares | ThetaData OI, Polygon TRF | [V](https://github.com/TheGameStopsNow/research/blob/main/papers/05_failure_accommodation_waterfall.md) |
| **The settlement system has a 630-day macrocycle** | 13.3× above noise; confirmed by agent-based model at 44.5× | SEC FTD data, custom ABM | [VI](https://github.com/TheGameStopsNow/research/blob/main/papers/06_resonance_and_cavity.md), [IX](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md) |
| **GME FTDs Granger-cause U.S. Treasury settlement fails** | F = 19.20, p < 0.0001; 16% of 15,916 tickers significant (3.2× chance) | SEC FTD data, NY Fed PDFTD | [IX](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md) |
| **Regulatory compression migrates stress to less-monitored tickers** | KOSS: +3,039% spectral power at T+33 post-T+1 | SEC FTD data | [IX](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md) |
| **Cross-border cost arbitrage incentivizes exporting failures** | 5,714:1 CSDR vs. Reg SHO penalty ratio | ESMA reports, Reg SHO | [IX](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md) |
| **A cancelled stock still actively fails 824 days post-CUSIP** | 31 unique FTD values, 43% block-sized, through Dec 2025 | SEC FTD data | [IX](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md) |
| **Same DMA fingerprint on 31 tickers, but FTD-coupled only on constrained ones** | GME: t = +3.86, p < 0.001; SPY: t = +0.38, p = 0.708 | ThetaData OPRA, SEC FTD | [VIII](https://github.com/TheGameStopsNow/research/blob/main/papers/08_compliance_as_a_service.md) |
| **FTX Tokenized Stocks served as phantom locates** | €32.7M total assets vs. $65M claim; 0 GME shares under oath | Bundesanzeiger, Kroll SOAL | [VII](https://github.com/TheGameStopsNow/research/blob/main/papers/07_shadow_ledger_offshore_crypto.md) |
| **42.2 billion CAT errors, $1 million fine** | $0.0000236 per violation | FINRA AWC 2020067253501 | [III](https://github.com/TheGameStopsNow/research/blob/main/papers/03_policy_regulatory_implications.md) |

---

## Five Actions for Regulators

Every item below is ranked by impact and feasibility. Each one points to the specific data, the specific authority who can act, and the specific statutory basis.

---

### Action 1: Execute the FINRA CAT Queries

**What:** Run eight specific Consolidated Audit Trail queries that close the attribution gap — identifying *who* operates the algorithmic patterns documented across 3.5 years.

**Why it matters:** The research identifies *what* happened, *how* it was executed, and *when*. But public data doesn't contain the Market Participant Identifier (MPID) that proves *who* did it. The CAT was built for exactly this purpose. Eight queries — ready to execute — are specified in [Paper III, §3.2](https://github.com/TheGameStopsNow/research/blob/main/papers/03_policy_regulatory_implications.md).

**The definitive query:** If the MPID on the January 2021 jitter sequence matches the MPID on the June 2024 sequence, that single datum proves the same entity engineered both events. The `[100, 102, 100]` signature has a zero background rate across 2,038 trading days. Even one query returning a match across time periods would be dispositive.

| Query | What it proves |
|:-----:|---------------|
| Q1 | Same entity structuring at 499 lots to evade the 500-contract ISG threshold |
| Q2 | Premeditated cross-strike probing 600ms before target sweep |
| Q3–Q5 | $34M conversion: options lock-in → 4-hour delay → fragmented dark pool delivery |
| Q6 | Same MPID settling across GME and KOSS simultaneously (Jaccard = 0.882) |
| Q7 | Put-call parity predictor: do the conversion MPIDs match subsequent TRF MPIDs? |
| Q8 | Intentional CAT linkage error exploitation using the T+3 repair window |

**Who has authority:** The SEC Division of Enforcement and FINRA Market Regulation both have direct CAT access. The House Financial Services Committee has subpoena authority.

**Statutory basis:** FINRA CAT NMS Plan; SEC Rule 613

---

### Action 2: Investigate the T+45 Accommodation Window

**What:** Conduct a formal investigation into the 45-business-day settlement accommodation window — the regulatory cascade that allows delivery failures to persist for over two months before capital-destructive mechanisms force resolution.

**Why it matters:** The Failure Accommodation Waterfall ([Paper V](https://github.com/TheGameStopsNow/research/blob/main/papers/05_failure_accommodation_waterfall.md)) is the first empirical lifecycle map of delivery failures. Three findings eliminate all non-settlement explanations:

- **18.1×** phantom OI enrichment at the T+33 checkpoint (p < 0.0001)
- **Zero** deep OTM put trades on control days vs. 240,880 on echo dates
- Enrichment is **inversely correlated with volatility** — 0.5× on FOMC days vs. 18.1× on settlement dates

The accommodation window functions as an unregulated lending facility for participants with clearing access, creating information asymmetry over participants who cannot observe the shadow inventory. And when the system is compressed (T+1 transition), the stress doesn't disappear — it migrates to less-monitored tickers ([Paper IX, §2](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md)).

**Who has authority:** GAO (non-partisan investigation), SEC Division of Trading and Markets, DTCC/NSCC.

**Statutory basis:** SEC Rules 204, 15c3-1; NSCC Rules 11, 18

---

### Action 3: Fix the Fine Structure

**What:** Reform the CAT error penalty structure so that fines are proportional to the economic benefit of non-compliance, not a flat fee per million events.

**Why it matters:** In October 2024, FINRA fined Citadel Securities $1 million for 42.2 billion inaccurate order events ([FINRA AWC 2020067253501](https://www.finra.org/rules-guidance/oversight-enforcement/finra-disciplinary-actions)). That's $0.0000236 per violation. A single 1,000,000-share conversion trade yields ~$80,000 in risk-free basis capture. The algorithm would need to generate 3.3 billion CAT errors before fines offset the profit of *one trade*.

The T+3 CAT Repair Window compounds this: firms can deliberately omit linkage data in real-time (blinding surveillance), execute the trade, and then retroactively repair the record within three days. The fine for this behavior is a rounding error.

**Proposed fix:** An escalating penalty matrix tied to:
1. Execution volume of unlinked trades
2. Potential arbitrage yield during the blindness window
3. Repeat offender multipliers

**Who has authority:** FINRA (SRO authority, can amend penalty schedules without legislation), SEC (can mandate via rulemaking).

**Statutory basis:** FINRA Rule 6830; CAT NMS Plan §6.6

---

### Action 4: Require Settlement Transparency

**What:** Four targeted disclosure requirements that close the major opacity gaps:

| Gap | Current State | Proposed Fix |
|-----|--------------|-------------|
| **FTD reporting** | Biweekly, netted, 2-week lag | Daily gross reporting, T+1 publication |
| **CAT linkage for HFT** | T+3 repair window allows deliberate blindness | Intraday repair requirement for HFT entities |
| **Conversion settlement** | Dark pool equity at prices detached from lit markets | Mandatory synthetic price attestation |
| **Cross-border fails** | No visibility into settlement failure exports | Require reporting when obligations move to foreign CSDs |

**Why these four:** Each corresponds to a documented blind spot. The 89% valve transfer ([Paper V, §5](https://github.com/TheGameStopsNow/research/blob/main/papers/05_failure_accommodation_waterfall.md)) shows settlement accommodation migrating from visible options channels to opaque dark pool equity — you can't regulate what you can't see. The 5,714:1 cross-border cost asymmetry ([Paper IX, §7](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md)) creates a rational incentive to export failures to European infrastructure where penalties are trivial.

**Who has authority:** SEC (rulemaking), Congress (legislation).

**Statutory basis:** Exchange Act §13, §17; Reg SHO Rule 204; Reg NMS Rule 613

---

### Action 5: Accelerate Securities Lending Transparency (Rule 10c-1a)

**What:** Reverse the extension of Rule 10c-1a's compliance deadline from March 2029 back to its original April 2026 effective date.

**Why it matters:** Rule 10c-1a was adopted in response to the January 2021 events. It would require public dissemination of aggregate securities lending data — the bilateral OTC stock lending channel identified in the research as the "dark locate pipeline." The industry successfully lobbied for an 8-year delay (2021 → 2029). During those eight years, the pipeline remains invisible.

The question for any regulator: *what requires eight years of preparation to disclose?*

**Who has authority:** SEC (can modify exemptive orders), Congress (can mandate via legislation or hearing pressure).

**Statutory basis:** Exchange Act §10(c); SEC Rule 10c-1a

---

## The Regulatory Evidence Package

Everything I've described above — every paper, every data source reference, every CAT query specification, every proposed rule amendment — is collected in a single, self-contained directory on GitHub:

📦 **[Regulatory Evidence Package](https://github.com/TheGameStopsNow/research/tree/main/regulatory_package)**

The package is designed for four audiences:

| Audience | Start Here | Time |
|----------|-----------|:----:|
| **Congressional staffer** | `EXECUTIVE_SUMMARY.md` | 5 min |
| **SEC/FINRA examiner** | `SUBPOENA_QUERIES.md` + `EVIDENCE_INDEX.md` | 30 min |
| **Legislative counsel** | `ACTION_ITEMS.md` + `RULE_AMENDMENTS.md` | 1 hour |
| **Technical reviewer** | `VERIFICATION.md` + the full papers | 4+ hours |

Everything in the package can be independently verified. Every statistical claim links to a specific notebook command. Every data source is public. The package is maintained in the same [GitHub repository](https://github.com/TheGameStopsNow/research) that contains every script, dataset, and pre-computed result from the entire research series.

---

## What You Can Do

If you found this research useful and want it to reach people who can act on it:

**1. Share the package.** The [Regulatory Evidence Package](https://github.com/TheGameStopsNow/research/tree/main/regulatory_package) is designed to be handed directly to congressional offices, regulatory analysts, and journalists. It stands on its own without requiring anyone to read Reddit.

**2. Write your representative.** The House Financial Services Committee has jurisdiction over SEC oversight. The Senate Banking Committee has jurisdiction over DTCC/NSCC clearing infrastructure. A constituent letter referencing specific findings — especially the Treasury contagion channel — is more effective than a thousand social media impressions.

**3. Verify the data yourself.** Every claim in this post is backed by a specific notebook in the [public repository](https://github.com/TheGameStopsNow/research). The evidence notebooks require **zero API keys** — they load pre-computed results and render every statistical test. If I'm wrong, show me where with data. That's the deal.

---

## How I Tried to Prove Myself Wrong

You don't get to claim something this big without saying what would kill it. Here's my list:

1. **"The Treasury thing is just market noise."** First tested 7 stocks — only GME was significant (F = 19.20, p < 0.0001). Then expanded to **15,916 tickers**: 16% predict Treasury fails vs 5% expected by chance. The signal is systemic, not GME-specific, which strengthens the contagion thesis. ([Paper IX, §3.4](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md); [expanded panel](https://github.com/TheGameStopsNow/research/blob/main/code/analysis/ftd_research/granger_panel_expanded.py))

2. **"The waterfall is just normal hedging."** If it were hedging, enrichment would increase with volatility. It's *inversely* correlated: 0.5× on FOMC days, 18.1× on settlement dates. Hedging hypothesis destroyed. ([Paper V, §3.3](https://github.com/TheGameStopsNow/research/blob/main/papers/05_failure_accommodation_waterfall.md))

3. **"The DMA fingerprint is normal market-making."** It is, on liquid securities. SPY shows zero FTD coupling. GME shows p < 0.001. Same algorithm. Different trigger logic. ([Paper VIII, §3.3](https://github.com/TheGameStopsNow/research/blob/main/papers/08_compliance_as_a_service.md))

4. **"The macrocycle is a data artifact."** I built a simulation with only the SEC's regulatory deadlines. The 630-day cycle emerged at 44.5× background noise without being specified as a parameter. It's emergent arithmetic, not curve-fitting. ([Paper IX, §8.2](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md))

5. **"BBBY is a database glitch."** 31 unique FTD values, 43% block-sized, actively cycling. Zero administrative noise. ([Paper IX, §5.2](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md))

If any of these falsification criteria are met, I'll update the record. That's how science works.

---

## The Complete Research Series

| Series | Posts | Core Finding | Papers |
|:------:|:-----:|-------------|:------:|
| [1. The Strike Price Symphony](https://www.reddit.com/user/TheGameStopsNow/comments/1r5hog7/strike_price_symphony_1) | 3 | Six forensic signatures of an algorithm targeting catalyst dates | [I](https://github.com/TheGameStopsNow/research/blob/main/papers/01_theory_options_hedging_microstructure.md), [II](https://github.com/TheGameStopsNow/research/blob/main/papers/02_forensic_trade_analysis.md) |
| [2. Options & Consequences](https://www.reddit.com/r/Superstonk/comments/1raqqef/options_consequences_following_the_money_1) | 4 | Balance sheets, the microwave network, the yen carry trade | [III](https://github.com/TheGameStopsNow/research/blob/main/papers/03_policy_regulatory_implications.md), [IV](https://github.com/TheGameStopsNow/research/blob/main/papers/04_infrastructure_macro.md) |
| [3. The Failure Waterfall](https://www.reddit.com/r/Superstonk/comments/1re1ps2/1_the_failure_accommodation_waterfall_where_your/) | 4 | FTDs surf a 15-node, 45-day cascade; the settlement system is a resonant bell | [V](https://github.com/TheGameStopsNow/research/blob/main/papers/05_failure_accommodation_waterfall.md), [VI](https://github.com/TheGameStopsNow/research/blob/main/papers/06_resonance_and_cavity.md) |
| [4. Boundary Conditions](https://www.reddit.com/r/Superstonk/comments/1rgrvuw/boundary_conditions_part_1_the_overflow/) | 3+summary | Stress migrates across tickers, Treasuries, borders; the macrocycle is emergent arithmetic | [IX](https://github.com/TheGameStopsNow/research/blob/main/papers/09_boundary_conditions.md) |
| 5. The Shadow Ledger | 7 | Phantom locates, the $6T derivative spike, the Ouroboros funding loop | [VII](https://github.com/TheGameStopsNow/research/blob/main/papers/07_shadow_ledger_offshore_crypto.md) |
| 6. The Trojan Horse | 5 | Compliance-as-a-Service, the BTC reflexive trap, the convergence | [VIII](https://github.com/TheGameStopsNow/research/blob/main/papers/08_compliance_as_a_service.md) |
| **7. The Ask** | **This post** | **What to do about it** | **All nine** |

📂 **Repository:** [github.com/TheGameStopsNow/research](https://github.com/TheGameStopsNow/research)
📦 **Regulatory Package:** [github.com/TheGameStopsNow/research/tree/main/regulatory_package](https://github.com/TheGameStopsNow/research/tree/main/regulatory_package)

---

*Not financial advice. Forensic research using public data. I'm not a financial advisor, attorney, or affiliated with any entity named in this post. The author holds a long position in GME.*

*"The most exciting phrase to hear in science, the one that heralds new discoveries, is not 'Eureka!' but 'That's funny...'"*
*— Isaac Asimov (attributed)*
