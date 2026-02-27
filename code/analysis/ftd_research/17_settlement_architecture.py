#!/usr/bin/env python3
"""
Test 16: Settlement Architecture — Survival Funnel & Deep Forensics

A) Intermediate Echo Survival Funnel — Phantom OI enrichment at
   T+9, T+15, T+21, T+27, T+33 (tests 5-reset chain vs single-step)
B) Post-Split Volume Ratio — Deep OTM trade volume pre/post to
   diagnose internalization
C) Jubilee vs Valve Transfer — FTD slope analysis post-splividend
D) Millisecond ISO-Equity Alignment — Cross-reference options ISOs
   with equity dark pool prints on phantom dates
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
THETA_STOCK_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/stock_trades/symbol=GME")

SPLIT_DATE = pd.Timestamp('2022-07-22')

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

def get_echo_dates_at_offset(spikes, offset_days):
    """Get echo dates at a specific T+N offset."""
    echo_centers = {}
    for spike_date in spikes.index:
        echo_date = add_business_days(spike_date, offset_days)
        echo_centers[echo_date] = spike_date
    return echo_centers

def main():
    print("=" * 70)
    print("TEST 16: Settlement Architecture — Survival Funnel & Deep Forensics")
    print("=" * 70)

    gme_ftd = load_csv("GME")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()

    mean_ftd = gme_ftd['quantity'].mean()
    std_ftd = gme_ftd['quantity'].std()
    threshold_2s = mean_ftd + 2 * std_ftd
    spikes = gme_ftd[gme_ftd['quantity'] > threshold_2s]

    # Load OI data
    print(f"\n  Loading OI snapshots...")
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
    deep_puts_ts = deep_puts.groupby(['snap_date', 'strike'])['open_interest'].sum().unstack(fill_value=0)

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
    # PART A: Intermediate Echo Survival Funnel
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: Survival Funnel — Phantom OI at T+9, T+15, T+21, T+27, T+33")
    print(f"{'='*60}")

    offsets = [3, 6, 9, 13, 15, 18, 21, 24, 27, 30, 33, 35, 40]
    results_a = {}
    total_oi_days = len(deep_puts_ts)

    for offset in offsets:
        echo_centers = get_echo_dates_at_offset(spikes, offset)

        # Use ±0d window (exact date) for precision
        exact_dates = set(echo_centers.keys())
        # Also ±2d for comparison
        window_dates = set()
        for ec in echo_centers:
            for o in range(-2, 3):
                window_dates.add(ec + timedelta(days=o))

        exact_day_count = sum(1 for d in deep_puts_ts.index if d in exact_dates)
        exact_pct = exact_day_count / max(1, total_oi_days)

        w2_day_count = sum(1 for d in deep_puts_ts.index if d in window_dates)
        w2_pct = w2_day_count / max(1, total_oi_days)

        phantoms_exact = detect_phantom(deep_puts_ts, exact_dates)
        phantoms_w2 = detect_phantom(deep_puts_ts, window_dates)

        total_p = len(phantoms_exact)  # always same
        exact_in = sum(1 for p in phantoms_exact if p['in_echo'])
        w2_in = sum(1 for p in phantoms_w2 if p['in_echo'])

        exact_enrichment = (exact_in / max(1, total_p)) / max(0.001, exact_pct) if total_p > 0 else 0
        w2_enrichment = (w2_in / max(1, total_p)) / max(0.001, w2_pct) if total_p > 0 else 0

        results_a[f"T+{offset}"] = {
            'offset': offset,
            'exact_in': exact_in,
            'exact_enrichment': float(exact_enrichment),
            'w2_in': w2_in,
            'w2_enrichment': float(w2_enrichment),
        }

    print(f"\n  {'Offset':>8} {'±0d In':>8} {'±0d Enrich':>12} {'±2d In':>8} {'±2d Enrich':>12}")
    print("  " + "-" * 55)
    for offset in offsets:
        r = results_a[f"T+{offset}"]
        marker = " ⭐" if r['exact_enrichment'] > 5 else ""
        print(f"  T+{offset:<5} {r['exact_in']:>8} {r['exact_enrichment']:>11.1f}× {r['w2_in']:>8} {r['w2_enrichment']:>11.1f}×{marker}")

    # ============================================================
    # PART B: Post-Split Deep OTM Volume Ratio
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Pre vs Post Split Deep OTM Trade Volume (Internalization)")
    print(f"{'='*60}")

    # Load options trade data for pre and post split
    pre_split_volume = {'total_trades': 0, 'total_size': 0, 'dates_checked': 0, 'dates_with_deep': 0}
    post_split_volume = {'total_trades': 0, 'total_size': 0, 'dates_checked': 0, 'dates_with_deep': 0}

    # Get echo dates for both periods
    echo_33 = get_echo_dates_at_offset(spikes, 33)
    echo_dates_all = set()
    for ec in echo_33:
        for o in range(-5, 6):
            echo_dates_all.add(ec + timedelta(days=o))

    # Sample dates from both periods
    import random
    random.seed(42)

    # Get all available trade dates
    trade_dirs = sorted(THETA_TRADES_DIR.glob("date=*"))
    pre_dirs = [d for d in trade_dirs if pd.Timestamp(d.name.split('=')[1]) < SPLIT_DATE]
    post_dirs = [d for d in trade_dirs if pd.Timestamp(d.name.split('=')[1]) >= SPLIT_DATE]

    print(f"\n  Pre-split trade dates: {len(pre_dirs)}")
    print(f"  Post-split trade dates: {len(post_dirs)}")

    # Process pre-split echo dates
    pre_echo_dirs = [d for d in pre_dirs if pd.Timestamp(d.name.split('=')[1]) in echo_dates_all]
    post_echo_dirs = [d for d in post_dirs if pd.Timestamp(d.name.split('=')[1]) in echo_dates_all]

    print(f"  Pre-split echo dates with trades: {len(pre_echo_dirs)}")
    print(f"  Post-split echo dates with trades: {len(post_echo_dirs)}")

    for d in pre_echo_dirs[:50]:
        try:
            snap_date = pd.Timestamp(d.name.split('=')[1])
            tdf = pd.read_parquet(d / "part-0.parquet")
            price = price_df.loc[snap_date, 'gme_close'] if snap_date in price_df.index else np.nan
            if np.isnan(price):
                continue

            deep = tdf[(tdf['right'] == 'P') & (tdf['strike'] < price * 0.3)]
            pre_split_volume['dates_checked'] += 1
            if len(deep) > 0:
                pre_split_volume['total_trades'] += len(deep)
                pre_split_volume['total_size'] += deep['size'].sum()
                pre_split_volume['dates_with_deep'] += 1
        except Exception:
            continue

    for d in post_echo_dirs[:50]:
        try:
            snap_date = pd.Timestamp(d.name.split('=')[1])
            tdf = pd.read_parquet(d / "part-0.parquet")
            price = price_df.loc[snap_date, 'gme_close'] if snap_date in price_df.index else np.nan
            if np.isnan(price):
                continue

            deep = tdf[(tdf['right'] == 'P') & (tdf['strike'] < price * 0.3)]
            post_split_volume['dates_checked'] += 1
            if len(deep) > 0:
                post_split_volume['total_trades'] += len(deep)
                post_split_volume['total_size'] += deep['size'].sum()
                post_split_volume['dates_with_deep'] += 1
        except Exception:
            continue

    pre_avg_trades = pre_split_volume['total_trades'] / max(1, pre_split_volume['dates_checked'])
    post_avg_trades = post_split_volume['total_trades'] / max(1, post_split_volume['dates_checked'])
    pre_avg_size = pre_split_volume['total_size'] / max(1, pre_split_volume['dates_checked'])
    post_avg_size = post_split_volume['total_size'] / max(1, post_split_volume['dates_checked'])

    print(f"\n  {'Metric':<25} {'Pre-Split':>12} {'Post-Split':>12} {'Ratio':>8}")
    print("  " + "-" * 60)
    print(f"  {'Dates checked':<25} {pre_split_volume['dates_checked']:>12} {post_split_volume['dates_checked']:>12}")
    print(f"  {'Dates with deep OTM':<25} {pre_split_volume['dates_with_deep']:>12} {post_split_volume['dates_with_deep']:>12}")
    print(f"  {'Total trades':<25} {pre_split_volume['total_trades']:>12,} {post_split_volume['total_trades']:>12,}")
    print(f"  {'Avg trades/day':<25} {pre_avg_trades:>12,.0f} {post_avg_trades:>12,.0f} {post_avg_trades/max(1,pre_avg_trades):>7.2f}×")
    print(f"  {'Total contracts':<25} {pre_split_volume['total_size']:>12,} {post_split_volume['total_size']:>12,}")
    print(f"  {'Avg contracts/day':<25} {pre_avg_size:>12,.0f} {post_avg_size:>12,.0f} {post_avg_size/max(1,pre_avg_size):>7.2f}×")

    # Diagnosis
    # If valve fully open post-split: ratio should be ~4× (need 4× contracts for same notional)
    # If fully internalized: ratio should be <1×
    volume_ratio = post_avg_size / max(1, pre_avg_size)
    print(f"\n  Settlement Diagnostic:")
    print(f"    Ratio = {volume_ratio:.2f}×")
    if volume_ratio > 3:
        print(f"    → Options valve FULLY OPEN (expected 4× for same notional)")
    elif volume_ratio > 1:
        print(f"    → PARTIAL internalization ({(1 - volume_ratio/4)*100:.0f}% internalized)")
    else:
        print(f"    → Options valve CLOSED — obligation internalized")

    # ============================================================
    # PART C: Jubilee vs Valve Transfer — FTD Slope Post-Split
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: Jubilee vs Valve Transfer — FTD Slope Analysis")
    print(f"{'='*60}")

    post_ftd = gme_ftd[gme_ftd.index >= SPLIT_DATE].copy()
    post_ftd['days_since_split'] = (post_ftd.index - SPLIT_DATE).days

    # Monthly rolling mean
    post_monthly = post_ftd.resample('ME')['quantity'].mean()

    # First 6 months
    first_6m = post_ftd[post_ftd['days_since_split'] <= 180]
    first_6m_mean = first_6m['quantity'].mean()
    first_6m_std = first_6m['quantity'].std()

    # Check for linear trend
    x = post_ftd['days_since_split'].values
    y = post_ftd['quantity'].values
    mask = ~np.isnan(y)
    slope, intercept, r_value, p_value, std_err = stats.linregress(x[mask], y[mask])

    print(f"\n  Post-splividend FTD analysis:")
    print(f"    Total days: {len(post_ftd)}")
    print(f"    Mean FTD: {post_ftd['quantity'].mean():,.0f}")
    print(f"    First 6 months mean: {first_6m_mean:,.0f}")

    print(f"\n  Linear trend:")
    print(f"    Slope: {slope:,.1f} FTDs/day")
    print(f"    R²: {r_value**2:.4f}")
    print(f"    p-value: {p_value:.4f}")

    # Check if first month was near zero (Jubilee signature)
    first_month = post_ftd[post_ftd['days_since_split'] <= 30]
    first_month_mean = first_month['quantity'].mean() if len(first_month) > 0 else 0

    print(f"\n  First month post-split: {first_month_mean:,.0f}")
    print(f"  Pre-split mean: {gme_ftd[gme_ftd.index < SPLIT_DATE]['quantity'].mean():,.0f}")

    if first_month_mean < mean_ftd * 0.1:
        print(f"\n  → JUBILEE SIGNATURE: FTDs near zero post-split")
    elif slope > 100:
        print(f"\n  → RE-ACCUMULATION: Positive slope ({slope:,.0f}/day)")
    else:
        print(f"\n  → VALVE TRANSFER: Flat noise floor, cyclic volatility")

    # Check for T+33 echo persistence in first 6 months immediately
    first_6m_spikes = first_6m[first_6m['quantity'] > first_6m_mean + 2 * first_6m_std]
    if len(first_6m_spikes) > 0:
        echo_hits_6m = 0
        echo_total_6m = 0
        for spike_date in first_6m_spikes.index:
            echo_date = add_business_days(spike_date, 33)
            echo_total_6m += 1
            window = pd.date_range(echo_date - timedelta(days=3), echo_date + timedelta(days=3))
            for d in window:
                if d in gme_ftd.index and gme_ftd.loc[d, 'quantity'] > first_6m_mean:
                    echo_hits_6m += 1
                    break

        print(f"\n  First 6 months T+33 echo rate: {echo_hits_6m}/{echo_total_6m} = {echo_hits_6m/max(1,echo_total_6m):.0%}")
        if echo_hits_6m / max(1, echo_total_6m) > 0.5:
            print(f"  → T+33 cycle ACTIVE immediately after split — NOT a jubilee")

    # ============================================================
    # PART D: Millisecond ISO-Equity Cross-Reference
    # ============================================================
    print(f"\n{'='*60}")
    print("PART D: ISO-Equity Millisecond Alignment on Phantom Dates")
    print(f"{'='*60}")

    # Find our top phantom dates and check for equity-options alignment
    echo_33_dates = set(echo_33.keys())
    echo_33_window = set()
    for ec in echo_33_dates:
        for o in range(-2, 3):
            echo_33_window.add(ec + timedelta(days=o))

    # Get phantom dates from Part A
    phantom_events = detect_phantom(deep_puts_ts, echo_33_window)
    phantom_dates = sorted(set(p['date'] for p in phantom_events if p['in_echo']))

    print(f"\n  Phantom dates in echo windows: {len(phantom_dates)}")
    print(f"  Checking for paired equity prints...")

    alignment_results = []
    dates_checked = 0

    for snap_date in phantom_dates[:20]:  # Check up to 20 dates
        date_str = snap_date.strftime('%Y%m%d')

        # Load options trades
        opt_dir = THETA_TRADES_DIR / f"date={date_str}"
        if not opt_dir.exists():
            continue

        # Load equity trades
        eq_dir = THETA_STOCK_DIR / f"date={date_str}"
        if not eq_dir.exists():
            continue

        try:
            opt_trades = pd.read_parquet(opt_dir / "part-0.parquet")
            eq_trades = pd.read_parquet(eq_dir / "part-0.parquet")
        except Exception:
            continue

        dates_checked += 1

        price = price_df.loc[snap_date, 'gme_close'] if snap_date in price_df.index else np.nan
        if np.isnan(price):
            continue

        # Find deep OTM put ISOs (condition 18) with size >= 100
        deep_isos = opt_trades[
            (opt_trades['right'] == 'P') &
            (opt_trades['strike'] < price * 0.3) &
            (opt_trades['condition'] == 18) &
            (opt_trades['size'] >= 100)
        ]

        if len(deep_isos) == 0:
            continue

        # For each ISO, look for equity prints within 1 second
        # Convert timestamps to comparable format
        for _, iso in deep_isos.iterrows():
            iso_ts = iso['timestamp']
            expected_shares = int(iso['size'] * 100)

            # Parse timestamps — ThetaData uses milliseconds from midnight
            try:
                iso_ms = int(iso_ts) if not isinstance(iso_ts, str) else int(iso_ts)
            except (ValueError, TypeError):
                continue

            # Look for equity trades within ±1000ms window
            # Also check for total shares near expected_shares
            try:
                eq_trades_ms = eq_trades.copy()
                eq_trades_ms['ts_int'] = pd.to_numeric(eq_trades_ms['ms_of_day'], errors='coerce')
                if 'ms_of_day' not in eq_trades_ms.columns:
                    # Try other timestamp columns
                    if 'timestamp' in eq_trades_ms.columns:
                        eq_trades_ms['ts_int'] = pd.to_numeric(eq_trades_ms['timestamp'], errors='coerce')
                    else:
                        continue

                nearby = eq_trades_ms[
                    (eq_trades_ms['ts_int'] >= iso_ms - 1000) &
                    (eq_trades_ms['ts_int'] <= iso_ms + 1000)
                ]

                if len(nearby) > 0:
                    total_shares = nearby['size'].sum()
                    max_single = nearby['size'].max()

                    alignment_results.append({
                        'date': str(snap_date.date()),
                        'option_strike': float(iso['strike']),
                        'option_size': int(iso['size']),
                        'expected_shares': expected_shares,
                        'nearby_equity_trades': len(nearby),
                        'nearby_total_shares': int(total_shares),
                        'max_single_trade': int(max_single),
                        'match_ratio': total_shares / max(1, expected_shares),
                    })
            except Exception as e:
                continue

    if alignment_results:
        print(f"\n  Dates with ISO-equity alignment data: {dates_checked}")
        print(f"  ISO events with nearby equity prints: {len(alignment_results)}")
        print(f"\n  {'Date':<12} {'Opt Strike':>10} {'Opt Lots':>9} {'Exp Shares':>11} {'Eq Trades':>10} {'Eq Shares':>10} {'Match':>7}")
        print("  " + "-" * 75)
        for r in sorted(alignment_results, key=lambda x: x['option_size'], reverse=True)[:15]:
            print(f"  {r['date']:<12} ${r['option_strike']:>8.1f} {r['option_size']:>9,} {r['expected_shares']:>11,} {r['nearby_equity_trades']:>10,} {r['nearby_total_shares']:>10,} {r['match_ratio']:>6.1f}×")
    else:
        print(f"\n  Dates checked: {dates_checked}")
        # Try without ms alignment — check column names
        if dates_checked > 0:
            print(f"  No millisecond alignment found — checking equity trade structure...")
            test_dir = THETA_STOCK_DIR / f"date={phantom_dates[0].strftime('%Y%m%d')}"
            if test_dir.exists():
                try:
                    test_eq = pd.read_parquet(test_dir / "part-0.parquet")
                    print(f"  Equity columns: {test_eq.columns.tolist()}")
                    print(f"  Equity dtypes: {dict(test_eq.dtypes)}")
                    print(f"  Sample row: {test_eq.iloc[0].to_dict()}")
                except Exception as e:
                    print(f"  Error: {e}")

    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Settlement Architecture — Survival Funnel & Deep Forensics', fontsize=14, fontweight='bold', y=1.02)

    # Panel 1: Survival Funnel
    ax = axes[0, 0]
    funnel_offsets = [o for o in offsets]
    exact_enrich = [results_a[f"T+{o}"]['exact_enrichment'] for o in offsets]
    w2_enrich = [results_a[f"T+{o}"]['w2_enrichment'] for o in offsets]

    ax.plot(funnel_offsets, exact_enrich, 'ro-', linewidth=2, markersize=8, label='±0d enrichment')
    ax.plot(funnel_offsets, w2_enrich, 'b^--', linewidth=1, markersize=6, label='±2d enrichment', alpha=0.7)
    ax.axhline(y=1.0, color='gray', linestyle='--', alpha=0.5, label='Random baseline')
    ax.set_xlabel('Settlement Offset (business days)')
    ax.set_ylabel('Phantom OI Enrichment (×)')
    ax.set_title('Survival Funnel: Phantom OI at Each T+N Node\n(Stair-Step vs Single-Spike)', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Annotate T+33 peak
    t33_idx = offsets.index(33)
    ax.annotate(f'{exact_enrich[t33_idx]:.1f}×', xy=(33, exact_enrich[t33_idx]),
                xytext=(0, 25), textcoords='offset points', ha='center',
                fontsize=9, fontweight='bold', color='red',
                arrowprops=dict(arrowstyle='->', color='red'))

    # Panel 2: Pre vs Post OI comparison (using OI snapshots, not trade tapes)
    ax = axes[0, 1]
    # Use deep_puts_ts which has OI per date
    pre_oi = deep_puts_ts[deep_puts_ts.index < SPLIT_DATE]
    post_oi = deep_puts_ts[deep_puts_ts.index >= SPLIT_DATE]
    pre_mean_oi = float(pre_oi.sum(axis=1).mean()) if len(pre_oi) > 0 else 0
    post_mean_oi = float(post_oi.sum(axis=1).mean()) if len(post_oi) > 0 else 0

    bars = [f'Pre-Split\n(n={len(pre_oi)})', f'Post-Split\n(n={len(post_oi)})']
    volumes = [pre_mean_oi, post_mean_oi]
    colors = ['steelblue', 'darkred']
    ax.bar(bars, volumes, color=colors, alpha=0.8)
    ax.set_ylabel('Mean Deep OTM Put OI (contracts)')
    ax.set_title('Deep OTM Put OI — Pre vs Post Splividend', fontsize=10)
    for i, v in enumerate(volumes):
        ax.text(i, v + max(max(volumes), 1)*0.02, f'{v:,.0f}', ha='center', fontweight='bold')
    if max(volumes) > 0:
        ratio = post_mean_oi / max(1, pre_mean_oi)
        ax.text(0.98, 0.95, f'Ratio: {ratio:.2f}×', transform=ax.transAxes,
                ha='right', va='top', fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    ax.grid(True, alpha=0.3, axis='y')

    # Panel 3: FTD slope post-split
    ax = axes[1, 0]
    post_monthly_plot = post_ftd.resample('ME')['quantity'].mean()
    ax.plot(post_monthly_plot.index, post_monthly_plot.values, 'o-', color='steelblue', markersize=4)
    ax.axhline(y=mean_ftd, color='red', linestyle='--', alpha=0.5, label=f'Full-period mean ({mean_ftd:,.0f})')
    ax.axvline(x=SPLIT_DATE, color='green', linestyle=':', alpha=0.5, label='Splividend')
    ax.set_xlabel('Date')
    ax.set_ylabel('Monthly Mean FTD')
    ax.set_title('FTD Trajectory Post-Splividend\n(Jubilee = slope up, Valve = flat)', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel 4: Summary diagram
    ax = axes[1, 1]
    ax.axis('off')
    funnel_text = "SURVIVAL FUNNEL RESULTS\n\n"
    for offset in offsets:
        r = results_a[f"T+{offset}"]
        bar = "█" * min(40, int(r['exact_enrichment'] * 2))
        funnel_text += f"T+{offset:>2}: {bar} {r['exact_enrichment']:.1f}×\n"

    funnel_text += f"\nDIAGNOSTIC:\n"
    # Determine pattern
    t33_e = results_a["T+33"]['exact_enrichment']
    t9_e = results_a.get("T+9", {}).get('exact_enrichment', 0)
    t15_e = results_a.get("T+15", {}).get('exact_enrichment', 0)
    t21_e = results_a.get("T+21", {}).get('exact_enrichment', 0)
    t27_e = results_a.get("T+27", {}).get('exact_enrichment', 0)

    intermediates = [t9_e, t15_e, t21_e, t27_e]
    if all(e < 3 for e in intermediates) and t33_e > 10:
        funnel_text += "→ FLAT-THEN-SPIKE: Single-step T+33\n"
        funnel_text += "  (NSCC Obligation Warehouse aging)\n"
    elif t9_e < t15_e < t21_e < t27_e < t33_e:
        funnel_text += "→ STAIR-STEP: 5-reset chain confirmed\n"
        funnel_text += "  (T+3 + 5×T+6 derivation valid)\n"
    else:
        funnel_text += f"→ MIXED: Partial intermediate signals\n"
        funnel_text += f"  T+9={t9_e:.1f} T+15={t15_e:.1f}\n"
        funnel_text += f"  T+21={t21_e:.1f} T+27={t27_e:.1f}\n"

    ax.text(0.05, 0.95, funnel_text, transform=ax.transAxes,
            fontfamily='monospace', fontsize=8, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()
    fig_path = FIG_DIR / "settlement_architecture.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")

    # Save results
    results = {
        'part_a_survival_funnel': results_a,
        'part_b_volume_ratio': {
            'pre_split': pre_split_volume,
            'post_split': post_split_volume,
            'pre_avg_contracts': float(pre_avg_size),
            'post_avg_contracts': float(post_avg_size),
            'ratio': float(volume_ratio),
        },
        'part_c_slope': {
            'slope': float(slope),
            'r_squared': float(r_value**2),
            'p_value': float(p_value),
            'first_month_mean': float(first_month_mean),
        },
        'part_d_alignment': alignment_results[:15] if alignment_results else [],
    }

    out_path = RESULTS_DIR / "settlement_architecture.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 16 complete.")

if __name__ == "__main__":
    main()
