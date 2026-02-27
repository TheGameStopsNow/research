#!/usr/bin/env python3
"""
Test 19: Per-Spike Tracing & Polygon TRF Cross-Reference

A) Per-Spike Tracing: Take 5 individual FTD mega-spikes and trace each
   through the survival funnel (T+3 → T+40) to verify individual-level
   behavior matches the aggregate curve.
B) Polygon TRF Equity Cross-Reference: Pull GME equity trades on peak
   phantom OI dates, filter for dark pool (exchange=4, FINRA TRF) prints
   and look for large blocks paired with options ISOs.
C) Polygon Options Trades: Pull options trades on phantom dates to verify
   ISO block trades with condition codes.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json, os, time, requests
from pathlib import Path
from datetime import timedelta, datetime
from scipy import stats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

THETA_OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
POLYGON_API_KEY = os.environ.get("POLYGON_API_KEY", "")

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

def polygon_get(url, params=None):
    """Rate-limited Polygon API call."""
    if not params:
        params = {}
    params['apiKey'] = POLYGON_API_KEY
    try:
        resp = requests.get(url, params=params, timeout=30)
        time.sleep(0.15)  # Rate limit
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"    API error {resp.status_code}: {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"    Request error: {e}")
        return None

def main():
    print("=" * 70)
    print("TEST 19: Per-Spike Tracing & Polygon TRF Cross-Reference")
    print("=" * 70)

    gme_ftd = load_csv("GME")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()

    mean_ftd = gme_ftd['quantity'].mean()
    std_ftd = gme_ftd['quantity'].std()
    threshold_3s = mean_ftd + 3 * std_ftd
    spikes = gme_ftd[gme_ftd['quantity'] > threshold_3s].sort_values('quantity', ascending=False)

    # Load OI data
    print(f"\n  Loading OI snapshots...")
    all_snapshots = []
    for f in sorted(THETA_OI_DIR.glob("oi_*.parquet")):
        date_str = f.stem.split('_')[1]
        snap_date = pd.Timestamp(datetime.strptime(date_str, '%Y%m%d'))
        df = pd.read_parquet(f)
        if len(df) == 0:
            continue
        price = np.nan
        if snap_date in price_df.index:
            price = price_df.loc[snap_date, 'gme_close']
        else:
            nearest = price_df.index[price_df.index.get_indexer([snap_date], method='nearest')]
            if len(nearest) > 0:
                price = price_df.loc[nearest[0], 'gme_close']
        df['snap_date'] = snap_date
        df['gme_price'] = price
        df['strike_ratio'] = df['strike'] / price if price > 0 else np.nan
        all_snapshots.append(df)

    full_df = pd.concat(all_snapshots, ignore_index=True)
    puts = full_df[full_df['right'] == 'PUT'].copy()
    deep_puts = puts[puts['strike_ratio'] < 0.3].copy()
    deep_puts_ts = deep_puts.groupby(['snap_date', 'strike'])['open_interest'].sum().unstack(fill_value=0)

    # Build total deep OTM put OI per date
    deep_oi_daily = deep_puts.groupby('snap_date')['open_interest'].sum()
    median_deep_oi = deep_oi_daily.median()
    mean_deep_oi = deep_oi_daily.mean()
    std_deep_oi = deep_oi_daily.std()
    elevated_threshold = median_deep_oi * 2  # 2× median = elevated
    print("  Deep OTM put OI: median={:,.0f}, mean={:,.0f}, elevated threshold (2x median)={:,.0f}".format(
        median_deep_oi, mean_deep_oi, elevated_threshold))

    def measure_oi_at_date(target_date, window=2):
        """Measure total deep OTM put OI near a specific date."""
        best_oi = 0
        best_date = None
        for o in range(-window, window + 1):
            check = target_date + timedelta(days=o)
            if check in deep_oi_daily.index:
                oi = deep_oi_daily[check]
                if oi > best_oi:
                    best_oi = oi
                    best_date = check
        is_elevated = best_oi > elevated_threshold
        return int(is_elevated), int(best_oi)

    # ============================================================
    # PART A: Per-Spike Tracing
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: Per-Spike Tracing Through the Survival Funnel")
    print(f"{'='*60}")

    # Select top 5 mega-spikes by volume — but only those with good OI coverage
    offsets = [3, 6, 9, 13, 15, 21, 27, 33, 35, 40]
    # First check which spike echo dates actually have OI snapshots
    oi_dates = set()
    for f in sorted(THETA_OI_DIR.glob("oi_*.parquet")):
        d = f.stem.split('_')[1]
        oi_dates.add(pd.Timestamp(datetime.strptime(d, '%Y%m%d')))

    def count_oi_coverage(spike_date, offsets_list):
        """Count how many echo dates have OI files."""
        hits = 0
        for offset in offsets_list:
            echo_date = add_business_days(spike_date, offset)
            # Check ±2 day window for OI
            for d_off in range(-2, 3):
                check_date = echo_date + timedelta(days=d_off)
                if check_date in oi_dates:
                    hits += 1
                    break
        return hits

    # Filter spikes to those with ≥7/10 echo dates covered by OI data
    eligible_spikes = []
    for spike_date, row in spikes.iterrows():
        coverage = count_oi_coverage(spike_date, offsets)
        if coverage >= 7:
            eligible_spikes.append((spike_date, row, coverage))

    eligible_spikes.sort(key=lambda x: x[1]['quantity'], reverse=True)
    print(f"\n  Eligible spikes (≥7/10 OI coverage): {len(eligible_spikes)} of {len(spikes)}")
    for sd, r, cov in eligible_spikes[:10]:
        print(f"    {sd.date()} ({r['quantity']:>10,.0f} FTDs) — OI coverage: {cov}/{len(offsets)}")

    top_spikes_data = eligible_spikes[:5]

    spike_traces = {}
    for spike_date, row, coverage in top_spikes_data:
        spike_qty = row['quantity']
        trace_name = f"{spike_date.strftime('%Y-%m-%d')} ({spike_qty:,.0f})"
        print(f"\n  📍 Spike: {trace_name} (OI coverage: {coverage}/{len(offsets)})")

        trace = {}
        for offset in offsets:
            echo_date = add_business_days(spike_date, offset)
            phantom_count, phantom_oi = measure_oi_at_date(echo_date, window=2)
            trace[offset] = {
                'echo_date': str(echo_date.date()),
                'phantom_count': phantom_count,
                'phantom_oi': phantom_oi,
            }
            marker = " ⭐" if phantom_count > 0 else ""
            print("    T+{:<3} -> {}: elevated={}, {:>10,} OI{}".format(offset, echo_date.strftime('%Y-%m-%d'), phantom_count, phantom_oi, marker))

        spike_traces[str(spike_date.date())] = {
            'quantity': int(spike_qty),
            'trace': trace,
        }

    # Summary: how many spikes show phantom OI at each node?
    print(f"\n  SUMMARY: Spike survival across nodes")
    print("  {:>8} {:>22} {:>6}".format('Offset', 'Spikes w/ Elevated OI', '%'))
    print("  " + "-" * 35)
    for offset in offsets:
        hits = sum(1 for s in spike_traces.values()
                   if s['trace'][offset]['phantom_count'] > 0)
        print(f"  T+{offset:<5} {hits}/{len(spike_traces):>17} {hits/len(spike_traces):>5.0%}")

    # ============================================================
    # PART B: Polygon TRF Equity Cross-Reference
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Polygon TRF Equity Cross-Reference on Phantom Dates")
    print(f"{'='*60}")

    if not POLYGON_API_KEY:
        print("  ⚠ POLYGON_API_KEY not set — skipping Polygon tests")
        polygon_results = {'error': 'No API key'}
    else:
        # Identify best phantom dates from our data
        # Use the top spike echo dates at T+33
        phantom_target_dates = []
        for spike_date, row, cov in top_spikes_data[:5]:
            echo_date = add_business_days(spike_date, 33)
            phantom_target_dates.append(echo_date)

        polygon_results = {}
        for target in phantom_target_dates[:3]:  # Check 3 dates
            date_str = target.strftime('%Y-%m-%d')
            print(f"\n  📊 Checking {date_str} (T+33 echo)...")

            # Polygon v3 trades endpoint
            url = f"https://api.polygon.io/v3/trades/GME"
            params = {
                'timestamp': date_str,
                'limit': 50000,
                'order': 'asc',
            }

            data = polygon_get(url, params)
            if not data or 'results' not in data:
                print(f"    No equity trade data for {date_str}")
                continue

            trades = pd.DataFrame(data['results'])
            print(f"    Total equity trades: {len(trades):,}")

            if 'exchange' in trades.columns:
                # Exchange 4 = FINRA TRF (dark pool / off-exchange)
                trf_trades = trades[trades['exchange'] == 4]
                print(f"    TRF (dark pool) trades: {len(trf_trades):,} ({len(trf_trades)/max(1,len(trades)):.1%})")

                if len(trf_trades) > 0 and 'size' in trf_trades.columns:
                    # Large blocks (>= 1000 shares)
                    large_blocks = trf_trades[trf_trades['size'] >= 1000]
                    print(f"    Large TRF blocks (≥1K shares): {len(large_blocks):,}")

                    if len(large_blocks) > 0:
                        print(f"    Total TRF block volume: {large_blocks['size'].sum():,} shares")
                        print(f"    Largest single TRF print: {large_blocks['size'].max():,} shares")
                        print(f"    Median TRF: {trades['size'].median():.0f}, Mean TRF: {trades['size'].mean():.0f}")

                        # Check for condition codes
                        if 'conditions' in large_blocks.columns:
                            all_conditions = []
                            for conds in large_blocks['conditions'].dropna():
                                if isinstance(conds, list):
                                    all_conditions.extend(conds)
                            if all_conditions:
                                from collections import Counter
                                cc = Counter(all_conditions)
                                print(f"    TRF block condition codes: {dict(cc.most_common(10))}")

                    polygon_results[date_str] = {
                        'total_trades': len(trades),
                        'trf_trades': len(trf_trades),
                        'trf_pct': len(trf_trades) / max(1, len(trades)),
                        'large_blocks': len(large_blocks),
                        'large_block_volume': int(large_blocks['size'].sum()) if len(large_blocks) > 0 else 0,
                        'largest_print': int(large_blocks['size'].max()) if len(large_blocks) > 0 else 0,
                    }

            # Also check overall trade size distribution
            if 'size' in trades.columns:
                odd_lots = trades[trades['size'] < 100]
                round_lots = trades[trades['size'] == 100]
                blocks = trades[trades['size'] >= 10000]
                print(f"    Size distribution: odd-lots={len(odd_lots)/len(trades):.0%}, "
                      f"round={len(round_lots)/len(trades):.0%}, blocks≥10K={len(blocks)}")

        # ============================================================
        # PART C: Polygon Options Trades on Phantom Dates
        # ============================================================
        print(f"\n{'='*60}")
        print("PART C: Polygon Options Trades — Deep OTM Puts on Phantom Dates")
        print(f"{'='*60}")

        options_results = {}
        for target in phantom_target_dates[:3]:
            date_str = target.strftime('%Y-%m-%d')
            print(f"\n  📊 Checking options on {date_str}...")

            # Get current price for deep OTM filtering
            price = np.nan
            if target in price_df.index:
                price = price_df.loc[target, 'gme_close']
            else:
                nearest = price_df.index[price_df.index.get_indexer([target], method='nearest')]
                if len(nearest) > 0:
                    price = price_df.loc[nearest[0], 'gme_close']

            if np.isnan(price):
                print(f"    No price data for {date_str}")
                continue

            deep_threshold = price * 0.3
            print(f"    GME price: ${price:.2f}, deep OTM threshold: <${deep_threshold:.2f}")

            # Polygon v3 options trades
            url = f"https://api.polygon.io/v3/trades/O:GME"
            # Need to search for specific options contracts
            # First, list available options contracts
            contracts_url = f"https://api.polygon.io/v3/reference/options/contracts"
            params = {
                'underlying_ticker': 'GME',
                'contract_type': 'put',
                'strike_price.lte': deep_threshold,
                'as_of': date_str,
                'expired': 'true',
                'limit': 100,
            }

            data = polygon_get(contracts_url, params)
            if not data or 'results' not in data:
                print(f"    No options contract data")
                continue

            contracts = data['results']
            print(f"    Deep OTM put contracts on {date_str}: {len(contracts)}")

            total_deep_trades = 0
            total_deep_volume = 0
            iso_count = 0
            block_count = 0
            top_prints = []

            for contract in contracts[:10]:  # Check top 10 contracts
                ticker = contract['ticker']
                strike = contract.get('strike_price', 0)

                trades_url = f"https://api.polygon.io/v3/trades/{ticker}"
                tparams = {
                    'timestamp': date_str,
                    'limit': 1000,
                    'order': 'asc',
                }

                tdata = polygon_get(trades_url, tparams)
                if not tdata or 'results' not in tdata:
                    continue

                trades_list = tdata['results']
                if len(trades_list) == 0:
                    continue

                tdf = pd.DataFrame(trades_list)
                total_deep_trades += len(tdf)
                if 'size' in tdf.columns:
                    total_deep_volume += tdf['size'].sum()
                    blocks = tdf[tdf['size'] >= 100]
                    block_count += len(blocks)

                    for _, t in blocks.iterrows():
                        conditions = t.get('conditions', [])
                        is_iso = 18 in (conditions if isinstance(conditions, list) else [])
                        if is_iso:
                            iso_count += 1
                        top_prints.append({
                            'strike': strike,
                            'size': int(t['size']),
                            'conditions': conditions,
                            'is_iso': is_iso,
                        })

                print(f"    ${strike}: {len(trades_list)} trades, {tdf['size'].sum() if 'size' in tdf.columns else 0} contracts")

            print(f"\n    TOTAL deep OTM on {date_str}:")
            print(f"      Trades: {total_deep_trades}")
            print(f"      Volume: {total_deep_volume:,} contracts")
            print(f"      Blocks (≥100): {block_count}")
            print(f"      ISOs (code 18): {iso_count}")

            if top_prints:
                top_prints.sort(key=lambda x: x['size'], reverse=True)
                print(f"      Top 5 prints:")
                for p in top_prints[:5]:
                    iso_tag = " [ISO]" if p['is_iso'] else ""
                    print(f"        ${p['strike']}: {p['size']:,} lots, conditions={p['conditions']}{iso_tag}")

            options_results[date_str] = {
                'total_trades': total_deep_trades,
                'total_volume': int(total_deep_volume),
                'blocks': block_count,
                'isos': iso_count,
                'top_prints': top_prints[:10],
            }

    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('GME Per-Spike Tracing & Polygon TRF Cross-Reference',
                 fontsize=14, fontweight='bold', y=0.98)

    # Panel 1: Per-spike traces overlaid
    ax = axes[0, 0]
    colors = ['red', 'blue', 'green', 'purple', 'orange']
    for idx, (spike_date, trace_data) in enumerate(spike_traces.items()):
        x = offsets
        y = [trace_data['trace'][o]['phantom_oi'] for o in offsets]
        ax.plot(x, y, 'o-', color=colors[idx % len(colors)], linewidth=1.5,
                markersize=5, label=f"{spike_date} ({trace_data['quantity']:,.0f})",
                alpha=0.8)

    ax.set_yscale('symlog', linthresh=10)
    ax.set_xlabel('Settlement Offset (Business Days)')
    ax.set_ylabel('Deep OTM Put OI (contracts - log scale)')
    ax.set_title('GME Individual Spike Traces — Elevated Deep OTM Put OI', fontsize=10)
    ax.legend(fontsize=7, title=f'Spikes with ≥7/{len(offsets)} OI coverage', title_fontsize=7)
    ax.grid(True, alpha=0.3)

    # Panel 2: Per-spike OI volume
    ax = axes[0, 1]
    for idx, (spike_date, trace_data) in enumerate(spike_traces.items()):
        x = offsets
        y = [trace_data['trace'][o]['phantom_oi'] for o in offsets]
        ax.plot(x, y, 'o-', color=colors[idx % len(colors)], linewidth=1.5,
                markersize=5, label=f"{spike_date}", alpha=0.8)

    ax.set_yscale('symlog', linthresh=10)
    ax.set_xlabel('Settlement Offset (Business Days)')
    ax.set_ylabel('Deep OTM Put OI (contracts - log scale)')
    ax.set_title('Deep OTM Put OI at Each Settlement Node', fontsize=10)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)

    # Panel 3: Hit rate per node
    ax = axes[1, 0]
    hit_rates = []
    for offset in offsets:
        hits = sum(1 for s in spike_traces.values()
                   if s['trace'][offset]['phantom_count'] > 0)
        hit_rates.append(hits / len(spike_traces))

    ax.bar(offsets, hit_rates, width=2, color='steelblue', alpha=0.8)
    ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='50% line')
    ax.set_xlabel('Settlement Offset (Business Days)')
    ax.set_ylabel('Fraction of Spikes with Elevated OI')
    ax.set_title('Per-Node Elevated OI Rate Across Top 5 Mega-Spikes', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 1.1)

    # Panel 4: Summary text
    ax = axes[1, 1]
    ax.axis('off')
    summary_text = "PER-SPIKE TRACING RESULTS\n" + "=" * 40 + "\n\n"
    for spike_date, trace_data in spike_traces.items():
        hits = sum(1 for o in offsets if trace_data['trace'][o]['phantom_count'] > 0)
        total_oi = sum(trace_data['trace'][o]['phantom_oi'] for o in offsets)
        summary_text += f"{spike_date} ({trace_data['quantity']:>10,} FTDs)\n"
        summary_text += f"  Phantom hits: {hits}/{len(offsets)} nodes\n"
        summary_text += f"  Total phantom OI: {total_oi:,}\n\n"

    if polygon_results and 'error' not in polygon_results:
        summary_text += "\nPOLYGON TRF RESULTS\n" + "=" * 40 + "\n"
        for date, r in polygon_results.items():
            summary_text += f"\n{date}:\n"
            summary_text += f"  TRF: {r['trf_trades']:,} ({r['trf_pct']:.0%})\n"
            summary_text += f"  Blocks: {r['large_blocks']}, {r['large_block_volume']:,} sh\n"

    ax.text(0.03, 0.95, summary_text, transform=ax.transAxes,
            fontfamily='monospace', fontsize=7, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()
    fig_path = FIG_DIR / "chart_per_spike_tracing.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")

    # Save results
    results = {
        'part_a_spike_traces': spike_traces,
        'part_b_polygon_trf': polygon_results if not isinstance(polygon_results, dict) or 'error' not in polygon_results else {},
        'part_c_polygon_options': options_results if 'options_results' in dir() else {},
    }

    out_path = RESULTS_DIR / "per_spike_tracing.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 19 complete.")

if __name__ == "__main__":
    main()
