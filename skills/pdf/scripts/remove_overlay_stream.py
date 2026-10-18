#!/usr/bin/env python3
"""Remove one dedicated, shared PDF text-content stream from selected pages."""

import argparse
import re
from pathlib import Path

import pymupdf


def normalized(value: str) -> str:
    return " ".join(value.split())


def selected_pages(value: str | None, total: int) -> list[int]:
    if value is None:
        return list(range(1, total + 1))
    selected = set()
    for part in value.split(","):
        bounds = part.split("-", 1)
        try:
            first = int(bounds[0])
            last = int(bounds[1]) if len(bounds) == 2 else first
        except ValueError as error:
            raise ValueError(f"Invalid page range: {part}") from error
        if not 1 <= first <= last <= total:
            raise ValueError(f"Page range out of bounds: {part}")
        selected.update(range(first, last + 1))
    return sorted(selected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--text", required=True, help="Exact text this stream must contribute on each page")
    parser.add_argument("--pages", help="One-based page list and ranges, for example 2,4,6-12; default all")
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        parser.error("output must be a new path distinct from input")

    doc = pymupdf.open(args.input)
    if doc.needs_pass:
        raise SystemExit("PDF needs a password; supply an authorized unlocked copy")
    try:
        pages = selected_pages(args.pages, len(doc))
    except ValueError as error:
        parser.error(str(error))
    if not pages:
        parser.error("no pages selected")

    contents = {number: doc[number - 1].get_contents() for number in pages}
    empty = [number for number, streams in contents.items() if not streams]
    if empty:
        raise SystemExit(f"Selected pages have no content stream: {empty}")
    last_streams = [contents[number][-1] for number in pages]
    if len(set(last_streams)) != 1:
        raise SystemExit("Selected pages do not share one final content stream")
    xref = last_streams[0]
    actual_users = [number for number, page in enumerate(doc, 1) if xref in page.get_contents()]
    if actual_users != pages:
        raise SystemExit(f"Content stream {xref} is also used on pages {actual_users}")
    stream = doc.xref_stream(xref)
    if not re.fullmatch(rb"\s*q\s+BT\b.*\bET\s+Q\s*", stream, re.DOTALL):
        raise SystemExit("Final stream is not one self-contained text block")
    if stream.count(b"BT") != 1 or stream.count(b"ET") != 1 or b" Do" in stream or b" BI" in stream:
        raise SystemExit("Final stream may contain other drawing operations")

    before = {number: doc[number - 1].get_text("text") for number in pages}
    for number, text in before.items():
        if text.count(args.text) != 1:
            raise SystemExit(f"Page {number}: target text is not an exact single match")
    links = {number: doc[number - 1].get_links() for number in pages}
    doc.update_stream(xref, b"\n")
    for number in pages:
        page = doc[number - 1]
        if normalized(before[number].replace(args.text, "")) != normalized(page.get_text("text")):
            raise RuntimeError(f"Page {number}: other text changed")
        if links[number] != page.get_links():
            raise RuntimeError(f"Page {number}: links changed")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(args.output, garbage=4, deflate=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    result = pymupdf.open(args.output)
    if (len(result) != len(doc) or result.metadata.get("encryption") != doc.metadata.get("encryption")
            or result.permissions != doc.permissions):
        raise RuntimeError("Page count, encryption, or permissions changed")
    print(f"Removed dedicated stream {xref} from {len(pages)} pages: {args.output}")


if __name__ == "__main__":
    main()
