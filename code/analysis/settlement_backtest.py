#!/usr/bin/env python3
"""
Phase 5: Backtesting the Settlement Decoder
=============================================
Tests whether the "machine's language" has PREDICTIVE POWER:

  1. STRESS → RETURNS: Do OI stress events predict excess returns at T+35?
  2. REGIME ANALYSIS: How has the machine's voice changed across eras?
  3. WATERFALL RESIDUALS: After stripping predicted signal, what's left?
  4. INTER-EVENT PREDICTION: Do stress events predict future stress events?
  5. FORWARD RETURNS AROUND DEADLINES: What happens to price at T+35?
  6. STRESS AS PRESSURE GAUGE: Does cumulative stress predict drawdowns?
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
FTD_CSV = Path(__file__).resolve().parents[2] / "data" / "ftd" / "GME_ftd.csv"
PRICE_CSV = Path(__file__).resolve().parents[2] / "data" / "ftd" / "gme_daily_price.csv"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results" / "oi_steganography"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_per_strike_oi():
    data = {}
    for f in sorted(OI_DIR.glob("oi_*.parquet")):
        date_str = f.stem.replace("oi_", "")
        try:
            df = pd.read_parquet(f)
            if len(df) > 0:
                data[date_str] = df
        except Exception:
            continue
    return data


def load_ftd():
    if FTD_CSV.exists():
        df = pd.read_csv(FTD_CSV)
        df.columns = [c.lower().strip() for c in df.columns]
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        return df.dropna(subset=['date', 'quantity'])
    return pd.DataFrame()


def load_price():
    df = pd.read_csv(PRICE_CSV)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').set_index('date')
    df['returns'] = df['gme_close'].pct_change()
    df['log_returns'] = np.log(df['gme_close'] / df['gme_close'].shift(1))
    return df


def build_stress_series(data):
    """Build the stress time series from OI data."""
    dates = sorted(data.keys())
    strike_ts = defaultdict(dict)
    for date_str in dates:
        df = data[date_str]
        deep = df[(df["right"] == "PUT") & (df["strike"] <= 15)]
        for _, row in deep.iterrows():
            strike_ts[float(row["strike"])][date_str] = int(row["open_interest"])

    oi_matrix = pd.DataFrame(strike_ts).fillna(0)
    oi_matrix.index = pd.to_datetime(oi_matrix.index, format="%Y%m%d")
    oi_matrix = oi_matrix.sort_index()

    baseline = oi_matrix.rolling(20, min_periods=5).median()
    rolling_std = oi_matrix.rolling(20, min_periods=5).std()
    z_scores = (oi_matrix - baseline) / rolling_std.replace(0, np.nan)
    z_scores = z_scores.fillna(0)

    daily_stress = z_scores.abs().sum(axis=1)
    daily_stress.name = "stress"

    # Also compute total deep OTM put OI
    total_deep_oi = oi_matrix.sum(axis=1)
    total_deep_oi.name = "total_deep_oi"

    return oi_matrix, z_scores, daily_stress, total_deep_oi


# ═════════════════════════════════════════════════════════════════════════
# 1. STRESS → FORWARD RETURNS (Does the machine predict price?)
# ═════════════════════════════════════════════════════════════════════════
def test_stress_returns(daily_stress, price_df):
    """
    The core predictive test: does high machine stress today
    predict abnormal returns T+35 business days later?
    """
    print("\n" + "=" * 70)
    print("  1. STRESS → FORWARD RETURNS")
    print("=" * 70)

    # Align stress and price
    merged = pd.DataFrame({
        'stress': daily_stress,
    }).join(price_df[['gme_close', 'returns']], how='inner')

    # Forward returns at different horizons
    for horizon in [5, 10, 15, 20, 25, 30, 35, 40, 45]:
        merged[f'fwd_{horizon}d'] = merged['gme_close'].shift(-horizon) / merged['gme_close'] - 1

    # Split into quintiles by stress
    merged['stress_q'] = pd.qcut(merged['stress'], q=5, labels=['Q1_low', 'Q2', 'Q3', 'Q4', 'Q5_high'],
                                  duplicates='drop')

    print(f"\n  Stress quintiles → Forward returns:")
    print(f"  {'Horizon':>10} | {'Q1 (low)':>10} | {'Q5 (high)':>10} | {'Spread':>10} | {'t-stat':>8}")
    print(f"  {'-'*60}")

    spread_results = {}
    for horizon in [5, 10, 15, 20, 25, 30, 35, 40, 45]:
        col = f'fwd_{horizon}d'
        q1_ret = merged[merged['stress_q'] == 'Q1_low'][col].dropna()
        q5_ret = merged[merged['stress_q'] == 'Q5_high'][col].dropna()

        if len(q1_ret) > 5 and len(q5_ret) > 5:
            q1_mean = q1_ret.mean() * 100
            q5_mean = q5_ret.mean() * 100
            spread = q5_mean - q1_mean

            # Simple t-stat (Welch's)
            from scipy import stats
            t_stat, p_val = stats.ttest_ind(q5_ret, q1_ret, equal_var=False)

            marker = " 🔴" if abs(t_stat) > 2 else " ⚠️" if abs(t_stat) > 1.5 else ""
            print(f"  T+{horizon:>7}d | {q1_mean:>9.2f}% | {q5_mean:>9.2f}% | "
                  f"{spread:>+9.2f}% | {t_stat:>7.2f}{marker}")

            spread_results[horizon] = {
                "q1_mean": round(q1_mean, 3),
                "q5_mean": round(q5_mean, 3),
                "spread": round(spread, 3),
                "t_stat": round(t_stat, 3),
                "p_val": round(p_val, 4),
                "n_q1": len(q1_ret),
                "n_q5": len(q5_ret),
            }

    # Also test: does stress predict VOLATILITY?
    for horizon in [5, 10, 20, 35]:
        col = f'fwd_{horizon}d'
        q1_vol = merged[merged['stress_q'] == 'Q1_low'][col].dropna().std() * 100
        q5_vol = merged[merged['stress_q'] == 'Q5_high'][col].dropna().std() * 100
        ratio = q5_vol / max(q1_vol, 0.01)
        marker = " 🔴" if ratio > 1.5 else ""
        print(f"\n  T+{horizon}d volatility: Q1={q1_vol:.2f}%, Q5={q5_vol:.2f}%, ratio={ratio:.2f}×{marker}")

    return spread_results


# ═════════════════════════════════════════════════════════════════════════
# 2. FTD SPIKE → T+35 PRICE IMPACT
# ═════════════════════════════════════════════════════════════════════════
def test_ftd_t35_impact(ftd_df, price_df):
    """
    The most direct test: when a large FTD occurs, what happens
    to the stock price exactly T+35 business days later?
    """
    print("\n" + "=" * 70)
    print("  2. FTD SPIKE → T+35 PRICE IMPACT")
    print("=" * 70)

    if ftd_df.empty:
        print("  No FTD data")
        return {}

    # Find FTD spikes
    ftd_threshold = ftd_df['quantity'].quantile(0.90)
    spikes = ftd_df[ftd_df['quantity'] > ftd_threshold].copy()
    print(f"  FTD spike threshold (90th pct): {ftd_threshold:,.0f}")
    print(f"  Number of spikes: {len(spikes)}")

    # For each spike, compute returns at various T+ offsets
    event_returns = defaultdict(list)
    event_details = []

    for _, spike in spikes.iterrows():
        spike_date = spike['date']
        for offset in [3, 6, 13, 15, 26, 33, 35, 36, 40, 45]:
            target_date = spike_date + pd.offsets.BDay(offset)
            # Get price at spike and at target
            try:
                spike_price = price_df.loc[spike_date - pd.Timedelta(days=3):spike_date + pd.Timedelta(days=3), 'gme_close']
                target_price = price_df.loc[target_date - pd.Timedelta(days=3):target_date + pd.Timedelta(days=3), 'gme_close']
                if len(spike_price) > 0 and len(target_price) > 0:
                    ret = (target_price.iloc[-1] / spike_price.iloc[0] - 1) * 100
                    event_returns[offset].append(ret)

                    if offset == 35:
                        event_details.append({
                            "ftd_date": str(spike_date.date()),
                            "ftd_qty": int(spike['quantity']),
                            "t35_date": str(target_date.date()),
                            "return_pct": round(ret, 2),
                        })
            except Exception:
                continue

    # Compute average returns and compare to unconditional
    unconditional_returns = {}
    for offset in [3, 6, 13, 15, 26, 33, 35, 36, 40, 45]:
        uc = price_df['gme_close'].pct_change(offset).dropna() * 100
        unconditional_returns[offset] = uc.mean()

    print(f"\n  Returns after FTD spike vs. unconditional:")
    print(f"  {'Offset':>8} | {'Post-FTD':>10} | {'Baseline':>10} | {'Excess':>10} | {'N':>5} | {'Node'}")
    print(f"  {'-'*70}")

    nodes = {3: "CNS", 6: "BFMM", 13: "RegSHO", 15: "Phantom", 
             26: "Cascade", 33: "Echo", 35: "Buy-in", 36: "Spillover", 
             40: "Terminal", 45: "Boundary"}

    impact_results = {}
    for offset in sorted(event_returns.keys()):
        rets = event_returns[offset]
        if not rets:
            continue
        mean_ret = np.mean(rets)
        baseline = unconditional_returns.get(offset, 0)
        excess = mean_ret - baseline
        marker = " 🔴" if abs(excess) > 3 else " ⚠️" if abs(excess) > 1.5 else ""

        print(f"  T+{offset:>5} | {mean_ret:>+9.2f}% | {baseline:>+9.2f}% | "
              f"{excess:>+9.2f}% | {len(rets):>5} | {nodes.get(offset,'')}{marker}")

        impact_results[offset] = {
            "mean_return": round(mean_ret, 3),
            "baseline": round(baseline, 3),
            "excess": round(excess, 3),
            "n": len(rets),
        }

    # Breakdown by FTD size
    print(f"\n  T+35 returns by FTD size:")
    for qty_label, qty_min, qty_max in [
        ("Small (50-90th pct)", ftd_df['quantity'].quantile(0.50), ftd_threshold),
        ("Large (90-99th pct)", ftd_threshold, ftd_df['quantity'].quantile(0.99)),
        ("Mega (>99th pct)", ftd_df['quantity'].quantile(0.99), float('inf')),
    ]:
        subset = [d for d in event_details if qty_min <= d['ftd_qty'] < qty_max]
        if subset:
            rets = [d['return_pct'] for d in subset]
            pct_positive = sum(1 for r in rets if r > 0) / len(rets) * 100
            print(f"    {qty_label}: mean={np.mean(rets):+.2f}%, "
                  f"median={np.median(rets):+.2f}%, "
                  f"positive={pct_positive:.0f}%, n={len(subset)}")

    return {"impact_by_offset": impact_results, "details": event_details[:50]}


# ═════════════════════════════════════════════════════════════════════════
# 3. REGIME ANALYSIS: How the machine's voice changed
# ═════════════════════════════════════════════════════════════════════════
def test_regime_analysis(daily_stress, total_deep_oi, price_df, z_scores):
    """
    Track how the settlement machinery's behavior has evolved across
    different eras of GME history.
    """
    print("\n" + "=" * 70)
    print("  3. REGIME ANALYSIS")
    print("=" * 70)

    regimes = {
        "Pre-DFV (2020 Q1-Q3)": ("2020-01-01", "2020-09-30"),
        "DFV Thesis Build (2020 Q4)": ("2020-10-01", "2020-12-31"),
        "Jan 2021 Squeeze": ("2021-01-01", "2021-02-28"),
        "Post-Squeeze (2021 Q2-Q4)": ("2021-03-01", "2021-12-31"),
        "Pre-Split (2022 H1)": ("2022-01-01", "2022-07-21"),
        "Post-Split (2022 H2)": ("2022-07-22", "2022-12-31"),
        "Quiet Era (2023)": ("2023-01-01", "2023-12-31"),
        "RK Return (2024 H1)": ("2024-01-01", "2024-06-30"),
        "Post-RK (2024 H2)": ("2024-07-01", "2024-12-31"),
        "Current (2025)": ("2025-01-01", "2025-12-31"),
    }

    regime_stats = {}
    print(f"\n  {'Regime':<30} | {'Days':>5} | {'Stress':>8} | {'OI':>10} | {'Events':>6} | {'Voice'}")
    print(f"  {'-'*85}")

    for name, (start, end) in regimes.items():
        mask = (daily_stress.index >= start) & (daily_stress.index <= end)
        if mask.sum() == 0:
            continue

        stress = daily_stress[mask]
        oi = total_deep_oi[mask] if mask.sum() > 0 else pd.Series([0])

        # Count events (stress > 2σ above rolling mean)
        stress_mean = stress.rolling(20, min_periods=5).mean()
        stress_std = stress.rolling(20, min_periods=5).std()
        events = ((stress - stress_mean) / stress_std.replace(0, 1) > 2).sum()

        # Voice characterization
        mean_stress = stress.mean()
        if mean_stress > 20:
            voice = "🔴 SCREAMING"
        elif mean_stress > 10:
            voice = "⚠️ LOUD"
        elif mean_stress > 5:
            voice = "TALKING"
        elif mean_stress > 2:
            voice = "whispering"
        else:
            voice = "silent"

        print(f"  {name:<30} | {mask.sum():>5} | {mean_stress:>7.1f} | "
              f"{oi.mean():>9,.0f} | {events:>6} | {voice}")

        regime_stats[name] = {
            "n_days": int(mask.sum()),
            "mean_stress": round(float(mean_stress), 2),
            "max_stress": round(float(stress.max()), 2),
            "mean_deep_oi": round(float(oi.mean()), 0),
            "n_events": int(events),
        }

    return regime_stats


# ═════════════════════════════════════════════════════════════════════════
# 4. WATERFALL RESIDUALS: What's left after stripping predicted signal?
# ═════════════════════════════════════════════════════════════════════════
def test_waterfall_residuals(z_scores, daily_stress, ftd_df):
    """
    The waterfall predicts OI perturbations at T+3, T+6, T+13, etc.
    After subtracting the EXPECTED waterfall signal, what residual remains?
    That residual is where unexplained activity hides.
    """
    print("\n" + "=" * 70)
    print("  4. WATERFALL RESIDUALS")
    print("=" * 70)

    if ftd_df.empty:
        print("  No FTD data for waterfall prediction")
        return {}

    waterfall_offsets = [3, 6, 13, 14, 15, 26, 33, 35, 36, 40]

    # For each OI date, compute the "expected" stress from known FTDs
    predicted_stress = pd.Series(0.0, index=daily_stress.index)

    for _, row in ftd_df.iterrows():
        ftd_date = row['date']
        ftd_qty = row['quantity']

        for offset in waterfall_offsets:
            target = ftd_date + pd.offsets.BDay(offset)
            if target in predicted_stress.index:
                # Predicted stress proportional to FTD size
                predicted_stress[target] += np.log1p(ftd_qty) * 0.1

    # Normalize predicted stress to same scale
    if predicted_stress.max() > 0:
        predicted_stress = predicted_stress * (daily_stress.mean() / predicted_stress.mean())

    # Residual = actual - predicted
    residual = daily_stress - predicted_stress
    residual = residual.dropna()

    # Correlation
    common = daily_stress.index.intersection(predicted_stress.index)
    actual = daily_stress[common]
    predicted = predicted_stress[common]
    valid = (actual > 0) & (predicted > 0)
    corr = np.corrcoef(actual[valid], predicted[valid])[0, 1] if valid.sum() > 10 else 0

    print(f"  Correlation (actual stress vs predicted from FTDs): {corr:.3f}")
    print(f"  R²: {corr**2:.3f}")

    # Residual analysis
    print(f"\n  Residual statistics:")
    print(f"    Mean residual: {residual.mean():.2f}")
    print(f"    Std residual:  {residual.std():.2f}")

    # Top residual days — these are UNEXPLAINED by the waterfall
    top_residual = residual.nlargest(20)
    print(f"\n  Top 20 unexplained stress days (highest residual):")
    print(f"  {'Date':>12} | {'Actual':>8} | {'Predicted':>9} | {'Residual':>9} | {'Interpretation'}")
    print(f"  {'-'*70}")

    unexplained = []
    for dt, res in top_residual.items():
        act = daily_stress.get(dt, 0)
        pred = predicted_stress.get(dt, 0)
        
        # Characterize the unexplained event
        if act > 20 and pred < 5:
            interp = "🔴 NO FTD EXPLAINS THIS — pure anomaly"
        elif act > pred * 2:
            interp = "⚠️ Stress 2x higher than FTDs predict"
        else:
            interp = "Moderate excess"

        print(f"  {dt.date()} | {act:>7.1f} | {pred:>8.1f} | {res:>+8.1f} | {interp}")

        unexplained.append({
            "date": str(dt.date()),
            "actual_stress": round(act, 2),
            "predicted_stress": round(pred, 2),
            "residual": round(res, 2),
            "interpretation": interp,
        })

    # Bottom residual days — the waterfall OVER-predicted
    bottom_residual = residual.nsmallest(10)
    print(f"\n  Top 10 OVER-predicted days (machine quieter than FTDs suggest):")
    for dt, res in bottom_residual.items():
        act = daily_stress.get(dt, 0)
        pred = predicted_stress.get(dt, 0)
        print(f"    {dt.date()}: actual={act:.1f}, predicted={pred:.1f}, residual={res:+.1f}")

    return {
        "correlation": round(corr, 4),
        "r_squared": round(corr**2, 4),
        "mean_residual": round(float(residual.mean()), 2),
        "unexplained_events": unexplained,
    }


# ═════════════════════════════════════════════════════════════════════════
# 5. STRESS AUTOCORRELATION: Does the machine predict itself?
# ═════════════════════════════════════════════════════════════════════════
def test_stress_autocorrelation(daily_stress):
    """
    If the waterfall creates self-reinforcing cascades,
    stress at T should predict stress at T+33 and T+35.
    """
    print("\n" + "=" * 70)
    print("  5. STRESS AUTOCORRELATION (Self-Prediction)")
    print("=" * 70)

    # Autocorrelation at specific waterfall lags
    print(f"\n  Autocorrelation at waterfall lags:")
    print(f"  {'Lag':>5} | {'ACF':>8} | {'Node'}")
    print(f"  {'-'*40}")

    nodes = {1: "Next day", 3: "CNS", 5: "BFMM-1", 6: "BFMM", 
             10: "2 weeks", 13: "RegSHO", 15: "Phantom",
             20: "1 month", 26: "Cascade", 33: "Echo", 35: "Buy-in",
             40: "Terminal"}

    acf_results = {}
    for lag in sorted(nodes.keys()):
        shifted = daily_stress.shift(lag)
        valid = daily_stress.index.intersection(shifted.dropna().index)
        if len(valid) > 20:
            acf = np.corrcoef(daily_stress[valid], shifted[valid])[0, 1]
            marker = " 🔴" if abs(acf) > 0.3 else " ⚠️" if abs(acf) > 0.15 else ""
            print(f"  T+{lag:>3} | {acf:>+7.3f} | {nodes[lag]}{marker}")
            acf_results[lag] = round(acf, 4)

    # Is waterfall-lag ACF higher than non-waterfall?
    wf_lags = {3, 6, 13, 15, 26, 33, 35, 40}
    non_wf_lags = {1, 5, 10, 20}
    wf_acf = np.mean([acf_results.get(l, 0) for l in wf_lags])
    nwf_acf = np.mean([acf_results.get(l, 0) for l in non_wf_lags])

    print(f"\n  Waterfall-lag mean ACF: {wf_acf:.4f}")
    print(f"  Non-waterfall mean ACF: {nwf_acf:.4f}")
    print(f"  Ratio: {wf_acf/max(abs(nwf_acf), 0.001):.2f}×")

    return acf_results


# ═════════════════════════════════════════════════════════════════════════
# 6. DEEP OTM OI AS PRESSURE GAUGE
# ═════════════════════════════════════════════════════════════════════════
def test_pressure_gauge(total_deep_oi, price_df):
    """
    Does total deep OTM put OI act as a "pressure gauge" that
    leads price moves?
    """
    print("\n" + "=" * 70)
    print("  6. DEEP OTM OI AS PRESSURE GAUGE")
    print("=" * 70)

    merged = pd.DataFrame({
        'deep_oi': total_deep_oi,
    }).join(price_df[['gme_close']], how='inner')

    if len(merged) < 30:
        print("  Insufficient overlap between OI and price data")
        return {}

    # OI change predicts future returns?
    merged['oi_change'] = merged['deep_oi'].pct_change()
    merged['oi_z'] = (merged['oi_change'] - merged['oi_change'].rolling(20).mean()) / \
                      merged['oi_change'].rolling(20).std().replace(0, np.nan)

    for horizon in [5, 10, 20, 35]:
        merged[f'fwd_{horizon}'] = merged['gme_close'].shift(-horizon) / merged['gme_close'] - 1

    # Split by OI change quintile
    merged_clean = merged.dropna(subset=['oi_z'])
    if len(merged_clean) < 50:
        print("  Insufficient data for quintile analysis")
        return {}

    merged_clean['oi_q'] = pd.qcut(merged_clean['oi_z'], q=5, 
                                     labels=['Q1_big_drop', 'Q2', 'Q3', 'Q4', 'Q5_big_surge'],
                                     duplicates='drop')

    print(f"\n  OI change quintile → Forward returns:")
    print(f"  {'Horizon':>10} | {'Q1(OI drop)':>12} | {'Q5(OI surge)':>12} | {'Spread':>8} | Interpretation")
    print(f"  {'-'*75}")

    gauge_results = {}
    for horizon in [5, 10, 20, 35]:
        col = f'fwd_{horizon}'
        q1 = merged_clean[merged_clean['oi_q'] == 'Q1_big_drop'][col].dropna()
        q5 = merged_clean[merged_clean['oi_q'] == 'Q5_big_surge'][col].dropna()

        if len(q1) > 3 and len(q5) > 3:
            q1_mean = q1.mean() * 100
            q5_mean = q5.mean() * 100
            spread = q5_mean - q1_mean

            if spread > 2:
                interp = "OI surge → HIGHER price"
            elif spread < -2:
                interp = "OI surge → LOWER price"
            else:
                interp = "No clear signal"

            marker = " 🔴" if abs(spread) > 5 else " ⚠️" if abs(spread) > 2 else ""
            print(f"  T+{horizon:>7}d | {q1_mean:>+11.2f}% | {q5_mean:>+11.2f}% | "
                  f"{spread:>+7.2f}% | {interp}{marker}")

            gauge_results[horizon] = {
                "q1_mean": round(q1_mean, 3),
                "q5_mean": round(q5_mean, 3),
                "spread": round(spread, 3),
            }

    # Long-term OI vs price correlation
    corr = merged[['deep_oi', 'gme_close']].corr().iloc[0, 1]
    print(f"\n  Deep OTM OI vs Price level correlation: {corr:.3f}")

    # Granger-like test: does lagged OI predict returns?
    merged['returns'] = merged['gme_close'].pct_change()
    print(f"\n  Lagged OI correlation with returns:")
    for lag in [1, 5, 10, 20, 35]:
        shifted_oi = merged['oi_change'].shift(lag)
        valid = merged['returns'].dropna().index.intersection(shifted_oi.dropna().index)
        if len(valid) > 20:
            r = np.corrcoef(merged.loc[valid, 'returns'], shifted_oi[valid])[0, 1]
            marker = " ⚠️" if abs(r) > 0.1 else ""
            print(f"    OI change at T-{lag} → return at T: r={r:+.3f}{marker}")

    return gauge_results


# ═════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  PHASE 5: BACKTESTING THE SETTLEMENT DECODER")
    print("  Does the machine's language predict the future?")
    print("=" * 70)

    print("\n  Loading data...")
    data = load_per_strike_oi()
    print(f"  OI snapshots: {len(data)}")
    ftd_df = load_ftd()
    print(f"  FTD records: {len(ftd_df)}")
    price_df = load_price()
    print(f"  Price records: {len(price_df)}")

    print("\n  Building stress series...")
    oi_matrix, z_scores, daily_stress, total_deep_oi = build_stress_series(data)
    print(f"  Stress series: {len(daily_stress)} days")

    results = {}
    results["stress_returns"] = test_stress_returns(daily_stress, price_df)
    results["ftd_t35_impact"] = test_ftd_t35_impact(ftd_df, price_df)
    results["regime_analysis"] = test_regime_analysis(daily_stress, total_deep_oi, price_df, z_scores)
    results["waterfall_residuals"] = test_waterfall_residuals(z_scores, daily_stress, ftd_df)
    results["stress_autocorrelation"] = test_stress_autocorrelation(daily_stress)
    results["pressure_gauge"] = test_pressure_gauge(total_deep_oi, price_df)

    out_path = RESULTS_DIR / "phase5_backtest.json"
    def convert(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, pd.Timestamp): return str(obj)
        return str(obj)

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=convert)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
