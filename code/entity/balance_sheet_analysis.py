#!/usr/bin/env python3
"""
Action 1: Interrogate the Client (Third Point & AETOS Context)

Mission: Extract the exact context of "orderly wind down" and "margin call"
from SEC EDGAR filings to determine if they are boilerplate risk disclosures
or specific event-driven references naming a prime broker or date.

Sources:
  - Third Point Private Capital Partners (Form 10-12G, CIK 2025369)
  - AETOS Capital Group (N-CSR, CIK 1169578 / 1169583)
"""

import urllib.request
import re
import html
import json
import os
import time

HEADERS = {'User-Agent': 'research admin@microstructure-forensics.com'}
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')


def fetch_edgar_document(cik, accession):
    """Fetch a specific SEC filing document by CIK and accession number."""
    acc_clean = accession.replace('-', '')
    index_url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"

    print(f"[*] Accessing SEC API for CIK {cik}...")
    try:
        r = urllib.request.Request(index_url, headers=HEADERS)
        with urllib.request.urlopen(r) as response:
            data = json.loads(response.read().decode('utf-8'))

        recent = data.get('filings', {}).get('recent', {})
        for i, acc in enumerate(recent.get('accessionNumber', [])):
            if acc == accession:
                doc = recent['primaryDocument'][i]
                doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc}"
                print(f"[*] Downloading: {doc_url}")

                doc_r = urllib.request.Request(doc_url, headers=HEADERS)
                with urllib.request.urlopen(doc_r) as doc_resp:
                    raw_html = doc_resp.read().decode('utf-8', errors='ignore')

                # Clean HTML to plain text
                text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', ' ', text)
                return re.sub(r'\s+', ' ', html.unescape(text)).strip()
    except Exception as e:
        print(f"[-] Error: {e}")
    return None


def scan_text_for_keywords(text, entity_name, keywords, window=400):
    """Scan filing text for keywords and extract surrounding context."""
    print(f"\n{'=' * 80}\n[+] SEC TEXT EXTRACTION: {entity_name}\n{'=' * 80}")
    found_any = False
    results = []

    for kw in keywords:
        hits = [m.start() for m in re.finditer(re.escape(kw), text, re.IGNORECASE)]
        if not hits:
            continue

        found_any = True
        print(f"\n🚨 KEYWORD TRIGGER: '{kw.upper()}' ({len(hits)} occurrences)")
        for i, idx in enumerate(hits[:5]):  # Show top 5 hits
            start = max(0, idx - window)
            end = min(len(text), idx + len(kw) + window)
            snippet = text[start:end]
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            snippet_highlighted = pattern.sub(f"\n\n>>> {kw.upper()} <<<\n", snippet)
            print(f"  [Hit {i + 1}] ...{snippet_highlighted}...\n  " + "-" * 76)

            results.append({
                "entity": entity_name,
                "keyword": kw,
                "hit_number": i + 1,
                "context": snippet.strip(),
                "is_boilerplate": None  # Must be assessed manually
            })

    if not found_any:
        print("  [-] No matching keywords found in text.")

    return results


def main():
    all_results = {
        "_metadata": {
            "title": "Client Autopsy — Third Point & AETOS Keyword Extraction",
            "date": "2026-02-18",
            "purpose": "Determine if 'orderly wind down' and 'margin call' references are boilerplate or event-specific",
            "keywords_searched": ["orderly wind down", "prime broker", "forced liquidation", "margin call", "swap", "ubs", "liquidat"]
        },
        "third_point": [],
        "aetos": []
    }

    # 1. Third Point Private Capital Partners (May 31, 2024)
    print("\n" + "=" * 80)
    print("STRIKE 1: THIRD POINT PRIVATE CAPITAL PARTNERS")
    print("=" * 80)
    tp_text = fetch_edgar_document("0002025369", "0001104659-24-067309")
    if tp_text:
        all_results["third_point"] = scan_text_for_keywords(
            tp_text, "THIRD POINT (Form 10-12G)",
            ["orderly wind down", "prime broker", "forced liquidation", "margin call", "swap"]
        )
    time.sleep(0.5)  # SEC rate limit

    # 2. AETOS Distressed Investment Strategies Fund
    print("\n" + "=" * 80)
    print("STRIKE 2: AETOS CAPITAL GROUP")
    print("=" * 80)
    aetos_text = fetch_edgar_document("0001169578", "0001193125-24-150644")
    if aetos_text:
        all_results["aetos"] = scan_text_for_keywords(
            aetos_text, "AETOS FUNDS",
            ["margin call", "prime broker", "ubs", "liquidat"]
        )

    # Save results
    out_path = os.path.join(RESULTS_DIR, 'client_analysis_results.json')
    with open(out_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n💾 Results saved to {out_path}")


if __name__ == "__main__":
    main()
