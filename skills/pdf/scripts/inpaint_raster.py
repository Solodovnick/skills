#!/usr/bin/env python3
"""Inpaint a prepared mask on one raster page image; keep all other pixels."""

import argparse
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Original page image")
    parser.add_argument("mask", type=Path, help="Same-size grayscale PNG; white marks pixels to repair")
    parser.add_argument("output", type=Path, help="New PNG output")
    parser.add_argument("--radius", type=float, default=5)
    parser.add_argument("--dilate-px", type=int, default=0)
    parser.add_argument("--method", choices=("telea", "ns"), default="telea")
    args = parser.parse_args()
    if args.output.suffix.lower() != ".png" or args.output.exists():
        parser.error("output must be a new PNG path")
    if args.radius <= 0 or args.dilate_px < 0:
        parser.error("radius must be positive and dilate-px nonnegative")

    image = cv2.imread(str(args.image), cv2.IMREAD_UNCHANGED)
    mask = cv2.imread(str(args.mask), cv2.IMREAD_GRAYSCALE)
    if image is None or mask is None:
        raise SystemExit("Cannot read image or mask")
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise SystemExit("Only 8-bit, three-channel page images are supported")
    if image.shape[:2] != mask.shape:
        raise SystemExit("Image and mask dimensions differ")
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    if args.dilate_px:
        size = args.dilate_px * 2 + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
        mask = cv2.dilate(mask, kernel)
    count = cv2.countNonZero(mask)
    if not count:
        raise SystemExit("Mask is empty")

    method = cv2.INPAINT_TELEA if args.method == "telea" else cv2.INPAINT_NS
    repaired = cv2.inpaint(image, mask, args.radius, method)
    if not np.array_equal(repaired[mask == 0], image[mask == 0]):
        raise RuntimeError("Pixels outside the mask changed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(args.output), repaired):
        raise RuntimeError("Could not write output PNG")
    print(f"Repaired {count} pixels at {image.shape[1]}x{image.shape[0]}: {args.output}")


if __name__ == "__main__":
    main()
