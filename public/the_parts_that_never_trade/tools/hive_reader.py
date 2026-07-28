#!/usr/bin/env python3
"""hive_reader.py — shared dual-schema reader for the trades hive
(power-tracks-research/data/raw/thetadata/trades/root=<TICKER>/date=<YYYYMMDD>/part-*.parquet).

THE LANDMINE THIS KILLS:
the hive's expiration column is named `expiry` in some files and `expiration`
in others, mixed at FILE level (a day's part-0 and part-leaps can differ), not
by clean era. GME ground truth (2026-07-21 census, 10,248 files):

  - 2018–2019: part-0 is `expiration`-only (503 days)
  - 2020–2025: part-0 carries BOTH names; part-leaps is `expiry`-only
    (2020–2022 have scattered `expiry`-only part-0 days, incl. 2021-01-26/27/28)
  - 2026-02-06 onward (incl. the v3 top-up): `expiration`-only (97 days)

A loader that requests only one name under-reads or, inside try/except,
SILENTLY SKIPS days (an early census missed 507/2,038 GME days, 24.9%;
fixed re-scan took GME 281→345 clips). Every hive loader must accept both
names and assert its day count. This module is the canonical implementation.
Reuse it; do not re-roll per-folder readers.

API:
    read_hive_day(root, ymd, columns=None, parts=("part-0", "part-leaps"))
        -> DataFrame with a normalized `expiration` column (string dates as
           found; both names merged, `expiry` preferred on conflict), plus a
           `hive_date` column (YYYYMMDD). Empty DataFrame if no readable part.
    list_hive_days(root, y0=None, y1=None) -> list of YYYYMMDD strings on disk.
    scan_hive(root, y0=None, y1=None, columns=None, parts=..., assert_coverage=True)
        -> (DataFrame, report dict). Reads every on-disk day in the window and
           ASSERTS day-count coverage: every on-disk day in the window must
           yield a readable frame. Raises CoverageError otherwise — fail
           closed, never silently skip.

Stdlib + pandas + pyarrow only. Run with the repo venv (.venv/bin/python).
"""
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

HIVE_BASE = Path.home() / "Documents/GitHub/power-tracks-research/data/raw/thetadata/trades"

DEFAULT_PARTS = ("part-0", "part-leaps")


class CoverageError(RuntimeError):
    """Raised when a scan cannot account for every on-disk hive day in its window."""


def _read_part(f: Path, columns):
    """Read one parquet part, tolerating both schema names. Returns None if the
    file is unreadable. Always normalizes to a single `expiration` column."""
    try:
        names = pq.read_schema(f).names
    except Exception:
        return None
    want = None
    if columns is not None:
        want = [c for c in columns if c in names]
        # pull whichever expiration-name the file carries if the caller asked
        # for either
        if ("expiry" in columns or "expiration" in columns):
            for alt in ("expiry", "expiration"):
                if alt in names and alt not in want:
                    want.append(alt)
    try:
        df = pd.read_parquet(f, columns=want)
    except Exception:
        return None
    if "expiry" in df.columns:
        df["expiration"] = df["expiry"].fillna(df.get("expiration"))
        df = df.drop(columns=["expiry"])
    return df


def read_hive_day(root: str, ymd: str, columns=None, parts=DEFAULT_PARTS) -> pd.DataFrame:
    """Read one hive day (both parts) for `root` (ticker) and `ymd` (YYYYMMDD)."""
    d = HIVE_BASE / f"root={root}" / f"date={ymd}"
    frames = []
    for part in parts:
        f = d / f"{part}.parquet"
        if not f.exists():
            continue
        df = _read_part(f, columns)
        if df is not None and len(df):
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out["hive_date"] = ymd
    return out


def list_hive_days(root: str, y0: int = None, y1: int = None) -> list:
    """All on-disk day-partition names (YYYYMMDD) for a root, optionally year-clamped."""
    base = HIVE_BASE / f"root={root}"
    days = sorted(p.name.split("=", 1)[1] for p in base.glob("date=*"))
    if y0 is not None:
        days = [d for d in days if int(d[:4]) >= y0]
    if y1 is not None:
        days = [d for d in days if int(d[:4]) <= y1]
    return days


def scan_hive(root: str, y0: int = None, y1: int = None, columns=None,
              parts=DEFAULT_PARTS, assert_coverage: bool = True):
    """Read every on-disk hive day for root in [y0, y1].

    Returns (df, report). With assert_coverage=True (the law), raises
    CoverageError if any on-disk day produced no readable frame — a day that
    cannot be read is a bug to fix, not a day to skip. Days that read fine but
    are empty after the caller's own filters are the caller's business, not
    this function's.
    """
    days = list_hive_days(root, y0, y1)
    frames, unreadable, empty = [], [], []
    for ymd in days:
        df = read_hive_day(root, ymd, columns=columns, parts=parts)
        d = HIVE_BASE / f"root={root}" / f"date={ymd}"
        n_parts = sum(1 for p in parts if (d / f"{p}.parquet").exists())
        if n_parts and df.empty:
            # files existed but nothing came back: distinguish "all parts
            # unreadable" (schema/IO failure) from "parts read, zero rows"
            probe = _read_part(d / f"{parts[0]}.parquet", None) if (d / f"{parts[0]}.parquet").exists() else None
            (unreadable if probe is None else empty).append(ymd)
        elif not df.empty:
            frames.append(df)
    report = {"root": root, "days_on_disk": len(days),
              "days_read": len(frames), "days_empty": len(empty),
              "days_unreadable": len(unreadable),
              "unreadable_dates": unreadable, "empty_dates": empty}
    if assert_coverage and unreadable:
        raise CoverageError(
            f"{root}: {len(unreadable)}/{len(days)} hive days unreadable "
            f"(first: {unreadable[0]}). Fix the reader; do NOT skip days. "
            f"See the hive_reader.py docstring.")
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return out, report
