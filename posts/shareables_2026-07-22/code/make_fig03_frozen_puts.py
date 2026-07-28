#!/usr/bin/env python3
"""make_fig03_frozen_puts.py — the frozen put legs, with a moneyness panel.

Panel A: daily put open interest in the two financing-unit legs (K37 Dec-26,
K50 Jan-27) plus the K30 comparison lines, from the daily OI store.
Panel B (shared x): GME spot with the two strikes drawn as dashed levels, so
the vertical gap IS the puts' in-the-money depth; the shaded span marks the
weeks the article calls "$13-26 in the money."

Run from the repo root with the repo venv:
    .venv/bin/python posts/shareables_2026-07-22/code/make_fig03_frozen_puts.py

Inputs: the daily OI store and greeks-EOD store documented in the replication
package's DATA_SOURCES.md. Output: figures/fig03_frozen_puts_rebuilt.png.
"""
from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
PT = Path.home() / "Documents/GitHub/power-tracks-research/data/raw/thetadata"
OI_DIR = PT / "gme_options_oi"
GREEKS_DIR = PT / "gme_options_greeks_eod"
OUT_FIG = REPO / "posts/shareables_2026-07-22/figures/fig03_frozen_puts_rebuilt.png"

START, END = "2025-12-01", "2026-07-24"
LINES = [  # (expiration, strike, label, color)
    ("2026-12-18", 37.0, "K37 Dec-26 put (unit 1)", "tab:red"),
    ("2027-01-15", 50.0, "K50 Jan-27 put (unit 2)", "tab:orange"),
    ("2027-01-15", 30.0, "K30 Jan-27 put (precursor ladder)", "tab:green"),
    ("2026-12-18", 30.0, "K30 Dec-26 put (ambient/diffuse)", "0.5"),
]
PRINT_DAYS = [("2026-04-14", "tab:red"), ("2026-05-07", "tab:orange")]


def day_files(d: Path) -> list[str]:
    return [f for f in sorted(glob.glob(str(d / "*.parquet")))
            if START <= Path(f).stem <= END]


def main() -> None:
    oi_rows, spot_rows = [], []
    for f in day_files(OI_DIR):
        df = pd.read_parquet(f, columns=["expiration", "strike", "right", "open_interest"])
        if df["strike"].median() > 5000:
            df["strike"] = df["strike"] / 1000.0
        r = df["right"].astype(str).str.upper().str[0]
        exp = pd.to_datetime(df["expiration"], errors="coerce").dt.strftime("%Y-%m-%d")
        for e, k, label, _c in LINES:
            m = df[(r == "P") & (exp == e) & (df["strike"] == k)]
            oi_rows.append(dict(date=Path(f).stem, label=label,
                                oi=float(m["open_interest"].sum())))
    for f in day_files(GREEKS_DIR):
        try:
            df = pd.read_parquet(f, columns=["underlying_price"])
            u = df["underlying_price"]
            u = u[(u > 0) & u.notna()]
            if len(u):
                spot_rows.append(dict(date=Path(f).stem, close=float(u.median())))
        except Exception:  # noqa: BLE001 - a malformed day shouldn't kill the figure
            continue

    oi = pd.DataFrame(oi_rows)
    oi["date"] = pd.to_datetime(oi["date"])
    spot = pd.DataFrame(spot_rows)
    spot["date"] = pd.to_datetime(spot["date"])
    spot = spot.sort_values("date")

    itm = spot[(spot["date"] >= PRINT_DAYS[0][0]) & (37.0 - spot["close"] >= 13.0)]
    if not itm.empty:
        d37 = 37.0 - itm["close"]
        d50 = 50.0 - itm["close"]
        print(f"[itm] span {itm['date'].min():%Y-%m-%d} -> {itm['date'].max():%Y-%m-%d}; "
              f"K37 depth {d37.min():.0f}-{d37.max():.0f}, K50 depth {d50.min():.0f}-{d50.max():.0f}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax, axp) = plt.subplots(2, 1, figsize=(12.8, 8.6), sharex=True,
                                  height_ratios=[2.1, 1.0])
    for e, k, label, c in LINES:
        g = oi[oi["label"] == label].sort_values("date")
        ax.plot(g["date"], g["oi"], color=c, lw=1.8, label=label)
    for d, c in PRINT_DAYS:
        ax.axvline(pd.Timestamp(d), color=c, ls="--", lw=1.0, alpha=0.6)
        axp.axvline(pd.Timestamp(d), color=c, ls="--", lw=1.0, alpha=0.6)
    ax.set_ylabel("put open interest")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_title("Signature: program put legs are frozen — held, not traded, not exercised "
                 "(dashed verticals = unit print days)", fontsize=11)

    axp.plot(spot["date"], spot["close"], color="black", lw=1.4)
    axp.axhline(37.0, color="tab:red", ls="--", lw=1.0, alpha=0.8)
    axp.axhline(50.0, color="tab:orange", ls="--", lw=1.0, alpha=0.8)
    axp.text(spot["date"].min(), 37.4, "unit-1 strike $37", fontsize=8, color="tab:red")
    axp.text(spot["date"].min(), 50.4, "unit-2 strike $50", fontsize=8, color="tab:orange")
    if not itm.empty:
        axp.axvspan(itm["date"].min(), itm["date"].max(), color="gold", alpha=0.18)
        mid = itm["date"].min() + (itm["date"].max() - itm["date"].min()) / 2
        axp.text(mid, 43.0,
                 "puts $13–29 in the money\n(the gap from spot up to each strike)",
                 ha="center", va="center", fontsize=8.5, color="0.25")
    axp.set_ylabel("GME close ($)")
    axp.set_ylim(spot["close"].min() * 0.9, 54)
    axp.set_title("The moneyness picture: spot vs the two strikes — the gap is the ITM depth "
                  "a normal holder would harvest", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT_FIG, dpi=150)
    print(f"[write] {OUT_FIG}")


if __name__ == "__main__":
    main()
