#!/usr/bin/env python3
"""
Test 3: T+33 FTD Echo Cascade
beckettcat hypothesis: FTDs don't just settle at T+33 — they re-FTD, creating a
repeating cascade. Original FTD → T+33 → re-FTD → T+66 → ...
Each cycle generates a new forcing date for GME price action.
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

def add_business_days(date, n):
    """Add n business days to a date."""
    current = date
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri
            added += 1
    return current

def main():
    print("=" * 70)
    print("TEST 3: T+33 FTD Echo Cascade")
    print("=" * 70)
    
    # Load data
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
    
    # Stats
    mean_ftd = gme_daily['quantity'].mean()
    std_ftd = gme_daily['quantity'].std()
    threshold_3sigma = mean_ftd + 3 * std_ftd
    threshold_2sigma = mean_ftd + 2 * std_ftd
    
    print(f"\n  GME FTD statistics:")
    print(f"    Mean:       {mean_ftd:>12,.0f}")
    print(f"    Std:        {std_ftd:>12,.0f}")
    print(f"    2σ thresh:  {threshold_2sigma:>12,.0f}")
    print(f"    3σ thresh:  {threshold_3sigma:>12,.0f}")
    
    # Find initial FTD spikes (>2σ)
    spikes = gme_daily[gme_daily['quantity'] > threshold_2sigma].copy()
    print(f"\n  Initial FTD spikes (>2σ): {len(spikes)}")
    
    # For each spike, project T+33 echo dates and check for re-FTDs
    cascade_results = []
    
    for spike_date, spike_row in spikes.iterrows():
        chain = [{
            'generation': 0,
            'date': spike_date.strftime('%Y-%m-%d'),
            'ftd': int(spike_row['quantity']),
            'is_elevated': True
        }]
        
        current_date = spike_date
        for gen in range(1, 5):  # Up to 4 echoes (T+33, T+66, T+99, T+132)
            echo_date = add_business_days(current_date, 33)
            
            # Check FTD level at echo date (±2 business days window)
            echo_window = gme_daily[
                (gme_daily.index >= echo_date - timedelta(days=4)) &
                (gme_daily.index <= echo_date + timedelta(days=4))
            ]
            
            if len(echo_window) > 0:
                max_ftd = echo_window['quantity'].max()
                max_date = echo_window['quantity'].idxmax()
                is_elevated = max_ftd > mean_ftd
                is_spike = max_ftd > threshold_2sigma
                
                chain.append({
                    'generation': gen,
                    'date': max_date.strftime('%Y-%m-%d'),
                    'expected_date': echo_date.strftime('%Y-%m-%d'),
                    'ftd': int(max_ftd),
                    'is_elevated': bool(is_elevated),
                    'is_spike': bool(is_spike)
                })
                current_date = max_date
            else:
                chain.append({
                    'generation': gen,
                    'date': echo_date.strftime('%Y-%m-%d'),
                    'expected_date': echo_date.strftime('%Y-%m-%d'),
                    'ftd': 0,
                    'is_elevated': False,
                    'is_spike': False
                })
                break
        
        cascade_results.append({
            'origin_date': spike_date.strftime('%Y-%m-%d'),
            'origin_ftd': int(spike_row['quantity']),
            'chain': chain,
            'echo_hit_rate': sum(1 for c in chain[1:] if c['is_elevated']) / max(1, len(chain) - 1)
        })
    
    # Aggregate echo hit rate
    echo_stats = {gen: {'elevated': 0, 'spike': 0, 'total': 0} 
                  for gen in range(1, 5)}
    
    for cascade in cascade_results:
        for link in cascade['chain']:
            if link['generation'] > 0:
                gen = link['generation']
                if gen in echo_stats:
                    echo_stats[gen]['total'] += 1
                    if link.get('is_elevated', False):
                        echo_stats[gen]['elevated'] += 1
                    if link.get('is_spike', False):
                        echo_stats[gen]['spike'] += 1
    
    print(f"\n  Echo Cascade Hit Rates:")
    print(f"  {'Generation':<12} {'T+days':<8} {'Elevated':>10} {'Re-spike':>10} {'Total':>8} {'Elev %':>8} {'Spike %':>8}")
    print("  " + "-" * 70)
    
    for gen in range(1, 5):
        s = echo_stats[gen]
        t_days = gen * 33
        elev_pct = s['elevated'] / max(1, s['total']) * 100
        spike_pct = s['spike'] / max(1, s['total']) * 100
        verdict = "✅" if elev_pct > 60 else ("⚠️" if elev_pct > 40 else "❌")
        print(f"  {f'Echo {gen}':<12} {f'T+{t_days}':<8} {s['elevated']:>10} {s['spike']:>10} {s['total']:>8} {elev_pct:>7.1f}% {spike_pct:>7.1f}% {verdict}")
    
    # Cross-reference echo dates with GME price action
    print(f"\n  Echo Date → GME Price Action (±3 day window):")
    print(f"  {'Echo Date':<12} {'Gen':<6} {'FTD':>10} {'GME Price':>10} {'3d Ret':>8} {'5d Ret':>8}")
    print("  " + "-" * 60)
    
    price_hits = []
    for cascade in cascade_results[:10]:  # Top 10 cascades
        for link in cascade['chain']:
            if link['generation'] > 0 and gme_price is not None:
                echo_date = pd.Timestamp(link['date'])
                # Get price and forward return
                nearby = gme_price[
                    (gme_price.index >= echo_date - timedelta(days=3)) &
                    (gme_price.index <= echo_date + timedelta(days=3))
                ]
                if len(nearby) > 0:
                    price = nearby['gme_close'].iloc[0]
                    # Forward returns
                    fwd = gme_price[gme_price.index > echo_date].head(5)
                    ret_3d = (fwd.iloc[2]['gme_close'] / price - 1) if len(fwd) >= 3 else None
                    ret_5d = (fwd.iloc[4]['gme_close'] / price - 1) if len(fwd) >= 5 else None
                    
                    r3 = f"{ret_3d:.1%}" if ret_3d is not None else "N/A"
                    r5 = f"{ret_5d:.1%}" if ret_5d is not None else "N/A"
                    gen_label = f'E{link["generation"]}'
                    print(f"  {link['date']:<12} {gen_label:<6} {link['ftd']:>10,} ${price:>8.2f} {r3:>8} {r5:>8}")
                    
                    price_hits.append({
                        'date': link['date'],
                        'generation': link['generation'],
                        'ftd': link['ftd'],
                        'price': float(price),
                        'ret_3d': float(ret_3d) if ret_3d is not None else None,
                        'ret_5d': float(ret_5d) if ret_5d is not None else None
                    })
    
    # Analyze if echo dates have systematically positive returns
    echo_returns_3d = [h['ret_3d'] for h in price_hits if h['ret_3d'] is not None]
    echo_returns_5d = [h['ret_5d'] for h in price_hits if h['ret_5d'] is not None]
    
    if echo_returns_3d:
        print(f"\n  Echo date forward return summary:")
        print(f"    3-day mean:  {np.mean(echo_returns_3d):.2%} (n={len(echo_returns_3d)}, positive: {sum(1 for r in echo_returns_3d if r > 0)}/{len(echo_returns_3d)})")
    if echo_returns_5d:
        print(f"    5-day mean:  {np.mean(echo_returns_5d):.2%} (n={len(echo_returns_5d)}, positive: {sum(1 for r in echo_returns_5d if r > 0)}/{len(echo_returns_5d)})")
    
    # ===== VISUALIZATION =====
    fig, axes = plt.subplots(2, 1, figsize=(16, 12), gridspec_kw={'height_ratios': [2, 1.5]})
    fig.suptitle('T+33 FTD Echo Cascade Analysis', fontsize=16, fontweight='bold', y=0.98)
    
    # Panel 1: GME FTD with echo markers
    axes[0].bar(gme_daily.index, gme_daily['quantity'], width=1, alpha=0.4, color='steelblue', label='GME Daily FTD')
    axes[0].axhline(y=threshold_2sigma, color='orange', linestyle='--', linewidth=1, label=f'2σ ({threshold_2sigma:,.0f})')
    axes[0].axhline(y=threshold_3sigma, color='red', linestyle='--', linewidth=1, label=f'3σ ({threshold_3sigma:,.0f})')
    axes[0].set_ylim(0, 2500000)  # Cap visually to avoid 3.2M outliers compressing the chart
    
    # Mark echo dates from top cascades
    echo_colors = {1: 'red', 2: 'orange', 3: 'purple', 4: 'green'}
    echo_labels_added = set()
    for cascade in cascade_results[:5]:
        for link in cascade['chain']:
            if link['generation'] > 0:
                echo_d = pd.Timestamp(link['date'])
                gen = link['generation']
                lbl = f'Echo {gen} (T+{gen*33})' if gen not in echo_labels_added else None
                if gen not in echo_labels_added:
                    echo_labels_added.add(gen)
                if echo_d in gme_daily.index:
                    axes[0].scatter([echo_d], [gme_daily.loc[echo_d, 'quantity']], 
                                  color=echo_colors.get(gen, 'gray'),
                                  s=40, zorder=5, marker='v', label=lbl)
    
    axes[0].set_ylabel('GME FTDs', fontsize=11)
    axes[0].legend(loc='upper right')
    axes[0].set_title('GME Daily FTDs with T+33 Echo Cascade Markers', fontsize=12)
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Echo hit rate by generation
    gens = list(range(1, 5))
    elev_rates = [echo_stats[g]['elevated'] / max(1, echo_stats[g]['total']) * 100 for g in gens]
    spike_rates = [echo_stats[g]['spike'] / max(1, echo_stats[g]['total']) * 100 for g in gens]
    
    x = np.arange(len(gens))
    width = 0.35
    axes[1].bar(x - width/2, elev_rates, width, color='steelblue', alpha=0.7, label='Elevated (>mean)')
    axes[1].bar(x + width/2, spike_rates, width, color='red', alpha=0.7, label='Re-spike (>2σ)')
    axes[1].axhline(y=50, color='gray', linestyle=':', linewidth=1, label='50% (chance)')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([f'T+{g*33}\n(Echo {g})' for g in gens])
    axes[1].set_ylabel('Hit Rate (%)', fontsize=11)
    axes[1].set_xlabel('Echo Generation', fontsize=11)
    axes[1].legend(loc='upper right')
    axes[1].set_title('T+33 Echo Cascade Hit Rates by Generation', fontsize=12)
    axes[1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    fig_path = FIG_DIR / "t33_echo_cascade.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    # Save results
    results = {
        'ftd_stats': {
            'mean': float(mean_ftd),
            'std': float(std_ftd),
            'threshold_2sigma': float(threshold_2sigma),
            'threshold_3sigma': float(threshold_3sigma),
            'initial_spikes': int(len(spikes))
        },
        'echo_hit_rates': {
            f'T+{gen*33}': {
                'elevated_rate': float(echo_stats[gen]['elevated'] / max(1, echo_stats[gen]['total'])),
                'spike_rate': float(echo_stats[gen]['spike'] / max(1, echo_stats[gen]['total'])),
                'total_tested': int(echo_stats[gen]['total'])
            }
            for gen in range(1, 5)
        },
        'top_cascades': cascade_results[:10],
        'echo_returns': {
            'mean_3d': float(np.mean(echo_returns_3d)) if echo_returns_3d else None,
            'mean_5d': float(np.mean(echo_returns_5d)) if echo_returns_5d else None,
            'n': len(echo_returns_3d)
        }
    }
    
    out_path = RESULTS_DIR / "t33_echo_cascade.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 3 complete.")

if __name__ == "__main__":
    main()
