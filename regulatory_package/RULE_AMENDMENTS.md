# Proposed Rule Amendments

Seven targeted amendments to existing SEC, FINRA, and NSCC rules, each addressing a specific vulnerability documented in the research. All amendments cite existing statutory authority — none require new legislation unless otherwise noted.

**Source:** Paper III, §4

---

## Amendment 1: Condition Code Reform

**Target Rule:** FINRA Rule 6380A (OTC Reporting Facility) / FINRA Rule 7440 (Trade Reporting)

**Current Problem:** Condition Code fragmentation across reporting venues allows a single trade to appear as hedging activity on one tape and settlement accommodation on another. The same $34M conversion produces Condition Code 12 (Form T, after-hours) on the equity leg while the options leg carries no special condition code.

**Proposed Change:**
- Require a **unified composite condition code** for multi-leg trades and conversions that links all legs (options + equity) to a common settlement instruction
- Mandate that dark pool and OTC equity legs of conversion trades carry a new condition code identifying them as "conversion-linked equity delivery"
- Require real-time reporting of the composite code, not just T+1 trade report

**Evidence:** Paper II §4.12, Paper III §4.1

---

## Amendment 2: Cross-Asset Sweep Detection

**Target Rule:** Reg NMS Rule 611 (Order Protection Rule) / SEC Rule 15c3-5 (Market Access)

**Current Problem:** Multi-exchange sweep orders that extract >5× the NBBO depth in under 100ms are permitted as standard market-making activity. The research documents a single sweep extracting 7.4× NBBO liquidity across 13+ exchanges in 34 milliseconds — functionally indistinguishable from a flash crash trigger.

**Proposed Change:**
- Require a **real-time sweep flag** when a single MPID executes across 5+ exchanges within 100ms
- Mandate that sweep orders extracting >3× aggregate NBBO depth trigger an automatic surveillance review
- Require the originating MPID to provide a **bona fide purpose attestation** within 24 hours for any sweep flagged by the threshold

**Evidence:** Paper II §4.11, Paper III §4.3

---

## Amendment 3: Pre-Trade Risk Control Enhancement

**Target Rule:** SEC Rule 15c3-5 (Market Access Rule)

**Current Problem:** Dedicated Direct Market Access (DMA) routing channels bypass standard pre-trade risk controls. The research identifies a specific routing fingerprint — characterized by `[100, 102, 100]` lot-size jitter — that appears on exactly 31 securities, all routed through DMA channels that are exempt from the broker-dealer's standard pre-trade risk checks.

**Proposed Change:**
- Require that **all DMA channels** — including dedicated prime broker routes — execute through the same pre-trade risk controls as standard order flow
- Mandate that broker-dealers report the number and percentage of orders routed through DMA channels that bypass standard risk checks
- Require annual certification that DMA routing does not create a separate risk control tier

**Evidence:** Paper VIII §2.4, Paper III §4.4

---

## Amendment 4: Settlement Reform — T+3 CAT Repair Window

**Target Rule:** CAT NMS Plan §6.6 (Error Correction)

**Current Problem:** The T+3 repair window allows firms to submit CAT records without inter-firm linkage data in real-time, blinding surveillance during the execution window, and then retroactively repair the records within three business days. For HFT entities executing thousands of trades per day, this creates a systematic opacity gap. The $1M fine for 42.2 billion errors (FINRA AWC 2020067253501) demonstrates the penalty is not a deterrent.

**Proposed Change:**
- **Eliminate the T+3 repair window for entities exceeding 10,000 daily order events**
- Require same-day linkage for all order events from HFT-designated entities
- Implement an **escalating penalty matrix:**
  - Base: $1 per unlinked event (vs. current ~$0.00002)
  - 2× multiplier after 1M cumulative unlinked events in a calendar year
  - 10× multiplier after 10M cumulative events
  - Mandatory SEC referral after 100M events
- Cap the repair window at T+1 for all other entities

**Evidence:** Paper III §4.2, FINRA AWC 2020067253501

---

## Amendment 5: Reg SHO Rule 204 — Synthetic Close-Out Prevention

**Target Rule:** SEC Rule 204 (Reg SHO Close-Out Requirements)

**Current Problem:** The research documents a mechanism where conversion trades (buy call + sell put = synthetic long) reset the Rule 204 close-out clock without effecting actual delivery. The enrichment pattern — 18.1× at T+33, zero on control days — is the signature of this synthetic reset cycle.

**Proposed Change:**
- Require that **close-out deliveries be attested as involving actual share delivery**, not synthetic equivalents
- Define a clear standard for when an options conversion constitutes a "bona fide" close-out vs. a clock reset
- Mandate DTCC reporting of how many Rule 204 close-outs are satisfied via conversion trades vs. market purchases
- Apply a **5-day cooling period** before a close-out via conversion can reset the Rule 204 clock

**Evidence:** Paper V §3.3, Paper V §6.1, Paper VIII §3.3

---

## Amendment 6: Cross-Border Fail Reporting

**Target Rule:** SEC Rule 204 (Reg SHO) / New Rule

**Current Problem:** There is no reporting requirement when a U.S. settlement obligation is transferred to a foreign CSD for resolution. The 5,714:1 cost asymmetry between CSDR (€1,140/35 days ≈ $1,750) and Reg SHO (~$10M/day) creates a rational incentive to export failures. EU equity fail rates spike selectively during U.S. stress events, consistent with failure export.

**Proposed Change:**
- Require U.S. broker-dealers to **report any transfer of settlement obligations to non-U.S. CSDs** to the SEC within T+1
- Mandate that transferred obligations remain subject to Reg SHO penalties and timelines regardless of the receiving CSD's penalty regime
- Require quarterly disclosure of aggregate cross-border obligation transfers by security class

**Evidence:** Paper IX §7.1–7.3

---

## Amendment 7: Cancelled CUSIP Obligation Resolution

**Target Rule:** NSCC Rule 11 (Settlement) / DTCC Procedure — New Requirement

**Current Problem:** When a stock is delisted and its CUSIP cancelled, the system has no mechanism to resolve outstanding delivery obligations. BBBY shows 31 unique FTD values actively cycling 824 days after cancellation — the obligations persist indefinitely with no resolution path. This creates a permanent "zombie" in the Obligation Warehouse.

**Proposed Change:**
- Require DTCC/NSCC to **automatically novate and extinguish all delivery obligations** within 90 business days of CUSIP cancellation
- Mandate that any counterparty holding an open obligation on a cancelled CUSIP either:
  - (a) Settle in cash at last closing price, or
  - (b) Submit a formal exemption request to the SEC explaining why the obligation cannot be resolved
- Publish quarterly reports of all outstanding obligations on cancelled CUSIPs

**Evidence:** Paper IX §5.2

---

## Summary Table

| # | Target | Current Gap | Fix | Authority |
|:-:|--------|------------|-----|-----------|
| 1 | FINRA 6380A/7440 | Multi-leg trades fragment across tapes | Unified composite condition code | FINRA (SRO) |
| 2 | Reg NMS 611 / Rule 15c3-5 | No sweep detection threshold | Auto-flag at >3× NBBO depth in <100ms | SEC |
| 3 | Rule 15c3-5 | DMA bypasses pre-trade controls | Apply same controls to all channels | SEC |
| 4 | CAT NMS Plan §6.6 | T+3 repair window enables opacity | Eliminate for HFT; escalating penalties | FINRA/SEC |
| 5 | Reg SHO Rule 204 | Conversions reset close-out clock | Require actual delivery attestation | SEC |
| 6 | Reg SHO Rule 204 | No cross-border fail visibility | Mandatory transfer reporting | SEC/Congress |
| 7 | NSCC Rule 11 | No cancelled-CUSIP resolution | 90-day auto-novation | DTCC/SEC |

---

*See [ACTION_ITEMS.md](ACTION_ITEMS.md) for the five high-priority actions that incorporate these amendments.*
