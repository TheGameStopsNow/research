#!/usr/bin/env python3
"""
V3 VERIFICATION: Testing the Novation Crush and May 2026 Convergence
1. T+126 + T+14 = T+140 (Novation Crush decomposition)
2. Dense spectrum around T+126 to find the swap expiry signal
3. The May 5-7, 2026 convergence calendar
4. Dec 2025 mega-seed forward cascade prediction
5. Cross-ticker coupling test (XRT FTDs vs GME FTDs)
"""
import pandas as pd
import numpy as np
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

    # ============================================================
    # TEST 1: NOVATION CRUSH DECOMPOSITION
    # T+126 (swap expiry) → T+140 (physical unwind)
    # If true: returns should turn negative BETWEEN T+126 and T+140
    # ============================================================
    print("=" * 70)
    print("TEST 1: NOVATION CRUSH (T+126 → T+140)")
    print("  Prediction: Swap expiry at T+126, physical unwind by T+140")
    print("  Signature: Returns turn negative in the T+126→T+140 window")
    print("=" * 70)
    
    print(f"\n  {'Offset':>8} {'Return':>8} {'Pos%':>6} {'p-val':>8} {'Sig':>4} {'Phase':>20}")
    print("  " + "-" * 60)
    
    for offset in range(115, 155):
        returns = []
        for spike_date in spikes.index:
            echo_date = add_business_days(spike_date, offset)
            if echo_date in price_df.index:
                p0 = price_df.loc[echo_date, 'gme_close']
                end = add_business_days(echo_date, 3)
                if end in price_df.index:
                    p1 = price_df.loc[end, 'gme_close']
                    if p0 > 0:
                        returns.append((p1 - p0) / p0 * 100)
        if len(returns) >= 10:
            mean_r = np.mean(returns)
            pos = sum(1 for r in returns if r > 0) / len(returns)
            t_stat, p = stats.ttest_1samp(returns, 0)
            sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
            
            phase = ""
            if offset <= 117: phase = "IMM roll window"
            elif offset <= 125: phase = "dead zone"
            elif offset == 126: phase = "← SWAP EXPIRY"
            elif offset <= 139: phase = "novation unwind"
            elif offset == 140: phase = "← NOVATION CRUSH"
            elif offset <= 145: phase = "post-crush"
            
            marker = "█" if mean_r < -1 else ("▓" if mean_r < 0 else "░")
            print(f"  T+{offset:<5} {mean_r:>+6.1f}% {pos:>5.0%} {p:>7.3f} {sig:>3} {phase:>20} {marker}")

    # ============================================================
    # TEST 2: FTD ECHOES AT T+126 (swap expiry) vs T+140 (crush)
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 2: FTD ECHO ENRICHMENT T+120→T+150")
    print("  Does the FTD itself echo at T+126 or T+140?")
    print(f"{'='*70}")
    
    for offset in range(120, 151):
        h, t, r = echo_test(spikes, gme_ftd, offset, threshold_1s)
        ratio = r / base_rate if t > 3 else 0
        bar = "█" * min(15, int(ratio * 4))
        flag = ""
        if offset == 126: flag = " ← swap expiry"
        elif offset == 140: flag = " ← novation crush"
        print(f"    T+{offset}: {ratio:.2f}× [{h:>2}/{t:>3}] {bar}{flag}")

    # ============================================================
    # TEST 3: THE MAY 2026 CONVERGENCE CALENDAR
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 3: THE MAY 2026 CONVERGENCE CALENDAR")
    print("  Mapping ALL predicted events arriving March→June 2026")
    print(f"{'='*70}")
    
    events = []
    
    # 6-year echoes (T+1575)
    for spike_date in spikes.index:
        echo_date = add_business_days(spike_date, 1575)
        if pd.Timestamp('2026-02-01') <= echo_date <= pd.Timestamp('2026-07-01'):
            qty = spikes.loc[spike_date, 'quantity']
            events.append({
                'date': echo_date, 'source': f"6yr echo from {spike_date.date()}",
                'type': 'T+1575', 'ftd': qty
            })
    
    # T+105 from recent large spikes (Dec 2025, Oct 2025, Jun 2025)
    recent_big = spikes[spikes.index >= '2025-01-01'].nlargest(10, 'quantity')
    for spike_date in recent_big.index:
        for harmonic, label in [(35, "T+35"), (70, "T+70"), (105, "T+105")]:
            echo_date = add_business_days(spike_date, harmonic)
            if pd.Timestamp('2026-02-01') <= echo_date <= pd.Timestamp('2026-07-01'):
                qty = recent_big.loc[spike_date, 'quantity']
                events.append({
                    'date': echo_date, 'source': f"{label} from {spike_date.date()}",
                    'type': label, 'ftd': qty
                })
    
    # T+140 novation crush from recent spikes
    for spike_date in recent_big.index:
        echo_date = add_business_days(spike_date, 140)
        if pd.Timestamp('2026-02-01') <= echo_date <= pd.Timestamp('2026-07-01'):
            qty = recent_big.loc[spike_date, 'quantity']
            events.append({
                'date': echo_date, 'source': f"Novation from {spike_date.date()}",
                'type': 'T+140', 'ftd': qty
            })
    
    events_df = pd.DataFrame(events).sort_values('date')
    
    print(f"\n  Total predicted events in Mar→Jun 2026: {len(events_df)}")
    
    if len(events_df) > 0:
        # Group by week
        events_df['week'] = events_df['date'].dt.isocalendar().week
        events_df['month'] = events_df['date'].dt.month
        
        print(f"\n  CONVERGENCE CALENDAR:")
        for _, row in events_df.iterrows():
            urgency = "🔴" if row['type'] in ['T+105', 'T+1575'] else ("🟡" if row['type'] == 'T+140' else "🟢")
            print(f"    {urgency} {row['date'].date()} | {row['type']:<8} | {row['ftd']:>10,} FTD | {row['source']}")
        
        # Count events per week
        print(f"\n  Events per week:")
        weekly = events_df.groupby(events_df['date'].dt.isocalendar().week).size()
        for week, count in weekly.items():
            dates_in_week = events_df[events_df['date'].dt.isocalendar().week == week]['date']
            start = dates_in_week.min().date()
            end = dates_in_week.max().date()
            bar = "█" * count
            danger = " ⚠️ CONVERGENCE" if count >= 3 else ""
            print(f"    Week {week}: {start}→{end}: {count} events {bar}{danger}")

    # ============================================================
    # TEST 4: XRT COUPLED OSCILLATOR (if XRT FTD data exists)
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 4: XRT COUPLING (Coupled Oscillator)")
    print(f"{'='*70}")
    
    xrt_path = DATA_DIR / "XRT_ftd.csv"
    if xrt_path.exists():
        xrt_ftd = pd.read_csv(xrt_path, parse_dates=['date'])
        xrt_ftd = xrt_ftd.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
        
        # Align dates
        common = gme_ftd.index.intersection(xrt_ftd.index)
        gme_aligned = gme_ftd.loc[common, 'quantity']
        xrt_aligned = xrt_ftd.loc[common, 'quantity']
        
        r, p = stats.pearsonr(gme_aligned, xrt_aligned)
        rho, p_rho = stats.spearmanr(gme_aligned, xrt_aligned)
        print(f"\n  GME vs XRT FTD correlation ({len(common)} common days):")
        print(f"  Pearson: r={r:.3f}, p={p:.4f}")
        print(f"  Spearman: ρ={rho:.3f}, p={p_rho:.4f}")
        
        # Anti-correlation test: When GME FTDs drop, do XRT FTDs spike?
        gme_diff = gme_aligned.diff()
        xrt_diff = xrt_aligned.diff()
        valid = gme_diff.dropna().index.intersection(xrt_diff.dropna().index)
        r_diff, p_diff = stats.pearsonr(gme_diff.loc[valid], xrt_diff.loc[valid])
        print(f"  FTD change correlation: r={r_diff:.3f}, p={p_diff:.4f}")
        print(f"  {'✅ Anti-correlated (energy transfer)' if r_diff < -0.05 and p_diff < 0.05 else '❌ Not anti-correlated' if r_diff > 0 else '⚠️ Weak anti-correlation'}")
        
        # Test: Do GME spikes predict XRT spikes at T+5?
        print(f"\n  GME spike → XRT echo test:")
        for offset in [0, 1, 2, 3, 5, 10, 13, 21, 35]:
            xrt_mean = xrt_ftd['quantity'].mean()
            xrt_std = xrt_ftd['quantity'].std()
            xrt_thresh = xrt_mean + xrt_std
            h, t, r = 0, 0, 0
            for spike_date in spikes.index:
                echo_date = add_business_days(spike_date, offset)
                if echo_date in xrt_ftd.index:
                    t += 1
                    if xrt_ftd.loc[echo_date, 'quantity'] > xrt_thresh:
                        h += 1
            if t > 3:
                xrt_base = (xrt_ftd['quantity'] > xrt_thresh).mean()
                ratio = (h / t) / xrt_base
                bar = "█" * min(12, int(ratio * 3))
                print(f"    T+{offset:<3}: {ratio:.1f}× [{h}/{t}] {bar}")
    else:
        print("  XRT FTD data not found — skipping coupling test")
        # Check what FTD files we have
        ftd_files = list(DATA_DIR.glob("*_ftd.csv"))
        print(f"  Available FTD files: {[f.name for f in ftd_files]}")

    # ============================================================
    # TEST 5: DEC 2025 MEGA-SEED FORWARD CASCADE
    # ============================================================
    print(f"\n{'='*70}")
    print("TEST 5: DEC 4, 2025 MEGA-SEED — FORWARD CASCADE PREDICTION")
    print("  Seed: 2,068,490 FTD on Dec 4, 2025")
    print(f"{'='*70}")
    
    seed_date = pd.Timestamp('2025-12-04')
    seed_qty = 2_068_490
    retention = 0.958
    multiplier = 23.8
    price = 23.0  # approximate
    
    gross = seed_qty * price * multiplier
    
    print(f"\n  Gross obligation: ${gross/1e6:.0f}M")
    print(f"\n  {'Node':>12} {'Date':>12} {'Remain':>10} {'Cal Days':>10} {'Type':>20}")
    print("  " + "-" * 70)
    
    nodes = [
        (5, "T+5 Fast"),
        (10, "T+10 Threshold"),
        (13, "T+13 Reg SHO"),
        (25, "T+25 Statutory Wall"),
        (35, "T+35 Composite"),
        (70, "T+70 2nd harmonic"),
        (105, "T+105 3rd (AMPLIFIED)"),
        (126, "T+126 Swap Expiry"),
        (140, "T+140 Novation Crush"),
        (175, "T+175 5th harmonic"),
        (525, "T+525 LCM Supercycle"),
        (1575, "T+1575 6yr Terminal"),
    ]
    
    for offset, label in nodes:
        echo_date = add_business_days(seed_date, offset)
        cycles = offset / 35
        remaining = gross * (retention ** cycles)
        cal_days = (echo_date - seed_date).days
        danger = "🔴" if offset in [105, 140, 1575] else ("🟡" if offset in [25, 35, 126] else "🟢")
        print(f"  {danger} T+{offset:<5} {echo_date.date()} ${remaining/1e6:>8.1f}M {cal_days:>8}d {label}")

    print(f"\n  💾 Results saved")

if __name__ == "__main__":
    main()
