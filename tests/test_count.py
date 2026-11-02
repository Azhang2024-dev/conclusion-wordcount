# -*- coding: utf-8 -*-
"""Tokenisation and counting rules."""
from wcengine.count import count_words, count_words_letters_only, verdict


def test_punctuation_is_not_counted():
    assert count_words("words, and more.") == 3
    assert count_words("– § = & + %") == 0


def test_hyphenated_compound_is_one_word():
    assert count_words("state-of-the-art model") == 2


def test_contraction_is_one_word():
    assert count_words("don't stop") == 2
    assert count_words("practitioners' beliefs") == 2


def test_numbers_count():
    assert count_words("published in 1999") == 3
    assert count_words("(p. 14)") == 2


def test_letters_only_variant_drops_numbers():
    text = "published in 1999 (p. 14)"
    assert count_words(text) == 5
    assert count_words_letters_only(text) == 3


def test_verdict_bounds():
    assert verdict(0) == "no-body"
    assert verdict(249) == "too-short"
    assert verdict(250) == "ok"
    assert verdict(600) == "ok"
    assert verdict(601) == "too-long"
    assert verdict(200, 200, 600) == "ok"
