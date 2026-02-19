import requests, re

HEADERS = {"User-Agent": "research contact@example.com"}
index_url = "https://www.sec.gov/Archives/edgar/data/1423053/000095012321007261/"
r_idx = requests.get(index_url, headers=HEADERS)
xml_files = re.findall(r'href="([^"]*infotable[^"]*\.xml)"', r_idx.text, re.IGNORECASE)
if not xml_files:
    xml_files = ["13f-hr_infotable.xml"]
xml_url = index_url + xml_files[0]
r_xml = requests.get(xml_url, headers=HEADERS)

lines = r_xml.text.split('\n')
for i, line in enumerate(lines):
    if "GAMESTOP" in line.upper() or "36467W" in line.upper():
        print(lines[i-2:i+8])

