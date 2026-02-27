#!/usr/bin/env python3
"""
Test 13: Deep OTM Put Forensics — Married Put / Reset Transaction Detection
Uses 424 ThetaData OI snapshots at the STRIKE level.

Hypothesis: If FTD obligations are being reset via married puts, we should see:
  A) Deep OTM put OI spikes 1-5 days before T+33 echo windows
  B) OTM put OI concentration in specific strike bands (far below price)
  C) OI buildup in puts that have no economic rationale (deep OTM, near-expiry)
  D) Asymmetric call/put OI changes around FTD spike dates
  E) "Phantom OI" — puts that appear and vanish within a few snapshots
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

def classify_moneyness(strike, price):
    """Classify a strike's moneyness relative to current price."""
    if price <= 0 or np.isnan(price):
        return 'unknown'
    ratio = strike / price
    if ratio < 0.3:
        return 'deep_otm_put'    # <30% of price — no legitimate hedge rationale
    elif ratio < 0.5:
        return 'far_otm_put'     # 30-50% — speculative or reset
    elif ratio < 0.8:
        return 'otm_put'         # 50-80% — plausible hedge
    elif ratio < 1.2:
        return 'atm'             # 80-120% — at the money
    elif ratio < 1.5:
        return 'otm_call'        # 120-150%
    else:
        return 'deep_otm_call'   # >150%

def main():
    print("=" * 70)
    print("TEST 13: Deep OTM Put Forensics — Reset Transaction Detection")
    print("=" * 70)

    gme_ftd = load_csv("GME")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()

    mean_ftd = gme_ftd['quantity'].mean()
    std_ftd = gme_ftd['quantity'].std()
    threshold_2s = mean_ftd + 2 * std_ftd
    spikes = gme_ftd[gme_ftd['quantity'] > threshold_2s]

    # Build T+33 echo dates
    echo_centers = {}
    for spike_date in spikes.index:
        echo_date = add_business_days(spike_date, 33)
        echo_centers[echo_date] = spike_date

    echo_window_dates = set()
    for ec in echo_centers:
        for offset in range(-5, 1):  # 5 days BEFORE echo to echo day
            d = ec + timedelta(days=offset)
            echo_window_dates.add(d)

    # ============================================================
    # Load ALL strike-level OI data
    # ============================================================
    print(f"\n  Loading {len(list(THETA_OI_DIR.glob('*.parquet')))} ThetaData OI files at strike level...")

    all_snapshots = []
    for f in sorted(THETA_OI_DIR.glob("oi_*.parquet")):
        date_str = f.stem.split('_')[1]
        snap_date = pd.Timestamp(datetime.strptime(date_str, '%Y%m%d'))

        df = pd.read_parquet(f)
        if len(df) == 0:
            continue

        # Get GME price for this date
        price = np.nan
        if snap_date in price_df.index:
            price = price_df.loc[snap_date, 'gme_close']
        else:
            # Find nearest price
            nearest = price_df.index[price_df.index.get_indexer([snap_date], method='nearest')]
            if len(nearest) > 0:
                price = price_df.loc[nearest[0], 'gme_close']

        df['snap_date'] = snap_date
        df['gme_price'] = price
        df['moneyness'] = df.apply(lambda r: classify_moneyness(r['strike'], price) if r['right'] == 'PUT' else
                                   classify_moneyness(price / max(0.01, r['strike']) * r['strike'], price), axis=1)
        # Simpler: for puts, moneyness = strike/price; for calls, moneyness = price/strike (inverted)
        df['strike_ratio'] = df['strike'] / price if price > 0 else np.nan

        # Days to expiry
        df['dte'] = (df['expiration'] - snap_date).dt.days

        all_snapshots.append(df)

    full_df = pd.concat(all_snapshots, ignore_index=True)
    print(f"  Total records: {len(full_df):,}")
    print(f"  Date range: {full_df['snap_date'].min().date()} to {full_df['snap_date'].max().date()}")

    # ============================================================
    # PART A: Deep OTM Put OI Around T+33 Echo Windows
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: Deep OTM Put OI — Echo vs Non-Echo Windows")
    print(f"{'='*60}")

    # Filter to puts only
    puts = full_df[full_df['right'] == 'PUT'].copy()

    # Classify each snapshot date as echo-window or not
    puts['in_echo_window'] = puts['snap_date'].isin(echo_window_dates).astype(int)

    # Deep OTM puts: strike < 30% of current price
    puts['is_deep_otm'] = puts['strike_ratio'] < 0.3
    puts['is_far_otm'] = (puts['strike_ratio'] >= 0.3) & (puts['strike_ratio'] < 0.5)
    puts['is_otm'] = (puts['strike_ratio'] >= 0.5) & (puts['strike_ratio'] < 0.8)
    puts['is_atm'] = (puts['strike_ratio'] >= 0.8) & (puts['strike_ratio'] < 1.2)

    # Aggregate by snapshot date and moneyness band
    daily_oi = puts.groupby(['snap_date', 'in_echo_window']).agg(
        deep_otm_oi=('open_interest', lambda x: x[puts.loc[x.index, 'is_deep_otm']].sum() if hasattr(x, 'index') else 0),
        far_otm_oi=('open_interest', lambda x: x[puts.loc[x.index, 'is_far_otm']].sum() if hasattr(x, 'index') else 0),
        total_put_oi=('open_interest', 'sum'),
    ).reset_index()

    # Simpler approach: aggregate per date
    daily_put_oi = []
    for snap_date, grp in puts.groupby('snap_date'):
        in_echo = int(snap_date in echo_window_dates)
        deep_otm = grp[grp['strike_ratio'] < 0.3]['open_interest'].sum()
        far_otm = grp[(grp['strike_ratio'] >= 0.3) & (grp['strike_ratio'] < 0.5)]['open_interest'].sum()
        otm = grp[(grp['strike_ratio'] >= 0.5) & (grp['strike_ratio'] < 0.8)]['open_interest'].sum()
        atm = grp[(grp['strike_ratio'] >= 0.8) & (grp['strike_ratio'] < 1.2)]['open_interest'].sum()
        total = grp['open_interest'].sum()

        # Near-expiry deep OTM (< 30 DTE and < 30% of price) — most suspicious
        near_deep = grp[(grp['strike_ratio'] < 0.3) & (grp['dte'] < 30)]['open_interest'].sum()
        # Far-expiry deep OTM (> 90 DTE and < 30% of price) — LEAPS, more legitimate
        far_deep = grp[(grp['strike_ratio'] < 0.3) & (grp['dte'] > 90)]['open_interest'].sum()

        price = grp['gme_price'].iloc[0] if len(grp) > 0 else np.nan

        daily_put_oi.append({
            'date': snap_date,
            'in_echo': in_echo,
            'deep_otm_oi': deep_otm,
            'far_otm_oi': far_otm,
            'otm_oi': otm,
            'atm_oi': atm,
            'total_put_oi': total,
            'deep_pct': deep_otm / max(1, total),
            'near_deep_oi': near_deep,
            'far_deep_oi': far_deep,
            'price': price,
        })

    dpo = pd.DataFrame(daily_put_oi).set_index('date').sort_index()

    echo_days = dpo[dpo['in_echo'] == 1]
    non_echo = dpo[dpo['in_echo'] == 0]

    print(f"\n  Echo-window days: {len(echo_days)}")
    print(f"  Non-echo days:   {len(non_echo)}")

    print(f"\n  {'Category':<25} {'Echo Window':>12} {'Non-Echo':>12} {'Ratio':>8}")
    print("  " + "-" * 60)

    categories = [
        ('Deep OTM (<30%)', 'deep_otm_oi'),
        ('Far OTM (30-50%)', 'far_otm_oi'),
        ('OTM (50-80%)', 'otm_oi'),
        ('ATM (80-120%)', 'atm_oi'),
        ('Total Put OI', 'total_put_oi'),
        ('Deep OTM % of Total', 'deep_pct'),
        ('Near-expiry Deep OTM', 'near_deep_oi'),
    ]

    results_a = {}
    for label, col in categories:
        e_mean = echo_days[col].mean()
        n_mean = non_echo[col].mean()
        ratio = e_mean / max(0.001, n_mean)
        if col == 'deep_pct':
            print(f"  {label:<25} {e_mean:>11.1%} {n_mean:>11.1%} {ratio:>7.2f}×")
        else:
            print(f"  {label:<25} {e_mean:>12,.0f} {n_mean:>12,.0f} {ratio:>7.2f}×")
        results_a[label] = {'echo': float(e_mean), 'non_echo': float(n_mean), 'ratio': float(ratio)}

    # Statistical test on deep OTM
    if len(echo_days) > 3 and len(non_echo) > 3:
        u_stat, u_p = stats.mannwhitneyu(
            echo_days['deep_otm_oi'].dropna(),
            non_echo['deep_otm_oi'].dropna(),
            alternative='greater'
        )
        print(f"\n  Deep OTM Put OI: Echo > Non-echo?")
        print(f"    Mann-Whitney U p = {u_p:.4f}")
        results_a['deep_otm_p'] = float(u_p)

    # ============================================================
    # PART B: Strike-Level Concentration in Deep OTM Puts
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Which Strikes Accumulate Anomalous Deep OTM Put OI?")
    print(f"{'='*60}")

    # Find the most popular deep OTM put strikes
    deep_puts = puts[(puts['strike_ratio'] < 0.3) & (puts['open_interest'] > 0)].copy()

    if len(deep_puts) > 0:
        # Echo window deep OTM puts
        echo_deep = deep_puts[deep_puts['in_echo_window'] == 1]
        non_echo_deep = deep_puts[deep_puts['in_echo_window'] == 0]

        # Top strikes by total OI
        print(f"\n  Top 15 Deep OTM Put Strikes (all periods):")
        print(f"  {'Strike':>8} {'Total OI':>12} {'Avg OI':>10} {'Snapshots':>10} {'Echo OI':>10} {'Non-echo OI':>12}")
        print("  " + "-" * 68)

        strike_agg = deep_puts.groupby('strike').agg(
            total_oi=('open_interest', 'sum'),
            avg_oi=('open_interest', 'mean'),
            n_snapshots=('snap_date', 'nunique'),
        ).sort_values('total_oi', ascending=False)

        # Add echo vs non-echo breakdown
        echo_strike = echo_deep.groupby('strike')['open_interest'].sum() if len(echo_deep) > 0 else pd.Series(dtype=float)
        non_echo_strike = non_echo_deep.groupby('strike')['open_interest'].sum() if len(non_echo_deep) > 0 else pd.Series(dtype=float)

        results_b = {}
        for strike in strike_agg.head(15).index:
            row = strike_agg.loc[strike]
            e_oi = echo_strike.get(strike, 0)
            ne_oi = non_echo_strike.get(strike, 0)
            print(f"  ${strike:>7.1f} {int(row['total_oi']):>12,} {int(row['avg_oi']):>10,} {int(row['n_snapshots']):>10} {int(e_oi):>10,} {int(ne_oi):>12,}")
            results_b[f"${strike:.1f}"] = {'total_oi': int(row['total_oi']), 'echo_oi': int(e_oi), 'non_echo_oi': int(ne_oi)}

    # ============================================================
    # PART C: Pre-Echo OI Buildup Detection
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: Pre-Echo Deep OTM Put OI Buildup")
    print(f"{'='*60}")

    # For each echo center, look at OI trajectory in the 10 days before
    buildup_results = []
    oi_dates = sorted(dpo.index)

    for echo_date, spike_date in echo_centers.items():
        # Find the nearest OI snapshot dates
        pre_window = dpo[(dpo.index >= echo_date - timedelta(days=15)) &
                         (dpo.index < echo_date)].copy()
        echo_snap = dpo[(dpo.index >= echo_date - timedelta(days=2)) &
                        (dpo.index <= echo_date + timedelta(days=2))]

        if len(pre_window) < 2 or len(echo_snap) == 0:
            continue

        # OI at the start vs end of pre-window
        early_oi = pre_window.iloc[0]['deep_otm_oi']
        late_oi = pre_window.iloc[-1]['deep_otm_oi']
        echo_oi = echo_snap['deep_otm_oi'].mean()

        change = (late_oi - early_oi) / max(1, early_oi)

        buildup_results.append({
            'echo_date': echo_date,
            'spike_date': spike_date,
            'early_deep_oi': early_oi,
            'late_deep_oi': late_oi,
            'echo_deep_oi': echo_oi,
            'pct_change': change,
            'buildup': late_oi > early_oi,
        })

    if buildup_results:
        bdf = pd.DataFrame(buildup_results)
        buildup_rate = bdf['buildup'].mean()
        avg_change = bdf['pct_change'].mean()

        print(f"\n  Echo events with OI data: {len(bdf)}")
        print(f"  Pre-echo buildup rate:    {buildup_rate:.1%} (deep OTM put OI increased)")
        print(f"  Average OI change:        {avg_change:+.1%}")
        print(f"\n  Top 10 buildup events:")
        print(f"  {'Echo Date':<12} {'Spike Date':<12} {'Early OI':>10} {'Late OI':>10} {'Change':>8}")
        print("  " + "-" * 55)
        for _, row in bdf.nlargest(10, 'pct_change').iterrows():
            print(f"  {row['echo_date'].strftime('%Y-%m-%d'):<12} {row['spike_date'].strftime('%Y-%m-%d'):<12} {int(row['early_deep_oi']):>10,} {int(row['late_deep_oi']):>10,} {row['pct_change']:>+7.0%}")

    # ============================================================
    # PART D: "Phantom OI" — Puts That Appear and Vanish
    # ============================================================
    print(f"\n{'='*60}")
    print("PART D: Phantom OI — Contracts That Appear and Vanish")
    print(f"{'='*60}")

    # Track deep OTM put OI at each strike across consecutive snapshots
    # Look for contracts that spike in OI and then drop back to near zero
    deep_puts_ts = deep_puts.groupby(['snap_date', 'strike'])['open_interest'].sum().unstack(fill_value=0)

    phantom_events = []
    for strike in deep_puts_ts.columns:
        series = deep_puts_ts[strike]
        if series.max() < 100:
            continue

        # Find spikes (> 2× rolling mean)
        rolling_mean = series.rolling(5, min_periods=1).mean()
        for i in range(2, len(series) - 2):
            curr = series.iloc[i]
            prev = series.iloc[i-1]
            nxt = series.iloc[i+1] if i+1 < len(series) else 0

            # Spike: current > 3× previous AND next drops back
            if curr > max(500, prev * 3) and (nxt < curr * 0.5 or prev < curr * 0.3):
                snap_date = series.index[i]
                in_echo = int(snap_date in echo_window_dates)
                phantom_events.append({
                    'date': snap_date,
                    'strike': strike,
                    'oi_before': int(prev),
                    'oi_spike': int(curr),
                    'oi_after': int(nxt),
                    'in_echo': in_echo,
                })

    if phantom_events:
        pdf = pd.DataFrame(phantom_events)
        echo_phantom = pdf[pdf['in_echo'] == 1]
        total_phantom = len(pdf)

        print(f"\n  Phantom OI events detected: {total_phantom}")
        print(f"  In echo windows:           {len(echo_phantom)} ({len(echo_phantom)/max(1,total_phantom):.1%})")

        # Expected rate if random
        echo_day_pct = len(echo_days) / max(1, len(echo_days) + len(non_echo))
        expected = total_phantom * echo_day_pct
        print(f"  Expected if random:        {expected:.0f} ({echo_day_pct:.1%})")

        if total_phantom > 0:
            enrichment = len(echo_phantom) / max(0.1, expected)
            print(f"  Enrichment:                {enrichment:.2f}×")

        print(f"\n  Top 15 phantom events by spike magnitude:")
        print(f"  {'Date':<12} {'Strike':>8} {'Before':>8} {'Spike':>8} {'After':>8} {'Echo?':>6}")
        print("  " + "-" * 55)
        for _, row in pdf.nlargest(15, 'oi_spike').iterrows():
            echo_flag = "✅" if row['in_echo'] else ""
            print(f"  {row['date'].strftime('%Y-%m-%d'):<12} ${row['strike']:>6.1f} {row['oi_before']:>8,} {row['oi_spike']:>8,} {row['oi_after']:>8,} {echo_flag:>6}")

    # ============================================================
    # PART E: DTE Profile of Deep OTM Puts
    # ============================================================
    print(f"\n{'='*60}")
    print("PART E: Days-to-Expiry Profile of Deep OTM Puts")
    print(f"{'='*60}")

    deep_dte = deep_puts[deep_puts['open_interest'] > 0].copy()
    if len(deep_dte) > 0:
        # Bucket by DTE
        dte_bins = [0, 7, 14, 30, 60, 90, 180, 365, 9999]
        dte_labels = ['<7d', '7-14d', '14-30d', '30-60d', '60-90d', '90-180d', '180-365d', '>365d']
        deep_dte['dte_bucket'] = pd.cut(deep_dte['dte'], bins=dte_bins, labels=dte_labels, right=False)

        echo_dte = deep_dte[deep_dte['in_echo_window'] == 1]
        non_echo_dte = deep_dte[deep_dte['in_echo_window'] == 0]

        print(f"\n  {'DTE Bucket':<12} {'Echo Avg OI':>12} {'Non-Echo Avg':>14} {'Ratio':>8}")
        print("  " + "-" * 50)

        results_e = {}
        for bucket in dte_labels:
            e_oi = echo_dte[echo_dte['dte_bucket'] == bucket]['open_interest'].mean() if len(echo_dte[echo_dte['dte_bucket'] == bucket]) > 0 else 0
            ne_oi = non_echo_dte[non_echo_dte['dte_bucket'] == bucket]['open_interest'].mean() if len(non_echo_dte[non_echo_dte['dte_bucket'] == bucket]) > 0 else 0
            ratio = e_oi / max(0.1, ne_oi)
            print(f"  {bucket:<12} {e_oi:>12,.0f} {ne_oi:>14,.0f} {ratio:>7.2f}×")
            results_e[bucket] = {'echo': float(e_oi), 'non_echo': float(ne_oi), 'ratio': float(ratio)}

    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Deep OTM Put Forensics — Reset Transaction Detection', fontsize=14, fontweight='bold', y=0.98)

    # Panel 1: Deep OTM put OI over time with echo windows
    ax = axes[0, 0]
    ax.plot(dpo.index, dpo['deep_otm_oi'], color='purple', linewidth=0.8, label='Deep OTM Put OI')
    ax.fill_between(dpo.index, 0, dpo['deep_otm_oi'], alpha=0.2, color='purple')
    # Mark echo windows
    for i, echo_date in enumerate(echo_centers):
        ax.axvline(x=echo_date, color='red', alpha=0.3, linewidth=0.5,
                   label='T+33 Echo Date' if i == 0 else None)
    ax.set_ylabel('Deep OTM Put OI')
    ax.set_title('Deep OTM Put OI Over Time (red = echo dates)', fontsize=10)
    ax.set_xlim(pd.Timestamp('2020-01-01'), dpo.index.max() + pd.Timedelta(days=30))
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel 2: Echo vs Non-Echo OI comparison bars
    ax = axes[0, 1]
    bars = ['Deep OTM\n(<30%)', 'Far OTM\n(30-50%)', 'OTM\n(50-80%)', 'ATM\n(80-120%)']
    echo_vals = [echo_days['deep_otm_oi'].mean(), echo_days['far_otm_oi'].mean(),
                 echo_days['otm_oi'].mean(), echo_days['atm_oi'].mean()]
    non_echo_vals = [non_echo['deep_otm_oi'].mean(), non_echo['far_otm_oi'].mean(),
                     non_echo['otm_oi'].mean(), non_echo['atm_oi'].mean()]
    x = np.arange(len(bars))
    ax.bar(x - 0.2, echo_vals, 0.35, label='Echo window', color='red', alpha=0.7)
    ax.bar(x + 0.2, non_echo_vals, 0.35, label='Non-echo', color='steelblue', alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(bars, fontsize=9)
    ax.set_ylabel('Mean Put OI')
    ax.set_title('Put OI by Moneyness — Echo vs Non-Echo', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel 3: Deep OTM % of total over time
    ax = axes[1, 0]
    ax.plot(dpo.index, dpo['deep_pct'] * 100, color='darkred', linewidth=0.8,
            label='Deep OTM % of Total Put OI')
    ax.fill_between(dpo.index, 0, dpo['deep_pct'] * 100, alpha=0.2, color='darkred')
    for i, echo_date in enumerate(echo_centers):
        ax.axvline(x=echo_date, color='red', alpha=0.3, linewidth=0.5,
                   label='T+33 Echo Date' if i == 0 else None)
    ax.set_ylabel('Deep OTM Put OI (% of total)')
    ax.set_title('Deep OTM Put Concentration Over Time', fontsize=10)
    ax.set_xlim(pd.Timestamp('2020-01-01'), dpo.index.max() + pd.Timedelta(days=30))
    ax.legend(fontsize=8, loc='upper left')
    ax.grid(True, alpha=0.3)

    # Panel 4: Phantom OI events timeline
    ax = axes[1, 1]
    if phantom_events:
        phantom_df_plot = pd.DataFrame(phantom_events)
        echo_p = phantom_df_plot[phantom_df_plot['in_echo'] == 1]
        non_echo_p = phantom_df_plot[phantom_df_plot['in_echo'] == 0]
        ax.scatter(non_echo_p['date'], non_echo_p['oi_spike'], s=20, alpha=0.5, color='steelblue', label='Non-echo')
        ax.scatter(echo_p['date'], echo_p['oi_spike'], s=40, alpha=0.8, color='red', label='Echo window', zorder=5)
        ax.set_ylabel('Phantom OI Spike Size')
        ax.set_title('Phantom OI Events (appear → vanish)', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    else:
        ax.text(0.5, 0.5, 'No phantom events detected', ha='center', va='center', fontsize=12)

    plt.tight_layout()
    fig_path = FIG_DIR / "deep_otm_puts.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")

    results = {
        'part_a_echo_vs_nonecho': results_a,
        'part_b_top_strikes': results_b if 'results_b' in dir() else {},
        'part_c_buildup': {
            'events': len(buildup_results) if buildup_results else 0,
            'buildup_rate': float(buildup_rate) if buildup_results else None,
            'avg_change': float(avg_change) if buildup_results else None,
        },
        'part_d_phantom': {
            'total_events': len(phantom_events) if phantom_events else 0,
            'in_echo': len(echo_phantom) if phantom_events else 0,
        },
        'part_e_dte_profile': results_e if 'results_e' in dir() else {},
    }

    out_path = RESULTS_DIR / "deep_otm_puts.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 13 complete.")

if __name__ == "__main__":
    main()
