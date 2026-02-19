#!/usr/bin/env python3
"""All basket tests with KOSS included"""
import json, os, sys, time, traceback
import numpy as np
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
THETA_ROOT = REPO_ROOT / "data" / "raw" / "thetadata" / "trades"
POLYGON_ROOT = REPO_ROOT / "data" / "raw" / "polygon" / "trades"

def load_eq(ticker, date_str):
    date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str
    path = POLYGON_ROOT / f"symbol={ticker}" / f"date={date_fmt}" / "part-0.parquet"
    if not path.exists(): return None
    df = pd.read_parquet(path)
    ts_col = 'timestamp' if 'timestamp' in df.columns else 'sip_timestamp'
    df['ts'] = pd.to_datetime(df[ts_col])
    if df['ts'].dt.tz is not None: df['ts'] = df['ts'].dt.tz_localize(None)
    return df

def load_opts(ticker, date_str):
    path = THETA_ROOT / f"root={ticker}" / f"date={date_str}" / "part-0.parquet"
    if not path.exists(): return None
    df = pd.read_parquet(path)
    df['ts'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    if df['ts'].dt.tz is not None: df['ts'] = df['ts'].dt.tz_localize(None)
    return df

all_results = {}

# ===================================================================
# T1: CROSS-TICKER LEAD-LAG WITH KOSS
# ===================================================================
print("=" * 60)
print("T1: CROSS-TICKER LEAD-LAG WITH KOSS")
print("=" * 60)

target_dates = ["20240513", "20240514", "20240515"]
targets = ["KOSS", "CHWY", "DJT", "AAPL"]
windows_ms = [50, 100, 250, 500, 1000, 5000, 30000, 60000]
results = {t: {w: {"before": 0, "after": 0} for w in windows_ms} for t in targets}
events_scanned = 0

for d in target_dates:
    t0 = time.time()
    gme_opts = load_opts("GME", d)
    if gme_opts is None:
        print(f"  {d}: No GME options"); continue
    
    blocks = gme_opts[gme_opts['size'] >= 10]
    if blocks.empty: continue
    
    block_ns = blocks['ts'].values.astype('int64')
    events_scanned += len(block_ns)
    
    for target in targets:
        tgt = load_eq(target, d)
        if tgt is None or len(tgt) < 10:
            print(f"  {d} {target}: insufficient data")
            continue
        
        tgt_ns = tgt['ts'].values.astype('int64')
        tgt_sz = tgt['size'].values
        
        sorted_idx = np.argsort(tgt_ns)
        tgt_ns_sorted = tgt_ns[sorted_idx]
        tgt_sz_sorted = tgt_sz[sorted_idx]
        
        for w in windows_ms:
            wns = w * 1_000_000
            total_before = 0
            total_after = 0
            
            for bt in block_ns:
                lo_b = np.searchsorted(tgt_ns_sorted, bt - wns, side='left')
                hi_b = np.searchsorted(tgt_ns_sorted, bt, side='left')
                total_before += int(tgt_sz_sorted[lo_b:hi_b].sum())
                
                lo_a = np.searchsorted(tgt_ns_sorted, bt, side='right')
                hi_a = np.searchsorted(tgt_ns_sorted, bt + wns, side='right')
                total_after += int(tgt_sz_sorted[lo_a:hi_a].sum())
            
            results[target][w]["before"] += total_before
            results[target][w]["after"] += total_after
    
    elapsed = time.time() - t0
    print(f"  {d}: {len(blocks):,} blocks, {elapsed:.1f}s")

print(f"\n  Total: {events_scanned:,} GME options blocks\n")

t1_ratios = {}
for target in targets:
    print(f"  {target}:")
    tgt_res = {}
    for w in windows_ms:
        b = results[target][w]["before"]
        a = results[target][w]["after"]
        r = round(a / max(1, b), 3)
        tgt_res[f"{w}ms"] = {"before": b, "after": a, "ratio": r}
        marker = " <<<" if r > 1.15 else ""
        print(f"    {w:6d}ms | Before: {b:>12,} | After: {a:>12,} | Ratio: {r:.3f}x{marker}")
    t1_ratios[target] = tgt_res
    print()

all_results["T1_lead_lag"] = {"events_scanned": events_scanned, "ratios": t1_ratios}

# ===================================================================
# T2: BASKET TAPE FRACTURE WITH KOSS (MAY 17)
# ===================================================================
print("=" * 60)
print("T2: BASKET TAPE FRACTURE WITH KOSS (MAY 17, 2024)")
print("=" * 60)

date_str = '2024-05-17'
basket = ["GME", "KOSS", "CHWY", "DJT", "SPY"]
dark_ids = {4, 15}
t2_results = {}

for ticker in basket:
    eq = load_eq(ticker, date_str)
    if eq is None or len(eq) < 10:
        t2_results[ticker] = {"status": "NO_DATA"}
        print(f"  {ticker:4s} | No data")
        continue
    
    pm = eq[(eq['ts'].dt.hour >= 8) & (eq['ts'].dt.hour < 14)].copy()
    if len(pm) < 10:
        t2_results[ticker] = {"status": "NO_PREMARKET", "total_trades": len(eq)}
        print(f"  {ticker:4s} | No premarket (total: {len(eq):,})")
        continue
    
    dark = pm[pm['exchange'].isin(dark_ids)].copy()
    lit = pm[~pm['exchange'].isin(dark_ids)].copy()
    
    if len(dark) < 5 or len(lit) < 5:
        t2_results[ticker] = {"status": "INSUFFICIENT_SPLIT", "dark": len(dark), "lit": len(lit)}
        print(f"  {ticker:4s} | Insuff split (D:{len(dark)}, L:{len(lit)})")
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
        t2_results[ticker] = {"status": "NO_OVERLAP"}
        continue
    
    df['abs_spread'] = (df['dark'] - df['lit']).abs()
    df['spread_pct'] = df['abs_spread'] / df['lit'] * 100
    
    max_pct = float(df['spread_pct'].max())
    max_abs = float(df['abs_spread'].max())
    mean_pct = float(df['spread_pct'].mean())
    dark_max = float(dark['price'].max())
    
    t2_results[ticker] = {
        "max_spread_pct": round(max_pct, 2),
        "max_spread_dollars": round(max_abs, 2),
        "mean_spread_pct": round(mean_pct, 2),
        "dark_max_price": round(dark_max, 2),
        "pm_trades": len(pm),
        "dark_trades": len(dark),
        "lit_trades": len(lit),
    }
    
    marker = "🚨 FRACTURE" if max_pct > 2.0 else "Normal"
    print(f"  {ticker:4s} | Max: {max_pct:>6.1f}% (${max_abs:>6.2f}) | Mean: {mean_pct:.2f}% | Dark Max: ${dark_max:.2f} | PM: {len(pm):,} trades | {marker}")

all_results["T2_basket_fracture"] = t2_results

# ===================================================================
# T3: CODE 12 BASKET SYNC WITH KOSS
# ===================================================================
print("\n" + "=" * 60)
print("T3: CODE 12 BASKET SYNC WITH KOSS")
print("=" * 60)

dates = ["2024-05-08", "2024-05-09", "2024-05-10", "2024-05-13", "2024-05-14",
         "2024-05-15", "2024-05-16", "2024-05-17", "2024-05-20", "2024-05-21"]
basket_c12 = ["GME", "KOSS", "CHWY", "DJT", "AAPL", "SPY"]
c12_volumes = {t: [] for t in basket_c12}

for d in dates:
    for t in basket_c12:
        eq = load_eq(t, d)
        vol = 0
        if eq is not None and not eq.empty and 'conditions' in eq.columns:
            trf = eq[eq['exchange'] == 4]
            for _, row in trf.iterrows():
                c = row.get('conditions')
                if isinstance(c, (list, np.ndarray)) and 12 in c:
                    vol += int(row['size'])
        c12_volumes[t].append(vol)
    print(f"  {d} done")

print(f"\n  {'Date':<12} | {'GME':>10} | {'KOSS':>10} | {'CHWY':>10} | {'DJT':>10} | {'AAPL':>10} | {'SPY':>10}")
print("  " + "-" * 78)

for i, d in enumerate(dates):
    vals = [f"{c12_volumes[t][i]:>10,}" for t in basket_c12]
    marker = " <--" if d == "2024-05-14" else ""
    print(f"  {d:<12} | {'|'.join(vals)}{marker}")

df_c12 = pd.DataFrame(c12_volumes)
correlations = {}
for t in ["KOSS", "CHWY", "DJT", "AAPL", "SPY"]:
    if df_c12[t].std() > 0 and df_c12['GME'].std() > 0:
        correlations[t] = round(float(df_c12['GME'].corr(df_c12[t])), 3)
    else:
        correlations[t] = 0.0

print(f"\n  Correlation with GME C12:")
for t, r in correlations.items():
    marker = " 🚨" if abs(r) > 0.5 else ""
    print(f"    {t:4s}: r = {r:+.3f}{marker}")

print(f"\n  Totals:")
for t in basket_c12:
    print(f"    {t:4s}: {sum(c12_volumes[t]):>12,}")

all_results["T3_code12_basket"] = {
    "volumes": {k: [int(v) for v in vals] for k, vals in c12_volumes.items()},
    "correlations": correlations,
    "totals": {t: sum(c12_volumes[t]) for t in basket_c12},
}

# Save everything
out_path = Path(__file__).parent / "round10_basket_results.json"
with open(out_path, "w") as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\n{'='*60}")
print(f"ALL SAVED to {out_path}")
