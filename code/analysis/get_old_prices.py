import pandas as pd
import requests
from pathlib import Path

# Need prices from at least Jan 1, 2020 to Dec 1, 2020. Might as well get 2019 too.
key = None
with open(str(Path.home()) + "/Documents/GitHub/power-tracks-research/.env") as f:
    for line in f:
        if line.startswith("POLYGON_API_KEY="):
            key = line.strip().split("=")[1]
            break

url = f"https://api.polygon.io/v2/aggs/ticker/GME/range/1/day/2019-01-01/2020-12-01?adjusted=true&sort=asc&limit=50000&apiKey={key}"
res = requests.get(url).json()

new_prices = []
for r in res.get('results', []):
    date = pd.to_datetime(r['t'], unit='ms').strftime('%Y-%m-%d')
    new_prices.append({'date': date, 'gme_close': r['c']})
    
new_df = pd.DataFrame(new_prices)

DATA_DIR = Path(str(Path.home()) + "/Documents/GitHub/research/code/analysis/data")
old_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv")

combined = pd.concat([new_df, old_df]).drop_duplicates(subset=['date']).sort_values('date')
combined.to_csv(DATA_DIR / "gme_daily_price.csv", index=False)
print(f"Updated price data: {combined['date'].min()} to {combined['date'].max()} ({len(combined)} rows)")
