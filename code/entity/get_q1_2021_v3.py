import requests, re

HEADERS = {"User-Agent": "research contact@example.com"}

accessions = [
    "000095012321007263",
    "000095012321007261",
    "000095012321007021"
]

for acc in accessions:
    index_url = f"https://www.sec.gov/Archives/edgar/data/1423053/{acc}/"
    r_idx = requests.get(index_url, headers=HEADERS)
    xml_files = re.findall(r'href="([^"]*infotable[^"]*\.xml)"', r_idx.text, re.IGNORECASE)
    
    if not xml_files:
        xml_files = re.findall(r'href="([^"]*13[fF][^"]*\.xml)"', r_idx.text, re.IGNORECASE)
        
    for xml_file in xml_files:
        xml_url = index_url + xml_file
        r_xml = requests.get(xml_url, headers=HEADERS)
        if "36467W" in r_xml.text.upper() or "GAMESTOP" in r_xml.text.upper():
            print(f"FOUND GME IN {xml_url}")
            lines = r_xml.text.split('\n')
            for i, line in enumerate(lines):
                if "GAMESTOP" in line.upper() or "36467W" in line.upper():
                    print("\n".join(lines[max(0, i-2):min(len(lines), i+8)]))
