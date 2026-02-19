#!/usr/bin/env python3
"""
Vector 4b: May 2024 FTD Analysis — The Settlement Window
Focus on T+1/T+2 FTD spikes after the May 14 C12 explosion.
"""
import json, pandas as pd
from pathlib import Path

FTD_DIR = Path("[REPO_PATH]/data/raw/sec_ftd")

def load_ftd(ticker):
    path = FTD_DIR / f"{ticker}_ftd.json"
    if not path.exists(): return None
    with open(path) as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    return df.sort_values('date')

tickers = ["GME", "KOSS", "XRT", "AMC", "CHWY", "IWM", "BB"]

# =================================================================
# MAY 2024 WINDOW
# =================================================================
print("="*70)
print("MAY 2024 FTD TIMELINE — THE SETTLEMENT WINDOW")
print("="*70)

may_start = pd.Timestamp("2024-04-29")
may_end = pd.Timestamp("2024-06-14")

# Load and filter
may_data = {}
for t in tickers:
    df = load_ftd(t)
    if df is None: continue
    m = df[(df['date'] >= may_start) & (df['date'] <= may_end)]
    may_data[t] = m.set_index('date')
    total = int(m['quantity'].sum()) if not m.empty else 0
    records = len(m)
    print(f"  {t:5s}: {records:>3} records in window | Total FTD: {total:>12,}")

# Print daily timeline
print(f"\n  {'Date':<12}", end="")
for t in ["GME", "KOSS", "XRT", "AMC", "CHWY"]:
    print(f" | {t:>12}", end="")
print()
print("  " + "-" * 80)

all_dates = pd.date_range(may_start, may_end, freq='B')
for d in all_dates:
    line = f"  {d.strftime('%Y-%m-%d'):<12}"
    vals = []
    for t in ["GME", "KOSS", "XRT", "AMC", "CHWY"]:
        if t in may_data and d in may_data[t].index:
            v = may_data[t].loc[d]
            if isinstance(v, pd.DataFrame):
                v = int(v['quantity'].sum())
            else:
                v = int(v['quantity'])
        else:
            v = 0
        vals.append(v)
        line += f" | {v:>12,}"
    
    marker = ""
    ds = d.strftime('%Y-%m-%d')
    if ds == "2024-05-14":
        marker = " <-- C12 EXPLOSION (222x KOSS)"
    elif ds == "2024-05-15":
        marker = " <-- T+1 SETTLEMENT"
    elif ds == "2024-05-16":
        marker = " <-- T+2 SETTLEMENT"
    elif ds == "2024-05-17":
        marker = " <-- OpEx / TAPE FRACTURE"
    elif ds == "2024-05-20":
        marker = " <-- T+1 post-OpEx"
    elif ds == "2024-05-21":
        marker = " <-- T+2 post-OpEx"
    elif ds == "2024-05-13":
        marker = " <-- Roaring Kitty returns"
    
    if vals[0] > 500000 or vals[1] > 10000 or vals[2] > 500000:
        line += "  🚨"
    
    print(line + marker)

# =================================================================
# PEAK ANALYSIS
# =================================================================
print(f"\n{'='*70}")
print("MAY 2024 — PEAK FTD DAYS")
print("="*70)

for t in ["GME", "KOSS", "XRT", "AMC", "CHWY"]:
    if t not in may_data or may_data[t].empty: continue
    df = may_data[t].reset_index()
    top = df.nlargest(5, 'quantity')
    print(f"\n  {t} — Top 5:")
    for _, row in top.iterrows():
        print(f"    {row['date'].strftime('%Y-%m-%d')}: {int(row['quantity']):>12,} shares @ ${row['price']:.2f}")

# =================================================================
# FTD SURGE RATIOS — Before/After May 14
# =================================================================
print(f"\n{'='*70}")
print("FTD SURGE RATIOS — Event Week vs Baseline")
print("="*70)

baseline_start = pd.Timestamp("2024-04-01")
baseline_end = pd.Timestamp("2024-05-10")
event_start = pd.Timestamp("2024-05-13")
event_end = pd.Timestamp("2024-05-24")

for t in tickers:
    df = load_ftd(t)
    if df is None: continue
    
    baseline = df[(df['date'] >= baseline_start) & (df['date'] <= baseline_end)]
    event = df[(df['date'] >= event_start) & (df['date'] <= event_end)]
    
    b_avg = baseline['quantity'].mean() if not baseline.empty else 0
    e_avg = event['quantity'].mean() if not event.empty else 0
    ratio = e_avg / max(1, b_avg)
    
    b_total = int(baseline['quantity'].sum()) if not baseline.empty else 0
    e_total = int(event['quantity'].sum()) if not event.empty else 0
    
    marker = " 🚨" if ratio > 3 else ""
    print(f"  {t:5s}: Baseline avg {b_avg:>10,.0f} | Event avg {e_avg:>10,.0f} | Ratio: {ratio:>6.1f}x | Total: {b_total:>10,} → {e_total:>10,}{marker}")

# =================================================================
# XRT-GME ANTI-CORRELATION CHECK
# =================================================================
print(f"\n{'='*70}")
print("XRT-GME FTD ANTI-CORRELATION — May 2024")
print("="*70)

if "GME" in may_data and "XRT" in may_data:
    combined = pd.DataFrame({
        'GME': may_data['GME']['quantity'] if 'quantity' in may_data['GME'].columns else may_data['GME'],
        'XRT': may_data['XRT']['quantity'] if 'quantity' in may_data['XRT'].columns else may_data['XRT'],
    }).fillna(0)
    
    if len(combined) > 3:
        corr = combined['GME'].corr(combined['XRT'])
        print(f"  GME-XRT daily FTD correlation (May 2024): r = {corr:.3f}")
        if corr < -0.2:
            print(f"  ⚠️ NEGATIVE correlation confirms FTD shuffling pattern")
        elif corr > 0.5:
            print(f"  🚨 POSITIVE correlation — simultaneous stress")
        else:
            print(f"  Weak/no correlation — independent settlement")

# Save
out = {"may_2024_ftds": {}}
for t in ["GME", "KOSS", "XRT", "AMC", "CHWY"]:
    if t in may_data:
        out["may_2024_ftds"][t] = [
            {"date": row['date'].isoformat() if isinstance(row['date'], pd.Timestamp) else row.name.isoformat(), 
             "quantity": int(row['quantity']), "price": float(row['price'])}
            for _, row in may_data[t].reset_index().iterrows()
        ]

out_path = Path(__file__).parent / "round11_v4b_may2024_ftd.json"
with open(out_path, 'w') as f:
    json.dump(out, f, indent=2)
print(f"\nSaved to {out_path}")
