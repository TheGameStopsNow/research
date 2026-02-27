#!/usr/bin/env python3
"""
Regenerate energy_flow_field.png using complete ThetaData
(part-0 + part-leaps merged) for full 7-bucket tenor coverage.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.ndimage import gaussian_filter, uniform_filter1d
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────
CSV_PATH = Path(__file__).parent / "output_full_range" / "daily_energy_budget.csv"
OUTPUT_PATH = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/"
                   "research/options_hedging_microstructure/review_package/"
                   "figures/energy_flow_field.png")

BUCKET_ORDER = ["0DTE", "1-7d", "8-30d", "31-90d", "91-180d", "181-365d", "365d+"]
ENERGY_WEIGHTS = {
    "0DTE": 0.1, "1-7d": 4.0, "8-30d": 19.0, "31-90d": 60.0,
    "91-180d": 135.0, "181-365d": 270.0, "365d+": 500.0,
}

# ── Load data ──────────────────────────────────────────────────────────────
daily_df = pd.read_csv(CSV_PATH, parse_dates=["date"])
daily_df = daily_df.sort_values("date").reset_index(drop=True)

# Build energy matrix
n_dates = len(daily_df)
t_axis = daily_df["date"].values
energy_matrix = np.column_stack([
    daily_df[f"{b}_count"].values.astype(float) * ENERGY_WEIGHTS[b]
    for b in BUCKET_ORDER
])

print(f"Data: {n_dates} days, {pd.Timestamp(t_axis[0]).strftime('%Y-%m-%d')} → "
      f"{pd.Timestamp(t_axis[-1]).strftime('%Y-%m-%d')}")

# ── Compute flow field (gradient of smoothed energy density) ───────────────
smooth_field = gaussian_filter(energy_matrix.T.astype(float), sigma=(0.5, 8))
grad_y, grad_x = np.gradient(smooth_field)

# Downsample for readable arrows
step_x = max(1, n_dates // 60)
step_y = 1
Y_q, X_q = np.mgrid[0:len(BUCKET_ORDER):step_y, 0:n_dates:step_x]

U = grad_x[::step_y, ::step_x]
V = grad_y[::step_y, ::step_x]

# ── Plot ───────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(20, 6))

# Background density heatmap
ax.imshow(
    smooth_field, aspect="auto", origin="lower",
    cmap="YlOrRd", alpha=0.4, interpolation="bilinear",
    extent=[0, n_dates, -0.5, len(BUCKET_ORDER) - 0.5],
)

# Quiver arrows (direction of energy migration)
magnitude = np.sqrt(U**2 + V**2)
ax.quiver(
    X_q, Y_q, U, V,
    magnitude,
    cmap="coolwarm", alpha=0.8,
    scale=magnitude.max() * 15 if magnitude.max() > 0 else 1,
    width=0.003,
)

# Format axes
ax.set_yticks(range(len(BUCKET_ORDER)))
ax.set_yticklabels(BUCKET_ORDER)

n_ticks = min(20, n_dates)
tick_pos = np.linspace(0, n_dates - 1, n_ticks, dtype=int)
ax.set_xticks(tick_pos)
ax.set_xticklabels(
    [pd.Timestamp(t_axis[i]).strftime("%Y-%m") for i in tick_pos],
    rotation=45, fontsize=8,
)

# Annotate key events
KEY_EVENTS = {
    "2021-01-28": "Jan 2021\nSneeze",
    "2024-06-07": "Jun 2024\nDFV Return",
}
t_pd = pd.DatetimeIndex(t_axis)
for evt_date, evt_label in KEY_EVENTS.items():
    evt_ts = pd.Timestamp(evt_date)
    if t_pd.min() <= evt_ts <= t_pd.max():
        idx = np.searchsorted(t_pd, evt_ts)
        ax.axvline(idx, color="white", linewidth=1.5, alpha=0.8, linestyle="--")
        ax.annotate(evt_label.replace("\n", " "), xy=(idx, len(BUCKET_ORDER) - 0.3),
                    fontsize=7, color="white", ha="center",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="black", alpha=0.7))

ax.set_ylabel("Tenor")
ax.set_xlabel("Date")
ax.set_title("Energy Flow Field — gradient of smoothed density (Full Range, 2018–2026)", fontsize=13)

plt.tight_layout()
fig.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {OUTPUT_PATH}")

# Also save a copy to the posts figures directories
for extra in [
    str(Path.home()) + "/Documents/GitHub/research/posts/01_strike_price_symphony/../figures/energy_flow_field.png",
    str(Path.home()) + "/Documents/GitHub/research/posts/04_the_trojan_horse/figures/chart_energy_flow_field.png",
]:
    p = Path(extra)
    if p.parent.exists():
        fig2, ax2 = plt.subplots(figsize=(20, 6))
        ax2.imshow(smooth_field, aspect="auto", origin="lower",
                   cmap="YlOrRd", alpha=0.4, interpolation="bilinear",
                   extent=[0, n_dates, -0.5, len(BUCKET_ORDER) - 0.5])
        ax2.quiver(X_q, Y_q, U, V, magnitude, cmap="coolwarm", alpha=0.8,
                   scale=magnitude.max() * 15 if magnitude.max() > 0 else 1, width=0.003)
        ax2.set_yticks(range(len(BUCKET_ORDER)))
        ax2.set_yticklabels(BUCKET_ORDER)
        ax2.set_xticks(tick_pos)
        ax2.set_xticklabels([pd.Timestamp(t_axis[i]).strftime("%Y-%m") for i in tick_pos],
                            rotation=45, fontsize=8)
        for evt_date, evt_label in KEY_EVENTS.items():
            evt_ts = pd.Timestamp(evt_date)
            if t_pd.min() <= evt_ts <= t_pd.max():
                idx = np.searchsorted(t_pd, evt_ts)
                ax2.axvline(idx, color="white", linewidth=1.5, alpha=0.8, linestyle="--")
                ax2.annotate(evt_label.replace("\n", " "), xy=(idx, len(BUCKET_ORDER) - 0.3),
                            fontsize=7, color="white", ha="center",
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="black", alpha=0.7))
        ax2.set_ylabel("Tenor")
        ax2.set_xlabel("Date")
        ax2.set_title("Energy Flow Field — gradient of smoothed density (Full Range, 2018–2026)", fontsize=13)
        plt.tight_layout()
        fig2.savefig(p, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"Saved copy: {p}")
