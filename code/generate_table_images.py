"""Generate clean table images for X.com articles (markdown tables get stripped)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os
import textwrap

OUT = os.path.join(os.path.dirname(__file__), "..", "posts", "figures")
os.makedirs(OUT, exist_ok=True)

# ── Style constants ──────────────────────────────────────────────────────────
BG       = "#0d1117"
HEADER   = "#161b22"
ROW_EVEN = "#0d1117"
ROW_ODD  = "#161b22"
ACCENT   = "#58a6ff"
TEXT     = "#c9d1d9"
BOLD_TXT = "#f0f6fc"
RED_TXT  = "#ff7b72"
GREEN_TXT= "#7ee787"
BORDER   = "#30363d"
FONT     = "Inter"


def make_table(data, col_widths, filename, title=None, highlight_rows=None,
               bold_cells=None, red_cells=None, green_cells=None, figw=10,
               max_col_chars=None):
    """
    data: list of lists (first row = header)
    col_widths: list of relative column widths
    highlight_rows: set of row indices (0-based, excluding header) to accent
    bold_cells: set of (row, col) to render bold white
    red_cells / green_cells: set of (row, col) for color
    max_col_chars: dict of {col_index: max_chars} for text wrapping
    """
    nrows = len(data)
    ncols = len(data[0])
    highlight_rows = highlight_rows or set()
    bold_cells = bold_cells or set()
    red_cells = red_cells or set()
    green_cells = green_cells or set()
    max_col_chars = max_col_chars or {}

    # Pre-wrap text and compute row heights
    LINE_H = 0.22  # height per line of text
    BASE_PAD = 0.18  # vertical padding per row
    header_height = 0.52
    row_heights = []
    wrapped_data = [data[0]]  # header stays unwrapped
    for r in range(1, nrows):
        row = []
        max_lines = 1
        for c, val in enumerate(data[r]):
            clean = val.replace("**", "")
            if c in max_col_chars:
                lines = textwrap.wrap(clean, width=max_col_chars[c])
                if not lines:
                    lines = [""]
                max_lines = max(max_lines, len(lines))
                row.append((val, lines))
            else:
                row.append((val, [clean]))
        row_heights.append(max_lines * LINE_H + BASE_PAD)
        wrapped_data.append(row)

    fig_height = header_height + sum(row_heights) + 0.3
    if title:
        fig_height += 0.5

    fig, ax = plt.subplots(figsize=(figw, fig_height))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, fig_height)
    ax.axis("off")

    # Compute x positions from col_widths
    total = sum(col_widths)
    norm = [w / total for w in col_widths]
    margin = 0.03
    usable = 1 - 2 * margin
    x_starts = [margin]
    for w in norm[:-1]:
        x_starts.append(x_starts[-1] + w * usable)

    y_top = fig_height - 0.15
    if title:
        ax.text(0.5, y_top, title, ha="center", va="top",
                fontsize=13, fontweight="bold", color=ACCENT,
                fontfamily=FONT, transform=ax.transData)
        y_top -= 0.5

    # Draw header
    y = y_top
    ax.fill_between([0, 1], y - header_height, y, color=HEADER)
    ax.plot([0, 1], [y - header_height, y - header_height], color=ACCENT, lw=1.5)
    for c, val in enumerate(data[0]):
        ax.text(x_starts[c] + 0.008, y - header_height / 2, val,
                ha="left", va="center", fontsize=10, fontweight="bold",
                color=ACCENT, fontfamily=FONT)
    y -= header_height

    # Draw data rows
    for r in range(1, nrows):
        rh = row_heights[r - 1]
        bg = ROW_ODD if r % 2 == 0 else ROW_EVEN
        if (r - 1) in highlight_rows:
            bg = "#1c2333"
        ax.fill_between([0, 1], y - rh, y, color=bg)
        ax.plot([0, 1], [y - rh, y - rh], color=BORDER, lw=0.5)

        for c, (val, lines) in enumerate(wrapped_data[r]):
            is_bold = "**" in val or (r - 1, c) in bold_cells
            color = TEXT
            weight = "normal"
            if is_bold:
                color = BOLD_TXT
                weight = "bold"
            if (r - 1, c) in red_cells:
                color = RED_TXT
                weight = "bold"
            if (r - 1, c) in green_cells:
                color = GREEN_TXT
                weight = "bold"
            # Render wrapped lines
            block_h = len(lines) * LINE_H
            text_top = y - (rh - block_h) / 2 - LINE_H / 2
            for i, line in enumerate(lines):
                ax.text(x_starts[c] + 0.008, text_top - i * LINE_H, line,
                        ha="left", va="center", fontsize=9.5, fontweight=weight,
                        color=color, fontfamily=FONT)
        y -= rh

    # Border
    rect = plt.Rectangle((0, y), 1, y_top - y, linewidth=1,
                          edgecolor=BORDER, facecolor="none")
    ax.add_patch(rect)

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    path = os.path.join(OUT, filename)
    fig.savefig(path, dpi=200, bbox_inches="tight", pad_inches=0.08,
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✓ {filename}")


# ═══════════════════════════════════════════════════════════════════════════════
# PART 1 TABLES
# ═══════════════════════════════════════════════════════════════════════════════

print("Part 1 tables:")

# Table 1: FTD Spike
make_table(
    data=[
        ["Date", "GME FTDs", "Multiplier", "Event"],
        ["May 3", "941", "1×", "Baseline"],
        ["**May 6**", "**186,627**", "**198×**", "**No public catalyst**"],
        ["**May 7**", "**433,054**", "**460×**", "**No public catalyst**"],
        ["**May 8**", "**525,493**", "**558×**", "**No public catalyst**"],
        ["May 13", "152,482", "162×", "First day after RK tweets"],
    ],
    col_widths=[1.2, 1.3, 1.2, 2.5],
    filename="table_p1_ftd_spike.png",
    title="GME Failures-to-Deliver — May 2024",
    highlight_rows={1, 2, 3},
    red_cells={(1, 2), (2, 2), (3, 2)},
)

# Table 2: Top Internalizers
make_table(
    data=[
        ["Rank", "Firm", "Event Volume", "Surge Multiple"],
        ["1", "Virtu Americas LLC", "81.3M", "**42.1×**"],
        ["2", "Citadel Securities LLC", "56.2M", "22.8×"],
        ["3", "G1 Execution Services", "44.2M", "**47.2×**"],
        ["4", "Jane Street Capital", "38.7M", "**44.4×**"],
        ["8", "UBS Securities LLC", "3.6M", "**∞ (from zero)**"],
    ],
    col_widths=[0.7, 2.5, 1.3, 1.5],
    filename="table_p1_internalizers.png",
    title="Top GME Non-ATS Internalizers — Event Week",
    red_cells={(0, 3), (2, 3), (3, 3), (4, 3)},
)

# Table 3: ETF Authorized Participants
make_table(
    data=[
        ["Rank", "Authorized Participant", "Redemption Value", "Creation Value"],
        ["1", "**Jane Street Capital, LLC**", "**$196,675,161**", "$80,302,990"],
        ["2", "J.P. Morgan Securities LLC", "$51,940,014", "$339,047,806"],
        ["3", "**Merrill Lynch (BofA)**", "$46,063,251", "$170,682,932"],
    ],
    col_widths=[0.6, 2.8, 1.8, 1.5],
    filename="table_p1_etf_aps.png",
    title="🧺 ETF Authorized Participants — N-CEN FY2024",
    highlight_rows={0, 2},
    red_cells={(0, 2)},
)

# Table 4: Tape Fracture (Two Markets)
make_table(
    data=[
        ["Market", "Price Range", "What You See"],
        ["**Lit exchanges**", "**$20.87–$20.99**", "Normal pre-market trading"],
        ["**FINRA TRF (dark)**", "**$31.20–$33.00**", "Off-tape derivative settlement"],
    ],
    col_widths=[1.8, 1.5, 2.5],
    filename="table_p1_tape_fracture.png",
    title="Two Simultaneous Markets — May 17, 2024 Pre-Market",
    highlight_rows={1},
    red_cells={(1, 1)},
)

# ═══════════════════════════════════════════════════════════════════════════════
# PART 2 TABLES
# ═══════════════════════════════════════════════════════════════════════════════

print("\nPart 2 tables:")

# Table 5: 13F Migration
make_table(
    data=[
        ["Quarter", "Calls", "Puts", "Status"],
        ["Q4 2020", "1,714,100", "2,224,500", "Pre-squeeze baseline"],
        ["**Q1 2021**", "2,278,000", "**3,271,400**", "**PUTS INCREASE 47%**"],
        ["Q2 2021", "2,148,500", "2,779,800", "Slow decline (−15%)"],
        ["Q3 2021", "2,127,100", "1,804,600", "Slow decline (−35%)"],
        ["Q1 2024", "708,100", "461,200", "−86% from peak"],
        ["**Q2 2024**", "3,511,800", "**5,733,500**", "**Puts reappear (+1,143%)**"],
    ],
    col_widths=[1.0, 1.2, 1.2, 2.2],
    filename="table_p2_13f_migration.png",
    title="Citadel Advisors 13F — GME Options Exposure",
    highlight_rows={1, 5},
    red_cells={(1, 2), (1, 3), (5, 2), (5, 3)},
)

# Table 6: 10b-5 Evidence Map
make_table(
    data=[
        ["Element", "Evidence"],
        ["Material Omission", "99.6% of off-NBBO TRF trades missing OPT flags, blinding CAT surveillance. Exploited dying Rule 605 odd-lot loophole."],
        ["Scienter (intent)", "GME flag evasion = 99.6% vs. AAPL = 56.0%. Flags selectively stripped on GME. Algorithmic exploitation of expiring loophole."],
        ["Regulation SHO", "ETF cannibalization to satisfy delivery obligations while dumping Zombie CUSIPs into FTDs."],
        ["Rule 15c3-3", "Robinhood locking $4.915B of retail cash in Special Reserve — literal receipt for undelivered shares."],
    ],
    col_widths=[1.0, 3.5],
    filename="table_p2_10b5_map.png",
    title="SEC Rule 10b-5 — Evidence-to-Statute Mapping",
    figw=8,
    max_col_chars={1: 50},
)

# Table 7: Part 3 - Empirical Shift Test
make_table(
    data=[
        ["Pair", "0-Lag (Real Matches)", "Background Noise Average", "Z-Score (Sigma)"],
        ["GME ↔ Control A", "70,841", "63,918", "4.99"],
        ["GME ↔ Control B", "113,191", "108,174", "3.27"],
        ["GME ↔ BBBY", "86,817", "66,282", "17.70"],
    ],
    col_widths=[1.5, 1.2, 1.5, 1.0],
    filename="table_p3_empirical_shift.png",
    title="Empirical Shift Test — GME Anomaly",
    highlight_rows=[4],
    bold_cells={(4, 0), (4, 1), (4, 2), (4, 3)},
    red_cells={(4, 3)},
    figw=9,
)

# Table 8: Part 4 - ISDA Counterparties
make_table(
    data=[
        ["ISDA Counterparty", "JGB Primary Dealer?", "Japanese Entity"],
        ["JPMorgan", "Yes", "JPMorgan Securities Japan Co., Ltd."],
        ["Morgan Stanley", "Yes", "Morgan Stanley MUFG Securities Co., Ltd."],
        ["Citibank", "Yes", "Citigroup Global Markets Japan Inc."],
        ["Goldman Sachs", "Yes", "Goldman Sachs Japan Co., Ltd."],
        ["Barclays", "Yes", "Barclays Securities Japan Limited"],
        ["BofA / Merrill Lynch", "Yes", "BofA Securities Japan Co., Ltd."],
        ["HSBC", "No", "HSBC Securities (Japan) — JGB clearing participant"],
    ],
    col_widths=[1.5, 1.0, 3.0],
    filename="table_p4_isda_dealers.png",
    title="UK ISDA Network — JGB Primary Dealer Registration",
    bold_cells={(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)},
    green_cells={(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1)},
    red_cells={(7, 1)},
    figw=10,
    max_col_chars={2: 50}
)

# Table 9: Part 4 - Yen Carry Trade Timeline
make_table(
    data=[
        ["Period", "Lev. Money Net Position", "What Was Happening"],
        ["H2 2019", "+15,924 avg (net long yen)", "Go West infrastructure being built. No carry trade yet."],
        ["Jan 2021", "+11,046 avg (net long yen)", "Squeeze. Leveraged funds were NOT short yen."],
        ["Feb 23, 2021", "+169", "Inflection point. Nearly zero."],
        ["Mar 2, 2021", "−6,528", "Crossed zero. Carry trade activated."],
        ["Mar 23, 2021", "−43,647", "Massive buildout in 3 weeks"],
        ["Nov 9, 2021", "−71,946", "2021 peak short"],
        ["Jul 9, 2024", "−110,635", "All-time peak. $11.1B notional short."],
    ],
    col_widths=[1.0, 1.5, 3.0],
    filename="table_p4_yen_carry.png",
    title="CFTC COT Data — Leveraged Money Net Position (JPY)",
    bold_cells={(2, 1), (5, 1), (5, 2), (8, 1)},
    highlight_rows=[5, 8],
    figw=10,
    max_col_chars={2: 50}
)

# Table 10: Part 4 - The Unwind
make_table(
    data=[
        ["Date", "Lev. Net Position", "Δ Weekly", "Notional (est.)"],
        ["Jul 9, 2024", "−110,635", "—", "~$11.1B short"],
        ["Jul 30, 2024", "−70,333", "+40,302", "covering"],
        ["Aug 6, 2024", "−24,158", "+46,175", "forced unwind"],
        ["Aug 13, 2024", "−2,415", "+21,743", "nearly flat"],
    ],
    col_widths=[1.0, 1.5, 1.0, 1.5],
    filename="table_p4_unwind.png",
    title="The Yen Unwind — July/August 2024",
    bold_cells={(2, 1), (5, 1)},
    highlight_rows=[5],
    figw=8,
)

# Table 11: Part 4 - Evidence Matrix
make_table(
    data=[
        ["Layer", "Evidence", "Primary Sources"],
        ["The Tape", "263M off-exchange shares; ETF Cannibalization; Rule 605 odd-lot evasion", "SEC FTD Data, FINRA Non-ATS, Polygon.io"],
        ["The Balance Sheets", "$2.16T derivative book; 47% increase in puts; UK ISDA offshore map", "SEC EDGAR X-17A-5, UK Companies House"],
        ["The Physical Reality", "17-Sigma algorithmic math; FCC microwave networks; $57M synthetic tax loss", "FCC ULS, Open-Meteo, Robinhood X-17A-5"],
        ["The Macro Machine", "Funded by 0% Japanese Yen; Triggered by NSCC VaR margin + clearinghouse conflict of interest", "FRED DEXJPUS, SEC Staff Report, Fed Discount Window"],
    ],
    col_widths=[1.0, 3.5, 1.5],
    filename="table_p4_evidence_matrix.png",
    title="The Shadow Ledger — Evidence Matrix",
    figw=12,
    max_col_chars={1: 60, 2: 30}
)

# ═══════════════════════════════════════════════════════════════════════════════
# FAILURE WATERFALL SERIES (Posts 1-4 of 03_the_failure_waterfall)
# Filenames: table_p{post}_{NN}_{name}.png — numbered by order in text
# ═══════════════════════════════════════════════════════════════════════════════

OUT_FW = os.path.join(os.path.dirname(__file__), "..", "posts", "03_the_failure_waterfall", "figures")
os.makedirs(OUT_FW, exist_ok=True)


def fw_table(**kwargs):
    """Wrapper that outputs to the Failure Waterfall figures directory."""
    kwargs["filename"] = os.path.join(OUT_FW, kwargs["filename"])
    # Strip the path prefix for make_table — it already joins with OUT
    fname = kwargs.pop("filename")
    # We need to bypass the default OUT directory, so save directly
    nrows = len(kwargs["data"])
    ncols = len(kwargs["data"][0])
    highlight_rows = kwargs.get("highlight_rows", set())
    bold_cells = kwargs.get("bold_cells", set())
    red_cells = kwargs.get("red_cells", set())
    green_cells = kwargs.get("green_cells", set())
    max_col_chars = kwargs.get("max_col_chars", {})
    col_widths = kwargs["col_widths"]
    figw = kwargs.get("figw", 10)
    title = kwargs.get("title", None)

    col_widths = np.array(col_widths, dtype=float)
    col_widths /= col_widths.sum()

    row_h = 0.52
    header_h = 0.55
    title_h = 0.7 if title else 0.0
    # Check for text wrapping to add height
    for r in range(nrows):
        for c in range(ncols):
            txt = str(kwargs["data"][r][c]).replace("**", "")
            limit = max_col_chars.get(c, 9999)
            if len(txt) > limit:
                lines = textwrap.wrap(txt, width=limit)
                extra = (len(lines) - 1) * 0.28
                if r == 0:
                    header_h = max(header_h, 0.55 + extra)
                else:
                    row_h = max(row_h, 0.52 + extra)

    total_h = title_h + header_h + row_h * (nrows - 1) + 0.25

    fig, ax = plt.subplots(figsize=(figw, total_h))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, total_h)
    ax.axis("off")

    y_top = total_h - 0.08

    if title:
        ax.text(0.5, y_top - title_h * 0.45, title,
                ha="center", va="center", fontsize=16, fontweight="bold",
                color=ACCENT, fontfamily=FONT)
        y_top -= title_h

    # header bg
    rect = plt.Rectangle((0.02, y_top - header_h), 0.96, header_h,
                          facecolor=HEADER, edgecolor=BORDER, linewidth=1.2,
                          clip_on=False, zorder=2)
    ax.add_patch(rect)
    # accent bar under header
    ax.plot([0.02, 0.98], [y_top - header_h, y_top - header_h],
            color=ACCENT, linewidth=2, zorder=3)

    x = 0.04
    for c in range(ncols):
        w = col_widths[c] * 0.94
        txt = str(kwargs["data"][0][c]).replace("**", "")
        limit = max_col_chars.get(c, 9999)
        if len(txt) > limit:
            txt = "\n".join(textwrap.wrap(txt, width=limit))
        ax.text(x, y_top - header_h / 2, txt,
                ha="left", va="center", fontsize=11, fontweight="bold",
                color=ACCENT, fontfamily=FONT, zorder=4)
        x += w

    y = y_top - header_h
    for r in range(1, nrows):
        bg = ROW_ODD if r % 2 == 0 else ROW_EVEN
        if (r - 1) in highlight_rows:
            bg = "#1c2333"
        rect = plt.Rectangle((0.02, y - row_h), 0.96, row_h - 0.01,
                              facecolor=bg, edgecolor="none", zorder=1)
        ax.add_patch(rect)

        x = 0.04
        for c in range(ncols):
            w = col_widths[c] * 0.94
            raw = str(kwargs["data"][r][c])
            is_bold = raw.startswith("**") and raw.endswith("**")
            txt = raw.replace("**", "")
            limit = max_col_chars.get(c, 9999)
            if len(txt) > limit:
                txt = "\n".join(textwrap.wrap(txt, width=limit))
            color = TEXT
            weight = "normal"
            if is_bold or (r - 1, c) in bold_cells:
                color = BOLD_TXT
                weight = "bold"
            if (r - 1, c) in red_cells:
                color = RED_TXT
                weight = "bold"
            if (r - 1, c) in green_cells:
                color = GREEN_TXT
                weight = "bold"
            ax.text(x, y - row_h / 2, txt,
                    ha="left", va="center", fontsize=10.5,
                    fontweight=weight, color=color, fontfamily=FONT, zorder=4)
            x += w
        y -= row_h

    fig.savefig(fname, dpi=200, bbox_inches="tight", pad_inches=0.08,
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  ✓ {os.path.basename(fname)}")


# ═══════════════════════════════════════════════════════════════════════════════
# POST 1: Where FTDs Go to Die
# Tables numbered in order of appearance in text
# ═══════════════════════════════════════════════════════════════════════════════

print("\nPost 1 — Where FTDs Go to Die:")

# 01: Glossary (L15)
fw_table(
    data=[
        ["Term", "What It Means"],
        ["**FTD**", "Failure to Deliver. Seller didn't deliver shares by deadline."],
        ["**OI**", "Open Interest. Total open options contracts."],
        ["**Phantom OI**", "OI that appears for one day and vanishes."],
        ["**Reg SHO**", "SEC rules governing short selling and delivery."],
        ["**CNS**", "Continuous Net Settlement (NSCC's netting system)."],
        ["**BFMM**", "Bona Fide Market Maker (extra time for FTD close-out)."],
        ["**TRF**", "Trade Reporting Facility (where dark pool trades report)."],
        ["**PFOF**", "Payment for Order Flow (broker sells your order to MM)."],
        ["**T+N**", "N business days after trade date."],
    ],
    col_widths=[1.0, 4.0],
    filename="table_p1_01_glossary.png",
    title="Key Terms — Part 1",
    figw=9,
    max_col_chars={1: 55},
)

# 02: Data Sources (L53)
fw_table(
    data=[
        ["Source", "What It Is", "Coverage"],
        ["SEC EDGAR FTD", "Official failure-to-deliver reports", "Jan 2020 – Jan 2026, 9 tickers"],
        ["ThetaData Options OI", "End-of-day open interest", "424 daily snapshots"],
        ["ThetaData Options Trades", "Every options trade (ms precision)", "2,038 trading days"],
        ["Polygon.io Equity Trades", "Every trade on lit + FINRA TRF", "Dec 2022"],
    ],
    col_widths=[1.5, 2.0, 1.8],
    filename="table_p1_02_data_sources.png",
    title="Data Sources — 19 Tests, 58 Sub-Tests, 9 Tickers",
    figw=9,
)

# 03: T+33 Metrics (L70)
fw_table(
    data=[
        ["Metric", "Value"],
        ["Hit rate (full period)", "**84%** (5/6 mega-spikes → T+33 echo)"],
        ["Hit rate (post-split)", "52% (reduced by valve transfer)"],
        ["2025 forward performance", "**100%** (4/4)"],
        ["ACF confirmation", "Statistically significant T+33 periodicity"],
    ],
    col_widths=[2.0, 3.0],
    filename="table_p1_03_t33_metrics.png",
    title="T+33 Echo Cascade — Performance Metrics",
    highlight_rows={0, 2},
    red_cells={(0, 1)},
    green_cells={(2, 1)},
    figw=8,
)

# 04: Deep OTM Put Enrichment (L92)
fw_table(
    data=[
        ["Metric", "Echo Windows", "Non-Echo Windows", "Enrichment"],
        ["Phantom OI trades", "Present at 18.1×", "Baseline", "**18.1×**"],
        ["Control-day trades", "Zero", "Zero", "—"],
        ["ISO block prints", "Present", "Absent", "∞"],
    ],
    col_widths=[1.5, 1.2, 1.2, 1.0],
    filename="table_p1_04_deep_otm.png",
    title="Deep OTM Put Factory — Echo vs Non-Echo",
    highlight_rows={0},
    red_cells={(0, 3)},
    figw=8,
)

# 05: Three Key Findings (L119)
fw_table(
    data=[
        ["Event", "Enrichment", "Volatility"],
        ["**T+33 echo**", "**18.1×**", "**Inverse** (−0.6 corr)"],
        ["Earnings", "0.9×", "High"],
        ["FOMC", "0.5×", "High"],
    ],
    col_widths=[1.3, 1.0, 1.5],
    filename="table_p1_05_three_findings.png",
    title="Three Key Findings",
    highlight_rows={0},
    red_cells={(0, 1)},
    figw=7,
)

# 06: The Failure Accommodation Waterfall (L140)
fw_table(
    data=[
        ["Offset", "Enrichment", "Layer", "What Happens"],
        ["**T+3**", "**5.4×**", "CNS netting", "Preemptive settlement activity"],
        ["T+6", "7.4×", "Post-BFMM spillover", "Failures surviving T+5 close-out"],
        ["T+13", "8.4×", "Threshold breach", "Reg SHO Threshold List trigger zone"],
        ["T+15", "10.0×", "2nd close-out", "Secondary BFMM cycle"],
        ["**T+25**", "**3.4×**", "**Statutory wall**", "**SEC Rule 204(a)(2): 35 cal days**"],
        ["T+27", "12.5×", "Broken roll", "OPEX roll failure cascade"],
        ["**T+33**", "**18.1×**", "**Volume mode**", "**Maximum reset volume (echo)**"],
        ["**T+35**", "**23.4×**", "**Composite echo**", "**T+25 + T+10 options bridge**"],
        ["T+38", "32.9×", "Red zone", "All exemptions exhausted"],
        ["**T+40**", "**40.3×**", "**Terminal peak**", "**Margin pressure convergence**"],
        ["**T+45**", "**0.0×**", "**Terminal boundary**", "**All obligations resolve**"],
    ],
    col_widths=[0.8, 1.0, 1.5, 2.5],
    filename="table_p1_06_waterfall.png",
    title="The Failure Accommodation Waterfall",
    highlight_rows={4, 6, 7, 9, 10},
    red_cells={(4, 1), (6, 1), (7, 1), (8, 1), (9, 1)},
    figw=10,
)

# 07: Control Ticker Comparison (L169)
fw_table(
    data=[
        ["Metric", "GME", "TSLA", "AAPL", "MSFT"],
        ["Trading days", "4,234", "2,808", "2,783", "2,593"],
        ["Spikes (>2σ)", "157", "116", "43", "77"],
        ["**Offsets > 2.0×**", "**15/16**", "9/16", "7/16", "3/16"],
        ["Mean enrichment", "**4.6×**", "2.3×", "2.4×", "1.1×"],
        ["T+33 enrichment", "**3.6×**", "0.9×", "1.9×", "1.1×"],
        ["T+35 enrichment", "**3.8×**", "0.7×", "0.0×", "0.5×"],
    ],
    col_widths=[1.5, 0.8, 0.8, 0.8, 0.8],
    filename="table_p1_07_control_tickers.png",
    title="Control Ticker Comparison — Waterfall Uniqueness",
    highlight_rows={2, 3, 4, 5},
    red_cells={(2, 1), (3, 1), (4, 1), (5, 1)},
    figw=9,
)

# 08: Rosetta Stone — Per-Spike Tracing (L188)
fw_table(
    data=[
        ["Spike Date", "FTD Volume", "Nodes Hit", "Coverage"],
        ["**2020-12-03**", "**1,787,191**", "**7/10**", "**70%**"],
        ["2021-01-26", "2,099,572", "1/10", "10%"],
        ["2021-01-27", "1,972,862", "0/10", "0%"],
        ["2022-07-26", "1,637,150", "0/10", "0%"],
        ["2025-12-04", "2,068,490", "0/10", "0%"],
    ],
    col_widths=[1.2, 1.2, 1.0, 1.0],
    filename="table_p1_08_rosetta_stone.png",
    title="The Rosetta Stone — Per-Spike Tracing",
    highlight_rows={0},
    green_cells={(0, 2), (0, 3)},
    figw=8,
)

# 09: 6-Share Vacuum — TRF Forensics (L211)
fw_table(
    data=[
        ["Date", "Type", "TRF %", "TRF Median", "Lit Median", "Odd Lot %", "ISOs"],
        ["**12/19**", "**Phantom**", "**41.2%**", "**6 shares**", "35", "73.3%", "**0**"],
        ["**12/22**", "**Phantom**", "**41.1%**", "10", "46", "69.6%", "**0**"],
        ["12/05", "Control", "35.2%", "12", "40", "69.4%", "0"],
        ["12/12", "Control", "37.6%", "10", "50", "67.2%", "0"],
    ],
    col_widths=[0.8, 0.9, 0.8, 1.0, 0.9, 0.8, 0.6],
    filename="table_p1_09_six_share_vacuum.png",
    title="The 6-Share Vacuum — Polygon.io TRF Forensics",
    highlight_rows={0, 1},
    red_cells={(0, 2), (0, 3)},
    figw=10,
)

# 10: Valve Transfer — Splividend (L234)
fw_table(
    data=[
        ["Period", "T+33 Echo Rate", "Phantom OI Enrichment"],
        ["Months 1-6 post-split", "75%", "10.17×"],
        ["Months 7-24", "52%", "**~2.0× (−89%)**"],
    ],
    col_widths=[2.0, 1.2, 1.5],
    filename="table_p1_10_valve_transfer.png",
    title="The Valve Transfer — Splividend Natural Experiment",
    red_cells={(1, 2)},
    figw=8,
)

# 11: Null Hypotheses (L266)
fw_table(
    data=[
        ["Hypothesis", "Evidence", "Verdict"],
        ["Retail lottery tickets", "Zero control-day trades. ISO blocks = institutional.", "REJECTED"],
        ["Dynamic hedging", "0.9× earnings, 0.5× FOMC. Settlement calendar, not vol.", "REJECTED"],
        ["OCC margin optimization", "T+33 tracks individual spikes, not fixed calendar.", "REJECTED"],
    ],
    col_widths=[1.5, 3.0, 0.6],
    filename="table_p1_11_null_hypotheses.png",
    title="Alternative Explanations — All Inconsistent",
    red_cells={(0, 2), (1, 2), (2, 2)},
    figw=9,
    max_col_chars={1: 45},
)


# ═══════════════════════════════════════════════════════════════════════════════
# POST 2: The Resonance
# ═══════════════════════════════════════════════════════════════════════════════

print("\nPost 2 — The Resonance:")

# 01: Glossary (L13)
fw_table(
    data=[
        ["Term", "What It Means"],
        ["**Q-factor**", "How many cycles an oscillation survives. Target: ≤0.5. Measured: ~21."],
        ["**Periodic echo**", "Recurrence at a multiple of the fundamental period (T+50, T+75…)."],
        ["**Standing wave**", "Persistent oscillation from overlapping, reinforcing echoes."],
        ["**LCM**", "Least Common Multiple. LCM(35,21) = 105."],
    ],
    col_widths=[1.2, 4.0],
    filename="table_p2_01_glossary.png",
    title="Key Terms — Part 2",
    figw=9,
    max_col_chars={1: 55},
)

# 02: Statutory Wall Scan (L47)
fw_table(
    data=[
        ["Offset (BD)", "Cal Days", "Enrichment", "What It Is"],
        ["T+20", "≈28", "2.40×", ""],
        ["T+21", "≈29", "2.59×", "OPEX cycle"],
        ["T+24", "≈34", "2.90×", "Pre-wall pressure"],
        ["**T+25**", "**≈35**", "**3.40×**", "**SEC Rule 204(a)(2): the wall**"],
        ["T+26", "≈36", "3.20×", "Post-wall spillover"],
        ["T+30", "≈42", "3.21×", ""],
        ["T+33", "≈46", "2.80×", "Part 1 echo (composite)"],
        ["T+35", "≈49", "2.46×", "T+25 + T+10 (options bridge)"],
        ["T+40", "≈56", "2.20×", ""],
    ],
    col_widths=[1.0, 0.8, 1.0, 2.5],
    filename="table_p2_02_statutory_wall.png",
    title="The Statutory Wall — T+20 to T+40 Scan",
    highlight_rows={3},
    red_cells={(3, 2)},
    figw=9,
)

# 03: Harmonic Series — T+25 vs T+35 (L77)
fw_table(
    data=[
        ["Multiple", "T+25 Series", "Enrichment", "T+35 Series", "Enrichment", "Winner"],
        ["1×", "T+25", "3.40×", "T+35", "2.46×", "**T+25**"],
        ["2×", "T+50", "1.89×", "T+70", "1.59×", "**T+25**"],
        ["3×", "T+75", "1.89×", "T+105", "2.99×", "**T+35**"],
        ["4×", "T+100", "1.37×", "T+140", "1.45×", "≈Tie"],
        ["5×", "T+125", "1.70×", "T+175", "1.57×", "**T+25**"],
    ],
    col_widths=[0.7, 0.9, 0.9, 0.9, 0.9, 0.8],
    filename="table_p2_03_harmonics.png",
    title="The Harmonic Series — T+25 vs T+35",
    highlight_rows={0, 2},
    red_cells={(0, 2)},
    green_cells={(2, 4)},
    figw=10,
)

# 04: Amplitude Decay (L136)
fw_table(
    data=[
        ["Cycles Later", "Business Days", "Calendar Time", "Amplitude Remaining"],
        ["1", "T+35", "~7 weeks", "**86%**"],
        ["5", "T+175", "~8 months", "**47%**"],
        ["10", "T+350", "~16 months", "**22%**"],
        ["**~4.5**", "**~T+158**", "**~7 months**", "**~50% ← half-life**"],
        ["25", "T+875", "~3.4 years", "**2.2%**"],
    ],
    col_widths=[1.0, 1.0, 1.2, 1.5],
    filename="table_p2_04_amplitude_decay.png",
    title="Amplitude Decay — What 86% Retention Means",
    highlight_rows={3},
    red_cells={(3, 3)},
    figw=8,
)

# 05: Resonance Summary (L148)
fw_table(
    data=[
        ["Metric", "Measured Value"],
        ["Amplitude retention per cycle", "**~86%**"],
        ["Energy leakage per cycle", "~14%"],
        ["Half-life", "**~7 months (~4.5 cycles)**"],
        ["Implied Q-factor", "**20.6 (CI: 16–28)**"],
    ],
    col_widths=[2.0, 2.0],
    filename="table_p2_05_resonance_summary.png",
    title="Resonance Summary — The System Rings",
    highlight_rows={0, 2, 3},
    red_cells={(0, 1), (3, 1)},
    figw=7,
)

# 06: Q-Factor Comparison (L159)
fw_table(
    data=[
        ["System", "Q-Factor", "Behavior"],
        ["Well-designed clearinghouse", "≤ 0.5", "Absorbs failure in <1 cycle"],
        ["Passive system (high friction)", "~1–5", "Decays within a few cycles"],
        ["**DTCC settlement (measured)**", "**~21**", "**Echoes persist for 1+ years**"],
    ],
    col_widths=[2.5, 0.8, 1.8],
    filename="table_p2_06_qfactor.png",
    title="Quality Factor — Settlement System vs Target",
    highlight_rows={2},
    red_cells={(2, 1)},
    figw=9,
)

# 07: Odd vs Even Asymmetry (L196)
fw_table(
    data=[
        ["Echo Type", "Mean Enrichment", "Example Offsets"],
        ["**Odd** (1st, 3rd, 5th...)", "**1.70×**", "T+35, T+105, T+175"],
        ["Even (2nd, 4th, 6th...)", "1.30×", "T+70, T+140, T+210"],
        ["**Ratio**", "**1.31:1**", ""],
    ],
    col_widths=[2.0, 1.2, 1.8],
    filename="table_p2_07_odd_even.png",
    title="Odd vs Even Asymmetry — 31% Dominance",
    highlight_rows={0},
    red_cells={(0, 1)},
    figw=8,
)

# 08: Macrocycle Peaks (L213)
fw_table(
    data=[
        ["Peak", "Offset", "Enrichment", "Calendar Time"],
        ["1", "T+105", "3.0×", "5 months"],
        ["Valley", "T+280", "0.5×", "13 months"],
        ["2", "T+385", "1.4×", "18 months"],
        ["Valley", "T+420", "0.9×", "20 months"],
        ["Valley", "T+560", "0.7×", "26 months"],
        ["**3**", "**T+595**", "**2.1×**", "**28 months**"],
        ["Valley", "T+735", "0.3×", "34 months"],
        ["**4**", "**T+1575**", "**2.4×**", "**6.25 years**"],
    ],
    col_widths=[0.8, 1.0, 1.0, 1.2],
    filename="table_p2_08_macrocycle.png",
    title="The ~2.5-Year Macrocycle",
    highlight_rows={5, 7},
    red_cells={(5, 2), (7, 2)},
    figw=8,
)

# 09: Obligation Echo Gauge (L253)
fw_table(
    data=[
        ["Seed Date", "FTD Shares", "Scaled", "Remaining", "MTM @ $25", "Cycles"],
        ["Dec 4, 2025", "2,068,490", "~14.7M", "**~12.6M**", "~$316M", "1"],
        ["Jun 13, 2025", "1,531,842", "~10.9M", "**~5.1M**", "~$128M", "5"],
        ["Oct 10, 2025", "916,384", "~6.5M", "**~4.8M**", "~$120M", "2"],
        ["Jul 26, 2022", "1,637,150", "~11.6M", "~0.1M", "~$3M", "26"],
    ],
    col_widths=[1.2, 1.0, 0.8, 0.9, 0.8, 0.6],
    filename="table_p2_09_obligation_gauge.png",
    title="Obligation Echo Gauge — Upper-Bound Estimate",
    highlight_rows={0},
    red_cells={(0, 3), (0, 4)},
    figw=10,
)

# 10: Tenor Mix (L273)
fw_table(
    data=[
        ["Tenor", "% of Trades", "% of Hedging Energy"],
        ["0DTE", "10.8%", "0.0%"],
        ["1–7d", "47.5%", "4.7%"],
        ["8–30d", "24.3%", "11.5%"],
        ["31–90d", "8.7%", "13.0%"],
        ["91d–1yr", "4.8%", "22.5%"],
        ["**1yr+ (LEAPS)**", "**3.9%**", "**48.1%**"],
    ],
    col_widths=[1.5, 1.0, 1.2],
    filename="table_p2_10_tenor_mix.png",
    title="Options Tenor Mix — 3.9% of Trades, 48% of Energy",
    highlight_rows={5},
    red_cells={(5, 2)},
    figw=7,
)

# 11: Energy Discharge Cycles (L298)
fw_table(
    data=[
        ["#", "Peak Date", "Peak Energy", "Discharge", "Duration"],
        ["2", "Jan 28, 2021", "5,555,228", "55.2%", "25 days"],
        ["6", "May 28, 2024", "5,299,154", "86.0%", "86 days"],
        ["8", "Apr 7, 2025", "3,443,623", "59.2%", "30 days"],
        ["**11**", "**Jan 21, 2026**", "**2,508,977**", "**Active**", "—"],
    ],
    col_widths=[0.4, 1.2, 1.0, 0.8, 0.8],
    filename="table_p2_11_energy_discharge.png",
    title="Accumulate → Discharge Cycles",
    highlight_rows={3},
    red_cells={(3, 3)},
    figw=8,
)

# 12: XRT Coupling (L325)
fw_table(
    data=[
        ["GME spike → XRT echo", "Enrichment"],
        ["T+0", "0.8×"],
        ["T+3", "**2.0×**"],
        ["T+10", "**2.3×**"],
        ["T+21", "0.0×"],
        ["T+35", "0.9×"],
    ],
    col_widths=[2.0, 1.0],
    filename="table_p2_12_xrt_coupling.png",
    title="XRT Coupled Oscillator — Propagation Delay",
    highlight_rows={1, 2},
    red_cells={(1, 1), (2, 1)},
    figw=6,
)

# 13: Convergence Calendar (L392)
fw_table(
    data=[
        ["Node", "Date", "Signal Retained", "Event"],
        ["T+25", "Jan 8, 2026", "90%", "Statutory wall"],
        ["T+35", "Jan 22, 2026", "86%", "Composite echo"],
        ["T+70", "Mar 12, 2026", "74%", "2nd periodic echo"],
        ["**T+105**", "**Apr 30, 2026**", "**63%**", "**LCM convergence (amplified)**"],
        ["T+126", "May 29, 2026", "58%", "6-month swap expiry"],
        ["**T+140**", "**Jun 18, 2026**", "**54%**", "**Novation Crush**"],
    ],
    col_widths=[0.8, 1.2, 1.0, 2.2],
    filename="table_p2_13_convergence.png",
    title="Convergence Calendar — Dec 4, 2025 Mega-Seed",
    highlight_rows={3, 5},
    red_cells={(3, 2), (5, 2)},
    figw=9,
)

# 14: 6-Year Echoes (L412)
fw_table(
    data=[
        ["Date", "Event", "Original FTD"],
        ["May 1", "6yr echo of Apr 17, 2020", "2,105,715 (largest 2020 spike)"],
        ["May 5", "6yr echo of Apr 21, 2020", "1,932,850"],
        ["May 13", "6yr echo of Apr 29, 2020", "1,119,476"],
        ["May 14", "6yr echo of Apr 30, 2020", "1,284,867"],
        ["May 15", "6yr echo of May 1, 2020", "1,380,982"],
    ],
    col_widths=[0.8, 2.0, 2.0],
    filename="table_p2_14_six_year_echoes.png",
    title="The Floodgates — May 2026 Terminal Echoes",
    highlight_rows={0},
    red_cells={(0, 2)},
    figw=8,
    max_col_chars={2: 35},
)

# 15: Standing Wave Model (L435)
fw_table(
    data=[
        ["Component", "Mechanism", "Evidence"],
        ["Fundamental freq", "T+25 BD (Rule 204(a)(2))", "3.40× peak"],
        ["Composite echo", "T+25 + T+10 options bridge = T+35", "23.4× phantom OI"],
        ["Q-factor", "20.6 (86% retention/cycle)", "Exponential fit, 20 harmonics"],
        ["LCM convergence", "T+35 × T+21 = T+105", "2.99× at T+105"],
        ["Coupling", "XRT basket energy transfer", "Anti-correlated (p=0.016)"],
        ["Leakage", "~14% amplitude decay/cycle", "Temporal signal measure"],
        ["Stored energy", "Upper-bound from 7.1× scaling", "Obligation Echo Gauge"],
    ],
    col_widths=[1.3, 2.0, 1.8],
    filename="table_p2_15_standing_wave.png",
    title="The Complete Standing Wave Model",
    figw=9,
    max_col_chars={1: 30, 2: 30},
)


# ═══════════════════════════════════════════════════════════════════════════════
# POST 3: The Cavity
# ═══════════════════════════════════════════════════════════════════════════════

print("\nPost 3 — The Cavity:")

# 01: Glossary (L13)
fw_table(
    data=[
        ["Term", "What It Means"],
        ["**Full periodogram**", "Spectral analysis of the entire unsegmented time series."],
        ["**Spectral coherence**", "Matching frequencies across independent securities."],
        ["**ODI (κ)**", "Obligation Distortion Index. κ>1 = nonlinear clipping."],
        ["**LCM convergence**", "T+35 × T+21 alignment at T+105."],
    ],
    col_widths=[1.4, 4.0],
    filename="table_p3_01_glossary.png",
    title="Key Terms — Part 3",
    figw=9,
    max_col_chars={1: 55},
)

# 02: Spectral Peaks (L28)
fw_table(
    data=[
        ["Period (BD)", "Power (×median)", "What It Is"],
        ["~630", "**13.3×**", "~2.5 year macrocycle"],
        ["~315", "5.4×", "Half-macrocycle"],
        ["~210", "4.7×", "Third-macrocycle"],
        ["~105", "3.8×", "LCM convergence (T+35 × T+21)"],
        ["~35", "2.9×", "Composite settlement echo"],
        ["~25", "3.4×", "Statutory wall (fundamental)"],
    ],
    col_widths=[1.0, 1.2, 2.5],
    filename="table_p3_02_spectral.png",
    title="Spectral Peaks — GME Settlement Frequencies",
    highlight_rows={0},
    red_cells={(0, 1)},
    figw=8,
)

# 03: Cross-Asset Fingerprint (L65)
fw_table(
    data=[
        ["Asset", "Settlement Freqs", "~630bd Region", "Classification"],
        ["**GME**", "Strong T+33, T+105", "**13.3×**", "Primary oscillator"],
        ["**AMC**", "Strong", "**Elevated**", "Swap basket member"],
        ["**KOSS**", "Present (inherited)", "**Elevated**", "Phantom limb (no options)"],
        ["**XRT**", "Present", "**Elevated**", "ETF transmission"],
        ["TSLA", "Moderate", "Moderate", "Possible separate basket"],
        ["IWM", "Noise", "Noise", "Control: clean"],
        ["AAPL", "Noise", "Noise", "Control: clean"],
        ["MSFT", "Noise", "Noise", "Control: clean"],
    ],
    col_widths=[0.8, 1.5, 1.0, 1.8],
    filename="table_p3_03_crossasset.png",
    title="Cross-Asset Spectral Fingerprint",
    highlight_rows={0, 1, 2, 3},
    green_cells={(0, 2), (1, 2), (2, 2), (3, 2)},
    figw=9,
)

# 04: BBBY Post-Delisting Fluctuation (L112)
fw_table(
    data=[
        ["Metric", "Value"],
        ["Unique post-delisting values", "**31**"],
        ["Day-to-day changes (non-zero)", "**30 of 30**"],
        ["Std dev of changes", "**12,586 shares**"],
        ["Range of values", "30 to 29,857 shares"],
    ],
    col_widths=[2.0, 1.5],
    filename="table_p3_04_bbby_fluctuation.png",
    title="BBBY Post-Delisting FTDs — Active Fluctuation",
    highlight_rows={0, 1},
    red_cells={(0, 1), (1, 1), (2, 1)},
    figw=7,
)

# 05: Obligation Distortion Index (L147)
fw_table(
    data=[
        ["Asset", "κ (ODI)", "Interpretation"],
        ["**BBBY**", "**9.28**", "Extreme clipping (sealed cavity)"],
        ["AMC", "2.97", "Moderate clipping"],
        ["XRT", "1.85", "Mild clipping"],
        ["KOSS", "1.34", "Mild clipping"],
        ["GME", "1.18", "Near-linear"],
        ["IWM", "0.82", "Linear (control)"],
        ["MSFT", "0.67", "Linear (control)"],
    ],
    col_widths=[0.8, 0.8, 2.0],
    filename="table_p3_05_odi.png",
    title="Obligation Distortion Index (κ)",
    highlight_rows={0},
    red_cells={(0, 1)},
    figw=7,
)

# 06: Per-Offering Impact (L175)
fw_table(
    data=[
        ["Offering", "Shares", "T+33 Change", "Mean FTD"],
        ["Apr 2021", "3.5M @ $157", "−43%", "**−85%**"],
        ["Jun 2021", "5M @ $225", "−36%", "−60%"],
        ["May 2024", "45M @ $23", "**−82%**", "−55%"],
        ["Jun 2024", "75M @ $24", "**−82%**", "−58%"],
    ],
    col_widths=[1.0, 1.2, 1.0, 1.0],
    filename="table_p3_06_per_offering.png",
    title="Per-Offering Impact on Settlement Harmonics",
    highlight_rows={2, 3},
    red_cells={(0, 3), (2, 2), (3, 2)},
    figw=8,
)

# 07: Relief Valve (L186)
fw_table(
    data=[
        ["Metric", "Pre-2024", "Post-2024"],
        ["Mean FTD", "**392,415**", "62,818"],
        ["T+33 echo rate", "**84%**", "100% (via TRF)"],
        ["Primary channel", "Options (phantom OI)", "TRF internalization"],
    ],
    col_widths=[1.5, 1.5, 1.5],
    filename="table_p3_07_relief_valve.png",
    title="Relief Valve — Share Offering Impact",
    highlight_rows={0},
    red_cells={(0, 1)},
    green_cells={(0, 2)},
    figw=8,
)

# 08: Confirmed Basket Components (L209)
fw_table(
    data=[
        ["Asset", "Evidence"],
        ["**BBBY**", "Strongest signal (sealed cavity, delisted, ex-clearing proof)"],
        ["**AMC**", "Strong spectral coherence, swap basket member"],
        ["**GME**", "Anchor (generates T+33, primary oscillator)"],
        ["**KOSS**", "Phantom limb (no options chain, inherited from basket)"],
        ["**TSLA**", "Moderate — possible separate basket, same mechanism"],
        ["**XRT**", "ETF transmission mechanism"],
    ],
    col_widths=[0.8, 3.5],
    filename="table_p3_08_basket_confirmed.png",
    title="Swap Basket — Confirmed Components",
    green_cells={(0, 0), (1, 0), (2, 0), (3, 0)},
    figw=8,
    max_col_chars={1: 50},
)

# 09: Not in the Basket (L220)
fw_table(
    data=[
        ["Asset", "Status"],
        ["EXPR", "No signal (marginal data length)"],
        ["NAKD/CENN", "No signal"],
        ["IWM", "Control: noise"],
        ["AAPL", "Control: noise"],
        ["MSFT", "Control: noise"],
    ],
    col_widths=[1.0, 2.5],
    filename="table_p3_09_basket_negative.png",
    title="Not in the Basket — Negative Results",
    figw=6,
)


# ═══════════════════════════════════════════════════════════════════════════════
# POST 4: What the SEC Report Got Wrong
# ═══════════════════════════════════════════════════════════════════════════════

print("\nPost 4 — What the SEC Report Got Wrong:")

# 01: Glossary (L27)
fw_table(
    data=[
        ["Term", "What It Means"],
        ["**Gamma Squeeze**", "MM buys stock to hedge calls, pushes price up, forcing more buying."],
        ["**Delta Hedge**", "Buying/selling shares proportional to options exposure to stay neutral."],
        ["**Put-Call Parity**", "Math relationship between puts, calls, and stock. If broken = unusual."],
        ["**Conversion**", "Buy call + sell put + sell stock. Creates synthetic settlement locate."],
        ["**CAT**", "Consolidated Audit Trail. FINRA database tracking every trade."],
        ["**ECP Charge**", "Excess Capital Premium. NSCC charge when risk-to-capital is too high."],
    ],
    col_widths=[1.2, 4.0],
    filename="table_p4_01_glossary.png",
    title="Key Terms — Part 4",
    figw=9,
    max_col_chars={1: 55},
)

# 02: Conversion-Driven Evidence (L52)
fw_table(
    data=[
        ["Metric", "Value"],
        ["OCC Origin Code breakdown", "49.4% of Firm (F) volume = single conversion"],
        ["Synthetic price (put-call parity)", "$35.00 (predicted 3 days early, 2.9% error)"],
        ["Lit vs. dark price gap (May 17)", "$12.13 for 4.5 minutes"],
        ["Compliance flag evasion", "99.6% of dark prints missing OPT flag"],
    ],
    col_widths=[2.0, 3.0],
    filename="table_p4_02_conversion_evidence.png",
    title="Conversion-Driven Settlement Architecture",
    red_cells={(3, 1)},
    figw=9,
    max_col_chars={1: 45},
)

# 03: Waterfall Key Nodes — Post 4 Context (L82)
fw_table(
    data=[
        ["Node", "Offset", "Enrichment", "What It Means"],
        ["CNS netting", "T+3", "5.4×", "Synthetic locate before deadline"],
        ["Post-BFMM", "T+6", "7.4×", "Failures surviving T+5 close-out"],
        ["**Volume mode**", "**T+33**", "**18.1×**", "**Maximum reset volume**"],
        ["**Convergent pressure**", "**T+40**", "**40.3×**", "**Economically destructive**"],
        ["Terminal boundary", "T+45", "0.0×", "All obligations resolve"],
    ],
    col_widths=[1.5, 0.7, 0.8, 2.5],
    filename="table_p4_03_waterfall_condensed.png",
    title="Failure Waterfall — Key Nodes (Post 4)",
    highlight_rows={2, 3},
    red_cells={(2, 2), (3, 2)},
    figw=9,
    max_col_chars={3: 35},
)

# 04: TRF Internalization (L186)
fw_table(
    data=[
        ["Date", "Event", "TRF %", "TRF Median", "Lit Median", "Frag Ratio"],
        ["**12/19/2022**", "T+35 close-out", "**41.2%**", "**6 shares**", "35 shares", "**5.8×**"],
        ["12/22/2022", "T+35 deadline", "**41.1%**", "10", "46", "4.6×"],
        ["12/05/2022", "Control", "35.2%", "12", "40", "3.3×"],
    ],
    col_widths=[1.0, 1.0, 0.8, 0.9, 0.9, 0.8],
    filename="table_p4_04_trf.png",
    title="TRF Internalization — FTD Close-Out Days",
    highlight_rows={0},
    red_cells={(0, 2), (0, 3), (0, 5)},
    figw=10,
)

# 05: T+1 Impact (L215)
fw_table(
    data=[
        ["Node", "Pre-T+1", "Post-T+1", "Change"],
        ["Initial settlement", "T+2", "T+1", "Compressed"],
        ["BFMM close-out", "T+5", "T+4", "Compressed"],
        ["**T+13 threshold → T+45 death**", "**Unchanged**", "**Unchanged**", "**None**"],
    ],
    col_widths=[2.5, 1.0, 1.0, 1.0],
    filename="table_p4_05_t1_impact.png",
    title="T+1 Impact — Settlement Changes",
    highlight_rows={2},
    red_cells={(2, 3)},
    figw=9,
)

# 06: SEC Scorecard — Full Evidence Map (L245)
fw_table(
    data=[
        ["#", "SEC Claim", "Page", "Verdict", "Key Evidence"],
        ["1", "No gamma squeeze", "30", "Correct, missed mechanism", "Conversion activity = settlement, not hedging"],
        ["2", "Short covering small fraction", "27", "**Incomplete**", "Only 22 days of CAT history"],
        ["3", "FTDs cleared quickly", "30", "**Incomplete**", "Obligation accelerates T+3 to T+40 (rotation)"],
        ["4", "NSCC rules-based ECP waiver", "32", "**Incomplete**", "Committee had interested clearing members"],
        ["5", "FTDs imperfect measure", "30", "**Incomplete**", "84% echo hit rate, zero controls = organized"],
        ["6", "80% internalization", "38", "Confirmed", "Same infrastructure still operating"],
        ["7", "Shorten settlement cycle", "45", "**Failed**", "T+33 echo 100% in 2025 post-T+1"],
    ],
    col_widths=[0.3, 1.8, 0.4, 1.6, 2.5],
    filename="table_p4_06_sec_scorecard.png",
    title="Seven SEC Claims — Five Years Later",
    highlight_rows={6},
    red_cells={(1, 3), (2, 3), (3, 3), (4, 3), (6, 3)},
    figw=13,
    max_col_chars={3: 18, 4: 40},

)


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE SUMMARY (not tied to a specific post)
# ═══════════════════════════════════════════════════════════════════════════════

print("\nStandalone:")

fw_table(
    data=[
        ["Finding", "Value", "Significance"],
        ["T+33 echo hit rate", "84% (full), 100% (2025)", "Predictive across 5 years"],
        ["Terminal peak enrichment", "**40.3× at T+40**", "Highest signal in dataset"],
        ["Quality factor (Q)", "**~21**", "Should be ≤ 0.5"],
        ["Macrocycle period", "~630 BD (~2.5 years)", "Visible only in basket securities"],
        ["BBBY post-delisting FTDs", "31 unique values", "Active obligation on cancelled CUSIP"],
        ["Control-day trades", "**Zero**", "Not a single deep OTM put on control days"],
        ["Dec 4, 2025 mega-spike", "**2,068,490 FTDs**", "Largest in post-offering era"],
    ],
    col_widths=[1.8, 1.8, 2.0],
    filename="table_p0_00_key_metrics.png",
    title="The Failure Waterfall — Key Metrics",
    highlight_rows={1, 2, 5},
    red_cells={(1, 1), (2, 1), (5, 1), (6, 1)},
    figw=10,
    max_col_chars={2: 35},
)

print("\n✅ All table images generated.")

