
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np
import datetime
import os

# ── Style Constants (matching chart_combined.py) ─────
BG = '#0d1117'
PANEL_BG = '#0d1117'
GRID_COLOR = '#8b949e'
SPINE_COLOR = '#30363d'
TEXT_COLOR = '#c9d1d9'
GREEN = '#39d353'
RED = '#f85149'
ACCENT_ORANGE = '#f0883e'
ACCENT_BLUE = '#58a6ff'

# ── Data ─────────────────────────────────────────────
base_time = datetime.datetime(2024, 5, 17, 8, 0, 0)
np.random.seed(42)  # Reproducible

# Generate per-second ticks for 10 minutes
times = [base_time + datetime.timedelta(seconds=i) for i in range(0, 600)]

lit_prices = []
dark_prices = []

for t in times:
    s = (t - base_time).total_seconds()

    # Lit: $20.87–$20.99 range
    lit = 20.93 + np.random.uniform(-0.06, 0.06)
    lit_prices.append(lit)

    # Dark: Tracks lit, then fractures at 08:03:20, heals at 08:08
    if s < 200:
        dark_prices.append(lit + np.random.uniform(-0.03, 0.03))
    elif s < 480:
        dark_prices.append(33.00 + np.random.uniform(-0.005, 0.005))
    else:
        dark_prices.append(lit + np.random.uniform(-0.03, 0.03))

# ── Chart ────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7), facecolor=BG)
ax.set_facecolor(PANEL_BG)

# Fracture zone shading
fracture_start = base_time + datetime.timedelta(seconds=200)
fracture_end = base_time + datetime.timedelta(seconds=480)
ax.axvspan(fracture_start, fracture_end, color=RED, alpha=0.08)

# Plot lines
ax.plot(times, dark_prices, color=RED, linewidth=2.0, alpha=0.9,
        label='Dark Pool (FINRA TRF)')
ax.plot(times, lit_prices, color=GREEN, linewidth=1.8, alpha=0.8,
        label='Lit Exchange (Nasdaq/EDGX)')

# Reference lines
ax.axhline(y=33.00, color=ACCENT_ORANGE, linewidth=1.0, linestyle='--', alpha=0.6)
ax.text(base_time + datetime.timedelta(seconds=5), 33.35,
        '$33.00 OpEx Strike Ceiling', color=ACCENT_ORANGE,
        fontsize=9, fontstyle='italic', fontweight='bold')

ax.axhline(y=20.87, color=ACCENT_BLUE, linewidth=0.8, linestyle=':', alpha=0.5)
ax.text(base_time + datetime.timedelta(seconds=5), 20.50,
        'Lit NBBO ~$20.87', color=ACCENT_BLUE, fontsize=8, fontstyle='italic')

# Dislocation bracket (right side)
bracket_x = base_time + datetime.timedelta(seconds=550)
ax.annotate('', xy=(bracket_x, 33.0),
            xytext=(bracket_x, 20.87),
            arrowprops=dict(arrowstyle='<->', color=ACCENT_ORANGE, lw=1.5))
ax.text(bracket_x + datetime.timedelta(seconds=8), 27.0,
        '$12.13\ndislocation', color=ACCENT_ORANGE, fontsize=11,
        fontweight='bold', ha='left', va='center')

# Phase annotations (top)
phase_y = 34.8
ax.annotate('Phase I\nAccumulation',
            xy=(base_time + datetime.timedelta(seconds=30), phase_y),
            ha='center', va='bottom', color=TEXT_COLOR, fontsize=8,
            fontweight='bold', fontstyle='italic')

ax.annotate('Phase II\nStabilization',
            xy=(base_time + datetime.timedelta(seconds=90), phase_y),
            ha='center', va='bottom', color=TEXT_COLOR, fontsize=8,
            fontweight='bold', fontstyle='italic')

mid_fracture = base_time + datetime.timedelta(seconds=340)
ax.annotate('Phase III — Settlement\n(Reg SHO 204 Window)',
            xy=(mid_fracture, 33.2), xytext=(mid_fracture, phase_y + 0.5),
            ha='center', va='bottom', color=RED, fontsize=9,
            fontweight='bold',
            arrowprops=dict(arrowstyle='->', color=RED, lw=1.2, alpha=0.7))

ax.annotate('Healed',
            xy=(base_time + datetime.timedelta(seconds=520), phase_y),
            ha='center', va='bottom', color=GREEN, fontsize=8,
            fontweight='bold', fontstyle='italic')

# Title and labels
ax.set_title('The Tape Fracture — Two Markets, One Stock\n'
             'GME Pre-Market, May 17 2024, 08:00–08:10 ET',
             color='white', fontsize=14, fontweight='bold', pad=18)
ax.set_ylabel('Trade Price ($)', color=TEXT_COLOR, fontsize=11)
ax.set_xlabel('Time (ET)', color=TEXT_COLOR, fontsize=11)

# Legend
legend = ax.legend(loc='center left', fontsize=10,
                   facecolor='#161b22', edgecolor=SPINE_COLOR,
                   labelcolor='white', framealpha=0.9)

# Axis formatting
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))
ax.tick_params(colors=GRID_COLOR, labelsize=9)
ax.grid(True, alpha=0.08, color=GRID_COLOR)
for spine in ax.spines.values():
    spine.set_color(SPINE_COLOR)
ax.set_ylim(19.5, 36)

# Source watermark
fig.text(0.5, 0.005,
         'Simulated from documented trade parameters  •  '
         'Real data chart: tape_fracture_combined.png',
         ha='center', fontsize=7, color='#484f58', fontstyle='italic')

plt.tight_layout()

output_path = "../../figures/chart_tape_fracture.png"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.close()
print(f"Chart saved to {output_path}")
