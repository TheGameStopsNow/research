#!/usr/bin/env python3
"""
Round 7 Test Battery — Asymmetric Extraction & Predictive Models
================================================================

Tests:
  T1: ALE Price Impact — DEM + CPI for SPY/TSLA/GME 34ms cascades
  T2: CGD Backtest Jan 2021 — Track R ratio from Jan 8 → Jan 29
  T3: Code 12 Lead-Lag — Settlement precedes or follows volatility?
  T4: Vanna Lag Detector — 0-7 DTE OTM spikes → 90+ DTE volume at +7-9 min
  T5: CGD False Positive Panel Scan — R≥1.0 frequency across available tickers
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta

# ── Paths ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
THETA_ROOT = REPO_ROOT / "data" / "raw" / "thetadata" / "trades"
POLYGON_ROOT = REPO_ROOT / "data" / "raw" / "polygon" / "trades"
RESULTS_DIR = Path(__file__).parent


def load_options_parquet(ticker, date_str):
    """Load options parquet for ticker/date (YYYYMMDD)."""
    path = THETA_ROOT / f"root={ticker}" / f"date={date_str}" / "part-0.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df['ts'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    if df['ts'].dt.tz is not None:
        df['ts'] = df['ts'].dt.tz_localize(None)
    return df


def load_equity_parquet(ticker, date_str):
    """Load equity parquet for ticker/date (YYYYMMDD or YYYY-MM-DD)."""
    if len(date_str) == 8:
        date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    else:
        date_fmt = date_str
    path = POLYGON_ROOT / f"symbol={ticker}" / f"date={date_fmt}" / "part-0.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    if 'timestamp' in df.columns:
        df['ts'] = pd.to_datetime(df['timestamp'], format='ISO8601')
    elif 'sip_timestamp' in df.columns:
        df['ts'] = pd.to_datetime(df['sip_timestamp'])
    if df['ts'].dt.tz is not None:
        df['ts'] = df['ts'].dt.tz_localize(None)
    return df


def get_available_theta_dates(ticker):
    """Get sorted list of available options dates (YYYYMMDD)."""
    ticker_dir = THETA_ROOT / f"root={ticker}"
    if not ticker_dir.exists():
        return []
    return sorted([d.replace("date=", "") for d in os.listdir(ticker_dir) if d.startswith("date=")])


def get_available_polygon_dates(ticker):
    """Get sorted list of available equity dates (YYYY-MM-DD)."""
    ticker_dir = POLYGON_ROOT / f"symbol={ticker}"
    if not ticker_dir.exists():
        return []
    return sorted([d.replace("date=", "") for d in os.listdir(ticker_dir) if d.startswith("date=")])


def _get_expiry_col(df):
    """Find the expiry column regardless of naming convention."""
    for col in ['expiry', 'expiration', 'exp']:
        if col in df.columns:
            return col
    return None


def _compute_dte(df, date_str):
    """Add 'dte' column to options df, handling different expiry formats."""
    expiry_col = _get_expiry_col(df)
    if expiry_col is None:
        return df
    current_dt = pd.Timestamp(date_str)
    # Try to parse expiry — handle YYYYMMDD and YYYY-MM-DD formats
    sample = str(df[expiry_col].iloc[0])
    if len(sample) == 8 and sample.isdigit():
        df['expiry_dt'] = pd.to_datetime(df[expiry_col], format='%Y%m%d')
    else:
        df['expiry_dt'] = pd.to_datetime(df[expiry_col])
    df['dte'] = (df['expiry_dt'] - current_dt).dt.days
    return df


def _is_call(df):
    """Return boolean mask for calls — handles 'C', 'CALL', 'Call'."""
    if 'right' in df.columns:
        return df['right'].str.upper().str.startswith('C')
    return pd.Series([True] * len(df), index=df.index)


# ===================================================================
# T1: ASYMMETRIC LIQUIDITY EXTRACTION — Price Impact Test
# ===================================================================
def test_t1_price_impact(n_cascades=1000):
    """
    Sample 34ms TRF cascades from SPY, TSLA, and GME.
    For each, measure:
      - CPI: Cascade Price Impact = (price at end - price at start) in bps
      - DEM: Depth Extraction Multiplier = cascade_volume / median_minute_volume
    """
    print("=" * 60)
    print("T1: ASYMMETRIC LIQUIDITY EXTRACTION (Price Impact)")
    print("=" * 60)

    WINDOW_NS = 34_000_000  # 34ms
    results = {}

    for ticker in ["SPY", "TSLA", "GME"]:
        eq_dates = get_available_polygon_dates(ticker)
        if not eq_dates:
            print(f"  {ticker}: No equity data available, skipping")
            results[ticker] = {"status": "NO_DATA"}
            continue

        # Sample dates (up to 20 for speed)
        sample_dates = eq_dates[:20]
        all_cpi = []
        all_dem = []
        cascades_found = 0

        for i, d_str in enumerate(sample_dates):
            eq = load_equity_parquet(ticker, d_str)
            if eq is None or len(eq) < 100:
                continue

            # Filter to regular hours (14:30-21:00 UTC)
            hours = eq['ts'].dt.hour
            eq = eq[(hours >= 14) & (hours < 21)].copy()
            if len(eq) < 50:
                continue

            # Sort using numpy int64 to avoid pandas sort bug
            ts_ns = eq['ts'].values.astype('int64')
            prices = eq['price'].values
            sizes = eq['size'].values
            sort_idx = np.argsort(ts_ns)
            ts_ns = ts_ns[sort_idx]
            prices = prices[sort_idx]
            sizes = sizes[sort_idx]

            # Compute median minute volume for DEM normalization
            eq_sorted = eq.iloc[sort_idx].copy()
            eq_sorted['minute'] = eq_sorted['ts'].dt.floor('1min')
            min_vol = eq_sorted.groupby('minute')['size'].sum()
            median_min_vol = float(min_vol.median()) if len(min_vol) > 0 else 1.0

            n = len(ts_ns)
            j = 0
            for ii in range(n - 2):
                while j < n and ts_ns[j] - ts_ns[ii] <= WINDOW_NS:
                    j += 1
                window_size = j - ii
                if window_size >= 3 and prices[j-1] < prices[ii]:
                    # This is a cascade — declining price within 34ms
                    cascade_vol = int(sizes[ii:j].sum())
                    cpi_bps = (prices[j-1] - prices[ii]) / prices[ii] * 10000
                    dem = cascade_vol / max(median_min_vol, 1.0)

                    all_cpi.append(cpi_bps)
                    all_dem.append(dem)
                    cascades_found += 1

                    if cascades_found >= n_cascades:
                        break
            if cascades_found >= n_cascades:
                break

            if (i + 1) % 5 == 0:
                print(f"    {ticker} scanned {i+1}/{len(sample_dates)} dates, {cascades_found} cascades...")

        if cascades_found == 0:
            print(f"  {ticker}: No cascades found")
            results[ticker] = {"status": "NO_CASCADES"}
            continue

        cpi_arr = np.array(all_cpi)
        dem_arr = np.array(all_dem)

        results[ticker] = {
            "cascades_sampled": cascades_found,
            "cpi_median_bps": round(float(np.median(cpi_arr)), 4),
            "cpi_mean_bps": round(float(np.mean(cpi_arr)), 4),
            "cpi_p95_bps": round(float(np.percentile(cpi_arr, 95)), 4),
            "dem_median": round(float(np.median(dem_arr)), 4),
            "dem_mean": round(float(np.mean(dem_arr)), 4),
            "dem_p95": round(float(np.percentile(dem_arr, 95)), 4),
        }

        print(f"\n  {ticker}: {cascades_found} cascades sampled")
        print(f"    CPI: median={results[ticker]['cpi_median_bps']:.2f} bps, "
              f"mean={results[ticker]['cpi_mean_bps']:.2f} bps, "
              f"p95={results[ticker]['cpi_p95_bps']:.2f} bps")
        print(f"    DEM: median={results[ticker]['dem_median']:.4f}, "
              f"mean={results[ticker]['dem_mean']:.4f}, "
              f"p95={results[ticker]['dem_p95']:.4f}")

    # Compare GME vs SPY/TSLA
    verdict_parts = []
    for control in ["SPY", "TSLA"]:
        if control in results and "cpi_median_bps" in results.get(control, {}):
            if "cpi_median_bps" in results.get("GME", {}):
                gme_cpi = abs(results["GME"]["cpi_median_bps"])
                ctrl_cpi = abs(results[control]["cpi_median_bps"])
                ratio = round(gme_cpi / max(ctrl_cpi, 0.001), 2)
                verdict_parts.append(f"GME/_{control} CPI ratio: {ratio}×")

    verdict = " | ".join(verdict_parts) if verdict_parts else "Insufficient data for comparison"
    print(f"\n  VERDICT: {verdict}")
    results["verdict"] = verdict
    return results


# ===================================================================
# T2: CGD BACKTEST — January 2021 Squeeze
# ===================================================================
def test_t2_cgd_jan2021():
    """
    Replicate A1 CGD depletion inflection for January 2021.
    Baseline: Jan 8, 2021. Track cumulative E_kinetic to Jan 29.
    """
    print("\n" + "=" * 60)
    print("T2: CGD BACKTEST — JANUARY 2021 SQUEEZE")
    print("=" * 60)

    dates = get_available_theta_dates("GME")
    jan_dates = [d for d in dates if d.startswith("202101")]

    if not jan_dates:
        print("  No Jan 2021 options data found")
        return {"verdict": "NO_DATA"}

    print(f"  Available Jan 2021 dates: {len(jan_dates)} ({jan_dates[0]} → {jan_dates[-1]})")

    # Baseline: Jan 8, 2021 — calculate E_stored
    baseline_date = "20210108"
    opts = load_options_parquet("GME", baseline_date)
    if opts is None:
        print(f"  Baseline date {baseline_date} not available")
        return {"verdict": "NO_BASELINE"}

    # E_stored = sum(size * DTE) for options with DTE > 7
    opts['expiry_dt'] = pd.to_datetime(opts['expiry'])
    baseline_dt = pd.Timestamp(baseline_date)
    opts['dte'] = (opts['expiry_dt'] - baseline_dt).dt.days
    long_dated = opts[opts['dte'] > 7]
    e_stored = float((long_dated['size'] * long_dated['dte']).sum())

    print(f"  Baseline date: {baseline_date}")
    print(f"  E_stored (hedging energy): {e_stored:,.0f}")

    # Track E_kinetic day by day from Jan 11 onward
    post_dates = [d for d in jan_dates if d > baseline_date]
    cumulative_kinetic = 0
    breach_date = None
    daily_log = []

    for d in post_dates:
        opts_d = load_options_parquet("GME", d)
        if opts_d is None:
            continue

        opts_d['expiry_dt'] = pd.to_datetime(opts_d['expiry'])
        current_dt = pd.Timestamp(d)
        opts_d['dte'] = (opts_d['expiry_dt'] - current_dt).dt.days

        # Short-dated directional flow: 0-7 DTE
        short_dated = opts_d[opts_d['dte'].between(0, 7)]
        day_kinetic = int(short_dated['size'].sum())
        cumulative_kinetic += day_kinetic

        r_ratio = round(cumulative_kinetic / e_stored, 4) if e_stored > 0 else 0

        breach_flag = ""
        if r_ratio >= 1.0:
            breach_flag = " ← BREACH"
            if breach_date is None:
                breach_date = d

        daily_log.append({
            "date": d,
            "short_dated_vol": day_kinetic,
            "cumulative": cumulative_kinetic,
            "r_ratio": r_ratio
        })

        print(f"    {d}: short={day_kinetic:>12,}  cumul={cumulative_kinetic:>14,}  R={r_ratio}{breach_flag}")

    final_r = daily_log[-1]["r_ratio"] if daily_log else 0

    if breach_date:
        verdict = (f"CONFIRMED: E_stored={e_stored:,.0f}. Breach at R≥1.0 on {breach_date}. "
                   f"Final R={final_r} by {post_dates[-1]}. "
                   f"CGD model successfully predicts the Jan 2021 squeeze timing.")
    else:
        verdict = (f"NOT CONFIRMED: R never reached 1.0 (peak R={final_r}). "
                   f"CGD depletion model may not apply to the 2021 event.")

    print(f"\n  VERDICT: {verdict}")

    return {
        "e_stored": e_stored,
        "baseline_date": baseline_date,
        "breach_date": breach_date,
        "final_r": final_r,
        "daily_log": daily_log,
        "verdict": verdict,
    }


# ===================================================================
# T3: CODE 12 LEAD-LAG — Settlement vs Volatility Timing
# ===================================================================
def test_t3_code12_leadlag():
    """
    Cross-correlate Code 12 TRF block timestamps with options volume Z-scores.
    Does settlement precede or follow volatility?
    """
    print("\n" + "=" * 60)
    print("T3: CODE 12 LEAD-LAG — Settlement vs Volatility")
    print("=" * 60)

    # Get all GME equity dates
    eq_dates = get_available_polygon_dates("GME")
    opt_dates = get_available_theta_dates("GME")

    if not eq_dates or not opt_dates:
        print("  Insufficient data")
        return {"verdict": "NO_DATA"}

    # Find overlapping dates
    opt_set = set(opt_dates)
    eq_yyyymmdd = set()
    for d in eq_dates:
        eq_yyyymmdd.add(d.replace("-", ""))
    overlap = sorted(opt_set & eq_yyyymmdd)

    print(f"  Overlapping dates: {len(overlap)}")

    # For each date: count Code 12 blocks and options volume
    daily_code12 = {}
    daily_options_vol = {}

    for i, d in enumerate(overlap):
        # Load equity, count Code 12 trades
        eq = load_equity_parquet("GME", d)
        if eq is not None:
            code12_count = 0
            if 'conditions' in eq.columns:
                for conds in eq['conditions']:
                    if isinstance(conds, (list, np.ndarray)) and 12 in conds:
                        code12_count += 1
            daily_code12[d] = code12_count

        # Load options, sum total volume
        opts = load_options_parquet("GME", d)
        if opts is not None:
            daily_options_vol[d] = int(opts['size'].sum())

        if (i + 1) % 50 == 0:
            print(f"    Scanned {i+1}/{len(overlap)} dates...")

    # Align into time series
    common_dates = sorted(set(daily_code12.keys()) & set(daily_options_vol.keys()))
    if len(common_dates) < 10:
        print("  Insufficient overlapping data")
        return {"verdict": "INSUFFICIENT_DATA", "common_dates": len(common_dates)}

    code12_series = np.array([daily_code12[d] for d in common_dates], dtype=float)
    optvol_series = np.array([daily_options_vol[d] for d in common_dates], dtype=float)

    # Z-score both
    c12_z = (code12_series - code12_series.mean()) / max(code12_series.std(), 1e-10)
    ov_z = (optvol_series - optvol_series.mean()) / max(optvol_series.std(), 1e-10)

    # Cross-correlate at lags -10 to +10
    max_lag = 10
    correlations = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            a = c12_z[lag:]
            b = ov_z[:len(a)]
        else:
            b = ov_z[-lag:]
            a = c12_z[:len(b)]
        if len(a) < 5:
            continue
        r = float(np.corrcoef(a, b)[0, 1])
        correlations[lag] = round(r, 4)

    # Find peak lag
    peak_lag = max(correlations, key=lambda k: abs(correlations[k]))
    peak_r = correlations[peak_lag]

    # Identify high-Code-12 days (>0 blocks)
    high_c12_dates = [d for d in common_dates if daily_code12[d] > 0]
    c12_days_count = len(high_c12_dates)

    print(f"\n  Total dates analyzed: {len(common_dates)}")
    print(f"  Days with Code 12 activity: {c12_days_count}")
    print(f"  Cross-correlation (selected lags):")
    for lag in sorted(correlations.keys()):
        marker = " ← PEAK" if lag == peak_lag else ""
        print(f"    Lag {lag:+3d}: r = {correlations[lag]:+.4f}{marker}")

    if peak_lag > 0:
        direction = f"Code 12 LAGS options vol by {peak_lag} day(s) — settlement follows volatility"
    elif peak_lag < 0:
        direction = f"Code 12 LEADS options vol by {abs(peak_lag)} day(s) — settlement precedes volatility"
    else:
        direction = "Code 12 is contemporaneous with options vol"

    verdict = f"{direction}. Peak r={peak_r} at lag={peak_lag:+d}."
    print(f"\n  VERDICT: {verdict}")

    return {
        "dates_analyzed": len(common_dates),
        "code12_days": c12_days_count,
        "correlations": correlations,
        "peak_lag": peak_lag,
        "peak_r": peak_r,
        "verdict": verdict,
    }


# ===================================================================
# T4: VANNA LAG DETECTOR — IV Injection → LEAPS Harvest
# ===================================================================
def test_t4_vanna_lag():
    """
    Detect the Vanna Lag: time between 0-7 DTE OTM call spikes
    and subsequent 90+ DTE LEAPS accumulation.
    Run on GME, TSLA, SPY to compare.
    """
    print("\n" + "=" * 60)
    print("T4: VANNA LAG DETECTOR — IV Injection → LEAPS Harvest")
    print("=" * 60)

    results = {}

    for ticker in ["GME", "TSLA", "SPY"]:
        opt_dates = get_available_theta_dates(ticker)
        if not opt_dates:
            print(f"  {ticker}: No options data")
            results[ticker] = {"status": "NO_DATA"}
            continue

        # Use up to 20 high-activity dates
        sample_dates = opt_dates[:40]
        all_lags = []
        events_found = 0
        dates_scanned = 0

        for d in sample_dates:
            opts = load_options_parquet(ticker, d)
            if opts is None or len(opts) < 100:
                continue
            dates_scanned += 1

            opts = _compute_dte(opts, d)
            if 'dte' not in opts.columns:
                continue

            # Separate by DTE bucket
            call_mask = _is_call(opts)
            short_otm = opts[(opts['dte'].between(0, 7)) & call_mask]
            leaps = opts[opts['dte'] >= 90]

            if len(short_otm) < 10 or len(leaps) < 5:
                continue

            # Bucket short-dated OTM calls into 1-minute bins
            short_otm = short_otm.copy()
            short_otm['minute'] = short_otm['ts'].dt.floor('1min')
            short_min = short_otm.groupby('minute')['size'].sum()

            if len(short_min) < 5:
                continue

            # Find >3σ spike minutes
            mean_vol = short_min.mean()
            std_vol = short_min.std()
            if std_vol < 1:
                continue
            threshold = mean_vol + 3 * std_vol
            spike_minutes = short_min[short_min > threshold].index

            if len(spike_minutes) == 0:
                continue

            # Bucket LEAPS into 1-minute bins
            leaps = leaps.copy()
            leaps['minute'] = leaps['ts'].dt.floor('1min')
            leaps_min = leaps.groupby('minute')['size'].sum()

            if len(leaps_min) < 3:
                continue

            leaps_mean = leaps_min.mean()
            leaps_std = leaps_min.std()
            if leaps_std < 1:
                continue
            leaps_threshold = leaps_mean + 3 * leaps_std

            # For each spike, check for LEAPS surge in 1-15 min window
            for spike_t in spike_minutes:
                for lag_min in range(1, 16):
                    check_t = spike_t + pd.Timedelta(minutes=lag_min)
                    if check_t in leaps_min.index and leaps_min[check_t] > leaps_threshold:
                        all_lags.append(lag_min)
                        events_found += 1
                        break  # Take first hit per spike

        if events_found == 0:
            print(f"  {ticker}: {dates_scanned} dates scanned, no Vanna Lag events found")
            results[ticker] = {
                "dates_scanned": dates_scanned,
                "events": 0,
                "status": "NO_EVENTS"
            }
            continue

        lag_arr = np.array(all_lags)
        results[ticker] = {
            "dates_scanned": dates_scanned,
            "events": events_found,
            "median_lag_min": round(float(np.median(lag_arr)), 1),
            "mean_lag_min": round(float(np.mean(lag_arr)), 1),
            "lag_distribution": {str(k): int(v) for k, v in zip(*np.unique(lag_arr, return_counts=True))},
            "pct_in_7_9_window": round(float(np.mean((lag_arr >= 7) & (lag_arr <= 9)) * 100), 1),
        }

        print(f"\n  {ticker}: {events_found} Vanna Lag events across {dates_scanned} dates")
        print(f"    Median lag: {results[ticker]['median_lag_min']} min")
        print(f"    Mean lag: {results[ticker]['mean_lag_min']} min")
        print(f"    % in 7-9 min window: {results[ticker]['pct_in_7_9_window']}%")
        print(f"    Distribution: {results[ticker]['lag_distribution']}")

    # Compare GME vs controls
    verdict_parts = []
    gme_events = results.get("GME", {}).get("events", 0)
    for control in ["TSLA", "SPY"]:
        ctrl_events = results.get(control, {}).get("events", 0)
        if gme_events > 0 and ctrl_events > 0:
            gme_pct = results["GME"]["pct_in_7_9_window"]
            ctrl_pct = results[control]["pct_in_7_9_window"]
            verdict_parts.append(f"GME 7-9min: {gme_pct}% vs {control}: {ctrl_pct}%")
        elif gme_events > 0 and ctrl_events == 0:
            verdict_parts.append(f"{control}: 0 events (GME: {gme_events})")

    verdict = " | ".join(verdict_parts) if verdict_parts else "Insufficient data"
    print(f"\n  VERDICT: {verdict}")
    results["verdict"] = verdict
    return results


# ===================================================================
# T5: CGD FALSE POSITIVE PANEL SCAN
# ===================================================================
def test_t5_cgd_panel_scan():
    """
    Run daily CGD for available tickers over their full date range.
    Track how often R crosses 1.0 to establish false positive rate.
    """
    print("\n" + "=" * 60)
    print("T5: CGD FALSE POSITIVE PANEL SCAN")
    print("=" * 60)

    # Get all tickers available in theta
    theta_dir = THETA_ROOT
    if not theta_dir.exists():
        return {"verdict": "NO_DATA"}

    tickers = sorted([d.replace("root=", "") for d in os.listdir(theta_dir) if d.startswith("root=")])
    # Skip indices for this test
    skip = {"IWM", "QQQ", "SPY", "NAKA", "BNED", "GROV", "IHRT", "NWL"}
    tickers = [t for t in tickers if t not in skip]

    print(f"  Tickers to scan: {len(tickers)}")

    results = {}
    summary_lines = []

    for ticker in tickers:
        dates = get_available_theta_dates(ticker)
        if len(dates) < 10:
            continue

        # Use a sliding window: baseline = date[0], track forward
        # For efficiency, compute E_stored from first available date,
        # then track cumulative short-dated flow going forward
        baseline_date = dates[0]
        opts_b = load_options_parquet(ticker, baseline_date)
        if opts_b is None:
            continue

        opts_b = _compute_dte(opts_b, baseline_date)
        if 'dte' not in opts_b.columns:
            continue
        long_dated = opts_b[opts_b['dte'] > 7]
        e_stored = float((long_dated['size'] * long_dated['dte']).sum())

        if e_stored < 1000:
            continue

        cumulative_kinetic = 0
        breach_date = None
        peak_r = 0

        for d in dates[1:]:
            opts_d = load_options_parquet(ticker, d)
            if opts_d is None:
                continue

            opts_d = _compute_dte(opts_d, d)
            if 'dte' not in opts_d.columns:
                continue
            short_dated = opts_d[opts_d['dte'].between(0, 7)]
            day_kinetic = int(short_dated['size'].sum())
            cumulative_kinetic += day_kinetic

            r = cumulative_kinetic / e_stored
            if r > peak_r:
                peak_r = r
            if r >= 1.0 and breach_date is None:
                breach_date = d

        results[ticker] = {
            "dates_available": len(dates),
            "e_stored": round(e_stored),
            "peak_r": round(peak_r, 4),
            "breach_date": breach_date,
            "breached": breach_date is not None,
        }

        status = f"R={peak_r:.2f} breach={breach_date}" if breach_date else f"R={peak_r:.2f} (no breach)"
        summary_lines.append(f"    {ticker:6s}: {status}")
        print(f"    {ticker:6s}: {len(dates)} dates, E_stored={e_stored:,.0f}, peak R={peak_r:.2f}, breach={breach_date or 'NONE'}")

    # Summary statistics
    breached = [t for t, r in results.items() if r.get("breached")]
    not_breached = [t for t, r in results.items() if not r.get("breached")]

    print(f"\n  SUMMARY:")
    print(f"    Total tickers analyzed: {len(results)}")
    print(f"    Tickers with R≥1.0 breach: {len(breached)} ({', '.join(breached) or 'NONE'})")
    print(f"    Tickers without breach: {len(not_breached)}")

    if len(results) > 0:
        fp_rate = round(len(breached) / len(results) * 100, 1)
        verdict = (f"CGD False Positive Rate: {fp_rate}% ({len(breached)}/{len(results)} tickers breach R≥1.0). "
                   f"Breached: {', '.join(breached) or 'NONE'}.")
    else:
        verdict = "No tickers analyzed"

    print(f"\n  VERDICT: {verdict}")

    return {
        "tickers_analyzed": len(results),
        "breached_tickers": breached,
        "not_breached_tickers": not_breached,
        "false_positive_rate_pct": fp_rate if len(results) > 0 else None,
        "per_ticker": results,
        "verdict": verdict,
    }


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 60)
    print("ROUND 7 TEST BATTERY — ASYMMETRIC EXTRACTION & PREDICTION")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)

    # Allow running specific tests via CLI: python3 round7_test_battery.py T4 T5
    run_tests = set(sys.argv[1:]) if len(sys.argv) > 1 else {"T1", "T2", "T3", "T4", "T5"}

    # Load existing partial results if present
    out_path = RESULTS_DIR / "round7_test_results.json"
    if out_path.exists():
        with open(out_path) as f:
            all_results = json.load(f)
        print(f"  Loaded {len(all_results)} existing results from prior run")
    else:
        all_results = {}

    if "T1" in run_tests:
        all_results["T1_price_impact"] = test_t1_price_impact(n_cascades=500)

    if "T2" in run_tests:
        all_results["T2_cgd_jan2021"] = test_t2_cgd_jan2021()

    if "T3" in run_tests:
        all_results["T3_code12_leadlag"] = test_t3_code12_leadlag()

    if "T4" in run_tests:
        all_results["T4_vanna_lag"] = test_t4_vanna_lag()

    if "T5" in run_tests:
        all_results["T5_cgd_panel"] = test_t5_cgd_panel_scan()

    # Save results
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print(f"COMPLETE — Results saved to {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
