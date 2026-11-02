# -*- coding: utf-8 -*-
"""Extraction orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .body import dedupe_join, filter_body
from .count import count_words, verdict
from .headings import (BACKMATTER_RE, backmatter_ok, concl_head_ok, find_boundary,
                       find_conclusion, heading_number, references_index)
from .review import Signals, assess
from .text import clean_lines


@dataclass
class Result:
    path: str
    words: int = 0
    verdict: str = "no-body"
    head: str = ""
    head_page: int = 0
    boundary: str = ""
    boundary_page: int = 0
    boundary_kind: str = ""
    pages: int = 0
    raw_lines: int = 0
    kept_lines: int = 0
    excluded_headings: int = 0
    excluded_rows: int = 0
    flags: List[str] = field(default_factory=list)
    confidence: int = 0
    reasons: List[str] = field(default_factory=list)
    text: str = ""

    @property
    def needs_review(self) -> bool:
        return self.confidence < 70

    def as_row(self) -> dict:
        return {
            "path": self.path,
            "words": self.words,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "needs_review": int(self.needs_review),
            "head": self.head,
            "head_page": self.head_page,
            "boundary": self.boundary,
            "boundary_page": self.boundary_page,
            "boundary_kind": self.boundary_kind,
            "pages": self.pages,
            "raw_lines": self.raw_lines,
            "kept_lines": self.kept_lines,
            "excl_headings": self.excluded_headings,
            "excl_rows": self.excluded_rows,
            "flags": "|".join(self.flags),
            "reasons": " | ".join(self.reasons),
        }


def extract(pdf: str, low: int = 250, high: int = 600, skip_ratio: float = 0.15) -> Result:
    """Extract the conclusion section of one PDF and count its words."""
    res = Result(path=pdf, verdict="no-body")

    lines, n_pages = clean_lines(pdf)
    res.pages = n_pages
    res.raw_lines = len(lines)
    if not lines:
        res.flags = ["EMPTY"]
        return res

    lo = int(len(lines) * skip_ratio)
    stop = references_index(lines, lo)
    if stop <= lo:
        stop = len(lines)

    hi, alt, n_heads = find_conclusion(lines, lo, stop)
    if hi < 0:
        sig = Signals(flags=["NO_CONCL_HEAD"], confidence=0,
                      reasons=["no conclusion section found"])
        res.flags, res.confidence, res.reasons = sig.flags, 0, sig.reasons
        res.kept_lines = 0
        return res

    res.head = lines[hi][1]
    res.head_page = lines[hi][0] + 1
    concl_num = heading_number(res.head)

    bidx, kind = find_boundary(lines, hi, concl_num)
    res.boundary_kind = kind
    if bidx is not None:
        res.boundary = lines[bidx][1]
        res.boundary_page = lines[bidx][0] + 1

    chunk = dedupe_join([s for _p, s in lines[hi + 1:(bidx if bidx is not None else len(lines))]])
    kept, drop_head, drop_row = filter_body(chunk)

    res.text = " ".join(kept)
    res.words = count_words(res.text)
    res.verdict = verdict(res.words, low, high)
    res.kept_lines = len(kept)
    res.excluded_headings = drop_head
    res.excluded_rows = drop_row

    sig = assess(res.text, res.words, len(kept), res.head_page, res.boundary_page,
                 alt, n_heads)
    if kind == "none":
        sig.add("NO_BOUNDARY", "no stopping point found; ran to end of document")
    res.flags, res.confidence, res.reasons = sig.flags, sig.confidence, sig.reasons
    return res
