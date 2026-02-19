#!/usr/bin/env python3
"""
Phase 12 V2c: Credit Suisse → UBS Lineage Analysis

Tests whether Credit Suisse ATS was the dominant GME venue during Jan 2021
(the same way UBS ATS dominated in May 2024).

Timeline:
- Jan 25-29 2021: GME squeeze / buy button off
- Mar 26 2021: Archegos blowup (Credit Suisse was prime broker, lost $5.5B)
- Jun 12 2023: UBS completes acquisition of Credit Suisse
- May 13-17 2024: GME event week (UBS ATS = 8.9M shares, #1 venue)

Key question: Did Credit Suisse's ATS handle GME volume in Jan 2021,
and did that book migrate to UBS ATS post-merger?

Credit Suisse ATS MPIDs to look for:
- CSIN (Credit Suisse Securities USA LLC)
- CSFB (Credit Suisse First Boston)
- CSSU (Credit Suisse Securities USA)
- CrossFinder ATS (Credit Suisse's dark pool, one of the largest)
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
            "weekStartDate", "issueSymbolIdentifier", "issueName",
            "totalWeeklyShareQuantity", "totalWeeklyTradeCount",
            "MPID", "firmCRDNumber", "marketParticipantName",
            "summaryTypeCode", "tierIdentifier"
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
        print(f"    HTTP {resp.status_code}: {resp.text[:200]}")
        return []

def fetch_week_all(week_date):
    all_records = []
    offset = 0
    while True:
        print(f"    Fetching offset={offset}...")
        page = fetch_week(week_date, offset=offset)
        if not page: break
        filtered = [r for r in page if r.get("issueSymbolIdentifier") in TARGET_SYMBOLS]
        all_records.extend(filtered)
        print(f"      Got {len(page)} records, {len(filtered)} targets")
        if len(page) < 5000: break
        offset += 5000
        time.sleep(0.5)
    return all_records

# ===================================================================
print("="*70)
print("PHASE 12 V2c: CREDIT SUISSE → UBS LINEAGE ANALYSIS")
print("="*70)

# Query weeks spanning the key events
weeks = {
    # Jan 2021 squeeze
    "2021-01-25": "SQUEEZE WEEK",
    "2021-01-18": "PRE-SQUEEZE",
    "2021-02-01": "POST-SQUEEZE",
    # Archegos collapse (March 2021)
    "2021-03-22": "ARCHEGOS WEEK",
    "2021-03-29": "POST-ARCHEGOS",
    # Pre-merger baseline (early 2023)
    "2023-05-15": "PRE-MERGER 2023",
    # Post-merger (late 2023)
    "2023-09-11": "POST-MERGER 2023",
    # May 2024 event (already have this, but include for comparison)
    "2024-05-13": "MAY 2024 EVENT",
}

# Credit Suisse related MPIDs to watch for
CS_MPIDS = {"CSIN", "CSFB", "CSSU", "CSEC", "CROS", "CRSS"}
UBS_MPIDS = {"UBSA", "UBSS"}

all_results = {}
for week_date, label in weeks.items():
    print(f"\n  === {label}: {week_date} ===")
    records = fetch_week_all(week_date)
    all_results[week_date] = {"label": label, "records": records}
    
    if not records:
        print("    No records")
        continue
    
    for sym in ["GME", "AMC", "KOSS", "XRT"]:
        sym_records = [r for r in records if r.get("issueSymbolIdentifier") == sym]
        if not sym_records: continue
        
        # Separate ATS firm-level records
        ats_firm = [r for r in sym_records 
                    if "ATS" in (r.get("summaryTypeCode") or "") 
                    and "NON" not in (r.get("summaryTypeCode") or "")
                    and "FIRM" in (r.get("summaryTypeCode") or "")]
        
        if not ats_firm: continue
        
        # Sort by volume
        sorted_ats = sorted(ats_firm, key=lambda x: int(x.get("totalWeeklyShareQuantity") or 0), reverse=True)
        
        # Find CS and UBS specifically
        cs_vol = sum(int(r.get("totalWeeklyShareQuantity") or 0) for r in ats_firm 
                     if (r.get("MPID") or "") in CS_MPIDS)
        ubs_vol = sum(int(r.get("totalWeeklyShareQuantity") or 0) for r in ats_firm 
                      if (r.get("MPID") or "") in UBS_MPIDS)
        total_ats = sum(int(r.get("totalWeeklyShareQuantity") or 0) for r in ats_firm)
        
        print(f"\n    {sym}: {len(ats_firm)} ATS firms | Total={total_ats:>14,}")
        
        # Flag any CS or UBS entries
        for r in sorted_ats:
            mpid = str(r.get("MPID") or "?")
            name = str(r.get("marketParticipantName") or "?")
            vol = int(r.get("totalWeeklyShareQuantity") or 0)
            
            # Flag Credit Suisse or UBS
            flag = ""
            if mpid in CS_MPIDS or "CREDIT" in name.upper() or "SUISSE" in name.upper() or "CROSSFINDER" in name.upper():
                flag = " 🔴 CREDIT SUISSE"
            elif mpid in UBS_MPIDS or "UBS" in name.upper():
                flag = " 🔵 UBS"
            
            # Show top 5 + any CS/UBS
            rank = sorted_ats.index(r) + 1
            if rank <= 5 or flag:
                print(f"      #{rank:>2} {mpid:<6} {name:<45} {vol:>14,} sh{flag}")
        
        if cs_vol > 0 or ubs_vol > 0:
            print(f"      --- CS total: {cs_vol:>14,} | UBS total: {ubs_vol:>14,} ---")
    
    time.sleep(1)

# ===================================================================
# TIMELINE SUMMARY
# ===================================================================
print("\n" + "="*70)
print("TIMELINE: GME ATS DOMINANCE — CREDIT SUISSE vs UBS")
print("="*70)

print(f"\n  {'Week':<20} {'Label':<20} {'#1 Venue':<20} {'#1 Vol':>14} {'CS Vol':>14} {'UBS Vol':>14}")
print(f"  {'-'*20} {'-'*20} {'-'*20} {'-'*14} {'-'*14} {'-'*14}")

for week_date, label in weeks.items():
    recs = all_results.get(week_date, {}).get("records", [])
    gme = [r for r in recs if r.get("issueSymbolIdentifier") == "GME"]
    ats_firm = [r for r in gme 
                if "ATS" in (r.get("summaryTypeCode") or "") 
                and "NON" not in (r.get("summaryTypeCode") or "")
                and "FIRM" in (r.get("summaryTypeCode") or "")]
    
    if not ats_firm:
        print(f"  {week_date:<20} {label:<20} {'N/A':<20} {'0':>14} {'0':>14} {'0':>14}")
        continue
    
    sorted_ats = sorted(ats_firm, key=lambda x: int(x.get("totalWeeklyShareQuantity") or 0), reverse=True)
    top = sorted_ats[0]
    top_mpid = str(top.get("MPID") or "?")
    top_name = str(top.get("marketParticipantName") or "?")[:18]
    top_vol = int(top.get("totalWeeklyShareQuantity") or 0)
    
    cs_vol = sum(int(r.get("totalWeeklyShareQuantity") or 0) for r in ats_firm 
                 if (r.get("MPID") or "") in CS_MPIDS
                 or "CREDIT" in str(r.get("marketParticipantName") or "").upper()
                 or "SUISSE" in str(r.get("marketParticipantName") or "").upper()
                 or "CROSSFINDER" in str(r.get("marketParticipantName") or "").upper())
    ubs_vol = sum(int(r.get("totalWeeklyShareQuantity") or 0) for r in ats_firm 
                  if (r.get("MPID") or "") in UBS_MPIDS
                  or "UBS" in str(r.get("marketParticipantName") or "").upper())
    
    display = f"{top_mpid} {top_name}"
    print(f"  {week_date:<20} {label:<20} {display:<20} {top_vol:>14,} {cs_vol:>14,} {ubs_vol:>14,}")

# Also scan ALL MPIDs that contain CS-related keywords across all data
print("\n" + "="*70)
print("ALL UNIQUE MPIDs FOUND (checking for Credit Suisse remnants)")
print("="*70)

all_mpids = {}
for week_data in all_results.values():
    for r in week_data.get("records", []):
        mpid = r.get("MPID") or "?"
        name = r.get("marketParticipantName") or "?"
        if mpid not in all_mpids:
            all_mpids[mpid] = name

for mpid in sorted(all_mpids.keys()):
    name = all_mpids[mpid]
    flag = ""
    if any(kw in name.upper() for kw in ["CREDIT", "SUISSE", "CROSSFINDER"]):
        flag = " 🔴 CS"
    if any(kw in name.upper() for kw in ["UBS"]):
        flag = " 🔵 UBS"
    if flag:
        print(f"  {mpid:<8} {name:<50}{flag}")

out_path = OUT_DIR / "round12_v2c_cs_ubs_lineage.json"
with open(out_path, 'w') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
