# -*- coding: utf-8 -*-
"""Conclusion-section extraction and word-count verification for academic PDFs."""
from .count import count_words, count_words_letters_only, verdict
from .engine import Result, extract
from .review import REVIEW_THRESHOLD, Signals
from .text import clean_lines, page_texts

__version__ = "1.0.0"
__all__ = [
    "extract", "Result", "verdict", "count_words", "count_words_letters_only",
    "clean_lines", "page_texts", "Signals", "REVIEW_THRESHOLD", "__version__",
]
