import requests

cik = "0001423053"
HEADERS = {"User-Agent": "research contact@example.com"}
url = f"https://data.sec.gov/submissions/CIK{cik}.json"
r = requests.get(url, headers=HEADERS)
data = r.json()
recent = data.get("filings", {}).get("recent", {})
forms = recent.get("form", [])
dates = recent.get("filingDate", [])
accs = recent.get("accessionNumber", [])

ctrs = []
for f, d, a in zip(forms, dates, accs):
    if "13F-CTR" in f:
        ctrs.append((f, d, a))

print("Citadel 13F-CTRs:", ctrs)
