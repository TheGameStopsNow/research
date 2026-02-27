#!/usr/bin/env python3
"""
ulysses_sync.py — One-way sync: Git markdown → Ulysses internal library.

Converts a markdown file to Ulysses' XML format and writes it to the
matching sheet's Content.xml, preserving embedded images.

Usage:
    python3 scripts/ulysses_sync.py papers/04_infrastructure_macro.md
    python3 scripts/ulysses_sync.py papers/04_infrastructure_macro.md --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

# Ulysses iCloud root
ULYSSES_ROOT = Path.home() / "Library" / "Mobile Documents" / \
    "X5AZV975AG~com~soulmen~ulysses3"
ULYSSES_GROUP = Path.home() / "Library" / "Group Containers" / \
    "X5AZV975AG.com.soulmen.shared" / "Ulysses"

# The boilerplate <markup> section for Markdown XL
MARKUP_HEADER = '''<sheet version="12" app_version="39.4" known_version="14">
<markup version="3" identifier="markdownxl" displayName="Markdown XL">
\t<tag definition="heading1" pattern="#"></tag>
\t<tag definition="heading2" pattern="##"></tag>
\t<tag definition="heading3" pattern="###"></tag>
\t<tag definition="heading4" pattern="####"></tag>
\t<tag definition="heading5" pattern="#####"></tag>
\t<tag definition="heading6" pattern="######"></tag>
\t<tag definition="divider" pattern="----"></tag>
\t<tag definition="filename" pattern="@:"></tag>
\t<tag definition="blockquote" pattern="&gt;"></tag>
\t<tag definition="comment" pattern="%%"></tag>
\t<tag definition="orderedList" pattern="\\d."></tag>
\t<tag definition="unorderedList" pattern="*"></tag>
\t<tag definition="unorderedList" pattern="+"></tag>
\t<tag definition="unorderedList" pattern="-"></tag>
\t<tag definition="codeblock" pattern="''"></tag>
\t<tag definition="codeblock" pattern="``"></tag>
\t<tag definition="nativeblock" pattern="~~"></tag>
\t<tag definition="table" pattern="(tbl)"></tag>
\t<tag definition="code" startPattern="`" endPattern="`"></tag>
\t<tag definition="delete" startPattern="||" endPattern="||"></tag>
\t<tag definition="emph" startPattern="*" endPattern="*"></tag>
\t<tag definition="emph" startPattern="_" endPattern="_"></tag>
\t<tag definition="inlineComment" startPattern="++" endPattern="++"></tag>
\t<tag definition="inlineNative" startPattern="~" endPattern="~"></tag>
\t<tag definition="mark" startPattern="::" endPattern="::"></tag>
\t<tag definition="strong" startPattern="**" endPattern="**"></tag>
\t<tag definition="strong" startPattern="__" endPattern="__"></tag>
\t<tag definition="annotation" startPattern="{" endPattern="}"></tag>
\t<tag definition="link" startPattern="[" endPattern="]"></tag>
\t<tag definition="footnote" pattern="(fn)"></tag>
\t<tag definition="image" pattern="(img)"></tag>
\t<tag definition="math" pattern="$$"></tag>
\t<tag definition="video" pattern="(vid)"></tag>
</markup>
<string xml:space="preserve">
'''

MARKUP_FOOTER = '</string>\n</sheet>\n'


# ─── XML escaping ───────────────────────────────────────────────────

def xe(text):
    """XML-escape text for Ulysses Content.xml."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


# ─── Inline Markdown → XML ─────────────────────────────────────────

def md_inline(text):
    """Convert markdown inline formatting to Ulysses XML elements."""
    result = []
    i = 0
    n = len(text)

    while i < n:
        # Escaped character: \x
        if text[i] == '\\' and i + 1 < n and text[i + 1] in r'~_*[](){}#+-.!|$`>\\':
            result.append('<escape>\\' + text[i + 1] + '</escape>')
            i += 2
            continue

        # Bold: **...**
        if text[i:i + 2] == '**':
            end = text.find('**', i + 2)
            if end != -1:
                inner = md_inline(text[i + 2:end])
                result.append(
                    f'<element kind="strong" startTag="**" endTag="**">'
                    f'{inner}</element>')
                i = end + 2
                continue

        # Italic: *...* (but not **)
        if (text[i] == '*' and text[i:i + 2] != '**'
                and i + 1 < n and text[i + 1] != '*'):
            end = i + 1
            while end < n:
                end = text.find('*', end)
                if end == -1:
                    break
                if end + 1 < n and text[end + 1] == '*':
                    end += 2
                    continue
                break
            if end != -1 and end > i + 1:
                inner = md_inline(text[i + 1:end])
                result.append(
                    f'<element kind="emph" startTag="*" endTag="*">'
                    f'{inner}</element>')
                i = end + 1
                continue

        # Inline code: `...`
        if text[i] == '`':
            end = text.find('`', i + 1)
            if end != -1:
                code = xe(text[i + 1:end])
                result.append(
                    f'<element kind="code" startTag="`" endTag="`">'
                    f'{code}</element>')
                i = end + 1
                continue

        # Inline math: $...$ (but not $$)
        if text[i] == '$' and (i + 1 < n and text[i + 1] != '$'):
            end = text.find('$', i + 1)
            if end != -1:
                math = xe(text[i + 1:end])
                result.append(
                    f'<element kind="math">'
                    f'<attribute identifier="code">{math}</attribute>'
                    f'</element>')
                i = end + 1
                continue

        # Image: ![alt](url)
        if text[i:i + 2] == '![':
            m = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', text[i:])
            if m:
                alt = xe(m.group(1))
                url = xe(m.group(2))
                result.append(
                    f'<element kind="image">'
                    f'<attribute identifier="URL">{url}</attribute>'
                    f'<attribute identifier="description">{alt}</attribute>'
                    f'</element>')
                i += m.end()
                continue

        # Link: [text](url)
        if text[i] == '[' and (i == 0 or text[i - 1] != '!'):
            m = re.match(r'\[([^\]]*)\]\(([^)]+)\)', text[i:])
            if m:
                link_text = md_inline(m.group(1))
                url = xe(m.group(2))
                result.append(
                    f'<element kind="link">'
                    f'<attribute identifier="URL">{url}</attribute>'
                    f'{link_text}</element>')
                i += m.end()
                continue

        # Regular character
        result.append(xe(text[i]))
        i += 1

    return ''.join(result)


# ─── Block-level Markdown → XML ────────────────────────────────────

def md_line_to_p(line):
    """Convert a single markdown line to a <p> element string."""
    # Empty line
    if not line.strip():
        return '<p></p>'

    # Heading
    m = re.match(r'^(#{1,6})\s+(.*)', line)
    if m:
        level = len(m.group(1))
        tag = m.group(1)
        body = md_inline(m.group(2))
        return (f'<p><tags><tag kind="heading{level}">'
                f'{tag} </tag></tags>{body}</p>')

    # Horizontal rule
    if re.match(r'^---+\s*$', line):
        return '<p><tags><tag kind="divider">---- </tag></tags></p>'

    # Blockquote
    m = re.match(r'^>\s?(.*)', line)
    if m:
        body = md_inline(m.group(1))
        return f'<p><tags><tag kind="blockquote">&gt; </tag></tags>{body}</p>'

    # Unordered list
    m = re.match(r'^(\s*)([-*+])\s+(.*)', line)
    if m:
        indent = m.group(1)
        marker = m.group(2)
        body = md_inline(m.group(3))
        prefix = indent + marker + ' '
        # Ulysses uses tab for indented list items
        tabs = '\t' * (len(indent) // 2) if indent else ''
        return (f'<p><tags><tag kind="unorderedList">'
                f'{tabs}{marker} </tag></tags>{body}</p>')

    # Ordered list
    m = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
    if m:
        num = m.group(2)
        body = md_inline(m.group(3))
        return (f'<p><tags><tag kind="orderedList">'
                f'{num}. </tag></tags>{body}</p>')

    # Standalone image line
    m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', line)
    if m:
        alt = xe(m.group(1))
        url = xe(m.group(2))
        return (f'<p><element kind="image">'
                f'<attribute identifier="URL">{url}</attribute>'
                f'<attribute identifier="description">{alt}</attribute>'
                f'</element></p>')

    # Regular paragraph
    return f'<p>{md_inline(line)}</p>'


def md_table_to_p(table_lines):
    """Convert markdown table lines to a Ulysses XML table paragraph."""
    if len(table_lines) < 2:
        return [md_line_to_p(l) for l in table_lines]

    # Parse header
    header_cells = [c.strip() for c in table_lines[0].strip().strip('|').split('|')]

    # Parse alignment from separator row
    sep_cells = [c.strip() for c in table_lines[1].strip().strip('|').split('|')]
    alignments = []
    for s in sep_cells:
        if s.startswith(':') and s.endswith(':'):
            alignments.append('center')
        elif s.endswith(':'):
            alignments.append('right')
        else:
            alignments.append('natural')

    # Extend alignments if needed
    while len(alignments) < len(header_cells):
        alignments.append('natural')

    # Parse data rows
    data_rows = []
    for line in table_lines[2:]:
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        data_rows.append(cells)

    # Build Ulysses table XML
    cols = ''.join(
        f'<column alignment="{a}" sizingMode="fill"></column>'
        for a in alignments
    )

    def make_row(cells, header=False):
        row_attr = ' header="YES"' if header else ''
        row_cells = ''
        for c in cells:
            cell_content = md_inline(c) if c else ''
            row_cells += (
                f'<cell><string xml:space="preserve">\n'
                f'<p>{cell_content}</p>\n'
                f'</string></cell>'
            )
        return f'<row{row_attr}>{row_cells}</row>'

    header_row = make_row(header_cells, header=True)
    body_rows = ''.join(make_row(r) for r in data_rows)

    table_xml = (
        f'<p><tags><tag kind="table">\ufffc</tag></tags>'
        f'<attribute identifier="table">'
        f'<table>{cols}{header_row}{body_rows}</table>'
        f'</attribute></p>'
    )
    return [table_xml]


def md_to_paragraphs(md_text):
    """Convert full markdown text to list of Ulysses XML <p> strings."""
    lines = md_text.split('\n')
    paragraphs = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Fenced code block
        if line.strip().startswith('```'):
            lang = line.strip()[3:].strip()
            paragraphs.append(
                f'<p><tags><tag kind="codeblock">`` </tag></tags>{xe(lang)}</p>'
            )
            i += 1
            while i < n and not lines[i].strip().startswith('```'):
                paragraphs.append(
                    f'<p><tags><tag kind="codeblock">`` </tag></tags>'
                    f'{xe(lines[i])}</p>'
                )
                i += 1
            if i < n:
                # closing ```
                paragraphs.append(
                    '<p><tags><tag kind="codeblock">`` </tag></tags></p>'
                )
                i += 1
            continue

        # Table block (| ... | with separator row)
        if (line.strip().startswith('|')
                and i + 1 < n
                and re.match(r'^\s*\|[-:\s|]+\|\s*$', lines[i + 1])):
            table_lines = []
            while i < n and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            paragraphs.extend(md_table_to_p(table_lines))
            continue

        # Regular line
        paragraphs.append(md_line_to_p(line))
        i += 1

    return paragraphs


# ─── Ulysses Sheet Discovery ───────────────────────────────────────

def find_all_sheets():
    """Find all .ulysses sheet bundles."""
    sheets = []
    for root_dir in [ULYSSES_ROOT, ULYSSES_GROUP]:
        if not root_dir.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Skip trash
            if 'Trash' in dirpath:
                continue
            p = Path(dirpath)
            if p.suffix == '.ulysses' and (p / 'Content.xml').exists():
                sheets.append(p)
    return sheets


def extract_sheet_title(sheet_path):
    """Extract the first heading from a Ulysses sheet."""
    content_xml = sheet_path / 'Content.xml'
    try:
        with open(content_xml, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return ''

    # Find first heading1 content
    m = re.search(
        r'<tag kind="heading1">[^<]*</tag></tags>([^<]+)</p>',
        text
    )
    return m.group(1).strip() if m else ''


def find_matching_sheet(md_path):
    """Find the Ulysses sheet matching a Git markdown file."""
    # Extract title from the markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('# '):
                md_title = line[2:].strip()
                break
        else:
            print("  Error: No H1 heading found in markdown file")
            return None

    print(f"  Looking for: \"{md_title[:60]}...\"")

    sheets = find_all_sheets()
    best_match = None
    best_score = 0.0

    for sheet in sheets:
        sheet_title = extract_sheet_title(sheet)
        if not sheet_title:
            continue
        score = SequenceMatcher(None, md_title.lower(),
                                sheet_title.lower()).ratio()
        if score > best_score:
            best_score = score
            best_match = sheet

    if best_match and best_score >= 0.6:
        title = extract_sheet_title(best_match)
        print(f"  Found: \"{title[:60]}...\" (score: {best_score:.0%})")
        return best_match

    print(f"  No matching sheet found (best score: {best_score:.0%})")
    return None


# ─── Embedded Image Preservation ───────────────────────────────────

def extract_embedded_images(content_xml_path):
    """Extract embedded image elements from existing Content.xml."""
    images = []
    try:
        with open(content_xml_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return images

    # Find all embedded image elements (with UUID, not URL)
    pattern = re.compile(
        r'<element kind="image">'
        r'<attribute identifier="image">([^<]+)</attribute>'
        r'(?:<attribute identifier="title">([^<]*)</attribute>)?'
        r'(?:<attribute identifier="description">([^<]*)</attribute>)?'
        r'</element>'
    )
    for m in pattern.finditer(text):
        images.append({
            'uuid': m.group(1),
            'title': m.group(2) or '',
            'description': m.group(3) or '',
            'raw': m.group(0),
        })
    return images


def reinsert_embedded_images(paragraphs, embedded_images):
    """Replace URL-based image refs with embedded ones where possible."""
    if not embedded_images:
        return paragraphs

    result = []
    for p in paragraphs:
        # Check if this paragraph is an image with a URL reference
        m = re.search(
            r'<element kind="image">'
            r'<attribute identifier="URL">[^<]+</attribute>'
            r'<attribute identifier="description">([^<]*)</attribute>'
            r'</element>',
            p
        )
        if m:
            alt_text = m.group(1)
            # Try to find a matching embedded image
            best_img = None
            best_score = 0.0
            for img in embedded_images:
                combined = f"{img['title']} {img['description']}"
                # Normalize for comparison
                a = re.sub(r'[^a-z0-9\s]', '', alt_text.lower())
                b = re.sub(r'[^a-z0-9\s]', '', combined.lower())
                score = SequenceMatcher(None, a, b).ratio()
                if score > best_score:
                    best_score = score
                    best_img = img

            if best_img and best_score >= 0.4:
                # Replace URL image with embedded image
                replacement = best_img['raw']
                p = re.sub(
                    r'<element kind="image">'
                    r'<attribute identifier="URL">[^<]+</attribute>'
                    r'<attribute identifier="description">[^<]*</attribute>'
                    r'</element>',
                    replacement,
                    p
                )
        result.append(p)
    return result


# ─── Sync Logic ─────────────────────────────────────────────────────

def build_content_xml(paragraphs, existing_header=None):
    """Assemble a complete Content.xml from paragraph list."""
    header = existing_header or MARKUP_HEADER
    body = '\n'.join(paragraphs)
    return header + body + '\n' + MARKUP_FOOTER


def extract_existing_header(content_xml_path):
    """Extract the <sheet>...<string> header from existing Content.xml."""
    try:
        with open(content_xml_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception:
        return None

    # Everything up to and including <string xml:space="preserve">\n
    m = re.search(r'(.*?<string xml:space="preserve">\n)', text, re.DOTALL)
    return m.group(1) if m else None


def count_changes(md_path, sheet_path):
    """Count differences between Git markdown and Ulysses sheet."""
    # Extract text from Content.xml
    content_xml = sheet_path / 'Content.xml'
    try:
        with open(content_xml, 'r', encoding='utf-8') as f:
            xml_text = f.read()
    except Exception:
        return -1

    # Extract plain text from XML paragraphs
    xml_paragraphs = re.findall(r'<p>(.*?)</p>', xml_text)
    xml_plain = []
    for p in xml_paragraphs:
        # Strip all XML tags to get plain text
        plain = re.sub(r'<[^>]+>', '', p)
        plain = plain.replace('&amp;', '&').replace('&lt;', '<')
        plain = plain.replace('&gt;', '>').replace('&quot;', '"')
        xml_plain.append(plain.strip())

    # Get markdown lines
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()
    md_lines = [l.strip() for l in md_text.split('\n')]

    # Simple diff count
    ops = SequenceMatcher(None, xml_plain, md_lines).get_opcodes()
    changes = sum(1 for op, *_ in ops if op != 'equal')
    return changes


def sync(md_path, sheet_path, dry_run=True):
    """Perform the sync."""
    content_xml = sheet_path / 'Content.xml'

    # Read markdown
    with open(md_path, 'r', encoding='utf-8') as f:
        md_text = f.read()

    # Convert to Ulysses XML paragraphs
    paragraphs = md_to_paragraphs(md_text)

    # Extract and preserve embedded images
    embedded = extract_embedded_images(content_xml)
    if embedded:
        print(f"  📸 Found {len(embedded)} embedded images to preserve")
        paragraphs = reinsert_embedded_images(paragraphs, embedded)

    # Preserve the existing XML header (sheet version, markup definitions)
    header = extract_existing_header(content_xml)

    # Build new Content.xml
    new_xml = build_content_xml(paragraphs, header)

    if dry_run:
        print(f"\n  📋 Dry run — would write {len(new_xml):,} bytes "
              f"({len(paragraphs)} paragraphs)")
        print(f"  📸 {len(embedded)} embedded images would be preserved")

        # Show a text diff summary
        with open(content_xml, 'r', encoding='utf-8') as f:
            old_xml = f.read()
        old_lines = old_xml.split('\n')
        new_lines = new_xml.split('\n')
        ops = SequenceMatcher(None, old_lines, new_lines).get_opcodes()
        changed = sum(1 for op, *_ in ops if op != 'equal')
        print(f"  📝 {changed} diff blocks between old and new XML")
        return True

    # Back up existing Content.xml
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = content_xml.with_name(f'Content.xml.{ts}.bak')
    shutil.copy2(content_xml, backup)
    print(f"  💾 Backed up to {backup.name}")

    # Write new Content.xml
    with open(content_xml, 'w', encoding='utf-8') as f:
        f.write(new_xml)

    print(f"  ✅ Updated Content.xml ({len(new_xml):,} bytes, "
          f"{len(paragraphs)} paragraphs)")
    print(f"  📸 {len(embedded)} embedded images preserved")
    print(f"  ⏱  Ulysses should pick up the change via iCloud sync")
    return True


# ─── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Sync a Git markdown file to its Ulysses sheet'
    )
    parser.add_argument('markdown_file', help='Path to the markdown file')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Show what would change without writing')
    parser.add_argument('--sheet', help='Explicit Ulysses sheet path '
                        '(skip auto-matching)')
    args = parser.parse_args()

    md_path = Path(args.markdown_file).resolve()
    if not md_path.exists():
        print(f"Error: {md_path} does not exist")
        sys.exit(1)

    print(f"\n🔄 Syncing: {md_path.name}")

    # Find matching Ulysses sheet
    if args.sheet:
        sheet_path = Path(args.sheet)
        if not (sheet_path / 'Content.xml').exists():
            print(f"Error: {sheet_path} is not a valid Ulysses sheet")
            sys.exit(1)
    else:
        print(f"\n📚 Searching Ulysses library...")
        sheet_path = find_matching_sheet(md_path)
        if not sheet_path:
            sys.exit(1)

    # Sync
    mode = "DRY RUN" if args.dry_run else "LIVE"
    print(f"\n⚡ Mode: {mode}")
    sync(md_path, sheet_path, dry_run=args.dry_run)

    if args.dry_run:
        print(f"\n💡 To apply: remove --dry-run flag")
    print()


if __name__ == '__main__':
    main()
