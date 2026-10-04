#!/usr/bin/env python3
"""Crop a real photograph and add an exact, readable meme caption."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps


DEFAULT_FONTS = (
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--input", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    text = result.add_mutually_exclusive_group(required=True)
    text.add_argument("--text")
    text.add_argument("--text-file", type=Path)
    result.add_argument("--crop", help="left,top,right,bottom in source pixels")
    result.add_argument("--anchor", choices=("top", "bottom"), default="top")
    result.add_argument("--font", type=Path)
    result.add_argument("--font-size", type=int, default=52)
    result.add_argument("--canvas", type=int, default=1080)
    result.add_argument("--brightness", type=float, default=1.0)
    result.add_argument("--contrast", type=float, default=1.04)
    result.add_argument("--panel-alpha", type=int, default=88)
    return result


def resolve_font(explicit: Path | None) -> Path:
    candidates = (explicit,) if explicit else DEFAULT_FONTS
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    raise SystemExit("No bold font found; pass an existing file with --font")


def parse_crop(raw: str | None, size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = size
    if raw:
        try:
            box = tuple(int(value.strip()) for value in raw.split(","))
        except ValueError as error:
            raise SystemExit("--crop must contain four integers") from error
        if len(box) != 4:
            raise SystemExit("--crop must be left,top,right,bottom")
        left, top, right, bottom = box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise SystemExit(f"Crop {box} is outside source size {size}")
        return left, top, right, bottom

    edge = min(width, height)
    left = (width - edge) // 2
    top = (height - edge) // 2
    return left, top, left + edge, top + edge


def load_caption(args: argparse.Namespace) -> str:
    if args.text_file:
        caption = args.text_file.read_text(encoding="utf-8").strip()
    else:
        caption = args.text.replace("\\n", "\n").strip()
    if not caption:
        raise SystemExit("Caption must not be empty")
    return caption


def render(args: argparse.Namespace) -> None:
    source = ImageOps.exif_transpose(Image.open(args.input)).convert("RGB")
    crop = parse_crop(args.crop, source.size)
    image = source.crop(crop).resize(
        (args.canvas, args.canvas), Image.Resampling.LANCZOS
    )
    image = ImageEnhance.Brightness(image).enhance(args.brightness)
    image = ImageEnhance.Contrast(image).enhance(args.contrast)

    caption = load_caption(args)
    font = ImageFont.truetype(str(resolve_font(args.font)), args.font_size)
    rgba = image.convert("RGBA")
    overlay = Image.new("RGBA", rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    spacing = max(7, args.font_size // 6)
    bounds = draw.multiline_textbbox(
        (0, 0), caption, font=font, spacing=spacing, align="left"
    )
    text_width = bounds[2] - bounds[0]
    text_height = bounds[3] - bounds[1]
    margin_x = round(args.canvas * 0.05)
    margin_y = round(args.canvas * 0.045)
    if text_width > args.canvas - 2 * margin_x:
        raise SystemExit(
            "Caption is too wide; add a line break or reduce --font-size"
        )
    if text_height > args.canvas - 2 * margin_y:
        raise SystemExit("Caption is too tall; shorten it or reduce --font-size")
    y = margin_y if args.anchor == "top" else args.canvas - text_height - margin_y

    pad_x = max(18, args.font_size // 2)
    pad_y = max(14, args.font_size // 3)
    panel = (
        margin_x - pad_x,
        y - pad_y,
        args.canvas - margin_x + pad_x,
        y + text_height + pad_y,
    )
    draw.rounded_rectangle(
        panel,
        radius=max(16, args.font_size // 2),
        fill=(0, 0, 0, max(0, min(args.panel_alpha, 255))),
    )
    draw.multiline_text(
        (margin_x, y),
        caption,
        font=font,
        fill=(255, 255, 255, 255),
        spacing=spacing,
        align="left",
        stroke_width=max(2, args.font_size // 17),
        stroke_fill=(0, 0, 0, 235),
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(rgba, overlay).convert("RGB").save(
        args.output, "PNG", optimize=True
    )


def main() -> None:
    args = parser().parse_args()
    if args.canvas < 320:
        raise SystemExit("--canvas must be at least 320")
    if args.font_size < 12:
        raise SystemExit("--font-size must be at least 12")
    render(args)
    print(args.output)


if __name__ == "__main__":
    main()
