#!/usr/bin/env python3
"""
Master FTD Loader — parses all SEC cnsfails*.zip files and extracts
daily FTD records for target tickers into per-ticker parquet files.
Also fetches GME daily price from Yahoo Finance for overlay analysis.
"""
import zipfile, io, os, glob
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Paths
FTD_DIR = Path(str(Path.home()) + "/Documents/GitHub/research/data/sec_ftd")
OUT_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Target tickers
TICKERS = {"GME", "XRT", "GMEU", "IGME", "GMEY", "IJH", "KOSS", "AMC", "IWM"}

def parse_ftd_zip(zip_path):
    """Parse a single SEC FTD zip file."""
    records = []
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            for name in z.namelist():
                with z.open(name) as f:
                    content = f.read()
                    # Try utf-8, fall back to latin-1
                    try:
                        text = content.decode('utf-8')
                    except UnicodeDecodeError:
                        text = content.decode('latin-1')
                    
                    lines = text.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        parts = line.strip().split('|')
                        if len(parts) >= 6:
                            symbol = parts[2].strip()
                            if symbol in TICKERS:
                                try:
                                    date = pd.Timestamp(datetime.strptime(parts[0].strip(), '%Y%m%d'))
                                    qty = int(parts[3].strip()) if parts[3].strip() else 0
                                    price = float(parts[5].strip()) if parts[5].strip() else 0.0
                                    records.append({
                                        'date': date,
                                        'symbol': symbol,
                                        'quantity': qty,
                                        'price': price,
                                        'cusip': parts[1].strip()
                                    })
                                except (ValueError, IndexError):
                                    continue
    except zipfile.BadZipFile:
        print(f"  ⚠️  Bad zip: {zip_path.name}")
    return records

def fetch_gme_price():
    """Fetch GME daily price history from Yahoo Finance."""
    try:
        import urllib.request
        import json
        
        # Use Yahoo Finance v8 API
        end = int(datetime.now().timestamp())
        start = int(datetime(2020, 12, 1).timestamp())
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/GME?period1={start}&period2={end}&interval=1d"
        
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        
        df = pd.DataFrame({
            'date': pd.to_datetime(timestamps, unit='s').normalize(),
            'gme_close': closes
        })
        df = df.dropna(subset=['gme_close'])
        return df
    except Exception as e:
        print(f"  ⚠️  Could not fetch GME price: {e}")
        # Fall back to FTD prices as proxy
        return None

def main():
    print("=" * 70)
    print("MASTER FTD LOADER — SEC cnsfails*.zip")
    print("=" * 70)
    
    # Find all zip files (avoid duplicates)
    zip_files = sorted(set(
        FTD_DIR / f for f in os.listdir(FTD_DIR)
        if f.endswith('.zip') and f.startswith('cnsfails')
        and '(' not in f  # Skip duplicate downloads with (1), (2) etc
    ))
    
    print(f"\n  Found {len(zip_files)} unique zip files")
    print(f"  Target tickers: {', '.join(sorted(TICKERS))}")
    print(f"  Date range: {zip_files[0].name[8:14]} – {zip_files[-1].name[8:14]}")
    
    # Parse all zips
    all_records = []
    for i, zf in enumerate(zip_files):
        records = parse_ftd_zip(zf)
        all_records.extend(records)
        if (i + 1) % 20 == 0:
            print(f"  Processed {i+1}/{len(zip_files)} files ({len(all_records):,} records so far)")
    
    print(f"\n  Total records extracted: {len(all_records):,}")
    
    if not all_records:
        print("  ❌ No records found!")
        return
    
    # Build master DataFrame
    df = pd.DataFrame(all_records)
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Summary per ticker
    print(f"\n  {'Ticker':<8} {'Records':>8} {'Date Range':>25} {'Total FTDs':>15} {'Peak FTDs':>15}")
    print("  " + "-" * 75)
    
    for ticker in sorted(df['symbol'].unique()):
        tdf = df[df['symbol'] == ticker]
        date_range = f"{tdf['date'].min().strftime('%Y-%m-%d')} – {tdf['date'].max().strftime('%Y-%m-%d')}"
        total = tdf['quantity'].sum()
        peak = tdf['quantity'].max()
        peak_date = tdf.loc[tdf['quantity'].idxmax(), 'date'].strftime('%Y-%m-%d')
        print(f"  {ticker:<8} {len(tdf):>8,} {date_range:>25} {total:>15,} {peak:>12,} ({peak_date})")
        
        # Save per-ticker parquet
        out_path = OUT_DIR / f"{ticker}_ftd.csv"
        tdf.to_csv(out_path, index=False)
    
    # Save combined
    combined_path = OUT_DIR / "all_ftd_combined.csv"
    df.to_csv(combined_path, index=False)
    print(f"\n  Saved combined data: {combined_path}")
    
    # Fetch GME price
    print(f"\n  Fetching GME daily price from Yahoo Finance...")
    gme_price = fetch_gme_price()
    if gme_price is not None:
        price_path = OUT_DIR / "gme_daily_price.csv"
        gme_price.to_csv(price_path, index=False)
        print(f"  Saved GME price: {price_path} ({len(gme_price)} trading days)")
    else:
        # Build price from FTD data as fallback
        gme_ftd = df[df['symbol'] == 'GME'][['date', 'price']].copy()
        gme_ftd = gme_ftd.groupby('date')['price'].last().reset_index()
        gme_ftd.columns = ['date', 'gme_close']
        price_path = OUT_DIR / "gme_daily_price.csv"
        gme_ftd.to_csv(price_path, index=False)
        print(f"  Saved GME price (FTD proxy): {price_path} ({len(gme_ftd)} days)")
    
    print(f"\n✅ Data loading complete. Output in {OUT_DIR}")

if __name__ == "__main__":
    main()
