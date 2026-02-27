#!/usr/bin/env python3
"""
Test 10: T+13 vs T+33 Timing + "Perfect Storm" Composite Signal
  A) Does T+13 (Reg SHO mandatory close-out) matter vs T+33 (re-FTD)?
  B) "Perfect Storm" — what happens when FTD velocity Q5 + monthly OPEX echo + 
     downtrend all converge?
  C) Volatility clustering — do T+33 echo windows have higher realized vol?
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
    print("TEST 10: T+13 vs T+33 + Perfect Storm + Volatility Clustering")
    print("=" * 70)
    
    gme_ftd = load_csv("GME")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()
    
    mean_ftd = gme_ftd['quantity'].mean()
    std_ftd = gme_ftd['quantity'].std()
    threshold_2s = mean_ftd + 2 * std_ftd
    spikes = gme_ftd[gme_ftd['quantity'] > threshold_2s]
    
    monthly_opex = get_monthly_opex()
    quad_witching = get_quad_witching()
    qw_set = set(d.strftime('%Y-%m-%d') for d in quad_witching)
    monthly_only = [d for d in monthly_opex if d.strftime('%Y-%m-%d') not in qw_set]
    
    # ============================================================
    # PART A: T+13 vs T+33 — Which Settlement Deadline Matters?
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: T+13 (Reg SHO) vs T+33 (Re-FTD) vs T+6 (CNS)")
    print(f"{'='*60}")
    
    # Test multiple settlement windows
    windows = {
        'T+6 (CNS)': 6,
        'T+13 (Reg SHO)': 13,
        'T+21 (Legacy)': 21,
        'T+33 (Re-FTD)': 33,
        'T+35 (SEC Rule)': 35,
    }
    
    print(f"\n  {'Window':<20} {'Elevated%':>10} {'Re-spike%':>10} {'Mean FTD':>12} {'Mean 5d Ret':>12}")
    print("  " + "-" * 70)
    
    results_a = {}
    for label, days in windows.items():
        elevated = 0
        respike = 0
        ftd_vals = []
        rets_5d = []
        
        for spike_date in spikes.index:
            echo_d = add_business_days(spike_date, days)
            window = gme_ftd[(gme_ftd.index >= echo_d - timedelta(days=2)) & 
                            (gme_ftd.index <= echo_d + timedelta(days=2))]
            if len(window) > 0:
                max_ftd = window['quantity'].max()
                ftd_vals.append(max_ftd)
                if max_ftd > mean_ftd:
                    elevated += 1
                if max_ftd > threshold_2s:
                    respike += 1
            
            # Forward returns from echo date
            nearby = price_df[(price_df.index >= echo_d - timedelta(days=2)) & 
                             (price_df.index <= echo_d + timedelta(days=2))]
            if len(nearby) > 0:
                p = nearby['gme_close'].iloc[0]
                fwd = price_df[price_df.index > echo_d].head(5)
                if len(fwd) >= 5:
                    rets_5d.append(float(fwd.iloc[4]['gme_close'] / p - 1))
        
        n = len(spikes)
        e_pct = elevated / n if n > 0 else 0
        r_pct = respike / n if n > 0 else 0
        avg_ftd = np.mean(ftd_vals) if ftd_vals else 0
        avg_ret = np.mean(rets_5d) if rets_5d else 0
        
        print(f"  {label:<20} {e_pct:>9.0%} {r_pct:>10.0%} {avg_ftd:>12,.0f} {avg_ret:>11.2%}")
        results_a[label] = {
            'elevated_pct': float(e_pct), 'respike_pct': float(r_pct),
            'avg_ftd': float(avg_ftd), 'avg_5d_ret': float(avg_ret)
        }
    
    # Statistical comparison: T+13 vs T+33
    t13_hits = []
    t33_hits = []
    for spike_date in spikes.index:
        for days, hit_list in [(13, t13_hits), (33, t33_hits)]:
            echo_d = add_business_days(spike_date, days)
            window = gme_ftd[(gme_ftd.index >= echo_d - timedelta(days=2)) & 
                            (gme_ftd.index <= echo_d + timedelta(days=2))]
            if len(window) > 0:
                hit_list.append(1 if window['quantity'].max() > mean_ftd else 0)
            else:
                hit_list.append(0)
    
    t13_rate = np.mean(t13_hits)
    t33_rate = np.mean(t33_hits)
    # McNemar-like test (paired)
    both = sum(1 for a, b in zip(t13_hits, t33_hits) if a == 1 and b == 1)
    t13_only = sum(1 for a, b in zip(t13_hits, t33_hits) if a == 1 and b == 0)
    t33_only = sum(1 for a, b in zip(t13_hits, t33_hits) if a == 0 and b == 1)
    neither = sum(1 for a, b in zip(t13_hits, t33_hits) if a == 0 and b == 0)
    
    print(f"\n  T+13 vs T+33 Paired Analysis (n={len(spikes)} spikes):")
    print(f"    Both elevated:     {both}")
    print(f"    T+13 only:         {t13_only}")
    print(f"    T+33 only:         {t33_only}")
    print(f"    Neither:           {neither}")
    print(f"    T+13 hit rate:     {t13_rate:.0%}")
    print(f"    T+33 hit rate:     {t33_rate:.0%}")
    
    # ============================================================
    # PART B: "Perfect Storm" Composite Signal
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Perfect Storm — Multi-Signal Convergence")
    print(f"{'='*60}")
    
    # Build daily signal matrix
    all_dates = pd.date_range('2021-01-01', '2026-01-31', freq='B')
    signals = pd.DataFrame(index=all_dates)
    signals['gme_ftd'] = gme_ftd['quantity'].reindex(all_dates).fillna(0)
    signals['gme_close'] = price_df['gme_close'].reindex(all_dates).ffill()
    
    # Signal 1: FTD velocity in top quintile
    signals['ftd_5d'] = signals['gme_ftd'].rolling(5, min_periods=1).sum()
    signals['ftd_velocity'] = signals['ftd_5d'].diff(5)
    vel_80 = signals['ftd_velocity'].quantile(0.80)
    signals['sig_velocity'] = (signals['ftd_velocity'] > vel_80).astype(int)
    
    # Signal 2: Within T+33 echo window (±3d of any echo date)
    echo_dates = set()
    for spike_date in spikes.index:
        for gen in range(1, 3):
            ed = add_business_days(spike_date, 33 * gen)
            for offset in range(-3, 4):
                echo_dates.add(ed + timedelta(days=offset))
    signals['sig_echo'] = signals.index.isin(echo_dates).astype(int)
    
    # Signal 3: Near monthly OPEX (not QW) ±5d
    opex_dates = set()
    for d in monthly_only:
        for offset in range(-5, 6):
            opex_dates.add(d + timedelta(days=offset))
    signals['sig_opex'] = signals.index.isin(opex_dates).astype(int)
    
    # Signal 4: GME trending down (below 20d MA)
    signals['sig_downtrend'] = (signals['gme_close'] < signals['gme_close'].rolling(20).mean()).astype(int)
    
    # Forward returns
    signals['fwd_5d'] = signals['gme_close'].pct_change(5).shift(-5)
    signals['fwd_10d'] = signals['gme_close'].pct_change(10).shift(-10)
    signals['fwd_20d'] = signals['gme_close'].pct_change(20).shift(-20)
    
    # Signal count
    signals['signal_count'] = signals['sig_velocity'] + signals['sig_echo'] + signals['sig_opex'] + signals['sig_downtrend']
    
    print(f"\n  Signal count distribution → Forward returns:")
    print(f"  {'Signals':>8} {'Days':>6} {'Mean 5d':>9} {'Mean 10d':>10} {'Mean 20d':>10} {'% Pos 10d':>10}")
    print("  " + "-" * 60)
    
    results_b = {}
    for count in range(0, 5):
        mask = signals['signal_count'] == count
        r5 = signals.loc[mask, 'fwd_5d'].dropna()
        r10 = signals.loc[mask, 'fwd_10d'].dropna()
        r20 = signals.loc[mask, 'fwd_20d'].dropna()
        if len(r10) > 0:
            pct = (r10 > 0).mean()
            print(f"  {count:>8} {mask.sum():>6} {r5.mean():>8.2%} {r10.mean():>10.2%} {r20.mean():>10.2%} {pct:>10.1%}")
            results_b[str(count)] = {
                'n': int(mask.sum()), 'mean_5d': float(r5.mean()),
                'mean_10d': float(r10.mean()), 'mean_20d': float(r20.mean()),
                'pct_positive': float(pct)
            }
    
    # Show "Perfect Storm" events (3+ signals)
    storm = signals[signals['signal_count'] >= 3].copy()
    if len(storm) > 0:
        print(f"\n  'Perfect Storm' events (3+ signals converging):")
        print(f"  {'Date':<12} {'Vel':>4} {'Echo':>5} {'OPEX':>5} {'Down':>5} {'GME':>8} {'5d':>8} {'10d':>8} {'20d':>8}")
        print("  " + "-" * 70)
        for date, row in storm.head(20).iterrows():
            r5 = f"{row['fwd_5d']:.1%}" if pd.notna(row['fwd_5d']) else "N/A"
            r10 = f"{row['fwd_10d']:.1%}" if pd.notna(row['fwd_10d']) else "N/A"
            r20 = f"{row['fwd_20d']:.1%}" if pd.notna(row['fwd_20d']) else "N/A"
            gme = f"${row['gme_close']:.2f}" if pd.notna(row['gme_close']) else "N/A"
            print(f"  {date.strftime('%Y-%m-%d'):<12} {int(row['sig_velocity']):>4} {int(row['sig_echo']):>5} {int(row['sig_opex']):>5} {int(row['sig_downtrend']):>5} {gme:>8} {r5:>8} {r10:>8} {r20:>8}")
    
    # ============================================================
    # PART C: Volatility Clustering Around Echo Windows
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: Volatility Clustering — Echo Windows vs Normal")
    print(f"{'='*60}")
    
    # Calculate realized volatility (5-day rolling)
    signals['log_ret'] = np.log(signals['gme_close'] / signals['gme_close'].shift(1))
    signals['realized_vol_5d'] = signals['log_ret'].rolling(5).std() * np.sqrt(252) * 100
    
    echo_vol = signals.loc[signals['sig_echo'] == 1, 'realized_vol_5d'].dropna()
    non_echo_vol = signals.loc[signals['sig_echo'] == 0, 'realized_vol_5d'].dropna()
    
    print(f"\n  Realized Volatility (annualized, 5-day rolling):")
    print(f"    Echo windows:      {echo_vol.mean():>6.1f}%  (median {echo_vol.median():.1f}%)")
    print(f"    Non-echo periods:  {non_echo_vol.mean():>6.1f}%  (median {non_echo_vol.median():.1f}%)")
    print(f"    Ratio:             {echo_vol.mean() / non_echo_vol.mean():>6.2f}×")
    
    u_stat, u_p = stats.mannwhitneyu(echo_vol, non_echo_vol, alternative='greater')
    print(f"    Mann-Whitney p:    {u_p:.4f}")
    
    # Also check: does volatility predict forward returns?
    signals_clean = signals.dropna(subset=['realized_vol_5d', 'fwd_10d'])
    vol_corr = signals_clean['realized_vol_5d'].corr(signals_clean['fwd_10d'].abs())
    print(f"\n  Vol → Absolute 10d return correlation: {vol_corr:.3f}")
    
    # ============================================================
    # PART D: Optimal Echo Window Size
    # ============================================================
    print(f"\n{'='*60}")
    print("PART D: Is T+33 Exactly Right? Testing T+30 through T+36")
    print(f"{'='*60}")
    
    print(f"\n  {'Window':>8} {'Elevated%':>10} {'Re-spike%':>10} {'Mean FTD':>12}")
    print("  " + "-" * 45)
    
    best_hit = 0
    best_day = 33
    for test_day in range(30, 37):
        elevated = 0
        respike = 0
        ftd_vals = []
        for spike_date in spikes.index:
            echo_d = add_business_days(spike_date, test_day)
            window = gme_ftd[(gme_ftd.index >= echo_d - timedelta(days=1)) & 
                            (gme_ftd.index <= echo_d + timedelta(days=1))]
            if len(window) > 0:
                max_ftd = window['quantity'].max()
                ftd_vals.append(max_ftd)
                if max_ftd > mean_ftd:
                    elevated += 1
                if max_ftd > threshold_2s:
                    respike += 1
        
        n = len(spikes)
        e_pct = elevated / n if n > 0 else 0
        r_pct = respike / n if n > 0 else 0
        avg_ftd = np.mean(ftd_vals) if ftd_vals else 0
        marker = " ⭐" if e_pct >= best_hit and test_day != 33 else (" ←" if test_day == 33 else "")
        if e_pct > best_hit:
            best_hit = e_pct
            best_day = test_day
        print(f"  T+{test_day:<5} {e_pct:>9.0%} {r_pct:>10.0%} {avg_ftd:>12,.0f}{marker}")
    
    print(f"\n  Best window: T+{best_day} ({best_hit:.0%} elevated)")
    
    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Advanced: T+13 vs T+33, Perfect Storm, Volatility', fontsize=14, fontweight='bold', y=0.98)
    
    # Panel 1: Settlement window hit rates
    ax = axes[0, 0]
    labels = list(results_a.keys())
    vals = [results_a[l]['elevated_pct'] * 100 for l in labels]
    colors_bar = ['steelblue' if 'T+33' not in l else 'red' for l in labels]
    ax.bar(range(len(labels)), vals, color=colors_bar, alpha=0.7, edgecolor='black')
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels([l.split(' ')[0] for l in labels], fontsize=9)
    ax.set_ylabel('Elevated Hit Rate (%)')
    ax.set_title('Settlement Window Comparison', fontsize=10)
    ax.axhline(y=50, color='gray', linestyle='--', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='y')
    for i, v in enumerate(vals):
        ax.text(i, v + 1, f'{v:.0f}%', ha='center', fontsize=8)
    
    # Panel 2: Perfect Storm signal count vs returns
    ax = axes[0, 1]
    counts = [int(k) for k in results_b.keys()]
    rets = [results_b[k]['mean_10d'] * 100 for k in results_b.keys()]
    c_colors = ['green' if r > 0 else 'red' for r in rets]
    ax.bar(counts, rets, color=c_colors, alpha=0.7, edgecolor='black')
    ax.set_xlabel('Number of Converging Signals')
    ax.set_ylabel('Mean 10d Forward Return (%)')
    ax.set_title('"Perfect Storm" Signal Convergence', fontsize=10)
    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Echo vs non-echo volatility distribution
    ax = axes[1, 0]
    ax.hist(non_echo_vol, bins=50, alpha=0.5, color='steelblue', label=f'Non-echo ({non_echo_vol.mean():.0f}%)', density=True)
    ax.hist(echo_vol, bins=50, alpha=0.5, color='red', label=f'Echo window ({echo_vol.mean():.0f}%)', density=True)
    ax.set_xlabel('5-day Realized Volatility (annualized %)')
    ax.set_ylabel('Density')
    ax.set_title(f'Volatility in Echo Windows (p={u_p:.4f})', fontsize=10)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Panel 4: Perfect Storm events on price chart
    ax = axes[1, 1]
    ax.plot(signals.index, signals['gme_close'], color='#1a1a2e', linewidth=0.8, label='GME Close')
    if len(storm) > 0:
        ax.scatter(storm.index, storm['gme_close'], color='gold', s=40, zorder=5,
                  edgecolors='red', linewidth=1, label=f'3+ signals (n={len(storm)})')
    ax.set_ylabel('GME Price ($)')
    ax.legend(fontsize=8)
    ax.set_title('Perfect Storm Events on GME Price', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = FIG_DIR / "advanced_signals.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    results = {
        'part_a_settlement': results_a,
        'part_a_paired': {
            'both': int(both), 't13_only': int(t13_only), 
            't33_only': int(t33_only), 'neither': int(neither)
        },
        'part_b_storm': results_b,
        'part_c_volatility': {
            'echo_vol_mean': float(echo_vol.mean()),
            'non_echo_vol_mean': float(non_echo_vol.mean()),
            'ratio': float(echo_vol.mean() / non_echo_vol.mean()),
            'p_value': float(u_p)
        },
        'part_d_optimal_window': {'best_day': int(best_day), 'best_hit': float(best_hit)},
    }
    
    out_path = RESULTS_DIR / "advanced_signals.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 10 complete.")

if __name__ == "__main__":
    main()
