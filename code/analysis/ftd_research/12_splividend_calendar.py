#!/usr/bin/env python3
"""
Test 11: Splividend Impact + Options Expiry Pinning + FTD Calendar
  A) Did the July 2022 splividend change FTD dynamics? Before vs After
  B) Do FTDs cluster differently around weekly vs monthly vs quarterly OPEX?
  C) Build the "FTD Calendar" — which day-of-week and day-of-month do FTDs peak?
  D) Auto-correlation analysis — what's the natural frequency of GME FTD cycles?
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
from pathlib import Path
from datetime import timedelta, datetime
from scipy import stats, signal as sp_signal

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

def load_csv(name):
    path = DATA_DIR / f"{name}_ftd.csv"
    if path.exists():
        df = pd.read_csv(path, parse_dates=['date'])
        return df.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    return None

def main():
    print("=" * 70)
    print("TEST 11: Splividend Impact + OPEX Pinning + FTD Calendar")
    print("=" * 70)
    
    gme_ftd = load_csv("GME")
    xrt_ftd = load_csv("XRT")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()
    
    SPLIT_DATE = pd.Timestamp('2022-07-22')  # 4:1 stock split via dividend
    
    # ============================================================
    # PART A: Splividend Impact — Did T+33 Change After the Split?
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: Pre-Split vs Post-Split FTD Dynamics")
    print(f"{'='*60}")
    
    pre = gme_ftd[gme_ftd.index < SPLIT_DATE]
    post = gme_ftd[gme_ftd.index >= SPLIT_DATE]
    
    print(f"\n  {'Metric':<30} {'Pre-Split':>15} {'Post-Split':>15} {'Ratio':>8}")
    print("  " + "-" * 72)
    
    # Note: post-split share count is 4x, so FTD counts should be scaled
    print(f"  {'Mean FTD (raw)':<30} {pre['quantity'].mean():>15,.0f} {post['quantity'].mean():>15,.0f} {post['quantity'].mean()/pre['quantity'].mean():>7.2f}×")
    print(f"  {'Median FTD':<30} {pre['quantity'].median():>15,.0f} {post['quantity'].median():>15,.0f} {post['quantity'].median()/max(1,pre['quantity'].median()):>7.2f}×")
    print(f"  {'Max FTD':<30} {pre['quantity'].max():>15,.0f} {post['quantity'].max():>15,.0f}")
    print(f"  {'Days with FTDs':<30} {len(pre):>15,} {len(post):>15,}")
    print(f"  {'Mean FTD (split-adj, /4)':<30} {'—':>15} {post['quantity'].mean()/4:>15,.0f} {post['quantity'].mean()/4/pre['quantity'].mean():>7.2f}×")
    
    # 2σ thresholds by era
    pre_2s = pre['quantity'].mean() + 2 * pre['quantity'].std()
    post_2s = post['quantity'].mean() + 2 * post['quantity'].std()
    
    pre_spikes = pre[pre['quantity'] > pre_2s]
    post_spikes = post[post['quantity'] > post_2s]
    
    pre_days = (pre.index.max() - pre.index.min()).days
    post_days = (post.index.max() - post.index.min()).days
    
    print(f"\n  Spike frequency:")
    print(f"  {'Pre-split':<20} {len(pre_spikes):>4} spikes in {pre_days:,} days = 1 per {pre_days/max(1,len(pre_spikes)):.0f} days")
    print(f"  {'Post-split':<20} {len(post_spikes):>4} spikes in {post_days:,} days = 1 per {post_days/max(1,len(post_spikes)):.0f} days")
    
    # T+33 hit rate by era
    def t33_hit_rate(era_ftd, era_spikes, era_mean):
        hits = 0
        for sd in era_spikes.index:
            from datetime import timedelta
            echo_d = sd + timedelta(days=47)  # ~33 business days
            window = era_ftd[(era_ftd.index >= echo_d - timedelta(days=3)) & 
                            (era_ftd.index <= echo_d + timedelta(days=3))]
            if len(window) > 0 and window['quantity'].max() > era_mean:
                hits += 1
        return hits / len(era_spikes) if len(era_spikes) > 0 else 0
    
    pre_t33 = t33_hit_rate(pre, pre_spikes, pre['quantity'].mean())
    post_t33 = t33_hit_rate(post, post_spikes, post['quantity'].mean())
    
    print(f"\n  T+33 echo hit rate:")
    print(f"    Pre-split:  {pre_t33:.0%}")
    print(f"    Post-split: {post_t33:.0%}")
    if post_t33 >= pre_t33:
        print(f"    ✅ T+33 echo PERSISTS after splividend")
    else:
        print(f"    ⚠️ T+33 echo weakened after splividend ({pre_t33:.0%} → {post_t33:.0%})")
    
    results_a = {
        'pre_mean': float(pre['quantity'].mean()), 'post_mean': float(post['quantity'].mean()),
        'pre_spikes': int(len(pre_spikes)), 'post_spikes': int(len(post_spikes)),
        'pre_t33_hit': float(pre_t33), 'post_t33_hit': float(post_t33),
    }
    
    # ============================================================
    # PART B: Day-of-Week FTD Calendar
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Day-of-Week FTD Calendar (Settlement Patterns)")
    print(f"{'='*60}")
    
    gme_copy = gme_ftd.copy()
    gme_copy['dow'] = gme_copy.index.dayofweek
    gme_copy['dom'] = gme_copy.index.day
    
    dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    dow_stats = gme_copy.groupby('dow')['quantity'].agg(['mean', 'median', 'count'])
    
    print(f"\n  {'Day':<12} {'Mean FTD':>12} {'Median FTD':>12} {'Days':>6}")
    print("  " + "-" * 45)
    for dow in range(5):
        if dow in dow_stats.index:
            print(f"  {dow_names[dow]:<12} {dow_stats.loc[dow, 'mean']:>12,.0f} {dow_stats.loc[dow, 'median']:>12,.0f} {int(dow_stats.loc[dow, 'count']):>6}")
    
    # ANOVA test
    from scipy.stats import kruskal
    groups = [gme_copy[gme_copy['dow'] == d]['quantity'].values for d in range(5)]
    kw_stat, kw_p = kruskal(*groups)
    print(f"\n  Kruskal-Wallis test (day-of-week effect):")
    print(f"    H-statistic: {kw_stat:.2f}")
    print(f"    p-value:     {kw_p:.4f}")
    
    # ============================================================
    # PART C: Day-of-Month FTD Calendar
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: Day-of-Month FTD Calendar (Settlement Cycles)")
    print(f"{'='*60}")
    
    dom_stats = gme_copy.groupby('dom')['quantity'].agg(['mean', 'count'])
    
    # Find the top 5 days
    top_doms = dom_stats.nlargest(5, 'mean')
    print(f"\n  Top 5 days of month for GME FTDs:")
    for dom, row in top_doms.iterrows():
        print(f"    Day {dom:>2}: {row['mean']:>12,.0f} (n={int(row['count'])})")
    
    bottom_doms = dom_stats.nsmallest(5, 'mean')
    print(f"\n  Bottom 5 days of month:")
    for dom, row in bottom_doms.iterrows():
        print(f"    Day {dom:>2}: {row['mean']:>12,.0f} (n={int(row['count'])})")
    
    # ============================================================
    # PART D: Auto-correlation — Natural FTD Cycle Frequency
    # ============================================================
    print(f"\n{'='*60}")
    print("PART D: Auto-Correlation — Natural FTD Cycle Frequency")
    print(f"{'='*60}")
    
    # Build daily series
    all_dates = pd.date_range('2018-01-01', '2026-01-31', freq='B')
    daily = pd.DataFrame(index=all_dates)
    daily['gme_ftd'] = gme_ftd['quantity'].reindex(all_dates).fillna(0)
    
    # Auto-correlation at various lags
    max_lag = 50
    acf_vals = []
    series = daily['gme_ftd'].values
    n = len(series)
    
    for lag in range(1, max_lag + 1):
        corr = np.corrcoef(series[:-lag], series[lag:])[0, 1]
        acf_vals.append({'lag': lag, 'correlation': float(corr)})
    
    # Find peaks
    correlations = [a['correlation'] for a in acf_vals]
    peaks, props = sp_signal.find_peaks(correlations, height=0.02, distance=3)
    
    print(f"\n  Auto-correlation peaks (natural FTD cycle):")
    print(f"  {'Lag (days)':>12} {'Correlation':>13}")
    print("  " + "-" * 28)
    for p in peaks:
        lag = acf_vals[p]['lag']
        corr = acf_vals[p]['correlation']
        biz_days = f" (~{lag} business days)"
        print(f"  {lag:>12} {corr:>12.3f}{biz_days}")
    
    # Specifically check key settlement lags
    print(f"\n  Key settlement lag correlations:")
    for lag_check in [6, 13, 21, 33, 35]:
        if lag_check <= max_lag:
            corr = acf_vals[lag_check - 1]['correlation']
            label = {6: 'CNS', 13: 'Reg SHO', 21: 'Legacy', 33: 'Re-FTD', 35: 'SEC Rule'}[lag_check]
            marker = " ⭐" if corr == max(correlations[12:36]) else ""
            print(f"    T+{lag_check:<3} ({label:<8}): r = {corr:>.3f}{marker}")
    
    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Splividend Impact, Calendar Effects, and Auto-Correlation', fontsize=14, fontweight='bold', y=0.98)
    
    # Panel 1: Pre vs Post split FTDs
    ax = axes[0, 0]
    ax.plot(pre.index, pre['quantity'], color='steelblue', linewidth=0.5, label='Pre-split')
    ax.plot(post.index, post['quantity'], color='red', linewidth=0.5, label='Post-split')
    ax.axvline(x=SPLIT_DATE, color='gold', linewidth=2, linestyle='--', label='Splividend (Jul 22)')
    ax.set_ylabel('GME FTD Count')
    ax.set_title('GME FTDs: Pre vs Post Splividend', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    
    # Panel 2: Day of week
    ax = axes[0, 1]
    means = [dow_stats.loc[d, 'mean'] if d in dow_stats.index else 0 for d in range(5)]
    ax.bar(dow_names, means, color='steelblue', alpha=0.7, edgecolor='black')
    ax.set_ylabel('Mean GME FTD')
    ax.set_title(f'Day-of-Week Calendar (KW p={kw_p:.3f})', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Day of month
    ax = axes[1, 0]
    doms = list(range(1, 32))
    dom_means = [dom_stats.loc[d, 'mean'] if d in dom_stats.index else 0 for d in doms]
    ax.bar(doms, dom_means, color='steelblue', alpha=0.7, edgecolor='black')
    ax.set_xlabel('Day of Month')
    ax.set_ylabel('Mean GME FTD')
    ax.set_title('Day-of-Month FTD Calendar', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 4: Auto-correlation
    ax = axes[1, 1]
    lags = [a['lag'] for a in acf_vals]
    corrs = [a['correlation'] for a in acf_vals]
    ax.bar(lags, corrs, color='steelblue', alpha=0.7, edgecolor='none')
    for p in peaks:
        ax.bar(acf_vals[p]['lag'], acf_vals[p]['correlation'], color='red', alpha=0.8)
    # Mark key settlement lags
    for lag_check in [13, 33, 35]:
        ax.axvline(x=lag_check, color='gold', linewidth=1, linestyle='--', alpha=0.7)
        ax.text(lag_check, max(corrs) * 0.9, f'T+{lag_check}', fontsize=7, ha='center')
    ax.set_xlabel('Lag (business days)')
    ax.set_ylabel('Auto-correlation')
    ax.set_title('GME FTD Auto-Correlation Function', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = FIG_DIR / "splividend_calendar.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    results = {
        'part_a_split': results_a,
        'part_b_dow': {dow_names[d]: float(dow_stats.loc[d, 'mean']) for d in range(5) if d in dow_stats.index},
        'part_c_top_doms': {int(d): float(r['mean']) for d, r in top_doms.iterrows()},
        'part_d_acf_peaks': [{'lag': int(acf_vals[p]['lag']), 'correlation': float(acf_vals[p]['correlation'])} for p in peaks],
        'part_d_settlement_lags': {
            f'T+{lag}': float(acf_vals[lag-1]['correlation']) 
            for lag in [6, 13, 21, 33, 35] if lag <= max_lag
        },
    }
    
    out_path = RESULTS_DIR / "splividend_calendar.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 11 complete.")

if __name__ == "__main__":
    main()
