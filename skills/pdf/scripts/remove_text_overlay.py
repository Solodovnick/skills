#!/usr/bin/env python3
"""Remove exact, searchable text overlays from selected PDF pages."""

import argparse
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
    parser.add_argument("--text", required=True, help="Exact overlay text")
    parser.add_argument("--pages", help="One-based page list and ranges, for example 2,4,6-12; default all")
    parser.add_argument("--expected-per-page", type=int, default=1)
    args = parser.parse_args()

    if args.input.resolve() == args.output.resolve():
        parser.error("input and output must differ")
    if args.output.exists():
        parser.error("output already exists")
    if args.expected_per_page < 1:
        parser.error("--expected-per-page must be positive")

    doc = pymupdf.open(args.input)
    if doc.needs_pass:
        raise SystemExit("PDF needs a password; supply an authorized unlocked copy")
    try:
        pages = selected_pages(args.pages, len(doc))
    except ValueError as error:
        parser.error(str(error))
    if not pages:
        parser.error("no pages selected")
    locations = {}
    original_texts = {}
    original_links = {}
    for number in pages:
        page = doc[number - 1]
        extracted = page.get_text("text")
        if extracted.count(args.text) != args.expected_per_page:
            raise SystemExit(f"Page {number}: overlay text is not an exact extracted match")
        matches = page.search_for(args.text)
        if len(matches) != args.expected_per_page:
            raise SystemExit(
                f"Page {number}: expected {args.expected_per_page} matches, found {len(matches)}"
            )
        locations[number] = matches
        original_texts[number] = extracted
        original_links[number] = page.get_links()

    for number in pages:
        page = doc[number - 1]
        matches = locations[number]
        original_text = original_texts[number]
        links = original_links[number]
        for rect in matches:
            page.add_redact_annot(rect, fill=False, cross_out=False)
        page.apply_redactions(images=0, graphics=0, text=0)
        if normalized(original_text.replace(args.text, "")) != normalized(page.get_text("text")):
            raise RuntimeError(f"Page {number}: other text changed inside a redaction area")
        if page.get_links() != links:
            raise RuntimeError(f"Page {number}: links changed by redaction")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(args.output, garbage=4, deflate=True, encryption=pymupdf.PDF_ENCRYPT_KEEP)
    result = pymupdf.open(args.output)
    if (len(result) != len(doc) or result.metadata.get("encryption") != doc.metadata.get("encryption")
            or result.permissions != doc.permissions):
        raise RuntimeError("Page count, encryption, or permissions changed")
    for number in pages:
        page = result[number - 1]
        if page.search_for(args.text):
            raise RuntimeError(f"Page {number}: overlay text remains")
    print(f"Removed overlay from {len(pages)} pages: {args.output}")


if __name__ == "__main__":
    main()
