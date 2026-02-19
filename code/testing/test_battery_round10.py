#!/usr/bin/env python3
"""
Round 10 Test Battery — Final Regulatory Audit & Boundary Testing
=================================================================

Tests:
  T1: Full-Day Tape Fracture Scan — Does the May 17 dislocation extend into the open?
  T2: Cross-Date TRF Ceiling — Is the $33 ceiling unique to OpEx Friday? (May 13-16)
  T3: Contingent Flag Audit — % of off-market TRF trades missing Codes 14/41/52/53 (GME vs SPY/AAPL)
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ── Paths ──────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
POLYGON_ROOT = REPO_ROOT / "data" / "raw" / "polygon" / "trades"
RESULTS_DIR = Path(__file__).parent

def load_equity_parquet(ticker, date_str):
    date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}" if len(date_str) == 8 else date_str
    path = POLYGON_ROOT / f"symbol={ticker}" / f"date={date_fmt}" / "part-0.parquet"
    if not path.exists(): return None
    df = pd.read_parquet(path)
    ts_col = 'timestamp' if 'timestamp' in df.columns else 'sip_timestamp'
    df['ts'] = pd.to_datetime(df[ts_col])
    if df['ts'].dt.tz is not None:
        df['ts'] = df['ts'].dt.tz_localize(None)
    return df

def get_available_polygon_dates(ticker):
    d_path = POLYGON_ROOT / f"symbol={ticker}"
    if not d_path.exists(): return []
    return sorted([d.replace("date=", "") for d in os.listdir(d_path) if d.startswith("date=")])

# ===================================================================
# T1: FULL-DAY TAPE FRACTURE SCAN (MAY 17, 2024)
# ===================================================================
def test_t1_fullday_fracture():
    print("\n" + "=" * 60)
    print("T1: FULL-DAY TAPE FRACTURE SCAN (MAY 17, 2024)")
    print("=" * 60)
    
    eq = load_equity_parquet('GME', '2024-05-17')
    if eq is None: return {"status": "NO_DATA"}
    
    print(f"  Total trades: {len(eq):,}")
    
    dark_ids = {4, 15}
    dark = eq[eq['exchange'].isin(dark_ids)].copy()
    lit = eq[~eq['exchange'].isin(dark_ids)].copy()
    
    print(f"  Dark (TRF): {len(dark):,} | Lit: {len(lit):,}")
    
    dark['minute'] = dark['ts'].dt.floor('1min')
    lit['minute'] = lit['ts'].dt.floor('1min')
    
    def calc_vwap(df):
        s = df['size'].sum()
        return (df['price'] * df['size']).sum() / s if s > 0 else np.nan
        
    lit_vwap = lit.groupby('minute').apply(calc_vwap)
    dark_vwap = dark.groupby('minute').apply(calc_vwap)
    
    df = pd.DataFrame({'lit_vwap': lit_vwap, 'dark_vwap': dark_vwap}).dropna()
    df['spread'] = df['dark_vwap'] - df['lit_vwap']
    df['abs_spread'] = df['spread'].abs()
    
    # Analyze by market session (UTC times)
    # Pre-market: before 13:30 UTC (09:30 ET)
    # Regular hours: 13:30 - 20:00 UTC (09:30 - 16:00 ET)
    # After hours: 20:00+ UTC (16:00+ ET)
    
    pm_mask = (df.index.hour < 13) | ((df.index.hour == 13) & (df.index.minute < 30))
    rh_mask = ~pm_mask & (df.index.hour < 20)
    ah_mask = df.index.hour >= 20
    
    pm = df[pm_mask]
    rh = df[rh_mask]
    ah = df[ah_mask]
    
    pm_max = round(float(pm['abs_spread'].max()), 2) if not pm.empty else 0
    pm_mean = round(float(pm['abs_spread'].mean()), 2) if not pm.empty else 0
    rh_max = round(float(rh['abs_spread'].max()), 2) if not rh.empty else 0
    rh_mean = round(float(rh['abs_spread'].mean()), 2) if not rh.empty else 0
    ah_max = round(float(ah['abs_spread'].max()), 2) if not ah.empty else 0
    ah_mean = round(float(ah['abs_spread'].mean()), 2) if not ah.empty else 0
    
    # Count dislocations by session
    pm_gt5 = int((pm['abs_spread'] > 5.0).sum()) if not pm.empty else 0
    rh_gt5 = int((rh['abs_spread'] > 5.0).sum()) if not rh.empty else 0
    pm_gt1 = int((pm['abs_spread'] > 1.0).sum()) if not pm.empty else 0
    rh_gt1 = int((rh['abs_spread'] > 1.0).sum()) if not rh.empty else 0
    
    print(f"\n  SESSION ANALYSIS:")
    print(f"    Pre-Market  | Max: ${pm_max:.2f} | Mean: ${pm_mean:.2f} | >$5: {pm_gt5} min | >$1: {pm_gt1} min | Minutes: {len(pm)}")
    print(f"    Regular Hrs | Max: ${rh_max:.2f} | Mean: ${rh_mean:.2f} | >$5: {rh_gt5} min | >$1: {rh_gt1} min | Minutes: {len(rh)}")
    print(f"    After Hours | Max: ${ah_max:.2f} | Mean: ${ah_mean:.2f} | Minutes: {len(ah)}")
    
    # Show worst regular-hours minutes
    if not rh.empty:
        worst_rh = rh.nlargest(5, 'abs_spread')
        if not worst_rh.empty:
            print(f"\n  Worst Regular-Hours Dislocations:")
            for idx, row in worst_rh.iterrows():
                ts_str = idx.strftime('%H:%M') if hasattr(idx, 'strftime') else str(idx)
                print(f"    {ts_str} UTC | Lit: ${row['lit_vwap']:.2f} | Dark: ${row['dark_vwap']:.2f} | Δ: ${row['abs_spread']:.2f}")
    
    res = {
        "pre_market": {"max_spread": pm_max, "mean_spread": pm_mean, "minutes_gt5": pm_gt5, "minutes_gt1": pm_gt1, "minutes_analyzed": len(pm)},
        "regular_hours": {"max_spread": rh_max, "mean_spread": rh_mean, "minutes_gt5": rh_gt5, "minutes_gt1": rh_gt1, "minutes_analyzed": len(rh)},
        "after_hours": {"max_spread": ah_max, "mean_spread": ah_mean, "minutes_analyzed": len(ah)},
    }
    
    if rh_gt5 == 0 and pm_gt5 > 0:
        verdict = f"Tape Fracture STRICTLY confined to pre-market. Pre-mkt max=${pm_max}, Reg hrs max=${rh_max}."
    elif rh_gt5 > 0:
        verdict = f"Tape Fracture BLEEDS into regular hours. Pre-mkt max=${pm_max}, Reg hrs max=${rh_max}."
    else:
        verdict = f"No severe fractures detected. Max spread=${max(pm_max, rh_max)}."
        
    print(f"\n  VERDICT: {verdict}")
    res["verdict"] = verdict
    return res

# ===================================================================
# T2: CROSS-DATE TRF CEILING (MAY 13-16, 2024)
# ===================================================================
def test_t2_crossdate_trf_ceiling():
    print("\n" + "=" * 60)
    print("T2: CROSS-DATE TRF CEILING (MAY 13-17, 2024)")
    print("=" * 60)
    
    dates = ["2024-05-13", "2024-05-14", "2024-05-15", "2024-05-16", "2024-05-17"]
    results = {}
    
    for d in dates:
        eq = load_equity_parquet('GME', d)
        if eq is None:
            print(f"  {d} | NO DATA")
            continue
        
        dark = eq[eq['exchange'].isin({4, 15})].copy()
        lit = eq[~eq['exchange'].isin({4, 15})].copy()
        
        # Pre-market specifically (before 13:30 UTC)
        pm_dark = dark[(dark['ts'].dt.hour < 13) | ((dark['ts'].dt.hour == 13) & (dark['ts'].dt.minute < 30))]
        pm_lit = lit[(lit['ts'].dt.hour < 13) | ((lit['ts'].dt.hour == 13) & (lit['ts'].dt.minute < 30))]
        
        # All-day dark
        all_max_dark = round(float(dark['price'].max()), 2) if not dark.empty else 0
        all_p99_dark = round(float(dark['price'].quantile(0.99)), 2) if not dark.empty else 0
        all_max_lit = round(float(lit['price'].max()), 2) if not lit.empty else 0
        
        # Pre-market dark
        pm_max_dark = round(float(pm_dark['price'].max()), 2) if not pm_dark.empty else 0
        pm_p99_dark = round(float(pm_dark['price'].quantile(0.99)), 2) if not pm_dark.empty else 0
        pm_max_lit = round(float(pm_lit['price'].max()), 2) if not pm_lit.empty else 0
        
        # Volume
        pm_dark_vol = int(pm_dark['size'].sum()) if not pm_dark.empty else 0
        
        results[d] = {
            "all_day_max_dark": all_max_dark,
            "all_day_p99_dark": all_p99_dark,
            "all_day_max_lit": all_max_lit,
            "pm_max_dark": pm_max_dark,
            "pm_p99_dark": pm_p99_dark,
            "pm_max_lit": pm_max_lit,
            "pm_dark_volume": pm_dark_vol,
        }
        
        is_opex = "(OpEx)" if d == "2024-05-17" else ""
        print(f"  {d} {is_opex:8s} | PM Dark Max: ${pm_max_dark:>7.2f} | PM Lit Max: ${pm_max_lit:>7.2f} | All-Day Dark Max: ${all_max_dark:>7.2f} | PM Dark Vol: {pm_dark_vol:>10,}")

    # Check if $33 ceiling appears on any non-OpEx day
    opex_max = results.get("2024-05-17", {}).get("pm_max_dark", 0)
    non_opex_max = max(results.get(d, {}).get("pm_max_dark", 0) for d in dates if d != "2024-05-17")
    
    if opex_max >= 33.0 and non_opex_max < 33.0:
        verdict = f"$33.00 ceiling is UNIQUE to OpEx Friday (May 17). Non-OpEx PM dark max: ${non_opex_max}."
    elif non_opex_max >= 33.0:
        verdict = f"$33.00 ceiling also appears on non-OpEx days (max: ${non_opex_max})."
    else:
        verdict = f"No $33 ceiling observed. OpEx dark max: ${opex_max}, Non-OpEx: ${non_opex_max}."
        
    print(f"\n  VERDICT: {verdict}")
    results["verdict"] = verdict
    return results

# ===================================================================
# T3: CONTINGENT FLAG AUDIT (GME vs SPY/AAPL)
# ===================================================================
def test_t3_contingent_flag_audit():
    print("\n" + "=" * 60)
    print("T3: CONTINGENT FLAG AUDIT (CODE 14/41/52/53 EVASION)")
    print("=" * 60)
    
    CONTINGENT_CODES = {14, 41, 52, 53}
    
    def audit_ticker(ticker, target_dates, label=""):
        total_off_market_trades = 0
        total_off_market_shares = 0
        missing_flag_trades = 0
        missing_flag_shares = 0
        has_flag_trades = 0
        dates_analyzed = 0
        
        for i, d in enumerate(target_dates):
            eq = load_equity_parquet(ticker, d)
            if eq is None or 'conditions' not in eq.columns: continue
            
            dark = eq[eq['exchange'].isin({4, 15})].copy()
            lit = eq[~eq['exchange'].isin({4, 15})].copy()
            if dark.empty or lit.empty: continue
            
            # Compute per-minute lit VWAP
            lit['minute'] = lit['ts'].dt.floor('1min')
            dark['minute'] = dark['ts'].dt.floor('1min')
            
            lit_vwap = lit.groupby('minute').apply(lambda x: (x['price'] * x['size']).sum() / max(1, x['size'].sum()))
            
            dark = dark.merge(lit_vwap.rename('lit_vwap'), left_on='minute', right_index=True, how='inner')
            
            if dark.empty: continue
            
            # Off-market: >2% away from lit VWAP
            dark['pct_from_lit'] = abs(dark['price'] - dark['lit_vwap']) / dark['lit_vwap']
            off_market = dark[dark['pct_from_lit'] > 0.02].copy()
            
            if off_market.empty: continue
            
            total_off_market_trades += len(off_market)
            total_off_market_shares += int(off_market['size'].sum())
            
            # Check for contingent flags
            has_flags = off_market['conditions'].apply(
                lambda c: isinstance(c, (list, np.ndarray)) and bool(CONTINGENT_CODES.intersection(set(c)))
            )
            has_flag_trades += int(has_flags.sum())
            missing = off_market[~has_flags]
            missing_flag_trades += len(missing)
            missing_flag_shares += int(missing['size'].sum())
            
            dates_analyzed += 1
            
            if (i+1) % 5 == 0:
                print(f"    {label} scanned {i+1}/{len(target_dates)} dates...")
        
        pct_missing_trades = round(missing_flag_trades / max(1, total_off_market_trades) * 100, 1)
        pct_missing_shares = round(missing_flag_shares / max(1, total_off_market_shares) * 100, 1)
        
        print(f"\n  {ticker:4s} RESULTS:")
        print(f"    Dates analyzed: {dates_analyzed}")
        print(f"    Off-market TRF trades (>2% spread): {total_off_market_trades:,}")
        print(f"    Off-market TRF shares: {total_off_market_shares:,}")
        print(f"    Trades WITH contingent flags: {has_flag_trades:,}")
        print(f"    Trades MISSING contingent flags: {missing_flag_trades:,} ({pct_missing_trades}%)")
        print(f"    Shares MISSING contingent flags: {missing_flag_shares:,} ({pct_missing_shares}%)")
        
        return {
            "dates_analyzed": dates_analyzed,
            "total_off_market_trades": total_off_market_trades,
            "total_off_market_shares": total_off_market_shares,
            "has_flag_trades": has_flag_trades,
            "missing_flag_trades": missing_flag_trades,
            "missing_flag_shares": missing_flag_shares,
            "pct_missing_trades": pct_missing_trades,
            "pct_missing_shares": pct_missing_shares,
        }

    # Use recent 20 dates for each ticker
    gme_dates = get_available_polygon_dates("GME")[-20:]
    spy_dates = get_available_polygon_dates("SPY")[-20:]
    aapl_dates = get_available_polygon_dates("AAPL")[-20:]
    
    print(f"\n  Auditing GME ({len(gme_dates)} dates)...")
    res_gme = audit_ticker("GME", gme_dates, "GME")
    
    print(f"\n  Auditing SPY ({len(spy_dates)} dates)...")
    res_spy = audit_ticker("SPY", spy_dates, "SPY")
    
    print(f"\n  Auditing AAPL ({len(aapl_dates)} dates)...")
    res_aapl = audit_ticker("AAPL", aapl_dates, "AAPL")
    
    baseline_pct = (res_spy['pct_missing_trades'] + res_aapl['pct_missing_trades']) / 2
    
    print(f"\n  COMPARISON:")
    print(f"    GME  missing flags: {res_gme['pct_missing_trades']}% of off-market trades")
    print(f"    SPY  missing flags: {res_spy['pct_missing_trades']}% of off-market trades")
    print(f"    AAPL missing flags: {res_aapl['pct_missing_trades']}% of off-market trades")
    print(f"    Baseline (SPY+AAPL avg): {baseline_pct:.1f}%")
    
    if res_gme['pct_missing_trades'] > baseline_pct + 20:
        verdict = f"GME shows SYSTEMATIC evasion ({res_gme['pct_missing_trades']}%) vs baseline ({baseline_pct:.1f}%). Δ = {res_gme['pct_missing_trades'] - baseline_pct:.1f}pp."
    elif res_gme['pct_missing_trades'] > 90 and baseline_pct > 90:
        verdict = f"Missing flags are SYSTEMIC infrastructure-wide ({res_gme['pct_missing_trades']}% GME, {baseline_pct:.1f}% baseline). Not GME-specific."
    else:
        verdict = f"GME: {res_gme['pct_missing_trades']}% vs baseline: {baseline_pct:.1f}%. Difference: {res_gme['pct_missing_trades'] - baseline_pct:.1f}pp."
        
    print(f"\n  VERDICT: {verdict}")
    return {"GME": res_gme, "SPY": res_spy, "AAPL": res_aapl, "baseline_pct": baseline_pct, "verdict": verdict}


# ===================================================================
# MAIN
# ===================================================================
def main():
    print("=" * 60)
    print("ROUND 10 TEST BATTERY — FINAL REGULATORY AUDIT")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    run_tests = set(sys.argv[1:]) if len(sys.argv) > 1 else {"T1", "T2", "T3"}
    
    out_path = RESULTS_DIR / "round10_test_results.json"
    
    if out_path.exists():
        with open(out_path, "r") as f:
            all_results = json.load(f)
        print(f"  Loaded {len(all_results)} existing results from prior run")
    else:
        all_results = {}

    if "T1" in run_tests:
        all_results["T1_fullday_fracture"] = test_t1_fullday_fracture()
    if "T2" in run_tests:
        all_results["T2_crossdate_trf"] = test_t2_crossdate_trf_ceiling()
    if "T3" in run_tests:
        all_results["T3_contingent_flag"] = test_t3_contingent_flag_audit()

    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n" + "=" * 60)
    print(f"COMPLETE — Results saved to {out_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
