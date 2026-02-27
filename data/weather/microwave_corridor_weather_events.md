# Microwave Corridor Weather Event Dataset

**Source:** NOAA Storm Events Database (NCEI), bulk CSV download
**Corridor:** Aurora, IL → Mahwah, NJ (passing through Indiana, Ohio, Pennsylvania)
**States filtered:** Illinois, Indiana, Ohio, Pennsylvania, New Jersey
**Event types:** Thunderstorm Wind, Heavy Rain, Hail, Flash Flood, Ice Storm, Blizzard, Heavy Snow, Winter Storm, High Wind, Strong Wind, Tornado, Freezing Rain
**Time filter:** Trading hours only (09:00–16:00 ET)
**Years:** 2021–2022

---

## Purpose

This dataset identifies severe weather days along the McKay Brothers / Pierce Broadband
microwave corridor (Aurora, IL → Mahwah, NJ) that could be cross-referenced with
millisecond-level trading data (NYSE TAQ) to test whether the cross-ticker correlation
signature documented in Paper I degrades during weather events that disrupt microwave
transmission at 10–11 GHz. See Paper IV, §3.7 for the falsifiability hypothesis.

---

## Key GME Trading Dates: Weather Conditions

| Date | GME Event | Corridor Weather |
|------|-----------|-----------------|
| 2021-01-27 | Squeeze peak ($347.51 high) | **No severe weather** — clear corridor |
| 2021-01-28 | Trading restrictions imposed | **No severe weather** — clear corridor |
| 2021-02-24 | Second spike ($184.68) | **No severe weather** — clear corridor |
| 2021-02-25 | Rapid decline from spike | **No severe weather** — clear corridor |
| 2021-03-10 | Flash crash $348→$172 | **No severe weather** — clear corridor |
| 2021-06-02 | DFV exercises options | **No severe weather** — clear corridor |
| 2021-06-09 | ATM offering ($302→$282) | **No severe weather** — clear corridor |

> **Observation:** All seven key GME events occurred under clear-weather conditions,
> meaning the microwave network was operating at full capability. The algorithmic
> signature was not weather-impaired on any of these dates.

---

## Significant Weather Days (≥15 events, ≥2 corridor states): 69 dates

These dates should be tested against TAQ data for correlation signature perturbation.
Higher event counts and more states indicate broader corridor impact.

### Tier 1: Extreme (≥80 events, ≥3 states) — Highest probability of microwave disruption

| Date | Events | Weather Types | States |
|------|-------:|--------------|--------|
| 29-AUG-22 | 165 | Flash Flood, Hail, Thunderstorm Wind | ILLINOIS, INDIANA, OHIO, PENNSYLVANIA |
| 11-AUG-21 | 148 | Flash Flood, Hail, Thunderstorm Wind, Tornado | INDIANA, OHIO, PENNSYLVANIA |
| 21-JUN-21 | 114 | Hail, Thunderstorm Wind, Tornado | INDIANA, OHIO, PENNSYLVANIA |
| 26-MAY-21 | 108 | Hail, Thunderstorm Wind | NEW JERSEY, OHIO, PENNSYLVANIA |
| 21-MAY-22 | 104 | Hail, Thunderstorm Wind, Tornado | ILLINOIS, INDIANA, OHIO |
| 23-JUL-22 | 97 | Flash Flood, Hail, Thunderstorm Wind | ILLINOIS, INDIANA, OHIO, PENNSYLVANIA |
| 29-JUL-21 | 95 | Flash Flood, Hail, Thunderstorm Wind, Tornado | ILLINOIS, NEW JERSEY, OHIO, PENNSYLVANIA |
| 22-JUN-22 | 82 | Hail, Thunderstorm Wind | INDIANA, OHIO, PENNSYLVANIA |

### Tier 2: Severe (40–79 events, ≥3 states) — Probable microwave degradation

| Date | Events | Weather Types | States |
|------|-------:|--------------|--------|
| 12-AUG-21 | 79 | Flash Flood, Hail, Thunderstorm Wind | ILLINOIS, INDIANA, NEW JERSEY, OHIO, PENNSYLVANIA |
| 16-JUN-22 | 73 | Hail, Thunderstorm Wind | ILLINOIS, OHIO, PENNSYLVANIA |
| 02-FEB-22 | 71 | Heavy Snow, Winter Storm | ILLINOIS, INDIANA, OHIO |
| 08-JUL-21 | 68 | Flash Flood, Hail, Thunderstorm Wind | ILLINOIS, INDIANA, NEW JERSEY, OHIO, PENNSYLVANIA |
| 16-JUL-21 | 59 | Flash Flood, Thunderstorm Wind | ILLINOIS, INDIANA, NEW JERSEY, OHIO, PENNSYLVANIA |
| 15-FEB-21 | 59 | Heavy Snow, Ice Storm, Winter Storm | ILLINOIS, INDIANA, OHIO, PENNSYLVANIA |
| 03-MAY-22 | 59 | Hail, Thunderstorm Wind, Tornado | INDIANA, OHIO, PENNSYLVANIA |
| 20-MAY-22 | 59 | Hail, Thunderstorm Wind, Tornado | INDIANA, NEW JERSEY, PENNSYLVANIA |
| 12-JUL-21 | 52 | Flash Flood, Hail, Thunderstorm Wind, Tornado | ILLINOIS, NEW JERSEY, OHIO, PENNSYLVANIA |
| 03-AUG-22 | 49 | Flash Flood, Hail, Thunderstorm Wind | ILLINOIS, INDIANA, OHIO |
| 31-MAR-22 | 48 | Flash Flood, Hail, High Wind, Strong Wind, Thunderstorm Wind, Tornado | INDIANA, OHIO, PENNSYLVANIA |
| 11-DEC-21 | 47 | High Wind, Strong Wind, Thunderstorm Wind | INDIANA, OHIO, PENNSYLVANIA |
| 17-FEB-22 | 43 | Flash Flood, Heavy Snow, Strong Wind, Winter Storm | ILLINOIS, INDIANA, OHIO |
| 24-JUL-22 | 43 | Hail, Thunderstorm Wind | ILLINOIS, INDIANA, PENNSYLVANIA |
| 30-JUN-21 | 42 | Flash Flood, Hail, Thunderstorm Wind | ILLINOIS, INDIANA, OHIO, PENNSYLVANIA |
| 20-AUG-22 | 42 | Flash Flood, Hail, Thunderstorm Wind, Tornado | ILLINOIS, INDIANA, OHIO |
| 27-AUG-21 | 40 | Flash Flood, Thunderstorm Wind | INDIANA, NEW JERSEY, OHIO, PENNSYLVANIA |

### Tier 3: Moderate (15–39 events, ≥2 states) — Possible microwave degradation

| Date | Events | Weather Types | States |
|------|-------:|--------------|--------|
| 13-JUN-22 | 39 | Flash Flood, Hail, Thunderstorm Wind | ILLINOIS, INDIANA, OHIO |
| 11-OCT-21 | 38 | Hail, Heavy Rain, Strong Wind, Thunderstorm Wind, Tornado | ILLINOIS, INDIANA |
| 13-JUN-21 | 37 | Hail, Thunderstorm Wind | OHIO, PENNSYLVANIA |
| 06-JUL-22 | 37 | Hail, Thunderstorm Wind, Tornado | INDIANA, OHIO |
| 01-JUN-22 | 37 | Hail, Thunderstorm Wind | INDIANA, OHIO, PENNSYLVANIA |
| 01-JUL-22 | 37 | Hail, Thunderstorm Wind | OHIO, PENNSYLVANIA |
| 27-NOV-22 | 36 | Hail, Thunderstorm Wind | OHIO, PENNSYLVANIA |
| 08-JUN-21 | 34 | Flash Flood, Hail, Thunderstorm Wind, Tornado | INDIANA, NEW JERSEY, PENNSYLVANIA |
| 06-JUL-21 | 34 | Hail, Thunderstorm Wind | NEW JERSEY, PENNSYLVANIA |
| 01-SEP-21 | 32 | Flash Flood, Heavy Rain, Thunderstorm Wind, Tornado | NEW JERSEY, PENNSYLVANIA |
| 26-JUN-21 | 32 | Flash Flood, Thunderstorm Wind, Tornado | ILLINOIS, INDIANA |
| 30-APR-21 | 31 | High Wind | NEW JERSEY, PENNSYLVANIA |
| 03-FEB-22 | 29 | Ice Storm, Winter Storm | INDIANA, OHIO, PENNSYLVANIA |
| 30-JAN-21 | 28 | Heavy Snow, Winter Storm | ILLINOIS, INDIANA |
| 07-MAR-22 | 28 | Thunderstorm Wind | INDIANA, PENNSYLVANIA |
| 06-JUN-22 | 27 | Flash Flood, Hail, Thunderstorm Wind | ILLINOIS, INDIANA, OHIO |
| 21-APR-21 | 26 | Hail, Thunderstorm Wind | NEW JERSEY, PENNSYLVANIA |
| 01-JUL-21 | 26 | Flash Flood, Thunderstorm Wind | INDIANA, NEW JERSEY, PENNSYLVANIA |
| 19-MAY-22 | 26 | Hail, Thunderstorm Wind, Tornado | ILLINOIS, INDIANA |
| 25-AUG-21 | 23 | Flash Flood, Hail, Thunderstorm Wind, Tornado | ILLINOIS, INDIANA, OHIO, PENNSYLVANIA |
| 27-MAY-22 | 22 | Flash Flood, Thunderstorm Wind, Tornado | INDIANA, NEW JERSEY, PENNSYLVANIA |
| 23-MAR-22 | 21 | Hail, Thunderstorm Wind, Tornado | INDIANA, OHIO |
| 12-JUN-21 | 20 | Hail, Heavy Rain, Thunderstorm Wind | ILLINOIS, INDIANA |
| 29-AUG-21 | 20 | Flash Flood, Thunderstorm Wind | ILLINOIS, INDIANA, NEW JERSEY, OHIO, PENNSYLVANIA |
| 12-JUL-22 | 20 | Hail, Thunderstorm Wind | NEW JERSEY, PENNSYLVANIA |
| 22-AUG-22 | 19 | Flash Flood, Hail, Heavy Rain, Thunderstorm Wind | NEW JERSEY, PENNSYLVANIA |
| 04-AUG-22 | 19 | Flash Flood, Hail, Thunderstorm Wind | INDIANA, OHIO, PENNSYLVANIA |
| 18-JUN-21 | 17 | Hail, Thunderstorm Wind, Tornado | ILLINOIS, INDIANA, OHIO |
| 26-AUG-21 | 16 | Flash Flood, Thunderstorm Wind | ILLINOIS, OHIO, PENNSYLVANIA |
| 25-APR-22 | 16 | Thunderstorm Wind, Tornado | OHIO, PENNSYLVANIA |
| 10-AUG-21 | 15 | Thunderstorm Wind | ILLINOIS, NEW JERSEY, OHIO, PENNSYLVANIA |
| 25-MAR-22 | 15 | High Wind, Thunderstorm Wind | ILLINOIS, INDIANA |

### Winter Events of Special Interest (Ice/Snow — different attenuation profile)

| Date | Events | Weather Types | States |
|------|-------:|--------------|--------|
| 22-DEC-22 | 91 | Blizzard, Winter Storm | ILLINOIS, INDIANA |
| 02-FEB-22 | 71 | Heavy Snow, Winter Storm | ILLINOIS, INDIANA, OHIO |
| 15-FEB-21 | 59 | Heavy Snow, Ice Storm, Winter Storm | ILLINOIS, INDIANA, OHIO, PENNSYLVANIA |
| 16-JAN-22 | 58 | Heavy Snow, Winter Storm | OHIO, PENNSYLVANIA |
| 17-FEB-22 | 43 | Flash Flood, Heavy Snow, Strong Wind, Winter Storm | ILLINOIS, INDIANA, OHIO |
| 03-FEB-22 | 29 | Ice Storm, Winter Storm | INDIANA, OHIO, PENNSYLVANIA |
| 30-JAN-21 | 28 | Heavy Snow, Winter Storm | ILLINOIS, INDIANA |

---

## Methodology Notes

1. **Data source:** NOAA NCEI Storm Events Database, bulk CSV files
   - 2021: `StormEvents_details-ftp_v1.0_d2021_c20250520.csv.gz` (61,389 total events)
   - 2022: `StormEvents_details-ftp_v1.0_d2022_c20250721.csv.gz`
2. **Corridor definition:** Events in IL, IN, OH, PA, NJ (states traversed by the Aurora→Mahwah microwave path)
3. **Time filter:** Events beginning between 09:00 and 16:00 ET (US equity trading hours)
4. **Significance threshold:** ≥15 NOAA-reported events during trading hours, spanning ≥2 corridor states
5. **10–11 GHz sensitivity:** Rain attenuation at 10 GHz is approximately 0.01 dB/km for light rain, 0.1 dB/km for moderate rain, and >1 dB/km for heavy rain (ITU-R P.838). Over 85 relay hops, even moderate rain along any segment can degrade link quality.
6. **Limitation:** NOAA Storm Events records severe weather *reports*, not continuous precipitation data. NEXRAD radar archives would provide more precise corridor-aligned precipitation intensity.

---

## Tick-Level Cross-Correlation Analysis: Weather vs. Clear Days

Using the Polygon.io trades API, I downloaded millisecond-resolution tick data for GME and KOSS on 14 severe weather dates and 16 clear-weather control dates spanning three eras (2019, 2020, 2023). I then ran `merge_asof` at 8 tolerance levels (10ms–1000ms) to test whether the cross-ticker correlation structure degrades during corridor weather events.

### Date Selection

- **Weather dates (N=14):** Top NOAA Storm Events days (≥20 events, ≥2 corridor states, weekdays only) from 2019 (1 date), 2020 (5 dates), and 2023 (8 dates)
- **Clear dates (N=16):** Days with zero NOAA corridor events, not within ±2 days of any weather event, from 2019 (3 dates), 2020 (3 dates), and 2023 (10 dates)
- **Minimum threshold:** ≥30 KOSS trades during regular trading hours (eliminates ultra-sparse 2019 dates)

### Results: Grand Summary (All Eras Combined)

| Tolerance | Weather Avg (N=14) | Clear Avg (N=16) | Difference |
|----------:|-------------------:|------------------:|-----------:|
| 10ms | 1.1% | 2.1% | **-0.9%** |
| 20ms | 2.3% | 3.3% | **-1.0%** |
| 50ms | 5.5% | 7.3% | **-1.8%** |
| 100ms | 10.4% | 12.0% | **-1.7%** |
| 150ms | 14.4% | 15.2% | -0.8% |
| 200ms | 16.7% | 19.3% | **-2.6%** |
| 500ms | 32.3% | 34.0% | -1.6% |
| 1000ms | 50.6% | 56.8% | **-6.2%** |

**Permutation tests (10,000 simulations):**
- 10ms: p = 0.097 (approaching significance)
- 100ms: p = 0.73 (not significant)

### Interpretation

The initial N=3 pilot showed a suggestive "window widening" pattern (lower at tight tolerances, higher at medium). However, the scaled N=14 vs N=16 analysis reveals a different signal: **uniform coherence degradation across all tolerances.** Weather days show consistently lower match rates at every tested window, with the effect growing at wider tolerances (-6.2% at 1000ms).

This pattern is consistent with:
1. **Broadband correlation disruption** — not a simple latency shift, but a general reduction in cross-ticker synchronization during weather events
2. **Possible intermittent outages** — brief complete link drops (rather than steady fiber fallback) would reduce correlation at all windows
3. **The 10ms p-value of 0.097** is suggestive but not definitive — a larger sample could potentially push this below 0.05

### Limitations

1. **KOSS liquidity:** KOSS trades 150-1,400 times/day during this period (vs 20,000-80,000 for GME). This low tock count adds significant noise.
2. **Pre-2021 sparsity:** Only 1 usable weather date from 2019 (KOSS traded <30 times on most days)
3. **Confounders:** Weather may independently affect market activity regardless of microwave infrastructure
4. **Sample size:** N=14 vs N=16 is still modest; the effect sizes are small relative to variance

### Daily Price Cross-Reference: Null Result

I also tested daily GME price moves (T+1 to T+3) after weather events across 2021-2022 and 2023-2024. **No significant effect was found at daily resolution.** GME's baseline volatility (75% of all trading days showed >5% moves in the 2021-2022 era; 82% showed >3% in 2023-2024) overwhelms any weather signal. This confirms that the proper test for the infrastructure hypothesis requires tick-level data, not daily candles.

### Recommended Next Steps

1. **Expand KOSS with AMC:** AMC trades much more frequently, providing a higher-fidelity correlation partner
2. **Focus on Tier 1 events only:** The 8 dates with ≥80 NOAA events are most likely to produce microwave disruption
3. **Hour-by-hour analysis:** Weather events have specific onset/peak times — comparing correlation within the storm window vs. pre-storm on the same day would control for date-level confounders
4. **Test against SPY↔QQQ:** As a negative control, SPY↔QQQ should NOT show weather-dependent correlation changes (both trade on co-located exchanges)