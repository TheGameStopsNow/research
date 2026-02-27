#!/usr/bin/env python3
"""
ulysses_extract_images.py — Extract embedded images from Ulysses' internal
storage and place them alongside your markdown files.

Usage:
    python scripts/ulysses_extract_images.py <markdown_file>

The script:
  1. Scans the markdown file for image references: ![...](figures/...)
  2. Checks which referenced images are missing from disk
  3. Searches all Ulysses sheets for matching embedded images
  4. Copies matched images to the correct figures/ path
  5. Reports any unresolved references
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from pathlib import Path

# Ulysses iCloud library root
ULYSSES_ROOT = Path.home() / "Library" / "Mobile Documents" / \
    "X5AZV975AG~com~soulmen~ulysses3"

# Also check non-iCloud Group Container
ULYSSES_GROUP = Path.home() / "Library" / "Group Containers" / \
    "X5AZV975AG.com.soulmen.shared" / "Ulysses"


def find_image_refs(md_path: Path) -> list[dict]:
    """Parse markdown file for image references and check which are missing."""
    text = md_path.read_text(encoding="utf-8")
    # Match ![alt text](path)
    pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    refs = []
    for match in pattern.finditer(text):
        alt_text = match.group(1)
        img_path = match.group(2)
        # Resolve relative to the markdown file's directory
        full_path = (md_path.parent / img_path).resolve()
        refs.append({
            "alt_text": alt_text,
            "rel_path": img_path,
            "full_path": full_path,
            "exists": full_path.exists(),
        })
    return refs


def find_ulysses_sheets() -> list[Path]:
    """Find all .ulysses sheet bundles across iCloud and local storage."""
    sheets = []
    for root in [ULYSSES_ROOT, ULYSSES_GROUP]:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            p = Path(dirpath)
            if p.suffix == ".ulysses" and (p / "Content.xml").exists():
                sheets.append(p)
    return sheets


def parse_sheet_images(sheet_path: Path) -> list[dict]:
    """Parse a Ulysses sheet's Content.xml for image elements."""
    content_xml = sheet_path / "Content.xml"
    if not content_xml.exists():
        return []

    try:
        tree = ET.parse(content_xml)
    except ET.ParseError:
        return []

    images = []
    # Ulysses XML uses <element kind="image"> with <attribute> children
    for elem in tree.iter("element"):
        if elem.get("kind") != "image":
            continue

        img_info = {"sheet": sheet_path}
        for attr in elem.iter("attribute"):
            ident = attr.get("identifier", "")
            text = (attr.text or "").strip()
            if ident == "image":
                # This is the UUID referencing a DraggedImage file
                img_info["uuid"] = text
            elif ident == "URL":
                # This is an external path reference
                img_info["url"] = text
            elif ident == "title":
                img_info["title"] = text
            elif ident == "description":
                img_info["description"] = text
            elif ident == "filename":
                img_info["filename"] = text

        # If we have a UUID, find the actual media file
        if "uuid" in img_info:
            media_dir = sheet_path / "Media"
            if media_dir.exists():
                for f in media_dir.iterdir():
                    if img_info["uuid"] in f.name:
                        img_info["media_file"] = f
                        break

        images.append(img_info)

    return images


def fuzzy_match(text_a: str, text_b: str) -> float:
    """Return similarity ratio between two strings (0.0 to 1.0)."""
    # Normalize: lowercase, strip markdown formatting
    a = re.sub(r'[^a-z0-9\s]', '', text_a.lower())
    b = re.sub(r'[^a-z0-9\s]', '', text_b.lower())
    return SequenceMatcher(None, a, b).ratio()


def match_images(missing_refs: list[dict],
                 ulysses_images: list[dict]) -> list[tuple]:
    """Match missing image references to Ulysses embedded images."""
    matches = []

    for ref in missing_refs:
        alt = ref["alt_text"]
        rel = ref["rel_path"]
        basename = Path(rel).name

        best_match = None
        best_score = 0.0

        for img in ulysses_images:
            if "media_file" not in img:
                continue  # No extractable media

            score = 0.0

            # Strategy 1: Check if the URL path matches
            if img.get("url", "") == rel:
                score = 1.0

            # Strategy 2: Match on description similarity to alt text
            if not score and "description" in img:
                desc_score = fuzzy_match(alt, img["description"])
                if desc_score > score:
                    score = desc_score

            # Strategy 3: Match title + description combined
            if not score:
                combined = f"{img.get('title', '')} {img.get('description', '')}"
                if combined.strip():
                    combo_score = fuzzy_match(alt, combined)
                    if combo_score > score:
                        score = combo_score

            if score > best_score:
                best_score = score
                best_match = img

        if best_match and best_score >= 0.4:
            matches.append((ref, best_match, best_score))
        else:
            matches.append((ref, None, best_score))

    return matches


def main():
    parser = argparse.ArgumentParser(
        description="Extract Ulysses images for a markdown file"
    )
    parser.add_argument("markdown_file", help="Path to the markdown file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without copying")
    parser.add_argument("--threshold", type=float, default=0.4,
                        help="Minimum fuzzy match score (0.0-1.0, default: 0.4)")
    args = parser.parse_args()

    md_path = Path(args.markdown_file).resolve()
    if not md_path.exists():
        print(f"Error: {md_path} does not exist")
        sys.exit(1)

    # Step 1: Find image references
    print(f"\n📄 Scanning: {md_path.name}")
    refs = find_image_refs(md_path)
    if not refs:
        print("   No image references found.")
        return

    existing = [r for r in refs if r["exists"]]
    missing = [r for r in refs if not r["exists"]]

    print(f"   Found {len(refs)} image references: "
          f"{len(existing)} exist, {len(missing)} missing")

    if not missing:
        print("\n✅ All images present. Nothing to do.")
        return

    print(f"\n🔍 Missing images:")
    for r in missing:
        print(f"   ❌ {r['rel_path']}")

    # Step 2: Search Ulysses
    print(f"\n📚 Searching Ulysses library...")
    sheets = find_ulysses_sheets()
    print(f"   Found {len(sheets)} sheets")

    all_images = []
    for sheet in sheets:
        all_images.extend(parse_sheet_images(sheet))

    embedded = [i for i in all_images if "media_file" in i]
    print(f"   Found {len(all_images)} image references, "
          f"{len(embedded)} with extractable media")

    if not embedded:
        print("\n⚠️  No embedded images found in Ulysses. "
              "Your images may be URL-referenced (generated externally).")
        return

    # Step 3: Match
    print(f"\n🔗 Matching missing images to Ulysses media...")
    matches = match_images(missing, all_images)

    resolved = [(r, m, s) for r, m, s in matches if m is not None]
    unresolved = [(r, m, s) for r, m, s in matches if m is None]

    # Step 4: Copy or report
    if resolved:
        print(f"\n{'📋 Would copy' if args.dry_run else '📋 Copying'}:")
        for ref, img, score in resolved:
            src = img["media_file"]
            dst = ref["full_path"]
            desc = img.get("description", img.get("title", ""))[:60]
            print(f"   {'→' if args.dry_run else '✅'} {ref['rel_path']}")
            print(f"      From: {src.name}")
            print(f"      Match: \"{desc}...\" (score: {score:.0%})")

            if not args.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

    if unresolved:
        print(f"\n⚠️  Unresolved ({len(unresolved)} images):")
        for ref, _, score in unresolved:
            print(f"   ❓ {ref['rel_path']}")
            alt_short = ref["alt_text"][:80]
            print(f"      Alt text: \"{alt_short}\"")

        # Show available Ulysses images for manual matching
        if embedded:
            print(f"\n📦 Available Ulysses images ({len(embedded)}):")
            for i, img in enumerate(embedded):
                title = img.get("title", "")
                desc = img.get("description", "")[:60]
                fname = img["media_file"].name
                sheet_name = img["sheet"].stem[:16]
                print(f"   [{i}] {fname} — {title}: {desc}")

    # Summary
    print(f"\n{'─' * 50}")
    total = len(missing)
    ok = len(resolved)
    print(f"Summary: {ok}/{total} missing images "
          f"{'would be' if args.dry_run else ''} resolved from Ulysses")
    if unresolved:
        print(f"         {len(unresolved)} images need manual placement "
              f"(likely generated by scripts)")


if __name__ == "__main__":
    main()
