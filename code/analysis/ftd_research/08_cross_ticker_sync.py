#!/usr/bin/env python3
"""
Test 7: Cross-Ticker FTD Synchronization & Lead-Lag Analysis
Tests whether XRT/IJH FTDs LEAD GME FTDs or vice versa.
beckettcat's mechanics imply: XRT creation → GME extraction → GME FTD spike
If true, XRT FTDs should lead GME FTDs by the creation/redemption cycle time.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
from pathlib import Path
from scipy import stats

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
    print("TEST 7: Cross-Ticker FTD Synchronization & Lead-Lag")
    print("=" * 70)
    
    # Load all tickers
    tickers = ['GME', 'XRT', 'IJH', 'IWM', 'AMC', 'KOSS']
    data = {}
    for t in tickers:
        d = load_csv(t)
        if d is not None:
            data[t] = d
            print(f"  Loaded {t}: {len(d)} records")
    
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()
    
    # Build aligned daily matrix
    all_dates = pd.date_range('2021-01-01', '2026-01-31', freq='B')
    matrix = pd.DataFrame(index=all_dates)
    for t in data:
        matrix[t] = data[t]['quantity'].reindex(all_dates).fillna(0)
    matrix['gme_price'] = price_df['gme_close'].reindex(all_dates).ffill()
    
    # ============================================================
    # PART A: Contemporaneous Correlations
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: FTD Cross-Correlations (same day)")
    print(f"{'='*60}")
    
    corr_matrix = matrix[list(data.keys())].corr()
    print(f"\n{corr_matrix.to_string()}")
    
    # ============================================================
    # PART B: Lead-Lag Analysis (does XRT FTD predict GME FTD?)
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Lead-Lag Analysis — Who leads whom?")
    print(f"{'='*60}")
    
    # Cross-correlation at different lags
    print(f"\n  XRT FTD → GME FTD (positive lag = XRT leads)")
    print(f"  {'Lag (days)':<12} {'Correlation':>12}")
    print("  " + "-" * 30)
    
    lead_lag_results = {}
    
    for leader, follower in [('XRT', 'GME'), ('IJH', 'GME'), ('IWM', 'GME'), ('AMC', 'GME'), ('KOSS', 'GME')]:
        if leader in matrix.columns and follower in matrix.columns:
            lags = range(-10, 11)
            correlations = []
            for lag in lags:
                if lag >= 0:
                    corr = matrix[leader].iloc[:-max(1,lag) if lag > 0 else len(matrix)].corr(
                        matrix[follower].iloc[lag:] if lag > 0 else matrix[follower]
                    )
                else:
                    corr = matrix[leader].iloc[-lag:].corr(
                        matrix[follower].iloc[:lag]
                    )
                correlations.append(float(corr) if pd.notna(corr) else 0)
            
            best_lag = lags[np.argmax(correlations)]
            best_corr = max(correlations)
            
            lead_lag_results[f'{leader}→{follower}'] = {
                'best_lag': int(best_lag),
                'best_correlation': float(best_corr),
                'all_correlations': {int(l): float(c) for l, c in zip(lags, correlations)}
            }
            
            lead_word = f"{leader} leads by {best_lag}d" if best_lag > 0 else (f"{follower} leads by {-best_lag}d" if best_lag < 0 else "Contemporaneous")
            print(f"  {leader:>4}→{follower:<4}: best lag = {best_lag:>3}d  (r={best_corr:.3f})  [{lead_word}]")
    
    # ============================================================
    # PART C: Granger-like Test — Does XRT FTD predict GME FTD?
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: Predictive Signal — FTD Changes Predicting FTD Changes")
    print(f"{'='*60}")
    
    # Use 5-day changes to avoid noise
    changes = pd.DataFrame(index=matrix.index)
    for t in data:
        changes[f'{t}_chg5d'] = matrix[t].rolling(5).sum().pct_change()
    changes['gme_price_chg5d'] = matrix['gme_price'].pct_change(5)
    changes = changes.replace([np.inf, -np.inf], np.nan).dropna()
    
    print(f"\n  Correlation of 5-day FTD change with FUTURE 5-day GME price change:")
    print(f"  {'Signal (today)':25s} {'→ GME price (5d fwd)':>20} {'→ GME price (10d fwd)':>22}")
    print("  " + "-" * 70)
    
    price_fwd_5 = matrix['gme_price'].pct_change(5).shift(-5)
    price_fwd_10 = matrix['gme_price'].pct_change(10).shift(-10)
    
    predict_results = {}
    for t in data:
        ftd_5d = matrix[t].rolling(5).sum()
        c5 = ftd_5d.corr(price_fwd_5)
        c10 = ftd_5d.corr(price_fwd_10)
        print(f"  {t + ' FTD 5d':25s} {c5:>20.4f} {c10:>22.4f}")
        predict_results[t] = {'corr_5d_fwd': float(c5) if pd.notna(c5) else 0, 'corr_10d_fwd': float(c10) if pd.notna(c10) else 0}
    
    # ============================================================
    # PART D: Synchronized Surge Events
    # ============================================================
    print(f"\n{'='*60}")
    print("PART D: Synchronized FTD Surges (Multiple Tickers Spike Together)")
    print(f"{'='*60}")
    
    # Count how many of {XRT, IJH, IWM, AMC, KOSS} are elevated on each day
    etf_tickers = ['XRT', 'IJH', 'IWM']
    meme_tickers = ['AMC', 'KOSS']
    
    thresholds = {}
    for t in data:
        thresholds[t] = matrix[t].mean() + 2 * matrix[t].std()
    
    matrix['etf_spike_count'] = sum(
        (matrix[t] > thresholds[t]).astype(int) for t in etf_tickers if t in matrix.columns
    )
    matrix['meme_spike_count'] = sum(
        (matrix[t] > thresholds[t]).astype(int) for t in meme_tickers if t in matrix.columns
    )
    matrix['total_spike_count'] = matrix['etf_spike_count'] + matrix['meme_spike_count'] + \
        (matrix['GME'] > thresholds.get('GME', 0)).astype(int)
    
    print(f"\n  Simultaneous spike count distribution:")
    for count in range(0, 6):
        n = (matrix['total_spike_count'] == count).sum()
        if n > 0:
            dates = matrix[matrix['total_spike_count'] == count]
            avg_gme_price = dates['gme_price'].mean()
            fwd = dates['gme_price'].pct_change(10).shift(-10)
            # Actually compute fwd differently
            fwd_returns = []
            for d in dates.index:
                fwd_p = price_df[price_df.index > d].head(10)
                if len(fwd_p) >= 10 and pd.notna(dates.loc[d, 'gme_price']):
                    fwd_returns.append(fwd_p.iloc[9]['gme_close'] / dates.loc[d, 'gme_price'] - 1)
            avg_fwd = np.mean(fwd_returns) if fwd_returns else np.nan
            fwd_str = f"{avg_fwd:.1%}" if not np.isnan(avg_fwd) else "N/A"
            print(f"    {count} tickers spiking: {n:>5} days | avg GME ${avg_gme_price:.2f} | avg 10d fwd: {fwd_str}")
    
    # Show dates with 3+ spikes
    multi_spike = matrix[matrix['total_spike_count'] >= 3].copy()
    if len(multi_spike) > 0:
        print(f"\n  Dates with 3+ tickers spiking simultaneously:")
        print(f"  {'Date':<12} {'GME':>10} {'XRT':>10} {'IJH':>10} {'IWM':>10} {'AMC':>10} {'KOSS':>8} {'Price':>8}")
        print("  " + "-" * 85)
        for date, row in multi_spike.head(25).iterrows():
            spiking = []
            for t in data:
                if row.get(t, 0) > thresholds.get(t, 0):
                    spiking.append(t)
            gme_p = f"${row['gme_price']:.2f}" if pd.notna(row['gme_price']) else "N/A"
            vals = " ".join(f"{row.get(t, 0):>10,.0f}" for t in ['GME', 'XRT', 'IJH', 'IWM', 'AMC', 'KOSS'])
            print(f"  {date.strftime('%Y-%m-%d'):<12} {vals} {gme_p:>8}")
    
    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Cross-Ticker FTD Analysis', fontsize=14, fontweight='bold', y=0.98)
    
    # Panel 1: Correlation heatmap
    import matplotlib.colors as mcolors
    ax = axes[0, 0]
    im = ax.imshow(corr_matrix.values, cmap='RdBu_r', vmin=-0.5, vmax=0.5)
    ax.set_xticks(range(len(corr_matrix.columns)))
    ax.set_xticklabels(corr_matrix.columns, rotation=45, ha='right')
    ax.set_yticks(range(len(corr_matrix.index)))
    ax.set_yticklabels(corr_matrix.index)
    for i in range(len(corr_matrix)):
        for j in range(len(corr_matrix)):
            ax.text(j, i, f'{corr_matrix.values[i,j]:.2f}', ha='center', va='center', fontsize=8)
    fig.colorbar(im, ax=ax)
    ax.set_title('FTD Cross-Correlation Matrix', fontsize=10)
    
    # Panel 2: Lead-lag plot for XRT→GME
    ax = axes[0, 1]
    for pair, result in lead_lag_results.items():
        lags = sorted(result['all_correlations'].keys())
        corrs = [result['all_correlations'][l] for l in lags]
        ax.plot(lags, corrs, marker='o', markersize=3, label=pair)
    ax.axvline(x=0, color='gray', linestyle=':', linewidth=0.5)
    ax.axhline(y=0, color='gray', linestyle=':', linewidth=0.5)
    ax.set_xlabel('Lag (days, positive = leader leads)')
    ax.set_ylabel('Cross-correlation')
    ax.legend(fontsize=7)
    ax.set_title('Lead-Lag Cross-Correlations', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Panel 3: Spike count distribution
    ax = axes[1, 0]
    colors_bar = {'GME': 'steelblue', 'XRT': 'red', 'IJH': 'orange', 'IWM': 'purple', 'AMC': 'green', 'KOSS': 'brown'}
    bottom = np.zeros(len(matrix))
    for t in data:
        elevated = (matrix[t] > thresholds[t]).astype(float) * matrix[t]
        ax.fill_between(matrix.index, 0, (matrix[t] > thresholds[t]).astype(int).rolling(10).sum(),
                       alpha=0.3, color=colors_bar.get(t, 'gray'), label=t)
    ax.set_ylabel('Elevated ticker count (10d window)')
    ax.legend(fontsize=7, loc='upper right')
    ax.set_title('FTD Spike Density Over Time', fontsize=10)
    ax.grid(True, alpha=0.2)
    
    # Panel 4: GME price with multi-spike overlay
    ax = axes[1, 1]
    ax.plot(matrix.index, matrix['gme_price'], color='#1a1a2e', linewidth=0.8, label='GME Close')
    if len(multi_spike) > 0:
        ax.scatter(multi_spike.index, multi_spike['gme_price'],
                  color='red', s=25, zorder=5, alpha=0.7, label=f'3+ ticker spikes (n={len(multi_spike)})')
    ax.set_ylabel('GME Price ($)')
    ax.legend(fontsize=8)
    ax.set_title('GME Price with Multi-Ticker Spike Events', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = FIG_DIR / "cross_ticker_sync.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    # Save results
    results = {
        'correlations': corr_matrix.to_dict(),
        'lead_lag': lead_lag_results,
        'predictive': predict_results,
    }
    
    out_path = RESULTS_DIR / "cross_ticker_sync.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 7 complete.")

if __name__ == "__main__":
    main()
