# Key Statistics

The 20 most important numbers from the research series. Each entry includes the exact value, what it means, its source, and—where applicable—the notebook or command that reproduces it.

---

## Settlement Mechanics

| # | Statistic | Value | What It Means | Source | Paper §
|:-:|-----------|:-----:|---------------|--------|:------:|
| 1 | Phantom OI enrichment at T+33 | **18.1×** | Settlement accommodation produces 18× more phantom options activity than random chance | SEC FTD + ThetaData OI | V §3.3 |
| 2 | T+33 echo hit rate (out-of-sample) | **100% (4/4)** | The T+33 echo model predicted all 2025 mega-FTD echoes before they occurred | ThetaData OI | V §3.4 |
| 3 | Settlement limbo as % of free float | **~18%** | Roughly 69.4M share-equivalents exist in settlement purgatory at any given time | SEC FTD | V §8.2 |
| 4 | Deep OTM put trades on control days | **0** | Zero phantom put activity on non-settlement dates—a structural boundary, not statistical | ThetaData trades | V §3.3 |
| 5 | Valve transfer post-splividend | **89%** | After July 2022, 89% of settlement accommodation shifted from options to opaque equity channels | ThetaData OI, Polygon TRF | V §5.2 |

## Resonance & Macrocycle

| # | Statistic | Value | What It Means | Source | Paper § |
|:-:|-----------|:-----:|---------------|--------|:------:|
| 6 | Settlement system Q-factor | **≈21** | A well-designed clearinghouse should have Q < 1. GME's system retains 86% amplitude per cycle | SEC FTD | VI §3 |
| 7 | Macrocycle period | **~630 business days** | A dominant 2.5-year oscillation at 13.3× noise appears in basket tickers, absent in controls | SEC FTD | VI §4 |
| 8 | ABM-emergent macrocycle strength | **44.5×** | An agent-based model using only SEC deadlines reproduced the macrocycle without it being specified | Custom ABM | IX §8.2 |

## Cross-Market Contagion

| # | Statistic | Value | What It Means | Source | Paper § |
|:-:|-----------|:-----:|---------------|--------|:------:|
| 9 | GME → Treasury Granger causality | **F = 9.25, p = 0.003** | GME FTDs predict Treasury settlement fails one week in advance; this is significant and unique | SEC FTD, NY Fed PDFTD | IX §3.4 |
| 10 | Other equities → Treasury causality | **Not significant** | None of 6 control equities (AMC, KOSS, AAPL, MSFT, TSLA, SPY) show the same result | SEC FTD, NY Fed PDFTD | IX §3.4 |
| 11 | Dec 2025 stress event magnitude | **GME: +4.2σ, Treasury: +4.0σ** | Both markets simultaneously produced extreme events separated by exactly one week | SEC FTD, NY Fed PDFTD | IX §3.5 |
| 12 | KOSS spectral amplification post-T+1 | **+3,039%** | When GME's settlement pressure dropped 96% under T+1, KOSS absorbed it at 30× amplification | SEC FTD | IX §2.3 |
| 13 | CSDR vs. Reg SHO penalty ratio | **5,714:1** | A 35-day fail costs $1,750 in Europe vs. ~$10M/day in the U.S. | ESMA, Reg SHO | IX §7.1 |

## Algorithmic Forensics

| # | Statistic | Value | What It Means | Source | Paper § |
|:-:|-----------|:-----:|---------------|--------|:------:|
| 14 | Jitter signature background rate | **0** | The `[100, 102, 100]` lot-size pattern does not occur on any non-catalyst day across 2,038 days | ThetaData OPRA | II §4.9 |
| 15 | ISG threshold evasion asymmetry | **7.5:1** at 499 vs. 500 | SPY trades cluster at exactly 499 contracts—one below the surveillance threshold | ThetaData OPRA | II §4.9 |
| 16 | DMA fingerprint coverage | **31 securities** | The same algorithmic footprint deploys across SPY, AAPL, TSLA, GME, AMC, and 26 others | ThetaData OPRA | VIII §2.4 |
| 17 | FTD coupling on constrained stocks | **t = +3.86, p < 0.001** | On borrow-constrained stocks (GME), FTDs significantly predict DMA activity the next day | ThetaData, SEC FTD | VIII §3.3 |
| 18 | FTD coupling on liquid stocks | **t = +0.38, p = 0.708** | On liquid stocks (SPY), the same algorithm shows zero FTD coupling | ThetaData, SEC FTD | VIII §3.3 |

## Enforcement & Penalties

| # | Statistic | Value | What It Means | Source | Paper § |
|:-:|-----------|:-----:|---------------|--------|:------:|
| 19 | Citadel Securities CAT fine | **$1M for 42.2B errors** | $0.0000236 per violation—fines are not a deterrent at any margin | FINRA AWC | III §4.2 |

---

*All statistics are derived from public data. See [VERIFICATION.md](VERIFICATION.md) for reproduction instructions.*
