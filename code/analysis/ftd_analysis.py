#!/usr/bin/env python3
"""
Vector 4: Reg SHO FTD Analysis — The FTD Shuffle
Analyze SEC FTD data for GME, KOSS, XRT, AMC around key event windows.
NOTE: FTD data extends Dec 2020 – Aug 2023 (covers Jan 2021 squeeze but NOT May 2024).
"""
import json, numpy as np, pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

FTD_DIR = Path("[REPO_PATH]/data/raw/sec_ftd")
OUT_DIR = Path(__file__).parent

# Load all FTD data
def load_ftd(ticker):
    path = FTD_DIR / f"{ticker}_ftd.json"
    if not path.exists(): return None
    with open(path) as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
    df = df.sort_values('date')
    return df

tickers = ["GME", "KOSS", "XRT", "AMC", "IWM", "BB", "BBBY", "CHWY"]
ftd_data = {}
for t in tickers:
    df = load_ftd(t)
    if df is not None:
        ftd_data[t] = df
        print(f"  {t:5s}: {len(df):>5,} records | {df['date'].min().strftime('%Y-%m-%d')} – {df['date'].max().strftime('%Y-%m-%d')} | Total: {df['quantity'].sum():>15,} shares")

# =================================================================
# ANALYSIS 1: January 2021 Squeeze Window
# =================================================================
print(f"\n{'='*70}")
print("ANALYSIS 1: JANUARY 2021 SQUEEZE — FTD TIMELINE")
print(f"{'='*70}")

jan_start = pd.Timestamp("2021-01-04")
jan_end = pd.Timestamp("2021-02-28")

print(f"\n  {'Date':<12} | {'GME':>12} | {'KOSS':>12} | {'AMC':>12} | {'XRT':>12} | {'BB':>12} | {'IWM':>12}")
print("  " + "-" * 85)

# Build daily FTD for January window
jan_dates = pd.date_range(jan_start, jan_end, freq='B')
jan_ftds = {}
for t in ["GME", "KOSS", "AMC", "XRT", "BB", "IWM"]:
    if t not in ftd_data: continue
    df = ftd_data[t]
    df_jan = df[(df['date'] >= jan_start) & (df['date'] <= jan_end)]
    jan_ftds[t] = df_jan.set_index('date')['quantity']

# Print daily
for d in jan_dates:
    vals = []
    for t in ["GME", "KOSS", "AMC", "XRT", "BB", "IWM"]:
        if t in jan_ftds and d in jan_ftds[t].index:
            v = jan_ftds[t].loc[d]
            # Handle potential duplicates (multiple entries per date)
            if isinstance(v, pd.Series):
                v = int(v.sum())
            else:
                v = int(v)
        else:
            v = 0
        vals.append(v)
    
    marker = ""
    if d.strftime('%Y-%m-%d') in ["2021-01-27", "2021-01-28", "2021-01-29"]:
        marker = " <-- SQUEEZE PEAK"
    elif d.strftime('%Y-%m-%d') in ["2021-02-01", "2021-02-02"]:
        marker = " <-- T+2 SETTLEMENT"
    
    gme_val = vals[0]
    line = f"  {d.strftime('%Y-%m-%d'):<12}"
    for v in vals:
        line += f" | {v:>12,}"
    
    if gme_val > 1000000:
        line += "  🚨"
    line += marker
    print(line)

# =================================================================
# ANALYSIS 2: Peak FTD Events by Ticker
# =================================================================
print(f"\n{'='*70}")
print("ANALYSIS 2: TOP 10 FTD DAYS PER TICKER")
print(f"{'='*70}")

for t in ["GME", "KOSS", "AMC", "XRT"]:
    if t not in ftd_data: continue
    df = ftd_data[t]
    top10 = df.nlargest(10, 'quantity')
    print(f"\n  {t}:")
    print(f"  {'Date':<12} | {'FTD Shares':>15} | {'Price':>8}")
    for _, row in top10.iterrows():
        print(f"  {row['date'].strftime('%Y-%m-%d'):<12} | {int(row['quantity']):>15,} | ${row['price']:>7.2f}")

# =================================================================
# ANALYSIS 3: FTD Shuffle — Cross-Ticker Correlation
# =================================================================
print(f"\n{'='*70}")
print("ANALYSIS 3: FTD SHUFFLE — CROSS-TICKER CORRELATION")
print(f"{'='*70}")

# Build weekly FTD for correlation
for t in ftd_data:
    df = ftd_data[t]
    df['week'] = df['date'].dt.isocalendar().week.astype(int) + df['date'].dt.year * 100

# Create weekly pivot
all_weekly = {}
for t in ["GME", "KOSS", "AMC", "XRT", "IWM"]:
    if t not in ftd_data: continue
    df = ftd_data[t]
    df['yearweek'] = df['date'].dt.strftime('%Y-W%U')
    weekly = df.groupby('yearweek')['quantity'].sum()
    all_weekly[t] = weekly

if len(all_weekly) >= 2:
    weekly_df = pd.DataFrame(all_weekly).fillna(0)
    print(f"\n  Weekly FTD correlations ({len(weekly_df)} weeks):")
    print(f"\n        {'GME':>8} {'KOSS':>8} {'AMC':>8} {'XRT':>8} {'IWM':>8}")
    for t1 in ["GME", "KOSS", "AMC", "XRT", "IWM"]:
        if t1 not in weekly_df.columns: continue
        line = f"  {t1:5s}"
        for t2 in ["GME", "KOSS", "AMC", "XRT", "IWM"]:
            if t2 not in weekly_df.columns:
                line += f" {'N/A':>8}"
                continue
            corr = weekly_df[t1].corr(weekly_df[t2])
            line += f" {corr:>8.3f}"
        print(line)

# =================================================================
# ANALYSIS 4: FTD Surge Events — Synchronized Spikes
# =================================================================
print(f"\n{'='*70}")
print("ANALYSIS 4: SYNCHRONIZED FTD SURGES")
print(f"{'='*70}")

# Find dates where multiple basket tickers have abnormally high FTDs
# Use 3-sigma threshold per ticker
surge_dates = {}
for t in ["GME", "KOSS", "AMC", "XRT"]:
    if t not in ftd_data: continue
    df = ftd_data[t]
    mean = df['quantity'].mean()
    std = df['quantity'].std()
    threshold = mean + 3 * std
    surges = df[df['quantity'] > threshold]
    surge_dates[t] = set(surges['date'].dt.strftime('%Y-%m-%d'))
    print(f"  {t:4s}: Mean={mean:>12,.0f} | 3σ threshold={threshold:>12,.0f} | Surge days: {len(surges)}")

# Find dates with 2+ simultaneous surges
all_surge_dates = set()
for t, dates in surge_dates.items():
    all_surge_dates |= dates

multi_surges = []
for d in sorted(all_surge_dates):
    surge_tickers = [t for t in surge_dates if d in surge_dates[t]]
    if len(surge_tickers) >= 2:
        multi_surges.append((d, surge_tickers))

print(f"\n  Synchronized surges (2+ basket tickers on same date): {len(multi_surges)}")
for d, tickers in multi_surges:
    vals = []
    for t in ["GME", "KOSS", "AMC", "XRT"]:
        if t in ftd_data:
            df = ftd_data[t]
            row = df[df['date'].dt.strftime('%Y-%m-%d') == d]
            v = int(row['quantity'].sum()) if not row.empty else 0
            vals.append(f"{v:>10,}")
        else:
            vals.append(f"{'N/A':>10}")
    marker = " 🚨 BASKET SURGE" if len(tickers) >= 3 else ""
    print(f"  {d} | {' | '.join(vals)} | Surging: {', '.join(tickers)}{marker}")

# Save results
out = {
    "date_range": {t: [ftd_data[t]['date'].min().isoformat(), ftd_data[t]['date'].max().isoformat()] for t in ftd_data},
    "total_ftds": {t: int(ftd_data[t]['quantity'].sum()) for t in ftd_data},
    "multi_surge_events": [(d, tickers) for d, tickers in multi_surges],
}

out_path = OUT_DIR / "round11_v4_ftd_analysis.json"
with open(out_path, 'w') as f:
    json.dump(out, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
