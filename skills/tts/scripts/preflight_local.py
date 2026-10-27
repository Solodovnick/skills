#!/usr/bin/env python3
"""Read-only preflight for a local Apple Silicon TTS + MLX Whisper run."""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=('qwen', 'silero'), required=True)
    parser.add_argument('--tts-model', type=Path)
    parser.add_argument('--asr-model', type=Path)
    parser.add_argument('--require-metal', action='store_true')
    args = parser.parse_args()

    checks: dict[str, object] = {
        'python': sys.executable,
        'python_version': platform.python_version(),
        'macos_version': platform.mac_ver()[0],
        'engine': args.engine,
    }
    errors: list[str] = []
    hints: list[str] = []

    if sys.platform == 'darwin' and not checks['macos_version']:
        errors.append('platform.mac_ver() is empty in this process')
        hints.append('Run this same Python in the permitted native environment; check DYLD_LIBRARY_PATH and sandbox access.')
    try:
        import pyexpat  # noqa: F401
        checks['pyexpat_import'] = 'ok'
    except Exception as exc:
        checks['pyexpat_import'] = repr(exc)
        errors.append('pyexpat import failed')
        hints.append('Check the Homebrew expat library path before installing packages or starting a long run.')

    modules = ('torch', 'mlx_whisper') if args.engine == 'silero' else ('mlx_audio', 'mlx_whisper')
    for name in modules:
        try:
            importlib.import_module(name)
            checks[name + '_import'] = 'ok'
        except Exception as exc:
            checks[name + '_import'] = repr(exc)
            errors.append(f'{name} import failed')

    if args.require_metal:
        try:
            import mlx.core as mx
            available = bool(mx.metal.is_available())
            checks['metal_available'] = available
            if not available:
                errors.append('MLX cannot access Metal')
        except Exception as exc:
            checks['metal_available'] = repr(exc)
            errors.append('MLX Metal check failed')
        if any('Metal' in error for error in errors):
            hints.append('Test access outside the restricted environment; do not invalidate completed audio batches.')

    if args.tts_model:
        checks['tts_model'] = str(args.tts_model)
        checks['tts_model_exists'] = args.tts_model.is_file() or args.tts_model.is_dir()
        if not checks['tts_model_exists']:
            errors.append('TTS model path does not exist')

    if args.asr_model:
        folder = args.asr_model
        checks['asr_model'] = str(folder)
        checks['asr_config_exists'] = (folder / 'config.json').is_file()
        checks['asr_weights_exists'] = any((folder / name).is_file() for name in ('weights.safetensors', 'weights.npz'))
        if not checks['asr_config_exists']:
            errors.append('Local ASR config.json is missing')
        if not checks['asr_weights_exists']:
            errors.append('Local MLX Whisper weights.safetensors/weights.npz is missing')
            if (folder / 'model.safetensors').is_file():
                hints.append('Create a weights.safetensors symlink in the work directory; keep the shared model cache unchanged.')

    print(json.dumps({'status': 'passed' if not errors else 'failed', 'checks': checks, 'errors': errors, 'hints': hints}, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == '__main__':
    raise SystemExit(main())
