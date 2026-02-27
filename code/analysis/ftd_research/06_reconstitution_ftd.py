#!/usr/bin/env python3
"""
Test 5: XRT Reconstitution + FTD Pattern
TheUltimator5 hypothesis: On quad witching (XRT reconstitution), XRT OPEX is loaded
with puts while GME is loaded with calls. This creates reconstitution arbitrage.
Test whether XRT FTDs spike around quad witching dates.
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

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

def get_quad_witching_dates(start_year=2021, end_year=2026):
    """
    Quad witching: 3rd Friday of March, June, September, December.
    These are XRT reconstitution dates.
    """
    dates = []
    for year in range(start_year, end_year + 1):
        for month in [3, 6, 9, 12]:
            # Find 3rd Friday
            first_day = datetime(year, month, 1)
            # Find first Friday
            days_until_friday = (4 - first_day.weekday()) % 7
            first_friday = first_day + timedelta(days=days_until_friday)
            third_friday = first_friday + timedelta(weeks=2)
            dates.append(pd.Timestamp(third_friday))
    return sorted(dates)

def main():
    print("=" * 70)
    print("TEST 5: XRT Reconstitution + FTD Pattern")
    print("=" * 70)
    
    quad_dates = get_quad_witching_dates()
    print(f"\n  Quad witching dates: {len(quad_dates)}")
    for d in quad_dates:
        print(f"    {d.strftime('%Y-%m-%d')} ({d.strftime('%A')})")
    
    # Load data
    xrt_path = DATA_DIR / "XRT_ftd.csv"
    gme_path = DATA_DIR / "GME_ftd.csv"
    price_path = DATA_DIR / "gme_daily_price.csv"
    
    if not xrt_path.exists() or not gme_path.exists():
        print("  ❌ Missing FTD data. Run 01_load_ftd_data.py first.")
        return
    
    xrt = pd.read_csv(xrt_path, parse_dates=['date'])
    gme_ftd = pd.read_csv(gme_path, parse_dates=['date'])
    
    xrt_daily = xrt.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    gme_daily = gme_ftd.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    
    gme_price = pd.read_csv(price_path, parse_dates=['date']) if price_path.exists() else None
    if gme_price is not None:
        gme_price['date'] = pd.to_datetime(gme_price['date'])
        gme_price = gme_price.set_index('date')
    
    # Event study: ±10 trading days around each quad witching
    window = 15  # calendar days for window
    
    print(f"\n  Event Study: XRT FTDs around Quad Witching (±{window}d)")
    print(f"  {'Date':<12} {'Pre-10d FTD':>12} {'Event FTD':>12} {'Post-10d':>12} {'Ratio':>8} {'GME Price':>10}")
    print("  " + "-" * 70)
    
    event_studies = []
    
    for qd in quad_dates:
        pre_start = qd - timedelta(days=window)
        pre_end = qd - timedelta(days=1)
        post_start = qd + timedelta(days=1)
        post_end = qd + timedelta(days=window)
        
        # XRT FTDs
        pre_xrt = xrt_daily[(xrt_daily.index >= pre_start) & (xrt_daily.index <= pre_end)]
        event_xrt = xrt_daily[(xrt_daily.index >= qd - timedelta(days=3)) & (xrt_daily.index <= qd + timedelta(days=3))]
        post_xrt = xrt_daily[(xrt_daily.index >= post_start) & (xrt_daily.index <= post_end)]
        
        pre_mean = pre_xrt['quantity'].mean() if len(pre_xrt) > 0 else 0
        event_mean = event_xrt['quantity'].mean() if len(event_xrt) > 0 else 0
        post_mean = post_xrt['quantity'].mean() if len(post_xrt) > 0 else 0
        ratio = event_mean / max(1, pre_mean)
        
        # GME price
        gme_p = "N/A"
        gme_ret = None
        if gme_price is not None:
            nearby = gme_price[(gme_price.index >= qd - timedelta(days=3)) & (gme_price.index <= qd + timedelta(days=3))]
            if len(nearby) > 0:
                gme_p = f"${nearby['gme_close'].iloc[-1]:.2f}"
                # Forward return
                fwd = gme_price[gme_price.index > qd].head(10)
                if len(fwd) >= 5:
                    gme_ret = float(fwd.iloc[4]['gme_close'] / nearby['gme_close'].iloc[-1] - 1)
        
        print(f"  {qd.strftime('%Y-%m-%d'):<12} {pre_mean:>12,.0f} {event_mean:>12,.0f} {post_mean:>12,.0f} {ratio:>7.1f}× {gme_p:>10}")
        
        event_studies.append({
            'date': qd.strftime('%Y-%m-%d'),
            'pre_mean': float(pre_mean),
            'event_mean': float(event_mean),
            'post_mean': float(post_mean),
            'ratio': float(ratio),
            'gme_5d_fwd_ret': gme_ret
        })
    
    # Overall statistics
    if event_studies:
        ratios = [e['ratio'] for e in event_studies if e['pre_mean'] > 0]
        elevated_count = sum(1 for r in ratios if r > 1.5)
        
        print(f"\n  Summary:")
        print(f"    Events analyzed:      {len(event_studies)}")
        print(f"    Mean elevation ratio: {np.mean(ratios):.2f}× (event vs pre)")
        print(f"    Elevated (>1.5×):     {elevated_count}/{len(ratios)} ({elevated_count/max(1,len(ratios)):.0%})")
        
        # Compare event days vs. all other days
        event_window_mask = pd.Series(False, index=xrt_daily.index)
        for qd in quad_dates:
            mask = (xrt_daily.index >= qd - timedelta(days=5)) & (xrt_daily.index <= qd + timedelta(days=5))
            event_window_mask = event_window_mask | mask
        
        event_ftds = xrt_daily.loc[event_window_mask, 'quantity']
        non_event_ftds = xrt_daily.loc[~event_window_mask, 'quantity']
        
        print(f"\n    XRT FTD near quad witching:  {event_ftds.mean():>12,.0f} (n={len(event_ftds)})")
        print(f"    XRT FTD other days:          {non_event_ftds.mean():>12,.0f} (n={len(non_event_ftds)})")
        print(f"    Ratio:                       {event_ftds.mean() / max(1, non_event_ftds.mean()):.2f}×")
        
        # Statistical test
        if len(event_ftds) > 5 and len(non_event_ftds) > 5:
            u_stat, u_pval = stats.mannwhitneyu(event_ftds, non_event_ftds, alternative='greater')
            print(f"    Mann-Whitney U:              {u_stat:,.0f}")
            print(f"    p-value (one-sided):         {u_pval:.4f}")
            verdict = "✅ SIGNIFICANT" if u_pval < 0.05 else "❌ NOT SIGNIFICANT"
            print(f"    Verdict:                     {verdict}")
        
        # GME price effect around quad witching
        if gme_price is not None:
            fwd_rets = [e['gme_5d_fwd_ret'] for e in event_studies if e['gme_5d_fwd_ret'] is not None]
            if fwd_rets:
                print(f"\n    GME 5-day fwd return after quad witching:")
                print(f"      Mean:     {np.mean(fwd_rets):.2%}")
                print(f"      Positive: {sum(1 for r in fwd_rets if r > 0)}/{len(fwd_rets)}")
    
    # GME FTD around same dates for comparison
    print(f"\n  GME FTD Event Study (same dates):")
    gme_event_mask = pd.Series(False, index=gme_daily.index)
    for qd in quad_dates:
        mask = (gme_daily.index >= qd - timedelta(days=5)) & (gme_daily.index <= qd + timedelta(days=5))
        gme_event_mask = gme_event_mask | mask
    
    gme_event_ftds = gme_daily.loc[gme_event_mask, 'quantity']
    gme_non_event_ftds = gme_daily.loc[~gme_event_mask, 'quantity']
    
    print(f"    GME FTD near quad witching:  {gme_event_ftds.mean():>12,.0f}")
    print(f"    GME FTD other days:          {gme_non_event_ftds.mean():>12,.0f}")
    print(f"    Ratio:                       {gme_event_ftds.mean() / max(1, gme_non_event_ftds.mean()):.2f}×")
    
    # ===== VISUALIZATION =====
    fig, axes = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2, 1.5]})
    fig.suptitle('XRT FTDs Around Quad Witching (Reconstitution) Dates', fontsize=16, fontweight='bold', y=0.98)
    
    # Panel 1: XRT FTD timeline with quad witching markers
    axes[0].bar(xrt_daily.index, xrt_daily['quantity'], width=1, alpha=0.4, color='steelblue', label='XRT Daily FTD')
    for qd in quad_dates:
        axes[0].axvline(x=qd, color='red', alpha=0.4, linewidth=1.5)
    axes[0].axvline(x=quad_dates[0], color='red', alpha=0.4, linewidth=1.5, label='Quad Witching')
    axes[0].set_ylabel('XRT FTDs', fontsize=11)
    axes[0].legend(loc='upper right')
    axes[0].set_title('XRT FTDs with Quad Witching (Reconstitution) Dates', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Averaged event study
    all_event_curves_xrt = []
    all_event_curves_gme = []
    days_range = range(-10, 11)
    
    for qd in quad_dates:
        xrt_curve = []
        gme_curve = []
        for d in days_range:
            check_date = qd + timedelta(days=d)
            xrt_val = xrt_daily.loc[check_date, 'quantity'] if check_date in xrt_daily.index else np.nan
            gme_val = gme_daily.loc[check_date, 'quantity'] if check_date in gme_daily.index else np.nan
            xrt_curve.append(xrt_val)
            gme_curve.append(gme_val)
        all_event_curves_xrt.append(xrt_curve)
        all_event_curves_gme.append(gme_curve)
    
    xrt_avg = np.nanmean(all_event_curves_xrt, axis=0)
    gme_avg = np.nanmean(all_event_curves_gme, axis=0)
    
    ax2l = axes[1]
    ax2r = axes[1].twinx()
    
    ax2l.bar(list(days_range), xrt_avg, color='steelblue', alpha=0.5, label='XRT FTD (avg)')
    ax2r.bar([d + 0.3 for d in days_range], gme_avg, color='orange', alpha=0.5, width=0.4, label='GME FTD (avg)')
    ax2l.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Quad Witching Day')
    ax2l.set_xlabel('Days Relative to Quad Witching', fontsize=11)
    ax2l.set_ylabel('XRT FTD (avg)', fontsize=11, color='steelblue')
    ax2r.set_ylabel('GME FTD (avg)', fontsize=11, color='orange')
    ax2l.legend(loc='upper left')
    ax2r.legend(loc='upper right')
    axes[1].set_title('Average FTD Pattern Around Quad Witching (Event Study)', fontsize=12)
    ax2l.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    fig_path = FIG_DIR / "reconstitution_ftd.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    # Save results
    results = {
        'quad_witching_dates': [d.strftime('%Y-%m-%d') for d in quad_dates],
        'event_studies': event_studies,
        'xrt_ftd_elevation': {
            'event_mean': float(event_ftds.mean()) if len(event_ftds) > 0 else None,
            'non_event_mean': float(non_event_ftds.mean()) if len(non_event_ftds) > 0 else None,
            'ratio': float(event_ftds.mean() / max(1, non_event_ftds.mean())) if len(event_ftds) > 0 else None
        },
        'gme_ftd_elevation': {
            'event_mean': float(gme_event_ftds.mean()),
            'non_event_mean': float(gme_non_event_ftds.mean()),
            'ratio': float(gme_event_ftds.mean() / max(1, gme_non_event_ftds.mean()))
        }
    }
    
    out_path = RESULTS_DIR / "reconstitution_ftd.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 5 complete.")

if __name__ == "__main__":
    main()
