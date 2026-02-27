#!/usr/bin/env python3
"""
Test 6: IJH FTDs + XRT Creation Combined Signal
beckettcat's A-Model: "IJH FTDs when mixed with XRT creation are why my A-Model
unironically is saying low 30s next week."

Also tests:
- T+33 echo × quad witching convergence (combining Test 3 + Test 5)
- XRT FTD direction classifier (when is creation bullish vs bearish?)
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
from pathlib import Path
from datetime import timedelta, datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

def add_business_days(date, n):
    current = date
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current

def get_quad_witching_dates(start_year=2021, end_year=2026):
    dates = []
    for year in range(start_year, end_year + 1):
        for month in [3, 6, 9, 12]:
            first_day = datetime(year, month, 1)
            days_until_friday = (4 - first_day.weekday()) % 7
            first_friday = first_day + timedelta(days=days_until_friday)
            third_friday = first_friday + timedelta(weeks=2)
            dates.append(pd.Timestamp(third_friday))
    return sorted(dates)

def load_csv(name):
    path = DATA_DIR / f"{name}_ftd.csv"
    if path.exists():
        df = pd.read_csv(path, parse_dates=['date'])
        return df.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    return None

def main():
    print("=" * 70)
    print("TEST 6: DEEP DIVE — IJH+XRT, Echo×Recon, Direction Classifier")
    print("=" * 70)
    
    # Load all data
    xrt = load_csv("XRT")
    gme_ftd = load_csv("GME")
    ijh = load_csv("IJH")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()
    
    if xrt is None or gme_ftd is None or ijh is None:
        print("  ❌ Missing data. Run 01_load_ftd_data.py first.")
        return
    
    # ============================================================
    # PART A: IJH + XRT Combined Signal
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: IJH FTDs + XRT FTDs Combined Signal")
    print(f"{'='*60}")
    
    # Build combined daily series
    all_dates = pd.date_range(
        max(xrt.index.min(), ijh.index.min(), gme_ftd.index.min()),
        min(xrt.index.max(), ijh.index.max(), gme_ftd.index.max()),
        freq='B'
    )
    
    combined = pd.DataFrame(index=all_dates)
    combined['xrt_ftd'] = xrt['quantity'].reindex(all_dates).fillna(0)
    combined['ijh_ftd'] = ijh['quantity'].reindex(all_dates).fillna(0)
    combined['gme_ftd'] = gme_ftd['quantity'].reindex(all_dates).fillna(0)
    combined['gme_close'] = price_df['gme_close'].reindex(all_dates).ffill()
    
    # Rolling sums
    combined['xrt_10d'] = combined['xrt_ftd'].rolling(10, min_periods=1).sum()
    combined['ijh_10d'] = combined['ijh_ftd'].rolling(10, min_periods=1).sum()
    combined['combined_10d'] = combined['xrt_10d'] + combined['ijh_10d']
    
    # Forward returns
    combined['fwd_5d'] = combined['gme_close'].pct_change(5).shift(-5)
    combined['fwd_10d'] = combined['gme_close'].pct_change(10).shift(-10)
    combined['fwd_20d'] = combined['gme_close'].pct_change(20).shift(-20)
    
    # Thresholds
    xrt_2s = combined['xrt_10d'].mean() + 2 * combined['xrt_10d'].std()
    ijh_2s = combined['ijh_10d'].mean() + 2 * combined['ijh_10d'].std()
    comb_2s = combined['combined_10d'].mean() + 2 * combined['combined_10d'].std()
    
    # Signal conditions
    xrt_spike = combined['xrt_10d'] > xrt_2s
    ijh_spike = combined['ijh_10d'] > ijh_2s
    both_spike = xrt_spike & ijh_spike
    either_spike = xrt_spike | ijh_spike
    combined_spike = combined['combined_10d'] > comb_2s
    
    print(f"\n  Signal detection:")
    print(f"    XRT-only spikes (>2σ):     {xrt_spike.sum()}")
    print(f"    IJH-only spikes (>2σ):     {ijh_spike.sum()}")
    print(f"    BOTH spiking:              {both_spike.sum()}")
    print(f"    Combined signal (>2σ):     {combined_spike.sum()}")
    
    # Compare forward returns
    print(f"\n  Forward 10-day GME returns by signal type:")
    print(f"  {'Signal':<25} {'Mean':>8} {'Median':>8} {'N':>6} {'% Pos':>8}")
    print("  " + "-" * 60)
    
    results_a = {}
    for label, mask in [
        ("No signal", ~either_spike),
        ("XRT only", xrt_spike & ~ijh_spike),
        ("IJH only", ijh_spike & ~xrt_spike),
        ("BOTH XRT+IJH", both_spike),
        ("Combined (XRT+IJH>2σ)", combined_spike),
    ]:
        ret = combined.loc[mask, 'fwd_10d'].dropna()
        if len(ret) > 0:
            pct_pos = (ret > 0).mean()
            print(f"  {label:<25} {ret.mean():>7.2%} {ret.median():>7.2%} {len(ret):>6} {pct_pos:>7.1%}")
            results_a[label] = {
                'mean_10d': float(ret.mean()),
                'median_10d': float(ret.median()),
                'n': int(len(ret)),
                'pct_positive': float(pct_pos)
            }
    
    # Top BOTH signal events
    if both_spike.sum() > 0:
        print(f"\n  Dates when BOTH XRT and IJH spiked simultaneously:")
        print(f"  {'Date':<12} {'XRT 10d':>12} {'IJH 10d':>12} {'GME':>8} {'5d':>8} {'10d':>8} {'20d':>8}")
        print("  " + "-" * 75)
        
        both_events = combined[both_spike].nlargest(15, 'combined_10d')
        for date, row in both_events.iterrows():
            r5 = f"{row['fwd_5d']:.1%}" if pd.notna(row['fwd_5d']) else "N/A"
            r10 = f"{row['fwd_10d']:.1%}" if pd.notna(row['fwd_10d']) else "N/A"
            r20 = f"{row['fwd_20d']:.1%}" if pd.notna(row['fwd_20d']) else "N/A"
            print(f"  {date.strftime('%Y-%m-%d'):<12} {row['xrt_10d']:>12,.0f} {row['ijh_10d']:>12,.0f} ${row['gme_close']:>6.2f} {r5:>8} {r10:>8} {r20:>8}")
    
    # IJH-XRT correlation
    corr = combined['xrt_ftd'].corr(combined['ijh_ftd'])
    corr_10d = combined['xrt_10d'].corr(combined['ijh_10d'])
    print(f"\n  XRT-IJH FTD correlation:")
    print(f"    Daily:    {corr:.3f}")
    print(f"    10-day:   {corr_10d:.3f}")
    
    # ============================================================
    # PART B: T+33 Echo × Quad Witching Convergence
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: T+33 Echo × Quad Witching Convergence")
    print(f"{'='*60}")
    
    quad_dates = get_quad_witching_dates()
    
    # Find GME FTD spikes
    mean_ftd = gme_ftd['quantity'].mean()
    std_ftd = gme_ftd['quantity'].std()
    threshold_2s = mean_ftd + 2 * std_ftd
    spikes = gme_ftd[gme_ftd['quantity'] > threshold_2s]
    
    # Generate T+33 echoes
    echoes = []
    for spike_date in spikes.index:
        for gen in range(1, 4):
            echo_d = add_business_days(spike_date, 33 * gen)
            echoes.append({
                'origin': spike_date,
                'echo_date': echo_d,
                'generation': gen,
                'origin_ftd': int(spikes.loc[spike_date, 'quantity'])
            })
    
    # Test: do echoes that land near quad witching have stronger effects?
    echo_near_qw = []
    echo_far_qw = []
    
    for echo in echoes:
        echo_d = echo['echo_date']
        min_gap = min(abs((echo_d - qd).days) for qd in quad_dates)
        
        # Get GME price at echo date
        nearby_price = price_df[
            (price_df.index >= echo_d - timedelta(days=3)) &
            (price_df.index <= echo_d + timedelta(days=3))
        ]
        if len(nearby_price) == 0:
            continue
        
        price = nearby_price['gme_close'].iloc[0]
        fwd = price_df[price_df.index > echo_d].head(10)
        ret_5d = float(fwd.iloc[4]['gme_close'] / price - 1) if len(fwd) >= 5 else None
        ret_10d = float(fwd.iloc[9]['gme_close'] / price - 1) if len(fwd) >= 10 else None
        
        # Get FTD at echo
        ftd_at_echo = gme_ftd.loc[gme_ftd.index == echo_d, 'quantity']
        ftd_val = int(ftd_at_echo.iloc[0]) if len(ftd_at_echo) > 0 else 0
        
        entry = {
            'echo_date': echo_d,
            'gap_to_qw': min_gap,
            'generation': echo['generation'],
            'origin_ftd': echo['origin_ftd'],
            'ftd_at_echo': ftd_val,
            'price': float(price),
            'ret_5d': ret_5d,
            'ret_10d': ret_10d,
        }
        
        if min_gap <= 5:
            echo_near_qw.append(entry)
        else:
            echo_far_qw.append(entry)
    
    # Compare
    near_rets_5d = [e['ret_5d'] for e in echo_near_qw if e['ret_5d'] is not None]
    far_rets_5d = [e['ret_5d'] for e in echo_far_qw if e['ret_5d'] is not None]
    near_rets_10d = [e['ret_10d'] for e in echo_near_qw if e['ret_10d'] is not None]
    far_rets_10d = [e['ret_10d'] for e in echo_far_qw if e['ret_10d'] is not None]
    
    near_ftds = [e['ftd_at_echo'] for e in echo_near_qw]
    far_ftds = [e['ftd_at_echo'] for e in echo_far_qw]
    
    print(f"\n  Echoes near quad witching (≤5d): {len(echo_near_qw)}")
    print(f"  Echoes far from quad witching:   {len(echo_far_qw)}")
    
    print(f"\n  {'Metric':<30} {'Near QW':>12} {'Far from QW':>12} {'Differential':>12}")
    print("  " + "-" * 70)
    
    results_b = {}
    if near_ftds and far_ftds:
        near_mean = np.mean(near_ftds)
        far_mean = np.mean(far_ftds)
        print(f"  {'Mean FTD at echo':<30} {near_mean:>12,.0f} {far_mean:>12,.0f} {near_mean/max(1,far_mean):>11.2f}×")
        results_b['ftd_at_echo'] = {'near_qw': float(near_mean), 'far_qw': float(far_mean)}
    
    if near_rets_5d and far_rets_5d:
        nm = np.mean(near_rets_5d)
        fm = np.mean(far_rets_5d)
        print(f"  {'Mean 5d fwd return':<30} {nm:>11.2%} {fm:>12.2%} {nm-fm:>11.2%}")
        results_b['ret_5d'] = {'near_qw': float(nm), 'far_qw': float(fm)}
    
    if near_rets_10d and far_rets_10d:
        nm = np.mean(near_rets_10d)
        fm = np.mean(far_rets_10d)
        print(f"  {'Mean 10d fwd return':<30} {nm:>11.2%} {fm:>12.2%} {nm-fm:>11.2%}")
        results_b['ret_10d'] = {'near_qw': float(nm), 'far_qw': float(fm)}
    
    # Show the convergence events (echo near quad witching)
    if echo_near_qw:
        print(f"\n  Echo dates that landed near quad witching:")
        print(f"  {'Echo Date':<12} {'QW Gap':>6} {'Gen':>4} {'FTD':>10} {'GME':>8} {'5d':>8} {'10d':>8}")
        print("  " + "-" * 60)
        sorted_events = sorted(echo_near_qw, key=lambda x: x['origin_ftd'], reverse=True)[:15]
        for e in sorted_events:
            r5 = f"{e['ret_5d']:.1%}" if e['ret_5d'] is not None else "N/A"
            r10 = f"{e['ret_10d']:.1%}" if e['ret_10d'] is not None else "N/A"
            gen_label = f'E{e["generation"]}'
            print(f"  {e['echo_date'].strftime('%Y-%m-%d'):<12} {e['gap_to_qw']:>6} {gen_label:>4} {e['ftd_at_echo']:>10,} ${e['price']:>6.2f} {r5:>8} {r10:>8}")
    
    # ============================================================
    # PART C: XRT FTD Direction Classifier
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: XRT FTD Direction Classifier")
    print(f"{'='*60}")
    print("  When is XRT creation bullish vs bearish for GME?")
    
    # Hypothesis: XRT FTD + rising GME FTD = delivery pressure (bullish)
    #             XRT FTD + flat GME FTD = suppression (bearish)
    
    # Build features
    classifier = combined.copy()
    classifier['xrt_spike'] = classifier['xrt_10d'] > xrt_2s
    classifier['gme_ftd_rising'] = classifier['gme_ftd'].rolling(5).mean() > classifier['gme_ftd'].rolling(20).mean()
    classifier['gme_price_rising'] = classifier['gme_close'] > classifier['gme_close'].rolling(10).mean()
    
    # Split XRT spikes into categories
    xrt_spike_mask = classifier['xrt_spike']
    
    # Category 1: XRT spike + GME FTD also rising (delivery pressure)
    delivery = xrt_spike_mask & classifier['gme_ftd_rising']
    # Category 2: XRT spike + GME FTD flat/falling (suppression)
    suppression = xrt_spike_mask & ~classifier['gme_ftd_rising']
    
    print(f"\n  XRT Spike Categories:")
    print(f"    Total XRT spikes:                    {xrt_spike_mask.sum()}")
    print(f"    + GME FTD rising (delivery):         {delivery.sum()}")
    print(f"    + GME FTD flat/falling (suppression): {suppression.sum()}")
    
    print(f"\n  {'Category':<35} {'5d Ret':>8} {'10d Ret':>8} {'20d Ret':>8} {'N':>6}")
    print("  " + "-" * 70)
    
    results_c = {}
    for label, mask in [
        ("XRT spike + GME FTD rising", delivery),
        ("XRT spike + GME FTD falling", suppression),
        ("No XRT spike", ~xrt_spike_mask),
    ]:
        r5 = classifier.loc[mask, 'fwd_5d'].dropna()
        r10 = classifier.loc[mask, 'fwd_10d'].dropna()
        r20 = classifier.loc[mask, 'fwd_20d'].dropna()
        if len(r10) > 0:
            print(f"  {label:<35} {r5.mean():>7.2%} {r10.mean():>8.2%} {r20.mean():>8.2%} {len(r10):>6}")
            results_c[label] = {
                'mean_5d': float(r5.mean()),
                'mean_10d': float(r10.mean()),
                'mean_20d': float(r20.mean()),
                'n': int(len(r10))
            }
    
    # Additional classifier: XRT spike + GME price trend
    print(f"\n  Alternative split by GME price trend:")
    trend_up = xrt_spike_mask & classifier['gme_price_rising']
    trend_down = xrt_spike_mask & ~classifier['gme_price_rising']
    
    for label, mask in [
        ("XRT spike + GME trending UP", trend_up),
        ("XRT spike + GME trending DOWN", trend_down),
    ]:
        r10 = classifier.loc[mask, 'fwd_10d'].dropna()
        r20 = classifier.loc[mask, 'fwd_20d'].dropna()
        if len(r10) > 0:
            pct = (r10 > 0).mean()
            print(f"  {label:<35} 10d: {r10.mean():>7.2%} (n={len(r10)}, {pct:.0%} positive) | 20d: {r20.mean():>7.2%}")
    
    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(3, 1, figsize=(18, 16), gridspec_kw={'height_ratios': [2, 1.5, 1.5]})
    fig.suptitle('Deep Dive: IJH+XRT Combined, Echo×Recon, Direction Classifier', fontsize=14, fontweight='bold', y=0.98)
    
    # Panel 1: IJH + XRT combined signal with GME price
    ax1 = axes[0]
    ax1r = ax1.twinx()
    ax1.fill_between(combined.index, 0, combined['xrt_10d'], alpha=0.3, color='steelblue', label='XRT 10d FTD')
    ax1.fill_between(combined.index, 0, combined['ijh_10d'], alpha=0.3, color='red', label='IJH 10d FTD')
    ax1r.plot(combined.index, combined['gme_close'], color='#1a1a2e', linewidth=1, label='GME Close')
    if both_spike.sum() > 0:
        ax1r.scatter(combined[both_spike].index, combined.loc[both_spike, 'gme_close'],
                    color='gold', s=40, zorder=5, edgecolors='red', linewidth=1, label=f'Both spike (n={both_spike.sum()})')
    ax1.set_ylabel('10-day FTD Sum', fontsize=10, color='steelblue')
    ax1r.set_ylabel('GME Price ($)', fontsize=10)
    ax1.legend(loc='upper left', fontsize=8)
    ax1r.legend(loc='upper right', fontsize=8)
    ax1.set_title('IJH + XRT FTD Combined Signal vs GME Price', fontsize=11)
    ax1.grid(True, alpha=0.2)
    
    # Panel 2: XRT Direction Classifier
    ax2 = axes[1]
    colors_map = []
    for i, (date, row) in enumerate(classifier.iterrows()):
        if row['xrt_spike'] and row['gme_ftd_rising']:
            colors_map.append('green')  # delivery
        elif row['xrt_spike'] and not row['gme_ftd_rising']:
            colors_map.append('red')    # suppression
        else:
            colors_map.append('lightgray')
    
    ax2.bar(classifier.index, classifier['xrt_10d'], width=1, color=colors_map, alpha=0.6)
    ax2.axhline(y=xrt_2s, color='orange', linestyle='--', linewidth=1, label=f'XRT 2σ ({xrt_2s:,.0f})')
    ax2.set_ylabel('XRT 10-day FTD', fontsize=10)
    ax2.set_title('XRT FTD Direction Classifier (green=delivery/bullish, red=suppression/bearish)', fontsize=11)
    ax2.legend(loc='upper right', fontsize=8)
    ax2.grid(True, alpha=0.2)
    
    # Panel 3: IJH-XRT correlation scatter
    ax3 = axes[2]
    ax3.scatter(combined['xrt_ftd'], combined['ijh_ftd'], s=10, alpha=0.3, color='steelblue')
    ax3.set_xlabel('XRT Daily FTD', fontsize=10)
    ax3.set_ylabel('IJH Daily FTD', fontsize=10)
    ax3.set_title(f'XRT vs IJH Daily FTD Scatter (r={corr:.3f})', fontsize=11)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = FIG_DIR / "deep_dive_combined.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    # Save results
    results = {
        'part_a_ijh_xrt': results_a,
        'ijh_xrt_correlation': {'daily': float(corr), '10d_rolling': float(corr_10d)},
        'part_b_echo_qw': results_b,
        'echo_near_qw_count': len(echo_near_qw),
        'echo_far_qw_count': len(echo_far_qw),
        'part_c_classifier': results_c,
    }
    
    out_path = RESULTS_DIR / "deep_dive_combined.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 6 (Deep Dive) complete.")

if __name__ == "__main__":
    main()
