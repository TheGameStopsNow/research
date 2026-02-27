# Options & Consequences: The Microstructure of Market Exploitation

This repository contains the data, replication code, and formal academic papers supporting the *Options & Consequences* research series.

This project reverse-engineers the execution mechanics, physical infrastructure, and macroeconomic funding of options-driven equity price displacement. By synchronizing nanosecond-resolution consolidated tape data (SIP), regulatory filings (SEC/FINRA), and physical hardware registries (FCC), this research maps a systemic regulatory exploit spanning U.S. equities and derivatives markets.

## 📄 The Research Papers

The formal findings are divided into a seven-paper series:

1. **[Paper I: Theory & ACF](papers/01_theory_options_hedging_microstructure.md)**
   *The Long Gamma Default, the Gamma Reynolds Number, and empirical measurement of options-driven equity dampening across a 37-ticker panel.*
2. **[Paper II: Evidence & Forensics](papers/02_forensic_trade_analysis.md)**
   *The 34-millisecond cross-asset liquidity vacuum, SEC Rule 605 odd-lot evasion, FINRA condition code fragmentation, and the $34M off-tape conversion.*
3. **[Paper III: Policy & Attribution](papers/03_policy_regulatory_implications.md)**
   *SEC Rule 10b-5 element mapping, the FINRA CAT subpoena roadmap, and the SEC FOIA "Zero-Day" log analysis.*
4. **[Paper IV: Infrastructure & Macro](papers/04_infrastructure_macro.md)**
   *The 17-Sigma basket proof (Empirical Shift Test), FCC 10GHz microwave networks, 5-year weather verification panel, DTCC RECAPS settlement cycles, and the Yen Carry Trade funding mechanism.*
5. **[Paper V: The Failure Accommodation Waterfall](papers/05_failure_accommodation_waterfall.md)**
   *The 15-node regulatory cascade from T+0 to T+45, FTD lifecycle mapping across 2,038 days, and the settlement waterfall that recycles delivery obligations.*
6. **[Paper VI: The Resonance Cavity](papers/06_resonance_and_cavity.md)**
   *Quality Factor Q ≈ 21, the 630-business-day macrocycle, standing wave analysis, and the system's energy storage capacity across years.*
7. **[Paper VII: Boundary Conditions](papers/09_boundary_conditions.md)**
   *T+1 spectral migration (KOSS +3,039%), equity-to-Treasury Granger causality (F=19.20), ETF substitution, CSDR cost arbitrage, BBBY zombie obligations, and the agent-based macrocycle model.*

## 📝 The Reddit Series

Four series of narrative distillations written for a general audience:

1. **The Strike Price Symphony** (3 parts) — Options microstructure forensics, real-time algorithm observation
2. **Options & Consequences** (4 parts) — Trade data, SEC filings, infrastructure, macro funding
3. **The Failure Waterfall** (4 parts) — Settlement lifecycle: the 15-node cascade, resonance cavity, macrocycle
4. **Boundary Conditions** (3 parts) — Cross-boundary overflow, sovereign contamination, coprime fix

## 🔬 Replication & Data

We believe in open-source, verifiable intelligence. Every statistical claim, chart, and latency measurement in these papers can be independently reproduced using the scripts provided.

*   `code/` — Python scripts for ACF generation, Lead-Lag correlation, NMF temporal archaeology, the Empirical Shift Test, FTD settlement analysis, Granger causality testing, spectral analysis, and the agent-based macrocycle model.
*   `data/` — Storm event datasets, systemic exhaust source documents, SEC FTD archives, and NY Fed Treasury FTD data.
*   `results/` — Pre-computed JSON and CSV outputs for rapid verification without requiring paid API subscriptions.

**For the complete file index, see [INDEX.md](INDEX.md).**


## ⚠️ Disclaimer

*This repository contains independent forensic research based entirely on publicly available data. The author is not a financial advisor, securities attorney, or affiliated with any regulatory body. This is not financial advice.*
