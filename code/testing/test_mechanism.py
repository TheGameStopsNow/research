#!/usr/bin/env python3
"""
Round 10b Mechanism Discovery Tests
Identifies HOW GME→KOSS contagion transmits through NMS infrastructure.
"""
import json, sys, time
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parents[2]
THETA_ROOT = REPO_ROOT / "data" / "raw" / "thetadata" / "trades"
POLYGON_ROOT = REPO_ROOT / "data" / "raw" / "polygon" / "trades"

# Polygon exchange ID mapping (partial)
EXCHANGE_NAMES = {
    1: "NYSE", 2: "ARCA", 3: "AMEX", 4: "TRF_FINRA",
    5: "NASDAQ_ISE", 6: "PHLX", 7: "CBOE_BYX", 8: "CBOE_BZX",
    9: "IEX", 10: "CBOE_EDGA", 11: "CBOE_EDGX", 12: "NASDAQ",
    13: "CTS", 14: "NASDAQ_BX", 15: "TRF_FINRA_2", 16: "MEMX",
    17: "MIAX_PEARL", 18: "LTSE", 19: "NYSE_NAT"
}

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
# M1: EXCHANGE ROUTING — Where do KOSS bursts hit?
# ===================================================================
print("=" * 60)
print("M1: EXCHANGE ROUTING ANALYSIS")
print("=" * 60)

m1_results = {}
for d in ["2024-05-13", "2024-05-14"]:
    koss = load_eq("KOSS", d)
    gme = load_eq("GME", d)
    if koss is None or gme is None: continue
    
    for ticker, df in [("KOSS", koss), ("GME", gme)]:
        ex_vol = df.groupby('exchange')['size'].sum().sort_values(ascending=False)
        total = ex_vol.sum()
        
        trf_vol = ex_vol.get(4, 0) + ex_vol.get(15, 0)
        lit_vol = total - trf_vol
        trf_pct = trf_vol / total * 100 if total > 0 else 0
        
        key = f"{ticker}_{d}"
        m1_results[key] = {
            "trf_pct": round(trf_pct, 1),
            "trf_volume": int(trf_vol),
            "lit_volume": int(lit_vol),
            "total_volume": int(total),
            "top_exchanges": {}
        }
        
        print(f"\n  {ticker} on {d} | TRF: {trf_pct:.1f}% ({trf_vol:,}) | Lit: {100-trf_pct:.1f}% ({lit_vol:,})")
        for ex_id, vol in ex_vol.head(8).items():
            name = EXCHANGE_NAMES.get(int(ex_id), f"EX_{ex_id}")
            pct = vol / total * 100
            m1_results[key]["top_exchanges"][name] = round(pct, 1)
            is_dark = " [DARK]" if ex_id in (4, 15) else ""
            print(f"    {name:15s} ({ex_id:2d}): {vol:>12,} ({pct:5.1f}%){is_dark}")

# Compare to quiet day
for d in ["2024-05-08"]:
    koss = load_eq("KOSS", d)
    if koss is None: continue
    ex_vol = koss.groupby('exchange')['size'].sum()
    total = ex_vol.sum()
    trf_vol = ex_vol.get(4, 0) + ex_vol.get(15, 0)
    trf_pct = trf_vol / total * 100 if total > 0 else 0
    print(f"\n  KOSS on {d} (QUIET CONTROL): TRF: {trf_pct:.1f}% ({trf_vol:,}) | Total: {total:,}")
    m1_results[f"KOSS_{d}_control"] = {"trf_pct": round(trf_pct, 1), "trf_volume": int(trf_vol), "total_volume": int(total)}

all_results["M1_exchange_routing"] = m1_results

# ===================================================================
# M2: INTRADAY CROSS-CORRELATION (minute-by-minute GME vs KOSS)
# ===================================================================
print("\n" + "=" * 60)
print("M2: INTRADAY CROSS-CORRELATION (GME vs KOSS)")
print("=" * 60)

m2_results = {}
for d in ["2024-05-13", "2024-05-14"]:
    gme = load_eq("GME", d)
    koss = load_eq("KOSS", d)
    if gme is None or koss is None: continue
    
    gme['minute'] = gme['ts'].dt.floor('1min')
    koss['minute'] = koss['ts'].dt.floor('1min')
    
    # Minute volume
    gme_mvol = gme.groupby('minute')['size'].sum()
    koss_mvol = koss.groupby('minute')['size'].sum()
    
    # Minute VWAP
    def vwap(df):
        g = df.groupby('minute')
        return (g.apply(lambda x: (x['price'] * x['size']).sum() / x['size'].sum(), include_groups=False))
    
    gme_vwap = vwap(gme)
    koss_vwap = vwap(koss)
    
    # Align on common minutes
    common = gme_mvol.index.intersection(koss_mvol.index)
    if len(common) < 10:
        print(f"  {d}: Only {len(common)} overlapping minutes")
        continue
    
    gv = gme_mvol.reindex(common).fillna(0)
    kv = koss_mvol.reindex(common).fillna(0)
    gp = gme_vwap.reindex(common)
    kp = koss_vwap.reindex(common)
    
    # Volume correlation
    vol_corr = float(gv.corr(kv))
    
    # Price return correlation
    gp_ret = gp.pct_change().dropna()
    kp_ret = kp.pct_change().dropna()
    common_ret = gp_ret.index.intersection(kp_ret.index)
    if len(common_ret) > 10:
        price_corr = float(gp_ret.reindex(common_ret).corr(kp_ret.reindex(common_ret)))
    else:
        price_corr = 0.0
    
    # Lead-lag: cross-correlate at different minute lags
    lags = {}
    for lag in range(-5, 6):
        if lag < 0:
            g_s = gp_ret.iloc[:lag] if lag < -1 else gp_ret.iloc[:-1]
            k_s = kp_ret.iloc[-lag:]
        elif lag > 0:
            g_s = gp_ret.iloc[lag:]
            k_s = kp_ret.iloc[:-lag] if lag < len(kp_ret) else kp_ret
        else:
            g_s = gp_ret
            k_s = kp_ret
        
        min_len = min(len(g_s), len(k_s))
        if min_len > 10:
            lags[lag] = round(float(np.corrcoef(g_s.values[:min_len], k_s.values[:min_len])[0, 1]), 3)
    
    best_lag = max(lags, key=lambda x: abs(lags[x]))
    
    m2_results[d] = {
        "volume_corr": round(vol_corr, 3),
        "price_return_corr": round(price_corr, 3),
        "overlapping_minutes": len(common),
        "best_lag_minutes": best_lag,
        "best_lag_corr": lags.get(best_lag, 0),
        "lag_profile": lags,
    }
    
    print(f"\n  {d} ({len(common)} overlapping minutes):")
    print(f"    Volume correlation    : r = {vol_corr:+.3f}")
    print(f"    Price return correlation: r = {price_corr:+.3f}")
    print(f"    Best lag: {best_lag:+d} min (r = {lags.get(best_lag, 0):+.3f})")
    print(f"    Lag profile: ", end="")
    for lag in sorted(lags.keys()):
        marker = " <<<" if lag == best_lag else ""
        print(f"\n      {lag:+d}min: {lags[lag]:+.3f}{marker}", end="")
    print()

all_results["M2_intraday_crosscorr"] = m2_results

# ===================================================================
# M3: KOSS PRICE IMPACT IN 50ms WINDOWS
# ===================================================================
print("\n" + "=" * 60)
print("M3: KOSS PRICE IMPACT AT 50ms WINDOWS")
print("=" * 60)

m3_results = {}
for d_opt in ["20240513", "20240514"]:
    d_eq = f"{d_opt[:4]}-{d_opt[4:6]}-{d_opt[6:8]}"
    gme_opts = load_opts("GME", d_opt)
    koss = load_eq("KOSS", d_eq)
    if gme_opts is None or koss is None: continue
    
    blocks = gme_opts[gme_opts['size'] >= 10]
    if blocks.empty: continue
    
    block_ns = blocks['ts'].values.astype('int64')
    koss_ns = koss['ts'].values.astype('int64')
    koss_px = koss['price'].values
    koss_sz = koss['size'].values
    
    sorted_idx = np.argsort(koss_ns)
    koss_ns_s = koss_ns[sorted_idx]
    koss_px_s = koss_px[sorted_idx]
    koss_sz_s = koss_sz[sorted_idx]
    
    # For each GME options block, measure KOSS price change in windows
    windows = [50, 100, 500, 1000, 5000]
    price_impacts = {w: [] for w in windows}
    
    for bt in block_ns:
        # Get KOSS price just before
        idx_before = np.searchsorted(koss_ns_s, bt, side='left') - 1
        if idx_before < 0 or idx_before >= len(koss_px_s):
            continue
        px_before = koss_px_s[idx_before]
        
        for w in windows:
            wns = w * 1_000_000
            lo = np.searchsorted(koss_ns_s, bt, side='right')
            hi = np.searchsorted(koss_ns_s, bt + wns, side='right')
            if hi > lo:
                # Volume-weighted price after
                chunk_px = koss_px_s[lo:hi]
                chunk_sz = koss_sz_s[lo:hi]
                if chunk_sz.sum() > 0:
                    vwap_after = (chunk_px * chunk_sz).sum() / chunk_sz.sum()
                    pct_change = (vwap_after - px_before) / px_before * 100
                    price_impacts[w].append(pct_change)
    
    print(f"\n  {d_opt}:")
    day_result = {}
    for w in windows:
        impacts = price_impacts[w]
        if len(impacts) < 10:
            print(f"    {w:5d}ms | {len(impacts)} events (insufficient)")
            continue
        
        arr = np.array(impacts)
        mean_impact = float(np.mean(arr))
        median_impact = float(np.median(arr))
        std_impact = float(np.std(arr))
        pos_pct = float((arr > 0).mean() * 100)
        
        # Is the mean significantly different from zero?
        t_stat = mean_impact / (std_impact / np.sqrt(len(arr))) if std_impact > 0 else 0
        
        day_result[f"{w}ms"] = {
            "events": len(impacts),
            "mean_bps": round(mean_impact * 100, 1),  # basis points
            "median_bps": round(median_impact * 100, 1),
            "positive_pct": round(pos_pct, 1),
            "t_stat": round(t_stat, 2),
        }
        
        direction = "UP" if mean_impact > 0 else "DOWN"
        sig = "***" if abs(t_stat) > 3 else ("**" if abs(t_stat) > 2 else ("*" if abs(t_stat) > 1.5 else ""))
        print(f"    {w:5d}ms | n={len(impacts):,} | Mean: {mean_impact*100:+5.1f}bps | Med: {median_impact*100:+5.1f}bps | {direction} {pos_pct:.0f}% | t={t_stat:+.2f} {sig}")
    
    m3_results[d_opt] = day_result

all_results["M3_price_impact"] = m3_results

# ===================================================================
# M4: CODE 12 INTRA-DAY TIMESTAMP OVERLAP
# ===================================================================
print("\n" + "=" * 60)
print("M4: CODE 12 TIMESTAMP OVERLAP (Same-Minute Co-occurrence)")
print("=" * 60)

m4_results = {}
for d in ["2024-05-13", "2024-05-14"]:
    gme = load_eq("GME", d)
    koss = load_eq("KOSS", d)
    if gme is None or koss is None: continue
    
    def get_c12_minutes(df):
        trf = df[df['exchange'] == 4].copy()
        c12_rows = []
        for _, row in trf.iterrows():
            c = row.get('conditions')
            if isinstance(c, (list, np.ndarray)) and 12 in c:
                c12_rows.append(row)
        if not c12_rows: return set(), 0
        c12_df = pd.DataFrame(c12_rows)
        minutes = set(c12_df['ts'].dt.floor('1min'))
        vol = int(c12_df['size'].sum())
        return minutes, vol
    
    gme_c12_min, gme_c12_vol = get_c12_minutes(gme)
    koss_c12_min, koss_c12_vol = get_c12_minutes(koss)
    
    overlap = gme_c12_min & koss_c12_min
    gme_only = gme_c12_min - koss_c12_min
    koss_only = koss_c12_min - gme_c12_min
    
    # Jaccard similarity
    union = gme_c12_min | koss_c12_min
    jaccard = len(overlap) / len(union) if len(union) > 0 else 0
    
    m4_results[d] = {
        "gme_c12_minutes": len(gme_c12_min),
        "koss_c12_minutes": len(koss_c12_min),
        "overlapping_minutes": len(overlap),
        "gme_only_minutes": len(gme_only),
        "koss_only_minutes": len(koss_only),
        "jaccard_similarity": round(jaccard, 3),
        "gme_c12_volume": gme_c12_vol,
        "koss_c12_volume": koss_c12_vol,
    }
    
    print(f"\n  {d}:")
    print(f"    GME  C12 minutes: {len(gme_c12_min):,} ({gme_c12_vol:,} shares)")
    print(f"    KOSS C12 minutes: {len(koss_c12_min):,} ({koss_c12_vol:,} shares)")
    print(f"    OVERLAP:          {len(overlap):,} minutes")
    print(f"    GME-only:         {len(gme_only):,} minutes")
    print(f"    KOSS-only:        {len(koss_only):,} minutes")
    print(f"    Jaccard:          {jaccard:.3f}")
    
    if overlap:
        overlap_sorted = sorted(overlap)[:10]
        print(f"    First overlapping minutes:")
        for m in overlap_sorted:
            print(f"      {m.strftime('%H:%M')} UTC")

all_results["M4_c12_timestamp_overlap"] = m4_results

# ===================================================================
# SAVE
# ===================================================================
out_path = Path(__file__).parent / "round10_mechanism_results.json"
with open(out_path, "w") as f:
    json.dump(all_results, f, indent=2, default=str)

print(f"\n{'='*60}")
print(f"ALL MECHANISM TESTS SAVED to {out_path}")
print(f"{'='*60}")
