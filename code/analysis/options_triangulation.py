#!/usr/bin/env python3
"""
Vector 2: Options Triangulation — Find the $33.00 Genesis
Scan ThetaData GME options tape for massive paired blocks (conversions)
on the $30/$33/$40 strikes, May 13-17 2024.
ThetaData columns: symbol, expiration, strike, right, timestamp, sequence,
    ext_condition1-4, condition, size, exchange, price, expiry, root
"""
import json, numpy as np, pandas as pd
from pathlib import Path

THETA_ROOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "thetadata" / "trades"

dates = ["20240513", "20240514", "20240515", "20240516", "20240517"]
results = {}

for d in dates:
    path = THETA_ROOT / f"root=GME" / f"date={d}" / "part-0.parquet"
    if not path.exists():
        print(f"  {d}: No data"); continue
    
    df = pd.read_parquet(path)
    df['ts'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    if df['ts'].dt.tz is not None: df['ts'] = df['ts'].dt.tz_localize(None)
    
    total_trades = len(df)
    total_volume = int(df['size'].sum())
    
    print(f"\n{'='*70}")
    print(f"  {d}: {total_trades:,} options trades, {total_volume:,} contracts")
    print(f"{'='*70}")
    
    # Convert strike to dollars (ThetaData stores as integer × 1000)
    if 'strike' in df.columns:
        df['strike_price'] = df['strike'] / 1000.0 if df['strike'].max() > 1000 else df['strike'].astype(float)
    
    # Big blocks (≥100 contracts)
    big_blocks = df[df['size'] >= 100].copy()
    print(f"  Big blocks (≥100): {len(big_blocks):,} trades, {int(big_blocks['size'].sum()):,} contracts")
    
    # Monster blocks (≥500 contracts)
    monster_blocks = df[df['size'] >= 500].copy()
    print(f"  Monster blocks (≥500): {len(monster_blocks):,} trades, {int(monster_blocks['size'].sum()):,} contracts")
    
    # Giant blocks (≥1000 contracts)
    giant_blocks = df[df['size'] >= 1000].copy()
    print(f"  Giant blocks (≥1000): {len(giant_blocks):,} trades, {int(giant_blocks['size'].sum()):,} contracts")
    
    # Condition code distribution (ThetaData uses 'condition' singular + ext_condition1-4)
    cond_col = 'condition' if 'condition' in df.columns else 'conditions'
    if cond_col in df.columns:
        cond_counts = df[cond_col].value_counts().head(15)
        print(f"\n  Condition codes (top 15):")
        for code, count in cond_counts.items():
            pct = count / total_trades * 100
            print(f"    Code {code}: {count:>8,} ({pct:5.1f}%)")
    
    # Extended conditions
    for ext in ['ext_condition1', 'ext_condition2', 'ext_condition3', 'ext_condition4']:
        if ext in df.columns:
            non_zero = df[df[ext] != 0]
            if len(non_zero) > 0:
                print(f"\n  {ext} non-zero: {len(non_zero):,} trades")
                for code, count in non_zero[ext].value_counts().head(5).items():
                    print(f"    Code {int(code)}: {count:>6,}")
    
    # Strike distribution for big blocks
    if 'strike_price' in df.columns:
        print(f"\n  Strike distribution (big blocks ≥100):")
        if len(big_blocks) > 0:
            strike_vol = big_blocks.groupby('strike_price')['size'].sum().sort_values(ascending=False)
            for strike, vol in strike_vol.head(15).items():
                pct = vol / big_blocks['size'].sum() * 100
                marker = " <<<" if strike in [30.0, 33.0, 35.0, 40.0] else ""
                print(f"    ${strike:>6.0f}: {int(vol):>8,} contracts ({pct:5.1f}%){marker}")
    
    # Right (Call/Put) split for big blocks
    if 'right' in df.columns and len(big_blocks) > 0:
        right_vol = big_blocks.groupby('right')['size'].sum()
        print(f"\n  Call/Put split (big blocks):")
        for right, vol in right_vol.items():
            label = "CALL" if right in ['C', 'Call', 1] else "PUT" if right in ['P', 'Put', 0] else str(right)
            print(f"    {label}: {int(vol):>10,} contracts")
    
    # Expiration distribution for big blocks  
    if 'expiration' in df.columns and len(big_blocks) > 0:
        exp_vol = big_blocks.groupby('expiration')['size'].sum().sort_values(ascending=False)
        print(f"\n  Expiration distribution (big blocks, top 10):")
        for exp, vol in exp_vol.head(10).items():
            pct = vol / big_blocks['size'].sum() * 100
            print(f"    {exp}: {int(vol):>8,} contracts ({pct:5.1f}%)")
    
    # Find potential conversions: paired Call+Put at same strike within 1 second
    if 'strike_price' in df.columns and 'right' in df.columns:
        print(f"\n  Scanning for synthetic conversions (paired C+P blocks)...")
        bb = big_blocks.copy()
        bb['sec'] = bb['ts'].dt.floor('1s')
        
        # Group by second and strike
        for (sec, strike), grp in bb.groupby(['sec', 'strike_price']):
            rights = set()
            if 'right' in grp.columns:
                rights = set(grp['right'].unique())
            
            # Check if both calls and puts present
            has_call = any(r in rights for r in ['C', 'Call', 1])
            has_put = any(r in rights for r in ['P', 'Put', 0])
            
            if has_call and has_put and grp['size'].sum() >= 200:
                total_sz = int(grp['size'].sum())
                # Calculate synthetic price
                call_rows = grp[grp['right'].isin(['C', 'Call', 1])]
                put_rows = grp[grp['right'].isin(['P', 'Put', 0])]
                
                call_px = (call_rows['price'] * call_rows['size']).sum() / call_rows['size'].sum() if len(call_rows) > 0 else 0
                put_px = (put_rows['price'] * put_rows['size']).sum() / put_rows['size'].sum() if len(put_rows) > 0 else 0
                
                # Conversion synthetic = Strike + Call - Put
                synthetic = strike + call_px - put_px
                
                call_vol = int(call_rows['size'].sum())
                put_vol = int(put_rows['size'].sum())
                
                marker = " 🚨 $33 MATCH" if 32.5 <= synthetic <= 33.5 else ""
                marker = marker or (" ⚠️ NEAR $33" if 30 <= synthetic <= 36 else "")
                
                if total_sz >= 500 or marker:
                    print(f"    {sec.strftime('%H:%M:%S')} | Strike ${strike:.0f} | C:{call_vol:>5,} @${call_px:.2f} + P:{put_vol:>5,} @${put_px:.2f} | Synthetic: ${synthetic:.2f} | Total: {total_sz:,}{marker}")
    
    # Top 20 largest trades
    top = df.nlargest(20, 'size')
    print(f"\n  Top 20 trades by size:")
    print(f"  {'Time':<15} | {'Size':>7} | {'Price':>8} | {'Strike':>8} | {'Right':>5} | {'Expiry':>10} | {'Cond':>5} | {'Exch':>4}")
    for _, row in top.iterrows():
        ts = row['ts'].strftime('%H:%M:%S.%f')[:-3]
        strike = f"${row.get('strike_price', 0):.0f}" if 'strike_price' in row.index else "N/A"
        right = str(row.get('right', 'N/A'))
        exp = str(row.get('expiration', 'N/A'))[:10]
        cond = int(row.get(cond_col, 0)) if cond_col in row.index else 0
        exch = int(row.get('exchange', 0))
        print(f"  {ts:<15} | {int(row['size']):>7,} | ${row['price']:>7.2f} | {strike:>8} | {right:>5} | {exp:>10} | {cond:>5} | {exch:>4}")
    
    results[d] = {
        "total_trades": total_trades,
        "total_volume": total_volume,
        "big_blocks": len(big_blocks),
        "monster_blocks": len(monster_blocks),
        "giant_blocks": len(giant_blocks),
    }

out_path = Path(__file__).parent / "round11_v2_options_triangulation.json"
with open(out_path, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\n\nSaved to {out_path}")
