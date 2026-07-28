#!/usr/bin/env python3
"""Re-render the shareables hidden-titer figure with public-safe labels.

Source data: posts/claim_tests/hidden_titer_trajectory_2026-07-21/data/
(frozen hunt package, untouched). Only change vs the hunt figure: the bottom
panel's y-label said "Hunt-1 top-3-cell share (21d)"; it now reads plainly.
Output: posts/shareables_2026-07-22/figures/fig05_titer_trajectory.png
"""
import json
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[3]
HUNT = REPO / 'posts/claim_tests/hidden_titer_trajectory_2026-07-21'
OUT = REPO / 'posts/shareables_2026-07-22/figures/fig05_titer_trajectory.png'

d = pd.read_parquet(HUNT / 'data/panel_daily.parquet')
res = json.load(open(HUNT / 'data/limb_results.json'))

fig, ax = plt.subplots(3, 1, figsize=(11, 9), sharex=True,
                       gridspec_kw={'height_ratios': [2, 1, 1]})
ax[0].fill_between(d['date'], d['titer'], step='mid', alpha=0.35, color='darkred')
ax[0].plot(d['date'], d['titer_21d'], color='darkred', lw=1.5,
           label='21d mean (titer growth)')
ax[0].set_yscale('symlog', linthresh=25)
ax[0].set_ylabel('daily titer (contracts)')
ax[0].legend(loc='upper left')
ax2 = ax[0].twinx()
ax2.plot(d['date'], d['titer_cum'], color='black', lw=1.2, alpha=0.8)
ax2.set_ylabel('cumulative titer')
ax[0].set_title('Hidden titer: daily builds + 21d growth + cumulative')

att = d['log_eq_vol'] / d['log_eq_vol'].max()
ax[1].fill_between(d['date'], att, alpha=0.4, color='steelblue')
ax[1].set_ylabel('attention (normed)')
for q, r in res['limb_ii_attention_independence']['regime_quintile_rhos'].items():
    ax[1].text(0.01 + 0.048 * int(q[1]), 0.85, f'{q}:{r:.2f}',
               transform=ax[1].transAxes, fontsize=8)

ax[2].plot(d['date'], d['top3_share_21d'], color='darkgreen', lw=1.2)
ax[2].set_ylabel("top-3 share (21d)")
ax[2].set_xlabel('date')
for a in ax:
    for lo, hi in [('2021-01-13', '2021-02-24'), ('2024-05-13', '2024-06-21')]:
        a.axvspan(lo, hi, color='orange', alpha=0.15)
plt.tight_layout()
plt.savefig(OUT, dpi=130)
plt.close()
print(f'wrote {OUT}')
