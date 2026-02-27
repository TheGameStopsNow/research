#!/usr/bin/env python3
"""
Test 2: GMEU Composite FTD Score
beckettcat hypothesis: GMEU FTDs should be double-counted. Build composite score:
  composite = GME_FTD + (2 × GMEU_FTD) + (0.5 × warrant_FTDs)
Test October 2025 GMEU spike → GME low → T+33 rally.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
from pathlib import Path
from datetime import timedelta

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

def load_ticker(ticker):
    """Load a ticker's FTD data if available."""
    path = DATA_DIR / f"{ticker}_ftd.csv"
    if path.exists():
        return pd.read_csv(path, parse_dates=['date'])
    return None

def main():
    print("=" * 70)
    print("TEST 2: GMEU Composite FTD Score")
    print("=" * 70)
    
    # Load all relevant tickers
    gme = load_ticker("GME")
    gmeu = load_ticker("GMEU")
    igme = load_ticker("IGME")
    gmey = load_ticker("GMEY")
    price_path = DATA_DIR / "gme_daily_price.csv"
    
    if gme is None:
        print("  ❌ Missing GME FTD data. Run 01_load_ftd_data.py first.")
        return
    
    gme_price = pd.read_csv(price_path, parse_dates=['date']) if price_path.exists() else None
    
    # Report availability
    print(f"\n  Data availability:")
    for name, df in [("GME", gme), ("GMEU", gmeu), ("IGME", igme), ("GMEY", gmey)]:
        if df is not None:
            print(f"    {name:6s}: {len(df):>6,} records | {df['date'].min().strftime('%Y-%m-%d')} – {df['date'].max().strftime('%Y-%m-%d')}")
        else:
            print(f"    {name:6s}: ❌ Not found in SEC FTD data")
    
    # Build daily FTD series for each ticker
    daily = {}
    for name, df in [("GME", gme), ("GMEU", gmeu), ("IGME", igme), ("GMEY", gmey)]:
        if df is not None:
            d = df.groupby('date')['quantity'].sum().reset_index()
            d = d.set_index('date').sort_index()
            daily[name] = d['quantity']
    
    # Build composite index
    # Use full date range from GME
    all_dates = pd.date_range(gme['date'].min(), gme['date'].max(), freq='B')
    composite = pd.DataFrame(index=all_dates)
    
    for name in daily:
        composite[name] = daily[name].reindex(all_dates).fillna(0)
    
    # Composite score: GME + 2×GMEU + 0.5×(IGME+GMEY)
    composite['composite'] = composite.get('GME', 0)
    if 'GMEU' in composite.columns:
        composite['composite'] += 2 * composite['GMEU']
    if 'IGME' in composite.columns:
        composite['composite'] += 0.5 * composite['IGME']
    if 'GMEY' in composite.columns:
        composite['composite'] += 0.5 * composite['GMEY']
    
    # Also compute GME-only for comparison
    composite['gme_only'] = composite.get('GME', 0)
    
    # Rolling sums
    composite['composite_10d'] = composite['composite'].rolling(10, min_periods=1).sum()
    composite['gme_only_10d'] = composite['gme_only'].rolling(10, min_periods=1).sum()
    
    # Add GME price
    if gme_price is not None:
        gme_price['date'] = pd.to_datetime(gme_price['date'])
        gme_price = gme_price.set_index('date')
        composite = composite.join(gme_price['gme_close'], how='left')
        composite['gme_close'] = composite['gme_close'].ffill()
    
    # Forward returns
    if 'gme_close' in composite.columns:
        composite['fwd_5d'] = composite['gme_close'].pct_change(5).shift(-5)
        composite['fwd_10d'] = composite['gme_close'].pct_change(10).shift(-10)
        composite['fwd_20d'] = composite['gme_close'].pct_change(20).shift(-20)
    
    # Stats
    mean_c = composite['composite_10d'].mean()
    std_c = composite['composite_10d'].std()
    thresh_2s = mean_c + 2 * std_c
    thresh_3s = mean_c + 3 * std_c
    
    print(f"\n  Composite 10-day rolling FTD:")
    print(f"    Mean:       {mean_c:>15,.0f}")
    print(f"    Std:        {std_c:>15,.0f}")
    print(f"    2σ thresh:  {thresh_2s:>15,.0f}")
    print(f"    3σ thresh:  {thresh_3s:>15,.0f}")
    
    # Compare composite vs GME-only spike detection
    comp_spikes = composite['composite_10d'] > thresh_2s
    
    mean_g = composite['gme_only_10d'].mean()
    std_g = composite['gme_only_10d'].std()
    gme_spikes = composite['gme_only_10d'] > (mean_g + 2 * std_g)
    
    print(f"\n  Spike detection comparison:")
    print(f"    Composite spikes (>2σ):  {comp_spikes.sum()}")
    print(f"    GME-only spikes (>2σ):   {gme_spikes.sum()}")
    
    # Dates where composite catches spikes that GME-only misses
    comp_only = comp_spikes & ~gme_spikes
    print(f"    Composite-ONLY spikes:   {comp_only.sum()} ← these are GMEU/IGME/GMEY contributions")
    
    if comp_only.sum() > 0:
        print(f"\n  Dates with composite-only spikes (GMEU/IGME/GMEY drove the signal):")
        print(f"  {'Date':<12} {'Composite':>12} {'GME Only':>12} {'GMEU':>10} {'GME Price':>10}")
        print("  " + "-" * 60)
        for date in composite[comp_only].index[:20]:
            row = composite.loc[date]
            gmeu_val = row.get('GMEU', 0)
            gme_p = f"${row['gme_close']:.2f}" if pd.notna(row.get('gme_close', np.nan)) else "N/A"
            print(f"  {date.strftime('%Y-%m-%d'):<12} {row['composite_10d']:>12,.0f} {row['gme_only_10d']:>12,.0f} {gmeu_val:>10,.0f} {gme_p:>10}")
    
    # OCTOBER 2025 CASE STUDY (beckettcat's specific claim)
    print(f"\n  {'='*60}")
    print(f"  OCTOBER 2025 CASE STUDY — beckettcat's GMEU spike claim")
    print(f"  {'='*60}")
    
    oct_start = pd.Timestamp("2025-09-15")
    oct_end = pd.Timestamp("2025-12-15")
    oct_window = composite[(composite.index >= oct_start) & (composite.index <= oct_end)]
    
    if len(oct_window) > 0:
        print(f"\n  {'Date':<12} {'Composite':>12} {'GME FTD':>10} {'GMEU FTD':>10} {'GME Price':>10}")
        print("  " + "-" * 60)
        
        # Show weekly summary
        oct_weekly = oct_window.resample('W')[['composite', 'GME', 'gme_close']].agg({
            'composite': 'sum',
            'GME': 'sum',
            'gme_close': 'last'
        })
        if 'GMEU' in oct_window.columns:
            oct_weekly['GMEU'] = oct_window.resample('W')['GMEU'].sum()
        else:
            oct_weekly['GMEU'] = 0
        
        for date, row in oct_weekly.iterrows():
            gme_p = f"${row['gme_close']:.2f}" if pd.notna(row['gme_close']) else "N/A"
            print(f"  {date.strftime('%Y-%m-%d'):<12} {row['composite']:>12,.0f} {row['GME']:>10,.0f} {row['GMEU']:>10,.0f} {gme_p:>10}")
        
        # Find the T+33 projection from October peak
        if 'GMEU' in oct_window.columns:
            gmeu_oct = oct_window['GMEU']
            if gmeu_oct.max() > 0:
                peak_date = gmeu_oct.idxmax()
                t33_date = peak_date + timedelta(days=33)
                print(f"\n  GMEU peak:   {peak_date.strftime('%Y-%m-%d')} ({gmeu_oct.max():,.0f} FTDs)")
                print(f"  T+33 target: {t33_date.strftime('%Y-%m-%d')}")
                
                # Check GME price action around T+33
                t33_window = composite[(composite.index >= t33_date - timedelta(days=5)) & 
                                       (composite.index <= t33_date + timedelta(days=5))]
                if len(t33_window) > 0 and 'gme_close' in t33_window.columns:
                    t33_prices = t33_window['gme_close'].dropna()
                    if len(t33_prices) > 0:
                        pre_price = composite.loc[composite.index <= peak_date, 'gme_close'].dropna()
                        if len(pre_price) > 0:
                            peak_price = pre_price.iloc[-1]
                            t33_price = t33_prices.iloc[-1]
                            ret = (t33_price - peak_price) / peak_price
                            print(f"  GME at peak: ${peak_price:.2f}")
                            print(f"  GME at T+33: ${t33_price:.2f} ({ret:+.1%})")
    else:
        print("  No data available for October 2025 window.")
    
    # Forward return analysis: composite spikes vs GME price
    results = {
        'data_availability': {
            name: {'records': int(len(df)), 'start': df['date'].min().strftime('%Y-%m-%d'), 'end': df['date'].max().strftime('%Y-%m-%d')}
            for name, df in [("GME", gme), ("GMEU", gmeu), ("IGME", igme), ("GMEY", gmey)]
            if df is not None
        },
        'composite_stats': {
            'mean_10d': float(mean_c),
            'std_10d': float(std_c),
            'threshold_2sigma': float(thresh_2s),
            'composite_spikes': int(comp_spikes.sum()),
            'gme_only_spikes': int(gme_spikes.sum()),
            'composite_only_spikes': int(comp_only.sum())
        }
    }
    
    if 'fwd_10d' in composite.columns:
        spike_ret = composite.loc[comp_spikes, 'fwd_10d'].dropna()
        non_spike_ret = composite.loc[~comp_spikes, 'fwd_10d'].dropna()
        if len(spike_ret) > 0 and len(non_spike_ret) > 0:
            results['forward_returns'] = {
                'composite_spike_10d_mean': float(spike_ret.mean()),
                'non_spike_10d_mean': float(non_spike_ret.mean()),
                'differential': float(spike_ret.mean() - non_spike_ret.mean())
            }
            print(f"\n  Forward 10d return after composite spike: {spike_ret.mean():.2%}")
            print(f"  Forward 10d return (non-spike):             {non_spike_ret.mean():.2%}")
            print(f"  Differential:                               {spike_ret.mean() - non_spike_ret.mean():.2%}")
    
    # ===== VISUALIZATION =====
    fig, axes = plt.subplots(3, 1, figsize=(16, 14), 
                              gridspec_kw={'height_ratios': [2, 1.5, 1.5]})
    fig.suptitle('Composite FTD Score (GME + 2×GMEU + 0.5×IGME/GMEY)', fontsize=16, fontweight='bold', y=0.98)
    
    # Panel 1: GME price
    if 'gme_close' in composite.columns:
        axes[0].plot(composite.index, composite['gme_close'], color='#1a1a2e', linewidth=1, label='GME Close')
        if comp_spikes.sum() > 0:
            axes[0].scatter(composite[comp_spikes].index, 
                          composite.loc[comp_spikes, 'gme_close'],
                          color='red', s=20, alpha=0.7, zorder=5, label=f'Composite spike dates (n={comp_spikes.sum()})')
        axes[0].set_ylabel('GME Price ($)', fontsize=11)
        axes[0].legend(loc='upper right')
        axes[0].set_title('GME Price with Composite FTD Spike Dates', fontsize=12)
        axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Composite vs GME-only
    axes[1].fill_between(composite.index, 0, composite['composite_10d'], alpha=0.4, color='red', label='Composite (GME+2×GMEU+0.5×others)')
    axes[1].fill_between(composite.index, 0, composite['gme_only_10d'], alpha=0.3, color='steelblue', label='GME-only')
    axes[1].axhline(y=thresh_2s, color='red', linestyle='--', linewidth=1, alpha=0.7, label=f'Composite 2σ ({thresh_2s:,.0f})')
    axes[1].set_ylabel('10-day Rolling FTD Sum', fontsize=11)
    axes[1].legend(loc='upper right')
    axes[1].set_title('Composite vs. GME-Only FTD Score', fontsize=12)
    axes[1].grid(True, alpha=0.3)
    
    # Panel 3: Individual ETF contributions
    colors = {'GME': 'steelblue', 'GMEU': 'red', 'IGME': 'orange', 'GMEY': 'purple'}
    for name in ['GMEU', 'IGME', 'GMEY']:
        if name in composite.columns:
            rolling = composite[name].rolling(10, min_periods=1).sum()
            axes[2].fill_between(composite.index, 0, rolling, alpha=0.3, color=colors.get(name, 'gray'), label=f'{name} (10d sum)')
    
    axes[2].set_ylabel('FTDs (10-day sum)', fontsize=11)
    axes[2].set_xlabel('Date', fontsize=11)
    axes[2].legend(loc='upper right')
    axes[2].set_title('Single-Stock ETF FTD Contributions', fontsize=12)
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = FIG_DIR / "composite_ftd_score.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    # Save results
    out_path = RESULTS_DIR / "composite_ftd_score.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 2 complete.")

if __name__ == "__main__":
    main()
