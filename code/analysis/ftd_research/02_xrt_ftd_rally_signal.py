#!/usr/bin/env python3
"""
Test 1: XRT FTD as Rally Signal
beckettcat hypothesis: When XRT goes into deep creation (high FTDs = high shares outstanding),
a GME rally follows. Test XRT FTD rolling sum against GME price action.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
from pathlib import Path
from datetime import timedelta

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("=" * 70)
    print("TEST 1: XRT FTD as Rally Signal")
    print("=" * 70)
    
    # Load data
    xrt_path = DATA_DIR / "XRT_ftd.csv"
    gme_path = DATA_DIR / "GME_ftd.csv"
    price_path = DATA_DIR / "gme_daily_price.csv"
    
    for p in [xrt_path, gme_path, price_path]:
        if not p.exists():
            print(f"  ❌ Missing: {p}")
            print("  Run 01_load_ftd_data.py first.")
            return
    
    xrt = pd.read_csv(xrt_path, parse_dates=['date'])
    gme_ftd = pd.read_csv(gme_path, parse_dates=['date'])
    gme_price = pd.read_csv(price_path, parse_dates=['date'])
    
    # Build daily XRT FTD series
    xrt_daily = xrt.groupby('date')['quantity'].sum().reset_index()
    xrt_daily = xrt_daily.sort_values('date').set_index('date')
    
    # Rolling windows: 5-day, 10-day, 20-day sums
    xrt_daily['ftd_5d'] = xrt_daily['quantity'].rolling(5, min_periods=1).sum()
    xrt_daily['ftd_10d'] = xrt_daily['quantity'].rolling(10, min_periods=1).sum()
    xrt_daily['ftd_20d'] = xrt_daily['quantity'].rolling(20, min_periods=1).sum()
    
    # Calculate thresholds
    mean_5d = xrt_daily['ftd_5d'].mean()
    std_5d = xrt_daily['ftd_5d'].std()
    threshold_2sigma = mean_5d + 2 * std_5d
    threshold_3sigma = mean_5d + 3 * std_5d
    
    print(f"\n  XRT FTD 5-day rolling sum:")
    print(f"    Mean:       {mean_5d:>12,.0f}")
    print(f"    Std:        {std_5d:>12,.0f}")
    print(f"    2σ thresh:  {threshold_2sigma:>12,.0f}")
    print(f"    3σ thresh:  {threshold_3sigma:>12,.0f}")
    
    # Find spike dates (>2σ)
    spike_dates = xrt_daily[xrt_daily['ftd_5d'] > threshold_2sigma].copy()
    print(f"\n  Spike dates (>2σ): {len(spike_dates)}")
    
    # Merge with GME price
    gme_price['date'] = pd.to_datetime(gme_price['date'])
    gme_price = gme_price.sort_values('date').set_index('date')
    
    # Forward return analysis: does GME rally within N days of XRT FTD spike?
    gme_price['fwd_5d_ret'] = gme_price['gme_close'].pct_change(5).shift(-5)
    gme_price['fwd_10d_ret'] = gme_price['gme_close'].pct_change(10).shift(-10)
    gme_price['fwd_20d_ret'] = gme_price['gme_close'].pct_change(20).shift(-20)
    
    # Align spike dates with forward returns
    merged = xrt_daily.join(gme_price[['gme_close', 'fwd_5d_ret', 'fwd_10d_ret', 'fwd_20d_ret']], how='left')
    merged = merged.dropna(subset=['gme_close'])
    
    # Compare returns after spikes vs. non-spikes
    spike_mask = merged['ftd_5d'] > threshold_2sigma
    
    results = {
        'xrt_ftd_5d_stats': {
            'mean': float(mean_5d),
            'std': float(std_5d),
            'threshold_2sigma': float(threshold_2sigma),
            'threshold_3sigma': float(threshold_3sigma)
        },
        'spike_dates_count': int(spike_mask.sum()),
        'non_spike_dates_count': int((~spike_mask).sum()),
        'forward_returns': {}
    }
    
    print(f"\n  {'Window':<12} {'Post-Spike':>12} {'Non-Spike':>12} {'Diff':>12} {'Verdict':>12}")
    print("  " + "-" * 65)
    
    for window, col in [('5-day', 'fwd_5d_ret'), ('10-day', 'fwd_10d_ret'), ('20-day', 'fwd_20d_ret')]:
        spike_ret = merged.loc[spike_mask, col].dropna()
        non_spike_ret = merged.loc[~spike_mask, col].dropna()
        
        if len(spike_ret) > 0 and len(non_spike_ret) > 0:
            s_mean = spike_ret.mean()
            n_mean = non_spike_ret.mean()
            diff = s_mean - n_mean
            verdict = "✅ BULLISH" if diff > 0.01 else ("⚠️ NEUTRAL" if diff > -0.01 else "❌ BEARISH")
            
            print(f"  {window:<12} {s_mean:>11.2%} {n_mean:>12.2%} {diff:>11.2%}  {verdict}")
            
            results['forward_returns'][window] = {
                'post_spike_mean': float(s_mean),
                'non_spike_mean': float(n_mean),
                'differential': float(diff),
                'spike_n': int(len(spike_ret)),
                'non_spike_n': int(len(non_spike_ret))
            }
    
    # Top 15 spike events with forward returns
    print(f"\n  Top 15 XRT FTD Spike Events:")
    print(f"  {'Date':<12} {'XRT 5d FTD':>12} {'GME Price':>10} {'5d Ret':>8} {'10d Ret':>8} {'20d Ret':>8}")
    print("  " + "-" * 70)
    
    top_spikes = merged[spike_mask].nlargest(15, 'ftd_5d')
    spike_events = []
    for date, row in top_spikes.iterrows():
        r5 = f"{row['fwd_5d_ret']:.1%}" if pd.notna(row['fwd_5d_ret']) else "N/A"
        r10 = f"{row['fwd_10d_ret']:.1%}" if pd.notna(row['fwd_10d_ret']) else "N/A"
        r20 = f"{row['fwd_20d_ret']:.1%}" if pd.notna(row['fwd_20d_ret']) else "N/A"
        print(f"  {date.strftime('%Y-%m-%d'):<12} {row['ftd_5d']:>12,.0f} ${row['gme_close']:>8.2f} {r5:>8} {r10:>8} {r20:>8}")
        spike_events.append({
            'date': date.strftime('%Y-%m-%d'),
            'xrt_ftd_5d': int(row['ftd_5d']),
            'gme_price': float(row['gme_close']),
            'fwd_5d_ret': float(row['fwd_5d_ret']) if pd.notna(row['fwd_5d_ret']) else None,
            'fwd_10d_ret': float(row['fwd_10d_ret']) if pd.notna(row['fwd_10d_ret']) else None,
            'fwd_20d_ret': float(row['fwd_20d_ret']) if pd.notna(row['fwd_20d_ret']) else None,
        })
    
    results['top_spike_events'] = spike_events
    
    # ===== VISUALIZATION =====
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 14), 
                                          gridspec_kw={'height_ratios': [2, 1.5, 1]})
    fig.suptitle('XRT FTD as GME Rally Signal', fontsize=16, fontweight='bold', y=0.98)
    
    # Panel 1: GME price with XRT FTD spike overlays
    ax1.plot(merged.index, merged['gme_close'], color='#1a1a2e', linewidth=1, label='GME Close')
    spike_x = merged[spike_mask].index
    spike_y = merged.loc[spike_mask, 'gme_close']
    ax1.scatter(spike_x, spike_y, color='red', s=20, alpha=0.7, zorder=5, label=f'XRT FTD Spike (>2σ, n={len(spike_x)})')
    ax1.set_ylabel('GME Price ($)', fontsize=11)
    ax1.legend(loc='upper right')
    ax1.set_title('GME Price with XRT FTD Spike Dates', fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # Panel 2: XRT FTD rolling sum
    ax2.fill_between(xrt_daily.index, 0, xrt_daily['ftd_5d'], alpha=0.3, color='steelblue', label='5-day rolling FTD')
    ax2.axhline(y=threshold_2sigma, color='orange', linestyle='--', linewidth=1, label=f'2σ threshold ({threshold_2sigma:,.0f})')
    ax2.axhline(y=threshold_3sigma, color='red', linestyle='--', linewidth=1, label=f'3σ threshold ({threshold_3sigma:,.0f})')
    ax2.set_ylabel('XRT FTD (5-day sum)', fontsize=11)
    ax2.legend(loc='upper right')
    ax2.set_title('XRT 5-Day Rolling FTD Sum', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # Panel 3: Forward return distribution comparison
    for window, col, color in [('5d', 'fwd_5d_ret', '#2196F3'), ('10d', 'fwd_10d_ret', '#4CAF50'), ('20d', 'fwd_20d_ret', '#FF9800')]:
        spike_ret = merged.loc[spike_mask, col].dropna()
        if len(spike_ret) > 5:
            ax3.hist(spike_ret, bins=30, alpha=0.4, color=color, label=f'{window} post-spike (n={len(spike_ret)})')
    
    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_xlabel('Forward Return', fontsize=11)
    ax3.set_ylabel('Frequency', fontsize=11)
    ax3.set_title('Distribution of GME Forward Returns After XRT FTD Spikes', fontsize=12)
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = FIG_DIR / "xrt_ftd_rally_signal.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    # Save results
    out_path = RESULTS_DIR / "xrt_rally_signal.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 1 complete.")

if __name__ == "__main__":
    main()
