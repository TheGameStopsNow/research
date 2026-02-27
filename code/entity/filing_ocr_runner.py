#!/usr/bin/env python3
"""OCR extraction from Citadel FY2024 scanned PDF — standalone runner"""
import pdf2image
import pytesseract
import json, re, os

PDF_PATH = '[ARCHIVE_PATH]/citadel_main/CDRG_FY2024.pdf'
RESULTS_DIR = '[BUNDLE_PATH]/results'

KEYWORDS = [
    'failed to deliver', 'fails to deliver', 'fails to receive',
    'failed to receive', 'net capital', 'deduction', 'charges',
    'aggregate indebtedness', 'excess net capital', 'total assets',
    'total liabilities', "member's capital", 'pledged', 'collateral',
    'unsettled', 'forward starting', 'securities owned', 'securities sold',
    'securities loaned', 'securities borrowed', 'receivable', 'payable'
]

print("=" * 70)
print("CITADEL FY2024 FAILS CHARGE — OCR EXTRACTION")
print("=" * 70)
print(f"[*] Source: {PDF_PATH}")

info = pdf2image.pdfinfo_from_path(PDF_PATH)
total_pages = info.get('Pages', 0)
print(f"[*] Total pages: {total_pages}")

results = {
    "_metadata": {
        "title": "Citadel Securities LLC FY2024 — OCR Extraction",
        "source": "CDRG_FY2024.pdf (scanned)",
        "method": "Tesseract OCR at 300 DPI",
        "date": "2026-02-18",
        "total_pages": total_pages
    },
    "pages": []
}

full_text = {}

batch_size = 3
for bs in range(1, total_pages + 1, batch_size):
    be = min(bs + batch_size - 1, total_pages)
    print(f"\n[*] Processing pages {bs}-{be}...")
    
    try:
        pages = pdf2image.convert_from_path(PDF_PATH, dpi=300, first_page=bs, last_page=be)
    except Exception as e:
        print(f"  [-] Error: {e}")
        continue
    
    for j, img in enumerate(pages):
        pnum = bs + j
        text = pytesseract.image_to_string(img)
        full_text[pnum] = text.strip()
        text_lower = text.lower()
        
        matched = [kw for kw in KEYWORDS if kw in text_lower]
        
        if matched:
            page_data = {"page": pnum, "matched_keywords": matched, "relevant_lines": []}
            print(f"\n  [+] PAGE {pnum}: {', '.join(matched[:5])}")
            
            for line in text.split('\n'):
                ls = line.strip()
                if not ls:
                    continue
                ll = ls.lower()
                if any(kw in ll for kw in KEYWORDS):
                    print(f"      {ls}")
                    page_data["relevant_lines"].append(ls)
                elif re.search(r'\$[\d,]+', ls) and len(ls) < 200:
                    page_data["relevant_lines"].append(ls)
            
            results["pages"].append(page_data)
        else:
            print(f"  [ ] Page {pnum}")

# Save results
out = os.path.join(RESULTS_DIR, 'citadel_fy2024_ocr_extraction.json')
with open(out, 'w') as f:
    json.dump(results, f, indent=2)

# Save full text
txt_out = os.path.join(RESULTS_DIR, 'citadel_fy2024_ocr_full_text.txt')
with open(txt_out, 'w') as f:
    for pg in sorted(full_text.keys()):
        f.write(f"\n{'='*70}\n  PAGE {pg}\n{'='*70}\n{full_text[pg]}\n")

print(f"\n💾 OCR results: {out}")
print(f"💾 Full text: {txt_out}")
total_match = len(results['pages'])
total_lines = sum(len(p['relevant_lines']) for p in results['pages'])
print(f"\n[✅] {total_match} pages with matches, {total_lines} relevant lines")
