#!/usr/bin/env python3
"""
STRIKE 2: CLIENT AUTOPSY (EDGAR TEXT EXTRACTION)
Extract the exact contextual wording from Third Point and AETOS filings 
regarding "orderly wind down", "margin calls", and Prime Broker issues.
"""
import urllib.request, re, html, ssl, json, os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HEADERS = {'User-Agent': 'research admin@microstructure-forensics.com'}
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results')

TARGET_FILINGS = [
    {
        "name": "Third Point Private Capital Partners (10-12G)",
        "cik": "0002025369",
        "filing_type": "10-12G",
        "keywords": ["orderly wind down", "prime broker", "liquidat", "swap", "margin call",
                     "total return", "counterparty", "termination", "unwind", "collateral"]
    },
    {
        "name": "AETOS Distressed Investment Strategies Fund III (N-CSR)",
        "cik": "0001169578",
        "filing_type": "N-CSR",
        "keywords": ["margin call", "prime broker", "forced", "liquidat", "ubs",
                     "credit suisse", "counterparty", "swap", "collateral", "default"]
    },
    {
        "name": "AETOS Multi-Strategy Arbitrage Fund (N-CSR)",
        "cik": "0001169583",
        "filing_type": "N-CSR",
        "keywords": ["margin call", "prime broker", "forced", "liquidat", "ubs",
                     "credit suisse", "counterparty", "swap", "collateral", "default"]
    },
]

print("=" * 75)
print("STRIKE 2: CLIENT AUTOPSY (EDGAR TEXT EXTRACTION)")
print("=" * 75)

all_results = []

for target in TARGET_FILINGS:
    cik = target['cik']
    cik_int = int(cik)
    cik_padded = cik.lstrip('0').zfill(10)
    
    print(f"\n{'='*60}")
    print(f"[*] {target['name']}")
    print(f"    CIK: {cik} | Type: {target['filing_type']}")
    print(f"{'='*60}")
    
    # Get filing index from EDGAR Full-Text Search API
    try:
        # Use the submissions endpoint
        sub_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        req = urllib.request.Request(sub_url, headers=HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            sub_data = json.loads(resp.read().decode('utf-8'))
        
        company_name = sub_data.get('name', 'Unknown')
        print(f"    Company: {company_name}")
        
        recent = sub_data.get('filings', {}).get('recent', {})
        accessions = recent.get('accessionNumber', [])
        forms = recent.get('form', [])
        dates = recent.get('filingDate', [])
        docs = recent.get('primaryDocument', [])
        
        # Find matching filings
        matches = []
        for i, form in enumerate(forms):
            if target['filing_type'] in form:
                matches.append({
                    'accession': accessions[i],
                    'form': form,
                    'date': dates[i],
                    'doc': docs[i]
                })
        
        if not matches:
            # Try all filings if specific type not found
            print(f"    [!] No {target['filing_type']} found. Available forms: {list(set(forms[:10]))}")
            # Take the most recent filing
            if accessions:
                matches = [{'accession': accessions[0], 'form': forms[0], 'date': dates[0], 'doc': docs[0]}]
        
        filing_results = {'name': target['name'], 'cik': cik, 'filings_found': len(matches), 'hits': []}
        
        for match in matches[:3]:  # Process up to 3 most recent filings
            acc = match['accession']
            acc_clean = acc.replace('-', '')
            doc = match['doc']
            
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{doc}"
            print(f"\n    📄 Filing: {match['form']} ({match['date']})")
            print(f"       URL: {doc_url}")
            
            try:
                doc_req = urllib.request.Request(doc_url, headers=HEADERS)
                with urllib.request.urlopen(doc_req, context=ctx, timeout=45) as doc_resp:
                    raw_html = doc_resp.read().decode('utf-8', errors='ignore')
                
                # Strip HTML tags
                text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', ' ', text)
                clean_text = re.sub(r'\s+', ' ', html.unescape(text)).strip()
                
                print(f"       Text length: {len(clean_text):,} chars")
                
                found_any = False
                for kw in target['keywords']:
                    hits = [m.start() for m in re.finditer(r'\b' + re.escape(kw), clean_text, re.IGNORECASE)]
                    if hits:
                        found_any = True
                        print(f"\n    🚨 HIT: '{kw.upper()}' ({len(hits)} occurrence{'s' if len(hits)>1 else ''})")
                        for idx in hits[:2]:  # Show first 2 occurrences
                            start = max(0, idx - 300)
                            end = min(len(clean_text), idx + len(kw) + 300)
                            snippet = clean_text[start:end]
                            # Highlight the keyword
                            pattern = re.compile(re.escape(kw), re.IGNORECASE)
                            highlighted = pattern.sub(f">>>{kw.upper()}<<<", snippet)
                            print(f"    ...{highlighted}...")
                            print(f"    {'─'*55}")
                            
                            filing_results['hits'].append({
                                'keyword': kw,
                                'filing_date': match['date'],
                                'form': match['form'],
                                'snippet': snippet,
                                'position': idx
                            })
                
                if not found_any:
                    print("    [-] No keyword hits in this filing.")
                    
            except Exception as e:
                print(f"    [-] Error downloading filing: {e}")
        
        all_results.append(filing_results)
        
    except Exception as e:
        print(f"    [-] Error querying EDGAR for {target['name']}: {e}")
        all_results.append({'name': target['name'], 'error': str(e)})

# Save results
out_path = os.path.join(OUT_DIR, 'phase16c_client_disclosures.json')
with open(out_path, 'w') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\n\n✅ Client disclosure results saved: {out_path}")
print(f"   Total entities scanned: {len(all_results)}")
print(f"   Total keyword hits: {sum(len(r.get('hits', [])) for r in all_results)}")
