import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import os

OUT = os.path.join(os.path.dirname(__file__), "..", "posts", "figures")
os.makedirs(OUT, exist_ok=True)

# ── Style constants ──────────────────────────────────────────────────────────
BG       = "#0d1117"
ACCENT   = "#58a6ff"
ACCENT_MUTED = "#1f6feb"
TEXT     = "#8b949e"
BOLD_TXT = "#f0f6fc"
GRID     = "#21262d"
RED_GLOW = "#ff7b72"
GREEN_GLOW= "#7ee787"
PURPLE_GLOW = "#d2a8ff"
FONT     = "Courier New"

# 5:2 ratio is exactly what X wants
FIGW = 10
FIGH = 4

titles = [
    ("PART 1", "Following the Money"),
    ("PART 2", "The Paper Trail"),
    ("PART 3", "Systemic Exhaust"),
    ("PART 4", "The Macro Machine")
]

for part_num, subtitle in titles:
    fig, ax = plt.subplots(figsize=(FIGW, FIGH))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")

    # Draw some abstract background "market data" on the right side
    np.random.seed(hash(part_num) % 10000)
    
    # 1. Subtle grid
    for x in np.linspace(4, 10, 15):
        ax.axvline(x, color=GRID, lw=0.5, alpha=0.3)
    for y in np.linspace(0, 4, 10):
        ax.axhline(y, color=GRID, lw=0.5, alpha=0.3)

    # 2. Glowing price line
    x_line = np.linspace(3.5, 10.0, 120)
    # Random walk with some momentum and drift
    steps = np.random.normal(0, 0.1, 120)
    if part_num == "PART 1":
        # Huge spike representing FTDs/tape fracture
        steps[96] = 2.0
        steps[97] = -1.5
    elif part_num == "PART 2":
        # Migration (going from one level to another)
        steps[50:70] = np.random.normal(0.05, 0.05, 20)
    elif part_num == "PART 3":
        # Exhaust (increasing volatility)
        steps = np.random.normal(0, np.linspace(0.05, 0.3, 120), 120)
    
    y_line = 2.0 + np.cumsum(steps)
    # Normalize y_line to fit beautifully between 0.5 and 3.5
    y_min, y_max = np.min(y_line), np.max(y_line)
    y_line = 0.5 + 3.0 * (y_line - y_min) / (y_max - y_min + 1e-6)

    # Plot glowing line
    line_color = ACCENT
    if part_num == "PART 1": line_color = RED_GLOW
    if part_num == "PART 2": line_color = ACCENT
    if part_num == "PART 3": line_color = PURPLE_GLOW
    if part_num == "PART 4": line_color = GREEN_GLOW

    ax.plot(x_line, y_line, color=line_color, lw=2, alpha=0.9)
    ax.fill_between(x_line, 0, y_line, color=line_color, alpha=0.1)

    # 3. Add some "volume" bars at the bottom right
    x_vol = np.linspace(3.5, 10.0, 50)
    y_vol = np.abs(np.random.normal(0, 0.3, 50))
    if part_num == "PART 1":
        y_vol[42] = 1.5
    ax.bar(x_vol, y_vol, width=0.08, color=TEXT, alpha=0.2, bottom=0)

    # 4. Fade mask on the left side of the chart (fades from solid BG to transparent)
    cmap_bg = mcolors.LinearSegmentedColormap.from_list("fade", [mcolors.to_rgba(BG, 0), BG])
    x_mask = np.linspace(0, 6.0, 300)
    alpha_arr = np.clip((6.0 - x_mask) / (6.0 - 3.5), 0, 1)
    ax.imshow(alpha_arr.reshape(1, -1), extent=[0, 6.0, 0, 4], aspect='auto', 
              cmap=cmap_bg, zorder=5, vmin=0, vmax=1)

    TITLE_FONT = "Inter"
    SUBTITLE_FONT = "Courier New"

    # ── Typography ──────────────────────────────────────────────────────────
    # Main Title
    ax.text(0.5, 2.6, "OPTIONS &", 
            fontsize=42, fontweight="900", color=BOLD_TXT, 
            fontfamily=TITLE_FONT, ha="left", va="bottom", alpha=0.95, zorder=10)
    
    ax.text(0.5, 2.1, "CONSEQUENCES", 
            fontsize=40, fontweight="900", color=BOLD_TXT, 
            fontfamily=TITLE_FONT, ha="left", va="bottom", alpha=0.95, zorder=10)

    # Subtitle / Part
    ax.text(0.5, 1.3, f"{part_num}", 
            fontsize=16, fontweight="bold", color=line_color, 
            fontfamily=SUBTITLE_FONT, ha="left", va="top", zorder=10)

    ax.text(0.5, 0.9, f"— {subtitle}", 
            fontsize=18, fontweight="normal", color=TEXT, 
            fontfamily=SUBTITLE_FONT, ha="left", va="top", zorder=10)

    # Border
    rect = plt.Rectangle((0, 0), 10, 4, linewidth=2, edgecolor=GRID, facecolor="none")
    ax.add_patch(rect)

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    filename = f"header_{part_num.lower().replace(' ', '')}.png"
    path = os.path.join(OUT, filename)
    fig.savefig(path, dpi=240, bbox_inches="tight", pad_inches=0, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✓ {filename}")

print("✅ Series headers generated!")
