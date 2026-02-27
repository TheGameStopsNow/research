# GME Energy Pattern Analysis — Findings Report

**Generated:** 2026-02-22 12:06
**Data range:** 2024-05-01 → 2025-12-23
**Trading days:** 286

## Burst Detection

Detected **2** accumulate→discharge cycles:

| Burst | Peak Date | Peak Energy | Trough Date | Discharge % | Duration |
|-------|-----------|-------------|-------------|-------------|----------|
| 1 | 2024-06-03 | 48,480,551 | 2024-10-21 | 99.8% | 140d |
| 2 | 2024-12-18 | 20,318,742 | 2025-01-03 | 99.5% | 16d |

## Cadence Analysis

- **Mean interval:** 198 days
- **Intervals:** [198]
- **Escalation ratios:** ['0.42x']

## Tenor Migration

| Burst | 0DTE | 1-7d | 8-30d | 31-90d | 91-180d | 181-365d | 365d+ | Long (91d+) |
|-------|------|------|-------|--------|---------|----------|-------|-------------|
| 1 | 0.0% | 0.1% | 0.5% | 2.7% | 6.1% | 14.9% | 75.7% | **96.7%** |
| 2 | 0.0% | 0.2% | 2.3% | 8.7% | 12.8% | 25.1% | 50.7% | **88.7%** |

## Data Limitation Note

This analysis covers **May 2024 through December 2025** — the earliest available options roll data. It cannot directly test for pre-January 2021 buildup patterns because that data was not collected in this format.

To test for pre-2021 patterns, you would need to:
1. Fetch historical options data from ThetaData for 2020 (or earlier)
2. Compute the same DTE-weighted energy budget
3. Look for similar accumulation signatures in the 91-365d tenor bands

The LEAPS energy persistence noted in Part 1 ("during the dead years of 2022-2023, LEAPS energy persisted at the 181-365 day level") suggests there *was* a sustained loading pattern, but without tick-level options data for that period, we can only infer its existence from the ACF regime data and settlement-layer (FTD) evidence.
