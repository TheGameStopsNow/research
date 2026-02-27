#!/usr/bin/env python3
"""
Phase 9: Testing settlement model V2 Predictions
==============================================
Four falsifiable predictions from the settlement model:

  1. PHASE TRANSITION DATE: Rolling correlation crosses zero in Q2/Q3 2021
  2. BBBY DEATH RATTLE: Sep 1 2023 anomaly = BBBY severance
  3. LATERAL RESOLUTION: Dec 4 2025 GME mega-FTD → AMC/KOSS absorption
  4. KOSS EARLY WARNING: Does KOSS FTD → 9d → GME stress work historically?
"""
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "ftd"
OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
OUT_DIR = Path(__file__).resolve().parents[2] / "temp" / "settlement_decoder"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_ftd(ticker):
    path = DATA_DIR / f"{ticker}_ftd.csv"
    if path.exists():
        df = pd.read_csv(path)
        df.columns = [c.lower().strip() for c in df.columns]
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        return df.dropna(subset=['date', 'quantity']).sort_values('date')
    return pd.DataFrame()


def build_stress_series():
    strike_ts = defaultdict(dict)
    for f in sorted(OI_DIR.glob("oi_*.parquet")):
        date_str = f.stem.replace("oi_", "")
        try:
            df = pd.read_parquet(f)
            deep = df[(df["right"] == "PUT") & (df["strike"] <= 15)]
            for _, row in deep.iterrows():
                strike_ts[float(row["strike"])][date_str] = int(row["open_interest"])
        except Exception:
            continue
    oi_matrix = pd.DataFrame(strike_ts).fillna(0)
    oi_matrix.index = pd.to_datetime(oi_matrix.index, format="%Y%m%d")
    oi_matrix = oi_matrix.sort_index()
    baseline = oi_matrix.rolling(20, min_periods=5).median()
    rolling_std = oi_matrix.rolling(20, min_periods=5).std()
    z_scores = (oi_matrix - baseline) / rolling_std.replace(0, np.nan)
    z_scores = z_scores.fillna(0)
    daily_stress = z_scores.abs().sum(axis=1)
    daily_stress.name = "stress"
    return daily_stress


def write_md(name, content):
    path = OUT_DIR / name
    with open(path, "w") as f:
        f.write(content)
    print(f"  → {path}")


# ═══════════════════════════════════════════════════════════════════
# PREDICTION 1: Phase Transition Date
# ═══════════════════════════════════════════════════════════════════
def test_phase_transition():
    print("\n" + "=" * 70)
    print("  PREDICTION 1: Phase Transition Date")
    print("=" * 70)

    gme = load_ftd("GME")
    amc = load_ftd("AMC")

    # Build daily FTD series
    idx = pd.date_range("2020-12-01", "2026-02-23", freq='B')
    gme_d = gme.groupby('date')['quantity'].sum().reindex(idx, fill_value=0)
    amc_d = amc.groupby('date')['quantity'].sum().reindex(idx, fill_value=0)

    # Rolling 30-day correlation
    gme_log = np.log1p(gme_d)
    amc_log = np.log1p(amc_d)

    rolling_corr = gme_log.rolling(30, min_periods=15).corr(amc_log)

    md = "# Phase Transition: When Did the Pipeline Lock?\n\n"
    md += "**Prediction**: Rolling 30-day GME↔AMC FTD correlation crosses from negative to permanently positive in Q2/Q3 2021, coinciding with SR-NSCC-2021-002.\n\n"

    # Find zero crossings
    md += "## Rolling 30-Day Correlation Timeline\n\n"
    md += "| Date | Correlation | Event Context |\n"
    md += "|------|:---:|---|\n"

    # Sample key dates
    key_dates = [
        ("2021-01-15", "Pre-squeeze"),
        ("2021-01-29", "Squeeze peak"),
        ("2021-02-26", "Post-squeeze"),
        ("2021-03-31", "Q1 end"),
        ("2021-04-30", "April"),
        ("2021-05-28", "May"),
        ("2021-06-25", "SR-NSCC-2021-002 approved (June 23)"),
        ("2021-07-30", "July"),
        ("2021-08-31", "August"),
        ("2021-09-30", "September"),
        ("2021-10-29", "October"),
        ("2021-12-31", "Year end"),
        ("2022-06-30", "Pre-split"),
        ("2022-09-30", "Post-split"),
        ("2023-05-31", "BBBY pre-death"),
        ("2023-09-01", "BBBY death rattle?"),
        ("2024-05-17", "Pre-DFV return"),
        ("2024-06-28", "Post-DFV"),
        ("2025-12-04", "Mega-FTD"),
    ]

    for date_str, context in key_dates:
        dt = pd.Timestamp(date_str)
        # Get nearest available date
        nearest = rolling_corr.index[rolling_corr.index.get_indexer([dt], method='nearest')[0]]
        r = rolling_corr.get(nearest, np.nan)
        if not np.isnan(r):
            marker = "🔴" if r > 0.3 else "⚠️" if r > 0 else "🔵" if r < -0.3 else ""
            md += f"| {nearest.date()} | {r:+.3f} {marker} | {context} |\n"

    # Find the EXACT zero crossing
    md += "\n## Zero-Crossing Detection\n\n"
    
    # Look for where rolling_corr transitions from <0 to >0 and stays positive
    rc = rolling_corr.dropna()
    zero_crossings = []
    for i in range(1, len(rc)):
        if rc.iloc[i-1] < 0 and rc.iloc[i] >= 0:
            zero_crossings.append((rc.index[i], rc.iloc[i], "negative → positive"))
        elif rc.iloc[i-1] >= 0 and rc.iloc[i] < 0:
            zero_crossings.append((rc.index[i], rc.iloc[i], "positive → negative"))

    md += "| Date | Correlation | Direction |\n"
    md += "|------|:---:|---|\n"
    for dt, r, direction in zero_crossings:
        md += f"| {dt.date()} | {r:+.3f} | {direction} |\n"

    # Find the LAST zero crossing (when it becomes permanently positive)
    last_neg_to_pos = None
    for dt, r, direction in zero_crossings:
        if "negative → positive" in direction:
            # Check if it stays positive for at least 60 days after
            future = rc[dt:dt + pd.Timedelta(days=90)]
            if len(future) > 20 and (future > 0).mean() > 0.7:
                last_neg_to_pos = dt

    if last_neg_to_pos:
        md += f"\n**Permanent positive lock date**: **{last_neg_to_pos.date()}**\n"
        md += f"(Correlation became persistently positive after this date)\n"
        print(f"    Phase transition: {last_neg_to_pos.date()}")

        # Check against SR-NSCC-2021-002 (approved June 23, 2021)
        nscc_date = pd.Timestamp("2021-06-23")
        delta = (last_neg_to_pos - nscc_date).days
        md += f"\nSR-NSCC-2021-002 approved: June 23, 2021\n"
        md += f"Delta from rule change: **{delta:+d} days**\n"

        if abs(delta) < 30:
            md += "🔴 **MATCH** — Phase transition coincides with NSCC rule change\n"
        elif abs(delta) < 90:
            md += "⚠️ Within 3 months of rule change\n"
        else:
            md += "No temporal match with SR-NSCC-2021-002\n"

    write_md("11_phase_transition.md", md)


# ═══════════════════════════════════════════════════════════════════
# PREDICTION 2: BBBY Death Rattle
# ═══════════════════════════════════════════════════════════════════
def test_bbby_death(daily_stress):
    print("\n" + "=" * 70)
    print("  PREDICTION 2: BBBY Death Rattle → Sep 1 2023")
    print("=" * 70)

    md = "# BBBY Death Rattle: Does Sep 1, 2023 Match?\n\n"
    md += "**Prediction**: Sept 1 unexplained anomaly (stress=84.3, residual=+74.3) was prime brokers re-weighting VaR to sever the BBBY leg from the swap basket.\n\n"
    md += "**BBBY Timeline**:\n"
    md += "- Jan 2023: BBBY announces going concern doubt\n"
    md += "- Apr 23, 2023: BBBY files Chapter 11\n"
    md += "- May 2023: BBBY delisted from NASDAQ\n"
    md += "- Sep 29, 2023: Shares officially canceled\n\n"

    # Stress around key BBBY dates
    md += "## GME Stress Around BBBY Events\n\n"
    md += "| Date | GME Stress | Percentile | BBBY Event |\n"
    md += "|------|:--:|:--:|---|\n"

    bbby_dates = [
        ("2023-01-06", "BBBY going concern warning"),
        ("2023-01-25", "Post-announcement"),
        ("2023-04-21", "Pre-Chapter 11"),
        ("2023-04-24", "Chapter 11 filing"),
        ("2023-04-25", "Day after filing"),
        ("2023-05-01", "BBBY delisted"),
        ("2023-08-28", "4 weeks pre-cancellation"),
        ("2023-09-01", "THE ANOMALY"),
        ("2023-09-05", "Post-Labor Day"),
        ("2023-09-15", "Mid-Sep"),
        ("2023-09-29", "Shares officially canceled"),
        ("2023-10-02", "Post-cancellation"),
        ("2023-10-16", "2 weeks post"),
    ]

    for date_str, event in bbby_dates:
        dt = pd.Timestamp(date_str)
        nearest = daily_stress.index[daily_stress.index.get_indexer([dt], method='nearest')[0]]
        s = daily_stress.get(nearest, 0)
        pctile = (daily_stress < s).mean() * 100
        marker = "🔴" if pctile > 95 else "⚠️" if pctile > 80 else ""
        md += f"| {nearest.date()} | {s:.1f} | {pctile:.0f}th {marker} | {event} |\n"

    # The critical test: was Sep 1 stress elevated relative to surrounding weeks?
    aug_stress = daily_stress["2023-08-15":"2023-08-31"].mean()
    sep1_stress = daily_stress.get(pd.Timestamp("2023-09-01"), 0)
    oct_stress = daily_stress["2023-10-01":"2023-10-15"].mean()

    md += f"\n## Stress Comparison\n\n"
    md += f"- Aug 15-31 mean stress: **{aug_stress:.1f}**\n"
    md += f"- **Sep 1 stress: {sep1_stress:.1f}** (the anomaly)\n"
    md += f"- Oct 1-15 mean stress: **{oct_stress:.1f}**\n"
    md += f"- Sep 1 / Aug mean: **{sep1_stress / aug_stress:.1f}× elevated**\n\n"

    # Did stress DECLINE after Sep 29 (cancellation)?
    pre_cancel = daily_stress["2023-09-15":"2023-09-28"].mean()
    post_cancel = daily_stress["2023-10-01":"2023-10-15"].mean()

    md += f"- Pre-cancellation stress (Sep 15-28): **{pre_cancel:.1f}**\n"
    md += f"- Post-cancellation stress (Oct 1-15): **{post_cancel:.1f}**\n"
    change = (post_cancel - pre_cancel) / pre_cancel * 100
    md += f"- Change: **{change:+.0f}%**\n\n"

    if post_cancel < pre_cancel * 0.8:
        md += "🔴 **CONFIRMED**: Stress dropped after BBBY cancellation — consistent with pipeline severance\n"
    elif post_cancel < pre_cancel:
        md += "⚠️ Mild decline after cancellation\n"
    else:
        md += "Stress did NOT decline after cancellation\n"

    print(f"    Sep 1 vs Aug avg: {sep1_stress/aug_stress:.1f}x elevated")
    print(f"    Post-cancel change: {change:+.0f}%")

    write_md("12_bbby_death_rattle.md", md)


# ═══════════════════════════════════════════════════════════════════
# PREDICTION 3: Dec 4 2025 Lateral Resolution
# ═══════════════════════════════════════════════════════════════════
def test_lateral_resolution():
    print("\n" + "=" * 70)
    print("  PREDICTION 3: Dec 4 2025 Mega-FTD → Lateral Resolution")
    print("=" * 70)

    gme = load_ftd("GME")
    amc = load_ftd("AMC")
    koss = load_ftd("KOSS")

    event_date = pd.Timestamp("2025-12-04")

    md = "# Lateral Resolution: Where Did the 2.07M-Share GME FTD Go?\n\n"
    md += "**Prediction**: The mega-FTD was absorbed through AMC/KOSS pipeline via cross-collateralization.\n"
    md += "AMC or KOSS should show anomalous FTD spikes or price crashes around Dec 4 + T+10 to T+35.\n\n"

    for ticker, ftd_df in [("AMC", amc), ("KOSS", koss), ("GME", gme)]:
        md += f"## {ticker} FTDs Around Dec 4, 2025\n\n"
        md += "| Date | FTDs | Offset | Context |\n"
        md += "|------|-----:|:---:|---|\n"

        nearby = ftd_df[
            (ftd_df['date'] >= event_date - pd.Timedelta(days=10)) &
            (ftd_df['date'] <= event_date + pd.Timedelta(days=60))
        ].sort_values('date')

        if len(nearby) == 0:
            md += "| — | No data | — | — |\n\n"
            continue

        # Historical 90th percentile for this ticker
        threshold = ftd_df['quantity'].quantile(0.90)

        for _, row in nearby.iterrows():
            offset = (row['date'] - event_date).days
            bday_offset = np.busday_count(event_date.date(), row['date'].date())
            
            context_parts = []
            if bday_offset == 0:
                context_parts.append("EVENT DAY")
            elif 10 <= bday_offset <= 18:
                context_parts.append("FAST WATERFALL zone")
            elif 33 <= bday_offset <= 36:
                context_parts.append("ECHO window")
            elif bday_offset == 35:
                context_parts.append("T+35 FORCED BUY-IN")

            if row['quantity'] > threshold:
                context_parts.append(f"🔴 >90th pctile ({threshold:,.0f})")

            context = ", ".join(context_parts) if context_parts else ""
            md += f"| {row['date'].date()} | {row['quantity']:,} | T+{bday_offset} | {context} |\n"

        # Was there an anomalous cluster?
        window_10_35 = nearby[
            (nearby['date'] >= event_date + pd.Timedelta(days=14)) &
            (nearby['date'] <= event_date + pd.Timedelta(days=55))
        ]
        if len(window_10_35) > 0:
            max_ftd = window_10_35['quantity'].max()
            max_date = window_10_35.loc[window_10_35['quantity'].idxmax(), 'date']
            mean_ftd = window_10_35['quantity'].mean()
            md += f"\n**T+10 to T+35 window**: max={max_ftd:,} on {max_date.date()}, mean={mean_ftd:,.0f}"
            md += f" (vs normal mean {ftd_df['quantity'].mean():,.0f})\n"

            if max_ftd > threshold:
                md += f"🔴 **Anomalous spike detected in {ticker} during GME's T+10 to T+35 window**\n"

        md += "\n---\n\n"

    write_md("13_lateral_resolution.md", md)


# ═══════════════════════════════════════════════════════════════════
# PREDICTION 4: KOSS Early Warning System
# ═══════════════════════════════════════════════════════════════════
def test_koss_early_warning(daily_stress):
    print("\n" + "=" * 70)
    print("  PREDICTION 4: KOSS Early Warning System")
    print("=" * 70)

    koss = load_ftd("KOSS")
    koss_daily = koss.groupby('date')['quantity'].sum().reindex(daily_stress.index, fill_value=0)

    md = "# KOSS Early Warning System\n\n"
    md += "**Prediction**: KOSS FTD spike → 9 business days → GME stress surge.\n"
    md += "KOSS has no options chain, so failures appear immediately in SEC data.\n\n"

    # Find all KOSS spikes
    koss_threshold = koss_daily[koss_daily > 0].quantile(0.85)
    spike_dates = koss_daily[koss_daily > koss_threshold].index

    md += f"KOSS spike threshold (85th pct): {koss_threshold:,.0f}\n"
    md += f"Number of spikes: {len(spike_dates)}\n\n"

    # For each KOSS spike, measure GME stress at T+1 through T+15
    md += "## Average GME Stress After KOSS FTD Spikes\n\n"
    md += "| Offset | GME Stress | vs Baseline | Interpretation |\n"
    md += "|--------|:--:|:--:|---|\n"

    baseline = daily_stress.mean()

    for offset in range(0, 16):
        shifted = spike_dates + pd.offsets.BDay(offset)
        stress_vals = daily_stress.reindex(shifted).dropna()
        if len(stress_vals) > 3:
            m = stress_vals.mean()
            excess = m - baseline
            pct = excess / baseline * 100
            marker = "🔴" if pct > 40 else "⚠️" if pct > 20 else ""
            node = ""
            if offset == 9:
                node = "← PREDICTED PEAK"
            elif offset == 0:
                node = "KOSS spike day"
            md += f"| T+{offset} | {m:.1f} | {excess:+.1f} ({pct:+.0f}%) | {node} {marker} |\n"

    # Does T+9 actually show peak excess?
    offsets_stress = {}
    for offset in range(0, 16):
        shifted = spike_dates + pd.offsets.BDay(offset)
        vals = daily_stress.reindex(shifted).dropna()
        if len(vals) > 3:
            offsets_stress[offset] = vals.mean()

    if offsets_stress:
        peak_offset = max(offsets_stress, key=offsets_stress.get)
        md += f"\n**Actual peak offset**: T+{peak_offset} (stress={offsets_stress[peak_offset]:.1f})\n"
        md += f"**Predicted peak**: T+9\n"

        if peak_offset == 9:
            md += "🔴 **EXACT MATCH** — KOSS leads GME by exactly 9 business days\n"
        elif 7 <= peak_offset <= 11:
            md += f"⚠️ Close to prediction (within 2 days)\n"
        else:
            md += f"Peak at T+{peak_offset}, not T+9\n"

        print(f"    Peak GME stress after KOSS spike: T+{peak_offset}")

    # Historical accuracy: for each KOSS spike, was GME stress elevated at T+9?
    md += "\n## Event-by-Event: KOSS Spike → GME Stress at T+9\n\n"
    md += "| KOSS Spike Date | KOSS FTD | GME Stress T+9 | vs Baseline | Hit? |\n"
    md += "|----------------|--------:|:--:|:--:|:--:|\n"

    hits = 0
    total = 0
    for dt in spike_dates:
        t9 = dt + pd.offsets.BDay(9)
        koss_qty = koss_daily.get(dt, 0)
        gme_s = daily_stress.reindex([t9]).iloc[0] if t9 in daily_stress.index else np.nan
        if not np.isnan(gme_s):
            total += 1
            excess = gme_s - baseline
            hit = "✅" if gme_s > baseline * 1.3 else "—"
            if gme_s > baseline * 1.3:
                hits += 1
            md += f"| {dt.date()} | {koss_qty:,} | {gme_s:.1f} | {excess:+.1f} | {hit} |\n"

    if total > 0:
        md += f"\n**Hit rate**: {hits}/{total} = **{hits/total*100:.0f}%** (where hit = stress > 130% of baseline)\n"

    # Current KOSS status
    md += "\n## Current KOSS Status (Last 20 Days)\n\n"
    recent_koss = koss.tail(20)
    if len(recent_koss) > 0:
        md += "| Date | KOSS FTDs | Above threshold? | GME signal expected by |\n"
        md += "|------|--------:|:--:|---|\n"
        for _, row in recent_koss.iterrows():
            above = "🔴 YES" if row['quantity'] > koss_threshold else ""
            signal_date = row['date'] + pd.offsets.BDay(9)
            md += f"| {row['date'].date()} | {row['quantity']:,} | {above} | {signal_date.date()} |\n"

    write_md("14_koss_early_warning.md", md)


# ═══════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  PHASE 9: TESTING settlement model V2 PREDICTIONS")
    print("=" * 70)

    print("\n  Loading data...")
    daily_stress = build_stress_series()
    print(f"  Stress: {len(daily_stress)} days")

    test_phase_transition()
    test_bbby_death(daily_stress)
    test_lateral_resolution()
    test_koss_early_warning(daily_stress)

    print(f"\n  All results saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
