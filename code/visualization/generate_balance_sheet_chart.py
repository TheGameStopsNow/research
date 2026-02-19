
import matplotlib.pyplot as plt
import numpy as np
import os

# Data
years = ['FY2020', 'FY2021', 'FY2022', 'FY2023', 'FY2024']
assets = [71.0, 65.4, 79.1, 73.0, 80.4]
capital = [8.8, 8.0, 8.0, 11.7, 6.2]

# Setup
x = np.arange(len(years))
width = 0.35

fig, ax = plt.subplots(figsize=(10, 6))

# Plotting
rects1 = ax.bar(x - width/2, assets, width, label='Total Assets ($B)', color='#4a90e2')
rects2 = ax.bar(x + width/2, capital, width, label="Member's Capital ($B)", color='#e74c3c')

# Styling
ax.set_ylabel('Billions ($)')
ax.set_title('Citadel Securities: Assets vs Member Capital (2020-2024)')
ax.set_xticks(x)
ax.set_xticklabels(years)
ax.legend()
ax.grid(axis='y', linestyle='--', alpha=0.7)

# Dark theme background for Reddit
ax.set_facecolor('#1e1e1e')
fig.patch.set_facecolor('#1e1e1e')
ax.tick_params(colors='white')
ax.yaxis.label.set_color('white')
ax.xaxis.label.set_color('white')
ax.title.set_color('white')

# Legend Styling - Fix: Added explicit background and edge color for readability
legend = ax.legend(facecolor='#1e1e1e', edgecolor='white', framealpha=0.9, loc='upper left')
plt.setp(legend.get_texts(), color='white')

# Adding labels
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'${height}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', color='white', fontweight='bold', fontsize=11)

autolabel(rects1)
autolabel(rects2)

# Annotation for the drop - Fix: Adjusted position to avoid overlap with bar label
# Pointing from FY2023 top to FY2024 top to visualize the drop
x_2023 = x[-2] + width/2
y_2023 = capital[-2]
x_2024 = x[-1] + width/2
y_2024 = capital[-1]

# Draw an arrow from 2023 down to 2024
ax.annotate('', xy=(x_2024, y_2024 + 0.5), xytext=(x_2023, y_2023),
            arrowprops=dict(arrowstyle="->", color='#e74c3c', lw=2))

# Text label for the drop placed in the middle
mid_x = (x_2023 + x_2024) / 2
mid_y = (y_2023 + y_2024) / 2

ax.text(mid_x, mid_y + 2, '-$5.48B\nWithdrawal', 
        ha='center', va='bottom', color='#e74c3c', fontweight='bold', fontsize=12,
        bbox=dict(facecolor='#1e1e1e', edgecolor='#e74c3c', boxstyle='round,pad=0.3'))

plt.tight_layout()

# Save
output_path = "../../figures/chart_balance_sheet_trend.png"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"Chart saved to {output_path}")
