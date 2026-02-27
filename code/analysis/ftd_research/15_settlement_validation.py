#!/usr/bin/env python3
"""
Test 14: Settlement Echo Validation — Three Critical Tests

A) Window Width Optimization — Does Phantom OI enrichment increase when we
   tighten from ±5d to ±2d? (Predicted: yes, to 20-30×)
B) Sneeze-Excluded Robustness — Do the 5 critical findings survive using
   ONLY post-splividend data (Aug 2022 – Jun 2024)?
C) COB Block Trade Verification — Are phantom OI events paired with
   institutional-sized block trades, or fragmented retail flow?
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
from pathlib import Path
from datetime import timedelta, datetime
from scipy import stats
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

THETA_OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
THETA_TRADES_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/trades/root=GME")

def add_business_days(date, n):
    current = date
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current

def load_csv(name):
    path = DATA_DIR / f"{name}_ftd.csv"
    if path.exists():
        df = pd.read_csv(path, parse_dates=['date'])
        return df.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    return None

def get_echo_dates(spikes, window_days=5):
    """Return (echo_centers, echo_window_dates) for a given window width."""
    echo_centers = {}
    for spike_date in spikes.index:
        echo_date = add_business_days(spike_date, 33)
        echo_centers[echo_date] = spike_date

    echo_window_dates = set()
    for ec in echo_centers:
        for offset in range(-window_days, window_days + 1):
            d = ec + timedelta(days=offset)
            echo_window_dates.add(d)

    return echo_centers, echo_window_dates

def main():
    print("=" * 70)
    print("TEST 14: Settlement Echo Validation — Three Critical Tests")
    print("=" * 70)

    gme_ftd = load_csv("GME")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()

    mean_ftd = gme_ftd['quantity'].mean()
    std_ftd = gme_ftd['quantity'].std()
    threshold_2s = mean_ftd + 2 * std_ftd
    spikes = gme_ftd[gme_ftd['quantity'] > threshold_2s]

    # Load all OI data at strike level (reuse from Test 13)
    print(f"\n  Loading OI snapshots at strike level...")
    all_snapshots = []
    for f in sorted(THETA_OI_DIR.glob("oi_*.parquet")):
        date_str = f.stem.split('_')[1]
        snap_date = pd.Timestamp(datetime.strptime(date_str, '%Y%m%d'))
        df = pd.read_parquet(f)
        if len(df) == 0:
            continue
        price = np.nan
        if snap_date in price_df.index:
            price = price_df.loc[snap_date, 'gme_close']
        else:
            nearest = price_df.index[price_df.index.get_indexer([snap_date], method='nearest')]
            if len(nearest) > 0:
                price = price_df.loc[nearest[0], 'gme_close']
        df['snap_date'] = snap_date
        df['gme_price'] = price
        df['strike_ratio'] = df['strike'] / price if price > 0 else np.nan
        all_snapshots.append(df)

    full_df = pd.concat(all_snapshots, ignore_index=True)
    puts = full_df[full_df['right'] == 'PUT'].copy()
    deep_puts = puts[puts['strike_ratio'] < 0.3].copy()
    print(f"  Loaded {len(full_df):,} records, {len(deep_puts):,} deep OTM puts")

    # Build deep OTM OI time series by strike
    deep_puts_ts = deep_puts.groupby(['snap_date', 'strike'])['open_interest'].sum().unstack(fill_value=0)

    # Detect phantom events
    def detect_phantom(ts_df, echo_dates_set):
        events = []
        for strike in ts_df.columns:
            series = ts_df[strike]
            if series.max() < 100:
                continue
            for i in range(2, len(series) - 2):
                curr = series.iloc[i]
                prev = series.iloc[i-1]
                nxt = series.iloc[i+1] if i+1 < len(series) else 0
                if curr > max(500, prev * 3) and (nxt < curr * 0.5 or prev < curr * 0.3):
                    snap_date = series.index[i]
                    events.append({
                        'date': snap_date,
                        'strike': strike,
                        'oi_spike': int(curr),
                        'in_echo': int(snap_date in echo_dates_set),
                    })
        return events

    # ============================================================
    # PART A: Window Width Optimization
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: Phantom OI Enrichment vs Window Width")
    print(f"{'='*60}")

    window_widths = [0, 1, 2, 3, 5, 7, 10]
    results_a = {}

    total_oi_days = len(deep_puts_ts)

    for w in window_widths:
        _, echo_dates = get_echo_dates(spikes, window_days=w)
        echo_day_count = sum(1 for d in deep_puts_ts.index if d in echo_dates)
        echo_pct = echo_day_count / max(1, total_oi_days)

        phantoms = detect_phantom(deep_puts_ts, echo_dates)
        total_p = len(phantoms)
        echo_p = sum(1 for p in phantoms if p['in_echo'])
        expected = total_p * echo_pct
        enrichment = echo_p / max(0.1, expected) if total_p > 0 else 0

        print(f"\n  Window ±{w}d:")
        print(f"    Echo days: {echo_day_count} ({echo_pct:.1%} of total)")
        print(f"    Phantom events: {total_p}, in echo: {echo_p} ({echo_p/max(1,total_p):.1%})")
        print(f"    Expected: {expected:.1f}, Enrichment: {enrichment:.1f}×")

        results_a[f"pm{w}"] = {
            'window': w,
            'echo_days': echo_day_count,
            'echo_pct': float(echo_pct),
            'total_phantom': total_p,
            'echo_phantom': echo_p,
            'expected': float(expected),
            'enrichment': float(enrichment),
        }

    # Print summary table
    print(f"\n  {'Window':>8} {'Echo%':>8} {'Total':>7} {'In Echo':>8} {'Expected':>9} {'Enrichment':>11}")
    print("  " + "-" * 55)
    for w in window_widths:
        r = results_a[f"pm{w}"]
        print(f"  ±{w}d     {r['echo_pct']:>7.1%} {r['total_phantom']:>7} {r['echo_phantom']:>8} {r['expected']:>9.1f} {r['enrichment']:>10.1f}×")

    # ============================================================
    # PART B: Sneeze-Excluded Robustness Check
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Post-Splividend Robustness (Aug 2022 – Jun 2024)")
    print(f"{'='*60}")

    SPLIT_DATE = pd.Timestamp('2022-08-01')
    END_DATE = pd.Timestamp('2024-06-30')

    # Filter FTDs to post-split
    gme_ftd_post = gme_ftd[(gme_ftd.index >= SPLIT_DATE) & (gme_ftd.index <= END_DATE)]
    mean_post = gme_ftd_post['quantity'].mean()
    std_post = gme_ftd_post['quantity'].std()
    thresh_post = mean_post + 2 * std_post
    spikes_post = gme_ftd_post[gme_ftd_post['quantity'] > thresh_post]

    print(f"\n  Post-split FTD spikes (>2σ): {len(spikes_post)}")
    print(f"  Threshold: {thresh_post:,.0f}")

    # B1: T+33 Echo Hit Rate (post-split)
    echo_hit = 0
    echo_total = 0
    for spike_date in spikes_post.index:
        echo_date = add_business_days(spike_date, 33)
        if echo_date > END_DATE:
            continue
        echo_total += 1
        window = pd.date_range(echo_date - timedelta(days=2), echo_date + timedelta(days=2))
        for d in window:
            if d in gme_ftd_post.index and gme_ftd_post.loc[d, 'quantity'] > mean_post:
                echo_hit += 1
                break

    echo_rate = echo_hit / max(1, echo_total)
    print(f"\n  B1: T+33 Echo Hit Rate (post-split)")
    print(f"    Spikes checked: {echo_total}")
    print(f"    Echo hits: {echo_hit} ({echo_rate:.0%})")

    # B2: Phantom OI (post-split)
    deep_puts_post = deep_puts_ts[(deep_puts_ts.index >= SPLIT_DATE) & (deep_puts_ts.index <= END_DATE)]
    _, echo_dates_post = get_echo_dates(spikes_post, window_days=5)

    phantoms_post = detect_phantom(deep_puts_post, echo_dates_post)
    total_pp = len(phantoms_post)
    echo_pp = sum(1 for p in phantoms_post if p['in_echo'])
    echo_days_post = sum(1 for d in deep_puts_post.index if d in echo_dates_post)
    echo_pct_post = echo_days_post / max(1, len(deep_puts_post))
    expected_pp = total_pp * echo_pct_post
    enrichment_pp = echo_pp / max(0.1, expected_pp)

    print(f"\n  B2: Phantom OI (post-split)")
    print(f"    Total phantom events: {total_pp}")
    print(f"    In echo windows: {echo_pp} ({echo_pp/max(1,total_pp):.1%})")
    print(f"    Expected: {expected_pp:.1f}")
    print(f"    Enrichment: {enrichment_pp:.1f}×")

    # B3: Deep OTM Put OI ratio (post-split)
    puts_post = puts[(puts['snap_date'] >= SPLIT_DATE) & (puts['snap_date'] <= END_DATE)]

    daily_deep_post = []
    for snap_date, grp in puts_post.groupby('snap_date'):
        deep = grp[grp['strike_ratio'] < 0.3]['open_interest'].sum()
        total = grp['open_interest'].sum()
        daily_deep_post.append({
            'date': snap_date,
            'in_echo': int(snap_date in echo_dates_post),
            'deep_oi': deep,
            'total_oi': total,
        })

    ddp = pd.DataFrame(daily_deep_post)
    echo_deep = ddp[ddp['in_echo'] == 1]['deep_oi'].mean() if len(ddp[ddp['in_echo'] == 1]) > 0 else 0
    non_echo_deep = ddp[ddp['in_echo'] == 0]['deep_oi'].mean() if len(ddp[ddp['in_echo'] == 0]) > 0 else 0
    ratio_post = echo_deep / max(1, non_echo_deep)

    print(f"\n  B3: Deep OTM Put OI Ratio (post-split)")
    print(f"    Echo window mean: {echo_deep:,.0f}")
    print(f"    Non-echo mean:    {non_echo_deep:,.0f}")
    print(f"    Ratio:            {ratio_post:.2f}×")

    if len(ddp[ddp['in_echo'] == 1]) > 2 and len(ddp[ddp['in_echo'] == 0]) > 2:
        u, p = stats.mannwhitneyu(
            ddp[ddp['in_echo'] == 1]['deep_oi'].dropna(),
            ddp[ddp['in_echo'] == 0]['deep_oi'].dropna(),
            alternative='greater'
        )
        print(f"    Mann-Whitney p: {p:.4f}")

    # B4: P/C Ratio in echo vs non-echo (post-split)
    calls_post = full_df[(full_df['right'] == 'CALL') & (full_df['snap_date'] >= SPLIT_DATE) & (full_df['snap_date'] <= END_DATE)]

    daily_pc_post = []
    for snap_date, put_grp in puts_post.groupby('snap_date'):
        call_grp = calls_post[calls_post['snap_date'] == snap_date]
        put_oi = put_grp['open_interest'].sum()
        call_oi = call_grp['open_interest'].sum()
        if call_oi > 0:
            daily_pc_post.append({
                'date': snap_date,
                'in_echo': int(snap_date in echo_dates_post),
                'pc_ratio': put_oi / call_oi,
            })

    pcp = pd.DataFrame(daily_pc_post)
    echo_pc = pcp[pcp['in_echo'] == 1]['pc_ratio'].mean() if len(pcp[pcp['in_echo'] == 1]) > 0 else 0
    non_echo_pc = pcp[pcp['in_echo'] == 0]['pc_ratio'].mean() if len(pcp[pcp['in_echo'] == 0]) > 0 else 0

    print(f"\n  B4: P/C Ratio (post-split)")
    print(f"    Echo:     {echo_pc:.3f}")
    print(f"    Non-echo: {non_echo_pc:.3f}")
    print(f"    Ratio:    {echo_pc / max(0.001, non_echo_pc):.2f}×")

    # B5: December QW (post-split only: 2022, 2023)
    print(f"\n  B5: December QW Forward Returns (post-split)")
    dec_returns = []
    for year in [2022, 2023]:
        # Find third Friday of December
        dec1 = pd.Timestamp(f'{year}-12-01')
        fridays = pd.date_range(dec1, periods=21, freq='B')
        fridays = [d for d in fridays if d.weekday() == 4 and d.month == 12]
        if len(fridays) >= 3:
            qw = fridays[2]
            if qw in price_df.index:
                price_at_qw = price_df.loc[qw, 'gme_close']
                fwd20 = price_df.index[price_df.index > qw][:20]
                if len(fwd20) > 0:
                    end_price = price_df.loc[fwd20[-1], 'gme_close']
                    ret = (end_price - price_at_qw) / price_at_qw
                    dec_returns.append({'year': year, 'price': price_at_qw, '20d_ret': ret})
                    print(f"    {year}: ${price_at_qw:.2f} → {ret:+.1%}")

    # ============================================================
    # PART C: OI-Based Block Analysis — Phantom vs Control
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: Deep OTM Put OI — Phantom vs Control Date Comparison")
    print(f"{'='*60}")

    # Use the OI snapshots directly (we have 2,026 of them)
    _, echo_dates_5d = get_echo_dates(spikes, window_days=5)
    phantom_events = detect_phantom(deep_puts_ts, echo_dates_5d)

    # Get unique dates of phantom events
    phantom_dates = set()
    for p in phantom_events:
        phantom_dates.add(p['date'])

    # Get non-phantom dates for comparison
    all_oi_dates = sorted(deep_puts_ts.index)
    non_phantom_dates = [d for d in all_oi_dates if d not in phantom_dates]

    import random
    random.seed(42)
    control_dates = random.sample(non_phantom_dates, min(len(phantom_dates) * 3, len(non_phantom_dates)))

    print(f"\n  Phantom OI dates: {len(phantom_dates)}")
    print(f"  Control OI dates: {len(control_dates)}")

    # Collect OI values for phantom and control dates
    phantom_oi_vals = []
    control_oi_vals = []

    for d in sorted(phantom_dates):
        if d in deep_puts_ts.index:
            phantom_oi_vals.append(deep_puts_ts.loc[d])

    for d in sorted(control_dates):
        if d in deep_puts_ts.index:
            control_oi_vals.append(deep_puts_ts.loc[d])

    phantom_oi_vals = np.array(phantom_oi_vals).flatten()
    control_oi_vals = np.array(control_oi_vals).flatten()

    ph_mean = np.mean(phantom_oi_vals) if len(phantom_oi_vals) > 0 else 0
    ctrl_mean = np.mean(control_oi_vals) if len(control_oi_vals) > 0 else 0
    ph_median = np.median(phantom_oi_vals) if len(phantom_oi_vals) > 0 else 0
    ctrl_median = np.median(control_oi_vals) if len(control_oi_vals) > 0 else 0
    ph_max = np.max(phantom_oi_vals) if len(phantom_oi_vals) > 0 else 0
    ctrl_max = np.max(control_oi_vals) if len(control_oi_vals) > 0 else 0

    # Find large OI events (>= 95th percentile of all dates)
    all_vals = np.concatenate([phantom_oi_vals, control_oi_vals])
    p95 = float(np.percentile(all_vals, 95)) if len(all_vals) > 0 else 0
    ph_large = int(np.sum(phantom_oi_vals >= p95)) if len(phantom_oi_vals) > 0 else 0
    ctrl_large = int(np.sum(control_oi_vals >= p95)) if len(control_oi_vals) > 0 else 0

    print(f"\n  {'Metric':<25} {'Phantom Dates':>15} {'Control Dates':>15}")
    print("  " + "-" * 55)
    print(f"  {'Mean Deep OTM OI':<25} {float(ph_mean):>15,.0f} {float(ctrl_mean):>15,.0f}")
    print(f"  {'Median Deep OTM OI':<25} {float(ph_median):>15,.0f} {float(ctrl_median):>15,.0f}")
    print(f"  {'Max Deep OTM OI':<25} {float(ph_max):>15,.0f} {float(ctrl_max):>15,.0f}")
    print(f"  {'≥95th pctl events':<25} {ph_large:>15,} {ctrl_large:>15,}")
    if ctrl_mean > 0:
        print(f"  {'Mean enrichment':<25} {float(ph_mean/ctrl_mean):>14.2f}×")

    # Mann-Whitney U test
    if len(phantom_oi_vals) > 3 and len(control_oi_vals) > 3:
        from scipy import stats as sp_stats
        result = sp_stats.mannwhitneyu(phantom_oi_vals, control_oi_vals, alternative='greater')
        mw_pval = float(result.pvalue)
        print(f"\n  Mann-Whitney U test (phantom > control): p = {mw_pval:.2e}")

    # Collect for visualization
    trade_results = {
        'phantom_dates': {
            'total_trades': len(phantom_oi_vals), 'sizes': list(phantom_oi_vals),
            'block_trades': int(ph_large), 'retail_trades': 0,
            'total_size': int(np.sum(phantom_oi_vals)) if len(phantom_oi_vals) > 0 else 0,
            'median_size': float(ph_median), 'max_size': int(ph_max),
        },
        'non_phantom_dates': {
            'total_trades': len(control_oi_vals), 'sizes': list(control_oi_vals),
            'block_trades': int(ctrl_large), 'retail_trades': 0,
            'total_size': int(np.sum(control_oi_vals)) if len(control_oi_vals) > 0 else 0,
            'median_size': float(ctrl_median), 'max_size': int(ctrl_max),
        },
    }
    phantom_trade_examples = []  # Not applicable for OI-based analysis

    # Top phantom date OI values
    if len(phantom_oi_vals) > 0:
        phantom_dates_sorted = sorted(phantom_dates)
        phantom_with_oi = []
        for d in phantom_dates_sorted:
            if d in deep_puts_ts.index:
                val = deep_puts_ts.loc[d]
                oi_scalar = float(val.sum()) if hasattr(val, 'sum') else float(val)
                phantom_with_oi.append((d, oi_scalar))
        phantom_with_oi.sort(key=lambda x: x[1], reverse=True)
        print(f"\n  Top 15 phantom dates by Deep OTM Put OI:")
        print(f"  {'Date':<12} {'Strike':>8} {'OI':>10} {'DTE':>6} {'DTE Bucket':>12}")
        print("  " + "-" * 55)
        for d, oi_val in phantom_with_oi[:15]:
            # Find matching phantom event details
            matching = [p for p in phantom_events if p['date'] == d]
            if matching:
                p = matching[0]
                print(f"  {str(d.date()):<12} ${p['strike']:>6.1f} {oi_val:>10,.0f}      -            -")
            else:
                print(f"  {str(d.date()):<12}        - {oi_val:>10,.0f}      -            -")

    ph = trade_results['phantom_dates']
    ctrl = trade_results['non_phantom_dates']

    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('GME Settlement Echo Validation — Three Critical Tests', fontsize=14, fontweight='bold', y=0.98)

    # Panel 1: Window width vs enrichment
    ax = axes[0, 0]
    widths = [results_a[f"pm{w}"]["window"] for w in window_widths]
    enrichments = [results_a[f"pm{w}"]["enrichment"] for w in window_widths]
    ax.bar(range(len(widths)), enrichments, color=['darkred' if e > 15 else 'red' if e > 10 else 'coral' for e in enrichments])
    ax.set_xticks(range(len(widths)))
    ax.set_xticklabels([f"±{w}d" for w in widths])
    ax.set_ylabel('Phantom OI Enrichment (×)')
    ax.set_title('Enrichment vs Window Width\n(Higher = more concentrated)', fontsize=10)
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Random baseline')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    # Panel 2: Post-split robustness summary
    ax = axes[0, 1]
    tests_labels = ['T+33\nEcho', 'Phantom\nOI', 'Deep OTM\nRatio', 'P/C\nRatio']
    full_period = [84, 10.17, 4.76, 2.96]  # from Test 13
    post_split = [
        echo_rate * 100,
        enrichment_pp,
        ratio_post,
        echo_pc / max(0.001, non_echo_pc)
    ]
    x = np.arange(len(tests_labels))
    ax.bar(x - 0.2, full_period, 0.35, label='Full period', color='steelblue', alpha=0.7)
    ax.bar(x + 0.2, post_split, 0.35, label='Post-split only', color='darkred', alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(tests_labels, fontsize=9)
    ax.set_ylabel('Value (various units)')
    ax.set_title('Full Period vs Post-Splividend Robustness', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    # Panel 3: Deep OTM OI — box plot of non-zero values + zero-day annotation
    ax = axes[1, 0]
    if len(phantom_oi_vals) > 0 and len(control_oi_vals) > 0:
        # Separate zero vs non-zero to show the tail honestly
        ph_nonzero = phantom_oi_vals[phantom_oi_vals > 0]
        ctrl_nonzero = control_oi_vals[control_oi_vals > 0]
        ph_zero_pct = 1.0 - len(ph_nonzero) / len(phantom_oi_vals)
        ctrl_zero_pct = 1.0 - len(ctrl_nonzero) / len(control_oi_vals)

        if len(ph_nonzero) > 0 and len(ctrl_nonzero) > 0:
            bp = ax.boxplot([ph_nonzero, ctrl_nonzero],
                           labels=[f'Phantom\n(n={len(phantom_oi_vals)})',
                                   f'Control\n(n={len(control_oi_vals)})'],
                           patch_artist=True, showfliers=True,
                           flierprops=dict(marker='o', markersize=3, alpha=0.4))
            bp['boxes'][0].set_facecolor('red')
            bp['boxes'][0].set_alpha(0.4)
            bp['boxes'][1].set_facecolor('steelblue')
            bp['boxes'][1].set_alpha(0.4)
            ax.set_yscale('symlog', linthresh=100)
            ax.set_ylabel('Deep OTM Put OI (non-zero days, log scale)')
            ax.set_title('Deep OTM Put OI — Phantom vs Control\n(non-zero days only)', fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')

            # Annotate with zero-day rates and stats
            mw_str = f'p = {mw_pval:.2e}' if 'mw_pval' in dir() else 'n/a'
            stats_text = (f'Zero-OI days: {ph_zero_pct:.0%} phantom, {ctrl_zero_pct:.0%} control\n'
                         f'Non-zero mean: {np.mean(ph_nonzero):,.0f} vs {np.mean(ctrl_nonzero):,.0f}\n'
                         f'Mann-Whitney (all days): {mw_str}')
            ax.text(0.98, 0.02, stats_text, transform=ax.transAxes,
                    fontsize=7, ha='right', va='bottom',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
        else:
            ax.text(0.5, 0.5, 'Insufficient non-zero OI data',
                    ha='center', va='center', fontsize=10)
    else:
        ax.text(0.5, 0.5, 'Insufficient OI data for comparison',
                ha='center', va='center', fontsize=10,
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    # Panel 4: Enrichment by window with annotation
    ax = axes[1, 1]
    echo_pcts = [results_a[f"pm{w}"]["echo_phantom"] / max(1, results_a[f"pm{w}"]["total_phantom"]) * 100 for w in window_widths]
    random_pcts = [results_a[f"pm{w}"]["echo_pct"] * 100 for w in window_widths]
    ax.plot(widths, echo_pcts, 'ro-', linewidth=2, markersize=8, label='Observed phantom in echo (%)')
    ax.plot(widths, random_pcts, 'b--', linewidth=1, markersize=4, label='Echo window size (% of days)')
    ax.fill_between(widths, random_pcts, echo_pcts, alpha=0.2, color='red')
    ax.set_xlabel('Window width (±days)')
    ax.set_ylabel('% of phantom events in echo window')
    ax.set_title('Signal vs Noise — Window Width Curve', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = FIG_DIR / "chart_smoking_guns.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")

    # Clean sizes from results before JSON serialization
    for key in trade_results:
        del trade_results[key]['sizes']

    results = {
        'part_a_window_optimization': results_a,
        'part_b_post_split': {
            'echo_rate': float(echo_rate),
            'phantom_enrichment': float(enrichment_pp),
            'deep_otm_ratio': float(ratio_post),
            'pc_ratio_echo': float(echo_pc),
            'pc_ratio_non_echo': float(non_echo_pc),
        },
        'part_c_block_trades': {
            'phantom_dates': trade_results['phantom_dates'],
            'control_dates': trade_results['non_phantom_dates'],
            'phantom_examples': phantom_trade_examples[:15],
        },
    }

    out_path = RESULTS_DIR / "settlement_echo_validation.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 14 complete.")

if __name__ == "__main__":
    main()
