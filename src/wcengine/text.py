# -*- coding: utf-8 -*-
"""PDF text layer, cleaning, and page-furniture removal."""
from __future__ import annotations

import re
from typing import List, Sequence, Tuple

import pypdfium2 as pdfium

Line = Tuple[int, str]          # (page_index, text)
SUBS = {
    "\ufffe": "",               # PDFium decode placeholder, almost always a broken word
    "\x00": " ",
    "\u00a0": " ",
    "\u200b": "",
    "\u2010": "-",
    "\u2011": "-",
    "\u2019": "'",
    "\u2018": "'",
}

PAGE_NO = re.compile(r"^\s*(?:[-–—]\s*)?\d{1,4}(?:\s*[-–—])?\s*$")

# Lines that are never conclusion prose: publisher chrome, licence, download stamps.
FURNITURE: Sequence[re.Pattern] = [
    re.compile(r"(?i)^downloaded (from|by)\b"),
    re.compile(r"(?i)^content uploaded by\b"),
    re.compile(r"(?i)wiley online library"),
    re.compile(r"(?i)^this article is protected by copyright"),
    re.compile(r"(?i)^©\s*\d{4}|^\(c\)\s*\d{4}"),
    re.compile(r"(?i)^all rights reserved"),
    re.compile(r"(?i)^(terms and conditions|privacy policy|cookie)"),
    re.compile(r"(?i)^(creative commons|cc[- ]by)\b"),
    re.compile(r"(?i)^https?://\S+$"),
    re.compile(r"(?i)^doi:\s*10\."),
    re.compile(r"(?i)^(issn|isbn|eissn)\b"),
    re.compile(r"(?i)^(received|accepted|published|revised|first published)\b.*\b\d{4}\b"),
    re.compile(r"(?i)^[A-Z][A-Za-z &:]{3,60}\s*\d{4}\s*;\s*\d+"),   # "Cognitive Linguistics 2016; 27(1): 1-30"
    re.compile(r"(?i)^[A-Z][A-Za-z &:]{3,60}\s+Vol\.?\s*\d+"),
    re.compile(r"(?i)^(volume|vol\.?|issue|no\.)\s*\d+"),
    re.compile(r"(?i)^(table of contents|contents)\s*$"),
    # Elsevier / Emerald page foot: "128 N. Harwood / English for Specific Purposes 68 (2022) 116-130"
    re.compile(r"^\d{1,4}\s+[A-Z]\.\s*[A-Za-z'\-]+.*/\s*[A-Z][A-Za-z &:.]+\s+\d+\s*\(\d{4}\)"),
    re.compile(r"(?i)^[A-Z][A-Za-z'\-]+\s+et\s+al\.?\s*/\s*.+\d{4}"),
    # Transcript notation blocks and data dumps
    re.compile(r"(?i)^transcript\s+key\b"),
]

# Journal-name + page-number running heads ("36 TESOL QUARTERLY").
RUNHEAD_CAPS = (
    re.compile(r"^\d{1,4}\s+[A-Z]{2,}(?:\s+[A-Z][A-Z&]*){1,6}$"),
    re.compile(r"^[A-Z]{2,}(?:\s+[A-Z][A-Z&]*){1,6}\s+\d{1,4}$"),
)
SECTION_WORD = re.compile(
    r"(?i)\b(conclusions?|concluding|discussion|references?|bibliography|introduction|"
    r"method(?:s|ology)?|results?|summary|appendix|appendices|acknowledg\w*|"
    r"limitations?|implications?|funding|notes?|abstract|findings?)\b")


def page_texts(path: str) -> List[str]:
    doc = pdfium.PdfDocument(path)
    try:
        return [
            pg.get_textpage().get_text_range().replace("\r\n", "\n").replace("\r", "\n")
            for pg in doc
        ]
    finally:
        doc.close()


def fix_text(s: str) -> str:
    for a, b in SUBS.items():
        s = s.replace(a, b)
    return re.sub(r"[ \t]+", " ", s)


def norm_key(s: str) -> str:
    """Digit-masked line fingerprint.

    Masking digits is what makes a running head repeat across pages:
    "36 TESOL QUARTERLY" and "37 TESOL QUARTERLY" collapse to one key.
    Without this, page furniture survives at the top of every page.
    """
    s = re.sub(r"\d+", "#", s.strip().lower())
    return re.sub(r"[\W_]+", "", s)[:70]


def is_running_head_caps(s: str) -> bool:
    if not any(r.match(s) for r in RUNHEAD_CAPS):
        return False
    return not SECTION_WORD.search(s)


def is_noise(s: str) -> bool:
    if PAGE_NO.match(s):
        return True
    if is_running_head_caps(s):
        return True
    return any(r.match(s) for r in FURNITURE)


def clean_lines(pdf: str, repeat_ratio: float = 0.30) -> Tuple[List[Line], int]:
    """Return [(page_index, line)] with page furniture removed, plus page count."""
    pages = [fix_text(p) for p in page_texts(pdf)]
    n_pages = len(pages)
    raw: List[Line] = []
    for pi, pg in enumerate(pages):
        for ln in pg.split("\n"):
            s = ln.strip()
            if s:
                raw.append((pi, s))

    seen: dict[str, set] = {}
    for pi, s in raw:
        k = norm_key(s)
        if len(k) >= 6:
            seen.setdefault(k, set()).add(pi)
    thr = max(2, int(n_pages * repeat_ratio))
    furniture = {k for k, ps in seen.items() if len(ps) >= thr}

    out: List[Line] = []
    for pi, s in raw:
        if norm_key(s) in furniture or is_noise(s):
            continue
        out.append((pi, s))
    return out, n_pages
