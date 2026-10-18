#!/usr/bin/env python3
"""Compare PDF structure, extractable text, and rendered pixel changes."""

import argparse
import json
from pathlib import Path

import pymupdf


def normalized(value: str) -> str:
    return " ".join(value.split())


def stable(value):
    if isinstance(value, dict):
        return tuple(sorted((key, stable(item)) for key, item in value.items() if key != "xref"))
    if isinstance(value, (pymupdf.Rect, pymupdf.Point, list, tuple)):
        return tuple(stable(item) for item in value)
    return value


def link_data(page: pymupdf.Page) -> tuple:
    return tuple(stable(link) for link in page.get_links())


def widget_data(page: pymupdf.Page) -> tuple:
    return tuple(
        (widget.field_name, widget.field_value, widget.field_type, stable(widget.rect))
        for widget in page.widgets() or ()
    )


def compare_pixels(source_path: Path, result_path: Path, page_index: int, dpi: int, tolerance: int, allowed: list[pymupdf.Rect]) -> dict:
    matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
    # Fresh documents prevent a renderer cache from carrying page resources
    # between comparisons in some PDFs.
    with pymupdf.open(source_path) as first_doc, pymupdf.open(result_path) as second_doc:
        a = first_doc[page_index].get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB, alpha=False)
        b = second_doc[page_index].get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB, alpha=False)
    if (a.width, a.height, a.n) != (b.width, b.height, b.n):
        raise ValueError("Rendered dimensions differ")
    a_samples = a.samples
    b_samples = b.samples
    left, top, right, bottom = a.width, a.height, -1, -1
    changed = outside = 0
    row_stride = a.width * 3
    for y in range(a.height):
        row = y * row_stride
        for x in range(a.width):
            offset = row + x * 3
            if any(abs(a_samples[offset + c] - b_samples[offset + c]) > tolerance for c in range(3)):
                changed += 1
                left, top = min(left, x), min(top, y)
                right, bottom = max(right, x), max(bottom, y)
                if not any(rect.contains(pymupdf.Point(x * 72 / dpi, y * 72 / dpi)) for rect in allowed):
                    outside += 1
    return {
        "changed_pixels": changed,
        "changed_bbox_px": [left, top, right, bottom] if changed else None,
        "outside_allowed_pixels": outside,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("result", type=Path)
    parser.add_argument("--removed-text", help="Text intentionally removed from every page")
    parser.add_argument("--dpi", type=int, default=96)
    parser.add_argument("--channel-tolerance", type=int, default=0)
    parser.add_argument(
        "--allow-rect", nargs=4, type=float, action="append", metavar=("X0", "Y0", "X1", "Y1"),
        help="Permitted change area in PDF points; repeat for multiple areas",
    )
    parser.add_argument("--max-outside-pixels", type=int, default=0)
    args = parser.parse_args()
    if args.dpi < 36 or not 0 <= args.channel_tolerance <= 255:
        parser.error("invalid DPI or channel tolerance")

    source = pymupdf.open(args.source)
    result = pymupdf.open(args.result)
    if source.needs_pass or result.needs_pass:
        raise SystemExit("A PDF needs a password; supply authorized unlocked copies")
    if len(source) != len(result):
        raise SystemExit(f"Page count changed: {len(source)} -> {len(result)}")

    allowed = [pymupdf.Rect(*values) for values in args.allow_rect or []]
    report = []
    problems = []
    encryption_equal = source.metadata.get("encryption") == result.metadata.get("encryption")
    permissions_equal = source.permissions == result.permissions
    toc_equal = source.get_toc() == result.get_toc()
    if not encryption_equal or not permissions_equal:
        problems.append("Document encryption or permissions changed")
    if not toc_equal:
        problems.append("Document outline changed")
    for number, (before, after) in enumerate(zip(source, result), 1):
        geometry_equal = before.rect == after.rect and before.mediabox == after.mediabox and before.rotation == after.rotation
        source_text = before.get_text("text")
        if args.removed_text:
            source_text = source_text.replace(args.removed_text, "")
        text_equal = normalized(source_text) == normalized(after.get_text("text"))
        links_equal = link_data(before) == link_data(after)
        widgets_equal = widget_data(before) == widget_data(after)
        pixels = compare_pixels(args.source, args.result, number - 1, args.dpi, args.channel_tolerance, allowed)
        row = {
            "page": number,
            "geometry_equal": geometry_equal,
            "text_equal_after_requested_removal": text_equal,
            "links_equal": links_equal,
            "widgets_equal": widgets_equal,
            **pixels,
        }
        report.append(row)
        if not all((geometry_equal, text_equal, links_equal, widgets_equal)):
            problems.append(f"Page {number}: structure or text changed")
        if pixels["outside_allowed_pixels"] > args.max_outside_pixels:
            problems.append(f"Page {number}: changes outside allowed regions")
    print(json.dumps({"source": str(args.source), "result": str(args.result), "encryption_equal": encryption_equal, "permissions_equal": permissions_equal, "outline_equal": toc_equal, "pages": report, "problems": problems}, ensure_ascii=False, indent=2))
    if problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
