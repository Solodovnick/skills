#!/usr/bin/env python3
"""Replace unique full-page raster images with prepared, same-size PNGs."""

import argparse
from pathlib import Path

import pymupdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--replace", nargs=2, action="append", required=True, metavar=("PAGE", "PNG"),
        help="One-based page number and prepared PNG; repeat for multiple pages",
    )
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        parser.error("output must be a new path distinct from input")

    doc = pymupdf.open(args.input)
    if doc.needs_pass:
        raise SystemExit("PDF needs a password; supply an authorized unlocked copy")
    replacements = {}
    for raw_number, raw_path in args.replace:
        try:
            number = int(raw_number)
        except ValueError:
            parser.error(f"invalid page number: {raw_number}")
        if not 1 <= number <= len(doc) or number in replacements:
            parser.error(f"page out of range or repeated: {number}")
        replacements[number] = Path(raw_path)

    selected = {}
    for number, image_path in replacements.items():
        page = doc[number - 1]
        images = page.get_images(full=True)
        if len(images) != 1:
            raise SystemExit(f"Page {number}: expected one image, found {len(images)}")
        xref = images[0][0]
        rectangles = page.get_image_rects(xref)
        if len(rectangles) != 1 or rectangles[0].get_area() < page.rect.get_area() * 0.95:
            raise SystemExit(f"Page {number}: image does not cover the page")
        original = doc.extract_image(xref)
        prepared = pymupdf.Pixmap(str(image_path))
        if (prepared.width, prepared.height) != (original["width"], original["height"]):
            raise SystemExit(f"Page {number}: replacement pixel dimensions differ")
        selected[number] = (xref, image_path)

    for number, (xref, _) in selected.items():
        users = [i for i, page in enumerate(doc, 1) if any(image[0] == xref for image in page.get_images(full=True))]
        if users != [number]:
            raise SystemExit(f"Page {number}: image XObject {xref} is shared by pages {users}")

    for number, (xref, image_path) in selected.items():
        doc[number - 1].replace_image(xref, filename=str(image_path))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(args.output, garbage=4, deflate=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    result = pymupdf.open(args.output)
    if (len(result) != len(doc) or result.metadata.get("encryption") != doc.metadata.get("encryption")
            or result.permissions != doc.permissions):
        raise RuntimeError("Page count, encryption, or permissions changed")
    print(f"Replaced {len(selected)} page images: {args.output}")


if __name__ == "__main__":
    main()
