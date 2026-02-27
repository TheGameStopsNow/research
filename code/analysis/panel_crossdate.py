#!/usr/bin/env python3
"""
Cross-Date Shkilko Replication — Proper Design
================================================
Compares NBBO spreads for the SAME ticker at the SAME hour on
a STORM day vs a matched CLEAR day (±5 trading days).

This eliminates the time-of-day confound that invalidated the
within-day panel (where morning hours naturally have wider spreads).

Design: spread(storm_date, hour_h) − spread(control_date, hour_h)
Test:   Is the difference > 0 across the panel?

Usage:
  python3 panel_crossdate.py                    # Full run
  python3 panel_crossdate.py --skip-download    # Use cached data
  python3 panel_crossdate.py --tickers AAPL     # Subset
"""

import argparse
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

# ============================================================
# Config
# ============================================================
WEATHER_DIR = Path(__file__).parent
OUTPUT_DIR = WEATHER_DIR / "crossdate_results"
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

# Storm dates with matched control dates
# Control = closest trading day ±3-5 days with NO corridor precipitation
# Storm hour = the hour when precipitation hit the Pierce Broadband corridor
STORM_EVENTS = {
    "2021-05-19": {"storm_hour": 10, "severity": "LIGHT",    "control": "2021-05-18"},
    "2021-05-26": {"storm_hour": 13, "severity": "MODERATE",  "control": "2021-05-25"},
    "2021-06-16": {"storm_hour": 9,  "severity": "CLEAR",     "control": "2021-06-15"},
    "2021-06-21": {"storm_hour": 12, "severity": "MODERATE",  "control": "2021-06-18"},
    "2021-07-12": {"storm_hour": 14, "severity": "MODERATE",  "control": "2021-07-13"},
    "2021-07-22": {"storm_hour": 9,  "severity": "LIGHT",     "control": "2021-07-21"},
    "2021-07-29": {"storm_hour": 12, "severity": "MODERATE",  "control": "2021-07-28"},
    "2021-08-04": {"storm_hour": 13, "severity": "LIGHT",     "control": "2021-08-03"},
    "2021-08-11": {"storm_hour": 15, "severity": "MODERATE",  "control": "2021-08-10"},
    "2022-05-16": {"storm_hour": 11, "severity": "MODERATE",  "control": "2022-05-17"},
    "2022-06-15": {"storm_hour": 9,  "severity": "CLEAR",     "control": "2022-06-14"},
    "2022-06-22": {"storm_hour": 12, "severity": "MODERATE",  "control": "2022-06-21"},
    "2022-07-18": {"storm_hour": 9,  "severity": "MODERATE",  "control": "2022-07-19"},
    "2022-08-22": {"storm_hour": 12, "severity": "MODERATE",  "control": "2022-08-23"},
    "2022-08-29": {"storm_hour": 9,  "severity": "LIGHT",     "control": "2022-08-30"},
}


def fmt_pval(p: float) -> str:
    if p < 1e-300:
        return "< 1e-300"
    elif p < 0.001:
        return f"{p:.2e}"
    elif p < 0.01:
        return f"{p:.4f}"
    else:
        return f"{p:.3f}"


# ============================================================
# Polygon Download (reuse from panel_spread_50)
# ============================================================

def _fetch_polygon_hour(ticker: str, date: str, hour_et: int) -> list[dict]:
    """Fetch NBBO quotes from Polygon for a single ET hour."""
    url = f"{POLYGON_BASE}/v3/quotes/{ticker}"
    params = {
        "timestamp.gte": f"{date}T{hour_et:02d}:00:00-04:00",
        "timestamp.lt": f"{date}T{hour_et+1:02d}:00:00-04:00",
        "limit": 50000,
        "order": "asc",
        "sort": "timestamp",
        "apiKey": POLYGON_KEY,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            time.sleep(12)
            resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("results", [])
    except Exception:
        return []


def download_nbbo_hour(ticker: str, date: str, hour: int) -> pd.DataFrame:
    """
    Download and cache NBBO quotes for a single ticker-date-hour.
    Returns DataFrame with spread_bps and minute_et columns.
    """
    cache_path = CACHE_DIR / f"{ticker}_{date}.parquet"

    # If full-date cache exists, filter to hour
    if cache_path.exists():
        df = pd.read_parquet(cache_path)
        if "hour_et" in df.columns and "spread_bps" in df.columns:
            return df[df["hour_et"] == hour]

    # Download just the target hour
    if not POLYGON_KEY:
        return pd.DataFrame()

    quotes = _fetch_polygon_hour(ticker, date, hour)
    if not quotes:
        return pd.DataFrame()

    df = pd.DataFrame(quotes)

    if "bid_price" not in df.columns or "ask_price" not in df.columns:
        return pd.DataFrame()

    df["spread"] = df["ask_price"] - df["bid_price"]
    df["mid"] = (df["bid_price"] + df["ask_price"]) / 2
    df = df[
        (df["bid_price"] > 0) & (df["ask_price"] > 0) &
        (df["spread"] >= 0) & (df["spread"] < df["mid"] * 0.10)
    ].copy()
    df["spread_bps"] = (df["spread"] / df["mid"]) * 10000

    if "sip_timestamp" in df.columns:
        df["ts_utc"] = pd.to_datetime(df["sip_timestamp"], unit="ns", utc=True)
        df["ts_et"] = df["ts_utc"].dt.tz_convert("America/New_York")
        df["hour_et"] = df["ts_et"].dt.hour
        df["minute_et"] = df["ts_et"].dt.minute

    keep = [c for c in ["spread_bps", "hour_et", "minute_et", "mid"] if c in df.columns]
    return df[keep]


def compute_hour_spread(df: pd.DataFrame) -> float | None:
    """Compute median of 1-minute median spreads for an hour slice."""
    if df.empty or "spread_bps" not in df.columns or "minute_et" not in df.columns:
        return None
    min_meds = df.groupby("minute_et")["spread_bps"].median()
    if len(min_meds) < 10:
        return None
    return float(min_meds.median())


# ============================================================
# Cross-Date Panel
# ============================================================

def process_pair(ticker: str, storm_date: str, control_date: str,
                 hour: int, skip_download: bool = False) -> dict | None:
    """
    Compare same ticker, same hour, storm day vs control day.
    Returns the shift (storm − control) in bps.
    """
    storm_df = download_nbbo_hour(ticker, storm_date, hour)
    control_df = download_nbbo_hour(ticker, control_date, hour)

    storm_spread = compute_hour_spread(storm_df)
    control_spread = compute_hour_spread(control_df)

    if storm_spread is None or control_spread is None:
        return None

    shift = storm_spread - control_spread

    return {
        "ticker": ticker,
        "storm_date": storm_date,
        "control_date": control_date,
        "hour": hour,
        "storm_spread_bps": storm_spread,
        "control_spread_bps": control_spread,
        "shift_bps": shift,
    }


def run_crossdate_panel(tickers: list[str], events: dict,
                        skip_download: bool = False) -> list[dict]:
    """Run the full cross-date panel with concurrent downloads."""
    results = []
    total = len(tickers) * len(events)
    done = 0

    for storm_date, event in sorted(events.items()):
        hour = event["storm_hour"]
        control = event["control"]
        sev = event["severity"]

        print(f"\n{'='*60}", flush=True)
        print(f"STORM: {storm_date} ({sev}) h={hour:02d}:00 | "
              f"CONTROL: {control}", flush=True)
        print(f"{'='*60}", flush=True)

        date_results = []

        def _do_ticker(t):
            return process_pair(t, storm_date, control, hour, skip_download)

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_do_ticker, t): t for t in tickers}
            for fut in as_completed(futures):
                done += 1
                try:
                    r = fut.result()
                    if r:
                        r["severity"] = sev
                        date_results.append(r)
                        results.append(r)
                except Exception:
                    pass
                sys.stdout.write(f"\r    [{done}/{total}] {len(date_results)} OK    ")
                sys.stdout.flush()

        if date_results:
            shifts = [r["shift_bps"] for r in date_results]
            widened = sum(1 for s in shifts if s > 0)
            print(f"\r    {storm_date}: {len(date_results)}/{len(tickers)} | "
                  f"Widened: {widened}/{len(date_results)} | "
                  f"Med shift: {np.median(shifts):+.2f} bps", flush=True)

    return results


# ============================================================
# Statistical Tests
# ============================================================

def run_stats(results: list[dict]) -> dict:
    """Run panel statistical tests."""
    shifts = np.array([r["shift_bps"] for r in results])
    stats_out = {
        "n": len(shifts),
        "n_tickers": len(set(r["ticker"] for r in results)),
        "n_storm_dates": len(set(r["storm_date"] for r in results)),
        "mean_shift": float(shifts.mean()),
        "median_shift": float(np.median(shifts)),
        "std_shift": float(shifts.std()),
        "widened": int((shifts > 0).sum()),
    }

    # Paired t-test (H₁: storm spread > control spread)
    t_stat, t_p_two = scipy_stats.ttest_1samp(shifts, 0)
    t_p_one = t_p_two / 2 if t_stat > 0 else 1 - t_p_two / 2
    stats_out["ttest_t"] = float(t_stat)
    stats_out["ttest_p_two"] = float(t_p_two)
    stats_out["ttest_p_one"] = float(t_p_one)

    # Wilcoxon signed-rank (one-sided: storm > control)
    try:
        w_stat, w_p = scipy_stats.wilcoxon(shifts, alternative="greater")
        stats_out["wilcoxon_p"] = float(w_p)
    except Exception:
        stats_out["wilcoxon_p"] = 1.0

    # Sign test
    n_pos = (shifts > 0).sum()
    n_nonzero = (shifts != 0).sum()
    sign_p = scipy_stats.binomtest(n_pos, n_nonzero, 0.5, alternative="greater").pvalue
    stats_out["sign_test_p"] = float(sign_p)

    # By severity
    for sev in ["MODERATE", "LIGHT", "CLEAR"]:
        sev_shifts = np.array([r["shift_bps"] for r in results if r.get("severity") == sev])
        if len(sev_shifts) >= 5:
            t_s, t_p = scipy_stats.ttest_1samp(sev_shifts, 0)
            w = (sev_shifts > 0).sum()
            stats_out[f"sev_{sev.lower()}_n"] = len(sev_shifts)
            stats_out[f"sev_{sev.lower()}_mean"] = float(sev_shifts.mean())
            stats_out[f"sev_{sev.lower()}_median"] = float(np.median(sev_shifts))
            stats_out[f"sev_{sev.lower()}_widened"] = int(w)
            stats_out[f"sev_{sev.lower()}_p"] = float(t_p)

    return stats_out


# ============================================================
# Visualization
# ============================================================

def plot_results(results: list[dict], stats: dict, save_dir: Path):
    """Generate summary plots."""
    df = pd.DataFrame(results)
    shifts = df["shift_bps"].values

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 1: Shift distribution
    ax = axes[0]
    ax.hist(shifts, bins=50, alpha=0.7, color="#5C6BC0", edgecolor="white", linewidth=0.3)
    ax.axvline(0, color="gray", linestyle="--", linewidth=1.5)
    ax.axvline(np.median(shifts), color="#F44336", linestyle="-", linewidth=2,
               label=f"Median: {np.median(shifts):+.2f} bps")
    ax.set_xlabel("Spread Shift: Storm Day − Control Day (bps)")
    ax.set_ylabel("Count")
    ax.set_title("Cross-Date NBBO Spread Shift", fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    widened = (shifts > 0).sum()
    ax.text(0.02, 0.98,
            f"N = {len(shifts)}\n"
            f"Widened: {widened}/{len(shifts)} ({widened/len(shifts)*100:.0f}%)\n"
            f"t-test: p = {fmt_pval(stats['ttest_p_two'])}\n"
            f"Wilcoxon: p = {fmt_pval(stats['wilcoxon_p'])}\n"
            f"Sign test: p = {fmt_pval(stats['sign_test_p'])}",
            transform=ax.transAxes, fontsize=9, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9),
            fontfamily="monospace")

    # 2: By severity
    ax = axes[1]
    sev_order = ["CLEAR", "LIGHT", "MODERATE"]
    sev_colors = {"CLEAR": "#4CAF50", "LIGHT": "#FFC107", "MODERATE": "#F44336"}
    sev_data = []
    sev_labels = []
    for sev in sev_order:
        s = df[df["severity"] == sev]["shift_bps"].values
        if len(s) > 0:
            sev_data.append(s)
            sev_labels.append(f"{sev}\n(n={len(s)})")
    if sev_data:
        bp = ax.boxplot(sev_data, tick_labels=sev_labels, patch_artist=True,
                        showfliers=False, widths=0.5)
        for i, sev in enumerate(sev_order[:len(sev_data)]):
            bp["boxes"][i].set_facecolor(sev_colors.get(sev, "#ccc"))
            bp["boxes"][i].set_alpha(0.6)
    ax.axhline(0, color="gray", linestyle="--", linewidth=1)
    ax.set_ylabel("Spread Shift (bps)")
    ax.set_title("By Storm Severity", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    # 3: Per-ticker ranking
    ax = axes[2]
    ticker_med = df.groupby("ticker")["shift_bps"].median().sort_values(ascending=True)
    top_n = min(25, len(ticker_med))
    ticker_med_top = ticker_med.tail(top_n)
    colors = ["#F44336" if v > 0 else "#2196F3" for v in ticker_med_top.values]
    ax.barh(range(top_n), ticker_med_top.values, color=colors, alpha=0.7)
    ax.set_yticks(range(top_n))
    ax.set_yticklabels(ticker_med_top.index, fontsize=8)
    ax.axvline(0, color="gray", linestyle="--")
    ax.set_xlabel("Median Shift (bps)")
    ax.set_title("Per-Ticker Ranking", fontweight="bold")
    ax.grid(True, alpha=0.3, axis="x")

    plt.tight_layout()
    plt.savefig(save_dir / "crossdate_panel.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: crossdate_panel.png", flush=True)

    # Heatmap
    if len(df["ticker"].unique()) > 3 and len(df["storm_date"].unique()) > 3:
        pivot = df.pivot_table(index="ticker", columns="storm_date",
                               values="shift_bps", aggfunc="first")
        fig, ax = plt.subplots(figsize=(16, max(8, len(pivot) * 0.3)))
        vals = pivot.values[~np.isnan(pivot.values)]
        vmax = np.percentile(np.abs(vals), 95) if len(vals) > 0 else 5
        im = ax.imshow(pivot.values, cmap="RdBu_r", aspect="auto",
                       vmin=-vmax, vmax=vmax)
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index, fontsize=8)
        ax.set_title("Cross-Date Spread Shift (bps)\n"
                     "Red = Wider on Storm Day | Blue = Tighter",
                     fontweight="bold")
        plt.colorbar(im, ax=ax, label="Shift (bps)")
        plt.tight_layout()
        plt.savefig(save_dir / "crossdate_heatmap.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  Saved: crossdate_heatmap.png", flush=True)


# ============================================================
# Report
# ============================================================

def generate_report(results: list[dict], stats: dict) -> str:
    """Generate markdown report."""
    lines = [
        "# Cross-Date Shkilko Replication",
        f"**Design:** Same ticker, same hour, storm day vs matched clear day (±1-3 trading days)",
        f"**Data:** Polygon v3 tick-level NBBO quotes",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "---",
        "",
        "## Panel Summary",
        "",
        f"- **Observations:** {stats['n']}",
        f"- **Tickers:** {stats['n_tickers']}",
        f"- **Storm dates:** {stats['n_storm_dates']}",
        "",
        "## Key Results",
        "",
        f"| Test | Value | p-value |",
        f"|------|-------|---------|",
        f"| Mean shift | {stats['mean_shift']:+.3f} bps | — |",
        f"| Median shift | {stats['median_shift']:+.3f} bps | — |",
        f"| Widened | {stats['widened']}/{stats['n']} ({stats['widened']/stats['n']*100:.0f}%) | — |",
        f"| Paired t-test | t = {stats['ttest_t']:.3f} | {fmt_pval(stats['ttest_p_two'])} |",
        f"| Wilcoxon (storm > ctrl) | — | {fmt_pval(stats['wilcoxon_p'])} |",
        f"| Sign test | — | {fmt_pval(stats['sign_test_p'])} |",
        "",
    ]

    # Severity
    sev_lines = []
    for sev in ["moderate", "light", "clear"]:
        if f"sev_{sev}_n" in stats:
            sig = "★" if stats[f"sev_{sev}_p"] < 0.05 else ""
            sev_lines.append(
                f"| {sev.upper()} | {stats[f'sev_{sev}_n']} | "
                f"{stats[f'sev_{sev}_mean']:+.3f} | "
                f"{stats[f'sev_{sev}_widened']}/{stats[f'sev_{sev}_n']} | "
                f"{fmt_pval(stats[f'sev_{sev}_p'])} {sig} |"
            )
    if sev_lines:
        lines.extend([
            "### By Storm Severity",
            "",
            "| Severity | N | Mean Shift | Widened | p |",
            "|----------|---|-----------|---------|---|",
        ] + sev_lines + [""])

    # Interpretation
    p = stats.get("ttest_p_two", 1)
    shift = stats.get("median_shift", 0)
    if p < 0.05 and shift > 0:
        lines.append(f"> ✅ **SIGNIFICANT WIDENING** on storm days (p = {fmt_pval(p)})")
    elif p < 0.05 and shift < 0:
        lines.append(f"> ⚠️ **SIGNIFICANT TIGHTENING** on storm days (p = {fmt_pval(p)})")
    else:
        lines.append(f"> ⚪ **NOT SIGNIFICANT** (p = {fmt_pval(p)})")

    report = "\n".join(lines)
    report_path = OUTPUT_DIR / "crossdate_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport: {report_path}", flush=True)
    return report


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Cross-Date Shkilko Replication")
    parser.add_argument("--tickers", nargs="+")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--max-tickers", type=int, default=50)
    args = parser.parse_args()

    print("=" * 60, flush=True)
    print("CROSS-DATE SHKILKO REPLICATION", flush=True)
    print("Same ticker, same hour, storm day vs control day", flush=True)
    print("=" * 60, flush=True)

    if not POLYGON_KEY and not args.skip_download:
        print("ERROR: POLYGON_API_KEY not set", flush=True)
        sys.exit(1)

    tickers = args.tickers if args.tickers else TICKERS_50[:args.max_tickers]

    print(f"Tickers: {len(tickers)}", flush=True)
    print(f"Storm events: {len(STORM_EVENTS)}", flush=True)
    print(f"Total pairs: {len(tickers) * len(STORM_EVENTS)}", flush=True)

    results = run_crossdate_panel(tickers, STORM_EVENTS, args.skip_download)

    if not results:
        print("\nNo results!", flush=True)
        sys.exit(1)

    panel_stats = run_stats(results)

    # Save
    save_results = [{k: v for k, v in r.items()} for r in results]
    with open(OUTPUT_DIR / "crossdate_raw.json", "w") as f:
        json.dump({"results": save_results, "stats": panel_stats}, f, indent=2, default=str)

    plot_results(results, panel_stats, OUTPUT_DIR)
    report = generate_report(results, panel_stats)
    print(report, flush=True)
    print(f"\n✅ CROSS-DATE PANEL COMPLETE: {len(results)} observations", flush=True)


if __name__ == "__main__":
    main()
