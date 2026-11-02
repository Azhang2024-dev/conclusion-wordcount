# Counting specification

This document is the normative definition of the numbers produced by `wcengine`.
It is written to be quotable in a methods chapter.

## 1. Unit of analysis

The **conclusion section** of a research article: the span that begins after the
conclusion heading and ends before the first backmatter unit.

When no conclusion heading exists, a functionally equivalent closing section
(`General discussion`, `Discussion and conclusions`, `Concluding remarks`,
`Summary and conclusions`) may be used; such rows are marked `ALT_HEAD`.

## 2. Word (token) definition

A token is a maximal whitespace-delimited run that contains at least one letter
(`A–Z`, `a–z`) or digit (`0–9`).

| input | tokens | count |
| --- | --- | --- |
| `findings,` | `findings,` | 1 |
| `state-of-the-art` | `state-of-the-art` | 1 |
| `don't` | `don't` | 1 |
| `1999` | `1999` | 1 |
| `p. 14` | `p.` `14` | 2 |
| `&` | — | 0 |
| `—` | — | 0 |

Rationale: this matches the orthographic word count used by Word and by most
journal word-count tools, so the figures are comparable with published counts.

A strict variant (`count_words_letters_only`) drops numerals and is provided for
sensitivity checks only; it is not the reported figure.

## 3. Exclusions

Not counted, in all cases:

1. The conclusion heading itself, including its number and any subtitle.
2. Sub-headings inside the conclusion chapter (`7.1 Patterns of use`).
3. Reference lists, under any of: `References`, `Reference list`, `List of References`,
   `Bibliography`, `Works Cited`, `Literature Cited`.
4. Acknowledgements, funding statements, declarations of interest, CRediT statements,
   data availability statements, ORCID, author biographies.
5. Appendices, supplementary material, notes, endnotes, footnotes, transcript keys,
   abbreviation and symbol lists.
6. Table bodies and figure captions.
7. Page furniture: running heads, page numbers, publisher download stamps, copyright and
   licence lines, journal volume/issue banners.

## 4. Line-level operations

**Hyphenation repair.** If a line ends with `-` and the next line begins with a lowercase
letter, the two are joined before tokenisation (`conclu-` + `sion` → `conclusion`). A
capitalised continuation is not joined, because it is usually a genuine word boundary.

**Running-head removal.** A line is removed if its digit-masked, punctuation-stripped form
recurs on at least `max(2, 30% of pages)` of the document. Digit masking is essential:
`36 TESOL QUARTERLY` and `37 TESOL QUARTERLY` are the same running head.

**Table-row test.** A line with three or more tokens where at least 45% of tokens contain
no two-letter alphabetic sequence is treated as a data row and removed.

**Sub-heading test.** A line of at most 9 words and 95 characters, without terminal
punctuation, that is numbered, all-capitals, or title case, is treated as a sub-heading.

Table rows are tested before sub-headings, because a data line such as `1 62 63 >4 A5`
begins with a digit and would otherwise be read as a numbered heading.

## 5. Boundary determination

The conclusion heading is the **last** line in the search window that matches the
conclusion pattern and passes the morphological gate. The search window stops at the last
`References`-type heading, so a cited title such as *Conclusion: …* cannot be picked up.

The end boundary is the first following line that is:

- a backmatter heading (`references`, `acknowledgements of funding`, `appendix A.`,
  `data availability`, `notes`, `about the authors`, …), or
- a sibling section heading (`limitations`, `implications`, `future research`, …) whose
  section number does not extend the conclusion's own number.

A numbered subsection of the conclusion (`7.1` under `7 Conclusions`) does **not** end
the span; its prose counts and its heading does not.

If no boundary is found, the span is cut at the first reference-list line and the row is
flagged `NO_BOUNDARY`.

## 6. Confidence

Confidence is an integer in `[0, 100]`. It starts at 100 and each distinct flag subtracts
its penalty once. `confidence < 70` places the row in the review queue.

Confidence measures **how likely the number is wrong**, not how long the text is. A
250-word conclusion that ends on a full stop with a clean boundary scores 100; a
1200-word span that ran into the reference list does not.

## 7. What is deliberately not automated

- Deciding whether a merged `Discussion and Conclusion` chapter should be counted whole.
- Choosing between two plausible conclusion headings when both pass the gate.
- Judging whether a 600-word span is a conclusion or a conclusion plus a coda.

These are reported through flags and left to the reviewer. A count without a boundary
judgement is not evidence.
