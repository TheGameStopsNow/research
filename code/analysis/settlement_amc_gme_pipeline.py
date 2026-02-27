#!/usr/bin/env python3
"""
Phase 8: AMC↔GME Shared Settlement Pipeline Deep Dive
=======================================================
The cross-correlation test (Phase 7) revealed r=0.234 between AMC FTDs
and GME deep OTM put stress. This script digs deep into that relationship:

  1. GRANGER CAUSALITY: Does AMC FTD → GME stress, or vice versa?
  2. REGIME EVOLUTION: Has the linkage strengthened or weakened over time?
  3. BASKET TEST: KOSS as a third member of the shared pipeline
  4. SUPERADDITIVITY: Combined GME+AMC FTD shocks → amplified stress?
  5. TIMING FORENSICS: When exactly does the cross-signal fire?
  6. FTD ECHO CHAINS: Do AMC FTDs echo into GME's waterfall at T+35?
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "ftd"
OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
PRICE_CSV = DATA_DIR / "gme_daily_price.csv"
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


def load_price():
    df = pd.read_csv(PRICE_CSV)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date').set_index('date')


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


def ftd_to_daily(ftd_df, stress_index):
    daily = ftd_df.groupby('date')['quantity'].sum()
    return daily.reindex(stress_index, fill_value=0)


def write_md(name, content):
    path = OUT_DIR / name
    with open(path, "w") as f:
        f.write(content)
    print(f"  → {path}")


# ═══════════════════════════════════════════════════════════════════
# 1. GRANGER-LIKE CAUSALITY
# ═══════════════════════════════════════════════════════════════════
def test_granger_causality(daily_stress, gme_ftd_daily, amc_ftd_daily, price_df):
    print("\n" + "=" * 70)
    print("  1. GRANGER-LIKE CAUSALITY: Who leads whom?")
    print("=" * 70)

    md = "# Granger-Like Causality: AMC ↔ GME Pipeline\n\n"
    md += "Does AMC FTD **cause** GME stress, or do they share a common cause?\n\n"

    # Build regression dataset
    combined = pd.DataFrame({
        'gme_stress': daily_stress,
        'gme_ftd': np.log1p(gme_ftd_daily),
        'amc_ftd': np.log1p(amc_ftd_daily),
    }).dropna()

    # Add lagged variables
    for lag in [1, 3, 5, 7, 10]:
        combined[f'gme_stress_lag{lag}'] = combined['gme_stress'].shift(lag)
        combined[f'amc_lag{lag}'] = combined['amc_ftd'].shift(lag)
        combined[f'gme_ftd_lag{lag}'] = combined['gme_ftd'].shift(lag)

    combined = combined.dropna()

    # Test 1: Does lagged AMC FTD predict GME stress beyond GME's own history?
    md += "## Test A: AMC FTDs → GME Stress (controlling for GME's own FTDs)\n\n"

    # Restricted model: GME stress ~ own lags
    from numpy.linalg import lstsq
    X_restricted = combined[['gme_stress_lag1', 'gme_stress_lag3', 'gme_stress_lag5',
                              'gme_ftd_lag1', 'gme_ftd_lag3', 'gme_ftd_lag5']].values
    X_unrestricted = combined[['gme_stress_lag1', 'gme_stress_lag3', 'gme_stress_lag5',
                                'gme_ftd_lag1', 'gme_ftd_lag3', 'gme_ftd_lag5',
                                'amc_lag1', 'amc_lag3', 'amc_lag5']].values
    y = combined['gme_stress'].values

    # Add intercept
    X_r = np.column_stack([np.ones(len(y)), X_restricted])
    X_u = np.column_stack([np.ones(len(y)), X_unrestricted])

    # OLS
    beta_r, res_r, _, _ = lstsq(X_r, y, rcond=None)
    beta_u, res_u, _, _ = lstsq(X_u, y, rcond=None)

    SSR_r = np.sum((y - X_r @ beta_r) ** 2)
    SSR_u = np.sum((y - X_u @ beta_u) ** 2)
    R2_r = 1 - SSR_r / np.sum((y - y.mean()) ** 2)
    R2_u = 1 - SSR_u / np.sum((y - y.mean()) ** 2)

    n = len(y)
    p_r = X_r.shape[1]
    p_u = X_u.shape[1]
    q = p_u - p_r  # number of additional regressors

    F_stat = ((SSR_r - SSR_u) / q) / (SSR_u / (n - p_u))
    from scipy.stats import f as f_dist
    p_value = 1 - f_dist.cdf(F_stat, q, n - p_u)

    md += f"- Restricted model (GME lags only): R² = {R2_r:.4f}\n"
    md += f"- Unrestricted model (+ AMC lags): R² = {R2_u:.4f}\n"
    md += f"- **R² improvement: {(R2_u - R2_r):.4f}** ({(R2_u - R2_r) / max(R2_r, 0.001) * 100:+.1f}%)\n"
    md += f"- F-statistic: **{F_stat:.2f}**, p = {p_value:.4f}\n"
    sig = "🔴 YES — AMC FTDs Granger-cause GME stress" if p_value < 0.05 else "⚠️ Marginal" if p_value < 0.10 else "No"
    md += f"- Granger causality: **{sig}**\n\n"

    print(f"    AMC → GME: F={F_stat:.2f}, p={p_value:.4f}, R² improvement={R2_u - R2_r:.4f}")

    # Test 2: Does lagged GME stress predict AMC FTDs?
    md += "## Test B: GME Stress → AMC FTDs (reverse direction)\n\n"

    y2 = combined['amc_ftd'].values
    X_r2 = np.column_stack([np.ones(n), combined[['amc_lag1', 'amc_lag3', 'amc_lag5']].values])
    X_u2 = np.column_stack([np.ones(n), combined[['amc_lag1', 'amc_lag3', 'amc_lag5',
                                                    'gme_stress_lag1', 'gme_stress_lag3', 'gme_stress_lag5']].values])

    beta_r2, _, _, _ = lstsq(X_r2, y2, rcond=None)
    beta_u2, _, _, _ = lstsq(X_u2, y2, rcond=None)
    SSR_r2 = np.sum((y2 - X_r2 @ beta_r2) ** 2)
    SSR_u2 = np.sum((y2 - X_u2 @ beta_u2) ** 2)
    R2_r2 = 1 - SSR_r2 / np.sum((y2 - y2.mean()) ** 2)
    R2_u2 = 1 - SSR_u2 / np.sum((y2 - y2.mean()) ** 2)
    q2 = X_u2.shape[1] - X_r2.shape[1]
    F_stat2 = ((SSR_r2 - SSR_u2) / q2) / (SSR_u2 / (n - X_u2.shape[1]))
    p_value2 = 1 - f_dist.cdf(F_stat2, q2, n - X_u2.shape[1])

    md += f"- Restricted model (AMC lags only): R² = {R2_r2:.4f}\n"
    md += f"- Unrestricted model (+ GME stress lags): R² = {R2_u2:.4f}\n"
    md += f"- **R² improvement: {(R2_u2 - R2_r2):.4f}**\n"
    md += f"- F-statistic: **{F_stat2:.2f}**, p = {p_value2:.4f}\n"
    sig2 = "🔴 YES — GME stress Granger-causes AMC FTDs" if p_value2 < 0.05 else "⚠️ Marginal" if p_value2 < 0.10 else "No"
    md += f"- Granger causality: **{sig2}**\n\n"

    print(f"    GME → AMC: F={F_stat2:.2f}, p={p_value2:.4f}")

    # Interpretation
    if p_value < 0.05 and p_value2 < 0.05:
        md += "> **BIDIRECTIONAL CAUSALITY**: Both directions are significant. This implies a shared settlement pipeline where failures in either stock propagate to the other.\n"
    elif p_value < 0.05:
        md += "> **AMC → GME UNIDIRECTIONAL**: AMC failures drive GME options chain stress, but not vice versa. AMC may be the larger pipeline.\n"
    elif p_value2 < 0.05:
        md += "> **GME → AMC UNIDIRECTIONAL**: GME's options stress channels predict AMC failures.\n"
    else:
        md += "> **COMMON CAUSE**: Neither direction is individually causal. Both may respond to a shared upstream trigger (e.g., a common short seller's settlement events).\n"

    return md


# ═══════════════════════════════════════════════════════════════════
# 2. REGIME-SPECIFIC CROSS-CORRELATION
# ═══════════════════════════════════════════════════════════════════
def test_regime_xcorr(daily_stress, amc_ftd_daily):
    print("\n" + "=" * 70)
    print("  2. REGIME-SPECIFIC CROSS-CORRELATION")
    print("=" * 70)

    md = "\n## Regime-Specific AMC↔GME Correlation\n\n"
    md += "Has the linkage strengthened, weakened, or shifted over time?\n\n"

    md += "| Era | Same-day r | Peak lag r | Peak lag | N | Interpretation |\n"
    md += "|-----|:--:|:--:|:--:|:--:|---|\n"

    regimes = [
        ("Pre-squeeze (2020)", "2020-01-01", "2020-12-31"),
        ("Squeeze (Q1 2021)", "2021-01-01", "2021-03-31"),
        ("Post-squeeze (2021)", "2021-04-01", "2021-12-31"),
        ("Pre-split (2022 H1)", "2022-01-01", "2022-07-21"),
        ("Post-split (2022-23)", "2022-07-22", "2023-12-31"),
        ("RK era (2024)", "2024-01-01", "2024-12-31"),
        ("Current (2025-26)", "2025-01-01", "2026-12-31"),
    ]

    for name, start, end in regimes:
        mask = (daily_stress.index >= start) & (daily_stress.index <= end)
        s = daily_stress[mask]
        a = amc_ftd_daily[mask]

        valid = (s > 0) & (a > 0)
        n_valid = valid.sum()
        if n_valid < 10:
            md += f"| {name} | — | — | — | {n_valid} | Insufficient data |\n"
            continue

        # Same-day
        r0 = np.corrcoef(s[valid], np.log1p(a[valid]))[0, 1]

        # Find peak lag
        best_r, best_lag = 0, 0
        for lag in range(-10, 11):
            shifted = np.log1p(a).shift(lag)
            v = (s > 0) & (shifted > 0) & shifted.notna()
            if v.sum() > 10:
                r = np.corrcoef(s[v], shifted[v])[0, 1]
                if abs(r) > abs(best_r):
                    best_r, best_lag = r, lag

        if best_lag < 0:
            interp = f"AMC leads by {abs(best_lag)}d"
        elif best_lag > 0:
            interp = f"GME leads by {best_lag}d"
        else:
            interp = "Contemporaneous"

        marker = "🔴" if abs(best_r) > 0.3 else "⚠️" if abs(best_r) > 0.15 else ""
        md += f"| {name} | {r0:+.3f} | {best_r:+.3f} {marker} | T{best_lag:+d} | {n_valid} | {interp} |\n"
        print(f"    {name}: r0={r0:+.3f}, peak r={best_r:+.3f} at lag {best_lag}")

    return md


# ═══════════════════════════════════════════════════════════════════
# 3. BASKET TEST: KOSS
# ═══════════════════════════════════════════════════════════════════
def test_basket_members(daily_stress):
    print("\n" + "=" * 70)
    print("  3. FULL BASKET TEST: AMC, KOSS, XRT, IWM")
    print("=" * 70)

    md = "\n## Full Basket Cross-Correlation Matrix\n\n"
    md += "| Ticker | Same-day r | Spike-day stress | vs Normal | t-stat | Lead/Lag peak |\n"
    md += "|--------|:--:|:--:|:--:|:--:|---|\n"

    for ticker in ["AMC", "KOSS", "XRT", "IWM"]:
        ftd = load_ftd(ticker)
        if ftd.empty:
            continue

        ftd_daily = ftd_to_daily(ftd, daily_stress.index)
        log_ftd = np.log1p(ftd_daily)
        valid = (daily_stress > 0) & (log_ftd > 0)

        if valid.sum() < 20:
            continue

        r0 = np.corrcoef(daily_stress[valid], log_ftd[valid])[0, 1]

        # Spike days
        threshold = ftd_daily[ftd_daily > 0].quantile(0.90)
        spike_dates = set(ftd_daily[ftd_daily > threshold].index)
        if spike_dates:
            stress_spike = daily_stress[daily_stress.index.isin(spike_dates)]
            stress_normal = daily_stress[~daily_stress.index.isin(spike_dates)]
            if len(stress_spike) > 3:
                t, p = stats.ttest_ind(stress_spike, stress_normal, equal_var=False)
            else:
                t, p = 0, 1
        else:
            t, p = 0, 1

        # Peak lag
        best_r, best_lag = 0, 0
        for lag in range(-10, 11):
            shifted = log_ftd.shift(lag)
            v = (daily_stress > 0) & (shifted > 0) & shifted.notna()
            if v.sum() > 20:
                r = np.corrcoef(daily_stress[v], shifted[v])[0, 1]
                if abs(r) > abs(best_r):
                    best_r, best_lag = r, lag

        lead_lag = f"T{best_lag:+d} (r={best_r:+.3f})"
        marker = "🔴" if abs(t) > 2 else "⚠️" if abs(t) > 1.5 else ""
        md += f"| {ticker} | {r0:+.3f} | {stress_spike.mean() if spike_dates else 0:.1f} | {stress_normal.mean():.1f} | {t:.2f} {marker} | {lead_lag} |\n"
        print(f"    {ticker}: r0={r0:+.3f}, t={t:.2f}, peak lag={best_lag}")

    return md


# ═══════════════════════════════════════════════════════════════════
# 4. SUPERADDITIVITY: Combined shocks
# ═══════════════════════════════════════════════════════════════════
def test_superadditivity(daily_stress, gme_ftd_daily, amc_ftd_daily):
    print("\n" + "=" * 70)
    print("  4. SUPERADDITIVITY: Combined FTD shocks")
    print("=" * 70)

    md = "\n## Superadditivity: Is GME + AMC Combined Stress > Sum of Parts?\n\n"

    # Classify days
    gme_threshold = gme_ftd_daily[gme_ftd_daily > 0].quantile(0.80)
    amc_threshold = amc_ftd_daily[amc_ftd_daily > 0].quantile(0.80)

    both_spike = (gme_ftd_daily > gme_threshold) & (amc_ftd_daily > amc_threshold)
    gme_only = (gme_ftd_daily > gme_threshold) & (amc_ftd_daily <= amc_threshold)
    amc_only = (gme_ftd_daily <= gme_threshold) & (amc_ftd_daily > amc_threshold)
    neither = (gme_ftd_daily <= gme_threshold) & (amc_ftd_daily <= amc_threshold)

    categories = {
        "Neither spiking": neither,
        "GME only spike": gme_only,
        "AMC only spike": amc_only,
        "BOTH spiking": both_spike,
    }

    md += "| Condition | Mean Stress | N | vs Baseline |\n"
    md += "|-----------|:--:|:--:|:--:|\n"

    baseline = daily_stress[neither].mean()
    cat_means = {}

    for label, mask in categories.items():
        s = daily_stress[mask]
        if len(s) > 0:
            m = s.mean()
            excess = m - baseline
            marker = "🔴" if excess > 5 else "⚠️" if excess > 2 else ""
            md += f"| {label} | {m:.1f} | {len(s)} | {excess:+.1f} {marker} |\n"
            cat_means[label] = m
            print(f"    {label}: stress={m:.1f}, n={len(s)}")

    # Superadditivity check
    if "GME only spike" in cat_means and "AMC only spike" in cat_means and "BOTH spiking" in cat_means:
        expected_additive = cat_means["GME only spike"] + cat_means["AMC only spike"] - baseline
        actual_both = cat_means["BOTH spiking"]
        ratio = actual_both / max(expected_additive, 0.01)

        md += f"\n**Superadditivity Test:**\n"
        md += f"- Expected (additive): {expected_additive:.1f}\n"
        md += f"- Actual (both spiking): {actual_both:.1f}\n"
        md += f"- Ratio: **{ratio:.2f}×**\n"

        if ratio > 1.2:
            md += f"- 🔴 **SUPERADDITIVE** — combined FTD shocks amplify OI stress beyond linear addition\n"
        elif ratio > 0.8:
            md += f"- Approximately additive — no amplification\n"
        else:
            md += f"- Sub-additive — combined shocks produce less stress than expected\n"

    return md


# ═══════════════════════════════════════════════════════════════════
# 5. FTD ECHO CHAINS: AMC → GME at T+35
# ═══════════════════════════════════════════════════════════════════
def test_cross_echo(daily_stress, amc_ftd_daily, price_df):
    print("\n" + "=" * 70)
    print("  5. CROSS-ECHO: AMC FTD → GME Price at T+35")
    print("=" * 70)

    md = "\n## Cross-Echo: Do AMC FTD Spikes Predict GME Price at T+35?\n\n"
    md += "If the pipeline is shared, AMC FTDs should predict GME price moves.\n\n"

    amc_threshold = amc_ftd_daily[amc_ftd_daily > 0].quantile(0.90)
    spike_dates = amc_ftd_daily[amc_ftd_daily > amc_threshold].index

    md += "### AMC FTD Spike → GME Forward Returns\n\n"
    md += "| Horizon | Post-AMC-FTD | Baseline | Excess | N | Sig? |\n"
    md += "|---------|:--:|:--:|:--:|:--:|:--:|\n"

    for horizon in [5, 10, 15, 20, 25, 30, 35, 40, 45]:
        event_rets = []
        for dt in spike_dates:
            try:
                base = price_df.loc[dt - pd.Timedelta(days=3):dt + pd.Timedelta(days=3), 'gme_close']
                fwd_dt = dt + pd.offsets.BDay(horizon)
                fwd = price_df.loc[fwd_dt - pd.Timedelta(days=3):fwd_dt + pd.Timedelta(days=3), 'gme_close']
                if len(base) > 0 and len(fwd) > 0:
                    event_rets.append((fwd.iloc[-1] / base.iloc[0] - 1) * 100)
            except Exception:
                pass

        if len(event_rets) > 5:
            mean_ret = np.mean(event_rets)
            uc = price_df['gme_close'].pct_change(horizon).dropna() * 100
            baseline = uc.mean()
            excess = mean_ret - baseline
            t_stat = (mean_ret - baseline) / (np.std(event_rets) / np.sqrt(len(event_rets))) if np.std(event_rets) > 0 else 0
            sig = "🔴" if abs(t_stat) > 2 else "⚠️" if abs(t_stat) > 1.5 else ""
            md += f"| T+{horizon}d | {mean_ret:+.1f}% | {baseline:+.1f}% | {excess:+.1f}% | {len(event_rets)} | {t_stat:.2f} {sig} |\n"

            if horizon in [10, 35]:
                print(f"    AMC FTD → GME T+{horizon}: ret={mean_ret:+.1f}%, excess={excess:+.1f}%, t={t_stat:.2f}")

    # Comparison: GME FTD spikes vs AMC FTD spikes → GME returns
    md += "\n### Comparison: Which FTD Source Predicts GME Better?\n\n"
    md += "| Source | T+10 Excess | T+35 Excess |\n|--------|:--:|:--:|\n"

    for ticker, ftd_daily in [("GME", load_ftd("GME")), ("AMC", load_ftd("AMC"))]:
        if ftd_daily.empty:
            continue
        ftd_d = ftd_to_daily(ftd_daily, daily_stress.index)
        thresh = ftd_d[ftd_d > 0].quantile(0.90)
        spikes = ftd_d[ftd_d > thresh].index

        for horizon in [10, 35]:
            rets = []
            for dt in spikes:
                try:
                    base = price_df.loc[dt - pd.Timedelta(days=3):dt + pd.Timedelta(days=3), 'gme_close']
                    fwd_dt = dt + pd.offsets.BDay(horizon)
                    fwd = price_df.loc[fwd_dt - pd.Timedelta(days=3):fwd_dt + pd.Timedelta(days=3), 'gme_close']
                    if len(base) > 0 and len(fwd) > 0:
                        rets.append((fwd.iloc[-1] / base.iloc[0] - 1) * 100)
                except Exception:
                    pass
            if rets:
                uc = price_df['gme_close'].pct_change(horizon).dropna() * 100
                excess = np.mean(rets) - uc.mean()
                if horizon == 10:
                    md += f"| {ticker} FTDs | {excess:+.1f}% |"
                else:
                    md += f" {excess:+.1f}% |\n"

    return md


# ═══════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  PHASE 8: AMC↔GME SHARED PIPELINE DEEP DIVE")
    print("=" * 70)

    print("\n  Loading data...")
    daily_stress = build_stress_series()
    print(f"  Stress: {len(daily_stress)} days")
    price_df = load_price()
    gme_ftd = load_ftd("GME")
    amc_ftd = load_ftd("AMC")
    print(f"  GME FTDs: {len(gme_ftd)}, AMC FTDs: {len(amc_ftd)}")

    gme_ftd_daily = ftd_to_daily(gme_ftd, daily_stress.index)
    amc_ftd_daily = ftd_to_daily(amc_ftd, daily_stress.index)

    md = "# AMC↔GME Shared Settlement Pipeline\n\n"
    md += "Deep dive into the r=0.234 cross-correlation discovered in Phase 7.\n\n---\n"

    md += test_granger_causality(daily_stress, gme_ftd_daily, amc_ftd_daily, price_df)
    md += test_regime_xcorr(daily_stress, amc_ftd_daily)
    md += test_basket_members(daily_stress)
    md += test_superadditivity(daily_stress, gme_ftd_daily, amc_ftd_daily)
    md += test_cross_echo(daily_stress, amc_ftd_daily, price_df)

    write_md("09_amc_gme_pipeline.md", md)
    print(f"\n  All results saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
