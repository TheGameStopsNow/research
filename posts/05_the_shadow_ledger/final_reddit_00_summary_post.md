# The Shadow Ledger: Summary Post

There's been a lot of interest in this series, but I've been asked to explain what this series found without requiring everyone to cross-reference four regulatory databases and a bankruptcy docket. Fair enough. This post is my plain-language interpretation of a seven-part investigation into how Wall Street funded, transferred, and concealed delivery obligations on GameStop using offshore structures, crypto plumbing, and a money market fund. If you want the actual evidence, every link goes to the full post. If you want the math, code, and reproducible scripts, they're on [GitHub](https://github.com/TheGameStopsNow/research).

**TL;DR:** I traced the phantom share supply chain from fake offshore locates, through a $16.7 billion repo machine that converts crypto into prime broker cash, to a DMA (Direct Market Access) algorithm running settlement compliance on 31 stocks. The same firms that are short GME are now forced to buy the assets GME holds on its balance sheet. I also found the machine that does it, running on exactly two options exchanges, and the SEC already prosecuted someone for the identical pattern a decade ago.

> **Position disclosure:** I hold a long position in GME. I am not a financial advisor, attorney, or affiliated with any entity named in this post.

---

---

![Ticker Key](figures/ticker_legend_00_summary_post.png)


## What Is This Series About?

My [previous series](../04_the_boundary_conditions/01_the_overflow.md) showed that settlement pressure doesn't stay inside GME's pipes. It floods into other stocks, breaks Treasury bond settlement, crosses national borders, and keeps cycling on a cancelled stock. That series ended with a question: *who is actually building the pipes?*

This series answers it. Seven posts. Seven layers. One machine.

---

## Part 1: The Fake Locates // [Full Post](01_the_fake_locates.md)

### The short version

Every time you short-sell a stock, you need a "locate" first. Think of it like a receipt that says "yes, we can find shares to borrow." When short interest hit 140% of GME's float in January 2021, someone was writing receipts for shares that didn't exist.

I found them in an unlikely place: FTX's "Tokenized Stocks." Starting in October 2020, FTX sold crypto tokens claiming each one was backed 1:1 by real GME shares held at a tiny German broker called CM-Equity AG. A U.S. prime broker could use that German attestation as a locate without checking whether the physical shares actually existed. Reg SHO only requires a "reasonable belief." Not proof.

Two problems with this story. First, CM-Equity's total assets at their absolute peak were **€32.7 million** (~$36M). That's everything the company owned. Meanwhile, in the FTX bankruptcy, Binance demanded **$65 million** in collateral from CM-Equity under the Tokenized Stocks Agreement. That's nearly double the entire company.

Second, the FTX bankruptcy trustee, John J. Ray III, filed a Schedule of Assets under penalty of federal perjury. It reports **zero GameStop shares**. Not a few. Zero. FTX sold Tokenized GME. They claimed each token was backed by real stock. The sworn filing says there was no stock.

When FTX collapsed on November 11, 2022, the GME settlement chain fractured. Delivery failures surged on T+35 timelines, with late December daily peaks hitting 597K shares against an October baseline of ~39K. The phantom locates died, and the undelivered shares surfaced on the lit tape. That's what happens when you pull the receipt out from under a pile of IOUs.

### My take

I don't think anyone woke up and said "let's manufacture fake shares through a German broker." I think someone noticed that a European-regulated entity could attest to holding shares, and U.S. prime brokers only needed a "reasonable belief" to check the box. The regulatory architecture practically invited it. FTX just gave it a crypto wrapper.

---

## Part 2: The Derivative Paper Trail // [Full Post](02_the_6_trillion_swap.md)

### The short version

So the phantom locates died. Where did the risk go?

The popular theory was JPMorgan. Their derivatives spiked $6 trillion in Q1 2021. Sounds like a smoking gun. Except when you break it down by asset class, the $6 trillion was almost entirely **interest rate swaps**. JPMorgan's equity derivative book actually *shrank* by $410 billion during the squeeze quarter. The GME-sized hiding place at JPMorgan doesn't exist.

The real trail is offshore. Citadel Securities (Europe) filed **8 ISDA (International Swaps and Derivatives Association) Initial Margin Agreements** with UK Companies House in **7 consecutive days** right before the September 2022 regulatory deadline. The counterparties? JPMorgan, Goldman Sachs, Morgan Stanley, Citibank, Barclays, HSBC, Bank of America, and Merrill Lynch. These are the exact banks that fund the carry trade.

Then there's the cleanup. When FTX went bankrupt, its counterparty ledger became an asset of the estate. Those records contain every name that used the phantom locates. A distressed debt fund called **Diameter Capital Partners** bought FTX bankruptcy claims. The CM-Equity $65 million phantom locate claim was settled for $51 million, no litigation, no discovery. The evidence stayed sealed.

And Citadel's Cayman Islands fund vehicles? Their Gross Asset Value more than doubled, from ~$90 billion to ~$180 billion, during the period when domestic positions were supposedly closing.

### My take

Buying the bankruptcy claims of the company that holds your receipts is legal. Standard distressed debt strategy. It's also exactly what you'd do if you wanted those receipts to never see a courtroom.

---

## Part 3: The Ouroboros // [Full Post](03_the_ouroboros.md)

### The short version

The machine needs fuel. Where does the money come from?

Picture a snake eating its own tail. That's the funding loop.

**Cantor Fitzgerald** is the primary custodian for Tether's $100+ billion in reserves. Their annual filing shows a **$16.7 billion** repo machine: $6.9 billion in reverse repos, $9.8 billion in repos, and $4.4 billion in Treasuries with $4.5 billion simultaneously pledged as collateral. Nearly every Treasury they own is doing double duty. And the word "Tether" appears nowhere in the entire filing.

On **August 13, 2024**, Tether minted $1 billion USDT. That same day, the GCF repo channel (the interdealer market where broker-dealers like Cantor pledge Treasury collateral) spiked **+11.6%** above its monthly average. Every other repo channel either declined or stayed flat. Only the channel Cantor uses surged on the exact day Tether deployed a billion dollars.

And then there's Jump Trading, one of the microwave consortium partners from [Options & Consequences](../02_options_and_consequences/03_the_systemic_exhaust.md). During the same week the yen carry trade blew up in August 2024, Jump dumped **$377 million in Ethereum**. The same firm connects to the microwave network (equities), the yen carry trade (funding), and the crypto liquidation pipeline. Three legs of the stool. One trading firm.

### My take

Cantor is pure plumbing. They take zero directional risk. They clip fees converting Treasury collateral into fiat for the prime broker network. The gamblers (Goldman, Citadel, Jane Street, Susquehanna) borrow that liquidity to fund their derivative positions. The loop feeds itself: Tether mints create Treasuries, Treasuries become repo collateral, repo cash becomes margin for equity shorts. When the system needs a drink, it triggers another mint.

---

## Part 4: The Reflexive Trap // [Full Post](04_the_reflexive_trap.md)

### The short version

In March 2025, GameStop updated its investment policy to add Bitcoin as a treasury reserve asset. On May 28, 2025, the company announced it had purchased 4,710 BTC (~$504 million), funded by a $1.3 billion convertible notes offering. Most people thought it was a crypto bet. The 13F data (quarterly institutional holdings reports filed with the SEC) suggests something different.

Within one quarter, Goldman Sachs held **$9-10 billion** in crypto-adjacent positions: $2.2 billion in iShares Bitcoin Trust shares, $1.7 billion in ₿ puts, $1.3 billion in iShares Ethereum Trust, $660 million in MicroStrategy puts, $900+ million in Coinbase. Citadel, Susquehanna, and Jane Street all built similar positions. The same firms that appear in the ISDA map are the same firms loading up on the exact asset class GameStop now holds on its balance sheet.

This creates a trap with no comfortable exit. If Bitcoin rises, GME's net asset value rises, making it harder to short. If Bitcoin falls, Goldman's $2.2 billion ₿ position falls, triggering margin calls, weakening the collateral that backs the Ouroboros.

> **Update (Jan/Feb 2026):** GameStop transferred all BTC to Coinbase Prime in late January 2026. Cohen publicly stated that a new strategy is "way more compelling than Bitcoin." If GME ultimately sells its BTC, the reflexive loop described above would break. The 13F data showing institutional crypto-adjacent positioning remains valid regardless of GameStop's BTC holdings.

### My take

I think Ryan Cohen noticed that the short machine's collateral and GME's balance sheet could be anchored to the same asset. He didn't buy Bitcoin because he likes crypto. He bought Bitcoin because it's their collateral. Whether this was the explicit strategy or just a happy accident, the 13F data shows the reflexive dependency. Every hedge they put on makes the loop tighter.

---

## Part 5: The Bridge // [Full Post](05_the_bridge.md)

### The short version

Parts 1 through 4 described separate layers: locates, derivatives, funding, collateral. Part 5 connects the wiring.

Both Citadel and Jane Street manage their London derivative books through the same custodian: **BNY Mellon**. Jane Street's ISDA Credit Support Annex charge was filed in April 2022, right when the Fed started hiking rates. BNY Mellon isn't a passive vault. It simultaneously generates the cash (Dreyfus money market funds), manages the collateral, clears the trades (Pershing), custodies the positions ($52.1 trillion in AUC/A as of Dec 2024), and controls the DTCC (Depository Trust & Clearing Corporation) settlement layer. One institution touches every link in the chain.

A federal lawsuit filed in early 2026 illuminates the bridge from the crypto side. *Snyder v. Jane Street* alleges that Jane Street executives maintained a covert information pipeline with a Terraform Labs insider, enabling an $85 million liquidation 10 minutes before the $40 billion Terra/LUNA collapse. The case has not been adjudicated, but it maps a capital flow pathway between crypto entities and equity market-making desks.

### My take

When the equity desk needs cash, the crypto desk liquidates. When the crypto desk needs compliance cover, the options algo generates synthetic close-outs. The layers aren't independent systems. They're one machine with six moving parts, and BNY Mellon is the common nerve center.

---

## Part 6: The Cash Engine // [Full Post](06_the_cash_engine.md)

### The short version

This is the post where I followed the money to its literal source.

BNY Mellon's **Dreyfus Government Cash Management** fund is one of the largest money market funds in the world. It takes investor cash and lends it to prime broker banks through triparty repos. Using the SEC's own N-MFP filings (money market fund portfolio disclosures), I pulled every monthly datapoint from December 2019 through May 2022.

In **July 2021**, repo lending jumped **58% in a single month**, from $40.5 billion to $64 billion. It never came back down. By December 2021, it had tripled from its baseline to **$86.2 billion**. That same month, Citadel Securities reported $71.33 billion in pledged collateral. The timing sync is the strongest quantitative link in the chain.

Here's the real kicker. Dreyfus repo cash is *negatively correlated* with GME settlement failures: **r = -0.42, p = 0.022**. More BNY Mellon cash flowing into the repo system, fewer FTDs reaching the public tape. At higher GME prices. Standard mechanics predict the opposite: higher prices and sustained short interest should produce *more* failures, not fewer.

I ran a control test. **Vanguard Federal Money Market Fund**, roughly the same size, same instruments, not operated by BNY Mellon. It showed **zero** correlation with GME FTDs (r = +0.096, p = 0.619). Dreyfus grew +179% over the period. Vanguard grew +40%. The control test narrows the signal to BNY Mellon's cash pool, not macro liquidity.

### My take

Cash is fungible, and I can't trace a specific dollar from a Dreyfus investor to a specific GME collateral posting. But I can prove the capacity ($86 billion), the mechanism (triparty repos to prime brokers), the timing (peak cash exactly when the ecosystem needed it most), and the control test (Vanguard shows nothing). The pipe is the right diameter, runs to the right building, and gushed water on the exact day the building caught fire. I just can't show you which faucet.

---

## Part 7: The Fingerprint // [Full Post](07_the_fingerprint.md)

### The short version

This is the part that made me set my laptop down and go for a walk.

Using 2,038 days of tick-level OPRA (Options Price Reporting Authority) data, I found a DMA routing fingerprint: 1-lot trades, sub-$0.10 prices, monotonic sequencing at 90%+, operating on exactly two exchanges. It runs on **31 stocks**, including 📊, 🍎, 🟩, and GME.

On liquid mega-caps like 📊, the algo runs based purely on market activity. FTDs have zero predictive power (t = 0.38). On borrow-constrained stocks like GME, lagged FTDs are highly significant (**t = +3.86, p < 0.001**), peaking at exactly the T-6 to T-7 Reg SHO close-out window.

Same hardware. Different trigger logic. On stocks where delivery is easy, it trades with the market. On stocks where delivery is hard, it trades with the settlement calendar.

The nail in the coffin is 🛁. During Bed Bath & Beyond's bankruptcy, the algo ran at **3x its normal pace**. But here it *inverted*: instead of resolving FTDs (Failures to Deliver, undelivered shares after the settlement deadline) (like it does on 🎬), it actively *deferred* them. On 🛁, algo days are associated with significantly smaller FTD drops at every tested window (p < 0.001).

And the algo ceased on the **exact date** the options chain was delisted. Not the bankruptcy filing. Not the equity delisting. The options chain. The delisting trigger was the options market.

It runs on only two exchanges: MIAX Pearl and Nasdaq BX. The only two with inverted fee models, where the taker *earns* a rebate instead of paying a fee. 4,307 daily trades that would cost $2,150 on a normal exchange instead generate $650-860 in revenue.

The SEC already caught someone doing this before. In 2013, they prosecuted **Wolverine Trading** for conducting pre-arranged transactions designed solely to reset the Reg SHO settlement clock. Wolverine is the confirmed Designated Primary Market Maker for GME options on Cboe. The identical mechanical profile.

### My take

I don't know who operates this algo. The OPRA data is anonymized. But the venue constraint (Pearl + BX only), the inverted-fee economics, and the DPM assignment narrow the candidates to three firms: Citadel Securities (~85% probability), Wolverine Trading (~75%), or Susquehanna (~65%). A $2,000 data purchase from MIAX Pearl would reveal the executing firm MPID for every qualifying trade. For anyone with subpoena authority, the roadmap is in the paper.

---

## How I Tried to Prove Myself Wrong

1. **"The $6 trillion JPMorgan spike is the smoking gun."** I tested it. It was interest rate swaps. Equity derivatives *declined* $410 billion. I killed my own headline.

2. **"The Dreyfus correlation is just macro liquidity."** The Vanguard control test says otherwise: r = +0.096, p = 0.619 vs. Dreyfus r = -0.42, p = 0.022. Only BNY Mellon's cash pool.

3. **"The DMA algo is just normal market-making."** On 📊: zero FTD correlation. On GME: t = +3.86 at the Reg SHO deadline. Same hardware, different trigger.

4. **"🛁 is a glitch."** The algo ran 3x during bankruptcy, inverted its FTD relationship, and ceased on the exact date of options delisting. Glitches don't have delisting triggers.

5. **"The Bitcoin move was just a crypto bet."** Goldman, Citadel, and SIG all massively expanded crypto-adjacent positions within one quarter. The 13F data shows institutional reflexive hedging, not a meme trade.

---

## What Would Change My Mind

1. If the **DMA fingerprint dissolves** when tested on post-2025 OPRA data with updated venue economics. New fee schedules could invalidate the inverted-fee hypothesis.
2. If the **Dreyfus-FTD correlation breaks** under additional macro controls (VIX, SOFR, ON RRP as covariates). The Vanguard test is strong, but not airtight.
3. If **Goldman's crypto-adjacent 13F exposure** declines below $2 billion. The reflexive loop thesis was a one-quarter anomaly.

I'll be the first to tell you if any of these happen.

---

## The Series

| Part | Title | One Sentence |
|:----:|:------|:-------------|
| [1](01_the_fake_locates.md) | **The Fake Locates** | FTX tokenized stocks functioned as phantom locates; the FTX bankruptcy filing reports zero GME shares |
| [2](02_the_6_trillion_swap.md) | **The Derivative Paper Trail** | The $6T JPMorgan spike was interest rate swaps; the real trail is 8 offshore ISDA filings in 7 days |
| [3](03_the_ouroboros.md) | **The Ouroboros** | Cantor's $16.7B repo machine converts Tether reserves into prime broker cash |
| [4](04_the_reflexive_trap.md) | **The Reflexive Trap** | Goldman holds $9-10B in crypto-adjacent positions; GameStop bought their collateral |
| [5](05_the_bridge.md) | **The Bridge** | BNY Mellon is the common custodian; Snyder v. Jane Street maps the capital flow |
| [6](06_the_cash_engine.md) | **The Cash Engine** | Dreyfus repos tripled to $86.2B; the Vanguard control test isolates BNY Mellon |
| [7](07_the_fingerprint.md) | **The Fingerprint** | A DMA algo runs on 31 tickers; same hardware, different trigger logic on borrow-constrained stocks |

⬅️ **Previously:** [Boundary Conditions](../04_the_boundary_conditions/01_the_overflow.md) (Parts 1-3)
➡️ **Next:** [The Custodian's Ledger](../06_the_custodians_ledger/01_the_satoshi_test.md) (Parts 1-3)

---

All code, data, and results: [github.com/TheGameStopsNow/research](https://github.com/TheGameStopsNow/research)

---

*Not financial advice. Forensic research using public data. I'm not a financial advisor, attorney, or affiliated with any entity named in this post. The author holds a long position in GME.*

*"Yes, of course duct tape works in a near-vacuum. Duct tape works anywhere. Duct tape is magic and should be worshiped."*
*— Andy Weir, The Martian*
