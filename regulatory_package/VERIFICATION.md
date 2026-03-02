# Verification Guide

How to independently verify every claim in this research package using the public repository.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/TheGameStopsNow/research.git
cd research

# Install Python dependencies
pip install -r requirements.txt
```

No API keys are required for verification. All analysis scripts load pre-computed results — you are verifying the analysis, not re-running data collection.

---

## Pre-Computed Results

The repository contains pre-computed JSON result files across two directories:

- **`results/`** — Top-level results (113+ files): Granger causality panels, resonance analysis, contagion maps, balance sheet extractions, and round-by-round test outputs.
- **`code/analysis/results/`** — Analysis pipeline outputs (9 files): cavity resonance, deep OTM puts, origin cascade, settlement architecture, echo validation, and splividend calendar data.

To verify that the pre-computed results match the published claims:

```bash
# Count all result files
find results/ -name "*.json" | wc -l
find code/analysis/results/ -name "*.json" | wc -l

# Verify file integrity (SHA-256 hashes are logged in git history)
git log --oneline results/ | head -20
```

---

## Analysis Scripts

The analysis pipeline is organized in `code/analysis/ftd_research/` as numbered Python scripts. Each script can be run independently to reproduce specific findings:

| Script | Paper | Verifies |
|--------|-------|----------|
| `01_load_ftd_data.py` | I–IX | SEC FTD data loading and preprocessing |
| `02_xrt_ftd_rally_signal.py` | IV, IX | XRT FTD substitution signal detection |
| `04_t33_echo_cascade.py` | V, IX | T+33 echo cascade timing and enrichment |
| `05_recaps_ftd_convergence.py` | V, VI | RECAPS cycle convergence analysis |
| `08_cross_ticker_sync.py` | VI, IX | Cross-ticker spectral synchronization |
| `12_splividend_calendar.py` | IX | Splividend corporate action regime changes |
| `14_deep_otm_puts.py` | VIII | Deep OTM put cross-ticker fingerprint |
| `15_settlement_validation.py` | V | Settlement waterfall validation |
| `17_settlement_architecture.py` | V, VI | Full settlement architecture model |
| `19_polygon_forensics.py` | VIII | Polygon tick-level trade forensics |

Additional Paper IX analysis scripts are referenced in the paper's Appendix B:

| Script | Avenue | Description |
|--------|--------|-------------|
| `t1_spectral_comparison.py` | 5 | Pre/post T+1 spectral analysis |
| `treasury_equity_overlay_v2.py` | 2 | Treasury-equity correlation and lag analysis |
| `granger_causality.py` | 2 | Formal Granger causality test with ADF stationarity check |
| `granger_panel_expanded.py` | 2 | Expanded 15,916-ticker Granger panel |
| `etf_heartbeat_analysis.py` | 3 | XRT/GME substitution, T+33 echo, event study |
| `cusip_mutation_analysis.py` | 4 | Corporate action regime changes |
| `dma_cross_ticker_sync.py` | 1 | DMA fingerprint cross-ticker synchronization test |
| `csdr_analysis.py` | 6 | Cross-border CSDR settlement arbitrage |
| `abm_prototype.py` | 7 | Agent-based model with spectral validation |

To run a script:
```bash
python code/analysis/ftd_research/04_t33_echo_cascade.py
```

---

## Verifying Specific Claims

### Claim: "18.1× phantom OI enrichment at T+33"

```bash
# Run the T+33 echo cascade analysis
python code/analysis/ftd_research/04_t33_echo_cascade.py
# Result file: code/analysis/results/t33_echo_cascade.json
# Cross-reference with: results/ftd_echo_enrichment.json (if present)
```

### Claim: "GME Granger-causes Treasury fails (F = 9.25, p = 0.003)"

```bash
# Result file: results/granger_causality_panel.json (if present)
# Or run the Granger causality script referenced in Paper IX Appendix B
# Cross-reference: results/contagion_GME.json
```

### Claim: "630-day macrocycle at 13.3× noise"

```bash
# Result file: code/analysis/results/cavity_resonance.json
# This contains the spectral power density peaks and Q-factor calculation
cat code/analysis/results/cavity_resonance.json | python -m json.tool | head -50
```

### Claim: "Same DMA fingerprint deploys across 31 securities"

```bash
# Run the deep OTM puts analysis for cross-ticker fingerprint
python code/analysis/ftd_research/14_deep_otm_puts.py
# Result file: code/analysis/results/deep_otm_puts.json
```

### Claim: "ABM produces 630-day cycle at 44.5× without specification"

```bash
# Run the ABM prototype script referenced in Paper IX Appendix B
# The spectral analysis of ABM output shows the dominant period
# Result file: results/abm_spectral_output.json (if present)
```

### Claim: "42.2 billion CAT errors, $1 million fine"

This is a public regulatory record:
- **Source:** [FINRA Disciplinary Actions](https://www.finra.org/rules-guidance/oversight-enforcement/finra-disciplinary-actions), AWC No. 2020067253501
- **Date:** October 2024
- **Entity:** Citadel Securities LLC
- Verify against the public FINRA record directly

---

## Data Sources

All source data is publicly available:

| Data | Source | URL | Cost |
|------|--------|-----|:----:|
| SEC FTD data | SEC EDGAR | [sec.gov/data-research/sec-markets-data/fails-deliver-data](https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data) | Free |
| Treasury settlement fails | NY Fed | [newyorkfed.org/data-and-statistics/data-visualization/primary-dealer-fails](https://www.newyorkfed.org/data-and-statistics/data-visualization/primary-dealer-fails) | Free |
| Options/equity trades | ThetaData | [thetadata.net](https://www.thetadata.net) | Subscription |
| FINRA TRF/ADF data | FINRA | [finra.org/finra-data/browse-catalog](https://www.finra.org/finra-data/browse-catalog) | Free |
| Equity trades | Polygon.io | [polygon.io](https://polygon.io) | Subscription |
| ESMA settlement data | ESMA | [esma.europa.eu/data-systematic-internaliser-calculations](https://www.esma.europa.eu/data-systematic-internaliser-calculations) | Free |
| Corporate filings (German) | Bundesanzeiger | [bundesanzeiger.de](https://www.bundesanzeiger.de) | Free |
| FTX bankruptcy filings | Kroll | [cases.ra.kroll.com/FTX](https://cases.ra.kroll.com/FTX) | Free |
| FINRA disciplinary actions | FINRA | [finra.org/rules-guidance/oversight-enforcement](https://www.finra.org/rules-guidance/oversight-enforcement) | Free |
| OFR repo data | OFR | [financialresearch.gov/short-term-funding-monitor](https://www.financialresearch.gov/short-term-funding-monitor) | Free |
| FDIC Call Reports | FDIC | [fdic.gov/analysis/quarterly-banking-profile](https://www.fdic.gov/analysis/quarterly-banking-profile) | Free |
| SEC 13F filings | SEC EDGAR | [sec.gov/cgi-bin/browse-edgar](https://www.sec.gov/cgi-bin/browse-edgar) | Free |
| OCC derivatives report | OCC | [occ.treas.gov/publications-and-resources/publications/quarterly-report-on-bank-trading-and-derivatives-activities](https://www.occ.treas.gov/publications-and-resources/publications/quarterly-report-on-bank-trading-and-derivatives-activities) | Free |

ThetaData and Polygon.io are subscription services. However, the pre-computed result files in the repository contain all derived statistics, so no subscription is needed to **verify the analysis** — only to **re-collect the raw data from scratch**.

---

## Reporting Issues

If you find an error in any claim, statistical test, or data source reference:

1. Open an issue on the [GitHub repository](https://github.com/TheGameStopsNow/research/issues)
2. Reference the specific finding number from [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md)
3. Include the corrected calculation or counter-evidence

All corrections will be acknowledged and incorporated.

---

*This verification guide was last updated March 2026.*
