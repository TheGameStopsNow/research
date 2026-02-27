#!/usr/bin/env python3
"""
Combined Chart — Tight Clean Scatter + Volume + Spread
=======================================================

Top panel:    Raw tick scatter (tight_clean style — every trade, no VWAP lines)
Middle panel: Volume by venue (Dark vs Lit, per-second bars)
Bottom panel: Dark − Lit VWAP spread (15-second bins)

Usage:
  python chart_combined.py

Output:
  figures/tape_fracture_combined.png
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
PARQUET_PATH = (REPO_ROOT / "data" / "raw" / "polygon" / "trades"
                / "symbol=GME" / "date=2024-05-17" / "part-0.parquet")
FIG_DIR = Path(__file__).parent.parent / "figures"
FIG_DIR.mkdir(exist_ok=True)

DARK_EXCHANGE_IDS = {4, 15}
BG = '#0d1117'           # GitHub dark
PANEL_BG = '#0d1117'
GRID_COLOR = '#8b949e'
SPINE_COLOR = '#30363d'
TEXT_COLOR = '#c9d1d9'
GREEN = '#39d353'         # Lit
RED = '#f85149'           # Dark/TRF
ACCENT_ORANGE = '#f0883e'
ACCENT_BLUE = '#58a6ff'
SPREAD_RED = '#f85149'
SPREAD_GREEN = '#39d353'


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


def make_combined_chart(burst, dpi=200):
    """Three-panel chart: scatter + volume + spread."""

    dark = burst[burst['is_dark']].copy()
    lit = burst[~burst['is_dark']].copy()

    fig, (ax1, ax2, ax3) = plt.subplots(
        3, 1,
        figsize=(16, 14),
        gridspec_kw={'height_ratios': [4, 1.2, 1.2], 'hspace': 0.12},
        facecolor=BG,
    )

    # ══════════════════════════════════════════════════
    # Panel 1 — Raw Tick Scatter (tight_clean style)
    # ══════════════════════════════════════════════════
    ax1.set_facecolor(PANEL_BG)

    # Lit on bottom, dark on top (layering order)
    ax1.scatter(lit['ts_et'], lit['price'], s=0.6, alpha=0.45,
                c=GREEN, label=f'Lit Exchanges ({len(lit):,})',
                edgecolors='none', zorder=2)
    ax1.scatter(dark['ts_et'], dark['price'], s=0.6, alpha=0.45,
                c=RED, label=f'Dark/TRF ({len(dark):,})',
                edgecolors='none', zorder=3)

    # $33 ceiling
    ax1.axhline(y=33.0, color=ACCENT_ORANGE, linewidth=1.2,
                linestyle='--', alpha=0.7)
    ax1.text(burst['ts_et'].min() + timedelta(seconds=5), 33.35,
             '$33.00 OpEx Strike Ceiling', color=ACCENT_ORANGE,
             fontsize=9, fontstyle='italic', fontweight='bold')

    # NBBO floor
    ax1.axhline(y=20.87, color=ACCENT_BLUE, linewidth=0.8,
                linestyle=':', alpha=0.5)
    ax1.text(burst['ts_et'].min() + timedelta(seconds=5), 21.07,
             'Lit NBBO ~$20.87', color=ACCENT_BLUE,
             fontsize=8, fontstyle='italic')

    # Dislocation bracket
    ax1.annotate('', xy=(burst['ts_et'].max() - timedelta(seconds=10), 33.0),
                 xytext=(burst['ts_et'].max() - timedelta(seconds=10), 20.87),
                 arrowprops=dict(arrowstyle='<->', color='#ffa657', lw=1.5))
    ax1.text(burst['ts_et'].max() - timedelta(seconds=8), 27.0,
             '$12.13\ndislocation', color='#ffa657', fontsize=10,
             fontweight='bold', ha='left', va='center')

    ax1.set_title(
        'GME — May 17, 2024, 08:00-08:10 ET\n'
        'Two Markets Running Simultaneously',
        color='white', fontsize=14, fontweight='bold', pad=15,
    )
    ax1.set_ylabel('Trade Price ($)', color=TEXT_COLOR, fontsize=11)
    ax1.legend(loc='upper right', fontsize=10,
               facecolor='#161b22', edgecolor='#30363d',
               labelcolor='white', markerscale=4)
    ax1.tick_params(colors='#8b949e', labelsize=9)
    ax1.grid(True, alpha=0.08, color=GRID_COLOR)
    for spine in ax1.spines.values():
        spine.set_color(SPINE_COLOR)

    # Remove x labels from top panel (shared axis below)
    ax1.tick_params(axis='x', labelbottom=False)

    # ══════════════════════════════════════════════════
    # Panel 2 — Volume by Venue (per-second bars)
    # ══════════════════════════════════════════════════
    ax2.set_facecolor(PANEL_BG)

    dark['second'] = dark['ts_et'].dt.floor('1s')
    lit['second'] = lit['ts_et'].dt.floor('1s')
    dark_vol = dark.groupby('second')['size'].sum()
    lit_vol = lit.groupby('second')['size'].sum()

    bar_w = 0.000008
    ax2.bar(dark_vol.index, dark_vol.values, width=bar_w,
            color=RED, alpha=0.7, label='Dark Vol')
    ax2.bar(lit_vol.index, lit_vol.values, width=bar_w,
            color=GREEN, alpha=0.7, label='Lit Vol')

    ax2.set_ylabel('Volume', color=TEXT_COLOR, fontsize=10)
    ax2.legend(loc='upper right', fontsize=8,
               facecolor='#161b22', edgecolor='#30363d',
               labelcolor='white')
    ax2.tick_params(colors='#8b949e', labelsize=9)
    ax2.grid(True, alpha=0.08, color=GRID_COLOR)
    for spine in ax2.spines.values():
        spine.set_color(SPINE_COLOR)
    ax2.tick_params(axis='x', labelbottom=False)

    # ══════════════════════════════════════════════════
    # Panel 3 — Dark − Lit VWAP Spread (15-second bins)
    # ══════════════════════════════════════════════════
    ax3.set_facecolor(PANEL_BG)

    dark['bin15'] = dark['ts_et'].dt.floor('15s')
    lit['bin15'] = lit['ts_et'].dt.floor('15s')

    d_vwap = dark.groupby('bin15').apply(
        lambda g: (g['price'] * g['size']).sum() / g['size'].sum()
    )
    l_vwap = lit.groupby('bin15').apply(
        lambda g: (g['price'] * g['size']).sum() / g['size'].sum()
    )
    spread = (d_vwap - l_vwap).dropna()

    colors = [RED if s > 0 else GREEN for s in spread]
    ax3.bar(spread.index, spread.values, width=0.00015,
            color=colors, alpha=0.8)
    ax3.axhline(y=0, color='white', linewidth=0.5, alpha=0.3)

    # Max spread annotation
    if len(spread) > 0:
        max_idx = spread.idxmax()
        max_val = spread[max_idx]
        ax3.annotate(
            f'Max Δ: ${max_val:.2f}', xy=(max_idx, max_val),
            xytext=(max_idx + timedelta(seconds=30), max_val + 0.8),
            arrowprops=dict(arrowstyle='->', color=ACCENT_ORANGE, lw=1.5),
            color=ACCENT_ORANGE, fontsize=9, fontweight='bold',
        )

    ax3.set_ylabel('Dark − Lit ($)', color=TEXT_COLOR, fontsize=10)
    ax3.set_xlabel('Time (ET)', color=TEXT_COLOR, fontsize=11)
    ax3.tick_params(colors='#8b949e', labelsize=9)
    ax3.grid(True, alpha=0.08, color=GRID_COLOR)
    for spine in ax3.spines.values():
        spine.set_color(SPINE_COLOR)

    # ── Shared x-axis formatting ─────────────────────
    for ax in [ax1, ax2, ax3]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))
        ax.set_xlim(burst['ts_et'].min() - timedelta(seconds=5),
                    burst['ts_et'].max() + timedelta(seconds=5))

    # Source watermark
    fig.text(
        0.5, 0.005,
        'Source: Polygon.io tick-level trade data  •  '
        'Independently verifiable  •  '
        'Code: github.com/TheGameStopsNow/research',
        ha='center', fontsize=7, color='#484f58', fontstyle='italic',
    )

    out = FIG_DIR / "tape_fracture_combined.png"
    fig.savefig(out, dpi=dpi, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")
    return out


def main():
    print("Loading burst window data...")
    burst = load_burst()
    print(f"  {len(burst):,} trades in 08:00–08:10 ET\n")
    print("Generating combined chart (scatter + volume + spread)...")
    make_combined_chart(burst)
    print("\nDone.")


if __name__ == "__main__":
    main()
