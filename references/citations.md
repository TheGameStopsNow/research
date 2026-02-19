# Citations & References — Forensic Analysis Bundle (Rounds 1–16)

**Last Updated:** February 20, 2026

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
    - URL: https://www.sec.gov/data/foiadocsfailsdatahtm

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
