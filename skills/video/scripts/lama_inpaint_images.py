#!/usr/bin/env python3
"""Batch inpaint image frames with a TorchScript LaMa model.

Images and masks remain local. Output is lossless PNG; pixels outside the
binary mask are copied from the source exactly. This helper does not encode
or mux a video.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import tempfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
MODEL_MODULO = 8


def parse_roi(value: str | None) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    try:
        parts = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ROI must be x,y,width,height") from exc
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        raise argparse.ArgumentTypeError("ROI must be x,y,width,height with positive dimensions")
    return parts


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_images(path: Path) -> list[Path]:
    if path.is_file():
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(f"Unsupported input image: {path}")
        return [path]
    if not path.is_dir():
        raise ValueError(f"Input does not exist: {path}")
    images = sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise ValueError(f"No supported images in: {path}")
    return images


def mask_for_image(mask_path: Path, image: Path, image_count: int) -> Path:
    if mask_path.is_file():
        return mask_path
    if not mask_path.is_dir():
        raise ValueError(f"Mask does not exist: {mask_path}")
    candidates = [p for p in mask_path.iterdir() if p.is_file() and p.stem == image.stem]
    if len(candidates) != 1:
        if image_count == 1 and len(candidates) == 1:
            return candidates[0]
        raise ValueError(f"Expected one mask named {image.stem}.* in {mask_path}, found {len(candidates)}")
    return candidates[0]


def reject_path_collisions(input_path: Path, mask_path: Path, output_path: Path) -> None:
    """Prevent opt-in overwrite from replacing source images or masks."""
    input_resolved = input_path.resolve()
    mask_resolved = mask_path.resolve()
    output_resolved = output_path.resolve()

    if input_path.is_file():
        protected = {input_resolved}
        if mask_path.is_file():
            protected.add(mask_resolved)
        if output_resolved in protected:
            raise ValueError("Output path must differ from the input image and mask")
        if mask_path.is_dir() and (output_resolved == mask_resolved or mask_resolved in output_resolved.parents):
            raise ValueError("Output path must be outside the mask directory")
        return

    if not input_path.is_dir():
        return  # list_images() reports the more specific missing-input error.

    for label, directory in (("input", input_resolved), ("mask", mask_resolved)):
        if directory.is_dir() and (output_resolved == directory or directory in output_resolved.parents):
            raise ValueError(f"Output directory must be outside the {label} directory: {directory}")
    if output_resolved == input_resolved:
        raise ValueError("Output directory must differ from input directory")


def select_device(requested: str) -> torch.device:
    mps_available = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
    if requested == "mps":
        if not mps_available:
            raise RuntimeError("MPS was requested but torch.backends.mps.is_available() is false")
        return torch.device("mps")
    if requested == "cpu":
        return torch.device("cpu")
    if mps_available:
        return torch.device("mps")
    print("WARNING: MPS unavailable; auto mode is falling back to CPU.", file=sys.stderr)
    return torch.device("cpu")


def roi_bounds(width: int, height: int, roi: tuple[int, int, int, int] | None, context: int):
    if roi is None:
        return 0, 0, width, height
    x, y, roi_width, roi_height = roi
    if x < 0 or y < 0 or x >= width or y >= height:
        raise ValueError(f"ROI origin is outside image bounds: {roi}, image={width}x{height}")
    return (
        max(0, x - context),
        max(0, y - context),
        min(width, x + roi_width + context),
        min(height, y + roi_height + context),
    )


def pad_to_modulo(image: np.ndarray, mask: np.ndarray):
    height, width = image.shape[:2]
    pad_h = (-height) % MODEL_MODULO
    pad_w = (-width) % MODEL_MODULO
    if pad_h or pad_w:
        mode = "reflect" if height > 1 and width > 1 else "edge"
        image = np.pad(image, ((0, pad_h), (0, pad_w), (0, 0)), mode=mode)
        mask = np.pad(mask, ((0, pad_h), (0, pad_w)), mode="constant", constant_values=0)
    return image, mask, height, width


def infer_one(model, device: torch.device, image: np.ndarray, mask: np.ndarray):
    padded_image, padded_mask, original_h, original_w = pad_to_modulo(image, mask)
    image_tensor = (
        torch.from_numpy(np.array(padded_image, copy=True, order="C"))
        .permute(2, 0, 1)
        .float()
        .div_(255)
        .unsqueeze(0)
        .to(device)
    )
    mask_tensor = torch.from_numpy((padded_mask > 0).astype(np.float32))[None, None].to(device)
    with torch.inference_mode():
        predicted = model(image_tensor, mask_tensor)
        if device.type == "mps":
            torch.mps.synchronize()
    if (
        not isinstance(predicted, torch.Tensor)
        or predicted.ndim != 4
        or predicted.shape[0] != 1
        or predicted.shape[1] != 3
        or tuple(predicted.shape[2:]) != tuple(image_tensor.shape[2:])
    ):
        raise ValueError(f"Model returned unexpected output: {type(predicted)}")
    predicted = predicted[0, :, :original_h, :original_w].permute(1, 2, 0).float().clamp(0, 1)
    predicted = (predicted * 255).round().byte().cpu().numpy()
    return np.where((mask[:original_h, :original_w] > 0)[:, :, None], predicted, image[:original_h, :original_w])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="One image or a folder of frame images")
    parser.add_argument("--mask", required=True, type=Path, help="One mask PNG or a folder with same-stem masks")
    parser.add_argument("--output", required=True, type=Path, help="PNG path for one input, or output folder for a batch")
    parser.add_argument("--model", required=True, type=Path, help="TorchScript LaMa checkpoint")
    parser.add_argument("--expected-sha256", help="Optional checkpoint digest; fail if it differs")
    parser.add_argument("--device", choices=("auto", "mps", "cpu"), default="auto")
    parser.add_argument("--roi", type=parse_roi, help="Optional full-image x,y,width,height around the target")
    parser.add_argument("--context", type=int, default=64, help="Pixels of context around --roi (default: 64)")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing an existing output PNG")
    args = parser.parse_args()

    if args.context < 0:
        parser.error("--context must be non-negative")
    if not args.model.is_file():
        parser.error(f"Model checkpoint does not exist: {args.model}")
    if args.expected_sha256:
        actual_hash = sha256_file(args.model)
        if actual_hash.lower() != args.expected_sha256.lower():
            parser.error(f"Checkpoint SHA-256 mismatch: got {actual_hash}")
    if args.input.is_file() and args.output.suffix.lower() != ".png":
        parser.error("Single-image output must end with .png (lossless output)")

    try:
        reject_path_collisions(args.input, args.mask, args.output)
        images = list_images(args.input)
        device = select_device(args.device)
        print(json.dumps({"event": "model_load_start", "device": str(device)}, ensure_ascii=False), flush=True)
        model = torch.jit.load(str(args.model), map_location="cpu").eval().to(device)
        print(json.dumps({"event": "model_loaded", "torch": torch.__version__, "device": str(device), "mps_available": bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())}, ensure_ascii=False), flush=True)

        if args.input.is_file():
            outputs = [(images[0], args.output)]
            args.output.parent.mkdir(parents=True, exist_ok=True)
        else:
            args.output.mkdir(parents=True, exist_ok=True)
            outputs = [(image, args.output / f"{image.stem}.png") for image in images]

        for index, (image_path, output_path) in enumerate(outputs, start=1):
            if output_path.exists() and not args.overwrite:
                raise FileExistsError(f"Refusing to overwrite existing output (pass --overwrite): {output_path}")
            mask_path = mask_for_image(args.mask, image_path, len(images))
            with Image.open(image_path) as image_file:
                original = np.asarray(image_file.convert("RGB"), dtype=np.uint8)
            with Image.open(mask_path) as mask_file:
                mask_full = np.asarray(mask_file.convert("L"), dtype=np.uint8)
            if original.shape[:2] != mask_full.shape:
                raise ValueError(f"image/mask size mismatch for {image_path.name}: {original.shape[1]}x{original.shape[0]} vs {mask_full.shape[1]}x{mask_full.shape[0]}")
            mask_pixels = np.argwhere(mask_full > 0)
            if not len(mask_pixels):
                raise ValueError(f"Mask contains no marked pixels: {mask_path}")

            x0, y0, x1, y1 = roi_bounds(original.shape[1], original.shape[0], args.roi, args.context)
            if np.any(mask_pixels[:, 1] < x0) or np.any(mask_pixels[:, 1] >= x1) or np.any(mask_pixels[:, 0] < y0) or np.any(mask_pixels[:, 0] >= y1):
                raise ValueError(f"ROI plus context does not contain the full mask for {image_path.name}")
            image_roi = original[y0:y1, x0:x1]
            mask_roi = mask_full[y0:y1, x0:x1]
            start = time.perf_counter()
            restored_roi = infer_one(model, device, image_roi, mask_roi)
            elapsed = time.perf_counter() - start

            # Copy only the ROI output back; outside the mask every input byte
            # is unchanged before lossless PNG encoding.
            result = original.copy()
            result[y0:y1, x0:x1] = restored_roi
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix=f".{output_path.stem}.", suffix=".part", dir=output_path.parent, delete=False) as tmp:
                temporary_path = Path(tmp.name)
            try:
                Image.fromarray(result, mode="RGB").save(temporary_path, format="PNG", optimize=False)
                os.replace(temporary_path, output_path)
            finally:
                temporary_path.unlink(missing_ok=True)
            record = {
                "event": "frame_done",
                "index": index,
                "count": len(outputs),
                "input": image_path.name,
                "mask": mask_path.name,
                "output": str(output_path),
                "device": str(device),
                "roi_xyxy": [x0, y0, x1, y1],
                "mask_pixels": int(np.count_nonzero(mask_full)),
                "elapsed_seconds": round(elapsed, 4),
                "mps_driver_allocated_bytes": int(torch.mps.driver_allocated_memory()) if device.type == "mps" else None,
            }
            print(json.dumps(record, ensure_ascii=False), flush=True)
    except Exception as exc:
        print(json.dumps({"event": "failed", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
