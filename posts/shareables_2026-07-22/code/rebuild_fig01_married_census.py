#!/usr/bin/env python3
"""rebuild_fig01_married_census.py — rebuild the married-pair census and fig01
from the raw trades hive, using the dual-schema fail-closed loader.

Why this exists: the original Hunt-13 census predated the loader fix for the
hive's expiry/expiration schema mix (2018-2019 files are `expiration`-only and
were silently skipped by an `expiry`-only reader). This script re-scans every
day on disk with the fixed loader, rebuilds the clip census and the event
clustering, prints a reconciliation summary, and redraws fig01 so the plot,
the clip count, and the event count all come from one post-fix run.

Matcher (from the registered watch spec): per day, per (expiration, strike,
size), call<->put nearest-in-time within 2,000 ms, floor 250 contracts per
side. An event clusters all clips sharing (day, expiration, strike); event
size = summed matched contracts per side, and max_clip = the largest single
matched print in that event (the two are very different for laddered days).

Two hive landmines this loader handles, both of which silently shrink a census:
  1. the expiry/expiration column-name mix (documented in the Hunt-13 ERRATA);
  2. the `right` VALUE mix — some files encode CALL/PUT, and at least one
     (2024-06-07) mixes CALL/PUT with C/P in the SAME file. A detector that
     tests `right == "CALL"` drops every C/P-encoded pair without erroring.
Both are handled here by normalizing the column name and the first letter.

Run from the repo root with the repo venv:
    .venv/bin/python posts/shareables_2026-07-22/code/rebuild_fig01_married_census.py

Outputs:
    data/married_census_rebuilt/combo_events_rebuilt.csv (+ the raw clips)
    posts/shareables_2026-07-22/figures/fig01_married_census_rebuilt.png
(The rebuilt figure is written alongside the old one for comparison; promote it
by renaming once the counts are accepted.)
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "public/the_parts_that_never_trade/tools"))
import hive_reader  # noqa: E402  (the packaged dual-schema fail-closed loader)

HIVE = Path.home() / "Documents/GitHub/power-tracks-research/data/raw/thetadata/trades/root=GME"
OUT_CSV = REPO / "data/married_census_rebuilt/combo_events_rebuilt.csv"
OUT_FIG = REPO / "posts/shareables_2026-07-22/figures/fig01_married_census_rebuilt.png"

FLOOR = 250          # min matched contracts per side
WINDOW_MS = 2000     # call<->put max separation
FAR_DAYS = 183       # far-dated threshold (T > 6m)
COLS = ["expiration", "expiry", "strike", "right", "timestamp", "size", "exchange"]

ERAS = [  # (label, start, end, color)
    ("E0\npre\nsneeze", "2018-01-01", "2021-01-10", "0.85"),
    ("E1\nsneeze", "2021-01-11", "2021-12-31", "mistyrose"),
    ("E2\ncalm", "2022-01-01", "2023-12-31", "lightsteelblue"),
    ("E3\nkitty", "2024-01-01", "2024-12-31", "navajowhite"),
    ("E4\npre\nwipe", "2025-01-01", "2025-10-07", "thistle"),
    ("E5\npost\nreset", "2025-10-08", "2026-12-31", "palegreen"),
]


def ts_to_ms(series: pd.Series) -> np.ndarray:
    """Normalize the hive timestamp column to milliseconds (any format)."""
    if not pd.api.types.is_numeric_dtype(series):
        dt = pd.to_datetime(series, errors="coerce")
        return dt.astype("int64").to_numpy() / 1e6
    if np.issubdtype(series.dtype, np.datetime64):
        return series.astype("int64").to_numpy() / 1e6
    vals = series.to_numpy(dtype="float64")
    m = np.nanmax(vals) if len(vals) else 0
    if m > 1e17:   # ns epoch
        return vals / 1e6
    if m > 1e14:   # us epoch
        return vals / 1e3
    return vals    # ms epoch or ms-of-day; either works for intraday deltas


def match_day(df: pd.DataFrame, ymd: str, floor: int = FLOOR,
              window: float = WINDOW_MS) -> list[dict]:
    df = df[df["size"] >= floor]
    if df.empty:
        return []
    df = df.copy()
    df["ms"] = ts_to_ms(df["timestamp"])
    right = df["right"].astype(str).str.upper().str[0]
    clips = []
    for (exp, strike, size), g in df.groupby(["expiration", "strike", "size"]):
        r = right.loc[g.index]
        calls = g[r == "C"].sort_values("ms")
        puts = g[r == "P"].sort_values("ms")
        if calls.empty or puts.empty:
            continue
        used = set()
        for _, c in calls.iterrows():
            cand = puts[~puts.index.isin(used)]
            if cand.empty:
                break
            dt = (cand["ms"] - c["ms"]).abs()
            j = dt.idxmin()
            if dt.loc[j] <= window:
                used.add(j)
                clips.append(dict(
                    date=ymd, expiration=str(exp), strike=float(strike),
                    size=int(size), dt_ms=float(dt.loc[j]),
                    exch_c=str(c["exchange"]), exch_p=str(cand.loc[j, "exchange"]),
                    same_ms=bool(dt.loc[j] < 1.0)))
    return clips


def main() -> None:
    days = hive_reader.list_hive_days("GME")
    print(f"[scan] {len(days)} hive days on disk, {days[0]} -> {days[-1]}", flush=True)
    all_clips, relaxed_clips, failed, days_read = [], [], [], 0
    for i, ymd in enumerate(days):
        try:
            df = hive_reader.read_hive_day("GME", ymd, columns=COLS)
        except Exception as e:  # noqa: BLE001
            failed.append((ymd, repr(e)))
            continue
        if df is None or df.empty:
            continue
        days_read += 1
        all_clips.extend(match_day(df, ymd))
        relaxed_clips.extend(match_day(df, ymd, floor=100, window=5000))
        if (i + 1) % 250 == 0:
            print(f"[scan] {i+1}/{len(days)} days, clips so far: {len(all_clips)}", flush=True)
    print(f"\n[coverage] days on disk: {len(days)}; days read: {days_read}; "
          f"unreadable: {len(failed)}", flush=True)
    if failed:
        print(f"[FAIL-CLOSED WARNING] unreadable days, e.g. {failed[:3]}", flush=True)
        raise SystemExit("coverage assertion failed — do not trust this census")

    clips = pd.DataFrame(all_clips)
    if clips.empty:
        print("NO CLIPS FOUND — check hive path and matcher.")
        return
    # strike scaling (thetadata often stores strike*1000)
    if clips["strike"].median() > 5000:
        clips["strike"] = clips["strike"] / 1000.0

    # Normalize the expiration format before grouping: the hive stores it as
    # ISO ("2019-07-19") in some files and YYYYMMDD ("20240614") in others, so
    # an un-normalized groupby splits one contract into two lines.
    # Two explicit passes: pandas infers a single format from the first value,
    # so a mixed column silently coerces the minority format to NaT.
    _iso = pd.to_datetime(clips["expiration"], errors="coerce", format="%Y-%m-%d")
    _compact = pd.to_datetime(clips["expiration"], errors="coerce", format="%Y%m%d")
    _exp = _iso.fillna(_compact)
    if _exp.isna().any():
        bad = clips.loc[_exp.isna(), "expiration"].unique()[:5]
        raise SystemExit(f"unparseable expiration values, refusing to guess: {bad}")
    clips["expiration"] = _exp.dt.strftime("%Y-%m-%d")
    ev = (clips.groupby(["date", "expiration", "strike"], as_index=False)
          .agg(size=("size", "sum"), max_clip=("size", "max"),
               clips=("size", "count"),
               dt_ms=("dt_ms", "max"), same_ms=("same_ms", "all")))
    ev["date_dt"] = pd.to_datetime(ev["date"], format="%Y%m%d")
    ev["exp_dt"] = pd.to_datetime(ev["expiration"], errors="coerce")
    ev["far"] = (ev["exp_dt"] - ev["date_dt"]).dt.days > FAR_DAYS

    print("\n================ RECONCILIATION ================")
    print(f"clips (<=2s window):        {len(clips)}")
    print(f"clips strictly same-ms:     {int(clips['same_ms'].sum())}")
    print(f"events (day+expiry+strike): {len(ev)}")
    print(f"events all-same-ms:         {int(ev['same_ms'].sum())}")
    print(f"earliest event:             {ev['date'].min()}")
    print("events by year:")
    print(ev.groupby(ev["date_dt"].dt.year).size().to_string())
    print("largest events (size = summed matched contracts per side):")
    print(ev.nlargest(6, "size")[["date", "expiration", "strike", "size",
                                  "max_clip", "clips"]].to_string(index=False))
    print("\nlargest SINGLE married clips (one print per side):")
    print(clips.nlargest(6, "size")[["date", "expiration", "strike", "size",
                                     "dt_ms"]].to_string(index=False))
    rel = pd.DataFrame(relaxed_clips)
    extra_window = len(rel[(rel["dt_ms"] > WINDOW_MS) & (rel["size"] >= FLOOR)]) if not rel.empty else 0
    extra_floor = len(rel[rel["size"] < FLOOR]) if not rel.empty else 0
    print("---------------- COMPLETENESS AUDIT ----------------")
    print(f"pairs just outside the 2s window (2-5s, size>=250): {extra_window}")
    print(f"pairs under the floor (size 100-249, <=5s):         {extra_floor}")
    print("(large counts here would mean the thresholds are doing the hiding;")
    print(" small counts mean the census boundary is not load-bearing)")
    print("=================================================\n", flush=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    clips.to_csv(OUT_CSV.with_name("combo_clips_rebuilt.csv"), index=False)
    ev.drop(columns=["date_dt", "exp_dt"]).to_csv(OUT_CSV, index=False)
    print(f"[write] {OUT_CSV}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ERA_DOT = {"E0": "0.4", "E1": "tab:red", "E2": "tab:blue",
               "E3": "tab:orange", "E4": "tab:purple", "E5": "tab:green"}

    def era_of(d):
        for (label, s, e, _c) in ERAS:
            if pd.Timestamp(s) <= d <= pd.Timestamp(e):
                return label.split("\n")[0]
        return "E5"

    ev["era"] = ev["date_dt"].map(era_of)
    ev["dotcolor"] = ev["era"].map(ERA_DOT)
    near = ev[~ev["far"]]
    far = ev[ev["far"]]

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12.8, 10.2))

    # ---- panel A: the census, dots colored by era ----
    for label, s, e, color in ERAS:
        ax.axvspan(pd.Timestamp(s), pd.Timestamp(e), color=color, alpha=0.35, zorder=0)
    ax.scatter(near["date_dt"], near["size"], s=20, alpha=0.55,
               c=near["dotcolor"], label="near-dated (T \u2264 6m)")
    ax.scatter(far["date_dt"], far["size"], s=60, facecolors="none",
               edgecolors="black", linewidths=1.5, label="far-dated (T > 6m)")
    fartop = far.nlargest(2, "size")
    giants = ev.nlargest(2, "size")
    giants = giants[~giants.index.isin(fartop.index)]
    for k, (_, r) in enumerate(fartop.iterrows()):
        ax.annotate(f"K{r['strike']:.0f} {r['exp_dt']:%b-%y}\n{r['size']:,.0f}\u00d72\n"
                    f"({int(r['clips'])} clip{'s' if r['clips'] > 1 else ''},"
                    f" max {r['max_clip']:,.0f})",
                    (r["date_dt"], r["size"]), textcoords="offset points",
                    xytext=(-120, -18) if k == 0 else (28, -62), fontsize=8.5,
                    arrowprops=dict(arrowstyle="-", lw=0.8, color="0.4"))
    for k, (_, r) in enumerate(giants.iterrows()):
        ax.annotate(f"K{r['strike']:.0f} {r['exp_dt']:%b-%y}\n{r['size']:,.0f}\u00d72\n"
                    f"({int(r['clips'])} clip{'s' if r['clips'] > 1 else ''},"
                    f" max {r['max_clip']:,.0f})",
                    (r["date_dt"], r["size"]), textcoords="offset points",
                    xytext=(30, -10 - 40 * k), fontsize=8.5,
                    arrowprops=dict(arrowstyle="-", lw=0.8, color="0.4"))
    for label, s, e, color in ERAS:
        mid = pd.Timestamp(s) + (pd.Timestamp(e) - pd.Timestamp(s)) / 2
        ax.text(mid, 0.03, label, ha="center", va="bottom", fontsize=8,
                color="0.45", transform=ax.get_xaxis_transform())
    ax.legend(loc="upper left", fontsize=9)
    ax.set_yscale("log")
    ax.set_ylabel("married contracts per event (each side, log)")
    ax.set_title(f"A) Married parity-combo census, GME {ev['date'].min()[:4]}-"
                 f"{ev['date'].min()[4:6]} \u2192 {ev['date'].max()[:4]}-{ev['date'].max()[4:6]} "
                 f"({len(clips)} clips \u2192 {len(ev)} events; C+P same size, \u22642s apart; "
                 f"loader-fix rebuild)", fontsize=11)

    # ---- panel B: the same events, drawn out to their expirations ----
    ok = ev.dropna(subset=["exp_dt"])
    for _, r in ok.iterrows():
        ax2.plot([r["date_dt"], r["exp_dt"]], [r["size"], r["size"]],
                 color=r["dotcolor"], alpha=0.45,
                 lw=2.6 if r["far"] else 1.1, zorder=3 if r["far"] else 2)
        ax2.scatter([r["date_dt"]], [r["size"]], s=10, color=r["dotcolor"],
                    alpha=0.8, zorder=4)
    for k, (_, r) in enumerate(fartop.iterrows()):
        ax2.annotate(f"K{r['strike']:.0f} \u2192 {r['exp_dt']:%b-%y}",
                     (r["exp_dt"], r["size"]), textcoords="offset points",
                     xytext=(6, 8 - 20 * k), fontsize=8.5, color="0.2")
    ax2.set_yscale("log")
    ax2.set_ylabel("married contracts per event (each side, log)")
    ax2.set_title("B) The same events, drawn from print date to expiration "
                  "(thick = far-dated): the new units are the only big mass "
                  "parked years out", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT_FIG, dpi=150)
    print(f"[write] {OUT_FIG}")


if __name__ == "__main__":
    main()
