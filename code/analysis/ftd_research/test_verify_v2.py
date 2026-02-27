#!/usr/bin/env python3
"""
VERIFICATION V2: Testing Deep Thinker Round 2 Predictions
1. T+25 recentered harmonics (T+50, T+75, T+100, T+125, T+150...)
2. LCM(25,21)=525 supercycle node
3. Bang-Bang threshold controller (binary OI response)
4. T+140 forensic calendar → audit month mapping
5. Duffing cubic: odd/even power spectrum
6. T+112 vs T+126 (IMM roll timing)
7. The 4.2% leakage / 23.8× multiplier validation
8. Stored energy estimation ("Doomsday Gauge")
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import timedelta
from scipy import stats

DATA_DIR = Path(str(Path.home()) + "/Documents/GitHub/research/data/ftd")
OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
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

    # ============================================================
    # TEST 1: T+25 RECENTERED HARMONICS
    # ============================================================
    print("=" * 70)
    print("TEST 1: T+25 HARMONIC SERIES (vs T+35 series)")
    print("  Fundamental = T+25 BD (35 calendar days)")
    print("=" * 70)
    
    print(f"\n  {'n':>4} {'T+25 harm':>10} {'Enrich':>8} {'T+35 harm':>10} {'Enrich':>8} {'Winner':>8}")
    print("  " + "-" * 55)
    
    t25_total, t35_total = 0, 0
    for n in range(1, 21):
        off_25 = n * 25
        off_35 = n * 35
        h25, t25, r25 = echo_test(spikes, gme_ftd, off_25, threshold_1s)
        ratio_25 = r25 / base_rate if t25 > 3 else 0
        h35, t35, r35 = echo_test(spikes, gme_ftd, off_35, threshold_1s)
        ratio_35 = r35 / base_rate if t35 > 3 else 0
        winner = "T+25" if ratio_25 > ratio_35 else "T+35"
        t25_total += ratio_25
        t35_total += ratio_35
        print(f"  {n:>4} T+{off_25:<5} {ratio_25:>7.2f}× T+{off_35:<5} {ratio_35:>7.2f}× {winner:>8}")
    
    print(f"\n  Sum of enrichments: T+25 series = {t25_total:.1f}, T+35 series = {t35_total:.1f}")
    print(f"  Winner: {'T+25 ✅' if t25_total > t35_total else 'T+35'}")

    # ============================================================
    # TEST 2: LCM(25,21)=525 SUPERCYCLE NODE
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 2: LCM NODES")
    print(f"{'='*70}")
    
    lcm_tests = [
        ("LCM(25,21)=525", 525),
        ("LCM(35,21)=105", 105),
        ("LCM(25,13)=325", 325),
        ("LCM(35,13)=455", 455),
        ("LCM(21,13)=273", 273),
        ("LCM(25,63)=225", 225),
        ("LCM(35,63)=315", 315),
    ]
    
    for name, offset in lcm_tests:
        h, t, r = echo_test(spikes, gme_ftd, offset, threshold_1s)
        ratio = r / base_rate if t > 3 else 0
        # Neighbors
        neighbors = []
        for n_off in range(offset-10, offset+11):
            if n_off != offset and n_off > 0:
                nh, nt, nr = echo_test(spikes, gme_ftd, n_off, threshold_1s)
                if nt > 3:
                    neighbors.append(nr / base_rate)
        n_mean = np.mean(neighbors) if neighbors else 0
        is_peak = ratio > n_mean * 1.1
        bar = "█" * min(15, int(ratio * 4))
        print(f"  {name:<20}: {ratio:.2f}× (neighbors: {n_mean:.2f}×) {bar} {'✅' if is_peak else '❌'}")

    # ============================================================
    # TEST 3: BANG-BANG THRESHOLD CONTROLLER
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 3: BANG-BANG THRESHOLD CONTROLLER")
    print("  Prediction: OI response is BINARY (on/off), not proportional")
    print("  Test: Do OI surges cluster at specific round-lot sizes?")
    print(f"{'='*70}")
    
    oi_events = []
    for spike_date in spikes.index:
        oi_file = OI_DIR / f"oi_{spike_date.strftime('%Y%m%d')}.parquet"
        if oi_file.exists():
            try:
                oi_df = pd.read_parquet(oi_file)
                total_oi = oi_df['open_interest'].sum()
                max_single = oi_df['open_interest'].max()
                n_strikes = len(oi_df[oi_df['open_interest'] > 100])
                oi_events.append({
                    'date': spike_date, 'ftd': spikes.loc[spike_date, 'quantity'],
                    'total_oi': total_oi, 'max_single': max_single, 'n_strikes': n_strikes
                })
            except:
                pass
    
    if oi_events:
        oi_df = pd.DataFrame(oi_events)
        
        # Test: Is the distribution of max_single_strike OI bimodal (bang-bang)?
        max_vals = oi_df['max_single'].values
        # Check for clustering at round lots
        round_5k = sum(1 for v in max_vals if abs(v - round(v/5000)*5000) < 500)
        round_10k = sum(1 for v in max_vals if abs(v - round(v/10000)*10000) < 1000)
        
        print(f"\n  Spike days with OI data: {len(oi_df)}")
        print(f"  Max single-strike OI stats:")
        print(f"    Mean: {max_vals.mean():,.0f}")
        print(f"    Median: {np.median(max_vals):,.0f}")
        print(f"    Std: {max_vals.std():,.0f}")
        print(f"    CV (coefficient of variation): {max_vals.std()/max_vals.mean():.2f}")
        print(f"    Near 5K round lots: {round_5k}/{len(max_vals)} ({round_5k/len(max_vals):.0%})")
        print(f"    Near 10K round lots: {round_10k}/{len(max_vals)} ({round_10k/len(max_vals):.0%})")
        
        # Test bimodality
        from scipy.stats import kurtosis
        k = kurtosis(max_vals)
        print(f"    Kurtosis: {k:.2f} ({'bimodal-like (negative)' if k < 0 else 'peaked (positive)'})")
        
        # Distribution of total_oi on spike days vs non-spike days
        print(f"\n  OI distribution on FTD spike days:")
        q25, q50, q75 = np.percentile(oi_df['total_oi'], [25, 50, 75])
        print(f"    Q25={q25:,.0f}, Median={q50:,.0f}, Q75={q75:,.0f}")
        
        # Correlation: FTD size vs number of active strikes (test "precision" of response)
        r, p = stats.pearsonr(oi_df['ftd'], oi_df['n_strikes'])
        print(f"\n  FTD size vs # active strikes: r={r:.3f}, p={p:.3f}")
        print(f"  (Bang-Bang predicts NO correlation — fixed response regardless of FTD size)")
        print(f"  Result: {'✅ No correlation (Bang-Bang confirmed)' if p > 0.05 else '❌ Significant correlation'}")

    # ============================================================
    # TEST 4: T+140 FORENSIC CALENDAR MAPPING
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 4: T+140 FORENSIC CALENDAR → AUDIT MONTHS")
    print("  Prediction: Seeds in Dec → resolution in June; Seeds in June → Dec")
    print(f"{'='*70}")
    
    # Map top 30 FTD spikes to their T+140 dates
    top_spikes = spikes.nlargest(30, 'quantity')
    t140_months = {}
    
    print(f"\n  Top 30 FTD spikes → T+140 resolution dates:")
    for spike_date in sorted(top_spikes.index):
        qty = top_spikes.loc[spike_date, 'quantity']
        t140_date = add_business_days(spike_date, 140)
        month = t140_date.month
        t140_months[month] = t140_months.get(month, 0) + 1
        seed_month = spike_date.strftime('%b')
        res_month = t140_date.strftime('%b')
        print(f"    {spike_date.date()} ({qty:>10,}) → T+140: {t140_date.date()} ({seed_month}→{res_month})")
    
    print(f"\n  T+140 resolution month distribution:")
    for m in range(1, 13):
        count = t140_months.get(m, 0)
        month_name = pd.Timestamp(2024, m, 1).strftime('%B')
        bar = "█" * count
        audit = " ← AUDIT" if m in [6, 12] else ""
        print(f"    {month_name:<12}: {count:>2} {bar}{audit}")

    # ============================================================
    # TEST 5: DUFFING ODD/EVEN POWER SPECTRUM
    # sin³(ωt) generates 3rd harmonic. Test: ratio of odd/even at each order
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 5: DUFFING CUBIC NONLINEARITY — ODD vs EVEN SPECTRUM")
    print("  Prediction: x³ generates ONLY odd harmonics (1,3,5,7...)")
    print(f"{'='*70}")
    
    # Using T+25 as fundamental
    print(f"\n  T+25 harmonics — odd vs even enrichment:")
    odd_vals, even_vals = [], []
    for n in range(1, 21):
        offset = n * 25
        h, t, r = echo_test(spikes, gme_ftd, offset, threshold_1s)
        ratio = r / base_rate if t > 3 else 0
        parity = "ODD" if n % 2 == 1 else "even"
        bar = "█" * min(15, int(ratio * 4))
        print(f"    {n:>3}× T+25 = T+{offset:<5}: {ratio:.2f}× [{parity:>4}] {bar}")
        if n % 2 == 1:
            odd_vals.append(ratio)
        else:
            even_vals.append(ratio)
    
    odd_mean = np.mean(odd_vals)
    even_mean = np.mean(even_vals)
    t_stat, p_val = stats.ttest_ind(odd_vals, even_vals)
    print(f"\n  Odd harmonic mean: {odd_mean:.3f}×")
    print(f"  Even harmonic mean: {even_mean:.3f}×")
    print(f"  Ratio (odd/even): {odd_mean/even_mean:.3f}")
    print(f"  t-test: t={t_stat:.2f}, p={p_val:.3f}")
    print(f"  Duffing prediction (odd > even): {'✅' if odd_mean > even_mean else '❌'}")

    # ============================================================
    # TEST 6: IMM ROLL — T+112 vs T+126
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 6: IMM ROLL TIMING (T+112 vs T+126)")
    print("  Prediction: Early roll at T+112 (=T+126 minus 14 BD)")
    print(f"{'='*70}")
    
    print(f"\n  Dense spectrum T+105 → T+130:")
    for offset in range(105, 131):
        h, t, r = echo_test(spikes, gme_ftd, offset, threshold_1s)
        ratio = r / base_rate if t > 3 else 0
        bar = "█" * min(15, int(ratio * 4))
        flag = ""
        if offset == 105: flag = " ← 3×T+35 / LCM(35,21)"
        elif offset == 112: flag = " ← predicted IMM roll"
        elif offset == 126: flag = " ← 2×T+63 (theoretical OPEX)"
        print(f"    T+{offset}: {ratio:.2f}× [{h:>2}/{t:>3}] {bar}{flag}")

    # ============================================================
    # TEST 7: THE 4.2% LEAKAGE
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 7: THE 4.2% LEAKAGE MODEL")
    print("  Q=74 → 4.2% energy loss per cycle → 23.8× multiplier")
    print(f"{'='*70}")
    
    # If FTD = 4.2% of true obligation, estimate total hidden obligation
    total_visible_ftd = gme_ftd['quantity'].sum()
    mean_price = price_df['gme_close'].mean()
    total_visible_notional = total_visible_ftd * mean_price / 1e9
    
    multiplier = 1 / 0.042
    gross_estimate = total_visible_notional * multiplier
    
    print(f"\n  Total visible FTD volume (22yr): {total_visible_ftd:,.0f} shares")
    print(f"  Average price: ${mean_price:.2f}")
    print(f"  Total visible notional: ${total_visible_notional:.2f}B")
    print(f"  23.8× multiplier → Gross hidden obligation: ${gross_estimate:.1f}B (cumulative)")
    
    # Per-year breakdown
    print(f"\n  Annual gross hidden obligation estimate:")
    for year in range(2016, 2026):
        yr_ftd = gme_ftd[gme_ftd.index.year == year]['quantity'].sum()
        yr_price = price_df[price_df.index.year == year]['gme_close'].mean() if year in price_df.index.year else mean_price
        yr_vis = yr_ftd * yr_price / 1e6
        yr_gross = yr_vis * multiplier
        bar = "█" * min(25, int(yr_gross / 100))
        print(f"    {year}: visible=${yr_vis:>8.1f}M → gross≈${yr_gross:>10.1f}M {bar}")

    # ============================================================
    # TEST 8: DOOMSDAY GAUGE — STORED ENERGY ESTIMATE
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 8: DOOMSDAY GAUGE — CURRENT STORED ENERGY")
    print("  E = Σ(FTD × 23.8 × Price × Retention^cycles)")
    print(f"{'='*70}")
    
    retention = 0.958
    cycle_len = 35  # BD
    
    # Calculate stored energy from all spikes still echoing
    last_date = gme_ftd.index.max()
    stored_energy = 0
    active_seeds = 0
    
    for spike_date in spikes.index:
        days_elapsed = np.busday_count(spike_date.date(), last_date.date())
        cycles_elapsed = days_elapsed / cycle_len
        qty = spikes.loc[spike_date, 'quantity']
        
        # Get price on spike date
        if spike_date in price_df.index:
            price = price_df.loc[spike_date, 'gme_close']
        else:
            price = mean_price
        
        notional = qty * price * multiplier  # Gross obligation
        remaining = notional * (retention ** cycles_elapsed)
        
        if remaining > 1_000_000:  # > $1M still echoing
            stored_energy += remaining
            active_seeds += 1
    
    print(f"\n  Active seeds still echoing (>$1M remaining): {active_seeds}")
    print(f"  Total estimated stored energy: ${stored_energy/1e9:.2f}B")
    print(f"\n  Top 10 contributors to current stored energy:")
    
    contributions = []
    for spike_date in spikes.index:
        days_elapsed = np.busday_count(spike_date.date(), last_date.date())
        cycles_elapsed = days_elapsed / cycle_len
        qty = spikes.loc[spike_date, 'quantity']
        price = price_df.loc[spike_date, 'gme_close'] if spike_date in price_df.index else mean_price
        notional = qty * price * multiplier
        remaining = notional * (retention ** cycles_elapsed)
        if remaining > 0:
            contributions.append((spike_date, qty, notional, remaining, cycles_elapsed))
    
    contributions.sort(key=lambda x: x[3], reverse=True)
    for spike_date, qty, notional, remaining, cycles in contributions[:10]:
        print(f"    {spike_date.date()}: {qty:>10,} FTD, gross=${notional/1e6:>8.1f}M, remaining=${remaining/1e6:>8.1f}M ({cycles:.0f} cycles ago)")

    print(f"\n  💾 All results saved")

if __name__ == "__main__":
    main()
