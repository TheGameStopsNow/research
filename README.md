# Options & Consequences: The Microstructure of Market Exploitation

This repository contains the data, replication code, and formal academic papers supporting the *Options & Consequences* research series.

This project reverse-engineers the execution mechanics, physical infrastructure, and macroeconomic funding of options-driven equity price displacement. By synchronizing nanosecond-resolution consolidated tape data (SIP), regulatory filings (SEC/FINRA), and physical hardware registries (FCC), this research maps a systemic regulatory exploit spanning U.S. equities and derivatives markets.

## 📄 The Research Papers

The formal findings are divided into a four-part series:

1. **[Paper I: Theory & ACF](papers/01_theory_options_hedging_microstructure.md)**
   *The Long Gamma Default, the Gamma Reynolds Number, and empirical measurement of options-driven equity dampening across a 37-ticker panel.*
2. **[Paper II: Evidence & Forensics](papers/02_forensic_trade_analysis.md)**
   *The 34-millisecond cross-asset liquidity vacuum, SEC Rule 605 odd-lot evasion, FINRA condition code fragmentation, and the $34M off-tape conversion.*
3. **Paper III: Policy & Attribution** 🔒 *EMBARGOED — releases with Reddit Part 3*
   *SEC Rule 10b-5 element mapping, the FINRA CAT subpoena roadmap, and the SEC FOIA "Zero-Day" log analysis.*
4. **Paper IV: Infrastructure & Macro** 🔒 *EMBARGOED — releases with Reddit Part 4*
   *The 17-Sigma basket proof (Empirical Shift Test), FCC 10GHz microwave networks, 5-year weather verification panel, DTCC RECAPS settlement cycles, and the Yen Carry Trade funding mechanism.*

## 📝 The Reddit Series

A four-part narrative distillation written for a general audience:

1. **[Part 1: Following the Money](posts/part1_following_the_money.md)** — Trade data analysis
2. **[Part 2: The Paper Trail](posts/part2_the_paper_trail.md)** — SEC filings & balance sheets
3. **Part 3: The Systemic Exhaust** 🔒 *Coming soon* — Lateral OSINT: algorithms, infrastructure, weather
4. **Part 4: The Macro Machine** 🔒 *Coming soon* — Macro funding & settlement timing

## 🔬 Replication & Data

We believe in open-source, verifiable intelligence. Every statistical claim, chart, and latency measurement in these papers can be independently reproduced using the scripts provided.

*   `code/` — Python scripts for ACF generation, Lead-Lag correlation, NMF temporal archaeology, the Empirical Shift Test, and the 52-ticker weather panel.
*   `data/` — Storm event datasets, systemic exhaust source documents, and SEC FTD archives.
*   `results/` — Pre-computed JSON and CSV outputs for rapid verification without requiring paid API subscriptions.

**For the complete file index, see [INDEX.md](INDEX.md).**

## 🔒 Upcoming Declassifications (Embargoed)

Papers III and IV contain findings regarding physical telecom infrastructure, federal bankruptcy dockets, offshore derivative funding, and DTCC administrative settlement cycles. To prevent narrative front-running while ensuring cryptographic proof of prior authorship, the text of these papers is under embargo until their corresponding summaries are published on Reddit.

* **Paper III (Policy & Attribution) SHA-256 Hash:** `808d928d651934e6fcd02ef6649275f6cd4e8f579bd51cc7c230aec846131c74`
* **Paper IV (Infrastructure & Macro) SHA-256 Hash:** `8d3778e152d212a7dc476d1c1e8d30752f46a9eb52550f448d210dc1b034e114`

When the embargoed papers are released, anyone can verify their integrity:
```bash
shasum -a 256 papers/03_policy_regulatory_implications.md
shasum -a 256 papers/04_infrastructure_macro.md
```

**Dead Man's Switch:** The file `evidence_package.zip.enc` (available under [Releases](../../releases)) is an AES-256-CBC encrypted archive containing all four papers, replication scripts, and source data. If this repository or the author's accounts are removed before the series concludes, the decryption password will be published independently.

To decrypt (when password is released):
```bash
openssl enc -aes-256-cbc -d -salt -pbkdf2 -iter 100000 -in evidence_package.zip.enc -out evidence_package.zip -pass 'pass:PASSWORD_HERE'
```

## ⚠️ Disclaimer

*This repository contains independent forensic research based entirely on publicly available data. The author is not a financial advisor, securities attorney, or affiliated with any regulatory body. This is not financial advice.*
