# -*- coding: utf-8 -*-
"""Tokenisation and counting.

A word (token) is a whitespace-delimited run containing at least one letter or
digit. Hyphenated compounds and apostrophe contractions count as one word.
Stand-alone punctuation does not count.
"""
from __future__ import annotations

import re

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['\u2019\-][A-Za-z0-9]+)*")
LETTER_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['\u2019\-][A-Za-z]+)*")


def count_words(text: str) -> int:
    """Canonical count: tokens containing at least one alphanumeric character."""
    return len(TOKEN_RE.findall(text))


def count_words_letters_only(text: str) -> int:
    """Strict variant used for cross-checking; drops numbers and page references."""
    return len(LETTER_TOKEN_RE.findall(text))


def count_from_lines(lines) -> int:
    return count_words(" ".join(lines))


def verdict(words: int, low: int = 250, high: int = 600) -> str:
    if not isinstance(words, int) or words <= 0:
        return "no-body"
    if words < low:
        return "too-short"
    if words > high:
        return "too-long"
    return "ok"
