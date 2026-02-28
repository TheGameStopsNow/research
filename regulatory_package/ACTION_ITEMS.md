# Action Items for Regulators

Five ranked actions, each with the statutory basis, the body with authority to act, and the specific evidence supporting it.

---

## Action 1: Execute the FINRA CAT Queries *(Immediate, High-Impact)*

**Summary:** Run eight specific Consolidated Audit Trail queries that identify the Market Participant behind the documented algorithmic patterns.

**Authority:** SEC Division of Enforcement, FINRA Market Regulation, House Financial Services Committee (subpoena)

**Statutory Basis:** FINRA CAT NMS Plan; SEC Rule 613

**Evidence:** Paper II §4.9–4.12 (forensic signatures), Paper III §3.2 (query specifications), Paper VIII §2.4 (31-ticker DMA fingerprint)

**Why this is Action #1:** The entire attribution gap — *who* operates the algorithm — collapses with a single CAT query. The `[100, 102, 100]` jitter signature has a zero background rate across 2,038 trading days. If the MPID on the January 2021 sequence matches the MPID on the June 2024 sequence, one datum proves the same entity engineered both events across 3.5 years.

**See:** [SUBPOENA_QUERIES.md](SUBPOENA_QUERIES.md) for the eight ready-to-execute queries.

---

## Action 2: Investigate the T+45 Accommodation Window *(Medium-Term, Systemic)*

**Summary:** Conduct a formal investigation of the 15-node Failure Accommodation Waterfall that allows delivery failures to persist for 45 business days.

**Authority:** GAO (non-partisan), SEC Division of Trading and Markets, DTCC/NSCC

**Statutory Basis:** SEC Rule 204 (Reg SHO), Rule 15c3-1 (Net Capital), NSCC Rules 11, 18

**Evidence:** Paper V §3 (waterfall mapping), Paper V §5 (valve transfer), Paper IX §2 (T+1 migration to KOSS)

**Key findings for investigation:**
- 18.1× phantom OI enrichment at T+33, p < 0.0001
- Zero control-day activity vs. 240,880 contracts on settlement dates
- 89% valve transfer to opaque channels post-July 2022 splividend
- ~18% of free float (~69.4M share-equivalents) in settlement limbo

---

## Action 3: Reform CAT Error Penalties *(Legislative or SRO Action)*

**Summary:** Replace flat-fee CAT penalties with an escalating matrix tied to economic benefit of non-compliance.

**Authority:** FINRA (SRO authority, can amend without legislation), SEC (rulemaking)

**Statutory Basis:** FINRA Rule 6830; CAT NMS Plan §6.6

**Evidence:** Paper III §4.2 (fine analysis), FINRA AWC 2020067253501 ($1M / 42.2B events = $0.0000236/violation)

**Proposed structure:**
1. Penalties proportional to execution volume of unlinked trades
2. Penalties proportional to potential arbitrage yield during the blindness window
3. Mandatory escalation multipliers for repeat offenders
4. Elimination of the T+3 repair window for HFT entities

---

## Action 4: Require Settlement Transparency *(Legislative)*

**Summary:** Four targeted disclosure requirements to close documented opacity gaps.

**Authority:** SEC (rulemaking), Congress (legislation)

**Statutory Basis:** Exchange Act §§13, 17; Reg SHO Rule 204; Reg NMS Rule 613

**Evidence:** Paper V §5 (valve transfer), Paper IX §7 (cross-border asymmetry), Paper VIII §2.4 (DMA routing)

**Four provisions:**

| Provision | Current Gap | Fix |
|-----------|------------|-----|
| Daily gross FTD reporting | Biweekly, netted, 2-week lag | T+1 publication of daily gross figures |
| Intraday CAT linkage for HFT | T+3 repair window allows deliberate blindness | Same-day repair requirement |
| Synthetic price attestation | Dark pool settlements at detached prices unreported | Mandatory attestation |
| Cross-border fail visibility | No reporting when obligations export to EU CSDs | Mandatory CSD transfer reporting |

---

## Action 5: Accelerate Rule 10c-1a *(Regulatory Pressure)*

**Summary:** Reverse the compliance extension from March 2029 to the original April 2026 effective date.

**Authority:** SEC (can modify exemptive orders), Congress (hearing pressure)

**Statutory Basis:** Exchange Act §10(c); SEC Rule 10c-1a

**Evidence:** Paper VII §§3–4 (dark locate pipeline), Paper VIII §3.3 (FTD coupling diagnostic)

**Context:** Rule 10c-1a was adopted in response to January 2021. The industry successfully obtained an 8-year delay (2021→2029). During those eight years, the bilateral OTC stock lending pipeline remains invisible to public surveillance.

---

*Each action item is supported by the full evidence chain in [EVIDENCE_INDEX.md](EVIDENCE_INDEX.md).*
