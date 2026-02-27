#!/usr/bin/env python3
"""
ulysses_export_textbundle.py — Export papers as TextBundle for Ulysses
External Folders with working inline image display.

TextBundle (.textbundle) is a directory containing:
  - text.md       — the markdown content
  - assets/       — images referenced by the markdown
  - info.json     — metadata

Ulysses External Folders fully support TextBundle, rendering images inline.

Usage:
    # Export one paper
    python3 scripts/ulysses_export_textbundle.py papers/06_resonance_and_cavity.md

    # Export all papers
    python3 scripts/ulysses_export_textbundle.py papers/*.md

    # Custom output directory
    python3 scripts/ulysses_export_textbundle.py papers/*.md --output ~/Ulysses-Papers
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def export_textbundle(md_path: Path, output_dir: Path) -> dict:
    """Convert a markdown file to a .textbundle directory."""
    md_text = md_path.read_text(encoding='utf-8')

    # Create textbundle directory
    bundle_name = md_path.stem + '.textbundle'
    bundle_path = output_dir / bundle_name
    assets_path = bundle_path / 'assets'

    # Clean and recreate
    if bundle_path.exists():
        shutil.rmtree(bundle_path)
    bundle_path.mkdir(parents=True)
    assets_path.mkdir()

    # Track results
    copied = 0
    missing = 0
    total = 0

    # Step 1: Resolve reference-style image links
    # Format: ![alt text][image-1]  with  [image-1]: figures/path.png
    ref_defs = {}
    for m in re.finditer(r'^\[([^\]]+)\]:\s*(\S+\.(?:png|jpg|jpeg|gif|svg|webp|tiff))\s*$',
                         md_text, re.MULTILINE | re.IGNORECASE):
        ref_defs[m.group(1)] = m.group(2).strip()

    def replace_ref_def(match):
        """Rewrite reference definitions to point to assets/."""
        nonlocal copied, missing, total
        ref_id = match.group(1)
        img_path = match.group(2).strip()
        src = (md_path.parent / img_path).resolve()
        if src.exists():
            total += 1
            filename = src.name
            dst = assets_path / filename
            if not dst.exists():
                shutil.copy2(src, dst)
            copied += 1
            return f'[{ref_id}]:\tassets/{filename}'
        return match.group(0)

    md_text = re.sub(r'^\[([^\]]+)\]:\s*(\S+\.(?:png|jpg|jpeg|gif|svg|webp|tiff))\s*$',
                     replace_ref_def, md_text,
                     flags=re.MULTILINE | re.IGNORECASE)

    # Step 2: Find and process inline image references: ![alt](path)
    def replace_image(match):
        nonlocal copied, missing, total
        total += 1
        alt = match.group(1)
        img_path = match.group(2)

        # Resolve the source image
        src = (md_path.parent / img_path).resolve()
        if src.exists():
            filename = src.name
            dst = assets_path / filename
            if not dst.exists():
                shutil.copy2(src, dst)
            copied += 1
            # Ulysses renders alt text as a visible caption beneath the image.
            # Use a short alt to prevent Ulysses from duplicating the full
            # caption. The source markdown already has italic caption lines
            # below figures where needed.
            fig_match = re.match(r'(Figure\s+\d+)', alt)
            short_alt = fig_match.group(1) if fig_match else filename
            return f'![{short_alt}](assets/{filename})'
        else:
            missing += 1
            return match.group(0)  # Keep original reference

    new_text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_image, md_text)

    # Step 3: De-duplicate adjacent identical italic caption lines.
    # Some papers have the caption in both alt text AND a separate italic line.
    # After shortening alt text above, the remaining italic line is the sole
    # caption. But if there were TWO identical italic lines, collapse them.
    new_text = re.sub(
        r'(\*[^\n]+\*)\s*\n\s*\n\1',
        r'\1',
        new_text
    )

    # Write text.md
    (bundle_path / 'text.md').write_text(new_text, encoding='utf-8')

    # Write info.json
    info = {
        "version": 2,
        "type": "net.daringfireball.markdown",
        "transient": False,
        "creatorIdentifier": "com.research.ulysses-sync"
    }
    (bundle_path / 'info.json').write_text(
        json.dumps(info, indent=2), encoding='utf-8'
    )

    return {
        'bundle': bundle_path,
        'images_total': total,
        'images_copied': copied,
        'images_missing': missing,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Export papers as TextBundle for Ulysses'
    )
    parser.add_argument('files', nargs='+',
                        help='Markdown files to export')
    parser.add_argument('--output', '-o', default=None,
                        help='Output directory (default: same as source)')
    args = parser.parse_args()

    for filepath in args.files:
        md_path = Path(filepath).resolve()
        if not md_path.exists():
            print(f"  ❌ {filepath}: not found")
            continue
        if not md_path.suffix == '.md':
            continue

        output_dir = Path(args.output).resolve() if args.output else md_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        result = export_textbundle(md_path, output_dir)

        imgs = result['images_copied']
        miss = result['images_missing']
        total = result['images_total']
        name = result['bundle'].name

        status = '✅' if miss == 0 else '⚠️'
        print(f"  {status} {name}: {imgs}/{total} images"
              + (f" ({miss} missing)" if miss else ""))

    print(f"\n  Point Ulysses External Folder at: {output_dir}")


if __name__ == '__main__':
    main()
