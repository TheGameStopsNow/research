#!/usr/bin/env python3
"""
Phase 12 Vector 4: The Put-Call Parity Settlement Predictor (Prototype)
Scans for T-3 options conversions that predict dark pool price ceilings.

Algorithm:
1. Identify large paired option blocks (puts + calls at same strike, same time)
2. Compute synthetic put-call parity price: Strike + Call_Premium - Put_Premium
3. Compare to actual T+3 tape fracture (if any Code 12 ceiling appears at that price)

Prototype validates on GME May 13-17, 2024.
"""
import json, sys, time
import numpy as np
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
THETA_ROOT = REPO_ROOT / "data" / "raw" / "thetadata" / "trades"
POLYGON_ROOT = REPO_ROOT / "data" / "raw" / "polygon" / "trades"
OUT_DIR = Path(__file__).parent

def load_opts(ticker, date_str):
    path = THETA_ROOT / f"root={ticker}" / f"date={date_str}" / "part-0.parquet"
    if not path.exists(): return None
    df = pd.read_parquet(path)
    df['ts'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    if df['ts'].dt.tz is not None: df['ts'] = df['ts'].dt.tz_localize(None)
    return df

def load_eq(ticker, date_str):
    date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str
    path = POLYGON_ROOT / f"symbol={ticker}" / f"date={date_fmt}" / "part-0.parquet"
    if not path.exists(): return None
    df = pd.read_parquet(path)
    ts_col = 'timestamp' if 'timestamp' in df.columns else 'sip_timestamp'
    df['ts'] = pd.to_datetime(df[ts_col])
    if df['ts'].dt.tz is not None: df['ts'] = df['ts'].dt.tz_localize(None)
    return df

def get_c12_ceiling(df):
    """Get the Code 12 price ceiling from equity tape."""
    trf = df[df['exchange'] == 4].copy()
    if trf.empty: return None, 0
    mask = trf['conditions'].apply(lambda c: 12 in c if isinstance(c, (list, np.ndarray)) else False)
    c12 = trf[mask]
    if c12.empty: return None, 0
    # Volume-weighted average price of C12 trades  
    vwap = (c12['price'] * c12['size']).sum() / c12['size'].sum()
    ceiling = c12['price'].max()
    return round(float(ceiling), 2), round(float(vwap), 2)

def find_conversions(opts_df, min_size=10):
    """
    Find paired put-call blocks at the same strike within a time window.
    These are synthetic conversions that lock in a settlement price.
    """
    if opts_df is None or opts_df.empty:
        return []
    
    # Need columns: right (C/P), strike, price, size, ts
    if 'right' not in opts_df.columns:
        return []
    
    # Large blocks only
    blocks = opts_df[opts_df['size'] >= min_size].copy()
    if blocks.empty:
        return []
    
    calls = blocks[blocks['right'] == 'C'].copy()
    puts = blocks[blocks['right'] == 'P'].copy()
    
    if calls.empty or puts.empty:
        return []
    
    conversions = []
    
    # Group by strike, find co-occurring puts+calls
    for strike in calls['strike'].unique():
        sc = calls[calls['strike'] == strike]
        sp = puts[puts['strike'] == strike]
        
        if sc.empty or sp.empty:
            continue
        
        # For each call block, find closest put block within 5 seconds
        for _, c_row in sc.iterrows():
            c_ts = c_row['ts']
            time_diffs = abs((sp['ts'] - c_ts).dt.total_seconds())
            close_puts = sp[time_diffs <= 5]
            
            if not close_puts.empty:
                p_row = close_puts.iloc[0]
                # Synthetic price = Strike + Call_Premium - Put_Premium
                # But prices in ThetaData are per-share premiums
                call_prem = float(c_row['price'])
                put_prem = float(p_row['price'])
                strike_val = float(strike) / 1000 if float(strike) > 1000 else float(strike)
                
                synthetic = strike_val + call_prem - put_prem
                
                conversions.append({
                    "strike": strike_val,
                    "call_premium": call_prem,
                    "put_premium": put_prem,
                    "synthetic_price": round(synthetic, 2),
                    "call_size": int(c_row['size']),
                    "put_size": int(p_row['size']),
                    "timestamp": str(c_row['ts']),
                    "time_diff_sec": float(time_diffs.min()),
                })
    
    return conversions

# ===================================================================
print("="*70)
print("PHASE 12 V4: PUT-CALL PARITY SETTLEMENT PREDICTOR")
print("="*70)

# VALIDATION RUN: GME May 13-17 2024
print("\n  === Validation: GME May 2024 ===")

# Step 1: Find T-3 conversions
conversion_dates = ["20240513", "20240514", "20240515"]
settlement_date = "20240517"

all_conversions = []
for d in conversion_dates:
    print(f"\n  Scanning {d} for conversions...")
    opts = load_opts("GME", d)
    if opts is None:
        print(f"    No options data")
        continue
    
    print(f"    {len(opts):,} total option trades")
    convs = find_conversions(opts, min_size=5)
    print(f"    Found {len(convs)} paired conversions")
    
    for c in convs[:10]:  # Top 10
        print(f"      Strike=${c['strike']:.2f} | C={c['call_premium']:.2f} P={c['put_premium']:.2f} | Synthetic=${c['synthetic_price']:.2f} | Size={c['call_size']}x{c['put_size']} | {c['timestamp']}")
    
    all_conversions.extend(convs)

# Step 2: Compute consensus synthetic price
if all_conversions:
    synth_prices = [c['synthetic_price'] for c in all_conversions]
    total_size = sum(c['call_size'] + c['put_size'] for c in all_conversions)
    
    # Volume-weighted synthetic
    weighted = sum(c['synthetic_price'] * (c['call_size'] + c['put_size']) for c in all_conversions) / total_size
    
    print(f"\n  SYNTHETIC PRICE CONSENSUS:")
    print(f"    Total conversions: {len(all_conversions)}")
    print(f"    Mean synthetic:    ${np.mean(synth_prices):.2f}")
    print(f"    Median synthetic:  ${np.median(synth_prices):.2f}")
    print(f"    Vol-weighted:      ${weighted:.2f}")
    print(f"    Range:             ${min(synth_prices):.2f} - ${max(synth_prices):.2f}")

# Step 3: Compare to actual T+3 Code 12 ceiling
print(f"\n  Checking actual settlement tape ({settlement_date})...")
eq = load_eq("GME", settlement_date)
if eq is not None:
    ceiling, vwap = get_c12_ceiling(eq)
    print(f"    Code 12 ceiling:   ${ceiling}")
    print(f"    Code 12 VWAP:      ${vwap}")
    
    if all_conversions and ceiling:
        error_pct = abs(weighted - ceiling) / ceiling * 100
        print(f"\n  🔮 ORACLE ACCURACY:")
        print(f"    Predicted (T-3):   ${weighted:.2f}")
        print(f"    Actual ceiling:    ${ceiling:.2f}")
        print(f"    Error:             {error_pct:.2f}%")
        if error_pct < 2:
            print(f"    VERDICT:           🎯 CONFIRMED — T-3 options predicted the ceiling within 2%")
        elif error_pct < 5:
            print(f"    VERDICT:           ✅ Strong signal — within 5%")
        else:
            print(f"    VERDICT:           ⚠️ Weak signal — needs refinement")

# Save
results = {
    "conversions": all_conversions,
    "synthetic_consensus": {
        "mean": float(np.mean(synth_prices)) if all_conversions else None,
        "median": float(np.median(synth_prices)) if all_conversions else None,
        "weighted": float(weighted) if all_conversions else None,
    },
    "actual_settlement": {
        "ceiling": ceiling if eq is not None else None,
        "vwap": vwap if eq is not None else None,
    }
}

out_path = OUT_DIR / "round12_v4_oracle.json"
with open(out_path, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
