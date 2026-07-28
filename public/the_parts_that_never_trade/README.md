# Replication package — "The parts of GME's options chain that never trade, and the machines that do"

This folder is the supporting kit for the article in `posts/shareables_2026-07-22/the_parts_that_never_trade.md`. The goal is full openness on everything the article claims: what data was used, exactly how to pull it, how each question was tested, and what would falsify the findings. The only thing not included is the market data itself, which is licensed and must be pulled from the vendors directly (see `DATA_SOURCES.md` for exactly how).

## What's in this package

| File | Contents |
|------|----------|
| `README.md` | This file: orientation and quick start |
| `DATA_SOURCES.md` | Every data source used, with endpoints, coverage windows, known landmines, and pull scripts |
| `QUESTION_MAP.md` | For each article question (Q1–Q12): what was tested, against which nulls, the key numbers, and the figures — plus the hash commitments behind the standing forward watches |
| `METHOD.md` | The statistical discipline: pre-registration, frozen configs, null construction, verdict taxonomy, and the forward observatory |
| `tools/get_data.py` | One-command bootstrap: downloads the free public stores (SEC FTD, DTCC swap tape, OCC daily OI) from their primary sources into the expected layout, and delegates the licensed options stores to `topup_recent.py` |
| `tools/topup_recent.py` | The standing incremental top-up that builds and maintains the three GME option stores (greeks EOD, open interest, trades) from ThetaData v3 |
| `tools/hive_reader.py` | The canonical fail-closed loader for the trades hive, including the dual-schema landmine it exists to kill |

The article's figures live in `posts/shareables_2026-07-22/figures/`, and the scripts that drew them in `posts/shareables_2026-07-22/code/`. The scripts read their derived inputs from `posts/claim_tests/<finding>/data/`, the per-finding test folders. Those folders are deliberately **not** distributed and neither is any market data: nothing of either kind ships in this repository, so a freshly cloned copy will report missing input paths until you rebuild them. `QUESTION_MAP.md` describes what each finding computed and `DATA_SOURCES.md` tells you how to pull the raw stores those computations run on. Every input derives from the sources documented in `DATA_SOURCES.md` — rebuild the stores, re-run the analyses, and the figures follow.

## Quick start

```bash
git clone https://github.com/TheGameStopsNow/research.git
cd research
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Then stand up the data stores. Everything public is one command:

```bash
.venv/bin/python public/the_parts_that_never_trade/tools/get_data.py --all
```

That pulls the SEC fails-to-deliver archive (2004 → present), the DTCC SBSR swap tape (its free ~1-year retention window), and OCC daily open interest, each into the layout the analyses expect — and, if a ThetaTerminal is running under your own subscription, tops up the three GME option stores too. Read `DATA_SOURCES.md` for what each store is and its known landmines. Read `METHOD.md` so you hold the work to the same bar it held itself to. Then take any question in `QUESTION_MAP.md` and rebuild it: every test is described by its design, window, populations, and null construction, and every headline number is listed so you know what you're trying to reproduce.

## What you need that isn't here

Raw market data. The options tape (trades, quotes, open interest, greeks) comes from ThetaData and cannot be redistributed; the equity bars come from any SIP source; the swap tape and FTD archives are free public DTCC/SEC data. If you have any way to get per-contract OPRA history with open interest, you can rebuild every input this article touched.

## What no one can get

The public tape has venue and condition codes but no participant identity: no CAT, no MPIDs, no open/close flags. ThetaData resells the anonymized OPRA SIP, which has no order-origin field. That is the honest ceiling of this entire research program, and it is why the article never names an actor. Every positive result caps at "directed, uneconomic structure that beats mundane controls" — a description of the ledger, never an accusation.

## License and disclaimer

Same as the repository root: independent research on public and commercially licensed data; not financial advice; no actor attribution. See the root `LICENSE` and `README.md`.
