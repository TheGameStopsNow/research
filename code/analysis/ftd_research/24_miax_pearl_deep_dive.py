#!/usr/bin/env python3
"""
Test 24: MIAX Pearl Deep Dive

Follow-up to Test 23's finding that Exchange 69 (MIAX Pearl) dominates
deep OTM put trades on T+33 settlement dates. Four sub-analyses:

  A) TIMELINE: Weekly exchange share for deep OTM puts — did activity
     migrate to MIAX Pearl after its Sept 2020 launch?
  B) CROSS-TICKER: Does the same MIAX Pearl dominance appear in
     AMC, BBBY, KOSS, BB, CHWY (the meme basket)?
  C) TRADE SIZE FINGERPRINT: Is the trade size distribution on MIAX Pearl
     consistent across dates (single entity) or varied (multiple firms)?
  D) INTRADAY TIMING: When during the day do MIAX Pearl deep OTM puts
     trade on settlement dates vs. control dates?

Data: ThetaData local parquets
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json, sys
from pathlib import Path
from datetime import timedelta
from collections import defaultdict

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FTD_DIR = REPO_ROOT / "data" / "ftd"
RESULTS_DIR = REPO_ROOT / "results" / "ftd_research"
FIG_DIR = REPO_ROOT / "figures" / "ftd_research"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

THETA_BASE = Path.home() / "Documents/GitHub/power-tracks-research/data/raw/thetadata/trades"

# Exchange IDs of interest
MIAX_PEARL_ID = 69
MIAX_EMERALD_ID = 76
MIAX_ID = 7
CBOE_ID = 1
ISE_ID = 5
BOX_ID = 6
PHLX_ID = 4  # Nasdaq PHLX / PACIFIC in ThetaData
C2_ID = 9
NASDAQ_BX_ID = 43

EXCHANGE_MAP = {
    1: "CBOE", 4: "PHLX", 5: "ISE", 6: "BOX", 7: "MIAX",
    9: "C2", 11: "Nasdaq OMX", 43: "Nasdaq BX", 46: "Ex_46",
    60: "BEST BBO", 65: "Ex_65", 69: "MIAX Pearl", 76: "MIAX Emerald",
}

BASKET_TICKERS = ['GME', 'AMC', 'BBBY', 'BB', 'KOSS', 'CHWY', 'BYND', 'BNED']
DEEP_OTM_RATIO = 0.30

# MIAX Pearl Equities launched September 25, 2020
PEARL_LAUNCH = pd.Timestamp('2020-09-25')


def add_business_days(date, n):
    current = pd.Timestamp(date)
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def load_trades(ticker, date_str):
    """Load ThetaData options trade parquet for ticker/date."""
    path = THETA_BASE / f"root={ticker}" / f"date={date_str}" / "part-0.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None


def get_available_dates(ticker):
    ticker_dir = THETA_BASE / f"root={ticker}"
    if not ticker_dir.exists():
        return []
    return sorted([
        d.name.replace('date=', '')
        for d in ticker_dir.iterdir()
        if d.is_dir() and d.name.startswith('date=')
    ])


def main():
    print("=" * 70)
    print("TEST 24: MIAX Pearl Deep Dive")
    print("=" * 70)

    # ================================================================
    # PART A: TIMELINE — Weekly exchange share for deep OTM puts
    # ================================================================
    print(f"\n{'='*60}")
    print("PART A: MIAX Pearl Timeline — Weekly Exchange Share")
    print(f"{'='*60}")

    gme_dates = get_available_dates('GME')
    print(f"  GME: {len(gme_dates)} dates ({gme_dates[0]} to {gme_dates[-1]})")

    # Load GME prices for deep OTM threshold
    price_df = pd.read_csv(FTD_DIR / "gme_daily_price.csv", parse_dates=['date']).set_index('date').sort_index()

    # Sample every 5th date for speed (still ~400 dates)
    sample_dates = gme_dates[::5]
    print(f"  Sampling {len(sample_dates)} dates (every 5th)")

    weekly_data = []

    for i, date_str in enumerate(sample_dates):
        dt = pd.Timestamp(date_str)
        if dt.weekday() >= 5:
            continue

        gme_price = None
        if dt in price_df.index:
            gme_price = price_df.loc[dt, 'gme_close']
        else:
            nearest = price_df.index[price_df.index.get_indexer([dt], method='nearest')]
            if len(nearest) > 0:
                gme_price = price_df.loc[nearest[0], 'gme_close']

        if gme_price is None or gme_price <= 0:
            continue

        deep_threshold = gme_price * DEEP_OTM_RATIO

        df = load_trades('GME', date_str)
        if df is None or len(df) == 0:
            continue

        puts = df[(df['right'] == 'PUT') & (df['strike'] <= deep_threshold)]
        if len(puts) == 0:
            continue

        total_vol = puts['size'].sum()
        pearl_vol = puts[puts['exchange'] == MIAX_PEARL_ID]['size'].sum()
        cboe_vol = puts[puts['exchange'] == CBOE_ID]['size'].sum()
        ise_vol = puts[puts['exchange'] == ISE_ID]['size'].sum()
        phlx_vol = puts[puts['exchange'] == PHLX_ID]['size'].sum()

        weekly_data.append({
            'date': dt,
            'total_trades': len(puts),
            'total_volume': int(total_vol),
            'pearl_pct': float(pearl_vol / total_vol) if total_vol > 0 else 0,
            'cboe_pct': float(cboe_vol / total_vol) if total_vol > 0 else 0,
            'ise_pct': float(ise_vol / total_vol) if total_vol > 0 else 0,
            'phlx_pct': float(phlx_vol / total_vol) if total_vol > 0 else 0,
            'post_launch': dt >= PEARL_LAUNCH,
        })

        if i % 50 == 0:
            print(f"    [{i}/{len(sample_dates)}] {date_str}: Pearl={weekly_data[-1]['pearl_pct']:.0%}")

    timeline_df = pd.DataFrame(weekly_data)
    print(f"\n  Processed {len(timeline_df)} dates with deep OTM puts")

    # Pre vs Post launch stats
    pre = timeline_df[~timeline_df['post_launch']]
    post = timeline_df[timeline_df['post_launch']]
    pre_pearl = pre['pearl_pct'].mean() if len(pre) > 0 else 0
    post_pearl = post['pearl_pct'].mean() if len(post) > 0 else 0

    print(f"\n  📊 MIAX Pearl share of deep OTM puts:")
    print(f"     Pre-launch (before Sep 2020):  {pre_pearl:.1%} (n={len(pre)})")
    print(f"     Post-launch (after Sep 2020):  {post_pearl:.1%} (n={len(post)})")
    print(f"     Change:                        {post_pearl - pre_pearl:+.1%}")

    # ================================================================
    # PART B: CROSS-TICKER — Same pattern in basket tickers?
    # ================================================================
    print(f"\n{'='*60}")
    print("PART B: Cross-Ticker MIAX Pearl Concentration")
    print(f"{'='*60}")

    cross_ticker_results = {}

    for ticker in BASKET_TICKERS:
        ticker_dates = get_available_dates(ticker)
        if not ticker_dates:
            print(f"  {ticker}: No data")
            continue

        # Sample dates from 2021 (peak activity period)
        target_dates = [d for d in ticker_dates if d.startswith('2021')]
        if not target_dates:
            target_dates = ticker_dates[-100:]  # Last 100 dates

        total_puts = 0
        pearl_puts = 0
        cboe_puts = 0
        exchange_counts = defaultdict(int)
        sample = target_dates[::3][:50]  # Every 3rd date, max 50

        for date_str in sample:
            df = load_trades(ticker, date_str)
            if df is None:
                continue

            # For non-GME tickers, just look at all puts under $5 strike
            puts = df[(df['right'] == 'PUT') & (df['strike'] <= 5.0)]
            if len(puts) == 0:
                continue

            total_puts += len(puts)
            pearl_puts += len(puts[puts['exchange'] == MIAX_PEARL_ID])
            cboe_puts += len(puts[puts['exchange'] == CBOE_ID])

            for eid in puts['exchange'].values:
                exchange_counts[int(eid)] += 1

        if total_puts > 0:
            pearl_pct = pearl_puts / total_puts
            cboe_pct = cboe_puts / total_puts
            top_3 = sorted(exchange_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_3_str = ', '.join(f"{EXCHANGE_MAP.get(e, f'Ex_{e}')}:{c/total_puts:.0%}" for e, c in top_3)

            print(f"  {ticker:<6} ({len(sample):>3} dates, {total_puts:>6} puts): "
                  f"Pearl={pearl_pct:>5.1%}  CBOE={cboe_pct:>5.1%}  Top3: {top_3_str}")

            cross_ticker_results[ticker] = {
                'dates_sampled': len(sample),
                'total_puts': total_puts,
                'pearl_pct': float(pearl_pct),
                'cboe_pct': float(cboe_pct),
                'top_exchanges': {EXCHANGE_MAP.get(e, f'Ex_{e}'): c/total_puts for e, c in top_3},
            }
        else:
            print(f"  {ticker}: No deep OTM puts found")

    # ================================================================
    # PART C: TRADE SIZE FINGERPRINT on MIAX Pearl
    # ================================================================
    print(f"\n{'='*60}")
    print("PART C: MIAX Pearl Trade Size Fingerprint")
    print(f"{'='*60}")

    # Load FTD data and get T+33 dates
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

    pearl_sizes_settlement = []
    pearl_sizes_control = []
    other_sizes_settlement = []

    for t33 in t33_dates:
        date_str = t33.strftime('%Y%m%d')
        gme_price = None
        if t33 in price_df.index:
            gme_price = price_df.loc[t33, 'gme_close']
        if gme_price is None or gme_price <= 0:
            continue

        df = load_trades('GME', date_str)
        if df is None:
            continue

        puts = df[(df['right'] == 'PUT') & (df['strike'] <= gme_price * DEEP_OTM_RATIO)]
        if len(puts) == 0:
            continue

        pearl = puts[puts['exchange'] == MIAX_PEARL_ID]
        other = puts[puts['exchange'] != MIAX_PEARL_ID]
        pearl_sizes_settlement.extend(pearl['size'].values)
        other_sizes_settlement.extend(other['size'].values)

        # Control: +10 BD
        ctrl = add_business_days(t33, 10)
        ctrl_str = ctrl.strftime('%Y%m%d')
        ctrl_df = load_trades('GME', ctrl_str)
        if ctrl_df is not None:
            ctrl_puts = ctrl_df[(ctrl_df['right'] == 'PUT') & (ctrl_df['strike'] <= gme_price * DEEP_OTM_RATIO)]
            ctrl_pearl = ctrl_puts[ctrl_puts['exchange'] == MIAX_PEARL_ID]
            pearl_sizes_control.extend(ctrl_pearl['size'].values)

    if pearl_sizes_settlement:
        ps = np.array(pearl_sizes_settlement)
        os_ = np.array(other_sizes_settlement)
        pc = np.array(pearl_sizes_control)

        print(f"\n  MIAX Pearl (settlement): {len(ps)} trades")
        print(f"    Median: {np.median(ps):.0f}, Mean: {np.mean(ps):.1f}")
        print(f"    Mode: {pd.Series(ps).mode().values}")
        print(f"    1-lot: {(ps == 1).sum()}/{len(ps)} ({(ps == 1).mean():.0%})")
        print(f"    ≤5-lot: {(ps <= 5).sum()}/{len(ps)} ({(ps <= 5).mean():.0%})")
        print(f"    Size distribution: {np.percentile(ps, [10, 25, 50, 75, 90])}")

        print(f"\n  Other Exchanges (settlement): {len(os_)} trades")
        print(f"    Median: {np.median(os_):.0f}, Mean: {np.mean(os_):.1f}")
        print(f"    1-lot: {(os_ == 1).sum()}/{len(os_)} ({(os_ == 1).mean():.0%})")
        print(f"    ≤5-lot: {(os_ <= 5).sum()}/{len(os_)} ({(os_ <= 5).mean():.0%})")

        if len(pc) > 0:
            print(f"\n  MIAX Pearl (control): {len(pc)} trades")
            print(f"    Median: {np.median(pc):.0f}, Mean: {np.mean(pc):.1f}")
            print(f"    1-lot: {(pc == 1).sum()}/{len(pc)} ({(pc == 1).mean():.0%})")

    # ================================================================
    # PART D: INTRADAY TIMING
    # ================================================================
    print(f"\n{'='*60}")
    print("PART D: Intraday Timing of MIAX Pearl Trades")
    print(f"{'='*60}")

    pearl_times_settlement = []
    pearl_times_control = []

    for t33 in t33_dates:
        date_str = t33.strftime('%Y%m%d')
        gme_price = None
        if t33 in price_df.index:
            gme_price = price_df.loc[t33, 'gme_close']
        if gme_price is None or gme_price <= 0:
            continue

        df = load_trades('GME', date_str)
        if df is None:
            continue

        puts = df[(df['right'] == 'PUT') & (df['strike'] <= gme_price * DEEP_OTM_RATIO)]
        pearl = puts[puts['exchange'] == MIAX_PEARL_ID]

        if len(pearl) > 0 and 'timestamp' in pearl.columns:
            times = pd.to_datetime(pearl['timestamp'], errors='coerce')
            hours = times.dt.hour + times.dt.minute / 60
            pearl_times_settlement.extend(hours.dropna().values)

        # Control
        ctrl = add_business_days(t33, 10)
        ctrl_str = ctrl.strftime('%Y%m%d')
        ctrl_df = load_trades('GME', ctrl_str)
        if ctrl_df is not None:
            ctrl_puts = ctrl_df[(ctrl_df['right'] == 'PUT') & (ctrl_df['strike'] <= gme_price * DEEP_OTM_RATIO)]
            ctrl_pearl = ctrl_puts[ctrl_puts['exchange'] == MIAX_PEARL_ID]
            if len(ctrl_pearl) > 0 and 'timestamp' in ctrl_pearl.columns:
                times = pd.to_datetime(ctrl_pearl['timestamp'], errors='coerce')
                hours = times.dt.hour + times.dt.minute / 60
                pearl_times_control.extend(hours.dropna().values)

    if pearl_times_settlement:
        st = np.array(pearl_times_settlement)
        print(f"\n  Settlement date trades ({len(st)}):")
        # Break into buckets
        buckets = [
            ("Pre-market (< 9:30)", st < 9.5),
            ("Morning (9:30-12:00)", (st >= 9.5) & (st < 12)),
            ("Midday (12:00-14:30)", (st >= 12) & (st < 14.5)),
            ("Afternoon (14:30-15:45)", (st >= 14.5) & (st < 15.75)),
            ("Last 15 min (15:45-16:00)", (st >= 15.75) & (st <= 16)),
            ("After hours (> 16:00)", st > 16),
        ]
        for label, mask in buckets:
            count = mask.sum()
            print(f"    {label:<30} {count:>5} ({count/len(st):.0%})")

    if pearl_times_control:
        ct = np.array(pearl_times_control)
        print(f"\n  Control date trades ({len(ct)}):")
        buckets = [
            ("Pre-market (< 9:30)", ct < 9.5),
            ("Morning (9:30-12:00)", (ct >= 9.5) & (ct < 12)),
            ("Midday (12:00-14:30)", (ct >= 12) & (ct < 14.5)),
            ("Afternoon (14:30-15:45)", (ct >= 14.5) & (ct < 15.75)),
            ("Last 15 min (15:45-16:00)", (ct >= 15.75) & (ct <= 16)),
            ("After hours (> 16:00)", ct > 16),
        ]
        for label, mask in buckets:
            count = mask.sum()
            print(f"    {label:<30} {count:>5} ({count/len(ct):.0%})")

    # ================================================================
    # VISUALIZATION
    # ================================================================
    fig, axes = plt.subplots(2, 2, figsize=(20, 14))
    fig.suptitle('MIAX Pearl Deep Dive — GME Deep OTM Put Activity',
                 fontsize=14, fontweight='bold', y=0.98)

    # Panel 1: Timeline
    ax = axes[0, 0]
    if len(timeline_df) > 0:
        # 20-date rolling average
        timeline_df = timeline_df.sort_values('date')
        timeline_df['pearl_rolling'] = timeline_df['pearl_pct'].rolling(10, min_periods=3).mean()
        timeline_df['cboe_rolling'] = timeline_df['cboe_pct'].rolling(10, min_periods=3).mean()

        ax.plot(timeline_df['date'], timeline_df['pearl_rolling'], color='crimson',
                linewidth=2, label='MIAX Pearl', alpha=0.9)
        ax.plot(timeline_df['date'], timeline_df['cboe_rolling'], color='steelblue',
                linewidth=2, label='CBOE', alpha=0.7)
        ax.axvline(x=PEARL_LAUNCH, color='gold', linewidth=2, linestyle='--',
                  label=f'Pearl Launch ({PEARL_LAUNCH.strftime("%Y-%m-%d")})')
        ax.fill_between(timeline_df['date'], 0, timeline_df['pearl_rolling'],
                       alpha=0.15, color='crimson')
        ax.set_xlabel('Date')
        ax.set_ylabel('Share of Deep OTM Put Volume')
        ax.set_title('Exchange Share Over Time (10-pt rolling avg)', fontsize=10)
        ax.legend(fontsize=8, loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        ax.set_ylim(0, max(0.5, timeline_df['pearl_rolling'].max() * 1.2))

    # Panel 2: Cross-ticker comparison
    ax = axes[0, 1]
    if cross_ticker_results:
        tickers = sorted(cross_ticker_results.keys())
        pearl_pcts = [cross_ticker_results[t]['pearl_pct'] for t in tickers]
        cboe_pcts = [cross_ticker_results[t]['cboe_pct'] for t in tickers]
        x = np.arange(len(tickers))
        ax.bar(x - 0.2, pearl_pcts, 0.35, label='MIAX Pearl', color='crimson', alpha=0.8)
        ax.bar(x + 0.2, cboe_pcts, 0.35, label='CBOE', color='steelblue', alpha=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(tickers, fontsize=9)
        ax.set_ylabel('% of Deep OTM Put Trades')
        ax.set_title('MIAX Pearl Share Across Basket Tickers', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis='y')

    # Panel 3: Trade size histogram
    ax = axes[1, 0]
    if pearl_sizes_settlement:
        ps = np.array(pearl_sizes_settlement)
        os_ = np.array(other_sizes_settlement)
        bins = np.arange(0, 21, 1)
        ax.hist(ps[ps <= 20], bins=bins, alpha=0.7, color='crimson',
                label=f'MIAX Pearl (n={len(ps)})', density=True, edgecolor='white')
        ax.hist(os_[os_ <= 20], bins=bins, alpha=0.5, color='steelblue',
                label=f'Other Exchanges (n={len(os_)})', density=True, edgecolor='white')
        ax.set_xlabel('Trade Size (contracts)')
        ax.set_ylabel('Density')
        ax.set_title('Trade Size Distribution — MIAX Pearl vs Others', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis='y')

    # Panel 4: Intraday timing
    ax = axes[1, 1]
    if pearl_times_settlement:
        bins = np.arange(9.5, 16.5, 0.25)
        ax.hist(pearl_times_settlement, bins=bins, alpha=0.7, color='crimson',
                label=f'Settlement (n={len(pearl_times_settlement)})', density=True, edgecolor='white')
        if pearl_times_control:
            ax.hist(pearl_times_control, bins=bins, alpha=0.5, color='steelblue',
                    label=f'Control (n={len(pearl_times_control)})', density=True, edgecolor='white')
        ax.axvline(x=15.75, color='gold', linewidth=2, linestyle='--', label='Last 15 min')
        ax.set_xlabel('Hour (ET)')
        ax.set_ylabel('Density')
        ax.set_title('Intraday Timing of MIAX Pearl Deep OTM Puts', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    fig_path = FIG_DIR / "chart_miax_pearl_deep_dive.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")

    # ================================================================
    # SAVE RESULTS
    # ================================================================
    results = {
        'timeline': {
            'pre_launch_pearl_pct': float(pre_pearl),
            'post_launch_pearl_pct': float(post_pearl),
            'delta': float(post_pearl - pre_pearl),
            'pearl_launch_date': str(PEARL_LAUNCH.date()),
            'n_pre': len(pre),
            'n_post': len(post),
        },
        'cross_ticker': cross_ticker_results,
        'fingerprint': {
            'pearl_settlement': {
                'n': len(pearl_sizes_settlement),
                'median': float(np.median(pearl_sizes_settlement)) if pearl_sizes_settlement else 0,
                'mean': float(np.mean(pearl_sizes_settlement)) if pearl_sizes_settlement else 0,
                'one_lot_pct': float(np.mean(np.array(pearl_sizes_settlement) == 1)) if pearl_sizes_settlement else 0,
                'lte_5_pct': float(np.mean(np.array(pearl_sizes_settlement) <= 5)) if pearl_sizes_settlement else 0,
            },
            'other_settlement': {
                'n': len(other_sizes_settlement),
                'median': float(np.median(other_sizes_settlement)) if other_sizes_settlement else 0,
                'mean': float(np.mean(other_sizes_settlement)) if other_sizes_settlement else 0,
                'one_lot_pct': float(np.mean(np.array(other_sizes_settlement) == 1)) if other_sizes_settlement else 0,
            },
        },
    }

    out_path = RESULTS_DIR / "miax_pearl_deep_dive.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")

    # ================================================================
    # SUMMARY
    # ================================================================
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"\n  🕐 Timeline: Pearl went from {pre_pearl:.1%} → {post_pearl:.1%} after launch ({post_pearl-pre_pearl:+.1%})")

    if cross_ticker_results:
        basket_pearl = np.mean([v['pearl_pct'] for v in cross_ticker_results.values()])
        gme_pearl = cross_ticker_results.get('GME', {}).get('pearl_pct', 0)
        print(f"  🧺 Cross-ticker: GME Pearl={gme_pearl:.1%}, Basket avg={basket_pearl:.1%}")
        for t, v in sorted(cross_ticker_results.items(), key=lambda x: x[1]['pearl_pct'], reverse=True):
            print(f"      {t}: Pearl={v['pearl_pct']:.1%}")

    if pearl_sizes_settlement:
        ps = np.array(pearl_sizes_settlement)
        print(f"  📏 Fingerprint: {(ps == 1).mean():.0%} of Pearl trades are 1-lot, median={np.median(ps):.0f}")

    print(f"\n✅ Test 24 complete.")


if __name__ == "__main__":
    main()
