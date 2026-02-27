# Citations & References — Forensic Analysis Bundle (Rounds 1–16, Posts 03–04)

**Last Updated:** February 22, 2026

---

## Regulatory Filings (SEC EDGAR)

### X-17A-5 Annual Audited Financial Statements
1. **Citadel Securities LLC** — Annual Report (X-17A-5), CIK 0001146184.
   - FY2020: Period ending December 31, 2020. Auditor: PricewaterhouseCoopers LLP, Chicago.
   - FY2021: Period ending December 31, 2021. Auditor: PwC.
   - FY2022: Period ending December 31, 2022. Auditor: PwC.
   - FY2023: Period ending December 31, 2023. Auditor: PwC. *First filing with Miami, FL principal address.*
   - FY2024: Period ending December 31, 2024. *(Scanned PDF; limited programmatic extraction.)*
   - URL: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001146184&type=X-17A-5

2. **Citadel Securities Institutional LLC** — Annual Report (X-17A-5).
   - FY2024: Period ending December 31, 2024. Total assets: $380M. Miami, FL.
   - URL: https://www.citadelsecurities.com/disclosures/

3. **Citadel Securities Swap Dealer LLC** — Annual Report (X-17A-5).
   - FY2024: Period ending December 31, 2024. Total assets: $3,388M. Miami, FL.
   - URL: https://www.citadelsecurities.com/disclosures/

4. **Palafox Trading LLC** (G1 Execution Services) — Annual Report (X-17A-5).
   - FY2021: Total assets: $16.4B. 
   - FY2022: Total assets: $29.7B. Unsettled forward repos: $14.1B/$14.1B.
   - FY2023: Total assets: $93M (−99.7%). Unsettled: $56.9B/$21.3B.
   - FY2024: Scanned PDF.
   - URL: https://www.citadelsecurities.com/disclosures/

5. **Virtu Americas LLC** — Annual Report (X-17A-5), CIK 0001569391.
   - FY2020–FY2024 (XML format filings archived).
   - URL: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001569391&type=X-17A-5

### N-CSR (Certified Shareholder Reports)
6. **AETOS Capital Group LLC** — N-CSR, CIK 0001169578 / 0001169583.
   - Multi-manager hedge fund allocator. "Margin call" references confirmed as standard risk disclosure language.
   - URL: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001169578&type=N-CSR

### 10-12G (Registration Statements)
7. **Third Point Investors Inc.** — Form 10-12G, CIK 0002025369.
   - Business Development Company (BDC) registration. "Orderly wind down" language is standard boilerplate risk disclosure for new fund launches, not indicative of distress.
   - Filed: 2024. URL: EDGAR full-text search for CIK 2025369.

### 13F-HR (Institutional Holdings)
8. **Citadel Advisors LLC** — 13F-HR quarterly holdings.
   - Includes GME, XRT positions for cross-referencing with dark pool flows.
   - URL: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001423053&type=13F

9. **Virtu Financial Inc.** — 13F-HR quarterly holdings.
   - CIK: 0001569391.

10. **Jane Street Group LLC** — 13F-HR quarterly holdings.
    - CIK: 0001595088.

### Rule 606 (Order Routing Reports)
11. **Interactive Brokers Group** — Rule 606(a) quarterly routing reports.
    - IB LITE orders → Citadel Securities, Jane Street Capital as primary venues.
    - URL: https://www.interactivebrokers.com/en/accounts/orderRoutingStatistics.php

12. **Robinhood Markets Inc.** — Rule 606(a) quarterly routing reports.
    - ~80% revenue from PFOF (Q1 2021; ~60-70% by 2024).
    - URL: https://robinhood.com/us/en/about/legal/ (regulatory disclosures)

---

## Market Data Sources

### SEC Public Data
13. **SEC FTD Data** — Failure-to-Deliver reports by CUSIP.
    - Format: TXT files with daily FTD quantities by CUSIP.
    - Used in: R11, R12 (V1 — XRT/KOSS anti-correlation), R14.
    - URL: https://www.sec.gov/data-research/sec-markets-data/fails-deliver-data

### FINRA Public Data
14. **FINRA ATS Transparency Data** — Weekly ATS volume by firm (MPID).
    - Used in: R11, R12 (V2, V2c, V2d — UBS/CS unmasking).
    - URL: https://otctransparency.finra.org/otctransparency/OtcIssueData

15. **FINRA Non-ATS Transparency API** — Weekly internalizer volume by firm.
    - Requires OAuth2 authentication (API key).
    - Dataset: `weeklySummary`, summary type: `OTC_W_SMBL_FIRM`.
    - Used in: R12 (V2b — 24-firm unmasking of 263M shares).

### CCP / Clearing Data
16. **NSCC Quantitative Disclosures (PQD)** — Principles for Financial Market Infrastructures.
    - Q2 2024 peak initial margin (PQD 6.1.1): $1.162B.
    - URL: https://www.dtcc.com/legal/policy-and-compliance

17. **OCC Quantitative Disclosures (PQD)** — Risk management reports.
    - Peak initial margin (Q2 2024): $107.59B.
    - URL: https://www.theocc.com/risk-management/pfmi-disclosures

18. **DTCC DDR (Swap Data Repository)** — Security-Based Swap dissemination.
    - **BLOCKED**: Portal retains only ~1 year of data. May 2024 data purged.
    - URL: https://pddata.dtcc.com/gtr/tracker.do

### Commercial Data (Subscription)
19. **Polygon.io** — Tick-level equity trades.
    - Fields: price, size, exchange, SIP conditions, timestamp (ns).
    - Used in: R1–R10 (all tape forensics).

20. **ThetaData** — Tick-level options trades.
    - Fields: strike, right, price, size, exchange, timestamp.
    - Used in: R7 (CGD), R12 (V4 — settlement predictor).

### Weather / Atmospheric Data
21. **Open-Meteo Historical Weather API** — Hourly precipitation, temperature, cloud cover.
    - Used in: Paper IV §3.8 (corridor storm identification, NBBO spread widening panel).
    - URL: https://archive-api.open-meteo.com/v1/archive

22. **NOAA NCEI Storm Events Database** — County-level severe weather event records.
    - Files: `StormEvents_details-ftp_v1.0_d2021_c20250520.csv.gz` (61,389 events), `StormEvents_details-ftp_v1.0_d2022_c20250721.csv.gz`.
    - Used in: Paper IV §3.8 (corridor storm date selection).
    - URL: https://www.ncdc.noaa.gov/stormevents/

---

## Legal & Regulatory Framework Citations

### Florida Jurisdiction
23. **Florida Constitution, Article VII, §5** — Prohibition on state personal income tax.
    - Estimated annual savings for Citadel: $450M+ vs New York (13.3% + 3.876% NYC).

24. **Florida Constitution, Article X, §4** — Homestead exemption.
    - Unlimited value protection for primary residence. Up to ½ acre within municipalities (160 acres outside).

25. **Florida Statute §689.115** — Tenancy by the entireties.
    - Extends to all personal property (stocks, bank accounts) held jointly by married couples. Protection against individual spousal creditors.

26. **Florida Uniform Commercial Code, Chapter 679** — Secured transactions.
    - UCC Article 9 filing jurisdiction = debtor's state of organization.
    - For securities: perfection by control (§8-106) supersedes filing.

27. **SEC Rule 15c3-1** (Net Capital Rule) — Uniform Net Capital Rule.
    - Federal standard; unchanged by state of domicile.
    - Citadel elections: alternative method, maintaining excess above $1.5M minimum.

28. **SEC Rule 17a-5** — Financial reporting for broker-dealers.
    - Annual audited financial statements + supplemental schedules (FOCUS report).

---

## Regulatory / Infrastructure Citations (Paper IV)

29. **FCC Universal Licensing System** — Pierce Broadband LLC (McKay Brothers) microwave licenses.
    - 85+ towers operating at 10–11 GHz, CME Aurora to NYSE Mahwah route.
    - Used in: Paper IV §3 (microwave corridor identification).
    - URL: https://www.fcc.gov/wireless/universal-licensing-system

30. **DTCC Important Notices — RECAPS Schedule.**
    - Annual settlement calendar: recurring end-of-cycle mark-to-market events.
    - A# 9079 (2025 schedule, Nov 12, 2024); A# 9676 (2026 schedule, Nov 13, 2025).
    - Used in: Paper IV §4 (RECAPS–GME event coincidence analysis).
    - URL: https://www.dtcc.com/legal/important-notices

31. **FRED Series DEXJPUS** — Japan/U.S. Foreign Exchange Rate (daily).
    - Board of Governors of the Federal Reserve System.
    - Used in: Paper IV §5 (yen carry trade correlation).
    - URL: https://fred.stlouisfed.org/series/DEXJPUS

32. **SEC FOIA Request Logs** — Monthly CSV files, December 2019 – January 2026.
    - Used in: Paper IV §6 (regulatory awareness gap analysis).
    - URL: https://www.sec.gov/foia-services/frequently-requested-documents/foia-logs

33. **Federal Reserve Board of Governors — Discount Window Lending Data.**
    - Q1 2021 transaction-level data.
    - Used in: Paper IV §6.2 (absence of upstream funding stress).
    - URL: https://www.federalreserve.gov/regreform/discount-window.htm

34. **CalPERS Annual Financial Reports** — FY2019–FY2023.
    - California Public Employees' Retirement System.
    - Used in: Paper IV §5.2 (institutional carry trade exposure).

35. **Citadel Securities / McKay Brothers** — "Citadel Securities Makes Minority Investment in McKay Brothers."
    - BusinessWire, November 12, 2024.
    - Used in: Paper IV §3.5 (infrastructure ownership attribution).

36. **U.S. Bankruptcy Court, District of New Jersey** — Case 23-13359-VFP.
    - Bed Bath & Beyond Inc. Chapter 11. Docket #2631 (DTC Position Report), Filed October 27, 2023.
    - Used in: Paper IV §2 (death-spiral convertible mechanics, Cede & Co. reconciliation).
    - URL: https://restructuring.ra.kroll.com/bbby

---

## Academic / Industry References

37. **PFMI Disclosure Framework** — Committee on Payments and Market Infrastructures (CPMI-IOSCO).
    - Framework for CCP quantitative disclosures used by NSCC, OCC, FICC.

38. **Beal Bank, S.S.B. v. Almand & Associates** — Florida Supreme Court, 780 So. 2d 45 (2001).
    - Established TBE protection for personal property (not just real estate) in Florida.

39. **In re Hurvitz** — Bankruptcy Court, 11th Circuit.
    - Confirmed bona fide Florida residency requirement for homestead exemption claims.

40. **Shkilko, A. & Sokolov, K. (2020).** "Every Cloud Has a Silver Lining: Fast Trading, Microwave Connectivity, and Trading Costs." *Journal of Finance*, 75(6), 2899–2927.
    - Used in: Paper IV §3.8 (cross-date matched design, adverse selection framework).

41. **Roll, R. (1984).** "A Simple Implicit Measure of the Effective Bid-Ask Spread in an Efficient Market." *Journal of Finance*, 39(4), 1127–1139.
    - Used in: Paper IV §3.8 (exchange-split DiD implied spread calculation).

42. **ITU-R P.838 (2005).** "Specific attenuation model for rain for use in prediction methods."
    - International Telecommunication Union. Governs 10 GHz rain fade threshold physics.
    - Used in: Paper IV §3.7, §3.8 (microwave rain fade/fiber failover model).

43. **Whewell, W. (1840).** *The Philosophy of the Inductive Sciences, Founded Upon Their History.* London: John W. Parker.
    - Origin of the Consilience Standard. Used in: Paper IV §1.

44. **Wilson, E.O. (1998).** *Consilience: The Unity of Knowledge.* New York: Alfred A. Knopf.
    - Modern formalization of the Consilience Standard. Used in: Paper IV §1.

45. **Nomura Holdings (2024).** "Yen Carry Trade Sizing and Risk." Q3 2024 Research Note.
    - Used in: Paper IV §5 (carry trade funding model).

---

## Data Files Generated (Phase 16)

| File | Description | Location |
|------|-------------|----------|
| `citadel_multiyear_final.json` | FY2020-2023 parsed balance sheet data | `results/` |
| `citadel_line_extraction.json` | Line-by-line keyword extraction (all entities) | `results/` |
| `multi_year_extraction.json` | Multi-entity multi-year extraction | `results/` |
| `pdf_diagnostics.json` | Text/scan detection for 22 PDFs | `results/` |
| `frontier1_ncsr_xrt_lending.json` | N-CSR XRT lending agent findings | `results/` |
| `frontier2_fails_charges.json` | X-17A-5 fails/charges data | `results/` |
| `frontier3_ib_606_venues.json` | IB 606 routing venue data | `results/` |
| `frontier4_entity_extraction.json` | Client hunt entity extraction | `results/` |
| `aetos_fund_filings.json` | AETOS N-CSR analysis | `results/` |

## Data Files Generated (Paper IV — Infrastructure & Macro)

| File | Description | Location |
|------|-------------|----------|
| `corridor_storms.json` | Storm events on CME–NYSE microwave corridor | `data/weather/` |
| `rigorous_controls_1ms.csv` | Empirical Shift Test results (1ms resolution) | `results/zombie_basket/` |
| `rigorous_controls_10ms.csv` | Empirical Shift Test results (10ms resolution) | `results/zombie_basket/` |
| `basket_correlation_results.csv` | Full basket correlation matrix | `results/zombie_basket/` |
| `zombie_basket_full_RTH.csv` | Regular Trading Hours zombie basket data | `results/zombie_basket/` |
| `Zombie_Basket_Analysis.md` | Analysis writeup | `results/zombie_basket/` |

---

## Post 03 — The Shadow Ledger (Citations 46–65)

### German Regulatory Filings

46. **Bundesanzeiger (Federal Gazette)** — CM-Equity AG Audited Financial Statements.
    - FY2020: Total assets €28.1M. FY2021: €32.7M.
    - German sovereign audit database; considered conclusive evidence in German courts.
    - Used in: Post 03, Part 1 §3 (balance sheet paradox).
    - URL: https://www.bundesanzeiger.de

47. **BaFin (Federal Financial Supervisory Authority)** — Public Enforcement Database.
    - Searched: CM-Equity AG, 2022–2025.
    - Result: Zero sanctions, zero license revocations, zero formal enforcement actions.
    - Used in: Post 03, Part 1 §5 (regulatory gap).
    - URL: https://www.bafin.de/EN/PublishingAffairs/ListsDataAndRegisters/listsdataandregisters_node_en.html

### FTX Bankruptcy Filings (Kroll)

48. **FTX Trading Ltd.** — Schedule of Assets and Liabilities (SOAL), Schedule A/B.
    - Case No. 22-11068-JTD (D. Del.).
    - Verified by Trustee John J. Ray III under 28 U.S.C. § 1746.
    - Used in: Post 03, Part 1 §4 (zero GME shares in FTX inventory).
    - URL: https://restructuring.ra.kroll.com/FTX/

49. **CM-Equity AG v. FTX Europe** — Proof of Claim.
    - Kroll Docket 11626-6: $65 million claim (U.S.) + Kroll Docket 11626-6: €68,544,156.16 (Switzerland).
    - Used in: Post 03, Part 1 §4 (Tokenized Stocks collateral claim).

50. **CM-Equity AG / FTX Settlement** — Kroll Docket 14301.
    - Settlement amount: $51,000,000. Resolved without litigation or discovery.
    - Used in: Post 03, Part 2 §3 (Diameter Capital claims purchase).

51. **Diameter Capital Partners LP** — FTX Bankruptcy Claims Purchase.
    - Distressed debt fund staffed by former Citadel portfolio managers.
    - Purchased significant FTX claims; gained standing to negotiate settlements.
    - Used in: Post 03, Part 2 §3.
    - Source: Kroll FTX restructuring filings; SEC EDGAR, Diameter Capital Partners LP Form ADV.

### FDIC / FFIEC Call Reports

52. **JPMorgan Chase Bank, N.A.** — FDIC Call Reports (FFIEC 031), CERT #628.
    - Schedule RC-L: Derivatives and Off-Balance-Sheet Items.
    - Q4 2020 → Q1 2021 derivative notional spike: +$6 trillion.
    - Used in: Post 03, Part 2 §1.
    - URL: https://api.fdic.gov
    - Script: `code/season2/ffiec_call_reports.py`

### SEC EDGAR — Additional Filings

53. **Citadel Advisors LLC** — Form ADV Part 1A, Item 7.B (Private Fund Reporting).
    - CIK search "Citadel Advisors." Annual updates 2020–2025.
    - Cayman Islands fund GAV growth: $59B (2020) → $113B (2025).
    - Used in: Post 03, Part 2 §4 (offshore fund growth).

54. **Cantor Fitzgerald & Co.** — X-17A-5 (FOCUS Report), CIK 0000017018.
    - Statement of Financial Condition, FY2024 (December 31, 2024).
    - Auditor: Deloitte & Touche LLP.
    - Total assets: $16.7B. Reverse repo: $6.9B. Treasuries owned: $4.4B. Pledged: $4.5B.
    - Used in: Post 03, Part 3 §1 (Ouroboros collateral machine).

55. **Cantor Fitzgerald, L.P.** — 13F-HR, CIK 0001024896.
    - Q1 2024 – Q4 2025 (10 quarters reviewed): zero Treasury ETF, zero Bitcoin ETF, zero MSTR.
    - Used in: Post 03, Part 3 §1.
    - Script: `code/season2/cantor_fitzgerald.py`

56. **Cantor Fitzgerald & Co.** — 13F-NT, CIK 0000017018.
    - Notice of Inability to File (claims <$100M in 13F-qualifying securities).
    - Used in: Post 03, Part 3 §1.

57. **Goldman Sachs Group Inc.** — 13F-HR, CIK 0000886982.
    - Q4 2025 (filed Feb 10, 2026): ~70 crypto-adjacent positions. ~$9–10B estimated exposure.
    - Includes: IBIT ($2.2B shares + $1.7B puts), MSTR ($1.6B), COIN ($580M), MARA ($380M), RIOT ($100M).
    - Used in: Post 03, Part 4 §2 (Goldman reflexivity trap).

58. **GameStop Corp.** — 8-K, CIK 0001326380.
    - Filed February 3, 2025: Bitcoin treasury reserve announcement (4,710 BTC, ~$513M).
    - Used in: Post 03, Part 4 §1.

### OFR / Repo Market Data

59. **OFR Short-Term Funding Monitor** — Repo market volume by channel.
    - GCF, DVP, and Tri-Party repo series, August 2024.
    - August 13, 2024: GCF repo spiked to $199.6B (+11.6% vs. monthly average).
    - Used in: Post 03, Part 3 §4 (Tether mint / GCF correlation).
    - URL: https://data.financialresearch.gov

### Blockchain / On-Chain Data

60. **Arkham Intelligence** — On-chain tracking, August 2024.
    - Jump Trading / Tai Mo Shan: $377M Ethereum liquidation sequence (Jul 24 – Aug 6, 2024).
    - Used in: Post 03, Part 3 §5 (crypto-yen bridge).

61. **Tether Operations Limited** — USDT minting events.
    - August 13, 2024: $1 billion USDT minted on Ethereum.
    - Used in: Post 03, Part 3 §4.

### UK Companies House

62. **Citadel Securities (Europe) Limited** — Charges Register, Company No. 05462867.
    - 8 Initial Margin Security Agreements filed Sep 2022 (UMR Phase 6).
    - Counterparties: JPMorgan, Goldman Sachs, BNP Paribas, Barclays, Morgan Stanley, UBS, Nomura, Bank of America.
    - Used in: Post 03, Part 2 §2.
    - URL: https://find-and-update.company-information.service.gov.uk/company/05462867/charges

### Cayman Islands / Offshore

63. **Cayman Islands Monetary Authority (CIMA)** — Regulated Entities Register.
    - Citadel Global Equities Fund Ltd., Citadel Multi-Strategy Equities Master Fund Ltd.
    - Used in: Post 03, Part 2 §4 (Citadel offshore fund enumeration).

### SEC Regulation

64. **Regulation SHO, Rule 203(b)(1)** — 17 CFR §242.203.
    - Locate requirement: broker-dealer must document source of borrowable shares before executing a short sale.
    - Used in: Post 03, Part 1 §1.
    - URL: https://www.ecfr.gov/current/title-17/chapter-II/part-242/subject-group-ECFR43c076a1f3e258f

### Pending FOIA Requests

65. **FOIA — SEC (SBSR Data).** Request filed for archived Security-Based Swap Reporting data, August 2024.
    - Response deadline: April 3, 2026.
    - Used in: Post 03, Part 4 §8.

66. **FOIA — CFTC (CME EFRP Volume).** Request filed for Exchange for Related Position volume data, CME Bitcoin Futures.
    - Used in: Post 03, Part 4 §8.

---

## Post 04 — The Trojan Horse (Citations 67–82)

### SEC EDGAR — BYON / tZERO Filings

67. **Beyond, Inc. (BYON)** — 10-K Annual Reports, CIK 0001130713.
    - FY2023, FY2024. tZERO ownership (55%), SPBD license approval, BBBY/buybuy BABY acquisitions.
    - Used in: Post 04, Part 1 §1 (corporate lineage); Part 2 §1 (ICE gatekeeper analysis).

68. **Beyond, Inc. (BYON)** — DEF 14A Proxy Statements.
    - 2024, 2025. Board composition tracking (ICE-affiliated director departures).
    - Used in: Post 04, Part 2 §3 (board transition timeline).

69. **tZERO Group Inc.** — Form ATS-N/UA (Alternative Trading System).
    - Filed June 11, 2025 with SEC.
    - Used in: Post 04, Part 1 §2 (tZERO capabilities matrix).

70. **tZERO Group Inc.** — SPBD (Special Purpose Broker-Dealer) License.
    - Approved September 2024. First regulatory exam passed October 2025 (no exceptions).
    - One of two SPBD licenses in the United States.
    - Used in: Post 04, Part 1 §2.

71. **GameStop Corp.** — 10-K (FY2025, pending).
    - CIK 0001326380. Due ~late March / early April 2026.
    - Used in: Post 04, Part 4 §4 (10-K countdown analysis).

72. **RC Ventures LLC** — Schedule 13D / 13D-A.
    - Ryan Cohen's beneficial ownership filings (GameStop, potential BYON).
    - Used in: Post 04, Part 4 §5 (EDGAR drop analysis).

### BYON Corporate Actions

73. **Beyond, Inc.** — Section 363 Bankruptcy Sale.
    - Acquisition of Bed Bath & Beyond IP for $21.5M (June 2023).
    - Free and clear of all liens, claims, and encumbrances.
    - Used in: Post 04, Part 3 §4 (Section 363 cleansing doctrine).
    - Source: U.S. Bankruptcy Court, District of New Jersey, Case 23-13359-VFP.

74. **Beyond, Inc.** — buybuy BABY Acquisition.
    - Purchase price: $5M (February 2025).
    - Tokenized as digital security on tZERO (May 2025).
    - Used in: Post 04, Part 1 §1 (timeline); Part 3 (airdrop architecture).

75. **Beyond, Inc.** — Warrant Dividend.
    - Issued 28 days after final ICE-affiliated director departure.
    - Used in: Post 04, Part 2 §4 (defensive posture analysis).

### Legal / Case Law

76. **Mangrove Partners Master Fund, Ltd. v. Overstock.com, Inc.** — Tenth Circuit Court of Appeals, October 2024.
    - Ruling: Digital dividends on proprietary blockchain ledgers are lawful corporate actions.
    - Used in: Post 04, Part 1 §3 (OSTK digital dividend legal precedent).

77. **DK-Butterfly, Inc. v. Ryan Cohen et al.** — Federal lawsuit, filed August 2024.
    - Amount: $47 million. Filed by BBBY bankruptcy estate.
    - Used in: Post 04, Part 3 §5 ($47M firewall analysis).

78. **Chamber of Commerce of the United States v. Federal Trade Commission** — E.D. Tex., February 12, 2026.
    - HSR Act enforcement stay.
    - Used in: Post 04, Part 4 §3 (antitrust filing window).

### Trademark / USPTO

79. **USPTO TSDR Database** — RC Ventures "Teddy" trademark filings.
    - Multiple serial numbers, verified February 2026.
    - Trademark activity as forward-looking signal.
    - Used in: Post 04, Part 4 §1 (Teddy trademark "tell").

### ICE / NYSE

80. **Intercontinental Exchange (ICE)** — tZERO Strategic Investment.
    - Investment date: February 2022. Installed CSO as tZERO CEO.
    - All 3 ICE-affiliated directors subsequently departed (2024–2025).
    - Used in: Post 04, Part 2 §1 (gatekeeper thesis).

### Jump Trading / Tai Mo Shan

81. **SEC v. Tai Mo Shan Limited** — Settlement.
    - $123 million settlement. TerraUSD stablecoin manipulation; $1.28 billion profit.
    - Used in: Post 03, Part 3 §5 (Jump Trading dual registration).

### BYON Press / Industry Sources

82. **Beyond.com Press Releases** — Corporate Timeline.
    - Overstock → Beyond, Inc. rename; BBBY acquisition; buybuy BABY tokenization; 24/7 trading launch.
    - Used in: Post 04, Part 1 §1.
    - Additional sources: BusinessWire, RetailDive, CoinDesk.

83. **Marcus Lemonis** — Reddit AMA, Public Statements.
    - Referenced in context of BYON governance and strategic direction.
    - Used in: Post 04, Part 4 §2.

---

## Post 04, Part 5 — The Convergence (Citations 84–86)

84. **DTCC Important Notice A#9676** — Year 2026 Obligation Warehouse RECAPS Schedule.
    - Published November 13, 2025. P&S #9249.
    - March 2026 RECAPS dates: **March 3** (settlement Mar 4), **March 17** (settlement Mar 18).
    - Used in: Post 04, Part 5 §4 (March 17 convergence window).
    - URL: https://www.dtcc.com/legal/important-notices

85. **Power Tracks Energy Budget** — Options Energy by Tenor (trades × DTE weight).
    - Proprietary metric computed from Polygon.io SIP tick data, 2020–2026.
    - Three ~10-week accumulate/discharge cycles identified: Jun 2025, Sep 2025, Dec 2025/Jan 2026.
    - Used in: Post 04, Part 5 §2–§3 (energy stacking and tenor migration analysis).
    - Script: `power-tracks-research/research/options_hedging_microstructure/`

86. **CBOE Options Expiration Calendar** — March 2026 Quarterly OpEx ("Triple Witching").
    - Date: Friday, March 20, 2026.
    - All March monthlies, quarterlies, and index options expire simultaneously.
    - Used in: Post 04, Part 5 §4 (convergence window).

---

## Paywalled / Pending Data (All Posts)

| Data Source | Status | Blocking Post |
|-------------|--------|---------------|
| XRT PCF (Daily Basket Holdings) | Paywalled (DTCC/NYSE Arca) | Post 03, Part 4 |
| SEC SBSR (Equity Swap Data) | FOIA pending (deadline Apr 3, 2026) | Post 03, Part 4; Post 04, Part 5 |
| CFTC CME EFRP Volume | FOIA pending | Post 03, Part 4 |
| FFIEC Bulk Call Report Data | Requires bulk retrieval | Post 03, Part 2 |

