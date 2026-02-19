#!/usr/bin/env python3
"""
Time-Binned Scatter Variants — GME May 17, 2024 Burst Window
==============================================================

Same 50,811 trades, different temporal granularity.
Shows how the anomaly appears (or disappears) as you aggregate:

  1. raw_ticks   — every individual trade execution
  2. 1s_bins     — 1-second VWAP bars
  3. 5s_bins     — 5-second VWAP bars
  4. 15s_bins    — 15-second VWAP bars
  5. 30s_bins    — 30-second VWAP bars
  6. 1min_bins   — 1-minute VWAP bars (what most charting platforms show)

The punchline: at 1-minute bins the dislocation nearly vanishes.
That's why TradingView doesn't show it.

Usage:
  python chart_scatter_variants.py
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from pathlib import Path
from datetime import timedelta

REPO_ROOT = Path(__file__).resolve().parents[2]
PARQUET_PATH = (REPO_ROOT / "data" / "raw" / "polygon" / "trades"
                / "symbol=GME" / "date=2024-05-17" / "part-0.parquet")
FIG_DIR = Path(__file__).parent.parent / "figures"
FIG_DIR.mkdir(exist_ok=True)

DARK_EXCHANGE_IDS = {4, 15}


def load_burst():
    """Load and filter to burst window (08:00–08:10 ET)."""
    df = pd.read_parquet(PARQUET_PATH)
    df['ts'] = pd.to_datetime(df['timestamp'])
    if df['ts'].dt.tz is not None:
        df['ts'] = df['ts'].dt.tz_localize(None)
    df['ts_et'] = df['ts'] - timedelta(hours=4)
    df['is_dark'] = df['exchange'].isin(DARK_EXCHANGE_IDS)
    burst = df[(df['ts_et'].dt.hour == 8) & (df['ts_et'].dt.minute < 10)].copy()
    return burst


def vwap_bin(group):
    """Volume-weighted average price for a bin."""
    notional = (group['price'] * group['size']).sum()
    volume = group['size'].sum()
    return notional / volume if volume > 0 else np.nan


def make_binned_scatter(burst, bin_label, bin_freq, figsize=(16, 10), dpi=180):
    """
    Generate a scatter plot for the given time-bin resolution.

    If bin_freq is None, plot raw ticks.
    Otherwise, aggregate into VWAP bars at the given pandas frequency string.
    """
    fig, ax = plt.subplots(1, 1, figsize=figsize, facecolor='#0d1117')
    ax.set_facecolor('#0d1117')

    dark = burst[burst['is_dark']].copy()
    lit = burst[~burst['is_dark']].copy()

    if bin_freq is None:
        # Raw ticks — every single trade
        ax.scatter(lit['ts_et'], lit['price'], s=0.6, alpha=0.45,
                   c='#39d353', label=f'Lit ({len(lit):,} trades)',
                   edgecolors='none', zorder=2)
        ax.scatter(dark['ts_et'], dark['price'], s=0.6, alpha=0.45,
                   c='#f85149', label=f'Dark/TRF ({len(dark):,} trades)',
                   edgecolors='none', zorder=3)
        n_points = len(burst)
        subtitle = f'{n_points:,} individual trade executions'
    else:
        # Bin into VWAP bars
        dark['bin'] = dark['ts_et'].dt.floor(bin_freq)
        lit['bin'] = lit['ts_et'].dt.floor(bin_freq)

        dark_vwap = dark.groupby('bin').apply(vwap_bin).dropna()
        lit_vwap = lit.groupby('bin').apply(vwap_bin).dropna()

        # Size proportional to volume in that bin
        dark_vol = dark.groupby('bin')['size'].sum()
        lit_vol = lit.groupby('bin')['size'].sum()

        # Normalize dot sizes
        max_vol = max(dark_vol.max(), lit_vol.max())
        dark_sizes = (dark_vol.reindex(dark_vwap.index).fillna(1) / max_vol * 120).clip(lower=3)
        lit_sizes = (lit_vol.reindex(lit_vwap.index).fillna(1) / max_vol * 120).clip(lower=3)

        ax.scatter(lit_vwap.index, lit_vwap.values, s=lit_sizes.values, alpha=0.7,
                   c='#39d353', label=f'Lit VWAP ({len(lit_vwap)} bins)',
                   edgecolors='white', linewidths=0.3, zorder=2)
        ax.scatter(dark_vwap.index, dark_vwap.values, s=dark_sizes.values, alpha=0.7,
                   c='#f85149', label=f'Dark VWAP ({len(dark_vwap)} bins)',
                   edgecolors='white', linewidths=0.3, zorder=3)

        n_points = len(dark_vwap) + len(lit_vwap)
        subtitle = f'{n_points} VWAP bins (dot size ∝ volume)'

    # Annotations
    ax.axhline(y=33.0, color='#f0883e', linewidth=1.2, linestyle='--', alpha=0.7)
    ax.text(burst['ts_et'].min() + timedelta(seconds=5), 33.35,
            '$33.00 OpEx Strike Ceiling', color='#f0883e', fontsize=9,
            fontstyle='italic', fontweight='bold')

    ax.axhline(y=21.5, color='#58a6ff', linewidth=0.8, linestyle=':', alpha=0.5)
    ax.text(burst['ts_et'].min() + timedelta(seconds=5), 21.7,
            'Lit NBBO ~$21.50', color='#58a6ff', fontsize=8, fontstyle='italic')

    # Dislocation bracket
    ax.annotate('', xy=(burst['ts_et'].max() - timedelta(seconds=10), 33.0),
                xytext=(burst['ts_et'].max() - timedelta(seconds=10), 21.5),
                arrowprops=dict(arrowstyle='<->', color='#ffa657', lw=1.5))
    ax.text(burst['ts_et'].max() - timedelta(seconds=8), 27.0,
            '$11.50\ndislocation', color='#ffa657', fontsize=10,
            fontweight='bold', ha='left', va='center')

    # Legend
    ax.legend(loc='upper right', fontsize=10,
              facecolor='#161b22', edgecolor='#30363d', labelcolor='white',
              markerscale=3)

    # Titles
    ax.set_title(f'GME — May 17, 2024, 08:00–08:10 ET\n'
                 f'Time Bin: {bin_label}  ({subtitle})',
                 color='white', fontsize=14, fontweight='bold', pad=15)
    ax.set_ylabel('Trade Price ($)', color='#c9d1d9', fontsize=11)
    ax.set_xlabel('Time (ET)', color='#c9d1d9', fontsize=11)

    ax.tick_params(colors='#8b949e', labelsize=9)
    ax.grid(True, alpha=0.08, color='#8b949e')
    for spine in ax.spines.values():
        spine.set_color('#30363d')

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))

    # Source watermark
    fig.text(0.5, 0.01,
             'Source: Polygon.io tick-level trade data  •  Independently verifiable  •  '
             'Code: github.com/TheGameStopsNow/research',
             ha='center', fontsize=7, color='#484f58', fontstyle='italic')

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    out = FIG_DIR / f"tape_fracture_scatter_{bin_label.replace(' ', '_').lower()}.png"
    fig.savefig(out, dpi=dpi, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"  {bin_label:20s} | {n_points:>8,} points | {out.name}")
    return out


def main():
    print("Loading burst window data...")
    burst = load_burst()
    print(f"  {len(burst):,} trades loaded\n")

    variants = [
        ("Raw Ticks",   None),
        ("1-Second",    "1s"),
        ("5-Second",    "5s"),
        ("15-Second",   "15s"),
        ("30-Second",   "30s"),
        ("1-Minute",    "1min"),
    ]

    print("Generating time-binned scatter variants:\n")
    print(f"  {'Bin':20s} | {'Points':>8s}        | Filename")
    print(f"  {'-'*20} | {'-'*15} | {'-'*50}")

    for label, freq in variants:
        make_binned_scatter(burst, label, freq)

    print("\nDone. All variants saved to figures/")
    print("\nThe punchline: as you aggregate toward 1-minute bins,")
    print("the dark cloud compresses into a line and the dislocation fades.")
    print("That's exactly what TradingView shows — and why the anomaly 'disappears.'")


if __name__ == "__main__":
    main()
