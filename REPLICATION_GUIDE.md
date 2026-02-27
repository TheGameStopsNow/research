# Replication Guide

**Repository:** [TheGameStopsNow/research](https://github.com/TheGameStopsNow/research)
**Last Updated:** February 19, 2026

This guide documents the **exact data inputs, temporal windows, detection thresholds, and CUSIPs** used across all 11 interactive evidence notebooks. Every claim in this research can be independently verified using the pre-computed JSON results in the `results/` directory — **no API keys or data subscriptions required**.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/TheGameStopsNow/research.git
cd research/notebooks

# Execute all 11 notebooks headless (Python 3.10+ required)
pip install jupyter pandas matplotlib numpy
for f in *.ipynb; do jupyter nbconvert --to notebook --execute --inplace "$f"; done
```

All notebooks load pre-computed results from `../results/` and render inline charts. Zero external data calls are made during execution.

---

## I. Target Securities

| Symbol | CUSIP | Name | Role in Analysis |
|--------|-------|------|-----------------|
| GME | `36467W109` | GameStop Corp (Hldg Co) Cl A | Primary target |
| AMC | `00165C104` | AMC Entertainment Holdings | Basket member |
| KOSS | `500769103` | Koss Corporation | Basket member (behavioral correlation) |
| XRT | `78464A870` | SPDR S&P Retail ETF | ETF basket vehicle |
| CHWY | — | Chewy Inc | Control / placebo |
| DJT | — | Trump Media & Technology | Control / placebo |
| AAPL | — | Apple Inc | Control / placebo |
| MSFT | — | Microsoft Corp | Control / placebo |
| SPY | — | SPDR S&P 500 ETF Trust | Control / baseline |
| TSLA | — | Tesla Inc | Control / placebo |
| PLTR | — | Palantir Technologies | Control / placebo |
| SOFI | — | SoFi Technologies | Control / placebo |

---

## II. Temporal Windows

### Primary Event Windows

| Window | Start | End | Description |
|--------|-------|-----|-------------|
| **May 2024 Event** | 2024-05-13 (Monday) | 2024-05-17 (Friday, OpEx) | Primary forensic target week |
| **May 2024 FTD Range** | 2024-05-01 | 2024-06-14 | Full SEC FTD data coverage (22 settlement dates) |
| **January 2021 Event** | 2021-01-19 (Tuesday) | 2021-02-12 (Friday) | Historical comparison window (29 trading days) |
| **13F Filing Period** | Q1 2020 | Q2 2024 | Entity position tracking via SEC 13F-HR |
| **Stacking Resonance** | Full history | 2,038 trade dates | 252 option expirations analyzed for GME |

### Pre-Market Burst Window (May 17, 2024)

| Parameter | Value |
|-----------|-------|
| **Pre-market session analyzed** | 04:00 – 09:30 ET |
| **Minutes analyzed (pre-market)** | 90 |
| **Minutes analyzed (regular hours)** | 390 |
| **Minutes analyzed (after hours)** | 240 |

### Lead-Lag Analysis Windows

Options-to-equity lead-lag measured at these millisecond intervals:

| Window (ms) | Purpose |
|-------------|---------|
| 50 | Sub-tick HFT detection |
| 100 | Fast-routing detection |
| 250 | Cross-venue arbitrage |
| 500 | Standard intermarket |
| 1,000 | Institutional flow |
| 2,000 | Algorithmic staging |
| 5,000 | Multi-leg execution |
| 10,000 | Block-level coordination |

**Dates analyzed for GME lead-lag:** `2025-12-26`, `2025-12-29`, `2025-12-30`, `2025-12-31`, `2026-01-02` (5 trading days, `phase4a_leadlag_GME.json`).

---

## III. Notebook-by-Notebook Data Inputs

### `00_evidence_viewer.ipynb`

**Zero-Setup Evidence Dashboard & Verification Matrix**

| Parameter | Value |
|-----------|-------|
| **Setup required** | None (runs offline) |
| **Data source** | 113 pre-computed JSON files in `results/` |
| **Output** | Renders smoking guns, panel ACF, squeeze mechanics, NMF archaeology |
| **Claim Matrix** | Verifies all cross-asset forensic and structural claims |

### `01_options_hedging_signatures.ipynb`

**NBBO Midquote ACF Test & Options Hedging Signatures**

| Parameter | Value |
|-----------|-------|
| **Test** | Panel ACF (Auto-Correlation Function) at lag-1 |
| **Primary date** | 2024-05-17 |
| **Panel size** | 40 observations (full panel) |
| **Tickers in panel** | GME, AAPL, TSLA, MSFT, SPY, PLTR, SOFI, CHWY, DJT, SNAP, AMD, NVDA |
| **ACF methodology** | Midquote return series, bid-ask bounce validation |
| **Detection threshold** | ACF-1 < −0.15 (significant negative autocorrelation) |
| **GME ACF-1 result** | −0.2502 (high-stack mean, `stacking_resonance_GME_20260212_091722.json`) |
| **Control AAPL ACF-1** | −0.191 (0DTE), −0.1269 (WEEKLY) |
| **Result files** | `stacking_resonance_*.json` (8 tickers, timestamped 2026-02-12) |
| **DTE categories** | 0DTE, WEEKLY, MONTHLY, LEAPS |

### `02_shadow_algorithm_forensics.ipynb`

**Stacking Resonance & Burst Analysis (The Shadow Algorithm)**

| Parameter | Value |
|-----------|-------|
| **Primary date** | 2024-05-17 |
| **Tape fracture test dates** | 2024-05-13 through 2024-05-17 (5 trading days) |
| **Pre-market max spread** | $8.42 |
| **Pre-market mean spread** | $0.78 |
| **Pre-market minutes with spread > $5** | 8 |
| **Pre-market minutes with spread > $1** | 14 |
| **Regular hours max spread** | $0.11 |
| **Regular hours mean spread** | $0.01 |
| **After-hours max spread** | $6.43 |
| **Dark pool ceiling (2024-05-17)** | $33.00 (pm_max_dark), $32.89 (pm_p99_dark) |
| **Lit ceiling (2024-05-17)** | $32.23 (pm_max_lit) |
| **Dark volume (2024-05-17)** | 4,433,841 shares |
| **T1 total events scanned** | 111,798 |
| **Result files** | `round10_test_results.json`, `round10_t1_results.json` |

**Contingent Flag Analysis (T3):**

| Symbol | Dates Analyzed | Off-Market Trades | Flagged | Missing Flag | Missing % (trades) | Missing % (shares) |
|--------|---------------|-------------------|---------|-------------|--------------------|--------------------|
| GME | 8 | 699 | 3 | 696 | 99.6% | 43.8% |
| SPY | 14 | 37 | 14 | 23 | 62.2% | 36.7% |
| AAPL | (control) | — | — | — | — | — |

**Cross-Date Dark Pool Maximums:**

| Date | All-Day Max Dark | PM Max Dark | Dark Volume |
|------|-----------------|-------------|-------------|
| 2024-05-13 | $38.20 | $26.58 | 3,088,216 |
| 2024-05-14 | $80.00 | $80.00 | 7,462,297 |
| 2024-05-15 | $64.74 | $64.74 | 4,167,362 |
| 2024-05-16 | $39.55 | $39.55 | 1,714,733 |
| 2024-05-17 | $34.01 | $33.00 | 4,433,841 |

### `03_pfof_structural_conflicts.ipynb`

**Payment-for-Order-Flow Execution Mechanics**

| Parameter | Value |
|-----------|-------|
| **Entity** | Robinhood Securities, LLC |
| **Data source** | SEC EDGAR Rule 606 XML filings |
| **Period** | FY2024 (all 4 quarters) |
| **Total annual PFOF** | $969,912,812.85 |
| **Citadel annual PFOF** | $352,532,886.15 (36.3% share) |
| **Citadel options PFOF** | $282,510,484.81 (36.1% of options) |
| **Result file** | `phase16_deep_forensic_master.json`, `pfof_crossref.json` |

**Quarterly PFOF Breakdown:**

| Quarter | Total PFOF | Citadel PFOF | Citadel Share % | Citadel Options PFOF | Citadel Equity PFOF |
|---------|-----------|-------------|-----------------|---------------------|---------------------|
| Q1 2024 | $188,734,621.64 | $73,134,416.99 | 38.7% | $58,305,712.91 | $14,828,704.08 |
| Q2 2024 | $228,533,952.77 | $83,275,984.33 | 36.4% | $68,982,609.10 | $14,293,375.23 |
| Q3 2024 | $253,396,132.92 | $86,607,062.15 | 34.2% | $68,982,609.10 | — |
| Q4 2024 | $299,248,105.52 | $109,515,422.68 | 36.6% | $86,239,553.70 | — |

**Dual-Role Entity Cross-Reference:**

| Entity | PFOF ($M) | Equity PFOF % | Options PFOF % | GME Shares Internalized | Baseline Multiplier |
|--------|----------|--------------|---------------|------------------------|-------------------|
| Citadel Securities LLC | 352.5 | 28.0% | 36.1% | 56,170,024 | 22.8× |
| Virtu Americas LLC | 42.3 | 37.1% | 0.0% | 81,331,154 | 42.1× |
| Jane Street Capital LLC | 44.1 | 15.8% | 0.0% | 38,651,285 | 18.9× |
| G1 Execution Services LLC | 13.6 | 10.0% | 0.0% | 44,223,226 | 25.0× |
| Two Sigma Securities LLC | 15.2 | 9.1% | 0.0% | 11,643,229 | 8.3× |

### `04_etf_cannibalization.ipynb`

**ETF Basket Correlation & Cannibalization**

| Parameter | Value |
|-----------|-------|
| **Symbols** | GME (`36467W109`), KOSS (`500769103`), XRT (`78464A870`) |
| **May 2024 window** | 2024-05-01 through 2024-05-31 (22 settlement dates) |
| **January 2021 window** | 2021-01-04 through 2021-02-12 (29 settlement dates) |
| **Data source** | SEC EDGAR FTD files (CNS Fail-to-Deliver) |
| **Result file** | `round12_v1_etf_cannibalization.json` |

**May 2024 FTD Totals:**

| Symbol | Total FTDs | Peak Single-Day FTDs | Peak Date |
|--------|-----------|---------------------|-----------|
| GME | 5,375,780 | 1,143,204 | 2024-05-14 |
| XRT | 2,451,042 | 1,173,396 | 2024-05-23 |
| KOSS | 703,464 | 440,604 | 2024-05-14 |

**January 2021 FTD Totals:**

| Symbol | Total FTDs | Peak Single-Day FTDs | Peak Date |
|--------|-----------|---------------------|-----------|
| GME | 14,048,909 | 2,099,572 | 2021-01-27 |
| XRT | 6,715,907 | 2,218,348 | 2021-02-02 |
| KOSS | 916,367 | 322,870 | 2021-02-02 |

### `05_swap_ledger_and_lineage.ipynb`

**Archegos Swap Ledger Timeline & UBS Migration**

| Parameter | Value |
|-----------|-------|
| **Primary event date** | 2024-05-13 |
| **CS → UBS merger completion** | ~June 2023 |
| **Key FINRA ATS weeks analyzed** | 2021-01-18, 2021-01-25, 2021-02-01, 2021-02-22, 2021-03-22, 2021-03-29, 2023-05-15, 2023-09-11, 2024-05-13 |
| **Result files** | `round12_v2c_cs_ubs_lineage_SUMMARY.json`, `round12_v2d_extended_timeline.json` |

**XRT Dark Pool Flow (CS + UBS Combined Share):**

| Week Starting | CS CrossFinder % | UBS ATS % | Combined % | UBS MPID |
|---------------|-----------------|----------|-----------|----------|
| 2021-02-22 | 5.7% | 52.8% | 58.5% | UBSA |
| 2021-03-22 | 12.4% | 49.3% | 61.7% | UBSA |
| 2024-05-13 | 0% (merged) | 50–62% | 50–62% | UBSA |

### `06_oracle_predictive_engine.ipynb`

**Put-Call Parity Settlement Predictor**

| Parameter | Value |
|-----------|-------|
| **Total conversions identified** | 6,526 |
| **Energy storage baseline date** | 2024-05-10 |
| **Stored energy (E_stored)** | 1,199,198 contracts |
| **R_ratio breach date** | 2024-05-15 (R = 1.236, first day > 1.0) |
| **Peak R_ratio** | 2.845 (2024-05-23) |
| **DTE categories analyzed** | 0DTE, WEEKLY, MONTHLY, LEAPS |
| **Result files** | `round6_test_results.json`, `q5_dte_timescale.json` |

**Energy Budget Daily Progression:**

| Date | Short-Dated Vol | Total Vol | Cumulative Kinetic | R_ratio | Breached? |
|------|----------------|----------|--------------------|---------|---------:|
| 2024-05-13 | 461,259 | 573,040 | 461,259 | 0.385 | No |
| 2024-05-14 | 497,020 | 651,660 | 958,279 | 0.799 | No |
| 2024-05-15 | 523,913 | 682,547 | 1,482,192 | **1.236** | **Yes** |
| 2024-05-16 | 490,833 | 676,442 | 1,973,025 | 1.645 | Yes |
| 2024-05-17 | 869,949 | 968,210 | 2,842,974 | 2.371 | Yes |
| 2024-05-20 | 210,256 | 260,091 | 3,053,230 | 2.546 | Yes |
| 2024-05-21 | 128,226 | 176,375 | 3,181,456 | 2.653 | Yes |
| 2024-05-22 | 101,389 | 146,455 | 3,282,845 | 2.738 | Yes |
| 2024-05-23 | 129,406 | 216,379 | 3,412,251 | 2.845 | Yes |

**DTE Peak Lag by Ticker (days):**

| Ticker | 0DTE | WEEKLY | MONTHLY | LEAPS |
|--------|------|--------|---------|-------|
| GME | 10 | 2 | 1 | 20 |
| AAPL | 0 | 10 | 20 | 5 |
| TSLA | 20 | 20 | 5 | 5 |

### `07_ftd_spike_analysis.ipynb`

**FTD Volume & Notional Value Timeline**

| Parameter | Value |
|-----------|-------|
| **Data source** | SEC EDGAR CNS Fails-to-Deliver |
| **May 2024 file** | `sec_ftd_gme_may_june_2024.json` (65,518 bytes) |
| **January 2021 file** | `phase16c_jan2021_ftd_comparison.json` (15,829 bytes) |
| **Result file** | `round11_v4b_may2024_ftd.json` |

**GME FTD Daily Detail (May 2024):**

| Settlement Date | CUSIP | Quantity Fails | Price ($) | Notional Value |
|----------------|-------|---------------|-----------|----------------|
| 2024-05-01 | 36467W109 | 8,167 | 11.09 | $90,571.03 |
| 2024-05-02 | 36467W109 | 6,793 | 10.91 | $74,111.63 |
| 2024-05-03 | 36467W109 | 941 | 12.76 | $12,007.16 |
| 2024-05-06 | 36467W109 | 186,627 | 16.47 | $3,073,786.69 |
| 2024-05-07 | 36467W109 | 433,054 | 16.31 | $7,067,130.74 |
| 2024-05-08 | 36467W109 | 525,493 | — | — |
| 2024-05-09 | 36467W109 | 366,850 | — | — |
| 2024-05-10 | 36467W109 | 223,129 | — | — |
| 2024-05-13 | 36467W109 | 152,482 | — | — |
| 2024-05-14 | 36467W109 | 344,501 | — | — |
| 2024-05-15 | 36467W109 | 571,602 | — | — |

### `08_balance_sheet_attribution.ipynb`

**Entity Attribution & Form 13F Analysis**

| Parameter | Value |
|-----------|-------|
| **Filing type** | SEC 13F-HR (quarterly institutional holdings) |
| **Period** | Q1 2020 through Q2 2024 |
| **Target CUSIP** | `36467W109` (GME) |
| **Result files** | `stone3_13f_ctr.json`, `stone3_13f_gme_positions.json`, `si_map_2021_13f.json` |

**Entity CIKs (SEC EDGAR identifiers):**

| Entity | CIK | Role |
|--------|-----|------|
| Citadel Advisors LLC | `0001423053` | Non-ATS Internalizer #2 (56.2M GME, 22.8× surge) |
| Virtu Financial LLC | `0001571891` | Non-ATS Internalizer #1 (81.3M GME, 42.1× surge) |
| Susquehanna Intl Group | `0001446194` | Non-ATS Internalizer #3 via G1 (44.2M GME) |
| Jane Street Group LLC | `0001595097` | Non-ATS Internalizer #4 (38.7M GME, 44.4× surge) |

**Citadel GME 13F Positions (Pre vs Post May 2024):**

| Period | Calls | Puts | Shares | Call Value | Put Value |
|--------|-------|------|--------|-----------|-----------|
| Q1 2024 (pre-event) | 708,100 | 461,200 | 78,439 | $8,865,412,000 | $5,774,224,000 |
| Q2 2024 (post-event) | 3,511,800 | 5,733,500 | 1,909,379 | $86,706,342,000 | $141,560,115,000 |
| **Delta** | **+396%** | **+1,143%** | **+2,334%** | — | — |

### `09_microstructure_replication.ipynb`

**Microstructure Engine & Robustness Replication**

| Parameter | Value |
|-----------|-------|
| **Setup required** | Polygon + ThetaData API keys |
| **Offline fallback** | Yes, auto-loads from `results/` if APIs fail |
| **Data source** | Tick-level equity, 1-second NBBO quotes, Options SIP |
| **Coverage** | Panel ACF Scan, Lead-Lag, NMF Archaeology, Stacking Resonance |

### `10_forensic_replication.ipynb`

**Manipulation Forensics & Shadow Discovery Replication**

| Parameter | Value |
|-----------|-------|
| **Setup required** | Polygon + ThetaData API keys |
| **Offline fallback** | Yes, auto-loads from `results/` if APIs fail |
| **Data source** | Tick-level equity, Options SIP, FINRA TRF |
| **Coverage** | Shadow Hunter, Wash Trade Detection, Squeeze Mechanics |

---

## IV. FINRA Short Volume Data (January 2021)

Daily short volume for GME from `si_map_2021_finra.json`:

| Date | Short Volume | Short Exempt | Total Volume | Short Ratio % | Note |
|------|-------------|-------------|-------------|--------------|------|
| 2021-01-19 | 14,785,915 | 541,011 | 44,827,328 | 33.0% | Pre-event |
| 2021-01-22 | 33,257,918 | 686,860 | 97,123,046 | 34.2% | First spike |
| 2021-01-25 | 27,342,770 | 393,941 | 72,224,899 | 37.9% | |
| 2021-01-26 | 27,348,512 | 514,375 | 82,653,297 | 33.1% | |
| 2021-01-27 | 16,292,827 | 161,900 | 29,923,417 | 54.4% | **Peak day** |
| 2021-01-28 | 9,606,123 | 455,032 | 18,899,860 | 50.8% | Trading restrictions |
| 2021-01-29 | 8,814,229 | 527,920 | 16,327,706 | 54.0% | |
| 2021-02-01 | 6,982,444 | 364,890 | 12,820,226 | 54.5% | |
| 2021-02-02 | 16,358,136 | 1,073,011 | 29,733,410 | 55.0% | |
| 2021-02-05 | 19,063,724 | 1,106,467 | 34,566,363 | 55.2% | |
| 2021-02-08 | 6,404,809 | 82,425 | 11,348,581 | 56.4% | |

---

## V. Internalization Statistics (Round 3)

From `round3_test_results.json` — Options micro-lot to block ratios:

| Symbol | Block Count | Micro-Lot Count | Micro/Block Ratio | Floor % | Electronic % | N Dates |
|--------|------------|-----------------|-------------------|---------|-------------|---------|
| GME | 19,270 | 381,832 | 19.81 | 49.3% | 50.7% | 20 |
| MSFT | 21,095 | 1,437,431 | 68.14 | 27.7% | 72.3% | 20 |
| AAPL | 42,945 | 1,671,039 | 38.91 | 34.4% | 65.6% | 20 |
| SPY | 216,359 | 5,025,213 | 23.23 | 37.1% | 62.9% | 20 |

---

## VI. Pre-Computed Results Manifest

All 120 JSON files in `results/` are self-contained. Key categories:

| Category | File Pattern | Count | Description |
|----------|-------------|-------|-------------|
| Stacking Resonance | `stacking_resonance_*.json` | 8 | Per-ticker ACF analysis (GME, AAPL, TSLA, SPY, AMD, NVDA, SNAP, PLTR) |
| Round Tests | `round[N]_*.json` | ~25 | Sequential forensic battery results |
| Stone Tests | `stone[N]_*.json` | ~20 | EDGAR filings, 13F, X-17A-5 extractions |
| Phase Tests | `phase[N]_*.json` | ~10 | Lead-lag, shadow detection, forensic master |
| Frontier Tests | `frontier[N]_*.json` | 5 | NCSR, fails charges, 606, entity extraction |
| FTD Data | `sec_ftd_*.json` | 1 | Raw SEC FTD data (65,518 bytes) |
| Balance Sheets | `citadel_*.json`, `palafox_*.json` | ~10 | Multi-year entity financials |
| PFOF Analysis | `robinhood_606_*.json`, `pfof_crossref.json` | 5 | Rule 606 quarterly breakdowns |

---

## VII. System Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| jupyter | Latest |
| pandas | 1.5+ |
| matplotlib | 3.5+ |
| numpy | 1.20+ |

**Note:** Historical raw data polling (for re-running the original analysis scripts in `code/`) requires Polygon.io and ThetaData API keys. However, the `results/` cache provided in this repository guarantees fully autonomous offline verification of all notebook outputs.

---

## VIII. Falsification Criteria

This research explicitly assumes objective falsifiability. Any of the following would disprove core claims:

1. **Tape Fracture:** FINRA CAT data shows the $8.42 pre-market spread on 2024-05-17 resulted from disconnected retail routing latency rather than coordinated tiering.
2. **Put/Call Imbalance:** Unmasked OCC settlement registers demonstrate the 1,143% put increase in Citadel's Q2 2024 filing was strictly delta-neutral hedging for bona-fide market making.
3. **ETF Cannibalization:** GME/KOSS/XRT FTD correlation is explained by independent, unrelated settlement failures with no common counterparty.
4. **Swap Lineage:** Regulatory records prove the Archegos legacy ledger was NOT absorbed into UBS ATS prior to May 2024.
5. **Contingent Flags:** The 99.6% missing contingent trade flag rate for GME (vs. 62.2% for SPY) is shown to be a standard data reporting artifact rather than selective suppression.
