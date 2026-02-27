#!/usr/bin/env python3
"""
Vector 1: Full Swap Basket Reconstruction
Run M4 C12 Timestamp Overlap across extended meme basket to find the "Missing 40 Minutes"
"""
import json, numpy as np, pandas as pd, time
from pathlib import Path

POLYGON_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "polygon" / "trades"

# Extended basket — everything we have in Polygon
BASKET = ["GME", "KOSS", "AMC", "CHWY", "DJT", "IWM", "AAPL", "SPY"]

def load_eq(ticker, date_str):
    path = POLYGON_ROOT / f"symbol={ticker}" / f"date={date_str}" / "part-0.parquet"
    if not path.exists(): return None
    df = pd.read_parquet(path)
    ts_col = 'timestamp' if 'timestamp' in df.columns else 'sip_timestamp'
    df['ts'] = pd.to_datetime(df[ts_col])
    if df['ts'].dt.tz is not None: df['ts'] = df['ts'].dt.tz_localize(None)
    return df

def get_c12_minutes(df):
    """Get C12 minutes and volume for a dataframe"""
    trf = df[df['exchange'] == 4].copy()
    if trf.empty: return set(), 0
    mask = trf['conditions'].apply(lambda c: 12 in c if isinstance(c, (list, np.ndarray)) else False)
    c12 = trf[mask]
    if c12.empty: return set(), 0
    return set(c12['ts'].dt.floor('1min')), int(c12['size'].sum())

results = {}
dates = ["2024-05-13", "2024-05-14"]

for d in dates:
    print(f"\n{'='*60}")
    print(f"  DATE: {d}")
    print(f"{'='*60}")
    
    # Load GME C12 minutes as reference
    gme = load_eq("GME", d)
    if gme is None:
        print("  GME: NO DATA"); continue
    gme_c12_min, gme_c12_vol = get_c12_minutes(gme)
    print(f"  GME: {len(gme_c12_min)} C12 minutes, {gme_c12_vol:,} shares")
    
    date_results = {"GME": {"minutes": len(gme_c12_min), "volume": gme_c12_vol}}
    
    for ticker in BASKET:
        if ticker == "GME": continue
        
        eq = load_eq(ticker, d)
        if eq is None:
            print(f"  {ticker:4s}: NO DATA")
            date_results[ticker] = {"status": "NO_DATA"}
            continue
        
        t_c12_min, t_c12_vol = get_c12_minutes(eq)
        
        if not t_c12_min:
            print(f"  {ticker:4s}: 0 C12 minutes")
            date_results[ticker] = {"minutes": 0, "volume": 0, "overlap": 0, "pct_overlap": 0}
            continue
        
        overlap = gme_c12_min & t_c12_min
        t_only = t_c12_min - gme_c12_min
        gme_only_covered = len(overlap)
        
        pct_of_ticker = len(overlap) / len(t_c12_min) * 100 if t_c12_min else 0
        pct_of_gme = len(overlap) / len(gme_c12_min) * 100 if gme_c12_min else 0
        jaccard = len(overlap) / len(gme_c12_min | t_c12_min) if (gme_c12_min | t_c12_min) else 0
        
        date_results[ticker] = {
            "minutes": len(t_c12_min),
            "volume": t_c12_vol,
            "overlap": len(overlap),
            "ticker_only": len(t_only),
            "pct_of_ticker": round(pct_of_ticker, 1),
            "pct_of_gme": round(pct_of_gme, 1),
            "jaccard": round(jaccard, 3),
        }
        
        marker = " 🚨 BASKET" if pct_of_ticker >= 95 else (" ⚠️" if pct_of_ticker >= 70 else "")
        print(f"  {ticker:4s}: {len(t_c12_min):3d} C12 min | {t_c12_vol:>10,} shares | Overlap: {len(overlap):3d}/{len(t_c12_min)} ({pct_of_ticker:.0f}%) | Jaccard: {jaccard:.3f}{marker}")
    
    # Now check: do the non-GME tickers fill the "missing" GME minutes?
    gme_only = gme_c12_min.copy()
    for ticker in BASKET:
        if ticker == "GME": continue
        eq = load_eq(ticker, d)
        if eq is None: continue
        t_min, _ = get_c12_minutes(eq)
        gme_only -= t_min
    
    print(f"\n  GME-only minutes (not covered by ANY basket ticker): {len(gme_only)}")
    if gme_only:
        gme_only_sorted = sorted(gme_only)[:10]
        print(f"  Sample: {[m.strftime('%H:%M') for m in gme_only_sorted]}")
    
    date_results["gme_uncovered_minutes"] = len(gme_only)
    results[d] = date_results

# Cross-date summary
print(f"\n{'='*60}")
print("SWAP BASKET RECONSTRUCTION SUMMARY")
print(f"{'='*60}")
print(f"\n  {'Ticker':<6} | {'May 13 Overlap':>15} | {'May 14 Overlap':>15} | {'Avg Jaccard':>12} | Verdict")
print("  " + "-" * 75)

for ticker in BASKET:
    if ticker == "GME": continue
    d13 = results.get("2024-05-13", {}).get(ticker, {})
    d14 = results.get("2024-05-14", {}).get(ticker, {})
    
    o13 = f"{d13.get('pct_of_ticker', 0):.0f}%" if d13.get('pct_of_ticker') else "N/A"
    o14 = f"{d14.get('pct_of_ticker', 0):.0f}%" if d14.get('pct_of_ticker') else "N/A"
    j_avg = (d13.get('jaccard', 0) + d14.get('jaccard', 0)) / 2
    
    if j_avg >= 0.8:
        verdict = "🚨 IN SWAP"
    elif j_avg >= 0.5:
        verdict = "⚠️ POSSIBLE"
    elif j_avg > 0:
        verdict = "Systemic"
    else:
        verdict = "No data"
    
    print(f"  {ticker:<6} | {o13:>15} | {o14:>15} | {j_avg:>12.3f} | {verdict}")

# Save
out_path = Path(__file__).parent / "round11_v1_basket_reconstruction.json"
with open(out_path, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
