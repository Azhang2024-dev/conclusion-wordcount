# -*- coding: utf-8 -*-
"""Review signals: contamination detection and a confidence score.

The point of this module is honesty. A word count produced by regex alone is
not self-validating, so every extraction carries a score and an explicit list of
reasons it may be wrong. Anything below the review threshold should be opened
and checked by a human before it is used as corpus evidence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

URL_RE = re.compile(r"(?i)https?://\S+|www\.\S+|10\.\d{4,9}/\S+")
# Data-availability links are normal in a conclusion; they are not contamination.
REPO_URL_RE = re.compile(r"(?i)(doi\.org|osf\.io|figshare|zenodo|dataverse|github\.com|"
                         r"icpsr|ukdataservice|doi\.org/10\.17605)")
REF_TAIL_RE = re.compile(r"(?i)\b(retrieved\s+from|doi:|pp?\.\s*\d+|press\b|routledge|springer|"
                         r"benjamins|palgrave|wiley|elsevier)")
REF_ENTRY_RE = re.compile(r"^[A-Z][A-Za-z'\-]+,\s+[A-Z]\.")
SYMBOL_RE = re.compile(r"[°$*+→§=<>]|--|\(2\.0\)")
SENT_END_RE = re.compile(r"""[.!?"'”’)\]]$""")

# Penalty weights; total is subtracted from 100.
PENALTIES = {
    "NO_CONCL_HEAD": 100,
    "NO_BOUNDARY": 45,
    "TIGHT_SPAN": 15,          # very few lines, boundary on the heading's page
    "SHORT_SPAN": 30,          # fewer than 8 lines kept
    "TRUNC_TAIL": 25,          # body does not end with sentence punctuation
    "URL_IN_BODY": 20,
    "REF_LEAK": 30,
    "REF_ENTRIES": 25,
    "TABLE_LEAK": 20,
    "SYMBOL_DENSE": 20,
    "SPAN_TOO_LARGE": 50,     # a conclusion this long means the boundary failed
    "ALT_HEAD": 8,             # conclusion inferred from a Discussion-type heading
    "MULTI_HEAD": 5,
    "EMPTY": 100,
}
REVIEW_THRESHOLD = 70


@dataclass
class Signals:
    flags: List[str] = field(default_factory=list)
    confidence: int = 100
    reasons: List[str] = field(default_factory=list)

    def add(self, flag: str, reason: str = "") -> None:
        if flag in self.flags:          # a signal is penalised once, not per occurrence
            return
        self.flags.append(flag)
        self.confidence -= PENALTIES.get(flag, 5)
        if reason:
            self.reasons.append(reason)

    @property
    def needs_review(self) -> bool:
        return self.confidence < REVIEW_THRESHOLD


def assess(body: str, words: int, kept_lines: int,
           head_page: int, boundary_page: int, alt: bool,
           n_heads: int) -> Signals:
    sig = Signals()
    if words > 1500:
        # No journal publishes a 2000-word conclusion. The boundary missed.
        sig.add("SPAN_TOO_LARGE", "%d words; the stopping point was not found" % words)
    if words <= 0:
        sig.add("EMPTY", "no prose survived filtering")
        sig.confidence = 0
        return sig

    if alt:
        sig.add("ALT_HEAD", "no Conclusion heading; used a Discussion-type closing section")
    if n_heads > 1:
        sig.add("MULTI_HEAD", "%d conclusion-like headings; the last one was taken" % n_heads)
    if kept_lines < 8:
        sig.add("SHORT_SPAN", "only %d lines kept; boundary may be too near" % kept_lines)
    elif kept_lines < 12 and boundary_page and head_page and boundary_page == head_page:
        # A 250-300 word conclusion routinely fits on one page, so a same-page
        # boundary is only worth flagging when the span is also thin.
        sig.add("TIGHT_SPAN", "%d lines kept between heading and boundary on one page" % kept_lines)

    tail = body.rstrip()
    if tail and not SENT_END_RE.search(tail):
        sig.add("TRUNC_TAIL", "body does not end with sentence punctuation")

    urls = URL_RE.findall(body)
    foreign = [u for u in urls if not REPO_URL_RE.search(u)]
    if foreign or len(urls) >= 3:
        sig.add("URL_IN_BODY", "%d non-repository link(s) inside the body" % len(foreign))

    if len(REF_TAIL_RE.findall(body)) >= 4:
        sig.add("REF_LEAK", "reference-list patterns inside the body")
    if sum(1 for ln in body.split("  ") if REF_ENTRY_RE.match(ln)) >= 2:
        sig.add("REF_ENTRIES", "reference entries inside the body")

    sym = len(SYMBOL_RE.findall(body))
    if sym and sym / max(1.0, words / 100.0) >= 6:
        sig.add("SYMBOL_DENSE", "transcript notation or data dump inside the body")

    sig.confidence = max(0, min(100, sig.confidence))
    return sig
