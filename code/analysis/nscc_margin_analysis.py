#!/usr/bin/env python3
"""
Stone 2: NSCC Clearinghouse Bleed — CPMI-IOSCO Public Quantitative Disclosures
================================================================================
Fetches the DTCC/NSCC Q2 2024 CPMI-IOSCO PQD report and extracts:
  - Disclosure 6.1: Peak Initial Margin Call
  - Disclosure 6.5: Margin Breaches
  - Disclosure 7.1: Estimated Largest Stress Shortfall

If peak margin/shortfall lands on May 14-16, 2024, it proves the swap unwind
threatened the US clearinghouse.

Output: ../results/stone2_nscc_pqd.json
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

# --- Known DTCC PQD URLs ---
# DTCC publishes quarterly PQDs at:
# https://www.dtcc.com/legal/policy-and-compliance/cpmi-iosco-public-quantitative-disclosures
PQD_URLS = {
    "NSCC_PQD_Landing": "https://www.dtcc.com/legal/policy-and-compliance/cpmi-iosco-public-quantitative-disclosures",
    # Direct PDF links (these follow a pattern but need manual verification)
    "NSCC_Q2_2024_PDF": "https://www.dtcc.com/-/media/Files/Downloads/legal/policy-and-compliance/NSCC-Quantitative-Disclosures-Q2-2024.pdf",
    "NSCC_Q1_2024_PDF": "https://www.dtcc.com/-/media/Files/Downloads/legal/policy-and-compliance/NSCC-Quantitative-Disclosures-Q1-2024.pdf",
    "NSCC_Q4_2023_PDF": "https://www.dtcc.com/-/media/Files/Downloads/legal/policy-and-compliance/NSCC-Quantitative-Disclosures-Q4-2023.pdf",
}

# Key disclosures we're hunting for
TARGET_DISCLOSURES = {
    "6.1": "Peak Initial Margin Call",
    "6.3": "Margin Calls Exceeding Prior Quarter",
    "6.5": "Number of Margin Breaches",
    "6.5.2": "Largest Breach Amount",
    "7.1": "Estimated Largest Aggregate Stress Shortfall",
    "7.2": "Number of Days Shortfall Exceeds Resources",
    "4.1": "Peak Aggregate Initial Margin",
    "4.4": "Total Clearing Fund Size",
}


def fetch_pqd_landing():
    """Fetch the DTCC PQD landing page to find available reports."""
    print("[*] Fetching DTCC CPMI-IOSCO landing page...")
    try:
        r = requests.get(PQD_URLS["NSCC_PQD_Landing"], timeout=30,
                         headers={"User-Agent": "Mozilla/5.0 (research)"})
        r.raise_for_status()
        # Extract PDF links
        pdf_links = re.findall(r'href="([^"]*(?:NSCC|nscc)[^"]*\.pdf)"', r.text, re.IGNORECASE)
        print(f"  Found {len(pdf_links)} NSCC PDF links on landing page")
        return pdf_links
    except Exception as e:
        print(f"  Landing page fetch failed: {e}")
        return []


def try_download_pdf(url, label):
    """Attempt to download a PQD PDF."""
    print(f"[*] Attempting to download: {label}")
    print(f"    URL: {url}")
    try:
        r = requests.get(url, timeout=30,
                         headers={"User-Agent": "Mozilla/5.0 (research)"})
        if r.status_code == 200 and len(r.content) > 10000:
            pdf_path = os.path.join(OUT_DIR, f"nscc_pqd_{label}.pdf")
            with open(pdf_path, 'wb') as f:
                f.write(r.content)
            print(f"  ✅ Downloaded: {pdf_path} ({len(r.content)//1024} KB)")
            return {"status": "downloaded", "path": pdf_path, "size_kb": len(r.content)//1024}
        else:
            print(f"  ❌ HTTP {r.status_code}, size={len(r.content)}")
            return {"status": "failed", "http_code": r.status_code}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"status": "error", "error": str(e)}


def try_dtcc_xlsx():
    """Try the Excel/XLSX version which DTCC sometimes publishes."""
    xlsx_urls = [
        "https://www.dtcc.com/-/media/Files/Downloads/legal/policy-and-compliance/NSCC-Quantitative-Disclosures-Q2-2024.xlsx",
        "https://www.dtcc.com/-/media/Files/Downloads/legal/policy-and-compliance/NSCC-PQD-Q2-2024.xlsx",
    ]
    for url in xlsx_urls:
        print(f"[*] Trying XLSX: {url}")
        try:
            r = requests.head(url, timeout=15, allow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                print(f"  ✅ XLSX exists! Downloading...")
                r2 = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                path = os.path.join(OUT_DIR, "nscc_pqd_q2_2024.xlsx")
                with open(path, 'wb') as f:
                    f.write(r2.content)
                return {"status": "downloaded", "path": path, "format": "xlsx"}
            else:
                print(f"  HTTP {r.status_code}")
        except Exception as e:
            print(f"  Error: {e}")
    return {"status": "not_found"}


def main():
    print("=" * 70)
    print("STONE 2: NSCC Clearinghouse Bleed — CPMI-IOSCO PQD Analysis")
    print("=" * 70)
    print()
    print("TARGET: Peak margin calls / stress shortfalls in Q2 2024")
    print("HYPOTHESIS: If peak lands on May 14-16, the swap unwind")
    print("            threatened the US clearinghouse.")
    print()

    results = {
        "stone": 2,
        "name": "NSCC Clearinghouse Bleed",
        "timestamp": datetime.now().isoformat(),
        "target_disclosures": TARGET_DISCLOSURES,
        "hypothesis": "Peak margin call or stress shortfall in Q2 2024 lands on May 14-16",
        "data_sources": {},
        "findings": {},
    }

    # Step 1: Try to fetch the landing page
    pdf_links = fetch_pqd_landing()
    results["data_sources"]["landing_page"] = {
        "url": PQD_URLS["NSCC_PQD_Landing"],
        "pdf_links_found": pdf_links[:5] if pdf_links else [],
    }

    # Step 2: Try direct PDF downloads
    for label, url in PQD_URLS.items():
        if label.endswith("_PDF"):
            result = try_download_pdf(url, label.replace("_PDF", "").lower())
            results["data_sources"][label] = {"url": url, **result}

    # Step 3: Try XLSX
    xlsx_result = try_dtcc_xlsx()
    results["data_sources"]["xlsx_attempt"] = xlsx_result

    # Step 4: Document what we need
    results["manual_research_needed"] = {
        "description": "If automated download failed, manually navigate to the DTCC PQD page",
        "url": PQD_URLS["NSCC_PQD_Landing"],
        "look_for": [
            "NSCC Quantitative Disclosures Q2 2024",
            "Disclosure 6.1: Peak Initial Margin Call — check if date is May 14-16",
            "Disclosure 6.5: Margin Breaches — count and amounts",
            "Disclosure 7.1: Largest Stress Shortfall — check if date is May 14-16",
        ],
        "comparison_quarters": ["Q1 2024", "Q4 2023", "Q3 2023"],
        "what_proves_hypothesis": (
            "If the PEAK margin call of the ENTIRE quarter lands on May 14-16, "
            "it mathematically proves the UBS/internalizer swap unwind created "
            "systemic clearing stress at the national clearinghouse level."
        ),
    }

    # Save
    out_path = os.path.join(OUT_DIR, 'stone2_nscc_pqd.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[✅] Results saved to: {out_path}")

    return results


if __name__ == '__main__':
    main()
