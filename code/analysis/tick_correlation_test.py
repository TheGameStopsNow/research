#!/usr/bin/env python3
"""
Zombie CUSIP Millisecond Correlation Test
=========================================
Pulls tick-level trade data from Polygon.io for GME, KOSS, AMC, SHLDQ, BLIAQ, BBBY
on key dates and runs pandas.merge_asof() to test for basket algorithm correlations.

Polygon.io Business ($200) tier provides:
  - Nanosecond-precision timestamps on trades
  - OTC market data (Pink Sheets)
  - Full historical tick data
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# Configuration
# ============================================================

POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "")
if not POLYGON_API_KEY:
    print("ERROR: Set POLYGON_API_KEY environment variable before running.")
    sys.exit(1)
BASE_URL = "https://api.polygon.io"

# Target symbols
NMS_SYMBOLS = ["GME", "KOSS", "AMC"]
OTC_SYMBOLS = ["SHLDQ", "BLIAQ", "BBBY", "EXPR"]
ALL_SYMBOLS = NMS_SYMBOLS + OTC_SYMBOLS

# Target dates
TARGET_DATES = [
    "2021-01-27",  # Original squeeze peak day
    "2021-01-28",  # PCO / trading halts
    "2024-05-17",  # 34ms options sweep
]

# Output directory (relative to repo root)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "results" / "zombie_basket"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Merge tolerances to test
TOLERANCES = ["1ms", "10ms", "50ms", "100ms", "500ms", "1s", "5s"]


def fetch_trades(symbol: str, date: str, limit: int = 50000) -> pd.DataFrame:
    """
    Fetch all trades for a symbol on a given date from Polygon.io.
    Uses pagination to get complete dataset.
    
    Polygon v3 trades endpoint returns nanosecond-precision timestamps.
    """
    all_results = []
    url = f"{BASE_URL}/v3/trades/{symbol}"
    params = {
        "timestamp.gte": f"{date}T04:00:00.000000000Z",  # Pre-market
        "timestamp.lte": f"{date}T23:59:59.999999999Z",   # After-hours
        "limit": limit,
        "sort": "timestamp",
        "order": "asc",
        "apiKey": POLYGON_API_KEY,
    }
    
    page = 0
    while True:
        page += 1
        print(f"  [{symbol}] Fetching page {page}...")
        
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                print(f"  [{symbol}] Rate limited, waiting 12s...")
                time.sleep(12)
                continue
            
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            print(f"  [{symbol}] ERROR: {e}")
            break
        
        results = data.get("results", [])
        if not results:
            break
            
        all_results.extend(results)
        print(f"  [{symbol}] Got {len(results)} trades (total: {len(all_results)})")
        
        # Check for pagination
        next_url = data.get("next_url")
        if not next_url:
            break
        
        # Follow pagination
        url = next_url
        params = {"apiKey": POLYGON_API_KEY}
        
        # Respect rate limits (5 req/min on free, unlimited on business)
        time.sleep(0.25)  
    
    if not all_results:
        print(f"  [{symbol}] No trades found for {date}")
        return pd.DataFrame()
    
    df = pd.DataFrame(all_results)
    
    # Convert SIP timestamp (nanoseconds) to datetime
    if "sip_timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["sip_timestamp"], unit="ns")
    elif "participant_timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["participant_timestamp"], unit="ns")
    elif "t" in df.columns:
        # v3 format uses 't' for timestamp in nanoseconds
        df["timestamp"] = pd.to_datetime(df["t"], unit="ns")
    else:
        print(f"  [{symbol}] WARNING: No timestamp column found. Columns: {list(df.columns)}")
        return pd.DataFrame()
    
    df["symbol"] = symbol
    
    # Rename price/size columns
    if "price" in df.columns:
        pass  # already named
    elif "p" in df.columns:
        df["price"] = df["p"]
    
    if "size" in df.columns:
        pass
    elif "s" in df.columns:
        df["size"] = df["s"]
    
    df = df.sort_values("timestamp").reset_index(drop=True)
    
    print(f"  [{symbol}] Total: {len(df)} trades, "
          f"time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    return df


def run_merge_asof_test(df_primary: pd.DataFrame, df_secondary: pd.DataFrame,
                        primary_sym: str, secondary_sym: str,
                        tolerance_str: str) -> dict:
    """
    Run a merge_asof between two trade dataframes and return match statistics.
    """
    if df_primary.empty or df_secondary.empty:
        return {
            "primary": primary_sym,
            "secondary": secondary_sym,
            "tolerance": tolerance_str,
            "primary_trades": len(df_primary),
            "secondary_trades": len(df_secondary),
            "matches": 0,
            "match_pct": 0.0,
        }
    
    tolerance = pd.Timedelta(tolerance_str)
    
    # Prepare dataframes
    left = df_primary[["timestamp", "price", "size"]].copy()
    left.columns = ["timestamp", f"price_{primary_sym}", f"size_{primary_sym}"]
    
    right = df_secondary[["timestamp", "price", "size"]].copy()
    right.columns = ["timestamp", f"price_{secondary_sym}", f"size_{secondary_sym}"]
    
    # Both must be sorted
    left = left.sort_values("timestamp")
    right = right.sort_values("timestamp")
    
    # merge_asof: for each trade in primary, find nearest trade in secondary within tolerance
    merged = pd.merge_asof(
        left, right,
        on="timestamp",
        tolerance=tolerance,
        direction="nearest",
    )
    
    # Count matches (non-NaN in secondary price)
    matches = merged[f"price_{secondary_sym}"].notna().sum()
    
    return {
        "primary": primary_sym,
        "secondary": secondary_sym,
        "tolerance": tolerance_str,
        "primary_trades": len(left),
        "secondary_trades": len(right),
        "matches": int(matches),
        "match_pct": round(matches / len(left) * 100, 2) if len(left) > 0 else 0.0,
    }


def run_correlation_test_for_date(date: str) -> dict:
    """
    For a given date, pull all tickers and run all pairwise correlations.
    """
    print(f"\n{'='*70}")
    print(f"DATE: {date}")
    print(f"{'='*70}")
    
    # Fetch all trade data
    trade_data = {}
    for symbol in ALL_SYMBOLS:
        print(f"\nFetching {symbol} ({date})...")
        df = fetch_trades(symbol, date)
        trade_data[symbol] = df
        
        # Save raw data
        if not df.empty:
            outfile = OUTPUT_DIR / f"{symbol}_{date}_trades.csv"
            df.to_csv(outfile, index=False)
            print(f"  Saved to {outfile}")
        
        # Rate limit between symbols
        time.sleep(0.5)
    
    # Run pairwise correlation tests (GME vs everything else)
    results = []
    primary_sym = "GME"
    
    if trade_data.get(primary_sym) is None or trade_data[primary_sym].empty:
        print(f"\nERROR: No GME data for {date}. Skipping correlation tests.")
        return {"date": date, "results": [], "trade_counts": {}}
    
    for secondary_sym in ALL_SYMBOLS:
        if secondary_sym == primary_sym:
            continue
        
        print(f"\n--- {primary_sym} vs {secondary_sym} ---")
        
        for tol in TOLERANCES:
            result = run_merge_asof_test(
                trade_data[primary_sym],
                trade_data[secondary_sym],
                primary_sym,
                secondary_sym,
                tol,
            )
            results.append(result)
            
            if result["matches"] > 0:
                print(f"  {tol}: {result['matches']} matches "
                      f"({result['match_pct']}% of GME trades)")
    
    # Also run KOSS vs zombie tests
    if trade_data.get("KOSS") is not None and not trade_data["KOSS"].empty:
        for secondary_sym in OTC_SYMBOLS:
            print(f"\n--- KOSS vs {secondary_sym} ---")
            for tol in TOLERANCES:
                result = run_merge_asof_test(
                    trade_data["KOSS"],
                    trade_data[secondary_sym],
                    "KOSS",
                    secondary_sym,
                    tol,
                )
                results.append(result)
                if result["matches"] > 0:
                    print(f"  {tol}: {result['matches']} matches "
                          f"({result['match_pct']}% of KOSS trades)")
    
    trade_counts = {sym: len(df) for sym, df in trade_data.items()}
    
    return {
        "date": date,
        "results": results,
        "trade_counts": trade_counts,
    }


def generate_report(all_date_results: list) -> str:
    """Generate a markdown report of all results."""
    lines = []
    lines.append("# Zombie CUSIP Millisecond Correlation Test — Results\n")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**Data Source:** Polygon.io (Business tier)\n")
    lines.append(f"**Symbols Tested:** {', '.join(ALL_SYMBOLS)}\n")
    lines.append(f"**Tolerances:** {', '.join(TOLERANCES)}\n")
    lines.append("---\n")
    
    for date_result in all_date_results:
        date = date_result["date"]
        trade_counts = date_result["trade_counts"]
        results = date_result["results"]
        
        lines.append(f"\n## {date}\n")
        lines.append("### Trade Counts\n")
        lines.append("| Symbol | Total Trades |")
        lines.append("| :--- | ---: |")
        for sym, count in trade_counts.items():
            lines.append(f"| {sym} | {count:,} |")
        lines.append("")
        
        if not results:
            lines.append("*No correlation tests run (missing data)*\n")
            continue
        
        # Group by primary/secondary pair
        pairs = {}
        for r in results:
            key = f"{r['primary']} vs {r['secondary']}"
            if key not in pairs:
                pairs[key] = []
            pairs[key].append(r)
        
        lines.append("### Correlation Results\n")
        
        for pair_name, pair_results in pairs.items():
            lines.append(f"#### {pair_name}\n")
            lines.append("| Tolerance | Matches | Match % | Primary Trades | Secondary Trades |")
            lines.append("| :--- | ---: | ---: | ---: | ---: |")
            
            for r in pair_results:
                flag = " **⚡**" if r["tolerance"] in ["1ms", "10ms"] and r["matches"] > 0 else ""
                lines.append(
                    f"| {r['tolerance']} | {r['matches']:,}{flag} | "
                    f"{r['match_pct']}% | {r['primary_trades']:,} | "
                    f"{r['secondary_trades']:,} |"
                )
            lines.append("")
    
    # Analysis section
    lines.append("---\n")
    lines.append("## Analysis Key\n")
    lines.append("- **⚡** = Match at 1ms or 10ms tolerance (strong basket algorithm indicator)\n")
    lines.append("- **Match %** = Percentage of primary symbol trades that had a matching ")
    lines.append("secondary symbol trade within the specified tolerance\n")
    lines.append("- A high match rate at tight tolerances (≤10ms) between GME and bankrupt ")
    lines.append("symbols is statistically extraordinary and suggests algorithmic basket execution\n")
    lines.append("- Baseline expectation: At 1ms tolerance, random matching between unrelated ")
    lines.append("securities should produce near-zero matches\n")
    
    return "\n".join(lines)


def main():
    print("=" * 70)
    print("ZOMBIE CUSIP MILLISECOND CORRELATION TEST")
    print(f"API Key: {POLYGON_API_KEY[:8]}...")
    print(f"Output: {OUTPUT_DIR}")
    print("=" * 70)
    
    all_date_results = []
    
    for date in TARGET_DATES:
        result = run_correlation_test_for_date(date)
        all_date_results.append(result)
        
        # Save intermediate JSON
        json_out = OUTPUT_DIR / f"correlation_{date}.json"
        with open(json_out, "w") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nSaved JSON: {json_out}")
    
    # Generate report
    report = generate_report(all_date_results)
    report_path = OUTPUT_DIR / "correlation_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nFinal report: {report_path}")
    
    # Also save full results as CSV
    all_results = []
    for dr in all_date_results:
        for r in dr["results"]:
            r["date"] = dr["date"]
            all_results.append(r)
    
    if all_results:
        results_df = pd.DataFrame(all_results)
        csv_path = OUTPUT_DIR / "correlation_results.csv"
        results_df.to_csv(csv_path, index=False)
        print(f"Full CSV: {csv_path}")
    
    print("\n✅ COMPLETE")


if __name__ == "__main__":
    main()
