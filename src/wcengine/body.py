# -*- coding: utf-8 -*-
"""Body filtering: sub-headings, table rows, captions, hyphenation repair."""
from __future__ import annotations

import re
from typing import List, Sequence

from .headings import NUM_LEAD, is_title_case

CAPTION_RE = re.compile(
    r"(?i)^\s*(?:table|figure|fig\.?|scheme|plate|chart|exhibit)\s*\d+[a-z]?\b")

WORDISH = re.compile(r"[A-Za-z]{2,}")


def is_table_row(s: str, junk_ratio: float = 0.45) -> bool:
    """A line where fewer than (1 - junk_ratio) of tokens look like words."""
    toks = s.split()
    if len(toks) < 3:
        return False
    junk = sum(1 for t in toks if not WORDISH.search(t))
    return junk / len(toks) >= junk_ratio


def is_subheading(s: str, next_line: str, max_words: int = 9, max_len: int = 95) -> bool:
    """Heading inside the conclusion chapter: numbered, ALL CAPS, or Title Case.

    Body lines wrapped by the PDF rarely satisfy all of (short, no terminal
    punctuation, title case), which keeps false positives low.
    """
    t = s.strip()
    if len(t) > max_len or len(t.split()) > max_words:
        return False
    if t.endswith((",", ";", ":")) or t.endswith("."):
        return False
    if NUM_LEAD.match(t):
        return len(t.split()) <= 12
    if len([c for c in t if c.isalpha()]) < 3:
        return False
    if t.upper() == t and len(t) > 3:
        return True
    if not is_title_case(t):
        return False
    return bool(next_line) and (next_line[:1].isupper() or next_line[:1].isdigit())


def dedupe_join(lines: Sequence[str]) -> List[str]:
    """Repair end-of-line hyphenation: "conclu-" + "sion" -> "conclusion"."""
    out: List[str] = []
    for s in lines:
        if out and re.search(r"[A-Za-z]-$", out[-1]) and s[:1].islower():
            out[-1] = out[-1][:-1] + s
        else:
            out.append(s)
    return out


def filter_body(lines: Sequence[str]) -> tuple[List[str], int, int]:
    """Drop sub-headings, captions and table rows. Return (kept, n_heading, n_row)."""
    kept: List[str] = []
    drop_head = drop_row = 0
    for k, s in enumerate(lines):
        nxt = lines[k + 1] if k + 1 < len(lines) else ""
        if CAPTION_RE.match(s):
            drop_row += 1
            continue
        # Table rows are checked before sub-headings: a data line such as
        # "1 62 63 >4 A5" starts with a digit and would otherwise look numbered.
        if is_table_row(s):
            drop_row += 1
            continue
        if is_subheading(s, nxt):
            drop_head += 1
            continue
        kept.append(s)
    # Only table/caption remnants are trimmed from the tail. Never trim by line length:
    # that silently deletes a legitimate closing line.
    while kept and (is_table_row(kept[-1]) or CAPTION_RE.match(kept[-1])):
        kept.pop()
    return kept, drop_head, drop_row
