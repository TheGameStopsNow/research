#!/usr/bin/env python3
"""Twitter-optimized (1600x900) render of the $50 reincarnation ladder.

Source data: posts/claim_tests/strike50_reincarnation_2026-07-22/data/ (frozen
hunt package, untouched). Output:
posts/shareables_2026-07-22/figures/tw_ladder.png
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(sys.executable).parent.parent.parent))
from daimon_runtime import setup_plot
setup_plot()
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "posts/claim_tests/strike50_reincarnation_2026-07-22/data"
OUT = REPO / "posts/shareables_2026-07-22/figures/tw_ladder.png"

ERA_SPANS = {"E1": ("2021-01-01", "2021-12-31"), "E2": ("2022-01-01", "2023-12-31"),
             "E3": ("2024-01-01", "2024-12-31"), "E4": ("2025-01-01", "2025-10-06"),
             "E5": ("2025-10-08", "2026-06-26")}
ERA_COLORS = {"E1": "#d62728", "E2": "#ff7f0e", "E3": "#2ca02c",
              "E4": "#1f77b4", "E5": "#9467bd"}
CLS_COLORS = {"REINCARNATE": "#1f77b4", "ROLL": "#d62728", "DIE_NO_REBUILD": "#7f7f7f",
              "PANEL_EDGE": "#bcbd22", "UNCLASSIFIABLE_WINDOW": "#cccccc", "MASKED": "#dddddd"}


def main():
    tot = pd.read_csv(DATA / "lineage_total_daily.csv", parse_dates=["date"])
    ll = pd.read_csv(DATA / "fig1_lifelines.csv", parse_dates=["date"])
    cc = pd.read_csv(DATA / "cohort_census.csv")
    cc = cc[cc.occupied]
    cls_map = pd.read_csv(DATA / "fig2_series.csv").set_index("expiry").classification.to_dict()

    fig, (a1, a2) = plt.subplots(2, 1, figsize=(12.8, 7.2), sharex=True,
                                 gridspec_kw={"height_ratios": [1, 1.5], "hspace": 0.10})
    fig.subplots_adjust(left=0.075, right=0.985, top=0.80, bottom=0.09)
    fig.suptitle("One wall, 173 lives: the $50 call strike has never been empty since January 2021",
                 fontsize=15.5, weight="bold", x=0.075, ha="left", y=0.945)
    fig.text(0.075, 0.868,
             "each colored line is one expiry cohort at the $50 strike; it dies on schedule and a new one starts building days later",
             fontsize=11, color="#444444", ha="left")

    a1.plot(tot.date, tot.total_oi_x4_pre.clip(0.5), color="#333333", lw=1.2)
    a1.set_yscale("log")
    a1.set_ylabel("total open interest\n(split-adjusted)", fontsize=9.5)
    a1.tick_params(labelsize=9)

    for exp, g in ll.groupby("expiration"):
        era = next((e for e, (a, b) in ERA_SPANS.items() if a <= exp <= b), "E2")
        peak = g.open_interest.max()
        a2.plot(g.date, [pd.Timestamp(exp)] * len(g), lw=0.6 + 1.8 * np.log10(max(peak, 10) / 3),
                color=ERA_COLORS[era], alpha=0.75, solid_capstyle="round")
    d = cc[cc.dies_in_panel]
    a2.scatter(pd.to_datetime(d.death_date), pd.to_datetime(d.expiration),
               s=6 + d.dying_oi.clip(0, 40000) / 1300,
               c=[CLS_COLORS.get(cls_map.get(e, "MASKED"), "#888888") for e in d.expiration],
               zorder=5, edgecolors="none")
    for cls, lab in [("REINCARNATE", "died, then rebuilt from fresh prints (35 at scale)"),
                     ("ROLL", "rolled to the next expiry (exactly 1)"),
                     ("DIE_NO_REBUILD", "died, no rebuild"), ("PANEL_EDGE", "still alive")]:
        a2.scatter([], [], s=34, color=CLS_COLORS[cls], label=lab)
    a2.legend(loc="upper left", fontsize=9, framealpha=0.92)
    a2.set_ylabel("expiry date", fontsize=9.5)
    a2.set_xlabel("date (daily open-interest snapshots)", fontsize=9.5)
    a2.tick_params(labelsize=9)
    for ev, lab in [("2022-07-22", "4:1 split"), ("2025-10-07", "warrant reset")]:
        for a in (a1, a2):
            a.axvline(pd.Timestamp(ev), color="k", ls=":", lw=1, alpha=0.6)
        a2.annotate(lab, (pd.Timestamp(ev), 0.02), xycoords=("data", "axes fraction"),
                    fontsize=8.5, rotation=90, va="bottom", ha="right", color="k")

    fig.savefig(OUT, dpi=125)  # 12.8x7.2 in * 125 dpi = 1600x900
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
