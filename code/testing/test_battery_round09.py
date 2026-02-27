#!/usr/bin/env python3
"""
Round 9 Test Battery — The Tape Fracture & Structural Premeditation
===================================================================

Tests:
  T1: Z-Scored CGD Model — Normalizes R against trailing 60-day baseline to eliminate FPs.
  T2: Vanna Lag Bimodality — Sarle's Bimodality Coefficient and GMM (1 vs 2 components).
  T3: Tape Fracture (Δ_LD) Scan — May 17, 2024 lit/dark dislocation measurement.
  T4: Code 12 T-1 Event Study — Formal offset mapping of settlement vs CGD breach.
"""

import json
import os
import sys
import numpy as np
import pandas as pd
import scipy.stats as stats
from sklearn.mixture import GaussianMixture
from pathlib import Path
from datetime import datetime
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
THETA_ROOT = REPO_ROOT / "data" / "raw" / "thetadata" / "trades"
POLYGON_ROOT = REPO_ROOT / "data" / "raw" / "polygon" / "trades"
RESULTS_DIR = Path(__file__).parent

def load_options_parquet(ticker, date_str):
    path = THETA_ROOT / f"root={ticker}" / f"date={date_str}" / "part-0.parquet"
    if not path.exists(): return None
    df = pd.read_parquet(path)
    df['ts'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    if df['ts'].dt.tz is not None:
        df['ts'] = df['ts'].dt.tz_localize(None)
    return df

def load_equity_parquet(ticker, date_str):
    date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str
    path = POLYGON_ROOT / f"symbol={ticker}" / f"date={date_fmt}" / "part-0.parquet"
    if not path.exists(): return None
    df = pd.read_parquet(path)
    ts_col = 'timestamp' if 'timestamp' in df.columns else 'sip_timestamp'
    df['ts'] = pd.to_datetime(df[ts_col])
    if df['ts'].dt.tz is not None:
        df['ts'] = df['ts'].dt.tz_localize(None)
    return df

def get_available_theta_dates(ticker):
    d_path = THETA_ROOT / f"root={ticker}"
    if not d_path.exists(): return []
    return sorted([d.replace("date=", "") for d in os.listdir(d_path) if d.startswith("date=")])

def get_available_polygon_dates(ticker):
    d_path = POLYGON_ROOT / f"symbol={ticker}"
    if not d_path.exists(): return []
    return sorted([d.replace("date=", "") for d in os.listdir(d_path) if d.startswith("date=")])

def _compute_dte(df, date_str):
    exp_col = next((c for c in ['expiry', 'expiration', 'exp'] if c in df.columns), None)
    if not exp_col: return df
    sample = str(df[exp_col].iloc[0])
    fmt = '%Y%m%d' if len(sample) == 8 and sample.isdigit() else None
    df['expiry_dt'] = pd.to_datetime(df[exp_col], format=fmt)
    df['dte'] = (df['expiry_dt'] - pd.Timestamp(date_str)).dt.days
    return df

# ===================================================================
# T1: Z-SCORED EVENT-WINDOW CGD (OI PROXY)
# ===================================================================
def test_t1_zscored_cgd():
    print("\n" + "=" * 60)
    print("T1: Z-SCORED EVENT-WINDOW CGD (OI PROXY)")
    print("=" * 60)
    
    tickers = ["GME", "AMC", "TSLA", "AAPL", "MSFT", "DJT", "SPY"]
    results = {}
    Z_THRESH = 3.0
    
    for ticker in tickers:
        dates = get_available_theta_dates(ticker)
        if len(dates) < 60: continue
        
        daily_R = []
        rolling_stored = deque(maxlen=60)
        
        for d in dates:
            opts = load_options_parquet(ticker, d)
            if opts is None: continue
            opts = _compute_dte(opts, d)
            if 'dte' not in opts.columns: continue
            
            kinetic = float(opts[opts['dte'].between(0, 7)]['size'].sum())
            long_vol = float(opts[opts['dte'] > 7]['size'].sum())
            rolling_stored.append(long_vol)
            
            # Proxy for E_stored: 60-day rolling sum of long-dated volume * 10
            e_stored_proxy = (sum(rolling_stored) / max(1, len(rolling_stored))) * 60 * 10
            
            R_raw = kinetic / max(e_stored_proxy, 1.0)
            daily_R.append((d, R_raw))
        
        if len(daily_R) < 60: continue
        
        df_R = pd.DataFrame(daily_R, columns=['date', 'R'])
        df_R['R_mean_60'] = df_R['R'].rolling(60, min_periods=30).mean().shift(1)
        df_R['R_std_60'] = df_R['R'].rolling(60, min_periods=30).std().shift(1)
        df_R['Z_score'] = (df_R['R'] - df_R['R_mean_60']) / df_R['R_std_60'].replace(0, np.nan)
        
        breaches = df_R[df_R['Z_score'] >= Z_THRESH]
        
        results[ticker] = {
            "dates_analyzed": len(df_R),
            "anomaly_days": len(breaches),
            "max_Z": round(float(df_R['Z_score'].max()), 2),
            "top_breach_dates": breaches.sort_values('Z_score', ascending=False)['date'].head(5).tolist()
        }
        
        print(f"  {ticker:5s} | Max Z: {results[ticker]['max_Z']:>6.2f} | >3σ Anomalies: {len(breaches):>3} | Top: {results[ticker]['top_breach_dates'][:3]}")

    # Compare GME anomaly count vs controls
    gme_anomalies = results.get("GME", {}).get("anomaly_days", 0)
    control_anomalies = [results.get(t, {}).get("anomaly_days", 0) for t in ["SPY", "AAPL", "MSFT"] if t in results]
    control_mean = np.mean(control_anomalies) if control_anomalies else 0

    verdict = f"Z-scoring isolates true anomalies. GME: {gme_anomalies} vs controls avg: {control_mean:.1f}."
    print(f"\n  VERDICT: {verdict}")
    results["verdict"] = verdict
    return results

# ===================================================================
# T2: VANNA LAG BIMODALITY (GMM & Sarle's)
# ===================================================================
def test_t2_vanna_lag_bimodality():
    print("\n" + "=" * 60)
    print("T2: VANNA LAG BIMODALITY (GMM TEST)")
    print("=" * 60)
    
    # Lag data from R8 expanded scan (74 events)
    lag_counts = {1:9, 2:8, 3:7, 4:7, 5:4, 6:3, 7:7, 8:5, 9:6, 10:2, 11:7, 12:3, 13:1, 14:2, 15:3}
    lags = []
    for k, v in lag_counts.items():
        lags.extend([k]*v)
    
    X = np.array(lags).reshape(-1, 1)
    
    # Sarle's Bimodality Coefficient
    skew = float(stats.skew(lags))
    kurt = float(stats.kurtosis(lags, fisher=False))  # Pearson kurtosis
    b_coef = (skew**2 + 1) / kurt
    
    # GMM comparison (1 vs 2 components)
    gmm1 = GaussianMixture(n_components=1, random_state=42).fit(X)
    gmm2 = GaussianMixture(n_components=2, random_state=42).fit(X)
    gmm3 = GaussianMixture(n_components=3, random_state=42).fit(X)
    
    aic1, bic1 = float(gmm1.aic(X)), float(gmm1.bic(X))
    aic2, bic2 = float(gmm2.aic(X)), float(gmm2.bic(X))
    aic3, bic3 = float(gmm3.aic(X)), float(gmm3.bic(X))
    
    print(f"  Total Events: {len(X)}")
    print(f"  Skewness: {skew:.3f}")
    print(f"  Kurtosis (Pearson): {kurt:.3f}")
    print(f"  Sarle's Bimodality Coefficient (b): {b_coef:.4f} (Threshold > 0.555)")
    print(f"  1-Component GMM: AIC={aic1:.1f}, BIC={bic1:.1f}")
    print(f"  2-Component GMM: AIC={aic2:.1f}, BIC={bic2:.1f}")
    print(f"  3-Component GMM: AIC={aic3:.1f}, BIC={bic3:.1f}")
    
    best_n = np.argmin([bic1, bic2, bic3]) + 1
    
    result = {
        "n_events": len(X),
        "skewness": round(skew, 4),
        "kurtosis_pearson": round(kurt, 4),
        "sarles_b": round(b_coef, 4),
        "sarles_exceeds_threshold": b_coef > 0.555,
        "aic": {"1comp": round(aic1, 2), "2comp": round(aic2, 2), "3comp": round(aic3, 2)},
        "bic": {"1comp": round(bic1, 2), "2comp": round(bic2, 2), "3comp": round(bic3, 2)},
        "best_n_components_bic": best_n,
    }
    
    if best_n >= 2:
        gmm_best = gmm2 if best_n == 2 else gmm3
        means = sorted(gmm_best.means_.flatten())
        weights = gmm_best.weights_.flatten()
        stds = np.sqrt(gmm_best.covariances_.flatten())
        
        for i, (m, w, s) in enumerate(zip(means, weights, stds)):
            label = ["Fast", "Slow", "Ultra-Slow"][i] if i < 3 else f"Component {i+1}"
            print(f"    {label}: μ={m:.2f} min, σ={s:.2f}, weight={w:.1%}")
            result[f"component_{i+1}"] = {"mean_min": round(float(m), 2), "std": round(float(s), 2), "weight": round(float(w), 4)}
        
        verdict = f"BIMODAL CONFIRMED (BIC selects {best_n}-component). Sarle's b={b_coef:.4f} {'>' if b_coef > 0.555 else '<='} 0.555."
    else:
        verdict = f"UNIMODAL (BIC selects 1-component). Sarle's b={b_coef:.4f}."
        
    print(f"\n  VERDICT: {verdict}")
    result["verdict"] = verdict
    return result

# ===================================================================
# T3: TAPE FRACTURE SCAN (MAY 17, 2024 Δ_LD)
# ===================================================================
def test_t3_tape_fracture():
    print("\n" + "=" * 60)
    print("T3: TAPE FRACTURE (Δ_LD) SCAN — MAY 17, 2024")
    print("=" * 60)
    
    date_str = "2024-05-17"
    eq = load_equity_parquet('GME', date_str)
    
    if eq is None or len(eq) < 100:
        print("  Insufficient equity data for May 17, 2024.")
        return {"status": "NO_DATA"}
    
    print(f"  Total trades loaded: {len(eq):,}")
    
    # Pre-market UTC is roughly 08:00 - 13:30 (04:00 to 09:30 ET)
    pm = eq[(eq['ts'].dt.hour >= 8) & (eq['ts'].dt.hour < 14)].copy()
    print(f"  Pre-market trades (08:00-14:00 UTC): {len(pm):,}")
    
    if len(pm) < 10:
        print("  Insufficient pre-market data.")
        return {"status": "NO_PREMARKET_DATA", "total_trades": len(eq)}
    
    # Identify TRF (exchange == 4 for FINRA TRF)
    # Also try common TRF exchange IDs
    trf_exchanges = set()
    for ex_id in pm['exchange'].unique():
        sub = pm[pm['exchange'] == ex_id]
        if len(sub) > 10:
            vwap = (sub['price'] * sub['size']).sum() / sub['size'].sum()
            # TRF usually has higher variation in pre-market
            trf_exchanges.add(int(ex_id))
    
    # Separate Dark (TRF, exchange 4 or 15) and Lit (everything else)
    dark_ids = {4, 15}  # FINRA TRF variants
    dark = pm[pm['exchange'].isin(dark_ids)].copy()
    lit = pm[~pm['exchange'].isin(dark_ids)].copy()
    
    print(f"  Dark (TRF) trades: {len(dark):,} | Lit trades: {len(lit):,}")
    print(f"  Exchanges present: {sorted(pm['exchange'].unique().tolist())}")
    
    if len(dark) < 5 or len(lit) < 5:
        # Fall back to just computing price range stats
        price_range = pm['price'].max() - pm['price'].min()
        print(f"  Insufficient split. Overall price range: ${price_range:.2f}")
        return {"status": "INSUFFICIENT_SPLIT", "price_range": price_range}
    
    # 1-minute VWAP comparison
    dark['minute'] = dark['ts'].dt.floor('1min')
    lit['minute'] = lit['ts'].dt.floor('1min')
    
    def calc_vwap(df):
        v = (df['price'] * df['size']).sum()
        s = df['size'].sum()
        return v / s if s > 0 else np.nan
        
    lit_vwap = lit.groupby('minute').apply(calc_vwap)
    dark_vwap = dark.groupby('minute').apply(calc_vwap)
    
    df_compare = pd.DataFrame({'lit_vwap': lit_vwap, 'dark_vwap': dark_vwap}).dropna()
    
    if df_compare.empty:
        print("  No overlapping minutes between lit and dark.")
        return {"status": "NO_OVERLAP"}
    
    df_compare['spread'] = df_compare['dark_vwap'] - df_compare['lit_vwap']
    df_compare['abs_spread'] = df_compare['spread'].abs()
    
    max_spread = round(float(df_compare['spread'].max()), 2)
    max_abs_spread = round(float(df_compare['abs_spread'].max()), 2)
    mean_spread = round(float(df_compare['spread'].mean()), 2)
    median_spread = round(float(df_compare['spread'].median()), 2)
    
    # Find minutes with >$5 dislocation
    fractures = df_compare[df_compare['abs_spread'] > 5.0]
    # Find minutes with >$1 dislocation
    dislocations_1 = df_compare[df_compare['abs_spread'] > 1.0]
    
    print(f"\n  Overlapping minutes: {len(df_compare)}")
    print(f"  Max spread: ${max_spread}")
    print(f"  Max |spread|: ${max_abs_spread}")
    print(f"  Mean spread: ${mean_spread}")
    print(f"  Median spread: ${median_spread}")
    print(f"  Minutes with |spread| > $5: {len(fractures)}")
    print(f"  Minutes with |spread| > $1: {len(dislocations_1)}")
    
    if not fractures.empty:
        print(f"\n  TAPE FRACTURE DETECTED — Severe dislocations:")
        for idx, row in fractures.head(10).iterrows():
            ts_str = idx.strftime('%H:%M') if hasattr(idx, 'strftime') else str(idx)
            print(f"    {ts_str} UTC | Lit: ${row['lit_vwap']:.2f} | Dark: ${row['dark_vwap']:.2f} | Δ: ${row['spread']:.2f}")
    
    # Dark ceiling analysis
    dark_max = round(float(dark['price'].max()), 2)
    dark_p99 = round(float(dark['price'].quantile(0.99)), 2)
    
    print(f"\n  Dark trade price ceiling: max=${dark_max}, p99=${dark_p99}")
    
    verdict = f"Max Δ_LD = ${max_abs_spread}. {len(fractures)} minutes with >$5 fracture. Dark ceiling=${dark_max}."
    print(f"\n  VERDICT: {verdict}")
    
    return {
        "total_pm_trades": len(pm),
        "dark_trades": len(dark),
        "lit_trades": len(lit),
        "overlapping_minutes": len(df_compare),
        "max_spread": max_spread,
        "max_abs_spread": max_abs_spread,
        "mean_spread": mean_spread,
        "median_spread": median_spread,
        "fracture_minutes_gt5": len(fractures),
        "dislocation_minutes_gt1": len(dislocations_1),
        "dark_price_max": dark_max,
        "dark_price_p99": dark_p99,
        "verdict": verdict,
    }

# ===================================================================
# T4: CODE 12 T-1 LEAD TEST (EVENT STUDY)
# ===================================================================
def test_t4_code12_t1_lead():
    print("\n" + "=" * 60)
    print("T4: CODE 12 T-1 LEAD TEST (GME)")
    print("=" * 60)
    
    theta_dates = set(get_available_theta_dates("GME"))
    polygon_dates = set([d.replace("-","") for d in get_available_polygon_dates("GME")])
    overlap = sorted(theta_dates & polygon_dates)
    
    print(f"  Overlapping dates: {len(overlap)}")
    
    c12_series, opt_series = [], []
    date_labels = []
    
    for i, d in enumerate(overlap):
        eq = load_equity_parquet("GME", d)
        opts = load_options_parquet("GME", d)
        if eq is None or opts is None: continue
        
        c12_vol = 0
        if 'conditions' in eq.columns:
            mask = eq['conditions'].apply(lambda c: isinstance(c, (list, np.ndarray)) and 12 in c)
            c12_vol = int(eq.loc[mask, 'size'].sum())
            
        c12_series.append(c12_vol)
        opt_series.append(int(opts['size'].sum()))
        date_labels.append(d)
        
        if (i+1) % 200 == 0:
            print(f"    Scanned {i+1}/{len(overlap)} dates...")

    if len(c12_series) < 30:
        return {"status": "INSUFFICIENT_DATA"}

    c12_arr = np.array(c12_series, dtype=float)
    opt_arr = np.array(opt_series, dtype=float)
    c12_z = (c12_arr - np.mean(c12_arr)) / (np.std(c12_arr) + 1e-9)
    opt_z = (opt_arr - np.mean(opt_arr)) / (np.std(opt_arr) + 1e-9)
    
    # Find Options Volume Spikes (Z > 2.5)
    opt_spike_indices = np.where(opt_z > 2.5)[0]
    
    print(f"  Options volume spikes (Z > 2.5): {len(opt_spike_indices)}")
    
    offsets = []
    event_details = []
    
    for idx in opt_spike_indices:
        # Look T-3 to T+1 for peak Code 12 volume
        start = max(0, idx - 3)
        end = min(len(overlap), idx + 2)
        
        local_c12 = c12_series[start:end]
        if not local_c12: continue
        
        peak_c12_local_idx = int(np.argmax(local_c12))
        absolute_c12_idx = start + peak_c12_local_idx
        
        offset = int(absolute_c12_idx - idx)
        offsets.append(offset)
        event_details.append({
            "opt_spike_date": date_labels[idx],
            "c12_peak_date": date_labels[absolute_c12_idx],
            "offset_days": offset,
            "opt_z": round(float(opt_z[idx]), 2),
            "c12_vol": c12_series[absolute_c12_idx],
        })
        print(f"    Vol Spike: {date_labels[idx]} (Z={opt_z[idx]:.1f}) | C12 Peak: {date_labels[absolute_c12_idx]} | Offset: {offset:+d} days")

    offset_dist = {str(k): offsets.count(k) for k in sorted(set(offsets))} if offsets else {}
    
    t_minus_1 = offsets.count(-1)
    t_0 = offsets.count(0)
    t_minus_2 = offsets.count(-2)
    total = len(offsets)
    
    print(f"\n  Offset Distribution: {offset_dist}")
    print(f"  T-1 (C12 leads by 1 day): {t_minus_1}/{total} ({round(t_minus_1/max(1,total)*100,1)}%)")
    print(f"  T-0 (Same day): {t_0}/{total} ({round(t_0/max(1,total)*100,1)}%)")
    print(f"  T-2 (C12 leads by 2 days): {t_minus_2}/{total} ({round(t_minus_2/max(1,total)*100,1)}%)")
    
    lead_pct = round((t_minus_1 + t_minus_2) / max(1, total) * 100, 1)
    verdict = f"{lead_pct}% of option vol spikes preceded by C12 peak (T-1 or T-2). T-1={t_minus_1}, T-2={t_minus_2}, T0={t_0} of {total} events."
    print(f"\n  VERDICT: {verdict}")
    
    return {
        "total_spikes_evaluated": total,
        "offset_distribution": offset_dist,
        "t_minus_1_count": t_minus_1,
        "t_minus_2_count": t_minus_2,
        "t_0_count": t_0,
        "lead_pct": lead_pct,
        "event_details": event_details,
        "verdict": verdict,
    }


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 60)
    print("ROUND 9 TEST BATTERY — THE TAPE FRACTURE & PREMEDITATION")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    run_tests = set(sys.argv[1:]) if len(sys.argv) > 1 else {"T1", "T2", "T3", "T4"}
    
    out_path = RESULTS_DIR / "round9_test_results.json"
    
    if out_path.exists():
        with open(out_path, "r") as f:
            all_results = json.load(f)
        print(f"  Loaded {len(all_results)} existing results from prior run")
    else:
        all_results = {}

    if "T1" in run_tests:
        all_results["T1_zscored_cgd"] = test_t1_zscored_cgd()
    if "T2" in run_tests:
        all_results["T2_vanna_bimodality"] = test_t2_vanna_lag_bimodality()
    if "T3" in run_tests:
        all_results["T3_tape_fracture"] = test_t3_tape_fracture()
    if "T4" in run_tests:
        all_results["T4_code12_lead"] = test_t4_code12_t1_lead()

    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n" + "=" * 60)
    print(f"COMPLETE — Results saved to {out_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
