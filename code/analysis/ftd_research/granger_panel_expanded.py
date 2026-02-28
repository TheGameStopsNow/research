"""
Expanded Granger Causality Panel Test (v4)
==========================================
Tests every equity in SEC FTD bulk data against Treasury settlement fails.
"""
import numpy as np, pandas as pd, json, warnings, zipfile, io
from pathlib import Path
from scipy import stats

warnings.filterwarnings('ignore')
ROOT = Path("/Users/markteater/Documents/GitHub/research")
OUT = ROOT / "results" / "ftd_research" / "granger_panel_expanded.json"

def granger(x, y, max_lag=6):
    dx, dy = np.diff(x), np.diff(y)
    if len(dx) < 20: return None, None, None
    best_f, best_p, best_lag = 0, 1, 0
    for lag in range(1, max_lag+1):
        n = len(dy)
        if n <= lag+2: continue
        Y = dy[lag:]
        n_obs = len(Y)
        Yl = np.column_stack([dy[lag-j-1:n-j-1] for j in range(lag)])
        Xl = np.column_stack([dx[lag-j-1:n-j-1] for j in range(lag)])
        Xr = np.column_stack([np.ones(n_obs), Yl])
        br = np.linalg.lstsq(Xr, Y, rcond=None)[0]
        ssr_r = np.sum((Y - Xr@br)**2)
        Xu = np.column_stack([np.ones(n_obs), Yl, Xl])
        bu = np.linalg.lstsq(Xu, Y, rcond=None)[0]
        ssr_u = np.sum((Y - Xu@bu)**2)
        df_u = n_obs - Xu.shape[1]
        if df_u <= 0 or ssr_u <= 0: continue
        f = ((ssr_r - ssr_u)/lag) / (ssr_u/df_u)
        p = 1 - stats.f.cdf(f, lag, df_u)
        if f > best_f: best_f, best_p, best_lag = f, p, lag
    return best_lag, best_f, best_p

print("="*60)
print("EXPANDED GRANGER CAUSALITY PANEL")
print("Equity FTDs -> Treasury Settlement Fails")
print("="*60)

# 1. Treasury
print("\n1. Treasury data...")
tdf = pd.read_csv(ROOT/"data"/"treasury"/"nyfrb_pdftd.csv")
tdf['date'] = pd.to_datetime(tdf['As Of Date'])
tdf['val'] = pd.to_numeric(tdf['Value (millions)'])
treas = tdf[['date','val']].dropna().sort_values('date').reset_index(drop=True)
print(f"   {len(treas)} weeks: {treas.date.min().date()} to {treas.date.max().date()}")

# 2. SEC FTDs
print("\n2. Loading SEC FTD bulk data...")
dfs = []
seen = set()
for d in [ROOT/"data"/"sec_ftd", ROOT/"data"/"_consolidated"/"ftd"/"raw_sec_zips"]:
    if not d.exists(): continue
    for zf in sorted(d.glob("cnsfails*.zip")):
        if zf.name in seen: continue
        seen.add(zf.name)
        try:
            with zipfile.ZipFile(zf) as z:
                for nm in z.namelist():
                    if nm.endswith(('.txt','.csv')):
                        dfs.append(pd.read_csv(io.BytesIO(z.read(nm)), sep='|', dtype=str, on_bad_lines='skip'))
        except: pass

raw = pd.concat(dfs, ignore_index=True)
raw.columns = [c.strip().upper() for c in raw.columns]
dc = [c for c in raw.columns if 'DATE' in c][0]
sc = [c for c in raw.columns if 'SYMBOL' in c][0]
qc = [c for c in raw.columns if 'QUANTITY' in c or 'QTY' in c][0]
raw['date'] = pd.to_datetime(raw[dc], format='%Y%m%d', errors='coerce')
raw['sym'] = raw[sc].str.strip()
raw['ftd'] = pd.to_numeric(raw[qc], errors='coerce')
raw = raw[['date','sym','ftd']].dropna()
print(f"   {len(raw):,} records | {raw['sym'].nunique():,} symbols")
print(f"   Date range: {raw.date.min().date()} to {raw.date.max().date()}")

# 3. Assign each daily FTD to nearest Treasury Wednesday via merge_asof
print("\n3. Aligning to Treasury weeks...")
raw['date'] = pd.to_datetime(raw['date'])
# Workaround for pandas sort bug: use numpy argsort
sort_idx = raw['date'].values.astype('int64').argsort()
raw = raw.iloc[sort_idx].reset_index(drop=True)
raw = pd.merge_asof(raw, treas.rename(columns={'val':'treas_val'}),
                     on='date', direction='forward', tolerance=pd.Timedelta('7D'))
raw = raw.dropna(subset=['treas_val'])
print(f"   {len(raw):,} records aligned")

# Weekly aggregate per symbol
weekly = raw.groupby(['date', 'sym']).agg(
    ftd=('ftd', 'mean'),
    treas=('treas_val', 'first')
).reset_index()

# Actually group by the Treasury week date
weekly_by_sym = weekly.groupby('sym')

sym_counts = weekly.groupby('sym')['date'].nunique()
MIN_WEEKS = 30
eligible = sym_counts[sym_counts >= MIN_WEEKS].index.tolist()
print(f"   {len(eligible):,} symbols with {MIN_WEEKS}+ weekly observations")

# 4. Granger tests
print(f"\n4. Testing {len(eligible):,} tickers...", flush=True)
results = {}
tested = 0
for i, sym in enumerate(eligible):
    if i % 500 == 0 and i > 0:
        print(f"   ...{i}/{len(eligible)} ({tested} tested so far)", flush=True)
    
    sd = weekly[weekly['sym']==sym].sort_values('date')
    # Deduplicate weekly (take mean per Treasury date)
    sd = sd.groupby('date').agg(ftd=('ftd','mean'), treas=('treas','first')).reset_index()
    
    if len(sd) < MIN_WEEKS: continue
    
    lag, f, p = granger(sd['ftd'].values, sd['treas'].values, max_lag=6)
    if lag is not None:
        tested += 1
        results[sym] = {'lag':int(lag), 'F':round(float(f),4), 'p':float(p),
                        'significant': p<0.05, 'n_weeks':len(sd)}

print(f"   Done. {tested} tickers tested.\n")

# Results
sr = sorted(results.items(), key=lambda x: x[1]['F'], reverse=True)
sig = sum(1 for r in results.values() if r['significant'])
bonf = 0.05/tested if tested else 0.05
bonf_sig = sum(1 for r in results.values() if r['p'] < bonf)

print("="*70)
print(f"TOP 30 BY F-STATISTIC (of {tested} tested)")
print("="*70)
print(f"{'#':<4} {'Ticker':<10} {'Lag':<5} {'F':<10} {'p-value':<16} {'Weeks':<7} {'Sig'}")
print("-"*70)
for i,(s,r) in enumerate(sr[:30],1):
    ss = "***" if r['p']<0.001 else "**" if r['p']<0.01 else "*" if r['p']<0.05 else ""
    print(f"{i:<4} {s:<10} {r['lag']:<5} {r['F']:<10.2f} {r['p']:<16.10f} {r['n_weeks']:<7} {ss}")

sig_list = [(s,r) for s,r in sr if r['significant']]
print(f"\n{'='*70}")
print(f"ALL SIGNIFICANT (p<0.05): {len(sig_list)} of {tested}")
print(f"{'='*70}")
for i,(s,r) in enumerate(sig_list,1):
    print(f"  {i:<3} {s:<10} lag={r['lag']} F={r['F']:.2f} p={r['p']:.8f} ({r['n_weeks']}wk)")

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
print(f"Total tested:              {tested}")
if tested:
    print(f"Significant (p<0.05):      {sig} ({100*sig/tested:.1f}%)")
    print(f"Expected by chance (5%):   {tested*0.05:.0f}")
    print(f"Bonferroni threshold:      {bonf:.10f}")
    print(f"Bonferroni significant:    {bonf_sig}")

gme_rank = next((i for i,(s,_) in enumerate(sr,1) if s=='GME'), None)
if gme_rank:
    g = results['GME']
    print(f"\n>>> GME: RANK #{gme_rank} of {tested} (F={g['F']:.2f}, p={g['p']:.10f}, lag={g['lag']})")
else:
    print("\n>>> GME not found in panel")

out = {'meta':{'tested':tested, 'sig05':sig, 'expected_fp':round(tested*0.05) if tested else 0,
               'bonferroni':bonf, 'bonf_sig':bonf_sig, 'gme_rank':gme_rank},
       'significant':{s:r for s,r in sig_list},
       'top30':{s:r for s,r in sr[:30]},
       'full':dict(sr)}
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT,'w') as f: json.dump(out, f, indent=2)
print(f"\nSaved to {OUT}")
