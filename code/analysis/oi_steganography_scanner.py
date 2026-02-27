#!/usr/bin/env python3
"""
Options Chain Steganography Scanner
====================================
Scans 593 per-strike GME options OI snapshots for hidden steganographic signals.

Five orthogonal encoding layers:
  A) Known-number lot sizes (Fibonacci, 741, 420, primes, etc.)
  B) Morse code from OI direction changes
  C) Strike alphabet mapping (anomalous strikes → characters)
  D) Put/Call bitstream decoder (P-dominant=1, C-dominant=0 across strikes)
  E) Temporal cadence (inter-arrival time clustering)

Includes Monte Carlo null-hypothesis test for each layer.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ─── Config ──────────────────────────────────────────────────────────────
OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
AGG_CSV = Path(__file__).resolve().parents[2] / "data" / "ftd" / "gme_options_oi_daily.csv"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results" / "oi_steganography"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

N_MONTE_CARLO = 5000  # null hypothesis permutations

# Known signal numbers from RK lore and market culture
SIGNAL_NUMBERS = {
    741, 420, 69, 33, 42, 13, 7, 21, 34, 55, 89, 144, 233, 377, 610,
    # Fibonacci sequence
    1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987,
    # Powers of 2
    2, 4, 8, 16, 32, 64, 128, 256, 512, 1024,
    # RK-specific
    741, 420, 69, 33, 7, 4, 1,
    # Meme numbers
    42, 1337, 6969, 4200, 7410,
}

# Fibonacci set for fast lookup
FIB_SET = set()
a, b = 1, 1
while a <= 100000:
    FIB_SET.add(a)
    a, b = b, a + b

# Primes up to 1000
def _sieve(n):
    s = [True] * (n + 1)
    s[0] = s[1] = False
    for i in range(2, int(n**0.5) + 1):
        if s[i]:
            for j in range(i*i, n + 1, i):
                s[j] = False
    return {i for i, v in enumerate(s) if v}

PRIMES = _sieve(2000)

# Morse code table
MORSE = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
    '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
    '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
    '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
    '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
    '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
    '...--': '3', '....-': '4', '.....': '5', '-....': '6',
    '--...': '7', '---..': '8', '----.': '9',
}


# ─── Data Loading ────────────────────────────────────────────────────────
def load_per_strike_oi():
    """Load all per-strike OI parquet files into a dict keyed by date string."""
    data = {}
    files = sorted(OI_DIR.glob("oi_*.parquet"))
    for f in files:
        date_str = f.stem.replace("oi_", "")
        try:
            df = pd.read_parquet(f)
            if len(df) > 0:
                data[date_str] = df
        except Exception:
            continue
    return data


def load_aggregate_oi():
    """Load the aggregate daily OI CSV."""
    if AGG_CSV.exists():
        return pd.read_csv(AGG_CSV, parse_dates=["date"])
    return pd.DataFrame()


# ═════════════════════════════════════════════════════════════════════════
# LAYER A: Known-Number Lot Size Detection
# ═════════════════════════════════════════════════════════════════════════
def layer_a_known_numbers(data):
    """
    For each day, compute per-strike OI deltas.
    Check if absolute delta values match known signal numbers.
    """
    print("\n" + "=" * 70)
    print("  LAYER A: Known-Number Lot Size Detection")
    print("=" * 70)

    dates = sorted(data.keys())
    hits = defaultdict(list)
    daily_hit_rate = []
    all_deltas = []

    for i in range(1, len(dates)):
        prev_date, curr_date = dates[i - 1], dates[i]
        prev_df, curr_df = data[prev_date], data[curr_date]

        # Merge on strike + right to compute deltas
        merged = pd.merge(
            curr_df.groupby(["strike", "right"])["open_interest"].sum().reset_index(),
            prev_df.groupby(["strike", "right"])["open_interest"].sum().reset_index(),
            on=["strike", "right"],
            suffixes=("_curr", "_prev"),
            how="outer",
        ).fillna(0)

        merged["delta"] = merged["open_interest_curr"] - merged["open_interest_prev"]
        abs_deltas = merged["delta"].abs().astype(int)
        abs_deltas = abs_deltas[abs_deltas > 0]

        if len(abs_deltas) == 0:
            continue

        all_deltas.extend(abs_deltas.tolist())

        # Check for known numbers
        n_hits = 0
        for idx, row in merged.iterrows():
            d = abs(int(row["delta"]))
            if d == 0:
                continue
            is_signal = (
                d in SIGNAL_NUMBERS
                or d in FIB_SET
                or d in PRIMES
            )
            if is_signal:
                n_hits += 1
                hits[curr_date].append({
                    "strike": float(row["strike"]),
                    "right": str(row["right"]),
                    "delta": int(row["delta"]),
                    "match_type": (
                        "SIGNAL" if d in SIGNAL_NUMBERS
                        else "FIBONACCI" if d in FIB_SET
                        else "PRIME"
                    ),
                })

        hit_rate = n_hits / len(abs_deltas) if len(abs_deltas) > 0 else 0
        daily_hit_rate.append({
            "date": curr_date,
            "n_deltas": len(abs_deltas),
            "n_hits": n_hits,
            "hit_rate": hit_rate,
        })

    # Monte Carlo null hypothesis
    print(f"  Computing Monte Carlo baseline ({N_MONTE_CARLO} permutations)...")
    real_overall_rate = sum(d["n_hits"] for d in daily_hit_rate) / max(1, sum(d["n_deltas"] for d in daily_hit_rate))
    mc_rates = []
    all_deltas_arr = np.array(all_deltas)
    for _ in range(N_MONTE_CARLO):
        shuffled = np.random.choice(all_deltas_arr, size=min(5000, len(all_deltas_arr)), replace=True)
        mc_hits = sum(1 for d in shuffled if d in SIGNAL_NUMBERS or d in FIB_SET or d in PRIMES)
        mc_rates.append(mc_hits / len(shuffled))

    mc_mean = np.mean(mc_rates)
    mc_std = np.std(mc_rates)
    z_score = (real_overall_rate - mc_mean) / mc_std if mc_std > 0 else 0
    p_value = np.mean([r >= real_overall_rate for r in mc_rates])

    # Top anomaly days (highest hit rate)
    top_days = sorted(daily_hit_rate, key=lambda x: x["hit_rate"], reverse=True)[:20]

    print(f"\n  Real hit rate:  {real_overall_rate:.4f}")
    print(f"  MC baseline:    {mc_mean:.4f} ± {mc_std:.4f}")
    print(f"  Z-score:        {z_score:.2f}")
    print(f"  p-value:        {p_value:.4f}")
    print(f"\n  Top 20 anomaly days:")
    for d in top_days:
        print(f"    {d['date']}: {d['n_hits']}/{d['n_deltas']} = {d['hit_rate']:.3f}")

    return {
        "real_hit_rate": real_overall_rate,
        "mc_mean": mc_mean,
        "mc_std": mc_std,
        "z_score": z_score,
        "p_value": p_value,
        "top_days": top_days[:20],
        "total_deltas": len(all_deltas),
        "total_hits": sum(d["n_hits"] for d in daily_hit_rate),
        "top_hit_details": {k: v[:5] for k, v in sorted(hits.items(), key=lambda x: len(x[1]), reverse=True)[:10]},
    }


# ═════════════════════════════════════════════════════════════════════════
# LAYER B: Morse Code from OI Direction Changes
# ═════════════════════════════════════════════════════════════════════════
def layer_b_morse_code(agg_df):
    """
    Convert daily total OI changes to dots and dashes.
    Big positive = dot (.), big negative = dash (-), small = gap.
    Try to decode as Morse.
    """
    print("\n" + "=" * 70)
    print("  LAYER B: Morse Code OI Direction Test")
    print("=" * 70)

    if agg_df.empty:
        print("  No aggregate data available")
        return {}

    df = agg_df.copy().sort_values("date").reset_index(drop=True)
    df["oi_delta"] = df["total_oi"].diff()
    df = df.dropna(subset=["oi_delta"])

    # Method 1: Direction-based (up=dot, down=dash)
    df["symbol"] = df["oi_delta"].apply(lambda x: "." if x > 0 else "-" if x < 0 else " ")
    direction_stream = "".join(df["symbol"].tolist())

    # Method 2: Magnitude-based (above median abs = dash, below = dot)
    median_abs = df["oi_delta"].abs().median()
    df["mag_symbol"] = df["oi_delta"].abs().apply(lambda x: "-" if x > median_abs else ".")
    magnitude_stream = "".join(df["mag_symbol"].tolist())

    # Method 3: Sliding window decode (try windows of 1-5 chars)
    decoded_fragments = []
    for stream_name, stream in [("direction", direction_stream), ("magnitude", magnitude_stream)]:
        # Try to find valid Morse sequences
        found = []
        for window_size in range(1, 6):
            for start in range(len(stream) - window_size + 1):
                chunk = stream[start : start + window_size]
                if chunk in MORSE:
                    found.append({
                        "stream": stream_name,
                        "position": start,
                        "code": chunk,
                        "letter": MORSE[chunk],
                        "date": str(df.iloc[start]["date"].date()) if start < len(df) else "?",
                    })
        decoded_fragments.extend(found)

    # Entropy analysis
    from collections import Counter
    dir_entropy = _entropy(direction_stream)
    mag_entropy = _entropy(magnitude_stream)

    # Monte Carlo: generate random direction streams, compute Morse hit rate
    real_hits = sum(1 for f in decoded_fragments if f["stream"] == "direction")
    mc_hits = []
    for _ in range(N_MONTE_CARLO):
        fake = "".join(np.random.choice([".", "-"], size=len(direction_stream)))
        count = 0
        for ws in range(1, 6):
            for s in range(len(fake) - ws + 1):
                if fake[s : s + ws] in MORSE:
                    count += 1
        mc_hits.append(count)

    mc_mean = np.mean(mc_hits)
    mc_std = np.std(mc_hits)
    z_score = (real_hits - mc_mean) / mc_std if mc_std > 0 else 0

    print(f"  Direction stream length: {len(direction_stream)}")
    print(f"  Direction entropy: {dir_entropy:.4f} (random binary ≈ 1.0)")
    print(f"  Magnitude entropy: {mag_entropy:.4f}")
    print(f"  Morse fragments found: {len(decoded_fragments)}")
    print(f"  MC baseline hits: {mc_mean:.1f} ± {mc_std:.1f}")
    print(f"  Z-score: {z_score:.2f}")

    # Try to read longest coherent sequences
    coherent = _find_coherent_morse(direction_stream)
    print(f"\n  Longest coherent Morse sequences (direction-based):")
    for seq in coherent[:10]:
        print(f"    Position {seq['start']}: '{seq['decoded']}' from '{seq['code']}'")

    return {
        "direction_entropy": dir_entropy,
        "magnitude_entropy": mag_entropy,
        "total_fragments": len(decoded_fragments),
        "mc_mean_hits": mc_mean,
        "z_score": z_score,
        "coherent_sequences": coherent[:20],
        "direction_stream_sample": direction_stream[:200],
        "magnitude_stream_sample": magnitude_stream[:200],
    }


def _entropy(s):
    """Shannon entropy of a string."""
    freq = Counter(s)
    total = len(s)
    return -sum((c / total) * np.log2(c / total) for c in freq.values() if c > 0)


def _find_coherent_morse(stream):
    """Try to decode consecutive Morse characters from the stream."""
    results = []
    i = 0
    while i < len(stream):
        best_match = None
        for length in range(5, 0, -1):
            chunk = stream[i : i + length]
            if chunk in MORSE:
                best_match = (chunk, MORSE[chunk], length)
                break
        if best_match:
            code, letter, length = best_match
            # Look for consecutive matches
            decoded = letter
            codes = code
            pos = i + length
            while pos < len(stream):
                found = False
                for l2 in range(5, 0, -1):
                    c2 = stream[pos : pos + l2]
                    if c2 in MORSE:
                        decoded += MORSE[c2]
                        codes += "|" + c2
                        pos += l2
                        found = True
                        break
                if not found:
                    break
            if len(decoded) >= 3:
                results.append({"start": i, "decoded": decoded, "code": codes, "length": len(decoded)})
        i += 1
    results.sort(key=lambda x: x["length"], reverse=True)
    return results


# ═════════════════════════════════════════════════════════════════════════
# LAYER C: Strike Alphabet Mapping
# ═════════════════════════════════════════════════════════════════════════
def layer_c_strike_alphabet(data):
    """
    Find strikes with anomalous OI changes.
    Map the anomalous strike sequence to characters.
    """
    print("\n" + "=" * 70)
    print("  LAYER C: Strike Alphabet Mapping")
    print("=" * 70)

    dates = sorted(data.keys())
    daily_anomalies = {}

    # Build rolling stats per strike
    strike_history = defaultdict(list)
    for date_str in dates:
        df = data[date_str]
        agg = df.groupby("strike")["open_interest"].sum()
        for strike, oi in agg.items():
            strike_history[strike].append((date_str, oi))

    # For each day, find strikes where OI deviates >2σ from rolling mean
    for i in range(20, len(dates)):  # need history
        curr_date = dates[i]
        curr_df = data[curr_date]
        curr_agg = curr_df.groupby("strike")["open_interest"].sum()

        anomalous_strikes = []
        for strike, oi in curr_agg.items():
            history = [v for d, v in strike_history[strike] if d < curr_date]
            if len(history) < 10:
                continue
            recent = history[-20:]
            mean_oi = np.mean(recent)
            std_oi = np.std(recent)
            if std_oi > 0 and abs(oi - mean_oi) > 2 * std_oi:
                z = (oi - mean_oi) / std_oi
                anomalous_strikes.append({
                    "strike": float(strike),
                    "oi": int(oi),
                    "z_score": round(z, 2),
                    "direction": "UP" if z > 0 else "DOWN",
                })

        if anomalous_strikes:
            anomalous_strikes.sort(key=lambda x: abs(x["z_score"]), reverse=True)
            daily_anomalies[curr_date] = anomalous_strikes

    # Map anomalous strikes to characters
    print(f"  Days with anomalous strikes: {len(daily_anomalies)}")

    # Direct numeric reading: take the integer part of the top anomalous strike
    numeric_messages = {}
    for date_str, strikes in sorted(daily_anomalies.items()):
        top_strikes = [s["strike"] for s in strikes[:3]]
        numeric_msg = "-".join(str(int(s)) for s in top_strikes)
        numeric_messages[date_str] = numeric_msg

    # ASCII mapping: strike $65 = 'A', etc.
    ascii_messages = {}
    for date_str, strikes in sorted(daily_anomalies.items()):
        chars = []
        for s in strikes[:5]:
            code = int(s["strike"])
            if 32 <= code <= 126:
                chars.append(chr(code))
            else:
                chars.append("?")
        ascii_messages[date_str] = "".join(chars)

    # Phone keypad: 2=ABC, 3=DEF, 4=GHI, 5=JKL, 6=MNO, 7=PQRS, 8=TUV, 9=WXYZ
    keypad = {2: "ABC", 3: "DEF", 4: "GHI", 5: "JKL", 6: "MNO", 7: "PQRS", 8: "TUV", 9: "WXYZ"}

    # Print samples
    print(f"\n  Sample numeric readings (top 3 anomalous strikes per day):")
    for date_str in sorted(numeric_messages.keys())[-30:]:
        anom = daily_anomalies[date_str]
        z_max = max(abs(s["z_score"]) for s in anom)
        print(f"    {date_str}: strikes={numeric_messages[date_str]}  "
              f"(max_z={z_max:.1f}, ascii='{ascii_messages.get(date_str, '?')}')")

    # Entropy of strike sequences
    all_top_strikes = [s["strike"] for strikes in daily_anomalies.values() for s in strikes[:1]]
    if all_top_strikes:
        strike_entropy = _entropy("".join(str(int(s)) for s in all_top_strikes))
    else:
        strike_entropy = 0

    print(f"\n  Strike sequence entropy: {strike_entropy:.4f}")

    return {
        "days_with_anomalies": len(daily_anomalies),
        "strike_entropy": strike_entropy,
        "numeric_messages_sample": dict(list(sorted(numeric_messages.items()))[-30:]),
        "ascii_messages_sample": dict(list(sorted(ascii_messages.items()))[-30:]),
        "top_anomaly_days": {
            k: v[:3] for k, v in sorted(
                daily_anomalies.items(),
                key=lambda x: max(abs(s["z_score"]) for s in x[1]),
                reverse=True,
            )[:20]
        },
    }


# ═════════════════════════════════════════════════════════════════════════
# LAYER D: Put/Call Bitstream Decoder
# ═════════════════════════════════════════════════════════════════════════
def layer_d_putcall_bitstream(data):
    """
    For each day, walk the strike ladder.
    At each strike: Put-dominant OI → 1, Call-dominant → 0.
    Read as bitstream, analyze for structure.
    """
    print("\n" + "=" * 70)
    print("  LAYER D: Put/Call Bitstream Decoder")
    print("=" * 70)

    dates = sorted(data.keys())
    daily_bitstreams = {}
    daily_entropy = []

    for date_str in dates:
        df = data[date_str]
        # Aggregate by strike and right
        pivot = df.pivot_table(index="strike", columns="right", values="open_interest", aggfunc="sum", fill_value=0)

        if "PUT" not in pivot.columns or "CALL" not in pivot.columns:
            continue

        # Walk strikes in order
        strikes = sorted(pivot.index)
        bits = []
        for strike in strikes:
            put_oi = pivot.loc[strike, "PUT"] if "PUT" in pivot.columns else 0
            call_oi = pivot.loc[strike, "CALL"] if "CALL" in pivot.columns else 0
            bit = 1 if put_oi > call_oi else 0
            bits.append(bit)

        bitstream = "".join(str(b) for b in bits)
        daily_bitstreams[date_str] = bitstream

        # Entropy
        if len(bitstream) > 0:
            e = _entropy(bitstream)
            daily_entropy.append({"date": date_str, "entropy": e, "length": len(bitstream)})

    # Analyze bitstreams for ASCII decoding
    ascii_messages = {}
    for date_str, bs in daily_bitstreams.items():
        # Try 8-bit ASCII chunks
        chars = []
        for i in range(0, len(bs) - 7, 8):
            byte = bs[i : i + 8]
            val = int(byte, 2)
            if 32 <= val <= 126:
                chars.append(chr(val))
            else:
                chars.append("·")
        if chars:
            ascii_messages[date_str] = "".join(chars)

    # Find days with lowest entropy (most structured bitstreams)
    daily_entropy.sort(key=lambda x: x["entropy"])
    low_entropy_days = daily_entropy[:20]

    # Find repeating patterns
    pattern_counts = Counter()
    for bs in daily_bitstreams.values():
        for plen in [4, 8, 16]:
            for i in range(len(bs) - plen + 1):
                pattern = bs[i : i + plen]
                pattern_counts[pattern] += 1

    most_common_patterns = pattern_counts.most_common(20)

    # Monte Carlo: compare entropy distribution to random bitstreams
    real_mean_entropy = np.mean([e["entropy"] for e in daily_entropy]) if daily_entropy else 0
    mc_entropies = []
    typical_len = int(np.median([e["length"] for e in daily_entropy])) if daily_entropy else 30
    for _ in range(N_MONTE_CARLO):
        fake = "".join(str(b) for b in np.random.randint(0, 2, typical_len))
        mc_entropies.append(_entropy(fake))
    mc_mean_e = np.mean(mc_entropies)
    mc_std_e = np.std(mc_entropies)
    z_score = (real_mean_entropy - mc_mean_e) / mc_std_e if mc_std_e > 0 else 0

    print(f"  Total days analyzed: {len(daily_bitstreams)}")
    print(f"  Mean bitstream entropy: {real_mean_entropy:.4f}")
    print(f"  Random baseline entropy: {mc_mean_e:.4f} ± {mc_std_e:.4f}")
    print(f"  Z-score (lower = more structured): {z_score:.2f}")

    print(f"\n  Lowest entropy days (most structured):")
    for d in low_entropy_days[:10]:
        bs = daily_bitstreams[d["date"]]
        ascii_msg = ascii_messages.get(d["date"], "")
        print(f"    {d['date']}: entropy={d['entropy']:.4f}, "
              f"bits={bs[:40]}..., ascii='{ascii_msg[:20]}'")

    print(f"\n  Most repeating 8-bit patterns:")
    for pat, count in most_common_patterns[:10]:
        val = int(pat, 2) if len(pat) <= 8 else "?"
        char = chr(val) if isinstance(val, int) and 32 <= val <= 126 else "·"
        print(f"    {pat} (={val}, '{char}'): {count} occurrences")

    return {
        "total_days": len(daily_bitstreams),
        "mean_entropy": real_mean_entropy,
        "mc_baseline_entropy": mc_mean_e,
        "z_score": z_score,
        "low_entropy_days": low_entropy_days[:20],
        "ascii_messages_sample": dict(list(sorted(ascii_messages.items()))[-20:]),
        "repeating_patterns": [(p, c) for p, c in most_common_patterns[:20]],
        "bitstream_sample": {k: v[:64] for k, v in list(sorted(daily_bitstreams.items()))[-10:]},
    }


# ═════════════════════════════════════════════════════════════════════════
# LAYER E: Temporal Cadence (Morse-like Timing)
# ═════════════════════════════════════════════════════════════════════════
def layer_e_temporal_cadence(agg_df, data):
    """
    Analyze timing of large OI spikes.
    Map to inter-arrival times. Test for Morse-like clustering:
    dot=1 unit, dash=3 units, letter gap=3 units, word gap=7 units.
    """
    print("\n" + "=" * 70)
    print("  LAYER E: Temporal Cadence Analysis")
    print("=" * 70)

    if agg_df.empty:
        print("  No aggregate data available")
        return {}

    df = agg_df.copy().sort_values("date").reset_index(drop=True)
    df["oi_delta"] = df["total_oi"].diff()
    df["abs_delta"] = df["oi_delta"].abs()
    df = df.dropna(subset=["oi_delta"])

    # Define "spike" as abs delta > 75th percentile
    threshold = df["abs_delta"].quantile(0.75)
    spikes = df[df["abs_delta"] > threshold].copy()

    print(f"  Spike threshold (75th pct): {threshold:,.0f}")
    print(f"  Number of spikes: {len(spikes)}")

    if len(spikes) < 5:
        return {"error": "Too few spikes for analysis"}

    # Compute inter-arrival times (in business days)
    spike_indices = spikes.index.tolist()
    inter_arrivals = [spike_indices[i] - spike_indices[i - 1] for i in range(1, len(spike_indices))]

    # Morse timing: look for clustering at 1, 3, 7 day intervals
    ia_arr = np.array(inter_arrivals)
    hist, bins = np.histogram(ia_arr, bins=range(1, max(ia_arr) + 2))

    print(f"\n  Inter-arrival distribution (business days):")
    for i, count in enumerate(hist[:15]):
        bar = "█" * count
        print(f"    {i+1:2d} days: {count:3d} {bar}")

    # Test for clustering at Morse intervals (1, 3, 7)
    morse_intervals = {1, 3, 7}
    morse_hits = sum(1 for ia in inter_arrivals if ia in morse_intervals)
    morse_rate = morse_hits / len(inter_arrivals) if inter_arrivals else 0

    # Monte Carlo: random spike positions
    mc_morse_rates = []
    for _ in range(N_MONTE_CARLO):
        fake_spikes = sorted(np.random.choice(range(len(df)), size=len(spikes), replace=False))
        fake_ia = [fake_spikes[i] - fake_spikes[i - 1] for i in range(1, len(fake_spikes))]
        fake_hits = sum(1 for ia in fake_ia if ia in morse_intervals)
        mc_morse_rates.append(fake_hits / len(fake_ia) if fake_ia else 0)

    mc_mean = np.mean(mc_morse_rates)
    mc_std = np.std(mc_morse_rates)
    z_score = (morse_rate - mc_mean) / mc_std if mc_std > 0 else 0

    print(f"\n  Morse interval hits (1,3,7 days): {morse_hits}/{len(inter_arrivals)} = {morse_rate:.3f}")
    print(f"  MC baseline: {mc_mean:.3f} ± {mc_std:.3f}")
    print(f"  Z-score: {z_score:.2f}")

    # Autocorrelation of inter-arrival times
    if len(ia_arr) > 10:
        autocorr = np.correlate(ia_arr - ia_arr.mean(), ia_arr - ia_arr.mean(), mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]
        autocorr = autocorr / autocorr[0] if autocorr[0] != 0 else autocorr
        significant_lags = [(lag, ac) for lag, ac in enumerate(autocorr[:20]) if abs(ac) > 0.15 and lag > 0]
    else:
        significant_lags = []

    print(f"\n  Significant autocorrelation lags:")
    for lag, ac in significant_lags:
        print(f"    Lag {lag}: {ac:.3f}")

    # Periodicity test: FFT of spike series
    max_idx = max(spike_indices) + 1 if spike_indices else len(df)
    spike_binary = np.zeros(max(max_idx, len(df) + 1))
    spike_binary[spike_indices] = 1
    if len(spike_binary) > 10:
        fft_result = np.abs(np.fft.fft(spike_binary))
        freqs = np.fft.fftfreq(len(spike_binary))
        # Find dominant frequencies (exclude DC)
        pos_mask = freqs > 0
        top_freqs = sorted(
            zip(freqs[pos_mask], fft_result[pos_mask]),
            key=lambda x: x[1],
            reverse=True,
        )[:10]
        dominant_periods = [(1.0 / f, amp) for f, amp in top_freqs if f > 0]
    else:
        dominant_periods = []

    print(f"\n  Dominant periodicities (business days):")
    for period, amp in dominant_periods[:5]:
        print(f"    {period:.1f} days (amplitude={amp:.1f})")

    return {
        "n_spikes": len(spikes),
        "threshold": float(threshold),
        "morse_rate": morse_rate,
        "mc_mean": mc_mean,
        "z_score": z_score,
        "inter_arrival_hist": {int(i + 1): int(c) for i, c in enumerate(hist[:20])},
        "significant_lags": significant_lags,
        "dominant_periods": [(round(p, 1), round(a, 1)) for p, a in dominant_periods[:10]],
    }


# ═════════════════════════════════════════════════════════════════════════
# PHANTOM PLACEMENT DETECTOR
# ═════════════════════════════════════════════════════════════════════════
def detect_phantom_placements(data):
    """
    Find OI that appears and disappears within 1-3 days.
    These are potential signaling vehicles — positions opened purely to be seen.
    """
    print("\n" + "=" * 70)
    print("  BONUS: Phantom Placement Detection")
    print("=" * 70)

    dates = sorted(data.keys())
    phantoms = []

    for i in range(1, len(dates) - 3):
        curr = data[dates[i]].groupby(["strike", "right"])["open_interest"].sum()
        prev = data[dates[i - 1]].groupby(["strike", "right"])["open_interest"].sum() if i > 0 else pd.Series(dtype=float)

        # Find positions that appeared (weren't in prev or were near zero)
        for (strike, right), oi in curr.items():
            prev_oi = prev.get((strike, right), 0) if len(prev) > 0 else 0
            if oi > 100 and prev_oi < 10:  # Position appeared
                # Check if it disappears within 3 days
                disappeared = False
                for j in range(1, min(4, len(dates) - i)):
                    future = data[dates[i + j]].groupby(["strike", "right"])["open_interest"].sum()
                    future_oi = future.get((strike, right), 0) if len(future) > 0 else 0
                    if future_oi < 10:
                        phantoms.append({
                            "appear_date": dates[i],
                            "disappear_date": dates[i + j],
                            "duration_days": j,
                            "strike": float(strike),
                            "right": str(right),
                            "peak_oi": int(oi),
                        })
                        disappeared = True
                        break

    print(f"  Total phantom placements found: {len(phantoms)}")

    if phantoms:
        # Statistics
        durations = [p["duration_days"] for p in phantoms]
        print(f"  Duration distribution: 1d={durations.count(1)}, 2d={durations.count(2)}, 3d={durations.count(3)}")

        # Top phantoms by OI
        phantoms.sort(key=lambda x: x["peak_oi"], reverse=True)
        print(f"\n  Top 20 phantom placements by OI:")
        for p in phantoms[:20]:
            print(f"    {p['appear_date']}→{p['disappear_date']} ({p['duration_days']}d): "
                  f"${p['strike']:.0f} {p['right']} OI={p['peak_oi']:,}")

        # Strike frequency among phantoms
        phantom_strikes = Counter(p["strike"] for p in phantoms)
        print(f"\n  Most common phantom strikes:")
        for strike, count in phantom_strikes.most_common(15):
            print(f"    ${strike:.0f}: {count} phantoms")

    return {
        "total_phantoms": len(phantoms),
        "duration_dist": dict(Counter(p["duration_days"] for p in phantoms)),
        "top_phantoms": phantoms[:30],
        "phantom_strike_freq": dict(Counter(p["strike"] for p in phantoms).most_common(20)),
    }


# ═════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  OPTIONS CHAIN STEGANOGRAPHY SCANNER")
    print("  Scanning 593 GME OI snapshots for hidden signals")
    print("=" * 70)

    # Load data
    print("\n  Loading per-strike OI data...")
    data = load_per_strike_oi()
    print(f"  Loaded {len(data)} daily snapshots")

    print("\n  Loading aggregate OI data...")
    agg_df = load_aggregate_oi()
    print(f"  Loaded {len(agg_df)} aggregate rows")

    results = {}

    # Run all layers
    results["layer_a_known_numbers"] = layer_a_known_numbers(data)
    results["layer_b_morse_code"] = layer_b_morse_code(agg_df)
    results["layer_c_strike_alphabet"] = layer_c_strike_alphabet(data)
    results["layer_d_putcall_bitstream"] = layer_d_putcall_bitstream(data)
    results["layer_e_temporal_cadence"] = layer_e_temporal_cadence(agg_df, data)
    results["phantom_placements"] = detect_phantom_placements(data)

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY — SIGNAL VS NOISE")
    print("=" * 70)
    for layer_name, layer_data in results.items():
        z = layer_data.get("z_score", "N/A")
        p = layer_data.get("p_value", "N/A")
        print(f"  {layer_name:35s}  z={z if isinstance(z, str) else f'{z:.2f}':>8s}"
              f"  {'p=' + f'{p:.4f}' if isinstance(p, float) else ''}")

    # Save results
    out_path = RESULTS_DIR / "steganography_scan_results.json"

    # Convert numpy types for JSON serialization
    def convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, pd.Timestamp):
            return str(obj)
        return str(obj)

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=convert)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    main()
