#!/usr/bin/env python3
"""
Settlement Waterfall Decoder
==============================
Translates the "machine language" of the options chain into human-readable
settlement signals. Reads deviations from the deep OTM put OI baseline
and maps them through the 15-node failure waterfall to:

  1. DETECT when settlement machinery is under stress
  2. DIAGNOSE which waterfall node is active
  3. PREDICT upcoming deadlines (T+35 forced buy-in, T+40 terminal)
  4. BUILD a phrasebook: what each pattern "says" in settlement language

The Phrasebook:
  - Sudden deep OTM put OI spike  → "A large FTD just entered the CNS pipeline"
  - Phantom OI (1-day spike)      → "A synthetic locate was manufactured and consumed"
  - PC ratio inversion at $0.50   → "Someone is building married puts for locate generation"
  - OI spike at T+33 from an FTD  → "Original failure echoing through ex-clearing"
  - OI collapse at T+45           → "Terminal boundary - capital-destructive deadline hit"
  - Spear tip buildup             → "Coordinated expiration targeting in progress"
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")
FTD_CSV = Path(__file__).resolve().parents[2] / "data" / "ftd" / "GME_ftd.csv"
AGG_CSV = Path(__file__).resolve().parents[2] / "data" / "ftd" / "gme_options_oi_daily.csv"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results" / "oi_steganography"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── The Waterfall Dictionary ────────────────────────────────────────────
# Each node maps an observed OI pattern to what the settlement machinery is doing
WATERFALL_DICTIONARY = {
    "T+0": {
        "name": "Trade Date",
        "signal": "New OI spike at any strike",
        "meaning": "New position opened — clock starts. FTD exposure begins on settlement date (T+2).",
        "what_to_watch": "Size and location of OI change. Deep OTM puts → likely locate generation.",
    },
    "T+2": {
        "name": "Settlement Date",
        "signal": "OI that was opened 2 business days ago should settle",
        "meaning": "If delivery fails here, FTD is born. Watch for OI that doesn't decrease.",
        "what_to_watch": "Positions that opened T-2 that remain static = potential FTD.",
    },
    "T+3": {
        "name": "CNS Netting",
        "signal": "Phantom OI spike (enrichment: 5.4×)",
        "meaning": "The Continuous Net Settlement engine is processing. New synthetic locates being manufactured to cover the T+2 failure.",
        "what_to_watch": "Deep OTM put OI appearing at $0.50-$5 strikes. This is the locate factory.",
    },
    "T+6": {
        "name": "Post-BFMM Spillover",
        "signal": "Phantom OI enrichment: 7.4×",
        "meaning": "The Bona Fide Market Maker T+5 close-out deadline has passed. Failures that survived are spilling into ex-clearing channels.",
        "what_to_watch": "OI that appeared at T+3 persisting or spreading to adjacent strikes.",
    },
    "T+13": {
        "name": "Reg SHO Threshold List",
        "signal": "OI regime change detectable",
        "meaning": "If 10,000+ shares fail for 13 consecutive settlement days, the security hits the threshold list. Locate requirements tighten.",
        "what_to_watch": "Shift from calls to puts at near-money strikes = hedging activity.",
    },
    "T+14/15": {
        "name": "Phantom OI Peak Zone",
        "signal": "Peak phantom enrichment (4.47-4.54×)",
        "meaning": "Maximum synthetic locate manufacturing. The system is working hardest to roll failures.",
        "what_to_watch": "This is the loudest the machine gets. Big OI spikes at deep OTM puts.",
    },
    "T+26/28": {
        "name": "Secondary Cascade",
        "signal": "Enrichment: 4.67× at T+26",
        "meaning": "The first generation of rolled failures is generating its own failures. Failure is self-replicating.",
        "what_to_watch": "New OI appearing at strikes that were quiet. The waterfall is spreading.",
    },
    "T+33": {
        "name": "The Echo Window",
        "signal": "Enrichment: 3.31× (confirmed at 84% hit rate)",
        "meaning": "The original FTD is echoing through ex-clearing. This is the T+35 deadline minus T+2 settlement = T+33 from trade date.",
        "what_to_watch": "OI spike that mirrors the original T+0 spike in relative magnitude.",
    },
    "T+35": {
        "name": "Reg SHO Forced Buy-In",
        "signal": "Enrichment: 4.73×",  
        "meaning": "Mandatory close-out deadline. If still failing, broker must buy shares on open market. This is the pressure point.",
        "what_to_watch": "Price action. If shares are hard to borrow, this creates a mini-squeeze.",
    },
    "T+36": {
        "name": "Post-Forced-Buy Spillover",
        "signal": "Peak enrichment: 5.06×",
        "meaning": "The HIGHEST enrichment in the entire waterfall. Forced buy-ins create new synthetic positions to comply, generating even more phantom OI.",
        "what_to_watch": "This is the LOUDEST signal. If you see massive deep OTM put OI here, the waterfall is in full cascade.",
    },
    "T+40": {
        "name": "Terminal Peak",
        "signal": "Enrichment: 3.98×",
        "meaning": "Convergent pressure from NSCC Value-at-Risk calculations AND Rule 15c3-1 net capital haircuts. The failure is becoming capital-destructive.",
        "what_to_watch": "OI should start declining. If it doesn't, the institution is absorbing margin damage.",
    },
    "T+45": {
        "name": "Terminal Boundary",
        "signal": "Enrichment collapses to 0.0×",
        "meaning": "No surviving failures past this point. Either resolved via buy-in, transferred via ex-clearing, or absorbed as capital loss.",
        "what_to_watch": "Everything should be quiet. If OI persists, it's a new cycle restarting.",
    },
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
    if FTD_CSV.exists():
        df = pd.read_csv(FTD_CSV)
        df = df.rename(columns={c: c.lower().strip() for c in df.columns})
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
        return df.dropna(subset=['date', 'quantity'])
    return pd.DataFrame()


def add_bdays(date, n):
    return pd.Timestamp(date) + pd.offsets.BDay(n)


# ═════════════════════════════════════════════════════════════════════════
# 1. BASELINE TRACKER: Measure the "quiet" OI profile
# ═════════════════════════════════════════════════════════════════════════
def build_baseline(data):
    """
    Build the slowly-evolving baseline OI profile at deep OTM puts.
    The baseline is the 20-day rolling median at each strike.
    Deviations from baseline = the machine talking.
    """
    print("\n" + "=" * 70)
    print("  1. BUILDING BASELINE OI PROFILE")
    print("=" * 70)

    dates = sorted(data.keys())
    
    # Build time series per strike (deep OTM puts only)
    strike_ts = defaultdict(dict)
    for date_str in dates:
        df = data[date_str]
        deep = df[(df["right"] == "PUT") & (df["strike"] <= 15)]
        for _, row in deep.iterrows():
            strike_ts[float(row["strike"])][date_str] = int(row["open_interest"])

    # Convert to DataFrame
    oi_matrix = pd.DataFrame(strike_ts).fillna(0)
    oi_matrix.index = pd.to_datetime(oi_matrix.index, format="%Y%m%d")
    oi_matrix = oi_matrix.sort_index()
    
    # Rolling 20-day median = baseline
    baseline = oi_matrix.rolling(20, min_periods=5).median()
    
    # Deviation from baseline (in standard deviations)
    rolling_std = oi_matrix.rolling(20, min_periods=5).std()
    z_scores = (oi_matrix - baseline) / rolling_std.replace(0, np.nan)
    z_scores = z_scores.fillna(0)
    
    # Total deviation per day (sum of |z| across all strikes)
    daily_stress = z_scores.abs().sum(axis=1)
    daily_stress.name = "stress"
    
    print(f"  Strikes tracked: {len(oi_matrix.columns)}")
    print(f"  Date range: {oi_matrix.index[0].date()} to {oi_matrix.index[-1].date()}")
    print(f"  Mean daily stress: {daily_stress.mean():.1f}")
    print(f"  Max daily stress: {daily_stress.max():.1f} on {daily_stress.idxmax().date()}")
    
    # Top 20 stress days
    top_stress = daily_stress.nlargest(20)
    print(f"\n  Top 20 'loudest' days (machine stress):")
    for dt, stress in top_stress.items():
        # Find which strikes deviated most
        day_z = z_scores.loc[dt]
        top_strike = day_z.abs().idxmax()
        top_z = day_z[top_strike]
        print(f"    {dt.date()}: stress={stress:.1f}, "
              f"loudest=${top_strike:.0f}P z={top_z:+.1f}")

    return oi_matrix, baseline, z_scores, daily_stress


# ═════════════════════════════════════════════════════════════════════════
# 2. EVENT DETECTOR: Identify when the machine is talking
# ═════════════════════════════════════════════════════════════════════════
def detect_machine_events(z_scores, daily_stress):
    """
    Identify discrete events where the settlement machinery
    produces a detectable signal: stress > 2σ from the long-run mean.
    """
    print("\n" + "=" * 70)
    print("  2. MACHINE EVENT DETECTION")
    print("=" * 70)

    stress_mean = daily_stress.rolling(60, min_periods=20).mean()
    stress_std = daily_stress.rolling(60, min_periods=20).std()
    stress_z = (daily_stress - stress_mean) / stress_std.replace(0, np.nan)
    stress_z = stress_z.fillna(0)

    # Events: stress_z > 2
    events = []
    for dt in stress_z.index:
        if stress_z[dt] > 2:
            # Find the dominant signal
            day_z = z_scores.loc[dt]
            top_strikes = day_z.abs().nlargest(3)
            
            event = {
                "date": dt,
                "stress": float(daily_stress[dt]),
                "stress_z": float(stress_z[dt]),
                "top_strikes": {
                    f"${k:.0f}": float(v) for k, v in top_strikes.items()
                },
                "dominant_direction": "PUT_SURGE" if day_z.sum() > 0 else "PUT_DRAIN",
            }
            events.append(event)

    print(f"  Machine events detected (stress > 2σ): {len(events)}")
    
    # Cluster into event windows (events within 3 days = same event)
    clusters = []
    current_cluster = []
    for event in events:
        if current_cluster and (event["date"] - current_cluster[-1]["date"]).days > 5:
            clusters.append(current_cluster)
            current_cluster = [event]
        else:
            current_cluster.append(event)
    if current_cluster:
        clusters.append(current_cluster)

    print(f"  Event clusters: {len(clusters)}")

    print(f"\n  Event clusters (loudest day shown):")
    for i, cluster in enumerate(clusters):
        peak = max(cluster, key=lambda x: x["stress"])
        duration = (cluster[-1]["date"] - cluster[0]["date"]).days + 1
        strikes = ", ".join(f"{k}({v:+.1f}σ)" for k, v in peak["top_strikes"].items())
        print(f"    [{i+1}] {cluster[0]['date'].date()} → {cluster[-1]['date'].date()} "
              f"({duration}d, {len(cluster)} events)")
        print(f"        Peak: stress={peak['stress']:.0f}, {peak['dominant_direction']}")
        print(f"        Strikes: {strikes}")

    return events, clusters


# ═════════════════════════════════════════════════════════════════════════
# 3. WATERFALL MAPPER: Trace each event through the cascade
# ═════════════════════════════════════════════════════════════════════════
def map_waterfall(events, ftd_df, z_scores, daily_stress):
    """
    For each detected machine event, look backward to find the
    originating FTD, and forward to predict the next waterfall node.
    """
    print("\n" + "=" * 70)
    print("  3. WATERFALL MAPPING")
    print("=" * 70)

    if ftd_df.empty:
        print("  No FTD data for backward mapping")
        return []

    waterfall_map = []

    for event in events[:50]:  # Process top 50 events
        event_date = event["date"]
        
        # BACKWARD LOOK: which FTD spawned this event?
        backward_matches = []
        for offset_name, info in WATERFALL_DICTIONARY.items():
            if "/" in offset_name:
                offsets = [int(x.replace("T+", "")) for x in offset_name.split("/")]
            else:
                try:
                    offsets = [int(offset_name.replace("T+", ""))]
                except ValueError:
                    continue
            
            for offset in offsets:
                origin_date = add_bdays(event_date, -offset)
                # Check if there was an FTD spike near the origin
                mask = (ftd_df["date"] >= origin_date - pd.Timedelta(days=2)) & \
                       (ftd_df["date"] <= origin_date + pd.Timedelta(days=2))
                nearby = ftd_df[mask]
                if len(nearby) > 0:
                    max_ftd = nearby["quantity"].max()
                    if max_ftd > ftd_df["quantity"].quantile(0.70):
                        backward_matches.append({
                            "offset": offset,
                            "node_name": info["name"],
                            "origin_date": origin_date.strftime("%Y-%m-%d"),
                            "ftd_quantity": int(max_ftd),
                            "meaning": info["meaning"],
                        })

        # FORWARD PREDICT: what waterfall nodes are coming?
        forward_predictions = []
        for offset_name, info in WATERFALL_DICTIONARY.items():
            if "/" in offset_name:
                offsets = [int(x.replace("T+", "")) for x in offset_name.split("/")]
            else:
                try:
                    offsets = [int(offset_name.replace("T+", ""))]
                except ValueError:
                    continue

            for offset in offsets:
                # If this event is at node X, the next nodes are at +Y from origin
                future_date = add_bdays(event_date, offset)
                if future_date > event_date and future_date <= event_date + pd.Timedelta(days=90):
                    forward_predictions.append({
                        "offset_from_event": offset,
                        "predicted_date": future_date.strftime("%Y-%m-%d"),
                        "node_name": info["name"],
                        "what_to_watch": info["what_to_watch"],
                    })

        # Diagnose: which waterfall node is this event?
        diagnosis = "UNKNOWN"
        if backward_matches:
            # The best match is the one with highest FTD at a known offset
            best = max(backward_matches, key=lambda x: x["ftd_quantity"])
            diagnosis = f"{best['node_name']} (from {best['origin_date']}, {best['ftd_quantity']:,} FTDs)"

        waterfall_map.append({
            "event_date": event_date.strftime("%Y-%m-%d"),
            "stress": event["stress"],
            "dominant_direction": event["dominant_direction"],
            "diagnosis": diagnosis,
            "backward_matches": backward_matches[:5],
            "forward_predictions": forward_predictions[:5],
        })

    # Print decoded events
    print(f"\n  Decoded waterfall events (top 20):")
    for wm in waterfall_map[:20]:
        print(f"\n    📅 {wm['event_date']} | stress={wm['stress']:.0f} | {wm['dominant_direction']}")
        print(f"    🔍 Diagnosis: {wm['diagnosis']}")
        if wm['backward_matches']:
            for bm in wm['backward_matches'][:2]:
                print(f"       ← T-{bm['offset']:>2} from {bm['origin_date']}: "
                      f"{bm['ftd_quantity']:>10,} FTDs ({bm['node_name']})")
        if wm['forward_predictions']:
            for fp in wm['forward_predictions'][:2]:
                print(f"       → T+{fp['offset_from_event']:>2} = {fp['predicted_date']}: "
                      f"{fp['node_name']}")

    return waterfall_map


# ═════════════════════════════════════════════════════════════════════════
# 4. THE PHRASEBOOK: Translate patterns into plain English
# ═════════════════════════════════════════════════════════════════════════
def build_phrasebook(z_scores, daily_stress, oi_matrix, ftd_df):
    """
    Create a structured phrasebook that maps observable OI patterns
    to their settlement-language meaning.
    """
    print("\n" + "=" * 70)
    print("  4. THE SETTLEMENT PHRASEBOOK")
    print("=" * 70)

    phrases = []
    dates = z_scores.index

    for dt in dates:
        if daily_stress[dt] < daily_stress.quantile(0.85):
            continue  # Only translate loud days

        day_z = z_scores.loc[dt]
        day_oi = oi_matrix.loc[dt]

        # Pattern 1: Broad deep OTM surge (many strikes spike simultaneously)
        n_elevated = (day_z.abs() > 2).sum()
        if n_elevated >= 3:
            total_excess = day_oi[day_z > 2].sum()
            if day_z[day_z > 2].mean() > 0:
                phrases.append({
                    "date": dt.strftime("%Y-%m-%d"),
                    "pattern": "BROAD_DEEP_OTM_SURGE",
                    "translation": f"Settlement pipeline flooding: {n_elevated} strikes "
                                   f"elevated simultaneously, {total_excess:,.0f} excess contracts. "
                                   f"A large FTD batch entered the system ~T-3 to T-6 days ago.",
                    "severity": "HIGH" if n_elevated >= 5 else "MODERATE",
                    "n_strikes": int(n_elevated),
                })

        # Pattern 2: Single-strike spike (one strike way above normal)
        if day_z.max() > 5 and n_elevated <= 2:
            spike_strike = day_z.idxmax()
            phrases.append({
                "date": dt.strftime("%Y-%m-%d"),
                "pattern": "SINGLE_STRIKE_SPIKE",
                "translation": f"Concentrated locate manufacturing at ${spike_strike:.0f}P. "
                               f"z={day_z.max():.1f}σ above baseline. A specific expiration "
                               f"is being used as a synthetic locate vehicle.",
                "severity": "HIGH",
                "strike": float(spike_strike),
            })

        # Pattern 3: OI drain (everything dropping simultaneously)
        n_drained = (day_z < -2).sum()
        if n_drained >= 3:
            phrases.append({
                "date": dt.strftime("%Y-%m-%d"),
                "pattern": "BROAD_DRAIN",
                "translation": f"Settlement resolution: {n_drained} strikes draining "
                               f"simultaneously. Failures being closed out — either via buy-in "
                               f"or capital absorption. Watch for price pressure.",
                "severity": "MODERATE",
                "n_strikes": int(n_drained),
            })

        # Pattern 4: Strike migration (OI shifting from one strike to another)
        surging = day_z[day_z > 2].index.tolist()
        draining = day_z[day_z < -2].index.tolist()
        if surging and draining:
            phrases.append({
                "date": dt.strftime("%Y-%m-%d"),
                "pattern": "STRIKE_MIGRATION",
                "translation": f"Obligation rolling: OI migrating from "
                               f"${', $'.join(f'{s:.0f}' for s in draining[:3])} to "
                               f"${', $'.join(f'{s:.0f}' for s in surging[:3])}. "
                               f"Failures being transferred between expirations or strikes "
                               f"to reset settlement clocks.",
                "severity": "HIGH" if len(surging) >= 2 else "MODERATE",
            })

    # Print the phrasebook
    patterns = defaultdict(list)
    for p in phrases:
        patterns[p["pattern"]].append(p)

    print(f"\n  Total translated events: {len(phrases)}")
    for pattern, items in patterns.items():
        print(f"\n  {pattern}: {len(items)} occurrences")
        for item in items[:3]:
            print(f"    {item['date']} [{item['severity']}]:")
            print(f"      \"{item['translation'][:120]}...\"")

    return phrases


# ═════════════════════════════════════════════════════════════════════════
# 5. CURRENT STATE DECODER: What is the machine saying RIGHT NOW?
# ═════════════════════════════════════════════════════════════════════════
def decode_current_state(oi_matrix, baseline, z_scores, daily_stress, ftd_df):
    """
    Read the most recent OI data and produce a plain-English
    report of what the settlement machinery is doing.
    """
    print("\n" + "=" * 70)
    print("  5. CURRENT STATE DECODE")
    print("=" * 70)

    # Get most recent date
    latest = z_scores.index[-1]
    latest_z = z_scores.loc[latest]
    latest_stress = daily_stress[latest]
    latest_oi = oi_matrix.loc[latest]

    # Recent trend (5-day)
    recent_stress = daily_stress.iloc[-5:]
    trend = "INCREASING" if recent_stress.iloc[-1] > recent_stress.iloc[0] else "DECREASING"

    print(f"\n  Date: {latest.date()}")
    print(f"  Current stress level: {latest_stress:.1f}")
    print(f"  5-day trend: {trend}")
    print(f"  Stress percentile: {(daily_stress < latest_stress).mean()*100:.0f}th")

    # Active signals
    elevated = latest_z[latest_z.abs() > 2].sort_values(ascending=False)
    if len(elevated) > 0:
        print(f"\n  Active signals ({len(elevated)} strikes deviating):")
        for strike, z in elevated.items():
            direction = "ABOVE" if z > 0 else "BELOW"
            print(f"    ${strike:.0f}P: {direction} baseline by {abs(z):.1f}σ "
                  f"(OI={latest_oi[strike]:,.0f})")
    else:
        print(f"\n  No active signals — machine is quiet")

    # Backward trace: what FTD events could be propagating?
    if not ftd_df.empty:
        print(f"\n  Active waterfall threads (FTD events still propagating):")
        for offset, info in sorted(WATERFALL_DICTIONARY.items(), key=lambda x: x[0]):
            if "/" in offset:
                nums = [int(x.replace("T+","")) for x in offset.split("/")]
            else:
                try:
                    nums = [int(offset.replace("T+", ""))]
                except ValueError:
                    continue
            
            for n in nums:
                origin = add_bdays(latest, -n)
                mask = (ftd_df["date"] >= origin - pd.Timedelta(days=2)) & \
                       (ftd_df["date"] <= origin + pd.Timedelta(days=2))
                nearby = ftd_df[mask]
                if len(nearby) > 0:
                    max_ftd = nearby["quantity"].max()
                    if max_ftd > ftd_df["quantity"].quantile(0.75):
                        remaining = 45 - n  # Days until terminal boundary
                        print(f"    ⏳ {info['name']} (T+{n}): FTD from {origin.date()}, "
                              f"{max_ftd:,} shares, {remaining}d until terminal")

    # Prediction
    print(f"\n  Upcoming waterfall deadlines:")
    for offset, info in sorted(WATERFALL_DICTIONARY.items(), key=lambda x: x[0]):
        if "/" in offset:
            nums = [int(x.replace("T+","")) for x in offset.split("/")]
        else:
            try:
                nums = [int(offset.replace("T+", ""))]
            except ValueError:
                continue

        for n in nums:
            future = add_bdays(latest, n)
            if n <= 45 and n >= 1:
                # Check if there's an FTD from T-n that would hit this deadline
                origin = add_bdays(latest, 0)  # Look at recent FTDs
                print(f"    📅 {future.date()} (T+{n}): {info['name']}")

    return {
        "date": str(latest.date()),
        "stress": float(latest_stress),
        "trend": trend,
        "n_active_signals": int(len(elevated)),
    }


# ═════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  SETTLEMENT WATERFALL DECODER")
    print("  Learning the machine's language")
    print("=" * 70)

    print("\n  Loading data...")
    data = load_per_strike_oi()
    print(f"  Loaded {len(data)} OI snapshots")
    ftd_df = load_ftd()
    print(f"  Loaded {len(ftd_df)} FTD records")

    # 1. Build baseline
    oi_matrix, baseline, z_scores, daily_stress = build_baseline(data)

    # 2. Detect events
    events, clusters = detect_machine_events(z_scores, daily_stress)

    # 3. Map through waterfall
    waterfall_map = map_waterfall(events, ftd_df, z_scores, daily_stress)

    # 4. Build phrasebook
    phrases = build_phrasebook(z_scores, daily_stress, oi_matrix, ftd_df)

    # 5. Current state
    current = decode_current_state(oi_matrix, baseline, z_scores, daily_stress, ftd_df)

    # Save everything
    results = {
        "waterfall_dictionary": WATERFALL_DICTIONARY,
        "stress_statistics": {
            "mean": float(daily_stress.mean()),
            "std": float(daily_stress.std()),
            "max": float(daily_stress.max()),
            "max_date": str(daily_stress.idxmax().date()),
        },
        "n_events": len(events),
        "n_clusters": len(clusters),
        "waterfall_map": waterfall_map[:30],
        "phrasebook_summary": {
            pattern: len(items) for pattern, items in
            defaultdict(list, {p["pattern"]: [] for p in phrases}).items()
        },
        "phrases_sample": phrases[:50],
        "current_state": current,
    }

    # Count actual patterns
    pattern_counts = defaultdict(int)
    for p in phrases:
        pattern_counts[p["pattern"]] += 1
    results["phrasebook_summary"] = dict(pattern_counts)

    out_path = RESULTS_DIR / "settlement_decoder.json"
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
