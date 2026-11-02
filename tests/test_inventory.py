# -*- coding: utf-8 -*-
"""Inventory: dedupe, per-journal accounting, gap and yield estimation."""
import os

import pytest

from wcengine.inventory import (Entry, build, load_manifest, render_text,
                                title_key, write_csv, write_markdown)


def mk(tmp_path, name, words, verdict=None, committed=False, journal="J1"):
    p = tmp_path / name
    p.write_bytes(name.encode() * 8)          # distinct bytes per name
    return Entry(path=str(p), relpath=name, journal=journal, batch="b",
                 words=words, verdict=verdict or ("ok" if 250 <= words <= 600 else
                                                  ("too-short" if words < 250 else "too-long")),
                 committed=committed)


def test_title_key_ignores_year_and_publisher_prefix():
    assert title_key("Language Learning - 2024 - Chen - Classroom talk.pdf") == \
           title_key("Classroom talk 2024.pdf")
    assert title_key("Applied linguistics Something 2021.pdf") == \
           title_key("Something.pdf")


def test_counts_add_up(tmp_path):
    e = [mk(tmp_path, "a.pdf", 300), mk(tmp_path, "b.pdf", 120), mk(tmp_path, "c.pdf", 900)]
    inv = build(e, manifest={}, target=500, per_journal=50)
    assert inv.total_ok() == 1
    assert len(inv.added()) == 3


def test_byte_duplicates_are_skipped(tmp_path):
    a = tmp_path / "a.pdf"
    a.write_bytes(b"same")
    b = tmp_path / "b.pdf"
    b.write_bytes(b"same")
    entries = [Entry(str(a), "a.pdf", "J1", "b", 300, "ok"),
               Entry(str(b), "b.pdf", "J1", "b", 300, "ok")]
    inv = build(entries, manifest={})
    assert len(inv.added()) == 1
    assert len(inv.duplicates) == 1


def test_title_duplicates_are_skipped(tmp_path):
    a = mk(tmp_path, "Classroom talk 2024.pdf", 300)
    b = mk(tmp_path, "Language Learning - 2024 - Chen - Classroom talk.pdf", 300)
    inv = build([a, b], manifest={})
    assert len(inv.added()) == 1
    assert len(inv.duplicates) == 1


def test_manifest_marks_committed(tmp_path):
    a = mk(tmp_path, "a.pdf", 300)
    man = {os.path.normcase(os.path.abspath(str(tmp_path / "a.pdf"))): "J1"}
    inv = build([a], manifest=man)
    assert len(inv.committed()) == 1
    assert inv.total_ok() == 1


def test_gap_surplus_and_deficit(tmp_path):
    entries = [mk(tmp_path, f"j1_{i}.pdf", 300, journal="J1") for i in range(60)]
    entries += [mk(tmp_path, f"j2_{i}.pdf", 300, journal="J2") for i in range(30)]
    inv = build(entries, manifest={}, target=500, per_journal=50)
    assert inv.surplus() == 10
    assert inv.deficit() == 20


def test_yield_rate_and_estimates(tmp_path):
    entries = [mk(tmp_path, f"x{i}.pdf", 300 if i < 2 else 100, journal="J1")
               for i in range(10)]
    inv = build(entries, manifest={}, per_journal=50)
    assert inv.yield_rate("J1") == pytest.approx(0.2)
    text = render_text(inv)
    assert "Observed yield" in text
    assert "needs" in text


def test_report_and_markdown_render(tmp_path):
    entries = [mk(tmp_path, "a.pdf", 300)]
    inv = build(entries, manifest={})
    text = render_text(inv)
    assert "Corpus inventory" in text
    assert "usable total" in text.lower() or "Usable total" in text

    csv_path = str(tmp_path / "inv.csv")
    md_path = str(tmp_path / "inv.md")
    write_csv(inv, csv_path)
    write_markdown(inv, md_path)
    assert os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    assert "# Corpus inventory" in open(md_path, encoding="utf-8").read()


def test_low_confidence_usable_rows_are_listed(tmp_path):
    e = mk(tmp_path, "a.pdf", 300)
    e.confidence = 75
    inv = build([e], manifest={})
    assert "below 90 confidence" in render_text(inv)


def test_title_key_strips_year_glued_to_last_word():
    short = title_key("Belonging-in-Interaction2024.pdf")
    long_ = title_key("Belonging-in-Interaction Expressing and Performing Belongings.pdf")
    assert short == "belongingininteraction"
    assert long_.startswith(short)
    assert title_key("Semantic differences 2020.pdf") == title_key("Semantic differences.pdf")


def test_prefix_duplicate_is_detected(tmp_path):
    a = mk(tmp_path, "Belonging-in-Interaction2024.pdf", 300)
    b = mk(tmp_path, "Belonging-in-Interaction Expressing and Performing Belongings.pdf", 300)
    inv = build([a, b], manifest={})
    assert len(inv.added()) == 1
    assert len(inv.duplicates) == 1


def test_short_titles_are_not_collapsed(tmp_path):
    a = mk(tmp_path, "Preface.pdf", 300)
    b = mk(tmp_path, "Preface to the second edition.pdf", 300)
    inv = build([a, b], manifest={})
    assert len(inv.added()) == 2


def test_title_key_keeps_meaningful_difference():
    assert title_key("Frames are for talking 2025.pdf") != title_key("Frames are for walking 2025.pdf")
