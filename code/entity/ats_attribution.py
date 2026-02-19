#!/usr/bin/env python3
"""
Vector 3: ATS De-Masking — FINRA OTC Transparency Data
Fetch FINRA ATS data to identify which dark pool venue facilitated the GME/KOSS settlement.

FINRA publishes weekly ATS volume data per ticker. We query for GME and KOSS
around May 13-17 2024 to find the anomalous venue.

URL: https://api.finra.org/data/group/otcMarket/name/weeklySummary
"""
import json, os, sys
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    print("requests not available, using urllib")
    import urllib.request
    import urllib.error

OUT_DIR = Path(__file__).parent

# FINRA OTC Transparency API
# The public endpoint for getting ATS issue data
FINRA_BASE = "https://api.finra.org/data/group/otcMarket/name/weeklySummary"

# Alternative: FINRA issues a CSV download per week
# https://ats.finra.org/TradingParticipants/WeeklyReports

# Since the FINRA API may require specific auth, let's try the public OTC transparency page
# FINRA publishes per-ATS, per-ticker weekly volumes

# The free public data is available at:
# https://otctransparency.finra.org/otctransparency/AtsIssueData
# Parameters: tierIdentifier=T1 (NMS), weekStartDate=YYYY-MM-DD, symbol=GME
# This returns JSON with per-ATS volumes

def fetch_finra_ats(symbol, week_start):
    """Fetch FINRA ATS transparency data for a symbol and week"""
    url = f"https://api.finra.org/data/group/otcMarket/name/weeklySummary"
    
    # Try the OTC transparency API
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # The FINRA API uses POST with filters
    payload = {
        "fields": ["weekStartDate", "issueSymbolIdentifier", "marketParticipantName", "totalWeeklyShareQuantity", "totalWeeklyTradeCount"],
        "compareFilters": [
            {"fieldName": "issueSymbolIdentifier", "fieldValue": symbol, "compareType": "EQUAL"},
            {"fieldName": "weekStartDate", "fieldValue": week_start, "compareType": "EQUAL"},
            {"fieldName": "tierIdentifier", "fieldValue": "T1", "compareType": "EQUAL"}
        ],
        "limit": 100,
        "offset": 0
    }
    
    try:
        if 'requests' in sys.modules:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            else:
                return {"error": resp.status_code, "text": resp.text[:500]}
        else:
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

# Try multiple week start dates around the May 13-17 event
# FINRA weeks typically start Monday
weeks = [
    "2024-05-06",  # Week before the event  
    "2024-05-13",  # THE EVENT WEEK
    "2024-05-20",  # Week after
    "2024-04-29",  # Baseline week 1
    "2024-04-22",  # Baseline week 2
]

tickers = ["GME", "KOSS"]
all_results = {}

for symbol in tickers:
    all_results[symbol] = {}
    for week in weeks:
        print(f"  Fetching {symbol} week {week}...")
        result = fetch_finra_ats(symbol, week)
        all_results[symbol][week] = result
        
        if isinstance(result, list) and len(result) > 0:
            # Sort by volume descending
            sorted_r = sorted(result, key=lambda x: x.get('totalWeeklyShareQuantity', 0), reverse=True)
            print(f"    {len(sorted_r)} ATS venues found")
            for r in sorted_r[:10]:
                name = r.get('marketParticipantName') or 'Unknown'
                vol = r.get('totalWeeklyShareQuantity') or 0
                trades = r.get('totalWeeklyTradeCount') or 0
                print(f"      {name:<40} | {vol:>12,} shares | {trades:>8,} trades")
        elif isinstance(result, dict) and 'error' in result:
            print(f"    Error: {result['error']}")
            if 'text' in result:
                print(f"    Response: {result['text'][:200]}")
        else:
            print(f"    No data returned")

# Save results  
out_path = OUT_DIR / "round11_v3_ats_demasking.json"
with open(out_path, 'w') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
