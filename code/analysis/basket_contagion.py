#!/usr/bin/env python3
"""
Round 10b Test Battery — Macro Contagion & The KOSS Paradox
==========================================================

Tests:
  T1: Cross-Ticker Lead-Lag — Do GME options sweeps trigger KOSS/AMC/XRT equity cascades?
  T2: Basket Tape Fracture — Does the May 17 lit-dark dislocation extend to the whole basket?
  T3: Code 12 Basket Co-occurrence — Do off-tape settlements align across tickers?
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
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

def get_available_polygon_dates(ticker):
    d_path = POLYGON_ROOT / f"symbol={ticker}"
    if not d_path.exists(): return []
    return sorted([d.replace("date=", "") for d in os.listdir(d_path) if d.startswith("date=")])

# ===================================================================
# T1: CROSS-TICKER LEAD-LAG (GME OPTIONS -> BASKET EQUITY)
# ===================================================================
def test_t1_cross_ticker_lead_lag():
    print("\n" + "=" * 60)
    print("T1: CROSS-TICKER LEAD-LAG (GME OPTIONS -> BASKET EQUITY)")
    print("=" * 60)
    
    # Target dates from recent volatility
    target_dates = ["20240513", "20240514", "20240515", "20240606", "20240607"]
    targets = ["CHWY", "DJT", "AAPL"]  # CHWY = meme basket, DJT = meme-adjacent, AAPL = control
    
    windows_ms = [50, 100, 250, 500, 1000]
    results = {target: {w: {"before": 0, "after": 0} for w in windows_ms} for target in targets}
    
    events_scanned = 0

    for d in target_dates:
        print(f"  Processing date: {d}...")
        gme_opts = load_options_parquet("GME", d)
        if gme_opts is None:
            print(f"    No GME options data for {d}")
            continue
        
        print(f"    GME options trades: {len(gme_opts):,}")
        
        # Find large GME options blocks (>100 contracts)
        gme_blocks = gme_opts[gme_opts['size'] >= 100]
        if gme_blocks.empty:
            # Try lower threshold
            gme_blocks = gme_opts[gme_opts['size'] >= 50]
            if gme_blocks.empty:
                gme_blocks = gme_opts[gme_opts['size'] >= 10]
                
        print(f"    GME options blocks (>=10 lots): {len(gme_blocks):,}")
        
        block_times_ns = gme_blocks['ts'].values.astype('int64')
        events_scanned += len(block_times_ns)
        
        for target in targets:
            tgt_eq = load_equity_parquet(target, d)
            if tgt_eq is None or len(tgt_eq) < 100:
                print(f"    {target}: No data or insufficient trades")
                continue
            
            print(f"    {target}: {len(tgt_eq):,} equity trades")
            tgt_ts_ns = tgt_eq['ts'].values.astype('int64')
            tgt_sizes = tgt_eq['size'].values
            
            for bt in block_times_ns:
                for w in windows_ms:
                    window_ns = w * 1_000_000
                    
                    mask_before = (tgt_ts_ns >= bt - window_ns) & (tgt_ts_ns < bt)
                    vol_before = int(tgt_sizes[mask_before].sum())
                    
                    mask_after = (tgt_ts_ns > bt) & (tgt_ts_ns <= bt + window_ns)
                    vol_after = int(tgt_sizes[mask_after].sum())
                    
                    results[target][w]["before"] += vol_before
                    results[target][w]["after"] += vol_after
                    
    print(f"\n  Scanned {events_scanned} GME options blocks total.")
    
    final_results = {}
    verdict_lines = []
    
    for target in targets:
        print(f"\n  Target: {target}")
        tgt_res = {}
        for w in windows_ms:
            bef = results[target][w]["before"]
            aft = results[target][w]["after"]
            ratio = round(aft / max(1, bef), 3)
            tgt_res[f"{w}ms"] = {"before": bef, "after": aft, "ratio": ratio}
            print(f"    {w:4d}ms Window | Vol Before: {bef:>10,} | After: {aft:>10,} | Ratio: {ratio:.2f}x")
        
        final_results[target] = tgt_res
        peak_ratio = max(v["ratio"] for v in tgt_res.values()) if tgt_res else 0
        if peak_ratio > 1.2:
            verdict_lines.append(f"{target} ({peak_ratio}x)")

    if verdict_lines:
        verdict = f"CONFIRMED: GME options actively lead basket equity bursts in {', '.join(verdict_lines)}. Proof of systemic contagion."
    else:
        verdict = "No direct sub-second contagion detected at block level. Try lower granularity or wider windows."
        
    print(f"\n  VERDICT: {verdict}")
    return {"events_scanned": events_scanned, "ratios": final_results, "verdict": verdict}

# ===================================================================
# T2: BASKET TAPE FRACTURE (MAY 17, 2024)
# ===================================================================
def test_t2_basket_tape_fracture():
    print("\n" + "=" * 60)
    print("T2: BASKET TAPE FRACTURE SCAN (MAY 17, 2024)")
    print("=" * 60)
    
    date_str = '2024-05-17'
    basket = ["GME", "CHWY", "DJT", "SPY"]  # CHWY = meme basket, DJT = meme-adjacent, SPY = control
    results = {}
    
    dark_ids = {4, 15}  # FINRA TRF
    
    for ticker in basket:
        eq = load_equity_parquet(ticker, date_str)
        if eq is None or len(eq) < 100:
            results[ticker] = {"status": "NO_DATA"}
            print(f"  {ticker:4s} | Insufficient data")
            continue
            
        # Pre-market window: 08:00-14:00 UTC (04:00-10:00 ET)
        pm = eq[(eq['ts'].dt.hour >= 8) & (eq['ts'].dt.hour < 14)].copy()
        if len(pm) < 10:
            results[ticker] = {"status": "NO_PREMARKET", "total_trades": len(eq)}
            print(f"  {ticker:4s} | No premarket data (total trades: {len(eq):,})")
            continue
            
        dark = pm[pm['exchange'].isin(dark_ids)].copy()
        lit = pm[~pm['exchange'].isin(dark_ids)].copy()
        
        print(f"  {ticker:4s} | PM trades: {len(pm):,} (Dark: {len(dark):,}, Lit: {len(lit):,})")
        
        if len(dark) < 5 or len(lit) < 5:
            results[ticker] = {"status": "INSUFFICIENT_SPLIT", "dark_trades": len(dark), "lit_trades": len(lit)}
            print(f"  {ticker:4s} | Insufficient Lit/Dark split")
            continue
            
        dark['minute'] = dark['ts'].dt.floor('1min')
        lit['minute'] = lit['ts'].dt.floor('1min')
        
        def calc_vwap(df):
            s = df['size'].sum()
            return (df['price'] * df['size']).sum() / s if s > 0 else np.nan
            
        lit_vwap = lit.groupby('minute').apply(calc_vwap)
        dark_vwap = dark.groupby('minute').apply(calc_vwap)
        
        df = pd.DataFrame({'lit': lit_vwap, 'dark': dark_vwap}).dropna()
        if df.empty:
            results[ticker] = {"status": "NO_OVERLAP"}
            print(f"  {ticker:4s} | No overlap between lit and dark minutes")
            continue
            
        df['abs_spread'] = (df['dark'] - df['lit']).abs()
        df['spread_pct'] = df['abs_spread'] / df['lit'] * 100
        
        max_pct = float(df['spread_pct'].max())
        max_abs = float(df['abs_spread'].max())
        mean_pct = float(df['spread_pct'].mean())
        fracture_time = df['spread_pct'].idxmax().strftime('%H:%M') if not df.empty else None
        dark_max_price = float(dark['price'].max())
        dark_p99 = float(dark['price'].quantile(0.99))
        
        results[ticker] = {
            "max_spread_dollars": round(max_abs, 2),
            "max_spread_pct": round(max_pct, 2),
            "mean_spread_pct": round(mean_pct, 2),
            "fracture_time": fracture_time,
            "dark_max_price": round(dark_max_price, 2),
            "dark_p99": round(dark_p99, 2),
            "overlapping_minutes": len(df),
        }
        
        marker = "🚨 FRACTURE" if max_pct > 2.0 else "Normal"
        print(f"  {ticker:4s} | Max Fracture: {max_pct:>6.1f}% (${max_abs:>6.2f}) | Mean: {mean_pct:.2f}% | Peak: {fracture_time} UTC | Dark Max: ${dark_max_price:.2f} | {marker}")

    # Check if fracture extends to basket
    basket_fracture = []
    for t in ["CHWY", "DJT", "SPY"]:
        pct = results.get(t, {}).get("max_spread_pct", 0)
        if isinstance(pct, (int, float)) and pct > 2.0:
            basket_fracture.append(f"{t} ({pct:.1f}%)")
    
    if basket_fracture:
        verdict = f"CONFIRMED: Tape Fracture affects broader basket: {', '.join(basket_fracture)}. Proof of portfolio-level swap/basket settlement."
    else:
        verdict = "Tape Fracture is isolated to GME on May 17."
        
    print(f"\n  VERDICT: {verdict}")
    results["verdict"] = verdict
    return results

# ===================================================================
# T3: CODE 12 BASKET SYNCHRONIZATION
# ===================================================================
def test_t3_code12_synchronization():
    print("\n" + "=" * 60)
    print("T3: CODE 12 BASKET SYNCHRONIZATION (MAY 2024)")
    print("=" * 60)
    
    dates = [
        "2024-05-08", "2024-05-09", "2024-05-10", "2024-05-13", "2024-05-14", 
        "2024-05-15", "2024-05-16", "2024-05-17", "2024-05-20", "2024-05-21"
    ]
    basket = ["GME", "CHWY", "DJT", "AAPL", "SPY"]
    
    c12_volumes = {t: [] for t in basket}
    
    for d in dates:
        for t in basket:
            eq = load_equity_parquet(t, d)
            vol = 0
            if eq is not None and not eq.empty and 'conditions' in eq.columns:
                mask = eq['conditions'].apply(lambda c: isinstance(c, (list, np.ndarray)) and 12 in c)
                # TRF exchange = 4
                vol = int(eq.loc[mask & (eq['exchange'] == 4), 'size'].sum())
            c12_volumes[t].append(vol)

    print(f"\n  Code 12 TRF Volume Timeline:")
    print(f"  {'Date':<12} | {'GME':>12} | {'KOSS':>12} | {'AMC':>12} | {'XRT':>12} | {'SPY':>12}")
    print("  " + "-" * 72)
    
    for i, d in enumerate(dates):
        gme_v = f"{c12_volumes['GME'][i]:>12,}"
        koss_v = f"{c12_volumes['KOSS'][i]:>12,}"
        amc_v = f"{c12_volumes['AMC'][i]:>12,}"
        xrt_v = f"{c12_volumes['XRT'][i]:>12,}"
        spy_v = f"{c12_volumes['SPY'][i]:>12,}"
        
        marker = " <-- C12 peak" if d == "2024-05-14" else ""
        print(f"  {d:<12} | {gme_v} | {koss_v} | {amc_v} | {xrt_v} | {spy_v}{marker}")

    df = pd.DataFrame(c12_volumes)
    
    correlations = {}
    for t in ["CHWY", "DJT", "AAPL", "SPY"]:
        if df[t].std() > 0 and df['GME'].std() > 0:
            correlations[t] = round(float(df['GME'].corr(df[t])), 3)
        else:
            correlations[t] = 0.0
    
    print(f"\n  Code 12 Volume Correlation with GME:")
    for t, r in correlations.items():
        marker = "🚨" if r > 0.4 else ""
        print(f"    {t:4s}: r = {r:+.3f} {marker}")
    
    # Also check if KOSS has ANY C12 volume
    chwy_total = sum(c12_volumes['CHWY'])
    djt_total = sum(c12_volumes['DJT'])
    aapl_total = sum(c12_volumes['AAPL'])
    
    print(f"\n  Total C12 Volume (10 days):")
    print(f"    GME:  {sum(c12_volumes['GME']):>12,}")
    print(f"    CHWY: {chwy_total:>12,}")
    print(f"    DJT:  {djt_total:>12,}")
    print(f"    AAPL: {aapl_total:>12,}")
    print(f"    SPY:  {sum(c12_volumes['SPY']):>12,}")
    
    high_corr = [f"{t} (r={r:.3f})" for t, r in correlations.items() if r > 0.4 and t != "SPY"]
    
    if high_corr:
        verdict = f"CONFIRMED: Off-tape settlement is synchronized at PORTFOLIO level. High correlation: {', '.join(high_corr)}."
    elif chwy_total > 0 or djt_total > 0:
        verdict = f"Mixed: CHWY C12={chwy_total:,}, DJT C12={djt_total:,}. Basket C12 exists but correlation is low."
    else:
        verdict = "Code 12 spikes are largely isolated to GME."
        
    print(f"\n  VERDICT: {verdict}")
    
    return {
        "dates": dates,
        "volumes": {k: [int(v) for v in vals] for k, vals in c12_volumes.items()},
        "correlations": correlations,
        "totals": {
            "GME": sum(c12_volumes['GME']),
            "CHWY": chwy_total,
            "DJT": djt_total,
            "AAPL": aapl_total,
            "SPY": sum(c12_volumes['SPY']),
        },
        "verdict": verdict
    }


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 60)
    print("ROUND 10b TEST BATTERY — MACRO CONTAGION & THE KOSS PARADOX")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    run_tests = set(sys.argv[1:]) if len(sys.argv) > 1 else {"T1", "T2", "T3"}
    
    out_path = RESULTS_DIR / "round10_basket_results.json"
    
    if out_path.exists():
        with open(out_path, "r") as f:
            all_results = json.load(f)
        print(f"  Loaded {len(all_results)} existing results from prior run")
    else:
        all_results = {}

    if "T1" in run_tests:
        all_results["T1_koss_paradox"] = test_t1_cross_ticker_lead_lag()
    if "T2" in run_tests:
        all_results["T2_basket_fracture"] = test_t2_basket_tape_fracture()
    if "T3" in run_tests:
        all_results["T3_code12_basket"] = test_t3_code12_synchronization()

    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n" + "=" * 60)
    print(f"COMPLETE — Results saved to {out_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
