#!/usr/bin/env python3
"""
Test 12: Options OI × FTD Correlation (ThetaData)
Uses 424 GME options OI snapshots from ThetaData (2020-04 to 2024-06).
  A) Total OI changes vs FTD spikes — do they co-move?
  B) Put/Call OI ratio around T+33 echo windows
  C) Max pain vs GME price around reconstitution
  D) OI concentration — do FTD spikes align with heavy OI strikes?
  E) Near-expiry OI surge — gamma ramp detection
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

def load_all_oi():
    """Load all 424 ThetaData OI snapshots and aggregate daily metrics."""
    cache_path = DATA_DIR / "gme_options_oi_daily.csv"
    if cache_path.exists():
        print("  Loading cached OI data...")
        return pd.read_csv(cache_path, parse_dates=['date']).set_index('date')
    
    print(f"  Loading {len(list(THETA_OI_DIR.glob('*.parquet')))} ThetaData OI files...")
    
    daily_records = []
    for f in sorted(THETA_OI_DIR.glob("oi_*.parquet")):
        date_str = f.stem.split('_')[1]
        snap_date = pd.Timestamp(datetime.strptime(date_str, '%Y%m%d'))
        
        df = pd.read_parquet(f)
        if len(df) == 0:
            continue
        
        # Total OI
        total_oi = df['open_interest'].sum()
        call_oi = df[df['right'] == 'CALL']['open_interest'].sum()
        put_oi = df[df['right'] == 'PUT']['open_interest'].sum()
        
        # OI-weighted strike (proxy for "center of mass")
        df_nonzero = df[df['open_interest'] > 0]
        if len(df_nonzero) > 0:
            oi_weighted_strike = (df_nonzero['strike'] * df_nonzero['open_interest']).sum() / df_nonzero['open_interest'].sum()
        else:
            oi_weighted_strike = np.nan
        
        # Max pain calculation (simplified: strike with max call+put OI)
        strike_oi = df.groupby('strike')['open_interest'].sum()
        max_pain_strike = strike_oi.idxmax() if len(strike_oi) > 0 else np.nan
        max_pain_oi = strike_oi.max() if len(strike_oi) > 0 else 0
        
        # Near-term OI (expiring within 30 days)
        near_mask = df['expiration'] <= snap_date + timedelta(days=30)
        near_oi = df[near_mask]['open_interest'].sum()
        near_call = df[near_mask & (df['right'] == 'CALL')]['open_interest'].sum()
        near_put = df[near_mask & (df['right'] == 'PUT')]['open_interest'].sum()
        
        # Far OI (>90 days out)
        far_mask = df['expiration'] > snap_date + timedelta(days=90)
        far_oi = df[far_mask]['open_interest'].sum()
        
        # Count of unique strikes and expirations
        n_strikes = df['strike'].nunique()
        n_exps = df['expiration'].nunique()
        
        daily_records.append({
            'date': snap_date,
            'total_oi': total_oi,
            'call_oi': call_oi,
            'put_oi': put_oi,
            'pc_ratio': put_oi / max(1, call_oi),
            'oi_weighted_strike': oi_weighted_strike,
            'max_pain_strike': max_pain_strike,
            'max_pain_oi': max_pain_oi,
            'near_oi': near_oi,
            'near_call': near_call,
            'near_put': near_put,
            'near_pc_ratio': near_put / max(1, near_call),
            'far_oi': far_oi,
            'near_far_ratio': near_oi / max(1, far_oi),
            'n_strikes': n_strikes,
            'n_exps': n_exps,
        })
    
    oi_df = pd.DataFrame(daily_records).set_index('date').sort_index()
    oi_df.to_csv(cache_path)
    print(f"  Loaded {len(oi_df)} daily OI snapshots ({oi_df.index.min().date()} to {oi_df.index.max().date()})")
    return oi_df

def main():
    print("=" * 70)
    print("TEST 12: Options OI × FTD Correlation (ThetaData)")
    print("=" * 70)
    
    gme_ftd = load_csv("GME")
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
    price_df = price_df.set_index('date').sort_index()
    
    mean_ftd = gme_ftd['quantity'].mean()
    std_ftd = gme_ftd['quantity'].std()
    threshold_2s = mean_ftd + 2 * std_ftd
    spikes = gme_ftd[gme_ftd['quantity'] > threshold_2s]
    
    oi_data = load_all_oi()
    
    # Build aligned daily dataset
    common_dates = oi_data.index.intersection(gme_ftd.index)
    print(f"\n  Aligned dates: {len(common_dates)} (OI ∩ FTD)")
    
    daily = pd.DataFrame(index=common_dates)
    daily['gme_ftd'] = gme_ftd['quantity'].reindex(common_dates)
    daily['gme_close'] = price_df['gme_close'].reindex(common_dates).ffill()
    for col in oi_data.columns:
        daily[col] = oi_data[col].reindex(common_dates)
    
    # Forward returns
    daily['fwd_5d'] = daily['gme_close'].pct_change(5).shift(-5)
    daily['fwd_10d'] = daily['gme_close'].pct_change(10).shift(-10)
    
    # OI changes
    daily['oi_change'] = daily['total_oi'].pct_change()
    daily['oi_change_5d'] = daily['total_oi'].pct_change(5)
    daily['ftd_z'] = (daily['gme_ftd'] - daily['gme_ftd'].mean()) / daily['gme_ftd'].std()
    daily['pc_ratio_change'] = daily['pc_ratio'].pct_change()
    
    # ============================================================
    # PART A: OI × FTD Correlation
    # ============================================================
    print(f"\n{'='*60}")
    print("PART A: Options OI × FTD Correlation")
    print(f"{'='*60}")
    
    clean = daily.dropna(subset=['total_oi', 'gme_ftd'])
    
    corr_total = clean['total_oi'].corr(clean['gme_ftd'])
    corr_call = clean['call_oi'].corr(clean['gme_ftd'])
    corr_put = clean['put_oi'].corr(clean['gme_ftd'])
    corr_pc = clean['pc_ratio'].corr(clean['gme_ftd'])
    corr_near = clean['near_oi'].corr(clean['gme_ftd'])
    
    print(f"\n  Correlation with GME FTDs:")
    print(f"    Total OI:     r = {corr_total:.3f}")
    print(f"    Call OI:      r = {corr_call:.3f}")
    print(f"    Put OI:       r = {corr_put:.3f}")
    print(f"    P/C Ratio:    r = {corr_pc:.3f}")
    print(f"    Near-term OI: r = {corr_near:.3f}")
    
    # Lead-lag: does OI change lead FTDs or follow?
    print(f"\n  Lead-Lag Analysis (OI change → FTD):")
    lag_corrs = {}
    for lag in range(-10, 11):
        if abs(lag) < len(clean) - 1:
            if lag < 0:
                c = clean['oi_change'].iloc[:lag].reset_index(drop=True).corr(
                    clean['gme_ftd'].iloc[-lag:].reset_index(drop=True))
            elif lag > 0:
                c = clean['oi_change'].iloc[lag:].reset_index(drop=True).corr(
                    clean['gme_ftd'].iloc[:-lag].reset_index(drop=True))
            else:
                c = clean['oi_change'].corr(clean['gme_ftd'])
            if pd.notna(c):
                lag_corrs[lag] = float(c)
    
    if lag_corrs:
        best_lag = max(lag_corrs, key=lag_corrs.get)
        print(f"    Best lag:  {best_lag:+d} days, r = {lag_corrs[best_lag]:.3f}")
        print(f"    Same-day:  r = {lag_corrs.get(0, 0):.3f}")
    
    # ============================================================
    # PART B: P/C Ratio Around T+33 Echo Windows
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Put/Call OI Ratio Around T+33 Echo Windows")
    print(f"{'='*60}")
    
    # Mark echo windows
    echo_dates = set()
    for spike_date in spikes.index:
        ed = add_business_days(spike_date, 33)
        for offset in range(-3, 4):
            echo_dates.add(ed + timedelta(days=offset))
    
    daily['in_echo'] = daily.index.isin(echo_dates).astype(int)
    
    echo_pc = daily[daily['in_echo'] == 1]['pc_ratio'].dropna()
    non_echo_pc = daily[daily['in_echo'] == 0]['pc_ratio'].dropna()
    
    if len(echo_pc) > 0 and len(non_echo_pc) > 0:
        print(f"\n  P/C Ratio in Echo vs Non-Echo Windows:")
        print(f"    Echo:      mean = {echo_pc.mean():.3f}, median = {echo_pc.median():.3f} (n={len(echo_pc)})")
        print(f"    Non-echo:  mean = {non_echo_pc.mean():.3f}, median = {non_echo_pc.median():.3f} (n={len(non_echo_pc)})")
        
        u_stat, u_p = stats.mannwhitneyu(echo_pc, non_echo_pc, alternative='two-sided')
        print(f"    Mann-Whitney p = {u_p:.4f}")
        if echo_pc.mean() > non_echo_pc.mean():
            print(f"    ⚠️ P/C ratio is HIGHER during echo windows (more protective puts)")
        else:
            print(f"    P/C ratio is lower during echo windows")
    
    # Near-term P/C ratio (more sensitive to expiry pressure)
    echo_near_pc = daily[daily['in_echo'] == 1]['near_pc_ratio'].dropna()
    non_echo_near_pc = daily[daily['in_echo'] == 0]['near_pc_ratio'].dropna()
    
    if len(echo_near_pc) > 0:
        print(f"\n  Near-Term P/C (<30d expiry):")
        print(f"    Echo:      {echo_near_pc.mean():.3f}")
        print(f"    Non-echo:  {non_echo_near_pc.mean():.3f}")
    
    # ============================================================
    # PART C: Max Pain vs GME Price — Pinning Analysis
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: Max Pain vs GME Price — Magnetic Pinning")
    print(f"{'='*60}")
    
    pin_data = daily.dropna(subset=['max_pain_strike', 'gme_close'])
    if len(pin_data) > 0:
        pin_data = pin_data.copy()
        pin_data['distance_from_mp'] = (pin_data['gme_close'] - pin_data['max_pain_strike']) / pin_data['max_pain_strike']
        pin_data['abs_dist'] = pin_data['distance_from_mp'].abs()
        
        print(f"\n  Max Pain Pinning Analysis (n={len(pin_data)}):")
        print(f"    Mean distance from max pain: {pin_data['distance_from_mp'].mean():+.1%}")
        print(f"    Median abs distance:         {pin_data['abs_dist'].median():.1%}")
        print(f"    Within 5% of MP:             {(pin_data['abs_dist'] < 0.05).mean():.1%} of days")
        print(f"    Within 10% of MP:            {(pin_data['abs_dist'] < 0.10).mean():.1%} of days")
        print(f"    Within 20% of MP:            {(pin_data['abs_dist'] < 0.20).mean():.1%} of days")
        
        # Does FTD spike pull price toward or away from max pain?
        ftd_spike_mask = pin_data['gme_ftd'] > threshold_2s
        spike_dist = pin_data.loc[ftd_spike_mask, 'abs_dist']
        normal_dist = pin_data.loc[~ftd_spike_mask, 'abs_dist']
        
        print(f"\n  Distance from Max Pain during FTD spikes:")
        print(f"    FTD spike days:  {spike_dist.mean():.1%} (n={len(spike_dist)})")
        print(f"    Normal days:     {normal_dist.mean():.1%} (n={len(normal_dist)})")
        if len(spike_dist) > 5:
            u, p = stats.mannwhitneyu(spike_dist, normal_dist, alternative='greater')
            print(f"    Mann-Whitney p:  {p:.4f} (testing: spike → further from MP)")
    
    # ============================================================
    # PART D: OI Concentration × FTD Signal
    # ============================================================
    print(f"\n{'='*60}")
    print("PART D: OI Regime Analysis — High vs Low OI Periods")
    print(f"{'='*60}")
    
    clean2 = daily.dropna(subset=['total_oi', 'gme_ftd', 'fwd_10d'])
    if len(clean2) > 20:
        clean2 = clean2.copy()
        clean2['oi_quintile'] = pd.qcut(clean2['total_oi'], 5, labels=['Q1 (low)', 'Q2', 'Q3', 'Q4', 'Q5 (high)'])
        
        print(f"\n  OI Quintile → FTD Level & Forward Returns:")
        print(f"  {'Quintile':<12} {'Mean OI':>12} {'Mean FTD':>12} {'Mean 10d':>10} {'% Pos':>8}")
        print("  " + "-" * 58)
        
        results_d = {}
        for q in ['Q1 (low)', 'Q2', 'Q3', 'Q4', 'Q5 (high)']:
            qd = clean2[clean2['oi_quintile'] == q]
            if len(qd) > 0:
                pct = (qd['fwd_10d'] > 0).mean()
                print(f"  {q:<12} {qd['total_oi'].mean():>12,.0f} {qd['gme_ftd'].mean():>12,.0f} {qd['fwd_10d'].mean():>9.2%} {pct:>8.1%}")
                results_d[q] = {'oi': float(qd['total_oi'].mean()), 'ftd': float(qd['gme_ftd'].mean()), 'ret': float(qd['fwd_10d'].mean())}
    
    # ============================================================
    # PART E: Near/Far OI Ratio as Gamma Signal
    # ============================================================
    print(f"\n{'='*60}")
    print("PART E: Near/Far OI Ratio — Gamma Exposure Proxy")
    print(f"{'='*60}")
    
    clean3 = daily.dropna(subset=['near_far_ratio', 'fwd_10d'])
    if len(clean3) > 20:
        clean3 = clean3.copy()
        clean3['nf_quintile'] = pd.qcut(clean3['near_far_ratio'], 5, labels=['Q1 (far-heavy)', 'Q2', 'Q3', 'Q4', 'Q5 (near-heavy)'])
        
        print(f"\n  Near/Far OI Ratio → Forward Returns:")
        print(f"  {'Quintile':<18} {'Mean N/F':>8} {'Mean FTD':>12} {'Mean 10d':>10} {'% Pos':>8}")
        print("  " + "-" * 60)
        
        for q in ['Q1 (far-heavy)', 'Q2', 'Q3', 'Q4', 'Q5 (near-heavy)']:
            qd = clean3[clean3['nf_quintile'] == q]
            if len(qd) > 0:
                pct = (qd['fwd_10d'] > 0).mean()
                print(f"  {q:<18} {qd['near_far_ratio'].mean():>8.2f} {qd['gme_ftd'].mean():>12,.0f} {qd['fwd_10d'].mean():>9.2%} {pct:>8.1%}")
    
    # ============================================================
    # VISUALIZATION
    # ============================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle('Options OI × FTD Analysis (ThetaData, 424 snapshots)', fontsize=14, fontweight='bold', y=0.98)
    
    # Panel 1: Total OI and FTD co-movement
    ax = axes[0, 0]
    ax2 = ax.twinx()
    ax.plot(daily.index, daily['total_oi'] / 1e6, color='steelblue', linewidth=1, label='Total OI (M)')
    ax2.plot(daily.index, daily['gme_ftd'], color='red', linewidth=0.5, alpha=0.7, label='FTD')
    ax.set_ylabel('Options OI (millions)', color='steelblue')
    ax2.set_ylabel('GME FTD', color='red')
    ax.set_title(f'OI vs FTD (r={corr_total:.3f})', fontsize=10)
    ax.legend(loc='upper left', fontsize=8)
    ax2.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Panel 2: P/C ratio over time with echo windows
    ax = axes[0, 1]
    ax.plot(daily.index, daily['pc_ratio'], color='steelblue', linewidth=0.8)
    echo_mask = daily['in_echo'] == 1
    if echo_mask.any():
        ax.scatter(daily.index[echo_mask], daily['pc_ratio'][echo_mask], color='red', s=15, zorder=5, label='T+33 echo')
    ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=0.5)
    ax.set_ylabel('Put/Call OI Ratio')
    ax.set_title('P/C Ratio (red = echo windows)', fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Panel 3: Max pain vs price
    ax = axes[1, 0]
    if len(pin_data) > 0:
        ax.scatter(pin_data['max_pain_strike'], pin_data['gme_close'], alpha=0.3, s=10, c='steelblue')
        lims = [min(pin_data['max_pain_strike'].min(), pin_data['gme_close'].min()),
                max(pin_data['max_pain_strike'].max(), pin_data['gme_close'].max())]
        ax.plot(lims, lims, 'r--', linewidth=0.5, label='Perfect pin')
        ax.set_xlabel('Max Pain Strike ($)')
        ax.set_ylabel('GME Close ($)')
        ax.set_title('Max Pain Magnetic Pinning', fontsize=10)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    # Panel 4: OI change lead-lag
    ax = axes[1, 1]
    if lag_corrs:
        lags_list = sorted(lag_corrs.keys())
        corrs_list = [lag_corrs[l] for l in lags_list]
        ax.bar(lags_list, corrs_list, color='steelblue', alpha=0.7, edgecolor='black')
        ax.set_xlabel('Lag (days, negative = OI change leads FTDs)')
        ax.set_ylabel('Correlation')
        ax.set_title('OI Change → FTD Lead-Lag', fontsize=10)
        ax.axhline(y=0, color='gray', linewidth=0.5)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = FIG_DIR / "options_oi_ftd.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    results = {
        'correlations': {
            'total_oi': float(corr_total), 'call_oi': float(corr_call),
            'put_oi': float(corr_put), 'pc_ratio': float(corr_pc), 'near_oi': float(corr_near),
        },
        'echo_pc_ratio': {
            'echo_mean': float(echo_pc.mean()) if len(echo_pc) > 0 else None,
            'non_echo_mean': float(non_echo_pc.mean()) if len(non_echo_pc) > 0 else None,
        },
        'oi_snapshots': int(len(oi_data)),
        'aligned_days': int(len(common_dates)),
    }
    
    out_path = RESULTS_DIR / "options_oi_ftd.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 12 complete.")

if __name__ == "__main__":
    main()
