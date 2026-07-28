#!/usr/bin/env python3
"""run_control.py — the easy-to-borrow positive control for the financing reading.

QUESTION: is the married-pair signature generic financing machinery whose PRICE
varies with each name's borrow stress, or is it something peculiar to the meme
names? If it is financing, then in easy-to-borrow names the same instrument must
price at ~0 borrow, while GME 2020 and AMC 2023 sit far above.

METHOD: verbatim from crossname_financing_2026-07-21/code/02_borrow.py (Hunt-13
conventions), so the numbers are directly comparable to the published ones:
  discounted put-call parity   C - P = e^{-rT}(F - K)
  implied borrow               b = r - ln(F/S)/T
  spot S                       same-day split-adjusted close from local bars
  frozen RF_BY_YEAR schedule   (no network pulls)
  reliability gate             tenor >= 30d, call >= $0.05, tick-err <= 5%/yr

DIVIDEND CAVEAT, stated because it decides which controls are usable: with a
dividend yield q, the parity residual returns b + q, not b. GME, AMC, TSLA, PLTR,
HOOD, BYND and U pay ~nothing, so their b is clean. NVDA (~0.03%) is effectively
clean. AAPL (~0.5%) and SPY (~1.3%) are biased UPWARD by roughly their yield,
which only makes them conservative controls: if they still print near zero, the
point stands harder.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]   # repo root, wherever it is cloned
CLIPS = REPO / "posts/claim_tests/migration_census_2026-07-21/data"
OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(parents=True, exist_ok=True)

RF_BY_YEAR = {2017: 0.010, 2018: 0.020, 2019: 0.022, 2020: 0.004, 2021: 0.0005,
              2022: 0.018, 2023: 0.050, 2024: 0.051, 2025: 0.043, 2026: 0.042}
ERAS = [("E0_pre_sneeze", "2012-06-01", "2020-12-31"), ("E1_sneeze", "2021-01-01", "2021-12-31"),
        ("E2_calm", "2022-01-01", "2023-12-31"), ("E3_kitty", "2024-01-01", "2024-12-31"),
        ("E4_pre_wipe", "2025-01-01", "2025-10-06"), ("E5_post_reset", "2025-10-08", "2026-06-26")]

# hand-labelled, for reporting only -- never used in any computation
BORROW_CLASS = {"GME": "hard", "AMC": "hard", "BBBY": "hard", "BYND": "hard",
                "CHWY": "moderate", "U": "moderate", "HOOD": "moderate", "PLTR": "moderate",
                "NVDA": "easy", "TSLA": "easy", "AAPL": "easy", "SPY": "easy"}
DIV_Q = {"SPY": 0.013, "AAPL": 0.005, "NVDA": 0.0003, "TSLA": 0.0, "GME": 0.0, "AMC": 0.0,
         "BBBY": 0.0, "BYND": 0.0, "CHWY": 0.0, "U": 0.0, "HOOD": 0.0, "PLTR": 0.0}

# THE LANDMINE. Local equity bars are SPLIT-ADJUSTED; hive strikes are AS-LISTED.
# For any event dated before a split, the two are in different units and ln(K/S)
# is garbage -- which silently produces implied borrows in the hundreds of percent
# rather than raising. 02_borrow.py dodged this by only ever running on names with
# no split inside their clip window (its docstring says so). Running it across
# GME's 2022-07-22 4:1 makes nonsense, so the adjustment has to be explicit.
# (effective_date, new_shares_per_old): 4.0 = 4-for-1 forward, 0.1 = 1-for-10 reverse
SPLITS = {
    "GME":  [("2022-07-22", 4.0)],
    "AMC":  [("2023-08-24", 0.1)],
    "NVDA": [("2021-07-20", 4.0), ("2024-06-10", 10.0)],
    "TSLA": [("2020-08-31", 5.0), ("2022-08-25", 3.0)],
    "AAPL": [("2020-08-31", 4.0)],
    "SPY": [], "PLTR": [], "HOOD": [], "BYND": [], "CHWY": [], "U": [], "BBBY": [],
}


def strike_factor(tkr, dates):
    """Multiplier putting AS-LISTED strikes into SPLIT-ADJUSTED units."""
    f = pd.Series(1.0, index=dates.index)
    for eff, ratio in SPLITS.get(tkr, []):
        f = f * np.where(dates < pd.Timestamp(eff), 1.0 / ratio, 1.0)
    return f


def era_of(d):
    for name, a, b in ERAS:
        if pd.Timestamp(a) <= d <= pd.Timestamp(b):
            return name
    return None


def events_for(tkr):
    """Identical aggregation + parity math to 02_borrow.py events_for()."""
    f = CLIPS / f"clips_{tkr}.csv"
    if not f.exists() or f.stat().st_size < 60:
        return pd.DataFrame()
    try:
        clips = pd.read_csv(f)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    if not len(clips):
        return pd.DataFrame()
    clips["date"] = pd.to_datetime(clips.date, format="%Y%m%d")
    clips["expiry"] = pd.to_datetime(clips["expiry"])
    ev = clips.groupby(["date", "expiry", "strike"], as_index=False).agg(
        clips_n=("size", "size"), total_contracts=("size", "sum"), max_clip=("size", "max"),
        cmp_vwap=("c_minus_p", lambda s: np.average(s, weights=clips.loc[s.index, "size"])),
        price_call_vwap=("price_call", lambda s: np.average(s, weights=clips.loc[s.index, "size"])),
        complex_share=("complex_pair", "mean"), min_dt_ms=("dt_ms", "max"),
    )
    ev["root"] = tkr
    ev["era"] = ev.date.map(era_of)
    # put strikes and the c-p residual into split-adjusted units before any parity math
    sf = strike_factor(tkr, ev.date)
    ev["strike_adj_factor"] = sf
    ev["strike"] = ev.strike * sf
    ev["cmp_vwap"] = ev.cmp_vwap * sf          # a price difference scales with the split too
    ev["tenor_yr"] = (ev.expiry - ev.date).dt.days / 365.25
    ev["r"] = ev.date.dt.year.map(RF_BY_YEAR)
    bars = REPO / f"data/_consolidated/equity_bars/{tkr}.parquet"
    if not bars.exists():
        return pd.DataFrame()
    spot = pd.read_parquet(bars)
    spot["date"] = pd.to_datetime(spot["date"])
    ev["S"] = ev.date.map(spot.set_index("date")["close"])
    ev = ev.dropna(subset=["S", "r", "tenor_yr"])
    ev = ev[ev.tenor_yr > 0]
    if not len(ev):
        return pd.DataFrame()
    ev["F"] = ev.strike + np.exp(ev.r * ev.tenor_yr) * ev.cmp_vwap
    ev = ev[ev.F > 0]
    ev["carry"] = np.log(ev.F / ev.S) / ev.tenor_yr
    ev["b_implied"] = ev.r - ev.carry
    ev["b_tick_err"] = np.exp(ev.r * ev.tenor_yr) * 0.01 / (ev.F * ev.tenor_yr)
    ev["reliable"] = (ev.tenor_yr >= 30 / 365.25) & (ev.price_call_vwap >= 0.05) & (ev.b_tick_err <= 0.05)
    ev["m_logKS"] = np.log(ev.strike / ev.S)
    ev["b_div_adj"] = ev.b_implied - DIV_Q.get(tkr, 0.0)
    ev["borrow_class"] = BORROW_CLASS.get(tkr, "?")
    return ev


def pct(x):
    return f"{100 * x:+.2f}%" if pd.notna(x) else "  n/a "


def main():
    frames = []
    for tkr in sorted(BORROW_CLASS):
        ev = events_for(tkr)
        if len(ev):
            frames.append(ev)
            print(f"  {tkr:5s} {len(ev):4d} events, {int(ev.reliable.sum()):4d} reliable")
    all_ev = pd.concat(frames, ignore_index=True)
    all_ev.to_csv(OUT / "control_events_all.csv", index=False)
    rel = all_ev[all_ev.reliable].copy()
    rel.to_csv(OUT / "control_events_reliable.csv", index=False)

    print("\n=== UNITS GATE: median |ln(K/S)| must be small, or strikes and spot disagree ===")
    bad = []
    for tkr, g in all_ev.groupby("root"):
        for era in g.era.dropna().unique():
            h = g[g.era == era]
            m = h.m_logKS.abs().median()
            flag = "  <-- UNITS MISMATCH" if m > 1.0 else ""
            if m > 1.0:
                bad.append((tkr, era, m))
            print(f"  {tkr:5s} {era:14s} n={len(h):4d}  median |ln(K/S)| = {m:5.2f}"
                  f"  adj x{h.strike_adj_factor.iloc[0]:g}{flag}")
    if bad:
        print(f"\n  !! {len(bad)} ticker-eras still mismatched; their rates are NOT usable")
    else:
        print("\n  all ticker-eras pass: strikes and spot are in the same units")

    print("\n=== implied borrow by name, reliable events only ===")
    print(f"  {'name':6s} {'class':9s} {'n':>4s}  {'median':>8s} {'p25':>8s} {'p75':>8s}  {'div-adj med':>12s}")
    rows = []
    for tkr, g in rel.groupby("root"):
        q = g.b_implied.quantile([.25, .5, .75])
        rows.append(dict(root=tkr, borrow_class=g.borrow_class.iloc[0], n=len(g),
                         med=q[.5], p25=q[.25], p75=q[.75], med_div_adj=g.b_div_adj.median()))
    rows.sort(key=lambda r: (r["borrow_class"], -r["med"]))
    for r in rows:
        print(f"  {r['root']:6s} {r['borrow_class']:9s} {r['n']:4d}  {pct(r['med']):>8s} "
              f"{pct(r['p25']):>8s} {pct(r['p75']):>8s}  {pct(r['med_div_adj']):>12s}")
    pd.DataFrame(rows).to_csv(OUT / "by_name.csv", index=False)

    print("\n=== the headline contrast ===")
    easy = rel[rel.borrow_class == "easy"]
    easy_clean = rel[rel.root.isin(["NVDA", "TSLA"])]
    hard = rel[rel.borrow_class == "hard"]
    print(f"  easy-to-borrow, all 4 names      n={len(easy):4d}  median {pct(easy.b_implied.median())}  "
          f"div-adj {pct(easy.b_div_adj.median())}")
    print(f"  easy, zero-dividend (NVDA+TSLA)  n={len(easy_clean):4d}  median {pct(easy_clean.b_implied.median())}")
    print(f"  hard-to-borrow names             n={len(hard):4d}  median {pct(hard.b_implied.median())}")

    print("\n=== GME by era vs the easy-to-borrow floor ===")
    gme = rel[rel.root == "GME"]
    for era, _, _ in ERAS:
        g = gme[gme.era == era]
        e = easy_clean[easy_clean.era == era]
        if len(g) or len(e):
            print(f"  {era:14s} GME n={len(g):3d} med {pct(g.b_implied.median()):>8s}   "
                  f"NVDA+TSLA n={len(e):3d} med {pct(e.b_implied.median()):>8s}")

    print("\n=== is the difference real, or just dispersion? Mann-Whitney on GME vs NVDA+TSLA ===")
    from scipy import stats
    if len(gme) >= 5 and len(easy_clean) >= 5:
        u, p = stats.mannwhitneyu(gme.b_implied.dropna(), easy_clean.b_implied.dropna(),
                                  alternative="greater")
        print(f"  GME > easy-to-borrow:  U={u:.0f}  p={p:.3g}  n={len(gme)}/{len(easy_clean)}")

    print("\n=== cross-strike consistency: is the rate flat in moneyness? ===")
    print("  (a loan's rate is a property of the loan, not the strike; slope should be ~0)")
    for tkr in ["GME", "NVDA", "TSLA", "SPY"]:
        g = rel[(rel.root == tkr)].dropna(subset=["m_logKS", "b_implied"])
        if len(g) >= 20:
            sl, ic, r_, p_, se = stats.linregress(g.m_logKS, g.b_implied)
            print(f"  {tkr:5s} n={len(g):4d}  slope={sl:+.4f} (se {se:.4f})  r={r_:+.3f}  p={p_:.3g}")

    summary = dict(n_events=int(len(all_ev)), n_reliable=int(len(rel)),
                   easy_median=float(easy.b_implied.median()),
                   easy_clean_median=float(easy_clean.b_implied.median()),
                   hard_median=float(hard.b_implied.median()),
                   by_name={r["root"]: dict(n=int(r["n"]), median=float(r["med"]),
                                            borrow_class=r["borrow_class"]) for r in rows})
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {OUT}/control_events_reliable.csv, by_name.csv, summary.json")


if __name__ == "__main__":
    main()
