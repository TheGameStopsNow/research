# Regulatory Evidence Package

**Prepared by:** TheGameStopsNow
**Last Updated:** February 28, 2026
**Repository:** [github.com/TheGameStopsNow/research](https://github.com/TheGameStopsNow/research)

---

## What Is This?

This directory contains a curated evidence package from a nine-paper forensic analysis of U.S. equity settlement infrastructure. Everything in this package is derived from public data, built with open-source tools, and independently verifiable.

The package is designed for people in positions of authority — congressional staff, regulatory examiners, enforcement analysts, and legislative counsel — who need to quickly understand what was found and what actions are available.

---

## How to Use This Package

| If you are... | Start here | Time needed |
|:--------------|:-----------|:----------:|
| A **congressional staffer** looking for the bottom line | [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | 5 minutes |
| An **SEC or FINRA examiner** who wants ready-to-run queries | [SUBPOENA_QUERIES.md](SUBPOENA_QUERIES.md) | 15 minutes |
| A **legislative counsel** drafting oversight questions or legislation | [ACTION_ITEMS.md](ACTION_ITEMS.md) + [RULE_AMENDMENTS.md](RULE_AMENDMENTS.md) | 1 hour |
| A **technical reviewer** who wants to verify the statistical claims | [VERIFICATION.md](VERIFICATION.md) → [KEY_STATISTICS.md](KEY_STATISTICS.md) | 2-4 hours |
| Looking for a specific finding and its source | [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md) | As needed |

---

## Contents

| File | Description |
|------|-------------|
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | Two-page plain-language summary of findings for non-technical readers |
| [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md) | Every finding mapped to its paper, section, data source, and verification method |
| [ACTION_ITEMS.md](ACTION_ITEMS.md) | Five ranked regulatory actions with statutory references |
| [SUBPOENA_QUERIES.md](SUBPOENA_QUERIES.md) | Eight FINRA CAT queries in ready-to-execute format |
| [RULE_AMENDMENTS.md](RULE_AMENDMENTS.md) | Seven proposed rule amendments with statutory citations |
| [KEY_STATISTICS.md](KEY_STATISTICS.md) | The 20 most important numbers, each with its source and verification command |
| [VERIFICATION.md](VERIFICATION.md) | How to independently verify every claim using the public repository |

---

## The Research Papers

The underlying research is a nine-paper series:

| # | Title | Focus |
|:-:|-------|-------|
| I | [The Long Gamma Default](../papers/01_theory_options_hedging_microstructure.md) | Options market-making creates measurable price dampening across 37 tickers |
| II | [The Shadow Algorithm](../papers/02_forensic_trade_analysis.md) | Six forensic signatures consistent with deliberate exploitation |
| III | [Exploitable Infrastructure](../papers/03_policy_regulatory_implications.md) | 10b-5 element mapping, FINRA CAT attribution roadmap, proposed rule amendments |
| IV | [Structural Fragility](../papers/04_infrastructure_macro.md) | Physical infrastructure, settlement mechanics, macro funding channels |
| V | [Failure Accommodation Waterfall](../papers/05_failure_accommodation_waterfall.md) | 15-node settlement cascade, T+33 echo, valve transfer |
| VI | [The Resonance Cavity](../papers/06_resonance_and_cavity.md) | Standing waves, spectral fingerprints, 630-day macrocycle |
| VII | [The Shadow Ledger](../papers/07_shadow_ledger_offshore_crypto.md) | Offshore synthetic supply, derivative risk transfer, collateral reflexivity |
| VIII | [Compliance-as-a-Service](../papers/08_compliance_as_a_service.md) | DMA routing fingerprint, FTD-coupled trigger discrimination, BBBY natural experiment |
| IX | [Boundary Conditions](../papers/09_boundary_conditions.md) | Settlement contagion across tickers, Treasuries, borders; ABM emergence |

---

## Data Integrity

All analyses can be reproduced using the [public repository](https://github.com/TheGameStopsNow/research):

- **113** pre-computed result files cover all statistical tests
- **10** interactive evidence notebooks require **zero API keys** for verification
- Every figure, table, and statistical claim links to a specific script and dataset
- All source data is publicly available (SEC EDGAR, FINRA, NY Fed, Polygon.io, ThetaData)

---

*This package is maintained as a living document. Updates are tracked via git commit history.*

*Not financial advice. Forensic research using public data.*
