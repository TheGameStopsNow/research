import requests, re

cik = "0001423053"
HEADERS = {"User-Agent": "research contact@example.com"}
url = f"https://data.sec.gov/submissions/CIK{cik}.json"
r = requests.get(url, headers=HEADERS)
data = r.json()
recent = data.get("filings", {}).get("recent", {})
forms = recent.get("form", [])
dates = recent.get("filingDate", [])
accs = recent.get("accessionNumber", [])
docs = recent.get("primaryDocument", [])

for f, d, a, doc in zip(forms, dates, accs, docs):
    if "13F-HR" in f and "2021-05" in d: # filed in May for Q1 (March)
        print(f"File found: {d} {a}")
        folder = a.replace('-', '')
        
        index_url = f"https://www.sec.gov/Archives/edgar/data/1423053/{folder}/"
        r_idx = requests.get(index_url, headers=HEADERS)
        
        xml_file = re.findall(r'href="([^"]*infotable[^"]*\.xml)"', r_idx.text, re.IGNORECASE)
        if xml_file:
             xml_url = index_url + xml_file[0]
             r_xml = requests.get(xml_url, headers=HEADERS)
             content = r_xml.text.upper()
             
             blocks = re.split(r'<INFOTABLE>', content, flags=re.IGNORECASE)
             for b in blocks:
                 if "36467W" in b or "GAMESTOP" in b:
                     val_m = re.search(r'<VALUE>(\d+)</VALUE>', b)
                     sh_m = re.search(r'<SSHPRNAMT>(\d+)</SSHPRNAMT>', b)
                     pc_m = re.search(r'<PUTCALL>(.*?)</PUTCALL>', b)
                     
                     val = int(val_m.group(1))*1000 if val_m else 0
                     sh = int(sh_m.group(1)) if sh_m else 0
                     pc = pc_m.group(1).strip() if pc_m else "SH"
                     print(f"GME Position -> Type: {pc}, Shares: {sh}, Value: ${val:,.0f}")
