# GME Full-Range Energy Pattern Analysis — Complete Data Findings

**Generated:** 2026-02-22
**Data range:** 2018-01-02 → 2026-02-11
**Trading days:** 2,038
**Data source:** ThetaData `part-0.parquet` (DTE 0–53) + `part-leaps.parquet` (DTE 61–400) merged

> **Note:** Previous versions of this analysis only read `part-0.parquet`, which contained weekly-chain trades with max DTE ~53 days. The `part-leaps.parquet` files (produced by `backfill_leaps.py`) contain monthly opex and LEAPS trades (DTE 61–400). With both files merged, all 7 tenor buckets now have full coverage across the entire 2018–2026 range.

## Tenor Distribution (Full 8-Year Dataset)

| Tenor | % of Trades | % of Hedging Energy |
| ----- | :---------: | :-----------------: |
| 0DTE | 10.8% | 0.0% |
| 1-7d | 47.5% | 4.7% |
| 8-30d | 24.3% | 11.5% |
| 31-90d | 8.7% | 13.0% |
| 91-180d | 2.9% | 9.7% |
| 181-365d | 1.9% | 12.8% |
| 365d+ | 3.9% | 48.1% |

**91d+ combined:** 8.7% of trades → **70.7% of hedging energy**

## Burst Detection

Detected **11** accumulate→discharge cycles:

| # | Peak Date | Peak Energy | Trough Date | Discharge | Duration |
| - | --------- | ----------- | ----------- | --------- | -------- |
| 1 | 2020-10-05 | 734,682 | 2020-11-06 | 75.6% | 32d |
| 2 | 2021-01-28 | 5,555,228 | 2021-02-22 | 55.2% | 25d |
| 3 | 2021-06-09 | 1,673,941 | 2021-08-09 | 76.9% | 61d |
| 4 | 2022-06-08 | 1,292,445 | 2022-06-27 | 27.8% | 19d |
| 5 | 2023-10-09 | 939,873 | 2023-11-06 | 82.3% | 28d |
| 6 | 2024-05-28 | 5,299,154 | 2024-08-22 | 86.0% | 86d |
| 7 | 2024-11-04 | 2,272,620 | 2024-12-03 | 50.7% | 29d |
| 8 | 2025-04-07 | 3,443,623 | 2025-05-07 | 59.2% | 30d |
| 9 | 2025-06-26 | 3,311,528 | 2025-08-06 | 80.7% | 41d |
| 10 | 2025-09-19 | 1,618,230 | 2025-11-07 | 56.9% | 49d |
| 11 | 2026-01-21 | 2,508,977 | N/A | N/A | N/A |

## Pre-Event Buildup Comparison

| Metric | Pre-Jan 2021 | Pre-Jun 2024 |
| ------ | ------------ | ------------ |
| Days analyzed | 124 | 124 |
| Energy slope | +26,813/day | +32,831/day |
| Peak energy | 15,486,884 | 11,839,814 |
| Long tenor start | 63% | 50% |
| Long tenor end | 48% | 83% |
| Long tenor shift | −15% | +33% |

## January 28, 2021 — Tenor Activation

5 out of 7 tenor buckets had non-zero trades on the sneeze date:

| Bucket | Trades | Energy |
| ------ | -----: | -----: |
| 0DTE | 0 | 0 |
| 1-7d | 75,154 | 300,616 |
| 8-30d | 63,002 | 1,197,038 |
| 31-90d | 28,011 | 1,680,660 |
| 91-180d | 6,425 | 867,375 |
| 181-365d | 8,310 | 2,243,700 |
| 365d+ | 0 | 0 |

0DTE had no same-day expiring chain. 365d+ LEAPS saw no trades on that specific date. Five consecutive tenor bands (1-7d through 181-365d) firing simultaneously remains unique in the dataset.

## 2022–2023 LEAPS Persistence

During the "dead years," long-dated tenors maintained near-continuous activity:

- 91-180d: 496/501 non-zero days (99%)
- 181-365d: 499/501 non-zero days (100%)
- 365d+: 481/501 non-zero days (96%)

## Generated Charts

- `full_energy_budget.png` — Stacked area chart of energy by tenor (all 7 buckets)
- `full_energy_heatmap.png` — Density heatmap across tenors and time
- `full_storage_release.png` — Accumulation/discharge dynamics
- `long_tenor_timeseries.png` — Long-dated tenor energy share (30-day rolling)
- `pre_event_comparison.png` — Side-by-side pre-event buildup patterns
- `energy_flow_field.png` — Gradient quiver plot of energy migration (saved to review_package and posts)
