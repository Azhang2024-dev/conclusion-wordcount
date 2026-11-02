# -*- coding: utf-8 -*-
"""Section-heading detection: conclusion start, backmatter boundary, sibling sections."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .text import Line

# Optional leading section number: "5 ", "5. ", "5: ", "5.2 " ...
# A page number is frequently glued in front of the heading: "452 6. Conclusion".
PAGE_LEAD = r"^(?:\d{1,4}\s+)?"
HEAD_PREFIX = PAGE_LEAD + r"\s*(?:(\d{1,2}(?:\.\d{1,2})*)\s*(?:[.)\]:]\s*|\s+))?"

# Up to two leading words are tolerated so that "Implications and Concluding Remarks"
# and "Discussion and Conclusions" still resolve to the conclusion keyword.
CONCL_KW = r"""
    (?:(?:[A-Z][A-Za-z'\u2019\-]*|and|in|of|the)\s+){0,2}
    (?:
       conclusions?\b
     | concluding\s+(?:remarks?|comments?|thoughts?|discussion|section|summary|notes?|observations?)\b
     | closing\s+(?:remarks?|thoughts?|comments?)\b
     | summary\s*(?:,|\s+and\s+)?\s*(?:and\s+)?(?:general\s+)?conclusions?\b
     | summary\s+and\s+implications\b
     | final\s+(?:remarks?|thoughts?|comments?)\b
    )
"""
# An optional short tail is allowed ("Conclusion: the future of pragmatics").
CONCL_TAIL = r".{0,72}$"

CONCL_RE = re.compile(r"(?ix)" + HEAD_PREFIX + CONCL_KW + CONCL_TAIL)

# Functionally equivalent closing sections, used only when no conclusion heading exists.
ALT_RE = re.compile(
    r"(?ix)" + HEAD_PREFIX + r"""
    (?:
       (?:general|overall|final|concluding)\s+discussion(?:\s+and\s+conclusions?\b)?
     | discussion\s*(?:,|\s+and\s+)\s*(?:conclusions?|future\s+directions?|implications)\b
     | summar(?:y|ies|ising|izing)\b.{0,60}
     | findings?\s+and\s+(?:implications?|discussion)\b.{0,40}
    )""" + CONCL_TAIL)

BACKMATTER_RE = re.compile(
    r"(?ix)" + HEAD_PREFIX + r"""
    (?:
       (?:list\s+of\s+)?references?|reference\s+list|bibliography|works\s+cited|literature\s+cited
     | acknowledg(?:e)?ments?(?:\s+(?:and|of)\s+(?:funding|financial\s+support|support|funds?))?
     | funding(?:\s+(?:information|sources?|statement|details|acknowledg\w*))?
     | (?:role|roles)\s+of\s+(?:the\s+)?funding\s+source
     | financial\s+support
     | declaration(?:s)?(?:\s+of\s+(?:competing\s+|conflicting\s+)?interests?)?
     | declaration\s+of\s+generative\s+ai
     | competing\s+interests?|conflicts?\s+of\s+interest
     | authors?['’]?\s*(?:contributions?|contribution\s+statement|statements?)
     | (?:authorship|author)\s+(?:contribution\s+)?statement
     | CRediT\b.{0,60}
     | (?:authorship\s+)?contribution\s+statement
     | data\s+availability(?:\s+statement)?|availability\s+of\s+data(?:\s+and\s+materials?)?
     | (?:supporting|supplementary)\s+(?:information|material|data)
     | (?:online\s+|supplementary\s+)?appendi(?:x|ces)\b.{0,120}
     | notes?|end\s*notes?|foot\s*notes?|notes?\s+and\s+references
     | about\s+the\s+authors?|notes?\s+on\s+contributors?|author\s+biograph(?:y|ies)
     | disclosure\s+statement|ethical\s+(?:approval|considerations)
     | ORCID
     | (?:list\s+of\s+)?(?:abbreviations|symbols)\b
     | transcript\s+key\b.{0,60}
    )\s*[:.]?\s*$""")

NEXT_SECTION_RE = re.compile(
    r"(?ix)" + HEAD_PREFIX + r"""
    (?:
       limitations?(?:\s+(?:of|to)\s+the\s+study)?
     | implications?(?:\s+for\s+\w[\w\s]{0,30})?
     | (?:theoretical|practical|pedagogical|methodological)\s+implications?
     | future\s+(?:research|studies|directions?|work|investigations?)
     | directions?\s+for\s+future\s+research
     | recommendations?(?:\s+for\s+\w[\w\s]{0,30})?
     | discussion|results?|method(?:s|ology)?|introduction|background|literature\s+review
     | references?
    )\s*[:.]?\s*$""")

NUM_LEAD = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2})*)\s*(?:[.)\]:]\s*|\s+)\S")

FINITE_VERB = re.compile(
    r"(?i)\b(am|is|are|was|were|be|been|being|have|has|had|do|does|did|"
    r"can|could|may|might|will|would|shall|should|must|"
    r"provide[sd]?|show(?:s|ed|n)?|indicat(?:e|es|ed)|suggest(?:s|ed)?|"
    r"reveal(?:s|ed)?|found|observed|reported|included|contained|examined)\b")

CONCL_VERB = re.compile(
    r"(?i)\b(are|is|were|was|have|has|had|can|could|may|might|will|would|should|"
    r"drawn|suggest|show|indicate|emerge|follow|derive|summariz|present|report|"
    r"we|our|this|these)\b")

HEAD_TAIL_BAD = re.compile(
    r"(?i)\b(sections?|regarding|written|discussed|drawn|presented|below|above|"
    r"we|our|study\s+of|of\s+the\s+study)\b")

TITLE_FUNC = {
    "and", "or", "for", "of", "the", "in", "to", "a", "an", "on", "at", "by",
    "with", "from", "as", "into", "upon", "toward", "towards", "vs",
}

REFERENCES_ONLY = re.compile(
    r"(?i)^\s*(?:\d{1,2}(?:\.\d{1,2})*[.)]?\s*)?"
    r"(?:(?:list\s+of\s+)?references?|reference\s+list|bibliography|"
    r"works\s+cited|literature\s+cited)\s*[:.]?\s*$")


def heading_number(s: str) -> str:
    m = NUM_LEAD.match(s)
    return m.group(1) if m else ""


def is_title_case(s: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z'\u2019\-]*", s)
    if not words or not words[0][0].isupper():
        return False
    for w in words:
        if w.lower().strip(".") in TITLE_FUNC:
            continue
        if not w[0].isupper():
            return False
    return True


def concl_head_ok(s: str) -> bool:
    """Morphological gate for a conclusion heading (ported from a validated heuristic)."""
    s = s.strip()
    m = re.match(r"^\s*(?:\d{1,4}\s+)?(?:\d{1,2}(?:\.\d{1,2})*\s*(?:[.)\]:]\s*|\s+))?", s)
    core = s[m.end():] if m else s
    if not core or not core[0].isupper():
        return False
    n = len(s.split())
    if n > 14 or len(s) > 120:
        return False
    if s.endswith((",", ";")):
        return False
    if CONCL_VERB.search(core) and n > 3:
        return False
    if HEAD_TAIL_BAD.search(core):
        return False
    if n <= 6:
        return True
    if ":" in s and n <= 14:
        return True
    if m and n <= 12:
        return True
    return is_title_case(core) and n <= 12


def simple_head_ok(s: str, max_words: int = 10, max_len: int = 95) -> bool:
    """Generic section heading: no terminal punctuation, no finite verb."""
    s = s.strip()
    if not (2 <= len(s) <= max_len):
        return False
    if len(s.split()) > max_words:
        return False
    if s.endswith((".", ",", ";", ":")):
        return False
    if FINITE_VERB.search(s):
        return False
    return True


def backmatter_ok(s: str, max_words: int = 10, max_len: int = 110) -> bool:
    """Backmatter heading; tolerates a trailing period on short headings ("Appendix A.")."""
    t = s.strip()
    if simple_head_ok(t, max_words, max_len):
        return True
    if t.endswith(".") and len(t.split()) <= 6 and not FINITE_VERB.search(t):
        return True
    return False


def references_index(lines: List[Line], lo: int) -> int:
    """Index of the last References-type heading; len(lines) when absent.

    The *last* one is used because body text often mentions "References" earlier.
    """
    for i in range(len(lines) - 1, lo - 1, -1):
        s = lines[i][1]
        if REFERENCES_ONLY.match(s) and simple_head_ok(s, 8, 60):
            return i
    return -1


def find_conclusion(lines: List[Line], lo: int, stop: int) -> Tuple[int, bool, int]:
    """Return (index, used_alt_pattern, candidate_count); index -1 when not found."""
    hits = [i for i in range(lo, stop)
            if CONCL_RE.match(lines[i][1]) and concl_head_ok(lines[i][1])]
    if hits:
        return hits[-1], False, len(hits)
    alt = [i for i in range(lo, stop)
           if ALT_RE.match(lines[i][1]) and concl_head_ok(lines[i][1])]
    if alt:
        return alt[-1], True, len(alt)
    return -1, False, 0


def find_boundary(lines: List[Line], hi: int, concl_num: str) -> Tuple[Optional[int], str]:
    """Index of the first line after the conclusion that starts the next unit."""
    for j in range(hi + 1, len(lines)):
        s = lines[j][1]
        # A transcript key is often one very long line, so it is matched on its
        # opening words rather than on a heading-length pattern.
        if re.match(r"(?i)^\s*transcript\s+key\b", s):
            return j, "transcript-key"
        if BACKMATTER_RE.match(s) and backmatter_ok(s, 10, 110):
            return j, "backmatter"
        if NEXT_SECTION_RE.match(s) and simple_head_ok(s, 10, 90):
            bn = heading_number(s)
            if concl_num and bn and bn.startswith(concl_num + "."):
                continue                       # subsection, still part of this chapter
            if not concl_num and bn and "." in bn:
                continue
            return j, "section"
    # Fallback: cut at the first reference list entry.
    for j in range(hi + 1, len(lines)):
        if REFERENCES_ONLY.match(lines[j][1]) or re.match(r"^[A-Z][a-z]+,\s+[A-Z]\.", lines[j][1]):
            return j, "fallback"
    return None, "none"
