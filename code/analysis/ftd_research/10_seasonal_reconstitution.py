#!/usr/bin/env python3
"""
Test 9: Year-End Reconstitution Deep Dive + Seasonal Decomposition
The strongest reconstitution effects were Dec (16x, 4.9x, 3.7x).
Is year-end systematically different from mid-year? And what drives it?
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
    print("TEST 9: Seasonal Decomposition + Year-End Deep Dive")
    print("=" * 70)
    
    xrt = load_csv("XRT")
    gme_ftd = load_csv("GME")
    ijh = load_csv("IJH")
    iwm = load_csv("IWM")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()
    
    # ============================================================
    # PART A: Monthly Seasonality of XRT FTDs
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: Monthly Seasonality of XRT FTDs")
    print(f"{'='*60}")
    
    xrt_monthly = xrt.copy()
    xrt_monthly['month'] = xrt_monthly.index.month
    xrt_monthly['year'] = xrt_monthly.index.year
    
    # Average FTDs by month
    monthly_avg = xrt_monthly.groupby('month')['quantity'].agg(['mean', 'median', 'count'])
    
    print(f"\n  {'Month':<8} {'Mean FTD':>12} {'Median FTD':>12} {'Days':>6}")
    print("  " + "-" * 42)
    for month in range(1, 13):
        if month in monthly_avg.index:
            row = monthly_avg.loc[month]
            month_name = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][month-1]
            print(f"  {month_name:<8} {row['mean']:>12,.0f} {row['median']:>12,.0f} {int(row['count']):>6}")
    
    # Test: December vs all other months
    dec_ftd = xrt_monthly[xrt_monthly['month'] == 12]['quantity']
    non_dec_ftd = xrt_monthly[xrt_monthly['month'] != 12]['quantity']
    
    u_stat, u_p = stats.mannwhitneyu(dec_ftd, non_dec_ftd, alternative='greater')
    print(f"\n  December vs Other Months:")
    print(f"    Dec mean:     {dec_ftd.mean():>12,.0f}")
    print(f"    Non-Dec mean: {non_dec_ftd.mean():>12,.0f}")
    print(f"    Ratio:        {dec_ftd.mean() / non_dec_ftd.mean():>12.2f}×")
    print(f"    Mann-Whitney p: {u_p:.4f}")
    
    # Quarter analysis (Q1 = recon aftermath, Q2-Q3 = mid-year, Q4 = year-end)
    xrt_monthly['quarter'] = xrt_monthly.index.quarter
    quarter_avg = xrt_monthly.groupby('quarter')['quantity'].mean()
    
    print(f"\n  Quarterly XRT FTD Averages:")
    for q in range(1, 5):
        if q in quarter_avg.index:
            print(f"    Q{q}: {quarter_avg.loc[q]:>12,.0f}")
    
    # ============================================================
    # PART B: Year-End vs Mid-Year Reconstitution
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Year-End vs Mid-Year Quad Witching Comparison")
    print(f"{'='*60}")
    
    # Build QW events with context
    qw_events = []
    for year in range(2021, 2026):
        for month in [3, 6, 9, 12]:
            first_day = datetime(year, month, 1)
            days_until_friday = (4 - first_day.weekday()) % 7
            first_friday = first_day + timedelta(days=days_until_friday)
            third_friday = pd.Timestamp(first_friday + timedelta(weeks=2))
            
            # Get XRT FTDs in ±5d window
            pre = xrt[(xrt.index >= third_friday - timedelta(days=10)) & 
                      (xrt.index < third_friday - timedelta(days=5))]
            event = xrt[(xrt.index >= third_friday - timedelta(days=5)) & 
                       (xrt.index <= third_friday + timedelta(days=5))]
            post = xrt[(xrt.index > third_friday + timedelta(days=5)) & 
                      (xrt.index <= third_friday + timedelta(days=10))]
            
            if len(event) == 0:
                continue
            
            # GME price and returns
            gme_nearby = price_df[(price_df.index >= third_friday - timedelta(days=3)) &
                                  (price_df.index <= third_friday + timedelta(days=3))]
            gme_price = gme_nearby['gme_close'].iloc[0] if len(gme_nearby) > 0 else np.nan
            
            fwd = price_df[price_df.index > third_friday].head(20)
            ret_5d = float(fwd.iloc[4]['gme_close'] / gme_price - 1) if len(fwd) >= 5 and pd.notna(gme_price) else None
            ret_10d = float(fwd.iloc[9]['gme_close'] / gme_price - 1) if len(fwd) >= 10 and pd.notna(gme_price) else None
            ret_20d = float(fwd.iloc[19]['gme_close'] / gme_price - 1) if len(fwd) >= 20 and pd.notna(gme_price) else None
            
            season = 'Year-End (Dec)' if month == 12 else 'Mid-Year'
            
            qw_events.append({
                'date': third_friday,
                'month': month,
                'year': year,
                'season': season,
                'pre_ftd': pre['quantity'].mean() if len(pre) > 0 else 0,
                'event_ftd': event['quantity'].mean(),
                'post_ftd': post['quantity'].mean() if len(post) > 0 else 0,
                'ratio': event['quantity'].mean() / max(1, pre['quantity'].mean()) if len(pre) > 0 else 0,
                'gme_price': gme_price,
                'ret_5d': ret_5d,
                'ret_10d': ret_10d,
                'ret_20d': ret_20d,
            })
    
    print(f"\n  {'Season':<18} {'Events':>7} {'Mean Ratio':>11} {'Mean 10d Ret':>13} {'Mean 20d Ret':>13}")
    print("  " + "-" * 65)
    
    for season in ['Year-End (Dec)', 'Mid-Year']:
        events = [e for e in qw_events if e['season'] == season]
        ratios = [e['ratio'] for e in events if e['ratio'] > 0]
        r10 = [e['ret_10d'] for e in events if e['ret_10d'] is not None]
        r20 = [e['ret_20d'] for e in events if e['ret_20d'] is not None]
        if ratios:
            print(f"  {season:<18} {len(events):>7} {np.mean(ratios):>10.2f}× {np.mean(r10):>12.2%} {np.mean(r20):>13.2%}")
    
    # Year-by-year Dec comparison
    print(f"\n  Year-End (Dec) Detail:")
    print(f"  {'Year':<6} {'Ratio':>8} {'Event FTD':>12} {'GME':>8} {'5d Ret':>8} {'10d Ret':>9} {'20d Ret':>9}")
    print("  " + "-" * 65)
    for e in sorted([ev for ev in qw_events if ev['month'] == 12], key=lambda x: x['year']):
        r5 = f"{e['ret_5d']:.1%}" if e['ret_5d'] is not None else "N/A"
        r10 = f"{e['ret_10d']:.1%}" if e['ret_10d'] is not None else "N/A"  
        r20 = f"{e['ret_20d']:.1%}" if e['ret_20d'] is not None else "N/A"
        gme = f"${e['gme_price']:.2f}" if pd.notna(e['gme_price']) else "N/A"
        print(f"  {e['year']:<6} {e['ratio']:>7.1f}× {e['event_ftd']:>12,.0f} {gme:>8} {r5:>8} {r10:>9} {r20:>9}")
    
    # ============================================================
    # PART C: Multi-ETF Reconstitution (XRT + IJH + IWM)
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: Multi-ETF Reconstitution Pressure")
    print(f"{'='*60}")
    
    all_dates = pd.date_range('2021-01-01', '2026-01-31', freq='B')
    etf_daily = pd.DataFrame(index=all_dates)
    for name, data in [('XRT', xrt), ('IJH', ijh), ('IWM', iwm)]:
        etf_daily[name] = data['quantity'].reindex(all_dates).fillna(0)
    etf_daily['gme_close'] = price_df['gme_close'].reindex(all_dates).ffill()
    
    # Normalized FTDs (z-scores) so we can combine
    for col in ['XRT', 'IJH', 'IWM']:
        etf_daily[f'{col}_z'] = (etf_daily[col] - etf_daily[col].mean()) / etf_daily[col].std()
    
    etf_daily['combined_z'] = etf_daily['XRT_z'] + etf_daily['IJH_z'] + etf_daily['IWM_z']
    etf_daily['combined_z_10d'] = etf_daily['combined_z'].rolling(10, min_periods=1).mean()
    
    # Forward returns
    etf_daily['fwd_10d'] = etf_daily['gme_close'].pct_change(10).shift(-10)
    
    # Combined z-score quintile analysis
    clean = etf_daily.dropna(subset=['combined_z_10d', 'fwd_10d'])
    clean['z_quintile'] = pd.qcut(clean['combined_z_10d'], 5, labels=['Q1 (low)', 'Q2', 'Q3', 'Q4', 'Q5 (high)'])
    
    print(f"\n  Combined ETF FTD Z-Score Quintile → GME Forward Returns:")
    print(f"  {'Quintile':<12} {'Mean Z':>8} {'Mean 10d Ret':>13} {'% Pos':>8} {'N':>6}")
    print("  " + "-" * 50)
    
    for q in ['Q1 (low)', 'Q2', 'Q3', 'Q4', 'Q5 (high)']:
        qd = clean[clean['z_quintile'] == q]
        if len(qd) > 0:
            pct = (qd['fwd_10d'] > 0).mean()
            print(f"  {q:<12} {qd['combined_z_10d'].mean():>8.2f} {qd['fwd_10d'].mean():>12.2%} {pct:>8.1%} {len(qd):>6}")
    
    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Seasonal & Multi-ETF Reconstitution Analysis', fontsize=14, fontweight='bold', y=0.98)
    
    # Panel 1: Monthly seasonality
    ax = axes[0, 0]
    months = list(range(1, 13))
    month_labels = ['J','F','M','A','M','J','J','A','S','O','N','D']
    month_means = [monthly_avg.loc[m, 'mean'] if m in monthly_avg.index else 0 for m in months]
    colors_m = ['red' if m in [3,6,9,12] else 'steelblue' for m in months]
    ax.bar(months, month_means, color=colors_m, alpha=0.7, edgecolor='black')
    ax.set_xticks(months)
    ax.set_xticklabels(month_labels)
    ax.set_ylabel('Mean XRT FTD')
    ax.set_title('XRT FTD Monthly Seasonality (red = QW months)', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 2: Year-end vs mid-year reconstitution ratios
    ax = axes[0, 1]
    dec_events = [e for e in qw_events if e['month'] == 12 and e['ratio'] > 0]
    other_events = [e for e in qw_events if e['month'] != 12 and e['ratio'] > 0]
    ax.boxplot([[e['ratio'] for e in dec_events], [e['ratio'] for e in other_events]],
               labels=['December', 'Mar/Jun/Sep'])
    ax.set_ylabel('FTD Elevation Ratio (Event / Pre)')
    ax.set_title('Year-End vs Mid-Year Reconstitution', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Combined ETF z-score vs GME price
    ax = axes[1, 0]
    ax2 = ax.twinx()
    ax.fill_between(etf_daily.index, 0, etf_daily['combined_z_10d'], alpha=0.3, color='steelblue')
    ax2.plot(etf_daily.index, etf_daily['gme_close'], color='#1a1a2e', linewidth=0.8)
    ax.set_ylabel('Combined ETF FTD Z-Score (10d)', color='steelblue')
    ax2.set_ylabel('GME Price ($)')
    ax.set_title('Combined ETF Pressure vs GME Price', fontsize=10)
    
    # Panel 4: Dec QW events over time
    ax = axes[1, 1]
    dec_years = [e['year'] for e in dec_events]
    dec_ratios = [e['ratio'] for e in dec_events]
    ax.bar(dec_years, dec_ratios, color='red', alpha=0.7, edgecolor='black')
    ax.set_xlabel('Year')
    ax.set_ylabel('XRT FTD Elevation Ratio')
    ax.set_title('December Reconstitution Intensity Over Time', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    for y, r in zip(dec_years, dec_ratios):
        ax.text(y, r + 0.2, f'{r:.1f}×', ha='center', fontsize=9)
    
    plt.tight_layout()
    fig_path = FIG_DIR / "seasonal_reconstitution.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    results = {
        'monthly_seasonality': {int(m): float(monthly_avg.loc[m, 'mean']) for m in monthly_avg.index},
        'dec_vs_other': {
            'dec_mean': float(dec_ftd.mean()),
            'non_dec_mean': float(non_dec_ftd.mean()),
            'ratio': float(dec_ftd.mean() / non_dec_ftd.mean()),
            'p_value': float(u_p)
        },
        'qw_events': [{k: str(v) if isinstance(v, pd.Timestamp) else v for k, v in e.items()} for e in qw_events],
    }
    
    out_path = RESULTS_DIR / "seasonal_reconstitution.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 9 complete.")

if __name__ == "__main__":
    main()
