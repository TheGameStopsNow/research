# Evidence Index

Every finding in the research series, mapped to its paper, section, data source, and key statistic.

---

## Category 1: Mechanism — How Options Market-Making Creates Exploitable Infrastructure

| # | Finding | Statistic | Paper | Section | Data Source |
|:-:|---------|:---------:|:-----:|:-------:|------------|
| 1 | Options listing produces negative return autocorrelation (dampening) | ACF₁ < 0 in 76% of IPOs | I | §4.8 | ThetaData SIP |
| 2 | Dampening spans the full spectrum from −0.232 to +0.111 | 37-ticker panel | I | §4.3 | ThetaData SIP, Polygon |
| 3 | Gamma squeeze events produce a specific ACF signature (+0.11) | GME: +0.107, AMC: +0.111 | I | §4.4 | ThetaData SIP |
| 4 | LEAPS carry 45% of hedging energy from 5% of trade volume | Inventory Battery Effect | I | §5.5 | ThetaData OPRA |
| 5 | A bespoke SOR uses `[100, 102, 100]` jitter exclusively on catalyst dates | p < 10⁻⁶ | II | §4.9 | ThetaData OPRA |
| 6 | The algorithm structures at exactly 499 lots to evade ISG thresholds | 7.5:1 asymmetry at 499 vs. 500 | II | §4.9 | ThetaData OPRA |
| 7 | A Universal Sonar probes adjacent strikes 0.4–2.3s before sweeping | 100% prevalence | II | §4.11 | ThetaData OPRA |
| 8 | A single 1,056-contract sweep extracted 7.4× NBBO liquidity in 34ms | 13+ exchanges | II | §4.11 | ThetaData OPRA |
| 9 | $34M conversion locked synthetic price, deferred equity delivery days later | Condition Code 12 (Form T) | II | §4.12 | ThetaData OPRA, Polygon |

---

## Category 2: Settlement Accommodation — How Failures Are Managed, Not Resolved

| # | Finding | Statistic | Paper | Section | Data Source |
|:-:|---------|:---------:|:-----:|:-------:|------------|
| 10 | FTDs propagate through a 15-node regulatory cascade over 45 business days | Enrichment: 5.4× (T+3) → 40.3× (T+40) → 0× (T+45) | V | §3.4 | SEC FTD, ThetaData OI |
| 11 | Phantom OI enrichment reaches 18.1× at exactly T+33 (±0 days) | p < 0.0001 | V | §3.3 | ThetaData OI |
| 12 | Zero deep OTM put trades on control days vs. 240,880 on echo dates | Structural boundary | V | §3.3 | ThetaData trades |
| 13 | Enrichment is inversely correlated with volatility | 0.5× FOMC vs. 18.1× settlement | V | §3.3 | ThetaData OI |
| 14 | 89% of settlement burden migrated to opaque channels post-splividend | 10.17× → 2.0× phantom OI; TRF spikes to 1.6M shares | V | §5.2 | ThetaData OI, Polygon TRF |
| 15 | ~18% of GME's free float in settlement limbo at any given time | ~69.4M share-equivalents | V | §8.2 | SEC FTD |
| 16 | Settlement system has Q-factor ≈ 21 (retains 86% echo amplitude per cycle) | Q = 21 | VI | §3 | SEC FTD |
| 17 | 630-business-day macrocycle at 13.3× median noise | Confirmed in basket: GME, AMC, KOSS; absent in SPY, AAPL | VI | §4 | SEC FTD |
| 18 | Same DMA fingerprint on 31 securities | SPY: 436,919 trades; GME: 107,767 trades | VIII | §2.4 | ThetaData OPRA |
| 19 | FTDs significantly predict algo activity on constrained stocks only | GME: t = +3.86, p < 0.001; SPY: t = +0.38, p = 0.708 | VIII | §3.3 | ThetaData OPRA, SEC FTD |
| 20 | BBBY algo activity impedes rather than resolves FTDs | χ² p < 0.001 (inverted) | VIII | §5.3 | ThetaData OPRA, SEC FTD |
| 21 | Algo ceases exactly on options delisting date (Kill Switch) | Deterministic cessation | VIII | §5.4 | ThetaData OPRA |

---

## Category 3: Contagion — How Settlement Stress Propagates Beyond the Ticker

| # | Finding | Statistic | Paper | Section | Data Source |
|:-:|---------|:---------:|:-----:|:-------:|------------|
| 22 | GME FTDs Granger-cause U.S. Treasury settlement fails | F = 9.25, p = 0.003; all lags 1–6 weeks significant | IX | §3.4 | SEC FTD, NY Fed PDFTD |
| 23 | Treasury → GME reverse causation is NOT significant | F = 1.41, p = 0.237 | IX | §3.4 | SEC FTD, NY Fed PDFTD |
| 24 | December 2025: simultaneous >4σ events in both markets, 1-week lag | GME: +4.2σ, Treasury: +4.0σ | IX | §3.5 | SEC FTD, NY Fed PDFTD |
| 25 | T+1 transition collapsed GME spectral power but amplified KOSS by 3,039% | Obligation migration to less-monitored ticker | IX | §2.3 | SEC FTD |
| 26 | XRT FTDs surge at T+33 echo of GME spikes | z = +5.5σ on Jan 27, 2021 | IX | §4.2 | SEC FTD |
| 27 | BBBY: 31 unique FTD values, 824 days post-CUSIP cancellation | 43% block-sized; actively managed | IX | §5.2 | SEC FTD |
| 28 | 5,714:1 cost asymmetry between CSDR and Reg SHO for a 35-day fail | CSDR: $1,750 vs. Reg SHO: ~$10M/day | IX | §7.1 | ESMA, Reg SHO |
| 29 | EU equity fail rates spike during U.S. stress events | T+1: +0.5pp; DFV return: +0.3pp | IX | §7.3 | ESMA Statistical Reports |
| 30 | Agent-based model reproduces 630-day macrocycle without it being coded | 44.5× mean spectral power | IX | §8.2 | Custom ABM |

---

## Category 4: Funding & Supply — Where the Supply and Money Come From

| # | Finding | Statistic | Paper | Section | Data Source |
|:-:|---------|:---------:|:-----:|:-------:|------------|
| 31 | FTX Tokenized Stocks: CM-Equity AG had €32.7M assets, filed $65M claim | Balance-sheet impossibility | VII | §3.1 | Bundesanzeiger, Kroll |
| 32 | FTX Trustee reported zero GME shares under penalty of perjury | SOAL | VII | §3.2 | Kroll SOAL |
| 33 | GME FTDs spiked 9.1× in Dec 2022 T+35 window after FTX collapse | KOSS control: 0.8× (flat) | VII | §4.2 | SEC FTD |
| 34 | JPMorgan total derivative notional: +$6T in Q1 2021 | $47.2T → $53.2T | VII | §5.1 | FDIC Call Reports |
| 35 | JPMorgan held 70% of all U.S. bank equity derivatives entering 2021 | $3,187B of $4,529B | VII | §5.1 | OCC Quarterly Report |
| 36 | 8 ISDA agreements filed in 7 consecutive days before UMR Phase 6 | €8B+ AANA threshold | VII | §5.2 | UK Companies House |
| 37 | Cantor Fitzgerald: $16.7B repo book, 102% Treasury pledge ratio | Zero mention of Tether | VII | §7.1 | SEC X-17A-5 |
| 38 | GCF repo spiked +11.6% on $1B Tether mint date; DVP and Tri-Party declined | Channel-specific divergence | VII | §7.3 | OFR Short-Term Funding Monitor |
| 39 | Goldman Sachs: ~$9–10B in crypto-adjacent 13F positions | IBIT, ETHE, MSTR, COIN | VII | §9.2 | SEC 13F-HR |
| 40 | 42.2 billion CAT errors, $1M fine = $0.0000236/violation | FINRA AWC 2020067253501 | III | §4.2 | FINRA |

---

*Every finding above can be independently verified using the [public repository](https://github.com/TheGameStopsNow/research). See [VERIFICATION.md](VERIFICATION.md) for step-by-step instructions.*
