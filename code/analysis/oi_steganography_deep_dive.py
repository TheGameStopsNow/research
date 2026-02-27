#!/usr/bin/env python3
"""
Steganography Deep Dive — Phase 2
===================================
Follow-up analysis on the most significant findings from the initial scan:

1. Jan 25, 2021 bitstream dissection (lowest entropy day)
2. Phantom placement timing vs RK activity windows
3. Meme-number OI placements (6666, 420, 741, 69, etc.)
4. Intra-GME permutation control (shuffle strikes within each day)
5. Bitstream transition analysis (when does the signal "flip"?)
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
AGG_CSV = Path(__file__).resolve().parents[2] / "data" / "ftd" / "gme_options_oi_daily.csv"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results" / "oi_steganography"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_per_strike_oi():
    data = {}
    for f in sorted(OI_DIR.glob("oi_*.parquet")):
        date_str = f.stem.replace("oi_", "")
        try:
            df = pd.read_parquet(f)
            if len(df) > 0:
                data[date_str] = df
        except Exception:
            continue
    return data


# ═════════════════════════════════════════════════════════════════════════
# 1. JAN 25, 2021 BITSTREAM DISSECTION
# ═════════════════════════════════════════════════════════════════════════
def dissect_jan25_bitstream(data):
    """
    The lowest-entropy bitstream day. What exactly is happening?
    Map every strike to its put/call OI and the resulting bit.
    """
    print("\n" + "=" * 70)
    print("  1. JAN 25, 2021 BITSTREAM DISSECTION")
    print("=" * 70)

    # Analyze the full squeeze window
    squeeze_dates = [d for d in sorted(data.keys()) if "202101" in d]
    results = {}

    for date_str in squeeze_dates:
        df = data[date_str]
        pivot = df.pivot_table(index="strike", columns="right", 
                               values="open_interest", aggfunc="sum", fill_value=0)
        
        if "PUT" not in pivot.columns or "CALL" not in pivot.columns:
            continue

        strikes = sorted(pivot.index)
        total_put = 0
        total_call = 0
        put_dominant = 0
        call_dominant = 0
        strike_details = []

        for strike in strikes:
            p = int(pivot.loc[strike, "PUT"])
            c = int(pivot.loc[strike, "CALL"])
            total_put += p
            total_call += c
            bit = 1 if p > c else 0
            if p > c: put_dominant += 1
            else: call_dominant += 1
            
            if p > 1000 or c > 1000:  # Only show significant strikes
                strike_details.append({
                    "strike": float(strike),
                    "put_oi": p,
                    "call_oi": c,
                    "bit": bit,
                    "dominance": "PUT" if p > c else "CALL",
                    "ratio": round(p / max(c, 1), 2),
                })

        pct_put = put_dominant / len(strikes) * 100 if strikes else 0

        results[date_str] = {
            "n_strikes": len(strikes),
            "put_dominant": put_dominant,
            "call_dominant": call_dominant,
            "pct_put_dominant": round(pct_put, 1),
            "total_put_oi": total_put,
            "total_call_oi": total_call,
            "pc_ratio": round(total_put / max(total_call, 1), 3),
        }

        print(f"\n  {date_str}: {len(strikes)} strikes, "
              f"{put_dominant} put-dominant ({pct_put:.0f}%), "
              f"P/C ratio={total_put/max(total_call,1):.2f}")

        # Show the strike map for Jan 25 specifically
        if date_str == "20210125":
            print(f"\n    Strike-by-strike breakdown (OI > 1000):")
            print(f"    {'Strike':>8} | {'Put OI':>8} | {'Call OI':>8} | {'Bit':>3} | {'P/C':>6}")
            print(f"    {'-'*45}")
            for s in strike_details:
                marker = " 🔴" if s["ratio"] > 5 else ""
                print(f"    ${s['strike']:>6.0f} | {s['put_oi']:>8,} | {s['call_oi']:>8,} | "
                      f"  {s['bit']} | {s['ratio']:>5.1f}x{marker}")

    return results


# ═════════════════════════════════════════════════════════════════════════
# 2. MEME NUMBER HUNTING
# ═════════════════════════════════════════════════════════════════════════
def hunt_meme_numbers(data):
    """
    Search for exact meme-number OI values across all snapshots.
    Looking for: 420, 741, 69, 666, 1337, 6969, 7410, 4200, 42, 33.
    """
    print("\n" + "=" * 70)
    print("  2. MEME NUMBER HUNTING")
    print("=" * 70)

    meme_numbers = {420, 741, 69, 666, 1337, 6969, 7410, 4200, 42, 33, 
                    6666, 4206, 7414, 1234, 5678, 999, 111, 222, 333, 
                    444, 555, 777, 888}
    
    findings = []
    oi_value_counter = Counter()

    for date_str in sorted(data.keys()):
        df = data[date_str]
        for _, row in df.iterrows():
            oi = int(row["open_interest"])
            if oi in meme_numbers:
                findings.append({
                    "date": date_str,
                    "strike": float(row["strike"]),
                    "right": str(row["right"]),
                    "oi": oi,
                })
            if 10 <= oi <= 10000:
                oi_value_counter[oi] += 1

    print(f"  Meme number hits across {len(data)} snapshots: {len(findings)}")

    # Group by meme number
    by_number = defaultdict(list)
    for f in findings:
        by_number[f["oi"]].append(f)

    for num in sorted(by_number.keys()):
        hits = by_number[num]
        print(f"\n  OI = {num}: {len(hits)} occurrences")
        for h in hits[:5]:
            print(f"    {h['date']}: ${h['strike']:.0f} {h['right']}")
        if len(hits) > 5:
            print(f"    ... and {len(hits) - 5} more")

    # Expected frequency: how often does each number appear vs neighbors?
    print(f"\n  Meme number frequency vs neighbors:")
    for num in sorted(meme_numbers):
        actual = oi_value_counter.get(num, 0)
        # Compare to average of ±5 neighbors
        neighbors = [oi_value_counter.get(num + offset, 0) 
                     for offset in range(-5, 6) if offset != 0]
        expected = np.mean(neighbors) if neighbors else 0
        ratio = actual / max(expected, 0.1)
        marker = " ⚠️ EXCESS" if ratio > 2 and actual > 5 else ""
        marker = marker or (" 🔴 HIGH" if ratio > 3 and actual > 10 else "")
        if actual > 0:
            print(f"    OI={num:>5}: actual={actual:>4}, expected≈{expected:.1f}, "
                  f"ratio={ratio:.1f}x{marker}")

    return {
        "total_hits": len(findings),
        "by_number": {k: len(v) for k, v in by_number.items()},
        "findings_sample": findings[:50],
    }


# ═════════════════════════════════════════════════════════════════════════
# 3. PHANTOM PLACEMENT DEEP ANALYSIS
# ═════════════════════════════════════════════════════════════════════════
def phantom_deep_dive(data):
    """
    Extend phantom analysis: look for patterns in WHEN phantoms appear,
    their strike/expiration choices, and whether they cluster.
    """
    print("\n" + "=" * 70)
    print("  3. PHANTOM PLACEMENT DEEP DIVE")
    print("=" * 70)

    dates = sorted(data.keys())
    phantoms = []

    for i in range(1, len(dates) - 3):
        curr = data[dates[i]].groupby(["strike", "right"])["open_interest"].sum()
        prev = data[dates[i-1]].groupby(["strike", "right"])["open_interest"].sum()

        for (strike, right), oi in curr.items():
            prev_oi = prev.get((strike, right), 0)
            if oi > 50 and prev_oi < 5:
                # Check disappearance within 3 days
                for j in range(1, min(4, len(dates) - i)):
                    future = data[dates[i+j]].groupby(["strike", "right"])["open_interest"].sum()
                    future_oi = future.get((strike, right), 0)
                    if future_oi < 5:
                        phantoms.append({
                            "appear": dates[i],
                            "disappear": dates[i+j],
                            "duration": j,
                            "strike": float(strike),
                            "right": str(right),
                            "oi": int(oi),
                        })
                        break

    print(f"  Extended phantom search (threshold >50 OI): {len(phantoms)} found")

    # Day-of-week distribution
    dow_counts = Counter()
    for p in phantoms:
        dt = pd.Timestamp(datetime.strptime(p["appear"], "%Y%m%d"))
        dow_counts[dt.day_name()] += 1
    
    print(f"\n  Day-of-week distribution:")
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        count = dow_counts.get(day, 0)
        bar = "█" * count
        print(f"    {day:>9}: {count:>3} {bar}")

    # Monthly distribution
    month_counts = Counter()
    for p in phantoms:
        month = p["appear"][:6]
        month_counts[month] += 1
    
    print(f"\n  Monthly phantom count (top 15):")
    for month, count in month_counts.most_common(15):
        bar = "█" * count
        print(f"    {month}: {count:>3} {bar}")

    # Clustered phantoms (multiple appearing same day)
    day_counts = Counter(p["appear"] for p in phantoms)
    cluster_days = {d: c for d, c in day_counts.items() if c >= 3}
    
    if cluster_days:
        print(f"\n  Cluster days (≥3 phantoms appearing):")
        for day, count in sorted(cluster_days.items(), key=lambda x: x[1], reverse=True):
            day_phantoms = [p for p in phantoms if p["appear"] == day]
            strikes = [f"${p['strike']:.0f}{p['right'][0]}" for p in day_phantoms]
            print(f"    {day}: {count} phantoms at {', '.join(strikes[:8])}")

    # Strike clustering: are phantoms concentrated at specific strikes?
    phantom_strike_freq = Counter(p["strike"] for p in phantoms)
    print(f"\n  Most frequent phantom strikes:")
    for strike, count in phantom_strike_freq.most_common(15):
        print(f"    ${strike:.0f}: {count} phantoms")

    # Check for sequential strike patterns (e.g., 3, 3.5, 4 appearing on same day)
    print(f"\n  Sequential strike patterns (same day):")
    for day in sorted(set(p["appear"] for p in phantoms)):
        day_strikes = sorted(set(p["strike"] for p in phantoms if p["appear"] == day))
        if len(day_strikes) >= 3:
            # Check for arithmetic sequences
            diffs = [day_strikes[i+1] - day_strikes[i] for i in range(len(day_strikes)-1)]
            if len(set(diffs)) == 1 and len(diffs) >= 2:
                print(f"    {day}: arithmetic sequence ${day_strikes} (step={diffs[0]})")

    return {
        "total_phantoms": len(phantoms),
        "dow_distribution": dict(dow_counts),
        "monthly_distribution": dict(month_counts.most_common(20)),
        "cluster_days": cluster_days,
        "top_phantom_strikes": dict(phantom_strike_freq.most_common(20)),
        "phantoms": phantoms,
    }


# ═════════════════════════════════════════════════════════════════════════
# 4. INTRA-GME PERMUTATION CONTROL
# ═════════════════════════════════════════════════════════════════════════
def permutation_control(data):
    """
    Instead of comparing to SPY/AAPL, we shuffle the put/call labels 
    within each day to create a synthetic control.
    If the structure persists after shuffling, it's inherent to the 
    strike distribution, not to the P/C assignment.
    """
    print("\n" + "=" * 70)
    print("  4. INTRA-GME PERMUTATION CONTROL")
    print("=" * 70)

    def compute_bitstream_entropy(df):
        pivot = df.pivot_table(index="strike", columns="right", 
                               values="open_interest", aggfunc="sum", fill_value=0)
        if "PUT" not in pivot.columns or "CALL" not in pivot.columns:
            return None
        strikes = sorted(pivot.index)
        bits = []
        for strike in strikes:
            p = pivot.loc[strike, "PUT"] if "PUT" in pivot.columns else 0
            c = pivot.loc[strike, "CALL"] if "CALL" in pivot.columns else 0
            bits.append(1 if p > c else 0)
        bitstream = "".join(str(b) for b in bits)
        if len(bitstream) == 0:
            return None
        freq = Counter(bitstream)
        total = len(bitstream)
        entropy = -sum((v/total) * np.log2(v/total) for v in freq.values() if v > 0)
        return entropy

    dates = sorted(data.keys())
    real_entropies = []
    shuffled_entropies = []

    n_shuffle = 100
    print(f"  Running {n_shuffle} permutations per day...")

    for date_str in dates:
        df = data[date_str]
        real_e = compute_bitstream_entropy(df)
        if real_e is None:
            continue
        real_entropies.append(real_e)

        # Shuffle: randomly reassign the "right" column
        day_shuffled = []
        for _ in range(n_shuffle):
            df_shuf = df.copy()
            df_shuf["right"] = np.random.permutation(df_shuf["right"].values)
            shuf_e = compute_bitstream_entropy(df_shuf)
            if shuf_e is not None:
                day_shuffled.append(shuf_e)
        
        if day_shuffled:
            shuffled_entropies.extend(day_shuffled)

    real_mean = np.mean(real_entropies)
    shuf_mean = np.mean(shuffled_entropies)
    shuf_std = np.std(shuffled_entropies)
    z_score = (real_mean - shuf_mean) / shuf_std if shuf_std > 0 else 0

    print(f"\n  Real mean entropy:     {real_mean:.4f}")
    print(f"  Shuffled mean entropy: {shuf_mean:.4f} ± {shuf_std:.4f}")
    print(f"  Z-score:               {z_score:.2f}")

    if z_score < -2:
        print(f"\n  ⚠️ SIGNIFICANT: Real bitstreams are MORE structured than shuffled controls.")
        print(f"     This means the put/call assignment is NOT random — puts and calls")
        print(f"     cluster at specific parts of the strike ladder in a non-random way.")
        print(f"     However, this could reflect market mechanics (deep OTM puts naturally")
        print(f"     dominate low strikes) rather than intentional signaling.")
    elif z_score > 2:
        print(f"\n  Real bitstreams are LESS structured than controls — unexpected.")
    else:
        print(f"\n  No significant difference between real and shuffled bitstreams.")

    # Regime analysis: compare different periods
    print(f"\n  Regime comparison:")
    regimes = {
        "Pre-squeeze (2020)": [d for d in dates if d.startswith("2020")],
        "Squeeze (Jan 2021)": [d for d in dates if d.startswith("20210")],
        "Post-split (2023)": [d for d in dates if d.startswith("2023")],
        "RK Return (May-Jun 2024)": [d for d in dates if d[:6] in ("202405", "202406")],
        "Quiet (Jul-Oct 2024)": [d for d in dates if d[:6] in ("202407", "202408", "202409", "202410")],
        "Recent (2025)": [d for d in dates if d.startswith("2025")],
    }

    regime_results = {}
    for regime_name, regime_dates in regimes.items():
        if not regime_dates:
            continue
        r_ents = []
        for d in regime_dates:
            if d in data:
                e = compute_bitstream_entropy(data[d])
                if e is not None:
                    r_ents.append(e)
        if r_ents:
            mean_e = np.mean(r_ents)
            regime_results[regime_name] = mean_e
            marker = " 🔴" if mean_e < 0.75 else " ⚠️" if mean_e < 0.85 else ""
            print(f"    {regime_name:30s}: entropy={mean_e:.4f} ({len(r_ents)} days){marker}")

    return {
        "real_mean_entropy": real_mean,
        "shuffled_mean_entropy": shuf_mean,
        "z_score": z_score,
        "regime_entropies": regime_results,
    }


# ═════════════════════════════════════════════════════════════════════════
# 5. BITSTREAM TRANSITION ANALYSIS
# ═════════════════════════════════════════════════════════════════════════
def bitstream_transitions(data):
    """
    Track how the bitstream CHANGES day-to-day.
    Where do bits flip? Does the transition pattern carry information?
    """
    print("\n" + "=" * 70)
    print("  5. BITSTREAM TRANSITION ANALYSIS")
    print("=" * 70)

    dates = sorted(data.keys())
    transition_log = []
    prev_bits = None
    prev_date = None

    for date_str in dates:
        df = data[date_str]
        pivot = df.pivot_table(index="strike", columns="right",
                               values="open_interest", aggfunc="sum", fill_value=0)
        if "PUT" not in pivot.columns or "CALL" not in pivot.columns:
            continue

        strikes = sorted(pivot.index)
        bits = {}
        for strike in strikes:
            p = pivot.loc[strike, "PUT"] if "PUT" in pivot.columns else 0
            c = pivot.loc[strike, "CALL"] if "CALL" in pivot.columns else 0
            bits[strike] = 1 if p > c else 0

        if prev_bits is not None:
            # Find flipped bits
            common_strikes = set(bits.keys()) & set(prev_bits.keys())
            flips = []
            for strike in sorted(common_strikes):
                if bits[strike] != prev_bits[strike]:
                    flips.append({
                        "strike": float(strike),
                        "from": prev_bits[strike],
                        "to": bits[strike],
                    })
            
            if flips:
                transition_log.append({
                    "date": date_str,
                    "prev_date": prev_date,
                    "n_flips": len(flips),
                    "n_strikes": len(common_strikes),
                    "flip_rate": len(flips) / len(common_strikes) if common_strikes else 0,
                    "flips": flips,
                })

        prev_bits = bits
        prev_date = date_str

    if not transition_log:
        print("  No transitions found")
        return {}

    # Statistics
    flip_rates = [t["flip_rate"] for t in transition_log]
    n_flips = [t["n_flips"] for t in transition_log]

    print(f"  Total transition days: {len(transition_log)}")
    print(f"  Mean flip rate: {np.mean(flip_rates):.4f}")
    print(f"  Mean flips per day: {np.mean(n_flips):.1f}")

    # High-transition days (most bits flipping at once)
    transition_log.sort(key=lambda x: x["n_flips"], reverse=True)
    print(f"\n  Top 15 high-transition days:")
    for t in transition_log[:15]:
        flip_strikes = [f"${f['strike']:.0f}" for f in t["flips"][:5]]
        print(f"    {t['date']}: {t['n_flips']} flips ({t['flip_rate']:.3f}) "
              f"at {', '.join(flip_strikes)}{'...' if len(t['flips']) > 5 else ''}")

    # Which strikes flip most often?
    flip_counter = Counter()
    for t in transition_log:
        for f in t["flips"]:
            flip_counter[f["strike"]] += 1

    print(f"\n  Most frequently flipping strikes:")
    for strike, count in flip_counter.most_common(15):
        total_days = len(transition_log)
        pct = count / total_days * 100
        print(f"    ${strike:.0f}: {count} flips ({pct:.1f}% of days)")

    # Direction of flips: are certain strikes consistently flipping one way?
    flip_direction = defaultdict(lambda: {"to_put": 0, "to_call": 0})
    for t in transition_log:
        for f in t["flips"]:
            if f["to"] == 1:
                flip_direction[f["strike"]]["to_put"] += 1
            else:
                flip_direction[f["strike"]]["to_call"] += 1

    print(f"\n  Directional flip bias (top 10 flippers):")
    for strike, count in flip_counter.most_common(10):
        d = flip_direction[strike]
        total = d["to_put"] + d["to_call"]
        bias = d["to_put"] / total if total > 0 else 0.5
        direction = "PUT-biased" if bias > 0.6 else "CALL-biased" if bias < 0.4 else "Balanced"
        print(f"    ${strike:.0f}: {d['to_put']}→PUT, {d['to_call']}→CALL ({direction})")

    return {
        "total_transitions": len(transition_log),
        "mean_flip_rate": float(np.mean(flip_rates)),
        "mean_flips_per_day": float(np.mean(n_flips)),
        "top_transition_days": [
            {"date": t["date"], "n_flips": t["n_flips"], "flip_rate": t["flip_rate"]}
            for t in transition_log[:20]
        ],
        "most_flipping_strikes": dict(flip_counter.most_common(20)),
    }


# ═════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  STEGANOGRAPHY DEEP DIVE — PHASE 2")
    print("=" * 70)

    print("\n  Loading per-strike OI data...")
    data = load_per_strike_oi()
    print(f"  Loaded {len(data)} daily snapshots")

    results = {}
    results["jan25_dissection"] = dissect_jan25_bitstream(data)
    results["meme_numbers"] = hunt_meme_numbers(data)
    results["phantom_deep_dive"] = phantom_deep_dive(data)
    results["permutation_control"] = permutation_control(data)
    results["bitstream_transitions"] = bitstream_transitions(data)

    # Save
    out_path = RESULTS_DIR / "steganography_deep_dive.json"
    def convert(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, pd.Timestamp): return str(obj)
        return str(obj)
    
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=convert)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
