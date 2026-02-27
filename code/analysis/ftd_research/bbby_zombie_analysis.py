"""
BBBY Zombie FTD Analysis
=========================
Examines whether post-cancellation BBBY FTDs represent active
bilateral novation (block-sized movements) or passive database
ghosting (admin rounding noise).

Inputs:
  - data/ftd/BBBY_ftd.csv

Output:
  - results/ftd_research/bbby_zombie_results.json

Key finding: 43% block-sized (>=10K) deltas, 0% admin noise (<100).
824+ days after CUSIP cancellation, actively managed obligations persist.
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

    print(f"BBBY FTD data: {len(df)} records, {df['date'].min().date()} to {df['date'].max().date()}")

    post = df[df['date'] > CANCELLATION_DATE].copy()
    print(f"Post-cancellation: {len(post)} observations")

    if len(post) < 2:
        print("Insufficient post-cancellation data")
        return

    vals = post['ftd'].values
    deltas = [int(vals[i+1] - vals[i]) for i in range(len(vals) - 1)]

    blocks = sum(1 for d in deltas if abs(d) >= 10000)
    admin = sum(1 for d in deltas if abs(d) < 100)
    mid = len(deltas) - blocks - admin
    total = len(deltas) or 1

    print(f"\nBlock-sized (>=10K): {blocks}/{total} ({blocks/total*100:.0f}%)")
    print(f"Admin noise (<100):  {admin}/{total} ({admin/total*100:.0f}%)")
    print(f"Mid-range:           {mid}/{total} ({mid/total*100:.0f}%)")

    if blocks > total * 0.3 and admin == 0:
        verdict = "ACTIVE_NOVATION"
        print("\nActive ex-clearing bilateral novation indicated")
    elif admin > total * 0.5:
        verdict = "DATABASE_GHOSTING"
        print("\nAdmin rounding dominates - database ghosting")
    else:
        verdict = "MIXED"
        print("\nMixed signal")

    results = {
        'test': 'BBBY_zombie_FTD_block_analysis',
        'cancellation_date': CANCELLATION_DATE,
        'post_cancellation_records': len(post),
        'unique_values': len(post['ftd'].unique()),
        'block_sized': blocks,
        'admin_noise': admin,
        'mid_range': mid,
        'total_deltas': total,
        'verdict': verdict,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {OUT_FILE}")


if __name__ == '__main__':
    main()
