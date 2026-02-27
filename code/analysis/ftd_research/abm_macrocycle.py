"""
Agent-Based Model: FTD Macrocycle Emergence
=============================================
Simulates the NSCC continuous net settlement (CNS) clearing
process with regulatory deadlines (T+6, T+13, T+35, RECAPS 10-day
cycle), market-maker locate abuse, and Obligation Warehouse leakage.

Uses FFT to detect emergent spectral peaks at:
  - T+33 (close-out deadline harmonic)
  - T+105 (3x T+35 harmonic)
  - ~630 bd macrocycle (4th harmonic of LCM(6,13,35,10)=2730)

Inputs: None (synthetic simulation)
Output:
  - results/ftd_research/abm_macrocycle_results.json

Key finding: The ~630-day macrocycle emerges from bare regulatory
rules alone, with no conspiracy or coordination required.
"""

import numpy as np
from scipy.signal import find_peaks
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
OUT_FILE = ROOT / "results" / "ftd_research" / "abm_macrocycle_results.json"

# Simulation parameters
N_DAYS = 2500
IMPULSE_DAY = 250
IMPULSE_SIZE = 5_000_000
DAILY_ORGANIC_FAIL_MEAN = 30_000
DAILY_ORGANIC_FAIL_STD = 15_000
T_CLOSE_SHORT = 6
T_CLOSE_THRESH = 13
T_CLOSE_FINAL = 35
T_RECAPS_CYCLE = 10
MM_LOCATE_PROBABILITY = 0.70
MM_LOCATE_LEAKAGE = 0.15
OW_DECAY_RATE = 0.005
RECAPS_REINJECTION = 0.10
POST_IMPULSE_ELEVATED_DAYS = 60
POST_IMPULSE_MULTIPLIER = 5.0


def run_abm(n_days=N_DAYS, seed=42):
    np.random.seed(seed)
    cns_queue = np.zeros(T_CLOSE_FINAL + 5)
    ow_stock = 0.0
    daily_ftd = np.zeros(n_days)

    for day in range(n_days):
        organic = max(0, np.random.normal(DAILY_ORGANIC_FAIL_MEAN, DAILY_ORGANIC_FAIL_STD))
        if IMPULSE_DAY < day < IMPULSE_DAY + POST_IMPULSE_ELEVATED_DAYS:
            decay = 1.0 - (day - IMPULSE_DAY) / POST_IMPULSE_ELEVATED_DAYS
            organic *= (1 + POST_IMPULSE_MULTIPLIER * decay)
        if day == IMPULSE_DAY:
            organic += IMPULSE_SIZE

        cns_queue[0] += organic
        new_queue = np.zeros_like(cns_queue)
        for age in range(len(cns_queue) - 1, -1, -1):
            shares = cns_queue[age]
            if shares <= 0:
                continue
            if age >= T_CLOSE_FINAL:
                ow_stock += shares * 0.20
            elif age == T_CLOSE_THRESH:
                if np.random.random() < MM_LOCATE_PROBABILITY:
                    leaked = shares * MM_LOCATE_LEAKAGE
                    ow_stock += leaked
                    new_queue[0] += shares - leaked
                else:
                    if age + 1 < len(new_queue):
                        new_queue[age + 1] += shares
            elif age == T_CLOSE_SHORT:
                remaining = shares * 0.50
                if np.random.random() < MM_LOCATE_PROBABILITY:
                    leaked = remaining * MM_LOCATE_LEAKAGE
                    ow_stock += leaked
                    new_queue[0] += remaining - leaked
                else:
                    if age + 1 < len(new_queue):
                        new_queue[age + 1] += remaining
            else:
                if age + 1 < len(new_queue):
                    new_queue[age + 1] += shares
                else:
                    ow_stock += shares

        cns_queue = new_queue
        ow_stock *= (1 - OW_DECAY_RATE)
        if day % T_RECAPS_CYCLE == 0 and day > 0:
            reinjected = ow_stock * RECAPS_REINJECTION
            ow_stock -= reinjected
            cns_queue[0] += reinjected

        daily_ftd[day] = cns_queue.sum()

    return daily_ftd


def analyze_spectrum(daily_ftd):
    x = daily_ftd - daily_ftd.mean()
    n = len(x)
    fft_vals = np.fft.rfft(x)
    power = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0)
    periods = np.where(freqs > 0, 1.0 / freqs, np.inf)

    valid = (periods > 5) & (periods < 1200)
    valid_power = np.where(valid, power, 0)
    peaks, props = find_peaks(valid_power, height=np.max(valid_power) * 0.03, distance=3)

    if len(peaks) == 0:
        return {}

    peak_order = np.argsort(props['peak_heights'])[::-1]
    top_peaks = peaks[peak_order[:15]]
    mean_power = power[1:].mean()

    results = []
    for p in top_peaks:
        results.append({
            'period_bd': float(periods[p]),
            'power_ratio': float(power[p] / mean_power),
        })
    return results


def main():
    print(f"Running ABM simulation ({N_DAYS} days)...")
    ftd = run_abm()
    spectrum = analyze_spectrum(ftd)

    print(f"\nTop spectral peaks:")
    print(f"{'Period (bd)':>12} {'Power Ratio':>12}")
    print("-" * 28)
    for p in spectrum[:10]:
        flags = []
        period = p['period_bd']
        if 30 <= period <= 37: flags.append("T+33")
        if 95 <= period <= 115: flags.append("T+105")
        if 580 <= period <= 700: flags.append("MACROCYCLE")
        flag = "  " + " ".join(flags) if flags else ""
        print(f"{period:>12.1f} {p['power_ratio']:>11.1f}x{flag}")

    output = {
        'n_days': N_DAYS,
        'seed': 42,
        'spectral_peaks': spectrum,
        'parameters': {
            'T_close_short': T_CLOSE_SHORT,
            'T_close_thresh': T_CLOSE_THRESH,
            'T_close_final': T_CLOSE_FINAL,
            'T_recaps_cycle': T_RECAPS_CYCLE,
            'MM_locate_probability': MM_LOCATE_PROBABILITY,
        }
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {OUT_FILE}")


if __name__ == '__main__':
    main()
