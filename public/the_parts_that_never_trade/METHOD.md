# Method — the discipline behind every claim

The article's method note promises that every claim comes out of a dated, pre-registered test folder and that killed theories were killed by frozen nulls, not vibes. This file documents what that means operationally, so a replicator can hold the work to the same bar — or a higher one.

## 1. The instrument (PET)

PET treats the options chain as a patient under a tracer scan. The tracers are **signed premium flow**, **open-interest change**, and **theta uptake**; rendered across strike and time, the bright spots are where the chain is metabolically active. The scan is a *proposal generator only*. Nothing a scan surfaces is a finding until it survives the test pipeline below.

## 2. The bar a claim must clear

A correlation or structure is never a finding until it has:

1. **Beaten a fair null.** Fair means the null preserves the structure that would produce the pattern for boring reasons: phase-randomized / IAAFT surrogates for spectral claims, rotation and grid-preserving shuffles for calendar claims, persistence nulls for autocorrelated series (OI walls persist; any test that ignores this manufactures significance), share-conditioned and venue-conditioned backgrounds for print-pattern claims, Poisson/Monte Carlo birth nulls for cohort-clustering claims.
2. **Held out-of-sample.** Sign and magnitude re-checked on held-out names, held-out eras, or forward data the test never touched.
3. **Survived multiplicity.** Corrected for the size of the search actually performed (look-elsewhere), not the search reported.

Additionally, every detector is **ground-truth-validated** before it is trusted: it must fire on a planted true signal and stay silent on noise. A detector that cannot pass a planted-signal test disqualifies its own findings.

## 3. Pre-registration mechanics

- Test designs are frozen as append-only documents with **sha256 sidecars** written before computation runs; the commitments behind the article's standing forward watches are published in `QUESTION_MAP.md`.
- Each test folder freezes its own `config.py` (parameters, windows, strike populations, null constructions) and records its hash in `config_sha.txt` **before analysis code runs**. A config changed after freezing invalidates the run.
- `input_manifest.txt` records the sha256 of every input the tests consumed, so a replicator can confirm they are testing against the same derived inputs.
- Decision paths are frozen with the spec: which statistics gate which verdicts, and what happens on each branch. **No fourth door** — if the frozen branches don't cover what the data did, the tension is stated as a contradiction, not resolved ad hoc.

## 4. Verdict taxonomy

Every tested claim lands in one of three states, and the state travels with it everywhere it is cited:

- **BANKED** — cleared the full bar above, or is a solid descriptive fact.
- **OPEN** — untested or under-powered frontier; may appear in prose only flagged as hypothesis.
- **DEAD** — an apparent effect that collapsed under a fair null, out-of-sample check, or multiplicity correction. Dead claims are kept on file as graveyards so nobody re-derives them.

The article's Q11 is the graveyard tour: every price-pushing channel (gamma/vanna/charm flows, magnets, pinning-as-weapon, IV suppression, baited flow) is DEAD under this taxonomy. The one survivor (OI-writing velocity → forward IV/volume decline) is BANKED retrospectively and now lives under forward scoring.

## 5. The forward observatory (SPEC 21)

Retrospective discipline, however honest, is simulation-of-prospectivity: nature had already written the answer. The forward observatory makes claims prospective in wall-clock time:

- Predictions are **time-stamped and hash-pinned before the outcome exists**.
- Each stream carries a frozen **baseline** (the dumb model to beat), a **kill condition** (what result retires the claim), and an **abstention rule** (when the stream may decline to predict).
- Grading uses **proper scoring rules**, and P&L is kept out of the verification loop entirely: a scoring rule that doubles as a trading rule is compromised as evidence.

The article's Q12 watches (the married-unit watch, the $32 wall Saturday scorer, the earnings-coupling test, the OI-velocity weekly scorer) are all residents of this framework.

## 6. The honest ceiling and the no-actor law

The public tape carries venue and condition codes but **no participant identity** — no CAT, no MPIDs, no open/close flags. Two consequences are enforced everywhere:

1. Positives are described as **populations and mechanisms**, never actors. The strongest claim available is "directed, uneconomic structure that beats mundane controls."
2. Where the article touches events involving real people (Q7's origin, Q11's attention events), it reports dates and public facts only and explicitly declines to infer intent. The tape answers "what happened on the ledger"; it is structurally silent on "who" and "why," and the writing must not pretend otherwise.

## 7. Data hygiene rules a replicator must keep

- **Fail closed.** A loader that can silently skip days is disqualified (see `tools/hive_reader.py` and its coverage assertion; the 507-day near-miss is documented in its docstring).
- **No synthetic fills.** Gaps are never interpolated; `polygon_second_synthetic` is excluded program-wide.
- **Declare coverage.** Every test states its data window and any known store boundary inside it (e.g., a hive top-up boundary becomes a declared fold boundary, not an invisible seam).
- **Manifests everywhere.** Store writes are sha256-logged (`_MANIFEST.jsonl`); failed pulls are sidecar-logged (`_FAILS.txt`) and retried, never papered over.
