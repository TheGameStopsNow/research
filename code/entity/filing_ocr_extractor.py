#!/usr/bin/env python3
"""
Action 2: Extract Citadel FY2024 Fails Data (OCR Bypass)

Mission: Use OCR to extract FTD/FTR and Net Capital data from the scanned
Citadel Securities FY2024 X-17A-5 PDF. Compare FY2024 Fails Charge to
the FY2023 baseline ($185M FTDs, $108M FTRs).

Prerequisites:
  pip install pdf2image pytesseract
  brew install tesseract        # macOS
  apt-get install tesseract-ocr # Linux

Source PDF: review_package_02_archive/citadel_main/CDRG_FY2024.pdf
"""

import sys
import os
import json
import re

try:
    import pdf2image
    import pytesseract
except ImportError:
    print("\n[!] Missing dependencies. Please run:")
    print("    pip install pdf2image pytesseract")
    print("    brew install tesseract  # macOS")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR = os.path.dirname(SCRIPT_DIR)
ARCHIVE_DIR = os.path.join(os.path.dirname(BUNDLE_DIR), 'review_package_02_archive')
PDF_PATH = os.path.join(ARCHIVE_DIR, 'citadel_main', 'CDRG_FY2024.pdf')
RESULTS_DIR = os.path.join(BUNDLE_DIR, 'results')

# Keywords to search for in each OCR'd page
KEYWORDS = [
    'failed to deliver', 'fails to deliver', 'fails to receive',
    'failed to receive', 'net capital', 'deduction', 'charges',
    'aggregate indebtedness', 'excess net capital', 'total assets',
    'total liabilities', "member's capital", 'pledged', 'collateral',
    'unsettled', 'forward starting'
]


def main():
    print("\n" + "=" * 70)
    print("CITADEL FY2024 FAILS CHARGE — OCR EXTRACTION")
    print("=" * 70)

    if not os.path.exists(PDF_PATH):
        print(f"[-] PDF not found: {PDF_PATH}")
        print("    Please ensure the FY2024 X-17A-5 PDF is in the archive.")
        sys.exit(1)

    print(f"[*] Source: {PDF_PATH}")
    print("[*] Converting PDF pages to images (DPI=300, this may take a minute)...")

    # Focus on pages 8-25 which contain balance sheet + notes + net capital
    try:
        pages = pdf2image.convert_from_path(PDF_PATH, dpi=300, first_page=8, last_page=25)
    except Exception as e:
        print(f"[-] PDF conversion failed: {e}")
        sys.exit(1)

    results = {
        "_metadata": {
            "title": "Citadel Securities LLC FY2024 — OCR Extraction",
            "source": "CDRG_FY2024.pdf (scanned)",
            "method": "Tesseract OCR at 300 DPI",
            "date": "2026-02-18"
        },
        "pages": []
    }

    for i, page_img in enumerate(pages, start=8):
        text = pytesseract.image_to_string(page_img)
        text_lower = text.lower()

        matched_keywords = [kw for kw in KEYWORDS if kw in text_lower]

        if matched_keywords:
            page_data = {
                "page": i,
                "matched_keywords": matched_keywords,
                "relevant_lines": []
            }

            print(f"\n  [+] PAGE {i} — Matched: {', '.join(matched_keywords)}")

            for line in text.split('\n'):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                line_lower = line_stripped.lower()
                if any(kw in line_lower for kw in KEYWORDS):
                    print(f"      {line_stripped}")
                    page_data["relevant_lines"].append(line_stripped)

                # Also capture lines with large dollar amounts
                if re.search(r'\$[\d,]+(?:\.\d+)?', line_stripped):
                    if line_stripped not in page_data["relevant_lines"]:
                        page_data["relevant_lines"].append(line_stripped)

            results["pages"].append(page_data)
        else:
            print(f"  [ ] Page {i} — no keyword matches")

    # Save results
    out_path = os.path.join(RESULTS_DIR, 'citadel_fy2024_ocr_extraction.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 OCR results saved to {out_path}")

    # Summary
    total_pages = len(results["pages"])
    total_lines = sum(len(p["relevant_lines"]) for p in results["pages"])
    print(f"\n[✅] Extraction complete: {total_pages} pages with matches, {total_lines} relevant lines captured")


if __name__ == "__main__":
    main()
