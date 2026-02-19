#!/usr/bin/env python3
"""
Phase 12 Vector 1: ETF Cannibalization — XRT Share Destruction Analysis
Tests whether XRT shares outstanding correlate with GME/KOSS settlement events.

Approach:
1. Pull XRT daily fund data (shares outstanding / NAV) from polygon
2. Look for redemption spikes (SO decreases) around May 13-17 2024
3. Compare with Jan 2021 squeeze period
4. Correlate with FTD collapse pattern
"""
import json, sys, time
from pathlib import Path
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("ERROR: requests library required")
    sys.exit(1)

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: pandas/numpy required")
    sys.exit(1)

OUT_DIR = Path(__file__).parent
REPO_ROOT = Path(__file__).resolve().parents[2]
FTD_DIR = REPO_ROOT / "data" / "raw" / "sec_ftd"

def load_ftd(ticker):
    path = FTD_DIR / f"{ticker}_ftd.json"
    if not path.exists(): return None
    with open(path) as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df = df.groupby('date').agg({'quantity': 'sum', 'price': 'mean'}).reset_index()
    return df.sort_values('date')

# ===================================================================
# XRT SHARES OUTSTANDING from Polygon
# ===================================================================
print("="*70)
print("PHASE 12 V1: XRT ETF CANNIBALIZATION ANALYSIS")
print("="*70)

# Try to get XRT shares outstanding and fund flows
# Method 1: Use Polygon reference data API
# Method 2: Calculate from AUM/NAV if available  
# Method 3: Use known public data points

# XRT is SPDR S&P Retail ETF managed by State Street
# Daily shares out are reported in Bloomberg/FactSet but we can derive from Polygon

# Let's look at what XRT data we have locally first
xrt_data_path = REPO_ROOT / "data" / "raw" / "polygon" / "trades" / "symbol=XRT"
print(f"\n  XRT local data: {xrt_data_path.exists()}")

if xrt_data_path.exists():
    dates = sorted([d.name for d in xrt_data_path.iterdir() if d.is_dir()])
    print(f"  Available dates: {len(dates)}")
    if dates:
        print(f"  Range: {dates[0]} to {dates[-1]}")

# Approach: We don't have SO data directly, but we can find signals
# from the FTD data + Polygon volume data

# XRT FTD timeline around events
print("\n  === XRT FTD Timeline ===")
xrt_ftd = load_ftd("XRT")
gme_ftd = load_ftd("GME")
koss_ftd = load_ftd("KOSS")

if xrt_ftd is not None:
    # MAY 2024 WINDOW
    print("\n  --- May 2024 Window ---")
    m24 = xrt_ftd[(xrt_ftd['date'] >= '2024-05-01') & (xrt_ftd['date'] <= '2024-05-31')]
    g24 = gme_ftd[(gme_ftd['date'] >= '2024-05-01') & (gme_ftd['date'] <= '2024-05-31')] if gme_ftd is not None else pd.DataFrame()
    k24 = koss_ftd[(koss_ftd['date'] >= '2024-05-01') & (koss_ftd['date'] <= '2024-05-31')] if koss_ftd is not None else pd.DataFrame()
    
    print(f"  {'Date':<12} | {'XRT FTDs':>12} | {'GME FTDs':>12} | {'KOSS FTDs':>12}")
    print("  " + "-"*60)
    
    all_dates = sorted(set(
        list(m24['date'].values) + 
        list(g24['date'].values if not g24.empty else []) +
        list(k24['date'].values if not k24.empty else [])
    ))
    
    xrt_may_vals = []
    gme_may_vals = []
    koss_may_vals = []
    
    for d in all_dates:
        xv = int(m24[m24['date'] == d]['quantity'].sum()) if not m24[m24['date'] == d].empty else 0
        gv = int(g24[g24['date'] == d]['quantity'].sum()) if not g24.empty and not g24[g24['date'] == d].empty else 0
        kv = int(k24[k24['date'] == d]['quantity'].sum()) if not k24.empty and not k24[k24['date'] == d].empty else 0
        
        ds = pd.Timestamp(d).strftime('%Y-%m-%d')
        marker = ""
        if ds == "2024-05-13": marker = " <-- RK Return"
        elif ds == "2024-05-14": marker = " <-- Conversions"
        elif ds == "2024-05-15": marker = " <-- T+1"
        elif ds == "2024-05-17": marker = " <-- OpEx"
        
        print(f"  {ds:<12} | {xv:>12,} | {gv:>12,} | {kv:>12,}{marker}")
        xrt_may_vals.append(xv)
        gme_may_vals.append(gv)
        koss_may_vals.append(kv)
    
    # Correlation
    if len(xrt_may_vals) > 3:
        xrt_arr = np.array(xrt_may_vals, dtype=float)
        gme_arr = np.array(gme_may_vals, dtype=float)
        koss_arr = np.array(koss_may_vals, dtype=float)
        
        if xrt_arr.std() > 0 and gme_arr.std() > 0:
            xrt_gme_corr = np.corrcoef(xrt_arr, gme_arr)[0,1]
            print(f"\n  XRT-GME FTD correlation (May 2024): {xrt_gme_corr:.3f}")
        if xrt_arr.std() > 0 and koss_arr.std() > 0:
            xrt_koss_corr = np.corrcoef(xrt_arr, koss_arr)[0,1]
            print(f"  XRT-KOSS FTD correlation (May 2024): {xrt_koss_corr:.3f}")
    
    # JANUARY 2021 WINDOW
    print("\n  --- January 2021 Window ---")
    m21 = xrt_ftd[(xrt_ftd['date'] >= '2021-01-04') & (xrt_ftd['date'] <= '2021-02-15')]
    g21 = gme_ftd[(gme_ftd['date'] >= '2021-01-04') & (gme_ftd['date'] <= '2021-02-15')] if gme_ftd is not None else pd.DataFrame()
    k21 = koss_ftd[(koss_ftd['date'] >= '2021-01-04') & (koss_ftd['date'] <= '2021-02-15')] if koss_ftd is not None else pd.DataFrame()
    
    print(f"  {'Date':<12} | {'XRT FTDs':>12} | {'GME FTDs':>12} | {'KOSS FTDs':>12}")
    print("  " + "-"*60)
    
    all_dates_21 = sorted(set(
        list(m21['date'].values) +
        list(g21['date'].values if not g21.empty else []) +
        list(k21['date'].values if not k21.empty else [])
    ))
    
    xrt_jan_vals = []
    gme_jan_vals = []
    koss_jan_vals = []
    
    for d in all_dates_21:
        xv = int(m21[m21['date'] == d]['quantity'].sum()) if not m21[m21['date'] == d].empty else 0
        gv = int(g21[g21['date'] == d]['quantity'].sum()) if not g21.empty and not g21[g21['date'] == d].empty else 0
        kv = int(k21[k21['date'] == d]['quantity'].sum()) if not k21.empty and not k21[k21['date'] == d].empty else 0
        
        ds = pd.Timestamp(d).strftime('%Y-%m-%d')
        marker = ""
        if ds == "2021-01-27": marker = " <-- Peak squeeze"
        elif ds == "2021-01-28": marker = " <-- Buy button off"
        elif ds == "2021-01-29": marker = " <-- Aftermath"
        
        print(f"  {ds:<12} | {xv:>12,} | {gv:>12,} | {kv:>12,}{marker}")
        xrt_jan_vals.append(xv)
        gme_jan_vals.append(gv)
        koss_jan_vals.append(kv)
    
    if len(xrt_jan_vals) > 3:
        xrt_arr = np.array(xrt_jan_vals, dtype=float)
        gme_arr = np.array(gme_jan_vals, dtype=float)
        koss_arr = np.array(koss_jan_vals, dtype=float)
        
        if xrt_arr.std() > 0 and gme_arr.std() > 0:
            c = np.corrcoef(xrt_arr, gme_arr)[0,1]
            print(f"\n  XRT-GME FTD correlation (Jan 2021): {c:.3f}")
        if xrt_arr.std() > 0 and koss_arr.std() > 0:
            c = np.corrcoef(xrt_arr, koss_arr)[0,1]
            print(f"  XRT-KOSS FTD correlation (Jan 2021): {c:.3f}")

    # XRT FTD surge analysis: pre vs during vs post event
    print("\n  === XRT FTD Surge Analysis ===")
    
    for label, start, end, peak_start, peak_end in [
        ("May 2024", "2024-04-01", "2024-06-30", "2024-05-13", "2024-05-17"),
        ("Jan 2021", "2020-12-01", "2021-03-15", "2021-01-25", "2021-01-29"),
    ]:
        bl = xrt_ftd[(xrt_ftd['date'] >= start) & (xrt_ftd['date'] < peak_start)]
        ev = xrt_ftd[(xrt_ftd['date'] >= peak_start) & (xrt_ftd['date'] <= peak_end)]
        post = xrt_ftd[(xrt_ftd['date'] > peak_end) & (xrt_ftd['date'] <= end)]
        
        bl_avg = bl['quantity'].mean() if not bl.empty else 0
        ev_avg = ev['quantity'].mean() if not ev.empty else 0
        post_avg = post['quantity'].mean() if not post.empty else 0
        
        ev_max = int(ev['quantity'].max()) if not ev.empty else 0
        
        print(f"\n  {label}:")
        print(f"    Pre-event avg:  {bl_avg:>12,.0f}")
        print(f"    Event avg:      {ev_avg:>12,.0f} ({ev_avg/max(1,bl_avg):.1f}x)")
        print(f"    Event max:      {ev_max:>12,}")
        print(f"    Post-event avg: {post_avg:>12,.0f} ({post_avg/max(1,bl_avg):.1f}x)")

else:
    print("  No XRT FTD data available")

# Save results
results = {
    "may_2024": {
        "xrt_ftds": xrt_may_vals if xrt_ftd is not None else [],
        "gme_ftds": gme_may_vals if xrt_ftd is not None else [],
        "koss_ftds": koss_may_vals if xrt_ftd is not None else [],
    },
    "jan_2021": {
        "xrt_ftds": xrt_jan_vals if xrt_ftd is not None else [],
        "gme_ftds": gme_jan_vals if xrt_ftd is not None else [],
        "koss_ftds": koss_jan_vals if xrt_ftd is not None else [],
    }
}

out_path = OUT_DIR / "round12_v1_etf_cannibalization.json"
with open(out_path, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
