# -*- coding: utf-8 -*-
"""Review signals and confidence scoring."""
from wcengine.review import PENALTIES, REVIEW_THRESHOLD, Signals, assess


def test_signal_penalty_accumulates():
    s = Signals()
    s.add("TRUNC_TAIL", "tail")
    s.add("URL_IN_BODY", "url")
    assert s.confidence == 100 - PENALTIES["TRUNC_TAIL"] - PENALTIES["URL_IN_BODY"]
    assert s.needs_review is (s.confidence < REVIEW_THRESHOLD)


def test_duplicate_flag_not_penalised_twice():
    s = Signals()
    s.add("TRUNC_TAIL")
    before = s.confidence
    s.add("TRUNC_TAIL")
    assert s.confidence == before


def test_clean_body_scores_high():
    body = ("Our findings indicate that the intervention improved outcomes across both groups. "
            "These results extend earlier work and suggest several directions for future study.")
    s = assess(body, 28, kept_lines=12, head_page=3, boundary_page=5,
               alt=False, n_heads=1)
    assert s.confidence == 100
    assert not s.needs_review


def test_truncated_tail_is_flagged():
    body = "The findings suggest that learners benefit from explicit instruction and motivational"
    s = assess(body, 13, 4, 3, 4, False, 1)
    assert "TRUNC_TAIL" in s.flags
    assert s.needs_review


def test_url_is_flagged():
    body = "The corpus is available at https://example.org/corpus for further analysis."
    s = assess(body, 11, 9, 3, 5, False, 1)
    assert "URL_IN_BODY" in s.flags


def test_empty_body_scores_zero():
    s = assess("", 0, 0, 0, 0, False, 0)
    assert s.confidence == 0
    assert s.needs_review


def test_absurdly_long_span_is_flagged():
    body = "word " * 2000
    s = assess(body, 2000, 120, 3, 12, False, 1)
    assert "SPAN_TOO_LARGE" in s.flags
    assert s.needs_review


def test_normal_long_conclusion_is_not_flagged_for_size():
    body = " ".join(["word"] * 800) + "."
    s = assess(body, 800, 30, 3, 8, False, 1)
    assert "SPAN_TOO_LARGE" not in s.flags
