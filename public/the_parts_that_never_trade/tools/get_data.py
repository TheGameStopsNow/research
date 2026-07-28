#!/usr/bin/env python3
"""get_data.py — one-command bootstrap for every data source the article uses.

Downloads the free public stores directly (SEC fails-to-deliver, DTCC SBSR
public swap tape, OCC daily open interest) and delegates the licensed options
stores to tools/topup_recent.py against YOUR OWN running ThetaTerminal.
Nothing here requires credentials except the ThetaData step, which requires
your own subscription; the rest is public data from the primary sources.

Usage (from the repo root, with the repo venv):
    .venv/bin/python public/the_parts_that_never_trade/tools/get_data.py --all
    .venv/bin/python public/the_parts_that_never_trade/tools/get_data.py ftd  --tickers GME,AMC,BYND,COIN
    .venv/bin/python public/the_parts_that_never_trade/tools/get_data.py sbsr --start 2025-07-26
    .venv/bin/python public/the_parts_that_never_trade/tools/get_data.py occ  --start 2026-01-02
    .venv/bin/python public/the_parts_that_never_trade/tools/get_data.py thetadata

`--all` (or the bare store name `all`) pulls everything the article's tests
draw on, with sensible defaults per store: the full SEC FTD archive
(2004 -> present) extracted for the whole cross-name panel, the DTCC swap
tape's full free retention window, the past year of OCC daily open interest,
and a ThetaData top-up if a ThetaTerminal is running locally.

Re-running is idempotent: files already on disk are skipped. Failures are
logged to the store's _FAILS.txt and retried on the next run; nothing is ever
fabricated or interpolated. Stores land where the analysis expects them:

    data/ftd/_zips/            SEC half-month zips (2004 -> present)
    data/ftd/<TICKER>_ftd.csv  per-ticker extracts (date,symbol,quantity,price,description)
    data/sbsr/_zips/           DTCC SBSR daily cumulative equities zips
    data/occ/daily_oi/         OCC daily open interest CSVs (one per day)
    data/occ/flex_reports/{OI,PR}/{E,I}/YYYYMMDD.txt
                               OCC FLEX volume & open-interest reports (Q3)

Endpoints (primary sources):
    SEC  https://www.sec.gov/files/data/fails-deliver-data/cnsfails{YYYYMM}{a|b}.zip
    DTCC https://kgc0418-tdw-data-0.s3.amazonaws.com/sec/eod/SEC_CUMULATIVE_EQUITIES_{YYYY_MM_DD}.zip
    OCC  https://marketdata.theocc.com/daily-open-interest?reportDate={mm/dd/yyyy}&action=download&format=csv
    FLEX https://marketdata.theocc.com/flex-reports?reportType={OI|PR}&optionType={E|I}&reportDate={YYYY-MM-DD}

Notes the fetchers already know: SEC requires a descriptive User-Agent; the
DTCC free tape retains only ~1 year (missing older days 404 — expected, not an
error); the OCC endpoint may return a zip or a bare CSV depending on the day;
and the FLEX endpoint returns **HTTP 200 with an error sentence in the body**
for any date outside its ~22-month retention, which run_flex() detects and
records as unretained rather than writing a fake empty report.
"""
from __future__ import annotations

import csv
import io
import sys
import time
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[3]
FTD_DIR = REPO / "data/ftd"
SBSR_DIR = REPO / "data/sbsr/_zips"
OCC_DIR = REPO / "data/occ/daily_oi"
FLEX_DIR = REPO / "data/occ/flex_reports"

UA = {"User-Agent": "research-replication get_data.py (open source; contact via github.com/TheGameStopsNow/research)"}
PAUSE_SEC = 1.1   # SEC asks automated clients to stay well under 10 req/s; be polite
FORCE_EXTRACT = False   # set by --force-extract
SEC_FTD_URL = "https://www.sec.gov/files/data/fails-deliver-data/cnsfails{ym}{half}.zip"
DTCC_URL = "https://kgc0418-tdw-data-0.s3.amazonaws.com/sec/eod/SEC_CUMULATIVE_EQUITIES_{d}.zip"
OCC_URL = "https://marketdata.theocc.com/daily-open-interest?reportDate={d}&action=download&format=csv"

FLEX_URL = "https://marketdata.theocc.com/flex-reports"
# The FLEX endpoint answers HTTP 200 for BOTH of its error conditions, with the
# error as the response body. Neither may ever be written to disk as a report.
#   - out of retention  -> "File requested does not exist."
#   - malformed date    -> "Report Date is invalid."
# The second is easy to hit by accident: reportDate must be YYYYMMDD. An ISO
# date (2026-07-23) or mm/dd/yyyy both return 200 + "Report Date is invalid.",
# so a fetcher that only checks the status code silently archives that sentence
# for every single day and the whole store reads as "this name had no FLEX".
FLEX_NOT_RETAINED = b"File requested does not exist."
FLEX_BAD_DATE = b"Report Date is invalid."

SBSR_FLOOR = date(2022, 2, 14)   # SBSR public dissemination go-live
FTD_FLOOR = date(2004, 1, 1)     # SEC archive start
PAUSE = 0.6                      # polite inter-request sleep, seconds

# The article's cross-name panel (Q2 flyway + controls). Override with --tickers.
DEFAULT_TICKERS = "GME,AMC,COIN,BYND,CHWY,HOOD,PLTR,TSLA,NVDA,AAPL,AMD,CVNA,SPY,U"


def log_fail(store_dir: Path, key: str, err: str) -> None:
    store_dir.mkdir(parents=True, exist_ok=True)
    with open(store_dir / "_FAILS.txt", "a") as f:
        f.write(f"{key}\t{err}\n")


def fetch(url: str, timeout: int = 60, retries_429: int = 2) -> requests.Response | None:
    """GET with 429 backoff. Returns the response on 200, None otherwise.
    SEC throttles bursts; on 429 this sleeps 65s and retries before giving up."""
    for attempt in range(retries_429 + 1):
        r = requests.get(url, headers=UA, timeout=timeout)
        if r.status_code == 200 and r.content:
            return r
        if r.status_code == 429 and attempt < retries_429:
            print(f"[rate-limit] 429 from server; backing off 65s "
                  f"(attempt {attempt + 1}/{retries_429})", flush=True)
            time.sleep(65)
            continue
        return None
    return None


# ---------------------------------------------------------------- SEC FTD --
def run_ftd(start: date, end: date, tickers: list[str]) -> None:
    zips = FTD_DIR / "_zips"
    zips.mkdir(parents=True, exist_ok=True)
    got, skipped, missing = 0, 0, 0
    d = date(start.year, start.month, 1)
    while d <= end:
        ym = f"{d.year}{d.month:02d}"
        for half in ("a", "b"):
            out = zips / f"cnsfails{ym}{half}.zip"
            if out.exists():
                skipped += 1
                continue
            try:
                r = fetch(SEC_FTD_URL.format(ym=ym, half=half))
            except Exception as e:  # noqa: BLE001 - log and continue
                log_fail(zips, f"cnsfails{ym}{half}", repr(e))
                continue
            if r is None:
                missing += 1   # not published yet, a gap, or still rate-limited
                continue
            out.write_bytes(r.content)
            got += 1
            time.sleep(PAUSE_SEC)
        d = (d.replace(day=28) + timedelta(days=5)).replace(day=1)
    print(f"[ftd] zips: {got} downloaded, {skipped} already on disk, {missing} not published")
    if not tickers:
        return
    # Guard: rebuilding extracts from a partial zip set would silently REPLACE a
    # complete history with a truncated one. Only rebuild when the archive on
    # disk plausibly covers the requested span.
    have = len(list((FTD_DIR / "_zips").glob("cnsfails*.zip")))
    want = max(1, ((end.year - start.year) * 12 + (end.month - start.month) + 1) * 2)
    if have < 0.9 * want and not FORCE_EXTRACT:
        print(f"[ftd] SKIPPING extract rebuild: only {have} zips on disk but the "
              f"requested span needs ~{want}. Existing <TICKER>_ftd.csv files are "
              f"left untouched so a partial archive cannot truncate a good one.\n"
              f"      Re-run once the downloads succeed, or pass --force-extract "
              f"to rebuild from what is on disk anyway.")
        return
    extract_ftd(tickers)


def extract_ftd(tickers: list[str]) -> None:
    """Rebuild per-ticker CSVs from every zip on disk (full rescan, idempotent).

    NOTE: extracts are rebuilt from whatever zips are in data/ftd/_zips/ and
    OVERWRITE any existing <TICKER>_ftd.csv. Run a full backfill (no --start)
    before trusting the extracts as complete histories.
    """
    zcount = len(list((FTD_DIR / "_zips").glob("cnsfails*.zip")))
    print(f"[ftd] rebuilding extracts from {zcount} zips on disk "
          f"(if that isn't the full archive, run a full backfill first)")
    rows: dict[str, list[list[str]]] = {t: [] for t in tickers}
    for zpath in sorted((FTD_DIR / "_zips").glob("cnsfails*.zip")):
        try:
            with zipfile.ZipFile(zpath) as z:
                name = z.namelist()[0]
                text = z.read(name).decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            log_fail(FTD_DIR, zpath.name, f"unreadable zip: {e!r}")
            continue
        for line in text.splitlines()[1:]:
            parts = line.split("|")
            if len(parts) < 6:
                continue
            settle, _cusip, symbol, qty, desc, price = parts[:6]
            if symbol in rows:
                iso = f"{settle[:4]}-{settle[4:6]}-{settle[6:8]}" if len(settle) == 8 else settle
                rows[symbol].append([iso, symbol, qty, price.strip() or "", desc])
    for t, rs in rows.items():
        out = FTD_DIR / f"{t}_ftd.csv"
        # Never shrink an existing extract in place: a smaller result means the
        # zip set is thinner than whatever built the current file.
        if out.exists():
            existing = sum(1 for _ in open(out)) - 1
            if len(rs) < existing:
                alt = out.with_name(f"{t}_ftd.partial.csv")
                print(f"[ftd] {out.name}: KEEPING existing {existing} rows; new "
                      f"rebuild only had {len(rs)}. Wrote {alt.name} instead.")
                out = alt
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "symbol", "quantity", "price", "description"])
            w.writerows(sorted(rs))
        print(f"[ftd] {out.name}: {len(rs)} rows")


# ------------------------------------------------------------- DTCC SBSR --
def run_sbsr(start: date, end: date) -> None:
    SBSR_DIR.mkdir(parents=True, exist_ok=True)
    got, skipped, gone = 0, 0, 0
    d = max(start, SBSR_FLOOR)
    while d <= end:
        tag = d.strftime("%Y_%m_%d")
        out = SBSR_DIR / f"SEC_CUMULATIVE_EQUITIES_{tag}.zip"
        if out.exists():
            skipped += 1
        else:
            try:
                r = fetch(DTCC_URL.format(d=tag))
            except Exception as e:  # noqa: BLE001
                log_fail(SBSR_DIR, tag, repr(e))
                r = None
            if r is None:
                gone += 1  # rolled off the free retention window, or weekend/holiday
            else:
                out.write_bytes(r.content)
                got += 1
                time.sleep(PAUSE)
        d += timedelta(days=1)
    print(f"[sbsr] {got} downloaded, {skipped} on disk, {gone} unavailable "
          f"(free retention is ~1 year; older days rolling off is expected)")


# -------------------------------------------------------------- OCC OI ----
def run_occ(start: date, end: date) -> None:
    OCC_DIR.mkdir(parents=True, exist_ok=True)
    got, skipped, gone = 0, 0, 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            out = OCC_DIR / f"{d.isoformat()}.csv"
            if out.exists():
                skipped += 1
            else:
                try:
                    r = fetch(OCC_URL.format(d=d.strftime("%m/%d/%Y")))
                except Exception as e:  # noqa: BLE001
                    log_fail(OCC_DIR, d.isoformat(), repr(e))
                    r = None
                if r is None:
                    gone += 1
                else:
                    body = r.content
                    if body[:2] == b"PK":  # some days arrive zip-wrapped
                        with zipfile.ZipFile(io.BytesIO(body)) as z:
                            body = z.read(z.namelist()[0])
                    out.write_bytes(body)
                    got += 1
                    time.sleep(PAUSE)
        d += timedelta(days=1)
    print(f"[occ] {got} downloaded, {skipped} on disk, {gone} unavailable")


# ------------------------------------------------------- OCC FLEX --------
def run_flex(start: date, end: date) -> None:
    """OCC FLEX volume-and-open-interest reports: the bespoke chain behind Q3.

    THE TRAP THIS EXISTS TO AVOID. For any date outside OCC's retention window
    the endpoint answers **HTTP 200 with the body `File requested does not
    exist.`** A fetcher that only checks the status code writes that sentence
    to disk as a report, and every downstream reader then sees a file that
    parses to zero rows for the ticker. That is indistinguishable from "this
    name had no FLEX open interest that day", and it manufactured a whole
    false finding once before it was caught. Retention is roughly 22 months,
    so most of history is permanently gone; a day that is out of window must
    be recorded as UNRETAINED, never as an empty report.

    Two report types, both needed: OI (open interest) and PR (prices). Two
    option types: E (equity) and I (index). Equity OI is what Q3 rests on.
    """
    FLEX_DIR.mkdir(parents=True, exist_ok=True)
    got = skipped = unretained = failed = 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            for rpt in ("OI", "PR"):
                for opt in ("E", "I"):
                    sub = FLEX_DIR / rpt / opt
                    sub.mkdir(parents=True, exist_ok=True)
                    out = sub / f"{d.strftime('%Y%m%d')}.txt"
                    if out.exists():
                        skipped += 1
                        continue
                    # reportDate MUST be YYYYMMDD; anything else 200s with
                    # "Report Date is invalid." See the constants above.
                    url = (f"{FLEX_URL}?reportType={rpt}"
                           f"&optionType={opt}&reportDate={d.strftime('%Y%m%d')}")
                    try:
                        r = fetch(url)
                    except Exception as e:  # noqa: BLE001
                        log_fail(FLEX_DIR, f"{rpt}/{opt}/{d}", repr(e))
                        r = None
                    if r is None:
                        failed += 1
                        continue
                    body = r.content
                    head = body.lstrip()
                    # fail closed on both 200-with-error-body sentinels
                    if head[:len(FLEX_BAD_DATE)] == FLEX_BAD_DATE:
                        raise SystemExit(
                            "[flex] ABORT: OCC rejected the date format. This is a "
                            "bug in the caller, not a data gap, and continuing would "
                            "archive the error string as a report for every day.")
                    if head[:len(FLEX_NOT_RETAINED)] == FLEX_NOT_RETAINED:
                        with (sub / "_UNRETAINED.txt").open("a") as fh:
                            fh.write(f"{d.isoformat()}\n")
                        unretained += 1
                        time.sleep(PAUSE)
                        continue
                    if body[:2] == b"PK":       # some days arrive zip-wrapped
                        with zipfile.ZipFile(io.BytesIO(body)) as z:
                            body = z.read(z.namelist()[0])
                    out.write_bytes(body)
                    got += 1
                    time.sleep(PAUSE)
        d += timedelta(days=1)
    print(f"[flex] {got} downloaded, {skipped} on disk, "
          f"{unretained} outside OCC retention (recorded, not written), "
          f"{failed} failed")
    if unretained:
        print("[flex] NOTE: unretained days are gone for good. OCC keeps roughly "
              "22 months. Archive daily if you want a durable history.")


# ------------------------------------------------------------ ThetaData ---
def run_thetadata(passthrough: list[str]) -> None:
    try:
        requests.get("http://localhost:25503/v3/system/mdds/status", timeout=3)
    except Exception:  # noqa: BLE001
        print("[thetadata] ThetaTerminal is not reachable at localhost:25503.\n"
              "  Start ThetaTerminal (your own subscription) on this machine, then rerun:\n"
              "  .venv/bin/python public/the_parts_that_never_trade/tools/get_data.py thetadata")
        return
    import subprocess
    topup = Path(__file__).with_name("topup_recent.py")
    subprocess.run([sys.executable, str(topup), *passthrough], check=False)


# ------------------------------------------------------------------ CLI ---
def main() -> None:
    import argparse

    p = argparse.ArgumentParser(
        prog="get_data.py",
        description="Download the article's data sources into the expected store layout.",
        epilog="Run with no arguments (or --all) to pull everything.")
    p.add_argument("store", nargs="?", default="all",
                   choices=["all", "ftd", "sbsr", "occ", "flex", "thetadata"],
                   help="which store to pull (default: all)")
    p.add_argument("--all", action="store_true", dest="everything",
                   help="pull every store with its full default window")
    p.add_argument("--start", metavar="YYYY-MM-DD",
                   help="start date (default: each store's own floor)")
    p.add_argument("--end", metavar="YYYY-MM-DD",
                   help="end date (default: today)")
    p.add_argument("--tickers", default=DEFAULT_TICKERS, metavar="A,B,C",
                   help="FTD per-ticker extracts (default: the article's panel)")
    p.add_argument("--force-extract", action="store_true",
                   help="rebuild FTD extracts even from a partial zip archive")
    a = p.parse_args()

    global FORCE_EXTRACT
    FORCE_EXTRACT = a.force_extract
    store = "all" if a.everything else a.store
    end = datetime.strptime(a.end, "%Y-%m-%d").date() if a.end else date.today()
    start = datetime.strptime(a.start, "%Y-%m-%d").date() if a.start else None
    tickers = [t.strip().upper() for t in a.tickers.split(",") if t.strip()]

    if store in ("ftd", "all"):
        run_ftd(start or FTD_FLOOR, end, tickers)
    if store in ("sbsr", "all"):
        run_sbsr(start or SBSR_FLOOR, end)
    if store in ("occ", "all"):
        run_occ(start or end - timedelta(days=365), end)
    if store in ("flex", "all"):
        # OCC retains roughly 22 months; asking for more just logs unretained days.
        run_flex(start or end - timedelta(days=660), end)
    if store in ("thetadata", "all"):
        run_thetadata([])


if __name__ == "__main__":
    main()
