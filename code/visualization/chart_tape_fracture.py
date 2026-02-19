#!/usr/bin/env python3
"""
Tape Fracture Chart — GME May 17, 2024 Pre-Market
===================================================

Recreates the lit vs dark price dislocation from raw Polygon.io
tick-level trade data. TradingView has scrubbed this anomaly from
their feed; this script lets you verify it independently.

Data source: Polygon.io Trades (Parquet), stored locally at:
  data/raw/polygon/trades/symbol=GME/date=2024-05-17/part-0.parquet

Usage:
  python chart_tape_fracture.py

Output:
  figures/tape_fracture_may17_2024.png

Requirements:
  pip install pandas pyarrow matplotlib
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from pathlib import Path
from datetime import timedelta

# ── Paths ────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
PARQUET_PATH = REPO_ROOT / "data" / "raw" / "polygon" / "trades" / "symbol=GME" / "date=2024-05-17" / "part-0.parquet"
FIG_DIR = Path(__file__).parent.parent / "figures"
FIG_DIR.mkdir(exist_ok=True)

# ── TRF Exchange IDs (Polygon) ───────────────────────
# 4 = FINRA TRF (Carteret), 15 = FINRA TRF (Chicago)
DARK_EXCHANGE_IDS = {4, 15}

# ── Load & Prep ──────────────────────────────────────
def load_data():
    """Load Polygon parquet and convert timestamps to ET."""
    df = pd.read_parquet(PARQUET_PATH)
    df['ts'] = pd.to_datetime(df['timestamp'])
    if df['ts'].dt.tz is not None:
        df['ts'] = df['ts'].dt.tz_localize(None)
    # Polygon timestamps are UTC; convert to ET (UTC-4 in May)
    df['ts_et'] = df['ts'] - timedelta(hours=4)
    df['is_dark'] = df['exchange'].isin(DARK_EXCHANGE_IDS)
    return df


def chart_full_premarket(df):
    """
    Chart 1: Full pre-market window (04:00–09:30 ET)
    Shows the entire lit vs dark price landscape.
    """
    pm = df[(df['ts_et'].dt.hour >= 4) & 
            ((df['ts_et'].dt.hour < 9) | 
             ((df['ts_et'].dt.hour == 9) & (df['ts_et'].dt.minute <= 30)))].copy()
    
    dark = pm[pm['is_dark']].copy()
    lit = pm[~pm['is_dark']].copy()
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), 
                                     gridspec_kw={'height_ratios': [3, 1]},
                                     facecolor='#1a1a2e')
    
    # ── Price Chart ──
    ax1.set_facecolor('#1a1a2e')
    ax1.scatter(dark['ts_et'], dark['price'], s=0.3, alpha=0.4, 
                c='#ff4444', label=f'Dark/TRF ({len(dark):,} trades)', zorder=2)
    ax1.scatter(lit['ts_et'], lit['price'], s=0.3, alpha=0.4, 
                c='#44ff44', label=f'Lit ({len(lit):,} trades)', zorder=3)
    
    # 1-minute VWAP lines
    dark['minute'] = dark['ts_et'].dt.floor('1min')
    lit['minute'] = lit['ts_et'].dt.floor('1min')
    
    dark_vwap = dark.groupby('minute').apply(
        lambda g: (g['price'] * g['size']).sum() / g['size'].sum()
    ).reset_index()
    dark_vwap.columns = ['minute', 'vwap']
    
    lit_vwap = lit.groupby('minute').apply(
        lambda g: (g['price'] * g['size']).sum() / g['size'].sum()
    ).reset_index()
    lit_vwap.columns = ['minute', 'vwap']
    
    ax1.plot(dark_vwap['minute'], dark_vwap['vwap'], color='#ff6666', 
             linewidth=1.5, alpha=0.9, label='Dark VWAP (1-min)', zorder=4)
    ax1.plot(lit_vwap['minute'], lit_vwap['vwap'], color='#66ff66', 
             linewidth=1.5, alpha=0.9, label='Lit VWAP (1-min)', zorder=5)
    
    # Annotation: $33 ceiling
    ax1.axhline(y=33.0, color='#ffaa00', linewidth=1, linestyle='--', alpha=0.7)
    ax1.text(pm['ts_et'].min(), 33.3, '$33.00 OpEx Settlement Ceiling', 
             color='#ffaa00', fontsize=9, fontstyle='italic')
    
    ax1.set_ylabel('Price ($)', color='white', fontsize=12)
    ax1.set_title('GME — May 17, 2024 Pre-Market: The Tape Fracture\n'
                  'Dark/TRF trades (red) vs Lit exchanges (green) — Polygon.io tick data',
                  color='white', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=9, facecolor='#2a2a4a', 
               edgecolor='#555', labelcolor='white')
    ax1.tick_params(colors='white')
    ax1.grid(True, alpha=0.15, color='white')
    ax1.spines['bottom'].set_color('#555')
    ax1.spines['left'].set_color('#555')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # ── Spread Chart ──
    ax2.set_facecolor('#1a1a2e')
    merged = pd.merge(dark_vwap, lit_vwap, on='minute', suffixes=('_dark', '_lit'))
    merged['spread'] = merged['vwap_dark'] - merged['vwap_lit']
    
    colors = ['#ff4444' if s > 0 else '#44ff44' for s in merged['spread']]
    ax2.bar(merged['minute'], merged['spread'], width=0.0006, color=colors, alpha=0.8)
    ax2.axhline(y=0, color='white', linewidth=0.5, alpha=0.3)
    ax2.set_ylabel('Dark − Lit ($)', color='white', fontsize=12)
    ax2.set_xlabel('Time (ET)', color='white', fontsize=12)
    ax2.tick_params(colors='white')
    ax2.grid(True, alpha=0.15, color='white')
    ax2.spines['bottom'].set_color('#555')
    ax2.spines['left'].set_color('#555')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    # Format x-axis
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
    
    plt.tight_layout()
    out = FIG_DIR / "tape_fracture_may17_2024_premarket.png"
    fig.savefig(out, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")
    return out


def chart_burst_window(df):
    """
    Chart 2: Burst window (08:00–08:10 ET) — the 10-minute settlement operation.
    High-resolution view of the $12 tape fracture.
    """
    burst = df[(df['ts_et'].dt.hour == 8) & (df['ts_et'].dt.minute < 10)].copy()
    
    dark = burst[burst['is_dark']].copy()
    lit = burst[~burst['is_dark']].copy()
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), 
                                          gridspec_kw={'height_ratios': [3, 1, 1]},
                                          facecolor='#1a1a2e')
    
    # ── Price Chart ──
    ax1.set_facecolor('#1a1a2e')
    ax1.scatter(dark['ts_et'], dark['price'], s=1.5, alpha=0.5, 
                c='#ff4444', label=f'Dark/TRF ({len(dark):,} trades)', zorder=2)
    ax1.scatter(lit['ts_et'], lit['price'], s=1.5, alpha=0.5, 
                c='#44ff44', label=f'Lit ({len(lit):,} trades)', zorder=3)
    
    # $33 ceiling
    ax1.axhline(y=33.0, color='#ffaa00', linewidth=1, linestyle='--', alpha=0.7)
    ax1.text(burst['ts_et'].min(), 33.3, '$33.00 OpEx Settlement Ceiling', 
             color='#ffaa00', fontsize=9, fontstyle='italic')
    
    # NBBO envelope 
    ax1.axhline(y=21.5, color='#4488ff', linewidth=0.8, linestyle=':', alpha=0.5)
    ax1.text(burst['ts_et'].min(), 21.7, 'Lit NBBO ~$21.50', 
             color='#4488ff', fontsize=8, fontstyle='italic')
    
    ax1.set_ylabel('Price ($)', color='white', fontsize=12)
    ax1.set_title('GME — May 17, 2024, 08:00–08:10 ET: The Settlement Burst\n'
                  'Two markets running simultaneously — $12 price dislocation\n'
                  'Source: Polygon.io tick-level trade data (independently verifiable)',
                  color='white', fontsize=13, fontweight='bold')
    ax1.legend(loc='upper right', fontsize=9, facecolor='#2a2a4a', 
               edgecolor='#555', labelcolor='white')
    ax1.tick_params(colors='white')
    ax1.grid(True, alpha=0.15, color='white')
    ax1.spines['bottom'].set_color('#555')
    ax1.spines['left'].set_color('#555')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # ── Volume by Venue ──
    ax2.set_facecolor('#1a1a2e')
    dark['second'] = dark['ts_et'].dt.floor('1s')
    lit['second'] = lit['ts_et'].dt.floor('1s')
    dark_vol = dark.groupby('second')['size'].sum()
    lit_vol = lit.groupby('second')['size'].sum()
    
    ax2.bar(dark_vol.index, dark_vol.values, width=0.000008, color='#ff4444', alpha=0.6, label='Dark Vol')
    ax2.bar(lit_vol.index, lit_vol.values, width=0.000008, color='#44ff44', alpha=0.6, label='Lit Vol')
    ax2.set_ylabel('Volume', color='white', fontsize=10)
    ax2.legend(loc='upper right', fontsize=8, facecolor='#2a2a4a', 
               edgecolor='#555', labelcolor='white')
    ax2.tick_params(colors='white')
    ax2.grid(True, alpha=0.15, color='white')
    ax2.spines['bottom'].set_color('#555')
    ax2.spines['left'].set_color('#555')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    # ── Spread (Dark VWAP - Lit VWAP) per 15 seconds ──
    ax3.set_facecolor('#1a1a2e')
    dark['bin15'] = dark['ts_et'].dt.floor('15s')
    lit['bin15'] = lit['ts_et'].dt.floor('15s')
    
    d_vwap = dark.groupby('bin15').apply(
        lambda g: (g['price'] * g['size']).sum() / g['size'].sum()
    )
    l_vwap = lit.groupby('bin15').apply(
        lambda g: (g['price'] * g['size']).sum() / g['size'].sum()
    )
    spread = (d_vwap - l_vwap).dropna()
    
    colors = ['#ff4444' if s > 0 else '#44ff44' for s in spread]
    ax3.bar(spread.index, spread.values, width=0.00015, color=colors, alpha=0.8)
    ax3.axhline(y=0, color='white', linewidth=0.5, alpha=0.3)
    ax3.set_ylabel('Dark − Lit ($)', color='white', fontsize=10)
    ax3.set_xlabel('Time (ET) — May 17, 2024', color='white', fontsize=12)
    ax3.tick_params(colors='white')
    ax3.grid(True, alpha=0.15, color='white')
    ax3.spines['bottom'].set_color('#555')
    ax3.spines['left'].set_color('#555')
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    
    # Max spread annotation
    if len(spread) > 0:
        max_idx = spread.idxmax()
        max_val = spread[max_idx]
        ax3.annotate(f'Max Δ: ${max_val:.2f}', xy=(max_idx, max_val),
                     xytext=(max_idx, max_val + 1),
                     arrowprops=dict(arrowstyle='->', color='#ffaa00'),
                     color='#ffaa00', fontsize=9, fontweight='bold')
    
    for ax in [ax1, ax2, ax3]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))
    
    plt.tight_layout()
    out = FIG_DIR / "tape_fracture_may17_2024_burst.png"
    fig.savefig(out, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")
    return out


def print_stats(df):
    """Print summary statistics for reproducibility."""
    burst = df[(df['ts_et'].dt.hour == 8) & (df['ts_et'].dt.minute < 10)].copy()
    dark = burst[burst['is_dark']]
    lit = burst[~burst['is_dark']]
    
    print("\n" + "=" * 60)
    print("TAPE FRACTURE STATISTICS — May 17, 2024, 08:00–08:10 ET")
    print("=" * 60)
    print(f"  Total burst trades:  {len(burst):>10,}")
    print(f"  Dark/TRF trades:     {len(dark):>10,}")
    print(f"  Lit trades:          {len(lit):>10,}")
    print(f"  Dark price range:    ${dark['price'].min():.2f} – ${dark['price'].max():.2f}")
    print(f"  Lit price range:     ${lit['price'].min():.2f} – ${lit['price'].max():.2f}")
    print(f"  Max dark price:      ${dark['price'].max():.2f}")
    print(f"  Max lit price:       ${lit['price'].max():.2f}")
    print(f"  Max dislocation:     ${dark['price'].max() - lit['price'].max():.2f}")
    print(f"  Dark volume:         {dark['size'].sum():>10,} shares")
    print(f"  Lit volume:          {lit['size'].sum():>10,} shares")
    print("=" * 60)


def main():
    print("Loading Polygon.io GME trade data for 2024-05-17...")
    df = load_data()
    print(f"  Loaded {len(df):,} trades")
    
    print_stats(df)
    
    print("\nGenerating Chart 1: Full Pre-Market...")
    chart_full_premarket(df)
    
    print("\nGenerating Chart 2: Burst Window (08:00–08:10 ET)...")
    chart_burst_window(df)
    
    print("\nDone. Charts saved to figures/ directory.")
    print("\nTo reproduce: download Polygon.io GME trades for 2024-05-17")
    print("as Parquet, place in data/raw/polygon/trades/symbol=GME/date=2024-05-17/")
    print("and run this script.")


if __name__ == "__main__":
    main()
