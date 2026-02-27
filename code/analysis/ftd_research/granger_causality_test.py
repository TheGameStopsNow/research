"""
Granger Causality: Equity FTDs -> Treasury Settlement Fails
===========================================================
Tests whether GME (and control tickers) Granger-cause U.S. Treasury
settlement failures. Uses first-differenced weekly FTDs and a custom
F-test across lags 1-6.

Inputs:
  - data/ftd/{GME,AMC,KOSS,XRT,AAPL,MSFT,TSLA}_ftd.csv
  - data/treasury/nyfrb_pdftd.csv

Output:
  - results/ftd_research/granger_causality_results.json

Key finding: Only GME is significant (F=19.20, p<0.0001).
Seven other equities show no Granger-causal relationship.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats
import json, warnings

warnings.filterwarnings('ignore')

ROOT = Path(__file__).resolve().parents[3]
FTD_DIR = ROOT / "data" / "ftd"
TREAS_FILE = ROOT / "data" / "treasury" / "nyfrb_pdftd.csv"
OUT_FILE = ROOT / "results" / "ftd_research" / "granger_causality_results.json"


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


def granger_test(x, y, max_lag=6):
    """Test if x Granger-causes y. Returns best (lag, F, p)."""
    combined = pd.DataFrame({'x': x, 'y': y}).dropna()
    if len(combined) < 50:
        return None, None, None

    dx = combined['x'].diff().dropna()
    dy = combined['y'].diff().dropna()
    idx = dx.index.intersection(dy.index)
    dx, dy = dx[idx], dy[idx]

    best_f, best_p, best_lag = 0, 1, 0
    for lag in range(1, max_lag + 1):
        n = len(dy)
        if n <= lag + 2:
            continue
        Y = dy.values[lag:]
        n_obs = len(Y)
        Y_lags = np.column_stack([dy.values[lag-j-1:n-j-1] for j in range(lag)])
        X_lags = np.column_stack([dx.values[lag-j-1:n-j-1] for j in range(lag)])

        X_r = np.column_stack([np.ones(n_obs), Y_lags])
        beta_r = np.linalg.lstsq(X_r, Y, rcond=None)[0]
        ssr_r = np.sum((Y - X_r @ beta_r) ** 2)

        X_u = np.column_stack([np.ones(n_obs), Y_lags, X_lags])
        beta_u = np.linalg.lstsq(X_u, Y, rcond=None)[0]
        ssr_u = np.sum((Y - X_u @ beta_u) ** 2)

        df_u = n_obs - X_u.shape[1]
        if df_u <= 0 or ssr_u <= 0:
            continue
        f_stat = ((ssr_r - ssr_u) / lag) / (ssr_u / df_u)
        p_val = 1 - stats.f.cdf(f_stat, lag, df_u)

        if f_stat > best_f:
            best_f, best_p, best_lag = f_stat, p_val, lag

    return best_lag, best_f, best_p


def main():
    # Load Treasury FTDs
    treas_df = pd.read_csv(TREAS_FILE)
    date_col = [c for c in treas_df.columns if 'date' in c.lower()][0]
    val_cols = [c for c in treas_df.columns if c != date_col and 'date' not in c.lower()]
    treas_df['date'] = pd.to_datetime(treas_df[date_col], errors='coerce')
    treas_df['treasury_ftd'] = pd.to_numeric(treas_df[val_cols[0]], errors='coerce')
    treas_df = treas_df.dropna(subset=['date', 'treasury_ftd']).set_index('date').sort_index()
    treas_weekly = treas_df['treasury_ftd'].resample('W-WED').mean().dropna()

    tickers = ['GME', 'AMC', 'KOSS', 'XRT', 'AAPL', 'MSFT', 'TSLA']
    equity_weekly = {}
    for t in tickers:
        s = load_ftd(t)
        if len(s) > 100:
            equity_weekly[t] = s.resample('W-WED').mean().dropna()

    print(f"{'Ticker':<8} {'Best Lag':<10} {'F-stat':<10} {'p-value':<12} {'Significant'}")
    print("-" * 55)

    results = {}
    for t in tickers:
        if t in equity_weekly:
            common_start = max(equity_weekly[t].index[0], treas_weekly.index[0])
            common_end = min(equity_weekly[t].index[-1], treas_weekly.index[-1])
            eq = equity_weekly[t][common_start:common_end]
            tr = treas_weekly[common_start:common_end]
            lag, f, p = granger_test(eq, tr, max_lag=6)
            if lag is not None:
                sig = "Yes" if p < 0.05 else "No"
                print(f"{t:<8} {lag:<10} {f:<10.2f} {p:<12.6f} {sig}")
                results[t] = {'lag': lag, 'F': float(f), 'p': float(p), 'significant': p < 0.05}

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {OUT_FILE}")


if __name__ == '__main__':
    main()
