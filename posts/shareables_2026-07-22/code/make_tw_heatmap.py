#!/usr/bin/env python3
"""tw_heatmap.png: phone/Twitter redraw of the rate-census predictive heatmap.

Single 21-day horizon panel, redrawn large at 1600x900. Cell values and FDR
stars are reused verbatim from rate_census_2026-07-22/data/results.json via the
same lookup as code/make_figures.py (candidate keys T@21d then T@4wk; feasible
cells only; stars from r["fdr_hits"]). Nothing is recomputed.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

REPO = Path(__file__).resolve().parents[3]
RES = REPO / "posts/claim_tests/rate_census_2026-07-22/data/results.json"
OUT = REPO / "posts/shareables_2026-07-22/figures"
OUT.mkdir(parents=True, exist_ok=True)

r = json.load(open(RES))
rates, hits = r["rates"], r["fdr_hits"]
keys = list(rates.keys())
TGTS = ["T1_spot_ret", "T2_dIV", "T3_dOI", "T4_dVol"]

G = np.full((len(keys), len(TGTS)), np.nan)
S = np.zeros_like(G, dtype=bool)
for i, k in enumerate(keys):
    for j, t in enumerate(TGTS):
        for cand in (f"{t}@21d", f"{t}@4wk"):      # identical lookup to make_figures.py
            c = rates[k]["cells"].get(cand)
            if c and c.get("feasible"):
                G[i, j] = c["rho"]
                S[i, j] = bool(hits.get(f"{k}|{cand}", False))
                break

row_lab = [k.split("_", 1)[1].replace("_", " ") for k in keys]   # strip R#_ prefix
row_lab = [lab + (" (off-tape)" if not rates[k]["visible"] else "")
           for lab, k in zip(row_lab, keys)]
col_lab = ["spot\nreturn", "implied vol\nchange", "open interest\nchange", "option volume\nchange"]

cmap = matplotlib.colormaps["RdBu_r"].copy()
cmap.set_bad("#dddddd")

plt.rcParams.update({"font.size": 14, "figure.facecolor": "white"})
fig, ax = plt.subplots(figsize=(16, 9))
fig.subplots_adjust(left=0.16, right=0.90, top=0.83, bottom=0.17)

im = ax.imshow(G, cmap=cmap, vmin=-0.2, vmax=0.2, aspect="auto")
for i in range(G.shape[0]):
    for j in range(G.shape[1]):
        if np.isnan(G[i, j]):
            ax.text(j, i, "n/a", ha="center", va="center", fontsize=13.5, color="#777777")
        else:
            dark = abs(G[i, j]) >= 0.12
            ax.text(j, i, f"{G[i, j]:+.2f}" + ("*" if S[i, j] else ""),
                    ha="center", va="center", fontsize=17,
                    fontweight="bold" if S[i, j] else "normal",
                    color="white" if dark else "#111111")

# outline the R2 row: the one visible rate whose slope survived all nulls + FDR
ax.add_patch(Rectangle((-0.5, 0.5), 4, 1, fill=False, edgecolor="#111111",
                       lw=2.8, clip_on=False))
# and box each surviving cell individually: the trailing asterisk alone reads faintly
for i in range(G.shape[0]):
    for j in range(G.shape[1]):
        if S[i, j]:
            ax.add_patch(Rectangle((j - 0.46, i - 0.46), 0.92, 0.92, fill=False,
                                   edgecolor="#111111", lw=2.2))

ax.set_xticks(range(len(TGTS)))
ax.set_xticklabels(col_lab, fontsize=16.5)
ax.set_yticks(range(len(keys)))
ax.set_yticklabels(row_lab, fontsize=15.5)
ax.tick_params(length=0)
cb = fig.colorbar(im, ax=ax, shrink=0.72, pad=0.03)
cb.set_label("Spearman rho", fontsize=14.5)
cb.ax.tick_params(labelsize=13)

fig.suptitle("The one visible slope: heavy OI-writing days predict falling implied vol",
             fontsize=19.5, fontweight="bold", y=0.955)
fig.text(0.5, 0.895,
         "Spearman rho, each rate vs forward 21-day targets; boxed + starred = survives shuffle + clock nulls + FDR",
         ha="center", fontsize=14.5, color="#333333")
fig.text(0.5, 0.045,
         "The census exactly as frozen. Velocity's two option-volume cells later failed a "
         "mean-reversion control and are retired; the implied-vol cells survive.",
         ha="center", fontsize=13, color="#444444", style="italic")

fig.savefig(OUT / "tw_heatmap.png", dpi=100)
print("wrote", OUT / "tw_heatmap.png")
