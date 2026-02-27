#!/usr/bin/env python3
"""
Phase 12 Vector 2: FINRA Non-ATS Entity Unmasking (FIXED)
Uses historicalWeek with Monday dates in yyyy-MM-dd format.
Downloads full week, filters for target symbols client-side.
"""
import json, sys, time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library required")
    sys.exit(1)

OUT_DIR = Path(__file__).parent
FINRA_URL = "https://api.finra.org/data/group/otcMarket/name/weeklySummaryHistoric"
HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}

TARGET_SYMBOLS = {"GME", "KOSS", "CHWY", "DJT", "AMC", "XRT", "U"}

def fetch_week(week_date, offset=0, limit=5000):
    """Fetch one page of weekly data. week_date must be yyyy-MM-dd (Monday)."""
    payload = {
        "fields": [
            "weekStartDate", "issueSymbolIdentifier", "issueName",
            "totalWeeklyShareQuantity", "totalWeeklyTradeCount",
            "MPID", "firmCRDNumber", "marketParticipantName",
            "summaryTypeCode", "tierIdentifier", "productTypeCode"
        ],
        "compareFilters": [
            {"fieldName": "historicalWeek", "fieldValue": week_date, "compareType": "EQUAL"},
            {"fieldName": "tierIdentifier", "fieldValue": "T1", "compareType": "EQUAL"}  
        ],
        "limit": limit,
        "offset": offset
    }
    
    resp = requests.post(FINRA_URL, json=payload, headers=HEADERS, timeout=60)
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 204:
        return []
    else:
        print(f"    HTTP {resp.status_code}: {resp.text[:300]}")
        return []

def fetch_week_all(week_date):
    """Paginate through all records for a week, filter for target symbols."""
    all_records = []
    offset = 0
    page_size = 5000
    
    while True:
        print(f"    Fetching offset={offset}...")
        page = fetch_week(week_date, offset=offset, limit=page_size)
        if not page:
            break
        
        # Filter for target symbols
        filtered = [r for r in page if r.get("issueSymbolIdentifier") in TARGET_SYMBOLS]
        all_records.extend(filtered)
        
        print(f"      Got {len(page)} records, {len(filtered)} target symbols")
        
        if len(page) < page_size:
            break  # Last page
        offset += page_size
        time.sleep(0.5)
    
    return all_records

# ===================================================================
# QUERY WEEKS
# ===================================================================
print("="*70)
print("PHASE 12 V2: FINRA NON-ATS ENTITY UNMASKING")
print("="*70)

# Event week + baseline weeks (must be Mondays)
weeks = {
    "2024-05-13": "EVENT WEEK (C12 explosion)",
    "2024-05-06": "Week before event",
    "2024-05-20": "Week after event",
    "2024-04-22": "Baseline week 1",
    "2024-04-15": "Baseline week 2",
}

all_results = {}

for week_date, label in weeks.items():
    print(f"\n  === {label}: {week_date} ===")
    records = fetch_week_all(week_date)
    all_results[week_date] = {"label": label, "records": records}
    
    if not records:
        print(f"    No matching records")
        continue
    
    # Group by symbol
    by_symbol = {}
    for r in records:
        sym = r.get("issueSymbolIdentifier", "?")
        if sym not in by_symbol:
            by_symbol[sym] = []
        by_symbol[sym].append(r)
    
    for sym in sorted(by_symbol.keys()):
        sym_records = by_symbol[sym]
        
        # Separate ATS vs Non-ATS
        non_ats = [r for r in sym_records if "NON_ATS" in (r.get("summaryTypeCode") or "")]
        ats_firm = [r for r in sym_records if ("ATS" in (r.get("summaryTypeCode") or "")) and ("NON" not in (r.get("summaryTypeCode") or "")) and ("FIRM" in (r.get("summaryTypeCode") or ""))]
        ats_agg = [r for r in sym_records if ("ATS" in (r.get("summaryTypeCode") or "")) and ("NON" not in (r.get("summaryTypeCode") or "")) and ("FIRM" not in (r.get("summaryTypeCode") or ""))]
        
        print(f"\n    {sym}: {len(sym_records)} records (ATS_AGG={len(ats_agg)}, ATS_FIRM={len(ats_firm)}, NON_ATS={len(non_ats)})")
        
        # Non-ATS data — THE GOLD
        if non_ats:
            sorted_non = sorted(non_ats, key=lambda x: x.get("totalWeeklyShareQuantity", 0) or 0, reverse=True)
            print(f"      *** NON-ATS INTERNALIZERS ***")
            for r in sorted_non:
                name = str(r.get("marketParticipantName") or "DE MINIMIS AGGREGATE")
                mpid = str(r.get("MPID") or "-")
                crd = str(r.get("firmCRDNumber") or "-")
                vol = int(r.get("totalWeeklyShareQuantity") or 0)
                trades = int(r.get("totalWeeklyTradeCount") or 0)
                stype = str(r.get("summaryTypeCode") or "")
                print(f"        {name:<45} | MPID={mpid:<8} | CRD={crd:<8} | {vol:>14,} sh | {trades:>8,} tr | {stype}")
        
        # ATS firm-level — top 5
        if ats_firm:
            sorted_ats = sorted(ats_firm, key=lambda x: x.get("totalWeeklyShareQuantity", 0) or 0, reverse=True)
            print(f"      ATS (top 5):")
            for r in sorted_ats[:5]:
                name = str(r.get("marketParticipantName") or "UNKNOWN")
                mpid = str(r.get("MPID") or "-")
                vol = int(r.get("totalWeeklyShareQuantity") or 0)
                print(f"        {name:<45} | MPID={mpid:<8} | {vol:>14,} sh")
    
    time.sleep(1)

# Save
out_path = OUT_DIR / "round12_v2_entity_unmasking.json"
with open(out_path, 'w') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
