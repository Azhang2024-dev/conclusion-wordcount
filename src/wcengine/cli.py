# -*- coding: utf-8 -*-
"""Command line interface."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Iterable, List

from .count import count_words, count_words_letters_only, verdict
from .engine import Result, extract


def _iter_pdfs(root: str) -> Iterable[str]:
    if os.path.isfile(root):
        yield root
        return
    for dp, _d, fs in os.walk(root):
        for f in sorted(fs):
            if f.lower().endswith(".pdf"):
                yield os.path.join(dp, f)


def _print_one(r: Result, show_text: bool) -> None:
    print("=" * 96)
    print("%s" % r.path)
    print("  words=%d  verdict=%s  confidence=%d%s" % (
        r.words, r.verdict, r.confidence, "  [REVIEW]" if r.needs_review else ""))
    print("  head      : %r  (p%d)" % (r.head, r.head_page))
    print("  boundary  : %r  (p%d, %s)" % (r.boundary, r.boundary_page, r.boundary_kind))
    print("  lines     : kept %d / raw %d  (dropped headings %d, rows %d)" % (
        r.kept_lines, r.raw_lines, r.excluded_headings, r.excluded_rows))
    print("  flags     : %s" % ("|".join(r.flags) or "-"))
    for why in r.reasons:
        print("    - %s" % why)
    if r.text:
        print("  first     : %s" % r.text[:110])
        print("  last      : %s" % r.text[-110:])
    if show_text:
        print("-" * 96)
        print(r.text)


def cmd_extract(args) -> int:
    rc = 0
    for pdf in _iter_pdfs(args.path):
        try:
            r = extract(pdf, args.low, args.high)
        except Exception as e:                      # noqa: BLE001
            print("ERROR %s: %s" % (pdf, e))
            rc = 1
            continue
        _print_one(r, args.text)
    return rc


def cmd_batch(args) -> int:
    rows: List[dict] = []
    files = list(_iter_pdfs(args.path))
    for i, pdf in enumerate(files, 1):
        try:
            r = extract(pdf, args.low, args.high)
            row = r.as_row()
        except Exception as e:                      # noqa: BLE001
            row = {"path": pdf, "words": 0, "verdict": "error", "confidence": 0,
                   "needs_review": 1, "flags": "EXCEPTION", "reasons": str(e)[:160]}
        row["relpath"] = os.path.relpath(pdf, args.path) if os.path.isdir(args.path) else os.path.basename(pdf)
        rows.append(row)
        if args.progress and i % 25 == 0:
            print("  %d/%d" % (i, len(files)), file=sys.stderr)

    fields = ["relpath", "words", "verdict", "confidence", "needs_review", "flags",
              "head", "head_page", "boundary", "boundary_page", "boundary_kind",
              "pages", "raw_lines", "kept_lines", "excl_headings", "excl_rows",
              "reasons", "path"]
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    ok = sum(1 for r in rows if r["verdict"] == "ok")
    review = sum(1 for r in rows if r["needs_review"])
    print("files=%d  ok=%d (%.1f%%)  needs_review=%d  -> %s" % (
        len(rows), ok, 100.0 * ok / max(1, len(rows)), review, args.out))

    if args.review_out:
        queue = [r for r in rows if r["needs_review"]]
        queue.sort(key=lambda r: (r["confidence"], -r["words"]))
        with open(args.review_out, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(queue)
        print("review queue (%d) -> %s" % (len(queue), args.review_out))
    return 0


def cmd_review(args) -> int:
    """List the least trustworthy extractions so a human can start there."""
    with open(args.csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: (int(r.get("confidence") or 0), -int(r.get("words") or 0)))
    n = args.limit or len(rows)
    print("%-4s %-5s %-6s %-10s %s" % ("conf", "words", "verdict", "flags", "file"))
    for r in rows[:n]:
        print("%-4s %-5s %-6s %-10s %s" % (
            r.get("confidence", ""), r.get("words", ""), r.get("verdict", ""),
            (r.get("flags") or "-")[:34], r.get("relpath", "")[:60]))
    return 0


def cmd_check(args) -> int:
    """Cross-check a count with the strict tokeniser."""
    for pdf in _iter_pdfs(args.path):
        r = extract(pdf, args.low, args.high)
        strict = count_words_letters_only(r.text)
        d = (r.words - strict) / max(1, strict) * 100
        print("%-56s %5d  strict %5d  %+5.1f%%  %s" % (
            os.path.basename(pdf)[:56], r.words, strict, d, verdict(r.words, args.low, args.high)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wcengine", description=(
        "Extract a paper's conclusion section and count its words."))
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--low", type=int, default=250, help="lower word bound (default 250)")
        sp.add_argument("--high", type=int, default=600, help="upper word bound (default 600)")

    e = sub.add_parser("extract", help="inspect one PDF or a folder")
    e.add_argument("path")
    e.add_argument("--text", action="store_true", help="print the extracted body")
    common(e)
    e.set_defaults(func=cmd_extract)

    b = sub.add_parser("batch", help="run a folder and write a CSV")
    b.add_argument("path")
    b.add_argument("-o", "--out", default="wc_report.csv")
    b.add_argument("--review-out", default="", help="write a low-confidence review queue here")
    b.add_argument("--progress", action="store_true")
    common(b)
    b.set_defaults(func=cmd_batch)

    r = sub.add_parser("review", help="print a review queue from a batch CSV")
    r.add_argument("csv")
    r.add_argument("--limit", type=int, default=30)
    r.set_defaults(func=cmd_review)

    c = sub.add_parser("check", help="compare canonical vs strict tokenisation")
    c.add_argument("path")
    common(c)
    c.set_defaults(func=cmd_check)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
