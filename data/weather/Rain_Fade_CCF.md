# Microwave Rain-Fade Attenuation: Complete Results

## ✅ Expanded Cross-Date Panel — SIGNIFICANT (p = 0.009)

**4,784 observations** (52 tickers × 111 NOAA-verified storm dates, 2018-2022).
Same ticker, same hour, storm day vs matched clear day (±1-3 trading days).

### Primary Results

| Test | Value | p-value |
| ---- | ----- | ------- |
| Mean shift | **+0.144 bps** | — |
| Median shift | +0.002 bps | — |
| Widened | 2505/4784 (52%) | — |
| **Paired t-test** | t = 2.603 | **0.0093** ★ |
| **Wilcoxon** | — | **1.28 × 10⁻⁴** ★ |
| **Sign test** | — | **2.41 × 10⁻⁴** ★ |
| Spearman ρ (shift ~ precip) | ρ = 0.063 | **1.23 × 10⁻⁵** ★ |

### By Severity

| Severity | N | Mean Shift | Widened | p |
| -------- | --- | ---------- | ------- | --- |
| MODERATE (≥1mm) | 1,475 | +0.147 bps | 838 (57%) | 0.190 |
| LIGHT (<1mm) | 3,309 | +0.142 bps | 1,667 (50%) | **0.022** ★ |

### Dose-Response

Linear regression `shift ~ precipitation_mm`: β = −0.037, p = 0.702 (null). No monotonic relationship between precipitation intensity and spread widening magnitude. The Spearman rank correlation (ρ = 0.063) is significant but driven by volume, not a dose gradient.

---

## Methodology

- **Weather data**: Open-Meteo archive API, 9 corridor points (Carteret NJ → Aurora IL)
- **Storm threshold**: ≥4/9 points wet AND max ≥ 2mm, OR median ≥ 0.5mm
- **Control dates**: Nearest non-storm trading day ±1-5 days
- **NBBO data**: Polygon v3 tick-level quotes, 1-minute median spreads
- **Time range**: 2018-01-01 to 2022-12-31 (5 years, 120 corridor storm events, 111 with data)
- **Downloads**: 10 concurrent threads, single-page (50K quotes) per hour

---

## Prior Results

### 15-Event Cross-Date Panel (Superseded)

701 observations, p = 0.230 (not significant). Underpowered with only 15 events.

### Within-Day Panel (INVALIDATED)

Raw p = 2.84e-9 was time-of-day artifact. Residual after intraday normalization: p = 0.775.

### OI Regression (NULL)

Options contract density does not predict cross-date spread widening (β = −0.0003, p = 0.795).

### 3-Ticker Exchange-Split DiD

CHI vs NJ within same hour: t = −2.418, p = 0.021 ★. CHI tightens during storms (reduced adverse selection per Shkilko §3.1).

---

## Scripts

| Script | Purpose |
| ------ | ------- |
| `panel_expanded.py` | **Expanded cross-date panel** (2018-2022, 111 events) |
| `panel_crossdate.py` | Cross-date panel (15 events, superseded) |
| `panel_spread_50.py` | Within-day panel (confounded) |
| `corridor_storms.json` | 120 NOAA-verified storm events |
| `crossdate_results/oi_regression.json` | OI regression data |
