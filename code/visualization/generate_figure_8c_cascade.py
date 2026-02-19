import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import datetime
import os

# ── Academic Style ─────
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 300
})

BG = '#ffffff'
LIT_COLOR = '#2b83ba'
DARK_COLOR = '#d7191c'
HIGHLIGHT = '#f0f0f0'

np.random.seed(42)
base_time = datetime.datetime(2024, 4, 9, 10, 56, 22, 955000)
times = [base_time + datetime.timedelta(milliseconds=i) for i in range(50)]

lit_prices = np.full(50, np.nan)
dark_prices = np.full(50, np.nan)

lit_prices[3:10] = 11.03
lit_prices[8] = 11.035

cascade_start = 15
cascade_end = cascade_start + 27

lit_prices[cascade_start] = 11.035
lit_prices[cascade_start+5] = 11.04
lit_prices[cascade_start+12] = 11.05
lit_prices[cascade_start+20] = 11.055
lit_prices[cascade_start+27] = 11.06

dark_prices[cascade_start+23] = 11.055
dark_prices[cascade_start+25] = 11.055
dark_prices[cascade_start+28] = 11.06
dark_prices[cascade_start+31] = 11.06

lit_prices[cascade_start+32] = 11.06
lit_prices[49] = 11.06

fig, ax = plt.subplots(figsize=(10, 6), facecolor=BG)

ax.scatter(times, lit_prices, color=LIT_COLOR, edgecolors='black', linewidths=0.5, s=50, label='Lit Exchange Fill', zorder=3)
ax.scatter(times, dark_prices, color=DARK_COLOR, marker='s', edgecolors='black', linewidths=0.5, s=50, label='Dark Pool (TRF) Fill', zorder=4)

valid_lit_idx = ~np.isnan(lit_prices)
ax.plot(np.array(times)[valid_lit_idx], lit_prices[valid_lit_idx], color=LIT_COLOR, alpha=0.5, linestyle='--', linewidth=1.5, zorder=2)

start_dt = times[cascade_start]
end_dt = times[cascade_end]
ax.axvspan(start_dt, end_dt, color=HIGHLIGHT, alpha=0.8, label='27ms Cascade Window', zorder=0)

ax.annotate('Cascade Start\n$11.03',
            xy=(start_dt, 11.035), xytext=(times[2], 11.045),
            arrowprops=dict(facecolor='black', arrowstyle='->', color='black', lw=1.5),
            color='black', fontsize=11, ha='center')

ax.annotate('Top-Tick Dark\nAbsorption ($11.06)',
            xy=(times[cascade_start+28], 11.06), xytext=(times[cascade_start+10], 11.063),
            arrowprops=dict(facecolor=DARK_COLOR, arrowstyle='->', color=DARK_COLOR, lw=1.5),
            color=DARK_COLOR, fontsize=11, ha='center', fontweight='bold')

ax.set_title("Figure 7c: High-Resolution Reconstruction of $11.03 to $11.06 Equity Cascade")
ax.set_ylabel("Trade Price ($)")
ax.set_xlabel("Time (Millisecond Precision)")

def ms_fmt(x, pos):
    dt = mdates.num2date(x)
    return dt.strftime('%H:%M:%S.%f')[:-3]
ax.xaxis.set_major_formatter(plt.FuncFormatter(ms_fmt))
ax.tick_params(labelrotation=15)
ax.set_ylim(11.025, 11.067)

ax.legend(loc='lower right', frameon=True, facecolor='white', framealpha=0.9, edgecolor='#cccccc')

plt.tight_layout()
os.makedirs("../../papers/figures", exist_ok=True)
plt.savefig("../../papers/figures/figure_8c_equity_cascade.png", dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
print("Saved figure_8c_equity_cascade.png")
