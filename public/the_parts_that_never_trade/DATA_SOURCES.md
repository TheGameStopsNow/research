# Data sources — what was used, where it lives, and exactly how to pull it

Everything in the article derives from the sources below. Paths are relative to the repo root unless noted; the sibling data repository (`power-tracks-research`, holding the raw vendor stores) is assumed to sit next to this one on disk.

---

## 1. ThetaData — the options tape (primary source)

Served locally by **ThetaTerminal** (Java app) at `http://localhost:25503/v3`. Tier used: **PROFESSIONAL**. History floor: **2012-06-01** (OPRA coverage start; nothing exists before that at any tier).

What it provides, per contract by strike and expiration:

| Endpoint (v3) | Contents | Notes |
|---|---|---|
| `/v3/option/history/open_interest` | Daily OI, 6 columns | This is the **06:30 ET snapshot** — the endpoint returns that snapshot; there is nothing to compute |
| `/v3/option/history/greeks/eod` | 43-column EOD greeks (1st–3rd order + trade greeks) | `expiration="*"`, one day per call |
| tick trades / quotes | Per-contract prints and NBBO quotes at tick resolution | The millisecond-married pairs in Q1 come from these |

**Concurrency law:** safe sustained pool = **12**. Burst ceiling is 24, but sustained heavy pulls above ~20 cause 429 storms **and silent data truncation** (an expiration returning OI≈4000 with greeks=0 while being marked "ok"). Cap at 12 and fail closed: only `ok` or `nodata` count as done; anything incomplete means abort and re-pull.

**What it does NOT have at any tier:** counterparty, participant type, or open/close flags. Do not go looking.

**A note on redistribution:** this repository ships none of ThetaData's data, raw or reformatted. Everything here is pointers and pull scripts; you pull your own copy under your own subscription.

### Open interest has a public, authoritative source

Open interest originates at the OCC (the clearinghouse), not at any vendor — the vendor feed carries OCC's morning snapshot. OCC publishes it directly: per-series current open interest via [Series Search](https://www.theocc.com/Market-Data/Market-Data-Reports/Series-and-Trading-Data/Series-Search), and a dated daily open-interest CSV via the batch endpoint `https://marketdata.theocc.com/daily-open-interest?reportDate=mm/dd/yyyy&action=download&format=csv` (see OCC's [Daily Open Interest batch page](https://www.theocc.com/market-data/market-data-reports/other-market-data-info/batch-processing/daily-open-interest)). If you want OI without any vendor relationship, or want to spot-check any OI number in the article against the authoritative source, start there; `tools/get_data.py occ` archives the daily report into `data/occ/daily_oi/`, and running it nightly costs nothing.

### The local stores the scripts expect

One physical store, sometimes two paths (symlinks are resolved and deduped at load):

| Store | Physical location | Symlink |
|---|---|---|
| OI ledger (daily parquets, 2012→present; 3,456 files at the June 2026 census) | `power-tracks-research/data/raw/thetadata/gme_options_oi/` | `data/_consolidated/options/oi_history/GME/` |
| EOD greeks | `power-tracks-research/data/raw/thetadata/gme_options_greeks_eod/` | `data/_consolidated/options/greeks_eod/GME` |
| EOD volume/quotes | `power-tracks-research/data/raw/thetadata/gme_options_eod/` | — |
| Trades hive | `power-tracks-research/data/raw/thetadata/trades/root=<TICKER>/date=<YYYYMMDD>/part-*.parquet` | — |
| Intraday NBBO samples | `power-tracks-research/data/raw/thetadata/quotes/` | — |

### The standing pull script

`tools/topup_recent.py` (in this package) is the incremental top-up for the three GME stores (greeks EOD, OI, trades). ThetaData v3 only, single-threaded, 70s timeout, fail-closed: a failed day goes to the store's `_FAILS.txt` and is retried next run; every write is sha256-manifested in the store's `_MANIFEST.jsonl`; nothing is ever fabricated.

```bash
.venv/bin/python public/the_parts_that_never_trade/tools/topup_recent.py                 # all three stores
.venv/bin/python public/the_parts_that_never_trade/tools/topup_recent.py --store oi      # one store
.venv/bin/python public/the_parts_that_never_trade/tools/topup_recent.py --dry-run      # show what would be pulled
```

Re-running is idempotent: days already on disk are skipped. To rebuild from scratch, run it with an empty store and a long `--budget`.

### The canonical reader (do not roll your own)

`tools/hive_reader.py` (in this package) is the required loader for the trades hive. It exists because of a real landmine: the hive's expiration column is named `expiry` in some files and `expiration` in others, **mixed at file level**. A loader that requests only one name silently skips days — an early census missed 507 of 2,038 GME days (24.9%) this way. `hive_reader.scan_hive()` merges both names and **asserts day-count coverage, failing closed** rather than skipping. Reuse it.

**A second, related landmine — the `right` values.** Most files encode the option right as `CALL`/`PUT`, but at least one (2024-06-07) mixes `CALL`/`PUT` with `C`/`P` **inside the same file**. Any detector written as `df.right == "CALL"` silently drops the `C`/`P`-encoded prints, no error raised. Normalize on the first character (`right.astype(str).str.upper().str[0]`) before filtering. This one cost the married-pair census most of its 2024 prints, including a genuine 10,000-lot married clip, until the rebuild caught it.

---

## 2. Alpaca — equity bars

SIP feed; daily and minute bars for the underlying. Used for spot, returns, and intraday alignment (including the convert pricing-day drops in Q5). Any SIP-derived OHLC source reproduces these numbers.

### A third landmine, and the one most likely to catch you: split-adjusted bars vs as-listed strikes

These bars are **split-adjusted**. The trades hive records strikes **as they were listed**. The two are in different units for any event dated before a split, and nothing in either dataset tells you so.

It matters most for put-call parity, because the borrow rate comes out of `ln(F/S)` and a units mismatch there does not produce a wrong-looking rate — it produces a catastrophic one, silently. Running the implied-borrow method across GME's 2022-07-22 four-for-one without adjusting returns a median implied borrow of **−810%/yr**, and the code raises nothing. Correct the strikes and the same events return **+3.3%/yr**.

Two defences, both cheap:

1. **Adjust explicitly.** Multiply as-listed strikes (and the call-minus-put residual, which scales the same way) by the product of `1/ratio` for every split effective *after* the event date. The splits inside this project's panel windows: GME 4-for-1 on 2022-07-22; AMC 1-for-10 reverse on 2023-08-24; NVDA 4-for-1 on 2021-07-20 and 10-for-1 on 2024-06-10; TSLA 5-for-1 on 2020-08-31 and 3-for-1 on 2022-08-25; AAPL 4-for-1 on 2020-08-31. SPY, PLTR, HOOD, BYND, CHWY and U have none in window.
2. **Gate on the units.** Compute median `|ln(K/S)|` per ticker-era and refuse any group above ~1.0. Married pairs print near the money, so this statistic is small whenever the units agree and enormous when they don't. `posts/claim_tests/borrow_easy_control_2026-07-26/code/run_control.py` implements both.

A related trap in the same family: **GameStop paid a dividend until 2019.** Parity returns `borrow + dividend yield`, so pre-2019 events are biased upward by the yield and are not comparable to later ones without adjustment. The same applies to any dividend-paying control name — SPY (~1.3%) and AAPL (~0.5%) need it; NVDA, TSLA and the meme names effectively do not.

## 3. SBSR public swap tape (the "public swap tape" in Q8)

**SEC Regulation SBSR public dissemination**, live since **2022-02-14**: transaction-level single-name equity swaps and total-return swaps. Access is free and machine-readable — one zip per day at

```
https://kgc0418-tdw-data-0.s3.amazonaws.com/sec/eod/SEC_CUMULATIVE_EQUITIES_{YYYY_MM_DD}.zip
```

`tools/get_data.py sbsr` downloads the full available window into `data/sbsr/_zips/`.

Caveats to declare in any use: notional is **capped at $250M** (large clips stack at the cap); GME runs ~22 rows/day; free retention is a **rolling ~1 year** — days fall off the head daily, so build a durable local archive and top it up continuously. Counterparty identities are never disclosed.

## 4. SEC fails-to-deliver archive

The SEC's public half-month FTD files, one zip per half-month back to 2004 at

```
https://www.sec.gov/files/data/fails-deliver-data/cnsfails{YYYYMM}{a|b}.zip
```

`tools/get_data.py ftd --tickers GME,AMC,BYND,COIN` downloads every missing zip into `data/ftd/_zips/` and rebuilds per-ticker extracts at `data/ftd/<TICKER>_ftd.csv` (date, symbol, quantity, price, description). A full backfill is how the **2017–2020 hole** in the local archive was filled — the fill that made BYND testable in Q2. The FTD inputs of earlier series are documented in the root `REPLICATION_GUIDE.md`.

## 5. Corporate events (Q5/Q6 anchors)

All from primary sources, verified July 2026:

- Convert 1: priced **2025-03-27**, $1.3B 0.00% notes due 2030, conversion rate 33.4970/$1,000 (≈$29.85), closed 2025-04-01; $200M greenshoe exercised → $1.5B total.
- Convert 2: priced **2025-06-12**, $2.25B 0.00% notes due 2032, rate 34.5872/$1,000 (≈$28.91), closed 2025-06-17; $450M greenshoe exercised → $2.7B total.
- Warrants: announced **2025-09-09**; record 2025-10-03; distributed **2025-10-07**; strike $32.00; expiry **2026-10-30** 5:00 p.m. ET; 1 per 10 shares; noteholders received warrants as-converted (3.34970 / 3.45872 per $1,000).

Sources: GameStop investor-relations press releases and the associated 8-K exhibits on EDGAR (CIK 1326380).

## 6. Excluded sources

- `polygon_second_synthetic` — interpolated cache, unreliable, **excluded everywhere**.
- Polygon as a live source — paused (lacked the options coverage that made ThetaData necessary).

## 7. OCC FLEX reports — the bespoke chain (Q3)

FLEX options are exchange-traded and OCC-cleared, but their terms are negotiated rather than listed, so each contract gets its own series and **those series are never disseminated to OPRA**. They are therefore absent from every per-contract vendor feed in this project, including ThetaData's — this is not a coverage gap in §1, it is what FLEX is. OCC publishes them separately, daily and free, as fixed-width text:

```
https://marketdata.theocc.com/flex-reports?reportType={OI|PR}&optionType={E|I}&reportDate=YYYYMMDD
```

`reportType` is `OI` (open interest) or `PR` (prices); `optionType` is `E` (equity) or `I` (index). Q3 rests on equity OI. `tools/get_data.py flex` pulls all four combinations into `data/occ/flex_reports/{OI,PR}/{E,I}/YYYYMMDD.txt`.

### Record layout

Fixed-width, one contract per line:

```
[style][root]  [C|P]  [MM DD YYYY]  [strike 5 digits][strike 3 decimals]  [price]  [open interest]
      1GME     C   01 20 2028  00032 000      2.5127    100000
      2GME     C   08 21 2026  00022 010      0.5321       995
```

`style` is **1 = American, 2 = European** — the single byte that carries the whole exercise-style argument in Q3. Strike is the two numeric fields joined on a decimal point (`00022` + `010` → 22.010), which is how the one-cent offsets are represented.

### Retention, and why you should archive daily

**OCC keeps roughly the trailing 24 months.** Probed by binary search on 2026-07-28: 2024-07-25 absent, **2024-07-29 present**, and everything after it present. That floor advances every day.

A warning about how to measure it, because the first attempt here got it wrong. An absent date is not evidence of the retention boundary unless you first confirm the market was open. The earlier figure in this file was 22 months, inferred from 2024-09-02 coming back empty; 2024-09-02 is **Labor Day**, so that report never existed. Check the trading calendar before concluding anything from a missing day.

Anything older than the floor exists only in a local archive, so if you want history you have to have been collecting it already. Running the fetcher nightly costs nothing and is the only way to build a durable record.

### Three landmines, in the order they will bite you

1. **The endpoint answers HTTP 200 for its own errors.** Out-of-retention dates return `File requested does not exist.` and a malformed `reportDate` returns `Report Date is invalid.` — both with status 200, both as the response body. A fetcher that checks only the status code writes that sentence to disk as a report; every downstream reader then finds zero rows for the ticker, which is indistinguishable from a genuine absence. This manufactured a false "GME had no FLEX in 2018" result once, and had already filled a store with **9,428 placeholder files** before it was caught. `run_flex()` in `tools/get_data.py` detects both sentinels, records unretained days to `_UNRETAINED.txt`, and aborts loudly on a bad date rather than continuing.
2. **`reportDate` must be `YYYYMMDD`.** ISO (`2026-07-23`) and `mm/dd/yyyy` both return 200 + `Report Date is invalid.`, i.e. landmine 1 fires for every day of a run. This is the easiest way to silently archive nothing.
3. **Match the root exactly, after stripping the style byte.** A substring test for `GME` admits **GMED** (Globus Medical, an unrelated company), and separately **GME1** — which is *not* another company but these same GameStop lines re-rooted by the October 2025 warrant adjustment (GME through 2025-10-02, GME1 from 2025-10-03, clean same-day break, no overlap). GMED must always be dropped. GME1 must be **kept** for capacity totals, because it is real GameStop exposure, and **dropped** for any test that compares strike to spot, because an adjusted contract's deliverable is not 100 plain shares and its strike is therefore not commensurable — the same class of error as the split-adjustment trap in §2. Keeping GME1 in the pair census double-counts four lines and inflates it from 24 to 28.

### A note on where this lands

`get_data.py` writes to `data/occ/flex_reports/` inside this repo, which is the right default for a replicator starting from nothing. If you already maintain a FLEX archive elsewhere, point your reader at that instead and treat this path as a bootstrap rather than a second copy — two stores of the same reports drifting apart is its own failure mode.

## 8. One environment note

ThetaTerminal serves only on the machine it runs on. Run pulls on the same machine as the terminal; anything remote must work from the materialized parquet stores instead. A localhost connection failure from elsewhere is not an outage.
