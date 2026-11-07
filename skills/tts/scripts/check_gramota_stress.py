#!/usr/bin/env python3
"""Audit prepared Russian text against a local Gramota orthoepic PDF.

Only explicitly printed, stressed word forms count as exact matches. This
script never infers stress for an unlisted inflection and never verifies audio.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

CYRILLIC = re.compile(r'[А-Яа-яЁё\u0301]+')
MARKED_CYRILLIC = re.compile(r'[+А-Яа-яЁё\u0301]+')
VOWELS = set('аеёиоуыэюя')
ENTRY_START = re.compile(r'^\s*[А-ЯЁ][А-ЯЁ\u0301 -]{1,100}(?=[,\\□]|$)')


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def pdf_pages(path: Path) -> list[str]:
    try:
        data = subprocess.check_output(
            ['pdftotext', '-layout', '-enc', 'UTF-8', str(path), '-'],
            stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise SystemExit('Install Poppler (pdftotext) before running this audit') from exc
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.stderr.decode('utf-8', 'replace')) from exc
    pages = data.decode('utf-8').split('\f')
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


def entry_blocks(page: str):
    block = []
    for line in page.splitlines():
        if ENTRY_START.match(line):
            if block:
                yield ' '.join(block)
            block = [line.strip()]
        elif block and line.strip():
            block.append(line.strip())
    if block:
        yield ' '.join(block)


def field_before_pronunciation(block: str) -> str:
    # The dictionary prints grammatical forms before \\ and definitions after □.
    field = re.split(r'\\|□', block, maxsplit=1)[0]
    # Poppler sometimes separates the combining acute from its uppercase
    # headword (e.g. АБА ́ К). Join only uppercase headword fragments.
    field = re.sub(r'([А-ЯЁ])\s+\u0301', lambda m: m.group(1) + '\u0301', field)
    field = re.sub(r'\u0301\s+([А-ЯЁ])', lambda m: '\u0301' + m.group(1), field)
    return field


def stress_variant(token: str):
    letters = []
    stressed = []
    for char in token.lower():
        if char == '\u0301':
            if letters and letters[-1] in VOWELS:
                stressed.append(len(letters) - 1)
        elif 'а' <= char <= 'я' or char == 'ё':
            letters.append(char)
            if char == 'ё':
                stressed.append(len(letters) - 1)
    word = ''.join(letters)
    if sum(c in VOWELS for c in word) < 2 or len(set(stressed)) != 1:
        return None
    return word, stressed[0], token.lower()


def build_index(pages: list[str]):
    index = collections.defaultdict(lambda: collections.defaultdict(set))
    entries = 0
    for page_number, page in enumerate(pages, 1):
        for block in entry_blocks(page):
            field = field_before_pronunciation(block)
            if not field:
                continue
            entries += 1
            for match in CYRILLIC.finditer(field):
                variant = stress_variant(match.group())
                if variant:
                    word, stress, written = variant
                    index[word][stress].add((written, page_number))
    return index, entries


def inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.rglob('*.txt') if p.is_file())
    raise SystemExit(f'Input not found: {path}')


def marked_positions(token: str) -> set[int]:
    letters = []
    positions = set()
    next_stressed = False
    for char in token.lower():
        if char == '+':
            next_stressed = True
        elif char == '\u0301':
            if letters:
                positions.add(len(letters) - 1)
        elif 'а' <= char <= 'я' or char == 'ё':
            letters.append(char)
            if next_stressed or char == 'ё':
                positions.add(len(letters) - 1)
            next_stressed = False
    return positions


def audit(input_path: Path, index, marked_input: Optional[Path] = None) -> dict:
    files = inputs(input_path)
    if not files:
        raise SystemExit('No .txt files found in input directory')
    forms = collections.Counter()
    locations = collections.defaultdict(list)
    per_file = []
    totals = collections.Counter()
    marked_summary = collections.Counter()
    marked_conflicts = []
    marked_unaligned = []
    yo_differences = []
    for path in files:
        counts = collections.Counter()
        source_text = path.read_text(encoding='utf-8')
        source_tokens = [m.group().lower() for m in CYRILLIC.finditer(source_text)
                         if sum(c in VOWELS for c in m.group().lower()) >= 2]
        if marked_input:
            relative = path.relative_to(input_path) if input_path.is_dir() else Path(path.name)
            marked_path = marked_input / relative if marked_input.is_dir() else marked_input
            if not marked_path.is_file():
                raise SystemExit(f'Marked counterpart missing: {marked_path}')
            marked_tokens = [m.group().lower() for m in MARKED_CYRILLIC.finditer(
                marked_path.read_text(encoding='utf-8'))
                if sum(c in VOWELS for c in m.group().lower()) >= 2]
            plain_marked = [t.replace('+', '').replace('\u0301', '').replace('ё', 'е')
                            for t in marked_tokens]
            plain_source = [t.replace('\u0301', '').replace('ё', 'е') for t in source_tokens]
            if plain_source != plain_marked:
                marked_summary['unaligned_file_count'] += 1
                marked_unaligned.append(str(path))
            else:
                marked_summary['aligned_files'] += 1
                for token_index, (source_token, marked_token) in enumerate(zip(source_tokens, marked_tokens)):
                    word = source_token.replace('\u0301', '')
                    marked_word = marked_token.replace('+', '').replace('\u0301', '')
                    if word != marked_word:
                        marked_summary['yo_or_spelling_differences'] += 1
                        if len(yo_differences) < 5000:
                            yo_differences.append({'file': str(path), 'token_index': token_index,
                                                   'source': word, 'marked': marked_word})
                        continue
                    variants = index.get(word)
                    if not variants:
                        continue
                    observed = marked_positions(marked_token)
                    if not observed:
                        marked_summary['unmarked_dictionary_occurrences'] += 1
                        continue
                    marked_summary['compared_dictionary_occurrences'] += 1
                    if observed.isdisjoint(variants):
                        marked_summary['conflicts'] += 1
                        if len(marked_conflicts) < 5000:
                            marked_conflicts.append({'file': str(path), 'token_index': token_index,
                                'word': word, 'marked': marked_token,
                                'expected_letter_indices': sorted(variants)})
        for line_number, line in enumerate(source_text.splitlines(), 1):
            for match in CYRILLIC.finditer(line):
                token = match.group().lower().replace('\u0301', '')
                if sum(c in VOWELS for c in token) < 2:
                    continue
                variants = index.get(token)
                status = ('absent' if not variants else
                          'ambiguous' if len(variants) > 1 else 'exact')
                counts[status] += 1
                totals[status] += 1
                forms[token] += 1
                if status != 'exact' and len(locations[token]) < 20:
                    locations[token].append({'file': str(path), 'line': line_number})
        per_file.append({'path': str(path), 'sha256': digest(path),
                         'eligible_words': sum(counts.values()), **dict(counts)})
    lexicon = {}
    for word, count in sorted(forms.items()):
        variants = index.get(word, {})
        item = {'count': count, 'status': 'absent' if not variants else
                'ambiguous' if len(variants) > 1 else 'exact'}
        if variants:
            item['stresses'] = [
                {'letter_index': stress, 'examples': [
                    {'spelling': written, 'page': page}
                    for written, page in sorted(examples)[:4]]}
                for stress, examples in sorted(variants.items())]
        if item['status'] != 'exact':
            item['locations'] = locations[word]
        lexicon[word] = item
    result = {'source': str(input_path), 'files': per_file,
            'eligible_words': sum(totals.values()),
            'counts': dict(totals), 'unique_forms': len(lexicon),
            'lexicon': lexicon}
    if marked_input:
        result['marked_check'] = {'source': str(marked_input), **dict(marked_summary),
                                  'unaligned_files': marked_unaligned,
                                  'yo_or_spelling_examples': yo_differences,
                                  'conflict_examples': marked_conflicts}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dictionary-pdf', required=True, type=Path)
    parser.add_argument('--input', required=True, type=Path,
                        help='Prepared UTF-8 .txt file or a directory of .txt files')
    parser.add_argument('--marked-input', type=Path,
                        help='Optional matching text(s) marked with + or U+0301 for comparison')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not args.dictionary_pdf.is_file():
        raise SystemExit(f'Dictionary PDF not found: {args.dictionary_pdf}')
    pages = pdf_pages(args.dictionary_pdf)
    index, entries = build_index(pages)
    result = {
        'method': 'Exact printed word forms with stress in the supplied Gramota PDF',
        'limits': ['Unlisted inflections are absent, not inferred',
                   'Homographs with multiple stresses need context review',
                   'Text lookup does not verify acoustic stress or intonation'],
        'dictionary_pdf': str(args.dictionary_pdf),
        'dictionary_sha256': digest(args.dictionary_pdf),
        'dictionary_pages': len(pages), 'entry_blocks': entries,
        'indexed_forms': len(index),
        'indexed_ambiguous_forms': sum(len(v) > 1 for v in index.values()),
        'audit': audit(args.input, index, args.marked_input),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + '.part')
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(args.output)
    print(json.dumps({key: result[key] for key in
                      ('dictionary_pages', 'entry_blocks', 'indexed_forms',
                       'indexed_ambiguous_forms')}, ensure_ascii=False))
    print(json.dumps({key: result['audit'][key] for key in
                      ('eligible_words', 'counts', 'unique_forms')}, ensure_ascii=False))
    if args.marked_input:
        print(json.dumps({key: value for key, value in result['audit']['marked_check'].items()
                          if key not in ('source', 'unaligned_files', 'yo_or_spelling_examples',
                                         'conflict_examples')},
                         ensure_ascii=False))
    print(args.output)


if __name__ == '__main__':
    main()
