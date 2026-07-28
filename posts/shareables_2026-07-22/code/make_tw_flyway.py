#!/usr/bin/env python3
"""tw_flyway.png: phone/Twitter redraw of the migration-census flyway map.

Only the four names where the rich-window clustering claim survived FDR
correction (AMC, GME, COIN, BYND, per overlay_results.csv q_bh < 0.05), one
strip each, shared 2018 -> mid-2026 axis. Same visual language as
migration_census_2026-07-21/code/06_figures.py fig1, redrawn at 1600x900.

Data (read-only): posts/claim_tests/migration_census_2026-07-21/data/
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "posts/claim_tests/migration_census_2026-07-21/data"
OUT = REPO / "posts/shareables_2026-07-22/figures"
OUT.mkdir(parents=True, exist_ok=True)

NAMES = ["AMC", "GME", "COIN", "BYND"]          # the four FDR survivors, in order
X0, X1 = pd.Timestamp("2018-01-01"), pd.Timestamp("2026-07-15")

C_RICH = "#d73027"   # red: ex-ante FTD-rich months (top within-name quintile)
C_CALM = "#4575b4"   # blue: calm months (bottom quintile)
C_MID = "#e9d8a6"    # tan: middle
C_STOP = "#111111"   # black spans: >=5k/side paired-dOI stopovers
C_RING = "#00e676"   # green rings: >=10k flags
C_RING_HALO = "#08331a"

plt.rcParams.update({"font.size": 14, "figure.facecolor": "white",
                     "axes.edgecolor": "#888888"})

stops = pd.read_csv(DATA / "stopovers_ge5000.csv", parse_dates=["start", "end"])

fig, axes = plt.subplots(
    4, 1, figsize=(16, 9), sharex=True,
    gridspec_kw=dict(hspace=0.30, left=0.075, right=0.985, top=0.855, bottom=0.085))

for ax, tkr in zip(axes, NAMES):
    lab = pd.read_csv(DATA / f"richness_{tkr}.csv", parse_dates=["date"])
    flags = pd.read_csv(DATA / f"oi_screen_{tkr}.csv", parse_dates=["date"])
    v = lab.dropna(subset=["ftd_ma"])
    if v.empty:
        raise RuntimeError(f"{tkr}: no FTD richness labels found; refusing to fabricate")
    # identical to 06_figures.py: within-name percentile of ftd_ma, monthly mean
    v = v.assign(pct=v.ftd_ma.rank(pct=True)).set_index("date")["pct"].resample("MS").mean()
    ax.fill_between(v.index, 0, 1, where=v >= 0.8, color=C_RICH, alpha=0.90, step="mid")
    ax.fill_between(v.index, 0, 1, where=(v >= 0.2) & (v < 0.8), color=C_MID,
                    alpha=0.70, step="mid")
    ax.fill_between(v.index, 0, 1, where=v < 0.2, color=C_CALM, alpha=0.80, step="mid")

    for _, r in stops[stops.root == tkr].iterrows():
        x0, x1 = r.start, r.end
        if (x1 - x0).days < 14:            # single-day stopovers stay visible at phone scale
            x1 = x0 + pd.Timedelta(days=14)
        ax.axvspan(x0, x1, color=C_STOP, alpha=0.92)

    big = sorted(set(flags.loc[flags.size_each_side >= 10000, "date"]))
    ax.scatter(big, [0.5] * len(big), marker="o", s=210, facecolors="none",
               edgecolors=C_RING_HALO, linewidths=3.4, zorder=5)
    ax.scatter(big, [0.5] * len(big), marker="o", s=150, facecolors="none",
               edgecolors=C_RING, linewidths=2.4, zorder=6)

    ax.set_ylabel(tkr, rotation=0, ha="right", va="center", fontsize=21, fontweight="bold")
    ax.set_yticks([])
    ax.set_ylim(0, 1)
    ax.set_xlim(X0, X1)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)

axes[-1].xaxis.set_major_locator(mdates.YearLocator())
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
axes[-1].tick_params(axis="x", labelsize=15.5)

fig.suptitle("The married financing trade lives where borrow is expensive",
             fontsize=22, fontweight="bold", y=0.972)
fig.text(0.5, 0.918,
         "red months = hard-to-borrow (top-quintile fails-to-deliver); "
         "black bars = big married-position stopovers; green rings = 10k+ lots",
         ha="center", fontsize=15, color="#333333")
fig.text(0.5, 0.882,
         "the four names (of 12 tested) where big paired positions cluster in "
         "hard-to-borrow windows, after FDR correction",
         ha="center", fontsize=13, color="#666666")

fig.savefig(OUT / "tw_flyway.png", dpi=100)
print("wrote", OUT / "tw_flyway.png")
