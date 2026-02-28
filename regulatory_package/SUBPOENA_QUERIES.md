# FINRA CAT Subpoena Queries

Eight Consolidated Audit Trail queries designed for immediate execution by FINRA Market Regulation or the SEC Division of Enforcement. These queries target the specific forensic signatures documented in the research series.

**Source:** Paper III, §3.2

---

## Query 1: SPY Block Threshold Evasion

**Purpose:** Identify whether a single Market Participant systematically structures SPY options trades at exactly 499 contracts to remain below the 500-contract ISG surveillance threshold.

```
FILTER:
  Symbol = SPY
  OrderType = LIMIT
  Quantity BETWEEN 490 AND 509
  Side = BUY
  Date BETWEEN 2021-01-01 AND 2025-12-31

RETURN:
  MPID, OrderID, Quantity, Price, Timestamp, ExchangeCode

ANALYSIS:
  - Count distribution of lot sizes 490–509
  - Expected: uniform distribution across the range
  - Finding: 7.5:1 asymmetry at exactly 499 (Paper II §4.9)
  - If a single MPID accounts for >50% of 499-lot orders, that is the entity
```

---

## Query 2: GME Cross-Strike Sonar Probing

**Purpose:** Identify the MPID that sends non-executable quote requests to strikes adjacent to the eventual target, 0.4–2.3 seconds before sweeping.

```
FILTER:
  Symbol = GME
  EventType IN (NEW_ORDER, CANCEL)
  Duration < 2500ms  (time between entry and cancel)
  Date IN [2021-01-27, 2021-06-02, 2024-05-13, 2024-06-07]

JOIN:
  Match cancelled probe orders to subsequent sweep orders
  WHERE probe.MPID = sweep.MPID
  AND sweep.Timestamp - probe.Timestamp BETWEEN 400ms AND 2300ms
  AND probe.Strike != sweep.Strike
  AND ABS(probe.Strike - sweep.Strike) <= 2 strikes

RETURN:
  Probe MPID, Probe Strike, Probe Timestamp,
  Sweep MPID, Sweep Strike, Sweep Timestamp, Sweep Quantity

ANALYSIS:
  - Expected: different MPIDs for probe and sweep (independent market participants)
  - Finding: 100% MPID match in lit-exchange reconstructions (Paper II §4.11)
```

---

## Query 3: $34M Conversion — Options Lock-In

**Purpose:** Identify the MPID that locked the call-side of the January 27, 2021 conversion trade.

```
FILTER:
  Symbol = GME
  Date = 2021-01-27
  Time BETWEEN 14:41:00 AND 14:41:05
  EventType = FILL
  Side = BUY
  OptionType = CALL
  Strike = $200
  Expiry = 2021-01-29

RETURN:
  MPID, OrderID, Quantity, Price, Timestamp, ExchangeCode, ConditionCode

ANALYSIS:
  - Look for a single MPID executing 1,056 contracts in <100ms across 13+ exchanges
  - Finding: Paper II §4.11 documents a 34ms sweep extracting 7.4× NBBO liquidity
```

---

## Query 4: $34M Conversion — Put-Side Lock-In

**Purpose:** Identify the MPID that sold the put-side of the conversion, confirming it matches the call-side MPID.

```
FILTER:
  Symbol = GME
  Date = 2021-01-27
  Time BETWEEN 14:41:00 AND 16:00:00
  EventType = FILL
  Side = SELL
  OptionType = PUT
  Strike = $200
  Expiry = 2021-01-29

RETURN:
  MPID, OrderID, Quantity, Price, Timestamp, ExchangeCode, ConditionCode

ANALYSIS:
  - Expected: different MPID from Query 3 (independent counterparty)
  - If same MPID → both sides of the conversion are controlled by one entity
  - Cross-reference timing gap between call fill and put fill
```

---

## Query 5: $34M Conversion — Equity Delivery

**Purpose:** Trace the equity leg settlement of the conversion trade through dark pool execution venues.

```
FILTER:
  Symbol = GME
  Date BETWEEN 2021-01-27 AND 2021-01-31
  EventType = FILL
  Venue IN (FINRA_TRF, FINRA_ADF, DARK_POOL)
  ConditionCode = 12  (Form T: outside regular hours)

RETURN:
  MPID, OrderID, Quantity, Price, Timestamp, Venue, ConditionCode

ANALYSIS:
  - Look for a block of ~105,600 shares arriving across multiple dark pools
  - Timing: 4+ hours after the options lock (14:41 → 18:00+)
  - Finding: Paper II §4.12 documents fragmented delivery across dark pools
  - If MPID matches Queries 3 and 4 → same entity controlled all three legs
```

---

## Query 6: GME-KOSS Cross-Ticker Settlement

**Purpose:** Determine whether the same MPID settles delivery obligations across both GME and KOSS on the same settlement stress dates.

```
FILTER:
  Symbol IN (GME, KOSS)
  Date IN [T+33 echo dates from Paper V §3.3 + Paper IX §2.1]
  EventType = FILL
  Venue IN (FINRA_TRF, FINRA_ADF)

RETURN:
  MPID, Symbol, OrderID, Quantity, Price, Timestamp, Venue

ANALYSIS:
  - Compute: Jaccard similarity of MPID sets between GME and KOSS fills on echo dates
  - Finding: Statistical correlation Jaccard = 0.882 (Paper IX §2.1)
  - If a single MPID appears in both GME and KOSS fills on >80% of echo dates,
    the basket settlement hypothesis is confirmed
```

---

## Query 7: Put-Call Parity Predictor

**Purpose:** Determine whether the MPIDs executing synthetic conversions (buy call + sell put) match the MPIDs subsequently appearing in FINRA TRF equity fills, confirming the options-to-equity settlement pipeline.

```
FILTER:
  Symbol = GME
  Date IN [T+33 echo dates]

  -- Part A: Conversion trades
  EventType = FILL
  Strategy = CONVERSION (or: matched BUY_CALL + SELL_PUT at same strike/expiry)

  -- Part B: TRF equity fills within 4 hours of Part A
  EventType = FILL
  Venue = FINRA_TRF
  Timestamp BETWEEN conversion.Timestamp AND conversion.Timestamp + 4h

RETURN:
  PartA_MPID, PartA_Timestamp, PartA_Strike, PartA_Quantity,
  PartB_MPID, PartB_Timestamp, PartB_Quantity, PartB_Price

ANALYSIS:
  - Match rate: what percentage of conversion MPIDs appear in subsequent TRF fills?
  - Finding: the pipeline predicts TRF activity (Paper V §6.1, Paper VIII §3.3)
```

---

## Query 8: CAT Linkage Error Exploitation

**Purpose:** Identify MPIDs that systematically break real-time CAT linkage on settlement stress dates and repair the records later within the T+3 window.

```
FILTER:
  Symbol = GME
  Date IN [T+33 echo dates]
  EventType = FILL
  LinkageStatus = REPAIRED  (records originally submitted without inter-firm linkage,
                              subsequently corrected within T+3)

RETURN:
  MPID, OrderID, Original_Timestamp, Repair_Timestamp,
  Quantity, Price, Venue, RepairDelay_Hours

ANALYSIS:
  - Compute: mean RepairDelay on echo dates vs. non-echo dates
  - Expected: repair delays are similar regardless of date
  - Finding: if repairs cluster on echo dates with delays near the T+3 boundary,
    the linkage breakage is deliberate (Paper III §4.2)
  - Cross-reference MPID with the Citadel Securities AWC (FINRA 2020067253501)
```

---

## Notes

- These queries use pseudocode notation for clarity. The FINRA CAT system uses a proprietary query interface; these specifications provide all the logical filters needed for translation.
- All date parameters reference specific settlement echo dates cataloged in [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md), finding #11.
- Query results should be evaluated individually AND cross-referenced: if Queries 1–8 return the same MPID, they collectively demonstrate a single entity operating a unified infrastructure across 3.5 years and 31+ securities.

---

*Source: Paper III, §3.2. See [ACTION_ITEMS.md](ACTION_ITEMS.md), Action 1 for the regulatory context.*
