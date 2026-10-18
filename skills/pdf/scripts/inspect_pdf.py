#!/usr/bin/env python3
"""Print a compact page inventory without copying PDF content to the report."""

import argparse
import json
from pathlib import Path

import pymupdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--needle", help="Count occurrences of this exact text on each page")
    args = parser.parse_args()

    doc = pymupdf.open(args.input)
    if doc.needs_pass:
        raise SystemExit("PDF needs a password; supply an authorized unlocked copy")
    pages = []
    for number, page in enumerate(doc, 1):
        image_blocks = page.get_image_info()
        area = page.rect.width * page.rect.height
        largest_image_fraction = max(
            (pymupdf.Rect(block["bbox"]).get_area() / area for block in image_blocks),
            default=0,
        )
        extracted = page.get_text("text")
        pages.append(
            {
                "page": number,
                "width_pt": round(page.rect.width, 2),
                "height_pt": round(page.rect.height, 2),
                "rotation": page.rotation,
                "text_chars": len(extracted.strip()),
                "image_blocks": len(image_blocks),
                "largest_image_fraction": round(largest_image_fraction, 3),
                "needle_matches": len(page.search_for(args.needle)) if args.needle else None,
            }
        )
    print(
        json.dumps(
            {
                "file": str(args.input),
                "pages": len(doc),
                "encrypted": bool(doc.metadata.get("encryption")),
                "encryption": doc.metadata.get("encryption") or None,
                "permissions": doc.permissions,
                "page_inventory": pages,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
