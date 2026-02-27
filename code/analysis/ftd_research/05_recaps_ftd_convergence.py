#!/usr/bin/env python3
"""
Test 4: RECAPS × FTD Convergence
Test whether T+33 FTD echo dates cluster around DTCC RECAPS dates more than chance.
Overlays the T+33 cascade from Test 3 against the bimonthly RECAPS calendar.
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

# DTCC RECAPS dates — bimonthly mark-to-market in the Obligation Warehouse
# Source: DTCC Important Notices + recaps_overlay_analysis.md
# Pattern: ~every 2 weeks on business days (NSCC-0116 schedule)
RECAPS_DATES = [
    # 2021
    "2021-01-13", "2021-01-28", "2021-02-10", "2021-02-25",
    "2021-03-11", "2021-03-25", "2021-04-08", "2021-04-22",
    "2021-05-06", "2021-05-20", "2021-05-26", "2021-06-10", "2021-06-14",
    "2021-06-24", "2021-07-08", "2021-07-22", "2021-08-05", "2021-08-19",
    "2021-08-26", "2021-09-02", "2021-09-16", "2021-09-30",
    "2021-10-14", "2021-10-28", "2021-11-11", "2021-11-24",
    "2021-12-09", "2021-12-23",
    # 2022
    "2022-01-06", "2022-01-13", "2022-01-27",
    "2022-02-10", "2022-02-24", "2022-03-10", "2022-03-24", "2022-03-30",
    "2022-04-07", "2022-04-21", "2022-05-05", "2022-05-19", "2022-05-25",
    "2022-06-02", "2022-06-16", "2022-06-30",
    "2022-07-14", "2022-07-28", "2022-08-10", "2022-08-25",
    "2022-09-08", "2022-09-22", "2022-10-06", "2022-10-20",
    "2022-11-03", "2022-11-17", "2022-12-01", "2022-12-15", "2022-12-29",
    # 2023
    "2023-01-11", "2023-01-26", "2023-02-09", "2023-02-23",
    "2023-03-09", "2023-03-23", "2023-04-06", "2023-04-20",
    "2023-05-04", "2023-05-18", "2023-06-01", "2023-06-15", "2023-06-29",
    "2023-07-13", "2023-07-27", "2023-08-10", "2023-08-24",
    "2023-09-07", "2023-09-21", "2023-10-05", "2023-10-19",
    "2023-11-02", "2023-11-16", "2023-11-30", "2023-12-14", "2023-12-28",
    # 2024
    "2024-01-11", "2024-01-25", "2024-02-08", "2024-02-22",
    "2024-03-07", "2024-03-21", "2024-04-04", "2024-04-18",
    "2024-05-02", "2024-05-09", "2024-05-16", "2024-05-30",
    "2024-06-11", "2024-06-13", "2024-06-27",
    "2024-07-11", "2024-07-25", "2024-08-08", "2024-08-22",
    "2024-09-05", "2024-09-19", "2024-10-03", "2024-10-17",
    "2024-10-31", "2024-11-14", "2024-11-27", "2024-12-12", "2024-12-26",
    # 2025
    "2025-01-09", "2025-01-23", "2025-02-06", "2025-02-20",
    "2025-03-06", "2025-03-20", "2025-04-03", "2025-04-17",
    "2025-05-01", "2025-05-15", "2025-05-29",
    "2025-06-12", "2025-06-26", "2025-07-10", "2025-07-24",
    "2025-08-07", "2025-08-21", "2025-09-04", "2025-09-18",
    "2025-10-02", "2025-10-16", "2025-10-30",
    "2025-11-13", "2025-11-26", "2025-12-11", "2025-12-24",
]

def add_business_days(date, n):
    current = date
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current

def main():
    print("=" * 70)
    print("TEST 4: RECAPS × FTD Convergence")
    print("=" * 70)
    
    recaps = sorted([pd.Timestamp(d) for d in RECAPS_DATES])
    print(f"\n  RECAPS dates loaded: {len(recaps)}")
    print(f"  Range: {recaps[0].strftime('%Y-%m-%d')} – {recaps[-1].strftime('%Y-%m-%d')}")
    
    # Load GME FTD data
    gme_path = DATA_DIR / "GME_ftd.csv"
    price_path = DATA_DIR / "gme_daily_price.csv"
    
    if not gme_path.exists():
        print("  ❌ Missing GME FTD data. Run 01_load_ftd_data.py first.")
        return
    
    gme = pd.read_csv(gme_path, parse_dates=['date'])
    gme_daily = gme.groupby('date')['quantity'].sum().reset_index()
    gme_daily = gme_daily.sort_values('date').set_index('date')
    
    gme_price = pd.read_csv(price_path, parse_dates=['date']) if price_path.exists() else None
    if gme_price is not None:
        gme_price['date'] = pd.to_datetime(gme_price['date'])
        gme_price = gme_price.set_index('date')
    
    mean_ftd = gme_daily['quantity'].mean()
    std_ftd = gme_daily['quantity'].std()
    threshold_2sigma = mean_ftd + 2 * std_ftd
    
    # Find all FTD spikes
    spikes = gme_daily[gme_daily['quantity'] > threshold_2sigma].copy()
    print(f"  FTD spikes (>2σ): {len(spikes)}")
    
    # Generate T+33 echo dates for each spike
    echo_dates = []
    for spike_date in spikes.index:
        for gen in range(1, 4):  # 3 echo generations
            echo_d = add_business_days(spike_date, 33 * gen)
            echo_dates.append({
                'origin': spike_date,
                'echo_date': echo_d,
                'generation': gen,
                'origin_ftd': int(spikes.loc[spike_date, 'quantity'])
            })
    
    print(f"  Echo dates generated: {len(echo_dates)}")
    
    # Test 1: How many echo dates fall within ±2 days of a RECAPS date?
    recaps_window = 2  # business days
    
    echo_near_recaps = 0
    echo_on_recaps = 0
    convergence_events = []
    
    for echo in echo_dates:
        echo_d = echo['echo_date']
        for recap_d in recaps:
            diff = abs((echo_d - recap_d).days)
            if diff <= recaps_window:
                echo_near_recaps += 1
                if diff == 0:
                    echo_on_recaps += 1
                convergence_events.append({
                    'echo_date': echo_d.strftime('%Y-%m-%d'),
                    'recaps_date': recap_d.strftime('%Y-%m-%d'),
                    'gap_days': int(diff),
                    'generation': echo['generation'],
                    'origin_date': echo['origin'].strftime('%Y-%m-%d'),
                    'origin_ftd': echo['origin_ftd']
                })
                break
    
    # Expected by chance
    total_days = (recaps[-1] - recaps[0]).days
    recaps_coverage = len(recaps) * (2 * recaps_window + 1) / total_days
    expected_by_chance = len(echo_dates) * recaps_coverage
    
    observed_rate = echo_near_recaps / max(1, len(echo_dates))
    expected_rate = recaps_coverage
    
    print(f"\n  CONVERGENCE RESULTS:")
    print(f"    Echo dates near RECAPS (±{recaps_window}d):  {echo_near_recaps}/{len(echo_dates)} ({observed_rate:.1%})")
    print(f"    Echo dates ON RECAPS:              {echo_on_recaps}/{len(echo_dates)}")
    print(f"    Expected by chance:                {expected_by_chance:.1f} ({expected_rate:.1%})")
    print(f"    Enrichment:                        {observed_rate / max(0.001, expected_rate):.2f}×")
    
    # Chi-squared test
    observed = np.array([echo_near_recaps, len(echo_dates) - echo_near_recaps])
    expected = np.array([expected_by_chance, len(echo_dates) - expected_by_chance])
    
    if expected.min() > 5:
        chi2, p_val = stats.chisquare(observed, f_exp=expected)
        print(f"    Chi-squared:                       {chi2:.2f}")
        print(f"    p-value:                           {p_val:.4f}")
        verdict = "✅ SIGNIFICANT" if p_val < 0.05 else "❌ NOT SIGNIFICANT"
        print(f"    Verdict:                           {verdict}")
    else:
        chi2, p_val = None, None
        print(f"    Chi-squared: insufficient expected counts")
    
    # Test 2: Are FTD levels higher near RECAPS dates?
    print(f"\n  FTD levels near RECAPS dates vs. other days:")
    
    near_recaps_mask = pd.Series(False, index=gme_daily.index)
    for recap_d in recaps:
        mask = (gme_daily.index >= recap_d - timedelta(days=recaps_window)) & \
               (gme_daily.index <= recap_d + timedelta(days=recaps_window))
        near_recaps_mask = near_recaps_mask | mask
    
    recaps_ftd = gme_daily.loc[near_recaps_mask, 'quantity']
    non_recaps_ftd = gme_daily.loc[~near_recaps_mask, 'quantity']
    
    print(f"    Near RECAPS mean FTD:    {recaps_ftd.mean():>12,.0f} (n={len(recaps_ftd)})")
    print(f"    Non-RECAPS mean FTD:     {non_recaps_ftd.mean():>12,.0f} (n={len(non_recaps_ftd)})")
    print(f"    Ratio:                   {recaps_ftd.mean() / max(1, non_recaps_ftd.mean()):.2f}×")
    
    # Mann-Whitney U test
    if len(recaps_ftd) > 10 and len(non_recaps_ftd) > 10:
        u_stat, u_pval = stats.mannwhitneyu(recaps_ftd, non_recaps_ftd, alternative='greater')
        print(f"    Mann-Whitney U:          {u_stat:,.0f}")
        print(f"    p-value (one-sided):     {u_pval:.4f}")
    
    # Test 3: GME price action near RECAPS × echo convergence
    if gme_price is not None and convergence_events:
        print(f"\n  Top convergence events (echo + RECAPS within {recaps_window}d):")
        print(f"  {'Echo Date':<12} {'RECAPS':<12} {'Gap':>4} {'Gen':>4} {'FTD':>10} {'GME':>8} {'5d Ret':>8}")
        print("  " + "-" * 65)
        
        # Sort by origin FTD (biggest spikes first)
        convergence_events.sort(key=lambda x: x['origin_ftd'], reverse=True)
        
        for event in convergence_events[:20]:
            echo_d = pd.Timestamp(event['echo_date'])
            nearby_price = gme_price[
                (gme_price.index >= echo_d - timedelta(days=3)) &
                (gme_price.index <= echo_d + timedelta(days=3))
            ]
            if len(nearby_price) > 0:
                price = nearby_price['gme_close'].iloc[0]
                fwd = gme_price[gme_price.index > echo_d].head(5)
                ret_5d = (fwd.iloc[4]['gme_close'] / price - 1) if len(fwd) >= 5 else None
                r5 = f"{ret_5d:.1%}" if ret_5d is not None else "N/A"
            else:
                price = np.nan
                r5 = "N/A"
                ret_5d = None
            
            price_str = f"${price:.2f}" if pd.notna(price) else "N/A"
            gen_label = f'E{event["generation"]}'  
            print(f"  {event['echo_date']:<12} {event['recaps_date']:<12} {event['gap_days']:>4} {gen_label:>4} {event['origin_ftd']:>10,} {price_str:>8} {r5:>8}")
    
    # ===== VISUALIZATION =====
    fig, axes = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2, 1.5]})
    fig.suptitle('RECAPS × T+33 FTD Echo Convergence', fontsize=16, fontweight='bold', y=0.98)
    
    # Panel 1: GME FTD with RECAPS and echo overlays
    axes[0].bar(gme_daily.index, gme_daily['quantity'], width=1, alpha=0.4, color='steelblue', label='GME Daily FTD')
    
    # Mark RECAPS dates
    for recap_d in recaps:
        if recap_d in gme_daily.index or (recap_d >= gme_daily.index.min() and recap_d <= gme_daily.index.max()):
            axes[0].axvline(x=recap_d, color='green', alpha=0.15, linewidth=0.5)
    
    # Mark convergence events
    for event in convergence_events:
        echo_d = pd.Timestamp(event['echo_date'])
        if echo_d in gme_daily.index:
            axes[0].scatter([echo_d], [gme_daily.loc[echo_d, 'quantity']], 
                          color='red', s=40, zorder=5, marker='*')
    
    axes[0].axhline(y=threshold_2sigma, color='orange', linestyle='--', linewidth=1, alpha=0.7, label=f'2σ ({threshold_2sigma:,.0f})')
    axes[0].set_ylabel('GME FTDs', fontsize=11)
    axes[0].legend(loc='upper right')
    axes[0].set_title('GME FTDs with RECAPS Dates (green) and Convergence Events (★)', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Gap distribution (echo → nearest RECAPS)
    gaps = []
    for echo in echo_dates:
        echo_d = echo['echo_date']
        min_gap = min(abs((echo_d - r).days) for r in recaps)
        gaps.append(min_gap)
    
    axes[1].hist(gaps, bins=range(0, 30), alpha=0.6, color='steelblue', edgecolor='black', label='Observed gap distribution')
    axes[1].axvline(x=recaps_window, color='red', linestyle='--', linewidth=2, label=f'±{recaps_window}d window')
    axes[1].set_xlabel('Days from Echo Date to Nearest RECAPS', fontsize=11)
    axes[1].set_ylabel('Frequency', fontsize=11)
    axes[1].legend(loc='upper right')
    axes[1].set_title('Distribution: T+33 Echo Date Proximity to RECAPS', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    fig_path = FIG_DIR / "recaps_ftd_convergence.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    # Save results
    results = {
        'recaps_dates_count': len(recaps),
        'echo_dates_count': len(echo_dates),
        'convergence': {
            'near_recaps': echo_near_recaps,
            'on_recaps': echo_on_recaps,
            'observed_rate': float(observed_rate),
            'expected_rate': float(expected_rate),
            'enrichment': float(observed_rate / max(0.001, expected_rate)),
            'chi_squared': float(chi2) if chi2 is not None else None,
            'p_value': float(p_val) if p_val is not None else None
        },
        'ftd_near_recaps': {
            'mean_near': float(recaps_ftd.mean()),
            'mean_non': float(non_recaps_ftd.mean()),
            'ratio': float(recaps_ftd.mean() / max(1, non_recaps_ftd.mean()))
        },
        'top_convergence_events': convergence_events[:20]
    }
    
    out_path = RESULTS_DIR / "recaps_convergence.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 4 complete.")

if __name__ == "__main__":
    main()
