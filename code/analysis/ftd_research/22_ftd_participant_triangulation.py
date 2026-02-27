#!/usr/bin/env python3
"""
Test 22: FTD Participant Triangulation

Attempts to narrow down WHO (or which venue/trade type) is recycling FTDs
by comparing trade-level behavior on settlement deadline dates vs. control
dates across multiple dimensions:

  A) Exchange Heatmap — volume by exchange on T+33 dates vs control
  B) Trade Size Distribution by Exchange
  C) Condition Code Forensics — which trade types cluster on settlement dates
  D) FINRA Short Volume by Exchange

Requires: POLYGON_API_KEY environment variable
Data: SEC FTD CSVs, GME daily prices
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json, os, time, requests, sys
from pathlib import Path
from datetime import timedelta, datetime
from collections import Counter

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

POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "")

# -------------------------------------------------------------------
# Polygon exchange ID → name mapping (pulled from Polygon reference API)
# -------------------------------------------------------------------
EXCHANGE_MAP = {
    1: "NYSE American",
    2: "Nasdaq BX",
    3: "NYSE National",
    4: "FINRA ADF",
    5: "UTP SIP",
    6: "ISE Stocks",
    7: "Cboe EDGA",
    8: "Cboe EDGX",
    9: "NYSE Chicago",
    10: "NYSE",
    11: "NYSE Arca",
    12: "Nasdaq",
    13: "CTA SIP",
    14: "LTSE",
    15: "IEX",
    16: "Cboe Stock Exch",
    17: "Nasdaq PHLX",
    18: "Cboe BYX",
    19: "Cboe BZX",
    20: "MIAX Pearl",
    21: "MEMX",
    22: "24X National",
    62: "OTC Equity",
    201: "FINRA NYSE TRF",
    202: "FINRA Nasdaq TRF Cart",
    203: "FINRA Nasdaq TRF Chi",
}

# Group exchanges for analysis
TRF_IDS = {4, 6, 16, 201, 202, 203}  # All off-exchange / TRF
LIT_IDS = {1, 2, 3, 7, 8, 9, 10, 11, 12, 14, 15, 17, 18, 19, 20, 21, 22}

# Polygon condition code reference (equity trades)
CONDITION_MAP = {
    0: "Regular",
    2: "Acquisition",
    5: "Distribution",
    7: "Bunched",
    10: "Sold Last",
    12: "Average Price",
    14: "Derivatively Priced",
    15: "Opening/Reopening",
    16: "Closing",
    17: "Re-Opening",
    22: "Form T (After Hours)",
    23: "Extended Hrs (Sold Out)",
    29: "Sub-Penny",
    33: "Odd Lot Trade",
    37: "Contingent Trade",
    38: "Qualified Contingent",
    41: "Prior Reference Price",
    52: "Corrected Consolidated Close",
    53: "Rule 155 Trade (NYSE)",
}


def add_business_days(date, n):
    current = pd.Timestamp(date)
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def polygon_get(url, params=None, max_retries=3):
    """Rate-limited Polygon API call with retries."""
    if not params:
        params = {}
    params['apiKey'] = POLYGON_API_KEY
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            time.sleep(0.15)  # Rate limit
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = 2 ** attempt
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    API error {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            print(f"    Request error: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
    return None


def polygon_get_all_trades(ticker, date_str):
    """Fetch ALL trades for a ticker on a date (handles pagination)."""
    all_trades = []
    url = f"https://api.polygon.io/v3/trades/{ticker}"
    params = {
        'timestamp': date_str,
        'limit': 50000,
        'order': 'asc',
    }

    while True:
        data = polygon_get(url, params)
        if not data or 'results' not in data:
            break
        all_trades.extend(data['results'])
        # Check for next_url (pagination)
        next_url = data.get('next_url')
        if next_url:
            url = next_url
            params = {}  # next_url includes params
        else:
            break

    return all_trades


def load_ftd_data():
    """Load GME FTD data."""
    path = FTD_DIR / "GME_ftd.csv"
    if not path.exists():
        print(f"  ERROR: {path} not found")
        sys.exit(1)
    df = pd.read_csv(path, parse_dates=['date'])
    df = df.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    return df


def get_t33_dates(ftd_df, n=10):
    """Get the top N FTD mega-spikes and their T+33 echo dates."""
    mean_ftd = ftd_df['quantity'].mean()
    std_ftd = ftd_df['quantity'].std()
    threshold = mean_ftd + 3 * std_ftd

    spikes = ftd_df[ftd_df['quantity'] > threshold].sort_values('quantity', ascending=False)

    dates = []
    for spike_date, row in spikes.head(n).iterrows():
        t33_date = add_business_days(spike_date, 33)
        # Only include dates where Polygon would have data (post-2015)
        if t33_date >= pd.Timestamp('2015-01-01'):
            dates.append({
                'spike_date': spike_date,
                'spike_qty': int(row['quantity']),
                't33_date': t33_date,
            })

    return dates


def get_control_dates(target_date, n_controls=3, offset=10):
    """Get control dates offset by ±N business days from target."""
    controls = []
    for mult in [-1, 1]:
        for i in range(1, n_controls + 1):
            ctrl = add_business_days(target_date, mult * offset * i)
            # Skip weekends
            while ctrl.weekday() >= 5:
                ctrl += timedelta(days=1)
            controls.append(ctrl)
    return controls


def analyze_trades(trades_list):
    """Analyze a list of trade dicts from Polygon."""
    if not trades_list:
        return None

    df = pd.DataFrame(trades_list)

    result = {
        'total_trades': len(df),
        'total_volume': 0,
        'exchange_breakdown': {},
        'condition_breakdown': {},
        'size_stats': {},
        'trf_pct': 0.0,
    }

    if 'size' not in df.columns:
        return result

    result['total_volume'] = int(df['size'].sum())

    # ----- Exchange breakdown -----
    if 'exchange' in df.columns:
        for exch_id, grp in df.groupby('exchange'):
            name = EXCHANGE_MAP.get(int(exch_id), f"Unknown({exch_id})")
            is_trf = int(exch_id) in TRF_IDS
            result['exchange_breakdown'][name] = {
                'id': int(exch_id),
                'trades': len(grp),
                'volume': int(grp['size'].sum()),
                'pct_trades': len(grp) / len(df),
                'pct_volume': float(grp['size'].sum() / df['size'].sum()) if df['size'].sum() > 0 else 0,
                'median_size': float(grp['size'].median()),
                'mean_size': float(grp['size'].mean()),
                'is_trf': is_trf,
            }

        trf_trades = df[df['exchange'].isin(TRF_IDS)]
        result['trf_pct'] = len(trf_trades) / len(df) if len(df) > 0 else 0

    # ----- Condition code breakdown -----
    if 'conditions' in df.columns:
        all_conditions = []
        for conds in df['conditions'].dropna():
            if isinstance(conds, list):
                all_conditions.extend([int(c) for c in conds])
        cc = Counter(all_conditions)
        for code, count in cc.most_common(20):
            name = CONDITION_MAP.get(code, f"Code_{code}")
            result['condition_breakdown'][name] = {
                'code': code,
                'count': count,
                'pct': count / len(df),
            }

    # ----- Size distribution -----
    result['size_stats'] = {
        'median': float(df['size'].median()),
        'mean': float(df['size'].mean()),
        'p25': float(df['size'].quantile(0.25)),
        'p75': float(df['size'].quantile(0.75)),
        'odd_lot_pct': float((df['size'] < 100).sum() / len(df)),
        'round_lot_pct': float((df['size'] == 100).sum() / len(df)),
        'block_count': int((df['size'] >= 10000).sum()),
    }

    return result


def fetch_finra_short_volume(date_str):
    """Fetch FINRA consolidated short volume for GME on a given date.
    Returns dict with exchange-level short volume data."""
    # FINRA short volume daily files
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    formatted = dt.strftime('%Y%m%d')
    url = f"https://cdn.finra.org/equity/regsho/daily/CNMSshvol{formatted}.txt"

    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None

        lines = resp.text.strip().split('\n')
        result = {}
        for line in lines[1:]:  # Skip header
            parts = line.split('|')
            if len(parts) >= 5 and parts[1].strip() == 'GME':
                exchange = parts[0].strip()
                short_vol = int(parts[2].strip())
                exempt_vol = int(parts[3].strip())
                total_vol = int(parts[4].strip())
                result[exchange] = {
                    'short_volume': short_vol,
                    'short_exempt_volume': exempt_vol,
                    'total_volume': total_vol,
                    'short_pct': short_vol / total_vol if total_vol > 0 else 0,
                }
        return result
    except Exception as e:
        print(f"    FINRA fetch error for {date_str}: {e}")
        return None


def main():
    print("=" * 70)
    print("TEST 22: FTD Participant Triangulation")
    print("=" * 70)

    if not POLYGON_API_KEY:
        print("ERROR: POLYGON_API_KEY not set")
        sys.exit(1)

    ftd_df = load_ftd_data()
    print(f"  Loaded {len(ftd_df)} FTD records ({ftd_df.index.min().date()} to {ftd_df.index.max().date()})")

    # Get T+33 echo dates from top mega-spikes
    t33_targets = get_t33_dates(ftd_df, n=15)
    print(f"  Found {len(t33_targets)} T+33 echo dates from mega-spikes (post-2015)")

    # ================================================================
    # PART A: Exchange Heatmap — T+33 dates vs control dates
    # ================================================================
    print(f"\n{'='*60}")
    print("PART A: Exchange Volume Heatmap — Settlement vs Control")
    print(f"{'='*60}")

    settlement_results = []
    control_results = []

    for i, target in enumerate(t33_targets[:8]):  # Check 8 dates
        t33_str = target['t33_date'].strftime('%Y-%m-%d')
        print(f"\n  [{i+1}/8] T+33 echo: {t33_str} (from spike {target['spike_date'].strftime('%Y-%m-%d')}, {target['spike_qty']:,} FTDs)")

        # Settlement date trades
        trades = polygon_get_all_trades('GME', t33_str)
        if trades:
            analysis = analyze_trades(trades)
            if analysis:
                analysis['date'] = t33_str
                analysis['type'] = 'settlement'
                settlement_results.append(analysis)
                print(f"    Settlement: {analysis['total_trades']:,} trades, {analysis['total_volume']:,} vol, TRF={analysis['trf_pct']:.1%}")

        # Control dates (±10, ±20 BD offset)
        controls = get_control_dates(target['t33_date'], n_controls=2, offset=10)
        for ctrl in controls[:3]:  # Use 3 control dates per settlement date
            ctrl_str = ctrl.strftime('%Y-%m-%d')
            ctrl_trades = polygon_get_all_trades('GME', ctrl_str)
            if ctrl_trades:
                ctrl_analysis = analyze_trades(ctrl_trades)
                if ctrl_analysis:
                    ctrl_analysis['date'] = ctrl_str
                    ctrl_analysis['type'] = 'control'
                    control_results.append(ctrl_analysis)

        # Small progress note
        if settlement_results:
            last = settlement_results[-1]
            if last['exchange_breakdown']:
                top_exch = max(last['exchange_breakdown'].items(),
                              key=lambda x: x[1]['volume'])
                print(f"    Top exchange: {top_exch[0]} ({top_exch[1]['pct_volume']:.0%} of volume)")

    # ================================================================
    # Aggregate Exchange Comparison
    # ================================================================
    print(f"\n{'='*60}")
    print("AGGREGATE EXCHANGE COMPARISON")
    print(f"{'='*60}")

    def aggregate_exchange_stats(results_list):
        """Average exchange breakdowns across multiple dates."""
        combined = {}
        for r in results_list:
            for exch_name, stats in r.get('exchange_breakdown', {}).items():
                if exch_name not in combined:
                    combined[exch_name] = {'pct_trades': [], 'pct_volume': [],
                                           'median_size': [], 'id': stats['id'],
                                           'is_trf': stats['is_trf']}
                combined[exch_name]['pct_trades'].append(stats['pct_trades'])
                combined[exch_name]['pct_volume'].append(stats['pct_volume'])
                combined[exch_name]['median_size'].append(stats['median_size'])
        # Average
        agg = {}
        for name, data in combined.items():
            agg[name] = {
                'id': data['id'],
                'is_trf': data['is_trf'],
                'avg_pct_trades': np.mean(data['pct_trades']),
                'avg_pct_volume': np.mean(data['pct_volume']),
                'avg_median_size': np.mean(data['median_size']),
                'n_dates': len(data['pct_trades']),
            }
        return agg

    settle_agg = aggregate_exchange_stats(settlement_results)
    ctrl_agg = aggregate_exchange_stats(control_results)

    # Print comparison
    all_exchanges = sorted(set(list(settle_agg.keys()) + list(ctrl_agg.keys())),
                          key=lambda x: settle_agg.get(x, {}).get('avg_pct_volume', 0),
                          reverse=True)

    print(f"\n  {'Exchange':<25} {'Sett %Vol':>10} {'Ctrl %Vol':>10} {'Delta':>8} {'Sett MedSz':>11} {'Ctrl MedSz':>11}")
    print("  " + "-" * 80)

    exchange_deltas = {}
    for exch in all_exchanges[:15]:  # Top 15 exchanges
        s_vol = settle_agg.get(exch, {}).get('avg_pct_volume', 0)
        c_vol = ctrl_agg.get(exch, {}).get('avg_pct_volume', 0)
        delta = s_vol - c_vol
        s_med = settle_agg.get(exch, {}).get('avg_median_size', 0)
        c_med = ctrl_agg.get(exch, {}).get('avg_median_size', 0)
        is_trf = settle_agg.get(exch, ctrl_agg.get(exch, {})).get('is_trf', False)
        tag = " [TRF]" if is_trf else ""

        print(f"  {exch+tag:<25} {s_vol:>9.1%} {c_vol:>9.1%} {delta:>+7.1%} {s_med:>10.1f} {c_med:>10.1f}")
        exchange_deltas[exch] = {'delta': delta, 's_vol': s_vol, 'c_vol': c_vol, 'is_trf': is_trf}

    # ================================================================
    # PART B: Condition Code Forensics
    # ================================================================
    print(f"\n{'='*60}")
    print("PART B: Condition Code Comparison — Settlement vs Control")
    print(f"{'='*60}")

    def aggregate_condition_stats(results_list):
        combined = {}
        for r in results_list:
            for cond_name, stats in r.get('condition_breakdown', {}).items():
                if cond_name not in combined:
                    combined[cond_name] = {'pcts': [], 'code': stats['code']}
                combined[cond_name]['pcts'].append(stats['pct'])
        agg = {}
        for name, data in combined.items():
            agg[name] = {
                'code': data['code'],
                'avg_pct': np.mean(data['pcts']),
                'n_dates': len(data['pcts']),
            }
        return agg

    settle_cond = aggregate_condition_stats(settlement_results)
    ctrl_cond = aggregate_condition_stats(control_results)

    all_conditions = sorted(set(list(settle_cond.keys()) + list(ctrl_cond.keys())),
                           key=lambda x: settle_cond.get(x, {}).get('avg_pct', 0),
                           reverse=True)

    print(f"\n  {'Condition':<30} {'Sett Avg%':>10} {'Ctrl Avg%':>10} {'Delta':>8}")
    print("  " + "-" * 62)

    condition_deltas = {}
    for cond in all_conditions[:15]:
        s_pct = settle_cond.get(cond, {}).get('avg_pct', 0)
        c_pct = ctrl_cond.get(cond, {}).get('avg_pct', 0)
        delta = s_pct - c_pct
        print(f"  {cond:<30} {s_pct:>9.2%} {c_pct:>9.2%} {delta:>+7.2%}")
        condition_deltas[cond] = {'delta': delta, 's_pct': s_pct, 'c_pct': c_pct}

    # ================================================================
    # PART C: Trade Size Distribution Comparison
    # ================================================================
    print(f"\n{'='*60}")
    print("PART C: Trade Size Distribution — Settlement vs Control")
    print(f"{'='*60}")

    def aggregate_size_stats(results_list):
        stats = {k: [] for k in ['median', 'mean', 'odd_lot_pct', 'round_lot_pct', 'block_count']}
        for r in results_list:
            ss = r.get('size_stats', {})
            for k in stats:
                if k in ss:
                    stats[k].append(ss[k])
        return {k: np.mean(v) if v else 0 for k, v in stats.items()}

    settle_size = aggregate_size_stats(settlement_results)
    ctrl_size = aggregate_size_stats(control_results)

    print(f"\n  {'Metric':<25} {'Settlement':>12} {'Control':>12} {'Delta':>10}")
    print("  " + "-" * 60)
    for metric in ['median', 'mean', 'odd_lot_pct', 'round_lot_pct', 'block_count']:
        s = settle_size.get(metric, 0)
        c = ctrl_size.get(metric, 0)
        d = s - c
        if 'pct' in metric:
            print(f"  {metric:<25} {s:>11.1%} {c:>11.1%} {d:>+9.1%}")
        else:
            print(f"  {metric:<25} {s:>11.1f} {c:>11.1f} {d:>+9.1f}")

    # ================================================================
    # PART D: FINRA Short Volume by Exchange
    # ================================================================
    print(f"\n{'='*60}")
    print("PART D: FINRA Short Volume by Exchange — Settlement vs Control")
    print(f"{'='*60}")

    finra_settle = {}
    finra_ctrl = {}

    for r in settlement_results[:5]:
        sv = fetch_finra_short_volume(r['date'])
        if sv:
            for exch, data in sv.items():
                if exch not in finra_settle:
                    finra_settle[exch] = {'short_pcts': [], 'total_vols': []}
                finra_settle[exch]['short_pcts'].append(data['short_pct'])
                finra_settle[exch]['total_vols'].append(data['total_volume'])
            print(f"  Settlement {r['date']}: {len(sv)} exchanges")

    for r in control_results[:10]:
        sv = fetch_finra_short_volume(r['date'])
        if sv:
            for exch, data in sv.items():
                if exch not in finra_ctrl:
                    finra_ctrl[exch] = {'short_pcts': [], 'total_vols': []}
                finra_ctrl[exch]['short_pcts'].append(data['short_pct'])
                finra_ctrl[exch]['total_vols'].append(data['total_volume'])

    if finra_settle:
        all_finra = sorted(set(list(finra_settle.keys()) + list(finra_ctrl.keys())))
        print(f"\n  {'Exchange':<15} {'Sett Short%':>12} {'Ctrl Short%':>12} {'Delta':>8} {'Sett AvgVol':>12}")
        print("  " + "-" * 62)
        finra_deltas = {}
        for exch in all_finra:
            s_pct = np.mean(finra_settle.get(exch, {}).get('short_pcts', [0]))
            c_pct = np.mean(finra_ctrl.get(exch, {}).get('short_pcts', [0]))
            s_vol = np.mean(finra_settle.get(exch, {}).get('total_vols', [0]))
            delta = s_pct - c_pct
            print(f"  {exch:<15} {s_pct:>11.1%} {c_pct:>11.1%} {delta:>+7.1%} {s_vol:>11,.0f}")
            finra_deltas[exch] = {'delta': delta, 's_pct': s_pct, 'c_pct': c_pct}
    else:
        print("  No FINRA data available for these dates")
        finra_deltas = {}

    # ================================================================
    # VISUALIZATION
    # ================================================================
    fig, axes = plt.subplots(2, 2, figsize=(20, 14))
    fig.suptitle('FTD Participant Triangulation — Settlement vs Control Dates',
                 fontsize=14, fontweight='bold', y=0.98)

    # Panel 1: Exchange volume share comparison
    ax = axes[0, 0]
    top_exchanges = sorted(exchange_deltas.items(), key=lambda x: abs(x[1]['delta']), reverse=True)[:10]
    names = [e[0] for e in top_exchanges]
    s_vals = [e[1]['s_vol'] for e in top_exchanges]
    c_vals = [e[1]['c_vol'] for e in top_exchanges]
    x = np.arange(len(names))
    ax.barh(x - 0.2, s_vals, 0.35, label='Settlement (T+33)', color='crimson', alpha=0.8)
    ax.barh(x + 0.2, c_vals, 0.35, label='Control', color='steelblue', alpha=0.8)
    ax.set_yticks(x)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel('% of Total Volume')
    ax.set_title('Exchange Volume Share: Settlement vs Control', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='x')
    ax.invert_yaxis()

    # Panel 2: Condition code deltas
    ax = axes[0, 1]
    cond_sorted = sorted(condition_deltas.items(), key=lambda x: abs(x[1]['delta']), reverse=True)[:10]
    cond_names = [c[0] for c in cond_sorted]
    cond_deltas_vals = [c[1]['delta'] for c in cond_sorted]
    colors = ['crimson' if d > 0 else 'steelblue' for d in cond_deltas_vals]
    ax.barh(range(len(cond_names)), cond_deltas_vals, color=colors, alpha=0.8)
    ax.set_yticks(range(len(cond_names)))
    ax.set_yticklabels(cond_names, fontsize=8)
    ax.set_xlabel('Settlement % − Control %')
    ax.set_title('Condition Code Delta (Settlement vs Control)', fontsize=10)
    ax.axvline(x=0, color='black', linewidth=0.5)
    ax.grid(True, alpha=0.3, axis='x')
    ax.invert_yaxis()

    # Panel 3: Trade size comparison
    ax = axes[1, 0]
    metrics = ['median', 'mean', 'odd_lot_pct']
    settle_vals = [settle_size[m] for m in metrics]
    ctrl_vals = [ctrl_size[m] for m in metrics]
    labels = ['Median Size', 'Mean Size', 'Odd Lot %']
    x = np.arange(len(labels))
    ax.bar(x - 0.2, settle_vals, 0.35, label='Settlement', color='crimson', alpha=0.8)
    ax.bar(x + 0.2, ctrl_vals, 0.35, label='Control', color='steelblue', alpha=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_title('Trade Size Characteristics: Settlement vs Control', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    # Panel 4: FINRA short volume deltas
    ax = axes[1, 1]
    if finra_deltas:
        finra_sorted = sorted(finra_deltas.items(), key=lambda x: abs(x[1]['delta']), reverse=True)[:8]
        f_names = [f[0] for f in finra_sorted]
        f_deltas = [f[1]['delta'] for f in finra_sorted]
        f_colors = ['crimson' if d > 0 else 'steelblue' for d in f_deltas]
        ax.barh(range(len(f_names)), f_deltas, color=f_colors, alpha=0.8)
        ax.set_yticks(range(len(f_names)))
        ax.set_yticklabels(f_names, fontsize=8)
        ax.set_xlabel('Settlement Short% − Control Short%')
        ax.set_title('FINRA Short Volume Delta by Exchange', fontsize=10)
        ax.axvline(x=0, color='black', linewidth=0.5)
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()
    else:
        ax.text(0.5, 0.5, 'No FINRA data available', transform=ax.transAxes,
                ha='center', va='center', fontsize=12, color='gray')
        ax.set_title('FINRA Short Volume (No Data)', fontsize=10)

    plt.tight_layout()
    fig_path = FIG_DIR / "chart_participant_triangulation.png"
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
            't33_targets': [{
                'spike_date': str(t['spike_date'].date()),
                'spike_qty': t['spike_qty'],
                't33_date': str(t['t33_date'].date()),
            } for t in t33_targets[:8]],
        },
        'exchange_comparison': {
            'settlement': {k: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                              for kk, vv in v.items()}
                          for k, v in settle_agg.items()},
            'control': {k: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                           for kk, vv in v.items()}
                       for k, v in ctrl_agg.items()},
            'deltas': {k: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                          for kk, vv in v.items()}
                      for k, v in exchange_deltas.items()},
        },
        'condition_comparison': {
            'settlement': {k: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                              for kk, vv in v.items()}
                          for k, v in settle_cond.items()},
            'control': {k: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                           for kk, vv in v.items()}
                       for k, v in ctrl_cond.items()},
            'deltas': {k: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                          for kk, vv in v.items()}
                      for k, v in condition_deltas.items()},
        },
        'size_comparison': {
            'settlement': {k: float(v) for k, v in settle_size.items()},
            'control': {k: float(v) for k, v in ctrl_size.items()},
        },
        'finra_short_volume': {
            'settlement': {k: {kk: float(np.mean(vv)) for kk, vv in v.items()}
                          for k, v in finra_settle.items()},
            'control': {k: {kk: float(np.mean(vv)) for kk, vv in v.items()}
                       for k, v in finra_ctrl.items()},
            'deltas': {k: {kk: float(vv) if isinstance(vv, (np.floating, float)) else vv
                          for kk, vv in v.items()}
                      for k, v in finra_deltas.items()},
        },
    }

    out_path = RESULTS_DIR / "participant_triangulation.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")

    # ================================================================
    # SUMMARY
    # ================================================================
    print(f"\n{'='*60}")
    print("SUMMARY — TOP TRIANGULATION SIGNALS")
    print(f"{'='*60}")

    # Top exchange anomaly
    if exchange_deltas:
        top_exch = max(exchange_deltas.items(), key=lambda x: abs(x[1]['delta']))
        dir_text = "MORE" if top_exch[1]['delta'] > 0 else "LESS"
        print(f"\n  🔍 Top Exchange Signal: {top_exch[0]}")
        print(f"     {abs(top_exch[1]['delta']):.1%} {dir_text} volume on settlement dates")
        print(f"     Settlement: {top_exch[1]['s_vol']:.1%}, Control: {top_exch[1]['c_vol']:.1%}")

    # Top condition code anomaly
    if condition_deltas:
        top_cond = max(condition_deltas.items(), key=lambda x: abs(x[1]['delta']))
        dir_text = "MORE" if top_cond[1]['delta'] > 0 else "LESS"
        print(f"\n  🔍 Top Condition Code Signal: {top_cond[0]}")
        print(f"     {abs(top_cond[1]['delta']):.2%} {dir_text} frequent on settlement dates")

    # TRF share comparison
    if settlement_results and control_results:
        settle_trf = np.mean([r['trf_pct'] for r in settlement_results])
        ctrl_trf = np.mean([r['trf_pct'] for r in control_results])
        print(f"\n  🔍 TRF (Dark Pool) Share:")
        print(f"     Settlement: {settle_trf:.1%}, Control: {ctrl_trf:.1%}, Delta: {settle_trf-ctrl_trf:+.1%}")

    # Size comparison
    if settle_size and ctrl_size:
        print(f"\n  🔍 Trade Size:")
        print(f"     Settlement median: {settle_size['median']:.1f}, Control median: {ctrl_size['median']:.1f}")
        print(f"     Settlement odd-lot%: {settle_size['odd_lot_pct']:.1%}, Control: {ctrl_size['odd_lot_pct']:.1%}")

    print(f"\n✅ Test 22 complete.")


if __name__ == "__main__":
    main()
