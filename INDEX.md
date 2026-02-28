# Repository File Index

## Papers
- **[01_theory_options_hedging_microstructure.md](papers/01_theory_options_hedging_microstructure.md)**: Theoretical framework for "The Player Piano" mechanism, describing how options chain leverage creates forced buy-in pressure.
- **[02_forensic_trade_analysis.md](papers/02_forensic_trade_analysis.md)**: Forensic validation of the theory using trade-by-trade data from May/June 2024.
- **[03_policy_regulatory_implications.md](papers/03_policy_regulatory_implications.md)**: Policy analysis and recommendations for regulatory reform (CAT implementation, FTD thresholds).
- **[04_infrastructure_macro.md](papers/04_infrastructure_macro.md)**: Cross-domain corroboration — FCC microwave infrastructure, 5-year cross-date weather verification panel (p=0.009), exchange-split DiD (p=0.021), DTCC RECAPS settlement mechanics, Yen carry trade funding, SEC FOIA regulatory vacuum, and the 17-sigma Empirical Shift Test proving algorithmic basket execution.
- **[05_failure_accommodation_waterfall.md](papers/05_failure_accommodation_waterfall.md)**: The 15-node regulatory cascade from T+0 to T+45, FTD lifecycle mapping, and the settlement waterfall.
- **[06_resonance_and_cavity.md](papers/06_resonance_and_cavity.md)**: Quality Factor Q ≈ 21, the 630-business-day macrocycle, standing wave analysis, and energy storage capacity.
- **[07_shadow_ledger_offshore_crypto.md](papers/07_shadow_ledger_offshore_crypto.md)**: Offshore synthetic supply, derivative risk transfer, and collateral reflexivity.
- **[08_compliance_as_a_service.md](papers/08_compliance_as_a_service.md)**: Asynchronous complex orders, regulatory arbitrage, and compliance infrastructure.
- **[09_boundary_conditions.md](papers/09_boundary_conditions.md)**: T+1 spectral migration, Granger causality, ETF substitution, CSDR arbitrage, zombie obligations, and agent-based macrocycle model.

## Reddit Posts (`posts/`)
- **[part1_following_the_money.md](posts/part1_following_the_money.md)**: Trade data analysis — 263M shares, $12.13 tape fracture, odd-lot rule evasion.
- **[part2_the_paper_trail.md](posts/part2_the_paper_trail.md)**: SEC filings — $5.48B capital withdrawal, put disappearance, $35.2B swap validation, UK ISDA map.
- **[part3_systemic_exhaust.md](posts/part3_systemic_exhaust.md)**: Lateral systems — 17-sigma algorithmic basket proof (GME/BBBY), FCC microwave network, 5-year weather panel confirming infrastructure dependency with asymmetric geographic response, $57M synthetic share cleanup (Robinhood COSM), SEC FOIA zero-day.
- **[part4_macro_machine.md](posts/part4_macro_machine.md)**: Macro funding — CalPERS pension locates, Yen carry trade, DTCC RECAPS / Obligation Warehouse clock.

## Analysis Code (`code/analysis`)
- **`ftd_analysis.py`**: Analyzes SEC FTD data to identify settlement cycles and T+35 spikes.
- **`putcall_parity_predictor.py`**: Calculates theoretical settlement prices based on put-call parity arbitrage limits.
- **`basket_contagion.py`**: Tests correlation between meme-basket stocks (GME, KOSS, XRT).
- **`pfof_crossref.py`**: Cross-references PFOF routing data with off-exchange wholesale execution volumes.
- **`swap_ledger.py`**: Reconstructs potential swap exposure from reported portfolio data.
- **`rule606_sweep.py`**: Aggregates Rule 606 routing reports to map order flow destinations.
- **`edgar_verifier.py`**: Validates parsed financial data against official SEC EDGAR filings.
- **`nbbo_midquote_acf_test.py`**: Statistical test for bid-ask bounce autocorrelation in quote data.
- **`tick_correlation_test.py`**: Core Empirical Shift Test — measures sub-millisecond cross-ticker correlation and computes Z-Scores against shifted background noise.
- **`zombie_basket_rigorous.py`**: Rigorous zombie basket correlation test with controls (AAPL, SPY) and multiple tolerance windows.
- **`panel_expanded.py`**: Expanded 5-year cross-date NBBO spread widening panel (52 tickers × 111 storm events, 2018–2022).
- **`panel_crossdate.py`**: Initial 15-event cross-date panel (superseded by expanded version).

## Entity Analysis (`code/entity`)
- **`balance_sheet_analysis.py`**: Extracts and visualizes derivative exposure trends from annual reports.
- **`x17a5_disclosure_parser.py`**: Parses text disclosures from broker-dealer FOCUS reports (X-17A-5).
- **`13f_position_query.py`**: Queries institutional 13F filings for specific position changes.
- **`ats_attribution.py`**: Attributes dark pool volume to specific Alternative Trading Systems using FINRA data.
- **`broker_lineage.py`**: Traces the transfer of obligations through clearing firm mergers.

## Visualization (`code/visualization`)
- **`chart_combined.py`**: Generates the master multi-panel summary chart.
- **`chart_tape_fracture.py`**: Visualizes the $12.13 price discontinuity event.
- **`generate_balance_sheet_chart.py`**: Produces the 6-year derivative exposure trend chart.

## Results — Zombie Basket (`results/zombie_basket/`)
- **`Zombie_Basket_Analysis.md`**: Full analysis report — API limitations, Empirical Shift Test methodology, 17.70 Z-Score finding.
- **`basket_correlation_report.md`**: Detailed correlation report with visualizations.
- **CSV data**: `basket_correlation_results.csv`, `control_correlation_results.csv`, `rigorous_controls_1ms.csv`, `rigorous_controls_10ms.csv`, `zombie_basket_full_RTH.csv`, `tier4_correlation_results.csv`.

## Data — Systemic Exhaust (`data/systemic_exhaust/`)
- **SEC FOIA logs**: `sec_foia_raw_data_2021–2024.xlsx`, `sec_foia_log_2023.xlsx`
- **DTCC RECAPS**: `recaps_overlay_analysis.md`, `dw_data_2020_q4.xlsx`, `dw_data_2021_q1.xlsx`, `dw_data_2021_q2.xlsx`
- **FX / Carry Trade**: `usdjpy_2021q1.csv`, `usdjpy_2024_may_aug.csv`, `eurusd_spot_jan2021.csv`
- **Reports**: `systemic_exhaust_report.md`, `systemic_exhaust_level2_report.md`

## Testing (`code/testing`)
- **`test_battery_round06.py`** - **`test_battery_round10.py`**: Sequential forensic test batteries verifying key claims.
- **`test_mechanism.py`**: Validates the core mechanical assumptions of the options-hedging model.
- **`test_koss_natural_experiment.py`**: Specific validation for the KOSS micro-float control group.

## Weather Analysis (`data/weather/`)
- **`corridor_storms.json`**: 120 NOAA-verified corridor storm events (2018–2022), identified via Open-Meteo hourly precipitation at 9 waypoints.
- **`microwave_corridor_weather_events.md`**: NOAA Storm Events Database analysis — 69 severe weather dates along the Aurora–Mahwah corridor.
- **`Rain_Fade_CCF.md`**: Complete results summary — expanded panel (p=0.009), exchange-split DiD (p=0.021), confound identification, and methodology notes.
