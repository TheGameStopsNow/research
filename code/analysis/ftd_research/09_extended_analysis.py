#!/usr/bin/env python3
"""
Test 8: Monthly OPEX Echo Convergence + Regime Analysis + AMC Control
Three-part deep analysis:
  A) Do T+33 echoes near monthly OPEX behave differently than quad witching?
  B) Has the T+33 pattern changed over time (regime shifts)?
  C) Does AMC show the same T+33 echo? If not → GME-specific
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

def add_business_days(date, n):
    current = date
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current

def get_monthly_opex(start_year=2021, end_year=2026):
    """3rd Friday of every month"""
    dates = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            first_day = datetime(year, month, 1)
            days_until_friday = (4 - first_day.weekday()) % 7
            first_friday = first_day + timedelta(days=days_until_friday)
            third_friday = first_friday + timedelta(weeks=2)
            dates.append(pd.Timestamp(third_friday))
    return sorted(dates)

def get_quad_witching(start_year=2021, end_year=2026):
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
    print("TEST 8: OPEX Echo + Regime Analysis + AMC Control")
    print("=" * 70)
    
    gme_ftd = load_csv("GME")
    amc_ftd = load_csv("AMC")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()
    
    monthly_opex = get_monthly_opex()
    quad_witching = set(d.strftime('%Y-%m-%d') for d in get_quad_witching())
    
    # Split OPEX into quad witching and monthly-only
    monthly_only = [d for d in monthly_opex if d.strftime('%Y-%m-%d') not in quad_witching]
    
    mean_ftd = gme_ftd['quantity'].mean()
    std_ftd = gme_ftd['quantity'].std()
    threshold_2s = mean_ftd + 2 * std_ftd
    spikes = gme_ftd[gme_ftd['quantity'] > threshold_2s]
    
    # ============================================================
    # PART A: Monthly OPEX vs Quad Witching Echo Convergence
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: T+33 Echo Proximity — Monthly OPEX vs Quad Witching")
    print(f"{'='*60}")
    
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
    
    # Classify each echo: near QW, near monthly OPEX only, or far from both
    echo_buckets = {'quad_witching': [], 'monthly_opex': [], 'neither': []}
    
    for echo in echoes:
        ed = echo['echo_date']
        
        # Check proximity
        qw_gap = min(abs((ed - pd.Timestamp(d)).days) for d in get_quad_witching())
        mo_gap = min(abs((ed - d).days) for d in monthly_only)
        
        # Get price/returns
        nearby = price_df[(price_df.index >= ed - timedelta(days=3)) & (price_df.index <= ed + timedelta(days=3))]
        if len(nearby) == 0:
            continue
        price = nearby['gme_close'].iloc[0]
        fwd = price_df[price_df.index > ed].head(10)
        ret_5d = float(fwd.iloc[4]['gme_close'] / price - 1) if len(fwd) >= 5 else None
        ret_10d = float(fwd.iloc[9]['gme_close'] / price - 1) if len(fwd) >= 10 else None
        
        entry = {**echo, 'price': price, 'ret_5d': ret_5d, 'ret_10d': ret_10d,
                 'qw_gap': qw_gap, 'mo_gap': mo_gap}
        
        if qw_gap <= 5:
            echo_buckets['quad_witching'].append(entry)
        elif mo_gap <= 5:
            echo_buckets['monthly_opex'].append(entry)
        else:
            echo_buckets['neither'].append(entry)
    
    print(f"\n  Echo classification:")
    print(f"  {'Bucket':<20} {'Count':>6} {'Mean 5d':>10} {'Mean 10d':>10} {'% Positive 10d':>15}")
    print("  " + "-" * 65)
    
    results_a = {}
    for bucket, events in echo_buckets.items():
        r5 = [e['ret_5d'] for e in events if e['ret_5d'] is not None]
        r10 = [e['ret_10d'] for e in events if e['ret_10d'] is not None]
        if r10:
            pct_pos = sum(1 for r in r10 if r > 0) / len(r10)
            print(f"  {bucket:<20} {len(events):>6} {np.mean(r5):>9.2%} {np.mean(r10):>10.2%} {pct_pos:>14.1%}")
            results_a[bucket] = {
                'n': len(events), 'mean_5d': float(np.mean(r5)),
                'mean_10d': float(np.mean(r10)), 'pct_positive': float(pct_pos)
            }
    
    # ============================================================
    # PART B: Regime Analysis — Has T+33 changed over time?
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Regime Analysis — T+33 Hit Rate Over Time")
    print(f"{'='*60}")
    
    # Define regimes
    regimes = {
        'Pre-sneeze (Dec 2020)': ('2020-12-01', '2021-01-24'),
        'Sneeze (Jan-Mar 2021)': ('2021-01-25', '2021-03-31'),
        'Post-sneeze 2021': ('2021-04-01', '2021-12-31'),
        '2022 pre-split': ('2022-01-01', '2022-07-21'),
        '2022 post-split': ('2022-07-22', '2022-12-31'),
        '2023': ('2023-01-01', '2023-12-31'),
        '2024 (DFV return)': ('2024-01-01', '2024-12-31'),
        '2025': ('2025-01-01', '2025-12-31'),
    }
    
    print(f"\n  {'Regime':<25} {'Spikes':>7} {'E1 Hit%':>8} {'E1 Spike%':>10} {'Avg FTD':>10}")
    print("  " + "-" * 65)
    
    results_b = {}
    for name, (start, end) in regimes.items():
        start_d, end_d = pd.Timestamp(start), pd.Timestamp(end)
        regime_spikes = spikes[(spikes.index >= start_d) & (spikes.index <= end_d)]
        
        if len(regime_spikes) == 0:
            print(f"  {name:<25} {0:>7}")
            continue
        
        # Check T+33 hit rate for this regime's spikes
        hits = 0
        respikes = 0
        for spike_date in regime_spikes.index:
            echo_d = add_business_days(spike_date, 33)
            # Check ±2 day window
            window = gme_ftd[(gme_ftd.index >= echo_d - timedelta(days=3)) & 
                            (gme_ftd.index <= echo_d + timedelta(days=3))]
            if len(window) > 0:
                max_ftd = window['quantity'].max()
                if max_ftd > mean_ftd:
                    hits += 1
                if max_ftd > threshold_2s:
                    respikes += 1
        
        hit_pct = hits / len(regime_spikes) if len(regime_spikes) > 0 else 0
        spike_pct = respikes / len(regime_spikes) if len(regime_spikes) > 0 else 0
        avg_ftd = regime_spikes['quantity'].mean()
        
        print(f"  {name:<25} {len(regime_spikes):>7} {hit_pct:>7.0%} {spike_pct:>9.0%} {avg_ftd:>10,.0f}")
        results_b[name] = {
            'spikes': int(len(regime_spikes)),
            'e1_hit_rate': float(hit_pct),
            'e1_spike_rate': float(spike_pct),
            'avg_ftd': float(avg_ftd)
        }
    
    # ============================================================
    # PART C: AMC Control — Does AMC show T+33 echo?
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: AMC Control — Does AMC show T+33 echo pattern?")
    print(f"{'='*60}")
    
    amc_mean = amc_ftd['quantity'].mean()
    amc_std = amc_ftd['quantity'].std()
    amc_2s = amc_mean + 2 * amc_std
    amc_spikes = amc_ftd[amc_ftd['quantity'] > amc_2s]
    
    print(f"\n  AMC FTD statistics:")
    print(f"    Mean:    {amc_mean:>12,.0f}")
    print(f"    2σ:      {amc_2s:>12,.0f}")
    print(f"    Spikes:  {len(amc_spikes):>12}")
    
    # T+33 echo hit rate for AMC
    amc_hits = 0
    amc_respikes = 0
    for spike_date in amc_spikes.index:
        echo_d = add_business_days(spike_date, 33)
        window = amc_ftd[(amc_ftd.index >= echo_d - timedelta(days=3)) & 
                        (amc_ftd.index <= echo_d + timedelta(days=3))]
        if len(window) > 0:
            max_ftd = window['quantity'].max()
            if max_ftd > amc_mean:
                amc_hits += 1
            if max_ftd > amc_2s:
                amc_respikes += 1
    
    amc_hit_pct = amc_hits / len(amc_spikes) if len(amc_spikes) > 0 else 0
    amc_spike_pct = amc_respikes / len(amc_spikes) if len(amc_spikes) > 0 else 0
    
    # GME comparison
    gme_hits = 0
    for sd in spikes.index:
        echo_d = add_business_days(sd, 33)
        window = gme_ftd[(gme_ftd.index >= echo_d - timedelta(days=3)) & 
                        (gme_ftd.index <= echo_d + timedelta(days=3))]
        if len(window) > 0 and window['quantity'].max() > mean_ftd:
            gme_hits += 1
    gme_hit_pct = gme_hits / len(spikes) if len(spikes) > 0 else 0
    
    print(f"\n  T+33 Echo Hit Rate Comparison:")
    print(f"  {'Ticker':<8} {'Spikes':>8} {'E1 Elevated':>12} {'E1 Re-spike':>12}")
    print("  " + "-" * 45)
    print(f"  {'GME':<8} {len(spikes):>8} {gme_hit_pct:>11.0%} {'25%':>12}")
    print(f"  {'AMC':<8} {len(amc_spikes):>8} {amc_hit_pct:>11.0%} {amc_spike_pct:>11.0%}")
    
    # Also test KOSS
    koss_ftd = load_csv("KOSS")
    if koss_ftd is not None and len(koss_ftd) > 50:
        koss_mean = koss_ftd['quantity'].mean()
        koss_2s = koss_mean + 2 * koss_ftd['quantity'].std()
        koss_spikes = koss_ftd[koss_ftd['quantity'] > koss_2s]
        
        koss_hits = 0
        koss_respikes = 0
        for spike_date in koss_spikes.index:
            echo_d = add_business_days(spike_date, 33)
            window = koss_ftd[(koss_ftd.index >= echo_d - timedelta(days=3)) & 
                            (koss_ftd.index <= echo_d + timedelta(days=3))]
            if len(window) > 0:
                max_ftd = window['quantity'].max()
                if max_ftd > koss_mean:
                    koss_hits += 1
                if max_ftd > koss_2s:
                    koss_respikes += 1
        
        koss_hit_pct = koss_hits / len(koss_spikes) if len(koss_spikes) > 0 else 0
        koss_spike_pct = koss_respikes / len(koss_spikes) if len(koss_spikes) > 0 else 0
        print(f"  {'KOSS':<8} {len(koss_spikes):>8} {koss_hit_pct:>11.0%} {koss_spike_pct:>11.0%}")
    
    # Statistical test: is GME's hit rate significantly higher than AMC's?
    # Fisher's exact test
    gme_table = [[gme_hits, len(spikes) - gme_hits], [amc_hits, len(amc_spikes) - amc_hits]]
    odds_ratio, fisher_p = stats.fisher_exact(gme_table, alternative='greater')
    print(f"\n  Fisher's exact test (GME vs AMC):")
    print(f"    Odds ratio: {odds_ratio:.2f}")
    print(f"    p-value:    {fisher_p:.4f}")
    if fisher_p < 0.05:
        print(f"    Verdict:    ✅ GME T+33 echo is SIGNIFICANTLY stronger than AMC")
    else:
        print(f"    Verdict:    ⚠️ No significant difference (p={fisher_p:.3f})")
    
    # ============================================================
    # PART D: FTD Velocity Signal
    # ============================================================
    print(f"\n{'='*60}")
    print("PART D: FTD Velocity Signal — Rate of Change Matters")
    print(f"{'='*60}")
    
    # Build daily GME FTD series
    all_dates = pd.date_range('2021-01-01', '2026-01-31', freq='B')
    daily = pd.DataFrame(index=all_dates)
    daily['gme_ftd'] = gme_ftd['quantity'].reindex(all_dates).fillna(0)
    daily['gme_close'] = price_df['gme_close'].reindex(all_dates).ffill()
    
    # FTD velocity = 5d change in rolling FTD sum
    daily['ftd_5d'] = daily['gme_ftd'].rolling(5, min_periods=1).sum()
    daily['ftd_velocity'] = daily['ftd_5d'].diff(5)  # 5-day change
    daily['ftd_acceleration'] = daily['ftd_velocity'].diff(5)  # acceleration
    
    # Forward returns
    daily['fwd_5d'] = daily['gme_close'].pct_change(5).shift(-5)
    daily['fwd_10d'] = daily['gme_close'].pct_change(10).shift(-10)
    
    # Quintile analysis
    daily_clean = daily.dropna(subset=['ftd_velocity', 'fwd_10d'])
    daily_clean['vel_quintile'] = pd.qcut(daily_clean['ftd_velocity'], 5, labels=['Q1 (falling)', 'Q2', 'Q3', 'Q4', 'Q5 (surging)'])
    
    print(f"\n  GME FTD Velocity Quintile Analysis:")
    print(f"  {'Quintile':<18} {'Mean Vel':>12} {'Mean 5d Ret':>12} {'Mean 10d Ret':>13} {'N':>6}")
    print("  " + "-" * 65)
    
    results_d = {}
    for q in ['Q1 (falling)', 'Q2', 'Q3', 'Q4', 'Q5 (surging)']:
        qdata = daily_clean[daily_clean['vel_quintile'] == q]
        if len(qdata) > 0:
            print(f"  {q:<18} {qdata['ftd_velocity'].mean():>12,.0f} {qdata['fwd_5d'].mean():>11.2%} {qdata['fwd_10d'].mean():>13.2%} {len(qdata):>6}")
            results_d[q] = {
                'mean_velocity': float(qdata['ftd_velocity'].mean()),
                'mean_5d_ret': float(qdata['fwd_5d'].mean()),
                'mean_10d_ret': float(qdata['fwd_10d'].mean()),
                'n': int(len(qdata))
            }
    
    # Acceleration analysis
    daily_clean['accel_quintile'] = pd.qcut(daily_clean['ftd_acceleration'].dropna(), 5, 
                                             labels=['A1 (decelerating)', 'A2', 'A3', 'A4', 'A5 (accelerating)'])
    
    print(f"\n  GME FTD Acceleration Quintile Analysis:")
    print(f"  {'Quintile':<22} {'Mean Accel':>12} {'Mean 10d Ret':>13} {'N':>6}")
    print("  " + "-" * 55)
    
    for q in ['A1 (decelerating)', 'A2', 'A3', 'A4', 'A5 (accelerating)']:
        qdata = daily_clean[daily_clean['accel_quintile'] == q]
        if len(qdata) > 0:
            print(f"  {q:<22} {qdata['ftd_acceleration'].mean():>12,.0f} {qdata['fwd_10d'].mean():>13.2%} {len(qdata):>6}")
    
    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Extended Analysis: OPEX, Regime, Control, Velocity', fontsize=14, fontweight='bold', y=0.98)
    
    # Panel 1: Echo proximity returns by OPEX type
    ax = axes[0, 0]
    buckets = list(results_a.keys())
    means = [results_a[b]['mean_10d'] for b in buckets]
    colors = ['red' if m < 0 else 'green' for m in means]
    bars = ax.bar(buckets, [m * 100 for m in means], color=colors, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Mean 10d Forward Return (%)')
    ax.set_title('T+33 Echo Returns by OPEX Proximity')
    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='y')
    for bar, m in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5 * (1 if m >= 0 else -1),
                f'{m:.1%}', ha='center', va='bottom' if m >= 0 else 'top', fontsize=9)
    
    # Panel 2: Regime analysis
    ax = axes[0, 1]
    regime_names = list(results_b.keys())
    hit_rates = [results_b[r]['e1_hit_rate'] * 100 for r in regime_names]
    ax.barh(regime_names, hit_rates, color='steelblue', alpha=0.7, edgecolor='black')
    ax.axvline(x=50, color='red', linestyle='--', linewidth=1, label='50% (chance)')
    ax.set_xlabel('T+33 Echo Hit Rate (%)')
    ax.set_title('T+33 Hit Rate by Market Regime')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='x')
    
    # Panel 3: AMC vs GME control comparison
    ax = axes[1, 0]
    tickers = ['GME', 'AMC']
    hit_vals = [gme_hit_pct * 100, amc_hit_pct * 100]
    bar_colors = ['steelblue', 'orange']
    ax.bar(tickers, hit_vals, color=bar_colors, alpha=0.7, edgecolor='black')
    ax.set_ylabel('T+33 Elevated Hit Rate (%)')
    ax.set_title(f'T+33 Echo: GME vs AMC Control (Fisher p={fisher_p:.3f})')
    ax.axhline(y=50, color='red', linestyle='--', linewidth=1, label='50% (chance)')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    for i, (t, v) in enumerate(zip(tickers, hit_vals)):
        ax.text(i, v + 1, f'{v:.0f}%', ha='center', fontsize=11, fontweight='bold')
    
    # Panel 4: FTD Velocity quintiles
    ax = axes[1, 1]
    q_labels = list(results_d.keys())
    q_rets = [results_d[q]['mean_10d_ret'] * 100 for q in q_labels]
    q_colors = ['red' if r < 0 else 'green' for r in q_rets]
    ax.bar(range(len(q_labels)), q_rets, color=q_colors, alpha=0.7, edgecolor='black')
    ax.set_xticks(range(len(q_labels)))
    ax.set_xticklabels(['Q1\nFalling', 'Q2', 'Q3', 'Q4', 'Q5\nSurging'], fontsize=8)
    ax.set_ylabel('Mean 10d Forward Return (%)')
    ax.set_title('GME FTD Velocity Quintiles → Forward Returns')
    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    fig_path = FIG_DIR / "extended_analysis.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    results = {
        'part_a_opex_echo': results_a,
        'part_b_regime': results_b,
        'part_c_control': {
            'gme_hit_rate': float(gme_hit_pct),
            'amc_hit_rate': float(amc_hit_pct),
            'fisher_p': float(fisher_p),
            'odds_ratio': float(odds_ratio),
        },
        'part_d_velocity': results_d,
    }
    
    out_path = RESULTS_DIR / "extended_analysis.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 8 complete.")

if __name__ == "__main__":
    main()
