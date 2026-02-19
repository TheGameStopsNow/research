"""
NBBO Midquote ACF Robustness Test
==================================
Paper I §7.1–§7.2: Bid-Ask Bounce Confound Quantification

This script fetches NBBO quotes and trades from the Polygon API for a panel of
tickers on a sample of recent trading dates, computes:

  1. Trade-price ACF₁  (using last-trade prices, matching the paper's methodology)
  2. Midquote ACF₁      (using NBBO midpoint = (bid + ask) / 2)
  3. Bounce component   = Trade ACF₁ − Midquote ACF₁

If bid-ask bounce is negligible, Trade ACF₁ ≈ Midquote ACF₁ and the bounce
component ≈ 0.  If bounce is the dominant driver, the midquote ACF₁ should be
close to zero.

Usage:
    export POLYGON_API_KEY=<your key>
    python nbbo_midquote_acf_test.py [--tickers AAPL MSFT GME TSLA] [--dates 2024-12-02 ...]

Output:
    - Console table with per-ticker, per-date ACF comparison
    - JSON results file at data/nbbo_acf_results.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("POLYGON_API_KEY")
BASE_URL = "https://api.polygon.io/v3"

# ============================================================================
# Default test parameters (per Paper I §7.2)
# ============================================================================
DEFAULT_TICKERS = ["AAPL", "MSFT", "GME", "TSLA"]
DEFAULT_DATES = [
    "2024-12-02", "2024-12-03", "2024-12-04", "2024-12-05", "2024-12-06",
    "2024-12-09", "2024-12-10", "2024-12-11", "2024-12-12", "2024-12-13",
]
INTERVAL_SEC = 60.0       # 1-minute bars (matching paper methodology)
MAX_LAG = 5               # Only need lag-1 for the test, but compute a few extra
RTH_START = "09:30"       # Regular Trading Hours
RTH_END = "16:00"

# ============================================================================
# Polygon API fetch (adapted from fetch_polygon_ticks.py)
# ============================================================================

def fetch_polygon_pages(url: str, params: dict) -> list:
    """Paginate through Polygon v3 results."""
    all_results = []
    params["apiKey"] = API_KEY
    params["limit"] = 50000

    current_url = url
    page = 0

    while current_url:
        try:
            resp = requests.get(current_url, params=params, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", [])
            all_results.extend(results)
            page += 1

            current_url = data.get("next_url")
            if current_url:
                if "apiKey" not in current_url:
                    current_url += f"&apiKey={API_KEY}"
                params = {}  # params are embedded in next_url

            # Rate limiting — Polygon free tier = 5 req/min
            time.sleep(0.25)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"    ⚠ 403 Forbidden — check API tier. Stopping.")
                break
            elif e.response.status_code == 429:
                print(f"    ⚠ Rate limited. Sleeping 12s...")
                time.sleep(12)
                continue
            else:
                print(f"    ⚠ HTTP {e.response.status_code}: {e}")
                break
        except Exception as e:
            print(f"    ⚠ Error: {e}")
            time.sleep(2)
            continue

    return all_results


def fetch_trades(symbol: str, date: str) -> pd.DataFrame:
    """Fetch trade ticks for a single symbol/date."""
    url = f"{BASE_URL}/trades/{symbol}"
    params = {"timestamp": date}
    records = fetch_polygon_pages(url, params)
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["sip_timestamp"], unit="ns", errors="coerce")
    df = df.dropna(subset=["timestamp"])
    cols = ["timestamp", "price", "size"]
    return df[[c for c in cols if c in df.columns]]


def fetch_quotes(symbol: str, date: str) -> pd.DataFrame:
    """Fetch NBBO quote ticks for a single symbol/date."""
    url = f"{BASE_URL}/quotes/{symbol}"
    params = {"timestamp": date}
    records = fetch_polygon_pages(url, params)
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["sip_timestamp"], unit="ns", errors="coerce")
    df = df.dropna(subset=["timestamp"])
    cols = ["timestamp", "bid_price", "bid_size", "ask_price", "ask_size"]
    return df[[c for c in cols if c in df.columns]]


# ============================================================================
# ACF computation (replicates acf_engine.compute_daily_acf methodology)
# ============================================================================

def compute_acf_from_prices(
    prices: pd.Series,
    timestamps: pd.Series,
    interval_sec: float = INTERVAL_SEC,
    max_lag: int = MAX_LAG,
) -> np.ndarray:
    """
    Compute ACF at lags 1..max_lag for a price series.

    Methodology (matching Paper I):
    1. Resample to fixed-width bars (last price per bar)
    2. Compute log returns
    3. Compute sample autocorrelation
    """
    # Use numpy for sorting to avoid pandas 3.14 argsort bug on large arrays
    ts_arr = np.array(timestamps.values, dtype="datetime64[ns]")
    pr_arr = np.array(prices.values, dtype=np.float64)

    # Remove NaT/NaN
    valid = ~(np.isnat(ts_arr) | np.isnan(pr_arr))
    ts_arr = ts_arr[valid]
    pr_arr = pr_arr[valid]

    if len(ts_arr) < 100:
        return np.full(max_lag, np.nan)

    # Sort by timestamp using numpy
    sort_idx = np.argsort(ts_arr)
    ts_arr = ts_arr[sort_idx]
    pr_arr = pr_arr[sort_idx]

    # Build sorted DataFrame for resample
    df = pd.DataFrame({"price": pr_arr}, index=pd.DatetimeIndex(ts_arr, name="ts"))

    # Filter to Regular Trading Hours
    df = df.between_time(RTH_START, RTH_END)
    if len(df) < 100:
        return np.full(max_lag, np.nan)

    bars = df.resample(f"{int(interval_sec)}s").last().dropna()
    returns = bars["price"].pct_change().dropna().values

    if len(returns) < max_lag + 10:
        return np.full(max_lag, np.nan)

    n = len(returns)
    mean = returns.mean()
    var = np.var(returns)
    if var < 1e-12:
        return np.full(max_lag, np.nan)

    acf = np.zeros(max_lag)
    for lag in range(1, max_lag + 1):
        acf[lag - 1] = (
            np.mean((returns[: n - lag] - mean) * (returns[lag:] - mean)) / var
        )
    return acf


def compute_midquote_acf(quotes_df: pd.DataFrame, **kwargs) -> np.ndarray:
    """Compute ACF from NBBO midquote prices."""
    if quotes_df.empty:
        return np.full(MAX_LAG, np.nan)

    # Filter out crossed/locked quotes and zero-price quotes
    valid = (
        (quotes_df["bid_price"] > 0)
        & (quotes_df["ask_price"] > 0)
        & (quotes_df["ask_price"] >= quotes_df["bid_price"])
    )
    df = quotes_df[valid].copy()
    if len(df) < 100:
        return np.full(MAX_LAG, np.nan)

    midquote = (df["bid_price"] + df["ask_price"]) / 2.0
    return compute_acf_from_prices(midquote, df["timestamp"], **kwargs)


def compute_trade_acf(trades_df: pd.DataFrame, **kwargs) -> np.ndarray:
    """Compute ACF from last-trade prices (paper's original methodology)."""
    if trades_df.empty:
        return np.full(MAX_LAG, np.nan)

    valid = trades_df["price"] > 0
    df = trades_df[valid].copy()
    if len(df) < 100:
        return np.full(MAX_LAG, np.nan)

    return compute_acf_from_prices(df["price"], df["timestamp"], **kwargs)


# ============================================================================
# Main test harness
# ============================================================================

def run_test(tickers: list, dates: list, output_path: str) -> dict:
    """Run the NBBO midquote ACF robustness test."""
    results = []

    for symbol in tickers:
        print(f"\n{'='*60}")
        print(f"  {symbol}")
        print(f"{'='*60}")

        symbol_acf_trade = []
        symbol_acf_mid = []

        for date in dates:
            print(f"\n  {date}:")

            # Fetch trades
            print(f"    Fetching trades...", end=" ", flush=True)
            trades = fetch_trades(symbol, date)
            n_trades = len(trades)
            print(f"{n_trades:,} records")

            # Fetch quotes
            print(f"    Fetching quotes...", end=" ", flush=True)
            quotes = fetch_quotes(symbol, date)
            n_quotes = len(quotes)
            print(f"{n_quotes:,} records")

            # Compute ACFs
            acf_trade = compute_trade_acf(trades)
            acf_mid = compute_midquote_acf(quotes)

            acf1_trade = float(acf_trade[0]) if not np.isnan(acf_trade[0]) else None
            acf1_mid = float(acf_mid[0]) if not np.isnan(acf_mid[0]) else None

            bounce = None
            if acf1_trade is not None and acf1_mid is not None:
                bounce = acf1_trade - acf1_mid

            if acf1_trade is not None:
                symbol_acf_trade.append(acf1_trade)
            if acf1_mid is not None:
                symbol_acf_mid.append(acf1_mid)

            result = {
                "symbol": symbol,
                "date": date,
                "n_trades": n_trades,
                "n_quotes": n_quotes,
                "acf1_trade_price": acf1_trade,
                "acf1_midquote": acf1_mid,
                "bounce_component": bounce,
            }
            results.append(result)

            # Print inline result
            t_str = f"{acf1_trade:+.4f}" if acf1_trade is not None else "N/A"
            m_str = f"{acf1_mid:+.4f}" if acf1_mid is not None else "N/A"
            b_str = f"{bounce:+.4f}" if bounce is not None else "N/A"
            print(f"    ACF₁ Trade: {t_str}  |  ACF₁ Midquote: {m_str}  |  Bounce: {b_str}")

        # Per-ticker summary
        if symbol_acf_trade and symbol_acf_mid:
            mean_trade = np.mean(symbol_acf_trade)
            mean_mid = np.mean(symbol_acf_mid)
            mean_bounce = mean_trade - mean_mid
            pct_retained = (mean_mid / mean_trade * 100) if abs(mean_trade) > 1e-6 else float("nan")

            print(f"\n  ── {symbol} Summary ──")
            print(f"    Mean Trade ACF₁:    {mean_trade:+.4f}")
            print(f"    Mean Midquote ACF₁: {mean_mid:+.4f}")
            print(f"    Mean Bounce:        {mean_bounce:+.4f}")
            print(f"    Signal Retained:    {pct_retained:.1f}%")

    # Save results
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump({
            "test": "NBBO Midquote ACF Robustness (Paper I §7.1–§7.2)",
            "methodology": {
                "interval_sec": INTERVAL_SEC,
                "max_lag": MAX_LAG,
                "rth_window": f"{RTH_START}–{RTH_END}",
                "trade_acf": "Last-trade price resampled to 1-min bars → pct_change → ACF",
                "midquote_acf": "NBBO midpoint (bid+ask)/2 resampled to 1-min bars → pct_change → ACF",
                "bounce_component": "Trade ACF₁ − Midquote ACF₁",
            },
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }, f, indent=2)
    print(f"\n✅ Results saved to {out}")

    # Print summary table
    print(f"\n{'='*78}")
    print(f"  NBBO MIDQUOTE ACF ROBUSTNESS TEST — SUMMARY")
    print(f"{'='*78}")
    print(f"  {'Ticker':<8} {'Mean Trade ACF₁':>16} {'Mean Mid ACF₁':>14} {'Bounce':>10} {'% Retained':>12}")
    print(f"  {'─'*62}")

    for symbol in tickers:
        sym_results = [r for r in results if r["symbol"] == symbol]
        trades_vals = [r["acf1_trade_price"] for r in sym_results if r["acf1_trade_price"] is not None]
        mid_vals = [r["acf1_midquote"] for r in sym_results if r["acf1_midquote"] is not None]
        if trades_vals and mid_vals:
            mt = np.mean(trades_vals)
            mm = np.mean(mid_vals)
            bounce = mt - mm
            pct = (mm / mt * 100) if abs(mt) > 1e-6 else float("nan")
            print(f"  {symbol:<8} {mt:>+16.4f} {mm:>+14.4f} {bounce:>+10.4f} {pct:>11.1f}%")
        else:
            print(f"  {symbol:<8} {'insufficient data':>50}")
    print(f"  {'─'*62}")
    print(f"  Interpretation:")
    print(f"    % Retained ≈ 100% → bid-ask bounce is negligible")
    print(f"    % Retained ≈ 0%   → signal was entirely bid-ask bounce")
    print(f"    Paper I panel mean ACF₁ = −0.203; typical bounce ~ −0.01 to −0.03")
    print(f"{'='*78}\n")

    return {"results": results}


def main():
    parser = argparse.ArgumentParser(
        description="NBBO Midquote ACF Robustness Test (Paper I §7.1–§7.2)"
    )
    parser.add_argument(
        "--tickers", nargs="+", default=DEFAULT_TICKERS,
        help="Tickers to test (default: AAPL MSFT GME TSLA)"
    )
    parser.add_argument(
        "--dates", nargs="+", default=DEFAULT_DATES,
        help="Trading dates in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--output", type=str,
        default="data/nbbo_acf_results.json",
        help="Output JSON path"
    )
    args = parser.parse_args()

    if not API_KEY:
        print("❌ Error: POLYGON_API_KEY not set in environment.")
        print("   export POLYGON_API_KEY=<your key>")
        sys.exit(1)

    print(f"NBBO Midquote ACF Robustness Test")
    print(f"  Tickers: {', '.join(args.tickers)}")
    print(f"  Dates:   {len(args.dates)} trading days ({args.dates[0]} → {args.dates[-1]})")
    print(f"  Interval: {INTERVAL_SEC}s bars")
    print()

    run_test(args.tickers, args.dates, args.output)


if __name__ == "__main__":
    main()
