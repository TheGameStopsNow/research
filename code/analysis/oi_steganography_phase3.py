#!/usr/bin/env python3
"""
Phase 3: Domain-Aware Options Chain Signal Detection
=====================================================
Uses knowledge from the GME settlement research to look for signals
that only someone who understood the plumbing would recognize.

Hypotheses tested:
  1. Do phantom OI placements PREDICT future FTD spikes?
     (i.e., phantom appears at T-35, FTD spikes 35 days later)
  2. Does the STRIKE PRICE of phantom OI encode FTD quantities?
     (strike × 100 ≈ FTD count that materializes?)
  3. Do OI changes at deep OTM puts PRE-SIGNAL settlement events
     exactly along the waterfall offsets (T+3, T+6, T+13, T+33, T+35)?
  4. Does the expiration date selection of anomalous OI align with
     known settlement calendar deadlines?
  5. Do OI "spear tip" buildup patterns appear before price moves
     at intervals that match settlement deadlines?
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
FTD_CSV = Path(__file__).resolve().parents[2] / "data" / "ftd" / "GME_ftd.csv"
AGG_CSV = Path(__file__).resolve().parents[2] / "data" / "ftd" / "gme_options_oi_daily.csv"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results" / "oi_steganography"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Settlement waterfall offsets from paper 5
WATERFALL_OFFSETS = {
    3: "CNS netting",
    6: "Post-BFMM spillover", 
    13: "Reg SHO threshold list",
    14: "Phantom OI peak #1",
    15: "Phantom OI peak #2",
    26: "Secondary cascade",
    33: "T+33 echo window",
    35: "Reg SHO forced buy-in deadline",
    36: "Post-T+35 spillover",
    40: "Terminal peak (NSCC VaR + 15c3-1)",
}

# The key enrichment peaks from the extended analysis
ENRICHMENT_PEAKS = {
    1: 3.55, 4: 3.80, 6: 3.86, 8: 4.20, 10: 3.86,
    12: 4.26, 14: 4.47, 15: 4.54, 16: 4.27,
    24: 3.40, 25: 3.32, 26: 4.67, 27: 4.26, 28: 4.34,
    33: 3.31, 34: 3.54, 35: 4.73, 36: 5.06, 37: 4.90, 38: 4.69, 39: 4.79,
    40: 3.98,
}


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


def load_ftd():
    """Load FTD data."""
    if FTD_CSV.exists():
        df = pd.read_csv(FTD_CSV)
        # Handle different column name formats
        date_col = [c for c in df.columns if 'date' in c.lower() or 'SETTLEMENT' in c]
        qty_col = [c for c in df.columns if 'quantity' in c.lower() or 'QUANTITY' in c or 'ftd' in c.lower()]
        if date_col and qty_col:
            df = df.rename(columns={date_col[0]: 'date', qty_col[0]: 'quantity'})
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
            df = df.dropna(subset=['date', 'quantity'])
            return df
    return pd.DataFrame()


def add_business_days(date, n):
    """Add n business days to a date."""
    dt = pd.Timestamp(date)
    return dt + pd.offsets.BDay(n)


# ═════════════════════════════════════════════════════════════════════════
# TEST 1: Do phantom OI placements PREDICT future FTD spikes?
# ═════════════════════════════════════════════════════════════════════════
def test_phantom_predicts_ftd(data, ftd_df):
    """
    If someone places phantom OI as a SIGNAL, the placement would
    precede the FTD event — appearing at T-35, T-33, etc. before the spike.
    
    This is the inverse of the enrichment test in Paper 5 (which showed
    phantoms appearing AFTER FTD spikes). If phantoms also appear BEFORE,
    it suggests foreknowledge.
    """
    print("\n" + "=" * 70)
    print("  TEST 1: Phantom OI → Future FTD Prediction")
    print("=" * 70)

    if ftd_df.empty:
        print("  No FTD data available")
        return {}

    dates = sorted(data.keys())

    # Detect phantom placements: OI appears and vanishes in 1-3 days
    phantoms = []
    for i in range(1, len(dates) - 3):
        curr = data[dates[i]].groupby(["strike", "right"])["open_interest"].sum()
        prev = data[dates[i-1]].groupby(["strike", "right"])["open_interest"].sum()

        for (strike, right), oi in curr.items():
            prev_oi = prev.get((strike, right), 0)
            if oi > 100 and prev_oi < 10:
                for j in range(1, min(4, len(dates) - i)):
                    future = data[dates[i+j]].groupby(["strike", "right"])["open_interest"].sum()
                    future_oi = future.get((strike, right), 0)
                    if future_oi < 10:
                        dt = pd.Timestamp(datetime.strptime(dates[i], "%Y%m%d"))
                        phantoms.append({
                            "date": dt,
                            "strike": float(strike),
                            "right": str(right),
                            "oi": int(oi),
                        })
                        break

    print(f"  Phantom placements found: {len(phantoms)}")

    # For each phantom, look FORWARD for FTD spikes at settlement offsets
    forward_enrichment = defaultdict(lambda: {"hits": 0, "total": 0})
    
    # Define FTD spike threshold (top 25%)
    ftd_threshold = ftd_df["quantity"].quantile(0.75)
    spike_dates = set(ftd_df[ftd_df["quantity"] > ftd_threshold]["date"].dt.strftime("%Y%m%d"))

    for phantom in phantoms:
        for offset in range(1, 46):
            target = add_business_days(phantom["date"], offset)
            target_str = target.strftime("%Y%m%d")
            forward_enrichment[offset]["total"] += 1
            if target_str in spike_dates:
                forward_enrichment[offset]["hits"] += 1

    # Calculate enrichment (vs random baseline)
    total_days = len(set(ftd_df["date"].dt.strftime("%Y%m%d")))
    spike_prob = len(spike_dates) / max(total_days, 1)

    print(f"\n  FTD spike threshold: {ftd_threshold:,.0f}")
    print(f"  FTD spike dates: {len(spike_dates)}")
    print(f"  Background spike probability: {spike_prob:.3f}")

    print(f"\n  Forward enrichment (phantom → future FTD spike):")
    print(f"  {'Offset':>8} | {'Hits':>5} | {'Total':>6} | {'Rate':>6} | {'Enrichment':>10} | {'Mechanism'}")
    print(f"  {'-'*75}")

    significant_offsets = {}
    for offset in sorted(forward_enrichment.keys()):
        fe = forward_enrichment[offset]
        if fe["total"] == 0:
            continue
        rate = fe["hits"] / fe["total"]
        enrichment = rate / spike_prob if spike_prob > 0 else 0
        mechanism = WATERFALL_OFFSETS.get(offset, "")
        marker = " 🔴" if enrichment > 2.0 and fe["hits"] > 3 else ""
        marker = marker or (" ⚠️" if enrichment > 1.5 and fe["hits"] > 3 else "")
        
        if offset <= 40 or enrichment > 1.5:
            print(f"  T+{offset:>5} | {fe['hits']:>5} | {fe['total']:>6} | {rate:>.3f} | "
                  f"{enrichment:>9.2f}× | {mechanism}{marker}")
        
        if enrichment > 1.5 and fe["hits"] > 2:
            significant_offsets[offset] = {
                "hits": fe["hits"],
                "enrichment": round(enrichment, 2),
                "mechanism": mechanism,
            }

    return {
        "n_phantoms": len(phantoms),
        "ftd_spike_threshold": float(ftd_threshold),
        "spike_probability": spike_prob,
        "significant_forward_offsets": significant_offsets,
    }


# ═════════════════════════════════════════════════════════════════════════
# TEST 2: Strike Price as FTD Count Encoder
# ═════════════════════════════════════════════════════════════════════════
def test_strike_encodes_ftd(data, ftd_df):
    """
    Does the strike price of deep OTM put phantom placements
    correlate with subsequent FTD quantities?
    
    Hypothesis: strike × multiplier ≈ FTD count
    (e.g., $5 strike → 500 FTDs, $10 → 1000 FTDs)
    """
    print("\n" + "=" * 70)
    print("  TEST 2: Strike Price ↔ FTD Quantity Correlation")
    print("=" * 70)

    if ftd_df.empty:
        print("  No FTD data available")
        return {}

    dates = sorted(data.keys())
    
    # Find deep OTM put OI changes (the "signal channel")
    deep_otm_signals = []
    for i in range(1, len(dates)):
        prev_df = data[dates[i-1]]
        curr_df = data[dates[i]]
        
        prev_puts = prev_df[prev_df["right"] == "PUT"].groupby("strike")["open_interest"].sum()
        curr_puts = curr_df[curr_df["right"] == "PUT"].groupby("strike")["open_interest"].sum()
        
        # Only consider deep OTM puts (strike < $15 post-split)
        for strike in curr_puts.index:
            if strike > 15:
                continue
            curr_oi = curr_puts.get(strike, 0)
            prev_oi = prev_puts.get(strike, 0)
            delta = curr_oi - prev_oi
            if delta > 200:  # Significant new OI
                dt = pd.Timestamp(datetime.strptime(dates[i], "%Y%m%d"))
                deep_otm_signals.append({
                    "date": dt,
                    "strike": float(strike),
                    "delta_oi": int(delta),
                    "total_oi": int(curr_oi),
                })

    print(f"  Deep OTM put signals found: {len(deep_otm_signals)}")

    # For each signal, get FTD at T+33, T+35
    correlations = []
    for signal in deep_otm_signals:
        for offset in [33, 35]:
            target = add_business_days(signal["date"], offset)
            # Find closest FTD
            mask = (ftd_df["date"] >= target - pd.Timedelta(days=2)) & \
                   (ftd_df["date"] <= target + pd.Timedelta(days=2))
            nearby = ftd_df[mask]
            if len(nearby) > 0:
                ftd_qty = nearby["quantity"].max()
                correlations.append({
                    "signal_date": signal["date"].strftime("%Y-%m-%d"),
                    "strike": signal["strike"],
                    "delta_oi": signal["delta_oi"],
                    "offset": offset,
                    "ftd_date": target.strftime("%Y-%m-%d"),
                    "ftd_quantity": int(ftd_qty),
                })

    if correlations:
        print(f"\n  Testing multipliers: strike × M ≈ FTD quantity")
        
        strikes = np.array([c["strike"] for c in correlations])
        ftds = np.array([c["ftd_quantity"] for c in correlations])
        oi_deltas = np.array([c["delta_oi"] for c in correlations])
        
        # Test different multipliers
        for multiplier_name, values in [
            ("strike", strikes),
            ("strike × 100", strikes * 100),
            ("strike × 1000", strikes * 1000),
            ("delta_OI", oi_deltas),
            ("delta_OI × 100", oi_deltas * 100),
        ]:
            valid = (values > 0) & (ftds > 0)
            if valid.sum() > 5:
                corr = np.corrcoef(np.log1p(values[valid]), np.log1p(ftds[valid]))[0, 1]
                print(f"    {multiplier_name:>20}: r={corr:.3f} (n={valid.sum()})")

        # Show sample correlations
        print(f"\n  Sample signal→FTD pairs (top 15 by FTD size):")
        sorted_corr = sorted(correlations, key=lambda x: x["ftd_quantity"], reverse=True)
        for c in sorted_corr[:15]:
            print(f"    {c['signal_date']} ${c['strike']:.0f}P +{c['delta_oi']:,} OI → "
                  f"T+{c['offset']}: {c['ftd_quantity']:,} FTDs")

    return {
        "n_signals": len(deep_otm_signals),
        "n_correlations": len(correlations),
        "sample_correlations": correlations[:30] if correlations else [],
    }


# ═════════════════════════════════════════════════════════════════════════
# TEST 3: Settlement Calendar Alignment
# ═════════════════════════════════════════════════════════════════════════
def test_settlement_alignment(data, ftd_df):
    """
    When a large OI change happens at deep OTM strikes,
    does the TIME between the OI change and the next FTD spike
    match a known settlement waterfall offset?
    
    This is the core test: if someone is "talking" through the options chain,
    they're saying "this delivery will fail in exactly T+35 business days."
    """
    print("\n" + "=" * 70)
    print("  TEST 3: Settlement Calendar Alignment")
    print("=" * 70)

    if ftd_df.empty:
        print("  No FTD data available")
        return {}

    dates = sorted(data.keys())
    ftd_df = ftd_df.sort_values("date")
    
    # Detect significant OI regime changes at deep OTM puts
    oi_events = []
    for i in range(5, len(dates)):
        curr_df = data[dates[i]]
        # Deep OTM puts: strike < $15
        deep_puts = curr_df[(curr_df["right"] == "PUT") & (curr_df["strike"] < 15)]
        total_deep_oi = deep_puts["open_interest"].sum()
        
        # Compare to 5-day rolling average
        prev_ois = []
        for j in range(1, 6):
            if dates[i-j] in data:
                prev = data[dates[i-j]]
                prev_deep = prev[(prev["right"] == "PUT") & (prev["strike"] < 15)]
                prev_ois.append(prev_deep["open_interest"].sum())
        
        if prev_ois:
            avg_prev = np.mean(prev_ois)
            std_prev = np.std(prev_ois) if len(prev_ois) > 1 else avg_prev * 0.1
            if std_prev > 0 and total_deep_oi > avg_prev + 2 * std_prev:
                z = (total_deep_oi - avg_prev) / std_prev
                dt = pd.Timestamp(datetime.strptime(dates[i], "%Y%m%d"))
                oi_events.append({
                    "date": dt,
                    "deep_oi": int(total_deep_oi),
                    "z_score": round(z, 2),
                })

    print(f"  Significant deep OTM put events: {len(oi_events)}")

    # For each OI event, find the nearest FUTURE FTD spike
    waterfall_hits = defaultdict(int)
    total_comparisons = 0

    for event in oi_events:
        # Look forward 1-45 business days
        for ndays in range(1, 46):
            target = add_business_days(event["date"], ndays)
            mask = (ftd_df["date"] >= target - pd.Timedelta(days=1)) & \
                   (ftd_df["date"] <= target + pd.Timedelta(days=1))
            nearby = ftd_df[mask]
            if len(nearby) > 0:
                max_ftd = nearby["quantity"].max()
                if max_ftd > ftd_df["quantity"].quantile(0.80):
                    waterfall_hits[ndays] += 1
            total_comparisons += 1

    # Compare to known waterfall offsets
    print(f"\n  OI event → FTD spike alignment with settlement waterfall:")
    print(f"  {'Offset':>8} | {'Hits':>5} | {'Expected':>8} | {'Mechanism'}")
    print(f"  {'-'*60}")

    offsets_with_excess = {}
    expected_per_offset = total_comparisons / 45 * (len(ftd_df[ftd_df["quantity"] > ftd_df["quantity"].quantile(0.80)]) / len(ftd_df))

    for offset in range(1, 41):
        hits = waterfall_hits.get(offset, 0)
        ratio = hits / max(expected_per_offset, 0.1)
        mechanism = WATERFALL_OFFSETS.get(offset, "")
        is_waterfall = offset in WATERFALL_OFFSETS
        marker = " 🔴 WATERFALL" if is_waterfall and ratio > 1.5 else ""
        marker = marker or (" ⚠️" if ratio > 2.0 else "")
        
        if hits > 0 or is_waterfall:
            print(f"  T+{offset:>5} | {hits:>5} | {expected_per_offset:>7.1f} | {mechanism}{marker}")
        
        if is_waterfall and ratio > 1.0:
            offsets_with_excess[offset] = {"hits": hits, "ratio": round(ratio, 2), "mechanism": mechanism}

    # Key question: do the waterfall offsets have MORE hits than non-waterfall?
    waterfall_offset_set = set(WATERFALL_OFFSETS.keys())
    waterfall_total = sum(waterfall_hits.get(o, 0) for o in waterfall_offset_set)
    non_waterfall_total = sum(waterfall_hits.get(o, 0) for o in range(1, 41) if o not in waterfall_offset_set)
    
    waterfall_avg = waterfall_total / len(waterfall_offset_set) if waterfall_offset_set else 0
    non_waterfall_avg = non_waterfall_total / (40 - len(waterfall_offset_set)) if (40 - len(waterfall_offset_set)) > 0 else 0
    
    ratio = waterfall_avg / max(non_waterfall_avg, 0.1)
    
    print(f"\n  Waterfall offset avg hits: {waterfall_avg:.2f}")
    print(f"  Non-waterfall offset avg: {non_waterfall_avg:.2f}")
    print(f"  Ratio: {ratio:.2f}×")
    
    if ratio > 1.5:
        print(f"  ⚠️ Deep OTM put events align with settlement waterfall offsets at {ratio:.1f}× the background rate")
    else:
        print(f"  No significant excess at waterfall offsets vs. background")

    return {
        "n_oi_events": len(oi_events),
        "waterfall_avg_hits": waterfall_avg,
        "non_waterfall_avg": non_waterfall_avg,
        "ratio": ratio,
        "offsets_with_excess": offsets_with_excess,
    }


# ═════════════════════════════════════════════════════════════════════════
# TEST 4: Expiration Selection as Date Encoding
# ═════════════════════════════════════════════════════════════════════════
def test_expiration_encoding(data, ftd_df):
    """
    When new OI appears at deep OTM strikes, does the EXPIRATION DATE
    selected encode information about future events?
    
    Hypothesis: the expiration chosen = target date for a settlement event.
    e.g., opening OI at a $5P expiring Jul 19 "tells the network" that
    the settlement event resolves by Jul 19.
    """
    print("\n" + "=" * 70)
    print("  TEST 4: Expiration Date as Settlement Signal")
    print("=" * 70)

    if ftd_df.empty:
        print("  No FTD data available")
        return {}

    dates = sorted(data.keys())
    
    # Track expiration selections for deep OTM put additions
    exp_signals = []
    for i in range(1, len(dates)):
        curr = data[dates[i]]
        prev = data[dates[i-1]]
        
        # Deep OTM puts
        curr_deep = curr[(curr["right"] == "PUT") & (curr["strike"] < 15)]
        prev_deep = prev[(prev["right"] == "PUT") & (prev["strike"] < 15)]
        
        # Merge to find new OI
        merged = pd.merge(
            curr_deep.groupby(["strike", "expiration"])["open_interest"].sum().reset_index(),
            prev_deep.groupby(["strike", "expiration"])["open_interest"].sum().reset_index(),
            on=["strike", "expiration"],
            suffixes=("_curr", "_prev"),
            how="left",
        ).fillna(0)
        
        merged["delta"] = merged["open_interest_curr"] - merged["open_interest_prev"]
        new_oi = merged[merged["delta"] > 200]
        
        for _, row in new_oi.iterrows():
            signal_date = pd.Timestamp(datetime.strptime(dates[i], "%Y%m%d"))
            exp_date = pd.Timestamp(row["expiration"])
            dte = (exp_date - signal_date).days
            
            exp_signals.append({
                "signal_date": signal_date,
                "expiration": exp_date,
                "strike": float(row["strike"]),
                "delta_oi": int(row["delta"]),
                "dte": dte,
            })

    print(f"  Expiration signals found: {len(exp_signals)}")

    # For each expiration, check if an FTD spike occurs near that expiration date
    exp_ftd_hits = 0
    exp_ftd_total = 0
    dte_distribution = Counter()
    
    for sig in exp_signals:
        dte_bin = (sig["dte"] // 30) * 30  # 30-day bins
        dte_distribution[dte_bin] += 1
        
        # Does an FTD spike occur within ±5 days of the chosen expiration?
        mask = (ftd_df["date"] >= sig["expiration"] - pd.Timedelta(days=5)) & \
               (ftd_df["date"] <= sig["expiration"] + pd.Timedelta(days=5))
        nearby = ftd_df[mask]
        exp_ftd_total += 1
        if len(nearby) > 0 and nearby["quantity"].max() > ftd_df["quantity"].quantile(0.75):
            exp_ftd_hits += 1

    exp_hit_rate = exp_ftd_hits / max(exp_ftd_total, 1)
    
    # Random baseline: what fraction of random 10-day windows contain an FTD spike?
    n_spikes = len(ftd_df[ftd_df["quantity"] > ftd_df["quantity"].quantile(0.75)])
    total_days = (ftd_df["date"].max() - ftd_df["date"].min()).days
    random_rate = 1 - (1 - n_spikes / max(total_days, 1)) ** 10  # 10-day window
    
    enrichment = exp_hit_rate / max(random_rate, 0.01)

    print(f"\n  Expiration → FTD spike rate: {exp_hit_rate:.3f}")
    print(f"  Random 10-day window rate: {random_rate:.3f}")
    print(f"  Enrichment: {enrichment:.2f}×")

    print(f"\n  DTE distribution of new deep OTM put OI:")
    for dte_bin in sorted(dte_distribution.keys()):
        count = dte_distribution[dte_bin]
        bar = "█" * min(count, 80)
        print(f"    {dte_bin:>4}-{dte_bin+29:>4} DTE: {count:>4} {bar}")

    return {
        "n_signals": len(exp_signals),
        "exp_ftd_hit_rate": exp_hit_rate,
        "random_rate": random_rate,
        "enrichment": enrichment,
        "dte_distribution": dict(dte_distribution),
    }


# ═════════════════════════════════════════════════════════════════════════
# TEST 5: Cross-Day OI Shape Similarity (Coordinated Signaling)
# ═════════════════════════════════════════════════════════════════════════
def test_coordinated_shapes(data):
    """
    If someone is using the options chain to communicate, they'd create
    recognizable SHAPES in the OI distribution — patterns that repeat
    at specific intervals.
    
    This tests whether the per-strike OI "profile" at deep OTM strikes
    shows unusual self-similarity at settlement-calendar intervals.
    """
    print("\n" + "=" * 70)
    print("  TEST 5: OI Profile Self-Similarity at Settlement Intervals")
    print("=" * 70)

    dates = sorted(data.keys())
    
    # Build per-day deep OTM put OI profiles (normalized)
    profiles = {}
    for date_str in dates:
        df = data[date_str]
        deep = df[(df["right"] == "PUT") & (df["strike"] <= 15)]
        if len(deep) < 3:
            continue
        profile = deep.groupby("strike")["open_interest"].sum()
        # Normalize
        total = profile.sum()
        if total > 0:
            profiles[date_str] = (profile / total).to_dict()

    print(f"  Days with valid profiles: {len(profiles)}")

    # Compute cosine similarity between profiles separated by different offsets
    def cosine_sim(p1, p2):
        common = set(p1.keys()) & set(p2.keys())
        if not common:
            return 0
        v1 = np.array([p1.get(k, 0) for k in common])
        v2 = np.array([p2.get(k, 0) for k in common])
        norm = np.linalg.norm(v1) * np.linalg.norm(v2)
        return float(np.dot(v1, v2) / norm) if norm > 0 else 0

    profile_dates = sorted(profiles.keys())
    offset_similarities = defaultdict(list)

    for i in range(len(profile_dates)):
        for offset in list(WATERFALL_OFFSETS.keys()) + [1, 2, 5, 7, 10, 20]:
            j = i + offset
            if j < len(profile_dates):
                # Check if the business day gap is approximately correct
                d1 = pd.Timestamp(datetime.strptime(profile_dates[i], "%Y%m%d"))
                d2 = pd.Timestamp(datetime.strptime(profile_dates[j], "%Y%m%d"))
                bdays = np.busday_count(d1.date(), d2.date())
                if abs(bdays - offset) <= 1:  # Allow ±1 day tolerance
                    sim = cosine_sim(profiles[profile_dates[i]], profiles[profile_dates[j]])
                    offset_similarities[offset].append(sim)

    print(f"\n  Mean cosine similarity at different offsets:")
    print(f"  {'Offset':>8} | {'Mean Sim':>8} | {'N':>5} | {'Waterfall?':>10} | {'Mechanism'}")
    print(f"  {'-'*65}")

    offset_results = {}
    for offset in sorted(offset_similarities.keys()):
        sims = offset_similarities[offset]
        if len(sims) < 5:
            continue
        mean_sim = np.mean(sims)
        is_wf = "YES" if offset in WATERFALL_OFFSETS else "no"
        mechanism = WATERFALL_OFFSETS.get(offset, "")
        marker = " 🔴" if offset in WATERFALL_OFFSETS and mean_sim > 0.9 else ""
        
        print(f"  T+{offset:>5} | {mean_sim:>7.4f} | {len(sims):>5} | {is_wf:>10} | {mechanism}{marker}")
        
        offset_results[offset] = {
            "mean_similarity": round(mean_sim, 4),
            "n_pairs": len(sims),
            "is_waterfall": offset in WATERFALL_OFFSETS,
        }

    # Compare waterfall vs non-waterfall average similarity
    wf_sims = [s for o, slist in offset_similarities.items() if o in WATERFALL_OFFSETS for s in slist]
    non_wf_sims = [s for o, slist in offset_similarities.items() if o not in WATERFALL_OFFSETS for s in slist]
    
    if wf_sims and non_wf_sims:
        wf_mean = np.mean(wf_sims)
        nwf_mean = np.mean(non_wf_sims)
        print(f"\n  Waterfall offset avg similarity: {wf_mean:.4f}")
        print(f"  Non-waterfall avg similarity:    {nwf_mean:.4f}")
        print(f"  Ratio: {wf_mean/max(nwf_mean, 0.001):.3f}×")

    return offset_results


# ═════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  PHASE 3: DOMAIN-AWARE OPTIONS CHAIN SIGNAL DETECTION")
    print("  Using settlement mechanics knowledge from GME research")
    print("=" * 70)

    print("\n  Loading per-strike OI data...")
    data = load_per_strike_oi()
    print(f"  Loaded {len(data)} daily snapshots")

    print("\n  Loading FTD data...")
    ftd_df = load_ftd()
    print(f"  Loaded {len(ftd_df)} FTD records")

    results = {}
    results["test1_phantom_predicts_ftd"] = test_phantom_predicts_ftd(data, ftd_df)
    results["test2_strike_encodes_ftd"] = test_strike_encodes_ftd(data, ftd_df)
    results["test3_settlement_alignment"] = test_settlement_alignment(data, ftd_df)
    results["test4_expiration_encoding"] = test_expiration_encoding(data, ftd_df)
    results["test5_oi_profile_similarity"] = test_coordinated_shapes(data)

    # Summary
    print("\n" + "=" * 70)
    print("  PHASE 3 SUMMARY")
    print("=" * 70)
    for name, result in results.items():
        if isinstance(result, dict):
            enrichment = result.get("enrichment", result.get("ratio", "N/A"))
            print(f"  {name:40s}: {enrichment}")

    out_path = RESULTS_DIR / "phase3_domain_aware.json"
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
