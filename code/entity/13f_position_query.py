#!/usr/bin/env python3
"""
Stone 3: The 13F & FOCUS Double-Entry Trap
===========================================
Queries SEC EDGAR for Q1 and Q2 2024 13F-HR filings from:
  - Virtu Americas (CRD 149823)
  - Citadel Securities (CRD 116797)
  - G1 Execution / Susquehanna (CRD 111528)
  - Jane Street Capital (CRD 103782)
  - UBS Securities (CRD 7654)

Looks for:
  1. Massive GME options positions (call+put parity = conversion hedge)
  2. 13F-CTR (Confidential Treatment Requests) — filing metadata visible even if payload redacted
  3. Quarter-over-quarter GME position changes

Output: ../results/stone3_13f_ctr.json
"""
import json, os, sys, time
from datetime import datetime

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "research contact@example.com"}

# --- Target entities and their EDGAR CIKs ---
# CIK lookup: https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK=virtu&type=13F&dateb=&owner=include&count=10&search_text=&action=getcompany
ENTITIES = {
    "Citadel Advisors LLC": {
        "cik": "0001423053",
        "role": "Non-ATS Internalizer #2 (56.2M GME, 22.8× surge)",
        "also_check": ["Citadel Securities LLC", "Citadel Multi-Strategy"],
    },
    "Virtu Financial LLC": {
        "cik": "0001571891",
        "role": "Non-ATS Internalizer #1 (81.3M GME, 42.1× surge)",
    },
    "Susquehanna International Group (G1 parent)": {
        "cik": "0001446194",
        "role": "Non-ATS Internalizer #3 via G1 Execution (44.2M GME)",
    },
    "Jane Street Group LLC": {
        "cik": "0001595097",
        "role": "Non-ATS Internalizer #4 (38.7M GME, 44.4× surge)",
    },
    "UBS Group AG": {
        "cik": "0001114446",
        "role": "Dual-channel: #1 ATS (8.9M) + #8 OTC (3.6M from zero)",
    },
}

# GME CUSIP for 13F matching
GME_CUSIP = "36467W109"
GME_CUSIP_SHORT = "36467W10"  # 13F uses 8-digit CUSIP sometimes


def get_filings(cik, form_type="13F-HR", count=10):
    """Get recent filings for a CIK from EDGAR."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        filings = []
        for i, (form, date, acc, doc) in enumerate(zip(forms, dates, accessions, primary_docs)):
            if form_type in form:
                filings.append({
                    "form": form,
                    "date": date,
                    "accession": acc.replace("-", ""),
                    "accession_raw": acc,
                    "primary_doc": doc,
                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc.replace('-','')}/{doc}",
                })
                if len(filings) >= count:
                    break
        return filings
    except Exception as e:
        return {"error": str(e)}


def check_13f_ctr(cik, entity_name):
    """Check for 13F-CTR (Confidential Treatment Request) filings."""
    # 13F-CTR is a separate form type
    filings_ctr = get_filings(cik, "13F-CTR", count=5)
    filings_nt = get_filings(cik, "13F-NT", count=5)  # Notice of late filing

    result = {
        "13F-CTR_filings": filings_ctr if isinstance(filings_ctr, list) else [],
        "13F-NT_filings": filings_nt if isinstance(filings_nt, list) else [],
        "has_Q2_2024_CTR": False,
    }

    if isinstance(filings_ctr, list):
        for f in filings_ctr:
            if "2024-07" <= f.get("date", "") <= "2024-09":
                result["has_Q2_2024_CTR"] = True
                result["Q2_2024_CTR_date"] = f["date"]
                print(f"  🚨 FOUND 13F-CTR for Q2 2024! Filed: {f['date']}")
                break

    return result


def search_13f_for_gme(cik, entity_name):
    """Search for GME positions in 13F-HR XML files."""
    filings = get_filings(cik, "13F-HR", count=6)
    if isinstance(filings, dict) and "error" in filings:
        return {"error": filings["error"]}

    gme_positions = []
    for filing in filings:
        if not isinstance(filing, dict) or "accession" not in filing:
            continue

        acc = filing["accession"]
        cik_clean = cik.lstrip("0")
        filing_date = filing.get("date", "")

        # Try to find the infotable XML
        index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{acc}/"
        try:
            time.sleep(0.15)  # SEC rate limit
            r = requests.get(index_url, headers=HEADERS, timeout=30)
            if r.status_code != 200:
                continue

            # Look for infotable XML file
            xml_files = re.findall(r'href="([^"]*infotable[^"]*\.xml)"', r.text, re.IGNORECASE)
            if not xml_files:
                xml_files = re.findall(r'href="([^"]*13[fF][^"]*\.xml)"', r.text)

            for xml_file in xml_files[:1]:
                xml_url = f"{index_url}{xml_file}"
                time.sleep(0.15)
                rx = requests.get(xml_url, headers=HEADERS, timeout=30)
                if rx.status_code == 200:
                    content = rx.text.upper()
                    # Search for GME CUSIP
                    if "36467W" in content or "GAMESTOP" in content:
                        # Extract position details
                        gme_block = extract_gme_from_xml(rx.text)
                        gme_positions.append({
                            "filing_date": filing_date,
                            "accession": filing.get("accession_raw", acc),
                            "gme_found": True,
                            **gme_block,
                        })
                        print(f"  📊 GME found in {filing_date} filing: {gme_block.get('summary', 'see details')}")
                    else:
                        gme_positions.append({
                            "filing_date": filing_date,
                            "gme_found": False,
                        })
        except Exception as e:
            gme_positions.append({
                "filing_date": filing.get("date", "?"),
                "error": str(e),
            })

    return gme_positions


import re

def extract_gme_from_xml(xml_text):
    """Extract GME position details from 13F XML infotable."""
    result = {"shares": [], "calls": [], "puts": [], "summary": ""}

    # Simple regex extraction (13F XML is relatively standard)
    # Look for blocks containing GME CUSIP
    blocks = re.split(r'<infoTable>', xml_text, flags=re.IGNORECASE)
    for block in blocks:
        if "36467W" not in block.upper() and "GAMESTOP" not in block.upper():
            continue

        # Extract value and shares
        value_m = re.search(r'<value>(\d+)</value>', block, re.IGNORECASE)
        shares_m = re.search(r'<sshPrnamt>(\d+)</sshPrnamt>', block, re.IGNORECASE)
        put_call_m = re.search(r'<putCall>(.*?)</putCall>', block, re.IGNORECASE)
        inv_disc_m = re.search(r'<investmentDiscretion>(.*?)</investmentDiscretion>', block, re.IGNORECASE)

        value = int(value_m.group(1)) * 1000 if value_m else 0  # 13F reports in $1000s
        shares = int(shares_m.group(1)) if shares_m else 0
        put_call = put_call_m.group(1).strip().upper() if put_call_m else "SH"

        entry = {"value_usd": value, "quantity": shares, "type": put_call}

        if put_call == "CALL":
            result["calls"].append(entry)
        elif put_call == "PUT":
            result["puts"].append(entry)
        else:
            result["shares"].append(entry)

    total_calls = sum(e["quantity"] for e in result["calls"])
    total_puts = sum(e["quantity"] for e in result["puts"])
    total_shares = sum(e["quantity"] for e in result["shares"])
    total_value = sum(e["value_usd"] for e in result["calls"] + result["puts"] + result["shares"])

    result["summary"] = f"SH: {total_shares:,} | CALL: {total_calls:,} | PUT: {total_puts:,} | Value: ${total_value:,.0f}"

    if total_calls > 0 and total_puts > 0:
        ratio = min(total_calls, total_puts) / max(total_calls, total_puts) if max(total_calls, total_puts) > 0 else 0
        result["call_put_parity_ratio"] = round(ratio, 3)
        if ratio > 0.8:
            result["ALERT"] = f"⚠️ SYNTHETIC PARITY DETECTED: Call/Put ratio = {ratio:.3f} (near 1.0 = conversion hedge)"

    return result


def main():
    print("=" * 70)
    print("STONE 3: The 13F & FOCUS Double-Entry Trap")
    print("=" * 70)
    print()
    print("TARGET: GME options parity hedges on internalizer 13F-HR filings")
    print("KILLSHOT: 13F-CTR (Confidential Treatment) filed in Q2 2024")
    print()

    results = {
        "stone": 3,
        "name": "13F & FOCUS Double-Entry Trap",
        "timestamp": datetime.now().isoformat(),
        "gme_cusip": GME_CUSIP,
        "entities": {},
    }

    for entity_name, info in ENTITIES.items():
        cik = info["cik"]
        print(f"\n{'='*50}")
        print(f"[*] {entity_name} (CIK: {cik})")
        print(f"    Role: {info['role']}")
        print(f"{'='*50}")

        entity_result = {
            "cik": cik,
            "role": info["role"],
        }

        # Check for 13F-CTR (the killshot)
        print(f"\n  [CTR] Checking for Confidential Treatment Requests...")
        entity_result["ctr_check"] = check_13f_ctr(cik, entity_name)

        # Search 13F-HR for GME positions
        print(f"\n  [13F] Searching for GME positions across recent filings...")
        entity_result["gme_positions"] = search_13f_for_gme(cik, entity_name)

        results["entities"][entity_name] = entity_result
        time.sleep(0.5)  # Be polite to EDGAR

    # Summary of findings
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    ctr_found = []
    parity_alerts = []
    for name, data in results["entities"].items():
        if data.get("ctr_check", {}).get("has_Q2_2024_CTR"):
            ctr_found.append(name)
        for pos in data.get("gme_positions", []):
            if isinstance(pos, dict) and pos.get("ALERT"):
                parity_alerts.append(f"{name} ({pos.get('filing_date','')}): {pos['ALERT']}")

    results["summary"] = {
        "entities_with_Q2_2024_CTR": ctr_found,
        "synthetic_parity_alerts": parity_alerts,
        "ctr_killshot": len(ctr_found) > 0,
    }

    if ctr_found:
        print(f"\n  🚨🚨🚨 KILLSHOT: {len(ctr_found)} entities filed 13F-CTR in Q2 2024:")
        for name in ctr_found:
            print(f"    → {name}")
    else:
        print(f"\n  No 13F-CTR filings found for Q2 2024 (check manually)")

    if parity_alerts:
        print(f"\n  ⚠️ SYNTHETIC PARITY HEDGES DETECTED:")
        for alert in parity_alerts:
            print(f"    → {alert}")

    # Save
    out_path = os.path.join(OUT_DIR, 'stone3_13f_ctr.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[✅] Results saved to: {out_path}")

    return results


if __name__ == '__main__':
    main()
