#!/usr/bin/env python3
"""
Backfill Missing Mid-Tenor ThetaData Trades (91-365 DTE)
=========================================================
The original fetch only captured weekly chains (max ~53 DTE).
This script fetches the missing 91-365d expirations for all dates
where we already have data, and merges them into the existing parquets.

Uses the existing ThetaData terminal on port 25503.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import sys

BASE_URL = "http://127.0.0.1:25503/v3"
DATA_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/trades/root=GME")

SESSION = requests.Session()
retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10, max_retries=retries)
SESSION.mount("http://", adapter)


def get_all_expirations():
    """Fetch all listed GME expirations from ThetaData."""
    url = f"{BASE_URL}/option/list/expirations?symbol=GME"
    resp = SESSION.get(url, timeout=10)
    if resp.status_code == 200:
        df = pd.read_csv(StringIO(resp.text))
        return df['expiration'].tolist()
    raise RuntimeError(f"Failed to get expirations: {resp.status_code}")


def fetch_trades_for_expiration(date_str, exp_ymd):
    """Fetch all trades for a single expiration on a single date."""
    url = f"{BASE_URL}/option/history/trade"
    params = {
        "symbol": "GME",
        "expiration": exp_ymd,
        "strike": 0,  # All strikes
        "date": date_str,
        "format": "csv"
    }
    try:
        resp = SESSION.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return None
        text = resp.text
        if text and len(text.splitlines()) > 1:
            df = pd.read_csv(StringIO(text))
            if 'root' not in df.columns:
                df['root'] = 'GME'
            if 'expiration' in df.columns and 'expiry' not in df.columns:
                df.rename(columns={'expiration': 'expiry'}, inplace=True)
            return df
    except Exception:
        pass
    return None


def get_existing_max_dte(date_str):
    """Check what max DTE exists in the current parquet for a date."""
    pq_path = DATA_DIR / f"date={date_str}" / "part-0.parquet"
    if not pq_path.exists():
        return None, 0
    try:
        df = pd.read_parquet(pq_path, columns=['expiry'])
        df['expiry_dt'] = pd.to_datetime(df['expiry'], errors='coerce')
        trade_dt = pd.Timestamp(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}")
        df['dte'] = (df['expiry_dt'] - trade_dt).dt.days
        return df['dte'].max(), len(df)
    except Exception:
        return None, 0


def main():
    print("=" * 70)
    print("Backfill Mid-Tenor ThetaData Trades (91-365d DTE)")
    print("=" * 70)

    # Get all expirations
    all_exps = get_all_expirations()
    all_exp_dts = {exp: datetime.strptime(exp, "%Y-%m-%d") for exp in all_exps}
    print(f"Total GME expirations in ThetaData: {len(all_exps)}")

    # Find all dates that need backfilling (2020-2025)
    date_dirs = sorted(DATA_DIR.glob("date=*"))
    dates_to_fix = []
    for d in date_dirs:
        date_str = d.name.replace("date=", "")
        year = int(date_str[:4])
        if 2020 <= year <= 2025:
            dates_to_fix.append(date_str)

    print(f"Dates to backfill: {len(dates_to_fix)} (2020-2025)")

    # Process each date
    total_new_trades = 0
    dates_updated = 0
    errors = 0

    for i, date_str in enumerate(dates_to_fix):
        trade_dt = datetime.strptime(date_str, "%Y%m%d")

        # Find expirations in the 91-365 DTE range for this date
        missing_exps = []
        for exp, exp_dt in all_exp_dts.items():
            dte = (exp_dt - trade_dt).days
            if 91 <= dte <= 400:  # Get everything we missed
                missing_exps.append((exp, dte))

        if not missing_exps:
            continue

        # Fetch all missing expirations for this date
        new_dfs = []
        for exp, dte in sorted(missing_exps, key=lambda x: x[1]):
            exp_ymd = exp.replace("-", "")
            df = fetch_trades_for_expiration(date_str, exp_ymd)
            if df is not None and len(df) > 0:
                new_dfs.append(df)

        if not new_dfs:
            if (i + 1) % 100 == 0:
                print(f"  [{i+1}/{len(dates_to_fix)}] {date_str} — no mid-tenor trades found")
            continue

        # Merge with existing data
        new_data = pd.concat(new_dfs, ignore_index=True)
        pq_path = DATA_DIR / f"date={date_str}" / "part-0.parquet"

        try:
            existing = pd.read_parquet(pq_path)
            merged = pd.concat([existing, new_data], ignore_index=True)
            # Deduplicate on key columns
            dedup_cols = [c for c in ['symbol', 'expiry', 'strike', 'right', 'timestamp', 'size', 'price']
                          if c in merged.columns]
            if dedup_cols:
                merged = merged.drop_duplicates(subset=dedup_cols)
            merged.to_parquet(pq_path, index=False)
            new_count = len(merged) - len(existing)
            total_new_trades += new_count
            dates_updated += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ERROR on {date_str}: {e}")

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(dates_to_fix)}] {date_str} — "
                  f"{dates_updated} dates updated, {total_new_trades:,} new trades, {errors} errors")

        # Rate limiting — be gentle with the terminal
        time.sleep(0.05)

    print(f"\n{'=' * 70}")
    print(f"BACKFILL COMPLETE")
    print(f"  Dates processed: {len(dates_to_fix)}")
    print(f"  Dates updated: {dates_updated}")
    print(f"  Total new trades added: {total_new_trades:,}")
    print(f"  Errors: {errors}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
