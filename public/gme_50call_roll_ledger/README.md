# GME persistent $50 call — roll ledger (reproducible)

A descriptive, chronological ledger of the 117 dominant-expiration hand-offs of a
split-adjusted **$50 GME call** structure, 2021-01-27 to 2026-06-26. Open interest
is **aggregate across all holders**: this is a position **structure**, not any one
actor, and no person is named. It is a factual record of what the open-interest data
shows. It is **not** a claim that rolls predict tops, and it is not investment advice.

`roll_ledger.csv` is the only data file here. The **raw ThetaData is licensed and is
not redistributed** — this folder ships the derived ledger plus the exact steps so you
can regenerate it (and locate every contract) from your own data subscriptions.

## What each row is

One row per **hand-off**: a date where the expiration holding the most open interest at
the $50 adjusted strike changes from one expiration to the next. Row 0 is the OPEN
(the strike blinking on from zero on 2021-01-27). A "roll" here is reconstructed from
where standing OI sits, not from an executed trade.

## Data sources (bring your own)

- **Options open interest & prices:** ThetaData v3, local terminal REST at
  `http://127.0.0.1:25503/v3`. Endpoints used:
  `option/history/open_interest`, `option/history/eod`, `option/history/trade_quote`.
  Requires a ThetaData options subscription (this ledger was built on the PROFESSIONAL tier).
- **Split-adjusted equity price:** Alpaca Market Data (SIP feed),
  `GET /v2/stocks/GME/bars?timeframe=1Day&adjustment=split&feed=sip`.

## Method — follow these steps exactly

1. **Build the OI panel.** For GME, pull EOD open interest per
   `(expiration, strike, right)` across 2020-06-01 to 2026-06-26 from
   `option/history/open_interest`. One row per contract per day.
2. **Split-adjust (4:1, ex-date 2022-07-22).** GameStop split 4:1 as a whole ratio, so
   OCC used the standard adjustment: strike divided by 4, contract count multiplied by 4,
   100-share multiplier unchanged. For every snapshot **before** 2022-07-22 set
   `strike_adj = raw_strike / 4` and `oi_adj = open_interest * 4`; on/after the split the
   raw and adjusted values are equal. The persistent call sits at `strike_adj = 50`
   (raw **$200** before the split, **$50** after).
3. **Standing OI.** For the $50 adjusted call, sum `oi_adj` over **all** expirations on
   each date. This is the "how much is alive at this strike today" series.
4. **Dominant leg.** On each date, take the single expiration holding the **maximum**
   `oi_adj` at the $50 adjusted strike. That is the leg the structure is currently parked in.
5. **Hand-offs (the rows).** Walk the dates in order; whenever the dominant expiration
   differs from the previous trading day, emit a row: `from_expiration` (previous dominant),
   `to_expiration` (new dominant), on that `roll_date`. The first appearance is the OPEN.
6. **Price context.** Take the Alpaca SIP split-adjusted daily close. Daily return =
   pct change. A **jump** is any day with `|return| >= 20%`. For each roll, record the
   signed trading-day distance to the nearest jump (negative = the jump came first) and a
   flag for whether a jump falls within +/- 5 trading days.

Reference implementation: `00_build_panel.py` ... `07_roll_ledger.py` and
`08_enrich_and_publish_ledger.py` in the research post
`posts/claim_tests/theta_pet_persistent_rolled_positions_2026-07-14/code/`.

## Locate any contract yourself

Each row carries a locator so you can pull the exact contract:

- `to_leg_occ` / `from_leg_occ` — the OCC option symbol, e.g. `GME270115C00050000`
  (root GME, YYMMDD expiry, C, strike x 1000). Pre-split legs use the raw **$200** strike,
  e.g. `GME210219C00200000`.
- `thetadata_key_to_leg` — the exact query string, e.g.
  `symbol=GME&expiration=20270115&right=C&strike=50`. Append it to
  `http://127.0.0.1:25503/v3/option/history/open_interest?...` for the OI series, or to
  `.../option/history/trade_quote?...` for the anonymized time-and-sales prints
  (size, price, exchange, NBBO) on that contract.
- `standing_OI_delta_on_roll_date` — the day-over-day change in total $50 standing OI on
  the roll date, so you can see the magnitude of the shift.

## Honest limits

- **Open interest is not trades.** Rows are OI-derived hand-offs, not executions. You can
  confirm the structure and pull the prints on a contract, but no single "roll trade" is
  identifiable, because OI nets all holders and a roll may be many prints or none that day.
- **The tape is anonymous.** OPRA (what ThetaData resells) carries no participant, account
  type, or open/close tag at any tier. You can see *what* traded, never *who*. Attribution
  needs account-level data (e.g. Cboe/OCC Open-Close), which is not used or shipped here.
- **Descriptive only.** This ledger records what the OI shows. It makes no claim that rolls
  anticipate price tops, and it is not advice.

## Column dictionary

`roll_number`, `event` (OPEN/ROLL), `roll_date`, `from_expiration`, `to_expiration`,
`strike_adj` ($50), `raw_listed_strike` ($200 pre-split / $50 post), `new_leg_OI_adj`,
`standing_OI_at_50_adj`, `dte_leg_closed` (negative = prior leg already expired, a gap in
the reconstruction), `dte_leg_opened`, `gme_price_splitadj`,
`trading_days_to_nearest_jump` (signed), `nearest_jump_move_pct`,
`within_5d_of_20pct_move`, `note`, `from_leg_occ`, `to_leg_occ`, `thetadata_key_to_leg`,
`standing_OI_delta_on_roll_date`.

*Built 2026-07-14 from cached ThetaData EOD OI + Alpaca SIP price. Derived ledger only; no raw licensed data included.*
