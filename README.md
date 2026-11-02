# Conclusion Word Count

Extract the conclusion section of an academic PDF and count its words, with an explicit
trust score and a review queue for the cases a regex cannot settle.

Built for corpus work: phrase-frame studies, human-vs-AI comparison corpora, and any
pipeline that needs a length gate such as "conclusion must be 250–600 words".

## Why this exists

Word counts from PDFs are easy to compute and easy to get wrong. In practice the errors
come from the boundary, not the tokeniser:

- the reference list is titled `List of References`, so `References` never matches
- the heading is `6: Conclusion` rather than `6. Conclusion`
- the conclusion chapter has subsections (`7.1 Implications`) that get cut off
- the acknowledgement heading is `Acknowledgement of funding`
- running heads such as `36 TESOL QUARTERLY` survive on every page and pollute the body
- a footnote block or a transcript key is glued onto the end of the conclusion

Every one of those was observed in real corpora and each has a regression test here.

Because a boundary decision is a judgement call, the library does not pretend otherwise.
Each extraction returns a **confidence score** plus the evidence used (`head`, `boundary`,
pages, dropped line counts, flags). Low-confidence rows go to a review queue.

## Install

```bash
pip install pypdfium2
pip install -e .
```

Python 3.9+.

## Use

```bash
# inspect one paper, with its body printed
wcengine extract paper.pdf --text

# run a folder and write a report plus a review queue
wcengine batch ./pdfs -o report.csv --review-out review_queue.csv

# what should a human look at first?
wcengine review report.csv --limit 20

# compare the canonical count with a strict letters-only tokeniser
wcengine check ./pdfs
```

```python
from wcengine import extract

r = extract("paper.pdf", low=250, high=600)
print(r.words, r.verdict, r.confidence)
print(r.head, r.boundary, r.flags)
if r.needs_review:
    print("manual check:", r.reasons)
```

## Counting rules

A **word** is a whitespace-delimited run containing at least one letter or digit.

- `state-of-the-art` → 1 word
- `don't` → 1 word
- `1999`, `p.`, `14` → 3 words (this matches Word and most journal counters)
- a stand-alone `–`, `§`, `=`, `&`, `+` → 0 words

Excluded from the count:

- the conclusion heading itself (`Conclusion`, `5 Conclusion`, `6: Conclusion`)
- sub-headings inside the conclusion chapter
- the reference list, acknowledgements, funding, conflicts, data availability, appendices,
  endnotes, author biographies, ORCID, abbreviations
- table bodies and figure captions
- running heads, page numbers, download stamps, licence lines, journal banners

End-of-line hyphenation is repaired: `conclu-` + `sion` → `conclusion`.

Full specification: [docs/SPEC.md](docs/SPEC.md).

## Flags

| flag | meaning | penalty |
| --- | --- | --- |
| `NO_CONCL_HEAD` | no conclusion section found | 100 |
| `NO_BOUNDARY` | no stopping point; ran to end of document | 45 |
| `SHORT_SPAN` | fewer than 8 lines kept | 30 |
| `REF_LEAK` | reference-list patterns inside the body | 30 |
| `TRUNC_TAIL` | body does not end with sentence punctuation | 25 |
| `REF_ENTRIES` | reference entries inside the body | 25 |
| `URL_IN_BODY` | non-repository link inside the body | 20 |
| `SYMBOL_DENSE` | transcript notation or data dump | 20 |
| `TABLE_LEAK` | table rows inside the body | 20 |
| `TIGHT_SPAN` | thin span, boundary on the heading's page | 15 |
| `ALT_HEAD` | no Conclusion heading; Discussion-type section used | 8 |
| `MULTI_HEAD` | several conclusion-like headings; the last was taken | 5 |

Confidence starts at 100 and each flag is deducted once. Below **70** the row is queued
for review. Data-availability links (`doi.org`, `osf.io`, `zenodo`, …) are not treated as
contamination.

## Validation

On a 55-paper sample from *Applied Linguistics*, *Cognitive Linguistics* and *TESOL
Quarterly*, manual review of each boundary agreed with every engine verdict. The two
papers whose counts were inflated by footnote and transcript-key bleed (`amac031`: 569 →
458, `amae029`: 564 → 493) were exactly the two lowest-confidence rows among the passing
set — the scoring surfaced what the human found, in the same order.

Cross-checking against an independent extractor (PyMuPDF) on the same page spans gives a
median absolute difference of about 5%; the engine reads lower because headings, table
bodies and glossary lists are excluded by design.

## Limits

- The boundary is a heuristic. Anything near a threshold (roughly 590–610 or 190–210
  words) should be opened and read.
- Conclusion chapters merged with a Discussion section can legitimately run well past 600
  words; this is reported, not resolved.
- Two-column and landscape layouts are handled through the PDF text layer, so reading
  order depends on how the publisher tagged the page.
- Scanned PDFs without a text layer return `NO_CONCL_HEAD`.

## Tests

```bash
pip install pytest
pytest -q
```

The suite covers tokenisation, heading morphology, body filtering, and the scoring rules.
No PDFs are required; fixtures are synthetic.

## Licence

MIT.

## Maintenance

`scripts/publish.py` pushes this working tree to GitHub. It reads the token from the
Windows user environment variable `Github_personal_access_token_1` and passes it to git
as a one-shot `http.extraheader`, so the credential never appears in the remote URL,
in `git config`, in process arguments, or in any file. Remove or lock this script down
before publishing a fork.

```bash
python scripts/publish.py
```
