#!/usr/bin/env python3
"""tw_titer.png: phone/Twitter redraw of the hidden-titer trajectory.

One panel: cumulative off-tape OI builds (GME deep-put far book), 2018 -> 2026,
ending at 670,322 contracts, faint daily-build bars behind (same contract
units, linear), vertical line at the 2025-10 warrant reset.

Values come from the audit-frozen titer series (preferred over the trajectory
intermediate): posts/claim_tests/offtape_oi_artifact_audit_2026-07-21/data/titer_daily.parquet
Trading-day calendar (dates only): hidden_titer_trajectory_2026-07-21/data/panel_daily.parquet
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
AUDIT = REPO / "posts/claim_tests/offtape_oi_artifact_audit_2026-07-21/data/titer_daily.parquet"
PANEL = REPO / "posts/claim_tests/hidden_titer_trajectory_2026-07-21/data/panel_daily.parquet"
OUT = REPO / "posts/shareables_2026-07-22/figures"
OUT.mkdir(parents=True, exist_ok=True)

a = pd.read_parquet(AUDIT)
a["tape_date"] = pd.to_datetime(a["tape_date"])
cal = pd.to_datetime(pd.read_parquet(PANEL, columns=["date"])["date"])
daily = pd.Series(0.0, index=pd.DatetimeIndex(cal)).add(
    a.set_index("tape_date")["titer"], fill_value=0.0)
cum = daily.cumsum()
if cum.iloc[-1] != 670322:
    raise RuntimeError(f"audit-frozen cumulative ends at {cum.iloc[-1]}, expected 670322")

RESET = pd.Timestamp("2025-10-07")   # GME warrant reset (migration config CA_MASKS)

plt.rcParams.update({"font.size": 14, "figure.facecolor": "white"})
fig, ax = plt.subplots(figsize=(16, 9))
fig.subplots_adjust(left=0.075, right=0.975, top=0.845, bottom=0.085)

ax.bar(daily.index, daily.values, width=4.0, color="#e57373", alpha=0.8,
       label="daily build (contracts)", zorder=2)
ax.plot(cum.index, cum.values, color="#111111", lw=3.2, drawstyle="steps-post",
        label="cumulative (contracts)", zorder=4)
ax.axvline(RESET, color="#555555", ls="--", lw=2.2, zorder=3)
ax.text(RESET - pd.Timedelta(days=40), 0.03, "2025-10 warrant reset",
        transform=ax.get_xaxis_transform(), rotation=90, va="bottom", ha="right",
        fontsize=14.5, color="#333333")

x_end, y_end = cum.index[-1], cum.iloc[-1]
ax.scatter([x_end], [y_end], s=70, color="#111111", zorder=5)
ax.annotate("670,322 contracts", xy=(x_end, y_end),
            xytext=(0.70, 0.86), textcoords="axes fraction",
            fontsize=18, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color="#111111", lw=1.4))

ax.set_ylim(0, 730000)
ax.set_xlim(pd.Timestamp("2018-01-01"), pd.Timestamp("2026-07-15"))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.tick_params(labelsize=14.5)
ax.set_ylabel("contracts", fontsize=15.5)
ax.grid(axis="y", color="#cccccc", alpha=0.5, lw=0.8)
ax.legend(loc="upper left", fontsize=14, framealpha=0.95)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)

fig.suptitle("Open interest that never traded: 670,322 contracts and still climbing",
             fontsize=21, fontweight="bold", y=0.965)
fig.text(0.5, 0.905,
         "cumulative off-tape OI builds, GME deep-put far book; grows fastest in the quietest weeks",
         ha="center", fontsize=15, color="#333333")

fig.savefig(OUT / "tw_titer.png", dpi=100)
print("wrote", OUT / "tw_titer.png")
