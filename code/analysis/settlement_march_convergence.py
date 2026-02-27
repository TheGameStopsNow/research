#!/usr/bin/env python3
"""
Phase 10: The March 2026 Convergence Calendar
===============================================
The settlement model predicts AMC's Jan 28 FTD spike (872K shares)
hits T+35 around March 18-20, 2026. Build the full cross-basket
forward calendar and verify the lateral energy transfer.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "ftd"
OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
OUT_DIR = Path(__file__).resolve().parents[2] / "temp" / "settlement_decoder"

NODES = {
    3: "CNS Netting",
    6: "Post-BFMM",
    10: "Fast Waterfall",
    13: "Reg SHO",
    18: "Margin Wall",
    26: "Secondary Cascade",
    33: "Echo Window",
    35: "Forced Buy-In",
    39: "Terminal Peak",
    45: "Terminal Boundary",
}


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
    z = (oi_matrix - baseline) / rolling_std.replace(0, np.nan)
    z = z.fillna(0)
    return z.abs().sum(axis=1)


def main():
    print("=" * 70)
    print("  PHASE 10: MARCH 2026 CONVERGENCE CALENDAR")
    print("=" * 70)

    today = pd.Timestamp("2026-02-23")
    gme = load_ftd("GME")
    amc = load_ftd("AMC")
    koss = load_ftd("KOSS")

    daily_stress = build_stress_series()

    # ═══════════════════════════════════════════════════════════════
    # CROSS-BASKET FORWARD CALENDAR
    # ═══════════════════════════════════════════════════════════════

    md = "# March 2026 Convergence Calendar\n\n"
    md += "**The Full Shadow Portfolio Forward View**\n\n"
    md += "Active FTD threads from GME, AMC, and KOSS that hit resolution\n"
    md += "deadlines in the next 90 days.\n\n---\n\n"

    events = []

    for ticker, ftd_df, threshold_pct in [("GME", gme, 0.85), ("AMC", amc, 0.85), ("KOSS", koss, 0.80)]:
        # Recent FTDs (last 90 days)
        recent = ftd_df[ftd_df['date'] >= today - pd.Timedelta(days=120)]
        threshold = ftd_df['quantity'].quantile(threshold_pct)

        # Only significant FTDs
        significant = recent[recent['quantity'] > threshold]

        for _, row in significant.iterrows():
            for offset, node in NODES.items():
                event_date = row['date'] + pd.offsets.BDay(offset)
                if today <= event_date <= today + pd.Timedelta(days=90):
                    events.append({
                        "date": event_date,
                        "ticker": ticker,
                        "node": node,
                        "offset": offset,
                        "ftd_date": row['date'],
                        "ftd_qty": row['quantity'],
                    })

    events.sort(key=lambda x: x['date'])

    # Build the calendar by week
    md += "## Cross-Basket Weekly Calendar\n\n"

    # Group by week
    if events:
        current_week = None
        for e in events:
            week = e['date'].isocalendar()[1]
            week_start = e['date'] - pd.Timedelta(days=e['date'].weekday())
            week_label = f"Week of {week_start.date()}"

            if week_label != current_week:
                if current_week is not None:
                    md += "\n"
                current_week = week_label
                md += f"### {week_label}\n\n"
                md += "| Date | Day | Ticker | Node | Offset | FTD Source | FTD Qty |\n"
                md += "|------|-----|--------|------|:--:|---|---:|\n"

            day = e['date'].day_name()[:3]
            md += (f"| {e['date'].date()} | {day} | **{e['ticker']}** | "
                   f"{e['node']} | T+{e['offset']} | {e['ftd_date'].date()} | "
                   f"{e['ftd_qty']:,} |\n")

    # ═══════════════════════════════════════════════════════════════
    # THE MARCH 18-20 CONVERGENCE
    # ═══════════════════════════════════════════════════════════════

    md += "\n---\n\n## 🔴 The March 18-20 Convergence\n\n"
    md += "AMC's massive Jan 28 FTD spike (872,178 shares) hits T+35 around March 18-20.\n"
    md += "Multiple GME threads also converge in this window.\n\n"

    # What converges on March 16-20?
    convergence = [e for e in events
                   if pd.Timestamp("2026-03-16") <= e['date'] <= pd.Timestamp("2026-03-20")]

    if convergence:
        md += "| Date | Ticker | Node | Source FTD | Qty |\n"
        md += "|------|--------|------|-----------|----:|\n"
        total_qty = 0
        for e in convergence:
            md += f"| {e['date'].date()} | **{e['ticker']}** | {e['node']} | {e['ftd_date'].date()} | {e['ftd_qty']:,} |\n"
            total_qty += e['ftd_qty']
        md += f"\n**Total FTD exposure converging**: {total_qty:,} shares across {len(convergence)} events\n"

    # ═══════════════════════════════════════════════════════════════
    # LATERAL ENERGY ACCOUNTING
    # ═══════════════════════════════════════════════════════════════

    md += "\n---\n\n## Lateral Energy Accounting: Dec 4, 2025 GME Mega-FTD\n\n"
    md += "Tracking the 2.07M-share GME FTD through the pipeline:\n\n"

    dec4 = pd.Timestamp("2025-12-04")

    # GME FTDs in the window
    gme_window = gme[(gme['date'] >= dec4) & (gme['date'] <= dec4 + pd.Timedelta(days=70))]
    gme_total = gme_window['quantity'].sum()

    # AMC FTDs in the window
    amc_window = amc[(amc['date'] >= dec4) & (amc['date'] <= dec4 + pd.Timedelta(days=70))]
    amc_total = amc_window['quantity'].sum()

    # KOSS FTDs
    koss_window = koss[(koss['date'] >= dec4) & (koss['date'] <= dec4 + pd.Timedelta(days=70))]
    koss_total = koss_window['quantity'].sum()

    # Baseline average FTDs per 70-day window
    gme_baseline = gme['quantity'].sum() / (gme['date'].max() - gme['date'].min()).days * 70
    amc_baseline = amc['quantity'].sum() / (amc['date'].max() - amc['date'].min()).days * 70
    koss_baseline = koss['quantity'].sum() / (koss['date'].max() - koss['date'].min()).days * 70

    md += "| Ticker | FTDs (70d after Dec 4) | Baseline (avg 70d) | Excess | Ratio |\n"
    md += "|--------|--------:|--------:|--------:|:--:|\n"

    for ticker, total, baseline in [("GME", gme_total, gme_baseline),
                                      ("AMC", amc_total, amc_baseline),
                                      ("KOSS", koss_total, koss_baseline)]:
        excess = total - baseline
        ratio = total / baseline if baseline > 0 else 0
        marker = "🔴" if ratio > 2 else "⚠️" if ratio > 1.5 else ""
        md += f"| {ticker} | {total:,.0f} | {baseline:,.0f} | {excess:+,.0f} | {ratio:.1f}× {marker} |\n"

    md += f"\n**Total cross-basket FTDs**: {gme_total + amc_total + koss_total:,.0f}\n"
    md += f"**GME seed**: 2,068,490\n"
    md += f"**Cascade multiplier**: {(gme_total + amc_total + koss_total) / 2068490:.1f}×\n"

    # ═══════════════════════════════════════════════════════════════
    # NOV 6, 2025: LIQUIDITY DEATH
    # ═══════════════════════════════════════════════════════════════

    md += "\n---\n\n## The Nov 6, 2025 Permanent Lock\n\n"
    md += "The GME↔AMC FTD correlation permanently locked positive on Nov 6, 2025.\n"
    md += "Before this date, the correlation oscillated with 32+ zero crossings.\n"
    md += "After this date: no negative readings.\n\n"

    # What changed around Nov 6?
    md += "### What Changed?\n\n"

    # GME / AMC FTDs in the weeks before and after
    pre_lock = gme[(gme['date'] >= '2025-10-01') & (gme['date'] <= '2025-11-05')]
    post_lock = gme[(gme['date'] >= '2025-11-06') & (gme['date'] <= '2025-12-15')]

    amc_pre = amc[(amc['date'] >= '2025-10-01') & (amc['date'] <= '2025-11-05')]
    amc_post = amc[(amc['date'] >= '2025-11-06') & (amc['date'] <= '2025-12-15')]

    md += "| Metric | Pre-lock (Oct-Nov 5) | Post-lock (Nov 6-Dec 15) | Change |\n"
    md += "|--------|:--:|:--:|:--:|\n"

    if len(pre_lock) > 0 and len(post_lock) > 0:
        gme_pre_mean = pre_lock['quantity'].mean()
        gme_post_mean = post_lock['quantity'].mean()
        md += f"| GME mean FTD | {gme_pre_mean:,.0f} | {gme_post_mean:,.0f} | {(gme_post_mean/gme_pre_mean - 1)*100:+.0f}% |\n"

    if len(amc_pre) > 0 and len(amc_post) > 0:
        amc_pre_mean = amc_pre['quantity'].mean()
        amc_post_mean = amc_post['quantity'].mean()
        md += f"| AMC mean FTD | {amc_pre_mean:,.0f} | {amc_post_mean:,.0f} | {(amc_post_mean/amc_pre_mean - 1)*100:+.0f}% |\n"

    # GME stress pre/post
    pre_stress = daily_stress['2025-10-01':'2025-11-05'].mean()
    post_stress = daily_stress['2025-11-06':'2025-12-15'].mean()
    md += f"| GME OI stress | {pre_stress:.1f} | {post_stress:.1f} | {(post_stress/pre_stress - 1)*100:+.0f}% |\n"

    # ═══════════════════════════════════════════════════════════════
    # CONSERVATION OF RISK MASS: BBBY
    # ═══════════════════════════════════════════════════════════════

    md += "\n---\n\n## Conservation of Risk Mass: BBBY\n\n"
    md += "When BBBY was canceled (Sep 29, 2023), did GME/AMC absorb its obligations?\n\n"

    # Stress before and after BBBY death
    pre_bbby = daily_stress['2023-05-01':'2023-08-31']
    post_bbby = daily_stress['2023-10-01':'2024-02-28']
    transition = daily_stress['2023-09-01':'2023-09-30']

    md += "| Period | Mean Stress | Change vs Pre |\n"
    md += "|--------|:--:|:--:|\n"
    md += f"| Pre-death (May-Aug 2023) | {pre_bbby.mean():.1f} | — |\n"
    md += f"| Death month (Sep 2023) | {transition.mean():.1f} | {(transition.mean()/pre_bbby.mean()-1)*100:+.0f}% |\n"
    md += f"| Post-death (Oct 2023-Feb 2024) | {post_bbby.mean():.1f} | {(post_bbby.mean()/pre_bbby.mean()-1)*100:+.0f}% |\n"

    # AMC FTDs before and after
    amc_pre_bbby = amc[(amc['date'] >= '2023-05-01') & (amc['date'] <= '2023-08-31')]
    amc_post_bbby = amc[(amc['date'] >= '2023-10-01') & (amc['date'] <= '2024-02-28')]

    if len(amc_pre_bbby) > 0 and len(amc_post_bbby) > 0:
        md += f"\nAMC mean FTD pre-BBBY death: **{amc_pre_bbby['quantity'].mean():,.0f}**\n"
        md += f"AMC mean FTD post-BBBY death: **{amc_post_bbby['quantity'].mean():,.0f}**\n"
        change = (amc_post_bbby['quantity'].mean() / amc_pre_bbby['quantity'].mean() - 1) * 100
        md += f"Change: **{change:+.0f}%**\n"
        if change > 50:
            md += "🔴 **AMC absorbed BBBY's obligations** — risk mass conserved\n"

    with open(OUT_DIR / "15_march_convergence.md", "w") as f:
        f.write(md)
    print(f"  → {OUT_DIR / '15_march_convergence.md'}")
    print(f"\n  {len(events)} total events in forward calendar")


if __name__ == "__main__":
    main()
