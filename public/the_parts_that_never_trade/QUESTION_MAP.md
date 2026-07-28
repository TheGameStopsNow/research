# Question map — what was tested, how, and what to reproduce

One section per article question: the test design, the null it had to beat, the key numbers a replicator should recover, and the figures. Data stores and pull scripts are in `DATA_SOURCES.md`; the discipline every test ran under (frozen specs, sha256-pinned configs, fail-closed loaders) is in `METHOD.md`. Composite figure scripts (`make_fig*.py`, `make_tw_*.py`) live in `posts/shareables_2026-07-22/code/`; all figures in `posts/shareables_2026-07-22/figures/`. The scripts' derived inputs are not distributed — no market data ships in this repository; they rebuild from the sources in `DATA_SOURCES.md`.

## Q1–Q2 — the married pairs and the financing reading

**Design.** Scan the full GME trades hive (2018 → present, dual-schema loader with asserted day coverage) for married pairs: a call print and a put print at the same expiration, strike, and size, nearest-in-time within 2,000 ms, floor 250 contracts per leg. Census the matches; track each unit's put-leg open interest daily thereafter. Back the implied financing rate out of married prices via discounted put-call parity. Repeat the census across 12 tickers and date each name's clusters against its own borrow-stress calendar (hard-to-borrow windows, FTD spikes from the SEC archive).

**Key numbers.** 406 clips → 278 GME events since 2018-02, rebuilt via `posts/shareables_2026-07-22/code/rebuild_fig01_married_census.py`. This supersedes an earlier 201-event count, which under-read the census through two independent hive landmines: the `expiry`/`expiration` column-name mix (all of 2018–2019 skipped) and a `right`-value mix where some files encode `CALL`/`PUT` and at least one mixes those with `C`/`P` in the same file (2024 pairs dropped). The rebuild's 406 clips are a strict superset of the prior corrected re-scan's 345, with zero clips lost. Event size is the summed matched contracts per side; `max_clip` is the largest single print, and the two diverge sharply on laddered days (July 2019: 18,400 summed across 7 clips, largest single 7,500). Largest single married prints in the whole census: 10,000 on 2024-06-07 ($40, 7 days to expiry) and 10,000 on 2026-04-14 ($37, far-dated); two ~10,000-lot far-dated units (2026-04-14 Dec-26 $37; 2026-05-07 Jan-27 $50) with frozen put legs (10,045 and 10,011 contracts, zero trades or exercises since print); implied borrow ≈ +19%/yr in the 2020 hard-borrow era, +2.3% and +5.5% on the two new units; AMC's 42,567-contract-per-side unit pricing +189–235%/yr in 2023; signature present in 10 of 12 names tested.

### Census count history (Q1) — read this before calling the numbers unstable

Three different married-pair counts exist across this project's own artifacts. All three are the same detector at different states of repair, and the progression is the audit trail, not instability:

| Count | Source | Why it changed |
|---|---|---|
| 285 clips → 201 events | original Hunt-13 census, as printed on the first published fig01 | loader requested only the `expiry` column and swallowed read errors, silently skipping ~600 of 2,131 GME day-files (all of 2018–2019) |
| 345 clips | corrected re-scan, recorded in the Hunt-13 ERRATA | expiry/expiration fix applied; 2018–2019 recovered |
| **406 clips → 278 events** | current, `rebuild_fig01_married_census.py` | second landmine found and fixed: some files encode the option right as `CALL`/`PUT`, and at least one mixes those with `C`/`P` inside the same file, so a `right == "CALL"` filter dropped pairs without erroring |

The 345-clip set is a strict subset of the current 406 with zero clips lost, and the coverage assertion in the rebuild now fails closed rather than skipping an unreadable day.

**Figures.** `fig01_married_census`, `fig02_implied_borrow`, `fig03_frozen_puts`, `fig04_flyway` (`make_tw_flyway.py`).

## Q3 — the bespoke chain (FLEX)

**Design.** Everything in Q1–Q2 comes off the listed chain, which is the only chain any vendor feed carries. Q3 reads the other one. OCC publishes daily FLEX volume-and-open-interest reports as fixed-width text; FLEX series are never disseminated to OPRA, so they are absent from every per-contract feed in this project. Pull with `tools/get_data.py flex` (§7 of `DATA_SOURCES.md`), parse the fixed-width layout, and census GME's book: total open interest, matched call/put pairs, exercise style, and strike geometry against spot on each line's inception date. Four falsification tests, all runnable from the reports plus the listed OI store:

- **Conversion capacity and sign.** If OCC's FLEX→listed conversion were creating the Q4 off-tape open interest, FLEX would have to drain by that amount and would fall on days listed OI rose. Both fail.
- **At-the-money geometry (A1/A2).** Median |ln(K/S)| at inception against a null that keeps the same strikes and dates but shuffles their pairing (10,000 draws), plus a newborn-vs-incumbent comparison on the same date so a drifting stock cannot manufacture the result.
- **Exact-size handoffs (the roll test).** Pair-lines linked by identical size across sequential expirations, against a size-shuffle null, swept across `LINK_DAYS ∈ {0,7,14,21,30,45}`.
- **Cross-root context.** The same census across every root in the file, so "this name has FLEX" is not mistaken for a finding.

**Key numbers.** GME has **zero** FLEX open interest before 2025-01-06 (not an archive gap: zero GME rows in all 205 retained 2024 reports), so the book is nineteen months old. Largest call position open in the name is off-chain: **100,000 contracts, $32, expiring Thursday 2028-01-20** — twice the largest listed call line as of 2026-07-24 (49,883 at $50, Jan-2027), though *not* the largest the listed chain has ever carried (180,319 at $127.50 in January 2024) nor far clear of the 2026 listed peak (99,503 at $30 on 2026-05-06). The Thursday expiry has no listed counterpart, so nothing can net or convert against it. **24 matched call/put pairs, split 24 European to 0 American**, against the single American $32 call, which moved twice in its life (80,000 → 100,000, January 2026) and has been static for seven months across 137 of 160 report-days. Median strike **3.6% from spot at inception** vs 13.7% null (p = 0.0001); newborn-vs-incumbent p = 0.0088. Roll test at the publish specification (`LINK_DAYS=0`, the suspect $31.02 adjacent-expiry pair dropped before the null is built): **2 handoffs, p = 0.0005**. Conversion excluded on capacity (FLEX peaks 150,766 vs 670,322 of Q4 creation) and on sign (rank correlation **+0.038, p = 0.65, n = 145**). The European pair book peaked at 47,536 in February 2026 and collapsed 95% to 2,495 by late July, while the American line never moved.

**Landmines this section cost, all of which will bite a replicator.** (1) OCC answers **HTTP 200 with an error sentence in the body** both for dates outside its ~22-month retention and for a malformed `reportDate` — see `DATA_SOURCES.md` §7; a status-code-only fetcher archives the error string and the whole store then reads as "this name has no FLEX". (2) Match the root **exactly** after stripping the leading style byte: a substring test admits **GMED** (Globus Medical), which is what produced an early and entirely false "GME had FLEX in 2024" result. (3) **GME1** is not another company — it is these same lines re-rooted by the October 2025 warrant adjustment (GME through 2025-10-02, GME1 from 2025-10-03, clean break). Grouping by `[symbol, expiry, strike]` double-counts four lines and inflates the pair census 24 → 28; worse, an adjusted-root contract's strike is not commensurable with spot, so it must be excluded from the geometry tests while being *kept* for capacity totals. Both scripts filter `symbol == "GME"` and say what they dropped.

**Figures.** None. Q3 is the one section that carries no figure; every number in it is recoverable from the OCC reports plus the listed OI store.

## Q4 — the silent ledger

**Design.** Compare daily open-interest changes per line against all attributable prints on any exchange for that line. Classify OI that appears with no trades behind it. Kill-tests run before accepting it: thin-data-day correlation (none), full schema rebuild (twice), exclusion of backfills, restatements, and corporate-action adjustments one by one. Sharpening tests, each frozen before compute: a coverage-matched era null for series-listing coupling (2,000 draws — the births land on listing days at exactly their coverage share, so the channel books into lines that already exist), a warrant-adjustment rebooking check (excluded), and exercise exclusion verified on both rights. Growth tested for attention-independence against attention proxies.

**Key numbers.** 670,322 contracts across 817 days; 6.3× the rate of attributable flow (12.6× in the deepest corner); 99.3% in far-dated monthly lines; accumulation fastest in the quietest weeks; the surviving classification is transfer-and-rebooking-class settlement bookkeeping.

**Figures.** `fig05_titer_trajectory` (`make_fig05_titer.py`, `make_tw_titer.py`).

## Q5 — the convert shadow

**Design.** First-appearance census over the far-dated book: for every new expiration, record the lines and the open interest present at first sight. Test the December 17, 2027 birth against the base rate of far-dated lines carrying positions at birth. Track the $5 put line daily against the convert calendar (pricing and closing days, verified from GameStop's press releases and EDGAR filings; the calendar is documented in `DATA_SOURCES.md` §5).

**Key numbers.** 34,083 contracts resting in 18 tracked lines (11 calls $10–$55, 7 puts $3–$35) on the 2025-03-28 snapshot, which records the 2025-03-27 session, the first pricing day; 93% of that seed in the $5 put (31,721); the $32 call opening at 3; the largest first-sight day of the 91 E4 mass-days at 4.3× the runner-up (2025-05-27); the $5 put flat at 43,428 into June, then +19,131 on the second pricing day and a further step on the June 17 close; 193,804 of the line's lifetime contracts arriving through the silent channel.

*A note on populations, since the counts differ by definition and this tripped up one review pass:* the 18 lines and 34,083 contracts are the frozen hunt's **tracked** set (`convert_cluster_typing_2026-07-24/data/cluster_wm_lines.csv`, `first_oi`). Counting every line in the raw OI store with any open interest that morning instead gives 33 lines and 34,194 contracts, the extra 15 lines carrying 111 contracts between them. Both are correct about different populations; the article quotes the tracked set, and the "4.3×" and "3 of 91" figures likewise use the hunt's E4 mass-day population, not a raw-store scan. Anyone re-deriving these from the store alone will land on the larger numbers and should not read that as a discrepancy.

**Figures.** `fig16_convert_shadow` (`make_fig16_convert_shadow.py`).

## Q6 — the $32 precursor

**Design.** Print-level anatomy of the December 2027 LEAPS $32 call around 2025-08-06 and 2025-08-14: count prints in the line on the build days, compare total strike volume to the OI build, and rank the loading at $32 against 16 tested strikes over the same window. Fingerprint checks against the financing program (married-pair structure, put-leg behavior). Reset audit: track every strike's survival through the OCC's chain-wide contract adjustment on the warrant's 2025-10-07 ex-date, and whether the precursor line re-formed.

**Key numbers.** 4,376 and 3,769 contracts appearing off-tape (OI 1,048 → 5,320 → 9,139) with zero prints in the line on those days and total strike volume under a tenth of the build; top loading of all 16 strikes tested; post-reset, the precursor line died (9,191 → 0 → ~600) while a new $32 wall grew in fresh paper.

**Figures.** `fig14_precursor_births`, `fig15_precursor_fate` (`make_tw_precursor.py`).

## Q7 — the moon tickets

**Design.** Species classifier over the trades hive: 1-contract, $10-wide, deep-OTM call verticals, ~91 days out, ~$0.11 premium, opened before 10 a.m. and closed intraday. Census the species over its lifetime; date each trait (lot discipline, entry clock, exit clock) by when it locks in.

**Key numbers.** 110,332 tickets; 127,875 contracts; $1.86M premium; 98.8% single-lot; shape first appears 2024-05-16; the 1-lot rule locks June 2025, the pre-10am clock March 2026, the exit drifting to noon; last ticket 2026-06-24, followed by seventeen straight silent sessions.

**Figures.** `fig06_moon_census`, `fig07_trait_assembly`.

## Q8 — the $50 machine

**Design.** Five-year census of the $50 strike (post-split basis, including its $200 pre-split birth). Detect position-scale "lives" (cohorts), then adjudicate roll vs reincarnate: measure what fraction of dying OI reappears in the next expiration and whether cross-expiry switching exceeds chance. Track one cohort's premium farmed vs adverse revaluation. Check for hedges on the public swap tape over its full retention window.

**Key numbers.** Born 2021-01-27 at the $200 strike, zero → 33,026 contracts overnight (132,104 post-split); occupied 1,359 of 1,359 days since (low 977, peak 121,993); 173 lives; under 21% of dying OI reappears next line, cross-expiry switching below chance; of 40 cohorts dying at ≥10,000 contracts, 35 reincarnated, 1 rolled, 1 rebuilt slowly; $986.5k premium farmed over 64 days vs $842.5k adverse revaluation on the 4 worst days (~1× coverage); 367 swap-tape days checked, nothing at its scale.

**Figures.** `fig09_keeper_roll_or_die`, `fig10_keeper_economics`, `fig13_reincarnation_ladder` (`make_fig13_reincarnation_ladder.py`).

## Q9 — the $45 hole

**Design.** Resting-OI and traded-flow censuses by strike between the two crowds. Test the hole against the smooth moneyness downtrend by extrapolating the 30–35–40 trend into $45 and $50, per era (pre-2021, post-squeeze, post-reset).

**Key numbers.** $45 rests at 2,569 contracts vs $40's 23.8k and $50's 63.9k (~15× emptier than chance for a round strike); the trend extrapolation leaves $45 3.6× short and misses $50 by 15.7× the other way; pre-squeeze, the same trend explained $45 at 0.98×; the hole re-dug itself at the October reset.

**Figures.** `fig11_two_crowds`, `tw_hole_trend` (`make_tw_hole_trend.py`).

## Q10 — the jitter engine

**Design.** Quote-event analysis on dead strikes: size-change and venue-rotation cadence, tested for clock structure (none; mean-reverting size randomizer) and for stimulus response, measuring latency from a real print at $50 to display-size reshuffling versus price re-marking. Cross-name check on AMC's dead strikes.

**Key numbers.** Size reshuffle within 1 second of a print (91% within 2); price re-mark ~73 seconds; same engine family on AMC with different settings.

**Figures.** `fig08_jitter_latency`.

## Q11 — the dead channels, and the one live signal

**Design.** Each candidate price-pushing channel (gamma/vanna/charm hedging flow, strike magnets, pinning-as-weapon, IV suppression by the $50 writer, baited flow herding the chasers) was given its own pre-registered test against a fair null — phase/IAAFT surrogates, persistence nulls, and look-elsewhere correction sized to the search actually run. All failed; the aggressive-flow response test additionally shows the crowd fades rather than chases. The surviving signal: OI-writing velocity vs forward implied volatility and option volume at 1–4 week horizons, tested per era and held out of sample before being promoted to a standing weekly forward scorer.

**Key numbers.** Every mechanical channel dead against its frozen null. The OI-velocity signal produced four starred cells in the rate census (forward ΔIV and Δvolume at 5d and 21d), and a follow-up mean-reversion control retired half of them. Run `oi_velocity_fwd_2026-07-22/code/iv_confound_test.py`; results archived in that folder's `CONFOUND_FINDINGS.txt`.

The control residualises velocity and each forward target on the target's own current level and its trailing 21-session path (Spearman partial correlation), because velocity tracks the current IV level at +0.18 and the current volume level at +0.38 while both levels predict their own forward decline at −0.22 to −0.39.

| Cell | raw ρ | partial ρ (level + path) | p | verdict |
|---|---|---|---|---|
| ΔIV 5d | −0.103 | −0.069 | 0.0008 | survives |
| ΔIV 21d | −0.113 | −0.068 | 0.0010 | survives |
| Δvolume 5d | −0.076 | +0.032 | 0.15 | **retired** |
| Δvolume 21d | −0.134 | +0.014 | 0.53 | **retired** |

Post-2021 the IV legs barely attenuate (raw −0.104 / −0.125 versus partial −0.106 / −0.122, both p ≤ 0.0001), so the surviving half is not an artifact of the pre-squeeze era. The volume legs fail in that subsample too (+0.015, −0.005). The forward scorer should carry the two IV predictions only.

**On reading fig12.** The census produced seven starred cells across two rows, where a star means the cell beat the shuffle and common-clock nulls and survived BH FDR at q = 0.10. Four belong to `R2_oi_velocity` (the only rate with `visible=True` that passes) and three to `R7_titer`, which carries `visible=False` because it is the off-tape channel from Q4 rather than anything on the tape; two of the titer's three are forward ΔOI cells, which are near-mechanical given that the titer is itself off-tape ΔOI. The figure is deliberately **not** regenerated after the confound control: it is the frozen census, and the two retired volume cells are documented in the table above and in the article's caption rather than edited out of the image.

**Figures.** `fig12_rate_census`.

## Q12 — the standing watches, and their commitments

Four watches score the article's falsification events on fixed schedules: a weeknight scanner for a third ~10,000-lot married unit at $40 or $45 in the 2026-12-18 / 2027-01-15 expiries (same matcher as the Q1 census; flag at ≥1,000, prominent at ≥5,000; detector validated against a planted positive control), a Saturday scorer on the $32 warrant wall into the 2026-10-30 expiry, an earnings-coupling check on the silent ledger the day after each print, and the weekly OI-velocity scorer.

**Commitments.** The watch and test designs were frozen and sha256-pinned before computation. The hashes below are published here as commitments; each pinned document can be disclosed later and verified against its hash:

| Frozen document | sha256 |
|---|---|
| Forward-observatory charter (Spec 21) | `3740e691a7340eb3a0966d15e1a854ce0c9a938b0c9f7f8cc269c8bd41c2381d` |
| Set-dynamics spec governing the silent-ledger tests (Spec 16) | `64781ac8c3813db004095ee652a34e94b43f7c9c021ffabb591c29dec543276f` |
| Swap-leg coupling spec (Spec 20) | `d1c7acd453f8c7cbf38b7dff30e8eab83fbace8a46baaef484aba7074ea396e8` |
| $32-precursor test config | `d812cdcc3a8ad58d92f55087e4c5296bc4f69c1a2d81c5808bbd6b5f096df9b9` |
| Married-band adjudication config | `7b2735df67e9a7cbee3ffbc1957746101a21894ae34bd90bbf39d087b55c81b9` |
| Silent-channel mechanism config | `68fb8509d404f737` |
