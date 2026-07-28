#!/usr/bin/env python3
"""Twitter-optimized (1600x900) render of the pre-announcement $32 births.

Source data: posts/claim_tests/k32_precursor_2026-07-23 (frozen hunt package,
untouched). The managed runtime has no pyarrow, so the daily $31/$32/$33 panel
is exported once from the Hunt-60 oi_panel.parquet with the repo venv:

  .venv/bin/python -c "
  import pandas as pd
  df = pd.read_parquet('posts/claim_tests/strike32_warrant_wall_2026-07-23/data/oi_panel.parquet')
  df = df[df.strike_adj.isin([31.0, 32.0, 33.0])]
  daily = df.groupby(['snap_date','strike_adj']).oi_adj.sum().unstack()
  daily.loc['2025-06-01':'2025-11-04'].to_csv('posts/shareables_2026-07-22/code/_tw_precursor_daily.csv')
  "

Output: posts/shareables_2026-07-22/figures/tw_precursor.png
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(sys.executable).parent.parent.parent))
from daimon_runtime import setup_plot
setup_plot()
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

REPO = Path(__file__).resolve().parents[3]
DATA = Path(__file__).resolve().parent / "_tw_precursor_daily.csv"
OUT = REPO / "posts/shareables_2026-07-22/figures/tw_precursor.png"

BIRTHS = [("2025-08-06", 4376), ("2025-08-14", 3769)]
EK = "2025-09-09"      # warrant 8-K + Q2 print (sourced in the hunt README)
RESET = "2025-10-07"   # warrant reset (store artifact date)


def main():
    daily = pd.read_csv(DATA, index_col=0, parse_dates=True)
    daily.columns = [float(c) for c in daily.columns]

    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.subplots_adjust(left=0.075, right=0.975, top=0.80, bottom=0.10)
    fig.suptitle("Occupied early: the \\$32 warrant strike filled up off-tape, weeks before the warrant existed",
                 fontsize=15, weight="bold", x=0.075, ha="left", y=0.945)
    fig.text(0.075, 0.855,
             "daily open interest at the \\$32 calls vs odd-dollar neighbors; dotted = two off-tape births "
             "(zero trades in the born line); dashed = the warrant 8-K, weeks later",
             fontsize=10.5, color="#444444", ha="left")

    ax.plot(daily.index, daily[32.0], color="#c41e3a", lw=2.4, label="$32 calls")
    ax.plot(daily.index, daily[31.0], color="#c9a227", lw=1.4, alpha=0.9, label="$31 calls (control)")
    ax.plot(daily.index, daily[33.0], color="#999999", lw=1.4, alpha=0.9, label="$33 calls (control)")

    for i, (d, n) in enumerate(BIRTHS):
        ax.axvline(pd.Timestamp(d), color="#333333", ls=":", lw=1.3)
        ax.annotate(f"off-tape birth: +{n:,} (zero prints in the line)",
                    xy=(pd.Timestamp(d), 1.0), xycoords=("data", "axes fraction"),
                    xytext=(4, -4), textcoords="offset points",
                    fontsize=8.5, color="#333333", rotation=90, ha="left", va="top")

    ax.axvline(pd.Timestamp(EK), color="#7b3294", ls="--", lw=1.5)
    ax.annotate("warrant 8-K + earnings:\nstrike $32 becomes public",
                xy=(pd.Timestamp(EK), 25000), xytext=(pd.Timestamp(EK) + pd.Timedelta(days=3), 23000),
                fontsize=9, color="#7b3294", ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color="#7b3294", lw=0.9))

    ax.axvline(pd.Timestamp(RESET), color="#e08214", ls="--", lw=1.2, alpha=0.9)
    ax.annotate("warrant reset", xy=(pd.Timestamp(RESET), 1.0), xycoords=("data", "axes fraction"),
                xytext=(4, -4), textcoords="offset points",
                fontsize=8.5, color="#b36a00", rotation=90, ha="left", va="top")

    ax.set_ylabel("daily open interest, all expiries (contracts)", fontsize=9.5)
    ax.set_xlabel("2025 (daily 06:30-ET snapshots)", fontsize=9.5)
    ax.set_ylim(0, 40000)
    ax.set_xlim(pd.Timestamp("2025-06-01"), pd.Timestamp("2025-11-04"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.tick_params(labelsize=9)
    ax.legend(loc="center left", fontsize=9, framealpha=0.92)

    fig.savefig(OUT, dpi=125)  # 12.8x7.2 in * 125 dpi = 1600x900
    plt.close(fig)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
