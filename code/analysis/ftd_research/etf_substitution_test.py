"""
ETF Substitution / Cross-Ticker Migration Test
===============================================
Tests whether XRT-style ETF creation/redemption acts as a
substitution channel for GME settlement obligations. Examines
cross-correlation and spectral coherence between GME FTDs and
XRT/basket-ticker FTDs before and after T+1.

Inputs:
  - data/ftd/{GME,XRT,KOSS,AMC}_ftd.csv

Output:
  - results/ftd_research/etf_substitution_results.json
"""

import numpy as np
import pandas as pd
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
FTD_DIR = ROOT / "data" / "ftd"
OUT_FILE = ROOT / "results" / "ftd_research" / "etf_substitution_results.json"

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
    tickers = ['GME', 'XRT', 'KOSS', 'AMC']
    results = {}

    for t in tickers:
        s = load_ftd(t)
        if len(s) < 100:
            continue

        pre = s[s.index < EXCLUSION_START]
        post = s[s.index > EXCLUSION_END]

        if len(pre) < 100 or len(post) < 30:
            continue

        # Cross-correlation with GME
        gme = load_ftd('GME')
        pre_gme = gme[gme.index < EXCLUSION_START]
        post_gme = gme[gme.index > EXCLUSION_END]

        # Compute lagged correlation (pre and post T+1)
        if t != 'GME':
            combined_pre = pd.DataFrame({'gme': pre_gme, t: pre}).dropna()
            combined_post = pd.DataFrame({'gme': post_gme, t: post}).dropna()
            corr_pre = combined_pre.corr().iloc[0, 1] if len(combined_pre) > 30 else 0
            corr_post = combined_post.corr().iloc[0, 1] if len(combined_post) > 30 else 0
        else:
            corr_pre = 1.0
            corr_post = 1.0

        # Spectral power at T+33
        pre_33 = spectral_power(pre, 33)
        post_33 = spectral_power(post, 33)
        chg_33 = ((post_33 / pre_33 - 1) * 100) if pre_33 > 0 else 0

        results[t] = {
            'correlation_with_gme_pre': float(corr_pre),
            'correlation_with_gme_post': float(corr_post),
            'pre_t33_power': pre_33,
            'post_t33_power': post_33,
            'change_t33_pct': chg_33,
        }

        print(f"{t}: corr(pre)={corr_pre:.3f} corr(post)={corr_post:.3f} "
              f"T+33 change={chg_33:+.0f}%")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {OUT_FILE}")


if __name__ == '__main__':
    main()
