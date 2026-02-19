#!/usr/bin/env python3
"""
Phase 12 V2d: Extended CS → UBS Migration Timeline
Monthly samples from Feb 2021 (API minimum) through May 2024.
Tracks CrossFinder (CROS) and UBS ATS (UBSA) volume for GME, AMC, XRT, KOSS.

Key dates in the timeline:
- Feb 2021: Earliest FINRA API data (post-squeeze)
- Mar 2021: Archegos collapse
- Jun 2023: UBS completes Credit Suisse acquisition
- May 2024: GME event week
"""
import json, sys, time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library required")
    sys.exit(1)

OUT_DIR = Path(__file__).parent
DATA_URL = "https://api.finra.org/data/group/otcMarket/name/weeklySummaryHistoric"
TARGET_SYMBOLS = {"GME", "KOSS", "AMC", "XRT"}

def fetch_week(week_date, offset=0, limit=5000):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {
        "fields": [
            "weekStartDate", "issueSymbolIdentifier",
            "totalWeeklyShareQuantity", "totalWeeklyTradeCount",
            "MPID", "marketParticipantName", "summaryTypeCode", "tierIdentifier"
        ],
        "compareFilters": [
            {"fieldName": "historicalWeek", "fieldValue": week_date, "compareType": "EQUAL"},
            {"fieldName": "tierIdentifier", "fieldValue": "T1", "compareType": "EQUAL"}
        ],
        "limit": limit, "offset": offset
    }
    resp = requests.post(DATA_URL, json=payload, headers=headers, timeout=60)
    if resp.status_code == 200: return resp.json()
    elif resp.status_code == 204: return []
    else:
        if resp.status_code != 400:
            print(f"    HTTP {resp.status_code}")
        return []

def fetch_week_all(week_date):
    all_records = []
    offset = 0
    while True:
        page = fetch_week(week_date, offset=offset)
        if not page: break
        filtered = [r for r in page if r.get("issueSymbolIdentifier") in TARGET_SYMBOLS]
        all_records.extend(filtered)
        if len(page) < 5000: break
        offset += 5000
        time.sleep(0.3)
    return all_records

def extract_venue_stats(records, symbol):
    """Extract CS and UBS volume for a given symbol."""
    sym_records = [r for r in records if r.get("issueSymbolIdentifier") == symbol]
    ats_firm = [r for r in sym_records 
                if "ATS" in (r.get("summaryTypeCode") or "") 
                and "NON" not in (r.get("summaryTypeCode") or "")
                and "FIRM" in (r.get("summaryTypeCode") or "")]
    
    cs_vol = 0
    ubs_vol = 0
    total = 0
    top_mpid = ""
    top_vol = 0
    
    for r in ats_firm:
        mpid = str(r.get("MPID") or "")
        name = str(r.get("marketParticipantName") or "")
        vol = int(r.get("totalWeeklyShareQuantity") or 0)
        total += vol
        
        if "CROS" in mpid or "CROSSFINDER" in name.upper() or "CREDIT" in name.upper():
            cs_vol += vol
        if "UBSA" in mpid or ("UBS" in name.upper() and "CROSS" not in name.upper()):
            ubs_vol += vol
        if vol > top_vol:
            top_vol = vol
            top_mpid = mpid
    
    return {
        "cs_vol": cs_vol, "ubs_vol": ubs_vol, "total": total,
        "combined": cs_vol + ubs_vol,
        "top_mpid": top_mpid, "top_vol": top_vol,
        "cs_pct": round(cs_vol / total * 100, 1) if total > 0 else 0,
        "ubs_pct": round(ubs_vol / total * 100, 1) if total > 0 else 0,
        "combined_pct": round((cs_vol + ubs_vol) / total * 100, 1) if total > 0 else 0,
    }

# ===================================================================
# Monthly sample weeks — first Monday of each month
# FINRA minDate = 2021-02-18, so start from Feb 22 2021
# ===================================================================
sample_weeks = [
    # 2021: Post-squeeze through Archegos
    ("2021-02-22", "Feb 2021 (post-squeeze)"),
    ("2021-03-22", "Mar 2021 (Archegos)"),
    ("2021-04-19", "Apr 2021"),
    ("2021-06-14", "Jun 2021"),
    ("2021-08-16", "Aug 2021"),
    ("2021-10-18", "Oct 2021"),
    ("2021-12-13", "Dec 2021"),
    # 2022
    ("2022-02-14", "Feb 2022"),
    ("2022-05-16", "May 2022"),
    ("2022-08-15", "Aug 2022"),
    ("2022-11-14", "Nov 2022"),
    # 2023: Pre-merger, merger, post-merger
    ("2023-02-13", "Feb 2023"),
    ("2023-04-17", "Apr 2023"),
    ("2023-05-15", "May 2023 (pre-merger)"),
    ("2023-06-12", "Jun 2023 (MERGER CLOSE)"),
    ("2023-07-17", "Jul 2023 (post-merger)"),
    ("2023-09-11", "Sep 2023"),
    ("2023-11-13", "Nov 2023"),
    # 2024: Lead-up to event
    ("2024-01-15", "Jan 2024"),
    ("2024-03-11", "Mar 2024"),
    ("2024-04-15", "Apr 2024 (baseline)"),
    ("2024-05-06", "May 6, 2024 (pre-event)"),
    ("2024-05-13", "May 13, 2024 (EVENT)"),
    ("2024-05-20", "May 20, 2024 (post-event)"),
]

print("="*70)
print("PHASE 12 V2d: EXTENDED CS→UBS MIGRATION TIMELINE")
print("="*70)

all_stats = {}
for week_date, label in sample_weeks:
    sys.stdout.write(f"\r  Querying {week_date} ({label})...                    ")
    sys.stdout.flush()
    records = fetch_week_all(week_date)
    
    stats = {}
    for sym in ["GME", "AMC", "XRT", "KOSS"]:
        stats[sym] = extract_venue_stats(records, sym)
    
    all_stats[week_date] = {"label": label, "stats": stats, "records": records}
    time.sleep(0.5)

print("\n")

# ===================================================================
# PRINT MIGRATION TABLE
# ===================================================================
for sym in ["GME", "AMC", "XRT"]:
    print(f"\n{'='*90}")
    print(f"  {sym} — CrossFinder (CS) vs UBS ATS Volume Migration")
    print(f"{'='*90}")
    print(f"  {'Week':<12} {'Label':<30} {'CS(CROS)':>10} {'UBS(UBSA)':>10} {'Combined':>10} {'ATS Total':>12} {'CS%':>6} {'UBS%':>6} {'Comb%':>6} {'#1':>6}")
    print(f"  {'-'*12} {'-'*30} {'-'*10} {'-'*10} {'-'*10} {'-'*12} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    
    for week_date, label in sample_weeks:
        s = all_stats[week_date]["stats"][sym]
        marker = ""
        if "MERGER" in label.upper(): marker = " ◀◀"
        elif "EVENT" in label.upper(): marker = " 🔥"
        elif "Archegos" in label: marker = " 💥"
        
        print(f"  {week_date:<12} {label:<30} {s['cs_vol']:>10,} {s['ubs_vol']:>10,} {s['combined']:>10,} {s['total']:>12,} {s['cs_pct']:>5.1f}% {s['ubs_pct']:>5.1f}% {s['combined_pct']:>5.1f}% {s['top_mpid']:>6}{marker}")

# ===================================================================
# KEY TRANSITION MOMENTS
# ===================================================================
print(f"\n\n{'='*70}")
print("KEY TRANSITION ANALYSIS")
print(f"{'='*70}")

# Find the last week CrossFinder had any volume
last_cs_week = None
for week_date, label in sample_weeks:
    for sym in ["GME", "AMC", "XRT"]:
        if all_stats[week_date]["stats"][sym]["cs_vol"] > 0:
            last_cs_week = (week_date, label)

if last_cs_week:
    print(f"\n  Last week CrossFinder had ANY volume: {last_cs_week[0]} ({last_cs_week[1]})")

# Find first week post-merger where CS=0
for week_date, label in sample_weeks:
    if "2023-06" <= week_date:
        all_cs = sum(all_stats[week_date]["stats"][sym]["cs_vol"] for sym in ["GME", "AMC", "XRT"])
        if all_cs == 0:
            print(f"  First post-merger week with CS=0:    {week_date} ({label})")
            break

# UBS growth rate
for sym in ["GME", "AMC"]:
    pre_merger = all_stats.get("2023-05-15", {}).get("stats", {}).get(sym, {}).get("ubs_vol", 0)
    post_merger = all_stats.get("2023-09-11", {}).get("stats", {}).get(sym, {}).get("ubs_vol", 0)
    event = all_stats.get("2024-05-13", {}).get("stats", {}).get(sym, {}).get("ubs_vol", 0)
    if pre_merger > 0:
        print(f"\n  {sym} UBS ATS growth:")
        print(f"    Pre-merger (May 2023):  {pre_merger:>12,}")
        print(f"    Post-merger (Sep 2023): {post_merger:>12,} ({post_merger/pre_merger:.1f}×)")
        print(f"    Event (May 2024):       {event:>12,} ({event/pre_merger:.1f}×)")

# Combined CS+UBS market share over time
print(f"\n  Combined CS+UBS share of ATS total (GME):")
for week_date, label in sample_weeks:
    s = all_stats[week_date]["stats"]["GME"]
    if s["total"] > 0:
        print(f"    {week_date} {label:<30} {s['combined_pct']:>5.1f}% = CS {s['cs_pct']:.1f}% + UBS {s['ubs_pct']:.1f}%")

out_path = OUT_DIR / "round12_v2d_extended_timeline.json"
with open(out_path, 'w') as f:
    # Save stats only (not raw records, to keep file manageable)
    save_data = {}
    for week_date in all_stats:
        save_data[week_date] = {
            "label": all_stats[week_date]["label"],
            "stats": all_stats[week_date]["stats"]
        }
    json.dump(save_data, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
