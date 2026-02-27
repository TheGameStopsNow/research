#!/usr/bin/env python3
"""
Full-Range Energy Pattern Analysis (2018–2026)
================================================
Process all 2,038 days of raw ThetaData GME options trades to compute
the DTE-weighted energy budget, detect accumulation/discharge cycles,
and identify buildup patterns before Jan 2021 and Jun 2024.

Data source: power-tracks-research/data/raw/thetadata/trades/root=GME/
Each date folder contains a part-0.parquet with columns:
    symbol, expiry, strike, right, timestamp, size, price, exchange, condition, ...

Usage:
    python3 full_range_energy_analysis.py
"""
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.ndimage import gaussian_filter, uniform_filter1d
from scipy.signal import find_peaks

# ============================================================================
# Configuration
# ============================================================================
THETA_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/trades/root=GME")
OUTPUT_DIR = Path(__file__).parent / "output_full_range"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# DTE buckets matching sweep_mechanics.py
BUCKET_ORDER = ["0DTE", "1-7d", "8-30d", "31-90d", "91-180d", "181-365d", "365d+"]
ENERGY_WEIGHTS = {
    "0DTE": 0.1, "1-7d": 4.0, "8-30d": 19.0, "31-90d": 60.0,
    "91-180d": 135.0, "181-365d": 270.0, "365d+": 500.0,
}
BUCKET_COLORS = [
    "#e6194b", "#f58231", "#3cb44b", "#4363d8",
    "#911eb4", "#42d4f4", "#f032e6",
]

# Key event dates for annotation
KEY_EVENTS = {
    "2021-01-28": "Jan 2021\nSneeze",
    "2024-05-13": "May 2024\nFTD Spike / DFV Return",
}


def dte_to_bucket(dte_days: int) -> str:
    """Map days-to-expiration to a bucket name."""
    if dte_days <= 0:
        return "0DTE"
    elif dte_days <= 7:
        return "1-7d"
    elif dte_days <= 30:
        return "8-30d"
    elif dte_days <= 90:
        return "31-90d"
    elif dte_days <= 180:
        return "91-180d"
    elif dte_days <= 365:
        return "181-365d"
    else:
        return "365d+"


# ============================================================================
# Data Loading — Process raw ThetaData trades
# ============================================================================
def load_all_theta_trades() -> pd.DataFrame:
    """Load all raw ThetaData GME trades and compute daily energy budget."""
    date_dirs = sorted(THETA_DIR.glob("date=*"))
    if not date_dirs:
        print(f"ERROR: No date dirs in {THETA_DIR}")
        sys.exit(1)

    print(f"Found {len(date_dirs)} date folders")

    daily_rows = []
    errors = 0
    for i, ddir in enumerate(date_dirs):
        date_str = ddir.name.replace("date=", "")

        try:
            dt = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            continue

        try:
            # Read BOTH part-0.parquet (short-dated, DTE 0-53) and
            # part-leaps.parquet (mid/long-dated, DTE 61-400) if it exists
            frames = []
            needed_cols = ["expiry", "size"]
            for part_name in ["part-0.parquet", "part-leaps.parquet"]:
                pq_path = ddir / part_name
                if not pq_path.exists():
                    continue
                try:
                    part_df = pd.read_parquet(pq_path, columns=needed_cols)
                except Exception:
                    try:
                        part_df = pd.read_parquet(pq_path, columns=["expiration", "size"])
                        part_df.rename(columns={"expiration": "expiry"}, inplace=True)
                    except Exception:
                        part_df = pd.read_parquet(pq_path)
                frames.append(part_df)

            if not frames:
                continue

            df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]

            if df.empty:
                daily_rows.append({"date": dt, **{f"{b}_count": 0 for b in BUCKET_ORDER},
                                   **{f"{b}_volume": 0 for b in BUCKET_ORDER}})
                continue

            # Compute DTE for each trade
            if "expiry" in df.columns:
                df["expiry_dt"] = pd.to_datetime(df["expiry"], errors="coerce")
            elif "expiration" in df.columns:
                df["expiry_dt"] = pd.to_datetime(df["expiration"], errors="coerce")
            else:
                errors += 1
                continue

            df["dte"] = (df["expiry_dt"] - pd.Timestamp(dt)).dt.days
            df["bucket"] = df["dte"].apply(dte_to_bucket)

            # Aggregate by bucket
            row = {"date": dt, "total_trades": len(df)}
            for b in BUCKET_ORDER:
                mask = df["bucket"] == b
                row[f"{b}_count"] = int(mask.sum())
                row[f"{b}_volume"] = int(df.loc[mask, "size"].sum()) if "size" in df.columns else int(mask.sum())
            daily_rows.append(row)

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error on {date_str}: {e}")

        if (i + 1) % 200 == 0 or i == 0 or i == len(date_dirs) - 1:
            print(f"  [{i+1}/{len(date_dirs)}] {date_str} — {len(daily_rows)} valid days, {errors} errors")

    result = pd.DataFrame(daily_rows).sort_values("date").reset_index(drop=True)
    print(f"\nLoaded {len(result)} trading days: {result['date'].min()} → {result['date'].max()}")
    if errors:
        print(f"  ({errors} dates skipped due to errors)")
    return result


# ============================================================================
# Energy Computation
# ============================================================================
def compute_energy(daily_df: pd.DataFrame) -> dict:
    """Compute energy matrices and derived metrics."""
    n = len(daily_df)
    t_axis = daily_df["date"].values

    # Build trade count matrix (n_dates × 7_buckets)
    trade_matrix = np.column_stack([
        daily_df[f"{b}_count"].values.astype(float) for b in BUCKET_ORDER
    ])

    # Energy = trades × weight
    weight_vec = np.array([ENERGY_WEIGHTS[b] for b in BUCKET_ORDER])
    energy_matrix = trade_matrix * weight_vec[np.newaxis, :]

    total_energy = energy_matrix.sum(axis=1)

    # Adaptive smoothing (larger window for more data)
    smooth_size = min(20, max(5, n // 100))
    smooth_energy = uniform_filter1d(total_energy, size=smooth_size)
    flow_rate = np.gradient(smooth_energy)
    flow_smooth = uniform_filter1d(flow_rate, size=max(3, smooth_size // 2))

    return {
        "t_axis": t_axis,
        "n_dates": n,
        "trade_matrix": trade_matrix,
        "energy_matrix": energy_matrix,
        "total_energy": total_energy,
        "smooth_energy": smooth_energy,
        "flow_rate": flow_rate,
        "flow_smooth": flow_smooth,
        "weight_vec": weight_vec,
        "smooth_size": smooth_size,
    }


# ============================================================================
# Burst Detection
# ============================================================================
def detect_bursts(edata: dict, min_prominence: float = 0.10) -> list[dict]:
    """Detect accumulate→discharge cycles."""
    smooth = edata["smooth_energy"]
    t_axis = edata["t_axis"]

    if smooth.max() == 0:
        return []
    normalized = smooth / smooth.max()

    peaks, _ = find_peaks(
        normalized,
        distance=30,         # at least 30 trading days apart (~6 weeks)
        prominence=min_prominence,
        width=3,
    )

    troughs, _ = find_peaks(
        -normalized,
        distance=15,
        prominence=min_prominence * 0.3,
    )

    bursts = []
    for i, peak_idx in enumerate(peaks):
        peak_date = pd.Timestamp(t_axis[peak_idx])
        peak_energy = float(smooth[peak_idx])

        # Find next trough
        subsequent_troughs = troughs[troughs > peak_idx]
        if len(subsequent_troughs) > 0:
            trough_idx = subsequent_troughs[0]
            trough_date = pd.Timestamp(t_axis[trough_idx])
            trough_energy = float(smooth[trough_idx])
            discharge_pct = (peak_energy - trough_energy) / peak_energy * 100
            duration_days = (trough_date - peak_date).days
        else:
            trough_date = trough_energy = discharge_pct = duration_days = None

        # Energy composition at peak
        em = edata["energy_matrix"]
        peak_row = em[peak_idx]
        total_at_peak = peak_row.sum()
        composition = {}
        for j, b in enumerate(BUCKET_ORDER):
            composition[b] = float(peak_row[j] / total_at_peak * 100) if total_at_peak > 0 else 0

        bursts.append({
            "burst_num": i + 1,
            "peak_date": peak_date,
            "peak_energy": peak_energy,
            "trough_date": trough_date,
            "trough_energy": trough_energy,
            "discharge_pct": discharge_pct,
            "duration_days": duration_days,
            "composition": composition,
            "peak_idx": peak_idx,
        })

    return bursts


# ============================================================================
# Pre-Event Analysis
# ============================================================================
def analyze_pre_event_buildup(daily_df: pd.DataFrame, edata: dict, event_date: str,
                                lookback_days: int = 180) -> dict:
    """Analyze energy buildup patterns in the N days before a specific event."""
    evt = pd.Timestamp(event_date)
    t_axis = pd.DatetimeIndex(edata["t_axis"])
    mask = (t_axis >= evt - pd.Timedelta(days=lookback_days)) & (t_axis <= evt)
    idxs = np.where(mask)[0]

    if len(idxs) == 0:
        return {"event": event_date, "status": "NO_DATA", "n_days": 0}

    em = edata["energy_matrix"][idxs]
    smooth_window = em.copy()

    # Compute per-bucket trends
    trends = {}
    for j, b in enumerate(BUCKET_ORDER):
        vals = em[:, j]
        if len(vals) > 5:
            # Linear regression slope
            x = np.arange(len(vals))
            slope = np.polyfit(x, vals, 1)[0]
            trends[b] = {
                "mean": float(vals.mean()),
                "max": float(vals.max()),
                "slope": float(slope),
                "slope_pct": float(slope / max(vals.mean(), 1) * 100),
                "final_vs_initial": float(vals[-5:].mean() / max(vals[:5].mean(), 1)),
            }
        else:
            trends[b] = {"mean": 0, "max": 0, "slope": 0, "slope_pct": 0, "final_vs_initial": 0}

    # Total energy trend
    total = em.sum(axis=1)
    total_slope = np.polyfit(np.arange(len(total)), total, 1)[0]

    # Long tenor concentration
    long_pct_start = em[:min(20, len(em)), 4:].sum() / max(em[:min(20, len(em))].sum(), 1) * 100
    long_pct_end = em[-min(20, len(em)):, 4:].sum() / max(em[-min(20, len(em)):].sum(), 1) * 100

    return {
        "event": event_date,
        "status": "OK",
        "n_days": len(idxs),
        "date_range": f"{pd.Timestamp(edata['t_axis'][idxs[0]]).strftime('%Y-%m-%d')} → {pd.Timestamp(edata['t_axis'][idxs[-1]]).strftime('%Y-%m-%d')}",
        "total_slope": float(total_slope),
        "total_mean": float(total.mean()),
        "total_peak": float(total.max()),
        "long_pct_start": float(long_pct_start),
        "long_pct_end": float(long_pct_end),
        "long_pct_shift": float(long_pct_end - long_pct_start),
        "trends": trends,
    }


# ============================================================================
# Visualization
# ============================================================================
def plot_full_energy_budget(edata: dict, bursts: list[dict], save_path: Path):
    """Full-range stacked area chart with event annotations."""
    fig, ax = plt.subplots(figsize=(24, 7))

    t_axis = edata["t_axis"]
    em = edata["energy_matrix"]
    n = edata["n_dates"]
    sm = edata["smooth_size"]

    bottom = np.zeros(n)
    for i, b in enumerate(BUCKET_ORDER):
        vals = uniform_filter1d(em[:, i], size=sm)
        ax.fill_between(t_axis, bottom, bottom + vals,
                        alpha=0.75, color=BUCKET_COLORS[i],
                        label=f"{b} (w={ENERGY_WEIGHTS[b]:.0f})")
        bottom += vals

    # Annotate key events
    t_pd = pd.DatetimeIndex(t_axis)
    for evt_date, evt_label in KEY_EVENTS.items():
        evt_ts = pd.Timestamp(evt_date)
        if t_pd.min() <= evt_ts <= t_pd.max():
            ax.axvline(evt_ts, color="red", linewidth=2, alpha=0.7, linestyle="--")
            ymax = bottom.max() * 0.85
            ax.annotate(evt_label, xy=(evt_ts, ymax),
                        fontsize=9, color="red", ha="center", fontweight="bold",
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.9, edgecolor="red"))

    ax.set_ylabel("Energy (trades × DTE weight)", fontsize=12)
    ax.set_title("GME Energy Budget by Tenor — Full Range (2018–2026)", fontsize=16, fontweight="bold")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.2)
    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_pre_event_comparison(pre_2021: dict, pre_2024: dict, save_path: Path):
    """Side-by-side comparison of pre-event energy buildup patterns."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    for ax, data, title in zip(axes,
                                [pre_2021, pre_2024],
                                ["180 Days Before Jan 28, 2021", "180 Days Before Jun 7, 2024"]):
        if data["status"] != "OK":
            ax.text(0.5, 0.5, f"No data for {data['event']}", ha="center", va="center", fontsize=14)
            ax.set_title(title)
            continue

        trends = data["trends"]
        buckets = list(trends.keys())
        slopes = [trends[b]["slope_pct"] for b in buckets]
        means = [trends[b]["mean"] for b in buckets]

        x = np.arange(len(buckets))
        bars = ax.bar(x, slopes, color=BUCKET_COLORS[:len(buckets)], edgecolor="black", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(buckets, rotation=45, ha="right")
        ax.set_ylabel("Slope (% of mean per day)")
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.grid(True, alpha=0.2, axis="y")

        # Annotate long-tenor shift
        ax.text(0.02, 0.95,
                f"Long tenor (91d+): {data['long_pct_start']:.0f}% → {data['long_pct_end']:.0f}%\n"
                f"Total energy slope: {data['total_slope']:+.0f}/day\n"
                f"Peak energy: {data['total_peak']:,.0f}",
                transform=ax.transAxes, fontsize=9, verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.9))

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_energy_heatmap(edata: dict, save_path: Path):
    """Full-range energy density heatmap (time × tenor)."""
    em = edata["energy_matrix"]
    smoothed = gaussian_filter(em.T.astype(float), sigma=(0.8, 10))

    fig, ax = plt.subplots(figsize=(24, 5))
    t_axis = edata["t_axis"]
    n = edata["n_dates"]

    im = ax.imshow(smoothed, aspect="auto", origin="lower",
                   cmap="inferno", interpolation="bilinear",
                   extent=[0, n, -0.5, len(BUCKET_ORDER) - 0.5])
    ax.set_yticks(range(len(BUCKET_ORDER)))
    ax.set_yticklabels(BUCKET_ORDER)

    n_ticks = min(20, n)
    tick_pos = np.linspace(0, n - 1, n_ticks, dtype=int)
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(
        [pd.Timestamp(t_axis[i]).strftime("%Y-%m") for i in tick_pos],
        rotation=45, fontsize=8,
    )

    # Annotate key events
    t_pd = pd.DatetimeIndex(t_axis)
    for evt_date, evt_label in KEY_EVENTS.items():
        evt_ts = pd.Timestamp(evt_date)
        if t_pd.min() <= evt_ts <= t_pd.max():
            idx = np.searchsorted(t_pd, evt_ts)
            ax.axvline(idx, color="white", linewidth=1.5, alpha=0.8, linestyle="--")
            ax.annotate(evt_label.replace("\n", " "), xy=(idx, len(BUCKET_ORDER) - 0.3),
                        fontsize=7, color="white", ha="center")

    ax.set_ylabel("Tenor")
    ax.set_title("GME Energy Density Heatmap (trades × DTE weight) — 2018–2026", fontsize=14, fontweight="bold")
    plt.colorbar(im, ax=ax, label="Energy", shrink=0.8)
    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_storage_release(edata: dict, save_path: Path):
    """Storage vs Release dual panel."""
    fig, (ax_store, ax_flow) = plt.subplots(
        2, 1, figsize=(24, 9), sharex=True,
        gridspec_kw={"height_ratios": [2, 1]}
    )

    t_axis = edata["t_axis"]
    smooth = edata["smooth_energy"]
    flow = edata["flow_smooth"]
    t_pd = pd.DatetimeIndex(t_axis)

    ax_store.fill_between(t_axis, smooth, alpha=0.3, color="#2196f3")
    ax_store.plot(t_axis, smooth, color="#2196f3", linewidth=1, label="Stored Energy")

    for evt_date, evt_label in KEY_EVENTS.items():
        evt_ts = pd.Timestamp(evt_date)
        if t_pd.min() <= evt_ts <= t_pd.max():
            ax_store.axvline(evt_ts, color="red", linewidth=1.5, alpha=0.6, linestyle="--")
            ax_flow.axvline(evt_ts, color="red", linewidth=1.5, alpha=0.6, linestyle="--")

    ax_store.set_ylabel("Stored Energy\n(trades × DTE weight)")
    ax_store.set_title("GME Hedging Energy — Accumulation/Discharge (2018–2026)", fontsize=14)
    ax_store.grid(True, alpha=0.2)
    ax_store.legend(loc="upper left")

    pos_flow = np.where(flow > 0, flow, 0)
    neg_flow = np.where(flow < 0, flow, 0)
    ax_flow.fill_between(t_axis, pos_flow, alpha=0.4, color="#2196f3", label="Accumulating")
    ax_flow.fill_between(t_axis, neg_flow, alpha=0.4, color="#ff4444", label="Discharging")
    ax_flow.axhline(0, color="gray", linewidth=0.5)
    ax_flow.set_ylabel("Energy Flow Rate")
    ax_flow.set_xlabel("Date")
    ax_flow.grid(True, alpha=0.2)
    ax_flow.legend(loc="upper left")

    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_long_tenor_timeseries(edata: dict, save_path: Path):
    """Track long-dated tenor % over time to visualize LEAPS loading."""
    em = edata["energy_matrix"]
    t_axis = edata["t_axis"]
    total = em.sum(axis=1)

    # Compute rolling % for each long bucket
    fig, ax = plt.subplots(figsize=(24, 6))
    window = 30

    for j, b in enumerate(BUCKET_ORDER[4:], start=4):  # 91-180d, 181-365d, 365d+
        pct = np.zeros(len(em))
        for k in range(len(em)):
            pct[k] = em[k, j] / max(total[k], 1) * 100
        smooth_pct = uniform_filter1d(pct, size=window)
        ax.plot(t_axis, smooth_pct, color=BUCKET_COLORS[j], linewidth=2,
                label=f"{b}", alpha=0.85)

    # Combined 91d+
    long_pct = np.zeros(len(em))
    for k in range(len(em)):
        long_pct[k] = em[k, 4:].sum() / max(total[k], 1) * 100
    smooth_long = uniform_filter1d(long_pct, size=window)
    ax.plot(t_axis, smooth_long, color="black", linewidth=2.5, linestyle="--",
            label="Total 91d+ (combined)", alpha=0.9)

    t_pd = pd.DatetimeIndex(t_axis)
    for evt_date, evt_label in KEY_EVENTS.items():
        evt_ts = pd.Timestamp(evt_date)
        if t_pd.min() <= evt_ts <= t_pd.max():
            ax.axvline(evt_ts, color="red", linewidth=1.5, alpha=0.5, linestyle="--")
            ax.annotate(evt_label.replace("\n", " "), xy=(evt_ts, 80),
                        fontsize=8, color="red", ha="center",
                        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

    ax.set_ylabel("% of Total Energy", fontsize=12)
    ax.set_title("Long-Dated Tenor Energy Share Over Time (30-day rolling)", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.2)
    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


# ============================================================================
# Main
# ============================================================================
def main():
    print("=" * 70)
    print("GME Full-Range Energy Pattern Analysis (2018–2026)")
    print("=" * 70)
    print()

    # Step 1: Load
    print("Step 1: Loading raw ThetaData trades...")
    daily_df = load_all_theta_trades()

    # Save intermediate CSV for reuse
    csv_path = OUTPUT_DIR / "daily_energy_budget.csv"
    daily_df.to_csv(csv_path, index=False)
    print(f"  Saved daily budget to {csv_path}")
    print()

    # Step 2: Compute energy
    print("Step 2: Computing energy budget...")
    edata = compute_energy(daily_df)
    print(f"  Peak stored energy: {edata['smooth_energy'].max():,.0f}")
    print(f"  Mean stored energy: {edata['smooth_energy'].mean():,.0f}")
    print()

    # Step 3: Detect bursts
    print("Step 3: Detecting bursts...")
    bursts = detect_bursts(edata)
    print(f"  Detected {len(bursts)} burst(s):")
    for b in bursts:
        discharge_info = ""
        if b["trough_date"]:
            discharge_info = (f" → {b['trough_date'].strftime('%Y-%m-%d')} "
                              f"({b['discharge_pct']:.1f}% discharge, {b['duration_days']}d)")
        print(f"    Burst {b['burst_num']}: {b['peak_date'].strftime('%Y-%m-%d')} "
              f"(energy={b['peak_energy']:,.0f}){discharge_info}")
    print()

    # Step 4: Pre-event analysis
    print("Step 4: Pre-event buildup analysis...")
    pre_2021 = analyze_pre_event_buildup(daily_df, edata, "2021-01-28", lookback_days=180)
    pre_2024 = analyze_pre_event_buildup(daily_df, edata, "2024-06-07", lookback_days=180)

    for label, data in [("Pre-Jan 2021", pre_2021), ("Pre-Jun 2024", pre_2024)]:
        print(f"\n  --- {label} ({data['date_range'] if data['status'] == 'OK' else 'NO DATA'}) ---")
        if data["status"] == "OK":
            print(f"  Total energy slope: {data['total_slope']:+,.0f}/day")
            print(f"  Total peak: {data['total_peak']:,.0f}")
            print(f"  Long tenor (91d+): {data['long_pct_start']:.0f}% → {data['long_pct_end']:.0f}% "
                  f"(Δ{data['long_pct_shift']:+.0f}%)")
            print(f"  Per-tenor slopes (% of mean/day):")
            for b_name in BUCKET_ORDER:
                t = data["trends"][b_name]
                print(f"    {b_name:>10}: slope={t['slope_pct']:+.2f}%/day  mean={t['mean']:,.0f}  max={t['max']:,.0f}")
    print()

    # Step 5: Generate charts
    print("Step 5: Generating charts...")
    plot_full_energy_budget(edata, bursts, OUTPUT_DIR / "full_energy_budget.png")
    plot_energy_heatmap(edata, OUTPUT_DIR / "full_energy_heatmap.png")
    plot_storage_release(edata, OUTPUT_DIR / "full_storage_release.png")
    plot_long_tenor_timeseries(edata, OUTPUT_DIR / "long_tenor_timeseries.png")
    plot_pre_event_comparison(pre_2021, pre_2024, OUTPUT_DIR / "pre_event_comparison.png")
    print()

    # Step 6: Write findings report
    report_path = OUTPUT_DIR / "full_range_report.md"
    with open(report_path, "w") as f:
        f.write("# GME Full-Range Energy Pattern Analysis — Findings\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Data range:** {pd.Timestamp(edata['t_axis'][0]).strftime('%Y-%m-%d')} → "
                f"{pd.Timestamp(edata['t_axis'][-1]).strftime('%Y-%m-%d')}\n")
        f.write(f"**Trading days:** {edata['n_dates']}\n\n")

        f.write("## Burst Detection\n\n")
        f.write(f"Detected **{len(bursts)}** accumulate→discharge cycles:\n\n")
        f.write("| # | Peak Date | Peak Energy | Trough Date | Discharge | Duration |\n")
        f.write("|---|-----------|-------------|-------------|-----------|----------|\n")
        for b in bursts:
            td = b['trough_date'].strftime('%Y-%m-%d') if b['trough_date'] else "N/A"
            dp = f"{b['discharge_pct']:.1f}%" if b['discharge_pct'] else "N/A"
            dd = f"{b['duration_days']}d" if b['duration_days'] else "N/A"
            f.write(f"| {b['burst_num']} | {b['peak_date'].strftime('%Y-%m-%d')} "
                    f"| {b['peak_energy']:,.0f} | {td} | {dp} | {dd} |\n")

        f.write("\n## Pre-Event Buildup Comparison\n\n")
        f.write("| Metric | Pre-Jan 2021 | Pre-Jun 2024 |\n")
        f.write("|--------|-------------|-------------|\n")
        if pre_2021["status"] == "OK" and pre_2024["status"] == "OK":
            f.write(f"| Days analyzed | {pre_2021['n_days']} | {pre_2024['n_days']} |\n")
            f.write(f"| Energy slope | {pre_2021['total_slope']:+,.0f}/day | {pre_2024['total_slope']:+,.0f}/day |\n")
            f.write(f"| Peak energy | {pre_2021['total_peak']:,.0f} | {pre_2024['total_peak']:,.0f} |\n")
            f.write(f"| Long tenor start | {pre_2021['long_pct_start']:.0f}% | {pre_2024['long_pct_start']:.0f}% |\n")
            f.write(f"| Long tenor end | {pre_2021['long_pct_end']:.0f}% | {pre_2024['long_pct_end']:.0f}% |\n")
            f.write(f"| Long tenor shift | {pre_2021['long_pct_shift']:+.0f}% | {pre_2024['long_pct_shift']:+.0f}% |\n")

        f.write("\n## Key Finding: The Inventory Battery\n\n")
        f.write("The long-tenor timeseries chart shows whether LEAPS-level energy (91d+) was being loaded \n")
        f.write("in the months prior to each major event. A rising long-tenor % with a positive slope \n")
        f.write("indicates systematic energy accumulation in the 'Inventory Battery' — exactly the pattern \n")
        f.write("described in Part 1 of The Strike Price Symphony.\n\n")
        f.write("See `long_tenor_timeseries.png` for the visual evidence.\n")

    print(f"  Report: {report_path}")
    print()
    print("=" * 70)
    print("Done! All output saved to:", OUTPUT_DIR)
    print("=" * 70)


if __name__ == "__main__":
    main()
