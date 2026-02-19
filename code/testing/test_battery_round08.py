#!/usr/bin/env python3
"""
Round 8 Test Battery — Advanced Predictors & Structural Forensics
=================================================================

Tests:
  T1: Rolling CGD (20-day window) — Eliminates the cumulative mechanical breach flaw.
  T2: Expanded Vanna Lag Scan — Full GME date history.
  T3: Price Impact by Regime — Split 34ms cascade CPI into Pre/Post CGD Breach.
  T4: CGD Velocity Metric — Compute dR/dt to predict explosion magnitude.
  T5: Code 12 Volume Clustering — Code 12 volume vs options volatility
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import deque

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

def _is_call(df):
    if 'right' in df.columns:
        return df['right'].str.upper().str.startswith('C')
    return pd.Series([True] * len(df), index=df.index)

# ===================================================================
# T1 & T4: ROLLING CGD (20-DAY WINDOW) & VELOCITY (dR/dt)
# ===================================================================
def test_t1_t4_rolling_cgd_and_velocity():
    print("\n" + "=" * 60)
    print("T1 & T4: ROLLING CGD (20-DAY WINDOW) & VELOCITY (dR/dt)")
    print("=" * 60)
    
    if not THETA_ROOT.exists():
        print("  Options data directory not found.")
        return {"status": "NO_DATA"}

    tickers = sorted([d.replace("root=", "") for d in os.listdir(THETA_ROOT) if d.startswith("root=")])
    skip = {"IWM", "QQQ", "SPY", "NAKA", "BNED", "GROV", "IHRT", "NWL"}
    tickers = [t for t in tickers if t not in skip]
    
    results = {}
    
    for ticker in tickers:
        dates = get_available_theta_dates(ticker)
        if len(dates) < 25:
            continue
            
        rolling_k = deque(maxlen=20)
        peak_r = 0.0
        peak_velocity = 0.0
        breach_date = None
        prev_r = 0.0
        
        for d in dates:
            opts = load_options_parquet(ticker, d)
            if opts is None: continue
            
            opts = _compute_dte(opts, d)
            if 'dte' not in opts.columns: continue
            
            day_kinetic = int(opts[opts['dte'].between(0, 7)]['size'].sum())
            rolling_k.append(day_kinetic)
            
            long_dated = opts[opts['dte'] > 7]
            e_stored = float((long_dated['size'] * long_dated['dte']).sum())
            
            if e_stored < 1000 or len(rolling_k) < 20:
                continue
                
            r = sum(rolling_k) / e_stored
            velocity = r - prev_r
            prev_r = r
            
            if r > peak_r: peak_r = r
            if velocity > peak_velocity: peak_velocity = velocity
            
            if r >= 1.0 and breach_date is None:
                breach_date = d
                
        results[ticker] = {
            "dates_available": len(dates),
            "peak_rolling_R": round(peak_r, 4),
            "peak_velocity_dR_dt": round(peak_velocity, 4),
            "breach_date": breach_date,
            "breached": breach_date is not None
        }
        status = f"Peak R={peak_r:.2f} | Peak dR/dt={peak_velocity:.3f} | Breach={breach_date or 'NONE'}"
        print(f"    {ticker:6s}: {status}")

    breached = [t for t, r in results.items() if r.get("breached")]
    not_breached = [t for t, r in results.items() if not r.get("breached")]
    fp_rate = round(len(breached) / len(results) * 100, 1) if results else 0
    
    print(f"\n  SUMMARY:")
    print(f"    Total tickers analyzed: {len(results)}")
    print(f"    Tickers with R_rolling >= 1.0: {len(breached)} ({', '.join(breached) or 'NONE'})")
    print(f"    Tickers without breach: {len(not_breached)}")
    
    verdict = f"Rolling CGD FP Rate: {fp_rate}% ({len(breached)}/{len(results)} tickers breach R_rolling >= 1.0)."
    print(f"\n  VERDICT: {verdict}")
    return {
        "tickers_analyzed": len(results),
        "false_positive_rate_pct": fp_rate,
        "breached_tickers": breached,
        "not_breached_tickers": not_breached,
        "per_ticker": results,
        "verdict": verdict,
    }

# ===================================================================
# T2: EXPANDED VANNA LAG SCAN
# ===================================================================
def test_t2_expanded_vanna_lag():
    print("\n" + "=" * 60)
    print("T2: EXPANDED VANNA LAG SCAN (FULL GME HISTORY)")
    print("=" * 60)
    
    dates = get_available_theta_dates("GME")
    all_lags = []
    events_found = 0
    scanned = 0
    
    for d in dates:
        opts = load_options_parquet("GME", d)
        if opts is None or len(opts) < 100: continue
        
        opts = _compute_dte(opts, d)
        if 'dte' not in opts.columns: continue
        
        call_mask = _is_call(opts)
        short_otm = opts[(opts['dte'].between(0, 7)) & call_mask].copy()
        leaps = opts[opts['dte'] >= 90].copy()
        
        if len(short_otm) < 10 or len(leaps) < 5: continue
        
        short_otm['minute'] = short_otm['ts'].dt.floor('1min')
        short_min = short_otm.groupby('minute')['size'].sum()
        
        leaps['minute'] = leaps['ts'].dt.floor('1min')
        leaps_min = leaps.groupby('minute')['size'].sum()
        
        s_mean, s_std = short_min.mean(), short_min.std()
        l_mean, l_std = leaps_min.mean(), leaps_min.std()
        
        if s_std < 1 or l_std < 1: continue
        
        s_thresh = s_mean + 3 * s_std
        l_thresh = l_mean + 3 * l_std
        
        spike_mins = short_min[short_min > s_thresh].index
        
        for spike_t in spike_mins:
            for lag_min in range(1, 16):
                check_t = spike_t + pd.Timedelta(minutes=lag_min)
                if check_t in leaps_min.index and leaps_min[check_t] > l_thresh:
                    all_lags.append(lag_min)
                    events_found += 1
                    break
                    
        scanned += 1
        if scanned % 100 == 0:
            print(f"    Scanned {scanned}/{len(dates)} dates... found {events_found} events")

    if not all_lags:
        print("  No Vanna Lag events found.")
        return {"events": 0, "dates_scanned": scanned, "verdict": "No Vanna Lag events across full history."}
        
    lag_arr = np.array(all_lags)
    dist = {str(k): int(v) for k, v in zip(*np.unique(lag_arr, return_counts=True))}
    pct_3_5 = round(float(np.mean((lag_arr >= 3) & (lag_arr <= 5)) * 100), 1)
    pct_7_9 = round(float(np.mean((lag_arr >= 7) & (lag_arr <= 9)) * 100), 1)
    median_lag = round(float(np.median(lag_arr)), 1)
    mean_lag = round(float(np.mean(lag_arr)), 2)
    
    print(f"\n  GME: {events_found} total Vanna Lag events across {scanned} dates.")
    print(f"  Median lag: {median_lag} min | Mean lag: {mean_lag} min")
    print(f"  % in 3-5 min: {pct_3_5}% | % in 7-9 min: {pct_7_9}%")
    print(f"  Distribution: {dist}")
    
    verdict = f"{events_found} events, median={median_lag}min, 3-5min window={pct_3_5}%, 7-9min window={pct_7_9}%"
    print(f"\n  VERDICT: {verdict}")
    
    return {
        "events": events_found,
        "dates_scanned": scanned,
        "median_lag_min": median_lag,
        "mean_lag_min": mean_lag,
        "pct_in_3_5_window": pct_3_5,
        "pct_in_7_9_window": pct_7_9,
        "lag_distribution": dist,
        "verdict": verdict,
    }

# ===================================================================
# T3: PRICE IMPACT BY DATE REGIME (PRE/POST CGD BREACH)
# ===================================================================
def test_t3_regime_price_impact():
    print("\n" + "=" * 60)
    print("T3: PRICE IMPACT BY REGIME (PRE vs POST CGD BREACH)")
    print("=" * 60)
    
    # We use Jan 2021 and June 2024 windows. 
    # Breach dates from R7: Jan 13, 2021 and May 15, 2024.
    all_eq_dates = get_available_polygon_dates("GME")
    pre_breach_dates = [d for d in all_eq_dates 
                        if ("2020-12-01" <= d <= "2021-01-12") or ("2024-04-01" <= d <= "2024-05-14")]
    post_breach_dates = [d for d in all_eq_dates 
                         if ("2021-01-13" <= d <= "2021-01-29") or ("2024-05-15" <= d <= "2024-06-14")]
    
    print(f"  Pre-breach dates available: {len(pre_breach_dates)}")
    print(f"  Post-breach dates available: {len(post_breach_dates)}")
    
    def get_cpi_for_dates(date_list, label=""):
        cpi_list = []
        for i, d in enumerate(date_list):
            eq = load_equity_parquet('GME', d)
            if eq is None or len(eq) < 100: continue
            
            # Filter regular hours
            eq = eq[(eq['ts'].dt.hour >= 14) & (eq['ts'].dt.hour < 21)]
            if len(eq) < 50: continue
            
            ts_ns = eq['ts'].values.astype('int64')
            prices = eq['price'].values
            
            sort_idx = np.argsort(ts_ns)
            ts_ns = ts_ns[sort_idx]
            prices = prices[sort_idx]
            
            n = len(ts_ns)
            j = 0
            for ii in range(n - 2):
                while j < n and ts_ns[j] - ts_ns[ii] <= 34_000_000:
                    j += 1
                if j - ii >= 3 and prices[j-1] < prices[ii]:
                    cpi = (prices[j-1] - prices[ii]) / prices[ii] * 10000
                    cpi_list.append(cpi)
            
            if (i + 1) % 5 == 0:
                print(f"    {label} scanned {i+1}/{len(date_list)} dates, {len(cpi_list)} cascades...")
        return cpi_list

    pre_cpi = get_cpi_for_dates(pre_breach_dates, "Pre-breach")
    post_cpi = get_cpi_for_dates(post_breach_dates, "Post-breach")
    
    pre_med = round(float(np.median(pre_cpi)), 4) if pre_cpi else 0
    post_med = round(float(np.median(post_cpi)), 4) if post_cpi else 0
    pre_mean = round(float(np.mean(pre_cpi)), 4) if pre_cpi else 0
    post_mean = round(float(np.mean(post_cpi)), 4) if post_cpi else 0
    
    print(f"\n  Pre-Breach (R < 1.0):  {len(pre_cpi)} cascades | Median CPI: {pre_med:.2f} bps | Mean: {pre_mean:.2f} bps")
    print(f"  Post-Breach (R >= 1.0): {len(post_cpi)} cascades | Median CPI: {post_med:.2f} bps | Mean: {post_mean:.2f} bps")
    
    if pre_med != 0 and abs(post_med) > abs(pre_med):
        ratio = round(abs(post_med) / abs(pre_med), 2)
        verdict = f"Price impact SPIKES {ratio}× after Confinement Field fails. Pre={pre_med:.2f} bps → Post={post_med:.2f} bps."
    elif pre_med != 0:
        ratio = round(abs(post_med) / abs(pre_med), 2)
        verdict = f"Post/Pre ratio = {ratio}×. Pre={pre_med:.2f} bps, Post={post_med:.2f} bps."
    else:
        verdict = "Insufficient pre-breach cascade data."
        
    print(f"\n  VERDICT: {verdict}")
    return {
        "pre_breach_cascades": len(pre_cpi),
        "post_breach_cascades": len(post_cpi),
        "pre_cpi_median_bps": pre_med,
        "post_cpi_median_bps": post_med,
        "pre_cpi_mean_bps": pre_mean,
        "post_cpi_mean_bps": post_mean,
        "verdict": verdict,
    }

# ===================================================================
# T5: CODE 12 VOLUME CLUSTERING
# ===================================================================
def test_t5_code12_volume_clustering():
    print("\n" + "=" * 60)
    print("T5: CODE 12 VOLUME CLUSTERING (GME)")
    print("=" * 60)
    
    theta_dates = set(get_available_theta_dates("GME"))
    polygon_dates_raw = get_available_polygon_dates("GME")
    polygon_dates_yyyymmdd = set([d.replace("-","") for d in polygon_dates_raw])
    overlap = sorted(theta_dates & polygon_dates_yyyymmdd)
    
    print(f"  Overlapping dates: {len(overlap)}")
    
    code12_vols = []
    opt_vols = []
    date_labels = []
    
    for i, d in enumerate(overlap):
        eq = load_equity_parquet("GME", d)
        opts = load_options_parquet("GME", d)
        if eq is None or opts is None: continue
        
        c12_vol = 0
        if 'conditions' in eq.columns:
            mask = eq['conditions'].apply(lambda c: isinstance(c, (list, np.ndarray)) and 12 in c)
            c12_vol = int(eq.loc[mask, 'size'].sum())
            
        code12_vols.append(c12_vol)
        opt_vols.append(int(opts['size'].sum()))
        date_labels.append(d)
        
        if (i+1) % 100 == 0:
            print(f"    Scanned {i+1}/{len(overlap)} dates...")

    if len(code12_vols) < 10:
        print("  Insufficient data.")
        return {"status": "INSUFFICIENT_DATA"}
    
    arr_c12 = np.array(code12_vols, dtype=float)
    arr_opt = np.array(opt_vols, dtype=float)
    
    # Calculate correlation
    corr = round(float(np.corrcoef(arr_c12, arr_opt)[0, 1]), 4)
    
    # Identify top 10 Code 12 days
    top_idx = np.argsort(arr_c12)[-10:][::-1]
    top_days = [(date_labels[idx], int(arr_c12[idx]), int(arr_opt[idx])) for idx in top_idx]
    
    # Percentage of days with Code 12 volume
    days_with_c12 = int(np.sum(arr_c12 > 0))
    pct_with_c12 = round(days_with_c12 / len(arr_c12) * 100, 1)
    
    # Volume stats
    c12_mean = round(float(arr_c12.mean()), 0)
    c12_median = round(float(np.median(arr_c12)), 0)
    c12_p95 = round(float(np.percentile(arr_c12, 95)), 0)
    
    print(f"\n  Code 12 Volume ↔ Options Volume Correlation: r = {corr}")
    print(f"  Days with Code 12 activity: {days_with_c12}/{len(arr_c12)} ({pct_with_c12}%)")
    print(f"  Code 12 volume: mean={c12_mean:,.0f}, median={c12_median:,.0f}, p95={c12_p95:,.0f}")
    print(f"\n  Top 10 Code 12 Volume Days:")
    for d, c12v, optv in top_days:
        print(f"    {d}: Code12={c12v:>12,} shares | Options={optv:>10,} contracts")
    
    verdict = f"Code 12 ↔ Options r={corr}. {pct_with_c12}% of days show Code 12. Mean vol={c12_mean:,.0f} shares."
    print(f"\n  VERDICT: {verdict}")
    
    return {
        "dates_analyzed": len(arr_c12),
        "correlation": corr,
        "days_with_code12": days_with_c12,
        "pct_with_code12": pct_with_c12,
        "code12_mean_vol": c12_mean,
        "code12_median_vol": c12_median,
        "code12_p95_vol": c12_p95,
        "top_10_days": [{"date": d, "code12_vol": v, "options_vol": o} for d, v, o in top_days],
        "verdict": verdict,
    }

# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 60)
    print("ROUND 8 TEST BATTERY — PREDICTIVE MODELS & FORENSICS")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    run_tests = set(sys.argv[1:]) if len(sys.argv) > 1 else {"T1", "T2", "T3", "T5"}
    
    out_path = RESULTS_DIR / "round8_test_results.json"
    
    if out_path.exists():
        with open(out_path, "r") as f:
            all_results = json.load(f)
        print(f"  Loaded {len(all_results)} existing results from prior run")
    else:
        all_results = {}

    if "T1" in run_tests:
        all_results["T1_T4_rolling_cgd_velocity"] = test_t1_t4_rolling_cgd_and_velocity()
    if "T2" in run_tests:
        all_results["T2_expanded_vanna_lag"] = test_t2_expanded_vanna_lag()
    if "T3" in run_tests:
        all_results["T3_regime_price_impact"] = test_t3_regime_price_impact()
    if "T5" in run_tests:
        all_results["T5_code12_volume"] = test_t5_code12_volume_clustering()

    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n" + "=" * 60)
    print(f"COMPLETE — Results saved to {out_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
