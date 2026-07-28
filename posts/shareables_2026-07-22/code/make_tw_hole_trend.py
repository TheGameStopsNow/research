#!/usr/bin/env python3
"""Twitter-optimized (1600x900) era-by-era round-strike OI ladder.

Answers the "it's just the 30-35-40 trend" objection to the $45 hole:
pre-2021 the same trend explains $45 exactly; post-reset $45 sits 3.6x
below its own trend extrapolation while $50 sits 15.7x above it.

Source data: posts/claim_tests/strike45_hole_2026-07-21/data/strike_ladder_era.csv
(frozen hunt package, untouched). Output:
posts/shareables_2026-07-22/figures/tw_hole_trend.png
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
DATA = REPO / "posts/claim_tests/strike45_hole_2026-07-21/data/strike_ladder_era.csv"
OUT = REPO / "posts/shareables_2026-07-22/figures/tw_hole_trend.png"

ROUNDS = [25, 30, 35, 40, 45, 50]
ERAS = ["E0_pre_sneeze", "E1_sneeze", "E2_calm", "E3_kitty", "E4_pre_wipe", "E5_post_reset"]
LABEL = {
    "E0_pre_sneeze": "2020, before the squeeze",
    "E1_sneeze": "2021 squeeze",
    "E2_calm": "2022-23 calm",
    "E3_kitty": "2024 Kitty return",
    "E4_pre_wipe": "2025, pre-reset",
    "E5_post_reset": "post-reset (Oct 2025 on)",
}
MUTED = {"E1_sneeze": "#c9a227", "E2_calm": "#8fb8d8", "E3_kitty": "#a8c69f", "E4_pre_wipe": "#b8b8d0"}


def main():
    df = pd.read_csv(DATA)
    pv = (df[df["K"].isin(ROUNDS)]
          .pivot(index="era", columns="K", values="mean_daily_oi")
          .reindex(ERAS))

    # post-reset trend: log-linear fit on 30/35/40, extended to 45 and 50
    e5 = pv.loc["E5_post_reset"]
    xfit = np.array([30.0, 35.0, 40.0])
    b, a = np.polyfit(xfit, np.log(e5[xfit].values), 1)
    xt = np.linspace(30, 50, 60)
    trend = np.exp(b * xt + a)
    pred45, pred50 = float(np.exp(b * 45 + a)), float(np.exp(b * 50 + a))

    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.subplots_adjust(left=0.075, right=0.975, top=0.775, bottom=0.10)
    fig.suptitle("The \\$45 hole is not the ladder's trend: before 2021 the same trend explained \\$45 exactly",
                 fontsize=15, weight="bold", x=0.075, ha="left", y=0.945)
    fig.text(0.075, 0.875,
             "mean daily open interest at the round-number strikes, by era (log scale); "
             "the dashed line extends the post-reset 30-35-40 downtrend to where \\$45 and \\$50 should sit",
             fontsize=10.5, color="#444444", ha="left")

    for era in ERAS:
        row = pv.loc[era]
        if era in MUTED:
            ax.plot(row.index, row.values, color=MUTED[era], lw=1.4, alpha=0.85,
                    marker="o", ms=3.5, label=LABEL[era], zorder=3)
        elif era == "E0_pre_sneeze":
            ax.plot(row.index, row.values, color="#333333", lw=2.2, marker="o", ms=5,
                    label=LABEL[era], zorder=5)
        else:
            ax.plot(row.index, row.values, color="#d62728", lw=2.6, marker="o", ms=6,
                    label=LABEL[era], zorder=6)

    ax.plot(xt, trend, color="#d62728", lw=1.4, ls=(0, (5, 4)), alpha=0.75, zorder=4)
    ax.scatter([45, 50], [pred45, pred50], facecolors="white", edgecolors="#d62728",
               s=52, lw=1.6, zorder=7)

    # callout: $45 sits below its own trend
    ax.annotate("$45: 2,569 resting\nits own trend predicts ~9,300\n(3.6x below trend; 15x below\nthe two-neighbor test)",
                xy=(45, 2569), xytext=(45.9, 1150),
                fontsize=9, color="#8c1414", ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color="#8c1414", lw=0.9,
                                connectionstyle="arc3,rad=-0.18"))
    # callout: the same trend fails upward at $50
    ax.annotate("the same trend predicts ~4,100 at $50;\nactual is 63,904 (15.7x above)\nso there is no smooth trend to blame",
                xy=(50, 4069), xytext=(42.3, 90000),
                fontsize=9, color="#8c1414", ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color="#8c1414", lw=0.9,
                                connectionstyle="arc3,rad=0.25"))
    # note on the pre-2021 control
    ax.annotate("2020 (dark line): \\$45 sits at 84% of \\$40\nand level with \\$50; the trend fits it\nalmost exactly (0.98x). No hole.",
                xy=(45, 3219), xytext=(25.8, 1050),
                fontsize=9, color="#333333", ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color="#555555", lw=0.9,
                                connectionstyle="arc3,rad=0.12"))

    ax.set_yscale("log")
    ax.set_ylim(800, 400000)
    ax.set_xlim(23.5, 51.5)
    ax.set_xticks(ROUNDS)
    ax.set_xticklabels([f"${k}" for k in ROUNDS], fontsize=10)
    ax.set_ylabel("mean daily open interest (log scale)", fontsize=9.5)
    ax.set_xlabel("strike (round numbers; calls + puts, all expiries)", fontsize=9.5)
    ax.tick_params(labelsize=9)
    fig.legend(loc="upper center", bbox_to_anchor=(0.525, 0.845), ncol=3,
               fontsize=8.4, frameon=False)

    fig.savefig(OUT, dpi=125)  # 12.8x7.2 in * 125 dpi = 1600x900
    plt.close(fig)
    print(f"wrote {OUT}")
    print(f"E5 trend: pred45={pred45:,.0f} actual45={e5[45.0]:,.0f} "
          f"pred50={pred50:,.0f} actual50={e5[50.0]:,.0f}")


if __name__ == "__main__":
    main()
