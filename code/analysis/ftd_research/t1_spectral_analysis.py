"""
T+1 Regime Shift: Spectral Analysis of FTD Periodicity
=======================================================
Compares FFT spectral power at T+33 and T+105 before and after
the T+1 transition (May 28, 2024) across multiple tickers.
Tests whether settlement timing changed the periodic structure
of failure-to-deliver obligations.

Inputs:
  - data/ftd/{GME,KOSS,AMC,XRT,AAPL,MSFT,TSLA}_ftd.csv

Output:
  - results/ftd_research/t1_spectral_results.json

Key finding: GME T+33 power dropped 92%, KOSS T+33 amplified +3,039%.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
FTD_DIR = ROOT / "data" / "ftd"
OUT_FILE = ROOT / "results" / "ftd_research" / "t1_spectral_results.json"

T1_DATE = pd.Timestamp('2024-05-28')
EXCLUSION_START = pd.Timestamp('2024-05-20')
EXCLUSION_END = pd.Timestamp('2024-06-07')


def load_ftd(ticker):
    f = FTD_DIR / f"{ticker}_ftd.csv"
    if not f.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(f, dtype=str)
    cols = [c.strip().lower() for c in df.columns]
    df.columns = cols
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['ftd'] = pd.to_numeric(df['quantity'], errors='coerce')
    return (df.dropna(subset=['date', 'ftd'])
              .drop_duplicates('date')
              .set_index('date')['ftd']
              .sort_index())


def spectral_power(series, target_period, window=5):
    x = series.values - series.values.mean()
    n = len(x)
    if n < target_period * 2:
        return 0
    fft_vals = np.fft.rfft(x)
    power = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0)
    periods = np.where(freqs > 0, 1.0 / freqs, np.inf)
    mask = (periods >= target_period - window) & (periods <= target_period + window)
    mean_power = power[1:].mean()
    if mask.any() and mean_power > 0:
        return float(power[mask].max() / mean_power)
    return 0


def main():
    tickers = ['GME', 'KOSS', 'AMC', 'XRT', 'AAPL', 'MSFT', 'TSLA']
    results = {}

    print(f"{'Ticker':<8} {'Pre T+33':>10} {'Post T+33':>10} {'Change':>10}  "
          f"{'Pre T+105':>10} {'Post T+105':>10} {'Change':>10}")
    print("-" * 80)

    for t in tickers:
        s = load_ftd(t)
        if len(s) < 100:
            continue
        pre = s[s.index < EXCLUSION_START]
        post = s[s.index > EXCLUSION_END]
        if len(pre) < 100 or len(post) < 50:
            continue

        pre_33 = spectral_power(pre, 33)
        post_33 = spectral_power(post, 33)
        pre_105 = spectral_power(pre, 105)
        post_105 = spectral_power(post, 105)

        chg_33 = ((post_33 / pre_33 - 1) * 100) if pre_33 > 0 else 0
        chg_105 = ((post_105 / pre_105 - 1) * 100) if pre_105 > 0 else 0

        print(f"{t:<8} {pre_33:>10.1f}x {post_33:>10.1f}x {chg_33:>+9.0f}%  "
              f"{pre_105:>10.1f}x {post_105:>10.1f}x {chg_105:>+9.0f}%")

        results[t] = {
            'pre_t33': pre_33, 'post_t33': post_33, 'change_t33_pct': chg_33,
            'pre_t105': pre_105, 'post_t105': post_105, 'change_t105_pct': chg_105,
        }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {OUT_FILE}")


if __name__ == '__main__':
    main()
