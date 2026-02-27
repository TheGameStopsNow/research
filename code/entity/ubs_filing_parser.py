#!/usr/bin/env python3
"""
Stone 1: The Swiss Confession — UBS Q2 2024 NCL Division Analysis
==================================================================
Downloads UBS Group AG Q2 2024 earnings materials and searches for:
  - Non-Core and Legacy (NCL) division performance
  - Risk-Weighted Asset (RWA) reductions in equity derivatives
  - Leverage Ratio Denominator (LRD) changes
  - Any mention of Archegos, Credit Suisse legacy, or equities financing

Target: ~$1.93B notional or ~$739M basis capture showing up as NCL wind-down.

Output: ../results/stone1_ubs_ncl.json
"""
import json, os, sys, re
from datetime import datetime

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
os.makedirs(OUT_DIR, exist_ok=True)

# --- UBS Investor Relations URLs ---
UBS_SOURCES = {
    "investor_relations": "https://www.ubs.com/global/en/investor-relations/financial-information/quarterly-reporting.html",
    # Q2 2024 results were published August 14, 2024
    "q2_2024_press_release": "https://www.ubs.com/global/en/investor-relations/financial-information/quarterly-reporting/2q24.html",
    # SEC EDGAR filings
    "ubs_edgar_cik": "0001114446",
    "ubs_edgar_search": "https://efts.sec.gov/LATEST/search-index?q=%22non-core+and+legacy%22&dateRange=custom&startdt=2024-07-01&enddt=2024-12-31&forms=20-F,6-K",
    "ubs_edgar_filings": "https://efts.sec.gov/LATEST/search-index?q=%22non-core%22+%22risk-weighted%22&forms=6-K&dateRange=custom&startdt=2024-07-01&enddt=2024-10-31",
    # EDGAR full-text search
    "edgar_efts_ncl": "https://efts.sec.gov/LATEST/search-index?q=%22non-core+and+legacy%22+%22equity%22&dateRange=custom&startdt=2024-07-01&enddt=2024-12-31",
}

# Keywords to hunt for in UBS filings
HUNT_KEYWORDS = [
    "Non-Core and Legacy",
    "NCL",
    "Risk-Weighted Assets",
    "RWA",
    "Leverage Ratio Denominator",
    "LRD",
    "equity derivatives",
    "equities financing",
    "prime brokerage",
    "Archegos",
    "Credit Suisse legacy",
    "wind-down",
    "run-off",
    "legacy portfolio",
    "total return swap",
    "equity swap",
]


def search_edgar_efts(query, forms="6-K,20-F"):
    """Search SEC EDGAR full-text search for UBS filings."""
    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "q": query,
        "dateRange": "custom",
        "startdt": "2024-07-01",
        "enddt": "2024-12-31",
        "forms": forms,
    }
    print(f"[*] EDGAR EFTS search: '{query}' in {forms}")
    try:
        r = requests.get(url, params=params, timeout=30,
                         headers={"User-Agent": "research contact@example.com"})
        if r.status_code == 200:
            data = r.json()
            hits = data.get("hits", {}).get("hits", [])
            total = data.get("hits", {}).get("total", {}).get("value", 0)
            print(f"  Found {total} results")
            return {"total": total, "hits": [h.get("_source", {}) for h in hits[:5]]}
        else:
            print(f"  HTTP {r.status_code}")
            return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        print(f"  Error: {e}")
        return {"error": str(e)}


def search_edgar_filing_index(cik="0001114446"):
    """Get UBS's recent filings from EDGAR."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    print(f"[*] Fetching UBS filing index from EDGAR (CIK: {cik})")
    try:
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "research contact@example.com"})
        if r.status_code == 200:
            data = r.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            descs = recent.get("primaryDocDescription", [])

            # Find Q2 2024 6-K filings (July-September 2024)
            q2_filings = []
            for i, (form, date, acc, desc) in enumerate(zip(forms, dates, accessions, descs)):
                if form in ("6-K", "20-F") and date >= "2024-07-01" and date <= "2024-10-31":
                    q2_filings.append({
                        "form": form,
                        "date": date,
                        "accession": acc,
                        "description": desc or "",
                    })
            print(f"  Found {len(q2_filings)} UBS filings in Q2-Q3 2024 window")
            return q2_filings[:10]
        else:
            print(f"  HTTP {r.status_code}")
            return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


def try_fetch_ubs_page():
    """Try to fetch the UBS Q2 2024 investor relations page."""
    url = UBS_SOURCES["q2_2024_press_release"]
    print(f"[*] Fetching UBS Q2 2024 IR page: {url}")
    try:
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0 (research)"})
        if r.status_code == 200:
            # Extract PDF/document links
            pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', r.text, re.IGNORECASE)
            doc_links = re.findall(r'href="([^"]*(?:supplement|presentation|report)[^"]*)"',
                                   r.text, re.IGNORECASE)
            all_links = list(set(pdf_links + doc_links))
            print(f"  Found {len(all_links)} document links")
            return {"status": "ok", "links": all_links[:20]}
        else:
            print(f"  HTTP {r.status_code}")
            return {"status": f"HTTP {r.status_code}"}
    except Exception as e:
        print(f"  Error: {e}")
        return {"status": "error", "error": str(e)}


def main():
    print("=" * 70)
    print("STONE 1: The Swiss Confession — UBS NCL Division Analysis")
    print("=" * 70)
    print()
    print("TARGET: UBS Q2 2024 NCL RWA reduction matching ~$1.93B notional")
    print("        or ~$739M basis capture from Put-Call Parity Settlement Predictor calculation")
    print()

    results = {
        "stone": 1,
        "name": "The Swiss Confession — UBS NCL",
        "timestamp": datetime.now().isoformat(),
        "target_amounts": {
            "notional_gme_only": "$1.93B (56.9M shares × $34.01)",
            "basis_capture": "$739M ($13/share × 56.9M shares)",
            "description": "If UBS NCL shows RWA reductions in this range during Q2 2024, it confirms the swap unwind",
        },
        "hunt_keywords": HUNT_KEYWORDS,
        "data_sources": {},
        "edgar_filings": [],
        "edgar_searches": {},
        "ubs_ir_page": {},
    }

    # Step 1: EDGAR filing index
    filings = search_edgar_filing_index()
    results["edgar_filings"] = filings

    # Step 2: EDGAR full-text searches
    for query in [
        '"non-core and legacy" "equity"',
        '"risk-weighted" "equity derivatives" UBS',
        '"NCL" "wind-down" UBS 2024',
    ]:
        key = query.replace('"', '').replace(' ', '_')[:40]
        results["edgar_searches"][key] = search_edgar_efts(query)

    # Step 3: UBS IR page
    results["ubs_ir_page"] = try_fetch_ubs_page()

    # Step 4: Document manual research
    results["manual_research_needed"] = {
        "description": "Download and read the UBS Q2 2024 Earnings Supplement PDF",
        "primary_url": UBS_SOURCES["q2_2024_press_release"],
        "what_to_find": [
            "NCL division: Total RWA and quarter-over-quarter change",
            "NCL division: Revenue or loss attributed to equity derivatives wind-down",
            "NCL division: 'Equities Financing' or 'Prime Brokerage' line items",
            "Pillar 3 report: LRD changes in 'Equity Derivatives' bucket",
            "Any mention of 'Archegos' or 'legacy positions' being unwound",
            "Compare NCL RWA to Q1 2024 — look for $1-2B discrete reduction",
        ],
        "alternative_sources": [
            "Bloomberg Terminal: UBS Group AG → Earnings → Q2 2024 → NCL segment",
            "UBS Annual Report 2024 (published March 2025): full NCL breakdown",
            "Pillar 3 Risk Report Q2 2024: RWA by asset class",
        ],
    }

    # Save
    out_path = os.path.join(OUT_DIR, 'stone1_ubs_ncl.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[✅] Results saved to: {out_path}")

    return results


if __name__ == '__main__':
    main()
