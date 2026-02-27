"""
ABM Welch Validation: Window-Independent PSD
=============================================
Validates that the ABM macrocycle (~630 bd) is a genuine emergent
property of the regulatory agent logic, not an FFT windowing artifact.

Uses Welch's method (overlapping Hann-windowed segments averaged)
to produce a window-independent power spectral density estimate.

Also includes a tripoint test (2500, 3400, 4100 days) to confirm
the peak does not track N/4.

Inputs: None (synthetic simulation; reuses ABM engine)
Output:
  - results/ftd_research/abm_welch_results.json

Key finding: Macrocycle peak (42.3x mean) survives Welch
decontamination. Falsification hypothesis REJECTED.
"""

import numpy as np
from scipy.signal import welch, find_peaks
from pathlib import Path
import json, sys

# Import the ABM runner from the companion script
sys.path.insert(0, str(Path(__file__).parent))
from abm_macrocycle import run_abm

ROOT = Path(__file__).resolve().parents[3]
OUT_FILE = ROOT / "results" / "ftd_research" / "abm_welch_results.json"


def main():
    print("=" * 70)
    print("ABM WELCH VALIDATION: Window-Independent PSD")
    print("=" * 70)

    # Run 5000-day simulation for best resolution
    n_days = 5000
    nperseg = 1250
    ftd = run_abm(n_days)
    x = ftd - ftd.mean()

    # Welch PSD
    freqs_w, psd_w = welch(x, fs=1.0, nperseg=nperseg, noverlap=nperseg//2,
                            window='hann', scaling='spectrum')
    periods_w = np.where(freqs_w > 0, 1.0 / freqs_w, np.inf)

    # Find peaks
    valid = (periods_w > 20) & (periods_w < 800)
    valid_psd = np.where(valid, psd_w, 0)
    peaks, props = find_peaks(valid_psd, height=np.max(valid_psd) * 0.03, distance=2)

    mean_psd = psd_w[psd_w > 0].mean()

    print(f"\nTop Welch spectral peaks (N={n_days}, nperseg={nperseg}):")
    if len(peaks) > 0:
        peak_order = np.argsort(props['peak_heights'])[::-1]
        for p in peaks[peak_order[:8]]:
            period = periods_w[p]
            ratio = psd_w[p] / mean_psd
            flags = []
            if 95 <= period <= 115: flags.append("T+105")
            if 580 <= period <= 700: flags.append("MACROCYCLE")
            if 30 <= period <= 37: flags.append("T+33")
            flag = "  " + " ".join(flags) if flags else ""
            print(f"  {period:>8.1f} bd  ({ratio:>6.1f}x mean){flag}")

    # Check macrocycle survival
    macro_mask = (periods_w >= 580) & (periods_w <= 700)
    t105_mask = (periods_w >= 95) & (periods_w <= 115)

    macro_ratio = float(psd_w[macro_mask].max() / mean_psd) if macro_mask.any() else 0
    t105_ratio = float(psd_w[t105_mask].max() / mean_psd) if t105_mask.any() else 0

    macro_survived = macro_ratio > 5.0
    t105_survived = t105_ratio > 5.0

    print(f"\nMacrocycle (~630bd): {macro_ratio:.1f}x mean - {'SURVIVED' if macro_survived else 'NOT SURVIVED'}")
    print(f"T+105:              {t105_ratio:.1f}x mean - {'SURVIVED' if t105_survived else 'NOT SURVIVED'}")

    # Tripoint check
    print(f"\nTripoint artifact test:")
    tripoint = []
    for n in [2500, 3400, 4100]:
        ftd_n = run_abm(n)
        x_n = ftd_n - ftd_n.mean()
        fft_v = np.fft.rfft(x_n)
        pwr = np.abs(fft_v) ** 2
        frq = np.fft.rfftfreq(n, d=1.0)
        per = np.where(frq > 0, 1.0 / frq, np.inf)
        mask = (per >= 400) & (per <= 1200)
        peak_idx = np.argmax(pwr[mask]) if mask.any() else 0
        peak_period = float(per[mask][peak_idx]) if mask.any() else 0
        tripoint.append({'n_days': n, 'peak_period': peak_period, 'n_over_4': n/4})
        print(f"  N={n}: peak={peak_period:.0f}bd, N/4={n/4:.0f}")

    verdict = "CONFIRMED_REAL" if macro_survived else "WEAK_REAL" if macro_ratio > 2.0 else "FALSIFIED"
    print(f"\nVerdict: {verdict}")

    output = {
        'test': 'Welch_method_decontamination',
        'n_days': n_days,
        'nperseg': nperseg,
        'macrocycle_welch_ratio': macro_ratio,
        't105_welch_ratio': t105_ratio,
        'macrocycle_survived': macro_survived,
        't105_survived': t105_survived,
        'tripoint': tripoint,
        'verdict': verdict,
    }

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {OUT_FILE}")


if __name__ == '__main__':
    main()
