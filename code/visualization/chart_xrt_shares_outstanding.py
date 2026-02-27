#!/usr/bin/env python3
"""
Stone 4: Physical ETF Destruction — XRT Shares Outstanding Collapse
=====================================================================
Queries multiple sources for XRT (SPDR S&P Retail ETF) daily Shares Outstanding
during the May 10-20, 2024 window.

If XRT SO plummeted by millions of shares on May 14-15, it proves Authorized
Participants executed Custom Redemptions to harvest underlying GME shares for
CNS settlement, while letting illiquid KOSS fail to deliver.

Data Sources (in order of preference):
  1. SEC EDGAR N-PORT filings (State Street as fund sponsor)
  2. Polygon.io reference data (if API key available)
  3. State Street SPDR website (historical fund data)

Output: ../results/stone4_xrt_so.json
"""
import json, os, sys, re, time
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "research contact@example.com"}

# XRT identifiers
XRT_INFO = {
    "ticker": "XRT",
    "name": "SPDR S&P Retail ETF",
    "cusip": "78464A870",
    "isin": "US78464A8707",
    "sponsor": "State Street Global Advisors",
    "cik_state_street": "0001064642",  # SSgA Funds Management
    "cik_spdr": "0001168164",  # SPDR Series Trust
}

# Event window
EVENT_WINDOW = {
    "start": "2024-05-06",
    "event_start": "2024-05-13",
    "event_peak": "2024-05-14",
    "peak_2": "2024-05-15",
    "settlement": "2024-05-17",
    "end": "2024-05-24",
}


def search_nport_filings():
    """Search EDGAR for XRT N-PORT filings around May 2024."""
    # N-PORT is filed monthly by funds, typically with a ~60 day lag
    # May 2024 N-PORT would be filed around July 2024
    url = f"https://data.sec.gov/submissions/CIK{XRT_INFO['cik_spdr']}.json"
    print("[*] Fetching SPDR Series Trust filing index...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        nport_filings = []
        for i, (form, date, acc, doc) in enumerate(zip(forms, dates, accessions, primary_docs)):
            if "NPORT" in form.upper() or "N-PORT" in form.upper():
                if "2024-05" <= date <= "2024-10":
                    nport_filings.append({
                        "form": form,
                        "date": date,
                        "accession": acc,
                        "primary_doc": doc,
                    })
        print(f"  Found {len(nport_filings)} N-PORT filings in May-Oct 2024 window")
        return nport_filings
    except Exception as e:
        print(f"  Error: {e}")
        return []


def search_edgar_for_xrt_so():
    """Search EDGAR full-text for XRT shares outstanding data."""
    queries = [
        '"SPDR S&P Retail" "shares outstanding"',
        '"78464A870" "shares outstanding"',
        '"XRT" "creation" "redemption" 2024',
    ]
    results = {}
    for q in queries:
        url = "https://efts.sec.gov/LATEST/search-index"
        params = {
            "q": q,
            "dateRange": "custom",
            "startdt": "2024-06-01",
            "enddt": "2024-10-31",
        }
        print(f"[*] EDGAR EFTS search: {q[:50]}...")
        try:
            time.sleep(0.2)
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                data = r.json()
                total = data.get("hits", {}).get("total", {}).get("value", 0)
                hits = data.get("hits", {}).get("hits", [])
                results[q[:40]] = {
                    "total": total,
                    "top_hits": [
                        {
                            "form": h["_source"].get("form_type", ""),
                            "date": h["_source"].get("file_date", ""),
                            "entity": h["_source"].get("entity_name", ""),
                        }
                        for h in hits[:3]
                    ],
                }
                print(f"  {total} results")
        except Exception as e:
            results[q[:40]] = {"error": str(e)}
    return results


def try_polygon_so(api_key=None):
    """Try Polygon.io for XRT shares outstanding data."""
    if not api_key:
        api_key = os.environ.get("POLYGON_API_KEY", "")
    if not api_key:
        print("[*] No POLYGON_API_KEY set, skipping Polygon source")
        return {"status": "no_api_key"}

    print("[*] Querying Polygon.io for XRT reference data...")

    # Polygon ticker details endpoint
    url = f"https://api.polygon.io/v3/reference/tickers/XRT"
    params = {"apiKey": api_key}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            data = r.json().get("results", {})
            so = data.get("share_class_shares_outstanding")
            weighted = data.get("weighted_shares_outstanding")
            print(f"  Current SO: {so:,}" if so else "  SO not in response")
            return {
                "status": "ok",
                "current_shares_outstanding": so,
                "weighted_shares_outstanding": weighted,
                "note": "This is current data. Historical daily SO requires Polygon Business plan.",
            }
        else:
            return {"status": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def try_spdr_website():
    """Try State Street SPDR website for historical fund data."""
    urls = [
        "https://www.ssga.com/us/en/intermediary/etfs/funds/spdr-sp-retail-etf-xrt",
        "https://www.ssga.com/us/en/intermediary/etfs/library/product-data/fund-data",
    ]
    results = {}
    for url in urls:
        print(f"[*] Trying SPDR website: {url[:60]}...")
        try:
            r = requests.get(url, timeout=30,
                             headers={"User-Agent": "Mozilla/5.0 (research)"})
            if r.status_code == 200:
                # Look for shares outstanding or NAV data
                so_match = re.search(r'[Ss]hares\s*[Oo]utstanding[^0-9]*([0-9,]+)', r.text)
                nav_match = re.search(r'[Nn][Aa][Vv][^0-9]*\$?([0-9,.]+)', r.text)
                csv_links = re.findall(r'href="([^"]*(?:download|export|csv|xlsx)[^"]*)"',
                                       r.text, re.IGNORECASE)

                results[url[:50]] = {
                    "status": "ok",
                    "shares_outstanding": so_match.group(1) if so_match else None,
                    "nav": nav_match.group(1) if nav_match else None,
                    "data_download_links": csv_links[:5],
                }
            else:
                results[url[:50]] = {"status": f"HTTP {r.status_code}"}
        except Exception as e:
            results[url[:50]] = {"status": "error", "error": str(e)}
    return results


def main():
    print("=" * 70)
    print("STONE 4: Physical ETF Destruction — XRT Shares Outstanding")
    print("=" * 70)
    print()
    print("TARGET: Daily XRT Shares Outstanding during May 10-20, 2024")
    print("HYPOTHESIS: SO plummets on May 14-15 as APs execute Custom")
    print("            Redemptions to harvest GME shares for CNS settlement")
    print()

    results = {
        "stone": 4,
        "name": "Physical ETF Destruction — XRT Shares Outstanding",
        "timestamp": datetime.now().isoformat(),
        "xrt_info": XRT_INFO,
        "event_window": EVENT_WINDOW,
        "hypothesis": (
            "XRT Shares Outstanding drops sharply on May 14-15 as Authorized Participants "
            "redeem ETF units to extract underlying GME shares for CNS delivery. "
            "KOSS shares in XRT are too illiquid to extract, so they fail → 63.4× FTD surge."
        ),
        "data_sources": {},
    }

    # Step 1: N-PORT filings
    results["data_sources"]["nport_filings"] = search_nport_filings()

    # Step 2: EDGAR full-text search
    results["data_sources"]["edgar_search"] = search_edgar_for_xrt_so()

    # Step 3: Polygon.io
    results["data_sources"]["polygon"] = try_polygon_so()

    # Step 4: SPDR website
    results["data_sources"]["spdr_website"] = try_spdr_website()

    # Step 5: Document manual research
    results["manual_research_needed"] = {
        "description": "Get daily XRT Shares Outstanding for May 2024",
        "best_sources": [
            "Bloomberg Terminal: XRT US Equity → DES → Shares Outstanding history",
            "State Street SPDR daily holdings file: https://www.ssga.com/us/en/intermediary/etfs/funds/spdr-sp-retail-etf-xrt (Holdings tab, download daily)",
            "Polygon.io Business plan: GET /v3/reference/tickers/XRT?date=2024-05-14",
            "CRSP database (academic access): daily shares outstanding",
        ],
        "what_proves_hypothesis": [
            "Compare XRT SO on May 13 vs May 15 vs May 17",
            "A drop of >1M shares on May 14-15 proves Custom Redemptions occurred",
            "Cross-reference with XRT FTD data (387K → 3K collapse on May 15)",
            "If GME weight in XRT dropped simultaneously, it proves GME-specific harvesting",
        ],
        "xrt_components_to_check": [
            "GME weight in XRT on May 13 vs May 17",
            "KOSS weight in XRT (if any — KOSS may not be in XRT)",
            "Total creation/redemption unit activity for May 13-17",
        ],
    }

    # Save
    out_path = os.path.join(OUT_DIR, 'stone4_xrt_so.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[✅] Results saved to: {out_path}")

    return results


if __name__ == '__main__':
    main()
