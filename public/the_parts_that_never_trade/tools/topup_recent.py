#!/usr/bin/env python3
"""topup_recent.py — STANDING incremental top-up for the three frozen GME option stores.

Run from anywhere with the repo venv:
    .venv/bin/python \
        tools/topup_recent.py \
        [--store {greeks|oi|trades|all}] [--through YYYY-MM-DD] [--budget SECONDS] [--dry-run]

Defaults: --store all, --through = latest completed weekday (yesterday, rolled
back over weekends). Re-running is idempotent: days already on disk are skipped.

THE THREE STORES (GME only; byte-compatibility with existing readers is the law):
  1. greeks EOD  — power-tracks-research/data/raw/thetadata/gme_options_greeks_eod/{YYYY-MM-DD}.parquet
                   (research/data/_consolidated/options/greeks_eod/GME is a SYMLINK
                   to that same directory — one physical store, two paths; roots are
                   resolved+deduped so every day is written exactly once). Raw 43-col
                   /v3/option/history/greeks/eod output, expiration="*", one day/call.
                   Failure sidecar: _FAILS.txt (one ISO date/line; retried next run,
                   removed on success). Builder pattern: thirdorder_coupling's
                   extend_gme_greek_cache.py.
  2. OI store    — research/data/_consolidated/options/oi_history/GME/{YYYY-MM-DD}.parquet
                   (a SYMLINK to power-tracks-research/.../gme_options_oi; resolved
                   at load so writes land once in the physical dir). Raw 6-col /v3/option/history/open_interest output (the 06:30-ET
                   snapshot of landmine #9 — the endpoint returns that snapshot;
                   nothing to compute). expiration="*", one day/call.
  3. trades hive — power-tracks-research/data/raw/thetadata/trades/root=GME/date={YYYYMMDD}/part-0.parquet
                   Post-2026-02-06 v3 convention (landmine #11): single part-0,
                   `expiration`-only (never `expiry`), 14 cols:
                   symbol,expiration,strike,right,timestamp,sequence,
                   ext_condition1..4,condition,size,exchange,price
                   per-(expiration, trade-day) /v3/option/history/trade pulls
                   (strike=0 bulk), post-filtered to the max-dte=400 law,
                   deduped on (timestamp,expiration,strike,right,size,price,sequence),
                   int cols fillna(255)->int64, sorted by timestamp, index=False.
                   Builder pattern: hot_quiet_forward_2026-07-20's fetch_theta_topup.py.

SETTLED RULES (DATA_ACCESS.md — do not re-diagnose):
  ThetaData v3 at http://127.0.0.1:25503/v3 ONLY (never :25510/v2). Single-threaded,
  one request at a time, 70s per-request timeout, incremental, local-first.
  HTTP 472 = healthy "no data" (holiday / unlisted expiration), never a failure.

TRADING-DAY CALENDAR (no non-ThetaData network): a weekday is a trading day iff
the OI endpoint returns rows for it. Both greeks and OI empty on the same weekday
= holiday -> skip. OI non-empty but greeks empty = a real greeks failure ->
_FAILS.txt, never fabricated. Startup sanity probes re-pull each scoped store's
last on-disk day and assert the terminal reproduces it (row counts; hive:
cell containment) — if the terminal is down everything would look like a holiday,
so a failed probe ABORTS the run (fail closed).

FAIL CLOSED, ALWAYS: a day that hard-fails is appended to the store's _FAILS.txt
and skipped; partial days are never written (tmp file + os.replace). Writes are
hashed (sha256) and appended to the store's _MANIFEST.jsonl.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import argparse
import hashlib
import io
import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

TD = "http://127.0.0.1:25503/v3"
SYMBOL = "GME"
TIMEOUT = 70
RETRIES = 4
MAX_DTE = 400  # hive top-up law (hot_quiet fetcher): 0 <= dte <= 400 days

REPO = Path(__file__).resolve().parents[3]
PT = REPO.parent / "power-tracks-research/data/raw/thetadata"
# The consolidated greeks/oi GME dirs are SYMLINKS into power-tracks-research
# (DATA_ACCESS.md "mount-the-parent" layout): greeks_eod/GME ->
# gme_options_greeks_eod, oi_history/GME -> gme_options_oi. Resolve and dedupe
# so every write/append happens exactly once per physical directory.
def _uniq(paths):
    out = []
    for p in paths:
        r = p.resolve()
        if r not in out:
            out.append(r)
    return out

GREEKS_ROOTS = _uniq([PT / "gme_options_greeks_eod",
                      REPO / "data/_consolidated/options/greeks_eod/GME"])
OI_ROOT = (REPO / "data/_consolidated/options/oi_history/GME").resolve()
HIVE_ROOT = PT / "trades/root=GME"

HIVE_COLS = ["symbol", "expiration", "strike", "right", "timestamp", "sequence",
             "ext_condition1", "ext_condition2", "ext_condition3", "ext_condition4",
             "condition", "size", "exchange", "price"]
HIVE_INT_COLS = ["sequence", "ext_condition1", "ext_condition2", "ext_condition3",
                 "ext_condition4", "condition", "size", "exchange"]

sys.path.insert(0, str(Path(__file__).resolve().parent))


# ----------------------------------------------------------------- ThetaData I/O
def td_get(path, params, timeout=TIMEOUT, retries=RETRIES):
    """One ThetaData v3 request. Returns ('ok', text) or ('nodata', '').
    Hard failure after retries raises RuntimeError (fail closed)."""
    url = f"{TD}{path}?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            head = raw[:80]
            if (not raw.strip() or raw.lstrip().startswith("{")
                    or "No data" in head or "no data" in head):
                return "nodata", ""
            return "ok", raw
        except urllib.error.HTTPError as e:
            if e.code == 472:  # "No data found" — healthy terminal, empty key
                return "nodata", ""
            last = f"HTTP {e.code}"
        except Exception as e:
            last = str(e)[:120]
        time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"ThetaData failed after {retries} tries ({last}): {url}")


def ymdslash(d):  # 2026-07-21 -> 20260721
    return d.replace("-", "")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def weekdays(a: str, b: str):
    """ISO dates in [a, b] with weekday < 5."""
    d0, d1 = date.fromisoformat(a), date.fromisoformat(b)
    out = []
    d = d0
    while d <= d1:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def default_through() -> str:
    """Latest completed weekday (yesterday, rolled back over a weekend)."""
    d = date.today() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


# ------------------------------------------------------------- calendar oracle
class Oracle:
    """Trading-day oracle = the raw OI day pull (cached). The pull doubles as
    the OI store payload. A hard failure aborts the run (fail closed)."""

    def __init__(self):
        self._cache = {}

    def day(self, d: str):
        """-> ('ok', DataFrame) | ('nodata', None). Raises on hard failure."""
        if d in self._cache:
            return self._cache[d]
        st, raw = td_get("/option/history/open_interest",
                         {"symbol": SYMBOL, "expiration": "*",
                          "start_date": d, "end_date": d})
        if st != "ok":
            res = ("nodata", None)
        else:
            df = pd.read_csv(io.StringIO(raw))
            res = ("ok", df) if len(df) else ("nodata", None)
        self._cache[d] = res
        time.sleep(0.1)
        return res

    def is_trading_day(self, d: str) -> bool:
        return self.day(d)[0] == "ok"


# ------------------------------------------------------------------ manifests
def append_manifest(root: Path, rec: dict):
    with open(root / "_MANIFEST.jsonl", "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def read_fails(path: Path):
    if not path.exists():
        return []
    return sorted({ln.strip() for ln in path.read_text().splitlines() if ln.strip()})


def write_fails(paths, fails):
    """Write the _FAILS set IN PLACE (the greeks roots are hardlinked; an
    in-place write to one updates both. Write both anyway for safety)."""
    text = "".join(d + "\n" for d in sorted(set(fails)))
    for p in paths:
        if text or p.exists():
            with open(p, "w") as f:  # in place: preserves the hardlink pair
                f.write(text)


# ------------------------------------------------------------------ greeks
def topup_greeks(through: str, oracle: Oracle, dry: bool, budget, t0, run_id, log):
    roots = GREEKS_ROOTS
    fails_path = roots[0] / "_FAILS.txt"
    fails = set(read_fails(fails_path))

    def on_disk(d):
        return all((r / f"{d}.parquet").exists() for r in roots)

    last = max(p.stem for r in roots for p in r.glob("????-??-??.parquet"))
    log(f"[greeks] last on disk: {last}; fails pending: {sorted(fails)}")

    # sanity probe: the terminal must reproduce the last stored day
    probe_day = last
    stored = pd.read_parquet(roots[0] / f"{probe_day}.parquet")
    st, raw = td_get("/option/history/greeks/eod",
                     {"symbol": SYMBOL, "expiration": "*",
                      "start_date": probe_day, "end_date": probe_day})
    if st != "ok":
        raise RuntimeError(f"[greeks] SANITY PROBE FAILED: no data for known-good {probe_day}")
    fresh = pd.read_csv(io.StringIO(raw))
    if len(fresh) != len(stored) or list(fresh.columns) != list(stored.columns):
        raise RuntimeError(f"[greeks] SANITY PROBE FAILED: {probe_day} fresh "
                           f"{len(fresh)}x{len(fresh.columns)} vs stored "
                           f"{len(stored)}x{len(stored.columns)} — schema/semantic drift")
    log(f"[greeks] sanity probe ok ({probe_day}: {len(stored)} rows reproduced)")

    cand = sorted(set(weekdays((date.fromisoformat(last) + timedelta(days=1)).isoformat(), through))
                  | {f for f in fails if f <= through})
    new_days, failed, holidays = [], [], []
    for d in cand:
        if on_disk(d):
            if d in fails and not dry:
                fails.discard(d)  # healed by an earlier run
            continue
        if budget and time.time() - t0 > budget:
            log(f"[greeks] BUDGET_OUT before {d}")
            break
        if not oracle.is_trading_day(d):
            holidays.append(d)
            if d in fails and not dry:
                fails.discard(d)  # a non-trading day can't be a data failure
            continue
        if dry:
            new_days.append((d, -1))
            continue
        try:
            st, raw = td_get("/option/history/greeks/eod",
                             {"symbol": SYMBOL, "expiration": "*",
                              "start_date": d, "end_date": d})
        except RuntimeError as e:
            st, raw = "error", str(e)
        if st != "ok":
            log(f"[greeks] FAIL {d}: {raw if st == 'error' else 'nodata on a confirmed trading day'}")
            fails.add(d)
            failed.append(d)
            continue
        df = pd.read_csv(io.StringIO(raw))
        if not len(df):
            log(f"[greeks] FAIL {d}: empty frame on a confirmed trading day")
            fails.add(d)
            failed.append(d)
            continue
        primary = roots[0]
        tmp = primary / f".tmp-{d}.parquet"
        df.to_parquet(tmp)  # index default — matches extend_gme_greek_cache.py
        os.replace(tmp, primary / f"{d}.parquet")
        files = [str(primary / f"{d}.parquet")]
        for extra in roots[1:]:  # only if the symlink pair is ever broken
            fp = extra / f"{d}.parquet"
            if not fp.exists():
                try:
                    os.link(primary / f"{d}.parquet", fp)
                except OSError:  # cross-device fallback: same bytes
                    shutil.copy2(primary / f"{d}.parquet", fp)
            files.append(str(fp))
        fails.discard(d)
        sha = sha256_file(primary / f"{d}.parquet")
        rec = {"kind": "day", "store": "greeks", "date": d, "rows": int(len(df)),
               "sha256": sha, "files": files,
               "run_id": run_id, "written_at": datetime.now().isoformat(timespec="seconds")}
        for r in roots:
            append_manifest(r, rec)
        new_days.append((d, len(df)))
        log(f"[greeks] {d}: {len(df)} rows written (sha256 {sha[:12]}…)")
        time.sleep(0.1)
    if not dry:
        write_fails([r / "_FAILS.txt" for r in roots], fails)
    return {"store": "greeks", "before": last, "new_days": new_days,
            "failed": failed, "holidays": holidays,
            "after": max([last] + [d for d, _ in new_days]) if new_days else last}


# ------------------------------------------------------------------ oi
def topup_oi(through: str, oracle: Oracle, dry: bool, budget, t0, run_id, log):
    root = OI_ROOT
    root.mkdir(parents=True, exist_ok=True)
    last = max(p.stem for p in root.glob("????-??-??.parquet"))
    log(f"[oi] last on disk: {last}")

    stored = pd.read_parquet(root / f"{last}.parquet")
    st, probe = oracle.day(last)
    if st != "ok" or len(probe) != len(stored) \
            or int(probe["open_interest"].sum()) != int(stored["open_interest"].sum()) \
            or list(probe.columns) != list(stored.columns):
        raise RuntimeError(f"[oi] SANITY PROBE FAILED on known-good {last} "
                           f"(stored {len(stored)} rows / OI {stored['open_interest'].sum()})")
    log(f"[oi] sanity probe ok ({last}: {len(stored)} rows, "
        f"OI {int(stored['open_interest'].sum()):,} reproduced)")

    cand = weekdays((date.fromisoformat(last) + timedelta(days=1)).isoformat(), through)
    new_days, failed, holidays = [], [], []
    for d in cand:
        if (root / f"{d}.parquet").exists():
            continue
        if budget and time.time() - t0 > budget:
            log(f"[oi] BUDGET_OUT before {d}")
            break
        st, df = oracle.day(d)
        if st != "ok":
            holidays.append(d)
            continue
        if dry:
            new_days.append((d, -1))
            continue
        tmp = root / f".tmp-{d}.parquet"
        df.to_parquet(tmp)  # raw endpoint frame, index default — matches builder
        os.replace(tmp, root / f"{d}.parquet")
        sha = sha256_file(root / f"{d}.parquet")
        append_manifest(root, {"kind": "day", "store": "oi", "date": d,
                               "rows": int(len(df)), "sha256": sha,
                               "files": [str(root / f"{d}.parquet")], "run_id": run_id,
                               "written_at": datetime.now().isoformat(timespec="seconds")})
        new_days.append((d, len(df)))
        log(f"[oi] {d}: {len(df)} rows written (sha256 {sha[:12]}…)")
    return {"store": "oi", "before": last, "new_days": new_days,
            "failed": failed, "holidays": holidays,
            "after": max([last] + [d for d, _ in new_days]) if new_days else last}


# ------------------------------------------------------------------ trades
def list_expirations():
    st, raw = td_get("/option/list/expirations", {"symbol": SYMBOL}, timeout=30)
    if st != "ok":
        raise RuntimeError("expiration listing failed")
    df = pd.read_csv(io.StringIO(raw))
    df.columns = [c.strip() for c in df.columns]
    return sorted(pd.to_datetime(df["expiration"]).dt.strftime("%Y-%m-%d").unique())


def topup_trades(through: str, oracle: Oracle, dry: bool, budget, t0, run_id, log):
    root = HIVE_ROOT
    fails_path = root / "_FAILS.txt"
    fails = set(read_fails(fails_path))
    last = max(p.name.split("=", 1)[1] for p in root.glob("date=*"))
    last_slash = f"{last[:4]}-{last[4:6]}-{last[6:]}"
    log(f"[trades] last on disk: {last_slash}; fails pending: {sorted(fails)}")

    # identity probe: a fresh cell pull must reproduce the stored hive rows
    old = pd.read_parquet(root / f"date={last}/part-0.parquet")
    probe_exp = old["expiration"].value_counts().idxmax()
    st, raw = td_get("/option/history/trade",
                     {"symbol": SYMBOL, "expiration": ymdslash(probe_exp),
                      "strike": 0, "date": last, "format": "csv"})
    if st != "ok":
        raise RuntimeError(f"[trades] IDENTITY PROBE FAILED: no data for known cell "
                           f"({probe_exp}, {last_slash})")
    new = pd.read_csv(io.StringIO(raw))
    new["ts_norm"] = pd.to_datetime(new["timestamp"], format="ISO8601")
    old_c = old[old["expiration"] == probe_exp].copy()
    old_c["ts_norm"] = pd.to_datetime(old_c["timestamp"], format="ISO8601")
    keycols = ["ts_norm", "strike", "right", "size", "price", "sequence"]
    new_k = set(map(tuple, new[keycols].itertuples(index=False, name=None)))
    old_k = set(map(tuple, old_c[keycols].itertuples(index=False, name=None)))
    missing = old_k - new_k
    if missing:
        raise RuntimeError(f"[trades] IDENTITY PROBE FAILED: {len(missing)}/{len(old_k)} "
                           f"stored rows not reproduced for ({probe_exp}, {last_slash})")
    log(f"[trades] identity probe ok ({probe_exp} {last_slash}: {len(old_k)} hive rows "
        f"reproduced, {len(new_k - old_k)} fresh rows beyond hive)")

    exps = list_expirations()
    cand = sorted(set(weekdays((date.fromisoformat(last_slash) + timedelta(days=1)).isoformat(), through))
                  | {f for f in fails if f <= through})
    new_days, failed, holidays = [], [], []
    for d in cand:
        ymd = ymdslash(d)
        if (root / f"date={ymd}/part-0.parquet").exists():
            if d in fails and not dry:
                fails.discard(d)
            continue
        if budget and time.time() - t0 > budget:
            log(f"[trades] BUDGET_OUT before {d}")
            break
        if not oracle.is_trading_day(d):
            holidays.append(d)
            if d in fails and not dry:
                fails.discard(d)  # a non-trading day can't be a data failure
            continue
        if dry:
            n_exp = sum(1 for e in exps if 0 <= (date.fromisoformat(e) - date.fromisoformat(d)).days <= MAX_DTE)
            new_days.append((d, -n_exp))  # rows unknown; carry request count
            continue
        day_frames, day_failed = [], False
        for e in exps:
            dte = (date.fromisoformat(e) - date.fromisoformat(d)).days
            if not (0 <= dte <= MAX_DTE):
                continue
            try:
                st, raw = td_get("/option/history/trade",
                                 {"symbol": SYMBOL, "expiration": ymdslash(e),
                                  "strike": 0, "date": ymd, "format": "csv"})
            except RuntimeError as ex:
                log(f"[trades] FAIL {d} exp {e}: {ex}")
                day_failed = True
                break
            if st == "ok":
                day_frames.append(pd.read_csv(io.StringIO(raw),
                                              dtype={"symbol": str, "expiration": str,
                                                     "right": str, "timestamp": str}))
            time.sleep(0.1)
        if day_failed:
            fails.add(d)
            failed.append(d)
            continue
        if not day_frames:
            log(f"[trades] FAIL {d}: zero rows across all in-law expirations on a "
                f"confirmed trading day — refusing to write an empty day")
            fails.add(d)
            failed.append(d)
            continue
        allt = pd.concat(day_frames, ignore_index=True)
        allt = allt.drop_duplicates(subset=["timestamp", "expiration", "strike",
                                            "right", "size", "price", "sequence"])
        allt["trade_date"] = pd.to_datetime(allt["timestamp"].str[:10])
        allt["dte"] = (pd.to_datetime(allt["expiration"]) - allt["trade_date"]).dt.days
        allt = allt[(allt["dte"] >= 0) & (allt["dte"] <= MAX_DTE)]
        for c in HIVE_INT_COLS:
            allt[c] = allt[c].fillna(255).astype("int64")
        allt["strike"] = allt["strike"].astype("float64")
        allt["price"] = allt["price"].astype("float64")
        out = allt[allt["trade_date"] == pd.Timestamp(d)][HIVE_COLS] \
            .sort_values("timestamp").reset_index(drop=True)
        if not len(out):
            fails.add(d)
            failed.append(d)
            log(f"[trades] FAIL {d}: rows collapsed to zero after lawful filters")
            continue
        ddir = root / f"date={ymd}"
        ddir.mkdir(parents=True, exist_ok=True)
        tmp = ddir / ".tmp-part-0.parquet"
        out.to_parquet(tmp, index=False)
        os.replace(tmp, ddir / "part-0.parquet")
        fails.discard(d)
        sha = sha256_file(ddir / "part-0.parquet")
        append_manifest(root, {"kind": "day", "store": "trades", "date": d,
                               "rows": int(len(out)), "sha256": sha,
                               "files": [str(ddir / "part-0.parquet")], "run_id": run_id,
                               "written_at": datetime.now().isoformat(timespec="seconds")})
        new_days.append((d, len(out)))
        log(f"[trades] {d}: {len(out)} rows written "
            f"({len(day_frames)} expirations, sha256 {sha[:12]}…)")
    if not dry:
        write_fails([fails_path], fails)
    return {"store": "trades", "before": last_slash, "new_days": new_days,
            "failed": failed, "holidays": holidays,
            "after": max([last_slash] + [d for d, _ in new_days]) if new_days else last_slash}


# ------------------------------------------------------------------ validate
def trailing_rows(store: str, before: str, n=5):
    """Row counts of the n on-disk days immediately before the gap."""
    if store == "greeks":
        days = sorted(p.stem for p in GREEKS_ROOTS[0].glob("????-??-??.parquet") if p.stem <= before)
        return {d: len(pd.read_parquet(GREEKS_ROOTS[0] / f"{d}.parquet")) for d in days[-n:]}
    if store == "oi":
        days = sorted(p.stem for p in OI_ROOT.glob("????-??-??.parquet") if p.stem <= before)
        return {d: len(pd.read_parquet(OI_ROOT / f"{d}.parquet")) for d in days[-n:]}
    days = sorted(p.name.split("=", 1)[1] for p in HIVE_ROOT.glob("date=*")
                  if p.name.split("=", 1)[1] <= ymdslash(before))
    import hive_reader
    return {f"{d[:4]}-{d[4:6]}-{d[6:]}": len(hive_reader.read_hive_day("GME", d, columns=["symbol"]))
            for d in days[-n:]}


def validate(store: str, new_days, before: str, log):
    """Read back each new day via the house readers; rows vs trailing-5 median."""
    import hive_reader
    rep = {"store": store, "before": before}
    trail = trailing_rows(store, before)
    med = float(pd.Series(list(trail.values())).median()) if trail else float("nan")
    rep["trailing5"] = trail
    rep["trailing5_median_rows"] = med
    checks = []
    for d, rows in new_days:
        if store == "greeks":
            df = pd.read_parquet(GREEKS_ROOTS[0] / f"{d}.parquet")
            ok_cols = len(df.columns) == 43
            rb = len(df)
        elif store == "oi":
            df = pd.read_parquet(OI_ROOT / f"{d}.parquet")
            ok_cols = list(df.columns) == ["symbol", "expiration", "strike", "right",
                                           "timestamp", "open_interest"]
            rb = len(df)
        else:
            df = hive_reader.read_hive_day("GME", ymdslash(d))
            ok_cols = ("expiration" in df.columns) and ("expiry" not in df.columns)
            rb = len(df)
        if store == "trades":
            assert rb > 0, f"hive read-back of {d} came back EMPTY — unreadable new day"
        checks.append({"date": d, "rows": int(rb), "schema_ok": bool(ok_cols),
                       "ratio_vs_trailing5_median": round(rb / med, 3) if med and med == med else None})
        if rows not in (-1,) and rows > 0 and rb != rows:
            raise RuntimeError(f"[{store}] read-back mismatch {d}: wrote {rows}, read {rb}")
    rep["days"] = checks
    rep["days_added"] = len(checks)
    rep["rows_added"] = int(sum(c["rows"] for c in checks))
    # hive: day-count assertion over the topped-up window via the canonical scanner
    if store == "trades" and checks:
        y0 = int(checks[0]["date"][:4])
        _, scan_rep = hive_reader.scan_hive("GME", y0, y0, columns=["symbol"], assert_coverage=True)
        rep["hive_scan_2026"] = {k: scan_rep[k] for k in
                                 ("days_on_disk", "days_read", "days_empty", "days_unreadable")}
        log(f"[trades] hive_reader.scan_hive 2026: {scan_rep['days_read']}/{scan_rep['days_on_disk']} "
            f"days readable, {scan_rep['days_unreadable']} unreadable, {scan_rep['days_empty']} empty")
    return rep


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--store", choices=["greeks", "oi", "trades", "all"], default="all")
    ap.add_argument("--through", default=None, help="YYYY-MM-DD; default = latest completed weekday")
    ap.add_argument("--budget", type=float, default=0,
                    help="seconds; 0 = no limit. On expiry: finish current day, report, exit.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    through = args.through or default_through()
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S")
    t0 = time.time()

    def log(msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

    stores = ["greeks", "oi", "trades"] if args.store == "all" else [args.store]
    log(f"topup_recent run {run_id} | stores={stores} through={through} "
        f"dry_run={args.dry_run} budget={args.budget or 'none'}")

    oracle = Oracle()
    results, validations = [], []
    try:
        for s in stores:
            if s == "greeks":
                r = topup_greeks(through, oracle, args.dry_run, args.budget, t0, run_id, log)
            elif s == "oi":
                r = topup_oi(through, oracle, args.dry_run, args.budget, t0, run_id, log)
            else:
                r = topup_trades(through, oracle, args.dry_run, args.budget, t0, run_id, log)
            results.append(r)
            if not args.dry_run and r["new_days"]:
                validations.append(validate(s, r["new_days"], r["before"], log))
    except RuntimeError as e:
        log(f"FAIL CLOSED — aborting run: {e}")
        print(json.dumps({"run_id": run_id, "status": "aborted", "reason": str(e),
                          "results": results}, indent=2, default=str))
        sys.exit(2)

    status = "dry_run" if args.dry_run else ("ok" if not any(r["failed"] for r in results) else "ok_with_failed_days")
    summary = {"run_id": run_id, "status": status, "through": through,
               "elapsed_s": round(time.time() - t0, 1),
               "stores": results, "validation": validations}
    if not args.dry_run:
        for r in results:
            roots = {"greeks": GREEKS_ROOTS, "oi": [OI_ROOT], "trades": [HIVE_ROOT]}[r["store"]]
            for root in roots:
                append_manifest(root, {"kind": "run", "run_id": run_id, "store": r["store"],
                                       "status": status, "through": through,
                                       "days_added": len(r["new_days"]),
                                       "rows_added": int(sum(n for _, n in r["new_days"] if n > 0)),
                                       "failed": r["failed"], "holidays": r["holidays"],
                                       "elapsed_s": summary["elapsed_s"]})
    print("=" * 78)
    print(json.dumps(summary, indent=2, default=str))
    if any(r["failed"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
