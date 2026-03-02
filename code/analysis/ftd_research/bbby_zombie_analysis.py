"""
BBBY Zombie FTD Analysis (CORRECTED)
======================================
Examines whether post-cancellation BBBY FTDs represent active
bilateral novation (block-sized movements) or passive database
ghosting (admin rounding noise).

CORRECTION (Mar 2, 2026): The original analysis conflated two
different CUSIPs because the CSV was filtered by ticker symbol
("BBBY"), not by CUSIP. Beyond Inc. (formerly Overstock.com)
reclaimed the BBBY ticker on NYSE on Aug 29, 2025 under CUSIP
690370101. The original Bed Bath & Beyond CUSIP was 075896100.
The "824 days of zombie FTDs" claim was a ticker collision artifact.

The corrected BBBY_ftd.csv now contains only CUSIP 075896100 data
(567 records, Dec 2020 - Oct 2, 2023). There is only 1 genuine
post-cancellation FTD record (Oct 2, 2023).

Inputs:
  - data/ftd/BBBY_ftd.csv (corrected, CUSIP 075896100 only)

Output:
  - results/ftd_research/bbby_zombie_results.json
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
FTD_FILE = ROOT / "data" / "ftd" / "BBBY_ftd.csv"
OUT_FILE = ROOT / "results" / "ftd_research" / "bbby_zombie_results.json"

CANCELLATION_DATE = '2023-09-29'


def main():
    df = pd.read_csv(FTD_FILE, dtype=str)
    cols = [c.strip().lower() for c in df.columns]
    df.columns = cols
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['ftd'] = pd.to_numeric(df['quantity'], errors='coerce')
    df = df.dropna(subset=['date', 'ftd']).drop_duplicates('date').sort_values('date')

    print(f"BBBY FTD data (CUSIP 075896100 only): {len(df)} records, "
          f"{df['date'].min().date()} to {df['date'].max().date()}")

    post = df[df['date'] > CANCELLATION_DATE].copy()
    print(f"Post-cancellation: {len(post)} observations")

    results = {
        'test': 'BBBY_zombie_FTD_block_analysis',
        'correction_note': (
            'CORRECTED Mar 2, 2026: Original analysis conflated two CUSIPs. '
            'Beyond Inc. (Overstock) reclaimed BBBY ticker Aug 29, 2025 under '
            'CUSIP 690370101. Original BBBYQ CUSIP 075896100 has only 1 post-'
            'cancellation record (Oct 2, 2023). The "824 days of zombie FTDs" '
            'claim was a ticker collision artifact.'
        ),
        'cancellation_date': CANCELLATION_DATE,
        'total_records': len(df),
        'post_cancellation_records': len(post),
        'verdict': 'TICKER_COLLISION_ARTIFACT',
    }

    if len(post) >= 1:
        print(f"\nPost-cancellation records:")
        for _, row in post.iterrows():
            print(f"  {row['date'].date()} | qty={int(row['ftd']):,}")
        results['post_cancellation_dates'] = [
            str(row['date'].date()) for _, row in post.iterrows()
        ]
        results['post_cancellation_ftds'] = [
            int(row['ftd']) for _, row in post.iterrows()
        ]

    print(f"\nVerdict: TICKER_COLLISION_ARTIFACT")
    print("The '824 days of zombie FTDs' claim was based on conflating")
    print("the original BBBYQ (CUSIP 075896100) with Beyond Inc.'s")
    print("relisted BBBY (CUSIP 690370101).")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {OUT_FILE}")


if __name__ == '__main__':
    main()
