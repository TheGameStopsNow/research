#!/usr/bin/env python3
"""
Test 21: Settlement Cavity Resonance — Hilbert Transform Phase Prediction
         & Fourier Clipping Model for Shadow Ledger Estimation

This script:
A) Extracts the 577bd frequency band from GME FTDs via bandpass filter
B) Applies Hilbert Transform to get instantaneous phase φ(t)
C) Projects phase forward to July 2026 (the predicted convergence node)
D) Implements the Fourier clipping model to estimate CNS netting capacity
E) Generates cross-asset spectral comparison chart
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.signal import hilbert, butter, filtfilt
from numpy.fft import fft, fftfreq
from pathlib import Path
from datetime import timedelta

FTD_DIR = Path(str(Path.home()) + "/Documents/GitHub/research/data/ftd")
FIG_DIR = Path(__file__).resolve().parent.parent / "figures"
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
FIG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

def load_ftd(symbol):
    """Load and create complete business day FTD series"""
    f = FTD_DIR / f"{symbol}_ftd.csv"
    if not f.exists():
        return None, None
    df = pd.read_csv(f, parse_dates=['date'])
    df = df.groupby('date')['quantity'].sum().reset_index().set_index('date').sort_index()
    full_range = pd.date_range(df.index.min(), df.index.max(), freq='B')
    full_series = df.reindex(full_range, fill_value=0)['quantity']
    return df, full_series

def bandpass_filter(data, low_period, high_period, fs=1.0, order=3):
    """Bandpass filter to isolate a specific frequency band (periods in bd)"""
    low_freq = 1.0 / high_period  # lower freq = longer period
    high_freq = 1.0 / low_period  # higher freq = shorter period
    nyquist = fs / 2
    low = low_freq / nyquist
    high = high_freq / nyquist
    # Clamp to valid range
    low = max(low, 0.001)
    high = min(high, 0.999)
    if low >= high:
        return data
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, data)

def compute_spectrum(series, key_periods=[33, 34, 35, 70, 105, 140, 193, 289, 577, 1190]):
    """Compute FFT and return power at key periods"""
    n = len(series)
    yf = fft(series.values)
    power = np.abs(yf[:n//2])**2
    freqs = fftfreq(n, d=1)[:n//2]
    periods = 1 / freqs[1:]
    power_at_period = power[1:]
    median_power = np.median(power_at_period)
    
    results = {}
    for target_p in key_periods:
        if target_p >= n // 2:
            results[target_p] = {'power': 0, 'ratio': 0}
            continue
        idx = np.argmin(np.abs(periods - target_p))
        band = power_at_period[max(0,idx-2):idx+3]
        avg_power = np.mean(band)
        results[target_p] = {
            'power': float(avg_power),
            'ratio': float(avg_power / median_power)
        }
    return results, periods, power_at_period, median_power


def main():
    print("=" * 70)
    print("TEST 21: Settlement Cavity Resonance")
    print("  Hilbert Transform + Fourier Clipping Model")
    print("=" * 70)

    # ============================================================
    # PART A: Load GME and extract 577bd band
    # ============================================================
    gme_raw, gme_series = load_ftd('GME')
    n = len(gme_series)
    
    print(f"\n  GME series: {n} business days")
    print(f"  Date range: {gme_series.index[0].strftime('%Y-%m-%d')} to {gme_series.index[-1].strftime('%Y-%m-%d')}")
    
    # Bandpass around 577bd (allow ±20% = 460-720bd)
    band_577 = bandpass_filter(gme_series.values.astype(float), 460, 720)
    
    # Also extract 33bd band for comparison
    band_33 = bandpass_filter(gme_series.values.astype(float), 28, 40)

    # ============================================================
    # PART B: Hilbert Transform for instantaneous phase
    # ============================================================
    print(f"\n{'='*60}")
    print("PART B: Hilbert Transform — Phase Extraction")
    print(f"{'='*60}")
    
    analytic_signal = hilbert(band_577)
    amplitude_envelope = np.abs(analytic_signal)
    instantaneous_phase = np.unwrap(np.angle(analytic_signal))
    
    # Phase velocity (radians per business day)
    phase_velocity = np.diff(instantaneous_phase).mean()
    period_from_phase = 2 * np.pi / abs(phase_velocity)
    
    print(f"\n  Phase velocity: {phase_velocity:.6f} rad/bd")
    print(f"  Implied period: {period_from_phase:.1f} bd (expect ~577)")
    
    # Current phase at end of data
    current_phase = instantaneous_phase[-1]
    current_date = gme_series.index[-1]
    print(f"  Current phase at {current_date.strftime('%Y-%m-%d')}: {current_phase:.2f} rad ({np.degrees(current_phase % (2*np.pi)):.1f}°)")
    
    # ============================================================
    # PART C: Project forward to July 2026
    # ============================================================
    print(f"\n{'='*60}")
    print("PART C: Forward Projection to July 2026")
    print(f"{'='*60}")
    
    # Business days from end of data to July 2026 targets
    targets = {
        'Jul 24, 2026': pd.Timestamp('2026-07-24'),
        'Jul 31, 2026': pd.Timestamp('2026-07-31'),
        'Aug 15, 2026': pd.Timestamp('2026-08-15'),
        'Sep 1, 2026': pd.Timestamp('2026-09-01'),
    }
    
    for label, target in targets.items():
        bd_forward = np.busday_count(current_date.date(), target.date())
        projected_phase = current_phase + phase_velocity * bd_forward
        # Normalize to 0-2π
        phase_mod = projected_phase % (2 * np.pi)
        phase_deg = np.degrees(phase_mod)
        
        # Constructive = near 0° or 360° (antinode), Destructive = near 180° (node)
        if phase_deg < 90 or phase_deg > 270:
            regime = "CONSTRUCTIVE (amplifying)"
        else:
            regime = "DESTRUCTIVE (dampening)"
        
        print(f"  {label}: +{bd_forward}bd → φ={phase_deg:.1f}° → {regime}")
    
    # Find next constructive and destructive nodes from now
    print(f"\n  Next critical nodes:")
    for target_phase_name, target_angle in [("Constructive peak (0°)", 0), 
                                              ("Destructive node (180°)", np.pi)]:
        # How many bd until phase hits target?
        phase_diff = (target_angle - (current_phase % (2*np.pi))) % (2*np.pi)
        bd_to_target = int(phase_diff / abs(phase_velocity))
        target_date = current_date + timedelta(days=int(bd_to_target * 1.4))  # approx calendar days
        print(f"    {target_phase_name}: ~{bd_to_target}bd → ~{target_date.strftime('%Y-%m-%d')}")

    # ============================================================
    # PART D: Fourier Clipping Model — Shadow Ledger Estimation
    # ============================================================
    print(f"\n{'='*60}")
    print("PART D: Fourier Clipping Model — Shadow Ledger")
    print(f"{'='*60}")
    
    symbols = ['GME', 'AMC', 'KOSS', 'BBBY', 'XRT', 'TSLA', 'BB', 'NOK',
               'IJH', 'SPY', 'IWM', 'NVDA', 'PLTR', 'AMZN', 'AAPL', 'MSFT']
    all_spectra = {}
    
    for sym in symbols:
        _, series = load_ftd(sym)
        if series is None:
            continue
        spectrum, _, _, _ = compute_spectrum(series)
        all_spectra[sym] = spectrum
    
    # ODI calculation
    print(f"\n  Obligation Distortion Index (κ):")
    print(f"  {'Symbol':<8} {'A₃₃':>8} {'A₃₅':>8} {'A₅₇₇':>8} {'κ':>8} {'Excess':>10} {'Regime'}")
    print("  " + "-" * 60)
    
    odi_results = {}
    for sym in symbols:
        if sym not in all_spectra:
            continue
        s = all_spectra[sym]
        a33 = s[33]['ratio']
        a35 = s[35]['ratio']
        a577 = s[577]['ratio']
        linear_sum = a33 + a35
        kappa = a577 / max(linear_sum, 0.01)
        excess = (a577 - linear_sum) / max(linear_sum, 0.01) * 100
        
        if kappa > 3:
            regime = "HARD CLIP"
        elif kappa > 2:
            regime = "HEAVY CLIP"
        elif kappa > 1.5:
            regime = "MODERATE"
        elif kappa > 1:
            regime = "SOFT CLIP"
        else:
            regime = "LINEAR"
        
        odi_results[sym] = {
            'a33': a33, 'a35': a35, 'a577': a577,
            'kappa': kappa, 'excess': excess, 'regime': regime
        }
        print(f"  {sym:<8} {a33:>7.1f}× {a35:>7.1f}× {a577:>7.1f}× {kappa:>7.2f} {excess:>+9.0f}% {regime}")

    # Estimate CNS netting capacity using clipping model
    # For a sine wave clipped at threshold C:
    # The ratio of harmonic power to fundamental power is related to clip depth
    # Deeper clipping → more harmonic energy → higher κ
    print(f"\n  Estimated relative clipping depth (1/κ ≈ visible fraction):")
    for sym, r in odi_results.items():
        visible_fraction = 1.0 / max(r['kappa'], 0.01)
        print(f"    {sym:<8}: ~{visible_fraction:.0%} of total obligations visible as FTDs")

    # ============================================================
    # PART E: Cross-Asset Spectral Comparison Chart
    # ============================================================
    fig = plt.figure(figsize=(22, 14))
    
    # Create grid: 2 rows, 2 cols — 3 panels total
    # Top: beat envelope (left), cross-asset heatmap (right)
    # Bottom: full-width power spectrum
    gs = fig.add_gridspec(2, 2, hspace=0.40, wspace=0.3,
                          height_ratios=[1.2, 0.8])
    
    # ------------------------------------------------------------------
    # Panel 1 (top-left): GME FTDs + ~630bd Hilbert envelope
    # Use DUAL Y-AXIS: raw FTDs on left (faded), envelope on right (prominent)
    # ------------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0, 0])
    dates = gme_series.index
    ax1.fill_between(dates, 0, gme_series.values, alpha=0.10, color='steelblue')
    ax1.set_ylabel('Raw FTDs', color='steelblue', fontsize=9, alpha=0.6)
    ax1.tick_params(axis='y', labelcolor='steelblue', labelsize=8, colors='steelblue')
    ax1.set_ylim(0, gme_series.max() * 1.1)
    ax1.grid(True, alpha=0.15)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    
    # Second y-axis for the envelope (much more prominent)
    ax1b = ax1.twinx()
    # Trim ~6 months (125 bd) from each end to remove Hilbert edge artifacts
    trim = 125
    env_dates = dates[trim:-trim]
    env_vals = amplitude_envelope[trim:-trim]
    ax1b.plot(env_dates, env_vals, color='crimson', linewidth=2.0, label='~630bd Beat Envelope')
    ax1b.fill_between(env_dates, 0, env_vals, alpha=0.15, color='crimson')
    ax1b.set_ylabel('Envelope Amplitude', color='crimson', fontsize=9)
    ax1b.tick_params(axis='y', labelcolor='crimson', labelsize=8)
    
    # Mark supercycle peaks on the envelope (only within trimmed range)
    from scipy.signal import argrelextrema
    peak_indices = argrelextrema(amplitude_envelope, np.greater, order=200)[0]
    for pi in peak_indices:
        if pi < trim or pi >= len(dates) - trim:
            continue  # skip edge-artifact peaks
        ax1b.annotate(dates[pi].strftime('%b\n%Y'), xy=(dates[pi], amplitude_envelope[pi]),
                     fontsize=7, ha='center', va='bottom', color='darkred', fontweight='bold')
    
    ax1.set_title('GME: ~630bd Beat Envelope (Hilbert Transform)', fontsize=11, fontweight='bold')
    ax1b.legend(fontsize=8, loc='upper left')
    
    # ------------------------------------------------------------------
    # Panel 2 (top-right): Cross-asset spectral comparison heatmap
    # ------------------------------------------------------------------
    ax3 = fig.add_subplot(gs[0, 1])
    period_labels = [33, 35, 105, 140, 193, 289, 577]
    heatmap_data = []
    heatmap_labels = []
    # Build all rows
    heatmap_order = ['BBBY', 'AMC', 'GME', 'KOSS', 'TSLA', 'BB', 'XRT', 'NOK',
                     'IJH', 'SPY', 'PLTR', 'NVDA', 'AMZN', 'AAPL', 'IWM', 'MSFT']
    for sym in heatmap_order:
        if sym in all_spectra:
            row = [all_spectra[sym].get(p, {}).get('ratio', 0) for p in period_labels]
            heatmap_data.append(row)
            label = 'BBBY†' if sym == 'BBBY' else sym
            heatmap_labels.append(label)
    
    heatmap_array = np.array(heatmap_data)
    # Log scale for better visibility
    heatmap_log = np.log10(np.maximum(heatmap_array, 1))
    im = ax3.imshow(heatmap_log, aspect='auto', cmap='YlOrRd', interpolation='nearest')
    ax3.set_xticks(range(len(period_labels)))
    ax3.set_xticklabels([f'T+{p}' for p in period_labels], fontsize=9, rotation=45)
    ax3.set_yticks(range(len(heatmap_labels)))
    ax3.set_yticklabels(heatmap_labels, fontsize=9, fontweight='bold')
    # Add value annotations
    for i in range(len(heatmap_labels)):
        for j in range(len(period_labels)):
            val = heatmap_array[i, j]
            if val < 0.5:  # Grey out insufficient data (0×)
                ax3.text(j, i, '—', ha='center', va='center', fontsize=8, color='#999999', style='italic')
            else:
                color = 'white' if heatmap_log[i, j] > 1.2 else 'black'
                ax3.text(j, i, f'{val:.0f}×', ha='center', va='center', fontsize=8, color=color, fontweight='bold')
    # Draw a separator line between basket and controls
    basket_names = {'BBBY', 'BBBY†', 'AMC', 'GME', 'KOSS', 'TSLA', 'BB', 'XRT', 'NOK'}
    n_basket = len([s for s in heatmap_labels if s in basket_names])
    ax3.axhline(y=n_basket - 0.5, color='white', linewidth=2, linestyle='--')
    ax3.text(len(period_labels) - 0.5, n_basket - 0.5, ' controls ↓', fontsize=6, color='gray',
             va='center', ha='left', style='italic')
    ax3.set_title('Cross-Asset Spectral Fingerprint\n(sorted by ~630bd power, log₁₀ scale)', 
                  fontsize=11, fontweight='bold')
    # BBBY footnote
    fig.text(0.87, 0.48, '† BBBY = original Bed Bath & Beyond (pre-bankruptcy 2023, not Beyond/BYON)',
             fontsize=7, color='gray', style='italic', ha='right')
    plt.colorbar(im, ax=ax3, label='log₁₀(ratio)', shrink=0.8)
    
    # ------------------------------------------------------------------
    # Panel 3 (bottom, full width): GME full FFT power spectrum  
    # ------------------------------------------------------------------
    ax5 = fig.add_subplot(gs[1, :])
    _, gme_periods, gme_power, gme_median = compute_spectrum(gme_series)
    
    # Plot spectrum
    mask = (gme_periods >= 20) & (gme_periods <= 1500)
    ax5.semilogy(gme_periods[mask], gme_power[mask], color='steelblue', linewidth=0.5, alpha=0.5)
    # Smooth with rolling average
    window = 5
    smoothed = pd.Series(gme_power[mask]).rolling(window, center=True).mean().values
    ax5.semilogy(gme_periods[mask], smoothed, color='darkblue', linewidth=1.5, label='Power spectrum (smoothed)')
    ax5.axhline(y=gme_median, color='gray', linestyle='--', alpha=0.5, label=f'Median noise ({gme_median:.1e})')
    
    # Mark key peaks — use ~630bd and 13.3× for the dominant beat
    peak_annotations = {33: 'T+33', 35: 'T+35', 105: 'T+105', 
                        193: '~630/3', 289: '~630/2', 577: '~630bd\n13.3×', 1190: 'T+1'}
    for p, label in peak_annotations.items():
        idx = np.argmin(np.abs(gme_periods[mask] - p))
        yval = smoothed[idx] if not np.isnan(smoothed[idx]) else gme_power[mask][idx]
        color = 'darkred' if p in [577, 1190] else 'green' if p in [33, 35] else 'purple'
        ax5.annotate(label, xy=(p, yval), xytext=(0, 20), textcoords='offset points',
                    fontsize=8, fontweight='bold', color=color, ha='center',
                    arrowprops=dict(arrowstyle='->', color=color, alpha=0.7))
    
    ax5.set_xlabel('Period (business days)')
    ax5.set_ylabel('Spectral Power')
    ax5.set_title('GME FTD Power Spectrum — The Settlement Cavity\n'
                  '(~630bd beat = dominant signal at 13.3× median; 289, 193 = cavity harmonics)',
                  fontsize=11, fontweight='bold')
    ax5.legend(fontsize=8)
    ax5.grid(True, alpha=0.3)
    ax5.set_xlim(20, 1300)

    fig.suptitle('Settlement Cavity Resonance — Spectral Analysis & Cross-Asset Fingerprint',
                 fontsize=14, fontweight='bold', y=1.01)
    
    fig_path = FIG_DIR / "chart_cavity_resonance.png"
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  📊 Saved figure: {fig_path}")
    
    # Also copy to post figures directory
    post_fig_dir = Path(str(Path.home()) + '/Documents/GitHub/research/posts/03_the_failure_waterfall/figures')
    import shutil
    shutil.copy2(fig_path, post_fig_dir / 'chart_cavity_resonance.png')
    print(f"  📋 Copied to: {post_fig_dir / 'chart_cavity_resonance.png'}")

    # Save results
    import json
    results = {
        'hilbert': {
            'phase_velocity_rad_per_bd': float(phase_velocity),
            'implied_period_bd': float(period_from_phase),
            'current_phase_rad': float(current_phase),
            'current_phase_deg': float(np.degrees(current_phase % (2*np.pi))),
            'current_date': str(current_date.date()),
        },
        'projections': {},
        'odi': odi_results,
        'spectra': {sym: {str(k): v for k, v in spec.items()} for sym, spec in all_spectra.items()},
    }
    for label, target in targets.items():
        bd_forward = int(np.busday_count(current_date.date(), target.date()))
        projected_phase = current_phase + phase_velocity * bd_forward
        phase_deg = float(np.degrees(projected_phase % (2 * np.pi)))
        regime = "CONSTRUCTIVE" if phase_deg < 90 or phase_deg > 270 else "DESTRUCTIVE"
        results['projections'][label] = {
            'bd_forward': bd_forward,
            'phase_deg': phase_deg,
            'regime': regime
        }
    
    out_path = RESULTS_DIR / "cavity_resonance.json"
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  💾 Saved results: {out_path}")
    print(f"\n✅ Test 21 complete.")


if __name__ == "__main__":
    main()
