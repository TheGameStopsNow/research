#!/usr/bin/env python3
"""
Expanded Cross-Date Panel — NOAA-Verified Storm Events
========================================================
Uses corridor_storms.json (41 NOAA-verified storm events) to run
the cross-date Shkilko replication with 2.7× more statistical power.

Same design: same ticker, same hour, storm day vs matched clear day.
"""

import json
import os
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy import stats as scipy_stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=FutureWarning)

WEATHER_DIR = Path(__file__).parent
OUTPUT_DIR = WEATHER_DIR / "expanded_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = WEATHER_DIR / "panel_nbbo_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

POLYGON_KEY = os.environ.get("POLYGON_API_KEY", "")
POLYGON_BASE = "https://api.polygon.io"

TICKERS_50 = [
    "AAPL", "MSFT", "AMZN", "GOOG", "META", "TSLA", "NVDA",
    "AMD", "NFLX", "PYPL", "CRM", "INTC", "ORCL", "ADBE",
    "SPY", "QQQ", "IWM", "DIA", "XLF", "XLE",
    "GME", "AMC", "BB", "BBBY", "PLTR", "SOFI",
    "BAC", "JPM", "GS", "MS", "C", "WFC",
    "DIS", "NKE", "BA", "F", "GM", "T",
    "PFE", "MRNA", "JNJ", "UNH",
    "XOM", "CVX", "GOLD",
    "COIN", "SNAP", "UBER", "ABNB", "RIVN", "LCID", "DKNG",
]


def _fetch_polygon_hour(ticker, date, hour_et):
    url = f"{POLYGON_BASE}/v3/quotes/{ticker}"
    params = {
        "timestamp.gte": f"{date}T{hour_et:02d}:00:00-04:00",
        "timestamp.lt": f"{date}T{hour_et+1:02d}:00:00-04:00",
        "limit": 50000, "order": "asc", "sort": "timestamp",
        "apiKey": POLYGON_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            time.sleep(12)
            resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return []
        return resp.json().get("results", [])
    except Exception:
        return []


def get_hour_spread(ticker, date, hour):
    """Get median 1-minute spread for a ticker-date-hour."""
    cache_path = CACHE_DIR / f"{ticker}_{date}.parquet"

    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        if "hour_et" in df.columns and "spread_bps" in df.columns:
            h = df[df["hour_et"] == hour]
            if len(h) >= 100:
                min_meds = h.groupby("minute_et")["spread_bps"].median()
                if len(min_meds) >= 10:
                    return float(min_meds.median())
        return None

    if not POLYGON_KEY:
        return None

    quotes = _fetch_polygon_hour(ticker, date, hour)
    if not quotes:
        return None

    df = pd.DataFrame(quotes)
    if "bid_price" not in df.columns or "ask_price" not in df.columns:
        return None

    df["spread"] = df["ask_price"] - df["bid_price"]
    df["mid"] = (df["bid_price"] + df["ask_price"]) / 2
    df = df[(df["bid_price"] > 0) & (df["ask_price"] > 0) &
            (df["spread"] >= 0) & (df["spread"] < df["mid"] * 0.10)].copy()

    if len(df) < 100:
        return None

    df["spread_bps"] = (df["spread"] / df["mid"]) * 10000
    if "sip_timestamp" in df.columns:
        df["ts_utc"] = pd.to_datetime(df["sip_timestamp"], unit="ns", utc=True)
        df["ts_et"] = df["ts_utc"].dt.tz_convert("America/New_York")
        df["minute_et"] = df["ts_et"].dt.minute
    else:
        return None

    min_meds = df.groupby("minute_et")["spread_bps"].median()
    if len(min_meds) < 10:
        return None
    return float(min_meds.median())


def find_control_date(storm_date_str, storm_dates_set):
    """Find nearest trading day ±1-5 days that's not a storm date."""
    from datetime import date as dt_date
    parts = storm_date_str.split("-")
    sd = dt_date(int(parts[0]), int(parts[1]), int(parts[2]))

    for offset in [1, -1, 2, -2, 3, -3, 5, -5]:
        cd = sd + timedelta(days=offset)
        if cd.weekday() >= 5:  # Skip weekends
            continue
        cd_str = cd.strftime("%Y-%m-%d")
        if cd_str not in storm_dates_set:
            return cd_str
    return None


def process_pair(ticker, storm_date, control_date, hour):
    storm_spread = get_hour_spread(ticker, storm_date, hour)
    control_spread = get_hour_spread(ticker, control_date, hour)
    if storm_spread is None or control_spread is None:
        return None
    return {
        "ticker": ticker,
        "storm_date": storm_date,
        "control_date": control_date,
        "hour": hour,
        "storm_spread_bps": storm_spread,
        "control_spread_bps": control_spread,
        "shift_bps": storm_spread - control_spread,
    }


def fmt_pval(p):
    if p < 0.001: return f"{p:.2e}"
    elif p < 0.01: return f"{p:.4f}"
    else: return f"{p:.3f}"


def main():
    # Load NOAA storm events
    storms_path = WEATHER_DIR / "corridor_storms.json"
    with open(storms_path) as f:
        storm_data = json.load(f)
    events = storm_data["events"]

    # Filter to only MODERATE+ for a cleaner signal
    # Actually use all events but tag severity
    storm_dates_set = {e["date"] for e in events}

    # Assign control dates
    for e in events:
        e["control"] = find_control_date(e["date"], storm_dates_set)

    events = [e for e in events if e["control"] is not None]
    print(f"Storm events: {len(events)}")
    print(f"Tickers: {len(TICKERS_50)}")
    print(f"Total pairs: {len(events) * len(TICKERS_50)}")

    # Run panel
    results = []
    total = len(events) * len(TICKERS_50)
    done = 0

    for e in sorted(events, key=lambda x: x["date"]):
        date = e["date"]
        hour = e["storm_hour"]
        control = e["control"]
        sev = e["severity"]
        med_mm = e["median_mm"]

        print(f"\n{'='*60}", flush=True)
        print(f"STORM: {date} h={hour:02d} ({sev}, {med_mm}mm) | "
              f"CTRL: {control}", flush=True)

        date_results = []

        def _do(t):
            return process_pair(t, date, control, hour)

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_do, t): t for t in TICKERS_50}
            for fut in as_completed(futures):
                done += 1
                try:
                    r = fut.result()
                    if r:
                        r["severity"] = sev
                        r["precip_mm"] = med_mm
                        date_results.append(r)
                        results.append(r)
                except Exception:
                    pass
                sys.stdout.write(f"\r    [{done}/{total}] {len(date_results)} OK    ")
                sys.stdout.flush()

        if date_results:
            shifts = [r["shift_bps"] for r in date_results]
            w = sum(1 for s in shifts if s > 0)
            print(f"\r    {date}: {len(date_results)}/{len(TICKERS_50)} | "
                  f"Widened: {w}/{len(date_results)} | Med: {np.median(shifts):+.2f}", flush=True)

    if not results:
        print("\nNo results!")
        sys.exit(1)

    # Stats
    shifts = np.array([r["shift_bps"] for r in results])
    t_stat, t_p = scipy_stats.ttest_1samp(shifts, 0)
    t_p_one = t_p / 2 if t_stat > 0 else 1 - t_p / 2
    try:
        w_stat, w_p = scipy_stats.wilcoxon(shifts, alternative="greater")
    except:
        w_p = 1.0
    widened = (shifts > 0).sum()
    n_pos = (shifts > 0).sum()
    n_nonzero = (shifts != 0).sum()
    sign_p = scipy_stats.binomtest(n_pos, n_nonzero, 0.5, alternative="greater").pvalue

    stats = {
        "n": len(shifts), "n_tickers": len(set(r["ticker"] for r in results)),
        "n_storms": len(set(r["storm_date"] for r in results)),
        "mean": float(shifts.mean()), "median": float(np.median(shifts)),
        "widened": int(widened),
        "ttest_t": float(t_stat), "ttest_p": float(t_p),
        "wilcoxon_p": float(w_p), "sign_p": float(sign_p),
    }

    # By severity
    for sev in ["MODERATE", "LIGHT"]:
        sub = np.array([r["shift_bps"] for r in results if r["severity"] == sev])
        if len(sub) >= 10:
            t_s, t_ps = scipy_stats.ttest_1samp(sub, 0)
            stats[f"sev_{sev.lower()}_n"] = len(sub)
            stats[f"sev_{sev.lower()}_mean"] = float(sub.mean())
            stats[f"sev_{sev.lower()}_widened"] = int((sub > 0).sum())
            stats[f"sev_{sev.lower()}_p"] = float(t_ps)

    # Continuous regression: shift ~ precip_mm
    precips = np.array([r["precip_mm"] for r in results])
    slope, intercept, r_val, reg_p, _ = scipy_stats.linregress(precips, shifts)
    rho, rho_p = scipy_stats.spearmanr(precips, shifts)
    stats["reg_slope"] = float(slope)
    stats["reg_r_sq"] = float(r_val**2)
    stats["reg_p"] = float(reg_p)
    stats["spearman_rho"] = float(rho)
    stats["spearman_p"] = float(rho_p)

    # Save
    save_results = [{k: v for k, v in r.items()} for r in results]
    with open(OUTPUT_DIR / "expanded_raw.json", "w") as f:
        json.dump({"results": save_results, "stats": stats}, f, indent=2, default=str)

    # Plot
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    ax = axes[0]
    ax.hist(shifts, bins=60, alpha=0.7, color="#5C6BC0", edgecolor="white", linewidth=0.3)
    ax.axvline(0, color="gray", linestyle="--")
    ax.axvline(np.median(shifts), color="#F44336", linewidth=2,
               label=f"Median: {np.median(shifts):+.3f}")
    ax.set_xlabel("Spread Shift (bps)")
    ax.set_title(f"Expanded Panel (N={len(shifts)})", fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.text(0.02, 0.98,
            f"t-test: p = {fmt_pval(t_p)}\n"
            f"Wilcoxon: p = {fmt_pval(w_p)}\n"
            f"Sign: p = {fmt_pval(sign_p)}\n"
            f"Widened: {widened}/{len(shifts)} ({widened/len(shifts)*100:.0f}%)",
            transform=ax.transAxes, fontsize=9, va="top",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9),
            fontfamily="monospace")

    ax = axes[1]
    sev_order = ["LIGHT", "MODERATE"]
    sev_colors = {"LIGHT": "#FFC107", "MODERATE": "#F44336"}
    for i, sev in enumerate(sev_order):
        sub = [r["shift_bps"] for r in results if r["severity"] == sev]
        if sub:
            bp = ax.boxplot([sub], positions=[i], widths=0.4, patch_artist=True, showfliers=False)
            bp["boxes"][0].set_facecolor(sev_colors.get(sev, "#ccc"))
            bp["boxes"][0].set_alpha(0.6)
    ax.set_xticks(range(len(sev_order)))
    ax.set_xticklabels([f"{s}\n(n={stats.get(f'sev_{s.lower()}_n', '?')})" for s in sev_order])
    ax.axhline(0, color="gray", linestyle="--")
    ax.set_ylabel("Spread Shift (bps)")
    ax.set_title("By Severity", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    ax = axes[2]
    ax.scatter(precips, shifts, alpha=0.15, s=10, c="#5C6BC0")
    x_line = np.linspace(0, max(precips), 100)
    ax.plot(x_line, intercept + slope * x_line, "r--", linewidth=2,
            label=f"β={slope:.3f}, p={fmt_pval(reg_p)}, R²={r_val**2:.4f}")
    ax.axhline(0, color="gray", linestyle="--")
    ax.set_xlabel("Corridor Precipitation (mm)")
    ax.set_ylabel("Spread Shift (bps)")
    ax.set_title("Continuous Dose-Response", fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "expanded_panel.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\nSaved: expanded_panel.png")

    # Report
    print(f"\n{'='*60}")
    print(f"EXPANDED CROSS-DATE PANEL RESULTS")
    print(f"{'='*60}")
    print(f"Observations: {stats['n']}")
    print(f"Tickers: {stats['n_tickers']}")
    print(f"Storm dates: {stats['n_storms']}")
    print(f"Mean shift: {stats['mean']:+.3f} bps")
    print(f"Median shift: {stats['median']:+.3f} bps")
    print(f"Widened: {stats['widened']}/{stats['n']} ({stats['widened']/stats['n']*100:.0f}%)")
    print(f"Paired t-test: t={stats['ttest_t']:.3f}, p={fmt_pval(stats['ttest_p'])}")
    print(f"Wilcoxon: p={fmt_pval(stats['wilcoxon_p'])}")
    print(f"Sign test: p={fmt_pval(stats['sign_p'])}")
    print(f"Precip regression: β={stats['reg_slope']:.4f}, p={fmt_pval(stats['reg_p'])}")
    print(f"Spearman ρ: {stats['spearman_rho']:.4f}, p={fmt_pval(stats['spearman_p'])}")
    for sev in ["moderate", "light"]:
        if f"sev_{sev}_n" in stats:
            sig = "★" if stats[f"sev_{sev}_p"] < 0.05 else ""
            print(f"  {sev.upper()}: N={stats[f'sev_{sev}_n']}, "
                  f"mean={stats[f'sev_{sev}_mean']:+.3f}, "
                  f"widened={stats[f'sev_{sev}_widened']}, "
                  f"p={fmt_pval(stats[f'sev_{sev}_p'])} {sig}")
    print(f"\n✅ DONE")


if __name__ == "__main__":
    main()
