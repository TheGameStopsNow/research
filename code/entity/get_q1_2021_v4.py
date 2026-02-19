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
    
    # Get all xml files
    xml_files = re.findall(r'href="([^"]*\.xml)"', r_idx.text, re.IGNORECASE)
    
    for xml_file in xml_files:
        if "primary_doc" in xml_file.lower():
            continue
        
        xml_url = "https://www.sec.gov" + xml_file
        print("Checking", xml_url)
        r_xml = requests.get(xml_url, headers=HEADERS)
        if "36467W" in r_xml.text.upper() or "GAMESTOP" in r_xml.text.upper():
            print(f"FOUND GME IN {xml_url}")
            lines = r_xml.text.split('\n')
            for i, line in enumerate(lines):
                if "GAMESTOP" in line.upper() or "36467W" in line.upper():
                    print("\n".join(lines[max(0, i-2):min(len(lines), i+8)]))
