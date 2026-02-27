#!/usr/bin/env python3
"""
Phase 7: Testing the settlement model's Predictions
=================================================
Three testable hypotheses from the settlement model analysis:

  1. FAST WATERFALL: T+10 signal = T+1 + T+4 + T+5 decomposition
  2. XRT CROSS-CORRELATION: Unexplained OI stress explained by ETF FTDs
  3. T+0 MECHANICAL AWARENESS: Stress systematically precedes FTD filing
  4. PRESSURE GAUGE FORENSICS: OI surges = locate generation for new shorts
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "ftd"
OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
PRICE_CSV = DATA_DIR / "gme_daily_price.csv"
OUT_DIR = Path(__file__).resolve().parents[2] / "temp" / "settlement_decoder"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_ftd(ticker):
    path = DATA_DIR / f"{ticker}_ftd.csv"
    if path.exists():
        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        return df.dropna(subset=['date', 'quantity']).sort_values('date')
    return pd.DataFrame()


def load_price():
    df = pd.read_csv(PRICE_CSV)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').set_index('date')


def build_stress_series():
    strike_ts = defaultdict(dict)
    for f in sorted(OI_DIR.glob("oi_*.parquet")):
        date_str = f.stem.replace("oi_", "")
        try:
            df = pd.read_parquet(f)
            deep = df[(df["right"] == "PUT") & (df["strike"] <= 15)]
            for _, row in deep.iterrows():
                strike_ts[float(row["strike"])][date_str] = int(row["open_interest"])
        except Exception:
            continue

    oi_matrix = pd.DataFrame(strike_ts).fillna(0)
    oi_matrix.index = pd.to_datetime(oi_matrix.index, format="%Y%m%d")
    oi_matrix = oi_matrix.sort_index()
    baseline = oi_matrix.rolling(20, min_periods=5).median()
    rolling_std = oi_matrix.rolling(20, min_periods=5).std()
    z_scores = (oi_matrix - baseline) / rolling_std.replace(0, np.nan)
    z_scores = z_scores.fillna(0)
    daily_stress = z_scores.abs().sum(axis=1)
    daily_stress.name = "stress"
    total_oi = oi_matrix.sum(axis=1)
    return daily_stress, total_oi, oi_matrix


def write_md(name, content):
    path = OUT_DIR / name
    with open(path, "w") as f:
        f.write(content)
    print(f"  → {path}")


# ═══════════════════════════════════════════════════════════════════
# TEST 1: FAST WATERFALL DECOMPOSITION
# ═══════════════════════════════════════════════════════════════════
def test_fast_waterfall(daily_stress, price_df, gme_ftd):
    """
    settlement model hypothesis: T+10 = T+1 (trade) + T+4 (BFMM) + T+5 (threshold).
    Test: does the T+10 signal decompose into sub-components at T+1, T+4-5, T+6?
    """
    print("\n" + "=" * 70)
    print("  TEST 1: FAST WATERFALL DECOMPOSITION")
    print("=" * 70)

    # Restrict to quiet era (2023-2026) where T+10 is the dominant signal
    merged = pd.DataFrame({'stress': daily_stress}).join(price_df[['gme_close']], how='inner')
    quiet = merged[merged.index >= '2023-01-01'].copy()

    for h in range(1, 46):
        quiet[f'fwd_{h}'] = quiet['gme_close'].shift(-h) / quiet['gme_close'] - 1

    try:
        quiet['stress_q'] = pd.qcut(quiet['stress'], q=5,
                                     labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'],
                                     duplicates='drop')
    except Exception:
        # Handle ties
        quiet['stress_q'] = pd.cut(quiet['stress'], bins=5,
                                    labels=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])

    md = "# Fast Waterfall Decomposition (2023-2026)\n\n"
    md += "**Hypothesis**: T+10 signal = T+1 (settlement) + T+4 (BFMM) + T+5 (threshold)\n\n"
    md += "Testing whether the stress→returns signal has sub-peaks at T+1, T+4-5, T+6.\n\n"

    md += "## Day-by-Day Signal Decomposition\n\n"
    md += "| Horizon | Q1 (quiet) | Q5 (loud) | Spread | t-stat | Waterfall Node |\n"
    md += "|---------|:--:|:--:|:--:|:--:|---|\n"

    nodes = {1: "T+1 Settlement", 2: "T+2 (old settlement)", 3: "CNS Netting",
             4: "BFMM Close-out", 5: "Threshold Trigger", 6: "Post-BFMM",
             7: "Week 1 end", 8: "", 9: "", 10: "**FAST WATERFALL**",
             13: "Reg SHO", 15: "Phantom Peak", 20: "", 25: "", 30: "",
             33: "Echo Window", 35: "Forced Buy-in", 40: "Terminal", 45: "Boundary"}

    peak_horizons = []
    for h in range(1, 46):
        col = f'fwd_{h}'
        q1 = quiet[quiet['stress_q'] == 'Q1'][col].dropna()
        q5 = quiet[quiet['stress_q'] == 'Q5'][col].dropna()

        if len(q1) > 5 and len(q5) > 5:
            q1_m = q1.mean() * 100
            q5_m = q5.mean() * 100
            spread = q5_m - q1_m
            t, p = stats.ttest_ind(q5, q1, equal_var=False)

            node = nodes.get(h, "")
            sig = "🔴" if abs(t) > 2 else "⚠️" if abs(t) > 1.5 else ""
            md += f"| T+{h}d | {q1_m:+.1f}% | {q5_m:+.1f}% | {spread:+.1f}% | {t:.2f} {sig} | {node} |\n"

            if abs(t) > 1.5:
                peak_horizons.append((h, spread, t))
                print(f"    T+{h}: spread={spread:+.1f}%, t={t:.2f} {node}")

    md += "\n## Interpretation\n\n"
    if peak_horizons:
        md += "Signal peaks at:\n\n"
        for h, s, t in sorted(peak_horizons, key=lambda x: abs(x[2]), reverse=True):
            node = nodes.get(h, "")
            md += f"- **T+{h}d**: spread={s:+.1f}%, t={t:.2f} {node}\n"
    md += "\n"

    # Does the signal match the Fast Waterfall decomposition?
    t1_5 = [h for h, s, t in peak_horizons if 1 <= h <= 5]
    t6_10 = [h for h, s, t in peak_horizons if 6 <= h <= 10]
    t33_35 = [h for h, s, t in peak_horizons if 33 <= h <= 35]

    md += f"\nFast Waterfall sub-peaks (T+1 to T+5): {len(t1_5)} found\n"
    md += f"Mid-range peaks (T+6 to T+10): {len(t6_10)} found\n"
    md += f"Slow Waterfall echoes (T+33 to T+35): {len(t33_35)} found\n"

    write_md("06_fast_waterfall.md", md)
    return peak_horizons


# ═══════════════════════════════════════════════════════════════════
# TEST 2: XRT FTD CROSS-CORRELATION
# ═══════════════════════════════════════════════════════════════════
def test_xrt_cross_correlation(daily_stress, gme_ftd):
    """
    settlement model: ETF basket mechanics explain unexplained OI stress.
    Test: does XRT FTD activity predict GME deep OTM put stress?
    """
    print("\n" + "=" * 70)
    print("  TEST 2: XRT FTD ← → GME OI STRESS CROSS-CORRELATION")
    print("=" * 70)

    xrt_ftd = load_ftd("XRT")
    iwm_ftd = load_ftd("IWM")
    amc_ftd = load_ftd("AMC")

    md = "# ETF FTD Cross-Correlation with GME OI Stress\n\n"
    md += "**Hypothesis**: Unexplained GME deep OTM put stress is caused by ETF basket mechanics.\n\n"

    for ticker, ftd_df in [("XRT", xrt_ftd), ("IWM", iwm_ftd), ("AMC", amc_ftd)]:
        if ftd_df.empty:
            continue

        md += f"## {ticker} FTDs vs GME OI Stress\n\n"
        print(f"\n  {ticker}: {len(ftd_df)} FTD records")

        # Align
        ftd_daily = ftd_df.groupby('date')['quantity'].sum()
        ftd_daily = ftd_daily.reindex(daily_stress.index, fill_value=0)
        ftd_log = np.log1p(ftd_daily)

        # Same-day correlation
        valid = (daily_stress > 0) & (ftd_log > 0)
        if valid.sum() > 20:
            r = np.corrcoef(daily_stress[valid], ftd_log[valid])[0, 1]
            md += f"- Same-day correlation: **r = {r:.3f}** (n={valid.sum()})\n"
            print(f"    Same-day r = {r:.3f}")

        # Cross-correlation at different lags
        md += "\n| Lag | Correlation | Direction | Interpretation |\n"
        md += "|-----|:---:|---|---|\n"

        for lag in [-10, -7, -5, -3, -1, 0, 1, 3, 5, 7, 10]:
            shifted = ftd_log.shift(lag)
            valid = (daily_stress > 0) & (shifted > 0) & shifted.notna()
            if valid.sum() > 20:
                r = np.corrcoef(daily_stress[valid], shifted[valid])[0, 1]
                if lag < 0:
                    direction = f"{ticker} at T{lag} → GME Stress at T"
                    interp = f"{ticker} FTDs {abs(lag)}d BEFORE GME stress" if r > 0.1 else ""
                elif lag > 0:
                    direction = f"GME Stress at T → {ticker} at T+{lag}"
                    interp = f"GME stress {lag}d BEFORE {ticker} FTDs" if r > 0.1 else ""
                else:
                    direction = "Same day"
                    interp = "Contemporaneous" if r > 0.1 else ""

                marker = "🔴" if abs(r) > 0.15 else "⚠️" if abs(r) > 0.08 else ""
                md += f"| T{lag:+d} | {r:+.3f} {marker} | {direction} | {interp} |\n"

        # Do XRT FTD spikes predict unexplained GME stress?
        xrt_spike_dates = set(ftd_df[ftd_df['quantity'] > ftd_df['quantity'].quantile(0.90)]['date'])
        if xrt_spike_dates:
            stress_on_spike_days = daily_stress[daily_stress.index.isin(xrt_spike_dates)]
            stress_on_normal_days = daily_stress[~daily_stress.index.isin(xrt_spike_dates)]

            if len(stress_on_spike_days) > 5 and len(stress_on_normal_days) > 5:
                t, p = stats.ttest_ind(stress_on_spike_days, stress_on_normal_days, equal_var=False)
                md += f"\n**{ticker} spike days vs normal days:**\n"
                md += f"- Stress on {ticker} spike days: **{stress_on_spike_days.mean():.1f}** (n={len(stress_on_spike_days)})\n"
                md += f"- Stress on normal days: **{stress_on_normal_days.mean():.1f}**\n"
                md += f"- t-stat: **{t:.2f}**, p = {p:.4f}\n"
                print(f"    {ticker} spike days: stress={stress_on_spike_days.mean():.1f} vs normal={stress_on_normal_days.mean():.1f}, t={t:.2f}")

        md += "\n---\n\n"

    # Multivariate: do GME FTDs + XRT FTDs together explain more stress?
    if not xrt_ftd.empty:
        md += "## Multivariate: GME FTDs + XRT FTDs → GME Stress\n\n"
        gme_daily = gme_ftd.groupby('date')['quantity'].sum()
        xrt_daily = xrt_ftd.groupby('date')['quantity'].sum()

        combined = pd.DataFrame({
            'stress': daily_stress,
            'gme_ftd': np.log1p(gme_daily.reindex(daily_stress.index, fill_value=0)),
            'xrt_ftd': np.log1p(xrt_daily.reindex(daily_stress.index, fill_value=0)),
        }).dropna()

        if len(combined) > 30:
            # GME only
            valid = combined['gme_ftd'] > 0
            if valid.sum() > 10:
                r_gme = np.corrcoef(combined.loc[valid, 'stress'], combined.loc[valid, 'gme_ftd'])[0, 1]
                md += f"- GME FTDs alone → stress: r = {r_gme:.3f}, R² = {r_gme**2:.3f}\n"

            # XRT only
            valid = combined['xrt_ftd'] > 0
            if valid.sum() > 10:
                r_xrt = np.corrcoef(combined.loc[valid, 'stress'], combined.loc[valid, 'xrt_ftd'])[0, 1]
                md += f"- XRT FTDs alone → stress: r = {r_xrt:.3f}, R² = {r_xrt**2:.3f}\n"

            # Combined (simple additive)
            combined['combined_ftd'] = combined['gme_ftd'] + combined['xrt_ftd']
            valid = combined['combined_ftd'] > 0
            if valid.sum() > 10:
                r_both = np.corrcoef(combined.loc[valid, 'stress'], combined.loc[valid, 'combined_ftd'])[0, 1]
                md += f"- GME + XRT combined → stress: r = {r_both:.3f}, R² = {r_both**2:.3f}\n"
                improvement = (r_both**2 - r_gme**2) / r_gme**2 * 100 if r_gme != 0 else 0
                md += f"- **R² improvement from adding XRT: {improvement:+.0f}%**\n"

    write_md("07_xrt_cross_correlation.md", md)


# ═══════════════════════════════════════════════════════════════════
# TEST 3: T+0 MECHANICAL AWARENESS
# ═══════════════════════════════════════════════════════════════════
def test_t0_awareness(daily_stress, gme_ftd):
    """
    settlement model: OI stress can PRECEDE FTD filing because operators
    know at execution they'll fail.
    Test: does OI stress systematically precede FTD spikes?
    """
    print("\n" + "=" * 70)
    print("  TEST 3: T+0 MECHANICAL AWARENESS")
    print("=" * 70)

    # Find FTD spikes
    ftd_daily = gme_ftd.groupby('date')['quantity'].sum()
    threshold = ftd_daily.quantile(0.85)
    spike_dates = ftd_daily[ftd_daily > threshold].index

    md = "# T+0 Mechanical Awareness: Does Stress Precede Failures?\n\n"
    md += f"**Hypothesis**: Operators know at execution they'll fail. OI stress appears BEFORE FTDs.\n\n"
    md += f"FTD spike threshold (85th pct): {threshold:,.0f}\n"
    md += f"Number of spike dates: {len(spike_dates)}\n\n"

    # For each FTD spike, measure stress at T-5 through T+10
    md += "## Average Stress Around FTD Spikes\n\n"
    md += "| Offset | Mean Stress | vs Baseline | Interpretation |\n"
    md += "|--------|:--:|:--:|---|\n"

    baseline_stress = daily_stress.mean()
    pre_excess = []
    post_excess = []

    for offset in range(-10, 11):
        shifted_dates = spike_dates + pd.offsets.BDay(offset)
        stress_at_offset = daily_stress.reindex(shifted_dates).dropna()

        if len(stress_at_offset) > 5:
            mean_s = stress_at_offset.mean()
            excess = mean_s - baseline_stress
            pct = excess / baseline_stress * 100

            if offset < 0:
                interp = "BEFORE FTD" if excess > 0 else ""
                pre_excess.append(excess)
            elif offset > 0:
                interp = "AFTER FTD" if excess > 0 else ""
                post_excess.append(excess)
            else:
                interp = "FTD day"

            marker = "🔴" if pct > 30 else "⚠️" if pct > 15 else ""
            md += f"| T{offset:+d} | {mean_s:.1f} | {excess:+.1f} ({pct:+.0f}%) | {interp} {marker} |\n"

    # Key diagnostic: is pre-FTD stress > post-FTD stress?
    if pre_excess and post_excess:
        pre_mean = np.mean(pre_excess[-5:])  # T-5 to T-1
        post_mean = np.mean(post_excess[:5])  # T+1 to T+5

        md += f"\n## Key Diagnostic\n\n"
        md += f"- Mean excess stress T-5 to T-1 (BEFORE failure): **{pre_mean:+.1f}**\n"
        md += f"- Mean excess stress T+1 to T+5 (AFTER failure): **{post_mean:+.1f}**\n"

        if pre_mean > post_mean:
            md += f"- **⚠️ Stress peaks BEFORE FTD filing** — consistent with T+0 mechanical awareness\n"
            md += f"- The options chain reacts to the TRADE; the SEC data reacts to the FAILURE of the trade\n"
        else:
            md += f"- Stress peaks AFTER FTD filing — standard reactive pattern\n"

    # Era-specific analysis
    md += "\n## Era-Specific Pattern\n\n"
    md += "| Era | Pre-FTD Excess | Post-FTD Excess | Leading? |\n"
    md += "|-----|:--:|:--:|:--:|\n"

    for era_name, start, end in [
        ("Pre-squeeze (2020)", "2020-01-01", "2020-12-31"),
        ("Squeeze (2021)", "2021-01-01", "2021-06-30"),
        ("Post-split (2022-23)", "2022-07-01", "2023-12-31"),
        ("Recent (2024-26)", "2024-01-01", "2026-12-31"),
    ]:
        era_spikes = spike_dates[(spike_dates >= start) & (spike_dates <= end)]
        if len(era_spikes) < 3:
            continue

        pre_vals = []
        post_vals = []
        for offset in range(-5, 0):
            shifted = era_spikes + pd.offsets.BDay(offset)
            vals = daily_stress.reindex(shifted).dropna()
            if len(vals) > 0:
                pre_vals.extend(vals.tolist())
        for offset in range(1, 6):
            shifted = era_spikes + pd.offsets.BDay(offset)
            vals = daily_stress.reindex(shifted).dropna()
            if len(vals) > 0:
                post_vals.extend(vals.tolist())

        pre_m = np.mean(pre_vals) - baseline_stress if pre_vals else 0
        post_m = np.mean(post_vals) - baseline_stress if post_vals else 0
        leading = "✅ YES" if pre_m > post_m else "No"
        md += f"| {era_name} | {pre_m:+.1f} | {post_m:+.1f} | {leading} |\n"

    write_md("08_t0_awareness.md", md)


# ═══════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  PHASE 7: TESTING settlement model PREDICTIONS")
    print("=" * 70)

    print("\n  Loading data...")
    daily_stress, total_oi, oi_matrix = build_stress_series()
    print(f"  Stress series: {len(daily_stress)} days")
    price_df = load_price()
    print(f"  Price records: {len(price_df)}")
    gme_ftd = load_ftd("GME")
    print(f"  GME FTD records: {len(gme_ftd)}")

    test_fast_waterfall(daily_stress, price_df, gme_ftd)
    test_xrt_cross_correlation(daily_stress, gme_ftd)
    test_t0_awareness(daily_stress, gme_ftd)

    print(f"\n  All results saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
