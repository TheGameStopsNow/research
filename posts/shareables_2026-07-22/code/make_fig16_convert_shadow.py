#!/usr/bin/env python3
"""
make_fig16_convert_shadow.py — article figure for "The Convert Shadow" section.

Three panels: (A) the 2027-12-17 ladder seeded on 2025-03-28 vs the two
conversion prices; (B) the $5 put and $32 call OI across both convert
windows; (C) GME close on the same calendar (pricing-day selloffs).

Reads the verified outputs of posts/claim_tests/convert_cluster_typing_2026-07-24
plus the strike5p biography series and the daily price file. No network.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
HUNT = REPO / "posts/claim_tests/convert_cluster_typing_2026-07-24"
BIO = REPO / "posts/claim_tests/strike5p_biography_2026-07-24"
PX_F = REPO / "data/ftd/gme_daily_price.csv"
OUT = REPO / "posts/shareables_2026-07-22/figures/fig16_convert_shadow.png"

C1 = dict(propose="2025-03-26", price="2025-03-27", close="2025-04-01", conv_px=29.85)
C2 = dict(propose="2025-06-11", price="2025-06-12", close="2025-06-17", conv_px=28.91)

wm = pd.read_csv(HUNT / "data/cluster_wm_lines.csv")
oi = pd.read_csv(BIO / "data/oi_series_both_lines.csv", parse_dates=["date"])
px = pd.read_csv(PX_F).rename(columns={"gme_close": "close"})
px["date"] = pd.to_datetime(px["date"])

fig = plt.figure(figsize=(14, 9))
gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.45], hspace=0.32, wspace=0.24)
ax_geo = fig.add_subplot(gs[:, 0])
ax_oi = fig.add_subplot(gs[0, 1])
ax_px = fig.add_subplot(gs[1, 1], sharex=ax_oi)

# --- A) geography
for right, color, marker in [("CALL", "#1f77b4", "o"), ("PUT", "#d62728", "s")]:
    sub = wm[wm["right"] == right]
    ax_geo.scatter(sub["strike_adj"], sub["first_oi"].clip(lower=1),
                   s=40 + 12 * sub["first_oi"].clip(lower=1) ** 0.5,
                   c=color, marker=marker, alpha=0.75, edgecolor="k", linewidth=0.4)
ax_geo.set_yscale("log")
ax_geo.axvline(C1["conv_px"], color="green", ls="--", lw=1.2)
ax_geo.axvline(C2["conv_px"], color="green", ls=":", lw=1.2)
ytop = wm["first_oi"].max() * 2.2
ax_geo.set_ylim(top=ytop * 1.6)
ax_geo.text(C1["conv_px"] + 0.7, ytop * 0.9, "note 1\nconverts at\n\\$29.85",
            rotation=0, color="green", fontsize=8, va="top")
ax_geo.text(C2["conv_px"] - 1.9, ytop * 0.35, "note 2\nconverts at\n\\$28.91",
            rotation=0, color="green", fontsize=8, va="top")
ax_geo.annotate("\\$5 put: 31,721 contracts\non day one (93% of the mass)",
                xy=(5.0, 31721), xytext=(11.5, 9000),
                arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8.5)
ax_geo.set_xlabel("strike ($) — December 17, 2027 expiry, listed in one day, 994 days out")
ax_geo.set_ylabel("contracts already booked (log)")
ax_geo.set_title("A) A whole new expiration, born on the first pricing day")
proxy = [Line2D([], [], marker="o", ls="", color="#1f77b4", markeredgecolor="k",
                markersize=8, label="call lines"),
         Line2D([], [], marker="s", ls="", color="#d62728", markeredgecolor="k",
                markersize=8, label="put lines")]
ax_geo.legend(handles=proxy, loc="upper right", fontsize=8)
ax_geo.grid(alpha=0.25)

# --- B) OI across windows
sub = oi[(oi["date"] >= "2025-03-15") & (oi["date"] <= "2025-07-15")]
ax_oi.plot(sub["date"], sub["oi_5p"], color="#d62728", lw=1.6)
ax_oi.set_ylabel("$5 put open interest", color="#d62728")
ax_oi.tick_params(axis="y", labelcolor="#d62728")
ax_oi.set_ylim(28000, 76000)
ax2 = ax_oi.twinx()
ax2.plot(sub["date"], sub["oi_32c"], color="#1f77b4", lw=1.4, ls="--")
ax2.set_ylabel("$32 call open interest", color="#1f77b4")
ax2.tick_params(axis="y", labelcolor="#1f77b4")
events = [C1["propose"], C1["price"], C1["close"], C2["propose"], C2["price"], C2["close"]]
for d in events:
    ax_oi.axvline(pd.Timestamp(d), color="gray", ls=":", lw=1.0)
for d, lab in [(C1["price"], "note 1 priced\nMar 27"), (C2["price"], "note 2 priced\nJun 12")]:
    ax_oi.annotate(lab, xy=(pd.Timestamp(d), 75000), xytext=(3, -2),
                   textcoords="offset points", fontsize=8, color="dimgray",
                   ha="left", va="top")
ax_oi.set_title("B) Both lines grow on the pricing and closing days (red = \\$5 put, blue = \\$32 call)")
ax_oi.grid(alpha=0.25)
plt.setp(ax_oi.get_xticklabels(), visible=False)

# --- C) equity tape
psub = px[(px["date"] >= "2025-03-15") & (px["date"] <= "2025-07-15")]
ax_px.plot(psub["date"], psub["close"], color="black", lw=1.4)
for d in events:
    ax_px.axvline(pd.Timestamp(d), color="gray", ls=":", lw=1.0)
c1p = float(px.loc[px["date"] == C1["price"], "close"].iloc[0])
c2p = float(px.loc[px["date"] == C2["price"], "close"].iloc[0])
ax_px.annotate("pricing day: -22.1%", xy=(pd.Timestamp(C1["price"]), c1p),
               xytext=(16, 58), textcoords="offset points", fontsize=8.5,
               arrowprops=dict(arrowstyle="->", lw=0.8))
ax_px.annotate("pricing day: -22.5%", xy=(pd.Timestamp(C2["price"]), c2p),
               xytext=(-112, 30), textcoords="offset points", fontsize=8.5,
               arrowprops=dict(arrowstyle="->", lw=0.8))
ax_px.set_ylabel("GME close ($)")
ax_px.set_title("C) The stock on the same days: the convert-arb hedge flow, visible twice")
ax_px.grid(alpha=0.25)
ax_px.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

fig.savefig(OUT, dpi=160, bbox_inches="tight")
print("wrote", OUT)
