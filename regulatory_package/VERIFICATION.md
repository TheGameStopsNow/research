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

No API keys are required for verification. All evidence notebooks load pre-computed results — you are verifying the analysis, not re-running data collection.

---

## Pre-Computed Results

The repository contains **113 pre-computed JSON result files** in `results/`. These files contain raw statistical outputs (test statistics, p-values, confidence intervals, raw data arrays) that the evidence notebooks load and render.

To verify that the pre-computed results match the published claims:

```bash
# List all result files
find results/ -name "*.json" | wc -l
# Expected: 113

# Verify file integrity (SHA-256 hashes are logged in git history)
git log --oneline results/ | head -20
```

---

## Evidence Notebooks

| Notebook | Verifies | Key Outputs |
|----------|----------|-------------|
| `notebooks/01_acf_panel.ipynb` | Paper I: ACF₁ dampening across 37 tickers | ACF panel figure, IPO transition stats |
| `notebooks/02_forensic_signatures.ipynb` | Paper II: Jitter, sonar, sweep signatures | Signature prevalence tables, lot-size distributions |
| `notebooks/03_attribution_roadmap.ipynb` | Paper III: 10b-5 element mapping | Element mapping table, CAT query specifications |
| `notebooks/05_waterfall_cascade.ipynb` | Paper V: T+33 echo, phantom OI enrichment | Enrichment ratios at each node, control-day comparison |
| `notebooks/06_resonance_cavity.ipynb` | Paper VI: Q-factor, macrocycle spectral peaks | Spectral power density plots, Q-factor calculation |
| `notebooks/07_offshore_crypto.ipynb` | Paper VII: FTX locate analysis, derivative spike | Balance sheet comparison, FTD spike timing |
| `notebooks/08_compliance_routing.ipynb` | Paper VIII: DMA fingerprint, FTD coupling | 31-ticker deployment table, regression coefficients |
| `notebooks/09_boundary_conditions.ipynb` | Paper IX: Granger causality, KOSS migration, BBBY zombie | F-statistics, spectral migration, zombie FTD timeline |
| `notebooks/09b_abm_simulation.ipynb` | Paper IX: Agent-based model emergence | Macrocycle emergence at 44.5× without specification |
| `notebooks/09c_csdr_arbitrage.ipynb` | Paper IX: Cross-border cost asymmetry | CSDR penalty math, EU fail rate correlation |

To run a notebook:
```bash
jupyter notebook notebooks/05_waterfall_cascade.ipynb
```

Each notebook loads from `results/` and renders all figures and tables. Running a cell-by-cell verification takes approximately 5–15 minutes per notebook.

---

## Verifying Specific Claims

### Claim: "18.1× phantom OI enrichment at T+33"

```bash
# Open the waterfall notebook
jupyter notebook notebooks/05_waterfall_cascade.ipynb
# Navigate to Section 3.3: "T+33 Echo Characterization"
# The enrichment ratio table shows the observed/expected ratio at each offset
# Result file: results/ftd_echo_enrichment.json
```

### Claim: "GME Granger-causes Treasury fails (F = 9.25, p = 0.003)"

```bash
# Open the boundary conditions notebook
jupyter notebook notebooks/09_boundary_conditions.ipynb
# Navigate to Section 3.4: "Granger Causality Panel"
# The Granger test table shows F-statistics and p-values for all 7 tickers
# Result file: results/granger_causality_panel.json
```

### Claim: "630-day macrocycle at 13.3× noise"

```bash
# Open the resonance cavity notebook
jupyter notebook notebooks/06_resonance_cavity.ipynb
# Navigate to Section 4: "Spectral Analysis"
# The Lomb-Scargle periodogram shows the dominant peak and its SNR
# Result file: results/spectral_peaks.json
```

### Claim: "Same DMA fingerprint deploys across 31 securities"

```bash
# Open the compliance routing notebook
jupyter notebook notebooks/08_compliance_routing.ipynb
# Navigate to Section 2.4: "Cross-Ticker Deployment"
# The deployment table shows the fingerprint presence across all 31 tickers
# Result file: results/dma_fingerprint_deployment.json
```

### Claim: "ABM produces 630-day cycle at 44.5× without specification"

```bash
# Open the ABM simulation notebook
jupyter notebook notebooks/09b_abm_simulation.ipynb
# Navigate to Section 8.2: "Emergent Macrocycle"
# The spectral analysis of ABM output shows the dominant period
# Result file: results/abm_spectral_output.json
```

### Claim: "42.2 billion CAT errors, $1 million fine"

This is a public regulatory record:
- **Source:** [FINRA Disciplinary Actions](https://www.finra.org/rules-guidance/oversight-enforcement/finra-disciplinary-actions), AWC No. 2020067253501
- **Date:** October 2024
- **Entity:** Citadel Securities LLC
- No notebook needed — verify against the public FINRA record directly

### Claim: "BBBY FTDs persist 824 days after CUSIP cancellation"

```bash
# Open the boundary conditions notebook
jupyter notebook notebooks/09_boundary_conditions.ipynb
# Navigate to Section 5.2: "Zombie Obligations"
# The FTD timeline shows 31 unique values through December 2025
# Result file: results/bbby_zombie_ftds.json
```

---

## Data Sources

All source data is publicly available:

| Data | Source | URL | Cost |
|------|--------|-----|:----:|
| SEC FTD data | SEC EDGAR | [sec.gov/data/foiadocsfailsdatahtm](https://www.sec.gov/data/foiadocsfailsdatahtm) | Free |
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

*This verification guide was last updated February 2026.*
