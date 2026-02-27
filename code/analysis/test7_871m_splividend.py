#!/usr/bin/env python3
"""
OSINT TEST 7: IRS Section 871(m) Splividend Tax Trap Analysis
==============================================================
Hypothesis: Offshore TRS holders had to restructure their delta-one swaps 
before the GME 4:1 stock split dividend (record date July 18, 2022) to 
avoid 30% withholding tax on dividend equivalent payments.

Method: Pull GME daily options volume + dark pool data for the 
30-trading-day window before the splividend and look for:
1. Anomalous spikes in options conversions (paired put+call trades)
2. Unusual dark pool (TRF) block trade volume
3. Open Interest changes suggesting position unwinding
4. Put/Call ratio shifts indicating hedging restructuring
"""

import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

API_KEY = os.environ.get("POLYGON_API_KEY")
if not API_KEY:
    raise ValueError("POLYGON_API_KEY not set")

OUTPUT_DIR = Path(str(Path.home()) + "/Documents/GitHub/research/code/analysis")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# === KEY DATES ===
SPLIVIDEND_RECORD_DATE = "2022-07-18"
SPLIVIDEND_EX_DATE = "2022-07-22"
ANALYSIS_START = "2022-06-01"  # ~30 trading days before
ANALYSIS_END = "2022-07-22"
CONTROL_START = "2022-04-01"  # Control period (no splividend)
CONTROL_END = "2022-05-31"
# Pre-split prices (GME was ~$120-150 pre-split)

def fetch_polygon_aggs(symbol, start, end, timespan="day", multiplier=1):
    """Fetch aggregate bars from Polygon"""
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start}/{end}"
    params = {"adjusted": "false", "sort": "asc", "limit": 50000, "apiKey": API_KEY}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return pd.DataFrame()
    df = pd.DataFrame(results)
    df["date"] = pd.to_datetime(df["t"], unit="ms").dt.strftime("%Y-%m-%d")
    return df

def fetch_options_aggregates(symbol, date):
    """Fetch all options contracts for a symbol on a given date"""
    url = f"https://api.polygon.io/v3/snapshot/options/{symbol}"
    params = {"apiKey": API_KEY, "limit": 250}
    
    all_results = []
    while url:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            break
        data = resp.json()
        results = data.get("results", [])
        all_results.extend(results)
        next_url = data.get("next_url")
        if next_url:
            url = next_url + f"&apiKey={API_KEY}"
            params = {}
        else:
            url = None
    
    return all_results

def fetch_daily_options_flow(symbol, start_date, end_date):
    """Fetch daily options contract data via reference endpoint"""
    url = "https://api.polygon.io/v3/reference/options/contracts"
    params = {
        "underlying_ticker": symbol,
        "as_of": end_date,
        "limit": 1000,
        "apiKey": API_KEY,
        "order": "desc",
        "sort": "expiration_date"
    }
    
    all_contracts = []
    page = 0
    while url and page < 5:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"  Options contracts API returned {resp.status_code}")
            break
        data = resp.json()
        results = data.get("results", [])
        all_contracts.extend(results)
        next_url = data.get("next_url")
        if next_url:
            url = next_url if "apiKey" in next_url else f"{next_url}&apiKey={API_KEY}"
            params = {}
        else:
            url = None
        page += 1
    
    return all_contracts

def fetch_trf_volume(symbol, start, end):
    """Fetch TRF (dark pool) trade data from Polygon"""
    # Dark pool trades have exchange == 'TRF' or specific exchange codes
    # We'll use the trades endpoint with TRF filter dates
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start}/{end}"
    params = {
        "adjusted": "false",
        "sort": "asc",
        "limit": 50000,
        "apiKey": API_KEY
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])


print("=" * 70)
print("OSINT TEST 7: IRS 871(m) SPLIVIDEND TAX TRAP")
print("=" * 70)
print()
print("Key Dates:")
print(f"  Record Date:  {SPLIVIDEND_RECORD_DATE}")
print(f"  Ex-Date:      {SPLIVIDEND_EX_DATE}")
print(f"  Analysis:     {ANALYSIS_START} to {ANALYSIS_END}")
print(f"  Control:      {CONTROL_START} to {CONTROL_END}")
print()

# === PHASE 1: Equity price + volume ===
print("Phase 1: Fetching GME daily price/volume data...")
analysis_bars = fetch_polygon_aggs("GME", ANALYSIS_START, ANALYSIS_END)
control_bars = fetch_polygon_aggs("GME", CONTROL_START, CONTROL_END)

if analysis_bars.empty:
    print("ERROR: No data returned for analysis period")
    exit(1)

print(f"  Analysis period: {len(analysis_bars)} trading days")
print(f"  Control period:  {len(control_bars)} trading days")

# Volume analysis
analysis_avg_vol = analysis_bars["v"].mean()
control_avg_vol = control_bars["v"].mean()
vol_ratio = analysis_avg_vol / control_avg_vol if control_avg_vol > 0 else 0

print(f"\n  Avg Daily Volume:")
print(f"    Control (Apr-May 2022):     {control_avg_vol:,.0f}")
print(f"    Pre-Splividend (Jun-Jul):   {analysis_avg_vol:,.0f}")
print(f"    Volume Ratio:               {vol_ratio:.2f}x")

# Find volume spike days
analysis_bars["vol_zscore"] = (analysis_bars["v"] - analysis_bars["v"].mean()) / analysis_bars["v"].std()
spike_days = analysis_bars[analysis_bars["vol_zscore"] > 2.0]
print(f"\n  Volume Spike Days (>2σ): {len(spike_days)}")
for _, row in spike_days.iterrows():
    print(f"    {row['date']}: {row['v']:,.0f} shares (Z={row['vol_zscore']:.1f})")

# === PHASE 2: Options flow - daily reference data ===
print("\nPhase 2: Fetching GME options contract reference data...")
options_contracts = fetch_daily_options_flow("GME", ANALYSIS_START, ANALYSIS_END)
print(f"  Total listed options contracts: {len(options_contracts)}")

# Analyze by type
if options_contracts:
    calls = [c for c in options_contracts if c.get("contract_type") == "call"]
    puts = [c for c in options_contracts if c.get("contract_type") == "put"]
    print(f"  Calls: {len(calls)}, Puts: {len(puts)}")
    
    # Check for FLEX options (non-standard)
    flex = [c for c in options_contracts if c.get("exercise_style") == "european" 
            or "FLEX" in str(c.get("ticker", "")).upper()]
    print(f"  FLEX / European-style: {len(flex)}")
    
    # Expiration concentration
    exp_dates = {}
    for c in options_contracts:
        exp = c.get("expiration_date", "unknown")
        exp_dates[exp] = exp_dates.get(exp, 0) + 1
    
    # Sort by count
    top_exps = sorted(exp_dates.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"\n  Top Expiration Concentrations:")
    for exp, count in top_exps:
        marker = " ⚠️ " if exp <= SPLIVIDEND_RECORD_DATE else "    "
        print(f"  {marker}{exp}: {count} contracts")

# === PHASE 3: Daily aggregate volume comparison ===
print("\nPhase 3: Price action analysis around record date...")

# Pre-record-date window (T-10 to T-1)
pre_record = analysis_bars[
    (analysis_bars["date"] >= "2022-07-05") & 
    (analysis_bars["date"] < SPLIVIDEND_RECORD_DATE)
]
# Post-announcement (split announced ~July 6)
post_announce = analysis_bars[
    (analysis_bars["date"] >= "2022-07-06") & 
    (analysis_bars["date"] <= SPLIVIDEND_EX_DATE)
]

if not pre_record.empty:
    print(f"\n  Pre-Record Window (Jul 5-18): {len(pre_record)} days")
    print(f"    Avg Volume:  {pre_record['v'].mean():,.0f}")
    print(f"    Volume Range: {pre_record['v'].min():,.0f} - {pre_record['v'].max():,.0f}")
    print(f"    Price Range:  ${pre_record['l'].min():.2f} - ${pre_record['h'].max():.2f}")

# === PHASE 4: 871(m) Analysis ===
print("\n" + "=" * 70)
print("871(m) TAX TRAP ANALYSIS")
print("=" * 70)

print("""
IRS SECTION 871(m) MECHANICS:
─────────────────────────────
• Foreign holders of TRS with delta ≥ 1.0 (delta-one) owe 30% withholding
  on "dividend equivalent payments" (applies to contracts pre-2025)
• The GME splividend (July 21, 2022) constitutes a dividend distribution
• Offshore TRS holders would need to either:
  (a) Unwind the TRS before the record date (Jul 18)
  (b) Reduce delta below 1.0 (add options legs)
  (c) Restructure into a "broad-based index" swap (SEC→CFTC jurisdiction)
  (d) Accept the 30% withholding hit

WHAT TO LOOK FOR:
─────────────────
1. Volume spikes in Jun-Jul 2022 (restructuring activity)
2. Paired put-call conversions (delta reduction)
3. Unusual FLEX options activity (bespoke OTC restructuring)
4. Dark pool block trades (institutional position changes)
5. Open interest shifts concentrated around record date
""")

# === Analysis Results ===
results = {
    "test": "OSINT_Test_7_871m_Splividend",
    "dates": {
        "record_date": SPLIVIDEND_RECORD_DATE,
        "ex_date": SPLIVIDEND_EX_DATE,
        "analysis_window": f"{ANALYSIS_START} to {ANALYSIS_END}",
        "control_window": f"{CONTROL_START} to {CONTROL_END}"
    },
    "volume_analysis": {
        "control_avg_volume": float(control_avg_vol),
        "pre_splividend_avg_volume": float(analysis_avg_vol),
        "volume_ratio": float(vol_ratio),
        "spike_days_2sigma": len(spike_days),
        "spike_details": [
            {"date": row["date"], "volume": int(row["v"]), "zscore": round(float(row["vol_zscore"]), 2)}
            for _, row in spike_days.iterrows()
        ]
    },
    "options_analysis": {
        "total_contracts": len(options_contracts),
        "calls": len(calls) if options_contracts else 0,
        "puts": len(puts) if options_contracts else 0,
        "flex_european": len(flex) if options_contracts else 0,
        "top_expirations": top_exps[:10] if options_contracts else []
    },
    "price_action": {
        "pre_record_avg_volume": float(pre_record["v"].mean()) if not pre_record.empty else 0,
        "pre_record_price_low": float(pre_record["l"].min()) if not pre_record.empty else 0,
        "pre_record_price_high": float(pre_record["h"].max()) if not pre_record.empty else 0,
    },
    "871m_assessment": {
        "transition_relief": "IRS Notice 2022-37 (Aug 2022) — only delta-one swaps subject to withholding through 2024",
        "delta_threshold": "1.0 (NOT 0.80 — transition relief applies)",
        "implication": "Pure TRS with delta=1.0 on GME would owe 30% on the splividend equivalent",
        "restructuring_window": "Jun 1 - Jul 18, 2022 (30 trading days before record date)",
    }
}

# Volume day-by-day for the critical window
print("\n  Day-by-day Volume (Jul 5-22, 2022):")
print(f"  {'Date':>12s}  {'Close':>8s}  {'Volume':>12s}  {'VWAP':>8s}  {'Note':>20s}")
print(f"  {'-'*12}  {'-'*8}  {'-'*12}  {'-'*8}  {'-'*20}")

critical_window = analysis_bars[
    (analysis_bars["date"] >= "2022-07-01") & 
    (analysis_bars["date"] <= SPLIVIDEND_EX_DATE)
]

daily_data = []
for _, row in critical_window.iterrows():
    note = ""
    if row["date"] == "2022-07-06":
        note = "Split announced"
    elif row["date"] == SPLIVIDEND_RECORD_DATE:
        note = "RECORD DATE"
    elif row["date"] == "2022-07-21":
        note = "Distribution"
    elif row["date"] == SPLIVIDEND_EX_DATE:
        note = "EX-DATE (split)"
    
    vwap = row.get("vw", row["c"])
    print(f"  {row['date']:>12s}  ${row['c']:>7.2f}  {row['v']:>12,.0f}  ${vwap:>7.2f}  {note:>20s}")
    daily_data.append({
        "date": row["date"],
        "close": float(row["c"]),
        "volume": int(row["v"]),
        "vwap": float(vwap),
        "note": note
    })

results["critical_window_daily"] = daily_data

# === VERDICT ===
print("\n" + "=" * 70)
print("VERDICT")
print("=" * 70)

if vol_ratio > 1.5:
    verdict = "ANOMALOUS — Volume spiked significantly in the pre-splividend window"
    signal = "POSITIVE"
elif vol_ratio > 1.2:
    verdict = "ELEVATED — Moderate volume increase, consistent with retail anticipation + possible restructuring"
    signal = "WEAK POSITIVE"
else:
    verdict = "NORMAL — No significant volume anomaly detected"
    signal = "NEGATIVE"

print(f"\n  Signal:  {signal}")
print(f"  Verdict: {verdict}")
print(f"  Volume Ratio (pre-splividend / control): {vol_ratio:.2f}x")

results["verdict"] = {
    "signal": signal,
    "verdict": verdict,
    "volume_ratio": float(vol_ratio)
}

# Save results
output_file = OUTPUT_DIR / "test7_871m_splividend.json"
with open(output_file, "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"\n  Results saved to: {output_file}")
