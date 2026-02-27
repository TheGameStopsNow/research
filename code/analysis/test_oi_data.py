import pandas as pd
from pathlib import Path

DATA_DIR = Path(str(Path.home()) + "/Documents/GitHub/research/code/analysis/data")
THETA_OI_DIR = Path(str(Path.home()) + "/Documents/GitHub/power-tracks-research/data/raw/thetadata/open_interest/GME")

price_df = pd.read_csv(DATA_DIR / "gme_daily_price.csv", parse_dates=['date'])
print(f"Price data: {price_df['date'].min().date()} to {price_df['date'].max().date()}")

oi_files = sorted(THETA_OI_DIR.glob("oi_*.parquet"))
print(f"Found {len(oi_files)} OI files.")
if len(oi_files) > 0:
    first_file = oi_files[0]
    last_file = oi_files[-1]
    print(f"First OI file: {first_file.name}")
    print(f"Last OI file: {last_file.name}")
    
    # Check the first file's contents
    df = pd.read_parquet(first_file)
    print(f"\nContents of first OI file:")
    print(f"  Rows: {len(df)}")
    print(f"  Min strike: {df['strike'].min()}")
    print(f"  Max strike: {df['strike'].max()}")
