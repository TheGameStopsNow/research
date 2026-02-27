#!/usr/bin/env python3
"""
Energy Pattern Analysis: Pre-Event Buildup Detection
=====================================================
Analyzes GME options energy budget data to identify accumulation/discharge
patterns analogous to those observed before January 2021 and June 2024.

Uses the 286 daily options roll parquets (May 2024 – Dec 2025) to:
1. Compute daily energy budget by DTE tenor bucket
2. Detect accumulate→discharge cycles using peak/trough detection
3. Measure cadence (inter-burst interval) and escalation (tenor migration)
4. Generate publication-quality charts

Data source: power-tracks-research/data/derived/rolls/GME_*_options_roll.parquet
Energy weights: same as sweep_mechanics.py Tab 7 (Energy Flow)

Usage:
    python3 energy_pattern_analysis.py
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
ROLLS_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/derived/rolls")
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# DTE buckets matching sweep_mechanics.py
BUCKET_ORDER = ["0DTE", "1-7d", "8-30d", "31-90d", "91-180d", "181-365d", "365d+"]
ENERGY_WEIGHTS = {
    "0DTE": 0.1,
    "1-7d": 4.0,
    "8-30d": 19.0,
    "31-90d": 60.0,
    "91-180d": 135.0,
    "181-365d": 270.0,
    "365d+": 500.0,
}
BUCKET_COLORS = [
    "#e6194b", "#f58231", "#3cb44b", "#4363d8",
    "#911eb4", "#42d4f4", "#f032e6",
]

# Map roll column prefixes to DTE buckets
# Week_0 = 0DTE (current week, ~0-4 days)
# Week_1 = next week (~5-11 days)
# Week_2-4 = 2-4 weeks out (~12-30 days)
# Month_1-3 = 1-3 months (~31-90 days)
# Month_4-6 = 4-6 months (~91-180 days)
# Month_7-12 = 7-12 months (~181-365 days)
# Month_13+ = >12 months (~365d+)
def week_to_bucket(week_offset: int) -> str:
    """Map a Week_N offset to a DTE bucket."""
    if week_offset <= 0:
        return "0DTE"
    elif week_offset <= 1:
        return "1-7d"
    elif week_offset <= 4:
        return "8-30d"
    else:
        # Weeks 5+ are >30 days
        days = week_offset * 7
        if days <= 90:
            return "31-90d"
        elif days <= 180:
            return "91-180d"
        elif days <= 365:
            return "181-365d"
        else:
            return "365d+"

def month_to_bucket(month_offset: int) -> str:
    """Map a Month_N offset to a DTE bucket."""
    if month_offset <= 0:
        return "0DTE"  # current month expired
    days = month_offset * 30  # approximate
    if days <= 7:
        return "1-7d"
    elif days <= 30:
        return "8-30d"
    elif days <= 90:
        return "31-90d"
    elif days <= 180:
        return "91-180d"
    elif days <= 365:
        return "181-365d"
    else:
        return "365d+"


# ============================================================================
# Data Loading
# ============================================================================
def load_all_rolls(ticker: str = "GME") -> pd.DataFrame:
    """Load all daily options roll parquets and compute daily energy budget."""
    pattern = f"{ticker}_*_options_roll.parquet"
    files = sorted(ROLLS_DIR.glob(pattern))
    if not files:
        print(f"ERROR: No files matching {pattern} in {ROLLS_DIR}")
        sys.exit(1)

    print(f"Found {len(files)} roll files for {ticker}")

    daily_rows = []
    for i, fpath in enumerate(files):
        # Extract date from filename
        date_str = fpath.stem.split("_")[1]  # e.g. "20240501"
        dt = datetime.strptime(date_str, "%Y%m%d")

        df = pd.read_parquet(fpath)
        if df.empty:
            continue

        # Sum volume across all minutes for each tenor column
        bucket_volume = defaultdict(float)
        bucket_count = defaultdict(float)

        for col in df.columns:
            if col == "timestamp":
                continue

            parts = col.split("_")
            if len(parts) < 3:
                continue

            # Parse prefix: "Week" or "Month"
            time_type = parts[0]
            try:
                offset = int(parts[1])
            except ValueError:
                continue

            metric = parts[-1]  # "volume", "count", or "pressure"
            # put_call = parts[-2]  # "C" or "P"

            # Only negative offsets are past (already expired), skip them
            if offset < 0:
                continue

            # Map to bucket
            if time_type == "Week":
                bucket = week_to_bucket(offset)
            elif time_type == "Month":
                bucket = month_to_bucket(offset)
            else:
                continue

            daily_total = df[col].sum()
            if metric == "volume":
                bucket_volume[bucket] += daily_total
            elif metric == "count":
                bucket_count[bucket] += daily_total

        row = {"date": dt}
        for b in BUCKET_ORDER:
            row[f"{b}_volume"] = bucket_volume.get(b, 0)
            row[f"{b}_count"] = bucket_count.get(b, 0)
        daily_rows.append(row)

        if (i + 1) % 50 == 0 or i == 0:
            print(f"  [{i+1}/{len(files)}] {dt.strftime('%Y-%m-%d')}")

    result = pd.DataFrame(daily_rows).sort_values("date").reset_index(drop=True)
    print(f"Loaded {len(result)} trading days: {result['date'].min()} → {result['date'].max()}")
    return result


# ============================================================================
# Energy Computation
# ============================================================================
def compute_energy(daily_df: pd.DataFrame) -> dict:
    """Compute energy matrices and derived metrics from daily volume data."""
    n = len(daily_df)
    t_axis = daily_df["date"].values

    # Build trade matrix (n_dates × 7_buckets) using volume
    trade_matrix = np.column_stack([
        daily_df[f"{b}_volume"].values.astype(float) for b in BUCKET_ORDER
    ])

    # Energy = trades × weight
    weight_vec = np.array([ENERGY_WEIGHTS[b] for b in BUCKET_ORDER])
    energy_matrix = trade_matrix * weight_vec[np.newaxis, :]

    # Total stored energy per date
    total_energy = energy_matrix.sum(axis=1)

    # Smooth for analysis
    smooth_energy = uniform_filter1d(total_energy, size=10)
    flow_rate = np.gradient(smooth_energy)
    flow_smooth = uniform_filter1d(flow_rate, size=5)

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
    }


# ============================================================================
# Burst Detection
# ============================================================================
def detect_bursts(edata: dict, min_prominence: float = 0.3) -> list[dict]:
    """Detect accumulate→discharge cycles from energy data.

    Uses scipy peak detection on smoothed energy to find local maxima (peaks)
    and minima (troughs). Each peak→trough pair is a discharge event.
    """
    smooth = edata["smooth_energy"]
    t_axis = edata["t_axis"]

    # Normalize for relative peak detection
    if smooth.max() == 0:
        return []
    normalized = smooth / smooth.max()

    # Find peaks (accumulation crests)
    peaks, peak_props = find_peaks(
        normalized,
        distance=15,        # at least 15 trading days apart (~3 weeks)
        prominence=min_prominence,
        width=5,            # minimum 5-day peak width
    )

    # Find troughs (discharge valleys)
    troughs, _ = find_peaks(
        -normalized,
        distance=15,
        prominence=min_prominence * 0.5,
    )

    bursts = []
    for i, peak_idx in enumerate(peaks):
        peak_date = pd.Timestamp(t_axis[peak_idx])
        peak_energy = float(smooth[peak_idx])

        # Find the next trough after this peak
        subsequent_troughs = troughs[troughs > peak_idx]
        if len(subsequent_troughs) > 0:
            trough_idx = subsequent_troughs[0]
            trough_date = pd.Timestamp(t_axis[trough_idx])
            trough_energy = float(smooth[trough_idx])
            discharge_pct = (peak_energy - trough_energy) / peak_energy * 100
            duration_days = (trough_date - peak_date).days
        else:
            trough_date = None
            trough_energy = None
            discharge_pct = None
            duration_days = None

        # Compute energy composition at peak (which tenors dominate)
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
# Cadence Analysis
# ============================================================================
def analyze_cadence(bursts: list[dict]) -> dict:
    """Measure inter-burst intervals and energy escalation."""
    if len(bursts) < 2:
        return {"intervals": [], "mean_interval": None, "escalation": []}

    intervals = []
    for i in range(1, len(bursts)):
        gap = (bursts[i]["peak_date"] - bursts[i-1]["peak_date"]).days
        intervals.append(gap)

    # Energy escalation: is each burst bigger than the last?
    escalation = []
    for i in range(1, len(bursts)):
        ratio = bursts[i]["peak_energy"] / bursts[i-1]["peak_energy"]
        escalation.append(ratio)

    # Tenor migration: is energy shifting to longer tenors over time?
    long_tenor_pct = []
    for b in bursts:
        pct_91plus = (
            b["composition"].get("91-180d", 0)
            + b["composition"].get("181-365d", 0)
            + b["composition"].get("365d+", 0)
        )
        long_tenor_pct.append(pct_91plus)

    return {
        "intervals_days": intervals,
        "mean_interval": np.mean(intervals) if intervals else None,
        "std_interval": np.std(intervals) if len(intervals) > 1 else None,
        "escalation_ratios": escalation,
        "long_tenor_pct": long_tenor_pct,
    }


# ============================================================================
# Visualization
# ============================================================================
def plot_energy_budget(edata: dict, bursts: list[dict], save_path: Path):
    """Stacked area chart of energy budget by tenor, with burst annotations."""
    fig, ax = plt.subplots(figsize=(18, 6))

    t_axis = edata["t_axis"]
    em = edata["energy_matrix"]
    n = edata["n_dates"]

    bottom = np.zeros(n)
    for i, b in enumerate(BUCKET_ORDER):
        vals = uniform_filter1d(em[:, i], size=10)
        ax.fill_between(t_axis, bottom, bottom + vals,
                        alpha=0.75, color=BUCKET_COLORS[i],
                        label=f"{b} (w={ENERGY_WEIGHTS[b]:.0f})")
        bottom += vals

    # Annotate bursts
    for b in bursts:
        ax.axvline(b["peak_date"], color="red", linewidth=1.5, alpha=0.7, linestyle="--")
        ax.annotate(f"Burst {b['burst_num']}\n{b['peak_date'].strftime('%Y-%m-%d')}",
                    xy=(b["peak_date"], b["peak_energy"] * 0.9),
                    fontsize=8, color="red", ha="center",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))

    ax.set_ylabel("Energy (trades × DTE weight)")
    ax.set_title("GME Energy Budget by Tenor — Burst Detection", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.2)
    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_storage_release(edata: dict, bursts: list[dict], save_path: Path):
    """Dual panel: stored energy + flow rate with burst markers."""
    fig, (ax_store, ax_flow) = plt.subplots(
        2, 1, figsize=(18, 8), sharex=True,
        gridspec_kw={"height_ratios": [2, 1]}
    )

    t_axis = edata["t_axis"]
    smooth = edata["smooth_energy"]
    flow = edata["flow_smooth"]

    # Stored energy
    ax_store.fill_between(t_axis, smooth, alpha=0.3, color="#2196f3")
    ax_store.plot(t_axis, smooth, color="#2196f3", linewidth=1.5, label="Stored Energy")
    for b in bursts:
        ax_store.axvline(b["peak_date"], color="red", linewidth=1, alpha=0.5, linestyle="--")
        if b["trough_date"]:
            ax_store.axvline(b["trough_date"], color="green", linewidth=1, alpha=0.5, linestyle=":")
    ax_store.set_ylabel("Stored Energy\n(trades × DTE weight)")
    ax_store.set_title("Hedging Energy Over Time — Accumulation/Discharge Cycles", fontsize=14)
    ax_store.grid(True, alpha=0.2)
    ax_store.legend(loc="upper left")

    # Flow rate
    pos_flow = np.where(flow > 0, flow, 0)
    neg_flow = np.where(flow < 0, flow, 0)
    ax_flow.fill_between(t_axis, pos_flow, alpha=0.4, color="#2196f3", label="Accumulating")
    ax_flow.fill_between(t_axis, neg_flow, alpha=0.4, color="#ff4444", label="Discharging")
    ax_flow.axhline(0, color="gray", linewidth=0.5)

    # Mark >2σ discharge events
    std_flow = np.std(flow)
    major_drops = np.where(flow < -2 * std_flow)[0]
    events = []
    if len(major_drops) > 0:
        events = [major_drops[0]]
        for idx in major_drops[1:]:
            if idx - events[-1] > 20:
                events.append(idx)
        for evt in events[:10]:
            evt_date = pd.Timestamp(t_axis[evt])
            ax_flow.annotate(
                evt_date.strftime("%Y-%m-%d"),
                xy=(t_axis[evt], flow[evt]),
                xytext=(0, -25), textcoords="offset points",
                fontsize=7, color="#ff4444", ha="center",
                arrowprops=dict(arrowstyle="->", color="#ff4444", lw=0.8),
            )

    ax_flow.set_ylabel("Energy Flow Rate")
    ax_flow.set_xlabel("Date")
    ax_flow.grid(True, alpha=0.2)
    ax_flow.legend(loc="upper left")

    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_tenor_migration(bursts: list[dict], save_path: Path):
    """Bar chart showing tenor composition shift across successive bursts."""
    if not bursts:
        return

    fig, ax = plt.subplots(figsize=(12, 6))

    n_bursts = len(bursts)
    x = np.arange(n_bursts)
    width = 0.6

    bottom = np.zeros(n_bursts)
    for j, b_name in enumerate(BUCKET_ORDER):
        vals = [bursts[i]["composition"].get(b_name, 0) for i in range(n_bursts)]
        ax.bar(x, vals, width, bottom=bottom, color=BUCKET_COLORS[j], label=b_name, alpha=0.85)
        bottom += np.array(vals)

    ax.set_xticks(x)
    ax.set_xticklabels([f"Burst {b['burst_num']}\n{b['peak_date'].strftime('%b %Y')}" for b in bursts])
    ax.set_ylabel("% of Total Energy at Peak")
    ax.set_title("Energy Composition by Burst — Tenor Migration", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.2, axis="y")
    ax.set_ylim(0, 105)

    plt.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {save_path}")


def plot_cadence_timeline(bursts: list[dict], cadence: dict, save_path: Path):
    """Timeline showing burst intervals and projected next burst."""
    if len(bursts) < 2:
        print("  Not enough bursts for cadence timeline")
        return

    fig, ax = plt.subplots(figsize=(14, 5))

    dates = [b["peak_date"] for b in bursts]
    energies = [b["peak_energy"] for b in bursts]

    ax.scatter(dates, energies, s=200, c="red", zorder=5, edgecolors="black", linewidths=1.5)
    for b in bursts:
        ax.annotate(
            f"Burst {b['burst_num']}\n{b['peak_energy']:,.0f}",
            xy=(b["peak_date"], b["peak_energy"]),
            xytext=(0, 20), textcoords="offset points",
            fontsize=9, ha="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="orange"),
        )

    # Draw interval arrows
    for i in range(1, len(bursts)):
        mid_date = dates[i-1] + (dates[i] - dates[i-1]) / 2
        mid_y = (energies[i-1] + energies[i]) / 2
        ax.annotate(
            f"{cadence['intervals_days'][i-1]}d",
            xy=(mid_date, mid_y),
            fontsize=10, ha="center", color="blue", fontweight="bold",
        )

    # Project next burst
    if cadence["mean_interval"]:
        projected_date = dates[-1] + pd.Timedelta(days=cadence["mean_interval"])
        ax.axvline(projected_date, color="orange", linewidth=2, linestyle="--", alpha=0.7)
        ax.annotate(
            f"Projected\n~{projected_date.strftime('%b %d, %Y')}",
            xy=(projected_date, max(energies) * 0.7),
            fontsize=10, ha="center", color="orange", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", edgecolor="orange"),
        )

    ax.set_ylabel("Peak Energy")
    ax.set_title(
        f"Burst Cadence — Mean Interval: {cadence['mean_interval']:.0f} days "
        f"(±{cadence['std_interval']:.0f}d)" if cadence["std_interval"] else
        f"Burst Cadence — {len(bursts)} bursts detected",
        fontsize=14, fontweight="bold"
    )
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
    print("GME Energy Pattern Analysis — Pre-Event Buildup Detection")
    print("=" * 70)
    print()

    # Step 1: Load data
    print("Step 1: Loading options roll data...")
    daily_df = load_all_rolls("GME")
    print()

    # Step 2: Compute energy
    print("Step 2: Computing energy budget...")
    edata = compute_energy(daily_df)
    print(f"  Peak stored energy: {edata['smooth_energy'].max():,.0f}")
    print(f"  Mean stored energy: {edata['smooth_energy'].mean():,.0f}")
    print()

    # Step 3: Detect bursts
    print("Step 3: Detecting accumulate→discharge cycles...")
    bursts = detect_bursts(edata, min_prominence=0.15)
    print(f"  Detected {len(bursts)} burst(s):")
    for b in bursts:
        print(f"    Burst {b['burst_num']}: Peak {b['peak_date'].strftime('%Y-%m-%d')} "
              f"(energy={b['peak_energy']:,.0f})"
              + (f" → Trough {b['trough_date'].strftime('%Y-%m-%d')} "
                 f"({b['discharge_pct']:.1f}% discharge, {b['duration_days']}d)"
                 if b['trough_date'] else " (no subsequent trough)"))
    print()

    # Step 4: Cadence analysis
    print("Step 4: Analyzing cadence...")
    cadence = analyze_cadence(bursts)
    if cadence["mean_interval"]:
        print(f"  Mean inter-burst interval: {cadence['mean_interval']:.0f} days "
              f"(±{cadence['std_interval']:.0f}d)" if cadence["std_interval"] else
              f"  Mean inter-burst interval: {cadence['mean_interval']:.0f} days")
        print(f"  Intervals: {cadence['intervals_days']}")
        print(f"  Escalation ratios: {[f'{r:.2f}x' for r in cadence['escalation_ratios']]}")
        print(f"  Long-tenor % (91d+) by burst: {[f'{p:.1f}%' for p in cadence['long_tenor_pct']]}")

        # Projected next burst
        if bursts:
            projected = bursts[-1]["peak_date"] + pd.Timedelta(days=cadence["mean_interval"])
            print(f"  → Projected next peak: ~{projected.strftime('%B %d, %Y')}")
    print()

    # Step 5: Tenor composition summary
    print("Step 5: Energy tenor summary...")
    em = edata["energy_matrix"]
    tenor_totals = em.sum(axis=0)
    total_all = tenor_totals.sum()
    print(f"  {'Tenor':<12} {'Weight':>8} {'Total Energy':>15} {'% of Total':>12}")
    print(f"  {'-'*12} {'-'*8} {'-'*15} {'-'*12}")
    for i, b in enumerate(BUCKET_ORDER):
        pct = tenor_totals[i] / total_all * 100 if total_all > 0 else 0
        print(f"  {b:<12} {ENERGY_WEIGHTS[b]:>8.0f} {tenor_totals[i]:>15,.0f} {pct:>11.1f}%")
    print()

    # Step 6: Generate charts
    print("Step 6: Generating charts...")
    plot_energy_budget(edata, bursts, OUTPUT_DIR / "energy_budget_bursts.png")
    plot_storage_release(edata, bursts, OUTPUT_DIR / "energy_storage_release.png")
    plot_tenor_migration(bursts, OUTPUT_DIR / "energy_tenor_migration.png")
    plot_cadence_timeline(bursts, cadence, OUTPUT_DIR / "energy_cadence_timeline.png")
    print()

    # Step 7: Write findings report
    report_path = OUTPUT_DIR / "energy_pattern_report.md"
    with open(report_path, "w") as f:
        f.write("# GME Energy Pattern Analysis — Findings Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Data range:** {pd.Timestamp(edata['t_axis'][0]).strftime('%Y-%m-%d')} → "
                f"{pd.Timestamp(edata['t_axis'][-1]).strftime('%Y-%m-%d')}\n")
        f.write(f"**Trading days:** {edata['n_dates']}\n\n")

        f.write("## Burst Detection\n\n")
        f.write(f"Detected **{len(bursts)}** accumulate→discharge cycles:\n\n")
        f.write("| Burst | Peak Date | Peak Energy | Trough Date | Discharge % | Duration |\n")
        f.write("|-------|-----------|-------------|-------------|-------------|----------|\n")
        for b in bursts:
            f.write(f"| {b['burst_num']} | {b['peak_date'].strftime('%Y-%m-%d')} "
                    f"| {b['peak_energy']:,.0f} "
                    f"| {b['trough_date'].strftime('%Y-%m-%d') if b['trough_date'] else 'N/A'} "
                    f"| {b['discharge_pct']:.1f}% " if b['discharge_pct'] else "| N/A ")
            f.write(f"| {b['duration_days']}d |\n" if b['duration_days'] else "| N/A |\n")

        if cadence["mean_interval"]:
            f.write(f"\n## Cadence Analysis\n\n")
            f.write(f"- **Mean interval:** {cadence['mean_interval']:.0f} days\n")
            if cadence["std_interval"]:
                f.write(f"- **Std deviation:** ±{cadence['std_interval']:.0f} days\n")
            f.write(f"- **Intervals:** {cadence['intervals_days']}\n")
            f.write(f"- **Escalation ratios:** {[f'{r:.2f}x' for r in cadence['escalation_ratios']]}\n\n")

            f.write("## Tenor Migration\n\n")
            f.write("| Burst | 0DTE | 1-7d | 8-30d | 31-90d | 91-180d | 181-365d | 365d+ | Long (91d+) |\n")
            f.write("|-------|------|------|-------|--------|---------|----------|-------|-------------|\n")
            for i, b in enumerate(bursts):
                c = b["composition"]
                long_pct = cadence["long_tenor_pct"][i]
                f.write(f"| {b['burst_num']} "
                        + " ".join(f"| {c.get(bn, 0):.1f}%" for bn in BUCKET_ORDER)
                        + f" | **{long_pct:.1f}%** |\n")

        f.write("\n## Data Limitation Note\n\n")
        f.write("This analysis covers **May 2024 through December 2025** — the earliest available "
                "options roll data. It cannot directly test for pre-January 2021 buildup "
                "patterns because that data was not collected in this format.\n\n")
        f.write("To test for pre-2021 patterns, you would need to:\n")
        f.write("1. Fetch historical options data from ThetaData for 2020 (or earlier)\n")
        f.write("2. Compute the same DTE-weighted energy budget\n")
        f.write("3. Look for similar accumulation signatures in the 91-365d tenor bands\n\n")
        f.write("The LEAPS energy persistence noted in Part 1 (\"during the dead years of 2022-2023, "
                "LEAPS energy persisted at the 181-365 day level\") suggests there *was* a sustained "
                "loading pattern, but without tick-level options data for that period, we can only "
                "infer its existence from the ACF regime data and settlement-layer (FTD) evidence.\n")

    print(f"  Report: {report_path}")
    print()
    print("Done! All output saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
