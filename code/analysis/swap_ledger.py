#!/usr/bin/env python3
"""
Phase 12 Vector 3: Hunting the Swap Ledger
Query DTCC DDR and ICE Trade Vault for Security-Based Swap data
around May 14-17 2024 (the settlement event).

DTCC DDR public dissemination: https://pddata.dtcc.com/gtr/
ICE Trade Vault: https://www.theice.com/swap-trade-vault

Under Reg SBSR, equity SBS must be reported to SDRs.
The public tape shows: Asset Class, Notional, Effective/End Dates, 
but masks counterparty identities.
"""
import json, sys, time
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library required")
    sys.exit(1)

OUT_DIR = Path(__file__).parent

# DTCC Data Repository Public Dissemination
# The DTCC publishes daily slices of swap data
# https://pddata.dtcc.com/gtr/tracker.do 

# DTCC DDR public API endpoint for equity swaps
# Real-time: https://kgc0418-tdw-data2-0.s3.amazonaws.com/slices/CUMULATIVE_EQUITIES_{date}.zip
# Date format: YYYY_MM_DD

def fetch_dtcc_equity_swaps(date_str):
    """Try to fetch DTCC DDR equity swap data for a given date."""
    # DTCC publishes daily cumulative slices
    # Format: YYYY_MM_DD
    formatted = date_str.replace("-", "_")
    
    # Try the known DTCC public data URLs
    urls = [
        f"https://kgc0418-tdw-data2-0.s3.amazonaws.com/slices/CUMULATIVE_EQUITIES_{formatted}.zip",
        f"https://pddata.dtcc.com/ppd/api/report/SECdata?&asOfDate={date_str}&action=download",
        f"https://pddata.dtcc.com/ppd/api/report/SECcumulative?&asOfDate={date_str}&action=download",
    ]
    
    results = []
    for url in urls:
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            results.append({
                "url": url,
                "status": resp.status_code,
                "content_type": resp.headers.get("Content-Type", ""),
                "content_length": resp.headers.get("Content-Length", ""),
            })
            print(f"    {resp.status_code}: {url}")
        except Exception as e:
            results.append({"url": url, "error": str(e)})
            print(f"    ERR: {url}: {e}")
    
    return results

# ICE Trade Vault SEC SDR data
def fetch_ice_sdr(date_str):
    """Check ICE Trade Vault for SEC SDR equity swap data."""
    # ICE SDR public data endpoint
    urls = [
        f"https://www.theice.com/swap-trade-vault/data/downloadReport?reportType=CUMULATIVE&productType=EQUITY&tradeDate={date_str}",
        f"https://reportcenter.theice.com/sdr/equity/{date_str}",
    ]
    
    results = []
    for url in urls:
        try:
            resp = requests.head(url, timeout=10, allow_redirects=True)
            results.append({
                "url": url,
                "status": resp.status_code,
                "content_type": resp.headers.get("Content-Type", ""),
                "final_url": resp.url if resp.url != url else None,
            })
            print(f"    {resp.status_code}: {url[:80]}...")
        except Exception as e:
            results.append({"url": url, "error": str(e)})
            print(f"    ERR: {url[:80]}... : {e}")
    
    return results

# ===================================================================
print("="*70)
print("PHASE 12 V3: SWAP LEDGER HUNT (DTCC DDR + ICE SDR)")
print("="*70)

target_dates = [
    "2024-05-14",  # Pre-positioning (conversions)
    "2024-05-15",  # T+1 
    "2024-05-16",  # T+2
    "2024-05-17",  # OpEx (settlement)
    "2024-05-13",  # RK return
]

all_results = {}

# DTCC DDR
print("\n  === DTCC Data Repository (DDR) ===")
for d in target_dates:
    print(f"\n  Date: {d}")
    dtcc_results = fetch_dtcc_equity_swaps(d)
    all_results[f"dtcc_{d}"] = dtcc_results
    time.sleep(0.5)

# ICE Trade Vault  
print("\n  === ICE Trade Vault ===")
for d in target_dates:
    print(f"\n  Date: {d}")
    ice_results = fetch_ice_sdr(d)
    all_results[f"ice_{d}"] = ice_results
    time.sleep(0.5)

# Also try the DTCC SEC SBSR portal directly
print("\n  === DTCC SEC SBSR Portal ===")
# The SEC SDR data is at pddata.dtcc.com
sbsr_url = "https://pddata.dtcc.com/ppd/api/report/SECdata"
try:
    # Try to get the available dates/reports
    resp = requests.get(f"{sbsr_url}?action=download&asOfDate=2024-05-17", timeout=15)
    print(f"  SEC SBSR response: HTTP {resp.status_code}, Content-Type={resp.headers.get('Content-Type','')}, Size={len(resp.content)}")
    if resp.status_code == 200 and len(resp.content) > 100:
        # Save the raw response
        sbsr_path = OUT_DIR / "dtcc_sbsr_20240517.csv"
        with open(sbsr_path, 'wb') as f:
            f.write(resp.content)
        print(f"  Saved {len(resp.content):,} bytes to {sbsr_path}")
        
        # Try to parse
        import io
        try:
            import pandas as pd
            df = pd.read_csv(io.BytesIO(resp.content))
            print(f"  Parsed: {len(df)} rows, {len(df.columns)} columns")
            print(f"  Columns: {list(df.columns)[:15]}")
            
            # Filter for equity swaps
            if 'Product type' in df.columns:
                equities = df[df['Product type'].str.contains('Equity', case=False, na=False)]
                print(f"  Equity swaps: {len(equities)}")
            elif 'Asset Class' in df.columns:
                equities = df[df['Asset Class'].str.contains('Equit', case=False, na=False)]
                print(f"  Equity swaps: {len(equities)}")
            else:
                equities = df
                print(f"  All records: {len(equities)} (no asset class filter available)")
            
            # Look for large notionals
            notional_cols = [c for c in df.columns if 'notional' in c.lower() or 'amount' in c.lower()]
            if notional_cols:
                print(f"  Notional columns: {notional_cols}")
                
        except Exception as e:
            print(f"  Parse error: {e}")
    
    all_results["sbsr_portal"] = {"status": resp.status_code, "size": len(resp.content)}
    
except Exception as e:
    print(f"  SEC SBSR portal error: {e}")
    all_results["sbsr_portal"] = {"error": str(e)}

# Save
out_path = OUT_DIR / "round12_v3_swap_ledger.json"
with open(out_path, 'w') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nSaved to {out_path}")
