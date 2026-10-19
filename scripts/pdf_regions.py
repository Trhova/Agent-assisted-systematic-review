"""Append auditable column views within mixed-layout PDF pages.

Full-width headings/figures must not suppress recovery of adjacent narrative
columns. Original text and PDF remain authoritative and are never replaced.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException

from scripts.model_backend import atomic_json, digest
from scripts.pdf_layout import has_central_gutter, source_pdf


def column_regions(chars, bbox):
    x0, top, x1, bottom = bbox
    glyphs = [c for c in chars if c.get('text', '').strip() and c.get('top') is not None and c.get('bottom') is not None]
    lines = []
    for char in sorted(glyphs, key=lambda c: c['top']):
        if lines and char['top'] <= lines[-1]['bottom']:
            lines[-1]['bottom'] = max(lines[-1]['bottom'], char['bottom'])
            lines[-1]['chars'].append(char)
        else:
            lines.append({'top': char['top'], 'bottom': char['bottom'], 'chars': [char]})
    middle = (x0 + x1) / 2
    groups = []
    for line in lines:
        crossing = any(c['x0'] < middle < c['x1'] for c in line['chars'])
        if groups and not crossing and not groups[-1]['crossing']:
            groups[-1]['bottom'] = line['bottom']
            groups[-1]['chars'] += line['chars']
        else:
            groups.append({**line, 'crossing': crossing})
    regions = []
    for group in groups:
        if not group['crossing'] and has_central_gutter(group['chars'], x1-x0, x0):
            a, b = max(top, group['top']-0.01), min(bottom, group['bottom']+0.01)
            regions.append([(x0, a, middle, b), (middle, a, x1, b)])
    return regions


def _append_column_view(folder, document):
    if document.get('column_view_version') == 1:
        return document
    pdf = source_pdf(folder, document)
    if pdf is None:
        return document
    original = dict(document)
    raw_hash = hashlib.sha256(Path(pdf).read_bytes()).hexdigest()
    parts = []
    with pdfplumber.open(pdf) as source:
        for index, page in enumerate(source.pages, 1):
            for region, boxes in enumerate(column_regions(page.chars, page.bbox), 1):
                for column, box in enumerate(boxes, 1):
                    parts.append({'page': index, 'region': region, 'column': column,
                                  'bbox': list(box), 'text': page.crop(box).extract_text(x_tolerance=1) or ''})
            page.close()
    projection = {'version': 1, 'pdf_sha256': raw_hash, 'parent_source_sha256': document['sha256'],
                  'method': 'Group vertically overlapping glyphs into rows; full-width crossing rows delimit bands. Split only bands with no central crossing glyph and at least 200 glyphs on each side.',
                  'limitations': 'Alternative narrative reading order only; no OCR or automatic table interpretation. Original full-page text is retained.', 'parts': parts}
    atomic_json(Path(folder)/('column-view-'+raw_hash[:16]+'.json'), projection)
    text = '\n'.join(f"[Original PDF page {p['page']}, region {p['region']}, column {p['column']}]\n{p['text']}" for p in parts)
    document = dict(document)
    if text and len(document['text']) + len(text) < 400_000:
        document['text'] += '\nALTERNATIVE COLUMN VIEW OF THE SAME VERIFIED PRIMARY PDF (original text retained):\n' + text
        document['sha256'] = digest(document['text'])
    document['column_view_version'] = 1
    document['column_view'] = {k:v for k,v in projection.items() if k != 'parts'}
    document['column_view']['appended'] = bool(text and document['sha256'] != original['sha256'])
    atomic_json(Path(folder)/('text.before-columns-'+original['sha256'][:12]+'.json'), original)
    atomic_json(Path(folder)/'text.json', document)
    return document


def append_column_view(folder, document):
    try:
        return _append_column_view(folder, document)
    except PdfminerException as error:
        # Optional parsing failure must preserve already usable primary text;
        # identity and checksum failures deliberately remain fatal.
        atomic_json(Path(folder)/"column-view-error.json", {"parent_source_sha256": document["sha256"], "error": str(error)})
        return document
