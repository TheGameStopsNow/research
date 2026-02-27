#!/usr/bin/env python3
"""
Test 23: Deep OTM Put Exchange Triangulation (ThetaData)

Uses LOCAL ThetaData options trade parquets (2,038 days of GME data) to
identify which OPTIONS EXCHANGE handles deep OTM put trades on T+33
settlement echo dates vs. control dates.

Each options exchange has a small number of designated market makers.
If settlement-related put activity concentrates on one exchange,
that narrows the field to 3-4 firms.

Data: ThetaData parquets at power-tracks-research/data/raw/thetadata/trades/root=GME/
Schema: symbol, expiry, strike, right, timestamp, condition, size, exchange, price
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json, os, sys
from pathlib import Path
from datetime import timedelta, datetime
from collections import Counter, defaultdict

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
FTD_DIR = DATA_DIR / "ftd"
RESULTS_DIR = REPO_ROOT / "results" / "ftd_research"
FIG_DIR = REPO_ROOT / "figures" / "ftd_research"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

THETA_TRADES_DIR = Path.home() / "Documents/GitHub/power-tracks-research/data/raw/thetadata/trades/root=GME"

# ThetaData options exchange mapping
# Source: https://http-docs.thetadata.us/docs/theta-data-rest-api-v2/cc07b05e1af84-exchange-mapping
EXCHANGE_MAP = {
    0: "COMPOSITE",
    1: "CBOE",
    2: "AMEX (NYSE American)",
    3: "PHLX (Nasdaq)",
    4: "PACIFIC",
    5: "ISE",
    6: "BOX",
    7: "MIAX",
    8: "BATS (Cboe BZX)",
    9: "C2 (Cboe C2)",
    10: "ARCA (NYSE Arca)",
    11: "NASDAQ OMX",
    12: "ISE GEMINI",
    13: "EMLD (MIAX Emerald)",
    14: "EDGX (Cboe EDGX)",
    15: "MPRL (MIAX Pearl)",
    16: "MEMX",
    60: "BEST BBO",
    62: "NSDQ NOM",
}

# Known DMMs per exchange (public info from exchange websites)
KNOWN_DMMS = {
    "CBOE": ["Citadel Securities", "Wolverine Trading", "Susquehanna (SIG)"],
    "AMEX (NYSE American)": ["Citadel Securities", "GTS", "Virtu Financial"],
    "PHLX (Nasdaq)": ["Susquehanna (SIG)", "Citadel Securities", "Morgan Stanley"],
    "ISE": ["Susquehanna (SIG)", "Citadel Securities", "Wolverine Trading"],
    "ARCA (NYSE Arca)": ["Citadel Securities", "GTS", "Virtu Financial"],
    "BATS (Cboe BZX)": ["Citadel Securities", "Wolverine Trading", "Two Sigma"],
    "MIAX": ["Susquehanna (SIG)", "Citadel Securities", "Wolverine Trading"],
    "C2 (Cboe C2)": ["Citadel Securities", "Wolverine Trading"],
    "BOX": ["Citadel Securities", "Susquehanna (SIG)"],
    "NASDAQ OMX": ["Citadel Securities", "Susquehanna (SIG)", "Dash Financial"],
}

# Deep OTM threshold: strike < 30% of current price
DEEP_OTM_RATIO = 0.30

# Target strikes that showed highest OI enrichment
TARGET_STRIKES = {0.5, 1.0, 2.0, 2.5, 3.0, 5.0, 10.0, 20.0}


def add_business_days(date, n):
    current = pd.Timestamp(date)
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def load_ftd_data():
    path = FTD_DIR / "GME_ftd.csv"
    df = pd.read_csv(path, parse_dates=['date'])
    return df.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()


def load_trades_for_date(date):
    """Load ThetaData options trade parquet for a given date."""
    date_str = date.strftime('%Y%m%d')
    path = THETA_TRADES_DIR / f"date={date_str}" / "part-0.parquet"
    if not path.exists():
        return None
    try:
        df = pd.read_parquet(path)
        return df
    except Exception as e:
        print(f"      Error loading {path}: {e}")
        return None


def get_gme_price_for_date(date, price_df):
    """Get GME close price for a date."""
    if date in price_df.index:
        return price_df.loc[date, 'gme_close']
    nearest = price_df.index[price_df.index.get_indexer([date], method='nearest')]
    if len(nearest) > 0:
        return price_df.loc[nearest[0], 'gme_close']
    return None


def analyze_trades_by_exchange(df, gme_price, filter_deep_otm=True):
    """Analyze options trades grouped by exchange."""
    if df is None or len(df) == 0:
        return None

    # Filter to puts only
    puts = df[df['right'] == 'PUT'].copy()
    if len(puts) == 0:
        return None

    if filter_deep_otm and gme_price and gme_price > 0:
        deep_threshold = gme_price * DEEP_OTM_RATIO
        puts = puts[puts['strike'] <= deep_threshold].copy()

    if len(puts) == 0:
        return None

    result = {
        'total_put_trades': len(puts),
        'total_put_volume': int(puts['size'].sum()),
        'exchange_breakdown': {},
        'condition_breakdown': {},
        'strike_breakdown': {},
        'size_stats': {
            'median': float(puts['size'].median()),
            'mean': float(puts['size'].mean()),
        },
    }

    # Exchange breakdown
    for exch_id, grp in puts.groupby('exchange'):
        name = EXCHANGE_MAP.get(int(exch_id), f"Exchange_{exch_id}")
        total_vol = int(puts['size'].sum())
        result['exchange_breakdown'][name] = {
            'id': int(exch_id),
            'trades': len(grp),
            'volume': int(grp['size'].sum()),
            'pct_trades': len(grp) / len(puts),
            'pct_volume': int(grp['size'].sum()) / total_vol if total_vol > 0 else 0,
            'median_size': float(grp['size'].median()),
            'unique_strikes': len(grp['strike'].unique()),
            'top_strikes': sorted(grp['strike'].value_counts().head(5).index.tolist()),
        }

    # Condition breakdown
    cc = Counter(puts['condition'].values)
    for code, count in cc.most_common(15):
        result['condition_breakdown'][int(code)] = {
            'count': count,
            'pct': count / len(puts),
        }

    # Strike breakdown
    for strike, grp in puts.groupby('strike'):
        if len(grp) >= 5:  # Only strikes with meaningful activity
            top_exch = grp['exchange'].value_counts().head(3)
            exch_names = {EXCHANGE_MAP.get(int(e), f"Ex_{e}"): int(c) for e, c in top_exch.items()}
            result['strike_breakdown'][float(strike)] = {
                'trades': len(grp),
                'volume': int(grp['size'].sum()),
                'top_exchanges': exch_names,
            }

    return result


def main():
    print("=" * 70)
    print("TEST 23: Deep OTM Put Exchange Triangulation (ThetaData)")
    print("=" * 70)

    if not THETA_TRADES_DIR.exists():
        print(f"  ERROR: ThetaData trades directory not found: {THETA_TRADES_DIR}")
        sys.exit(1)

    available_dates = sorted([
        d.name.replace('date=', '')
        for d in THETA_TRADES_DIR.iterdir()
        if d.is_dir() and d.name.startswith('date=')
    ])
    print(f"  ThetaData: {len(available_dates)} dates of GME options trades")
    print(f"  Range: {available_dates[0]} to {available_dates[-1]}")

    ftd_df = load_ftd_data()
    print(f"  FTD records: {len(ftd_df)} ({ftd_df.index.min().date()} to {ftd_df.index.max().date()})")

    # Load price data
    price_path = FTD_DIR / "gme_daily_price.csv"
    price_df = pd.read_csv(price_path, parse_dates=['date']).set_index('date').sort_index()

    # Get T+33 echo dates from mega-spikes
    mean_ftd = ftd_df['quantity'].mean()
    std_ftd = ftd_df['quantity'].std()
    threshold = mean_ftd + 3 * std_ftd
    spikes = ftd_df[ftd_df['quantity'] > threshold].sort_values('quantity', ascending=False)

    t33_targets = []
    for spike_date, row in spikes.head(20).iterrows():
        t33_date = add_business_days(spike_date, 33)
        t33_str = t33_date.strftime('%Y%m%d')
        if t33_str in available_dates:
            t33_targets.append({
                'spike_date': spike_date,
                'spike_qty': int(row['quantity']),
                't33_date': t33_date,
            })

    print(f"  T+33 echo dates with trade data: {len(t33_targets)}")

    # Generate control dates (±15 BD from each T+33)
    available_set = set(available_dates)
    control_dates = []
    for t in t33_targets:
        for offset in [10, -10, 20, -20]:
            ctrl = add_business_days(t['t33_date'], offset)
            ctrl_str = ctrl.strftime('%Y%m%d')
            if ctrl_str in available_set:
                control_dates.append(ctrl)
    control_dates = list(set(control_dates))[:len(t33_targets) * 3]  # ~3:1 controls

    print(f"  Control dates: {len(control_dates)}")

    # ================================================================
    # PART A: Deep OTM Put Exchange Distribution on T+33 Echo Dates
    # ================================================================
    print(f"\n{'='*60}")
    print("PART A: Deep OTM Put Trades by Exchange — T+33 Echo Dates")
    print(f"{'='*60}")

    settlement_results = []
    for i, t in enumerate(t33_targets):
        date = t['t33_date']
        gme_price = get_gme_price_for_date(date, price_df)
        if gme_price is None:
            continue

        print(f"\n  [{i+1}/{len(t33_targets)}] {date.strftime('%Y-%m-%d')} (spike: {t['spike_date'].strftime('%Y-%m-%d')}, "
              f"{t['spike_qty']:,} FTDs, GME=${gme_price:.2f})")

        trades = load_trades_for_date(date)
        if trades is None:
            print(f"    No trade data")
            continue

        analysis = analyze_trades_by_exchange(trades, gme_price, filter_deep_otm=True)
        if analysis is None:
            print(f"    No deep OTM put trades")
            continue

        analysis['date'] = date.strftime('%Y-%m-%d')
        settlement_results.append(analysis)

        print(f"    Deep OTM put trades: {analysis['total_put_trades']:,}, volume: {analysis['total_put_volume']:,}")
        sorted_exch = sorted(analysis['exchange_breakdown'].items(),
                            key=lambda x: x[1]['volume'], reverse=True)
        for name, data in sorted_exch[:5]:
            print(f"      {name:<25} {data['trades']:>6} trades ({data['pct_trades']:>5.1%}), "
                  f"{data['volume']:>8,} vol ({data['pct_volume']:>5.1%}), "
                  f"med={data['median_size']:.0f}, strikes={data['unique_strikes']}")

    # ================================================================
    # PART B: Control Date Exchange Distribution
    # ================================================================
    print(f"\n{'='*60}")
    print("PART B: Deep OTM Put Trades by Exchange — Control Dates")
    print(f"{'='*60}")

    control_results = []
    for i, date in enumerate(control_dates):
        gme_price = get_gme_price_for_date(date, price_df)
        if gme_price is None:
            continue

        trades = load_trades_for_date(date)
        if trades is None:
            continue

        analysis = analyze_trades_by_exchange(trades, gme_price, filter_deep_otm=True)
        if analysis is None:
            continue

        analysis['date'] = date.strftime('%Y-%m-%d')
        control_results.append(analysis)

        if i < 3:  # Print first few
            print(f"\n  [{i+1}] {date.strftime('%Y-%m-%d')} (GME=${gme_price:.2f})")
            print(f"    Deep OTM put trades: {analysis['total_put_trades']:,}")

    print(f"\n  Processed {len(control_results)} control dates with deep OTM put data")

    # ================================================================
    # AGGREGATE COMPARISON
    # ================================================================
    print(f"\n{'='*60}")
    print("AGGREGATE: Exchange Distribution — Settlement vs Control")
    print(f"{'='*60}")

    def aggregate_exchanges(results_list):
        combined = defaultdict(lambda: {'trades': 0, 'volume': 0, 'pct_trades': [], 'pct_volume': [], 'n': 0})
        for r in results_list:
            for name, data in r.get('exchange_breakdown', {}).items():
                combined[name]['trades'] += data['trades']
                combined[name]['volume'] += data['volume']
                combined[name]['pct_trades'].append(data['pct_trades'])
                combined[name]['pct_volume'].append(data['pct_volume'])
                combined[name]['n'] += 1
                combined[name]['id'] = data['id']
        agg = {}
        for name, data in combined.items():
            agg[name] = {
                'id': data['id'],
                'total_trades': data['trades'],
                'total_volume': data['volume'],
                'avg_pct_trades': np.mean(data['pct_trades']),
                'avg_pct_volume': np.mean(data['pct_volume']),
                'n_dates': data['n'],
            }
        return agg

    settle_agg = aggregate_exchanges(settlement_results)
    ctrl_agg = aggregate_exchanges(control_results)

    all_exchanges = sorted(
        set(list(settle_agg.keys()) + list(ctrl_agg.keys())),
        key=lambda x: settle_agg.get(x, {}).get('avg_pct_volume', 0),
        reverse=True
    )

    print(f"\n  {'Exchange':<25} {'Sett %Vol':>10} {'Ctrl %Vol':>10} {'Delta':>8} {'Sett Trades':>12} {'Known DMMs'}")
    print("  " + "-" * 100)

    exchange_deltas = {}
    for exch in all_exchanges:
        s_pct = settle_agg.get(exch, {}).get('avg_pct_volume', 0)
        c_pct = ctrl_agg.get(exch, {}).get('avg_pct_volume', 0)
        delta = s_pct - c_pct
        s_trades = settle_agg.get(exch, {}).get('total_trades', 0)
        dmms = ', '.join(KNOWN_DMMS.get(exch, ['—']))

        print(f"  {exch:<25} {s_pct:>9.1%} {c_pct:>9.1%} {delta:>+7.1%} {s_trades:>11,}  {dmms}")

        exchange_deltas[exch] = {
            'settlement_pct': float(s_pct),
            'control_pct': float(c_pct),
            'delta': float(delta),
            'settlement_trades': s_trades,
            'settlement_volume': settle_agg.get(exch, {}).get('total_volume', 0),
        }

    # ================================================================
    # PART C: Per-Strike Exchange Concentration
    # ================================================================
    print(f"\n{'='*60}")
    print("PART C: Which Exchange Handles Each Strike?")
    print(f"{'='*60}")

    # Aggregate all settlement trades by strike → exchange
    strike_exchange_map = defaultdict(lambda: defaultdict(int))
    for r in settlement_results:
        for strike, data in r.get('strike_breakdown', {}).items():
            for exch_name, count in data.get('top_exchanges', {}).items():
                strike_exchange_map[strike][exch_name] += count

    print(f"\n  {'Strike':>8} {'Top Exchange':>25} {'% of Trades':>12} {'#2 Exchange':>25} {'#2 %':>8}")
    print("  " + "-" * 80)

    strike_results = {}
    for strike in sorted(strike_exchange_map.keys()):
        exch_counts = strike_exchange_map[strike]
        total = sum(exch_counts.values())
        sorted_exchanges = sorted(exch_counts.items(), key=lambda x: x[1], reverse=True)

        if len(sorted_exchanges) >= 2:
            top1 = sorted_exchanges[0]
            top2 = sorted_exchanges[1]
            print(f"  ${strike:>7.1f} {top1[0]:>25} {top1[1]/total:>11.1%} {top2[0]:>25} {top2[1]/total:>7.1%}")
        elif sorted_exchanges:
            top1 = sorted_exchanges[0]
            print(f"  ${strike:>7.1f} {top1[0]:>25} {top1[1]/total:>11.1%}")

        strike_results[float(strike)] = {
            name: {'count': count, 'pct': count/total}
            for name, count in sorted_exchanges[:5]
        }

    # ================================================================
    # VISUALIZATION
    # ================================================================
    fig, axes = plt.subplots(2, 2, figsize=(20, 14))
    fig.suptitle('Deep OTM Put Exchange Triangulation — GME (ThetaData)',
                 fontsize=14, fontweight='bold', y=0.98)

    # Panel 1: Exchange volume share comparison
    ax = axes[0, 0]
    top_ex = sorted(exchange_deltas.items(),
                   key=lambda x: x[1]['settlement_volume'], reverse=True)[:10]
    names = [e[0] for e in top_ex]
    s_vals = [e[1]['settlement_pct'] for e in top_ex]
    c_vals = [e[1]['control_pct'] for e in top_ex]
    x = np.arange(len(names))
    ax.barh(x - 0.2, s_vals, 0.35, label='T+33 Echo', color='crimson', alpha=0.8)
    ax.barh(x + 0.2, c_vals, 0.35, label='Control', color='steelblue', alpha=0.8)
    ax.set_yticks(x)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel('% of Deep OTM Put Volume')
    ax.set_title('Options Exchange: Settlement vs Control', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='x')
    ax.invert_yaxis()

    # Panel 2: Delta chart
    ax = axes[0, 1]
    delta_sorted = sorted(exchange_deltas.items(),
                         key=lambda x: abs(x[1]['delta']), reverse=True)[:10]
    d_names = [e[0] for e in delta_sorted]
    d_vals = [e[1]['delta'] for e in delta_sorted]
    colors = ['crimson' if d > 0 else 'steelblue' for d in d_vals]
    ax.barh(range(len(d_names)), d_vals, color=colors, alpha=0.8)
    ax.set_yticks(range(len(d_names)))
    ax.set_yticklabels(d_names, fontsize=8)
    ax.set_xlabel('Settlement % − Control %')
    ax.set_title('Exchange Volume Delta (T+33 vs Control)', fontsize=10)
    ax.axvline(x=0, color='black', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='x')
    ax.invert_yaxis()

    # Panel 3: Per-strike exchange stacking
    ax = axes[1, 0]
    target_list = sorted([s for s in strike_results.keys() if s <= 20])[:8]
    if target_list:
        all_exch_names = set()
        for s in target_list:
            all_exch_names.update(strike_results[s].keys())
        exch_order = sorted(all_exch_names,
                          key=lambda e: sum(strike_results.get(s, {}).get(e, {}).get('pct', 0) for s in target_list),
                          reverse=True)[:6]

        bottom = np.zeros(len(target_list))
        for exch_name in exch_order:
            vals = [strike_results.get(s, {}).get(exch_name, {}).get('pct', 0) for s in target_list]
            ax.bar(range(len(target_list)), vals, bottom=bottom, label=exch_name, alpha=0.8)
            bottom += np.array(vals)

        ax.set_xticks(range(len(target_list)))
        ax.set_xticklabels([f'${s}' for s in target_list], fontsize=9)
        ax.set_ylabel('% of Trades')
        ax.set_title('Exchange Distribution per Strike (Settlement Dates)', fontsize=10)
        ax.legend(fontsize=6, loc='upper right', ncol=2)
        ax.grid(True, alpha=0.3, axis='y')

    # Panel 4: Summary text with DMM implications
    ax = axes[1, 1]
    ax.axis('off')
    summary = "EXCHANGE TRIANGULATION RESULTS\n" + "=" * 40 + "\n\n"
    summary += f"Settlement dates: {len(settlement_results)}\n"
    summary += f"Control dates: {len(control_results)}\n\n"

    if exchange_deltas:
        top = max(exchange_deltas.items(), key=lambda x: x[1]['settlement_volume'])
        summary += f"DOMINANT EXCHANGE:\n  {top[0]}\n"
        summary += f"  {top[1]['settlement_pct']:.1%} of settlement volume\n"
        summary += f"  {top[1]['settlement_trades']:,} trades\n"
        if top[0] in KNOWN_DMMS:
            summary += f"\n  Known DMMs:\n"
            for dmm in KNOWN_DMMS[top[0]]:
                summary += f"    • {dmm}\n"

        top_delta = max(exchange_deltas.items(), key=lambda x: abs(x[1]['delta']))
        dir_text = "MORE" if top_delta[1]['delta'] > 0 else "LESS"
        summary += f"\nLARGEST SHIFT:\n  {top_delta[0]}\n"
        summary += f"  {abs(top_delta[1]['delta']):.1%} {dir_text} on settlement dates\n"

    ax.text(0.03, 0.95, summary, transform=ax.transAxes,
            fontfamily='monospace', fontsize=7, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()
    fig_path = FIG_DIR / "chart_deep_otm_exchange_triangulation.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")

    # ================================================================
    # SAVE RESULTS
    # ================================================================
    results = {
        'metadata': {
            'n_settlement_dates': len(settlement_results),
            'n_control_dates': len(control_results),
            'data_source': 'ThetaData local parquets',
            'deep_otm_threshold': f'{DEEP_OTM_RATIO:.0%} of GME price',
        },
        'exchange_comparison': {
            k: v for k, v in exchange_deltas.items()
        },
        'strike_exchange_map': {
            str(k): {name: data for name, data in v.items()}
            for k, v in strike_results.items()
        },
        'known_dmms': KNOWN_DMMS,
        'per_date': {
            r['date']: {
                'total_trades': r['total_put_trades'],
                'total_volume': r['total_put_volume'],
                'exchange_breakdown': {
                    name: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                          for kk, vv in data.items() if kk != 'top_strikes'}
                    for name, data in r['exchange_breakdown'].items()
                },
            } for r in settlement_results
        },
    }

    out_path = RESULTS_DIR / "deep_otm_exchange_triangulation.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")

    # ================================================================
    # SUMMARY
    # ================================================================
    print(f"\n{'='*60}")
    print("SUMMARY — WHO IS DOING THIS?")
    print(f"{'='*60}")

    if exchange_deltas:
        # Top exchange by volume
        top = max(exchange_deltas.items(), key=lambda x: x[1]['settlement_volume'])
        print(f"\n  🔍 Dominant Exchange for Deep OTM Puts: {top[0]}")
        print(f"     {top[1]['settlement_pct']:.1%} of volume on settlement dates")
        print(f"     {top[1]['settlement_trades']:,} total trades")
        if top[0] in KNOWN_DMMS:
            print(f"     Known DMMs on this exchange:")
            for dmm in KNOWN_DMMS[top[0]]:
                print(f"       • {dmm}")

        # Top delta
        top_delta = max(exchange_deltas.items(), key=lambda x: x[1]['delta'])
        if top_delta[1]['delta'] > 0.01:
            print(f"\n  🔍 Exchange with INCREASED settlement activity: {top_delta[0]}")
            print(f"     +{top_delta[1]['delta']:.1%} more volume on T+33 dates")
            if top_delta[0] in KNOWN_DMMS:
                print(f"     DMMs: {', '.join(KNOWN_DMMS[top_delta[0]])}")

        # Check if one exchange dominates the key strikes
        for strike in [0.5, 1.0, 5.0]:
            if strike in strike_results:
                top_exch = max(strike_results[strike].items(), key=lambda x: x[1]['pct'])
                if top_exch[1]['pct'] > 0.3:
                    print(f"\n  🔍 ${strike} puts: {top_exch[1]['pct']:.0%} on {top_exch[0]}")
                    if top_exch[0] in KNOWN_DMMS:
                        print(f"     DMMs: {', '.join(KNOWN_DMMS[top_exch[0]])}")

    print(f"\n✅ Test 23 complete.")


if __name__ == "__main__":
    main()
