#!/usr/bin/env python3
"""
Test 25: MIAX Pearl Forensics — Algo Signature Detection

Deeper forensic analysis of MIAX Pearl deep OTM put trades:

  A) BURST DETECTION: Are trades clustered in rapid bursts (algo) or
     spread out (multiple firms)? Measure inter-trade intervals.
  B) CONDITION CODES: What trade condition codes are specific to
     MIAX Pearl vs. other exchanges?
  C) STRIKE PERSISTENCE: Does the same strike/expiry keep appearing
     on MIAX Pearl across many settlement dates? (same entity signal)
  D) COUNTERPARTY PAIRING: Do MIAX Pearl put trades correlate with
     FINRA ADF equity trades in the same time windows?
  E) PRICE CONSISTENCY: Are MIAX Pearl trades at the bid, ask, or mid?
     Systematic execution at or below bid = non-economic (locates).

Data: ThetaData local parquets
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

EXCHANGE_MAP = {
    1: "CBOE", 4: "PHLX", 5: "ISE", 6: "BOX", 7: "MIAX",
    9: "C2", 11: "Nasdaq OMX", 43: "Nasdaq BX", 46: "Ex_46",
    60: "BEST BBO", 65: "Ex_65", 69: "MIAX Pearl", 76: "MIAX Emerald",
}

# ThetaData options trade condition codes
CONDITION_MAP = {
    0: "Regular",
    2: "Late/Out of Sequence",
    4: "Opening",
    5: "Closing",
    6: "Re-Opening",
    18: "Trade Thru Exempt",
    22: "Spread",
    23: "Straddle",
    24: "Buy-Write",
    25: "Combo",
    26: "STPD (Stock/Options)",
    27: "ISOs",
    29: "Auto-Execution",
    40: "Multi-Leg Cross",
    41: "Stock-Options Cross",
    47: "Single Leg Crossing",
    48: "Multi-Leg Floor",
    107: "Complex Floor",
    121: "Spread Floor",
    122: "Straddle Floor",
    123: "Short Sale Exempt",
    125: "Electronic",
    227: "Complex Electronic",
}


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
    if path.exists():
        return pd.read_parquet(path)
    return None


def main():
    print("=" * 70)
    print("TEST 25: MIAX Pearl Forensics — Algo Signature Detection")
    print("=" * 70)

    gme_dates = sorted([
        d.name.replace('date=', '') for d in (THETA_BASE / "root=GME").iterdir()
        if d.is_dir() and d.name.startswith('date=')
    ])

    price_df = pd.read_csv(FTD_DIR / "gme_daily_price.csv", parse_dates=['date']).set_index('date').sort_index()

    ftd_df = pd.read_csv(FTD_DIR / "GME_ftd.csv", parse_dates=['date'])
    ftd_df = ftd_df.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    threshold = ftd_df['quantity'].mean() + 3 * ftd_df['quantity'].std()
    spikes = ftd_df[ftd_df['quantity'] > threshold].sort_values('quantity', ascending=False)

    available_set = set(gme_dates)
    t33_dates = []
    for spike_date, row in spikes.head(20).iterrows():
        t33 = add_business_days(spike_date, 33)
        t33_str = t33.strftime('%Y%m%d')
        if t33_str in available_set:
            t33_dates.append(t33)

    # Also get control dates
    ctrl_dates = []
    for t33 in t33_dates:
        ctrl = add_business_days(t33, 10)
        if ctrl.strftime('%Y%m%d') in available_set:
            ctrl_dates.append(ctrl)

    print(f"  T+33 dates with data: {len(t33_dates)}")
    print(f"  Control dates: {len(ctrl_dates)}")

    # Collect all MIAX Pearl deep OTM put trades across T+33 dates
    all_pearl_trades = []
    all_other_trades = []
    all_pearl_ctrl = []

    for date in t33_dates:
        date_str = date.strftime('%Y%m%d')
        gme_price = None
        if date in price_df.index:
            gme_price = price_df.loc[date, 'gme_close']
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

        pearl = puts[puts['exchange'] == MIAX_PEARL_ID]
        other = puts[puts['exchange'] != MIAX_PEARL_ID]
        all_pearl_trades.append(pearl)
        all_other_trades.append(other)

    for date in ctrl_dates:
        date_str = date.strftime('%Y%m%d')
        gme_price = None
        if date in price_df.index:
            gme_price = price_df.loc[date, 'gme_close']
        if gme_price is None or gme_price <= 0:
            continue
        df = load_trades('GME', date_str)
        if df is None:
            continue
        puts = df[(df['right'] == 'PUT') & (df['strike'] <= gme_price * DEEP_OTM_RATIO)].copy()
        if len(puts) == 0:
            continue
        puts['dt'] = pd.to_datetime(puts['timestamp'], errors='coerce')
        pearl = puts[puts['exchange'] == MIAX_PEARL_ID]
        all_pearl_ctrl.append(pearl)

    pearl_df = pd.concat(all_pearl_trades, ignore_index=True) if all_pearl_trades else pd.DataFrame()
    other_df = pd.concat(all_other_trades, ignore_index=True) if all_other_trades else pd.DataFrame()
    ctrl_pearl_df = pd.concat(all_pearl_ctrl, ignore_index=True) if all_pearl_ctrl else pd.DataFrame()

    print(f"\n  MIAX Pearl settlement trades: {len(pearl_df):,}")
    print(f"  Other exchange settlement trades: {len(other_df):,}")
    print(f"  MIAX Pearl control trades: {len(ctrl_pearl_df):,}")

    # ================================================================
    # PART A: BURST DETECTION — Inter-trade intervals
    # ================================================================
    print(f"\n{'='*60}")
    print("PART A: Burst Detection — Inter-Trade Intervals")
    print(f"{'='*60}")

    burst_results = {}

    for label, df_subset in [('Pearl Settlement', pearl_df), ('Other Settlement', other_df), ('Pearl Control', ctrl_pearl_df)]:
        if len(df_subset) == 0:
            continue

        # Group by date and compute inter-trade intervals
        intervals = []
        for date_label, grp in df_subset.groupby(df_subset['dt'].dt.date):
            sorted_times = grp['dt'].dropna().sort_values()
            if len(sorted_times) < 2:
                continue
            diffs = sorted_times.diff().dt.total_seconds().dropna()
            intervals.extend(diffs.values)

        if not intervals:
            continue

        intervals = np.array(intervals)
        intervals = intervals[intervals > 0]  # Remove zeros

        # Burst = clustered trades < 1 second apart
        burst_pct = (intervals < 1.0).mean()
        rapid_pct = (intervals < 5.0).mean()
        slow_pct = (intervals > 60.0).mean()

        print(f"\n  {label} ({len(intervals)} intervals):")
        print(f"    Median interval: {np.median(intervals):.1f}s")
        print(f"    < 1s (burst):    {burst_pct:.0%}")
        print(f"    < 5s (rapid):    {rapid_pct:.0%}")
        print(f"    > 60s (slow):    {slow_pct:.0%}")
        print(f"    P10/P25/P50/P75/P90: {np.percentile(intervals, [10,25,50,75,90])}")

        burst_results[label] = {
            'n_intervals': len(intervals),
            'median_sec': float(np.median(intervals)),
            'burst_pct': float(burst_pct),
            'rapid_pct': float(rapid_pct),
            'slow_pct': float(slow_pct),
        }

    # ================================================================
    # PART B: CONDITION CODES
    # ================================================================
    print(f"\n{'='*60}")
    print("PART B: Condition Codes — MIAX Pearl vs Others")
    print(f"{'='*60}")

    def describe_conditions(df_in, label):
        if len(df_in) == 0:
            return {}
        cc = Counter(df_in['condition'].values)
        total = len(df_in)
        print(f"\n  {label} ({total:,} trades):")
        result = {}
        for code, count in cc.most_common(10):
            name = CONDITION_MAP.get(int(code), f"Code_{code}")
            pct = count / total
            print(f"    {name:<30} {count:>6} ({pct:>5.1%})")
            result[name] = {'code': int(code), 'count': count, 'pct': float(pct)}
        return result

    pearl_conds = describe_conditions(pearl_df, "MIAX Pearl (Settlement)")
    other_conds = describe_conditions(other_df, "Other Exchanges (Settlement)")
    ctrl_conds = describe_conditions(ctrl_pearl_df, "MIAX Pearl (Control)")

    # ================================================================
    # PART C: STRIKE PERSISTENCE — Same strikes across dates?
    # ================================================================
    print(f"\n{'='*60}")
    print("PART C: Strike Persistence — Do Same Strikes Repeat?")
    print(f"{'='*60}")

    if len(pearl_df) > 0 and 'date_label' in pearl_df.columns:
        # For each strike, count how many unique dates it appears on
        strike_dates = pearl_df.groupby('strike')['date_label'].nunique().sort_values(ascending=False)
        total_dates = pearl_df['date_label'].nunique()

        print(f"\n  Total settlement dates with MIAX Pearl trades: {total_dates}")
        print(f"\n  {'Strike':>8} {'Dates':>6} {'%':>6} {'Trades':>8} {'Vol':>8}")
        print("  " + "-" * 42)

        strike_persistence = {}
        for strike, n_dates in strike_dates.head(20).items():
            grp = pearl_df[pearl_df['strike'] == strike]
            trades = len(grp)
            vol = int(grp['size'].sum())
            pct = n_dates / total_dates
            print(f"  ${strike:>7.1f} {n_dates:>6} {pct:>5.0%} {trades:>8} {vol:>8}")
            strike_persistence[float(strike)] = {
                'n_dates': int(n_dates),
                'pct_dates': float(pct),
                'total_trades': trades,
                'total_volume': vol,
            }

        # Check for "anchor" strikes that appear >50% of dates
        anchor_strikes = [s for s, d in strike_dates.items() if d / total_dates > 0.5]
        if anchor_strikes:
            print(f"\n  🔍 ANCHOR STRIKES (>50% of dates): {', '.join(f'${s}' for s in sorted(anchor_strikes))}")

    # ================================================================
    # PART D: PRICE ANALYSIS — Bid/Ask/Mid positioning
    # ================================================================
    print(f"\n{'='*60}")
    print("PART D: Price Analysis — Economic vs Non-Economic Trades")
    print(f"{'='*60}")

    if len(pearl_df) > 0:
        # For deep OTM puts, check if trades are at minimum price (non-economic)
        pearl_prices = pearl_df['price'].dropna()
        print(f"\n  MIAX Pearl price distribution:")
        print(f"    Min: ${pearl_prices.min():.4f}")
        print(f"    Median: ${pearl_prices.median():.4f}")
        print(f"    Mean: ${pearl_prices.mean():.4f}")
        print(f"    Max: ${pearl_prices.max():.4f}")
        print(f"    At $0.01 (minimum): {(pearl_prices <= 0.01).sum()}/{len(pearl_prices)} ({(pearl_prices <= 0.01).mean():.0%})")
        print(f"    At $0.05 or less:   {(pearl_prices <= 0.05).sum()}/{len(pearl_prices)} ({(pearl_prices <= 0.05).mean():.0%})")
        print(f"    At $0.10 or less:   {(pearl_prices <= 0.10).sum()}/{len(pearl_prices)} ({(pearl_prices <= 0.10).mean():.0%})")

        # Compare to other exchanges
        other_prices = other_df['price'].dropna()
        print(f"\n  Other Exchanges price distribution:")
        print(f"    Min: ${other_prices.min():.4f}")
        print(f"    Median: ${other_prices.median():.4f}")
        print(f"    At $0.01 (minimum): {(other_prices <= 0.01).sum()}/{len(other_prices)} ({(other_prices <= 0.01).mean():.0%})")
        print(f"    At $0.05 or less:   {(other_prices <= 0.05).sum()}/{len(other_prices)} ({(other_prices <= 0.05).mean():.0%})")

    # ================================================================
    # PART E: EXPIRY ANALYSIS — What expiries are used?
    # ================================================================
    print(f"\n{'='*60}")
    print("PART E: Expiry Analysis — What DTE Are These Puts?")
    print(f"{'='*60}")

    if len(pearl_df) > 0:
        pearl_cp = pearl_df.copy()
        pearl_cp['expiry_dt'] = pd.to_datetime(pearl_cp['expiry'], errors='coerce')
        pearl_cp['trade_dt'] = pearl_cp['dt'].dt.normalize()
        pearl_cp['dte'] = (pearl_cp['expiry_dt'] - pearl_cp['trade_dt']).dt.days

        dte_valid = pearl_cp['dte'].dropna()
        if len(dte_valid) > 0:
            print(f"\n  MIAX Pearl DTE distribution:")
            buckets = [
                ("≤7 days (weeklies)", dte_valid <= 7),
                ("8-14 days", (dte_valid > 7) & (dte_valid <= 14)),
                ("15-30 days", (dte_valid > 14) & (dte_valid <= 30)),
                ("31-60 days", (dte_valid > 30) & (dte_valid <= 60)),
                ("61-90 days", (dte_valid > 60) & (dte_valid <= 90)),
                ("91-180 days", (dte_valid > 90) & (dte_valid <= 180)),
                ("181-365 days", (dte_valid > 180) & (dte_valid <= 365)),
                (">365 days (LEAPS)", dte_valid > 365),
            ]
            for label, mask in buckets:
                count = mask.sum()
                print(f"    {label:<25} {count:>5} ({count/len(dte_valid):.0%})")

    # ================================================================
    # VISUALIZATION
    # ================================================================
    fig, axes = plt.subplots(2, 3, figsize=(24, 13))
    fig.suptitle('MIAX Pearl Forensics — GME Deep OTM Put Algo Signatures',
                 fontsize=14, fontweight='bold', y=0.98)

    # Panel 1: Inter-trade interval histogram
    ax = axes[0, 0]
    for label, df_subset, color in [('Pearl Sett', pearl_df, 'crimson'), ('Other Sett', other_df, 'steelblue')]:
        if len(df_subset) == 0:
            continue
        intervals = []
        for _, grp in df_subset.groupby(df_subset['dt'].dt.date):
            sorted_times = grp['dt'].dropna().sort_values()
            if len(sorted_times) >= 2:
                diffs = sorted_times.diff().dt.total_seconds().dropna()
                intervals.extend(diffs.values)
        intervals = np.array([i for i in intervals if 0 < i < 300])
        if len(intervals) > 0:
            ax.hist(intervals, bins=50, alpha=0.6, color=color, label=label, density=True)
    ax.set_xlabel('Inter-trade Interval (seconds)')
    ax.set_ylabel('Density')
    ax.set_title('Inter-Trade Intervals (< 5 min)', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel 2: Condition codes comparison
    ax = axes[0, 1]
    if pearl_conds and other_conds:
        all_conds = sorted(set(list(pearl_conds.keys()) + list(other_conds.keys())),
                          key=lambda x: pearl_conds.get(x, {}).get('pct', 0), reverse=True)[:8]
        x = np.arange(len(all_conds))
        p_vals = [pearl_conds.get(c, {}).get('pct', 0) for c in all_conds]
        o_vals = [other_conds.get(c, {}).get('pct', 0) for c in all_conds]
        ax.barh(x - 0.2, p_vals, 0.35, label='MIAX Pearl', color='crimson', alpha=0.8)
        ax.barh(x + 0.2, o_vals, 0.35, label='Other', color='steelblue', alpha=0.8)
        ax.set_yticks(x)
        ax.set_yticklabels([c[:20] for c in all_conds], fontsize=7)
        ax.set_xlabel('% of Trades')
        ax.set_title('Condition Codes: Pearl vs Others', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()

    # Panel 3: Strike persistence heatmap
    ax = axes[0, 2]
    if len(pearl_df) > 0 and 'date_label' in pearl_df.columns:
        top_strikes = pearl_df.groupby('strike')['size'].sum().nlargest(12).index
        dates = sorted(pearl_df['date_label'].unique())
        heatmap_data = np.zeros((len(top_strikes), len(dates)))
        for i, strike in enumerate(top_strikes):
            for j, d in enumerate(dates):
                trades = pearl_df[(pearl_df['strike'] == strike) & (pearl_df['date_label'] == d)]
                heatmap_data[i, j] = len(trades)
        im = ax.imshow(heatmap_data, aspect='auto', cmap='hot', interpolation='nearest')
        ax.set_yticks(range(len(top_strikes)))
        ax.set_yticklabels([f'${s}' for s in top_strikes], fontsize=7)
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels([d[:7] for d in dates], fontsize=6, rotation=45)
        ax.set_title('Strike × Date Heatmap (# trades)', fontsize=10)
        fig.colorbar(im, ax=ax, shrink=0.6)

    # Panel 4: Price distribution
    ax = axes[1, 0]
    if len(pearl_df) > 0:
        pp = pearl_df['price'].dropna()
        op = other_df['price'].dropna()
        bins = np.arange(0, 0.52, 0.01)
        ax.hist(pp[pp <= 0.5], bins=bins, alpha=0.7, color='crimson', label='MIAX Pearl', density=True)
        ax.hist(op[op <= 0.5], bins=bins, alpha=0.5, color='steelblue', label='Other', density=True)
        ax.set_xlabel('Trade Price ($)')
        ax.set_ylabel('Density')
        ax.set_title('Trade Price Distribution (≤$0.50)', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    # Panel 5: DTE distribution
    ax = axes[1, 1]
    if len(pearl_df) > 0:
        pearl_cp = pearl_df.copy()
        pearl_cp['expiry_dt'] = pd.to_datetime(pearl_cp['expiry'], errors='coerce')
        pearl_cp['trade_dt'] = pearl_cp['dt'].dt.normalize()
        pearl_cp['dte'] = (pearl_cp['expiry_dt'] - pearl_cp['trade_dt']).dt.days
        dte = pearl_cp['dte'].dropna()
        dte = dte[(dte >= 0) & (dte <= 400)]
        ax.hist(dte, bins=50, alpha=0.7, color='crimson', edgecolor='white')
        ax.set_xlabel('Days to Expiry')
        ax.set_ylabel('Count')
        ax.set_title('MIAX Pearl: DTE of Deep OTM Puts', fontsize=10)
        ax.grid(True, alpha=0.3)

    # Panel 6: Summary
    ax = axes[1, 2]
    ax.axis('off')
    summary = "FORENSIC ANALYSIS SUMMARY\n" + "=" * 35 + "\n\n"
    if burst_results:
        for label, data in burst_results.items():
            summary += f"{label}:\n"
            summary += f"  Median interval: {data['median_sec']:.1f}s\n"
            summary += f"  Burst (<1s): {data['burst_pct']:.0%}\n"
            summary += f"  Rapid (<5s): {data['rapid_pct']:.0%}\n\n"
    if len(pearl_df) > 0:
        pp = pearl_df['price'].dropna()
        summary += f"Price at ≤$0.01: {(pp <= 0.01).mean():.0%}\n"
        summary += f"Price at ≤$0.05: {(pp <= 0.05).mean():.0%}\n"
    ax.text(0.03, 0.95, summary, transform=ax.transAxes,
            fontfamily='monospace', fontsize=7, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()
    fig_path = FIG_DIR / "chart_miax_pearl_forensics.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")

    # Save results
    results = {
        'burst_detection': burst_results,
        'condition_codes': {
            'pearl_settlement': pearl_conds,
            'other_settlement': other_conds,
            'pearl_control': ctrl_conds,
        },
        'strike_persistence': strike_persistence if 'strike_persistence' in dir() else {},
        'price_analysis': {
            'pearl_at_0.01': float((pearl_df['price'] <= 0.01).mean()) if len(pearl_df) > 0 else 0,
            'pearl_at_0.05': float((pearl_df['price'] <= 0.05).mean()) if len(pearl_df) > 0 else 0,
            'pearl_median_price': float(pearl_df['price'].median()) if len(pearl_df) > 0 else 0,
            'other_at_0.01': float((other_df['price'] <= 0.01).mean()) if len(other_df) > 0 else 0,
            'other_at_0.05': float((other_df['price'] <= 0.05).mean()) if len(other_df) > 0 else 0,
        },
    }
    out_path = RESULTS_DIR / "miax_pearl_forensics.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 25 complete.")


if __name__ == "__main__":
    main()
