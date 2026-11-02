# -*- coding: utf-8 -*-
"""Body filtering rules."""
from wcengine.body import CAPTION_RE, dedupe_join, filter_body, is_subheading, is_table_row


def test_hyphenation_join():
    assert dedupe_join(["the conclu-", "sion of this"]) == ["the conclusion of this"]


def test_hyphenation_join_skips_capitalised_continuation():
    assert dedupe_join(["the conclu-", "Sion"]) == ["the conclu-", "Sion"]


def test_table_row_detection():
    assert is_table_row("1 62 63 >4 A5")
    assert not is_table_row("The results showed a moderate effect across groups")


def test_caption_detection():
    assert CAPTION_RE.match("Table 1. Descriptive statistics")
    assert CAPTION_RE.match("Figure 2")
    assert not CAPTION_RE.match("The table shows the results")


def test_subheading_numbered():
    assert is_subheading("7.1 Patterns of use by Chinese writers", "Notably,")


def test_subheading_rejects_wrapped_prose():
    # a PDF-wrapped sentence: no terminal punctuation but lowercase content words
    assert not is_subheading(
        "Our findings indicate that for RFEP students the number of years since", "redesignation")


def test_filter_body_counts_drops():
    lines = ["Real sentence one.", "7.1 Patterns of use", "Table 2. Data",
             "1 62 63 >4 A5", "Real sentence two."]
    kept, heads, rows = filter_body(lines)
    assert kept == ["Real sentence one.", "Real sentence two."]
    assert heads == 1 and rows == 2


def test_filter_body_keeps_short_final_line():
    # never trim by line length: a legitimate closing line can be short
    lines = ["A long opening sentence about the findings.", "needs."]
    kept, _h, _r = filter_body(lines)
    assert kept[-1] == "needs."
