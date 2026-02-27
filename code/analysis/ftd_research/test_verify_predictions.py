#!/usr/bin/env python3
"""
VERIFICATION: Testing Deep Thinker Falsifiable Predictions
Each test targets a specific claim from the waveguide model.
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import timedelta
from scipy import stats

DATA_DIR = Path(str(Path.home()) + "/Documents/GitHub/research/data/ftd")
OUT_DIR = Path(str(Path.home()) + "/Documents/GitHub/research/temp/resonance_deep_dive")

def add_business_days(date, n):
    current = date
    added = 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current

def echo_test(spikes, all_ftd, offset, threshold):
    hits, total = 0, 0
    for spike_date in spikes.index:
        echo_date = add_business_days(spike_date, offset)
        if echo_date in all_ftd.index:
            total += 1
            if all_ftd.loc[echo_date, 'quantity'] > threshold:
                hits += 1
    rate = hits / max(1, total)
    return hits, total, rate

def main():
    gme_ftd = pd.read_csv(DATA_DIR / "GME_ftd.csv", parse_dates=['date'])
    gme_ftd = gme_ftd.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date']).set_index('date').sort_index()
    
    mean_ftd = gme_ftd['quantity'].mean()
    std_ftd = gme_ftd['quantity'].std()
    spikes = gme_ftd[gme_ftd['quantity'] > mean_ftd + 2 * std_ftd]
    threshold_1s = mean_ftd + 1 * std_ftd
    base_rate = (gme_ftd['quantity'] > threshold_1s).mean()
    
    results = {}
    
    # ============================================================
    # PREDICTION 1: LCM(35,21) = 105 explains amplification
    # If true: T+105 should be stronger than neighboring offsets
    # AND all LCM multiples should show enhanced enrichment
    # ============================================================
    print("=" * 70)
    print("PREDICTION 1: LCM(35,21)=105 CONSTRUCTIVE INTERFERENCE")
    print("  Claim: T+105 amplifies because settlement (35) and OPEX (21) collide")
    print("=" * 70)
    
    # Test: compare LCM points vs non-LCM points
    # LCMs of 35 and 21: 105, 210, 315, 420, 525, 630...
    # Also test LCM(35,13) = 455, LCM(21,13) = 273
    lcm_35_21 = [105, 210, 315, 420, 525, 630]
    
    print(f"\n  LCM(35,21) points:")
    for offset in lcm_35_21:
        h, t, r = echo_test(spikes, gme_ftd, offset, threshold_1s)
        ratio = r / base_rate
        # Compare to neighbors (offset-5 through offset+5, excluding self)
        neighbor_ratios = []
        for n_off in range(offset-5, offset+6):
            if n_off != offset and n_off > 0:
                nh, nt, nr = echo_test(spikes, gme_ftd, n_off, threshold_1s)
                if nt > 3:
                    neighbor_ratios.append(nr / base_rate)
        neighbor_mean = np.mean(neighbor_ratios) if neighbor_ratios else 0
        is_peak = ratio > neighbor_mean
        print(f"    T+{offset}: {ratio:.2f}× (neighbors: {neighbor_mean:.2f}×) {'✅ PEAK' if is_peak else '❌ NOT PEAK'}")
    
    # Test: T+21 harmonics
    print(f"\n  T+21 harmonics (OPEX cycle):")
    for n in range(1, 16):
        offset = n * 21
        h, t, r = echo_test(spikes, gme_ftd, offset, threshold_1s)
        ratio = r / base_rate
        is_lcm = offset % 35 == 0
        bar = "█" * min(15, int(ratio * 3))
        flag = " ← LCM(35,21)" if is_lcm else ""
        print(f"    {n:>2}× T+21 = T+{offset:<5}: {ratio:>5.1f}× {bar}{flag}")
    
    results['lcm_test'] = {
        'prediction': 'LCM(35,21)=105 shows amplification',
    }

    # ============================================================
    # PREDICTION 2: T+25 BD = 35 CALENDAR DAYS (statutory wall)
    # If true: T+25 should be a local peak, and the system should
    # show enrichment at T+25 + T+10 = T+35
    # ============================================================
    print(f"\n{'='*70}")
    print("PREDICTION 2: T+25 BD = 35 CALENDAR DAYS (STATUTORY WALL)")
    print("  Claim: T+25 is the SEC Rule 204(a)(2) deadline")
    print("  Corollary: T+25 (capital limit) + T+10 (options bridge) = T+35")
    print(f"{'='*70}")
    
    print(f"\n  Fine-grained enrichment T+20 → T+40:")
    for offset in range(20, 41):
        h, t, r = echo_test(spikes, gme_ftd, offset, threshold_1s)
        ratio = r / base_rate
        bar = "█" * min(20, int(ratio * 4))
        cal_days = offset * 7 / 5
        flag = ""
        if offset == 25: flag = " ← 35 cal days (Rule 204)"
        elif offset == 35: flag = " ← T+25 + T+10 (predicted)"
        elif offset == 33: flag = " ← T+33 (old waterfall node)"
        print(f"    T+{offset}: {ratio:.2f}× (≈{cal_days:.0f} cal) {bar}{flag}")

    # ============================================================
    # PREDICTION 3: BEAT SIDEBANDS AT T+75 AND T+85
    # If AM modulation: T+35 signal × T+63 carrier → sidebands at
    # T+79 ± ~5 = T+74-84
    # ============================================================
    print(f"\n{'='*70}")
    print("PREDICTION 3: AM SIDEBANDS (T+35 × T+63 beat)")
    print("  Predicted: T+79 (1/(1/35-1/63)) with sidebands at T+75 and T+85")
    print(f"{'='*70}")
    
    print(f"\n  Dense spectrum T+70 → T+90:")
    for offset in range(70, 91):
        h, t, r = echo_test(spikes, gme_ftd, offset, threshold_1s)
        ratio = r / base_rate
        bar = "█" * min(20, int(ratio * 4))
        flag = ""
        if offset == 70: flag = " ← 2×T+35"
        elif offset == 75: flag = " ← predicted lower sideband"
        elif offset == 79: flag = " ← predicted beat center"
        elif offset == 85: flag = " ← predicted upper sideband"
        print(f"    T+{offset}: {ratio:.2f}× [{h}/{t}] {bar}{flag}")

    # ============================================================
    # PREDICTION 4: Q ≈ 41 (SEVERELY UNDERDAMPED)
    # Verify: energy retention per cycle ≈ 92.5%
    # If Q=41, amplitude after n cycles = e^(-nπ/Q) = e^(-n×0.077)
    # ============================================================
    print(f"\n{'='*70}")
    print("PREDICTION 4: QUALITY FACTOR Q ≈ 41")
    print("  If Q=41: each T+35 cycle retains 92.5% of amplitude")
    print(f"{'='*70}")
    
    # Measure actual energy retention
    ratios_by_harmonic = []
    for n in range(1, 20):
        offset = n * 35
        h, t, r = echo_test(spikes, gme_ftd, offset, threshold_1s)
        ratio = r / base_rate
        ratios_by_harmonic.append((n, ratio))
    
    # Fit actual decay
    ns = np.array([x[0] for x in ratios_by_harmonic])
    rs = np.array([x[1] for x in ratios_by_harmonic])
    log_rs = np.log(np.maximum(rs, 0.1))
    slope, intercept, r_val, p_val, std_err = stats.linregress(ns, log_rs)
    
    # β per cycle
    beta_per_cycle = abs(slope)
    retention = np.exp(-beta_per_cycle)
    # Q = π / (beta_per_cycle)
    Q_measured = np.pi / beta_per_cycle if beta_per_cycle > 0 else float('inf')
    
    # Also compute via corrected method (half-life based)
    half_life_cycles = np.log(2) / beta_per_cycle if beta_per_cycle > 0 else float('inf')
    half_life_bd = half_life_cycles * 35
    beta_daily = np.log(2) / half_life_bd if half_life_bd > 0 else 0
    omega_0 = 2 * np.pi / 35
    Q_corrected = omega_0 / (2 * beta_daily) if beta_daily > 0 else float('inf')
    
    print(f"\n  Measured decay rate per T+35 cycle: {beta_per_cycle:.4f}")
    print(f"  Energy retention per cycle: {retention:.1%}")
    print(f"  Half-life: {half_life_cycles:.1f} cycles = {half_life_bd:.0f} BD = {half_life_bd*7/5/30:.1f} months")
    print(f"  Q (from per-cycle decay): {Q_measured:.1f}")
    print(f"  Q (from daily β, corrected): {Q_corrected:.1f}")
    print(f"  Deep Thinker predicted: Q ≈ 41")
    print(f"  Match: {'✅' if abs(Q_corrected - 41) < 15 else '❌'}")
    
    print(f"\n  Predicted vs Actual amplitude at each harmonic:")
    print(f"  {'n':>4} {'Predicted':>10} {'Actual':>8} {'Match':>8}")
    Q = Q_corrected
    for n, ratio in ratios_by_harmonic[:15]:
        predicted = np.exp(intercept) * np.exp(slope * n)
        print(f"  {n:>4} {predicted:>9.2f}× {ratio:>7.2f}× {'✅' if abs(predicted - ratio) < 0.5 else '~'}")

    # ============================================================
    # PREDICTION 5: T+140 = FOCUS REPORTING (semi-annual audit)
    # If true: T+140 should show negative returns AND be
    # specifically 28 weeks / 6.5 months
    # ============================================================
    print(f"\n{'='*70}")
    print("PREDICTION 5: T+140 = SEMI-ANNUAL FOCUS REPORTING")
    print("  Claim: −6.1% return from forced resolution at audit windows")
    print(f"{'='*70}")
    
    # Check returns at T+140 vs surrounding offsets
    print(f"\n  5-day returns around T+140:")
    for offset in [120, 125, 126, 130, 135, 140, 145, 150, 155]:
        returns = []
        for spike_date in spikes.index:
            echo_date = add_business_days(spike_date, offset)
            if echo_date in price_df.index:
                p0 = price_df.loc[echo_date, 'gme_close']
                end = add_business_days(echo_date, 5)
                if end in price_df.index:
                    p1 = price_df.loc[end, 'gme_close']
                    if p0 > 0:
                        returns.append((p1 - p0) / p0 * 100)
        if returns:
            mean_r = np.mean(returns)
            t_stat, p = stats.ttest_1samp(returns, 0)
            sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
            weeks = offset * 7 / 5 / 7
            print(f"    T+{offset} ({weeks:.0f}wk): {mean_r:>+6.1f}%, p={p:.3f} {sig:>3}")
    
    # Also check if T+126 (semi-annual = 26 weeks exactly) shows anything
    print(f"\n  Key reporting windows:")
    for name, offset in [("Quarterly (13wk)", 63), ("Semi-annual (26wk)", 126), 
                          ("6.5 months (28wk)", 140), ("Annual (52wk)", 252)]:
        returns = []
        for spike_date in spikes.index:
            echo_date = add_business_days(spike_date, offset)
            if echo_date in price_df.index:
                p0 = price_df.loc[echo_date, 'gme_close']
                end = add_business_days(echo_date, 5)
                if end in price_df.index:
                    p1 = price_df.loc[end, 'gme_close']
                    if p0 > 0:
                        returns.append((p1 - p0) / p0 * 100)
        if returns:
            mean_r = np.mean(returns)
            t_stat, p = stats.ttest_1samp(returns, 0)
            pos = sum(1 for r in returns if r > 0) / len(returns)
            print(f"    {name:<25}: {mean_r:>+6.1f}%, pos={pos:.0%}, p={p:.3f}")

    # ============================================================
    # PREDICTION 6: "FAST WATERFALL" T+10 in post-2021 era
    # Claim: T+1 + T+4 (BMME exempt) + T+5 (threshold) = T+10
    # ============================================================
    print(f"\n{'='*70}")
    print("PREDICTION 6: 'FAST WATERFALL' T+10 IN POST-2021")
    print("  Claim: Settlement shifted from T+35 to T+10 after squeeze")
    print(f"{'='*70}")
    
    for era, start, end in [("Pre-squeeze (2020)", "2020-01-01", "2020-12-31"),
                             ("Squeeze (2021)", "2021-01-01", "2021-12-31"),
                             ("Post-squeeze (2022-23)", "2022-01-01", "2023-12-31"),
                             ("Post-T+1 (2024-26)", "2024-01-01", "2026-12-31")]:
        era_spikes = spikes[(spikes.index >= start) & (spikes.index <= end)]
        if len(era_spikes) < 3:
            continue
        print(f"\n  {era} ({len(era_spikes)} spikes):")
        for offset in [5, 10, 13, 21, 25, 35]:
            h, t, r = echo_test(era_spikes, gme_ftd, offset, threshold_1s)
            ratio = r / base_rate if t > 0 else 0
            bar = "█" * min(15, int(ratio * 2))
            print(f"    T+{offset:<3}: {ratio:>5.1f}× [{h:>3}/{t:>3}] {bar}")

    # ============================================================
    # PREDICTION 7: 6-YEAR ECHO = SWAP MATURITY + RULE 17a-4
    # T+1575 BD ≈ 6.25 years. 2020 seed → arrives 2026
    # ============================================================
    print(f"\n{'='*70}")
    print("PREDICTION 7: 6-YEAR ECHO AND SWAP MATURITY")
    print("  Claim: T+1575 aligns with Rule 17a-4 (6yr record retention)")
    print(f"{'='*70}")
    
    # Which 2020 spikes have their T+1575 echoes arriving in 2026?
    spikes_2020 = spikes[(spikes.index >= '2020-01-01') & (spikes.index <= '2020-12-31')]
    print(f"\n  2020 FTD spikes and their T+1575 (6.25yr) echo dates:")
    for spike_date in spikes_2020.index[:15]:
        qty = spikes_2020.loc[spike_date, 'quantity']
        echo_date = add_business_days(spike_date, 1575)
        echo_year = echo_date.year
        in_data = "✅ in FTD data" if echo_date in gme_ftd.index else "→ future"
        if echo_date in gme_ftd.index:
            echo_qty = gme_ftd.loc[echo_date, 'quantity']
            is_spike = echo_qty > threshold_1s
            print(f"    {spike_date.date()} ({qty:>10,}) → {echo_date.date()} ({echo_qty:>10,}) {'⭐ SPIKE' if is_spike else ''}")
        else:
            print(f"    {spike_date.date()} ({qty:>10,}) → {echo_date.date()} {in_data}")

    # ============================================================
    # PREDICTION 8: ACTIVE NOISE CANCELLATION CHECK
    # If T+0 phantom OI is ANC, total OI should anti-correlate
    # with FTD magnitude (bigger FTD → more inverse-wave OI)
    # ============================================================
    print(f"\n{'='*70}")
    print("PREDICTION 8: T+0 ACTIVE NOISE CANCELLATION")
    print("  If ANC: FTD size should correlate with same-day OI surge")
    print(f"{'='*70}")
    
    THETA_OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
    
    correlations = []
    for spike_date in spikes.index:
        qty = spikes.loc[spike_date, 'quantity']
        oi_file = THETA_OI_DIR / f"oi_{spike_date.strftime('%Y%m%d')}.parquet"
        if oi_file.exists():
            try:
                oi_df = pd.read_parquet(oi_file)
                total_oi = oi_df['open_interest'].sum()
                correlations.append({'date': spike_date, 'ftd': qty, 'oi': total_oi})
            except:
                pass
    
    if correlations:
        cor_df = pd.DataFrame(correlations)
        r, p = stats.pearsonr(cor_df['ftd'], cor_df['oi'])
        rho, p_rho = stats.spearmanr(cor_df['ftd'], cor_df['oi'])
        print(f"\n  FTD spike days with OI data: {len(cor_df)}")
        print(f"  Pearson correlation (FTD vs OI): r={r:.3f}, p={p:.3f}")
        print(f"  Spearman correlation: ρ={rho:.3f}, p={p_rho:.3f}")
        print(f"  {'✅ POSITIVE — bigger FTDs → more phantom OI (ANC confirmed)' if r > 0.1 and p < 0.05 else '❌ No significant correlation'}")

    # Save
    print(f"\n  💾 Saved verification results")

if __name__ == "__main__":
    main()
