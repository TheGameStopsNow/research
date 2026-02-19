#!/usr/bin/env python3
"""
Zombie Basket Correlation — Rigorous Empirical Shift Testing
============================================================
This script resolves the "massive volume" statistical trap by using an Empirical Shift Test.
When trade volumes reach millions of prints per day (e.g. GME 90M shares on Jan 27),
basic mathematical probability models overstate significance due to volatility clustering.

Methodology to Withstand Scrutiny:
1. Fetch RTH-only trades (9:30 AM to 4:00 PM ET) to ensure proper temporal overlap.
2. Run merge_asof at 0-Lag offset (the real correlation).
3. Offset the secondary series artificially (e.g., ±1s, ±5s, ±60s) and rerun merge_asof.
   This establishes an empirical "background noise floor" of random clustering overlaps.
4. Calculate a Z-Score for the 0-Lag correlation against the background permutations.
5. Compare the Meme Basket pairs against High-Volume Controls (AAPL, SPY) to filter out
   market-wide SIP (Consolidated Tape) batching artifacts.

Author: Antigravity / Power Tracks Research
"""

import time
import requests
import pandas as pd
import numpy as np
from pathlib import Path

# Config
import os
API_KEY = os.environ.get("POLYGON_API_KEY", "")
if not API_KEY:
    raise RuntimeError("Set POLYGON_API_KEY environment variable before running.")
OUTPUT_DIR = Path(__file__).parent / "tick_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATE = "2021-01-27"
RTH_START = f"{DATE}T14:30:00Z"
RTH_END = f"{DATE}T21:00:00Z"

def safe_sort(df, col="timestamp"):
    if df.empty or col not in df.columns: return df
    idx = np.argsort(df[col].values)
    return df.iloc[idx].reset_index(drop=True)

def load_cached_or_fetch(symbol):
    cached = OUTPUT_DIR / f"{symbol}_{DATE}_rth_trades.parquet"
    if cached.exists():
        return pd.read_parquet(cached)

    print(f"[{symbol}] Fetching from Polygon API...")
    url = f"https://api.polygon.io/v3/trades/{symbol}"
    params = {
        "timestamp.gte": RTH_START,
        "timestamp.lte": RTH_END,
        "limit": 50000, "sort": "timestamp", "order": "asc",
        "apiKey": API_KEY,
    }
    all_results = []
    page = 0
    while True:
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                time.sleep(15)
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            break
        
        results = data.get("results", [])
        if not results: break
        all_results.extend(results)
        
        next_url = data.get("next_url")
        if not next_url: break
        url = next_url
        params = {"apiKey": API_KEY}
        time.sleep(0.25)

    if not all_results: return pd.DataFrame()
    
    df = pd.DataFrame(all_results)
    ts_col = next((c for c in ["sip_timestamp", "participant_timestamp", "t"] if c in df.columns), None)
    if ts_col: df["timestamp"] = pd.to_datetime(df[ts_col], unit="ns")
    if "p" in df.columns: df["price"] = df["p"]
    if "s" in df.columns: df["size"] = df["s"]
    df["symbol"] = symbol
    df = safe_sort(df)
    keep = df[["timestamp", "price", "size", "symbol"]]
    keep.to_parquet(cached, index=False)
    return keep

def run_empirical_shift_test(df_primary, df_secondary, primary_sym, secondary_sym, tol="1ms"):
    if df_primary.empty or df_secondary.empty: return None
    
    # We use very close offsets and larger offsets to capture the local clustering noise
    shifts = [0, -0.1, 0.1, -1, 1, -5, 5, -60, 60]
    tolerance = pd.Timedelta(tol)
    
    left = safe_sort(df_primary[["timestamp", "price"]].rename(columns={"price": f"p_{primary_sym}"}).copy())
    
    results = {}
    for shift_sec in shifts:
        right = df_secondary[["timestamp", "price"]].rename(columns={"price": f"p_{secondary_sym}"}).copy()
        if shift_sec != 0:
            right["timestamp"] = right["timestamp"] + pd.Timedelta(seconds=shift_sec)
        right = safe_sort(right)
        
        merged = pd.merge_asof(left, right, on="timestamp", tolerance=tolerance, direction="nearest")
        matches = merged[f"p_{secondary_sym}"].notna().sum()
        results[f"shift_{shift_sec}s"] = int(matches)
        
    bg_shifts = [results[k] for k in results if k != "shift_0s"]
    bg_mean = np.mean(bg_shifts)
    bg_std = np.std(bg_shifts) if np.std(bg_shifts) > 0 else 1.0
    
    z_score = (results["shift_0s"] - bg_mean) / bg_std
    
    return {
        "pair": f"{primary_sym}↔{secondary_sym}",
        "matches_0s": results["shift_0s"],
        "bg_mean": bg_mean,
        "bg_std": bg_std,
        "z_score": z_score
    }

def main():
    print("Loading datasets...")
    symbols = ["GME", "AMC", "KOSS", "BBBY", "AAPL", "SPY"]
    data = {sym: load_cached_or_fetch(sym) for sym in symbols}
    
    print("\nRunning Empirical Shift Test at 1ms Tolerance...")
    test_pairs = [
        ("GME", "AMC"), ("GME", "KOSS"), ("KOSS", "AMC"),
        ("GME", "BBBY"), ("AMC", "BBBY"), ("KOSS", "BBBY"),
        ("GME", "AAPL"), ("GME", "SPY"),
    ]
    
    report = []
    for sym_a, sym_b in test_pairs:
        res = run_empirical_shift_test(data[sym_a], data[sym_b], sym_a, sym_b, tol="1ms")
        if res:
            report.append(res)
            print(f"  {res['pair']:12s} | Z-Score: {res['z_score']:5.2f} | 0-Lag: {res['matches_0s']:,} vs BG: {res['bg_mean']:,.0f}")
            
    df_report = pd.DataFrame(report)
    df_report.to_csv(OUTPUT_DIR / "rigorous_controls_1ms.csv", index=False)
    print("\nComplete.")

if __name__ == "__main__":
    main()
