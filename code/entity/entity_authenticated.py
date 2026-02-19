#!/usr/bin/env python3
"""
Phase 12 Vector 2b: Authenticated FINRA Non-ATS Query
Uses FINRA API key for authenticated access to Non-ATS (internalizer) data.

FINRA API auth: OAuth2 client credentials flow
- Client ID: provided by user
- Must be activated via email before use
"""
import json, sys, time, base64
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library required")
    sys.exit(1)

OUT_DIR = Path(__file__).parent

# FINRA API credentials
FINRA_CLIENT_ID = "eeb6284a36e948c7bb85"
# Note: Public credentials may not require a secret, or use empty string
FINRA_CLIENT_SECRET = ""  # Public credentials may not need this

# Token endpoint
TOKEN_URL = "https://ews.fip.finra.org/fip/rest/ews/oauth2/access_token?grant_type=client_credentials"
DATA_URL = "https://api.finra.org/data/group/otcMarket/name/weeklySummaryHistoric"

TARGET_SYMBOLS = {"GME", "KOSS", "CHWY", "DJT", "AMC", "XRT", "U"}

def get_token():
    """Get OAuth2 access token from FINRA."""
    # FINRA uses Basic auth with client_id:client_secret
    credentials = f"{FINRA_CLIENT_ID}:{FINRA_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        resp = requests.post(TOKEN_URL, headers=headers, timeout=15)
        print(f"  Token response: HTTP {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            return data.get("access_token")
        else:
            print(f"  Token error: {resp.text[:300]}")
            # Try without auth (public access)
            return None
    except Exception as e:
        print(f"  Token exception: {e}")
        return None

def fetch_week(week_date, token=None, offset=0, limit=5000):
    """Fetch weekly data with optional auth."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
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
    
    resp = requests.post(DATA_URL, json=payload, headers=headers, timeout=60)
    if resp.status_code == 200:
        return resp.json()
    elif resp.status_code == 204:
        return []
    else:
        print(f"    HTTP {resp.status_code}: {resp.text[:300]}")
        return []

def fetch_week_all(week_date, token=None):
    """Paginate and filter for target symbols."""
    all_records = []
    offset = 0
    page_size = 5000
    
    while True:
        print(f"    Fetching offset={offset}...")
        page = fetch_week(week_date, token=token, offset=offset, limit=page_size)
        if not page:
            break
        filtered = [r for r in page if r.get("issueSymbolIdentifier") in TARGET_SYMBOLS]
        all_records.extend(filtered)
        print(f"      Got {len(page)} records, {len(filtered)} targets")
        if len(page) < page_size:
            break
        offset += page_size
        time.sleep(0.5)
    
    return all_records

# ===================================================================
# AUTHENTICATE
# ===================================================================
print("="*70)
print("PHASE 12 V2b: AUTHENTICATED FINRA NON-ATS QUERY")
print("="*70)

print("\n  Attempting OAuth2 token...")
token = get_token()
if token:
    print(f"  ✅ Got token: {token[:20]}...")
else:
    print("  ⚠️  No token — using unauthenticated access (Non-ATS may be hidden)")

# ===================================================================
# QUERY - Focus on event week first
# ===================================================================
weeks = {
    "2024-05-13": "EVENT WEEK",
    "2024-04-22": "BASELINE",
}

all_results = {}
for week_date, label in weeks.items():
    print(f"\n  === {label}: {week_date} ===")
    records = fetch_week_all(week_date, token=token)
    all_results[week_date] = {"label": label, "records": records}
    
    if not records:
        print("    No records")
        continue
    
    # Group by symbol, focus on GME and KOSS
    by_symbol = {}
    for r in records:
        sym = r.get("issueSymbolIdentifier", "?")
        if sym not in by_symbol:
            by_symbol[sym] = []
        by_symbol[sym].append(r)
    
    for sym in ["GME", "KOSS", "AMC", "DJT", "CHWY", "XRT", "U"]:
        if sym not in by_symbol:
            continue
        sym_records = by_symbol[sym]
        
        non_ats = [r for r in sym_records if "NON_ATS" in (r.get("summaryTypeCode") or "")]
        ats_firm = [r for r in sym_records if ("ATS" in (r.get("summaryTypeCode") or "")) and ("NON" not in (r.get("summaryTypeCode") or "")) and ("FIRM" in (r.get("summaryTypeCode") or ""))]
        ats_agg = [r for r in sym_records if ("ATS" in (r.get("summaryTypeCode") or "")) and ("NON" not in (r.get("summaryTypeCode") or "")) and ("FIRM" not in (r.get("summaryTypeCode") or ""))]
        
        print(f"\n    {sym}: {len(sym_records)} recs (ATS_AGG={len(ats_agg)}, ATS_FIRM={len(ats_firm)}, NON_ATS={len(non_ats)})")
        
        if non_ats:
            print(f"      🚨 NON-ATS INTERNALIZERS:")
            sorted_non = sorted(non_ats, key=lambda x: int(x.get("totalWeeklyShareQuantity") or 0), reverse=True)
            for r in sorted_non:
                name = str(r.get("marketParticipantName") or "DE MINIMIS")
                mpid = str(r.get("MPID") or "-")
                crd = str(r.get("firmCRDNumber") or "-")
                vol = int(r.get("totalWeeklyShareQuantity") or 0)
                trades = int(r.get("totalWeeklyTradeCount") or 0)
                stype = str(r.get("summaryTypeCode") or "")
                print(f"        {name:<45} MPID={mpid:<8} CRD={crd:<10} {vol:>14,} sh  {trades:>8,} tr  {stype}")
        
        # Top 3 ATS
        if ats_firm:
            sorted_ats = sorted(ats_firm, key=lambda x: int(x.get("totalWeeklyShareQuantity") or 0), reverse=True)
            print(f"      Top ATS:")
            for r in sorted_ats[:3]:
                name = str(r.get("marketParticipantName") or "?")
                vol = int(r.get("totalWeeklyShareQuantity") or 0)
                print(f"        {name:<45} {vol:>14,} sh")
    
    time.sleep(1)

# Summary: Compare ATS aggregate volumes
print("\n" + "="*70)
print("SUMMARY: ATS AGGREGATE VOLUME COMPARISON")
print("="*70)
for sym in ["GME", "KOSS"]:
    for week_date, label in weeks.items():
        recs = all_results.get(week_date, {}).get("records", [])
        sym_recs = [r for r in recs if r.get("issueSymbolIdentifier") == sym]
        ats_agg = [r for r in sym_recs if (r.get("summaryTypeCode") or "") == "ATS_W_SMBL"]
        ats_total = sum(int(r.get("totalWeeklyShareQuantity") or 0) for r in sym_recs if "FIRM" in (r.get("summaryTypeCode") or ""))
        non_ats_total = sum(int(r.get("totalWeeklyShareQuantity") or 0) for r in sym_recs if "NON_ATS" in (r.get("summaryTypeCode") or ""))
        agg_vol = int(ats_agg[0].get("totalWeeklyShareQuantity") or 0) if ats_agg else 0
        print(f"  {sym} {label:<12} | ATS_AGG={agg_vol:>14,} | ATS_FIRM_SUM={ats_total:>14,} | NON_ATS={non_ats_total:>14,}")

out_path = OUT_DIR / "round12_v2b_authenticated.json"
with open(out_path, 'w') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
