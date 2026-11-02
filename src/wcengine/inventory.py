# -*- coding: utf-8 -*-
"""Corpus inventory: what a batch of word counts adds up to, and what is still missing.

Turns one or more ``wcengine batch`` reports into an accounting statement:

    committed (already in the corpus) + newly usable - duplicates = total
    total vs a target, overall and per journal

Duplicates are removed two ways, because either one alone misses cases: byte
identity (the same PDF saved twice under different names) and a normalised title
key (the same article saved with a year suffix).
"""
from __future__ import annotations

import csv
import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

OK = "ok"
SHORT = "too-short"
LONG = "too-long"
EMPTY = "no-body"


@dataclass
class Entry:
    path: str
    relpath: str
    journal: str
    batch: str
    words: int
    verdict: str
    flags: str = ""
    confidence: int = 100
    committed: bool = False
    duplicate_of: str = ""


@dataclass
class JournalRow:
    journal: str
    committed: int = 0
    added: int = 0
    screened: int = 0          # new files seen for this journal (all verdicts)

    @property
    def total(self) -> int:
        return self.committed + self.added

    def gap(self, per_journal: int) -> int:
        return self.total - per_journal


@dataclass
class Inventory:
    entries: List[Entry] = field(default_factory=list)
    duplicates: List[Entry] = field(default_factory=list)
    target: int = 500
    per_journal: int = 50
    low: int = 250
    high: int = 600

    # ---- derived views -------------------------------------------------
    def committed(self) -> List[Entry]:
        return [e for e in self.entries if e.committed]

    def added(self) -> List[Entry]:
        return [e for e in self.entries if not e.committed]

    def committed_ok(self) -> List[Entry]:
        return [e for e in self.committed() if e.verdict == OK]

    def added_ok(self) -> List[Entry]:
        return [e for e in self.added() if e.verdict == OK]

    def total_ok(self) -> int:
        return len(self.committed_ok()) + len(self.added_ok())

    def journals(self) -> Dict[str, JournalRow]:
        rows: Dict[str, JournalRow] = {}
        for e in self.entries:
            row = rows.setdefault(e.journal or "unlabelled", JournalRow(e.journal or "unlabelled"))
            if e.committed:
                if e.verdict == OK:
                    row.committed += 1
            else:
                row.screened += 1
                if e.verdict == OK:
                    row.added += 1
        return rows

    def surplus(self) -> int:
        return sum(max(0, r.gap(self.per_journal)) for r in self.journals().values())

    def deficit(self) -> int:
        return sum(max(0, -r.gap(self.per_journal)) for r in self.journals().values())

    def yield_rate(self, journal: str) -> Optional[float]:
        r = self.journals().get(journal)
        if not r or not r.screened:
            return None
        return r.added / r.screened


# ---------------------------------------------------------------------------

def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def title_key(name: str) -> str:
    """Loose key for spotting the same article saved under two file names."""
    s = os.path.basename(name).lower()
    s = re.sub(r"\.pdf$", "", s)
    # Publisher export form: "Language Learning - 2024 - Chen - Classroom talk"
    s = re.sub(r"^.{2,70}?\s+-\s+(?:19|20)\d{2}\s+-\s+.{1,60}?\s+-\s+", "", s)
    # Leading journal name, with or without a separator
    s = re.sub(r"^(?:language learning|journal of [a-z ]+|tesol quarterly|"
               r"applied linguistics|ijcl|cognitive linguistics)\s*[-\u2013]?\s*", "", s)
    s = re.sub(r"\b(19|20)\d{2}\b", " ", s)          # year as a separate token
    s = re.sub(r"[^a-z0-9]+", "", s)
    # Year glued to the last word: "belongingininteraction2024" -> "belongingininteraction"
    s = re.sub(r"(?:19|20)\d{2}$", "", s)
    return s[:56]


def _title_match(tk: str, titles: Dict[str, str]) -> Optional[str]:
    """Find an existing key that denotes the same article.

    Byte identity is not enough: the same paper is routinely saved once with the
    full title and once with a truncated one. A shared prefix of at least 30
    characters catches that without collapsing genuinely different titles.
    """
    if tk in titles:
        return titles[tk]
    if len(tk) >= 20:
        for k, v in titles.items():
            if k.startswith(tk):
                return v
    for k, v in titles.items():
        if len(k) >= 20 and tk.startswith(k):
            return v
    return None


def _journal_of(relpath: str, depth: int) -> str:
    parts = [p for p in re.split(r"[\\/]+", relpath) if p]
    if len(parts) <= depth + 1:
        return ""
    return parts[depth]


def _to_int(v, default=0) -> int:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def load_report(path: str, batch: str = "", journal_depth: int = 0,
                root: Optional[str] = None) -> List[Entry]:
    """Read a CSV written by ``wcengine batch``."""
    out: List[Entry] = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rel = r.get("relpath") or os.path.basename(r.get("path", ""))
            full = r.get("path") or (os.path.join(root, rel) if root else rel)
            if not os.path.isabs(full) and root:
                full = os.path.join(root, full)
            out.append(Entry(
                path=full,
                relpath=rel,
                journal=_journal_of(rel, journal_depth),
                batch=batch or os.path.basename(path),
                words=_to_int(r.get("words")),
                verdict=r.get("verdict", "") or (OK if _to_int(r.get("words")) else EMPTY),
                flags=r.get("flags", ""),
                confidence=_to_int(r.get("confidence"), 100),
            ))
    return out


def load_manifest(path: str, status: str = "active",
                  status_col: str = "status", path_col: str = "pdf_path",
                  journal_col: str = "journal") -> Dict[str, str]:
    """Map normalised absolute path -> journal for rows in the wanted status."""
    kept: Dict[str, str] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if (r.get(status_col) or "").strip() != status:
                continue
            p = (r.get(path_col) or "").strip()
            if p:
                kept[os.path.normcase(p)] = (r.get(journal_col) or "").strip()
    return kept


def build(entries: Iterable[Entry], manifest: Optional[Dict[str, str]] = None,
          target: int = 500, per_journal: int = 50,
          low: int = 250, high: int = 600) -> Inventory:
    inv = Inventory(target=target, per_journal=per_journal, low=low, high=high)
    entries = list(entries)

    if manifest:
        for e in entries:
            jn = manifest.get(os.path.normcase(os.path.abspath(e.path)))
            if jn is not None:
                e.committed = True
                if jn:
                    e.journal = jn

    # Deduplicate the uncommitted pool against everything, then against itself.
    hashes: Dict[str, str] = {}
    titles: Dict[str, str] = {}
    for e in entries:
        if e.committed:
            try:
                hashes.setdefault(_sha256(e.path), e.relpath)
            except OSError:
                pass
            titles.setdefault(title_key(e.relpath), e.relpath)

    for e in entries:
        if e.committed:
            continue
        why = ""
        try:
            h = _sha256(e.path)
        except OSError:
            h = ""
        if h and h in hashes:
            why = "byte-identical to %s" % hashes[h]
        else:
            tk = title_key(e.relpath)
            hit = _title_match(tk, titles) if tk else None
            if hit:
                why = "same title as %s" % hit
            elif h and h in hashes:
                why = "byte-identical to %s" % hashes[h]
        if why:
            e.duplicate_of = why
            inv.duplicates.append(e)
            continue
        if h:
            hashes[h] = e.relpath
        tk = title_key(e.relpath)
        if tk and _title_match(tk, titles) is None:
            titles[tk] = e.relpath
        inv.entries.append(e)

    inv.entries.extend(e for e in entries if e.committed)
    return inv


# ---------------------------------------------------------------------------

def render_text(inv: Inventory) -> str:
    lines: List[str] = []
    add = lines.append
    total = inv.total_ok()
    add("=" * 78)
    add("Corpus inventory")
    add("=" * 78)
    add("Bounds: %d-%d words" % (inv.low, inv.high))
    add("")
    add("Committed (manifest)      : %d, of which usable %d" % (
        len(inv.committed()), len(inv.committed_ok())))
    add("New files screened        : %d, of which usable %d" % (
        len(inv.added()), len(inv.added_ok())))
    add("Duplicates skipped        : %d" % len(inv.duplicates))
    add("Usable total              : %d  (target %d, short by %d)" % (
        total, inv.target, max(0, inv.target - total)))
    add("")

    rows = inv.journals()
    if rows:
        add("%-42s %9s %6s %6s %6s %8s" % ("journal", "committed", "new", "total", "target", "gap"))
        add("-" * 78)
        for jn, r in sorted(rows.items(), key=lambda x: -x[1].total):
            add("%-42s %9d %6d %6d %6d %+8d" % (
                jn[:42], r.committed, r.added, r.total, inv.per_journal,
                r.gap(inv.per_journal)))
        add("")
        add("Surplus in over-filled journals: %d" % inv.surplus())
        add("Deficit in under-filled journals: %d" % inv.deficit())
        add("(a surplus does not transfer: the per-journal quotas are counted separately)")
        add("")

    yields = [(jn, inv.yield_rate(jn)) for jn in rows]
    yields = [(jn, y) for jn, y in yields if y is not None and rows[jn].screened >= 5]
    if yields:
        add("Observed yield (usable / screened) for journals with >=5 new files:")
        for jn, y in sorted(yields, key=lambda x: -x[1]):
            add("  %-42s %5.1f%%  (%d/%d)" % (
                jn[:42], y * 100, rows[jn].added, rows[jn].screened))
        add("")
        add("Estimated downloads still needed, assuming the observed yield holds:")
        for jn, r in sorted(rows.items(), key=lambda x: x[1].gap(inv.per_journal)):
            need = -r.gap(inv.per_journal)
            if need <= 0:
                continue
            y = inv.yield_rate(jn)
            est = ("%d files" % int(need / y)) if y and y > 0 else "no yield data"
            add("  %-42s needs %3d  -> %s" % (jn[:42], need, est))
        add("")

    flagged = [e for e in inv.added_ok() if e.confidence < 90]
    if flagged:
        add("Usable but below 90 confidence (open these before using):")
        for e in sorted(flagged, key=lambda x: x.confidence):
            add("  conf=%-3d %4d words  %-24s %s" % (
                e.confidence, e.words, e.flags[:24], os.path.basename(e.path)[:44]))
        add("")
    return "\n".join(lines)


def write_csv(inv: Inventory, path: str) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["batch", "journal", "file", "words", "verdict", "confidence",
                    "flags", "committed", "counted", "duplicate_of"])
        for e in sorted(inv.entries, key=lambda x: (x.journal, x.relpath)):
            w.writerow([e.batch, e.journal, os.path.basename(e.relpath), e.words,
                        e.verdict, e.confidence, e.flags,
                        "yes" if e.committed else "no",
                        "yes" if e.verdict == OK else "no", ""])
        for e in inv.duplicates:
            w.writerow([e.batch, e.journal, os.path.basename(e.relpath), e.words,
                        e.verdict, e.confidence, e.flags, "no", "no", e.duplicate_of])


def write_markdown(inv: Inventory, path: str) -> None:
    total = inv.total_ok()
    lines = [
        "# Corpus inventory",
        "",
        "Bounds: %d-%d words. Target %d papers, %d per journal." % (
            inv.low, inv.high, inv.target, inv.per_journal),
        "",
        "| | count |",
        "| --- | --- |",
        "| committed, usable | %d |" % len(inv.committed_ok()),
        "| new, usable | %d |" % len(inv.added_ok()),
        "| duplicates skipped | %d |" % len(inv.duplicates),
        "| **usable total** | **%d** |" % total,
        "| short by | %d |" % max(0, inv.target - total),
        "",
        "| journal | committed | new | total | gap | yield |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for jn, r in sorted(inv.journals().items(), key=lambda x: -x[1].total):
        y = inv.yield_rate(jn)
        lines.append("| %s | %d | %d | %d | %+d | %s |" % (
            jn, r.committed, r.added, r.total, r.gap(inv.per_journal),
            ("%.0f%%" % (y * 100)) if y is not None else "-"))
    lines += ["", "Surplus %d, deficit %d." % (inv.surplus(), inv.deficit()), ""]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
