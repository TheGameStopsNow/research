#!/usr/bin/env python3
"""
Test 26: MIAX Pearl Algo Fingerprint Extraction

The deepest forensic pass. Building on Test 25's finding of a single
automated program pacing 1-lot trades every ~26s on MIAX Pearl, we now
extract the specific algo fingerprint:

  A) SPACING REGULARITY: Is the 26s interval a fixed cadence (metronome)
     or variable? Plot the interval histogram at sub-second resolution.
     A fixed cadence = single algo with programmatic sleep().
  B) EXTENDED CONDITION CODES: The ext_condition1-4 fields have been
     ignored. Analyze for hidden OPRA condition information.
  C) CONTRACT FINGERPRINT: Build a (strike, expiry, date) matrix.
     Do the EXACT same contracts repeat across settlement dates?
  D) SEQUENCE NUMBER ANALYSIS: Do sequence numbers show monotonic bursts
     (single feed) or interleaved patterns (multiple participants)?
  E) CROSS-DATE TIMESTAMP ALIGNMENT: Are trades placed at the same
     time-of-day across different settlement dates? (synchronized cron)
  F) SETTLEMENT CORRELATION: Match each MIAX Pearl burst to a specific
     FTD spike and verify T+33 alignment.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json, sys
from pathlib import Path
from datetime import timedelta
from collections import defaultdict, Counter

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FTD_DIR = REPO_ROOT / "data" / "ftd"
RESULTS_DIR = REPO_ROOT / "results" / "ftd_research"
FIG_DIR = REPO_ROOT / "figures" / "ftd_research"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

THETA_BASE = Path.home() / "Documents/GitHub/power-tracks-research/data/raw/thetadata/trades"
MIAX_PEARL_ID = 69
DEEP_OTM_RATIO = 0.30


def add_business_days(date, n):
    current = pd.Timestamp(date)
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def load_trades(ticker, date_str):
    path = THETA_BASE / f"root={ticker}" / f"date={date_str}" / "part-0.parquet"
    return pd.read_parquet(path) if path.exists() else None


def main():
    print("=" * 70)
    print("TEST 26: MIAX Pearl Algo Fingerprint Extraction")
    print("=" * 70)

    gme_dates = sorted([
        d.name.replace('date=', '') for d in (THETA_BASE / "root=GME").iterdir()
        if d.is_dir() and d.name.startswith('date=')
    ])
    available_set = set(gme_dates)

    price_df = pd.read_csv(FTD_DIR / "gme_daily_price.csv",
                           parse_dates=['date']).set_index('date').sort_index()

    ftd_df = pd.read_csv(FTD_DIR / "GME_ftd.csv", parse_dates=['date'])
    ftd_df = ftd_df.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    threshold = ftd_df['quantity'].mean() + 3 * ftd_df['quantity'].std()
    spikes = ftd_df[ftd_df['quantity'] > threshold].sort_values('quantity', ascending=False)

    t33_targets = []
    for spike_date, row in spikes.head(20).iterrows():
        t33 = add_business_days(spike_date, 33)
        if t33.strftime('%Y%m%d') in available_set:
            t33_targets.append({
                'spike_date': spike_date,
                'spike_qty': int(row['quantity']),
                't33_date': t33,
            })

    # Also gather non-T+33 dates in same period for comparison
    non_t33_dates = []
    for t in t33_targets:
        for offset in [3, -3, 7, -7]:
            other = add_business_days(t['t33_date'], offset)
            other_str = other.strftime('%Y%m%d')
            if other_str in available_set:
                non_t33_dates.append(other)
    non_t33_dates = list(set(non_t33_dates))[:20]

    print(f"  T+33 dates: {len(t33_targets)}")
    print(f"  Non-T+33 control dates: {len(non_t33_dates)}")

    # ================================================================
    # Collect ALL Pearl deep OTM trades with full metadata
    # ================================================================
    all_pearl = []
    all_other = []

    for t in t33_targets:
        date = t['t33_date']
        date_str = date.strftime('%Y%m%d')
        gme_price = price_df.loc[date, 'gme_close'] if date in price_df.index else None
        if gme_price is None or gme_price <= 0:
            continue

        df = load_trades('GME', date_str)
        if df is None:
            continue

        puts = df[(df['right'] == 'PUT') & (df['strike'] <= gme_price * DEEP_OTM_RATIO)].copy()
        if len(puts) == 0:
            continue

        puts['dt'] = pd.to_datetime(puts['timestamp'], errors='coerce')
        puts['date_label'] = date.strftime('%Y-%m-%d')
        puts['spike_date'] = t['spike_date'].strftime('%Y-%m-%d')
        puts['spike_qty'] = t['spike_qty']
        puts['is_t33'] = True

        pearl = puts[puts['exchange'] == MIAX_PEARL_ID]
        other = puts[puts['exchange'] != MIAX_PEARL_ID]
        all_pearl.append(pearl)
        all_other.append(other)

    # Non-T+33 controls
    for date in non_t33_dates:
        date_str = date.strftime('%Y%m%d')
        gme_price = price_df.loc[date, 'gme_close'] if date in price_df.index else None
        if gme_price is None or gme_price <= 0:
            continue
        df = load_trades('GME', date_str)
        if df is None:
            continue
        puts = df[(df['right'] == 'PUT') & (df['strike'] <= gme_price * DEEP_OTM_RATIO)].copy()
        if len(puts) == 0:
            continue
        puts['dt'] = pd.to_datetime(puts['timestamp'], errors='coerce')
        puts['date_label'] = date.strftime('%Y-%m-%d')
        puts['is_t33'] = False
        pearl = puts[puts['exchange'] == MIAX_PEARL_ID]
        all_pearl.append(pearl)

    pearl_df = pd.concat(all_pearl, ignore_index=True)
    other_df = pd.concat(all_other, ignore_index=True) if all_other else pd.DataFrame()

    t33_pearl = pearl_df[pearl_df.get('is_t33', False) == True] if 'is_t33' in pearl_df.columns else pearl_df
    ctrl_pearl = pearl_df[pearl_df.get('is_t33', False) == False] if 'is_t33' in pearl_df.columns else pd.DataFrame()

    print(f"\n  Total MIAX Pearl deep OTM put trades: {len(pearl_df):,}")
    print(f"    T+33 settlement: {len(t33_pearl):,}")
    print(f"    Non-T+33 control: {len(ctrl_pearl):,}")
    print(f"  Other exchange trades: {len(other_df):,}")

    # ================================================================
    # PART A: SPACING REGULARITY — Is 26s a fixed cadence?
    # ================================================================
    print(f"\n{'='*60}")
    print("PART A: Trade Spacing Regularity — Cadence Analysis")
    print(f"{'='*60}")

    def analyze_intervals(df_in, label):
        intervals_all = []
        per_date = {}
        for date_label, grp in df_in.groupby('date_label'):
            sorted_times = grp['dt'].dropna().sort_values()
            if len(sorted_times) < 3:
                continue
            diffs = sorted_times.diff().dt.total_seconds().dropna().values
            diffs = diffs[diffs > 0]
            intervals_all.extend(diffs)
            per_date[date_label] = {
                'n': len(diffs),
                'median': float(np.median(diffs)),
                'std': float(np.std(diffs)),
                'cv': float(np.std(diffs) / np.median(diffs)) if np.median(diffs) > 0 else 0,
            }

        if not intervals_all:
            return None, None

        intervals = np.array(intervals_all)
        # Coefficient of variation: std/mean. Low CV = regular; high CV = random
        cv = np.std(intervals) / np.mean(intervals)

        print(f"\n  {label} ({len(intervals)} intervals):")
        print(f"    Mean: {np.mean(intervals):.2f}s, Std: {np.std(intervals):.2f}s")
        print(f"    CV (std/mean): {cv:.2f} — {'REGULAR' if cv < 1.0 else 'IRREGULAR'}")
        print(f"    Percentiles: {np.percentile(intervals, [5,10,25,50,75,90,95])}")

        # Check for dominant cadence
        # Round to nearest second and find mode
        rounded = np.round(intervals).astype(int)
        mode_counter = Counter(rounded)
        top_cadences = mode_counter.most_common(5)
        print(f"    Top cadences (rounded to 1s):")
        for cadence, count in top_cadences:
            pct = count / len(rounded)
            print(f"      {cadence}s: {count} ({pct:.0%})")

        # Check for harmonic patterns (multiples of a base interval)
        for base in [13, 15, 20, 25, 26, 30]:
            near_base = np.sum(np.abs(intervals - base) < 3) / len(intervals)
            near_2x = np.sum(np.abs(intervals - base*2) < 5) / len(intervals)
            if near_base > 0.1:
                print(f"    ~{base}s pattern: {near_base:.0%} of intervals (±3s)")

        return intervals, per_date

    pearl_sett_intervals, pearl_sett_per_date = analyze_intervals(t33_pearl, "MIAX Pearl T+33")
    pearl_ctrl_intervals, pearl_ctrl_per_date = analyze_intervals(ctrl_pearl, "MIAX Pearl Control")
    other_intervals, _ = analyze_intervals(other_df, "Other Exchanges T+33")

    # Per-date breakdown for settlement dates
    if pearl_sett_per_date:
        print(f"\n  Per-date cadence:")
        for date, stats in sorted(pearl_sett_per_date.items()):
            print(f"    {date}: median={stats['median']:.1f}s, std={stats['std']:.1f}s, "
                  f"CV={stats['cv']:.2f}, n={stats['n']}")

    # ================================================================
    # PART B: EXT_CONDITION CODES — Hidden OPRA metadata
    # ================================================================
    print(f"\n{'='*60}")
    print("PART B: Extended Condition Codes (ext_condition 1-4)")
    print(f"{'='*60}")

    for cname in ['ext_condition1', 'ext_condition2', 'ext_condition3', 'ext_condition4']:
        if cname not in t33_pearl.columns:
            continue
        vals = Counter(t33_pearl[cname].values)
        print(f"\n  MIAX Pearl T+33 — {cname}:")
        for v, c in vals.most_common(5):
            pct = c / len(t33_pearl)
            print(f"    {v}: {c} ({pct:.0%})")

        if len(other_df) > 0 and cname in other_df.columns:
            vals_o = Counter(other_df[cname].values)
            print(f"  Other Exchanges T+33 — {cname}:")
            for v, c in vals_o.most_common(5):
                pct = c / len(other_df)
                print(f"    {v}: {c} ({pct:.0%})")

    # ================================================================
    # PART C: CONTRACT FINGERPRINT — Same contracts across dates
    # ================================================================
    print(f"\n{'='*60}")
    print("PART C: Contract Fingerprint — Exact Strike×Expiry Persistence")
    print(f"{'='*60}")

    if len(t33_pearl) > 0:
        t33_pearl_cp = t33_pearl.copy()
        t33_pearl_cp['contract'] = t33_pearl_cp['strike'].astype(str) + 'P_' + t33_pearl_cp['expiry'].astype(str)

        # For each contract, which dates it appears on
        contract_dates = t33_pearl_cp.groupby('contract')['date_label'].apply(set)
        all_t33_date_labels = sorted(t33_pearl_cp['date_label'].unique())
        n_dates = len(all_t33_date_labels)

        # Contracts appearing on multiple dates = same entity
        repeat_contracts = {k: v for k, v in contract_dates.items() if len(v) >= 2}
        print(f"\n  Total unique contracts traded: {len(contract_dates)}")
        print(f"  Contracts appearing on ≥2 dates: {len(repeat_contracts)}")
        print(f"  Contracts appearing on ≥3 dates: {sum(1 for v in repeat_contracts.values() if len(v) >= 3)}")

        # Show the most persistent contracts
        sorted_contracts = sorted(repeat_contracts.items(), key=lambda x: len(x[1]), reverse=True)
        print(f"\n  {'Contract':<30} {'Dates':>5} {'Date List'}")
        print("  " + "-" * 70)
        for contract, dates in sorted_contracts[:15]:
            print(f"  {contract:<30} {len(dates):>5}  {', '.join(sorted(dates))}")

    # ================================================================
    # PART D: SEQUENCE NUMBER ANALYSIS
    # ================================================================
    print(f"\n{'='*60}")
    print("PART D: Sequence Number Pattern Analysis")
    print(f"{'='*60}")

    if 'sequence' in t33_pearl.columns and len(t33_pearl) > 0:
        for date_label, grp in t33_pearl.groupby('date_label'):
            if len(grp) < 10:
                continue
            seqs = grp.sort_values('dt')['sequence'].values
            diffs = np.diff(seqs)
            monotonic = (diffs > 0).mean()
            median_gap = np.median(diffs[diffs > 0]) if (diffs > 0).any() else 0

            print(f"\n  {date_label} ({len(seqs)} trades):")
            print(f"    Monotonic: {monotonic:.0%}")
            print(f"    Median sequence gap: {median_gap:.0f}")
            print(f"    Min gap: {diffs[diffs > 0].min() if (diffs > 0).any() else 0:.0f}")
            print(f"    Max gap: {diffs.max():.0f}")

            # Check for interleaving (sequence goes up AND down = multiple feeds)
            reversals = (diffs < 0).sum()
            print(f"    Reversals (seq decrease): {reversals} ({reversals/len(diffs):.0%})")

    # ================================================================
    # PART E: CROSS-DATE TIMESTAMP ALIGNMENT
    # ================================================================
    print(f"\n{'='*60}")
    print("PART E: Cross-Date Timestamp Alignment — Synchronized Execution?")
    print(f"{'='*60}")

    if len(t33_pearl) > 0:
        t33_pearl_cp = t33_pearl.copy()
        t33_pearl_cp['time_of_day'] = t33_pearl_cp['dt'].dt.hour * 3600 + t33_pearl_cp['dt'].dt.minute * 60 + t33_pearl_cp['dt'].dt.second

        # For each settlement date, find the first trade time
        first_trades = {}
        for date_label, grp in t33_pearl_cp.groupby('date_label'):
            sorted_grp = grp.sort_values('dt')
            first_time = sorted_grp.iloc[0]['dt']
            first_trades[date_label] = first_time.strftime('%H:%M:%S')

        print(f"\n  First MIAX Pearl deep OTM put trade per settlement date:")
        for d, t in sorted(first_trades.items()):
            print(f"    {d}: {t}")

        # Histogram of time-of-day across all dates
        # Bin by 15-minute intervals
        t33_pearl_cp['minute_of_day'] = t33_pearl_cp['dt'].dt.hour * 60 + t33_pearl_cp['dt'].dt.minute
        bins = np.arange(570, 960, 15)  # 9:30 to 16:00 in 15-min bins
        hist, _ = np.histogram(t33_pearl_cp['minute_of_day'].dropna(), bins=bins)

        print(f"\n  Time-of-day distribution (15-min bins, settlement dates):")
        total_in_bins = hist.sum()
        for i, count in enumerate(hist):
            if count > 0:
                start_min = bins[i]
                h, m = divmod(start_min, 60)
                pct = count / total_in_bins
                bar = '█' * int(pct * 50)
                print(f"    {h:02d}:{m:02d} {count:>4} ({pct:>4.0%}) {bar}")

    # ================================================================
    # PART F: FTD SPIKE CORRELATION
    # ================================================================
    print(f"\n{'='*60}")
    print("PART F: FTD Spike → MIAX Pearl Volume Correlation")
    print(f"{'='*60}")

    if len(t33_pearl) > 0 and 'spike_qty' in t33_pearl.columns:
        spike_vol = t33_pearl.groupby('date_label').agg({
            'spike_qty': 'first',
            'size': ['count', 'sum'],
        })
        spike_vol.columns = ['ftd_quantity', 'pearl_trades', 'pearl_volume']
        spike_vol = spike_vol.sort_values('ftd_quantity', ascending=False)

        print(f"\n  {'Date':<12} {'FTDs':>12} {'Pearl Trades':>14} {'Pearl Vol':>12} {'Ratio':>8}")
        print("  " + "-" * 60)
        for idx, row in spike_vol.iterrows():
            ratio = row['pearl_volume'] / row['ftd_quantity'] if row['ftd_quantity'] > 0 else 0
            print(f"  {idx:<12} {row['ftd_quantity']:>12,.0f} {row['pearl_trades']:>14,.0f} "
                  f"{row['pearl_volume']:>12,.0f} {ratio:>7.2%}")

        # Correlation
        if len(spike_vol) >= 3:
            corr = spike_vol['ftd_quantity'].corr(spike_vol['pearl_volume'])
            print(f"\n  📊 Correlation (FTDs vs Pearl volume): r = {corr:.3f}")

    # ================================================================
    # VISUALIZATION
    # ================================================================
    fig, axes = plt.subplots(2, 3, figsize=(24, 13))
    fig.suptitle('MIAX Pearl Algo Fingerprint — Deep Forensic Extraction',
                 fontsize=14, fontweight='bold', y=0.98)

    # Panel 1: Interval histogram at fine resolution
    ax = axes[0, 0]
    if pearl_sett_intervals is not None:
        # Focus on 0-120s range with 1s bins
        mask = (pearl_sett_intervals > 0) & (pearl_sett_intervals < 120)
        fine = pearl_sett_intervals[mask]
        bins = np.arange(0, 121, 1)
        ax.hist(fine, bins=bins, alpha=0.8, color='crimson', edgecolor='darkred', linewidth=0.3)
        ax.axvline(x=26, color='gold', linewidth=2, linestyle='--', label='26s cadence')
        ax.set_xlabel('Inter-trade Interval (seconds)')
        ax.set_ylabel('Count')
        ax.set_title('Pearl T+33: Trade Spacing (1s bins)', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    # Panel 2: Interval autocorrelation
    ax = axes[0, 1]
    if pearl_sett_intervals is not None and len(pearl_sett_intervals) > 20:
        # Auto-correlation of intervals to detect periodicity
        from numpy.fft import fft
        ints = pearl_sett_intervals[pearl_sett_intervals > 0]
        ints = ints[:500]  # Limit for FFT
        ints_centered = ints - np.mean(ints)
        acf = np.correlate(ints_centered, ints_centered, 'full')
        acf = acf[len(acf)//2:]
        acf = acf / acf[0]
        ax.plot(acf[:50], color='crimson', linewidth=1.5)
        ax.set_xlabel('Lag')
        ax.set_ylabel('Autocorrelation')
        ax.set_title('Interval Autocorrelation (periodicity check)', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linewidth=0.5)

    # Panel 3: Contract persistence heatmap
    ax = axes[0, 2]
    if len(t33_pearl) > 0:
        t33_cp = t33_pearl.copy()
        t33_cp['contract'] = t33_cp['strike'].astype(str) + 'P_' + t33_cp['expiry'].astype(str)
        dates = sorted(t33_cp['date_label'].unique())
        top_contracts = t33_cp.groupby('contract')['size'].sum().nlargest(15).index
        heatmap = np.zeros((len(top_contracts), len(dates)))
        for i, c in enumerate(top_contracts):
            for j, d in enumerate(dates):
                heatmap[i, j] = len(t33_cp[(t33_cp['contract'] == c) & (t33_cp['date_label'] == d)])
        im = ax.imshow(heatmap, aspect='auto', cmap='YlOrRd', interpolation='nearest')
        ax.set_yticks(range(len(top_contracts)))
        ax.set_yticklabels([c[:20] for c in top_contracts], fontsize=6)
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(dates, fontsize=6, rotation=45)
        ax.set_title('Contract × Date Persistence', fontsize=10)
        fig.colorbar(im, ax=ax, shrink=0.6)

    # Panel 4: Time-of-day overlay across dates
    ax = axes[1, 0]
    if len(t33_pearl) > 0:
        colors = plt.cm.tab10(np.linspace(0, 1, len(t33_pearl['date_label'].unique())))
        for i, (date_label, grp) in enumerate(t33_pearl.groupby('date_label')):
            times = grp['dt'].dt.hour + grp['dt'].dt.minute / 60
            times = times.dropna()
            if len(times) > 5:
                ax.hist(times, bins=np.arange(9.5, 16.5, 0.25), alpha=0.5,
                       color=colors[i % len(colors)], label=date_label, density=True)
        ax.set_xlabel('Hour (ET)')
        ax.set_ylabel('Density')
        ax.set_title('Intraday Timing — Each Settlement Date', fontsize=10)
        ax.legend(fontsize=6, loc='upper right', ncol=2)
        ax.grid(True, alpha=0.3)

    # Panel 5: FTD size vs Pearl volume scatterplot
    ax = axes[1, 1]
    if len(t33_pearl) > 0 and 'spike_qty' in t33_pearl.columns:
        spike_vol = t33_pearl.groupby('date_label').agg({
            'spike_qty': 'first',
            'size': 'sum',
        }).rename(columns={'size': 'pearl_volume'})
        ax.scatter(spike_vol['spike_qty'], spike_vol['pearl_volume'],
                  s=100, color='crimson', alpha=0.8, edgecolors='darkred', zorder=5)
        for idx, row in spike_vol.iterrows():
            ax.annotate(idx[:7], (row['spike_qty'], row['pearl_volume']),
                       fontsize=6, ha='center', va='bottom')
        ax.set_xlabel('FTD Spike Quantity')
        ax.set_ylabel('MIAX Pearl Volume on T+33')
        ax.set_title('FTD Spike vs Pearl Volume', fontsize=10)
        ax.grid(True, alpha=0.3)

    # Panel 6: Sequence gap histogram
    ax = axes[1, 2]
    if 'sequence' in t33_pearl.columns and len(t33_pearl) > 0:
        seq_gaps = []
        for _, grp in t33_pearl.groupby('date_label'):
            seqs = grp.sort_values('dt')['sequence'].values
            d = np.diff(seqs)
            seq_gaps.extend(d[d > 0])
        if seq_gaps:
            gaps = np.array(seq_gaps)
            gaps = gaps[gaps < np.percentile(gaps, 95)]
            ax.hist(gaps, bins=50, alpha=0.8, color='steelblue', edgecolor='white')
            ax.set_xlabel('Sequence Number Gap')
            ax.set_ylabel('Count')
            ax.set_title('Sequence Gaps Between Trades', fontsize=10)
            ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = FIG_DIR / "chart_miax_pearl_fingerprint.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")

    # Save results
    results = {
        'spacing': {
            'settlement': {
                'mean': float(np.mean(pearl_sett_intervals)) if pearl_sett_intervals is not None else 0,
                'std': float(np.std(pearl_sett_intervals)) if pearl_sett_intervals is not None else 0,
                'cv': float(np.std(pearl_sett_intervals)/np.mean(pearl_sett_intervals)) if pearl_sett_intervals is not None and np.mean(pearl_sett_intervals) > 0 else 0,
            },
            'per_date': pearl_sett_per_date or {},
        },
        'first_trades': first_trades if 'first_trades' in dir() else {},
    }

    out_path = RESULTS_DIR / "miax_pearl_fingerprint.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 26 complete.")


if __name__ == "__main__":
    main()
